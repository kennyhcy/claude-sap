# SAP Agent

An agent with full knowledge of the SAP S/4 HANA system. Connected to SAP S/4 HANA via [mcp-abap-adt-b](https://github.com/kennyhcy/mcp-abap-adt-b), it provides business Q&A, configuration guidance, business data queries, ABAP development, and BR/defect analysis through built-in agents, skills, and workflows.

* **Tech stack**: ABAP + TypeScript/MCP
* **Runtime**: Claude Code (CLI / Desktop / Web / IDE extension)
* **MCP connection**: [mcp-abap-adt-b](https://github.com/kennyhcy/mcp-abap-adt-b) stdio, started via `node dist/index.js`; see `.mcp.example.json` for a connection example

\---

## Directory Structure

```
claude-sap/
├── .claude/
│   ├── agents/          # 2 agent definitions (abaper, clerk)
│   ├── skills/          # 19 skills (each with SKILL.md + optional references/, scripts/)
│   ├── workflows/       # 3 workflow orchestration scripts (work-list / work-analyze / tr-check)
│   └── settings.json    # PreToolUse hook: SAP write-operation tools force "ask" interception
├── CLAUDE.md            # Project master instructions (routing, conventions, authorization red lines)
├── CHANGELOG.md         # Change log
├── .mcp.example.json    # MCP connection example (copy to .mcp.json)
├── .env.example.json    # Env var template (copy to .env.json)
├── .systems.example.json# SAP system connection template (copy to .systems.json)
├── .gitignore
├── px_claude_sap.bat    # Claude launcher script (injects .env.json)
├── px_cmd_here.bat      # Open cmd in current directory
└── git-toolbox.bat      # Git utility script
```

> The output directory `workfolder/` is gitignored; all runtime output files go there and are not version-controlled. Local-only config files (`.mcp.json`, `.env.json`, `.systems.json`) are also gitignored; commit only their `*.example.json` counterparts.

\---

## Agents (2)

Routed by role; the main Claude dispatches based on frontmatter `description`:

|Agent|Responsibility|
|-|-|
|`abaper`|Senior ABAP development expert: code analysis, logic tracing, creating/modifying/activating ABAP objects via mcp-abap-adt-b tools|
|`clerk`|Documentation clerk: writes/maintains agent & skill .md files, CLAUDE.md, reference files, memory files; consistency only, no code or business data|

\---

## Skills (19)

Skills serving the same task type share one prefix (`br-*` / `defect-*` / `sap-*` / `kb-*` / `bosch-*`); ownership and index rules are described in the "Skill-Agent 索引同步规则" section of [`clerk.md`](.claude/agents/clerk.md). Multi-skill orchestration lives in `.claude/workflows/`:

|Category|Skill|Description|
|-|-|-|
|BR/defect work|`br-note` / `defect-note`|Create & find BR / Defect notes under `$BR_FOLDER` / `$DEFECT_FOLDER`|
|BR/defect work|`br-download`|Download a BR's WB docx from SharePoint and incrementally sync it into the note|
|BR/defect work|`br-analyze` / `defect-analyze`|Section paradigm & write rules for BR / Defect analysis results|
|Integration|`br-jira-query`|Intranet Jira issue read, JQL search, comment append|
|Integration|`defect-alm-query`|Bosch ALM 24 defect read/write (curl + session cookie)|
|Integration|`docupedia-download`|Download Docupedia pages and save them as KB md files|
|SAP knowledge/query|`sap-ewm`|EWM knowledge & business data query master index (details in references/)|
|SAP knowledge/query|`sap-basic-data-query`|SAP cross-module general knowledge (IDoc/OData/BAPI/CDS View/SPRO etc.)|
|SAP knowledge/query|`sap-error-explain`|Explain SAP/EWM error messages to key users|
|SAP knowledge/query|`sap-abc-reclassification`|Reclassify material ABC indicators by warehouse-task frequency|
|SAP knowledge/query|`sap-note` / `sap-note-search`|SAP Note / KBA full-text read (get_sapnote.ps1) and keyword search|
|SAP knowledge/query|`abap-adt-write`|mcp-abap-adt write tool practice (Create/Update/Activate)|
|Knowledge base|`kb-search`|Local vector semantic search & KB Q&A over the local knowledge base (`$KB_VAULT`)|
|Bosch generic|`bosch-adaptive-slides`|Markdown to Bosch-branded HTML/PPTX/PDF slides|
|Bosch generic|`bosch-skillhub`|Bosch SkillHub skill find/download/upload|
|Meta skill|`skill-writer`|Conventions & sync checklist for writing/rewriting skills|

## Workflows (3)

|Workflow|Description|
|-|-|
|`work-list`|Pull open BRs (Jira) & defects (ALM), incrementally sync their status/replies into the notes' log blocks, and return the open list|
|`work-analyze`|Analyze one open BR/defect in five steps: sync+read note → KB retrieval → deep-dive analysis → write note sections → summarize & draft reply (publishing requires user confirmation)|
|`tr-check`|Inspect a transport request's contents (E070/E071/E07T/VRSD) in parallel across multiple SAP systems|

\---

## Core Conventions

1. **🔴 Code create/modify requires prior user authorization**: any `CreateObject` / `UpdateObjectSource` / `ActivateObject` on the SAP system must be approved by the user first. The PreToolUse hook in `.claude/settings.json` forces `ask` for these three tools.
2. **No guessing technical objects**: prompts describe business goals, never unverified table/field/class/FM names; verify via MCP first when a concrete object must be referenced.
3. **Read the full SKILL.md before invoking a skill**: never infer its rules from the injected description alone. For EWM knowledge & data queries, `sap-ewm` is the unified entry point.
4. **Layering**: a skill performs one basic operation (no skill-to-skill calls); a workflow only orchestrates steps; multi-skill operations are implemented as workflows.

See [`CLAUDE.md`](CLAUDE.md) for details.

\---

## Quick Start

1. Install Claude Code (CLI / Desktop / IDE extension, any one).
2. Copy `.mcp.example.json` to `.mcp.json` and change the `args` path to the absolute path of your local mcp-abap-adt `dist/index.js`.
3. Copy `.env.example.json` to `.env.json` and fill in your credentials (Jira/ALM tokens, knowledge-base folders `$KB_VAULT`/`$BR_FOLDER`/`$DEFECT_FOLDER`/`$DOCUPEDIA_FOLDER`, proxy).
4. Make sure you are logged on to SAP S/4 HANA (mcp-abap-adt connection config in `.systems.json`).
5. Run `px_claude_sap.bat` (or start Claude Code in the project directory) so the env vars are injected.
6. Ask questions in the conversation; the main Claude routes automatically to the proper agent or workflow.

\---

## Git Operations

See [`git-toolbox.bat`](git-toolbox.bat) for the project's Git utility commands.
