#!/usr/bin/env python3
"""create_wiki_doc — 在指定 Wiki 空间建 docx 节点（wiki v2 + docx v1）

用法:
  python3 create_wiki_doc.py --space <space_id> --title "..." [--parent <node_token>]

流程:
  1. POST /wiki/v2/spaces/{space_id}/nodes body={obj_type:docx, node_type:origin, title}
     飞书会自动建一篇新 docx 并挂到 wiki 空间根节点（或 --parent 指定的节点下）
  2. 返回 node.obj_token 就是 docx 的 document_id
  3. 之后可直接用 append_block.py / get_doc.py 等已有脚本操作内容

输出:
  space_id=<sid>
  node_token=<ntoken>
  document_id=<obj_token>    ← 即 docx document_id
  title=<title>
  url=https://feishu.cn/wiki/<ntoken>

需要 scope: wiki:wiki (+ docx:document 内容编辑)，先跑 auth.py login。
"""

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request

from auth import get_access_token

BASE = "https://open.feishu.cn/open-apis/wiki/v2/spaces"


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--space", required=True, help="space_id (list_wiki_spaces.py 可拿)")
    p.add_argument("--title", required=True)
    p.add_argument("--parent", default=None,
                   help="parent node_token (default: space root)")
    args = p.parse_args()

    token = get_access_token()
    url = f"{BASE}/{urllib.parse.quote(args.space)}/nodes"

    body = {
        "obj_type": "docx",
        "node_type": "origin",
        "title": args.title,
    }
    if args.parent:
        body["parent_node_token"] = args.parent

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

    node = data["data"]["node"]
    print(f"space_id={node.get('space_id', args.space)}")
    print(f"node_token={node.get('node_token', '')}")
    print(f"document_id={node.get('obj_token', '')}")
    print(f"title={node.get('title', args.title)}")
    print(f"url=https://feishu.cn/wiki/{node.get('node_token', '')}")


if __name__ == "__main__":
    main()
