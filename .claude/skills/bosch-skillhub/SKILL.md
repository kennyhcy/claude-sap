---
name: bosch-skillhub
description: >
  Find, download, and manage AI skills in the Bosch SkillHub.
  Use when the user asks "is there a skill for X", wants to browse available
  skills, download a skill, report problems with skills, upload new skills,
  or submit pull requests to fix existing skills.
  Trigger phrases: "what skills are available", "find a skill", "download skill",
  "skill for X", "report a problem with skill", "submit feedback", "upload skill",
  "fix skill", "submit a fix", "create a PR for skill".
compatibility: >
  Requires SKILLHUB_API_KEY and SKILLHUB_BASE_URL environment variables.
  Corporate proxy required on Bosch network.
metadata:
  author: BD Innovation
  version: "2.0"
  tags: skillhub, discovery, search, feedback, download
---

# Bosch SkillHub Navigator

Interact with the Bosch SkillHub to find, download, and manage AI skills.

## Prerequisites

**Required Environment Variables:**

Both variables MUST be set before using this skill. Check for them before any API call.

```bash
# PowerShell
$env:SKILLHUB_API_KEY = "sh_your_pat_token_here"
$env:SKILLHUB_BASE_URL = "https://bosch-ai-agency.cfapps.eu10.hana.ondemand.com/api/v1"

# Bash (Linux/macOS)
export SKILLHUB_API_KEY="sh_your_pat_token_here"
export SKILLHUB_BASE_URL="https://bosch-ai-agency.cfapps.eu10.hana.ondemand.com/api/v1"
```

**How to get a PAT:**
1. Log in to the SkillHub platform via your browser
2. Click your avatar in the top-right corner → "Profile & Settings"
3. Under "Personal Access Tokens", click "Create Token"
4. Enter a token name and expiry period, then click "Generate"
5. **Copy the token immediately** — it will only be shown once

Helper variables used throughout this skill:

```bash
BASE="${SKILLHUB_BASE_URL:?ERROR: SKILLHUB_BASE_URL not set. Please set this environment variable.}"
API_KEY="x-api-key: ${SKILLHUB_API_KEY:?ERROR: SKILLHUB_API_KEY not set. Please create a PAT in SkillHub Profile & Settings.}"
PROXY="https_proxy=http://localhost:3128"
```

**Runtime Check:** Before executing any API call, verify both environment variables are set. If either is missing, stop and prompt the user to configure them.

---

## 1. Find / Search Skills

### Semantic search (preferred)

When the user describes a need or task without knowing the skill name, fetch all skills and use reasoning to surface the best matches.

```bash
$PROXY curl -s -H "$API_KEY" "$BASE/skills" | python -m json.tool
```

Analyze the returned list and explain which skills are most relevant to the user's need and why.

### Keyword search

When the user provides specific search terms:

```bash
$PROXY curl -s -H "$API_KEY" "$BASE/skills?search=<term>" | python -m json.tool
```

### Filter by domain

Available domains: `development`, `infrastructure`, `project-management`, `procurement`, `logistics`, `product`, `finance`, `quality`, `hr`, `data`

```bash
$PROXY curl -s -H "$API_KEY" "$BASE/skills?domain=infrastructure" | python -m json.tool
```

### Filter by tag

```bash
$PROXY curl -s -H "$API_KEY" "$BASE/skills?tag=proxy" | python -m json.tool
```

### Full list

```bash
$PROXY curl -s -H "$API_KEY" "$BASE/skills" | python -m json.tool
```

Display results as a table: **name** | **domain** | **description** | **tags** | **version** | **downloadCount**

### Response Format

```json
[
  {
    "id": "bosch-jira",
    "name": "bosch-jira",
    "description": "Manage Jira issues on rb-tracker via REST API",
    "version": "1.0",
    "author": "BD Innovation",
    "domain": "project-management",
    "tags": "[\"jira\",\"issue-tracking\",\"rest-api\"]",
    "path": "skills/bosch-jira",
    "source": "official",
    "status": "stable",
    "installCommand": "skill install bosch-jira",
    "gitCloneUrl": "https://github.boschdevcloud.com/...",
    "downloadCount": 42,
    "createdAt": "2024-01-15T10:30:00",
    "updatedAt": "2024-03-20T14:22:00"
  }
]
```

Note: `tags` is returned as a JSON string (array serialized), parse it if needed.

---

## 2. Get Skill Details

Get detailed information about a specific skill:

```bash
$PROXY curl -s -H "$API_KEY" "$BASE/skills/{skill_id}" | python -m json.tool
```

### Response Format

```json
{
  "id": "bosch-jira",
  "name": "bosch-jira",
  "description": "Manage Jira issues on rb-tracker via REST API",
  "version": "1.0",
  "author": "BD Innovation",
  "domain": "project-management",
  "tags": "[\"jira\",\"issue-tracking\"]",
  "path": "skills/bosch-jira",
  "source": "official",
  "status": "stable",
  "installCommand": "skill install bosch-jira",
  "gitCloneUrl": "https://github.boschdevcloud.com/...",
  "downloadCount": 42,
  "createdAt": "2024-01-15T10:30:00",
  "updatedAt": "2024-03-20T14:22:00"
}
```

### Error Response (404)

```json
{
  "message": "Skill not found: invalid-skill-id"
}
```

---

## 3. Check Skill Dependencies

Skills declare dependencies in a `skill.json` file alongside their `SKILL.md`. Before downloading, check if the skill has required dependencies:

```bash
$PROXY curl -s -H "$API_KEY" "$BASE/skills/{skill_id}/requires" | python -m json.tool
```

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

- `requires` is a flat BFS-ordered list of all transitive dependencies (deduplicated).
- If `requires` is an empty array, the skill has no dependencies.

### Error Response (404)

```json
{
  "message": "Skill not found: invalid-skill-id"
}
```

---

## 4. Download Skill (with Dependencies)

Skills may declare dependencies in their `skill.json`. Always check dependencies first, then download each package separately (one ZIP per skill).

### Step 1 — Check dependencies

```bash
$PROXY curl -s -H "$API_KEY" "$BASE/skills/{skill_id}/requires" | python -m json.tool
```

### Step 2 — Download dependencies first (if any)

For each dependency ID in the `requires` list:

```bash
$PROXY curl -s -H "$API_KEY" -o {dep_id}.zip "$BASE/skills/$(python3 -c "import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1]))" "{dep_id}")/download"
```

> **Note:** Dependency IDs for cross-source deps contain colons (e.g. `ext:hub-name:skill-name`). URL-encode the ID in the path, and replace colons with dashes in the output filename to avoid file system issues on Windows.

### Step 3 — Download the main skill

```bash
$PROXY curl -s -H "$API_KEY" -o {skill_id}.zip "$BASE/skills/{skill_id}/download"
```

Each ZIP contains that skill's `SKILL.md`, `skill.json`, and all associated files. Install dependencies before the main skill.

After downloading, you can:
- Extract and inspect the SKILL.md for usage instructions
- Use `installCommand` from the skill details to install
- Or `git clone` using `gitCloneUrl` if available

### Error Response (404)

```json
{
  "message": "Skill not found: invalid-skill-id"
}
```

---

## 5. Submit Feedback / Report an Issue

Use when a skill did not work as expected, produced wrong output, or caused problems.

### Step 1 — Collect information

| Field | How to get it |
|-------|--------------|
| `skillId` | The skill ID or name. You can use the full `id` from `GET /api/v1/skills` (e.g. `ext:repo:skill-name`), or just the skill name (e.g. `skill-name`). If the name matches multiple skills, the API returns a `candidates` list — present it to the user for confirmation, then retry with the chosen `id`. |
| `text` | Ask the user: "What went wrong with this skill?" |
| `createGhIssue` | Ask if user wants to create a GitHub Issue for tracking (optional, default: false) |

### Step 2 — Confirm before submitting

Show the feedback content and ask the user to confirm. Feedback is visible to the SkillHub maintainers.

### Step 3 — POST

```bash
$PROXY curl -s -X POST "$BASE/skills/feedback" \
  -H "$API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "skillId": "<skill-id>",
    "text": "<feedback or issue description>",
    "createGhIssue": true
  }'
```

### Response (201 Created)

```json
{
  "id": 123,
  "skillId": "bosch-jira",
  "parentId": null,
  "author": "DGM1SGH",
  "text": "Got a 403 error when trying to create an issue",
  "ghIssueNumber": 42,
  "ghIssueUrl": "https://github.com/bosch/repo/issues/42",
  "ghIssueTitle": "[Feedback] bosch-jira: Got a 403 error...",
  "createdAt": "2024-03-20T14:22:00",
  "replies": []
}
```

Note: `ghIssueNumber`, `ghIssueUrl`, and `ghIssueTitle` are only populated when `createGhIssue` is `true`.

---

## 6. Submit a New Skill

Use when the user wants to contribute a skill to the SkillHub. Upload a ZIP package containing `SKILL.md`, `skill.json`, and any other files.

### skill.json format

Every skill directory should contain a `skill.json` alongside `SKILL.md`. This file carries all machine-readable metadata — the SkillHub scanner reads `skill.json` first and falls back to `SKILL.md` frontmatter only when `skill.json` is absent.

```json
{
  "name": "my-skill",
  "description": "One-line description of what this skill does",
  "version": "1.0",
  "author": "Your Name",
  "domain": "development",
  "tags": ["tag1", "tag2"],
  "requires": ["_shared", "sf"]
}
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `name` | string | yes | Kebab-case identifier (lowercase, alphanumeric, hyphens/underscores) |
| `description` | string | yes | Brief description shown in the marketplace |
| `version` | string | no | Default: `"1.0"` |
| `author` | string | no | Author display name |
| `domain` | string | no | Category (e.g. `development`, `hr`, `infrastructure`) |
| `tags` | array | no | List of tags for search |
| `requires` | array | no | Skill IDs that must be installed first; omit or leave empty if none. Use bare name (e.g. `"_shared"`) for same-source deps, or `"ext:repo-name:skill-name"` for cross-source deps |

`SKILL.md` should contain only human/LLM-readable instructions — no frontmatter needed when `skill.json` is present.

### Step 1 — Collect metadata and create skill files

Collect from the user: skill name, description, domain, tags, version, and any dependencies.

1. Write the `skill.json` with the collected metadata.
2. Write the `SKILL.md` with usage instructions (no frontmatter needed).
3. Create a ZIP archive containing both files and any additional resources.

### Step 2 — Confirm before uploading

Show the metadata and confirm with the user before uploading.

### Step 3 — Upload

Send the ZIP file as multipart/form-data:

```bash
# First, create the ZIP file
zip /tmp/skill.zip /tmp/skill/*

# Then upload
$PROXY curl -s -X POST "$BASE/skills/upload" \
  -H "$API_KEY" \
  -F "metadata={\"name\":\"<skill-name>\",\"description\":\"<desc>\",\"domain\":\"<domain>\",\"tags\":[\"<tag1>\"],\"version\":\"1.0\"};type=application/json" \
  -F "file=@/tmp/skill.zip;type=application/zip"
```

| Part | Type | Required | Notes |
|------|------|----------|-------|
| `metadata` | JSON | yes | Skill metadata as `application/json` (used as fallback if skill.json is absent from ZIP) |
| `file` | binary | yes | ZIP file containing SKILL.md, skill.json, and related files |

### Response (201 Created)

```json
{
  "name": "bosch-sap-ariba",
  "path": "skills/bosch-sap-ariba",
  "author": "DGM1SGH",
  "message": "Skill 上传成功"
}
```

Show the result to the user. The skill will be reviewed by the SkillHub team before being published.

---

## 7. Update / Check Skill Version

When the user wants to ensure they have the latest version of a skill, compare the locally installed version with the SkillHub platform version and update if needed.

**Trigger phrases**: "use the latest X skill", "update X skill", "is my X skill up to date", "check X version"

### Step 1 — Query platform latest version

```bash
$PROXY curl -s -H "$API_KEY" "$BASE/skills/{skill_id}" | python -m json.tool
```

Extract `version` (platform version, e.g. "3") and `authorVersion` from the response.

### Step 2 — Check locally installed version

Read the `.skillhub-version` file inside the locally installed skill's directory. This file is injected into every downloaded ZIP and records the platform version at download time.

```bash
cat /path/to/skills/{skill_id}/.skillhub-version
```

Example `.skillhub-version` content:

```json
{
  "skillId": "teams",
  "platformVersion": "2",
  "authorVersion": "1.0",
  "contentHash": "abc123...",
  "downloadedAt": "2026-07-01T10:00:00Z"
}
```

If `.skillhub-version` does NOT exist, the skill was downloaded before this feature was added (or never installed). Treat as "not installed" or "unknown version" and proceed to download.

### Step 3 — Compare versions

- **No `.skillhub-version` file** → skill was never installed or downloaded with an older tool. Proceed to download (Step 4).
- **`platformVersion` < platform `version`** → update available. Tell the user the current and latest versions, then proceed to download.
- **`platformVersion` == platform `version`** → already up to date. Inform the user and stop.

### Step 4 — Download and install

Follow the same flow as Section 4 (Download Skill with Dependencies):
1. Check dependencies: `GET /skills/{id}/requires`
2. Download dependencies first (if any)
3. Download the main skill: `GET /skills/{id}/download`
4. Extract and replace the existing local skill files

### Optional: View version history

To show the user what changed between versions:

```bash
$PROXY curl -s -H "$API_KEY" "$BASE/skills/{skill_id}/versions?limit=3" | python -m json.tool
```

This returns the most recent version records with `platformVersion`, `authorVersion`, `commitSha`, and `committedAt`.

---

## 8. Submit a Pull Request to Fix a Skill

Use when the user wants to fix or improve an existing skill by submitting changes back to the skill's Git repository.

**Trigger phrases**: "fix skill X", "submit a fix for", "create a PR for skill", "improve skill X", "I found a bug in skill X"

### Step 1 — Download and modify the skill locally

Follow Section 4 (Download Skill with Dependencies) to get the latest version of the skill and its dependencies.

1. Download the skill: `GET /skills/{id}/download`
2. Check dependencies: `GET /skills/{id}/requires`
3. Download dependencies if any
4. Extract and inspect the files locally
5. Make the necessary changes to fix the issue

If dependency packages also need changes, modify them as well. Each changed skill/dependency will be submitted as a separate PR.

### Step 2 — Collect PR metadata

| Field | How to get it |
|-------|--------------|
| `prTitle` | Ask the user: "What title should the PR have?" (e.g. "Fix: correct API endpoint URL") |
| `prDescription` | Ask the user: "Please describe the changes you made" (detailed description of what was fixed and why) |
| `commentText` | Optional. A shorter summary for the SkillHub comment. Defaults to `prDescription` if not provided. |
| `createGhIssue` | Ask if user wants to also create a GitHub Issue for tracking (optional, default: false) |

### Step 3 — Package modified files and confirm

1. Create a ZIP archive containing ALL files of the skill (not just the modified ones). Include `SKILL.md`, `skill.json`, and all related files.
2. Show the PR title, description, and list of changed files to the user for confirmation.

> **Important**: The ZIP must contain the complete skill directory (all files), not just the changed files. The system will replace the entire skill directory in the repository.

### Step 4 — Submit the PR

Send the ZIP file as multipart/form-data:

```bash
# Create the ZIP containing all modified skill files
zip /tmp/skill-fix.zip /tmp/skill-fix/*

# Submit the PR
$PROXY curl -s -X POST "$BASE/skills/{skill_id}/pr" \
  -H "$API_KEY" \
  -F "metadata={\"prTitle\":\"Fix: correct API endpoint URL\",\"prDescription\":\"Updated the endpoint from /v1 to /v2...\",\"createGhIssue\":true};type=application/json" \
  -F "file=@/tmp/skill-fix.zip;type=application/zip"
```

| Part | Type | Required | Notes |
|------|------|----------|-------|
| `metadata` | JSON | yes | PR metadata as `application/json` |
| `file` | binary | yes | ZIP file containing the complete modified skill |

**metadata JSON structure:**

```json
{
  "prTitle": "Fix: correct API endpoint URL",
  "prDescription": "Updated the endpoint from /v1 to /v2 to match the latest API version.\n\nAlso fixed authentication header handling.",
  "commentText": "Fixed the API endpoint URL that was causing 404 errors",
  "createGhIssue": true,
  "targetBranch": "main"
}
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `prTitle` | string | yes | PR title shown in GitHub |
| `prDescription` | string | yes | Detailed description of changes |
| `commentText` | string | no | Shorter summary for SkillHub comment (defaults to prDescription) |
| `createGhIssue` | boolean | no | Default: false. When true, also creates a GitHub Issue |
| `targetBranch` | string | no | Target branch for the PR (default: repository default branch) |
| `dependencySkillIds` | array | no | List of dependency skill IDs that also have changes (the agent should call this endpoint separately for each) |

### Response (201 Created)

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
- The system creates a new branch `skillhub-pr/{skillName}-{timestamp}` for each PR
- A SkillHub comment is automatically created referencing the PR

### Dependency Changes

If the user also modified dependency packages:

1. Package each changed dependency as a separate ZIP
2. Call `POST /skills/{dep_id}/pr` for each dependency, with its own PR title and description
3. The dependency PRs are independent — each goes to the dependency's own repository
4. In the main skill's `prDescription`, mention the related dependency PRs for cross-reference

### Error Responses

- `400 Bad Request` — Validation error (missing required fields, invalid ZIP)
- `404 Not Found` — Skill not found
- `502 Bad Gateway` — Git API failure (token permissions, branch protection, etc.)

---

## Examples

| User says | Action |
|-----------|--------|
| "Is there a skill for SAP?" | Semantic search — fetch all skills, surface relevant matches |
| "List all infrastructure skills" | `GET /skills?domain=infrastructure` |
| "Download the Jira skill" | Check `GET /skills/bosch-jira/requires`, then download deps + `GET /skills/bosch-jira/download` |
| "Show me details about skill X" | `GET /skills/{id}` |
| "Does skill X have dependencies?" | `GET /skills/{id}/requires` |
| "The Jira skill gave me a 403 error" | Submit feedback: `{skillId: "bosch-jira", text: "Got 403 error..."}` |
| "I want to submit a new skill for SAP Ariba" | Guide user to provide SKILL.md content, create ZIP, then `POST /skills/upload` |
| "What skills are available?" | `GET /skills`, display as table |
| "Use the latest teams skill" | Query `GET /skills/teams` for platform version, check local `.skillhub-version`, download if outdated |
| "Is my Jira skill up to date?" | Compare local `platformVersion` in `.skillhub-version` vs platform `version`, report status |
| "Check what changed in skill X" | `GET /skills/{id}/versions?limit=3` to see recent version history |
| "Fix the Jira skill's API endpoint" | Download skill, make changes locally, package as ZIP, `POST /skills/bosch-jira/pr` |
| "Create a PR for my changes to skill X" | Confirm changes, collect PR title/description, `POST /skills/{id}/pr` |

---

## Important Notes

- **Confirm before write**: Feedback submissions and skill proposals are visible to the SkillHub team — always show the payload and get confirmation before POSTing.
- **PAT Token**: Create PAT in the platform's Profile & Settings page. Token is shown only once at creation time.
- **Environment Variables**: Both `SKILLHUB_API_KEY` and `SKILLHUB_BASE_URL` MUST be set before any API call. Check for them first and prompt the user if missing.
- **Proxy**: Required on the corporate network. Prefix every `curl` command with `https_proxy=http://localhost:3128`.
- **API key missing**: If `SKILLHUB_API_KEY` is not set, prompt the user to create a PAT in Profile & Settings.
- **Version tracking**: Every downloaded ZIP contains a `.skillhub-version` file recording the `platformVersion` at download time. Use this file to check if a local skill is up to date — compare `platformVersion` with the `version` field from `GET /skills/{id}`.
