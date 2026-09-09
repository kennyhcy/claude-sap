# Readme
# SAP Agent

对 SAP S/4 HANA 系统全知全能的智能体。经 [mcp-abap-adt-b](https://github.com/kennyhcy/mcp-abap-adt-b) 连接 SAP S/4 HANA，通过内置的 agents 与 skills，提供业务问答、配置指引、业务数据查询、ABAP 开发、代码审查与端到端验证等能力。

* **技术栈**：ABAP + TypeScript/MCP
* **运行环境**：Claude Code（CLI / Desktop / Web / IDE 插件）
* **MCP 连接**：[mcp-abap-adt-b](https://github.com/kennyhcy/mcp-abap-adt-b) stdio，经 `node dist/index.js` 启动，接入示例见 `.mcp.json.example.txt`）

\---

## 目录结构

```
claude-sap/
├── .claude/
│   ├── agents/          # 10 个角色 agent 定义（.md）
│   ├── skills/          # 11 个 skill（每个含 SKILL.md + 可选 references/）
│   ├── settings.json    # PreToolUse hook：写操作工具强制 ask 拦截
│   └── hooks/
├── CLAUDE.md            # 项目主指令（路由、规范、授权红线）
├── GIT-GUIDE.md         # 简明 Git 操作指南
├── CHANGELOG.md         # 变更记录
├── .mcp.json.example.txt# MCP 接入示例
├── .gitignore
├── px\\\_claude\\\_sap.bat    # Claude 启动脚本
├── px\\\_cmd\\\_here.bat      # 当前目录开 cmd
└── git-toolbox.cmd      # Git 工具脚本
```

> 产出目录 `workfolder/` 已纳入 `.gitignore`，所有运行时输出文件存放于此，不纳入版本管理。

\---

## Agents（10 个）

按角色分流，由主 Claude 依据 frontmatter `description` 派工：

|类别|agent|职责|
|-|-|-|
|文档|`clerk`|撰写/维护所有 agent 与 skill 的 .md、CLAUDE.md、reference 文件|
|开发|`abaper`|ABAP 代码创建/修改/激活（含写操作工具）|
|审查|`code-reviewer`|代码 diff 审查（只读不改）|
|验证|`tester`|端到端验证（含写操作工具）|
|顾问|`sap-ewm-function-consultant`|仓储管理 / 仓库任务 / 补货 / EWM 主数据与业务数据|
|顾问|`sap-mm-function-consultant`|采购 / 库存 / 物料与供应商主数据|
|顾问|`sap-sd-function-consultant`|销售 / 交货 / 开票 / 定价 / 客户主数据|
|顾问|`sap-pp-function-consultant`|生产计划 / BOM / 工艺路线 / 工作中心 / MRP / 生产订单|
|顾问|`sap-fi-function-consultant`|财务会计 / 总账 / 应收应付 / 资产 / 凭证|
|顾问|`sap-co-function-consultant`|管理会计 / 成本中心 / 利润中心 / 内部订单 / 产品成本 / CO-PA|

\---

## Skills（11 个）

skill 按归属分四类，详见 [`clerk.md`](.claude/agents/clerk.md) 的「Skill-Agent 索引同步规则」：

|类别|skill|说明|
|-|-|-|
|EWM 专属|`sap-ewm-business-data-query`|经 MCP 读取 EWM 业务数据（表查询配方、字段陷阱）|
|EWM 专属|`sap-ewm-qm-defect`|分布式 EWM QM defect 流程口径|
|EWM 专属|`sap-ewm-replenishment`|EWM 补货系统知识（6 表决定链路）|
|EWM 专属|`br-write-ps`|EWM BR 文档 Product Specification（PS）撰写|
|跨模块通用|`sap-basic-data-query`|SAP 系统通用知识库（IDoc/OData/BAPI/CDS View/SPRO 等）|
|跨模块通用|`sap-note`|读取 SAP Note / KBA 全文（经 `get\\\_sapnote.ps1` 脚本）|
|跨模块通用|`sap-note-search`|按关键词搜 SAP Note / KBA 编号|
|技术/工具|`abap-adt-write`|mcp-abap-adt 写入工具实操（Create/Update/Activate）|
|技术/工具|`abap-test-verify`|ABAP/MCP 改动端到端验证（E070/E071/TADIR）|
|技术/工具|`abap-code-review`|ABAP 代码静态审查（Clean ABAP 规范）|
|技术/工具|`mcp-adt-pitfalls`|mcp-abap-adt 项目已知坑清单（TS/MCP）|

\---

## 核心规范

1. **🔴 代码创建/修改须先经用户授权**：凡 `CreateObject` / `UpdateObjectSource` / `ActivateObject`，一律先汇总至主 Claude 报请用户授权，获准后方可执行。`.claude/settings.json` 的 PreToolUse hook 对这三项工具强制返回 `ask`，弹窗由用户确认。
2. **模块顾问路由**：按业务模块分流，跨模块问题同条消息并行派工；模块归属不明按最接近模块派工，必要时转派。
3. **禁止臆测技术对象**：派工 prompt 描述业务目标，不指定未核实的表名/字段名/类名/FM 名；确需引用某对象时先经 MCP 实测确认。
4. **Skill 调用前必读 SKILL.md 全文**：不得仅凭系统注入的 description 推断其规则。

详见 [`CLAUDE.md`](CLAUDE.md)。

\---

## 快速开始

1. 安装 Claude Code（CLI / Desktop / IDE 插件任一）。
2. 复制 `.mcp.json.example.txt` 为 `.mcp.json`，将 `args` 路径改为你本地 mcp-abap-adt 的 `dist/index.js` 绝对路径。
3. 确保已登录 SAP S/4 HANA（mcp-abap-adt 的连接配置）。
4. 运行 `px\\\_claude\\\_sap.bat`（或在项目目录启动 Claude Code）。
5. 在对话中直接提问，主 Claude 会自动路由到对应 agent。

\---

## Git 操作

参见 [`GIT-GUIDE.md`](GIT-GUIDE.md) 与 [`git-toolbox.cmd`](git-toolbox.cmd)。

