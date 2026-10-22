---
name: defect-alm-query
description: Query and update defects in Bosch ALM (OpenText ALM 24) via curl with a session cookie — list defects assigned to the user, read one defect with all comments, append a comment (PUT dev-comments + XSRF token; publishing requires a user-confirmed draft). Use when the user asks for open defects, a specific defect, or to comment on a defect.
---

# ALM Defect Query

## Env Vars

All required; if any is missing, stop and ask the user:

| Var | Meaning |
|---|---|
| `ALM_BASE_URL` | e.g. `https://otalm24.de.bosch.com/qcbin` |
| `ALM_CLIENT_ID` | OAuth2 API key (`apikey-...`) |
| `ALM_CLIENT_SECRET` | matching secret |
| `ALM_DOMAIN` | ALM domain |
| `ALM_PROJECT` | project name |
| `ALM_USER` | current user's ALM account, for "assigned to me" queries |

## Hard Constraints

1. curl always needs `-g`: query strings contain `{...}` braces.
2. URL spaces must be `%20`; literal spaces fail.
3. No `--insecure`: local curl uses Windows schannel and trusts the Bosch internal CA. Do not use Python requests (missing Bosch CA).
4. Comments live in the `dev-comments` field; there is no `/comments` endpoint (404). `dev-comments` is HTML.
5. The title field is `name` (`summary` is usually empty).
6. Parse JSON with Python (no jq on this machine). Always prefix Python commands with `PYTHONIOENCODING=utf-8` (cp1252 console). Python is local parsing only, no network. Python accesses `/tmp` via its real path `%TEMP%`.
7. Cookie file: `/tmp/alm_cookies.txt` (Git Bash `/tmp` = TEMP).
8. Any PUT must carry the `X-XSRF-TOKEN` header (401 otherwise); the token is the `XSRF-TOKEN` cookie from the login cookie file.

## Workflow

### 1. Login

```bash
curl -sS --max-time 30 -c /tmp/alm_cookies.txt -o /dev/null -w "login: %{http_code}\n" \
  -X POST "$ALM_BASE_URL/rest/oauth2/login" \
  -H "Content-Type: application/json" \
  -d "{\"clientId\":\"$ALM_CLIENT_ID\",\"secret\":\"$ALM_CLIENT_SECRET\"}"
```

Continue only on `login: 200`; 401 = bad credentials, confirm the API key with the user.

### 2. Query

Defects assigned to the current user, not closed:

```bash
curl -sS -g --max-time 60 -b /tmp/alm_cookies.txt \
  "$ALM_BASE_URL/rest/domains/$ALM_DOMAIN/projects/$ALM_PROJECT/defects?query={owner[$ALM_USER];status[Not%20Closed]}&page-size=50" \
  -H "Accept: application/json" -o /tmp/alm_my_defects.json
```

Single defect (all fields including `dev-comments`; no other endpoint needed):

```bash
curl -sS -g --max-time 60 -b /tmp/alm_cookies.txt \
  "$ALM_BASE_URL/rest/domains/$ALM_DOMAIN/projects/$ALM_PROJECT/defects/<ID>" \
  -H "Accept: application/json" -o /tmp/alm_defect.json
```

### 3. Parse & Report

Values sit in `Fields[]` as `Name`/`values[0].value` pairs.

- **List query**: output a table of ID, status, priority, title.
- **Single defect**: output title (`name`), readable-text version of `description` (HTML to text, structure kept; include `detected-by`, `owner`, `status`, `priority`, `creation-time`), and all comments parsed from `dev-comments` HTML. Each comment has the fixed pattern `<b>Name <ID>, date:</b> body`; split on it and list author/date/body in order, restoring HTML entities.

### 4. Append Comment (write — requires user-confirmed draft)

Show the comment body to the user and execute only after explicit consent; send only the confirmed text in one call. Mandatory pre-publish check: defect ID and body match the user-confirmed draft verbatim. Append comments only; never change status/owner or any other field.

Flow: GET the defect for raw `dev-comments` HTML → insert the new comment block before `</body></html>` → PUT back.

Comment block format (matches what the ALM UI generates):

```html
<div align="left" style="min-height:9pt"><font face="Arial" color="#000080"><span dir="ltr" style="font-size:8pt"><b>________________________________________</b></span></font><font face="Arial"><span dir="ltr" style="font-size:8pt"><br /></span></font><font face="Arial" color="#000080"><span dir="ltr" style="font-size:8pt"><b>Name &lt;ID&gt;, dd.MM.yyyy:</b></span></font><font face="Arial"><span dir="ltr" style="font-size:8pt">&nbsp;</span></font></div><div align="left" style="min-height:9pt"><font face="Arial"><span dir="ltr" style="font-size:8pt">comment body (HTML-escaped)</span></font></div>
```

Build the payload with Python — the PUT body contains only the `dev-comments` field:

```bash
PYTHONIOENCODING=utf-8 python -c "
import json
d = json.load(open(r'<TEMP>/alm_defect.json', encoding='utf-8'))
e = d if 'Fields' in d else (d.get('entities') or [{}])[0]
old = ''
for f in e['Fields']:
    if f['Name'] == 'dev-comments':
        v = f.get('values', [])
        if v: old = v[0].get('value','') if isinstance(v[0], dict) else str(v[0])
marker = '</body></html>'
assert old.rstrip().endswith(marker), old[-80:]
new_comment = '<block above with actual name/date/body>'
new = old.rstrip()[:-len(marker)] + new_comment + marker
open(r'<TEMP>/alm_put.json','w',encoding='utf-8').write(
    json.dumps({'Fields':[{'Name':'dev-comments','values':[{'value': new}]}]}))
"

XSRF=$(awk '$6=="XSRF-TOKEN"{print $7}' /tmp/alm_cookies.txt)
curl -sS -g --max-time 60 -b /tmp/alm_cookies.txt -X PUT \
  "$ALM_BASE_URL/rest/domains/$ALM_DOMAIN/projects/$ALM_PROJECT/defects/<ID>" \
  -H "Content-Type: application/json" -H "Accept: application/json" \
  -H "X-XSRF-TOKEN: $XSRF" \
  --data-binary @<TEMP>/alm_put.json \
  -o /tmp/alm_put_resp.json -w "put: %{http_code}\n"
```

After `put: 200`, always re-GET the defect and verify the new comment (signature + body) before reporting success.
