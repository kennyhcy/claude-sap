---
name: sap-basic-data-query
description: SAP 系统通用知识库（所有 agent 共享）。收录不归属于任何单一业务模块的跨模块通用知识：IDoc、OData、BAPI/RFC、ALE、CDS View、事务码体系、SPRO/IMG 配置框架等。涉及这些通用概念的问题、或需要理解某模块对象在系统层面的承载方式时使用。本 skill 是知识型，不含特定技术对象的实测清单，具体对象名仍须先经 MCP 验证。
---

# SAP 系统通用知识库

收录 SAP S/4 HANA 系统中**不归属任何单一业务模块**的通用知识。所有 agent 共享，不属于 MM/SD/PP/FI/CO/EWM 任一模块的专属技能。当一个模块顾问遇到"这个模块对象在系统层面怎么承载/怎么集成"这类跨模块底层问题，或用户直接问 IDoc/OData 等通用概念时使用。

## 何时使用本 skill

- 用户问 IDoc、OData、BAPI、RFC、ALE、CDS View 等跨模块通用概念
- 模块顾问需要理解本模块对象在系统层面的承载方式（如：某业务数据除透明表外，是否也以 CDS View 暴露给 OData 服务）
- 需要区分"业务数据"（属各模块顾问）与"系统层承载机制"（通用）的边界
- 需要理解 SAP 标准集成/接口技术在当前场景中的适用性

## 知识范畴（概念层，不含实测对象清单）

### IDoc（Intermediate Document）
- SAP 系统间/系统内异步集成的事实标准数据载体，基于层次结构（控制记录 / 数据记录 / 状态记录）。
- 与 ALE（Application Link Enabling）配合实现分布式主数据/业务数据同步；与 EDI 配合对接外部伙伴。
- 模块相关性：各模块（MM/SD/FI 等）都有各自的 IDoc 类型与消息类型，但 IDoc 的处理框架（端口、伙伴协议、处理码、状态监控）是通用的。
- 关键区分：IDoc 是"载体"，消息类型（如 ORDERS、ORDERS05）是"语义"，具体消息类型属对应模块。

### OData 服务
- SAP S/4 HANA 对外提供 RESTful 接口的主流方式，基于 OData 协议（V2/V4）。
- 底层多由 CDS View（Core Data Services）作为数据模型，经 OData 服务暴露为端点。
- Fiori 应用的后端数据来源、第三方集成的首选只读/读写接口。
- 模块相关性：每个模块有自己的 OData 服务（如 MM 的、SD 的），但 OData 的注册/暴露/消费机制是通用的。

### BAPI / RFC
- BAPI（Business Application Programming Interface）：SAP 为业务对象提供的标准化、稳定的接口方法（经 RFC 实现）。
- RFC（Remote Function Call）：SAP 系统间/外部调用的同步通信机制，BAPI 与许多标准功能都基于它。
- 与 IDoc 的区分：RFC 是同步、IDoc 是异步；选型取决于场景（实时性 vs 解耦/可靠性）。

### ALE（Application Link Enabling）
- SAP 系统间分布式集成的框架，底层用 IDoc 传数据，用事务码维护模型/分发视图/接收方。
- 分布式 EWM 与 ERP 的主数据/部分业务数据同步即走 ALE 通道（具体配置属 EWM 顾问，ALE 框架本身通用）。

### CDS View（Core Data Services）
- S/4 HANA 的数据建模层，作为底层数据库表的语义层视图，同时是 OData/Fiori/分析报表的数据来源。
- 模块相关性：各模块有自己的标准 CDS View，但 CDS 语法/注解/暴露机制通用。

### 事务码体系与 SPRO/IMG 配置框架
- 事务码：SAP 用户进入具体功能的入口，各模块各有其事务码，但事务码的创建/维护/分配机制通用。
- SPRO/IMG（Implementation Guide）：SAP 配置的统一入口，按模块-子功能-配置活动分层；各模块顾问在 SPRO 里配自己模块的节点，但 IMG 框架与导航通用。

## 与各模块顾问的分工边界

- **本 skill**：提供通用概念、架构、承载机制、技术选型依据（概念层）。
- **各模块顾问**：提供本模块的具体业务对象、表、事务码、配置节点（实测层，经 MCP 验证）。
- 例：问"MM 采购订单怎么对接外部系统" -> 本 skill 给 IDoc/OData/RFC 的选型与机制，MM 顾问给采购订单相关的具体消息类型/服务名（须验证）。

## 行为准则

1. **概念可答，对象名须验证**：本 skill 的通用概念（IDoc/OData/BAPI 等的定义、架构、适用场景）可直接据实陈述；但一旦涉及具体的服务名、IDoc 类型名、FM 名、CDS View 名等，须先经 MCP（`SearchObject`/`GetTable`/`GetTypeInfo` 等）验证存在再引用，**禁止臆测对象名**。
2. **不越界到模块专属**：问到具体模块业务（采购/销售/成本等）时，路由到对应模块顾问；本 skill 只就"系统通用承载机制"作答。
3. **系统知识盲区自己查**：通用概念盲区用 `WebSearch`/`WebFetch` 查 help.sap.com 或 `sap-note`/`sap-note-search` skill；查不到明说「未查到官方依据」；反复查无果再上报主 Claude。
4. **只读不写**：本 skill 不涉及 `CreateObject`/`UpdateObjectSource`/`ActivateObject`，不创建/修改代码或配置对象。

## 多系统选择（system 参数）

本项目 MCP server 支持同时连接多个 SAP 系统。所有工具（`GetTable`/`GetTableContents`/`SearchObject`/`GetClass` 等）都接受一个**可选**参数 `system`，用于指定目标系统 id（如 `"prd"`、`"dev"`）。**不传 `system` 时用默认系统**（由 MCP 的 `.env` 里 `SAP_DEFAULT_SYSTEM` 指定，或回退到首个已配置系统），完全向后兼容。

- 多系统配置：MCP 的 `.env` 用前缀变量，如 `SAP_URL_PRD`/`SAP_USERNAME_PRD`/`SAP_PASSWORD_PRD`/`SAP_CLIENT_PRD`，`SAP_DEFAULT_SYSTEM=prd`。
- 单系统场景（沿用裸 `SAP_URL` 等）：无需关心 `system`，照旧不传即可。
- agent 无需知道有哪些系统--工具的 `system` 参数描述里会动态列出当前已配置的系统 id。

## 约束

- 本 skill 是知识型，**不含已实测的对象清单**。所有具体技术对象名在使用前须先经 MCP 验证存在。
- 知识以 SAP 官方文档为准，不凭记忆硬答；不确定的概念标注为"待查证"。
