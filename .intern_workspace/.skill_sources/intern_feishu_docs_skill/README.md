# intern_feishu_docs_skill — 人类使用参考

创建和修改飞书云文档（docx）、电子表格（sheets），以及 Wiki 节点的 skill。纯 Python stdlib，脚本调飞书开放平台 REST。

## 一次性配置

### 1. 凭据

`<WORK_AGENTS_ROOT>/key.txt`：第 1 行 `app_id`（`cli_*`），第 2 行 `app_secret`。`WORK_AGENTS_ROOT` 取 env（VS Code 插件 / hooks 自动 export），或由 `scripts/root.py` 从 CWD 向上递归找含 `key.txt + .feishu_registry/` 的目录（同兄弟 `intern_feishu_messaging_skill`）。

### 2. redirect_uri 托管页

飞书 OAuth 授权码流要求 redirect_uri 是一个**公网 HTTPS 页**用来 echo `code`。本 skill 提供 `echo.html` 做这件事。

推荐部署方式：**GitHub Pages**（免费、国内手机 4G/5G 通常可达、返回正确 `text/html`）。

1. 建 public repo（比如 `chlxydl/echo_intern`）
2. 把 `echo.html` push 到 `main` 分支
3. repo Settings → Pages → Source: Deploy from a branch → Branch: `main` / `/ (root)` → Save
4. 等 1-2 分钟，URL 形如 `https://<user>.github.io/<repo>/echo.html`

### 3. config.json

`config.json` 填第 2 步得到的 URL：

```json
{"redirect_uri": "https://chlxydl.github.io/echo_intern/echo.html"}
```

### 4. 飞书 app 后台

在 [open.feishu.cn](https://open.feishu.cn/) 自建应用的后台：

- **安全设置 → redirect_uri 白名单**：填第 3 步得到的 URL（必须完全一致，不要多/少 `/`）
- **权限管理** 开通**用户身份**的 5 个 scope（逐个申请审批；没审批通过时授权页会报 `code=20027`）：
  - `docx:document`（文档读写，必需）
  - `sheets:spreadsheet`（电子表格读写，必需）
  - `wiki:wiki`（Wiki 空间/节点管理，Wiki 功能需要）
  - `drive:file`（云空间 folder 指定 / 附件上传，`create_doc --folder` 需要）
  - `offline_access`（颁发 `refresh_token`，没开的话 access 2h 过期必须重跑 `auth.py login`）

## 一次性鉴权

```bash
python3 scripts/auth.py login --intern <intern_name>
```

流程：
1. 脚本调本机 daemon HTTP，发卡到你的飞书群：**「飞书 OAuth 授权」** 卡片带「打开飞书授权页」 url_button
2. 你在**飞书手机客户端**点按钮 → 浏览器打开飞书授权页 → 同意
3. 授权后 302 到 `echo.html?code=...&state=...`，页面大字显示 code + 一键复制按钮
4. 点复制 → 回飞书群粘贴 `FEISHU_OAUTH code=... state=...`（直接粘贴发送即可）
5. 脚本每 3 秒轮询一次，拿到 code → 换 token → 存 `~/.feishu_skill_token.json`（权限 `0600`）

查看当前 token 状态：
```bash
python3 scripts/auth.py status
```

Token 文件样例：
```json
{
  "access_token": "u-xxx",
  "refresh_token": "ur-xxx",
  "expires_at": "2026-05-10T18:00:00Z",
  "refresh_expires_at": "2026-05-17T10:00:00Z",
  "scope": "docx:document sheets:spreadsheet drive:file offline_access wiki:wiki auth:user.id:read"
}
```

`access_token` 2 小时、`refresh_token` **7 天**有效（飞书 v2 `/oauth/token` 实测 `refresh_token_expires_in=604800s`；部分文档写 30 天但实际返回是 7d，以飞书响应为准）。其他脚本 `from auth import get_access_token` 时，过期前 5 分钟自动 refresh；每次 refresh 会同时颁发新的 2h access + 7d refresh，所以只要 7 天内任何一次调用就永不过期。连续 7 天不用再跑一次 `auth.py login`。

## 文档操作

```bash
python3 scripts/create_doc.py --title "2026-05-10 训练结果" [--folder <folder_token>]
python3 scripts/get_doc.py --doc <doc_token> [--format text|blocks]
python3 scripts/append_block.py --doc <doc_token> --text "要追加的段落" [--parent <block_id>]
python3 scripts/insert_block.py --doc <doc_token> --parent <parent_id> --index N --text "要插入的段落"
python3 scripts/insert_block.py --doc <doc_token> --parent <parent_id> --index N --children-json children.json
python3 scripts/replace_block.py --doc <doc_token> --block <block_id> --text "新内容"
python3 scripts/replace_block.py --doc <doc_token> --block <block_id> --elements-json elements.json
```

- `append_block` 默认在文档末尾追加（parent=根节点）；传 `--parent <block_id>` 可挂到指定块下
- `insert_block` 支持任意 index 定点插入（0-based，原位置及之后的 block 向后挤）——append_block 不能指定位置时用它。`--children-json` 支持一次插入多块（例如一个新段落：heading + 介绍 + bullets），数组每项是完整 block 对象，block_type 对照：1=page, 2=text, 3=heading1, 4=heading2, 5=heading3, 14=code, 24=divider, 27=image, 31=table, 32=table_cell, 34=quote
- `replace_block --text`：单段 text_run，原多 run/多样式会被压成纯文本
- `replace_block --elements-json <file>`：文件是 JSON 数组，保留多 run 结构和每段样式（bold/italic/underline/strikethrough/inline_code），也支持 `mention_doc`（内嵌子文档链接）与 `text_run.link`（URL 超链接），格式举例：
  ```json
  [
    {"text_run": {"content": "- "}},
    {"text_run": {"content": "17 台", "text_element_style": {"bold": true}}},
    {"text_run": {"content": " 开发机同时运行"}},
    {"mention_doc": {"obj_type": 16, "token": "<wiki_node_token>"}},
    {"text_run": {"content": "见 ", "text_element_style": {"link": {"url": "https%3A%2F%2Fexample.com"}}}}
  ]
  ```
  link.url 需 URL-encoded；mention_doc 的 `obj_type` 传 16（wiki node）或 22（docx），飞书服务端会自动补齐 title/url
- 先跑 `get_doc.py --format blocks` 输出块树 JSON 拿每块的 `block_id`（**固定 27 字符**，别被 pretty-print 截短）再做 replace / insert

## 表格结构编辑

```bash
python3 scripts/update_table.py --doc <doc_token> --block <table_block_id> insert-column --column-index N
python3 scripts/update_table.py --doc <doc_token> --block <table_block_id> insert-rows   --row-index N [--row-size 1]
python3 scripts/update_table.py --doc <doc_token> --block <table_block_id> delete-columns --start A --end B
python3 scripts/update_table.py --doc <doc_token> --block <table_block_id> merge-cells --row-start R --col-start C --row-size RS --col-size CS
```

- table 是组合块：table block（block_type=31）→ cells（block_type=32）→ 内部 text block（block_type=2）
- `insert-column` / `insert-rows` 新建的 cell 自带一个空 text block；**填内容**要再跑一次 `get_doc.py --format blocks` 拿新 cell 下的 inner text block_id，然后 `replace_block.py` 写入
- `delete-columns --end` 是 exclusive（删 `[start, end)`）

## 电子表格操作

```bash
python3 scripts/create_sheet.py --title "2026 训练指标"
python3 scripts/read_range.py --sheet <spreadsheet_token> --range "Sheet1!A1:C10"
python3 scripts/write_range.py --sheet <spreadsheet_token> --range "Sheet1!A1:B2" --values '[["a","b"],["c","d"]]'
python3 scripts/append_row.py --sheet <spreadsheet_token> --range "Sheet1!A:D" --values '[["x","y","z","w"]]' [--mode INSERT_ROWS|OVERWRITE]
```

- `--values` 是 JSON 二维数组字符串（外层列表是行，内层列表是列）
- `write_range` 覆盖原有内容；`append_row` 追加到已有数据末尾
- `append_row --mode INSERT_ROWS`（默认）新插入行下推原有数据；`OVERWRITE` 覆盖目标位置

## Wiki 操作（知识库 / "我的文档库"）

```bash
python3 scripts/list_wiki_spaces.py                           # 列可访问 Wiki 空间
python3 scripts/get_wiki_node.py --url <wiki_url>             # wiki URL → docx document_id
python3 scripts/get_wiki_node.py --node <node_token>          # 同上，直接给 node_token
python3 scripts/create_wiki_doc.py --space <space_id> --title "..." [--parent <node_token>]
```

- `get_wiki_node`：把 Wiki URL（`/wiki/<node_token>`）或 node_token 映射到实际 docx `document_id`（返回字段 `obj_token`）；之后用 `get_doc.py` / `append_block.py` 等已有 docx 脚本操作内容
- `create_wiki_doc`：在 Wiki 空间建 docx 节点；建完返回的 `document_id` 直接喂 `append_block.py` 写内容
- **wiki API 只管组织层**（节点树、空间），**内容读写全复用 docx API**——两套协同工作

**典型工作流：读/改某个 Wiki 文档**
```bash
# 1) 用户/主管贴 https://x.feishu.cn/wiki/<node_token>
python3 scripts/get_wiki_node.py --url <URL>       # 拿到 obj_token
# 2) 用 obj_token 当 document_id 读/改
python3 scripts/get_doc.py --doc <obj_token> --format text
python3 scripts/append_block.py --doc <obj_token> --text "..."
```

## 架构说明

```
auth.py login --intern NAME
   │
   │ HTTP POST /api/question/ask (带 url_button option)
   ▼
本机 feishu_daemon ──── send_interactive_card ──── 飞书群
                                                    │
                                                    ▼
                                                 主管手机飞书
                                                    │ ① 点按钮
                                                    ▼
                                             飞书 OAuth 授权页
                                                    │ ② 同意
                                                    ▼
                                          GitHub Pages echo.html
                                                    │ ③ 复制 code
                                                    ▼
                                                 主管回群粘贴
                                                    │
                                                    ▼
feishu_relay ──── 分发到本机 daemon ──── _try_answer_pending_question
                                                    │
                                                    ▼
auth.py 轮询 /api/question/poll 拿到 answer
   │
   │ POST /open-apis/authen/v2/oauth/token
   ▼
~/.feishu_skill_token.json
```

## 常见问题

- **"daemon metadata missing"**：本机 feishu_daemon 没跑，启动插件或 `internctl daemon start`
- **"config not found / redirect_uri missing"**：编辑 `config.json` 填第 2 步 URL
- **"Auth card sent ... timed out"**：10 分钟内没收到粘贴；检查卡片是否到群、授权是否完成
- **"state mismatch"**：粘贴的是旧 auth session 的 code，重跑 `auth.py login --intern <NAME>`
- **"token exchange failed"**：飞书返回错误；检查 app scope / redirect_uri 白名单是否一致
- **"refresh failed; refresh_token likely expired"**：连续 7 天没调用过 skill，跑一次 `auth.py login --intern <NAME>` 重新授权
