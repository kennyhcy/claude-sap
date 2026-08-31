---
name: sap-ewm-business-data-query
description: 经 MCP 读取 EWM 业务数据的实操流程。当前以表读取为主（定位表、验证表名、GetTableContents 取数、字段命名陷阱、where/fields 大小写规则、ORDIM 双表查询配方、空结果验证法），架构上预留向 OData / API / RFC 等读取方式扩展。查询 EWM 业务数据时使用。
---

# 读取 EWM 业务数据

本 skill 用于经 MCP 读取 SAP S/4 HANA 系统中分布式 EWM 的业务数据。当前以**表读取**为主要手段（`GetTableContents` 等），架构上预留向 OData 服务、API、RFC 等其他读取方式扩展的空间。本 skill 编码了取数实操流程、表布局、状态/工序类型含义，以及**实测发现的字段命名陷阱**。

完整实操指南与查询配方见 reference 文件 **[[ewm-table-query-guide.md]]**（`references/ewm-table-query-guide.md`，相对本 skill 目录）；表清单与表间关系见 **[[ewm-common-tables.md]]**（`references/ewm-common-tables.md`）。本 skill 是入口指针，查询前先读这两个 reference。

## 何时使用本 skill

- 用户问 EWM 业务数据（仓库任务 WT / 库存 / 仓位 / 交货单 / HU / 资源等）的实际记录
- 需经 MCP 读取 EWM 业务数据
- 遇到字段命名 / where 大小写 / fields 投影相关问题
- 查 WT（ORDIM_O / ORDIM_C）数据

## 数据读取流程

1. **定位表**：先查 `references/ewm-common-tables.md` 找到目标表名（仓位->`/SCWM/LAGP`、WT->`/SCWM/ORDIM_O`/`/SCWM/ORDIM_C`、库存->`/SCWM/AQUA`、Stock Type 配置->`/SCWM/TCAT`、交货单->`/SCDL/DB_PROCH_*`/`DB_PROCI_*`、检验凭证->`/SCWM/TWF_INSP`、Follow-up->`/SCWM/TQFU`、系统版本->`CVERS` 等）。
2. **验证表存在**：用 `GetTable`（验证透明表，读取字段结构）或 `SearchObject`（DDIC 确认 TABL/DT）核实表名存在。验证通过方可查询；查不到须明说「未核实到」，**禁止列出多个候选表名逐一尝试**。
3. **取数**：核实表名后，用 `GetTableContents` 查询实际业务数据。用 `fields` 仅投影简单字段，避开 GUID/RAW/STRING 等复杂类型。
4. **空结果验证**：若结果为空，**先放宽日期范围验证**再下“无数据”结论--字段名写错导致的静默空返回与真正无行无法区分。先用已知有数据的范围确认一次。

## 多系统选择

若项目配置了多个 SAP 系统，所有取数工具（`GetTable`/`GetTableContents`/`SearchObject` 等）支持可选 `system` 参数指定目标系统 id；不传则用默认系统。详见 `sap-basic-data-query` skill 的「多系统选择」一节。单系统场景无需关心。

## 字段命名陷阱（实测，最易踩坑）

⚠️ **WT 表没有 `matnr` 字段。** 物料用 `matid`（RAW/GUID）标识，解析成物料号需另行 join/查询，不得假设存在 `matnr` 列。

### `where` 子句 -> 用大写带下划线（真实 DDIC 名）
```
where: LGNUM = 'CN01' AND CREATED_AT >= 20260803000000
```
- ✅ `CREATED_AT`、`VLPLA`、`WHO` - 可用
- ❌ `createdAt`（camelCase）-> 抛 `CX_SY_DYNAMIC_OSQL_SEMANTICS`
- 时间戳是**数字**，按数字比较：`created_at >= 20260803000000 AND created_at <= 20260803235959`
- 单边范围也可：`CREATED_AT >= 20260803000000`

### `fields` 投影 -> 一律大写
```
fields: LGNUM, TANUM, CREATED_AT, TOSTAT, PROCTY, VLPLA, NLPLA, VSOLM, MEINS, WHO
```
- ✅ `CREATED_AT` - 返回值（key 回来时大写：`CREATEDAT`、`CREATEDBY`）
- ❌ `fields` 里写 `created_at` -> **不报错，但值返回空**（静默失败，极易漏看）

### 如何确认真实字段名
`GetTable` 查 `/SCWM/ORDIM_C` 只显示 include 占位符（该表由 include 拼成）。要看真实字段名，用 `GetStructure` 查 include：
- `/SCWM/S_ORDIM_ATT` - WT 主属性（含 `created_at`、`procty`、`vlpla` 等）
- `/SCWM/S_ORDIM_C_KEY` - key 字段
- `/SCWM/S_ORDIM_C_ATT` - confirmed-WT 专有字段

## ORDIM 双表查询配方

一条 WT 物理上只存在于 `ORDIM_O`（open）或 `ORDIM_C`（confirmed）**之一**，由状态决定。查 WT 时两张表都要查。

- `tostat` 状态码：**`C` = Confirmed（已确认）**、**`A` = canceled（已取消）**、空 = open（用户 2026-08-04 确认，见 memory ewm-wt-tostat-codes）

### 1. 某仓库今日任务（两张表都查）
```
table: /scwm/ordim_o
where: lgnum = 'CN01' AND created_at >= 20260803000000
fields: TANUM, CREATED_AT, CREATED_BY, TOSTAT, PROCTY, VLPLA, NLPLA, VSOLM, MEINS, WHO
```
对 `/scwm/ordim_c` 重复一次取已确认的。两张都空 -> 今日无 WT（用更大范围如 `created_at >= 20250101000000` 查最新 `created_at` 验证）。

### 2. 某仓库订单（WO）的全部任务
```
where: lgnum = 'CN01' AND who = 2002804655
```
两张表都查--一个 WO 可能部分 open 部分 confirmed。

### 3. 未确认（open）WT
只查 `/scwm/ordim_o`--该表所有行按定义都是 open。可选 `where: tostat = ''`，通常冗余。

### 4. 涉及某仓位的 WT（源或目标）
```
where: lgnum = 'CN01' AND (vlpla = 'GI-PACK-AA-IAM' OR nlpla = 'GI-PACK-AA-IAM')
```
两张表都查。

### 5. 按工序类型查出站任务
```
where: lgnum = 'CN01' AND procty = '2000'
```
系统中见过的 PROCTY：`2000`（outbound，搬到 GI-PACK）、`3042`（OB02 outbound process）。完整工序类型目录在 `/SCWM/T333`（`lgnum`/`procty`/`trart`/`act_type`/`vltyp`/`nltyp`/`wcr`/`prces`）。

## 结果呈现

- 用紧凑表格列关键字段（lgnum、tanum、status、procty、源->目标仓位、qty、WO、创建人、时间）。
- 解码 `tostat`：`C` = Confirmed、`A` = canceled、空 = Open（见 memory ewm-wt-tostat-codes）。
- `created_at`/`confirmed_at` 数字格式化为 `YYYY-MM-DD HH:MM:SS` 便于阅读。
- 结果为空时，**先放宽日期范围验证**再下"无数据"结论。
- 标注来源表（ORDIM_O vs ORDIM_C），让用户知道看到的是 open 还是 confirmed 任务。

## 扩展说明

本 skill 当前聚焦表读取，但定位不限于"查表"。未来 EWM 业务数据可通过以下方式读取（届时据此扩展）：
- **OData 服务**：EWM 提供的标准/自定义 OData 服务。
- **API / RFC**：经 RFC 函数模块读取业务对象。
- 其他经 MCP 可达的读取通道。

当前 reference 中的表清单与查询配方仍适用于表读取场景。

## 约束

- **只读。** 经 MCP 访问为只读--严禁写代码或持久化改动，修复建议以 recommendation 形式给出。
- 断言任何表名 / 字段名前，先对照系统验证。
- 详见 `references/ewm-table-query-guide.md` 与 `references/ewm-common-tables.md`。
