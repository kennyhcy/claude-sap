---
name: kb-search
description: 知识库语义检索与 KB 问答：对整个知识库根目录 $KB_VAULT（BR/Defect/Docupedia KB/会议纪要等，含 $DOCUPEDIA_FOLDER）做本地向量语义检索（kb/kb_search.py CLI，本地 Qwen3 embedding，语料不外发），命中后按作答规范回答知识型问题；CLI 未命中时 Grep/Glob 精确补查，再降级网络搜索。当用户问概念/流程/配置/为什么等知识型问题、找历史相似 BR/Defect 案例、或需要跨子库模糊查找时使用。精确字符串（表名/br_id/错误号/T-code）可直接 Grep，更快。
---

# 知识库语义检索与 KB 问答

流程：kb-search CLI 向量语义检索（$KB_VAULT 全库 + $DOCUPEDIA_FOLDER）→ Grep/Glob 精确兜底 → 网络搜索，逐级降级。

## 使用时机

- **语义问题**（概念/流程/如何做/为什么/相似案例）→ 走本 skill 全流程。典型：「补货策略怎么配置」「有没有类似 skip lot 自动 UD 的历史 defect」「XX 流程的步骤」
- **精确字符串**（表名、br_id/defect_id、错误消息号、T-code）→ 直接 Grep 更快，可跳过 CLI
- 中文问题查英文文档、中英混排查询，CLI 均可（实测跨语言命中）

## 前置检查

1. venv：`kb/.venv/Scripts/python.exe` 存在。不存在 → 按「首次安装」执行（**须用户确认**依赖安装 + 模型下载 ~1.1GB 经代理）。
2. 索引：`kb/index/state.json` 存在。不存在 → 提示执行首次全量构建（CPU 约 10-20 分钟，**须用户确认**）：
   `PYTHONIOENCODING=utf-8 kb/.venv/Scripts/python.exe -X utf8 kb/kb_search.py rebuild`

## 调用命令

一律用 venv python 完整路径 + `-X utf8`（Windows 控制台 cp1252 打中文会崩，脚本内已兜底但双保险）：

```bash
cd "<project>" && PYTHONIOENCODING=utf-8 kb/.venv/Scripts/python.exe -X utf8 kb/kb_search.py query "<查询语句>" --k 8
```

- 查询语句直接作 argv 传入（不要经 stdin/临时文件；路径含空格注意引号）
- 增量更新自动：每次 query 前脚本自动扫描知识库变更并重嵌（秒级），无需手动 rebuild
- 可选参数：`--k N`（条数，默认 8）、`--min-score 0.35`（阈值）、`--files`（只列命中文件）、`--json`（机器可读）、`--scope docupedia|br|defects|support|projects|kb|minutes|other`（按知识库子目录过滤）
- 中文问题直接用中文原句查询（模型跨语言）；必要时补一条英文关键句提高召回

## 结果使用规则

- 输出格式：`[n] score | 相对路径 | 标题链 | br_id/page_id 等元数据` + chunk 内容预览（~1200 字符）
- **chunk 只是定位器**：作答前必须 Read 命中的原文件核实全文，不得仅凭 chunk 内容下结论——仅得分高不算命中
- Docupedia 命中标注 page_id/版本号；`type=log` 的 chunk 来自笔记的同步历史 log 块
- 输出预算 12KB，超出条目只列路径——用 Read 读那些文件补全

## 降级链

1. **kb-search CLI 向量语义检索**——一条命令覆盖 $KB_VAULT 全库与 `$DOCUPEDIA_FOLDER`；
2. **Grep/Glob 精确补查**——CLI 未命中（NO HIT / 得分普遍低 / 命中内容与问题实质不符）时，对 `$DOCUPEDIA_FOLDER`（知识库的 `6.EWM Trade Docupedia` 子目录）按中英文同义词关键词检索（如 收货/Goods Receipt/GR、补货/Replenishment、盘点/Physical Inventory）。相关性不足时如实降级，宁可降级也不要牵强命中；
3. **网络搜索**——本地两级均未命中时才使用。

注意：`$DOCUPEDIA_FOLDER` 为 Docupedia 页面落盘的知识库（由 `docupedia-download` skill 维护），不适用 `workfolder/` 输出规则。

## 作答规范

- 用与用户问题相同的语言作答。
- 回答以文档内容为依据，标注信息来自哪个文档；文档 header 有版本号/页面更新日期，答案可能受版本影响时一并注明。
- 文档之间有冲突时，列出冲突并给出倾向判断。
- 文档未覆盖的部分明确说明「知识库未覆盖」，不要编造；基于文档的合理推断须标注为推断。
- 涉及 SAP 技术对象名（表/字段/类/FM）时只引用文档中明确出现的名称，不得臆测。
- 回答开头用一行注明来源：`kb-search（$KB_VAULT 全库向量检索）`、`Docupedia KB（$DOCUPEDIA_FOLDER）` 或 `网络搜索（本地知识库未命中）`。

### 网络搜索层补充

- WebSearch 为主，必要时 WebFetch 打开结果页核实。
- 优先权威来源（help.sap.com、SAP Community 等官方资料），综合多个来源交叉验证，不得只凭单一结果下定论。
- 末尾以「Sources:」列出实际引用的 URL；找不到可靠答案时如实说明。

## 用户是 SAP 专家顾问

提供的答案中要包含技术细节，表、程序名、类、方法、视图、事务代码等都要指出。

## 数据边界

- 全程本地计算（fastembed/onnxruntime CPU），语料不外发
- 唯一联网动作：首次模型下载（公开权重，经 https_proxy）；之后离线

## 首次安装（fallback 链）

1. `python -m venv kb/.venv`（现有 Python 3.14）→ `pip install fastembed numpy`（经 $https_proxy）
2. 模型 `Qwen/Qwen3-Embedding-0.6B-Q`（fastembed 支持列表内，bge-m3 **不支持**，勿再尝试）
3. fastembed 在 3.14 装不上 → venv 换 Python 3.12 重装
4. 模型下载被代理拦 → 换 `intfloat/multilingual-e5-large`（注意 e5 需 query:/passage: 前缀）或 `jinaai/jina-embeddings-v2-base-zh`
5. 内存不足 OOM → 已内置 batch_size=8；仍 OOM 减到 4

## 已验证查询（2026-10-22 smoke test）

- 「补货策略在 EWM 里怎么配置」→ 命中 Replenishment strategies 文档（sim 0.746）
- 「盘点重盘容差设置」→ 命中 Physical inventory 文档（sim 0.586）
- 「有没有类似 skip lot 自动 UD 的历史案例」→ 命中 Defect 7022 笔记（sim 0.723）
