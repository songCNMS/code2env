#!/usr/bin/env python3
"""read_range — 读飞书电子表格指定范围的值（sheets v2）

用法:
  python3 read_range.py --sheet <spreadsheet_token> --range "Sheet1!A1:C10"

range 格式:
  <sheet_id>!<cell_range>   例如 "rq6xQs!A1:C10"
  <sheet_name>!<cell_range> 也支持

输出 JSON 数组：[[row1], [row2], ...]。空 cell 会是空字符串或 null。

需要先跑一次 auth.py login。
"""

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request

from auth import get_access_token

BASE = "https://open.feishu.cn/open-apis/sheets/v2/spreadsheets"


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--sheet", required=True, help="spreadsheet_token")
    p.add_argument("--range", dest="cell_range", required=True,
                   help="sheet!A1:C10 notation")
    args = p.parse_args()

    token = get_access_token()
    url = (
        f"{BASE}/{urllib.parse.quote(args.sheet)}"
        f"/values/{urllib.parse.quote(args.cell_range, safe='!')}"
    )

    req = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {token}"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        sys.exit(f"feishu HTTP {e.code}: {e.read().decode()}")

    if data.get("code") != 0:
        sys.exit(f"feishu error: {json.dumps(data, ensure_ascii=False)}")

    value_range = data["data"]["valueRange"]
    values = value_range.get("values", [])
    print(json.dumps(values, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
