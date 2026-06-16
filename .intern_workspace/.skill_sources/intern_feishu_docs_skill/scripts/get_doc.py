#!/usr/bin/env python3
"""get_doc — 读取飞书云文档内容（docx v1）

用法:
  python3 get_doc.py --doc <document_id> [--format text|blocks]

format:
  text   - 纯文本 raw_content（默认）
  blocks - 块树 JSON（用于做精细编辑前的结构探查）

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


def _get(path, token):
    req = urllib.request.Request(
        f"{BASE}{path}",
        headers={"Authorization": f"Bearer {token}"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        sys.exit(f"feishu HTTP {e.code}: {e.read().decode()}")


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--doc", required=True, help="document_id")
    p.add_argument("--format", choices=["text", "blocks"], default="text")
    args = p.parse_args()

    token = get_access_token()

    if args.format == "text":
        data = _get(f"/{urllib.parse.quote(args.doc)}/raw_content", token)
        if data.get("code") != 0:
            sys.exit(f"feishu error: {json.dumps(data, ensure_ascii=False)}")
        print(data["data"]["content"])
    else:
        # Paginate through blocks (飞书 blocks endpoint default page_size=500)
        path = f"/{urllib.parse.quote(args.doc)}/blocks"
        all_blocks = []
        page_token = None
        while True:
            query = f"{path}?page_size=500"
            if page_token:
                query += f"&page_token={urllib.parse.quote(page_token)}"
            data = _get(query, token)
            if data.get("code") != 0:
                sys.exit(f"feishu error: {json.dumps(data, ensure_ascii=False)}")
            payload = data["data"]
            all_blocks.extend(payload.get("items", []))
            if not payload.get("has_more"):
                break
            page_token = payload.get("page_token")
            if not page_token:
                break
        print(json.dumps(all_blocks, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
