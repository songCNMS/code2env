#!/usr/bin/env python3
"""write_range — 写飞书电子表格指定范围（覆盖）的值（sheets v2）

用法:
  python3 write_range.py --sheet <spreadsheet_token> \
      --range "Sheet1!A1:B2" \
      --values '[["a","b"],["c","d"]]'

values 是 JSON 二维数组字符串（外层 list 是行，内层 list 是列）。
会**覆盖** range 目标范围的原有内容；保持 values 的行×列与 range 尺寸一致最稳。

需要先跑一次 auth.py login。
"""

import argparse
import json
import sys
import urllib.error
import urllib.request

from auth import get_access_token

BASE = "https://open.feishu.cn/open-apis/sheets/v2/spreadsheets"


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--sheet", required=True, help="spreadsheet_token")
    p.add_argument("--range", dest="cell_range", required=True,
                   help="sheet!A1:B2 notation")
    p.add_argument("--values", required=True,
                   help='JSON 2D array string, e.g. \'[["a","b"],["c","d"]]\'')
    args = p.parse_args()

    try:
        values = json.loads(args.values)
    except json.JSONDecodeError as e:
        sys.exit(f"--values is not valid JSON: {e}")
    if not isinstance(values, list) or (values and not isinstance(values[0], list)):
        sys.exit("--values must be a 2D JSON array (list of lists)")

    token = get_access_token()
    url = f"{BASE}/{args.sheet}/values"

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
        method="PUT",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        sys.exit(f"feishu HTTP {e.code}: {e.read().decode()}")

    if data.get("code") != 0:
        sys.exit(f"feishu error: {json.dumps(data, ensure_ascii=False)}")

    d = data.get("data", {})
    print(f"updated_range={d.get('updatedRange', '')}")
    print(f"updated_rows={d.get('updatedRows', 0)}")
    print(f"updated_columns={d.get('updatedColumns', 0)}")
    print(f"updated_cells={d.get('updatedCells', 0)}")


if __name__ == "__main__":
    main()
