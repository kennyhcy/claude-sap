# 变更记录（CHANGELOG）

## [v0.1.0] - 2026-08-16

- **版本号**：v0.1.0
- **提交人**：HU Kenny (BD/PTD-I2D2) `<ukh1sgh@bosch.com>`
- **时间**：2026-08-16
- **提交信息**：补齐全模块顾问；skill 统一 `sap-XX-*` 命名；新增 Skill-Agent 索引同步规则；精简全量 agent 文档；新增 README

### Agents（`.claude/agents/`）
- **新增 5 个模块顾问**：`sap-mm-function-consultant`（采购/库存）、`sap-sd-function-consultant`（销售/交货/开票）、`sap-pp-function-consultant`（生产计划/BOM/MRP）、`sap-fi-function-consultant`（财务会计）、`sap-co-function-consultant`（管理会计）
- **重命名**：`ewm-function-consultant.md` -> `sap-ewm-function-consultant.md`（统一 `sap-` 前缀）
- **clerk.md 新增「Skill-Agent 索引同步规则」章节**：6 个子节
  - skill 归属判定（模块专属/跨模块通用/技术工具/业务数据查询四类）
  - 新增 skill 的强制同步动作
  - 重命名 / 删除同步（Grep 全量排查）
  - 索引与正文一致性自检清单
  - 不擅改 frontmatter
  - 新增 agent 的 skill 索引预置（与新增 skill 规则对称）
- **精简全量 agent 文档**（信息无损）：删冗余引导句、合并重复 SAP Note 提示、去重开篇自我介绍；abaper/tester/code-reviewer 的 🔴 授权红线一字保留
- **修正 EWM 顾问索引不一致**：补回漏挂的 `br-write-ps`；`sap-note` / `sap-note-search` 配对

### Skills（`.claude/skills/`）
- **新增**：`sap-basic-data-query`（SAP 系统通用知识库，跨模块共享）
- **重命名（统一 `sap-` 前缀）**：
  - `ewm-table-query/` -> `sap-ewm-business-data-query/`（SKILL.md + 2 个 references）
  - `ewm-qm-defect/` -> `sap-ewm-qm-defect/`（SKILL.md + 1 个 reference）
  - `ewm-replenishment/` -> `sap-ewm-replenishment/`（SKILL.md + 1 个 reference）
- 调整 `abap-adt-write` / `abap-test-verify` / `br-write-ps` / `sap-note` 等多个 SKILL.md 口径

### 根文件与配置
- **新增**：`README.md`（项目说明文档）
- **新增**：`px_claude_sap.bat`（替代 `px_claude_EWM.bat`，启动脚本改名适配全模块）
- **删除**：`CLAUDE - Copy.md`、`px_claude_EWM.bat`（废弃副本与旧名脚本）
- 修改 `.mcp.json.example.txt`、`.gitignore`、`CLAUDE.md`、`.claude/settings.json`

---

## [v0.02] - 2026-08-15

- **版本号**：0.02
- **提交人**：HU Kenny (BD/PTD-I2D2) `<ukh1sgh@bosch.com>`
- **时间**：2026-08-15
- **提交信息**：新增变更记录与 Git 指南；修正 mcp 示例路径

### 变更内容
- 新增 `CHANGELOG.md` - 变更记录文档
- 新增 `GIT-GUIDE.md` - 简明 Git 操作指南
- 修改 `.mcp.json.example.txt` - mcp 入口路径 `index.js` -> `dist\index.js`

---

## [Initial] - 88ba499

- **版本号**：0.01 - 88ba499
- **提交人**：HU Kenny (BD/PTD-I2D2) `<ukh1sgh@bosch.com>`
- **时间**：2026-08-14 23:03:16
- **提交信息**：Initial

建立项目骨架，共 49 个文件、净增 2118 行。

### Agents（`.claude/agents/`）
- `abaper.md` - ABAP 开发
- `clerk.md` - 文档撰写
- `code-reviewer.md` - 代码审查
- `ewm-function-consultant.md` - EWM 功能顾问
- `tester.md` - 测试验证

### Skills（`.claude/skills/`）
- `abap-adt-write/` - ABAP 对象创建/修改/激活
- `abap-code-review/` - ABAP 代码审查
- `abap-test-verify/` - ABAP 测试验证
- `br-write-ps/` - BR 文档 PS 部分
- `ewm-qm-defect/` - EWM 质量缺陷
- `ewm-replenishment/` - EWM 补货
- `ewm-table-query/` - EWM 表查询
- `mcp-adt-pitfalls/` - mcp-abap-adt 坑
- `sap-note-search/` - SAP Note 检索
- `sap-note/` - SAP Note 获取（含 `get_sapnote.ps1` + 24 个缓存 Note）

### 项目配置与根文件
- `.gitignore` - 忽略本地个人配置
- `.mcp.json.example.txt` - MCP 接入示例
- `CLAUDE.md` - 项目主指令
- `px_claude_EWM.bat` - Claude 启动脚本
- `px_cmd_here.bat` - 当前目录开 cmd

---

## 备注

- CHANGELOG.md 曾于 v0.02 后的「完善 git toolbox」提交（b8ce0d0, 2026-08-15）中误删，v0.1.0 据原版格式重建并补齐。
