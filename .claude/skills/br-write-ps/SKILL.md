---
name: br-write-ps
description: 按 BR 书写规范，只填写 SAP EWM BR（Business Requirement）文档的 Product Specification（PS，第 4 章）部分——依据已写好的 PR 逐条撰写解决方案、SPRO/F1 文档要求、方案选项说明等，其余章节（History / General / PR / Cut-over）一律不许修改。涉及"写 BR 的 PS 部分"、"补 PS"、"按 PR 写解决方案"时使用。
---

# BR PS 撰写实操规则

本 skill 编码了 SAP EWM BR 文档 **Product Specification（PS）** 部分的完整书写规范与安全修改技术。规范、模板章节结构、占位提示原文均已写入下文。

> 🔴 **范围强制规范（最高优先级）**：本 skill **只允许修改 BR 文档第 4 章 "Product specification" 区间内的段落**。第 1 章 History、第 2 章 General information（含 2.1–2.6 全部子章节）、第 3 章 Process requirements（PR）、第 5 章 Cut-over activities，**以及文档里唯一的那个表格（History 版本表 `Ver/Status/Date/By/Change`）一律不许触碰、不许增删、不许改样式**。即便发现别处有错，也不要顺手改——如实告知用户后待命。

## 什么时候用这个 skill

- 用户要给一份 BR 文档"写 PS"、"补 PS"、"完成 Product Specification 部分"
- PR（第 3 章）已写好，需要据此撰写对应的 PS（第 4 章）
- 用户问"PS 该怎么写 / 该写什么"——回答前先读本 skill 的规范要点

---

## 一、BR 文档总则（General，规范原文内化）

这些是 BR 文档全局规则，PS 撰写须遵循其中相关项：

1. **PR 与 PS 必须互链**：一条 PR 至少对应一条 PS。PS 审批时检查所有 PR 是否都有至少一条 PS 链接。链接方式有两种（模板采用 Option 1）：
   - Option 1 —— PR 与 PS 各占独立章节（PR 在第 3 章，PS 在第 4 章）。
   - Option 2 —— PR 和 PS 紧挨着写在一起。
2. **版本管理**：内容有变更就要建新版本。原属 scope 后续讨论认为无关的，移到 "out of scope" 并建新版本。须记录变更原因（如"X、Y、Z 开会，结论是改用流程 ABC"）。**删除线内容要建新版本并删除**。测试阶段如有变更，建新版本更新相关部分（主要是 PS，特殊情况下也改 PR）。
3. **Cut-over 活动归第 5 章**：即使部分在 PS 描述里已涉及，也必须在第 5 章 "Cut-over activities" 集中汇总——但**第 5 章不归本 skill 改**，本 skill 只在 PS 里写明哪些改动可能引出 cutover 任务，提示用户去第 5 章汇总。
4. **上传**：有效的 PR+PS 须上传到中央 SharePoint（这是流程要求，非本 skill 动作）。

## 二、BR 文档章节结构（模板实测，内化）

BR 文档固定 5 个 Heading 1 章节，PS 是第 4 章：

| # | 章节 | 子章节 | 归属 | 本 skill 可改 |
|---|------|--------|------|--------------|
| 1 | History | —（含版本表 `Ver/Status/Date/By/Change`） | — | ❌ |
| 2 | General information | 2.1 Purpose and Background Information / 2.2 Constraints, Assumptions and Dependencies / 2.3 Out-of-scope / 2.4 Process flowchart / 2.5 High-Level test scenarios / 2.6 Glossary | — | ❌ |
| 3 | Process requirements | 3.1 Functional requirements / 3.2 Quality requirements | PR | ❌（只读，作为输入） |
| **4** | **Product specification** | — | **PS** | **✅ 仅此区间** |
| 5 | Cut-over activities | — | — | ❌ |

文档里通常只有 **1 个表格**——History 版本表。PS 与 PR 在文档里都是**段落正文**（不是表格）。

### 各章节占位提示原文（识别用，不改）

撰写 PS 时需识别 PR 章节的占位与结构，下面是模板各处的占位提示原文（**这些是给撰写者的引导问题，不是要照抄进 PS**）：

- **2.1 Purpose and Background Information**：What is the purpose and scope of this BR? / Any background information necessary from project context? / Which systems are affected? EWM PL7? AEB? ERP? / Which interfaces do we need to consider?
- **2.2 Constraints, Assumptions and Dependencies**：Are there any constraints or boundary conditions? / Do we need to take any assumptions? / Do we have any dependencies on other BRs, developments, projects?
- **2.3 Out-of-scope**：What will not be considered in this BR? / Which topics are out-of-scope?
- **2.4 Process flowchart**：If possible and useful, especially for new developments or complex processes, create process flow chart here.
- **2.5 High-Level test scenarios**：Think about possible test scenarios on a higher level, considering the end-to-end process, and write it down here.
- **2.6 Glossary**：Are there any wordings which are warehouse or project specific, which need to be explained or defined? / Are there any abbreviations used, which are not in common use?
- **3.1 Functional requirements**：Describe here the new requirements. ... / Describe here how you would test the requirement.（即每条 functional requirement 配 acceptance criteria）
- **3.2 Quality requirements**：含固定说明——ERP 接口须用精简 IDoc（不含 sensitive 信息如 debitor credit limit）；报表/事务性能须可接受（复杂报表 2–3 分钟可，30 分钟不可）；须支持所有已装语言（English/German/French/Korean/Japanese/Spanish/Portuguese/Polish/Czech/Hungarian），BD 提供翻译清单给 GS；master data（如 `/RBL0/EWM_GIDET`）及整个 SPRO 可保持英文；新事务/程序须加入角色 xxxx，新表通过 `S_TABU_DIS` Authorization Group xxxx 或 `S_TABU_NAM` 赋权，并向 Hanna Wurst（GS/PSD14）建 defect。
- **5 Cut-over activities**：List here all activities, especially master data, which need to be done, to work with the above-described functionalities.

### PR 写作规范（理解 PR 用，本 skill 不写 PR 但要据此 link）

- PR 只写"真正的需求"（客户到底要什么），**不写 how、不写技术方案**。
- 每条 requirement 须配 **acceptance criteria**（一条 requirement 至少一条，也可多条 PR 共用一条；负面测试也可作 acceptance criteria）。
- 区分 functional（系统须执行的行为/功能）与 quality（非功能性属性：性能、可靠性、安全、可用性）requirement。
- T&R 里的 Label 须填 Warehouse process ID（来自 Docupedia）。

---

## 三、PS 区间如何精确定位（技术锚点）

docx 是 zip + `word/document.xml`。PS 区间 = **"Product specification" 这个 Heading1 段落（含）** 到 **下一个 Heading1（"Cut-over activities"）段落（不含）** 之间的所有段落。

- 用 `python-docx`（本项目环境已装，1.2.0）遍历 `document.paragraphs`，按 `paragraph.style.name` 命中 `Heading 1` + 文本 `Product specification` 定位起点；再找下一个 `Heading 1`（"Cut-over activities"）定位终点。
- 修改时**只动这个区间内的段落**：可删除模板占位提示、可新增/改写段落，但**不得越界到其他 Heading 区间**。
- **禁止碰表格**：`document.tables[0]` 是 History 版本表（`Ver/Status/Date/By/Change`），任何情况下不读不写不删。

### PS 区间内的段落样式（实测，写回时保持一致）

模板 PS 区间用到的段落样式名（`paragraph.style.name`）：

- `Heading 1` —— "Product specification" 标题行本身，**不要改**。
- `Normal` —— 首行占位提示 `Delete everything which is not applicable...`（撰写完成后删除此句）。
- `Product Requirements` —— PS 正文描述行，模板里是 `[link of Cust.Req. here] Describe how to solve the requirement here...`。**你写的每条 PS 解决方案段落就用这个样式**（仿照 PR 的描述样式），保持文档风格统一。
- `Comment` —— 两条待回答的问题（authorization defect / SPRO tree）。回答时保留 `Comment` 样式，或在正文里作答后删除占位问题句。

新增 PS 段落时，优先复用上述已存在的样式名（尤其 `Product Requirements`），不要自创新样式，避免破坏文档主题。

### 备份与回滚

> 修改前**先备份原文件**（复制一份 `.bak`）。docx 写入是整文件覆盖，出错难回滚。

---

## 四、PS 模板占位（需替换/填充的内容）

模板第 4 章自带占位提示，撰写 PS 时按需替换或在其后追加：

1. `Delete everything which is not applicable for this BR (even this sentence).` —— 撰写完成后删除此句（它本就是给撰写者的提示）。
2. `[link of Cust.Req. here] Describe how to solve the requirement here. ...` —— 这是 PS 的正文位置：**每条 PS 先 link 回对应的 PR（Customer Requirement），再写解决方案描述**。
3. `Any new transactions/program/table to be added to authorization concept? -> create defect in ALM to Hanna Wurst GS/PSD14 ...` —— 若涉及新事务/程序/表，须在 PS 里列出，并按提示去 ALM 建 defect 给 Hanna Wurst（GS/PSD14）。
4. `Any new customizing tables need to be added to the Bosch-specific SPRO tree?` —— 若新建 customizing 表，回答是/否并说明。

---

## 五、PS 书写规范要点（Docupedia "How to write the Product Specifications" 原文内化）

撰写 PS 内容时**逐条对照**以下规则：

1. **用自己的话认真写**（formulation in own words）——不要照抄 PR，要把 PR 的"需要什么"转成"解决方案长什么样"。
2. **详细描述解决方案的样貌**——不过于技术、**不写代码**。可附 mock-up（文字描述或简单示意）帮助理解。
3. **逐条 link PR**：一条 PR 至少对应一条 PS。每条 PS 开头注明它解决的是哪条 Customer Requirement（用模板的 `[link of Cust.Req. here]` 位置）。PS 审批时会检查所有 PR 是否都有至少一条 PS 链接。
4. **新建表**时：
   - PS 里必须给出 **SPRO 路径**，并在系统中实际创建。
   - 必须维护 **Text info + F1 help**。
5. **Customizing 变更**：每张涉及的表都要描述，**含 SPRO 路径**。
6. **多方案时**：若存在多种解法满足同一 PR，须与相关方讨论，在 PS 里**列出选项**，并加注释说明**为何选了方案 X**。
7. **影响特定仓库时**：若改动可能影响某些仓库，须写明——可作为 PS 的注释，或放在 "2.2 Constraints, Assumptions and Dependencies" 作 dependency（但 2.2 不归本 skill 改，只能提示用户）。cutover task 后续据此推导。
8. **Functional / Technical 文档必须提供**：所有新建事务、现有表的新字段、Customizing 点，都要用系统标准文档手段记录：
   - 事务：右键 → Display documentation；进入事务后点字段 → F1 help。
   - SPRO 节点：右键 → Display documentation；节点内点字段 → F1 help。
   - 参照示例：`/RBL0/EWM_LOAD_S` 字段 "manual staging" 的 F1 help。
9. **Flowchart 须补充技术信息**（若 PR 里 2.4 有流程图）。
10. **RF 屏幕有新改动**时：PS 里须注明要考虑 **UI5 conversion + UI5 objects**。

---

## 六、与 PR 的对应写法

PS 是 PR 的"解"。撰写顺序：

1. 先**通读第 3 章 PR**（3.1 Functional requirements 的每一条需求 + 3.2 Quality requirements），逐条编号理解。
2. 对**每条 functional requirement**，写一条或数条 PS，开头标注其 link 的 PR。
3. **Quality requirements**（3.2）通常是非功能性约束（性能、多语言、权限等），PS 里要说明如何满足（如权限如何挂角色、多语言如何翻译）。模板 3.2 已有固定说明文字，PS 侧只补充本 BR 特有的落实方式。
4. 写完后**自检**：是否每条 PR 都有至少一条 PS 对应？有没有遗漏 acceptance criteria 关联的解决方案？

---

## 七、写作语气与质量

- 英文撰写（BR 文档语言为英文）。
- 描述"解决方案是什么样"，不描述"代码怎么写"。
- 涉及具体事务码/表名/SPRO 路径时，**必须核实其真实存在**（用 MCP `SearchObject` / `GetTable` / `GetTransaction` 等），区分客观事实与推断结论。未核实的对象不要臆测，宁可用业务描述并向用户标注"待核实"。
- 涉及权限角色名、ALM defect 归属人（Hanna Wurst GS/PSD14）等，按模板原文照引，不要改写。

---

## 八、Testing 相关要点（规范原文内化，影响 PS 写法）

- 新事务/Customizing 节点的**每个字段都须有 F1 help**；事务与 Customizing 须有正规文档（Right Click → Display Documentation）。→ 这条决定 PS 里新建对象时必须把 F1/documentation 维护写进方案。
- acceptance criteria 写得好，可直接作为 ALM 上传的 testcases（仅需少量增强）。→ PS 撰写时若 PR 的 acceptance criteria 清晰，PS 方案应与之可测。

---

## 九、落地步骤（标准动作）

1. **读规范**：本 SKILL.md 已含全部 PS 规范要点与原文，无需读任何外部模板文件。
2. **备份**：`cp "<目标 BR>.docx" "<目标 BR>.docx.bak"`。
3. **提取 PR 与当前 PS 区间**：用 python-docx 遍历段落，定位 PS Heading1 区间，打印该区间当前内容 + 第 3 章 PR 全文，作为撰写输入。
4. **撰写 PS**：按第五节"PS 书写规范要点"逐条写，link 回 PR。
5. **写回 docx**：用 python-docx **只修改 PS 区间段落**（删占位、追加新段落），保存。务必确保未触碰其他章节与表格。
6. **读回验证**：重新打开 docx，确认 PS 区间已更新、其他章节未变（可对比 `.bak`）。
7. **如实汇报**：写了哪些 PS、对应哪些 PR、有无未核实对象、是否需要用户去 ALM 建 defect / 维护 SPRO / 去第 5 章补 cutover。

---

## 十、常见坑

- **越界改 PR**：PS 写着写着发现 PR 有歧义，想去改 PR 表述——**禁止**。PR 是输入，只读。如有歧义，在 PS 里用注释说明假设，或汇报用户。
- **删了不该删的占位**：模板 PS 区间里 "Any new transactions..." 和 "Any new customizing tables..." 是**待回答的问题**，不是废话。若本 BR 不涉及，可删该句并简注 "N/A"；若涉及，须实际作答，不能整段删空。
- **碰了版本表**：文档唯一的表格是 History 版本表。python-docx 改段落时不要碰 `document.tables`。
- **整文件覆盖未备份**：docx 保存是覆盖原文件。不备份就改 = 出错无法回滚。
- **臆测事务码/表名/SPRO 路径**：PS 里出现的技术对象名必须经 MCP 核实存在。未核实用业务描述代替，并向用户标注"待核实"。