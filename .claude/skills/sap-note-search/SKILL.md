---
name: sap-note-search
description: 按关键词搜 SAP Note / KBA。调用本 skill 后必须先用 Read 把本 SKILL.md 全文读完（正文有 DuckDuckGo 查询 URL 构造、CAPTCHA 避坑、与 sap-note 的衔接规则，只看 description 不够）。搜编号用 WebFetch 抓 DuckDuckGo HTML 端；取全文必须委托 sap-note skill 的 get_sapnote.ps1 脚本——禁止自拼 Edge/curl 或用 WebFetch 抓 SAP Note 正文（SAP session cookie 是 HttpOnly，只有脚本里的独立 Edge profile 才带得上）。当用户描述一个问题（如"skip lot 自动 UD 的 note"）而手头没有具体编号时使用。
---

# SAP Note 搜索

按**关键词**搜出 SAP Note / KBA 编号清单，再用 [[sap-note]] skill 抓每条的全文并给摘要。

## 思路：两层解耦

- **找编号**（本 skill 负责）：用公开搜索引擎找哪些 note 编号与问题相关。不依赖 SAP 登录态——me.sap.com 的搜索是 SPA + 登录墙，公开搜索抓不到；改用 DuckDuckGo HTML 端，让 WebFetch 的小模型从结果页里抽编号。
- **取全文**（委托 [[sap-note]] skill）：拿到编号后，调 `sap-note` skill 的脚本（`.claude/skills/sap-note/get_sapnote.ps1`）走 headless Edge 复用 SAP 登录态抓 note JSON。

两层职责正交：本 skill **不重复实现**取全文逻辑，只管"搜编号 → 喂给 sap-note"。

## 这个 skill 是自包含的

整个 `.claude/skills/sap-note-search/` 文件夹只有本 `SKILL.md`，没有脚本——搜索用 WebFetch 工具，取全文复用 `sap-note` skill 的脚本。所以本 skill **依赖同项目下存在 `.claude/skills/sap-note/`**。搬到别的项目时，把 `sap-note` 和 `sap-note-search` 两个文件夹一起拷贝即可。

## 工作流程

1. **用户给关键词**（自然语言，如"skip lot 自动 UD"、"F2929 附件上传报错"）。如果是中文，先在脑子里翻成英文关键词（SAP Note 标题几乎都是英文），用英文去搜。

2. **构造 DuckDuckGo HTML 查询 URL**：
   ```
   https://html.duckduckgo.com/html/?q=SAP+Note+<关键词1>+<关键词2>+...
   ```
   - 关键词用 `+` 连接，空格转 `+`，特殊字符用百分号编码（`%20` 也行）。
   - **查询前缀加 `SAP+Note`**，让结果偏向 SAP 官方/社区/博客里提到 Note 编号的页面。
   - 1–2 次实测后定稿的查询样式（命中率高，可直接套）：
     - `SAP+Note+skip+lot+automatic+usage+decision`（泛化自然语言）
     - `SAP+Note+%22usage+decision%22+%22skip+lot%22+note`（带少量引号锁定短语）
   - **避免**：`site:me.sap.com` 限定（实测触发 CAPTCHA，整页变验证码）、过多引号（命中数骤降）、纯 `SAP Note` + 一个很泛的词（噪声大）。

3. **用 WebFetch 抓该 URL**，prompt 明确要求：
   > 从这些 DuckDuckGo 搜索结果里，抽取所有 SAP Note / KBA 编号（6–10 位数字）及其标题/摘要。输出 `NUMBER - title` 列表，每行一条。只列你实际在文本中看到的编号。

   WebFetch 会用小模型解析 HTML 结果页，从标题、摘要、URL（如 `/notes/0003152102`）里抽编号。

4. **判读与重试**：
   - 拿到编号清单 → 进第 5 步。
   - 结果为空、或 WebFetch 说"这是 CAPTCHA 验证页" → 换关键词措辞重试（同义词替换、去掉引号、加/减 `SAP Note` 前缀），最多 2–3 次。
   - 仍搜不到 → 如实告诉用户"公开搜索没命中，可能这条 note 没被外部站点索引"，让用户给编号或换词。

5. **把候选编号交给用户确认，或直接取全文**：
   - 先列搜索命中：`NUMBER - title` 每行一条，附来源类型（SAP 官方/社区/博客）。
   - 用户多半想看最相关的 1–3 条全文。对每条候选编号，**先查 [[sap-note]] 的缓存**：编号补零到 10 位（如 `3152102` → `0003152102.json`），看 `.claude/skills/sap-note/sap-notes/<编号>.json` 是否已存在。
     - **缓存命中**：直接用 Read 读该 JSON 解析，不走网络。
     - **缓存未命中**：把所有未命中编号**一次性**传给脚本批量抓取（脚本内部串行、登录只一次），**不要为每条编号各起一个进程**：
       ```
       powershell -ExecutionPolicy Bypass -File ".claude/skills/sap-note/get_sapnote.ps1" <编号1> <编号2> <编号3>
       ```
       首次使用或 SAP 登录态过期时，脚本会开 Edge 窗口让用户登录 SAP，**用户登录后自己关掉那个窗口**，脚本检测到关窗后自动继续抓取剩余 note（完整规则见 [[sap-note]] 的 SKILL.md，本 skill 不重复说明）。
     - **🔴 禁止并发起多个 `get_sapnote.ps1` 进程**：它们共用一个 Edge profile 会互锁，还会互杀登录窗口导致 500。多 note 一律走单次批量调用。

6. **汇总**：主 Claude 给出搜索命中清单 + 对取了全文的 note 逐条摘要（标题、类型、组件、Symptom、Resolution、关联 Note）。摘要口径与 [[sap-note]] 一致。

## 注意与约束

- **固有局限：公开搜索只能找到被外部站点（SAP 帮助、SAP Community、博客、第三方文档）索引到的 note**——也就是标题/摘要出现在公开网页里的那些。少数仅 SAP 内部可见、或新发布尚未被外部引用的 note，公开搜索搜不到。遇到搜不到别硬编编号，如实告诉用户。
- **编号噪声**：社区帖子里可能有其它 6–10 位数字（如订单号、其它系统的 ID）被小模型误抽。主 Claude 交叉判断：编号是否出现在 "Note / KBA / note number" 上下文里、是否带 me.sap.com 链接。可疑的编号取全文时会自然露馅（note API 返回 404 或非 note JSON）。
- **查询措辞敏感**：同一问题不同措辞命中率差很多。`site:` 限定和多引号会触发 CAPTCHA/降命中，已实测避免。
- **取全文仍需 SAP 登录态**：搜索是公开的，但拿 note 正文走的是 [[sap-note]] 的登录态机制。登录态过期时按其规则弹窗登录。
- 输出文件仅本地查看，勿分发（继承 [[sap-note]] 的约束）。
