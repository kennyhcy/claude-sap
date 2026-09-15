---
name: docupedia-read
description: 读取 Bosch 内网 Docupedia（Confluence）页面，读取后自动落盘为项目 docupedia/ 目录下的 md 知识库文件。WebFetch/curl 裸访问均 401，必须用 Bearer $JIRA_TOKEN（Jira 的 PAT 对 Docupedia 同域有效）调 Confluence REST API。当用户要求读取某 Docupedia 页面（给链接、页面标题或页面 ID 均可）时使用。
---

# 内网 Docupedia（Confluence）页面读取 → docupedia/ 知识库

流程：REST API 抓页面 → 剥标签转纯文本 → 存为 `docupedia/<标题>.md` → 向用户报告路径与内容摘要。

## 禁止项

- **禁止 WebFetch**：域名安全校验直接被拦（"Unable to verify if domain is safe to fetch"）。
- **禁止裸 curl 抓页面 URL**：返回 401 + JS 提示页（SSO 认证，无登录态拿不到内容）。
- Jira PAT 同样**禁止解码、禁止 Basic auth**（与 jira-query 约定一致）。

## 认证方式

`$JIRA_TOKEN`（Bearer）对 `inside-docupedia.bosch.com` 的 Confluence REST API 有效——同一内网 SSO/PAT 体系，实测通过。调用前先检查 `[ -n "$JIRA_TOKEN" ]`，未设置则停下提示用户配置。

## 定位页面

- 用户给 URL：从路径 `/pages/<pageId>/<title>` 中提取数字页面 ID。
- 用户只给标题/编号（如 BR 编号 WH-GR-01-01）：先按标题搜页面 ID。

```bash
curl -s -H "Authorization: Bearer $JIRA_TOKEN" -H "Accept: application/json" \
  "https://inside-docupedia.bosch.com/confluence/rest/api/content?spaceKey=<SPACE>&title=<URL编码标题>&expand=version"
```

## ⚠️ 目录页陷阱：children 宏（批量抓取必读）

- 有些页面正文极短（几百字符），只含 `<ac:structured-macro ac:name="children">` 宏——**实际内容全在子页面里**，单抓该页毫无价值。实例：SAPEWM 的 STEP BY STEP GUIDELINES 正文仅 329 字符。
- 遇到目录页须列出子页面：`GET /rest/api/content/<pageId>/child/page?limit=200`，返回 `results[]`（含 `id`、`title`）。
- **递归到叶子**：子页面本身也可能是类目录页（如 WH-TI-01 ERP Connection 下挂 13 个系统环境页）。先抽查子页面有无下级；目录深度不一定是 2 层。
- 判定目录页特征：`len(body) < 600` 且含 `ac:structured-macro` + `children`。若子页面返回 `size: 0` 则确认是叶子，直接抓正文。
- Archiving 这类分支可能 `size: 0`、整支无页面，属正常。

## 限流（Rate limit exceeded）——批量抓取的必踩坑

- Confluence 有严格限流，**串行请求间隔 3~4 秒**通常安全；无间隔连发约每 20 个请求必中一次。错误形态：HTTP 200 但 body 是 `{"message": "Rate limit exceeded."}`——**没有 title/results 字段**，解析前必须检查。
- 中招后等待 20~60 秒重试即可恢复；批量任务失败几个属预期，收尾后**收集失败 ID 统一重跑**，间隔加大到 6 秒。
- 稳妥做法：每页 `sleep 4`，python 循环里逐页判断 `'title' not in data` 则记为失败并继续，最后汇总重试。

## 批量抓取（用现成脚本）

多个页面时优先用 skill 自带脚本（含限流退避重试、按 pageId 缓存断点续传、版本比对跳过）：

```bash
# 1. 递归列出子页面树（标记目录页），确认叶子清单
python <skill_dir>/scripts/batch_grab.py tree <pageId> > tree.txt

# 2. 从树中摘出叶子 pageId 存 ids.txt（每行一个），批量抓取落盘
python <skill_dir>/scripts/batch_grab.py grab ids.txt
```

- JSON 按 pageId 缓存于 `$TMP/docupedia_page_<id>.json`，中断后重跑自动续传；API 错误响应不写缓存。
- 可用环境变量：`DOCUPEDIA_DELAY`（请求间隔秒数，默认 4，仍限流就调大）。
- 脚本落盘规则与下方「知识库规则」一致（版本比对、header 格式相同）。

## 单页抓取（curl，Git Bash）

```bash
curl -s --max-time 60 -H "Authorization: Bearer $JIRA_TOKEN" -H "Accept: application/json" \
  "https://inside-docupedia.bosch.com/confluence/rest/api/content/<pageId>?expand=body.storage,version,space" \
  -o "$TMP/docupedia_page.json"
```

expand 参数：`body.storage`（正文 XHTML，必备）、`version`（版本号/更新时间）、`space`（所属空间，写入知识库 header 用）。

## 解析并落盘（一步完成）

⚠️ Git Bash 的 `/tmp` 是 MSYS 路径，**Windows 版 python 看不见 `/tmp/xxx`**——落盘用 `$TMP`（Windows temp），python 里用 `os.environ['TMP']` 拼路径。

storage 格式是 XHTML，剥标签转文本并直接写出知识库 md：

```bash
python -c "
import json, re, html, os, datetime
p = os.path.join(os.environ['TMP'], 'docupedia_page.json')
data = json.load(open(p, encoding='utf-8'))
body = data['body']['storage']['value']
body = body.replace('</td>', ' | ').replace('</th>', ' | ')   # 表格单元格分隔
body = re.sub(r'<br\s*/?>', '\n', body)
body = re.sub(r'</(p|div|tr|li|h1|h2|h3|h4|table|ul|ol)>', '\n', body)
# ac:link（Confluence 内链）先摘出链接文本，URL 丢弃，否则整块被剥标签吞掉
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
out_dir = os.path.join(os.getcwd(), 'docupedia')
os.makedirs(out_dir, exist_ok=True)
out = os.path.join(out_dir, fname)

new_ver = int(data['version']['number'])
if os.path.exists(out):
    m = re.search(r'Version: (\d+)', open(out, encoding='utf-8').read())
    if m and int(m.group(1)) >= new_ver:
        print('UP-TO-DATE: v%s 已是最新，未改动 %s' % (m.group(1), out))
        raise SystemExit
header = ('# ' + title + '\n\n'
          '- 源页面: https://inside-docupedia.bosch.com/confluence/pages/viewpage.action?pageId=' + data['id'] + '\n'
          '- Page ID: ' + data['id'] + ' | Space: ' + data.get('space',{}).get('key','') + ' | Version: ' + str(new_ver) + '\n'
          '- 页面更新: ' + data['version']['when'][:10] + ' | 抓取: ' + datetime.date.today().isoformat() + '\n\n')
open(out, 'w', encoding='utf-8').write(header + body + '\n')
print('SAVED v%d: %s' % (new_ver, out))
print('=' * 60)
print(body)
"
```

## 知识库规则

- **保存位置**：项目根目录 `docupedia/`（用户指定的知识库目录，不适用 CLAUDE.md 的 workfolder 输出规则）。
- **文件名**：页面标题清洗为文件名安全字符（去 `\ / : * ? " < > | ( )`，空格换 `-`），如 `WH-GR-01-01-Inbound-Delivery-Creation-automatic.md`。
- **md 结构**：一级标题 = 页面标题；header 列表记录源页面 URL（viewpage.action?pageId= 形式，可再点回原文）、Page ID、Space、版本号、页面更新日期、抓取日期；正文随后。
- **版本比对**：同名文件已存在时比较版本号——远端版本更新才覆盖；已是最新则不动文件、只提示 UP-TO-DATE。知识库文件按页面标题命名即可稳定复用，无需手工维护清单。
- **落盘后**：向用户报告 md 路径 + 版本号，并给正文内容摘要（摘要写在回复里，不写进 md）。

## 解析要点

- `title`、`version.number`、`version.when` 在 JSON 顶层，正文在 `body.storage.value`。
- storage 里的表格无分隔符，先在 `</td>`/`</th>` 处插 ` | ` 再剥标签，否则列全粘连。
- 原文常含 `&nbsp;` 等实体和 BOM 控制符（`�`），`html.unescape` 后仍有残留属正常。
- 页面末尾的 Related BR 指向 T&R issue（如 `WH-GR-01-01`），要读 issue 细节转 [[jira-query]]。

## SAPEWM 空间页面树（实测沉淀）

GUIDELINES 目录页（pageId 1049782819）下的分支结构与编号规律，可作查找起点：

| 分支 | 编号前缀 | 页面数 | 备注 |
|---|---|---|---|
| Goods Receipt | WH-GR-01~04 | 17 | 01 收货前置 / 02 卸货 / 03 上架 / 04 过账收尾 |
| Goods Issue | WH-GI-01~05 | 29 | 01 发货创建 / 02 拣配 / 03 包装 / 04 装车 / 05 过账取消 |
| Internal Processes | WH-IP-01~03 | 24 | 01 补货 / 02 KTS 生产 / 03 盘点 |
| Supporting Functions | WH-SF-01~08 | 13 | 转储/QM/序列号/批次/GTS/保质期 |
| Master Data & Structure | WH-MD | 3 | Material Master / Warehouse Structure / DG |
| Forms and Labels | WH-FL | 2 | |
| Technical Interface | WH-TI | 2+13 | WH-TI-01 ERP Connection 下挂 13 个系统环境页（BT/HC/MA/PT 各生产系统） |
| Performance Management | WH-PM | 3 | |
| Authorization Concept | WH-AC | 1 | |
| Archiving | — | 0 | 空分支 |
| Automation Technology | WH-AT | 6 | Autostore App 系列 + VLM |

- 同一前缀可能有重复编号（WH-MD-01 出现两次：Dangerous Goods 与 Material Master），落盘时靠标题区分文件名，不冲突。
- 页面标题含逗号等标点属正常（如 `WH-GI-02-07 Pick, Pack, Pass`），清洗规则已处理。
