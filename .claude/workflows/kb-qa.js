export const meta = {
  name: 'kb-qa',
  description: '回答知识型问题：优先查项目 docupedia/ 知识库 → 环境变量 WIKI_DIR 指向的知识库 → 网络搜索，逐级降级',
  whenToUse: '用户提出概念/流程/配置等知识型问题，需要先查本地知识库、未命中再降级网络搜索时',
  phases: [
    { title: '检索', detail: 'docupedia/ 与 WIKI_DIR 知识库逐级查找' },
    { title: '解答', detail: '载入命中文档作答；全部未命中时网络搜索' },
  ],
}

// ---- 参数 ----
// args = { question: '用户的问题' } 或直接传字符串
const question = typeof args === 'string' ? args : (args && args.question)
if (!question) {
  throw new Error('缺少必填参数 question（用户的问题）')
}

const SEARCH_SCHEMA = {
  type: 'object',
  properties: {
    hit: { type: 'boolean', description: '是否找到与问题实质相关的文档' },
    files: { type: 'array', items: { type: 'string' }, description: '相关文档路径清单（相对项目根目录，按相关性排序）' },
    note: { type: 'string', description: '一句话说明命中了什么，或为什么未命中' },
  },
  required: ['hit', 'files', 'note'],
}

const searchPrompt = (dirLabel, extra) =>
  '用户问题：' + question + '\n\n' +
  '请在「' + dirLabel + '」下检索与该问题相关的文档（只读操作：Glob/Grep/Read，严禁任何写操作）。\n' +
  '方法：\n' +
  '1. 从问题中提取检索关键词。文档多为英文（SAP/仓储业务术语），问题可能是中文——须同时构造中英文关键词，并考虑同义词（如 收货/Goods Receipt/GR、补货/Replenishment、盘点/Physical Inventory）。\n' +
  '2. 先 Glob 看目录结构，再 Grep 关键词定位候选文件，最后 Read 候选文件的相关段落确认内容确实覆盖问题实质——仅文件名沾边不算命中。\n' +
  '3. 相关性不足时如实返回 hit=false，宁可降级到下一级来源也不要牵强命中。\n' +
  (extra || '') +
  '\n返回结构化结果：hit=是否命中；files=相关文档路径清单（相对项目根目录，按相关性排序，最多 5 个）；note=一句话说明。'

// ---- 第 1 级：项目 docupedia/ 知识库 ----
log('第 1 级：检索项目 docupedia/ 知识库…')
const r1 = await agent(searchPrompt('项目 docupedia/ 目录'), { label: '检索:docupedia', phase: '检索', schema: SEARCH_SCHEMA })

let source = null
let files = []
if (r1 && r1.hit && r1.files.length) {
  source = 'docupedia/（项目知识库）'
  files = r1.files
} else {
  // ---- 第 2 级：WIKI_DIR 知识库 ----
  log('docupedia/ 未命中，第 2 级：检索 $WIKI_DIR 知识库…')
  const r2 = await agent(
    searchPrompt('由环境变量 WIKI_DIR 指定的知识库目录',
      '\n先用 Bash 执行 `echo "$WIKI_DIR"` 读取目录路径：若为空/未设置，直接返回 hit=false，note 写明「WIKI_DIR 未设置」；若目录不存在同样返回 hit=false。已设置且存在时，在该目录下按上述方法检索（Windows Git Bash 环境，路径按实际输出使用）。\n'),
    { label: '检索:WIKI_DIR', phase: '检索', schema: SEARCH_SCHEMA }
  )
  if (r2 && r2.hit && r2.files.length) {
    source = 'WIKI_DIR（外部知识库）'
    files = r2.files
  }
}

// ---- 命中：载入文档分析作答 ----
if (source) {
  log('在 ' + source + ' 命中 ' + files.length + ' 个文档，载入分析作答。')
  return await agent(
    '用户问题：' + question + '\n\n' +
    '已在与问题相关的知识库（' + source + '）中检索到以下文档：\n' +
    files.map(f => '- ' + f).join('\n') + '\n\n' +
    '请逐个 Read 这些文档（相对项目根目录的路径），基于文档内容分析并回答用户问题：\n' +
    '- 用与用户问题相同的语言作答。\n' +
    '- 回答须以文档内容为依据，标注信息来自哪个文档；文档 header 里有版本号/页面更新日期，答案可能受版本影响时一并注明。\n' +
    '- 文档之间有冲突时，列出冲突并给出倾向判断。\n' +
    '- 文档未覆盖的部分明确说明「知识库未覆盖」，不要编造；基于文档的合理推断须标注为推断。\n' +
    '- 涉及 SAP 技术对象名（表/字段/类/FM）时只引用文档中明确出现的名称，不得臆测。\n' +
    '- 回答开头用一行注明：来源：' + source + '。',
    { label: '解答', phase: '解答' }
  )
}

// ---- 两级知识库均未命中：网络搜索 ----
log('两级知识库均未命中，降级网络搜索。')
return await agent(
  '用户问题：' + question + '\n\n' +
  '本地两级知识库（项目 docupedia/、环境变量 WIKI_DIR 指向的目录）均未检索到相关文档，请改用网络检索回答（WebSearch 为主，必要时 WebFetch 打开结果页核实）。\n' +
  '要求：\n' +
  '- 用与用户问题相同的语言作答，优先权威来源（如 help.sap.com、SAP Community 等官方资料）。\n' +
  '- 综合多个来源交叉验证后作答，不得只凭单一结果下定论。\n' +
  '- 涉及 SAP 技术对象名（表/字段/类/FM）时只引用来源中明确出现的名称，不得臆测。\n' +
  '- 回答开头用一行注明：来源：网络搜索（本地知识库未命中）；回答末尾以「Sources:」列出实际引用的 URL。\n' +
  '- 若网络检索也找不到可靠答案，如实说明。',
  { label: '网络搜索作答', phase: '解答' }
)
