---
name: br-analyze
description: Section paradigm and write rules for BR analysis results (# Scope / # Product Requirements (PR) / # Analysis / # Product Specification (PS)) — rules only, no evidence gathering, no write-back, no sync. Used by the work-analyze workflow when analyzing a BR to write results into the BR note sections; also usable as a reference for manual analysis in the main session.
---

# BR Analysis Paradigm

Defines how BR analysis results are organized and written into the note — a pure rule document:

- Evidence gathering (MCP read-only, sap-note, kb-search) → the workflow's evidence phase or the caller.
- SharePoint WB sync → `br-download` skill.
- Note skeleton and reply appending → `br-note` skill.
- Publishing replies to Jira → `br-jira-query` (comment append, user-confirmed draft required).
- Full five-step flow → `work-analyze` workflow.

## Note Write Rules

- Markdown; condensed rewrites in Chinese, quotes of the counterpart's original text keep their language.
- Write only this BR's note file (Edit to append/revise); never touch other files.
- Existing section content: reference what still holds, point out and revise what is outdated.
- Mark unverifiable findings as「未验证」; never fabricate; cite data sources for technical details.
- Replies and work logs go **only** into the ```log block at the top of the note (`YYYY-MM-DD HH:mm Author : body`), never into the body sections.

## BR Section Paradigm

| Section | Content |
|---|---|
| `# Scope` | Condensed rewrite of the description: business background + warehouse/system + key objects (OBD/material/stock situation); one or two paragraphs stating what the BR solves. Never repeat the Jira text verbatim. |
| `# Product Requirements (PR)` | PR items from the Jira description as a list (`[Cust. Req. n]` + optional `[Comment]`), original semantics kept; this is the requirement baseline, never rewrite requirements. |
| `# Analysis` | Analysis process and evidence: per-PR analysis, verified technical details (FM/class/method/table/config/transaction code with data sources), alternative-trade-off conclusions (including rejected options and why), PoC results. Requirement baseline follows the synced WB when available (state it when not synced). |
| `# Product Specification (PS)` | Final solution: `[Prod. Req. n]` items — requirement statement + Reason/How to (down to class/method/table/FM level) + `[Comment]` with technical details and PoC records. PS is the deliverable for review/development; wording in English. |

Draft reply: when PR/PS contains points needing business/requester confirmation, draft one reply ready to paste into Jira (no signature; language matches the counterpart's comments, or Chinese).

## Red Lines

- SAP system read-only; ABAP write operations (CreateObject/UpdateObjectSource/ActivateObject) are out of scope — request authorization per project rules when needed.
- This skill never publishes replies; publishing and user confirmation live in the work-analyze workflow / main session.
