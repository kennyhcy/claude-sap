---
name: ewm-table-query-guide
description: 在 SAP S/4 HANA 系统上经 MCP 查询 EWM 数据的实操指南——字段命名陷阱、where/fields 大小写规则、ORDIM 双表查询配方、空结果验证法。
---

# Query EWM Warehouse Data on SAP S/4 HANA

SAP S/4 HANA 系统为 S/4HANA-based decentralized EWM,经 MCP 只读访问。本指南编码了表布局、状态/工序类型含义,以及**实测发现的字段命名陷阱**。

## Core tables

查数据时先查 [[ewm-common-tables.md]] 定位表,再用 `GetTableContents` 查;用 `fields` 只投影简单字段,避开 GUID/RAW/STRING 等复杂类型。

一条 WT 物理上只存在于 `ORDIM_O`(open)或 `ORDIM_C`(confirmed)**之一**,由状态决定。

## Key fields (real DDIC names, lowercase_with_underscore)

| Field | Type | Meaning |
|---|---|---|
| `lgnum` | char | Warehouse number (e.g. `CN01`) |
| `tanum` | numc | WT number (e.g. `10006130504`) |
| `tapos` | numc | WT item number |
| `tostat` | char | Status — **`C` = Confirmed**; **`A` = canceled**; empty = open(用户 2026-08-04 确认,见 memory ewm-wt-tostat-codes) |
| `trart` | char | Movement type (3 = goods-issue related) |
| `procty` | char | Warehouse process type (e.g. `2000`, `3042`) |
| `prces` / `procs` | char | Source / destination process |
| `created_at` | num | **Timestamp `YYYYMMDDHHMMSS`** (e.g. `20251031125945`) |
| `created_by` | char | Creator user |
| `confirmed_at` | num | Confirmation timestamp (same format) |
| `vlenr` / `nlenr` | char | Source / destination handling unit |
| `vltyp`/`vlpla` | char | Source storage type / bin |
| `nltyp`/`nlpla` | char | Destination storage type / bin |
| `vsolm` / `meins` | num/char | Quantity / unit |
| `who` | num | **WO number** (e.g. `2002804655`) |
| `matid` | raw | Material GUID (NOT material number — no `matnr` here) |
| `charg` | char | Batch |
| `qdoccat`/`qdocid` | char/raw | qRFC doc category / id (ERP↔EWM link) |

⚠️ **No `matnr` field.** Material is identified by `matid` (GUID). To resolve to a material number, join/lookup separately — do not assume a `matnr` column exists.


### `where` clause → use uppercase_with_underscore (real DDIC name)
```
where: LGNUM = 'CN01' AND CREATED_AT >= 20260803000000
```
- ✅ `CREATED_AT`, `VLPLA`, `WHO` — works
- ❌ `createdAt` (camelCase) → raises `CX_SY_DYNAMIC_OSQL_SEMANTICS` (dynamic SQL semantic exception)
- Timestamps are **numbers**, compare numerically: `created_at >= 20260803000000 AND created_at <= 20260803235959`
- Single-sided range also works: `CREATED_AT >= 20260803000000`

### `fields` projection → always uppercase
```
fields: LGNUM, TANUM, CREATE_AT, TOSTAT, PROCTY, VLPLA, NLPLA, VSOLM, MEINS, WHO
```
- ✅ `CREATED_AT` — returns values (keys come back UPPERCASE: `CREATEDAT`, `CREATEDBY`)
- ❌ `created_at` in `fields` → **no error, but value comes back empty** (silent failure — very easy to miss)



### How to confirm a real field name
`GetTable` on `/SCWM/ORDIM_C` shows only include placeholders (the table is built from includes). To see real field names, run `GetStructure` on the include:
- `/SCWM/S_ORDIM_ATT` — main WT attributes (has `created_at`, `procty`, `vlpla`, etc.)
- `/SCWM/S_ORDIM_C_KEY` — key fields
- `/SCWM/S_ORDIM_C_ATT` — confirmed-WT-specific fields

## Query recipes

### 1. Today's tasks for a warehouse (query BOTH tables)
```
table: /scwm/ordim_o
where: lgnum = 'CN01' AND created_at >= 20260803000000
fields: tanum,createdAt,createdBy,tostat,procty,vlpla,nlpla,vsolm,meins,who
```
Repeat with `table: /scwm/ordim_c` for confirmed ones. If both empty → no WT created today (verify by checking the newest `created_at` with a wider range, e.g. `created_at >= 20250101000000`).

### 2. All tasks in a WO
```
where: lgnum = 'CN01' AND who = 2002804655
```
Run on both `/scwm/ordim_o` and `/scwm/ordim_c` — a WO may have some open and some confirmed items.

### 3. Unconfirmed (open) WT
Just query `/scwm/ordim_o` — by definition all rows there are open. Optionally `where: tostat = ''` but usually redundant.

### 4. WT touching a specific bin (source OR destination)
```
where: lgnum = 'CN01' AND (vlpla = 'GI-PACK-AA-IAM' OR nlpla = 'GI-PACK-AA-IAM')
```
Run on both tables.

### 5. Outbound tasks by process type
```
where: lgnum = 'CN01' AND procty = '2000'
```
PROCTY values seen on the system: `2000` (outbound, move to GI-PACK), `3042` (OB02 outbound process). Full process-type catalog is in `/SCWM/T333` (`lgnum`/`procty`/`trart`/`act_type`/`vltyp`/`nltyp`/`wcr`/`prces`).

## Result presentation

- Show a compact table of key fields (lgnum, tanum, status, procty, source→dest bin, qty, WO, creator, time).
- Decode `tostat`: `C` = Confirmed, `A` = canceled, empty = Open(见 memory ewm-wt-tostat-codes)。
- Format `created_at`/`confirmed_at` numbers as `YYYY-MM-DD HH:MM:SS` for readability.
- If result is empty, **verify** by widening the date range before concluding "no data" — silent empty (from a bad `fields` name) looks identical to genuinely no rows. Confirm with a known-good range first.
- Note the source table (ORDIM_O vs ORDIM_C) so the user knows whether they're seeing open or confirmed tasks.

## Constraints

- **Read-only.** System access via MCP is read-only — never write code or persist changes. Deliver fixes as recommendations only.
- Always verify table/field names against the system before asserting them.
