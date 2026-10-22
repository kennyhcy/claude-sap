# Project: SAP Agent

## Overview

- A fully-informed agent for the SAP S/4 system.
- Connects to SAP S/4 HANA via mcp-abap-adt-b (instance depends on the environment).
- Tech stack: ABAP + TypeScript/MCP.
- Skills and workflows live under `.claude/`; output files go to `workfolder/` (gitignored).

## 🔴 Mandatory: user authorization before code write

Any ABAP code creation/modification (`CreateObject` / `UpdateObjectSource` / `ActivateObject`) requires prior user approval. Without it: analyze, propose, or stand by — never execute. Tasks must be labeled「已授权可执行」or「未授权，仅分析不执行」.

Enforcement: the PreToolUse hook in `.claude/settings.json` intercepts these three tools and returns `ask` for user confirmation on every call, including in subagents.

## Conventions

- Layering: a skill performs a single basic operation and never calls other skills; a workflow only orchestrates steps; multi-skill operations become workflows.
- Skills: read the full SKILL.md before invoking; never rely on the injected description alone. EWM knowledge & data queries use the `sap-ewm` skill (SKILL.md is an index; read the matching `references/` file first).
- Naming: skills for the same task type share one prefix; see the `skill-writer` skill when creating or modifying skills.
- No guessing technical objects: describe the business goal; reference table/field/class/FM names only after MCP verification.
- MCP data queries are the executing task's own responsibility (including `GetTableContents`).

Note: the user is a senior SAP consultant — answers must include technical details: tables, programs, classes, methods, views, transaction codes.
