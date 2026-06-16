#!/usr/bin/env python3
"""update_table — 对飞书文档中的 table block 做行/列级操作（docx v1）

支持的操作：
  insert-column   在指定列位置插入一列（原列及之后往右挤）
  insert-rows     在指定行位置插入 N 行
  delete-columns  删除连续列 [start, end)
  merge-cells     合并单元格

用法示例:
  # 在 3 列表里加第 4 列（右侧）
  python3 update_table.py --doc <doc> --block <table_block_id> insert-column --column-index 3

  # 在第 2 行之前插入 2 行
  python3 update_table.py --doc <doc> --block <table_block_id> insert-rows --row-index 2 --row-size 2

  # 删除第 3、4 列
  python3 update_table.py --doc <doc> --block <table_block_id> delete-columns --start 3 --end 5

  # 合并 (row=1,col=0) 与 (row=1,col=1)
  python3 update_table.py --doc <doc> --block <table_block_id> merge-cells \\
    --row-start 1 --col-start 0 --row-size 1 --col-size 2

新插入的 cell 自带一个空 text block；要填内容先 get_doc --format blocks 拿新 cell 的 inner
text block_id，再用 replace_block.py 写入。

先跑 get_doc.py --format blocks 拿 table 的 block_id（block_type=31）与当前 column_size /
row_size，避免越界。

需要先跑一次 auth.py login --intern <NAME>。
"""

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request

from auth import get_access_token

BASE = "https://open.feishu.cn/open-apis/docx/v1/documents"


def patch(doc, block, body):
    token = get_access_token()
    url = f"{BASE}/{urllib.parse.quote(doc)}/blocks/{urllib.parse.quote(block)}"
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
    return data["data"].get("block", {})


def cmd_insert_column(args):
    blk = patch(args.doc, args.block, {"insert_table_column": {"column_index": args.column_index}})
    prop = blk.get("table", {}).get("property", {})
    print(f"ok cols={prop.get('column_size')} rows={prop.get('row_size')}")
    print("new cells under children (last column):")
    children = blk.get("children", [])
    cs = prop.get("column_size", 0)
    rs = prop.get("row_size", 0)
    for r in range(rs):
        cell = children[r * cs + args.column_index] if cs and r * cs + args.column_index < len(children) else None
        print(f"  row={r} new_cell_id={cell}")


def cmd_insert_rows(args):
    blk = patch(args.doc, args.block, {
        "insert_table_rows": {"row_index": args.row_index, "row_size": args.row_size},
    })
    prop = blk.get("table", {}).get("property", {})
    print(f"ok cols={prop.get('column_size')} rows={prop.get('row_size')}")


def cmd_delete_columns(args):
    blk = patch(args.doc, args.block, {
        "delete_table_columns": {"column_start_index": args.start, "column_end_index": args.end},
    })
    prop = blk.get("table", {}).get("property", {})
    print(f"ok cols={prop.get('column_size')} rows={prop.get('row_size')}")


def cmd_merge_cells(args):
    blk = patch(args.doc, args.block, {
        "merge_table_cells": {
            "row_start_index": args.row_start,
            "column_start_index": args.col_start,
            "row_size": args.row_size,
            "column_size": args.col_size,
        },
    })
    print(f"ok merged cells in block={blk.get('block_id')}")


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--doc", required=True)
    p.add_argument("--block", required=True, help="table block_id (block_type=31)")
    sub = p.add_subparsers(dest="op", required=True)

    pc = sub.add_parser("insert-column")
    pc.add_argument("--column-index", type=int, required=True, help="0-based insert position")
    pc.set_defaults(func=cmd_insert_column)

    pr = sub.add_parser("insert-rows")
    pr.add_argument("--row-index", type=int, required=True)
    pr.add_argument("--row-size", type=int, default=1)
    pr.set_defaults(func=cmd_insert_rows)

    pd = sub.add_parser("delete-columns")
    pd.add_argument("--start", type=int, required=True)
    pd.add_argument("--end", type=int, required=True, help="exclusive")
    pd.set_defaults(func=cmd_delete_columns)

    pm = sub.add_parser("merge-cells")
    pm.add_argument("--row-start", type=int, required=True)
    pm.add_argument("--col-start", type=int, required=True)
    pm.add_argument("--row-size", type=int, required=True)
    pm.add_argument("--col-size", type=int, required=True)
    pm.set_defaults(func=cmd_merge_cells)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
