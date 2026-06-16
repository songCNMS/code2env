#!/usr/bin/env python3
"""create_sheet — 新建飞书电子表格（sheets v3）

用法:
  python3 create_sheet.py --title "实验数据" [--folder <folder_token>]

输出:
  spreadsheet_token=<token>
  url=https://feishu.cn/sheets/<token>

需要先跑一次 auth.py login。
"""

import argparse
import json
import sys
import urllib.error
import urllib.request

from auth import get_access_token

ENDPOINT = "https://open.feishu.cn/open-apis/sheets/v3/spreadsheets"


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

    sheet = data["data"]["spreadsheet"]
    sp_token = sheet["spreadsheet_token"]
    print(f"spreadsheet_token={sp_token}")
    print(f"title={sheet.get('title', args.title)}")
    print(f"url=https://feishu.cn/sheets/{sp_token}")


if __name__ == "__main__":
    main()
