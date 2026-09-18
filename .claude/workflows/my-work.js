export const meta = {
  name: 'my-work',
  description: '工作检查：拉取未完成 BR（Jira）与 defect（ALM），与 workfolder 快照比对出新工作并更新快照（sync 模式）；对指定 open 条目分析问题并起草建议回复（analyze 模式）',
  whenToUse: '用户询问「我有什么工作/查一下工作」时以 sync 模式执行；用户授权分析某条 open 内容后以 analyze 模式执行',
  phases: [
    { title: '采集', detail: '并行拉取 Jira 未完成 BR 与 ALM 未 closed defect' },
    { title: '比对更新', detail: '逐条与 workfolder 快照比对、写回最新内容、判定 open' },
    { title: '分析', detail: 'analyze 模式：逐条分析问题并起草建议回复' },
  ],
}

// ---- 参数 ----
// 兼容三种形态（skill 经 Skill 工具调用时 args 是字符串，程序化调用可传对象）：
//   1) 缺省或 "sync"                      → sync 模式
//   2) "analyze <目标>..."                → analyze 模式，目标写法：
//        defect 7036 / 7036               → ALM defect（快照 workfolder/defect/Defect<id>.md）
//        br 2353 / BXBRSWMS-2353          → Jira BR（快照 workfolder/BR/<号>.md）
//      多条目标用逗号或空格分隔；快照路径为最佳猜测，分析 agent 会按 id 在 workfolder/ 下兜底定位
//   3) { mode: 'analyze', items: [{ id, source, title, file }] } → analyze 模式（结构化，向后兼容）
const rawArgs = (typeof args === 'string' && args.trim().startsWith('{'))
  ? JSON.parse(args)
  : args
const strArgs = typeof rawArgs === 'string' ? rawArgs.trim() : ''
const isAnalyze = (rawArgs && typeof rawArgs === 'object' && rawArgs.mode === 'analyze')
  || /^analyze\b/i.test(strArgs)
const mode = isAnalyze ? 'analyze' : 'sync'

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
          number: { type: 'string', description: 'BR 号或 defect 数字 id，用于快照文件命名' },
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
    file: { type: 'string', description: '快照文件相对路径' },
    fileAction: { type: 'string', description: 'created / updated / unchanged' },
    open: { type: 'boolean' },
    reason: { type: 'string', description: 'open 判定依据，一句话' },
  },
  required: ['id', 'source', 'title', 'file', 'fileAction', 'open', 'reason'],
}

// ============ analyze 模式（步骤 4：对已授权条目分析并起草回复）============
if (mode === 'analyze') {
  let items = []
  if (rawArgs && typeof rawArgs === 'object' && rawArgs.items) {
    items = rawArgs.items
  } else {
    // 从字符串解析目标："analyze defect 7036"、"analyze br 2353, defect 7036"、"analyze 7036"…
    const rest = strArgs.replace(/^analyze\b/i, '').trim()
    if (rest) {
      let pendingSource = null
      for (const tok of rest.split(/[,;，；\s]+/).filter(Boolean)) {
        const low = tok.toLowerCase()
        if (low === 'defect' || low === 'br') { pendingSource = low; continue }
        const num = tok.replace(/[^0-9]/g, '')
        if (!num) continue
        items.push({
          id: low.startsWith('bxbrswms') ? 'BXBRSWMS-' + num : tok.replace(/^[^0-9]*/, ''),
          source: pendingSource === 'br' || low.startsWith('bxbrswms') ? 'jira' : 'alm',
          file: pendingSource === 'br' || low.startsWith('bxbrswms')
            ? 'workfolder/BR/' + num + '.md'
            : 'workfolder/defect/Defect' + num + '.md',
        })
        pendingSource = null
      }
    }
  }
  if (!items.length) throw new Error('analyze 模式未能从 args 解析出条目（支持 "analyze defect 7036" 或 { mode, items }）')

  const analyzePrompt = (it) =>
    '任务：分析一条 open 工作内容（来源 ' + (it.source || '（见快照）') + '，条目 ' + it.id + '），并起草建议回复。\n' +
    '⚠️ 这是纯分析任务：严禁任何写操作——不写 Jira/ALM、不改 SAP 对象、不修改任何文件。SAP 系统只允许只读查询。\n' +
    '条目标题：' + (it.title || '（见快照）') + '\n' +
    '快照文件：' + it.file + '（若该路径不存在，用 Glob 在 workfolder/BR/ 与 workfolder/defect/ 下按 id 兜底定位；仍找不到则报错返回，不要臆测内容）\n\n' +
    '步骤：\n' +
    '1. Read 快照全文，理清来龙去脉；重点是最新一条（非用户本人）回复提出了什么问题/要求。\n' +
    '2. 按需取证（只读）：\n' +
    '   - 涉及 SAP 数据/配置/对象：用 MCP 工具（GetTableContents/GetClass 等）实测查询；禁止臆测表名/字段名/类名/FM 名（项目 CLAUDE.md 强制规范），描述业务目标后再查证。\n' +
    '   - 涉及 EWM 业务：可用 Skill 工具加载 sap-ewm；若 Skill 工具不可用，改为 Read .claude/skills/sap-ewm/SKILL.md 并按其指引读 references/。其它知识型问题同理查 .claude/skills/ 下对应 skill。\n' +
    '   - 需回看 Jira/ALM 原始条目时，按 .claude/skills/jira-query 或 .claude/skills/alm-defects 的规则只读查询。\n' +
    '3. 输出（Markdown，中文；引用对方原文可保留原语言）：\n' +
    '   ## 这条工作是什么\n' +
    '   ## 问题分析\n（含经实测验证的技术细节：表/字段/程序/类/配置/事务码，注明数据来源）\n' +
    '   ## 建议回复\n（可直接粘贴的草稿，落款留空；语言与对方评论一致或中文）\n' +
    '   ## 待确认\n（需要用户拍板/补充信息的点）\n' +
    '4. 取证不到的部分如实标注「未验证」，不得编造。'

  phase('分析')
  log('对 ' + items.length + ' 条已授权条目并行分析…')
  const results = await parallel(items.map((it) => () =>
    agent(analyzePrompt(it), { label: '分析:' + it.id, phase: '分析' })))

  return items.map((it, i) => ({ id: it.id, source: it.source, file: it.file, analysis: results[i] }))
}

// ============ sync 模式（步骤 1–3）============

// ---- 步骤 1a：Jira 未完成 BR ----
const jiraPrompt =
  '任务：从内网 Jira（T&R）拉取 assign 给当前用户、未完成的全部 issue（BR）及其全部评论。\n' +
  '必做前置：Read 并完整阅读 .claude/skills/jira-query/SKILL.md，严格遵循其中全部规则（环境变量检查、JQL 必带 project 条件、fields 裁剪等）。\n' +
  '步骤：\n' +
  '1. Bash 检查 $JIRA_BASE_URL、$JIRA_PROJECT、$JIRA_USERNAME 是否已设置；有缺失则返回 ok=false，error 写明缺失的变量名，不要猜。\n' +
  '2. JQL 搜索：project = $JIRA_PROJECT AND assignee = currentUser() AND statusCategory != Done；若该 JQL 报错，降级改用 status not in (Closed, Done)。fields 取 summary,status,issuetype,priority,assignee,created,updated,labels,description。注意翻页（startAt/maxResults）取全。\n' +
  '3. 对每个 issue 用 /issue/<KEY>?fields=...,comment 拉全量评论（author、created、body），按时间正序。\n' +
  '4. number（BR 号）：优先从 summary/labels 中识别形如 BR+数字 的编号；找不到则用 issue key 的数字部分，numberSource 注明来源。\n' +
  '5. comments 的 body 保留原文，不要概括；description 保留原文。\n' +
  '返回结构化结果（ok/items）。'

// ---- 步骤 1b：ALM 未 closed defect ----
const almPrompt =
  '任务：从 Bosch ALM（OpenText ALM 24）拉取 owner 为当前用户、状态 Not Closed 的全部 defect 及其全部 comments。\n' +
  '必做前置：Read 并完整阅读 .claude/skills/alm-defects/SKILL.md，严格遵循其中全部规则（curl 加 -g、URL 空格用 %20、python 解析加 PYTHONIOENCODING=utf-8、dev-comments 字段、cookie 文件路径等）。\n' +
  '步骤：\n' +
  '1. Bash 检查 $ALM_BASE_URL、$ALM_CLIENT_ID、$ALM_CLIENT_SECRET、$ALM_DOMAIN、$ALM_PROJECT、$ALM_USER；有缺失则返回 ok=false，error 写明缺失的变量名，不要猜。\n' +
  '2. 按 skill 步骤 1 登录拿会话；按 skill 步骤 2a 查询 owner[$ALM_USER] 且 status[Not Closed] 的 defect 列表。\n' +
  '3. 对每个 defect 按 skill 步骤 2b 查单条，取得 description（HTML 转可读文本）与 dev-comments（按 skill 的输出规则逐条解析为 作者/日期/正文，HTML 实体还原）。\n' +
  '4. comments 按时间正序，body 保留原文不概括；lastCommentAuthor 取最后一条署名中的 ID。\n' +
  '5. number 取 defect 的数字 id。\n' +
  '返回结构化结果（ok/items）。'

// ---- 步骤 2+3：逐条与快照比对并更新 ----
const syncPrompt = (it, source) => {
  const isJira = source === 'jira'
  return '任务：将一条' + (isJira ? 'Jira BR' : 'ALM defect') + '的最新数据与 workfolder 快照比对，必要时更新快照，并判定是否为 open 工作内容。\n' +
    '条目最新数据（JSON）：\n' + JSON.stringify(it, null, 2) + '\n\n' +
    '规则：\n' +
    '1. 快照路径：' + (isJira
      ? 'workfolder/BR/<BR号>.md（BR 号取条目 number 字段；若 workfolder/BR/ 下已有同号但不同命名的文件，沿用既有文件）'
      : 'workfolder/defect/Defect<number>.md') +
    '。目录不存在时先 mkdir -p 创建。注意：只读写入快照文件，严禁改其它文件。\n' +
    '2. Read 读快照（不存在则视为新条目）。将「快照中已记录的回复」与数据中 comments 按 作者+日期 匹配：快照中没有的即为新增回复。\n' +
    '3. open 判定（满足任一即 open）：\n' +
    '   a. 快照文件不存在（新工作）；\n' +
    '   b. 有新增回复；\n' +
    '   c. 最后一条回复的作者不是当前用户：' + (isJira
      ? 'Jira 用户名取环境变量 $JIRA_USERNAME（Bash echo 读取），与评论 author（显示名/用户名/邮箱）匹配；无法确认作者身份时按 open 处理并在 reason 注明「作者未确认」'
      : 'ALM 用户取环境变量 $ALM_USER，与最后一条评论署名中的 <ID> 匹配') + '。\n' +
    '4. 仅当快照不存在或比对发现有新增内容时写文件（Write），否则不改（fileAction=unchanged）。文件模板：\n' +
    '\n# <number> <title>\n' +
    '- 来源: ' + (isJira ? 'Jira <id>' : 'ALM defect <id>') + '\n' +
    '- 状态: <status>\n' +
    '- 同步时间: <先用 Bash 执行 date +"%F %R" 取当前时间>\n' +
    '\n## 描述\n<description 原文>\n\n' +
    '## 回复（按时间正序）\n\n' +
    '### <序号>. <作者> (<日期>)\n\n<正文>\n\n' +
    '5. 严禁写 Jira/ALM/SAP。\n' +
    '返回结构化结果。'
}

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
log('共 ' + jobs.length + ' 条待比对（BR ' + (jira && jira.ok ? jira.items.length : '拉取失败') +
  '，defect ' + (alm && alm.ok ? alm.items.length : '拉取失败') + '）')

phase('比对更新')
const synced = (await parallel(jobs.map(([it, src]) => () =>
  agent(syncPrompt(it, src), { label: '比对:' + it.id, phase: '比对更新', schema: SYNC_SCHEMA })
))).filter(Boolean)

const open = synced.filter((s) => s.open)
const settled = synced.filter((s) => !s.open)
log('比对完成：open ' + open.length + ' 条，无新动作 ' + settled.length + ' 条。open 清单交回主会话，逐条征求用户授权后分析。')

return {
  errors,
  total: jobs.length,
  open,
  settled,
}
