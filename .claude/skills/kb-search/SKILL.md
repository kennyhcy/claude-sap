---
name: kb-search
description: 知识库语义检索与 KB 问答：对本地知识库（KB 数据目录默认 ~/.kb：向量索引 + 本地 Qwen3 embedding + kb_config.json，语料不外发）做本地向量语义检索（skill 内 kb_search.py CLI），命中后按作答规范回答知识型问题；CLI 未命中时 Grep/Glob 精确补查，再降级网络搜索。KB 未初始化时本 skill 可执行完整初始化（kb_setup.py：建索引/模型/venv）。当用户问概念/流程/配置/为什么等知识型问题、找历史相似 BR/Defect 案例、需要跨子库模糊查找、或要求搭建/初始化本地知识库检索时使用。精确字符串（表名/br_id/错误号/T-code）可直接 Grep，更快。
---

# 知识库语义检索与 KB 问答

流程：kb-search CLI 向量语义检索（vault 全库）→ Grep/Glob 精确兜底 → 网络搜索，逐级降级。

本 skill 自包含全部脚本（`kb_setup.py` / `kb_search.py` / `kb_test.py`，脚本只在 skill 目录）；数据（kb_config.json / 索引 / 模型 / venv）在 **KB 数据目录，默认 `~/.kb`**（即 `%USERPROFILE%\.kb`，无需任何环境变量）——同一用户的多个 AI 工具共用。安装/迁移/排错见同目录 `README.md`。

## 前置检查

1. KB 数据目录就绪：`~/.kb/kb_config.json` 存在且 `vault` 非空。
2. 索引已建：`~/.kb/index/state.json` 存在；venv 在 `~/.kb/.venv/`。
3. **任一不满足 → 走「初始化（KB 未就绪时）」**。

## 初始化（KB 未就绪时）

`~/.kb` 缺失或内容不全（`kb_config.json` / `index/state.json` / `.venv` 任一缺失）时，由本 skill 执行完整初始化：

1. **收集 vault 路径**（直接询问用户；KB 数据目录默认 `~/.kb`，用户想放别处时记下替代路径）。
2. **告知成本**（须用户确认后才执行）：建 venv 装依赖 + 下载模型 ~1.1GB（经 https_proxy）+ 对 vault 全库建索引（耗时可达数十分钟）。
3. **执行**（用户确认后）：
   ```bash
   python "<skill目录>/kb_setup.py" --vault "<vault目录>"
   # KB 数据目录放非默认位置时加: --kb-folder <目录>
   ```
   run_in_background 跑，期间报告进度；模型已存在自动跳过下载。
4. **收尾**：无需配置任何环境变量；跑一条冒烟 query 验证（如 `query "test" --k 1 --files`）。
5. 迁移场景（`~/.kb` 已带 model/ 或 index/）：同样跑上述命令，缺失步骤自动补齐。

## 调用命令

一律用 KB venv python 完整路径 + `-X utf8`（Windows 控制台 cp1252 打中文会崩，脚本内已兜底但双保险）；脚本用 skill 目录内的（以本 skill base directory 为准）：

```bash
PYTHONIOENCODING=utf-8 "$HOME/.kb/.venv/Scripts/python.exe" -X utf8 "<skill目录>/kb_search.py" query "<查询语句>" --k 8
```

- 查询语句直接作 argv 传入（不要经 stdin/临时文件；路径含空格注意引号）
- 增量更新自动：每次 query 前脚本自动扫描知识库变更并重嵌（秒级），无需手动 rebuild
- 可选参数：`--k N`（条数，默认 8）、`--min-score 0.35`（阈值）、`--files`（只列命中文件）、`--json`（机器可读）、`--scope docupedia|br|defects|support|projects|kb|minutes|other`（按知识库子目录过滤）
- 中文问题直接用中文原句查询（模型跨语言）；必要时补一条英文关键句提高召回
- 索引质量可视化测试：`"$HOME/.kb/.venv/Scripts/python.exe" -X utf8 "<skill目录>/kb_test.py"`（Flask 对话框，http://127.0.0.1:5000）

## 结果使用规则

- 输出格式：`[n] score | 相对路径 | 标题链 | br_id/page_id 等元数据` + chunk 内容预览（~1200 字符）
- **chunk 只是定位器**：作答前必须 Read 命中的原文件核实全文，不得仅凭 chunk 内容下结论——仅得分高不算命中
- Docupedia 命中标注 page_id/版本号；`type=log` 的 chunk 来自笔记的同步历史 log 块
- 输出预算 12KB，超出条目只列路径——用 Read 读那些文件补全

## 降级链

1. **kb-search CLI 向量语义检索**——一条命令覆盖 vault 全库；
2. **Grep/Glob 精确补查**——CLI 未命中（NO HIT / 得分普遍低 / 命中内容与问题实质不符）时，对 vault 按中英文同义词关键词检索（如 收货/Goods Receipt/GR、补货/Replenishment、盘点/Physical Inventory）。相关性不足时如实降级，宁可降级也不要牵强命中；
3. **网络搜索**——本地两级均未命中时才使用。

## 作答规范

- 用与用户问题相同的语言作答。
- 回答以文档内容为依据，标注信息来自哪个文档；文档 header 有版本号/页面更新日期，答案可能受版本影响时一并注明。
- 文档之间有冲突时，列出冲突并给出倾向判断。
- 文档未覆盖的部分明确说明「知识库未覆盖」，不要编造；基于文档的合理推断须标注为推断。
- 涉及 SAP 技术对象名（表/字段/类/FM）时只引用文档中明确出现的名称，不得臆测。
- 回答开头用一行注明来源：`kb-search（~/.kb 全库向量检索）` 或 `网络搜索（本地知识库未命中）`。

### 网络搜索层补充

- WebSearch 为主，必要时 WebFetch 打开结果页核实。
- 优先权威来源（help.sap.com、SAP Community 等官方资料），综合多个来源交叉验证，不得只凭单一结果下定论。
- 末尾以「Sources:」列出实际引用的 URL；找不到可靠答案时如实说明。

## 用户是 SAP 专家顾问

提供的答案中要包含技术细节，表、程序名、类、方法、视图、事务代码等都要指出。

## 数据边界

- 全程本地计算（fastembed/onnxruntime CPU），语料不外发
- 唯一联网动作：首次模型下载（公开权重，经 https_proxy）；之后离线
- 模型缓存固定在 `~/.kb/model/`（~1.1GB）——脚本已显式指定 cache_dir，勿依赖 fastembed 默认的 `%TEMP%\fastembed_cache`（会被存储感知/磁盘清理删除）
