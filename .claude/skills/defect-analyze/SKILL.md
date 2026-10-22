---
name: defect-analyze
description: Section paradigm and write rules for defect analysis results (# Issue / # Analysis / # Root cause / # Solution) — rules only, no evidence gathering, no write-back, no sync. Used by the work-analyze workflow when analyzing a defect to write results into the defect note sections; also usable as a reference for manual analysis in the main session.
---

# Defect Analysis Paradigm

Defines how defect analysis results are organized and written into the note — a pure rule document:

- Evidence gathering (MCP read-only, sap-note, kb-search) → the workflow's evidence phase or the caller.
- Note skeleton and reply appending → `defect-note` skill.
- Publishing replies to ALM → `defect-alm-query` (comment append, user-confirmed draft required).
- Full five-step flow → `work-analyze` workflow.

## Note Write Rules

- Markdown; condensed rewrites in Chinese, quotes of the counterpart's original text keep their language.
- Write only this defect's note file (Edit to append/revise); never touch other files.
- Existing section content: reference what still holds, point out and revise what is outdated.
- Mark unverifiable findings as「未验证」; never fabricate; cite data sources for technical details.
- Replies and work logs go **only** into the ```log block at the top of the note (`YYYY-MM-DD HH:mm Author : body`), never into the body sections.

## Defect Section Paradigm

| Section | Content |
|---|---|
| `# Issue` | Condensed rewrite of the description: symptom (error message/transaction code/warehouse/document number) + impact scope; states what the defect is. Never repeat the ALM text verbatim. |
| `# Analysis` | Analysis process and evidence: investigation paths, verified technical details (with data sources), rejected hypotheses and why. |
| `# Root cause` | Confirmed root-cause statement — one or two sentences on the technical origin (which object/config/logic flaw), consistent with the Analysis conclusion, no repetition of the process. |
| `# Solution` | Fix (Customizing path / code change direction / SAP Note / operation steps; list trade-offs and a recommendation when multiple options) + **draft reply**: ready to paste into ALM (no signature; language matches the counterpart's comments, or Chinese). |

## Red Lines

- SAP system read-only; ABAP write operations (CreateObject/UpdateObjectSource/ActivateObject) are out of scope — request authorization per project rules when needed.
- This skill never publishes replies; publishing and user confirmation live in the work-analyze workflow / main session.
