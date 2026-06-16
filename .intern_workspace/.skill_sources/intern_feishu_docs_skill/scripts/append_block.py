#!/usr/bin/env python3
"""append_block — 在飞书文档末尾追加文本块（docx v1）

用法:
  python3 append_block.py --doc <document_id> --text "..."
  python3 append_block.py --doc <document_id> --parent <block_id> --text "..."

parent 默认 = document_id（根节点，追加到文档末尾）；传 --parent 可挂到
具体块（如 heading 下方）。先跑 get_doc.py --format blocks 看 block_id。

输出:
  block_id=<新块 id>  (每个 child 一行)

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
    p.add_argument("--text", required=True, help="text content of the new paragraph")
    p.add_argument("--parent", default=None, help="parent block_id (default: document root)")
    args = p.parse_args()

    token = get_access_token()
    parent = args.parent or args.doc
    url = (
        f"{BASE}/{urllib.parse.quote(args.doc)}"
        f"/blocks/{urllib.parse.quote(parent)}/children"
    )

    body = {
        "children": [{
            "block_type": 2,
            "text": {
                "elements": [{"text_run": {"content": args.text}}],
                "style": {},
            },
        }],
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        sys.exit(f"feishu HTTP {e.code}: {e.read().decode()}")

    if data.get("code") != 0:
        sys.exit(f"feishu error: {json.dumps(data, ensure_ascii=False)}")

    children = data["data"].get("children", [])
    if not children:
        sys.exit(f"feishu returned empty children: {json.dumps(data, ensure_ascii=False)}")
    for blk in children:
        print(f"block_id={blk.get('block_id')}")


if __name__ == "__main__":
    main()
