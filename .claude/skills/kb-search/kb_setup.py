#!/usr/bin/env python
"""kb_setup.py — kb 数据目录初始化脚本 (纯 stdlib, 系统 python 运行).

本脚本与 kb_search.py/kb_test.py 同属 kb-search skill (脚本只在 skill 目录,
不进 KB 数据目录); 一切生成物 (kb_config.json/venv/model/index) 写入
KB 数据目录: 默认 ~/.kb, 可用 --kb-folder 覆盖. 已完成的步骤自动跳过,
重复运行安全; 换机器迁移后重跑即可补齐.

步骤:
  1. 配置: 生成 kb_config.json (无则), 写入 vault
  2. 模型: 交互选择 embedding 模型 (写入 config 的 model 字段)
  3. venv: 在 KB 数据目录创建 .venv 并安装 fastembed numpy flask (经 https_proxy)
  4. 模型下载: fastembed 预载所选模型到 model/ (已有则跳过)
  5. 索引: 调 skill 内 kb_search.py rebuild 对 vault 全库向量化

用法:
  python kb_setup.py --vault <path>            # 免交互 (AI 工具/agent 代跑)
  python kb_setup.py                           # 全交互
  python kb_setup.py --kb-folder <dir>         # KB 数据目录放非默认位置时
  python kb_setup.py --model <name>            # 直接指定模型
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

# 脚本所在目录 = skill 目录 (只读源); 生成物一律写 KB 数据目录
SCRIPT_DIR = Path(__file__).resolve().parent

DEFAULT_MODEL = "Qwen/Qwen3-Embedding-0.6B-Q"
MODEL_CANDIDATES = [
    DEFAULT_MODEL,                        # 默认: 多语, 快, 中文友好 (Windows CPU)
    "intfloat/multilingual-e5-large",     # 备选: fastembed 默认装不上 Qwen3 时换
    "jinaai/jina-embeddings-v2-base-zh",  # 备选: 代理拦 Qwen3 权重下载时换
]


def resolve_kb_dir(cli_value: str | None) -> Path:
    """KB 数据目录: --kb-folder > 默认 ~/.kb."""
    kb_path = Path(cli_value).resolve() if cli_value else Path.home() / ".kb"
    kb_path.mkdir(parents=True, exist_ok=True)
    return kb_path


KB_DIR = ""  # main() 里赋值 (argparse 之后)
CONFIG_FILE = VENV_DIR = MODEL_DIR = None  # 同上, 基于 KB_DIR

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def venv_py() -> Path:
    venv = KB_DIR / ".venv"
    return venv / "Scripts" / "python.exe" if os.name == "nt" else venv / "bin" / "python"


def step_config(args) -> dict:
    """生成/补全 kb_config.json."""
    if CONFIG_FILE.exists():
        cfg = json.load(open(CONFIG_FILE, encoding="utf-8"))
    else:
        cfg = {"vault": "", "model": DEFAULT_MODEL}
        json.dump(cfg, open(CONFIG_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        print(f"[setup] generated {CONFIG_FILE}")

    if args.vault:
        cfg["vault"] = args.vault
    if args.model:
        cfg["model"] = args.model

    if not cfg.get("vault"):
        print(f"[setup] vault not set. Edit {CONFIG_FILE} and set 'vault' to your knowledge-base root directory.")
        print("        (在 kb_config.json 的 vault 字段填知识库根目录, 然后重跑本脚本)")
        sys.exit(2)
    if not Path(cfg["vault"]).is_dir():
        print(f"[setup] ERROR: vault directory does not exist: {cfg['vault']}")
        sys.exit(2)

    json.dump(cfg, open(CONFIG_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"[setup] config OK: vault={cfg['vault']} model={cfg.get('model')}")
    return cfg


def step_model_choice(cfg: dict) -> None:
    """模型选择 (config 已定且非默认提示不改; 免交互模式直接用 config 值)."""
    if not sys.stdin.isatty():
        return
    if cfg.get("model") and cfg["model"] != DEFAULT_MODEL:
        return  # 已明确选过
    print("\n[setup] select embedding model (默认直接回车):")
    for i, m in enumerate(MODEL_CANDIDATES, 1):
        tag = " (recommended)" if i == 1 else ""
        print(f"  {i}. {m}{tag}")
    try:
        choice = input(f"  choice [1]: ").strip()
    except EOFError:
        choice = ""
    if choice and choice.isdigit() and 1 <= int(choice) <= len(MODEL_CANDIDATES):
        cfg["model"] = MODEL_CANDIDATES[int(choice) - 1]
        json.dump(cfg, open(CONFIG_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"[setup] model = {cfg.get('model')}")


def step_venv() -> None:
    """创建 venv + 装依赖 (已存在则跳过)."""
    if venv_py().exists():
        print("[setup] venv exists (.venv), skip")
        return
    print("[setup] creating venv ...")
    subprocess.check_call([sys.executable, "-m", "venv", str(KB_DIR / ".venv")])
    # pip 经代理装依赖 (首次联网动作); flask 供 kb_test.py 测试对话框
    env = dict(os.environ)
    subprocess.check_call([
        str(venv_py()), "-m", "pip", "install", "--quiet", "fastembed", "numpy", "flask",
    ], env=env)
    print("[setup] venv ready (fastembed + numpy + flask installed)")


def step_model_download(cfg: dict) -> None:
    """预载所选模型到 model/ (目录已有内容则跳过)."""
    has_model = MODEL_DIR.exists() and any(MODEL_DIR.iterdir())
    if has_model:
        print(f"[setup] model cache exists ({MODEL_DIR.name}/), skip download")
        return
    print(f"[setup] downloading model {cfg.get('model')} (~1.1GB, via proxy) ...")
    code = (
        "from fastembed import TextEmbedding;"
        f"TextEmbedding({cfg.get('model')!r}, cache_dir=r'{MODEL_DIR}');"
        "print('model cached')"
    )
    subprocess.check_call([str(venv_py()), "-c", code])
    print("[setup] model ready")


def step_index() -> None:
    """对 vault 全库建索引 (已有索引则提示可直接用增量)."""
    state = KB_DIR / "index" / "state.json"
    if state.exists():
        print("[setup] index exists, skip rebuild (增量自动, 无需重建)")
        return
    print("[setup] building index (CPU 时长取决于 vault 大小, 可达数十分钟) ...")
    subprocess.check_call([
        str(venv_py()), "-X", "utf8", str(SCRIPT_DIR / "kb_search.py"), "rebuild",
    ])
    print("[setup] index ready")


def main() -> None:
    global KB_DIR, CONFIG_FILE, VENV_DIR, MODEL_DIR
    ap = argparse.ArgumentParser(description="kb data folder initialization (config / venv / model / index)")
    ap.add_argument("--kb-folder", help="KB data directory (default: ~/.kb)")
    ap.add_argument("--vault", help="knowledge-base root directory (写入 kb_config.json)")
    ap.add_argument("--model", help="embedding model name (写入 kb_config.json)")
    args = ap.parse_args()

    KB_DIR = resolve_kb_dir(args.kb_folder)
    CONFIG_FILE = KB_DIR / "kb_config.json"
    VENV_DIR = KB_DIR / ".venv"
    MODEL_DIR = KB_DIR / "model"
    print(f"[setup] KB dir = {KB_DIR}")

    cfg = step_config(args)
    step_model_choice(cfg)
    step_venv()
    step_model_download(cfg)
    step_index()

    print("\n[setup] all done. usage:")
    py = str(venv_py())
    print(f'  "{py}" -X utf8 "{SCRIPT_DIR / "kb_search.py"}" query "<问题>" --k 8')
    print(f'  "{py}" -X utf8 "{SCRIPT_DIR / "kb_test.py"}"   (浏览器打开 http://127.0.0.1:5000 测试索引)')


if __name__ == "__main__":
    main()
