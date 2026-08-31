---
name: sap-ewm-physicalinventory
description: 经 MCP 实测（2026-08-21）的 SAP EWM 盘点（Physical Inventory）系统知识--两层盘点引擎、凭证状态机、重盘流程与触发判定、两套容差组、多次盘点版本追踪、配置点。涉及盘点/重盘/容差/Cycle Counting/零盘时使用。
---

# EWM Physical Inventory（盘点）

本 skill 编码了经 MCP 实测（2026-08-21）的 EWM 盘点系统知识。完整内容见 reference 文件 **[[ewm-physical-inventory.md]]**（`references/ewm-physical-inventory.md`，相对本 skill 目录）。本 skill 是其入口指针，触发场景下先读 reference 再作答。

EWM 盘点分两层：核心层 LIME（`/LIME/PI_CORE`）管凭证存储/状态机/核心逻辑，EWM 应用层（`/SCWM/PI_APPL`）封装 UI/容差检查/监控。重盘由**容差检查**驱动，触发判定依据是按**用户**分配的「重盘容差组」。全部表/函数/事务码/域固定值经 MCP 实测确认。

## 什么时候用这个 skill

- 用户问盘点（Physical Inventory）流程、盘点凭证、盘点状态
- 用户问重盘（Recount）流程、重盘触发条件、重盘与三盘的关系
- 用户问盘点容差（Tolerance）、容差组、为什么触发重盘
- 用户问 Cycle Counting（周期盘点 CC）/ 自动盘点
- 用户问盘点差异过账、零盘（Zero Count）
- 涉及 `/LIME/PI_DOC_IT`、`/LIME/PI_DOC_TB`、`/LIME/PICUST_TRE`、`/LIME/PICUST_RUS`、`/SCWM/PI_UI_TOLERANCE_CHECK` 等对象的语义
- 涉及盘点状态 `COUN` / `RECO` / `POST` 的流转

## 核心要点

### 一、状态机（域 `/LIME/PI_STATUS`，6 值实测）
`INAC` -> `ACTI` -> `COUN` -> `RECO` -> `POST`（`DELE` 为删除标记支路）。重盘将 `COUN` 转 `RECO`。

### 二、重盘触发判定（核心）
两套独立容差组（实测）：
- **重盘容差组** `/LIME/PICUST_TRE` + 用户分配 `/LIME/PICUST_RUS` -> 决定**是否触发重盘**
- **过账差异容差组** `/LIME/PICUST_TOL` + 用户分配 `/LIME/PICUST_USE` -> 决定**差异能否直接过账**

容差组按**用户**（重盘容差组）/ **用户 + 盘点区域**（过账差异容差组）分配（非按凭证/库位）。FM `/SCWM/PI_UI_TOLERANCE_CHECK` 在录入盘点结果时比对盘点数与账面数，差异超出该用户重盘容差组即触发重盘。EWM 层另附加价值容差与告警。

### 三、多次盘点版本追踪（实测数据模型）
重盘不覆盖原记录，而是新增行：`CHANGE_SEQ`（变更序号）递增，重盘行类型 `CC`（Count Item Change），数量状态 `MU`/`MC`。初盘为 `C`/`CO`。无次数硬上限，以最新 `CHANGE_SEQ` 为准过账。

### 四、触发方式
手动（事务 `/SCWM/PI`、Count Monitor `/SCWM/PI_COUNTMON`、Difference Monitor `/SCWM/PI_DIFFMON`）+ 自动（容差检查超限自动转 `RECO`；自动盘点文档类型 EL/ES/PL）。

## 守则

- 表 / 函数 / 事务码 / 域固定值为**实测事实**，照写无需重复验证；reference 未覆盖的新对象，先用 MCP 验证再报。
- 容差检查的具体判定顺序、状态自动转换时机为**基于 DDIC 语义的推断**，未做断点级运行时验证，回答时按 agent md 的 Truthfulness Rule 分开标注。
- 配置点具体 SPRO 路径因版本/实例而异，建议 SPRO 内以 "Physical Inventory" 搜索或经事务码 `/SCWM/PICUST_AR` 等进入，不凭记忆给路径名。
