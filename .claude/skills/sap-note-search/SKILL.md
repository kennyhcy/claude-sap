---
name: sap-note-search
description: 按关键词搜 SAP Note / KBA。调用本 skill 后必须先用 Read 把本 SKILL.md 全文读完（正文有搜索引擎 fallback 链、查询构造、CAPTCHA/403 避坑、与 sap-note 的衔接规则，只看 description 不够）。搜编号用 WebFetch 抓公开搜索引擎结果页（主用 DuckDuckGo，被 CAPTCHA 风控时切 Brave）；取全文必须委托 sap-note skill 的 get_sapnote.ps1 脚本——禁止自拼 Edge/curl 或用 WebFetch 抓 SAP Note 正文。当用户描述一个问题（如"skip lot 自动 UD 的 note"）而手头没有具体编号时使用。
---

# SAP Note 搜索

按关键词搜出 Note/KBA 编号，再委托 [[sap-note]] 抓全文（缓存 `.claude/skills/sap-note/sap-notes/<编号10位>.json`，命中直接 Read；未命中批量传脚本，🔴禁止并发多进程）。本 skill 只管"搜编号"，取全文逻辑不重复实现。

## 搜索引擎 fallback 链（2026-09-14 实测）

| 引擎 | URL | 结论 |
|---|---|---|
| DuckDuckGo html | `https://html.duckduckgo.com/html/?q=<query>` | 平时可用 |
| **Brave** | `https://search.brave.com/search?q=<query>` | **DDG 被 CAPTCHA 风控时的主力**，`site:community.sap.com` 可用 |
| 其余（DDG lite/Bing/Mojeek/Ecosia/内置 WebSearch） | — | 均实测无用（同套风控/泛化结果/403），不必试 |

- CAPTCHA 特征：`Select all squares containing a duck` + `Code: 90d2`。属 **IP 级风控**，换措辞/换 DDG 端点无用——连续 2 次即切 Brave。
- 高信号关键词：引号锁定系统术语/字段名（"posting block"）、事务码（/SCWM/PI）、表名（AQUA）；查询前缀加 `SAP+Note`。DDG 上避免 `site:me.sap.com` 和过多引号。

## 工作流程

1. 中文关键词先译成英文，构造查询 URL（DDG 优先）。
2. WebFetch 抓结果页，prompt 要求：抽取所有 6–10 位 Note/KBA 编号及标题，输出 `NUMBER - title` 每行一条，只列实际看到的编号。
3. 判读：空结果→换措辞重试 2–3 次；CAPTCHA→切 Brave；全空→如实告知"未命中，可能未被外部索引"。
4. 编号噪声交叉判断：须在 Note/KBA 上下文或带 me.sap.com/userapps 链接；可疑编号抓全文时自然露馅（404）。
5. 列命中清单给用户，取全文走 [[sap-note]]（见首段）。
6. 汇总：命中清单 + 逐条摘要（标题、组件、Symptom、Resolution、关联 Note）。

## SAP Community 帖子 403 绕行（2026-09-14 实测）

community.sap.com 对非浏览器请求一律 403（curl/PowerShell 带 UA 也 403）。**唯一可用：WebFetch 走 `https://r.jina.ai/<原帖URL>`**，返回完整 markdown（问题+回复+采纳答案）。仅用于公开论坛帖，勿送登录态 URL/敏感信息。KBA 直链（userapps.support.sap.com）不需绕行——全文一律走 [[sap-note]] 脚本。

## 约束

- 公开搜索只能找到被外部索引的 note；搜不到别硬编编号。
- 取全文需 SAP 登录态，过期时按 [[sap-note]] 规则弹窗登录；输出仅本地查看勿分发。
