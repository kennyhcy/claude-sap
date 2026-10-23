# kb-search — Self-contained Local Knowledge-Base Search (Vector RAG)

自包含的本地知识库向量检索 skill。**脚本全部在本 skill 文件夹**（检索 CLI、初始化脚本、
一键安装 bat、配置模板、说明）；数据（kb_config.json / 向量索引 / 模型 / venv）统一在
**KB 数据目录，默认 `~/.kb`**（即 `%USERPROFILE%\.kb`，无需任何环境变量）——
同一用户的多个 AI 工具共用同一份数据。

Everything script-side ships inside this skill folder (search CLI, setup script, one-click bat,
config template, this README). Data (config, vector index, model, venv) lives in the KB data
folder, defaulting to `~/.kb` — no environment variables needed — and is shared by all AI tools.

## Folder layout

```
.claude/skills/kb-search/          ← 本 skill (脚本只在这里 / scripts live only here)
├── SKILL.md                       # agent 使用规则 (agent usage rules)
├── kb_search.py                   # 检索 CLI (search CLI)
├── kb_setup.py                    # 初始化脚本 (setup / migration re-run)
├── kb_test.py                     # 向量索引测试对话框 (Flask + HTML5, browser UI)
├── kb_setup.bat                   # Windows 一键初始化 (prompts for vault dir)
├── kb_config.example.json         # 配置模板
└── README.md                      # 本文件

~/.kb/                             ← KB 数据目录 (default, created by setup)
├── kb_config.json                 # vault (必填) / model (可选) — 含本地路径, 不外传
├── .venv/                         # Python venv (setup 创建)
├── model/                         # embedding 模型缓存 (~1.1GB)
└── index/                         # 向量索引
```

## Quick start

**Windows (easiest / 最简单)**: double-click `kb_setup.bat` — it prompts for your
knowledge-base root directory (md files to be indexed), then runs the full setup.

**Command line / agent-driven:**

```bash
python kb_setup.py --vault "C:\path\to\your\notes"
# KB 数据目录想放非默认位置: 加 --kb-folder "D:\somewhere\.kb"
```

（Setup does, in order: generate/complete `~/.kb/kb_config.json` → pick embedding model →
create `~/.kb/.venv` + install `fastembed numpy flask` → download model → build index over
the whole vault. Rerun anytime — completed steps are skipped.
重跑安全，已完成步骤自动跳过；换机器迁移后重跑即可补齐。）

Manual config if you prefer: create `~/.kb/kb_config.json` (copy the example):

```json
{
  "vault": "C:/path/to/your/knowledge-base-root",
  "model": "Qwen/Qwen3-Embedding-0.6B-Q"
}
```

（`vault` 必填：指向整个知识库根目录，其下所有 `.md` 都会被向量化；`model` 可选。）

## AI-tool integration

**Claude Code (this skill)**: install this skill. Nothing else to configure —
scripts resolve `~/.kb` themselves. If the KB data folder is missing or incomplete,
the skill's initialization flow runs `kb_setup.py` for you.

**Other tools / direct use**: call the CLI with the KB venv + skill script:

```bash
# Windows (Git Bash)
PYTHONIOENCODING=utf-8 "$HOME/.kb/.venv/Scripts/python.exe" -X utf8 "<skill目录>/kb_search.py" \
  query "补货策略怎么配置" --k 8

# query options
#   --k N            结果条数 (default 8)
#   --min-score F    相似度阈值 (default 0.35)
#   --files          只列命中文件
#   --json           机器可读 JSON 输出
#   --scope NAME     按知识库子目录过滤 (docupedia|br|defects|... 见脚本内 SCOPES;
#                    子目录名与你的库不同时可编辑 SCOPES)
#   rebuild          全量重建索引 (首次 setup 自动做过)
```

增量：每次 query 前自动扫描 vault 变更并重嵌新增 chunk，无需手动重建。
（Incremental indexing is automatic on every query — only changed files are re-embedded.）

## Index test dialog / 索引测试对话框

Browser UI to eyeball retrieval quality: type a query, get chunks with score/path/heading/preview.

```bash
python "<skill目录>/kb_test.py" [--port 5000]   # 缺依赖时自动用 ~/.kb/.venv 重启
# then open http://127.0.0.1:5000
```

（低分命中也会显示（便于观察阈值效果）；服务仅监听 127.0.0.1，本地测试用。）

## Migration (copy to another machine)

1. Copy `~/.kb` (including `model/` to skip the ~1.1GB download) **and** this skill folder
   (scripts live only here).
2. Delete `~/.kb/.venv` if the target machine differs, then rerun `kb_setup.bat`
   (or `python kb_setup.py --vault ...`) — it recreates the venv and rebuilds the index if missing.
（换机器：`~/.kb` + skill 一起拷 → 重跑 setup 即可；模型随夹带走免下载，索引会自动重建。
venv 含绝对路径，跨机要删掉重由 setup 建。）

## Troubleshooting

- **fastembed won't install** (Python 3.14): recreate the venv with Python 3.12 —
  delete `~/.kb/.venv/`, then `py -3.12 -m venv .venv` and rerun setup.
- **Model download blocked by proxy**: set `model` in `~/.kb/kb_config.json` to
  `intfloat/multilingual-e5-large` or `jinaai/jina-embeddings-v2-base-zh`, delete `~/.kb/model/`, rerun setup.
- **OOM on large vault**: `kb_search.py` already uses `batch_size=4`; reduce further if needed.
- **`kb_config.json not found` / `vault is empty`**: run `kb_setup.py --vault <dir>` first;
  the config must have a non-empty `vault`.
- Console prints garbled Chinese: always use `-X utf8` (and `PYTHONIOENCODING=utf-8`).

## Data boundary

- 100% local computation (fastembed/onnxruntime CPU). Corpus and embeddings never leave the machine.
- Only network action ever needed: the one-time model download (public weights, via your proxy).
- （全程本地计算，语料不外发；唯一联网动作是首次模型下载，权重为公开模型。）
