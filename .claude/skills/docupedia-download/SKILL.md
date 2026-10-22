---
name: docupedia-download
description: Download Bosch intranet Docupedia (Confluence) pages and save them as md knowledge-base files under $DOCUPEDIA_FOLDER. Bare WebFetch/curl gets 401 — must call the Confluence REST API with Bearer $JIRA_TOKEN (the Jira PAT is valid on the Docupedia domain). Rate limiting and children-macro index pages are known traps (see body). Use when the user asks to read/grab/sync a Docupedia page (URL, title, or page ID) or batch-download a page tree.
---

# Docupedia (Confluence) Download → $DOCUPEDIA_FOLDER

Flow: REST API fetch page → strip XHTML to text → save as `$DOCUPEDIA_FOLDER/<title>.md` → report path + content summary to the user.

## Env Vars

Check before any call; stop and ask the user if unset:

- `$JIRA_TOKEN` (Bearer) — valid on `inside-docupedia.bosch.com` Confluence REST API (same intranet SSO/PAT system, verified). Never decode, never Basic auth.
- `$DOCUPEDIA_FOLDER` — output directory (configured in `.env.json`, currently the knowledge-base subdirectory `6.EWM Trade Docupedia`). Never create a project-internal docupedia/ directory; verify the directory exists before writing.

## Forbidden

- **WebFetch**: blocked by domain safety check ("Unable to verify if domain is safe to fetch").
- **Bare curl of page URLs**: 401 + JS prompt page (SSO; no login state, no content).

## Locating a Page

- URL given → extract the numeric page ID from `/pages/<pageId>/<title>`.
- Only title/number given (e.g. BR number `WH-GR-01-01`) → search by title first:

```bash
curl -s -H "Authorization: Bearer $JIRA_TOKEN" -H "Accept: application/json" \
  "https://inside-docupedia.bosch.com/confluence/rest/api/content?spaceKey=<SPACE>&title=<URL-encoded title>&expand=version"
```

## ⚠️ Index-Page Trap: children macro (mandatory reading for batch grabs)

- Some pages have a tiny body (a few hundred chars) containing only `<ac:structured-macro ac:name="children">` — all real content lives in child pages; grabbing the page alone is worthless. Example: SAPEWM's STEP BY STEP GUIDELINES body is only 329 chars.
- Detect index pages: `len(body) < 600` AND contains `ac:structured-macro` + `children`.
- List child pages: `GET /rest/api/content/<pageId>/child/page?limit=200` → `results[]` (with `id`, `title`).
- **Recurse to leaves**: a child may itself be an index page (e.g. WH-TI-01 ERP Connection has 13 system-environment children); index depth is not always 2. If a child returns `size: 0` it is a leaf — grab its body.
- Branches like Archiving may return `size: 0` with no pages at all — normal.

## Rate Limiting — the certain trap of batch grabs

- Confluence rate-limits hard: **serial requests with 3–4 s spacing** are usually safe; unspaced bursts hit roughly every 20 requests. Error shape: HTTP 200 but body `{"message": "Rate limit exceeded."}` — no `title`/`results` fields; check before parsing.
- On hit: wait 20–60 s and retry. A few failures per batch are expected — collect failed IDs and rerun at the end with 6 s spacing.

## Batch Grab (use the bundled script)

For multiple pages prefer `scripts/batch_grab.py` (rate-limit backoff retry, per-pageId JSON cache for resume, version-compare skip):

```bash
# 1. Recursively list the child-page tree (index pages marked); confirm the leaf list
python <skill_dir>/scripts/batch_grab.py tree <pageId> > tree.txt

# 2. Extract leaf pageIds into ids.txt (one per line); batch-grab to disk
python <skill_dir>/scripts/batch_grab.py grab ids.txt
```

- JSON cached per pageId under `$TMP/docupedia_page_<id>.json`; reruns resume; API error responses are never cached.
- Env var: `DOCUPEDIA_DELAY` (request spacing in seconds, default 4; increase if still rate-limited).
- Save rules identical to the section below.

## Single-Page Fetch (curl, Git Bash)

```bash
curl -s --max-time 60 -H "Authorization: Bearer $JIRA_TOKEN" -H "Accept: application/json" \
  "https://inside-docupedia.bosch.com/confluence/rest/api/content/<pageId>?expand=body.storage,version,space" \
  -o "$TMP/docupedia_page.json"
```

expand: `body.storage` (XHTML body, required), `version` (number/date), `space` (for the KB header).

## Parse & Save (single step)

⚠️ Git Bash `/tmp` is an MSYS path invisible to Windows Python — use `$TMP` (Windows temp) and `os.environ['TMP']` in Python.

storage is XHTML; strip tags and write the KB md directly:

```bash
python -c "
import json, re, html, os, datetime
p = os.path.join(os.environ['TMP'], 'docupedia_page.json')
data = json.load(open(p, encoding='utf-8'))
body = data['body']['storage']['value']
body = body.replace('</td>', ' | ').replace('</th>', ' | ')   # table cell separator
body = re.sub(r'<br\s*/?>', '\n', body)
body = re.sub(r'</(p|div|tr|li|h1|h2|h3|h4|table|ul|ol)>', '\n', body)
# ac:link (Confluence internal links): extract link text, drop URL, else the whole block vanishes with tag stripping
def _link_text(m):
    t = re.search(r'<!\[CDATA\[(.*?)\]\]>', m.group(0), re.S)
    if t:
        return t.group(1)
    t = re.search(r'ri:content-title=\"([^\"]*)\"', m.group(0))
    return html.unescape(t.group(1)) if t else ''
body = re.sub(r'<ac:link[^>]*>.*?</ac:link>', _link_text, body, flags=re.S)
body = re.sub(r'<[^>]+>', '', body)
body = html.unescape(body)
body = re.sub(r'\n{3,}', '\n\n', body).strip()

title = data['title']
fname = re.sub(r'[\\\\/:*?\"<>|()]+', '', title).strip().replace(' ', '-') + '.md'
out_dir = os.environ.get('DOCUPEDIA_FOLDER', '')
if not out_dir:
    raise SystemExit('ERROR: DOCUPEDIA_FOLDER not set')
os.makedirs(out_dir, exist_ok=True)
out = os.path.join(out_dir, fname)

new_ver = int(data['version']['number'])
if os.path.exists(out):
    m = re.search(r'Version: (\d+)', open(out, encoding='utf-8').read())
    if m and int(m.group(1)) >= new_ver:
        print('UP-TO-DATE: v%s already latest, untouched %s' % (m.group(1), out))
        raise SystemExit
header = ('# ' + title + '\n\n'
          '- Source page: https://inside-docupedia.bosch.com/confluence/pages/viewpage.action?pageId=' + data['id'] + '\n'
          '- Page ID: ' + data['id'] + ' | Space: ' + data.get('space',{}).get('key','') + ' | Version: ' + str(new_ver) + '\n'
          '- Page updated: ' + data['version']['when'][:10] + ' | Grabbed: ' + datetime.date.today().isoformat() + '\n\n')
open(out, 'w', encoding='utf-8').write(header + body + '\n')
print('SAVED v%d: %s' % (new_ver, out))
print('=' * 60)
print(body)
"
```

## KB Rules

- **Location**: the `$DOCUPEDIA_FOLDER` directory (env-var configured; the CLAUDE.md `workfolder/` output rule does not apply).
- **Filename**: page title sanitized (strip `\ / : * ? " < > | ( )`, spaces → `-`), e.g. `WH-GR-01-01-Inbound-Delivery-Creation-automatic.md`.
- **md structure**: H1 = page title; header list records the source-page URL (`viewpage.action?pageId=` form, click back to the original), Page ID, Space, version, page-updated date, grabbed date; body follows.
- **Version compare**: when a same-name file exists, compare versions — overwrite only if the remote is newer; otherwise touch nothing and report UP-TO-DATE. Files are stably reused by page title; no manual inventory needed.
- **After saving**: report the md path + version to the user with a content summary (summary in the reply, never written into the md).

## Parsing Notes

- `title`, `version.number`, `version.when` sit at the JSON top level; the body is `body.storage.value`.
- storage tables carry no separators — insert ` | ` at `</td>`/`</th>` before stripping tags, else columns fuse.
- Bodies contain `&nbsp;` entities and BOM control chars (`﻿`); residue after `html.unescape` is normal.
- Trailing "Related BR" links point to T&R issues (e.g. `WH-GR-01-01`); to read issue details use `br-jira-query`.

## SAPEWM Space Page Tree (field-tested)

Branch structure and numbering under the GUIDELINES index page (pageId 1049782819), a starting point for lookups:

| Branch | Numbering | Pages | Notes |
|---|---|---|---|
| Goods Receipt | WH-GR-01~04 | 17 | 01 pre-receipt / 02 unloading / 03 putaway / 04 posting & closing |
| Goods Issue | WH-GI-01~05 | 29 | 01 GI creation / 02 picking / 03 packing / 04 loading / 05 posting cancellation |
| Internal Processes | WH-IP-01~03 | 24 | 01 replenishment / 02 KTS production / 03 physical inventory |
| Supporting Functions | WH-SF-01~08 | 13 | stock transfers/QM/serial numbers/batches/GTS/SLED |
| Master Data & Structure | WH-MD | 3 | Material Master / Warehouse Structure / DG |
| Forms and Labels | WH-FL | 2 | |
| Technical Interface | WH-TI | 2+13 | WH-TI-01 ERP Connection has 13 system-environment children (BT/HC/MA/PT production systems) |
| Performance Management | WH-PM | 3 | |
| Authorization Concept | WH-AC | 1 | |
| Archiving | — | 0 | empty branch |
| Automation Technology | WH-AT | 6 | Autostore App series + VLM |

- The same prefix may have duplicate numbers (WH-MD-01 twice: Dangerous Goods and Material Master); titles differentiate filenames, no conflict on disk.
- Page titles with punctuation are normal (e.g. `WH-GI-02-07 Pick, Pack, Pass`); the sanitize rule handles them.
