#!/usr/bin/env python
"""kb_search.py — 自包含 kb 文件夹内的本地向量 RAG 检索 CLI.

本脚本随 kb-search skill 分发 (位于 skill 目录); KB 数据 (config/索引/模型)
默认在 ~/.kb (kb_setup.py 初始化时创建), 配置读 ~/.kb/kb_config.json:
vault (必填) / model (可选).
全程本地计算 (fastembed/onnxruntime CPU), 语料不外发.

用法:
  python kb_search.py query "补货策略怎么配置" [--k 8] [--min-score 0.35] [--files] [--json]
  python kb_search.py rebuild [--full]
初始化 (venv/模型/索引) 用同目录 kb_setup.py.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path

# --- Windows 控制台 UTF-8 (cp1252 打中文会崩) ---
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# --- 路径: KB 数据目录默认 ~/.kb (可用 --kb-folder 覆盖); 脚本自身随 skill 分发 ---
KB_DIR = Path.home() / ".kb"
CONFIG_FILE = KB_DIR / "kb_config.json"
if not CONFIG_FILE.exists():
    sys.stderr.write(f"ERROR: {CONFIG_FILE} not found. Run kb_setup.py first (see skill README).\n")
    sys.exit(2)
_config = json.load(open(CONFIG_FILE, encoding="utf-8"))

VAULT = _config.get("vault")
if not VAULT:
    sys.stderr.write("ERROR: ~/.kb/kb_config.json: 'vault' is empty. Set your knowledge-base root directory.\n")
    sys.exit(2)
if not Path(VAULT).is_dir():
    sys.stderr.write(f"ERROR: kb_config.json: vault directory does not exist: {VAULT}\n")
    sys.exit(2)

MODEL_NAME = _config.get("model") or "Qwen/Qwen3-Embedding-0.6B-Q"
INDEX_DIR = KB_DIR / "index"
# 模型缓存目录 (fastembed 默认放 %TEMP%, 会被存储感知/磁盘清理删除; 固定到 ~/.kb/model)
MODEL_CACHE = str(KB_DIR / "model")

# 固定排除目录 (附件/配置/模板)
EXCLUDE_DIRS = {"_attachments", "_template", ".obsidian", ".claude", ".claudian", ".trash", "node_modules", ".venv"}

# scope -> 知识库子目录前缀 (供 --scope 过滤; 默认 all 不过滤)
SCOPES = {
    "docupedia": "6.EWM Trade Docupedia",
    "br": "1.BXBRSWMS",
    "defects": "2.Defects",
    "support": "3.Supports",
    "projects": "4.Projects",
    "kb": "5.EWM Knowledge Base",
    "minutes": "7.Meeting Minutes",
    "other": "8.Other Topics",
}

# 分块参数 (按字符; Qwen3 上下文 32k, 目标 chunk ~300-800 tokens)
CHUNK_TARGET = 2000        # 章节超过此字符数按段落二切
CHUNK_MIN = 200            # 低于此字符数的相邻章节合并
OVERLAP = 320              # 二切时段落 overlap (字符)
CHUNK_PREVIEW = 1200       # 查询输出里 chunk 内容预览上限 (字符)
OUTPUT_BUDGET = 12000      # 查询输出总字符预算

STATE_FILE = INDEX_DIR / "state.json"
CHUNKS_FILE = INDEX_DIR / "chunks.jsonl"
VECTORS_FILE = INDEX_DIR / "vectors.npz"

EMBED_MODEL = None  # lazy


# ============================ 解析 / 分块 ============================

META_BLOCK_RE = re.compile(r"^```[ \t]*\n(.*?)```", re.S)
KV_LINE_RE = re.compile(r"^\s*([A-Za-z_][\w ]*):\s*(.+)$")
HEADING_RE = re.compile(r"^(#{1,3})\s+(.*)$")
WIKI_EMBED_RE = re.compile(r"!\[\[([^\]]+)\]\]")
WIKI_LINK_RE = re.compile(r"\[\[([^\]\|]+)(?:\|[^\]]*)?\]\]")
DOCUPEDIA_PAGEID_RE = re.compile(r"Page ID:\s*(\d+)\s*\|\s*Space:\s*(\S+)\s*\|\s*Version:\s*(\d+)")


def clean_text(text: str) -> str:
    """剔除图片 embed, wiki 链接保留链接文本."""
    text = WIKI_EMBED_RE.sub("", text)
    text = WIKI_LINK_RE.sub(r"\1", text)
    return text


def parse_metadata_block(text: str) -> tuple[dict, str]:
    """提取文档开头的无标记 ``` 代码块内 key-value 元数据 (BR/Defect 笔记格式).

    返回 (元数据 dict, 去除该块后的剩余文本). 非 key-value 的裸代码块原样保留.
    """
    m = META_BLOCK_RE.match(text.lstrip("﻿ \n"))
    if not m:
        return {}, text
    body = m.group(1)
    kvs = {}
    for line in body.splitlines():
        km = KV_LINE_RE.match(line)
        if km:
            kvs[km.group(1).strip().lower().replace(" ", "_")] = km.group(2).strip()
    # 至少 2 个 kv 才认定为元数据块, 否则当普通代码块保留
    if len(kvs) < 2:
        return {}, text
    rest = text[: m.start()] + text[m.end():]
    return kvs, rest


def parse_docupedia_header(text: str) -> tuple[dict, str]:
    """提取 Docupedia 中文元信息头 (源页面/Page ID/Version), 返回 (meta, 去除 header 后文本)."""
    meta = {}
    pm = DOCUPEDIA_PAGEID_RE.search(text)
    if pm:
        meta["page_id"] = pm.group(1)
        meta["space"] = pm.group(2)
        meta["version"] = pm.group(3)
        # header 在首个空行结束
        end = text.find("\n\n", pm.start())
        if end > 0 and "源页面" in text[:end]:
            text = text[end + 2:]
    return meta, text


def iter_sections(text: str):
    """按标题层级切分, yield (heading_chain, section_text)."""
    chain: list[tuple[int, str]] = []
    buf: list[str] = []
    buf_heading: list[tuple[int, str]] = []

    def flush():
        if buf:
            yield_chain = " > ".join(h for _, h in buf_heading) if buf_heading else ""
            yield_text = "\n".join(buf).strip()
            if yield_text:
                yield (yield_chain, yield_text)

    collected = []
    for line in text.splitlines():
        hm = HEADING_RE.match(line)
        if hm:
            if buf:
                collected.append((" > ".join(h for _, h in buf_heading), "\n".join(buf).strip()))
                buf = []
            level = len(hm.group(1))
            title = hm.group(2).strip()
            chain = [c for c in chain if c[0] < level]
            chain.append((level, title))
            buf_heading = list(chain)
            buf.append(line)
        else:
            buf.append(line)
    if buf:
        collected.append((" > ".join(h for _, h in buf_heading), "\n".join(buf).strip()))
    yield from (c for c in collected if c[1])


def split_long_section(text: str) -> list[str]:
    """超长章节按段落二切, 带 overlap."""
    if len(text) <= CHUNK_TARGET:
        return [text]
    paras = re.split(r"\n\s*\n", text)
    parts: list[str] = []
    cur = ""
    for p in paras:
        if cur and len(cur) + len(p) > CHUNK_TARGET:
            parts.append(cur)
            cur = cur[-OVERLAP:] + "\n\n" + p if OVERLAP else p
        else:
            cur = cur + "\n\n" + p if cur else p
    if cur:
        parts.append(cur)
    return parts


def chunk_file(path: Path, rel: str) -> list[dict]:
    """单个 md -> chunk 列表. 每 chunk: {text, context, path, rel, heading, meta}."""
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        # OneDrive 按需下载未落地的文件读取失败, 跳过
        print(f"  [skip] read failed: {rel} ({e})", file=sys.stderr)
        return []
    if not raw.strip():
        return []

    meta: dict = {}
    kvs, text = parse_metadata_block(raw)
    meta.update(kvs)
    dmeta, text = parse_docupedia_header(text)
    meta.update(dmeta)
    text = clean_text(text)

    vault_name = rel.split(os.sep)[0].split("/")[0] if (os.sep in rel or "/" in rel) else "KB"

    chunks: list[dict] = []
    for heading, sec in iter_sections(text):
        for piece in split_long_section(sec):
            chunks.append({
                "text": piece,
                "heading": heading,
                "path": str(path),
                "rel": rel.replace(os.sep, "/"),
                "vault": vault_name,
                "meta": meta,
            })

    # ```log 代码块整体成 chunk (type=log)
    for lm in re.finditer(r"```log\n(.*?)```", raw, re.S):
        log_body = lm.group(1).strip()
        if log_body:
            chunks.append({
                "text": log_body,
                "heading": "log",
                "path": str(path),
                "rel": rel.replace(os.sep, "/"),
                "vault": vault_name,
                "meta": dict(meta, type="log"),
            })

    # 无标题的短文档 (iter_sections 无产出) 整文一个 chunk
    if not chunks and text.strip():
        chunks.append({
            "text": text.strip(),
            "heading": "",
            "path": str(path),
            "rel": rel.replace(os.sep, "/"),
            "vault": vault_name,
            "meta": meta,
        })
    return chunks


def chunk_context(c: dict) -> str:
    """embedding 前拼接的前置上下文."""
    lines = [f"vault: {c['vault']}", f"file: {c['rel']}"]
    if c["heading"]:
        lines.append(f"heading: {c['heading']}")
    m = c.get("meta") or {}
    for key in ("br_id", "defect_id", "page_id", "version", "tags", "type"):
        if m.get(key):
            lines.append(f"{key}: {m[key]}")
    return "<context>\n" + "\n".join(lines) + "\n</context>\n\n" + c["text"]


def chunk_hash(c: dict) -> str:
    return hashlib.sha256(chunk_context(c).encode("utf-8")).hexdigest()[:16]


# ============================ 文件扫描 ============================

def iter_md_files() -> list[Path]:
    files: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(VAULT):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        for fn in filenames:
            if fn.lower().endswith(".md"):
                files.append(Path(dirpath) / fn)
    return files


def fingerprint(path: Path) -> dict:
    st = path.stat()
    return {"mtime": st.st_mtime, "size": st.st_size}


def content_sha(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 16), b""):
            h.update(block)
    return h.hexdigest()


def scan_changes(state: dict) -> tuple[list[Path], list[str]]:
    """对照 state.json, 返回 (变更文件, 删除的 rel)."""
    changed, removed = [], []
    seen_rels = set()
    for path in iter_md_files():
        rel = str(path).replace("\\", "/")
        seen_rels.add(rel)
        fp = fingerprint(path)
        old = state.get("files", {}).get(rel)
        if old and old.get("mtime") == fp["mtime"] and old.get("size") == fp["size"]:
            continue
        # mtime/size 变了 -> hash 确认 (OneDrive 触碰 mtime 但内容没变的情况)
        try:
            sha = content_sha(path)
        except OSError:
            print(f"  [skip] unreadable: {rel}", file=sys.stderr)
            continue
        if old and old.get("sha") == sha:
            state["files"][rel] = {**fp, "sha": sha}
            continue
        changed.append(path)
        state["files"][rel] = {**fp, "sha": sha}
    removed = [rel for rel in state.get("files", {}) if rel not in seen_rels]
    for rel in removed:
        state["files"].pop(rel, None)
    return changed, removed


# ============================ 索引 ============================

def get_model():
    global EMBED_MODEL
    if EMBED_MODEL is None:
        import onnxruntime as _ort
        from fastembed import TextEmbedding
        # 禁 arena + 双线程：arena 碎片累积在 16GB 内存机上实测可达 5-9GB
        so = _ort.SessionOptions()
        so.intra_op_num_threads = 2
        so.inter_op_num_threads = 1
        so.enable_cpu_mem_arena = False
        so.log_severity_level = 3
        EMBED_MODEL = TextEmbedding(MODEL_NAME, cache_dir=MODEL_CACHE)
        EMBED_MODEL.model.model = _ort.InferenceSession(
            str(EMBED_MODEL.model.model._model_path), sess_options=so
        )
    return EMBED_MODEL


# embedding 输入截断（字符）。attention 缓冲 O(seq²)，长 chunk 是内存失控根源；
# 语义检索截到 1600 字符（~800 tokens）信息损失可接受
EMBED_MAX_CHARS = 1600


def embed_texts(texts: list[str]) -> "np.ndarray":
    import numpy as np
    model = get_model()
    texts = [t[:EMBED_MAX_CHARS] for t in texts]
    # batch_size=4: 更大 batch 在 16GB 内存机上 attention 缓冲会 OOM（实测）
    vecs = np.stack([np.asarray(v, dtype=np.float32) for v in model.embed(texts, batch_size=4)])
    n = np.linalg.norm(vecs, axis=1, keepdims=True)
    n[n == 0] = 1.0
    return vecs / n


def build_full() -> None:
    import numpy as np
    t0 = time.time()
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    state = {"model": MODEL_NAME, "chunk_params": [CHUNK_TARGET, OVERLAP], "files": {}}
    all_chunks: list[dict] = []
    files = iter_md_files()
    print(f"Indexing {len(files)} md files ...")
    for path in files:
        rel = str(path).replace("\\", "/")
        fp = fingerprint(path)
        try:
            state["files"][rel] = {**fp, "sha": content_sha(path)}
        except OSError:
            print(f"  [skip] unreadable: {rel}", file=sys.stderr)
            continue
        all_chunks.extend(chunk_file(path, rel))
    print(f"  {len(all_chunks)} chunks, embedding ...")
    if all_chunks:
        vecs = embed_texts([chunk_context(c) for c in all_chunks])
        np.savez_compressed(VECTORS_FILE, vectors=vecs)
        with open(CHUNKS_FILE, "w", encoding="utf-8") as f:
            for c in all_chunks:
                f.write(json.dumps(c, ensure_ascii=False) + "\n")
    state["built_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    state["n_chunks"] = len(all_chunks)
    json.dump(state, open(STATE_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"Done: {len(all_chunks)} chunks in {time.time()-t0:.1f}s -> {INDEX_DIR}")


def incremental() -> None:
    """增量更新索引 (query 前自动调用)."""
    import numpy as np
    if not (STATE_FILE.exists() and CHUNKS_FILE.exists() and VECTORS_FILE.exists()):
        print("索引不存在, 请先执行: python kb/kb_search.py rebuild", file=sys.stderr)
        sys.exit(2)
    state = json.load(open(STATE_FILE, encoding="utf-8"))
    if state.get("model") != MODEL_NAME or state.get("chunk_params") != [CHUNK_TARGET, OVERLAP]:
        print("模型/分块参数已变, 自动全量重建 ...", file=sys.stderr)
        build_full()
        return
    changed, removed = scan_changes(state)
    if not changed and not removed:
        return
    print(f"  [增量] {len(changed)} 文件变更, {len(removed)} 文件删除", file=sys.stderr)
    chunks = [json.loads(l) for l in open(CHUNKS_FILE, encoding="utf-8")]
    changed_set = {str(p).replace("\\", "/") for p in changed}
    removed_set = set(removed)
    # 保留: 未变更未删除的
    kept = [c for c in chunks if c["rel"] not in removed_set and c["rel"] not in changed_set]
    kept_keys = {chunk_hash(c) for c in kept}
    # 变更文件重新分块, 只嵌新增块
    new_chunks: list[dict] = []
    to_embed: list[dict] = []
    for path in changed:
        rel = str(path).replace("\\", "/")
        for c in chunk_file(path, rel):
            new_chunks.append(c)
            if chunk_hash(c) not in kept_keys:
                to_embed.append(c)
    if to_embed:
        vecs_new = embed_texts([chunk_context(c) for c in to_embed])
        emb_map = {chunk_hash(c): v for c, v in zip(to_embed, vecs_new)}
    else:
        emb_map = {}
    # 旧向量: 按行读出
    old_vecs = np.load(VECTORS_FILE)["vectors"]
    all_chunks, all_vecs = [], []
    for c, v in zip(chunks, old_vecs):
        if c["rel"] in removed_set or c["rel"] in changed_set:
            continue
        all_chunks.append(c)
        all_vecs.append(v)
    for c in new_chunks:
        all_chunks.append(c)
        h = chunk_hash(c)
        all_vecs.append(emb_map[h] if h in emb_map else np.zeros(old_vecs.shape[1], dtype=np.float32))
    if all_vecs:
        vecs = np.stack(all_vecs)
        # 新块中未嵌的 (hash 在 kept 中但向量丢了) 不会再出现; kept 块向量一定在 old_vecs
        np.savez_compressed(VECTORS_FILE, vectors=vecs)
        with open(CHUNKS_FILE, "w", encoding="utf-8") as f:
            for c in all_chunks:
                f.write(json.dumps(c, ensure_ascii=False) + "\n")
    state["n_chunks"] = len(all_chunks)
    state["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    json.dump(state, open(STATE_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


# ============================ 查询 ============================

def load_index() -> tuple[list[dict], "np.ndarray"]:
    import numpy as np
    chunks = [json.loads(l) for l in open(CHUNKS_FILE, encoding="utf-8")]
    vecs = np.load(VECTORS_FILE)["vectors"]
    return chunks, vecs


# 索引元信息 (kb_test.py 等 embedder 复用方读取; do_query 首次运行后填充)
STATE = {"n_chunks": 0}


def search(query: str, k: int = 8, min_score: float = 0.35, scope: str | None = None) -> list[tuple[float, dict]]:
    """核心检索: 返回 [(score, chunk), ...] (供 CLI 与 kb_test.py 共用)."""
    import numpy as np
    incremental()
    chunks, vecs = load_index()
    if not chunks:
        sys.exit(2)
    STATE["n_chunks"] = len(chunks)
    qv = embed_texts([query])[0]
    sims = vecs @ qv
    order = np.argsort(-sims)

    prefix = SCOPES.get(scope, "") if scope else ""
    results = []
    for i in order:
        c = chunks[int(i)]
        if prefix and not c["rel"].replace("/", os.sep).startswith(prefix) and prefix not in c["rel"]:
            continue
        results.append((float(sims[int(i)]), c))
        if len(results) >= k:
            break
    return [(s, c) for s, c in results if s >= min_score]


def do_query(query: str, k: int, min_score: float, files_only: bool, as_json: bool, scope: str | None) -> None:
    results = search(query, k=k, min_score=min_score, scope=scope)

    if as_json:
        print(json.dumps([{
            "score": round(s, 4), "file": c["path"], "rel": c["rel"],
            "heading": c["heading"], "meta": c.get("meta"), "text": c["text"],
        } for s, c in results], ensure_ascii=False, indent=1))
        return

    if not results:
        print("NO HIT (低于 min-score)")
        return

    if files_only:
        seen = set()
        for s, c in results:
            if c["rel"] not in seen:
                seen.add(c["rel"])
                print(f"{s:.3f}  {c['path']}")
        return

    budget = OUTPUT_BUDGET
    for n, (s, c) in enumerate(results, 1):
        meta = c.get("meta") or {}
        metaline = " ".join(f"{kk}={meta[kk]}" for kk in ("br_id", "defect_id", "page_id", "version", "type") if meta.get(kk))
        head = f"[{n}] score={s:.3f} | {c['rel']}"
        if c["heading"]:
            head += f" | {c['heading']}"
        if metaline:
            head += f" | {metaline}"
        preview = c["text"][:CHUNK_PREVIEW] + (" …[截断]" if len(c["text"]) > CHUNK_PREVIEW else "")
        block = head + "\n" + preview + "\n"
        if budget - len(block) < 0:
            print(f"[{n}] score={s:.3f} | {c['rel']} | {c['heading']}  (超输出预算, 用 Read 读原文)")
            continue
        budget -= len(block)
        print(block)


def main() -> None:
    ap = argparse.ArgumentParser(description="知识库 (KB_VAULT) 本地向量 RAG 检索")
    sub = ap.add_subparsers(dest="cmd", required=True)
    qp = sub.add_parser("query", help="语义检索")
    qp.add_argument("query")
    qp.add_argument("--k", type=int, default=8)
    qp.add_argument("--min-score", type=float, default=0.35)
    qp.add_argument("--files", action="store_true", help="只列命中文件")
    qp.add_argument("--json", action="store_true", help="JSON 输出")
    qp.add_argument("--scope", choices=sorted(SCOPES), default=None, help="按知识库子目录过滤")
    rp = sub.add_parser("rebuild", help="(重)建索引")
    rp.add_argument("--full", action="store_true", help="清空重建 (默认也是全量; 参数保留)")
    args = ap.parse_args()
    if args.cmd == "rebuild":
        build_full()
    elif args.cmd == "query":
        do_query(args.query, args.k, args.min_score, args.files, args.json, args.scope)


if __name__ == "__main__":
    main()
