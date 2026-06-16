#!/usr/bin/env python3
"""insert_block — 在飞书文档指定 parent 的指定 index 位置插入新块（docx v1）

用法:
  # 单个纯文本块（最常见场景：在某 bullet 后插入一行）
  python3 insert_block.py --doc <document_id> --parent <parent_id> --index 40 --text "- 支持群附件/图片发送 — ..."

  # 复杂 block 数组（heading / 多 run 样式 / mention_doc / link 等）
  python3 insert_block.py --doc <document_id> --parent <parent_id> --index 77 --children-json path/to/children.json

与 append_block.py 的区别：
  - append_block 只能追加到 parent 末尾
  - insert_block 支持任意 index 插入（0-based，原位置及之后的 block 往后挤）

children-json 结构：JSON 数组，每项是完整 block 对象，例如：
  [
    {"block_type": 5, "heading3": {"elements": [{"text_run": {"content": "7. 新段落"}}], "style": {}}},
    {"block_type": 2, "text": {"elements": [
       {"text_run": {"content": "请参考 "}},
       {"mention_doc": {"obj_type": 16, "token": "<wiki_node_token>"}},
       {"text_run": {"content": " 了解详情"}}
    ], "style": {}}}
  ]

block_type 对照：1=page, 2=text, 3=heading1, 4=heading2, 5=heading3, 14=code, 24=divider,
                 27=image, 31=table, 32=table_cell, 34=quote。

先跑 get_doc.py --format blocks 拿 parent 的 block_id 和它当前 children 列表，再定位
目标 index（parent 的 children 数组里插入到第几个位置）。文档根节点的 parent = document_id。

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


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--doc", required=True, help="document_id")
    p.add_argument("--parent", required=True, help="parent block_id (use document_id for root)")
    p.add_argument("--index", type=int, required=True, help="0-based position in parent.children")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--text", help="shortcut: insert a single text block with this content")
    g.add_argument("--children-json", dest="children_json", help="path to JSON array of full block objects")
    args = p.parse_args()

    if args.children_json:
        with open(args.children_json, "r", encoding="utf-8") as f:
            children = json.load(f)
        if not isinstance(children, list) or not children:
            sys.exit(f"--children-json: expected non-empty JSON array, got {type(children).__name__}")
    else:
        children = [{
            "block_type": 2,
            "text": {
                "elements": [{"text_run": {"content": args.text}}],
                "style": {},
            },
        }]

    token = get_access_token()
    url = (
        f"{BASE}/{urllib.parse.quote(args.doc)}"
        f"/blocks/{urllib.parse.quote(args.parent)}/children"
    )
    body = {"children": children, "index": args.index}

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

    inserted = data["data"].get("children", [])
    if not inserted:
        sys.exit(f"feishu returned empty children: {json.dumps(data, ensure_ascii=False)}")
    for blk in inserted:
        print(f"block_id={blk.get('block_id')} type={blk.get('block_type')}")


if __name__ == "__main__":
    main()
