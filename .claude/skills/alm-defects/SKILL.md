---
name: alm-defects
description: 查询和更新 Bosch ALM (OpenText ALM 24) 中的 defect。当用户要求"找出 assign 给我的未 closed 的 defect"、"查询 defect <ID>"、"给 defect <ID> 加 comment"、或其它读写 defect 数据的请求时使用。用 curl + 会话 Cookie 访问 ALM REST API，返回 title、summary、详细信息及所有 comments，支持追加评论（PUT dev-comments + XSRF token）。
---

# ALM Defect 查询 Skill

## 前置条件：环境变量

以下变量必须已设置（缺失时提示用户设置，不要猜）：

| 变量 | 说明 |
|---|---|
| `ALM_BASE_URL` | 如 `https://otalm24.de.bosch.com/qcbin` |
| `ALM_CLIENT_ID` | OAuth2 API Key，如 `apikey-xxxx` |
| `ALM_CLIENT_SECRET` | 对应 secret |
| `ALM_DOMAIN` | ALM 域，如 `GS` |
| `ALM_PROJECT` | 项目名，如 `SWMS_SPRINT_TESTING` |
| `ALM_USER` | 当前用户的 ALM 账号（如 `ukh1sgh`），用于 "assign 给我" 查询 |

检查方式：`echo "[$ALM_BASE_URL][$ALM_CLIENT_ID][$ALM_CLIENT_SECRET][$ALM_DOMAIN][$ALM_PROJECT][$ALM_USER]"`，有空的就向用户要。

## 关键约束（必须遵守）

1. **curl 必须加 `-g`**：查询串含花括号 `{...}`，否则 curl 报 "nested brace in URL"。
2. **URL 中空格用 `%20`**：bash 引号里的字面空格会导致 "Malformed input to a URL function"。
3. **SSL 不需要 `--insecure`**：本机 curl 走 Windows schannel，信任 Bosch 内部 CA，直接即可。不要给 Python requests 用（缺 Bosch CA 会失败）。
4. **评论在 `dev-comments` 字段**：没有 `/comments` 子端点（404）。`dev-comments` 是 HTML，需转成可读文本展示给用户。
5. **title 字段是 `name`**：`summary` 字段通常为空；完整信息 = `name`（标题）+ `description`（详细描述，HTML）。
6. **解析 JSON 用 python**：本机没有 jq。python 只做本地解析，不发网络请求。**python 命令前必须加 `PYTHONIOENCODING=utf-8`**：本机控制台是 cp1252，输出中文或 `ü` 等非 ASCII 字符会抛 UnicodeEncodeError。
7. Cookie 文件用 `/tmp/alm_cookies.txt`（Git Bash 的 /tmp 即 TEMP）。
8. **写操作（PUT）必须带 XSRF token**：PUT 更新 defect 时若不带 `X-XSRF-TOKEN` header，返回 401（"Unauthorized request... see XSRF Token section"）。token 从登录后 cookie 文件里的 `XSRF-TOKEN` 取。

## 操作步骤

### 1. 登录拿会话

```bash
curl -sS --max-time 30 -c /tmp/alm_cookies.txt -o /dev/null -w "login: %{http_code}\n" \
  -X POST "$ALM_BASE_URL/rest/oauth2/login" \
  -H "Content-Type: application/json" \
  -d "{\"clientId\":\"$ALM_CLIENT_ID\",\"secret\":\"$ALM_CLIENT_SECRET\"}"
```

`login: 200` 才继续；401 = 凭证错误，向用户确认 API Key。

### 2a. 查 "assign 给我的未 closed 的 defect"

```bash
curl -sS -g --max-time 60 -b /tmp/alm_cookies.txt \
  "$ALM_BASE_URL/rest/domains/$ALM_DOMAIN/projects/$ALM_PROJECT/defects?query={owner[$ALM_USER];status[Not%20Closed]}&page-size=50" \
  -H "Accept: application/json" -o /tmp/alm_my_defects.json
```

### 2b. 查单个 defect（含全部字段和 comments）

```bash
curl -sS -g --max-time 60 -b /tmp/alm_cookies.txt \
  "$ALM_BASE_URL/rest/domains/$ALM_DOMAIN/projects/$ALM_PROJECT/defects/<ID>" \
  -H "Accept: application/json" -o /tmp/alm_defect.json
```

单条查询返回全部字段（含 `dev-comments`），无需再调其它端点。

### 3. 解析并输出

用 python 解析（列表数据）：

```bash
PYTHONIOENCODING=utf-8 python -c "
import json
d = json.load(open(r'C:/Users/ukh1sgh/AppData/Local/Temp/alm_my_defects.json', encoding='utf-8'))
def fld(e, n):
    for f in e['Fields']:
        if f['Name'] == n:
            v = f.get('values', [])
            return v[0].get('value') if v and isinstance(v[0], dict) and 'value' in v[0] else None
    return None
for e in d.get('entities', []):
    print(fld(e,'id'), '|', fld(e,'status'), '|', fld(e,'priority'), '|', fld(e,'name'))
"
```

注意：python（非 Git Bash）访问 `/tmp` 要用真实路径 `C:/Users/ukh1sgh/AppData/Local/Temp/`。

### 4. 追加评论（写操作）

流程：读单条 defect 取 `dev-comments` 原始 HTML → 在 `</body></html>` 前追加新评论块 → PUT 回去。

**追加格式**（与 ALM UI 生成的一致，直接沿用）：

```html
<div align="left" style="min-height:9pt"><font face="Arial" color="#000080"><span dir="ltr" style="font-size:8pt"><b>________________________________________</b></span></font><font face="Arial"><span dir="ltr" style="font-size:8pt"><br /></span></font><font face="Arial" color="#000080"><span dir="ltr" style="font-size:8pt"><b>姓名 &lt;ID&gt;, DD.MM.YYYY[dd.MM.yyyy]:</b></span></font><font face="Arial"><span dir="ltr" style="font-size:8pt">&nbsp;</span></font></div><div align="left" style="min-height:9pt"><font face="Arial"><span dir="ltr" style="font-size:8pt">评论正文（HTML 转义）</span></font></div>
```

**构建 payload 并 PUT**（python 拼 JSON，body 只发 `dev-comments` 一个字段）：

```bash
PYTHONIOENCODING=utf-8 python -c "
import json
d = json.load(open(r'C:/Users/ukh1sgh/AppData/Local/Temp/alm_defect.json', encoding='utf-8'))
e = d if 'Fields' in d else (d.get('entities') or [{}])[0]
old = ''
for f in e['Fields']:
    if f['Name'] == 'dev-comments':
        v = f.get('values', [])
        if v: old = v[0].get('value','') if isinstance(v[0], dict) else str(v[0])
marker = '</body></html>'
assert old.rstrip().endswith(marker), old[-80:]
new_comment = '...（上面的评论块 HTML）...'
new = old.rstrip()[:-len(marker)] + new_comment + marker
open(r'C:/Users/ukh1sgh/AppData/Local/Temp/alm_put.json','w',encoding='utf-8').write(
    json.dumps({'Fields':[{'Name':'dev-comments','values':[{'value': new}]}]}))
"

XSRF=$(awk '$6=="XSRF-TOKEN"{print $7}' /tmp/alm_cookies.txt)
curl -sS -g --max-time 60 -b /tmp/alm_cookies.txt -X PUT \
  "$ALM_BASE_URL/rest/domains/$ALM_DOMAIN/projects/$ALM_PROJECT/defects/<ID>" \
  -H "Content-Type: application/json" -H "Accept: application/json" \
  -H "X-XSRF-TOKEN: $XSRF" \
  --data-binary @/c/Users/ukh1sgh/AppData/Local/Temp/alm_put.json \
  -o /tmp/alm_put_resp.json -w "put: %{http_code}\n"
```

`put: 200` 后**必须重新 GET 该 defect 读回验证**（解析最后一条评论的署名和正文），确认写入成功。


**列表查询**：表格形式输出 ID、状态、优先级、标题。

**单个 defect**：必须包含——
- **标题**：`name`
- **概要/详细信息**：`description` 的可读文本版（HTML 转文本，保留结构；来源字段 `detected-by`、`owner`、`status`、`priority`、`creation-time` 一并给出）
- **所有回复和 comments**：`dev-comments` HTML 逐条解析。每条评论格式固定为 `<b>姓名 &lt;ID&gt;, 日期:</b> 正文`，按此拆分为多条，按时间顺序列出作者、日期、正文。HTML 实体（`&lt;` `&amp;` `&nbsp;` 等）要还原。

HTML 转文本建议用 python：`re.sub(r'<[^>]+>', ' ', s)` 去标签后清理空白和实体，或直接结构化解析 `<b>` 分隔的评论条目。
