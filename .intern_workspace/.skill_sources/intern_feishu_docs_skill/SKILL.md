---
name: feishu-docs
description: "Create / read / edit Feishu (Lark) cloud docs (docx), spreadsheets, and Wiki nodes via local CLI. Trigger when user asks to 新建/改飞书文档, 在用户手册追加/更新, 把数据写到飞书表格, 更新飞书文档 <link>, read / summarize a shared Feishu doc or wiki — including probes like '能不能读到这个飞书链接'. URL RULE (hard): ANY URL on *.feishu.cn / *.larksuite.com / *.feishu-pre.com (paths /wiki /docx /docs /sheets /base) MUST go through this skill (get_wiki_node.py → get_doc.py / read_range.py). NEVER WebFetch those hosts — Feishu requires user OAuth; WebFetch only sees the login wall. Do NOT trigger for: Feishu URLs mentioned purely as a pointer, '飞书里怎么做 X' usage questions, sending image/file into a chat (use sibling intern_feishu_messaging_skill), editing local Markdown. CALL CONTRACT for scripts/auth.py login ONLY: pass --intern <NAME> from the UserPromptSubmit line '你是 intern_X，在项目 Y 中工作' verbatim; wrong name sends auth card to wrong group. Other scripts address Feishu objects by token, NOT --intern. See SKILL.md for full contract."
---

# intern_feishu_docs_skill

创建和修改飞书云文档（docx）、电子表格（sheets），以及 Wiki 节点。纯 CLI，脚本调飞书开放平台 REST API；唯一会"路由到某个群"的命令是 `auth.py login`，其余脚本按对象 token 直接寻址。

## Call contract (IMPORTANT — only for `auth.py login`)

`python3 scripts/auth.py login --intern <NAME>` sends an OAuth authorization card to the intern's supervisor Feishu group. The card is routed by `feishu_daemon → feishu_relay → supervisor group` using the `<NAME>` you pass.

**You MUST pass the intern name explicitly on every `auth.py login` call:**

```
python3 scripts/auth.py login --intern <NAME>
```

The value of `<NAME>` is in this turn's UserPromptSubmit additionalContext, on the "你是 intern_X，在项目 Y 中工作" (English equivalent: "you are intern_X, working on project Y") line. **Read it from there verbatim.**

Do NOT derive the intern name from:

- the current working directory
- environment variables
- file path components (`/work-agents/intern_paper_reading/…` is a *project repo* path for that project, not an intern)
- the name of the folder Claude Code is running in

Passing the wrong name silently sends the authorization card to another deployment's supervisor group — the wrong supervisor gets asked to authorize, and you never receive the token.

**Every other script in this skill (`create_doc` / `get_doc` / `append_block` / `replace_block` / `create_sheet` / `read_range` / `write_range` / `append_row` / `list_wiki_spaces` / `get_wiki_node` / `create_wiki_doc`) does NOT take `--intern`.** Its destination is a specific Feishu object identified by its token. No message is sent into any chat; no routing decision is made.

## URL 识别铁律（IMPORTANT）

**看到飞书 URL → 走本 skill 的脚本，绝不 `WebFetch`。** 飞书云文档内容需要 `user_access_token`（OAuth 用户身份），`WebFetch` 无鉴权，只能拿到登录墙 HTML，白费一个 turn。

| URL 形态 | 正确入口 |
|----------|---------|
| `https://<x>.feishu.cn/wiki/<node_token>` | `get_wiki_node.py --url <URL>` → 拿 `obj_token` → `get_doc.py --doc <obj_token>` |
| `https://<x>.feishu.cn/docx/<doc_token>` 或 `/docs/<doc_token>` | `get_doc.py --doc <doc_token>` |
| `https://<x>.feishu.cn/sheets/<spreadsheet_token>` | `read_range.py --sheet <spreadsheet_token> --range "Sheet1!A1:Z100"` |
| `https://<x>.feishu.cn/base/<bitable_token>` | 暂不支持（bitable 未覆盖），告诉主管 |

涵盖域名：`*.feishu.cn`、`*.larksuite.com`、`*.feishu-pre.com`（预发）。

**"能不能读到 / 看看里面是什么 / 先打开这个链接" 这类能力探测表达也按"让你读"处理**，直接触发本 skill——不要先用 `WebFetch` 试一下"看能不能读"，那只会验证"登录墙存在"这个无意义结论。

## 何时调用

- "帮我建一篇飞书文档记录今天训练结果"
- "把这批数据写到飞书表格 X"
- "在用户手册的 xx 章节追加一段"
- "更新飞书文档 <link> 把旧版本改为新版"
- "读一下这个 wiki 页总结关键信息"
- "生成一个飞书文档 outline"
- **能力探测型**："你先看看能不能读到 `<feishu-url>` 的内容"、"试试能否打开这个 wiki"、"先看看里面是什么"——主管是想让你去读，不是想让你评估可行性

## 不该调用

- 用户只是**贴飞书文档链接作引用**（出现在 PR 描述、commit message、讨论材料里），**并没让你读或改**（分清"请读/请改"和"背景材料"）
- 用户问**飞书里怎么做 X** 这类使用问题（教学场景，不是执行）
- 用户想**把图片 / 文件发到飞书群** → 走 sibling skill `intern_feishu_messaging_skill`
- 用户只是让你改本地 Markdown 文件

> ⚠️ 判断"引用 vs 让你读"时**宁可触发 skill**：读一次的 cost 很低（一次 API 调用），漏触发的 cost 是走 `WebFetch` 撞登录墙再重来一轮。

## 鉴权前提

飞书文档修改需要 **user_access_token（用户身份）**，不是 app_access_token。首次使用前主管必须先跑一次（严格遵守上文 Call contract 的 `--intern` 契约）：

```bash
python3 scripts/auth.py login --intern <NAME>
```

完成 OAuth 授权后，token 缓存到 `~/.feishu_skill_token.json`（权限 `0600`），后续脚本 `from auth import get_access_token` 时过期前 5 分钟自动 refresh。

凭据来源：`<WORK_AGENTS_ROOT>/key.txt` 第 1 行 `app_id`、第 2 行 `app_secret`。`WORK_AGENTS_ROOT` 取自 env（VS Code 插件/hooks 自动 export），或由 `scripts/root.py` 从 CWD 向上递归查找（同时含 `key.txt` 与 `.feishu_registry/` 的目录）。

Token 缺失或 refresh_token 失效时脚本会 `sys.exit` 并提示用户重新跑 `auth.py login`，不做静默 fallback。

## 核心脚本

| 脚本 | 用途 |
|------|------|
| `scripts/auth.py login --intern <NAME>` | 一次性 OAuth 授权拿 user_access_token（唯一路由到群的命令） |
| `scripts/auth.py status` | 查看当前 token 是否有效、过期时间 |
| `scripts/create_doc.py` | 新建飞书 docx 文档 |
| `scripts/get_doc.py` | 读文档纯文本（`--format text`）或块树 JSON（`--format blocks`） |
| `scripts/append_block.py` | 向文档追加文本块（默认文档末尾，可挂到指定 parent） |
| `scripts/replace_block.py` | 替换指定块的 text 内容（`--text` 单 run / `--elements-json` 保多样式） |
| `scripts/create_sheet.py` | 新建电子表格 |
| `scripts/read_range.py` | 读取 sheet 单元格范围 |
| `scripts/write_range.py` | 覆盖写入 sheet 单元格范围 |
| `scripts/append_row.py` | 追加行（`INSERT_ROWS` 下推 / `OVERWRITE` 覆盖） |
| `scripts/list_wiki_spaces.py` | 列可访问的 Wiki 空间 |
| `scripts/get_wiki_node.py` | Wiki URL / node_token → 实际 docx `document_id` |
| `scripts/create_wiki_doc.py` | 在 Wiki 空间下建 docx 节点，返回 `document_id` 可直接复用 docx 脚本 |

详细命令与示例见 `README.md`。Wiki 与 docx 的边界：**Wiki API 只管空间/节点树组织层，内容读写全部复用 docx API**——拿到 `obj_token` 之后用已有 docx 脚本编辑即可。

## 错误处理

- 禁止"鉴权失败当未鉴权继续"之类的 fallback——让错误抛出
- `refresh_token` 失效 → 提示 "refresh_token 过期，请重新运行 auth.py login --intern <NAME>"
- 飞书 API 返回非 `code=0` → 打印 `{code, msg}` 原文后 `sys.exit`
