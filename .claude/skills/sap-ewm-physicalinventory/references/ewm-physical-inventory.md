---
name: ewm-physical-inventory
description: 经 MCP 实测（2026-08-21）的 SAP EWM 盘点（Physical Inventory）系统知识--两层盘点引擎、凭证数据模型、状态机、重盘流程与触发判定、两套容差组、多次盘点版本追踪、配置点与查询入口。对象名均经实测确认存在。
---

# EWM Physical Inventory（盘点）

本文编码 EWM 盘点系统知识。所列表 / 函数 / 事务码 / 域固定值均经 MCP（`GetTable` / `GetTableContents` / `SearchObject` / `GetTransaction` / `GetTypeInfo`）于 2026-08-21 实测确认存在。流程描述基于已验证的 DDIC 结构与域值进行业务语义解读，其中**推断**部分（容差检查判定顺序、状态自动转换时机、视图分工）已明确标注，未做断点级运行时验证。

## 一、两层盘点引擎（实测）

EWM 盘点分两层：

| 层 | 包 | 职责 |
|---|---|---|
| 核心层 LIME（Lower Inventory Management Engine） | `/LIME/PI_CORE` | 盘点凭证存储、状态机、核心业务逻辑（创建/盘点/重盘/过账/读取） |
| EWM 应用层 | `/SCWM/PI_APPL` | 在 LIME 之上封装 EWM 专用 UI、容差检查、监控、打印等 |

重盘函数在两层都存在（实测）：
- 核心层：FM `/LIME/PI_DOCUMENT_RECOUNT`（描述 "Recount Physical Inventory Document"）
- EWM 层：FM `/SCWM/PI_CALL_DOCUMENT_RECOUNT`（同描述，调用核心层）
- 监控层：FM `/SCWM/PI_DOC_MTH_RECOUNT`（同描述，用于监控查询场景）

## 二、盘点凭证数据模型（实测）

盘点凭证为「项目表 + 数量表 + 序列号表」三表联动，通过 `CHANGE_SEQ`（变更序号）实现多次盘点的版本追踪。

### 2.1 项目表 `/LIME/PI_DOC_IT`（实测结构）

键字段（复合主键）：
- `GUID_DOC`（凭证 GUID）
- `ITEM_NO`（项目号）
- `LINE_IDX`（行索引）
- **`CHANGE_SEQ`（变更序号）** ← 关键：每次重盘递增，保留历史版本
- `ITEM_TYPE`（项目类型，域 `/LIME/PI_LINE_TYPE`）

业务字段：
- **`DOC_STATUS`（域 `/LIME/PI_STATUS`）** ← 项目级状态
- `COUNT_DATE` / `COUNT_USER`（盘点日期 / 人员）
- `COUNT_REFERENCE`（盘点参考）
- `BLOCK_IND`（库存冻结指示）
- `FREEZE_IND`（账面库存冻结指示）
- `DIF_DIRECTION`（差异方向）

### 2.2 数量表 `/LIME/PI_DOC_TB`（实测结构）

键字段（复合主键）：
- `GUID_DOC` / `ITEM_NO` / `LINE_IDX` / `CHANGE_SEQ` / `ITEM_TYPE`（与项目表对齐）
- **`QAN_DOC_STATUS`（域 `/LIME/PI_QAN_DOC_STATUS`）** ← 数量级状态，作为键的一部分
- `QUAN_SEQ` / `UNIT`

业务字段：
- `QUANTITY` / `ENTERED_QUANTITY` / `ENTERED_UNIT`
- **`IND_ZERO_COUNT`（域 `/LIME/PI_ZERO_COUNT_INDICATOR`，"Zero Count Executed"）** ← 零盘指示符
- `IND_NOT_COUNT`（未盘指示符）

> **关键洞察**：`CHANGE_SEQ` + `QAN_DOC_STATUS` 作为复合键，说明每次重盘 / 多次盘点**不是覆盖原记录，而是新增一条数量记录**（新状态、新变更序号），原始盘点记录保留。这正是"重盘可追溯"的数据基础。

### 2.3 文档类型表 `/LIME/PI_DOCTYPE`（实测数据）

| DOC_TYPE | CATEGORY | IND_AUTO | IND_PERIODIC | PI_CHECK | 业务解读 |
|---|---|---|---|---|---|
| AL | L | – | – | – | 库位盘点（非自动） |
| AS | O | – | – | – | 对象盘点（非自动） |
| **CC** | O | – | **X** | – | **周期盘点（Cycle Counting）** |
| **EL** | L | **X** | – | – | **自动库位盘点** |
| **ES** | O | **X** | – | – | **自动对象盘点** |
| HL | L | – | – | – | 库位盘点（另一类） |
| HS | O | – | – | – | 对象盘点（另一类） |
| ML | L | – | **X** | – | 周期库位盘点 |
| NL | L | – | – | **X** | 库位盘点（带检查类别） |
| **PL** | L | **X** | – | – | **自动库位盘点（另一类）** |

> `IND_AUTO = X` 表示该盘点类型可由系统在货物移动等业务过程中自动触发；`IND_PERIODIC = X` 表示周期性盘点。

## 三、状态体系（全部经 DD07T 实测确认）

### 3.1 项目级状态 `/LIME/PI_STATUS`（6 个固定值）

| 状态码 | 含义 | 在重盘流程中的位置 |
|---|---|---|
| `INAC` | Inactive（未激活） | 凭证创建后、激活前 |
| `ACTI` | Active（已激活） | 凭证激活，可开始盘点 |
| `COUN` | Counted（已盘点） | 初次盘点完成 |
| **`RECO`** | **Recounted（已重盘）** | **重盘完成后的状态** |
| `DELE` | Deletion Indicated（已标记删除） | 凭证被标记删除 |
| `POST` | Posted（已过账） | 差异已过账，盘点闭环 |

### 3.2 数量级状态 `/LIME/PI_QAN_DOC_STATUS`（11 个固定值）

| 状态码 | 含义 | 与重盘的关系 |
|---|---|---|
| `CO` | Counted Quantity（盘点数量） | 初次盘点的数量行 |
| `BO` | Book Inventory（账面库存） | 系统账面数量 |
| `MU` | **Multiple Count（多次盘点）** | **重盘 / 多次盘点的数量行** |
| `CH` | **Count Change（盘点变更）** | **盘点数量的变更记录** |
| `MC` | **Multiple Count, Changed Entry（多次盘点-已变更条目）** | **重盘后又被修改的数量行** |
| `PR` | Default Line（默认行） | 建议行 |
| `PA` | Param Entry（参数录入） | 参数行 |
| `DI` | Differences（差异） | 差异数量行 |
| `PD` | Differences Default Line（差异默认行） | 默认差异行 |
| `MT` | MTQ Quantities | MTQ 数量 |
| `BC` | Book Inventory Change（账面库存变更） | 账面库存的变更行 |

### 3.3 行类型 `/LIME/PI_LINE_TYPE`（11 个固定值）

| 码 | 含义 | 与重盘的关系 |
|---|---|---|
| `O` | Object-Specific Item | 对象级项目 |
| `L` | Location-Specific Item | 库位级项目 |
| `P` | Default (Suggested) Item | 建议（默认）项目 |
| `C` | Count Item | 盘点项目 |
| `D` | Difference Item | 差异项目 |
| `B` | Book Inventory Line | 账面库存行 |
| `E` | Existence Items | 存在性项目 |
| `PD` | Default Difference Item | 默认差异项目 |
| **`CC`** | **Count Item Change（盘点项目变更）** | **重盘产生的新盘点行** |
| `CD` | Difference Item Change | 差异项目变更 |
| `CB` | Book Inventory Change | 账面库存变更 |

> `CC`（Count Item Change）行类型 + `MU`/`CH`/`MC`（数量级状态）+ `CHANGE_SEQ`（变更序号）三者配合，完整记录"第几次盘点、每次盘了什么、是否被修改过"的全链路。

## 四、重盘整体流程（从触发到差异过账）

> 流程描述基于已验证的状态码、表结构、函数模块和行类型，通过业务语义串联。前后台程序交互细节未做断点级验证，推断部分已标注。

### 阶段 0：前置--盘点凭证创建与激活

| 步骤 | 动作 | 涉及对象（实测） | 状态变化 |
|---|---|---|---|
| 1 | 创建盘点凭证 | 事务码 `/SCWM/PI_DOC_CREATE`；FM `/LIME/PI_DOCUMENT_CREATE`、`/SCWM/PI_CALL_DOCUMENT_CREATE`；程序 `/SCWM/PI_DOCUMENT_CREATE`；编号对象 `/SCWM/PIDO` | `INAC`（未激活）或直接 `ACTI`（取决于创建参数，见数据元素 `/SCWM/PI_DE_ACTIVE_UI` "Create Active or Inactive Physical Inventory Document"） |
| 2 | 激活凭证（若以未激活创建） | FM `/LIME/PI_CHANGE_CREATE_STATUS`、`/SCWM/PI_CHANGE_CREATE_STATUS` | `INAC` -> `ACTI` |

凭证创建时，`/LIME/PI_DOC_IT` 写入项目行（行类型 `O`/`L`/`P`），`/LIME/PI_DOC_TB` 写入账面库存行（数量状态 `BO`）。按配置可能冻结库存（`BLOCK_IND`）或冻结账面库存（`FREEZE_IND`）。

### 阶段 1：初次盘点

| 步骤 | 动作 | 涉及对象（实测） | 状态变化 |
|---|---|---|---|
| 3 | 录入盘点结果 | 事务码 `/SCWM/PI_COUNT`（单条）或 `/SCWM/PI_COUNTLIST`（列表）；FM `/LIME/PI_DOCUMENT_COUNT`、`/SCWM/PI_CALL_DOCUMENT_COUNT` | 项目状态 `ACTI` -> `COUN`；数量表新增盘点数量行（数量状态 `CO`） |
| 4 | **容差检查**（录入时自动执行） | FM `/SCWM/PI_UI_TOLERANCE_CHECK`（"Tolerance Check of Specified Count Quantity"） | 见第五节 |

容差检查通过（差异在容差内）-> 进差异过账路径（阶段 4）；不通过（差异超容差）-> 触发重盘（阶段 2）。

### 阶段 2：触发重盘 ← 核心

| 步骤 | 动作 | 涉及对象（实测） | 状态变化 |
|---|---|---|---|
| 5 | 触发重盘 | FM `/LIME/PI_DOCUMENT_RECOUNT`（核心）、`/SCWM/PI_CALL_DOCUMENT_RECOUNT`（EWM）、`/SCWM/PI_DOC_MTH_RECOUNT`（监控入口） | 项目状态 `COUN` -> **`RECO`**；`CHANGE_SEQ` 递增；数量表新增重盘数量行（行类型 `CC`「Count Item Change」，数量状态 `MU`「Multiple Count」） |

重盘核心机制：
- **不删除原盘点记录**：原 `COUN` 状态数量行保留，`CHANGE_SEQ` 不变
- **新增重盘行**：`CHANGE_SEQ` 递增，行类型 `CC`，数量状态 `MU`
- 重盘结果又被修改 -> 数量状态变 `MC`（Multiple Count, Changed Entry）
- 原始盘点行被"冻结"，以重盘结果为准

### 阶段 3：重盘结果录入

| 步骤 | 动作 | 涉及对象 | 状态变化 |
|---|---|---|---|
| 6 | 录入重盘结果 | 同阶段 1 录入事务码 `/SCWM/PI_COUNT` / `/SCWM/PI_COUNTLIST`；FM `/LIME/PI_DOCUMENT_COUNT` | 重盘数量行填入实际数量；`IND_ZERO_COUNT` 若为零盘则置位 |
| 7 | 再次容差检查 | FM `/SCWM/PI_UI_TOLERANCE_CHECK` | 仍超容差可再次重盘（回到步骤 5，`CHANGE_SEQ` 再递增）= "三盘" |

### 阶段 4：差异确认与过账（盘点闭环）

| 步骤 | 动作 | 涉及对象（实测） | 状态变化 |
|---|---|---|---|
| 8 | 确认差异 | 差异行类型 `D`（Difference Item）/ `PD`（Default Difference Item）；数量状态 `DI` | 差异行生成 |
| 9 | 过账差异 | FM `/LIME/PI_DOCUMENT_POST`、`/SCWM/PI_CALL_DOCUMENT_POST`、`/SCWM/PI_DIFFERENCE_POST`（"Update Physical Inventory Difference"） | 项目状态 `RECO`（或 `COUN`）-> **`POST`** |
| 10 | 盘点完成检查 | FM `/SCWM/PI_ADMI_CHECK_COMPLETE`（"Checks Whether Inventory Is Complete"）、`/SCWM/PI_ADMI_SET_COMPLETE` | 盘点闭环 |

### 完整状态流转

```
INAC ──激活──▶ ACTI ──初次盘点──▶ COUN ──容差超限,触发重盘──▶ RECO ──差异过账──▶ POST
                                   │                                                    ▲
                                   └──容差通过,直接过账──────────────────────────────────┘
```

## 五、触发重盘的判定依据（核心）

系统存在**两套独立的容差体系**（实测）：一套管"是否需要重盘"，一套管"差异能否直接过账"。

### 5.1 两套容差组（实测表结构）

| 容差组类型 | 定义表（实测） | 用户分配表（实测） | IMG 节点（实测） |
|---|---|---|---|
| **重盘容差组** | `/LIME/PICUST_TRE`（"Definition of Tolerance Group 'Recount'"） | `/LIME/PICUST_RUS`（"Assignment of User to Tolerance Group for Recount"） | IMG 对象 `/LIME/PICUST_TRE`（"Define Tolerance Group for Recounting"） |
| **过账差异容差组** | `/LIME/PICUST_TOL`（"Definition of Tolerance Group 'Post Differences'"） | `/LIME/PICUST_USE`（"Assignment of User to Tolerance Group"） | – |

### 5.2 重盘容差组表 `/LIME/PICUST_TRE` 结构（实测）

```
键字段：
  MANDT            (集团)
  PI_AREAD          (盘点区域)            -> 域 /LIME/PI_DE_PI_AREAD
  PI_TOL_GROUP_REC  (重盘容差组)          -> 域 /LIME/PI_TOLERANCE_GROUP_REC
业务字段：
  PI_QUAN_TOLERANC  (数量容差)            -> 域 /LIME/PI_QUAN_TOLERANCE
  PI_NO_TOLERANCE   (无容差 / 下限容差)    -> 域 /LIME/PI_NO_TOLERANCE
```

### 5.3 过账差异容差组表 `/LIME/PICUST_TOL` 结构（实测）

```
键字段：
  MANDT / PI_AREAD / PI_TOL_GROUP
业务字段：
  PI_QUAN_TOLERANC  (数量容差)
  PI_NO_TOLERANCE   (无容差 / 下限容差)
```

### 5.4 EWM 层容差值表（实测）

EWM 层在 LIME 之上增加**价值容差**与**告警**：

| 表（实测） | 描述 | 关键字段 |
|---|---|---|
| `/SCWM/PICUSTTOLR` | "Tolerance Vals Allowed for Each PI Area and Tolerance Group" | `PI_QUAN_TOLERANC`、`PI_NO_TOLERANCE`、`VALUE_TOLERANCE`（价值容差，带货币）、`NO_VAL_TOLERANCE`（"Do Not Execute Value-Based Tolerance Check"） |
| `/SCWM/PICUST_TOL` | 同上（另一视图） | 同上 + **`SEND_ALERT`**（发送告警） |
| `/SCWM/PICUST_REC` | "Assignment of Phys. Inv. Area, Tolerance Grp and Tolerances" | 同 PICUSTTOLR 字段集 |

### 5.5 用户到容差组的分配（实测）

| 表 | 描述 | 键 | 字段 |
|---|---|---|---|
| `/LIME/PICUST_RUS` | "Assignment of User to Tolerance Group for Recount" | `MANDT` + `USERID` | `PI_TOL_GROUP_REC`（该用户对应的重盘容差组） |
| `/LIME/PICUST_USE` | "Assignment of User to Tolerance Group"（过账差异用，**同时持有重盘容差组分配**） | `MANDT` + `USERID` + **`PI_AREA`**（盘点区域） | `PI_TOL_GROUP`（过账容差组）**和 `PI_TOL_GROUP_REC`（重盘容差组）** |

> **关键设计**：两套容差组的分配粒度不同（2026-08-21 在 TL7 client 011 经 MCP `GetTable` 实测）：
> - **重盘容差组**（`/LIME/PICUST_RUS`）按**用户**分配（键 `MANDT` + `USERID`），与凭证/库位无关；
> - **过账差异容差组**（`/LIME/PICUST_USE`）按**用户 + 盘点区域**分配（键 `MANDT` + `USERID` + `PI_AREA`），同一用户在不同盘点区域可有不同容差等级。
>
> `/LIME/PICUST_USE` 一张表同时持有 `PI_TOL_GROUP`（过账容差组）与 `PI_TOL_GROUP_REC`（重盘容差组）双重分配。不同仓管员可有不同容差等级--资深员工容差大（允许直接过账差异），新员工容差小（更易触发重盘）。

### 5.6 判定逻辑（基于已验证对象的业务语义推断，未断点级验证）

容差检查 FM `/SCWM/PI_UI_TOLERANCE_CHECK`（"Tolerance Check of Specified Count Quantity"）在录入盘点结果时执行，判定逻辑（推断）如下：

```
录入盘点数量 (COUNT_QUAN)
        │
        ▼
  取账面库存数量 (BOOK_QUAN, 来自数量状态 BO 的行)
        │
        ▼
  计算差异 = |COUNT_QUAN - BOOK_QUAN|
        │
        ├──▶ 查用户对应的【重盘容差组】(/LIME/PICUST_RUS -> /LIME/PICUST_TRE)
        │         取 PI_QUAN_TOLERANC (数量容差) / PI_NO_TOLERANCE (下限)
        │    │
        │    ├── 差异 > 重盘容差  ──▶ 触发重盘 (状态 COUN -> RECO)
        │    │
        │    └── 差异 ≤ 重盘容差  ──▶ 不触发重盘，进入过账判定 ↓
        │
        ├──▶ 查用户对应的【过账差异容差组】(/LIME/PICUST_USE -> /LIME/PICUST_TOL)
        │         取 PI_QUAN_TOLERANC / PI_NO_TOLERANCE
        │    │
        │    ├── 差异 > 过账容差  ──▶ 不允许直接过账，仍需重盘或人工干预
        │    │
        │    └── 差异 ≤ 过账容差  ──▶ 允许直接过账差异 (状态 -> POST)
        │
        └──▶ (EWM 层) 价值容差检查 (/SCWM/PICUST_TOL)
                  VALUE_TOLERANCE (价值容差) / NO_VAL_TOLERANCE (跳过价值检查)
             └── 若超出价值容差且 SEND_ALERT = X ──▶ 发送告警
```

### 5.7 零盘的特殊处理

零盘（库位实际为空但账面有库存，或反过来）是重要重盘触发场景：
- 数量表 `/LIME/PI_DOC_TB` 有 `IND_ZERO_COUNT`（域 `/LIME/PI_ZERO_COUNT_INDICATOR`，"Zero Count Executed"，CHAR 1）
- UI 层数据元素 `/SCWM/PI_DE_IND_ZERO_COUNT`（"Physical Inventory Indicator: Zero Count Executed"）
- 零盘通常被视为高风险差异，多数场景会自动触发重盘要求

### 5.8 盘点区域级低库存检查（独立容差层，实测）

除上述「容差组级别」的检查（`/LIME/PICUST_TRE` / `/LIME/PICUST_TOL`）外，系统在**盘点区域级别**还设有一层独立的低库存检查机制，承载于 `/LIME/PICUST_ARE`（LIME 层盘点区域设置）。

> 2026-08-21 在 TL7 client 011 经 MCP `GetTable` 读 `/LIME/PICUST_ARE`（实测 141 行全量，键含 `PI_AREAD` 盘点区域），AU01 仓库三个区域 AU01_PI_1 / AU01_PI_2 / AU01_PI_3 取值一致：

| 字段 | 含义 | AU01 实测值 |
|---|---|---|
| `LOWCHK_INV` | 低库存盘点指示符（Low Stock Check Inventory Indicator） | X |
| `LOWCHECK` | 低库存检查（Low Stock Check） | X |
| `BOOK_AFTER_COUNT` | 盘点后过账（Book Inventory After Count） | X |
| `LOWCHK_TOL` | 低库存容差检查（Low Stock Check Tolerance） | X |
| `HU_CNT_MODE` | HU 盘点模式（HU Counting Mode） | 2 |

要点：
1. 这是**盘点区域级别**的容差检查机制，与第五节所述「容差组级别」的检查（`PICUST_TRE` / `PICUST_TOL`）是**独立的两层**。
2. `LOWCHECK = X` + `LOWCHK_TOL = X` 表示低库存检查及低库存容差检查在盘点区域级激活；`BOOK_AFTER_COUNT = X` 表示盘点后过账激活。
3. 该层按盘点区域配置，不随用户/容差组变化。

## 六、触发方式与触发人

### 6.1 手动触发重盘

| 方式 | 涉及对象（实测） | 说明 |
|---|---|---|
| 通过主事务码 | 事务码 `/SCWM/PI`（"Physical Inventory"，实测确认属 SCM-EWM-PI 应用） | 在盘点监控 / 处理界面中对已盘点（`COUN`）的凭证项目执行重盘 |
| 通过监控事务 | 函数组 `/SCWM/PI_COUNTMON`（Count Monitor，含按天分组查询 `..._DOC_0`~`..._DOC_9`）和 `/SCWM/PI_DIFFMON`（Difference Monitor） | 监控中发现差异超容差的项目，手动触发重盘 |
| 通过函数 / API | `/SCWM/PI_CALL_DOCUMENT_RECOUNT` 或 `/LIME/PI_DOCUMENT_RECOUNT` | 程序化触发 |

### 6.2 自动触发重盘

| 方式 | 涉及对象（实测） | 说明 |
|---|---|---|
| 容差检查时自动 | FM `/SCWM/PI_UI_TOLERANCE_CHECK` | 录入盘点结果时，差异超出**重盘容差组**容差值，系统自动将项目状态置为 `RECO` 并创建重盘行 |
| 自动盘点场景 | 文档类型表 `/LIME/PI_DOCTYPE` 中 `IND_AUTO = X` 的类型（EL/ES/PL） | 自动盘点在货物移动时触发，其重盘同样由容差检查驱动 |

### 6.3 谁可以触发

- **权限控制**：授权对象 `/SCWM/PIPR`（"EWM Physical Inventory"，实测确认）控制盘点处理权限；`/SCWM/PIBK`（"EWM PI book Inventory Change"）控制账面库存变更权限
- **容差组决定权**：用户被分配到哪个重盘容差组（`/LIME/PICUST_RUS`），决定该用户录入的盘点结果在多大差异范围内可"不重盘直接过账"

## 七、重盘与初盘、三盘等多次盘点的关系

基于已验证数据模型（`CHANGE_SEQ` + `QAN_DOC_STATUS` + 行类型 `CC`），多次盘点机制：

| 盘点次数 | CHANGE_SEQ | 行类型 | 数量级状态 | 项目状态 | 说明 |
|---|---|---|---|---|---|
| 初次盘点 | 1 | `C`（Count Item） | `CO`（Counted Quantity） | `COUN` | 第一次录入 |
| 第一次重盘 | 2 | `CC`（Count Item Change） | `MU`（Multiple Count） | `RECO` | 第二次录入，原记录保留 |
| 第二次重盘（三盘） | 3 | `CC` | `MU` | `RECO` | 第三次录入 |
| 重盘后又被修改 | n | `CC` | `MC`（Multiple Count, Changed Entry） | `RECO` | 重盘结果被修改 |

关键关系：
1. **所有历史保留**：每次盘点新增行（`CHANGE_SEQ` 递增），不覆盖。可完整追溯"第几次盘了多少、谁盘的、何时盘的"
2. **以最新为准**：过账时以最大 `CHANGE_SEQ` 的数量行为准计算差异
3. **次数无硬上限**：`CHANGE_SEQ` 为 `SYTABIX` 类型（整数），无域级上限。实际重盘次数由业务流程和容差配置决定--差异仍超容差即可继续重盘
4. **零盘可参与重盘**：每次盘点行的 `IND_ZERO_COUNT` 独立标记，可追溯哪次是零盘
5. **最终差异基于最终盘点结果**：差异行类型 `D`（Difference Item）和 `DI`（Differences 数量状态）在最终盘点结果确认后生成

## 八、配置点总览（IMG 结构，实测）

| 配置内容 | IMG 对象 / 表 | 描述 |
|---|---|---|
| 盘点区域维护 | 事务码 `/SCWM/PICUST_AR`；表 `/LIME/PICUST_ARE`、`/SCWM/PICUST_ARE` | 维护盘点区域及其设置；`/LIME/PICUST_ARE` 另承载区域级低库存检查（`LOWCHECK` / `LOWCHK_INV` / `LOWCHK_TOL`）、盘点后过账（`BOOK_AFTER_COUNT`）、HU 盘点模式（`HU_CNT_MODE`）等设置（见 5.8） |
| **重盘容差组定义** | IMG `/LIME/PICUST_TRE`（"Define Tolerance Group for Recounting"）；表 `/LIME/PICUST_TRE` | 定义每个盘点区域的重盘容差组和数量容差 |
| 过账差异容差组定义 | 表 `/LIME/PICUST_TOL` | 定义过账差异容差组 |
| 容差值（含价值容差） | 表 `/SCWM/PICUSTTOLR`、`/SCWM/PICUST_TOL`、`/SCWM/PICUST_REC` | 每个区域 + 容差组的数量 / 价值容差值 |
| **用户-重盘容差组分配** | 表 `/LIME/PICUST_RUS` | 将用户分配到重盘容差组 |
| 用户-过账容差组分配 | 表 `/LIME/PICUST_USE` | 将用户分配到过账差异容差组 |
| 盘点程序 / 文档类型 | 表 `/LIME/PI_DOCTYPE`；IMG `/LIME/PICUST_DTY` | 定义盘点程序及其属性（自动 / 周期 / 检查） |
| 盘点原因 | 表 `/SCWM/PICUST_REA`、`/LIME/PICUST_REA`；IMG `/SCWM/PICUST_REA` | 定义盘点原因代码 |
| 差异原因 | 表 `/SCWM/PICUST_REB` | 定义差异原因代码 |
| 差异分析器设置 | 表 `/SCWM/PICUST_MON` | 差异分析器配置 |
| 盘点优先级 | 表 `/SCWM/PICUST_PRI`；IMG `/SCWM/PICUST_PRI` | 定义盘点优先级 |
| 凭证编号范围 | IMG `/SCWM/PIDO`；编号对象 `/SCWM/PIDO` | 盘点凭证编号范围 |
| 周期盘点 ABC 指示符 | BAdI `/SCWM/PI_ABC_IND`（"Setting the ABC Indicators for Cycle Counting"） | 设置 ABC 分类 |
| 库位检查间隔 | 数据元素 `/SCWM/PI_DE_MRL_INT`（"Physical Inventory Interval of Stor. Bin Check"）、`/SCWM/PI_DE_MRL_BUF_INT`（"Buffer Time"） | 库位检查的周期和缓冲时间 |

> IMG 顶层结构节点为 `/SCWM/PI`（SHI3 类型，描述 "Physical Inventory"，属包 `/SCWM/IMG`），上述各配置点均挂在此节点下。具体 SPRO 路径因系统版本和实例而异，建议在 SPRO 中以 "Physical Inventory" 为关键字搜索，或直接经事务码 `/SCWM/PICUST_AR` 等进入对应配置视图。

## 九、总结

| 问题 | 核心答案 |
|---|---|
| **重盘流程** | `INAC`->`ACTI`->`COUN`->`RECO`->`POST`。录入盘点->容差检查->超限则状态转 `RECO` 且 `CHANGE_SEQ` 递增新增重盘行->录入重盘结果->（可再重盘=三盘）->差异确认->过账 `POST`。所有历史版本保留在 `/LIME/PI_DOC_IT` / `/LIME/PI_DOC_TB`。 |
| **触发重盘的判定依据** | **重盘容差组**（`/LIME/PICUST_TRE`）定义的数量容差。容差检查 FM `/SCWM/PI_UI_TOLERANCE_CHECK` 在录入盘点结果时比较盘点数与账面数，差异超出该用户所分配的重盘容差组（`/LIME/PICUST_RUS`）的容差值即触发重盘。另有独立的"过账差异容差组"控制能否跳过重盘直接过账。EWM 层附加价值容差和告警。 |
| **触发方式** | 手动（事务 `/SCWM/PI`、Count Monitor `/SCWM/PI_COUNTMON`、Difference Monitor `/SCWM/PI_DIFFMON`）和自动（容差检查超限自动转 `RECO`；自动盘点文档类型 EL/ES/PL）。 |
| **多次盘点关系** | 通过 `CHANGE_SEQ` 递增 + 行类型 `CC`（Count Item Change）+ 数量状态 `MU`/`MC` 实现版本化追踪，初盘为 `C`/`CO`，重盘为 `CC`/`MU`，无硬性次数上限，以最新 `CHANGE_SEQ` 为准过账。 |

---

**事实来源**：本文表 / 函数 / 事务码 / 域固定值经 MCP 实测（2026-08-21）确认存在。容差检查判定顺序、状态自动转换时机、视图分工为基于已验证 DDIC 结构与域值的业务语义推断，未做断点级运行时验证。help.sap.com 官方文档因 SPA 单页应用未被 WebFetch 抓取正文，未能交叉印证流程细节。
