#!/usr/bin/env python3
"""get_wiki_node — 把 Wiki URL 的 node_token 映射到实际 obj_token（wiki v2）

用法:
  python3 get_wiki_node.py --node <node_token>
  python3 get_wiki_node.py --url "https://acnn.feishu.cn/wiki/HBNvw4nDJi5GoakUNfOcnjVrnqh"

背景:
  飞书 Wiki URL 形如 /wiki/<node_token>，node_token 不能直接当 docx document_id。
  本脚本调 /wiki/v2/spaces/get_node 映射出实际的 obj_token（docx 的 document_id）。
  之后可用 obj_token 走 get_doc.py / append_block.py 等 docx 脚本读写内容。

输出:
  space_id=<sid>
  node_token=<ntoken>
  obj_type=docx|sheet|mindnote|bitable|file|slides
  obj_token=<oid>    ← 这是 docx document_id，喂给已有 docx 脚本
  title=<title>

需要 scope: wiki:wiki，先跑 auth.py login。
"""

import argparse
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

from auth import get_access_token

ENDPOINT = "https://open.feishu.cn/open-apis/wiki/v2/spaces/get_node"

URL_RE = re.compile(r"/wiki/([A-Za-z0-9]+)")


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--node", help="node_token")
    g.add_argument("--url", help="full Wiki URL, will extract node_token from /wiki/<token>")
    args = p.parse_args()

    if args.url:
        m = URL_RE.search(args.url)
        if not m:
            sys.exit(f"could not extract /wiki/<token> from URL: {args.url}")
        node_token = m.group(1)
    else:
        node_token = args.node

    token = get_access_token()
    qs = urllib.parse.urlencode({"token": node_token, "obj_type": "wiki"})
    url = f"{ENDPOINT}?{qs}"
    req = urllib.request.Request(
        url, headers={"Authorization": f"Bearer {token}"}, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        sys.exit(f"feishu HTTP {e.code}: {e.read().decode()}")

    if data.get("code") != 0:
        sys.exit(f"feishu error: {json.dumps(data, ensure_ascii=False)}")

    node = data["data"]["node"]
    print(f"space_id={node.get('space_id', '')}")
    print(f"node_token={node.get('node_token', '')}")
    print(f"obj_type={node.get('obj_type', '')}")
    print(f"obj_token={node.get('obj_token', '')}")
    print(f"title={node.get('title', '')}")


if __name__ == "__main__":
    main()
