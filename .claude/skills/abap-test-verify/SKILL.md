---
name: abap-test-verify
description: ABAP/MCP 改动的端到端验证实操——Transport 归属验证（读 E070/E071/TADIR 字段语义）、测试流程标准动作、激活验证、读回验证。tester 对代码改动做端到端验证时使用。
---

# ABAP 改动端到端验证实操（经实测）

本 skill 编码了 tester 对 ABAP/MCP 代码改动做端到端验证的专属实操：Transport 归属验证（读 `E070`/`E071`/`TADIR`）、测试流程标准动作、激活与读回验证。经 MCP 实测验证。

写入操作本身（CreateObject/UpdateObjectSource/ActivateObject 的对象类型支持、Transport 坑、源码要求、修改日志模板）见 **`abap-adt-write`** skill——本 skill 只覆盖"验证"侧。

## 什么时候用这个 skill

- 验证代码改动是否真正生效（创建/更新/激活/读回）
- 验证对象挂到预期的 TR/task 上、package 正确
- 验证激活成功（`activationExecuted="true"` 且无错误）
- 验证参数校验逻辑（如传 package 不传 transport 应被拦截）

> 🔴 **授权前置**：验证中涉及的创建/更新/激活操作须先经用户授权。主 Claude 任务分配时会明示「已授权可执行」或「未授权只验证不动手」。未授权只做读取/分析/待命。详见 tester agent md 的授权强制规范。

## Transport 归属验证（核心）

对象会落到 `transport_request` 指定 request 的**子 task** 里（request 自身 E071 为空，对象在 task 的 E071）——这是正常行为，验证时读 **task 的 E071**，别误判为失败。

验证 transport 归属读三张表：

| 表 | 用途 | 关键字段 |
|---|---|---|
| `E070` | 确认 request/task 父子关系 | `TRFUNCTION`（K=request、S=task）、`STRKORR`（指向上级） |
| `E071` | 对象清单 | `PGMID`/`OBJECT`/`OBJ_NAME`、`LOCKFLAG`（=X 表示锁定） |
| `TADIR` | 确认 package | `DEVCLASS`（package 名）、`OBJ_NAME`、`PGMID`/`OBJECT` |

验证步骤：
1. 读 `E070` 确认 request/task 父子关系（TRFUNCTION K=request、S=task，STRKORR 指向上级）。
2. 读 task 的 `E071` 确认对象在清单里（不是 request 的 E071，是 task 的）。
3. 读 `TADIR` 确认 `DEVCLASS` 与预期 package 一致。

## 测试流程标准动作

1. **创建/更新对象**：用新名字避免与遗留空壳冲突。
2. **激活**：检查 `activationExecuted="true"` 且无错误消息。
3. **读回源码**：用对应 Get 工具读，确认写入内容正确。
4. **TR 归属**：带路径时读 `E071`/`TADIR` 确认（见上节）。
5. **隔离测试**：测试对象用 $TMP 或明确指定的测试 TR，**不要污染正式 package**。

若项目配置了多个 SAP 系统，上述激活/读回/TR 归属验证的工具调用支持可选 `system` 参数指定目标系统；**验证流程中创建、更新、激活、读回、查表须用同一个 `system`**（默认系统场景则全程不传）。多系统配置见 `sap-basic-data-query` skill。

## 验证业务结果（EWM 业务表）

验证业务结果时需要查 **EWM 业务表**（`/SCWM/ORDIM_O`、`/SCWM/AQUA`、`/SCDL/DB_PROCI_*` 等仓库任务/库存/交货/仓位表）**自己直接用 `GetTableContents` 查**，不必转交其他 agent。EWM 表知识（表关系/字段语义等深层疑问）的**权威**是 `sap-ewm-function-consultant`，遇到拿不准的表含义可向它请教，但"查个数据验证结果"这类事自己做，不要凭空猜表结构。查表实操细节见 `sap-ewm` skill。

## 联动校验测试

验证参数校验逻辑（如传 package 不传 transport 应被拦截且不发请求）——确认错误被正确拦截、无副作用请求发出。

## 报告格式

用表格汇总测试矩阵（步骤 / 结果 / 证据），每个 pass/fail 结论附客观证据（工具返回值、表数据），不臆断。验证不了直说「无法验证」并说明缺什么入口，绝不伪造输出。测试完报告遗留对象清单供清理。

## MCP 源码位置

MCP server 的安装路径因环境而异，不要在文档里写死绝对路径。需要定位 MCP 源码或确认实际启用的 server 时，读项目的 `.mcp.json`（其中 `mcpServers` 的每个条目 `args` 指向该 server 的 `dist/index.js`）。改 MCP 源码后须 `npm run build` 并重启 MCP 才生效。ADT 底层契约见记忆 `adt-rest-create-update-contract.md`。
