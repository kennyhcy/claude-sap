---
name: br-download
description: Download the latest WB (Work Book) docx of a BR from SharePoint (SAP EWM BR Management site), convert it to md, and incrementally merge it into the BR note under $BR_FOLDER (append-only, differences marked). Use when the user says "sync BR xxxx / download BR xxxx", or when br-analyze needs the latest BR content before analysis.
---

# BR WB Download & Incremental Sync

Download the WB docx of a BR from the SharePoint BR Management site (folder `BXBRSWMS-<number>/`), convert it to md, and merge it incrementally into the BR note.

## Hard Constraints

- **Incremental, never delete**: content already in the note but absent from the new WB is kept; source differences are marked with `[Comment]` lines or log lines, never silently removed.
- SharePoint requires SSO: bare WebFetch/curl gets 403; use this skill's Edge scripts (`scripts/sp_fetch.ps1` / `sp_download.ps1`).
- Output files go to `workfolder/` (project output directory rule).

## SharePoint Access Mechanism

- Site: `https://bosch.sharepoint.com/sites/20032140`, list page `https://bosch.sharepoint.com/sites/20032140/Shared%20Documents/Forms/AllItems.aspx`.
- A BR lives in exactly one of the top-level BR folders (configured in `$SP_BR_FOLDERS`, see below) — by BR status: open / done / cancelled. Sub-folder per BR: `BXBRSWMS-<number>/`.
- Same principle as the sap-note skill's get_sapnote.ps1: the HttpOnly SSO cookie of a dedicated Chromium profile; headless/windowed Edge with a dedicated profile is the only reliable channel.
- Dedicated profile: `%LOCALAPPDATA%\ClaudeSharePointProfile` (first use creates the login state via headless `--dump-dom`; if the page title is "Sign in" instead of the site name, the session expired — open the site in a windowed Edge for the user to log in once, then close it).

## Env Vars

- `SP_BR_SITE`: SharePoint site base URL (e.g. `https://bosch.sharepoint.com/sites/20032140`).
- `SP_BR_FOLDERS`: JSON array of top-level BR folder names under `Shared Documents/`, ordered by search priority (e.g. `["01_OPEN_BRs","05_DONE_BRs","10_CANCELLED_BRs"]`). A BR is looked up in these folders in order; the first folder containing `BXBRSWMS-<number>/` wins.

If either var is missing or empty, stop and ask the user to configure them in `.env.json`.

## Steps

### 1. Locate the BR folder and file

1. Verify `BR_FOLDER`, `SP_BR_SITE`, `SP_BR_FOLDERS` are set via Bash.
2. For each folder name in `$SP_BR_FOLDERS` (in order), fetch the list-page DOM of its BR sub-folder with `scripts/sp_fetch.ps1 -Url "<folder AllItems.aspx URL>"` (headless Edge --dump-dom):
   `<SP_BR_SITE>/Shared%20Documents/Forms/AllItems.aspx?id=<URL-encoded path %2Fsites%2F...%2FShared%20Documents%2F<folder>%2FBXBRSWMS%2D<number>>`
   Stop at the first folder where the sub-folder yields at least one `.docx`. Empty result in one folder is not an error — continue with the next folder (the BR may be done/cancelled and moved).
3. Extract `.docx` filenames from the DOM (regex `[A-Za-z0-9_\-\.\(\)]+\.docx`, excluding URL-encoding fragments); if the title line contains "Sign in", stop and ask the user to log in first.
4. No docx in any configured folder or no sub-folder at all → report as-is and stop; never guess filenames.

### 2. Download the docx

1. Target directory: `workfolder/` (project root, gitignored).
2. Download with `scripts/sp_download.ps1 -Url "<download.aspx?SourceUrl=<URL-encoded file path>" -OutFile "workfolder/<name>.docx"`. The script uses windowed Edge to trigger the download (lands in the system Downloads folder, then copies to OutFile).
3. Troubleshooting order: expired profile session (windowed Edge login first) → stale same-name files in Downloads (clean `(n).docx` copies and retry) → insufficient permissions (report to user).

### 3. Convert to md

```bash
pandoc "workfolder/<name>.docx" -t gfm -o "workfolder/<name>.md" --extract-media=workfolder/
```

Read the converted file in full. Fixed WB sections: History / General information / Process requirements (Functional + Quality) / Product specification / Cut-over activities.

### 4. Incremental merge into the BR note

Glob `$BR_FOLDER` (including `_Closed/`) for `BR <number>*`; if the note is missing, create the skeleton following the br-note skill's template (the workflow/main session invokes br-note; this skill does not call other skills), then do a full fill (no existing content to protect).

When the note exists, compare the WB md against the note section by section and merge in the direction "WB → note", **append-only**:

| WB section | Note target | Rule |
|---|---|---|
| History | ```log block | Append one line: `<now> : Synced SharePoint WB (v<version> <date> <author>) -> workfolder/<md path>`; WB version-history highlights go into the same or a following log line |
| General information | `# Scope` | Merge affected warehouses/systems/interfaces/classification into Scope; keep identical existing content, append WB additions with `（per SharePoint WB v<version>）` |
| Process requirements > Functional | `# Product Requirements (PR)` | Append WB-only items/Comments at the end of PR; keep matching content |
| Quality requirements | `# Product Requirements (PR)` | Merge as a subsection (`Quality requirements (from WB):`) at the end of PR |
| Product specification | `# Product Specification (PS)` | Same rule as PR: append WB-only [Prod. Req. n]/[Comment]/Reason; WB screenshot references become `[Comment]` lines pointing to the workfolder md/media |
| Cut-over activities | (no note section) | Substantive content → append as a note under PR or a log hint; empty template → ignore |

**Reverse difference (note has it, WB does not)**: keep untouched and add nearby:

```
[Comment] (sync <YYYY-MM-DD>) Only in the note, not in the latest WB — kept for reference.
```

**Conflict (both sides have it, content differs)**: keep the note's version and append `[Comment] (sync <date>) Differs from WB v<version>: WB says "<WB excerpt>", note kept / to be confirmed.`

After syncing: append a sync record to the log block (time, WB version, difference summary), and return a summary (what was added, what was marked, note path, workfolder docx/md paths).

## Notes

- This skill only downloads/converts/syncs; it does not analyze content (analysis goes to br-analyze) and never writes back to Jira/SharePoint.
- No SAP operations in this skill; never call MCP within its flow.
- If the docx contains sensitive customer data, keep it in `workfolder/` (gitignored); never send it out.
