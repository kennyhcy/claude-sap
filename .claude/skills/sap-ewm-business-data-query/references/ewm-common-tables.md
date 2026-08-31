---
name: ewm-common-tables
description: 经 MCP 实测确认存在的 SAP EWM 常用表(仓位/存储类型/WT/库存/资源/HU/交货单等)及表间关系。
---

经 MCP `GetTable`(读取到完整字段结构)或 `SearchObject`(DDIC 确认为透明表 TABL/DT)实测验证存在的 EWM 常用表:

**仓库基础配置**
- `/SCWM/T300` 仓库号定义;`/SCWM/T300T` 仓库号描述;`/SCWM/T300_MD` 仓库号↔业务伙伴分配
- `/SCWM/T301` 存储类型;`/SCWM/T301T` 存储类型描述
- `/SCWM/T302` 存储区(Storage Section,字段 `lgnum`/`lgtyp`/`lgber`/`aarea_plan`)
- `/SCWM/T303` 仓位类型(Storage Bin Type,字段 `lptyp`/`max_weight`/`max_volume`/`max_capa`/`max_length`/`width`/`height`)
- `/SCWM/LAGP` 仓位主数据 Storage Bins(核心!字段含 `lgnum`/`lgpla`/`lgtyp`/`lgber`/`lptyp`/`max_weight`/`volum`/`guid_loc`/`x_cord`/`y_cord`/`z_cord`/`aisle`/`stack`)。注意命名沿用 SAP 经典 WM 的 `LAGP`,不是 `TSTORAGE_BIN`。
- `/SCWM/TDOOR` 仓库门(字段 `lgnum`/`door`/`door_bin`/`load_dir`/`starea_def`/`yard_lgnum`)

**Warehouse Task / Warehouse Order**
- `/SCWM/ORDIM_O` 开放 WT(Warehouse Tasks Open,字段 `vltyp`/`vlpla`源 → `nltyp`/`nlpla`目标,`cat`,`nlenr`/`vlenr`)
- `/SCWM/ORDIM_C` 已确认 WT
- `/SCWM/ORDIM_E` WT 异常码;`/SCWM/ORDIM_H` HU 项移动 WT;`/SCWM/ORDIM_L` WT 日志;`/SCWM/ORDIM_OS`/`/SCWM/ORDIM_CS` 序列号项
- `/SCWM/T333` 仓库工序类型 Warehouse Process Type(字段 `lgnum`/`procty`/`trart`/`act_type`/`vltyp`/`nltyp`/`wcr`/`prces`)
- `/SCWM/WHO` 仓库订单， WO表。

**库存**
- `/SCWM/AQUA` 库存 Quant(字段 `lgnum`/`lgtyp`/`lgpla`/`rsrc`/`huident`/`cat`库存类别/`entitled`库存归属/`charg`批次/`quan`/`unit`/`vfdat` SLED/`wdatu`/`insptyp`检验ID类型/`inspid`检验ID/`skzsi`库存标识)。stock type 经 include `/SCWM/S_STOCK` 引入，`cat` 取值(如 `F2`=仓库非限制使用、`Q2`=质检、`B2`=冻结)定义见 `/SCWM/TCAT`。

**库存类别（Stock Type）配置**(EWM 术语 stock type 在 DDIC 层面叫 `cat`/stock category；位置无关码 `FF`=非限制使用/`QQ`=质检/`B`=冻结，对应仓位级 `F2`/`Q2`/`B2`)
- `/SCWM/TCAT` Stock Type Definition 核心(字段 `lgnum`/`cat`stock type code/`catgrpr`stock type group representative/`catgrpq`/`avlgrp`可用库存组/`catlocn`location-dependent 标志/`cat_role`stock type role)。注意表名是 `TCAT` 系列，**不是** `TSTOCKTYPE`/`T_STOCKTYPE`。
- `/SCWM/TCAT_TXT` Stock Type 描述(字段 `spras`/`lgnum`/`cat`/`cat_txt`)
- `/SCWM/TCATG` Stock Type Group 定义；`/SCWM/TCATGT` group 描述
- `/SCWM/TCATLOCN` Non-Location-Specific Stock Type(location-dependent 配置)；`/SCWM/TCATLOCNT` 描述
- `/SCWM/TSTOCK_DET` 库存确定(Stock Determination)配置表(注意不是 stock type)

**资源 / HU / 包装 / 运输单元**(均经 SearchObject 确认为透明表)
- `/SCWM/TRSRC_GRP` 资源组;`/SCWM/TRSRC_GRPT` 描述;`/SCWM/TRSRC_TYP` 资源类型;`/SCWM/TRSRC_TYPT` 描述;`/SCWM/TRSRC_PRN` 资源↔打印机
- `/SCWM/THUTYP` HU 类型;`/SCWM/THUTYPT` 描述;`/SCWM/THUTYPG` HU 类型组;`/SCWM/THUNR` HU 号码范围
- `/SCWM/TUNIT` 运输单元 Transportation Unit
- `/SCWM/TMATPP` 产品上架 Profile

**入站/出站交货单(Warehouse Request)— 物理表(全部 MCP 实测确认,透明表 TABL/DT)**
交货数据存储在 SCDL 框架的 DBAL 数据层(包 `/SCDL/DBAL_DB`),`/SCWM/DLV_*` 系列多为结构/表类型而非透明表。真实的交货物理表是以下 7 张(表名规则:`DB_PROCH`=header / `DB_PROCI`=item,后缀 `_I`=Inbound / `_O`=Outbound / `_P`=Production):
- `/SCDL/DB_PROCH_I` Inbound Delivery: Header(内向交货表头)
- `/SCDL/DB_PROCH_O` Outbound Delivery Order Header(外向交货单表头)
- `/SCDL/DB_PROCH_P` Production Material Request Header(生产领料单表头)
- `/SCDL/DB_PROCI_I` Inbound Delivery Item(内向交货行项目)
- `/SCDL/DB_PROCI_O` Outbound Delivery Order Item(外向交货单行项目)
- `/SCDL/DB_PROCI_P` Production Material Request Item(生产领料单行项目;含 `/SCWM/PSA` 字段)
- `/SCDL/DB_REFDOC` Reference(参考凭证/凭证流关联)

这些表字段均通过 include 引用(key include `..._key`,data include `..._data`),需展开 include 结构才能看到具体字段。日常查询也常用事务码 `/SCWM/PRDI`(入站维护)、`/SCWM/PRDO`(出站维护)或 `/SCWM/DELIVERY` 函数组。

**质量管理（QM）/ 检验凭证 / 检验对象类型 / Follow-up**
- `/SCWM/TWF_INSP` 检验凭证(Inspection Document)工作流持久化表。关键字段经 include `/SCWM/S_EXCEP_INSP` 引入: `skip`(skip lot 核心标志，类型 `qie_tv_skip`)、`insp_doc_number`检验凭证号、`auto_decided`自动决策标志、`deci_code_id`决策代码、`insp_valuation`/`dmod_valuation`/`prop_valuation`检验评估、`decided_on`决策日期、`qlevel_guid`质量水平、`lot_size`/`lot_unit`、`catlocn`stock category location-dependent、`qdoccat`/`qdocid`/`qitmid`(ERP↔EWM 链路)。持久化类 `/SCWM/CB_EXCEPTION_OBJ_INSP`。注意表名是 `TWF_INSP`，**不是** `T_INSP_DOC`/`T_INSP_ITEM`。
- `/SCWM/QIOT` Version-Dependent 检验对象类型(IOT)配置(字段 `version`/`iot`检验对象类型/`enabled`/`iot_guid`/`irule_res_ind`)
- `/SCWM/QIOTPRP` IOT 属性配置；`/SCWM/QIOTWM` 仓库级 IOT 配置；`/SCWM/QIOTWM_NIR` 无检验规则的检验计划设置
- `/SCWM/TQFU` Follow-Up Action 定义配置(字段 `lgnum`/`fup`follow-up action 代码/`iot`检验对象类型/`catlocn`/`procty`仓库过程类型/`exccode`异常代码/`dest_lgpla`目标仓位/`wt_ref_4_fup`)。执行逻辑在 FM `/SCWM/QFUP_PROCESS_RFC`(跑在 WMQF 队列)。注意表名是 `TQFU`，**不是** `T_QFUP`/`A_QFUP`。
- `/SCWM/TQFUCODE` Follow-Up Action 代码定义

**系统版本**
- `CVERS` Software Component Versions(字段 `component`/`release`/`extrelease`体现 SP/`comp_type`)。查 S4CORE release/SP 判断 Note 适用性: `component = 'S4CORE'`。注: 实际无 COMPID/DESC_TEXT/VERSION 字段，SP 由 `extrelease` 体现。

## 表间关系速查

- **WT ↔ WO**: WT 表(`ORDIM_O`/`ORDIM_C`)的 `who` 字段 = `/SCWM/WHO` 的 WO 号;一个 WO 可含多个 WT,WT 可能部分 open 部分 confirmed(故查 WO 时两张 ORDIM 表都要查)。
- **WT 单表归属**: 一条 WT 物理上只存在于 `ORDIM_O`(open)或 `ORDIM_C`(confirmed)**之一**。注意 tostat 字段: `C` = Confirmed(已确认), `A` = canceled(已取消), 空 = open(用户 2026-08-04 确认,见 memory ewm-wt-tostat-codes)。
- **WT ↔ 物料**: WT 表**没有 `matnr`**,物料用 `matid`(RAW/GUID)。要解析成物料号需另行 join/查询(如 `/SCWM/MAT_DOC` 或物料主数据)。
- **WT ↔ HU**: WT 的 `vlenr`/`nlenr` = HU 标识,指向包装表。
- **WT ↔ 仓位**: `vltyp`/`vlpla`(源) → `nltyp`/`nlpla`(目标);仓位主数据在 `/SCWM/LAGP`(用 `lgnum`+`lgpla`+`lgtyp` 定位)。
- **WT ↔ 工序类型**: `procty` 解释在 `/SCWM/T333`(含 `trart` 移动类型、`act_type`、源/目标存储类型、`wcr` 等)。
- **交货单表头 ↔ 行项目**: `/SCDL/DB_PROCH_*`(H) ↔ `/SCDL/DB_PROCI_*`(I),按 docid 关联;`_I`/`_O`/`_P` 后缀区分内向/外向/生产。
- **交货单 ↔ WT**: 通过 qRFC 字段 `qdoccat`/`qdocid`(ERP↔EWM 链路)及 warehouse request 关联。
- **库存 Quant ↔ 仓位/HU**: `/SCWM/AQUA` 的 `lgpla`/`lgtyp` 关联 `LAGP`;`huident` 关联 HU;`cat` 区分库存类别,`entitled` 区分归属。
- **库存类别 ↔ 配置**: `/SCWM/AQUA` 的 `cat` 释义在 `/SCWM/TCAT`(同 `lgnum`+`cat`)；`catlocn` 标志位置相关性。
- **检验凭证 ↔ skip lot**: `/SCWM/TWF_INSP`(经 include `/SCWM/S_EXCEP_INSP`)的 `skip` 字段是 skip lot 标志；`auto_decided`/`deci_code_id` 记录自动 UD 决策。
- **Follow-up ↔ IOT**: `/SCWM/TQFU` 的 `iot` 关联 `/SCWM/QIOT` 的 `iot`(同 `version`+`iot`)，定义某 IOT 在某 stock category 下触发什么 follow-up action。
- **库存 ↔ 检验**: `/SCWM/AQUA` 的 `insptyp`/`inspid` 关联检验凭证/检验 ID。
