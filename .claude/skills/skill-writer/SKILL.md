---
name: skill-writer
description: Meta-skill for creating or modifying skills in this project. Enforces format conventions, naming rules, and mandatory sync obligations (CHANGELOG, env vars, gitignore, samples, cross-references). Use when the user asks to create, rewrite, or refactor a skill.
---

# Skill Writer

Create or modify a skill under `.claude/skills/<name>/`, then run the sync checklist so every mandatory companion file stays consistent. Workflow: gather requirements → draft/modify SKILL.md → run sync checklist → report.

## Format Rules

- All project documentation files (SKILL.md, CHANGELOG.md, README.md) must be written in English. Keep them concise and normative; do not write examples. Historical CHANGELOG entries keep their original language.
- Frontmatter carries exactly two fields:
  - `name`: identical to the directory name, lowercase kebab-case.
  - `description`: one long line stating scope, key technical hints (env vars, script paths, CLI), and the trigger phrase ("use when ...").
- Body structure: `#` title, a short lead-in paragraph, then `##` sections. Put large procedural detail in `references/`, executable code in `scripts/`. An index-type skill keeps SKILL.md as a thin index only.
- Do not call other skills from inside a skill; keep coupling low. Multi-skill orchestration belongs in workflows.
- Reference env vars as `$VAR`. Never reference unverified table/field/class/FM names; describe the business goal instead, or verify via MCP first.
- Steps that depend on tool mechanics (auth, session cookies, fallback chains) must be spelled out in the skill body, not assumed from the description.

## Naming Rules

- Skills serving the same task type share one prefix. Current families: `br-*`, `defect-*`, `sap-*`, `kb-*`. Pick the family prefix or propose a new one for the user to confirm.
- Do not name skills after storage or tooling (e.g. an `obsidian-` prefix); name them after the task or business object.

## Sync Checklist

Run every item after creating or modifying a skill; report which were done and which need manual action:

1. `CHANGELOG.md` (in English): add a `### Skills` entry under a `## [vX.Y.Z] - <ISO date>` section. Bump the minor version for a new skill, patch version for edits.
2. New env vars: add placeholder keys to `.env.example.json` and tell the user to update local `.env.json`. When existing vars are renamed, warn in the CHANGELOG section heading.
3. New config JSON file: add the file itself to `.gitignore` and commit a sample following the `<name>.example.json` convention.
4. New output directory: add it to `.gitignore`.
5. Cross-references: when renaming, Grep the old name project-wide and update all hits. Update the `README.md` (in English) skills table and counts. Add or update the owning agent's `## Skill 索引` row per clerk.md rules; universal skills need rows in every module-consultant agent.
6. Structural edits to skills or workflows are the user's call: prepare the change, obtain explicit approval, then execute.

## Red Lines

- Touch only the target skill files and the checklist items; everything else stays read-only.
- Never modify `.claude/settings.json`, hooks, or permission rules.
- SAP write operations are always out of scope; they require user authorization per CLAUDE.md.
