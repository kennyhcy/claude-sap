export const meta = {
  name: 'work-list',
  description: '工作检查：拉取未完成 BR（Jira）与 defect（ALM），把最新状态与回复增量更新到笔记（$BR_FOLDER/$DEFECT_FOLDER）的 log 代码块（笔记不存在则按模板创建并填标题/描述）。返回 open 清单。分析经 work-analyze workflow 另行执行。',
  whenToUse: '用户询问「我有什么工作/查一下工作」时执行',
  phases: [
    { title: '采集', detail: '并行拉取 Jira 未完成 BR 与 ALM 未 closed defect' },
    { title: '同步笔记', detail: '逐条把最新状态与回复更新到笔记 log 代码块（缺失则创建），判定 open' },
  ],
}

// ---- 参数 ----
// 无参数（或任意字符串）→ 拉取并同步。分析已拆分到 work-analyze workflow，本 workflow 不做分析。
const strArgs = typeof args === 'string' ? args.trim() : ''

// ---- schema ----
const COMMENT = {
  type: 'object',
  properties: {
    author: { type: 'string', description: '作者姓名/ID（原始署名）' },
    date: { type: 'string', description: '发表时间（原始字符串）' },
    body: { type: 'string', description: '正文原文，不概括' },
  },
  required: ['author', 'date', 'body'],
}

const FETCH_SCHEMA = {
  type: 'object',
  properties: {
    ok: { type: 'boolean', description: '拉取是否成功' },
    error: { type: 'string', description: '失败原因（环境变量缺失/接口报错等）' },
    items: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          id: { type: 'string', description: 'Jira issue key 或 ALM defect id' },
          number: { type: 'string', description: 'BR 号或 defect 数字 id，用于笔记文件命名' },
          numberSource: { type: 'string', description: 'number 取自哪里' },
          title: { type: 'string', description: '标题（Jira summary / ALM name）' },
          status: { type: 'string' },
          issuetype: { type: 'string' },
          updated: { type: 'string', description: '最后更新时间（原始字符串）' },
          description: { type: 'string', description: '描述的可读文本版，不概括' },
          comments: { type: 'array', items: COMMENT, description: '按时间正序' },
          lastCommentAuthor: { type: 'string', description: '最后一条评论的作者' },
        },
        required: ['id', 'number', 'title', 'status', 'comments'],
      },
    },
  },
  required: ['ok', 'items'],
}

const SYNC_SCHEMA = {
  type: 'object',
  properties: {
    id: { type: 'string' },
    source: { type: 'string', description: 'jira 或 alm' },
    title: { type: 'string' },
    status: { type: 'string' },
    file: { type: 'string', description: '笔记绝对路径' },
    fileAction: { type: 'string', description: 'created / updated / unchanged' },
    open: { type: 'boolean' },
    reason: { type: 'string', description: 'open 判定依据，一句话' },
  },
  required: ['id', 'source', 'title', 'file', 'fileAction', 'open', 'reason'],
}

// ---- 阶段 1：采集（只拉取，技术细节在 br-jira-query / defect-alm-query skill）----

const jiraPrompt =
  '任务：从内网 Jira（T&R）拉取 assign 给当前用户、未完成的全部 issue（BR）及其全部评论。\n' +
  '必做前置：Read 并完整阅读 .claude/skills/br-jira-query/SKILL.md 全文，严格遵循其中全部规则（环境变量检查、项目范围、curl 调用方式、fields 裁剪等）。\n' +
  '要求：\n' +
  '1. 拉取范围：project = $JIRA_PROJECT 且 assignee = currentUser() 且未完成（statusCategory != Done；该 JQL 报错则按 skill 允许的方式降级）。注意翻页取全。\n' +
  '2. 每个 issue 拉全量评论（author、created、body），按时间正序；body 与 description 保留原文不概括。\n' +
  '3. number（BR 号）：优先从 summary/labels 中识别形如 BR+数字 的编号；找不到则用 issue key 的数字部分，numberSource 注明来源。\n' +
  '4. 环境变量缺失时返回 ok=false，error 写明缺失的变量名，不要猜。\n' +
  '返回结构化结果（ok/items）。'

const almPrompt =
  '任务：从 Bosch ALM（OpenText ALM 24）拉取 owner 为当前用户、状态 Not Closed 的全部 defect 及其全部 comments。\n' +
  '必做前置：Read 并完整阅读 .claude/skills/defect-alm-query/SKILL.md 全文，严格遵循其中全部规则（环境变量、关键约束、登录会话、列表/单条查询、dev-comments 解析等）。\n' +
  '要求：\n' +
  '1. 查询条件：owner[$ALM_USER] 且 status[Not Closed]。\n' +
  '2. 每个 defect 取 description（HTML 转可读文本）与 dev-comments（按 skill 输出规则逐条解析为 作者/日期/正文，HTML 实体还原），comments 按时间正序、body 保留原文不概括；lastCommentAuthor 取最后一条署名中的 ID。\n' +
  '3. number 取 defect 的数字 id。\n' +
  '4. 环境变量缺失时返回 ok=false，error 写明缺失的变量名，不要猜。\n' +
  '返回结构化结果（ok/items）。'

phase('采集')
log('并行拉取 Jira 未完成 BR 与 ALM 未 closed defect…')
const [jira, alm] = await parallel([
  () => agent(jiraPrompt, { label: '采集:Jira BR', phase: '采集', schema: FETCH_SCHEMA }),
  () => agent(almPrompt, { label: '采集:ALM defect', phase: '采集', schema: FETCH_SCHEMA }),
])

const errors = []
if (!jira || !jira.ok) errors.push('Jira: ' + ((jira && jira.error) || '拉取失败'))
if (!alm || !alm.ok) errors.push('ALM: ' + ((alm && alm.error) || '拉取失败'))

const jobs = []
if (jira && jira.ok) for (const it of jira.items) jobs.push([it, 'jira'])
if (alm && alm.ok) for (const it of alm.items) jobs.push([it, 'alm'])
log('共 ' + jobs.length + ' 条待同步（BR ' + (jira && jira.ok ? jira.items.length : '拉取失败') +
  '，defect ' + (alm && alm.ok ? alm.items.length : '拉取失败') + '）')

// ---- 阶段 2：同步笔记（只动 log 节；标题/描述仅在创建时填）----

// 笔记路径/文件名清洗/先查后建/模板/log 追加规则由 br-note / defect-note skill 定义；
// 本 workflow 只约定：本阶段只做 log 级同步（状态+回复），不做章节内容填充（分析是 work-analyze 的事）。
const syncPrompt = (it, source) => {
  const isJira = source === 'jira'
  const skill = isJira ? 'br-note' : 'defect-note'
  return '任务：将一条' + (isJira ? 'Jira BR' : 'ALM defect') + '的最新状态与回复同步到笔记的 log 代码块。**只做 log 级同步，不做任何章节内容分析/填充**（分析经 work-analyze workflow 另行执行）。\n' +
    '条目最新数据（JSON）：\n' + JSON.stringify(it, null, 2) + '\n\n' +
    '必做前置：Read 并完整阅读 .claude/skills/' + skill + '/SKILL.md 全文，严格遵循其中全部规则——路径规则与 Windows 文件名清洗、先查后建、模板（log 代码块 + 主体章节）、以及「Sync 增量更新规则」节。\n' +
    '本阶段边界（比 skill 的 Sync 规则更收窄）：\n' +
    '1. 笔记不存在 → 按 skill 模板创建：填第一行创建时间、元数据块（title/编号/System/Warehouse/Data 等已知信息）、log 节「Created」行；主体章节只放标题（# Issue 或 # Scope 起头的空章节骨架），description **不加工**放入 ' + (isJira ? '# Scope 上方的简述或留待分析' : '# Issue 节') + '（原文照抄即可，浓缩改写留给分析阶段）。\n' +
    '2. 笔记已存在 → 不动主体章节与元数据，只在 log 节末尾追加新增回复（按「作者+日期」比对，格式与既有 log 行一致）；元数据块的状态类字段可更新为最新 status。\n' +
    '3. open 判定（满足任一即 open）：a. 笔记不存在；b. 有新增回复；c. 最后一条回复作者不是当前用户（' + (isJira ? '$JIRA_USERNAME 与评论 author 匹配' : '$ALM_USER 与最后评论署名 <ID> 匹配') + '）。\n' +
    '4. 无新增且笔记已存在 → 不写文件（fileAction=unchanged）。\n' +
    '5. 只读写入该条目的笔记文件，严禁写其它文件；严禁写 Jira/ALM/SAP。\n' +
    '返回结构化结果（file 返回笔记绝对路径）。'
}

phase('同步笔记')
const synced = (await parallel(jobs.map(([it, src]) => () =>
  agent(syncPrompt(it, src), { label: '同步:' + it.id, phase: '同步笔记', schema: SYNC_SCHEMA })
))).filter(Boolean)

const open = synced.filter((s) => s.open)
const settled = synced.filter((s) => !s.open)
log('同步完成：open ' + open.length + ' 条，无新动作 ' + settled.length + ' 条。open 清单交回主会话；分析经 work-analyze workflow 逐条执行（用户授权后）。')

return {
  errors,
  total: jobs.length,
  open,
  settled,
  // 主会话最终汇报格式规范（一览表必须包含：条目、title、最后回复人、当前责任方、下一步、过往总结）
  reportFormat: [
    'open 与 settled 条目各出一张一览表，每行含：条目（id）、title、最后回复人（姓名+日期）。',
    'open 条目表后逐条用 1-3 句中文点出这条工作是什么、等你做什么（基于 title 与最后回复，不做深入分析）。',
    '表格之外的正文按「🆕 新工作 → open → settled」组织，保持简洁。',
    '结尾提示：要深入分析某条时说「分析 BR/defect <号>」，将经 work-analyze workflow 执行。',
  ].join('\n'),
}
