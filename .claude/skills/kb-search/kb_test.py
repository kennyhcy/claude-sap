#!/usr/bin/env python
"""kb_test.py — kb 文件夹内的向量索引测试对话框 (Flask + HTML5).

单文件 Web UI: 输入查询语句, 调 kb_search.py 的检索逻辑, 返回命中 chunk
(含 score/路径/标题链/元数据/内容预览). 用于快速验证向量索引质量, 不承担生产用途.

运行 (使用 ~/.kb/.venv, setup 建立):
  python kb_test.py [--port 5000]     # 脚本在 skill 目录; 缺依赖时自动用 ~/.kb/.venv 重启
然后浏览器打开 http://127.0.0.1:5000

依赖: flask (kb_setup.py 已随 fastembed 一并装入 ~/.kb/.venv).
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

# --- Windows 控制台 UTF-8 ---
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# 让 kb_search.py (同目录, skill 内) 可导入, 其按 ~/.kb 定位 config/index/model
sys.path.insert(0, str(Path(__file__).resolve().parent))


def _reexec_with_kb_venv() -> None:
    """当前解释器缺 fastembed/onnxruntime 时, 若 ~/.kb/.venv 存在则用它重启自己.

    依赖装在 KB 数据目录的 venv 里; 防止误用系统 python.
    """
    import importlib.util
    if importlib.util.find_spec("onnxruntime") is not None:
        return
    venv_py = Path.home() / ".kb" / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not venv_py.exists():
        sys.stderr.write(f"ERROR: onnxruntime missing and KB venv not found at {venv_py}. Run kb_setup.py first.\n")
        sys.exit(2)
    if Path(sys.executable).resolve() == venv_py.resolve():
        sys.stderr.write("ERROR: KB venv python is missing onnxruntime — rerun kb_setup.py.\n")
        sys.exit(2)
    print(f"[kb_test] restarting with KB venv python: {venv_py}", file=sys.stderr)
    # subprocess 而非 os.execv: Windows 路径含空格时 execv 参数重组会损坏
    import subprocess
    subprocess.check_call([str(venv_py), "-X", "utf8", str(Path(__file__).resolve()), *sys.argv[1:]])
    sys.exit(0)


_reexec_with_kb_venv()

try:
    from flask import Flask, request, render_template_string
except ImportError:
    sys.stderr.write("ERROR: flask not installed. Run: pip install flask (in the KB venv)\n")
    sys.exit(2)

import kb_search  # noqa: E402  (同目录; 模块加载时已完成 ~/.kb config 校验)

app = Flask(__name__)

PAGE = """<!doctype html>
<html lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>kb_search index test</title>
<style>
  :root { color-scheme: light dark; }
  body { font-family: "Segoe UI", system-ui, sans-serif; max-width: 960px;
         margin: 2rem auto; padding: 0 1rem; line-height: 1.5; }
  h1 { font-size: 1.3rem; }
  .bar { display: flex; gap: .5rem; }
  input[type=text] { flex: 1; padding: .55rem .8rem; font-size: 1rem;
         border: 1px solid #8886; border-radius: .5rem; }
  button { padding: .55rem 1.2rem; font-size: 1rem; border: 0; border-radius: .5rem;
         cursor: pointer; background: #2563eb; color: #fff; }
  .meta { color: #888; font-size: .85rem; margin: .4rem 0 .2rem; }
  .hit { border: 1px solid #8884; border-radius: .5rem; padding: .6rem .9rem;
         margin: .7rem 0; overflow-wrap: anywhere; }
  .score { font-weight: 600; }
  pre { white-space: pre-wrap; margin: .3rem 0 0; font-size: .9rem;
        font-family: inherit; }
  .status { color: #888; font-size: .9rem; min-height: 1.2em; }
  .empty { color: #c00; }
</style>
</head>
<body>
<h1>kb_search 向量索引测试</h1>
<p class="meta">vault: {{ vault }} &nbsp;|&nbsp; model: {{ model }} &nbsp;|&nbsp; chunks: {{ n_chunks }}</p>
<form class="bar" onsubmit="return doSearch()">
  <input type="text" id="q" placeholder="输入查询语句 (中英皆可)…" autofocus>
  <button type="submit">Search</button>
</form>
<p class="status" id="status"></p>
<div id="results"></div>
<script>
async function doSearch() {
  const q = document.getElementById('q').value.trim();
  const status = document.getElementById('status');
  const box = document.getElementById('results');
  if (!q) return false;
  status.textContent = 'searching…';
  box.innerHTML = '';
  const t0 = performance.now();
  const r = await fetch('/api/search', {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({q, k: 8})
  });
  const hits = await r.json();
  const ms = Math.round(performance.now() - t0);
  if (!hits.length) { status.textContent = `NO HIT (${ms} ms)`; return false; }
  status.textContent = `${hits.length} hits in ${ms} ms`;
  for (const h of hits) {
    const d = document.createElement('div');
    d.className = 'hit' + (h.score < 0.35 ? ' empty' : '');
    const meta = [h.rel, h.heading].filter(Boolean).join(' | ') +
                 (h.meta_str ? ' | ' + h.meta_str : '');
    d.innerHTML = `<div class="meta">${meta}</div>` +
                  `<span class="score">${h.score.toFixed(3)}</span>` +
                  `<pre>${h.text}</pre>`;
    box.appendChild(d);
  }
  return false;
}
document.getElementById('q').addEventListener('keydown', e => {
  if (e.key === 'Enter') { e.preventDefault(); doSearch(); }
});
</script>
</body>
</html>"""


@app.route("/", methods=["GET"])
def index():
    return render_template_string(
        PAGE, vault=kb_search.VAULT, model=kb_search.MODEL_NAME,
        n_chunks=kb_search.STATE["n_chunks"],
    )


@app.route("/api/search", methods=["POST"])
def api_search():
    data = request.get_json(silent=True) or {}
    q = (data.get("q") or "").strip()
    k = max(1, min(int(data.get("k") or 8), 30))
    if not q:
        return []
    t0 = time.time()
    hits = kb_search.search(q, k=k, min_score=0.0)  # 测试页不过滤, 低分也显示
    ms = int((time.time() - t0) * 1000)
    print(f"[kb_test] {ms} ms  k={k}  {q!r}", file=sys.stderr)
    return [
        {
            "score": s,
            "rel": c["rel"],
            "heading": c.get("heading", ""),
            "meta_str": " ".join(
                f"{key}={c['meta'][key]}"
                for key in ("br_id", "defect_id", "page_id", "version", "type")
                if (c.get("meta") or {}).get(key)
            ),
            "text": c["text"][:1500],
        }
        for s, c in hits
    ]


def main() -> None:
    port = 5000
    for i, a in enumerate(sys.argv):
        if a == "--port" and i + 1 < len(sys.argv):
            port = int(sys.argv[i + 1])
    print(f"[kb_test] http://127.0.0.1:{port}  (Ctrl+C to stop)", file=sys.stderr)
    app.run(host="127.0.0.1", port=port, debug=False)


if __name__ == "__main__":
    main()
