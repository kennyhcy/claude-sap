---
name: defect-note
description: Create and find defect notes in the folder configured by $DEFECT_FOLDER, storing defect content and analysis results. Use when the work-list workflow or the user asks to save a defect as a note, create a defect note, or find a defect note.
---

# Defect Note

Create and find defect notes in the folder set by the env var `DEFECT_FOLDER`.

## Input Parsing

Input normally comes from the work-list workflow: defect number, title, description, reply list.

Naming: `Defect xxxx Title` — keep the number as-is (letter suffixes allowed); keep the rest of the title verbatim (no translation, no case changes, underscores/colons preserved).

## Path Rules (important)

Target folder: `$DEFECT_FOLDER`. A defect is a **single md file**, no subfolder (unlike br-note, which uses folders):

```
$DEFECT_FOLDER/Defect xxxx Title.md
```

Windows filename sanitizing: remove the forbidden characters `\ / : * ? " < > |` outright; trim leading/trailing spaces; keep internal runs of spaces; keep apostrophes, underscores, hyphens.

## Template

````markdown
<YYYY-MM-DD HH:mm>
```
title: <sanitized title, identical to the filename without .md>
defect_id: "<xxxx>"
System:
Warehouse:
Data:
Assigned:
Target sprint:
```
```log
<YYYY-MM-DD HH:mm> : Defect created.
<YYYY-MM-DD HH:mm> <author> : <reply/work-log body, appended in chronological order>
```
---
# Issue

<Condensed rewrite of the description: symptom + impact; filled by defect-analyze.>

---
# Analysis

<Investigation path, verified details with sources, rejected hypotheses; filled by defect-analyze, empty at creation.>

---
# Root cause



---
# Solution

<Fix + draft reply; filled by defect-analyze, empty at creation.>
````

Rules: the first line is the creation timestamp (`YYYY-MM-DD HH:mm`, local time via Bash `date +"%F %R"`); metadata goes in a triple-backtick block (not YAML frontmatter) following the existing note style; `defect_id` is double-quoted; fill known fields from ALM data, leave the rest blank; log lines follow `YYYY-MM-DD HH:mm Author : body`; sections in the fixed order above; replies and work logs go into the log block only.

## Steps

1. Verify `DEFECT_FOLDER` is set via Bash; if not, error out — never guess a path.
2. Parse defect_id and title; sanitize the title into a valid filename.
3. Find before create: Glob `$DEFECT_FOLDER` (including `_Closed/`) for `Defect <number>*`.
   - Existing → return its path without overwriting (cache hit).
   - Missing → write the md with the Write tool (timestamp via Bash `date +"%F %R"`).
4. Return the note's absolute path.

## Edge Cases

- A same-name/same-number file exists → inform and stop; never overwrite.
- Old notes may have been moved into `$DEFECT_FOLDER/_Closed/`; include that directory when searching.

## Sync Incremental Update Rules (used by the work-list workflow sync phase)

When the work-list workflow compares a defect's latest data (with all dev-comments) against this note, apply the following — defined here, the workflow only passes the data in:

1. **Read old**: Read the full note (log block + Issue/Analysis/Root cause/Solution); missing note = new entry.
2. **Match**: compare recorded replies against incoming comments by author + date; normalize ALM date formats to YYYY-MM-DD when comparing; when in doubt, treat as new and note it in the log.
3. **Append**: add new replies at the end of the log block, `YYYY-MM-DD HH:mm Author : body` (normalized time, body compressed to one line in its original language). Never modify existing log lines, body sections, or metadata.
4. **Status**: update metadata fields (Target sprint/Assigned etc.) only on explicit new values; otherwise leave untouched.
5. **Open decision** (any one = open): (a) note missing; (b) new replies found; (c) the `<ID>` in the last reply's signature is not `$ALM_USER`.
6. **fileAction**: created / updated / unchanged (no write when unchanged).
7. Only this entry's note file may be written; never write ALM/SAP.
