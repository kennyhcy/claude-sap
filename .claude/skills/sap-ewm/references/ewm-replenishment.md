---
name: ewm-replenishment
description: 经 MCP 实测(2026-08-05)的 SAP EWM 补货(Replenishment)系统知识——补货表谱、6 表决定链路、固定仓位补货数据链路、CN01 现状、查询陷阱。
---

# EWM Replenishment

补货由专属表谱 `/SCWM/TREPA` / `/SCWM/TREPLTM` + 主数据 `/SCWM/BINMAT` / `/SAPAPO/MATLWHST` 共同决定，**不挂** `/SCWM/T331`(近拣货位控制)或 `/SCWM/T331C`。全部经 MCP `GetTable`/`SearchObject` 实测确认。

## 一、补货相关表/视图清单（实测存在）

| 表/视图 | 类型 | 描述 | CN01 数据 |
|---|---|---|---|
| `/SCWM/TREPA` | 透明表 | 补货策略分配到存储类型(Assign Replenishment Strategies to Storage Type) | 有(6条) |
| `/SCWM/V_TREPA` | 视图 | 在存储类型中激活补货策略(Activate Replenishment Strategies in Storage Types) | 有(底层 TREPA) |
| `/SCWM/TREPLTM` | 透明表 | 补货执行时间控制(Control Execution Time for Replenishment)，字段 `rpltm`/`time_to_exec`/`unit_t` | 有(1条) |
| `/SCWM/T333` | 透明表 | 仓库过程类型(Warehouse Process Type)；补货 WPT 以 `doctype='SRPL'` 标识，`no_autrepl` 控制自动补货开关 | 有(3010 等) |
| `/SCWM/V_T333RPL` | 视图 | 补货仓库请求的单据/项目类型(Document/Item Type for Replenishment Warehouse Request) | 有(底层 T333) |
| `/SCWM/BINMAT` | 透明表 | 固定仓位-物料分配(Assignment Table for Fixed Bins - Product)，含 `maxqty`/`minqty` 等仓位级库存阈值 | 有(PF01 多条) |
| `/SAPAPO/MATLWHST` | 透明表 | 物料-存储类型级补货参数(Location Product for Location Whse and Subloc. Storage Type)，含 `repqty`/`minqty`/`maxqty` | 有(抽样 PO01) |
| `/SCWM/T301` | 透明表 | 存储类型(Storage Types)，含 `fixbin` 固定仓位标识 | 有(PF01) |
| `/SCWM/TMATWH` | **不存在** | (前番臆测，实测不存在；物料仓储主数据真实归属见 `BINMAT`/`MATLWHST`) | — |

## 二、补货由 6 张表共同决定

- 配置层 4 张：`TREPA`(策略-WPT 分配)、`TREPLTM`(执行时间)、`T333`(WPT 定义/SRPL 单据类型)、`T301`(存储类型 `fixbin` 标识)
- 主数据层 2 张：`BINMAT`(物料-固定仓位分配 + 仓位级阈值)、`MATLWHST`(物料-存储类型级补货参数 `repqty`)

## 三、固定仓位补货完整数据链路（CN01 实测）

`T301`(PF01, `fixbin='X'`) → `BINMAT`(物料分配到固定仓位,含 `maxqty`/`minqty`) → `TREPA`(绑定 PF01 策略→WPT 如 3010) → `TREPLTM`(定义执行时间) → `T333`(该 WPT `trart=3`/`doctype=SRPL`) → 库存跌破阈值时生成 SRPL 补货 WT，从源存储类型搬到 PF01 固定仓位。

## 四、两视图分工（推断：视图字段 ADT 读不到，以下层表推断）

- `V_TREPA`：策略激活与 WPT 路由(何时何地补)
- `V_T333RPL`：补货单据类型定义(补货单据长什么样)

## 五、CN01 现状（实测）

- 补货骨架完整：`TREPA` 6 条策略、`TREPLTM` 执行时间、`T333` WPT 3010/3011/3014/3015 俱全。
- `BINMAT` 有大量 PF01 固定仓位分配，但 `rmmqty_fix` 全空（改用 `maxqty`-`minqty` 算补货量）。
- `MATLWHST` 抽样(PO01)补货字段全空；待精确查 CN01。

## 六、查询陷阱（实测）

- **`MATLWHST` 无 `lgnum` 字段**：靠 `scuguid`(GUID) 关联仓库。REST 字符串等值查 `scuguid` 报 `CX_SY_OPEN_SQL_DATA_ERROR`。查指定仓库需经 `/SAPAPO/LOC`(`locid`→`lgnum`) 反查 GUID 后用 GUID 比较，或由 ABAPer 在 SE16N 查。
- **两视图 ADT 读不到字段**：`/SCWM/V_TREPA`、`/SCWM/V_T333RPL` 视图对象 ADT REST 返回"无法导入"(SWB_TOOL 025)，字段定义以下层透明表为准。
- **历史教训**：补货曾误判为挂 `/SCWM/T331` 上、或把 `/SCWM/T331C`(近拣货位控制表)当补货表——皆错。补货有专属表谱 `TREPA`/`TREPLTM` + 主数据 `BINMAT`/`MATLWHST`。

---

**事实来源**：本文事实来自 MCP 实测(2026-08-05)；视图字段、两视图分工为推断；`MATLWHST` 的 CN01 精确数据待 ABAPer 用 GUID 查证。
