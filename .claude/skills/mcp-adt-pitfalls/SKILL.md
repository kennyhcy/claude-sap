---
name: mcp-adt-pitfalls
description: mcp-abap-adt-b（TypeScript/MCP）项目的已知坑清单与审查要点——ADT REST 调用陷阱（URL 路径大小写、header、ETag/corrNr 处理）、错误处理、类型安全。审查或排查 mcp-abap-adt-b 源码时使用。注意：这是领域坑清单，不是通用 review 方法论；ABAP 代码审查用 abap-code-review。
---

# mcp-abap-adt-b 已知坑清单（TypeScript/MCP）

本 skill 编码了 mcp-abap-adt-b 这个 TS/MCP 项目的**领域已知坑清单**与审查要点——不是通用 review 方法论，而是这个项目特有的 ADT REST 契约陷阱。审查或排查 mcp-abap-adt-b 源码时使用。ABAP 代码审查（Clean ABAP 规范、性能、安全）用 `abap-code-review` skill。

## 什么时候用这个 skill

- 审查 mcp-abap-adt-b 的 handler 逻辑
- 排查 ADT REST 调用相关的 bug（URL 路径、header、ETag/corrNr）
- 审查 TS/MCP 源码的错误处理、类型安全

## MCP 源码位置

MCP server 的安装路径因环境而异，不要在文档里写死绝对路径。需要定位 MCP 源码或确认实际启用的 server 时，读项目的 `.mcp.json`（其中 `mcpServers` 的每个条目 `args` 指向该 server 的 `dist/index.js`）。改 MCP 源码后须 `npm run build` 并重启 MCP 才生效。

## 审查要点

审查 handler 逻辑时关注：
- ADT REST 调用是否正确（URL 路径、header、ETag/corrNr 处理）
- 错误处理是否完整
- 类型是否安全

## ADT REST 已知坑清单（重点检查项）

| 坑 | 正确做法 |
|---|---|
| 类/接口 URL 大小写 | 类/接口 URL 用**小写**，程序/include 用**大写** |
| include 端点路径 | include 端点是 `/programs/includes/`，**不是** `/programs/programs/` |
| 真实 package 的 PUT | 必须带 `corrNr`，否则报 `Parameter corrNr could not be found` |
| POST 创建后取 ETag | POST 创建后响应**无 ETag**，必须 GET `/source/main` 取 |
| `If-Match: *` | xl7 **拒绝** `If-Match: *` |
| 直调 axios 的 GET 漏 `sap-client` | handler 绕过 `makeAdtRequest` 的请求（update/create 取 ETag 的 GET）必须带 `params: {'sap-client': client}`，否则登到系统默认 client：用户不在该 client 时返回 401「Anmeldung fehlgeschlagen」登录页（读正常、写 401 即此症）。2026-09-13 已修 |
| 改源码后状态 | 存为 inactive，需调 `ActivateObject` |

## 底层契约参考

ADT 底层契约（body XML 结构、ETag 流程、corrNr 规则）的完整记录见项目记忆 `adt-rest-create-update-contract.md`；源码真相在 xl7 的 `CL_OO_ADT_RES_CLASS` / `CL_SEDI_ADT_RES_SOURCE`。

## 审查输出

按 code-reviewer agent md 的规则输出：按严重度排序（正确性 bug > 复用/简化 > 效率），每个发现引用具体 `file:line`，验证不了的标注「不确定」，无发现时明确说「无问题」。
