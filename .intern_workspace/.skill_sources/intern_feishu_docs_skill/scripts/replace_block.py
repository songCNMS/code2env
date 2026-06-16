#!/usr/bin/env python3
"""replace_block — 替换飞书文档中指定块的文本内容（docx v1）

用法:
  python3 replace_block.py --doc <document_id> --block <block_id> --text "..."
  python3 replace_block.py --doc <document_id> --block <block_id> --elements-json path/to/elements.json

只改文本 run；不改 block_type。先跑 get_doc.py --format blocks 拿 block_id。

--text 简单替换为单个 text_run（丢失原有多 run 的分段/样式，只剩纯文本）。
--elements-json 传文件路径；文件内容是 JSON 数组，形如:
  [
    {"text_run": {"content": "- "}},
    {"text_run": {"content": "17 台", "text_element_style": {"bold": true}}},
    {"text_run": {"content": " 开发机同时运行"}}
  ]
保留多 run 结构和每段样式（bold/italic/underline/strikethrough/inline_code 等）。

需要先跑一次 auth.py login。
"""

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request

from auth import get_access_token

BASE = "https://open.feishu.cn/open-apis/docx/v1/documents"


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--doc", required=True, help="document_id")
    p.add_argument("--block", required=True, help="block_id to update")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--text", help="new text content (single plain text_run)")
    g.add_argument(
        "--elements-json",
        dest="elements_json",
        help="path to JSON file containing text_run elements array (preserves multi-run styles)",
    )
    args = p.parse_args()

    if args.elements_json:
        with open(args.elements_json, "r", encoding="utf-8") as f:
            elements = json.load(f)
        if not isinstance(elements, list) or not elements:
            sys.exit(f"--elements-json: expected non-empty JSON array, got {type(elements).__name__}")
    else:
        elements = [{"text_run": {"content": args.text}}]

    token = get_access_token()
    url = (
        f"{BASE}/{urllib.parse.quote(args.doc)}"
        f"/blocks/{urllib.parse.quote(args.block)}"
    )

    body = {"update_text_elements": {"elements": elements}}

    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
        },
        method="PATCH",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        sys.exit(f"feishu HTTP {e.code}: {e.read().decode()}")

    if data.get("code") != 0:
        sys.exit(f"feishu error: {json.dumps(data, ensure_ascii=False)}")

    blk = data["data"].get("block", {})
    print(f"block_id={blk.get('block_id', args.block)}")
    print(f"revision_id={blk.get('revision_id', '')}")


if __name__ == "__main__":
    main()
