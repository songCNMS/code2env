#!/usr/bin/env python3
"""create_doc — 新建飞书云文档（docx v1）

用法:
  python3 create_doc.py --title "训练结果" [--folder <folder_token>]

输出:
  document_id=<id>
  url=https://feishu.cn/docx/<id>

需要先跑一次 auth.py login。
"""

import argparse
import json
import sys
import urllib.error
import urllib.request

from auth import get_access_token

ENDPOINT = "https://open.feishu.cn/open-apis/docx/v1/documents"


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--title", required=True)
    p.add_argument("--folder", default=None, help="folder_token (optional; default root)")
    args = p.parse_args()

    token = get_access_token()
    body = {"title": args.title}
    if args.folder:
        body["folder_token"] = args.folder

    req = urllib.request.Request(
        ENDPOINT,
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

    doc = data["data"]["document"]
    doc_id = doc["document_id"]
    print(f"document_id={doc_id}")
    print(f"title={doc.get('title', args.title)}")
    print(f"url=https://feishu.cn/docx/{doc_id}")


if __name__ == "__main__":
    main()
