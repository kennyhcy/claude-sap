# -*- coding: utf-8 -*-
"""Docupedia (Confluence) 批量抓取 → docupedia/ 知识库

用法（在项目根目录运行）:
  python batch_grab.py tree <pageId>        # 递归列出子页面树（标记含下级的类目录页）
  python batch_grab.py grab <ids.txt>       # 按 ID 清单（每行一个 pageId）批量抓取落盘

环境变量:
  JIRA_TOKEN          必填，Bearer PAT（Jira 的 PAT 对 Docupedia 同域有效）
  DOCUPEDIA_DELAY     请求间隔秒数，默认 4（限流时调大）
  TMP                 JSON 缓存目录（默认系统 temp），按 pageId 缓存可断点续传
"""
import json, re, html, os, sys, time, datetime
import urllib.request

API = 'https://inside-docupedia.bosch.com/confluence/rest/api/content'
DELAY = float(os.environ.get('DOCUPEDIA_DELAY', '4'))
TMP = os.environ.get('TMP', '/tmp')
OUT_DIR = os.path.join(os.getcwd(), 'docupedia')


def api_json(url):
    """GET JSON，遇限流（响应无 title/results 字段）按 10s/30s/60s 退避重试。"""
    token = os.environ.get('JIRA_TOKEN')
    if not token:
        sys.exit('ERROR: JIRA_TOKEN 未设置')
    delays = [10, 30, 60]
    for attempt in range(len(delays) + 1):
        req = urllib.request.Request(url, headers={
            'Authorization': 'Bearer ' + token,
            'Accept': 'application/json'})
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.load(resp)
        except Exception as e:
            if attempt == len(delays):
                return {'message': 'HTTP_ERR %s' % e}
        time.sleep(delays[attempt])
    return {'message': 'unreachable'}


def cache_get(pid, expand):
    """按 pageId 缓存 JSON 到 $TMP；已有缓存直接复用（断点续传）。"""
    jf = os.path.join(TMP, 'docupedia_page_%s.json' % pid)
    if os.path.exists(jf):
        try:
            return json.load(open(jf, encoding='utf-8'))
        except Exception:
            os.remove(jf)  # 缓存损坏（如限流错误响应）则重新抓
    time.sleep(DELAY)
    data = api_json('%s/%s?expand=%s' % (API, pid, expand))
    if 'title' not in data:
        return data  # API 错误不写缓存，下次重抓
    open(jf, 'w', encoding='utf-8').write(json.dumps(data, ensure_ascii=False))
    return data


def clean_body(body):
    body = body.replace('</td>', ' | ').replace('</th>', ' | ')
    body = re.sub(r'<br\s*/?>', '\n', body)
    body = re.sub(r'</(p|div|tr|li|h1|h2|h3|h4|table|ul|ol)>', '\n', body)
    # ac:link（Confluence 内链）：保留链接文本，URL 丢弃。
    # 文本优先取 ac:plain-text-link-body 的 CDATA；无则退回 ri:page 的 content-title。
    def _link_text(m):
        t = re.search(r'<!\[CDATA\[(.*?)\]\]>', m.group(0), re.S)
        if t:
            return t.group(1)
        t = re.search(r'ri:content-title="([^"]*)"', m.group(0))
        return html.unescape(t.group(1)) if t else ''
    body = re.sub(r'<ac:link[^>]*>.*?</ac:link>', _link_text, body, flags=re.S)
    body = re.sub(r'<[^>]+>', '', body)
    body = html.unescape(body)
    return re.sub(r'\n{3,}', '\n\n', body).strip()


def fname_of(title):
    return re.sub(r'[\\\\/:*?\"<>|()]+', '', title).strip().replace(' ', '-') + '.md'


def is_dir_page(data):
    """目录页特征：正文极短且只含 children 宏，无实际内容。"""
    body = data.get('body', {}).get('storage', {}).get('value', '')
    return len(body) < 600 and 'ac:structured-macro' in body and 'children' in body


def cmd_tree(pid, depth=0):
    data = cache_get(pid, 'body.storage,version,space')
    if 'title' not in data:
        print('  ' * depth + '%s API_ERR %s' % (pid, data.get('message', '?')))
        return
    mark = ' [目录页]' if is_dir_page(data) else ''
    print('  ' * depth + '%s | %s (v%s)%s' % (pid, data['title'],
          data.get('version', {}).get('number', '?'), mark))
    time.sleep(DELAY)
    kids = api_json('%s/%s/child/page?limit=200' % (API, pid))
    for k in kids.get('results', []):
        cmd_tree(k['id'], depth + 1)


def cmd_grab(ids_file):
    os.makedirs(OUT_DIR, exist_ok=True)
    ids = [l.strip() for l in open(ids_file, encoding='utf-8') if l.strip()]
    for pid in ids:
        data = cache_get(pid, 'body.storage,version,space')
        if 'title' not in data:
            print('%s API_ERR %s' % (pid, data.get('message', '?')[:40]))
            continue
        body = clean_body(data['body']['storage']['value'])
        title = data['title']
        out = os.path.join(OUT_DIR, fname_of(title))
        new_ver = int(data['version']['number'])
        if os.path.exists(out):
            m = re.search(r'Version: (\d+)', open(out, encoding='utf-8').read())
            if m and int(m.group(1)) >= new_ver:
                print('%-58s v%-4s UP-TO-DATE' % (title[:58], new_ver))
                continue
        header = ('# ' + title + '\n\n'
                  '- 源页面: https://inside-docupedia.bosch.com/confluence/pages/viewpage.action?pageId=' + data['id'] + '\n'
                  '- Page ID: ' + data['id'] + ' | Space: ' + data.get('space', {}).get('key', '') + ' | Version: ' + str(new_ver) + '\n'
                  '- 页面更新: ' + data['version']['when'][:10] + ' | 抓取: ' + datetime.date.today().isoformat() + '\n\n')
        open(out, 'w', encoding='utf-8').write(header + body + '\n')
        print('%-58s v%-4s SAVED (%d chars)' % (title[:58], new_ver, len(body)))


if __name__ == '__main__':
    if len(sys.argv) >= 3 and sys.argv[1] == 'tree':
        cmd_tree(sys.argv[2])
    elif len(sys.argv) >= 3 and sys.argv[1] == 'grab':
        cmd_grab(sys.argv[2])
    else:
        sys.exit(__doc__)
