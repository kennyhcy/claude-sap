---
name: br-jira-query
description: Read and search intranet Jira (T&R) issues, and append comments to an issue (comment publishing requires a user-confirmed draft). Limited to the $JIRA_PROJECT project. Use when the user gives an issue number to view/analyze, asks for a JQL search, or wants to post a comment to an issue.
---

# Jira (T&R) Issue Read & Comment

Terminology: entries in Jira are called **issue** or **BR** — never "ticket".

## Env Vars

- `JIRA_BASE_URL`: API base URL including the `/rest/api/2` suffix.
- `JIRA_PROJECT`: project key.
- `JIRA_TOKEN`: PAT. Use the raw value as Bearer — never decode, never Basic auth, never as a session password (all verified to fail).

Before any call, check that the vars are set; if not, stop and ask the user. Never guess URLs or project keys.

## Project Scope (mandatory)

Only issues under `$JIRA_PROJECT`:

- JQL queries must always include `project = $JIRA_PROJECT`.
- Single-issue reads/writes require the key to belong to `$JIRA_PROJECT`; refuse keys from other projects and state the scope.

## API Calls (curl, Git Bash)

Read one issue (always trim fields; the default returns many empty `customfield_*`):

```bash
curl -s -H "Authorization: Bearer $JIRA_TOKEN" -H "Accept: application/json" \
  "$JIRA_BASE_URL/issue/<KEY>?fields=summary,status,issuetype,priority,assignee,reporter,created,updated,labels,fixVersions,components,description"
```

JQL search (results in the `issues` array):

```bash
curl -s -H "Authorization: Bearer $JIRA_TOKEN" -H "Accept: application/json" \
  "$JIRA_BASE_URL/search?jql=project%3D%27%24JIRA_PROJECT%27%20AND%20<rest>&startAt=0&maxResults=20"
```

## Related Skills (cross-reference only)

- The full BR source (WB docx) can be fetched and merged into the BR note via the `br-download` skill. This skill does not invoke it and never calls it directly; mention it to the user when the BR note lacks the original content.

## Parsing

- Key fields under `fields`: `summary`, `description` (plain text), `status.name`, `issuetype.name`, `assignee.displayName`, `reporter.displayName`, `fixVersions[].name`, `labels`.
- `customfield_*` are mostly null; skip by default. Attachments/images need a browser session; the API cannot fetch them.

## Append Comment (write — requires user-confirmed draft)

Show the comment body to the user and execute only after explicit consent; send only the confirmed text in one call. Never publish for convenience.

Mandatory pre-publish check: target issue key and comment body match the user-confirmed draft verbatim.

```bash
curl -s -X POST -H "Authorization: Bearer $JIRA_TOKEN" -H "Content-Type: application/json" \
  -d '{"body":"<comment body, Jira wiki markup>"}' \
  "$JIRA_BASE_URL/issue/<KEY>/comment"
```

- Append comments only; never change status, assignee, or any other field.
- On success, log "Published to Jira <KEY> <time>" with the body into the related note's log block (caller's job; this skill never writes notes).
