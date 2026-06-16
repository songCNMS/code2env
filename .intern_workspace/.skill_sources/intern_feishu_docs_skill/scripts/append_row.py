#!/usr/bin/env python3
"""append_row — 在飞书电子表格尾部追加行（sheets v2）

用法:
  python3 append_row.py --sheet <spreadsheet_token> \
      --range "Sheet1!A:D" \
      --values '[["step1","done","0.92","2026-05-10"]]'

飞书 append 语义：在 range 范围的**已有数据末尾**追加新行（不是覆盖）。
range 通常写成列范围如 "Sheet1!A:D" 让飞书自动找最后一行；也可精确写 "Sheet1!A5:D5"。

insertDataOption=INSERT_ROWS：如果紧挨着的下一行非空，会插入新行把现有数据下推；
OVERWRITE：覆盖现有数据。默认 INSERT_ROWS。

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
                   help="e.g. Sheet1!A:D or Sheet1!A5:D5")
    p.add_argument("--values", required=True,
                   help='JSON 2D array string, e.g. \'[["a","b","c","d"]]\'')
    p.add_argument("--mode", choices=["INSERT_ROWS", "OVERWRITE"],
                   default="INSERT_ROWS",
                   help="insertDataOption: INSERT_ROWS (default) or OVERWRITE")
    args = p.parse_args()

    try:
        values = json.loads(args.values)
    except json.JSONDecodeError as e:
        sys.exit(f"--values is not valid JSON: {e}")
    if not isinstance(values, list) or (values and not isinstance(values[0], list)):
        sys.exit("--values must be a 2D JSON array (list of lists)")

    token = get_access_token()
    qs = urllib.parse.urlencode({"insertDataOption": args.mode})
    url = f"{BASE}/{args.sheet}/values_append?{qs}"

    body = {
        "valueRange": {
            "range": args.cell_range,
            "values": values,
        }
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

    d = data.get("data", {})
    print(f"updated_range={d.get('tableRange', d.get('updates', {}).get('updatedRange', ''))}")
    upd = d.get("updates", {})
    print(f"updated_rows={upd.get('updatedRows', d.get('updatedRows', 0))}")
    print(f"updated_cells={upd.get('updatedCells', d.get('updatedCells', 0))}")


if __name__ == "__main__":
    main()
