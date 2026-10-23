---
name: br-note
description: Create and find BR notes in the folder configured by $BR_FOLDER, storing Business Request content and analysis results. Use when the work-list workflow or the user asks to save a BR as a note, create a BR note, or find a BR note.
---

# BR Note

Create and find Business Request notes in the folder set by the env var `BR_FOLDER`.

## Input Parsing

Input normally comes from the work-list workflow: BR number, title, description, reply list.

Naming: folder and md filename always use the short form `BR xxxx Title` (no `BXBRSWMS-` prefix). **Zero-pad the number to 4 digits to match the SharePoint folder convention** (BR 129 → `BR 0129 ...`, BR 42 → `BR 0042 ...`), keeping letter suffixes (e.g. `BR 2224a`); `br_id` in the metadata block uses the same zero-padded value.

## Language Rule (mandatory)

- **Never translate BR content.** The BR's original language (Jira summary/description/comments, WB docx, SharePoint documents) is the note's language — write PR/PS/Scope etc. in that original language, quoting text verbatim wherever possible.
- Do not paraphrase requirement items ([Cust. Req. n], [Prod. Req. n], [Acpt. Crit. n]) or table/form/FM names; keep original wording, only trim obvious boilerplate (page headers, "All versions on paper are copies only").
- Sections the BR does not provide content for (e.g. Analysis, written by br-analyze) may use whatever language the working conversation uses; but any quoted BR source text stays verbatim.

## Path Rules (important)

Folder = `BR xxxx Title`, md file = folder name + `.md`:

```
$BR_FOLDER/BR xxxx Title/BR xxxx Title.md
```

Windows filename sanitizing: remove the forbidden characters `\ / : * ? " < > |` outright (no full-width replacement); trim leading/trailing spaces; keep apostrophes.

## Template

````markdown
<YYYY-MM-DD HH:mm>
```
title: <title>
br_id: <xxxx>
Function Consultant:
Developer:
Effort Estimation:
```
```log
<YYYY-MM-DD HH:mm> : Created.
<YYYY-MM-DD HH:mm> <author> : <reply body, appended in chronological order>
```
---
# Scope

<Condensed rewrite of the description; left empty at creation, filled by br-analyze.>

---
# Product Requirements (PR)

<PR items from the description: [Cust. Req. n] + optional [Comment]; left empty at creation, filled by br-analyze.>

---
# Analysis

<Analysis process and evidence; filled by br-analyze, empty at creation.>

---
# Product Specification (PS)

<Final solution: [Prod. Req. n] items, English wording; filled by br-analyze, empty at creation.>
````

Rules: first line is the creation timestamp; the metadata and log blocks use triple-backtick fences; log lines follow `YYYY-MM-DD HH:mm Author : body` (no author on the Created line); sections are separated by `---` in the fixed order above. Replies and work logs go into the log block only, never into the four sections.

## Steps

1. Verify `BR_FOLDER` is set via Bash; if not, error out — never guess a path.
2. Parse br_id and title; sanitize the title into a valid folder name.
3. Find before create: Glob `$BR_FOLDER` for `BR <number>*`.
   - Existing → return its path without overwriting (cache hit).
   - Missing → `mkdir -p "$BR_FOLDER/<folder>"`, write the md with the Write tool.
4. Return the note's absolute path.

## Edge Cases

- A differently named folder with the same number exists → reuse it as cache; never create a duplicate.
- User-provided metadata (Function Consultant, start sprint, etc.) goes into the matching lines.
- Old notes may have been moved into `$BR_FOLDER/_Closed/`; include that directory when searching.

## Sync Incremental Update Rules (used by the work-list workflow sync phase)

When the work-list workflow compares a BR's latest data (with all comments) against this note, apply the following — defined here, the workflow only passes the data in:

1. **Read old**: Read the full note (log block + body sections); missing note = new entry.
2. **Match**: compare recorded replies against incoming comments by author + date; unmatched ones are new. Compare raw date strings; when in doubt, treat as new and note it in the log.
3. **Append**: add new replies at the end of the log block, `YYYY-MM-DD HH:mm Author : body` (original time, body compressed to one line in its original language). Never modify existing log lines, body sections, or metadata.
4. **Status**: update a status-like metadata field if present; do not add one if absent.
5. **Open decision** (any one = open): (a) note missing; (b) new replies found; (c) last reply's author is not the current user (match against `$JIRA_USERNAME`; if authorship is unclear, treat as open and note it).
6. **fileAction**: created / updated / unchanged (no write when unchanged).
7. Only this entry's note file may be written; never write Jira/SAP.
