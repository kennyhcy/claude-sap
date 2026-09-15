---
name: sap-ewm
description: SAP EWM 系统知识与业务数据查询总索引（经 MCP 实测）。覆盖四块：①业务数据表查询实操（表清单/表间关系、where/fields 大小写规则、ORDIM 双表配方、字段陷阱）②补货 Replenishment ③盘点 Physical Inventory/重盘/容差 ④QM defect（IOT4/IOT5）。查 EWM 数据或问补货/盘点/QM 流程时使用；先读本 SKILL.md 再按需读 references/ 下对应文件。
---

# SAP EWM

本 skill 是 EWM 知识与查询实操的总入口。按场景读对应 reference（均在 `references/` 下），先读再作答：

| 场景 | reference 文件 |
|---|---|
| 查 EWM 业务数据（WT/库存/仓位/交货单/HU/资源/QM 表等）| `ewm-table-query-guide.md`（实操指南+查询配方）+ `ewm-common-tables.md`（表清单+表间关系） |
| 补货 / 固定仓位补货 / SRPL | `ewm-replenishment.md` |
| 盘点 / 重盘 / 容差组 / Cycle Counting / 零盘 | `ewm-physical-inventory.md` |
| QM defect / 入库检验 IOT4 / internal 质检 IOT5 | `ewm-qm-defect-distributed.md` |

## 通用守则

- **查数据三步**：先 `ewm-common-tables.md` 定位表 → `GetTable`/`SearchObject` 验证表存在（未核实到就明说，禁止列多个候选表逐一尝试）→ `GetTableContents` 取数（`fields` 只投影简单字段，避开 GUID/RAW/STRING）。
- **空结果先放宽日期范围验证**再下"无数据"结论——字段名写错的静默空返回与真无数据无法区分。
- **字段命名陷阱**（实测最易踩坑，详见 query guide）：WT 表无 `matnr`（物料是 `matid` GUID）；`where` 用大写带下划线（`LGNUM = 'CN01'`，camelCase 抛 `CX_SY_DYNAMIC_OSQL_SEMANTICS`）；`fields` 一律大写（小写**不报错但返回空**）；时间戳按数字比较。
- **一张 WT 只在 ORDIM_O（open）或 ORDIM_C（confirmed）之一**，查 WT 两张都查；`tostat`：`C`=Confirmed、`A`=canceled、空=open。
- 各 reference 中标注「实测」的表/FM/事务码照写；标注「推断」的按 Truthfulness Rule 分开标注；未覆盖的新对象先 MCP 验证再报。
- **只读**：严禁写代码或持久化改动；多系统取数可传 `system` 参数（见 `sap-basic-data-query` skill）。
