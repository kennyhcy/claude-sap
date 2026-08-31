# SkillHub API Contract

This document defines the REST API for the `bosch-skillhub` skill.
All endpoints are served at the configured `SKILLHUB_BASE_URL` (e.g. `https://skillhub.bosch.com/api/v1`).

## Authentication

All endpoints require the `x-api-key` header with a valid Personal Access Token (PAT):

```
x-api-key: sh_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

PAT tokens:
- Format: `sh_` prefix + 40 random characters
- Created via the platform UI (Profile & Settings → Personal Access Tokens)
- Can have an optional expiration date
- Token value is only shown once at creation time

Tokens are validated server-side via BCrypt hash comparison.

## Error Format

All errors return:

```json
{
  "message": "Human-readable error description"
}
```

Common HTTP status codes:
- `400 Bad Request` — Validation error (missing required fields, invalid values)
- `401 Unauthorized` — Missing or invalid `x-api-key` header
- `404 Not Found` — Resource not found
- `500 Internal Server Error` — Server-side error

---

## GET /api/v1/skills

List all skills with optional filters. Returns a flat list (no pagination).

### Query Parameters

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `search` | string | no | Keyword filter applied to name, description, and tags |
| `domain` | string | no | Filter by domain (e.g. `infrastructure`, `development`) |
| `tag` | string | no | Filter by tag (e.g. `proxy`, `jira`) |

### Response `200 OK`

```json
[
  {
    "id": "bosch-jira",
    "name": "bosch-jira",
    "description": "Manage Jira issues on rb-tracker via REST API",
    "version": "1.0",
    "author": "BD Innovation",
    "domain": "project-management",
    "tags": "[\"jira\",\"issue-tracking\",\"rest-api\",\"agile\"]",
    "requires": "[\"_bosch_sso_base\"]",
    "path": "skills/bosch-jira",
    "source": "official",
    "status": "stable",
    "installCommand": "skill install bosch-jira",
    "gitCloneUrl": "https://github.boschdevcloud.com/...",
    "endpoint": null,
    "agentCardUrl": null,
    "protocol": "A2A 1.0",
    "downloadCount": 42,
    "createdAt": "2024-01-15T10:30:00",
    "updatedAt": "2024-03-20T14:22:00"
  }
]
```

**Notes:**
- `tags` is a JSON-serialized string (array), not a native JSON array
- `requires` is a JSON-serialized string (array of skill IDs), or `null` when there are no dependencies. Metadata is sourced from `skill.json` in the skill directory (falls back to `SKILL.md` frontmatter for older skills without `skill.json`).
- `source` is either `"official"` or `"ext:{repoName}"` for extension sources
- Returns `[]` when no skills match the filters

---

## GET /api/v1/skills/{id}

Get detailed information about a specific skill.

### Path Parameters

| Param | Type | Description |
|-------|------|-------------|
| `id` | string | The skill ID |

### Response `200 OK`

```json
{
  "id": "bosch-jira",
  "name": "bosch-jira",
  "description": "Manage Jira issues on rb-tracker via REST API",
  "version": "1.0",
  "author": "BD Innovation",
  "domain": "project-management",
  "tags": "[\"jira\",\"issue-tracking\",\"rest-api\"]",
  "requires": "[\"_bosch_sso_base\",\"_shared\"]",
  "path": "skills/bosch-jira",
  "source": "official",
  "status": "stable",
  "installCommand": "skill install bosch-jira",
  "gitCloneUrl": "https://github.boschdevcloud.com/...",
  "endpoint": null,
  "agentCardUrl": null,
  "protocol": "A2A 1.0",
  "downloadCount": 42,
  "createdAt": "2024-01-15T10:30:00",
  "updatedAt": "2024-03-20T14:22:00"
}
```

**Notes:**
- `requires` is a JSON-serialized string (array of skill IDs), or `null` when there are no dependencies. Declared in `skill.json` alongside `SKILL.md`.

### Response `404 Not Found`

```json
{
  "message": "Skill not found: invalid-skill-id"
}
```

---

## GET /api/v1/skills/{id}/requires

Get the full transitive dependency list for a skill (BFS order, deduplicated).

### Path Parameters

| Param | Type | Description |
|-------|------|-------------|
| `id` | string | The skill ID |

### Response `200 OK`

```json
{
  "skillId": "sf",
  "requires": [
    {
      "id": "_bosch_sso_base",
      "name": "_bosch_sso_base",
      "description": "Shared Bosch SSO authentication helpers",
      "requires": []
    },
    {
      "id": "_shared",
      "name": "_shared",
      "description": "Common utilities shared across skills",
      "requires": []
    }
  ]
}
```

**Notes:**
- `requires` is a flat, BFS-ordered list covering all transitive dependencies. Always an array (empty if no dependencies).
- Each entry's `requires` lists that dependency's own direct dependencies.
- Dependencies not found in the registry appear with `name` equal to their `id` and `description: null`.
- Dependency IDs follow the format: bare name (e.g. `_shared`) for same-source deps, or `ext:{repoName}:{skillName}` for cross-source deps. URL-encode the ID when using it in the download path.
- Download each dependency separately via `GET /api/v1/skills/{dep_id}/download` (URL-encode `dep_id`) before installing the main skill.

### Response `404 Not Found`

```json
{
  "message": "Skill not found: invalid-skill-id"
}
```

---

## GET /api/v1/skills/{id}/download

Download a skill as a ZIP archive containing all skill files (SKILL.md and associated files).

### Path Parameters

| Param | Type | Description |
|-------|------|-------------|
| `id` | string | The skill ID |

### Response `200 OK`

- Content-Type: `application/octet-stream`
- Content-Disposition: `attachment; filename="{id}.zip"`
- Body: ZIP file bytes

The ZIP contains all files from the skill's Git directory and a `.skillhub-version` metadata file:

```json
{
  "skillId": "teams",
  "platformVersion": "3",
  "authorVersion": "1.0",
  "contentHash": "abc123...",
  "downloadedAt": "2026-07-09T14:30:00Z"
}
```

Use this file to check if a locally installed skill is up to date by comparing `platformVersion` with the `version` field from `GET /skills/{id}`.

### Response `404 Not Found`

```json
{
  "message": "Skill not found: invalid-skill-id"
}
```

---

## GET /api/v1/skills/{id}/versions

Get the version history for a skill, ordered by creation time descending.

### Path Parameters

| Param | Type | Description |
|-------|------|-------------|
| `id` | string | The skill ID |

### Query Parameters

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `limit` | integer | no | Max number of records to return (default: all) |

### Response `200 OK`

```json
[
  {
    "id": 42,
    "skillId": "teams",
    "platformVersion": "3",
    "authorVersion": "1.0",
    "commitSha": "abc123def456...",
    "contentHash": "def789...",
    "committedAt": "2026-07-09T12:00:00Z",
    "createdAt": "2026-07-09T14:13:58Z"
  },
  {
    "id": 35,
    "skillId": "teams",
    "platformVersion": "2",
    "authorVersion": "1.0",
    "commitSha": "111222...",
    "contentHash": "abc123...",
    "committedAt": "2026-06-15T08:30:00Z",
    "createdAt": "2026-06-15T08:31:00Z"
  }
]
```

**Notes:**
- `platformVersion` is the platform's internal auto-incremented version (e.g. "1", "2", "3").
- `authorVersion` is the version declared in `skill.json` / `SKILL.md` (may be null).
- `committedAt` is the Git commit timestamp; `createdAt` is when the version record was created.
- Returns `[]` if no version history exists.

### Response `404 Not Found`

```json
{
  "message": "Skill not found: invalid-skill-id"
}
```

---

## POST /api/v1/skills/feedback

Submit feedback or report an issue with a skill. Optionally creates a GitHub Issue.

### Request Body

```json
{
  "skillId": "bosch-jira",
  "text": "Got a 403 Forbidden error even with a valid PAT when trying to create an issue",
  "createGhIssue": true
}
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `skillId` | string | yes | Accepts the full skill `id` (e.g. `ext:repo:skill-name`) or just the skill name (e.g. `skill-name`). If the name matches multiple skills, the response contains a `candidates` list for user confirmation. |
| `text` | string | yes | Feedback content or issue description |
| `createGhIssue` | boolean | no | Default: `false`. When `true`, also creates a GitHub Issue |

The author is determined from the PAT token (no need to pass user info in body).

### Response `201 Created`

```json
{
  "id": 123,
  "skillId": "bosch-jira",
  "parentId": null,
  "author": "DGM1SGH",
  "text": "Got a 403 Forbidden error even with a valid PAT",
  "ghIssueNumber": 42,
  "ghIssueUrl": "https://github.com/bosch/repo/issues/42",
  "ghIssueTitle": "[Feedback] bosch-jira: Got a 403 Forbidden error...",
  "createdAt": "2024-03-20T14:22:00",
  "replies": []
}
```

**Notes:**
- `ghIssueNumber`, `ghIssueUrl`, `ghIssueTitle` are only populated when `createGhIssue` is `true`
- `replies` is always empty for newly created comments

### Response `200 OK` (Multiple skills matched)

Returned when the `skillId` matches multiple skills by name. The agent should present the candidates to the user for confirmation, then retry with the chosen `id`.

```json
{
  "message": "Multiple skills matched \"working-time\". Please ask the user to confirm which skill, then retry with the correct skill ID.",
  "candidates": [
    {
      "id": "ext:BTP AI Hub:working-time",
      "name": "working-time",
      "domain": "hr",
      "url": "/marketplace/skills/ext:BTP AI Hub:working-time"
    },
    {
      "id": "working-time",
      "name": "working-time",
      "domain": "development",
      "url": "/marketplace/skills/working-time"
    }
  ]
}
```

### Response `400 Bad Request`

```json
{
  "message": "skillId 不能为空"
}
```

### Response `404 Not Found`

Returned when the skill ID or name cannot be resolved to any existing skill.

```json
{
  "message": "Skill not found: working-time"
}
```

---

## POST /api/v1/skills/upload

Upload a new skill to the SkillHub as a ZIP package. Same format as the platform's web UI upload.

### Request

**Content-Type:** `multipart/form-data`

| Part | Type | Required | Description |
|------|------|----------|-------------|
| `metadata` | JSON | yes | Skill metadata (see below) |
| `file` | binary | yes | ZIP file containing SKILL.md and related files |

**metadata JSON structure:**

```json
{
  "name": "bosch-sap-ariba",
  "description": "Manage purchase orders in SAP Ariba",
  "domain": "procurement",
  "tags": ["sap", "ariba", "procurement"],
  "version": "1.0.0"
}
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `name` | string | yes | Skill identifier (lowercase, alphanumeric, hyphens/underscores) |
| `description` | string | yes | Brief description |
| `domain` | string | yes | Category/domain |
| `tags` | array of strings | no | List of tags |
| `version` | string | no | Default: `"1.0.0"` |

The author is determined from the PAT token (no need to pass user info in body).

### Response `201 Created`

```json
{
  "name": "bosch-sap-ariba",
  "path": "skills/bosch-sap-ariba",
  "author": "DGM1SGH",
  "message": "Skill 上传成功"
}
```

### Response `400 Bad Request`

```json
{
  "message": "<error details>"
}
```

### Response `500 Internal Server Error`

```json
{
  "message": "上传失败: <error details>"
}
```

---

## POST /api/v1/skills/{id}/pr

Submit a Pull Request to fix or improve an existing skill. Creates a new branch, commits the changed files, opens a PR, and automatically creates a SkillHub comment.

### Path Parameters

| Param | Type | Description |
|-------|------|-------------|
| `id` | string | The skill ID to submit changes for |

### Request

**Content-Type:** `multipart/form-data`

| Part | Type | Required | Description |
|------|------|----------|-------------|
| `metadata` | JSON | yes | PR metadata (see below) |
| `file` | binary | yes | ZIP file containing the complete modified skill |

**metadata JSON structure:**

```json
{
  "prTitle": "Fix: correct API endpoint URL",
  "prDescription": "Updated the endpoint from /v1 to /v2 to match the latest API version.\n\nAlso fixed authentication header handling.",
  "commentText": "Fixed the API endpoint URL that was causing 404 errors",
  "createGhIssue": true,
  "targetBranch": "main",
  "dependencySkillIds": ["dep-skill-1", "dep-skill-2"]
}
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `prTitle` | string | yes | PR title shown in GitHub |
| `prDescription` | string | yes | Detailed description of the changes |
| `commentText` | string | no | Shorter summary for the SkillHub comment (defaults to prDescription) |
| `createGhIssue` | boolean | no | Default: false. When true, also creates a GitHub Issue in the skill's repository |
| `targetBranch` | string | no | Target branch for the PR (default: repository default branch) |
| `dependencySkillIds` | array of strings | no | IDs of dependency skills that also have changes. The agent should call this endpoint separately for each. |

The author is determined from the PAT token.

### Response `201 Created`

```json
{
  "prUrl": "https://github.com/owner/repo/pull/123",
  "prNumber": 123,
  "branchName": "skillhub-pr/my-skill-1712345678",
  "commentId": 456,
  "ghIssueNumber": 42,
  "ghIssueUrl": "https://github.com/owner/repo/issues/42",
  "ghIssueTitle": "[my-skill] Fixed the API endpoint URL..."
}
```

**Notes:**
- `ghIssueNumber`, `ghIssueUrl`, `ghIssueTitle` are only populated when `createGhIssue` is `true`
- `branchName` follows the format `skillhub-pr/{skillName}-{timestamp}` for uniqueness
- A SkillHub comment (ID = `commentId`) is automatically created with a link to the PR
- The ZIP must contain the complete skill directory, not just changed files

### Response `400 Bad Request`

```json
{
  "message": "prTitle 不能为空"
}
```

### Response `404 Not Found`

```json
{
  "message": "Skill not found: invalid-skill-id"
}
```

### Response `502 Bad Gateway`

```json
{
  "message": "创建 Pull Request 权限被拒绝（403）：Git Token 可能没有写权限，或受分支保护限制。"
}
```

### Dependency Changes

When both the main skill and its dependencies need changes:

1. Submit the main skill PR first via this endpoint
2. For each dependency with changes, call this endpoint again with the dependency's `skillId`
3. Each dependency PR goes to its own repository (as resolved by the dependency's `source` field)
4. Cross-reference related PRs in the `prDescription` field

---

## PAT Management (UI Only)

PAT tokens are managed through the platform's web UI, not via API:

1. **Create PAT**: Profile & Settings → Personal Access Tokens → Create Token
2. **List PATs**: View all active tokens with masked values and expiry status
3. **Revoke PAT**: Click the revoke button next to a token

These operations require session authentication (SSO login) and are not accessible via the `x-api-key` header.
