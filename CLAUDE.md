# Project: SAP Agent

## 项目概况

- 项目定位：构建一个对 SAP S/4 系统全知全能的智能体。
- 经 mcp-abap-adt-b 连接 SAP S/4 HANA 系统（具体连接实例视使用环境而定）。
- 技术栈：ABAP + TypeScript/MCP。
- 本项目内置 skills 与 agents，统一置于 `.claude/` 目录下。
- 产出目录：本项目输出的所有文件统一存放于 `workfolder/`（已纳入 .gitignore，不纳入版本管理）。

## 🔴 强制规范：代码创建与修改须先经用户授权

任何 agent 凡需在 SAP S/4 系统中创建或修改代码（`CreateObject` / `UpdateObjectSource` / `ActivateObject`），一律先汇总至主 Claude，由主 Claude 报请用户授权，获准后方可执行。未获授权时，改以分析、方案输出或待命方式处理，严禁擅自执行。

强制执行机制：

- `.claude/settings.json` 的 PreToolUse hook 拦截上述三项工具，每次调用返回 `ask`，弹窗由用户确认，不予自动放行。
- ⚠️ hook 在 subagent 中同样触发，但 `ask` 在非交互式 subagent 中的具体行为官方未作明确规定；首次经 agent 路径执行写操作时须实测验证。

## 任务分配

- 主 Claude 仅承担用户沟通、任务分配与结果汇总职责；具体工作分配给对应 agent，仅当所有 agent 场景均不匹配时方由主 Claude 自行执行。
- Agent 按照自己的职责工作， 仅使用允许的 skill。
- 依据 `.claude/agents` 下各 agent 的 frontmatter `description` 所述触发场景进行分配。
- 禁止臆测技术对象：分配 prompt 时不得引用未经核实的表名/字段名/类名/FM 名。应描述业务目标（如"查询某物料本月库存"），而非指定技术对象；确需引用某对象时，须先经 MCP 实测确认其存在。
- 分配时须在 prompt 中明确标注「已授权可执行」或「未授权，仅分析不执行」；agent 不得以「便于测试」「临时验证」等理由越权操作。

### 模块顾问路由

按业务模块分流，涉及哪个模块就调用哪个模块的顾问；跨模块问题同时调用多个顾问（在同一条消息里并行派工，独立模块并行、有依赖再串行）：

| 业务模块 | 顾问 agent |
|---|---|
| 仓储管理 / 仓库任务 / 补货 / EWM 主数据与业务数据 | `sap-ewm-function-consultant` |
| 采购 / 库存 / 物料与供应商主数据 | `sap-mm-function-consultant` |
| 销售 / 交货 / 开票 / 定价 / 客户主数据 | `sap-sd-function-consultant` |
| 生产计划 / BOM / 工艺路线 / 工作中心 / MRP / 生产订单 | `sap-pp-function-consultant` |
| 财务会计 / 总账 / 应收应付 / 资产 / 凭证 | `sap-fi-function-consultant` |
| 管理会计 / 成本中心 / 利润中心 / 内部订单 / 产品成本 / CO-PA | `sap-co-function-consultant` |

- 模块归属不明的 SAP 业务问题：先按上表最接近的模块派工，必要时让顾问回报该问题是否超出其模块范围，再行转派。
- ABAP 开发 / 代码修改（`CreateObject`/`UpdateObjectSource`/`ActivateObject`）：派 `abaper`（须先获用户授权）。
- 代码改动审查：派 `code-reviewer`；端到端验证：派 `tester`；文档维护：派 `clerk`。
- 各模块表知识 / 字段语义的权威是对应模块顾问；跨模块数据关联（如 SD 开票转 FI 凭证）由相关模块顾问各司其职、各自负责本模块侧。

## 工具

- Skills：调用前须确认文件存在并 Read SKILL.md 全文，不得仅凭系统注入的 description 推断其规则。
- MCP：所有 agent 均可使用完整的 MCP 功能（含 `GetTableContents`）。数据查询为手段，由对应任务执行者自行负责。