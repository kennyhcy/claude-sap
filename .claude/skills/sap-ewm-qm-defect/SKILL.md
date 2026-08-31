---
name: sap-ewm-qm-defect
description: 分布式 EWM QM defect 流程口径（用户 2026-08-05 定案）。涉及入库检验 / internal 质检 / defect 语义 / IOT4 / IOT5 / 架构归属问答时使用。对象名均经实测确认存在。
---

# 分布式 EWM QM defect 流程

本 skill 编码了分布式 EWM 的 QM defect 流程口径，由用户于 2026-08-05 定案，属**确定结论**（不再是先前实测时标的"推断"）。所列事务 / FM / 包 / IDoc 名均经实测确认存在，照写即可。

完整口径与双轨对比表见 reference 文件 **[[ewm-qm-defect-distributed.md]]**（`references/ewm-qm-defect-distributed.md`，相对本 skill 目录）。本 skill 是其入口指针，触发场景下先读 reference 再作答。

## 什么时候用这个 skill

- 用户问 QM defect / 质检缺陷的流程归属
- 用户问入库检验（IOT4）与 internal 质检（IOT5）的区别
- 用户问本系统是分布式还是嵌入式 EWM
- 用户问 defect 判定（UD / decision code）在哪一侧做
- 涉及 `/SCWM/QINSP`、`/SCWM/QM_GM_CREATE`、`/SCWM/QINSP_IOT4_MAINTAIN_RFC` 等对象的语义

## 三条口径要点

### 一、本系统为分布式 EWM（确定）

- 本系统经实测确认为**分布式 EWM**（distributed EWM），而非嵌入式。
- 分布式 ERP↔EWM 集成通道为：**SRFC（启用的 RFC）** + **IDoc `/SCWM/QM_MASTER_DATA_SYNC_IDOC`**。该通道已经实测确认，即分布式集成的真实载体，**不必非得是老式 CIF/SMOF 队列**。
- 本系统上虽存在嵌入式适配器包 `/SCWM/ADAPTER_S4_ERP_QM`，但**不改变本系统的分布式定性**。

### 二、IOT4 = 入库检验（ERP 主导双轨）

IOT4 为 ERP 主导的双轨入库检验，流程链路：

1. ERP 经 `/SCWM/QINSP_IOT4_MAINTAIN_RFC` 触发 →
2. EWM 执行检验：事务 `/SCWM/QINSP`，记录 defect →
3. **质检判定（Usage Decision, UD）在 ERP 侧做** →
4. 结果经 `/SCWM/QINSP_RESULT_CR_SEND` 回传 EWM →
5. `/SCWM/QM_GM_CREATE` 过账 + `/SCWM/QM_REMOVE_QIR_FROM_STOCK` 闭环。

要点：检验在 EWM 执行，但 **UD 判定归属 ERP**，结果回流 EWM 完成过账闭环。

### 三、IOT5 = internal 质检（EWM 自闭环）

IOT5 为 EWM 自身的内部质检，全程 EWM 内闭环，ERP 不参与：

1. EWM 自身经 `/SCWM/QINSPDOC_CREATE_IOT5_MON` 创建 →
2. 事务 `/SCWM/QINSP` 执行、记录 defect →
3. decision code + follow-up action 处置 →
4. `/SCWM/QM_GM_CREATE` 过账 + `/SCWM/QM_REMOVE_QIR_FROM_STOCK` 闭环。

要点：创建、执行、判定（decision code）、过账、闭环**全在 EWM 内**，ERP 不参与。

## 双轨总结

| 维度 | IOT4（入库检验） | IOT5（internal 质检） |
|---|---|---|
| 主导 | ERP 主导 | EWM 自闭环 |
| 触发 | ERP 经 `/SCWM/QINSP_IOT4_MAINTAIN_RFC` | EWM 经 `/SCWM/QINSPDOC_CREATE_IOT5_MON` |
| 检验执行 | EWM（事务 `/SCWM/QINSP`） | EWM（事务 `/SCWM/QINSP`） |
| 判定归属 | **ERP 侧 UD** | EWM 内 decision code + follow-up action |
| ERP 参与 | 是（判定回流） | 否 |
| 过账闭环 | `/SCWM/QM_GM_CREATE` + `/SCWM/QM_REMOVE_QIR_FROM_STOCK` | `/SCWM/QM_GM_CREATE` + `/SCWM/QM_REMOVE_QIR_FROM_STOCK` |

一句话：**IOT4 = ERP 主导、EWM 干活、判定回流；IOT5 = EWM 自闭环。**

## 守则

- 本 skill 口径为**确定结论**，回答时直接据实陈述，不再标注"推断"。
- 所列对象名（事务 `/SCWM/QINSP`；FM `/SCWM/QINSP_IOT4_MAINTAIN_RFC`、`/SCWM/QINSP_RESULT_CR_SEND`、`/SCWM/QM_GM_CREATE`、`/SCWM/QM_REMOVE_QIR_FROM_STOCK`、`/SCWM/QINSPDOC_CREATE_IOT5_MON`；IDoc `/SCWM/QM_MASTER_DATA_SYNC_IDOC`；包 `/SCWM/ADAPTER_S4_ERP_QM`）均经实测确认存在，照写即可，无需重复验证。
- 若用户问及 reference 未覆盖的 QM 细节，按 agent md 的强制规范处理（先验证再报 / 系统知识盲区走官方文档），不凭记忆硬答。
