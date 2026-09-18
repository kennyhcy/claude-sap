---
name: jira-query
description: 读取内网 Jira（T&R）issue 或按 JQL 搜索，仅限 $JIRA_PROJECT（环境变量，如 BXBRSWMS）项目下的 issue。API 地址从环境变量 JIRA_BASE_URL 读取（含 /rest/api/2 后缀），认证用 Bearer $JIRA_TOKEN 原始值。当用户给出 issue 编号要求查看/分析 issue 内容，或需要按 JQL 搜索 issue 时使用。
---

# 内网 Jira（T&R）issue 读取

术语约定：Jira 中的条目统一称 **issue**，或者 **BR**。

## 环境变量

- `JIRA_BASE_URL`：API 基地址，含实例前缀与 `/rest/api/2` 后缀，形如 `https://<host>/<instance>/rest/api/2`。
- `JIRA_PROJECT`：项目 key（如 `BXBRSWMS`）。
- `JIRA_TOKEN`：PAT，原始值直接放 Bearer，**禁止解码、禁止 Basic auth、禁止当 session 密码**（均实测必失败）。

调用前先检查 `[ -n "$JIRA_BASE_URL" ]` 与 `[ -n "$JIRA_PROJECT" ]`；有未设置的则停下提示用户配置，不要猜 URL 或项目 key。

## 项目范围（强制）

只读取 `$JIRA_PROJECT` 项目下的 issue：

- **JQL 搜索**：JQL 一律带 `project = $JIRA_PROJECT` 条件（如 `project = BXBRSWMS AND assignee = currentUser() ...`）。
- **读单个 issue**：issue key 必须属于 `$JIRA_PROJECT`；用户给的 key 属于其它项目（如 BXITSWMS-xxx）时，不查询，说明本 skill 仅覆盖 `$JIRA_PROJECT` 项目。

## 调用方式（curl，Git Bash）

读单个 issue（必带 fields 裁剪，默认全量会返回大量空 customfield_*）：

```bash
curl -s -H "Authorization: Bearer $JIRA_TOKEN" -H "Accept: application/json" \
  "$JIRA_BASE_URL/issue/<KEY>?fields=summary,status,issuetype,priority,assignee,reporter,created,updated,labels,fixVersions,components,description"
```

JQL 搜索（结果在响应 `issues` 数组，**JQL 必带 `project = $JIRA_PROJECT`**）：

```bash
curl -s -H "Authorization: Bearer $JIRA_TOKEN" -H "Accept: application/json" \
  "$JIRA_BASE_URL/search?jql=project%3D%27%24JIRA_PROJECT%27%20AND%20<其余条件>&startAt=0&maxResults=20"
```

## 解析要点

- 关键字段在 `fields` 下：`summary`、`description`（纯文本）、`status.name`、`issuetype.name`、`assignee.displayName`、`reporter.displayName`、`fixVersions[].name`、`labels`。
- `customfield_*` 大多为 null，默认不取；附件/图片需浏览器登录态，API 拿不到。

