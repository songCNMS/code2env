#!/usr/bin/env python3
"""feishu-docs skill OAuth 鉴权模块（daemon 卡片 + 飞书粘贴回群 + GitHub Pages echo）

飞书文档/表格修改需要 user_access_token（用户身份）。授权流程：
  1. auth.py 生成授权 URL（含 state），调本机 feishu_daemon /api/question/ask
     发带 url_button 的卡片到对应 intern 的主管飞书群
  2. 主管点按钮 → 手机浏览器打开飞书授权页 → 同意
  3. 飞书 302 redirect 到 config.redirect_uri（GitHub Pages 的 echo.html）
  4. echo.html 从 URL 参数提取 code/state，一键复制 "FEISHU_OAUTH code=... state=..."
  5. 主管回飞书群粘贴 → relay 分发 → daemon 匹配 pending 写入 answer
  6. auth.py 轮询 /api/question/poll 拿到 answer → regex 提取 code/state
  7. POST /open-apis/authen/v2/oauth/token grant_type=authorization_code 换 token
  8. 存 ~/.feishu_skill_token.json (chmod 0600)

用法:
  python3 auth.py login --intern <intern_name>    # 触发 OAuth
  python3 auth.py status                          # 查看 token 状态
  from auth import get_access_token               # 其他脚本 import

配置（一次性）:
  ../config.json 填 {"redirect_uri": "https://..."}（同飞书后台白名单一致）
  <WORK_AGENTS_ROOT>/key.txt 第 1 行 app_id、第 2 行 app_secret
    WORK_AGENTS_ROOT 先取 env 同名变量（VS Code 插件 / hooks 自动 export），
    否则从 CWD 向上递归查找同时含 key.txt + .feishu_registry/ 的目录（见 root.py）。
"""

import argparse
import json
import os
import re
import secrets
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

from root import find_work_agents_root

TOKEN_FILE = Path.home() / ".feishu_skill_token.json"
DAEMON_META = Path("/tmp/feishu_daemon.json")
CONFIG_FILE = Path(__file__).resolve().parent.parent / "config.json"

SCOPE = "docx:document sheets:spreadsheet drive:file offline_access wiki:wiki"
FEISHU_AUTHORIZE_URL = "https://accounts.feishu.cn/open-apis/authen/v1/authorize"
FEISHU_TOKEN_URL = "https://open.feishu.cn/open-apis/authen/v2/oauth/token"

POLL_INTERVAL_SEC = 3
POLL_TIMEOUT_SEC = 600

ANSWER_RE = re.compile(r"FEISHU_OAUTH\s+code=(\S+?)(?:\s+state=(\S*))?(?:\s|$)")


def _read_credentials():
    root = Path(find_work_agents_root())
    key_file = root / "key.txt"
    if not key_file.exists():
        sys.exit(f"credentials not found: {key_file}")
    lines = key_file.read_text().strip().splitlines()
    if len(lines) < 2:
        sys.exit(f"{key_file} must have app_id on line 1 and app_secret on line 2")
    return lines[0].strip(), lines[1].strip()


def _read_config():
    if not CONFIG_FILE.exists():
        sys.exit(
            f"config not found: {CONFIG_FILE}\n"
            "create it with: {\"redirect_uri\": \"https://<your-echo-page-url>\"}\n"
            "must match the redirect_uri whitelisted in Feishu app console."
        )
    cfg = json.loads(CONFIG_FILE.read_text())
    if not cfg.get("redirect_uri"):
        sys.exit(f"{CONFIG_FILE} missing or empty 'redirect_uri'")
    return cfg


def _daemon_base_url():
    if not DAEMON_META.exists():
        sys.exit(f"daemon metadata missing: {DAEMON_META} (is feishu_daemon running?)")
    meta = json.loads(DAEMON_META.read_text())
    port = meta.get("http_port") or meta.get("port")
    if not port:
        sys.exit(f"daemon http_port missing in {DAEMON_META}")
    return f"http://localhost:{port}"


def _post_json(url, body, timeout=15):
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def _get_json(url, timeout=15):
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def _save_token(resp):
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(seconds=int(resp["expires_in"]))
    refresh_exp_sec = resp.get("refresh_token_expires_in")
    payload = {
        "access_token": resp["access_token"],
        "refresh_token": resp.get("refresh_token"),  # absent when app lacks offline_access
        "expires_at": expires_at.isoformat(),
        "refresh_expires_at": (
            (now + timedelta(seconds=int(refresh_exp_sec))).isoformat()
            if refresh_exp_sec
            else None
        ),
        "scope": resp.get("scope", ""),
    }
    TOKEN_FILE.write_text(json.dumps(payload, indent=2))
    os.chmod(TOKEN_FILE, 0o600)


def _load_token():
    if not TOKEN_FILE.exists():
        sys.exit(f"no token at {TOKEN_FILE}; run: python3 auth.py login --intern <name>")
    return json.loads(TOKEN_FILE.read_text())


def _exchange_code(app_id, app_secret, code, redirect_uri):
    resp = _post_json(FEISHU_TOKEN_URL, {
        "grant_type": "authorization_code",
        "client_id": app_id,
        "client_secret": app_secret,
        "code": code,
        "redirect_uri": redirect_uri,
    })
    if "access_token" not in resp:
        sys.exit(f"token exchange failed: {json.dumps(resp, ensure_ascii=False)}")
    print(
        f"token exchange resp keys: {sorted(resp.keys())}",
        file=sys.stderr,
    )
    return resp


def _refresh(app_id, app_secret, refresh_token):
    resp = _post_json(FEISHU_TOKEN_URL, {
        "grant_type": "refresh_token",
        "client_id": app_id,
        "client_secret": app_secret,
        "refresh_token": refresh_token,
    })
    if "access_token" not in resp:
        sys.exit(
            "refresh failed; refresh_token likely expired. "
            "re-run: python3 auth.py login --intern <name>. "
            f"server said: {json.dumps(resp, ensure_ascii=False)}"
        )
    return resp


def get_access_token():
    """读缓存 token，过期前 5 分钟自动用 refresh_token 续。供其他脚本 import。"""
    token = _load_token()
    now = datetime.now(timezone.utc)
    expires = datetime.fromisoformat(token["expires_at"])
    if now + timedelta(seconds=300) >= expires:
        refresh_token = token.get("refresh_token")
        if not refresh_token:
            sys.exit(
                "access token expired and no refresh_token cached (app lacks offline_access). "
                "re-run: python3 auth.py login --intern <name>"
            )
        app_id, app_secret = _read_credentials()
        resp = _refresh(app_id, app_secret, refresh_token)
        _save_token(resp)
        return resp["access_token"]
    return token["access_token"]


def _extract_answer_text(answers):
    """answers 在 daemon 的 shape：{question_text_or_key: value_str}。union 所有 value。"""
    if isinstance(answers, str):
        return answers
    if isinstance(answers, dict):
        return " ".join(str(v) for v in answers.values() if v)
    return str(answers)


def cmd_login(intern_name):
    app_id, app_secret = _read_credentials()
    cfg = _read_config()
    redirect_uri = cfg["redirect_uri"]
    daemon_url = _daemon_base_url()

    state = secrets.token_urlsafe(16)
    params = {
        "app_id": app_id,
        "redirect_uri": redirect_uri,
        "state": state,
        "scope": SCOPE,
    }
    auth_url = f"{FEISHU_AUTHORIZE_URL}?{urllib.parse.urlencode(params)}"

    ask_resp = _post_json(f"{daemon_url}/api/question/ask", {
        "intern_name": intern_name,
        "tool_name": "FeishuAuth",
        "questions": [{
            "header": "飞书 OAuth 授权",
            "question": (
                "点下方按钮打开飞书授权页，同意后回 echo 页复制 code；"
                "回群粘贴 `FEISHU_OAUTH code=... state=...` 即可"
            ),
            "options": [{
                "label": "打开飞书授权页",
                "description": "跳转飞书授权，授权后 echo 页给出 code",
                "url": auth_url,
                "recommended": True,
            }],
        }],
    })
    if not ask_resp.get("ok"):
        sys.exit(f"daemon /api/question/ask failed: {ask_resp}")

    print(f"Auth card sent to Feishu group for intern '{intern_name}'.")
    print(
        f"Waiting for you to authorize and paste 'FEISHU_OAUTH code=... state=...' "
        f"back to the group (up to {POLL_TIMEOUT_SEC}s)..."
    )

    deadline = time.time() + POLL_TIMEOUT_SEC
    poll_url = (
        f"{daemon_url}/api/question/poll?intern_name="
        f"{urllib.parse.quote(intern_name)}"
    )
    while time.time() < deadline:
        time.sleep(POLL_INTERVAL_SEC)
        poll = _get_json(poll_url)
        status = poll.get("status")
        if status == "none":
            sys.exit(
                "pending question vanished before answer; "
                "did the daemon restart or was the question cancelled?"
            )
        if status != "answered":
            continue

        answer_text = _extract_answer_text(poll.get("answers", {}))
        m = ANSWER_RE.search(answer_text)
        if not m:
            sys.exit(
                f"could not extract code from answer: {answer_text!r}\n"
                "expected format: FEISHU_OAUTH code=<code> state=<state>"
            )
        code = m.group(1)
        returned_state = m.group(2) or ""
        if returned_state and returned_state != state:
            sys.exit(
                f"state mismatch — possible CSRF or stale paste. "
                f"expected {state!r}, got {returned_state!r}"
            )
        token_resp = _exchange_code(app_id, app_secret, code, redirect_uri)
        _save_token(token_resp)
        print(f"Token saved to {TOKEN_FILE}")
        print(f"  access expires in {token_resp['expires_in']}s")
        if token_resp.get("refresh_token_expires_in"):
            print(f"  refresh expires in {token_resp['refresh_token_expires_in']}s")
        return

    sys.exit(f"auth timed out after {POLL_TIMEOUT_SEC}s without receiving code")


def cmd_status():
    token = _load_token()
    now = datetime.now(timezone.utc)
    expires = datetime.fromisoformat(token["expires_at"])
    print(f"token file: {TOKEN_FILE}")
    print(
        f"access expires: {expires.isoformat()} "
        f"({(expires - now).total_seconds():.0f}s left)"
    )
    if token.get("refresh_expires_at"):
        refresh_exp = datetime.fromisoformat(token["refresh_expires_at"])
        print(
            f"refresh expires: {refresh_exp.isoformat()} "
            f"({(refresh_exp - now).total_seconds():.0f}s left)"
        )
    print(f"scope: {token.get('scope', '')}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_login = sub.add_parser("login", help="trigger OAuth via daemon card + Feishu paste")
    p_login.add_argument("--intern", required=True, help="intern name (for daemon card routing)")
    sub.add_parser("status", help="show current token expiry")
    args = parser.parse_args()
    if args.cmd == "login":
        cmd_login(args.intern)
    elif args.cmd == "status":
        cmd_status()


if __name__ == "__main__":
    main()
