---
name: codegraph-setup
description: 当项目初始化入口按已启用的扩展准备本仓代码索引时使用。检查 CodeGraph、初始化索引并配置 Cursor 项目查询。普通代码编辑、只读查询不触发该初始化。
---

# 准备本仓 CodeGraph

1. 核对当前目录是获准的 Git 仓库根。对本技能的 CodeGraph 命令设置 `DO_NOT_TRACK=1`。检查 `codegraph --version`、`codegraph status --json` 和项目配置。预览索引、Cursor 项目配置、忽略规则和项目规则的变化。调用方已取得这些项目级写入的同版确认时直接执行。CLI 缺失时交回缺口，局限在当前项目。
2. 确保根 `.gitignore` 含 `/.codegraph/`，保留已有条目。索引未初始化时在仓库根执行 `DO_NOT_TRACK=1 codegraph init --yes`。已初始化时复用，若状态显示源码变更待同步则执行 `DO_NOT_TRACK=1 codegraph sync`。以 `codegraph status --json` 核对 `initialized` 与已索引文件数。
3. 以 `codegraph install --print-config cursor` 的公开示例为依据，在项目 `.cursor/mcp.json` 合并项目入口 `clarity-codegraph`，包含命令 `codegraph`、参数 `serve --mcp --path ${workspaceFolder}` 和环境项 `DO_NOT_TRACK=1`。保留其他 MCP 配置。向 `AGENTS.md` 补充或复用现有 CodeGraph 指引，说明查符号与调用关系先用项目 MCP，再按需核对源码。若本机 PATH 无法解析 `codegraph`，交回缺口，项目配置使用可移植的命令名。
4. 交回索引状态、文件数、变更路径和待重开会话事项。用已知项目符号做查询。只有在 Cursor 实际调用成功时才记录 MCP 已验证，结构核对和 CLI 查询各自留证。
