---
name: jira-query
description: 读取内网 Jira（T&R）issue 或按 JQL 搜索。API 地址从环境变量 JIRA_BASE_URL 读取（含 /rest/api/2 后缀），认证用 Bearer $JIRA_TOKEN 原始值。当用户给出 issue 编号要求查看/分析 issue 内容，或需要按 JQL 搜索 issue 时使用。
---

# 内网 Jira（T&R）issue 读取

术语约定：Jira 中的条目统一称 **issue**，或者 **BR**。

## 环境变量

- `JIRA_BASE_URL`：API 基地址，含实例前缀与 `/rest/api/2` 后缀，形如 `https://<host>/<instance>/rest/api/2`。
- `JIRA_TOKEN`：PAT，原始值直接放 Bearer，**禁止解码、禁止 Basic auth、禁止当 session 密码**（均实测必失败）。

调用前先检查 `[ -n "$JIRA_BASE_URL" ]`；未设置则停下提示用户配置，不要猜 URL。

## 调用方式（curl，Git Bash）

读单个 issue（必带 fields 裁剪，默认全量会返回大量空 customfield_*）：

```bash
curl -s -H "Authorization: Bearer $JIRA_TOKEN" -H "Accept: application/json" \
  "$JIRA_BASE_URL/issue/<KEY>?fields=summary,status,issuetype,priority,assignee,reporter,created,updated,labels,fixVersions,components,description"
```

JQL 搜索（结果在响应 `issues` 数组）：

```bash
curl -s -H "Authorization: Bearer $JIRA_TOKEN" -H "Accept: application/json" \
  "$JIRA_BASE_URL/search?jql=<URL编码的JQL>&startAt=0&maxResults=20"
```

## 解析要点

- 关键字段在 `fields` 下：`summary`、`description`（纯文本）、`status.name`、`issuetype.name`、`assignee.displayName`、`reporter.displayName`、`fixVersions[].name`、`labels`。
- `customfield_*` 大多为 null，默认不取；附件/图片需浏览器登录态，API 拿不到。

