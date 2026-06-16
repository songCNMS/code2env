#!/usr/bin/env python3
"""list_wiki_spaces — 列出当前用户可访问的飞书 Wiki 空间（wiki v2）

用法:
  python3 list_wiki_spaces.py [--page-size 20]

输出每个 space 的 space_id + name（建 wiki 文档时需要 space_id）。

需要 scope: wiki:wiki，先跑 auth.py login。
"""

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request

from auth import get_access_token

BASE = "https://open.feishu.cn/open-apis/wiki/v2/spaces"


def _get(url, token):
    req = urllib.request.Request(
        url, headers={"Authorization": f"Bearer {token}"}, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        sys.exit(f"feishu HTTP {e.code}: {e.read().decode()}")


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--page-size", type=int, default=20)
    args = p.parse_args()

    token = get_access_token()
    page_token = None
    total = 0
    while True:
        qs = {"page_size": args.page_size}
        if page_token:
            qs["page_token"] = page_token
        url = f"{BASE}?{urllib.parse.urlencode(qs)}"
        data = _get(url, token)
        if data.get("code") != 0:
            sys.exit(f"feishu error: {json.dumps(data, ensure_ascii=False)}")
        payload = data["data"]
        for sp in payload.get("items", []):
            total += 1
            print(f"space_id={sp.get('space_id')}\tname={sp.get('name', '')}")
        if not payload.get("has_more"):
            break
        page_token = payload.get("page_token")
        if not page_token:
            break
    if total == 0:
        print("(no spaces accessible)", file=sys.stderr)


if __name__ == "__main__":
    main()
