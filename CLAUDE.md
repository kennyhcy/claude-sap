# Project: SAP Agent

## 项目概况

- 项目定位：构建一个对 SAP S/4 系统全知全能的智能体。
- 经 mcp-abap-adt-b 连接 SAP S/4 HANA 系统（具体连接实例视使用环境而定）。
- 技术栈：ABAP + TypeScript/MCP。
- 本项目内置 skills 与 agents，统一置于 `.claude/` 目录下。
- 产出目录：本项目输出的所有文件统一存放于 `workfolder/`（已纳入 .gitignore，不纳入版本管理）。

## 🔴 强制规范：代码创建与修改须先经用户授权

任何 agent 凡需在 SAP S/4 系统中创建或修改代码（`CreateObject` / `UpdateObjectSource` / `ActivateObject`），一律报请用户授权，获准后方可执行。未获授权时，改以分析、方案输出或待命方式处理，严禁擅自执行。

强制执行机制：

- `.claude/settings.json` 的 PreToolUse hook 拦截上述三项工具，每次调用返回 `ask`，弹窗由用户确认，不予自动放行。
- ⚠️ hook 在 subagent 中同样触发，但 `ask` 在非交互式 subagent 中的具体行为官方未作明确规定；首次经 agent 路径执行写操作时须实测验证。

## 任务执行方式

- 工作主要经封装的 workflow 完成，不再按模块拆分派发 agent。
- 禁止臆测技术对象：prompt 中不得引用未经核实的表名/字段名/类名/FM 名。应描述业务目标（如"查询某物料本月库存"），而非指定技术对象；确需引用某对象时，须先经 MCP 实测确认其存在。
- 涉及 SAP 写操作的任务须明确标注「已授权可执行」或「未授权，仅分析不执行」；不得以「便于测试」「临时验证」等理由越权操作。

## 知识型问答的检索顺序

用户提出知识型问题（概念/流程/配置等）时，按以下优先级检索，逐级降级，经 workflow `kb-qa`（`.claude/workflows/kb-qa.js`）执行：

1. 项目 `docupedia/` 知识库 —— 有命中则载入文档分析并解答；
2. 环境变量 `WIKI_DIR` 指定的知识库目录 —— docupedia 未命中时查找其中文档；
3. 网络搜索 —— 两级知识库均未命中时才使用。

注意：`docupedia/` 为 Docupedia 页面落盘的知识库（由 `docupedia-read` skill 维护），不适用 `workfolder/` 输出规则。
用户是 SAP 专家顾问, 提供的答案中要包含技术细节, 表, 程序名, 类, 方法, 视图, 事务代码等都要指出。

## 工具

- Skills：调用前须确认文件存在并 Read SKILL.md 全文，不得仅凭系统注入的 description 推断其规则。EWM 知识与数据查询统一入口为 `sap-ewm` skill（SKILL.md 只作索引，具体流程细节在其 `references/` 下，按场景先读对应 reference 再作答）。
- MCP：数据查询为手段，由对应任务执行者自行负责（含 `GetTableContents`）。
