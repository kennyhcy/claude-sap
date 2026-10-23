export const meta = {
  name: 'work-analyze',
  description: '分析一条 open 的 BR（Jira issue）或 defect（ALM）：①同步（如同意）+读取缓存笔记 md → ②KB 知识检索 → ③按需深入分析（agent 自行选用用户同意的 MCP/SAP Note/网络） → ④写入笔记章节 → ⑤总结并草拟回复，回写 Jira/ALM 须经用户确认',
  whenToUse: '用户说「分析 BR xxxx / 分析 defect xxxx / 起草回复」，或对 work-list 同步结果授权分析某条时执行。⚠️ 主会话启动本 workflow 前必须先用 AskUserQuestion 向用户问清：①（仅 BR）是否先从 SharePoint 同步 WB；②允许使用哪些取证渠道（KB / MCP 只读查 SAP / SAP Note 检索 / 网络查找，可多选）。问清后以对象形式传入 args：{ type, id, syncWb, useKb, useMcp, useSapNote, useWeb }——未经询问不得直接启动。启动后按五步顺序执行，workflow 内 agent 非交互式，中途不得再询问用户',
  phases: [
    { title: '读取', detail: 'BR 经用户同意后先同步 SharePoint WB；读取缓存笔记全文' },
    { title: '知识', detail: '调用 KB 读取相关知识（本地知识库；用户同意时含网络查找）' },
    { title: '分析', detail: '结合 KB 知识与笔记内容判断是否需深入分析；深入分析时 agent 自行选用用户同意的渠道补充取证' },
    { title: '写入', detail: '按章节范式把分析结果写入笔记 md' },
    { title: '总结', detail: '总结分析结论并草拟回复；是否发布由用户确认（用户说「回复到 jira」）' },
  ],
}

// ---- 参数 ----
// args = { type: 'br'|'defect', id: '<号>', syncWb: bool, useKb: bool, useMcp: bool, useSapNote: bool, useWeb: bool }
// 对象形式须由主会话在启动前经 AskUserQuestion 问清用户后传入（见 whenToUse）：
//   syncWb    — 仅 BR 有效：是否先经 br-download 同步 SharePoint WB（缺省 false）
//   useKb     — 是否启用知识库检索（kb-search，缺省 true）
//   useMcp    — 是否允许 MCP 只读查 SAP（缺省 true）
//   useSapNote— 是否允许 SAP Note / KBA 检索（缺省 true）
//   useWeb    — 是否允许网络查找（缺省 false：未获同意禁止联网检索）
// 兼容旧用法：字符串 'br 2353' / 'defect 7036' 视为 KB+MCP+SAP Note 开启、不同步 WB、禁止网络查找。
const obj = (args && typeof args === 'object') ? args : null
const raw = typeof args === 'string' ? args.trim().toLowerCase() : ''
const m = raw.match(/^(br|bxbwms-|defect)\s*([0-9]+[a-z]?)/i) ||
  (obj ? [null, ('' + (obj.type || '')).toLowerCase().startsWith('br') ? 'br' : 'defect', '' + obj.id] : null)
if (!m || !m[2] || m[2] === 'undefined') {
  throw new Error('缺少或无法解析参数：应为 { type, id, syncWb, useKb, useMcp, useSapNote, useWeb } 或 "br <号>"，收到：' + JSON.stringify(args))
}
const isBR = m[1].startsWith('br') || m[1].startsWith('bxb')
const id = m[2]
const syncWb = obj ? obj.syncWb === true : false
const useKb = obj ? obj.useKb !== false : true
const useMcp = obj ? obj.useMcp !== false : true
const useSapNote = obj ? obj.useSapNote !== false : true
const useWeb = obj ? obj.useWeb === true : false
const channels = [useKb && 'KB', useMcp && 'MCP只读', useSapNote && 'SAP Note', useWeb && '网络查找'].filter(Boolean).join(' + ')
log((isBR ? 'BR ' : 'defect ') + id + '：开始分析（' + (isBR && syncWb ? '同步WB；' : '') + '许可渠道：' + channels + '）')

// ---- 通用约束（每个 agent 的 prompt 都带上许可边界）----
const permitLine =
  '⚠️ 渠道许可（用户启动前已同意，超出即为违规）：\n' +
  '- KB 本地知识库检索（本地知识库，KB 数据目录默认 ~/.kb）：' + (useKb ? '允许' : '禁止') + '\n' +
  '- MCP 只读查 SAP（mcp-abap-adt-b 只读工具，严禁 CreateObject/UpdateObjectSource/ActivateObject）：' + (useMcp ? '允许' : '禁止') + '\n' +
  '- SAP Note / KBA 检索（sap-note / sap-note-search skill）：' + (useSapNote ? '允许' : '禁止') + '\n' +
  '- 网络查找（WebSearch/WebFetch 任何联网检索）：' + (useWeb ? '允许' : '禁止') + '\n' +
  '被禁止的渠道一律不得调用；禁止臆测表名/字段名/类名/FM 名，先查证存在再引用；查不到的如实标注「未验证」，不得编造。\n\n'

// ---- schema ----
const EVIDENCE_SCHEMA = {
  type: 'object',
  properties: {
    topic: { type: 'string' },
    findings: { type: 'string', description: '取证结果的紧凑文本：实测对象/表/字段/配置/Note 编号/知识与结论，注明来源；未验证的如实标注' },
  },
  required: ['topic', 'findings'],
}

const ANALYZE_SCHEMA = {
  type: 'object',
  properties: {
    needDeepDive: { type: 'boolean', description: 'KB 知识是否足够直接回答；false=无需进一步分析' },
    analysis: { type: 'string', description: '分析结论的紧凑文本（含引用的 KB 知识点与来源）' },
    deepDiveFindings: { type: 'string', description: '深入分析阶段的补充取证结果；未做深入分析则为空字符串' },
    openQuestions: { type: 'array', items: { type: 'string' }, description: '待用户拍板/补充的点' },
  },
  required: ['needDeepDive', 'analysis'],
}

const NOTE_WRITE_SCHEMA = {
  type: 'object',
  properties: {
    file: { type: 'string', description: '写入的笔记绝对路径' },
    sectionsUpdated: { type: 'array', items: { type: 'string' }, description: '更新的章节名' },
    summary: { type: 'string', description: '分析结论总结' },
    draftReply: { type: 'string', description: '起草的可发布回复草稿原文' },
    openQuestions: { type: 'array', items: { type: 'string' }, description: '待用户拍板/补充的点' },
  },
  required: ['file', 'sectionsUpdated', 'summary', 'draftReply'],
}

// ---- 第一步：同步（仅 BR 且用户同意）+ 读取笔记 ----
phase('读取')
let wbSyncNote = '（未同步 SharePoint WB，基于本地缓存笔记分析）'
if (isBR && syncWb) {
  log('BR ' + id + '：经用户同意，先用 br-download skill 同步 SharePoint WB…')
  const wb = await agent(
    permitLine +
    '任务：按 .claude/skills/br-download/SKILL.md 的完整流程，同步 BR ' + id + '。\n' +
    '必做前置：Read 并完整阅读该 SKILL.md，严格遵循其中全部步骤（SharePoint 访问机制、下载、pandoc 转换、增量同步规则——只增不删、差异用 [Comment] 标记、log 节记录）。\n' +
    '完成后返回：同步结果摘要（WB 版本/日期、新增内容、标记的差异、笔记路径、workfolder 中 docx/md 路径）。',
    { label: '同步:SharePoint WB', phase: '读取' }
  )
  if (wb) {
    wbSyncNote = '（已同步 SharePoint WB：' + String(wb).slice(0, 300) + '）'
    log('WB 同步完成。')
  } else {
    wbSyncNote = '（WB 同步失败，基于本地缓存笔记分析）'
    log('WB 同步失败，改用现有笔记继续。')
  }
}

const readPrompt =
  '任务：读取一条' + (isBR ? 'BR' : 'defect') + '的缓存笔记全文。\n' +
  (isBR
    ? '1. Bash 检查 $BR_FOLDER 已设置，未设置则报错不猜路径。\n' +
      '2. Glob 在该目录（含 _Closed/ 子目录）按 "BR ' + id + '*.md" 查找（文件夹形式 BR <号> 标题/BR <号> 标题.md）。找不到则返回 notFound=true。\n' +
      '3. Read 笔记全文（log 节 + Scope/PR/Analysis/PS 章节），原样返回笔记全文文本与绝对路径。\n'
    : '1. Bash 检查 $DEFECT_FOLDER 已设置，未设置则报错不猜路径。\n' +
      '2. Glob 在该目录（含 _Closed/ 子目录）按 "Defect ' + id + '*.md" 查找（单文件）。找不到则返回 notFound=true。\n' +
      '3. Read 笔记全文（log 节 + Issue/Analysis/Root cause/Solution 章节），原样返回笔记全文文本与绝对路径。\n') +
  '只读操作，严禁任何写操作。'
const note = await agent(readPrompt, { label: '读取:笔记', phase: '读取', schema: {
  type: 'object',
  properties: {
    notFound: { type: 'boolean' },
    file: { type: 'string' },
    content: { type: 'string', description: '笔记全文' },
  },
  required: ['notFound'],
} })

if (!note || note.notFound) {
  return { error: '未找到' + (isBR ? 'BR ' : 'defect ') + id + ' 的缓存笔记，请先跑 work-list（工作检查）。' }
}
log('笔记已读取：' + note.file)
const notePathLine = '笔记路径：' + note.file + '（Read 全文作为上下文）。\n'
const noteContent = note.content

// ---- 第二步：KB 知识检索 ----
phase('知识')
let kbResult = null
if (useKb) {
  kbResult = await agent(
    permitLine +
    '任务：针对下面' + (isBR ? 'BR' : 'defect') + ' ' + id + ' 的内容，检索本地知识库回答相关概念/流程/配置问题。\n' +
    '必做前置：Read 并完整阅读 .claude/skills/kb-search/SKILL.md。\n' +
    '检索范围严格遵守渠道许可：优先用 kb-search CLI 对 vault 全库做向量语义检索；CLI 未命中或结果可疑时用 Grep/Glob 精确补查；网络查找' + (useWeb ? '允许，仅在前两级未命中且确有必要时使用' : '被禁止，前两级未命中就如实报告未命中') + '。\n' +
    notePathLine +
    '笔记内容（已代读，直接用作上下文）：\n<<<NOTE\n' + noteContent + '\nNOTE>>>\n\n' +
    '返回：检索命中的知识点与来源文档；未命中如实说明。',
    { label: '知识:KB 检索', phase: '知识', schema: EVIDENCE_SCHEMA }
  )
  log('KB 检索完成。')
} else {
  log('用户未启用 KB 渠道，跳过知识检索。')
}

// ---- 第三步：结合 KB 判断是否深入分析；深入分析时自行选用许可渠道 ----
phase('分析')
const analysis = await agent(
  permitLine +
  '任务：对' + (isBR ? 'BR ' : 'defect ') + id + '做分析。分两个层次执行：\n' +
  '【层次 1：判断】结合下述 KB 知识与笔记内容，判断现有信息是否已足够支撑完整分析（各需求点/问题的技术背景是否清楚、结论是否可落笔）。\n' +
  '【层次 2：按需深入】若信息不足（needDeepDive=true），你自行判断需要补充什么，并从【允许的渠道】中选用进行补充取证：\n' +
  (useMcp ? '- MCP 只读查 SAP：用 mcp-abap-adt-b 只读工具实测（GetTableContents/GetClass/GetProgram/GetTable/SearchObject 等，严禁写对象）\n' : '') +
  (useSapNote ? '- SAP Note/KBA：有编号用 .claude/skills/sap-note/（先 Read SKILL.md 全文）；无编号用 .claude/skills/sap-note-search/（先 Read SKILL.md 全文）。严禁 WebFetch 直接抓 SAP Note 正文\n' : '') +
  (useWeb ? '- 网络查找：WebSearch/WebFetch（SAP Note 正文除外，走 sap-note skill）\n' : '') +
  '若全部信息已足够（needDeepDive=false），直接给出分析结论，deepDiveFindings 留空。\n' +
  notePathLine +
  '笔记内容（已代读，直接用作上下文）：\n<<<NOTE\n' + noteContent + '\nNOTE>>>\n\n' +
  'KB 知识检索结果（JSON）：\n' + JSON.stringify(kbResult, null, 2) + '\n\n' +
  '同步状态备注：' + wbSyncNote + '\n' +
  '返回：needDeepDive / analysis（分析结论，含引用来源）/ deepDiveFindings（深入取证的实测细节，注明对象名+结论+来源）/ openQuestions。',
  { label: '分析:按需深入', phase: '分析', schema: ANALYZE_SCHEMA }
)
log(analysis && analysis.needDeepDive ? '需深入分析，补充取证完成。' : 'KB 知识已足够，无需深入取证。')

// ---- 第四步：分析结果写入笔记 ----
phase('写入')
const sectionSpec = isBR
  ? 'BR 范式（参照 $BR_FOLDER 下 BR 2440 笔记格式）：# Scope（描述浓缩改写）、# Product Requirements (PR)（[Cust. Req. n] 需求基线）、# Analysis（分析过程/实测细节/方案取舍/PoC）、# Product Specification (PS)（最终 solution，[Prod. Req. n] 条目，英文措辞）。详见 .claude/skills/br-analyze/SKILL.md。'
  : 'defect 范式：# Issue（现象+影响范围浓缩改写）、# Analysis（排查路径/实测细节/被否假设）、# Root cause（一两句根因）、# Solution（解决办法 + 起草回复草稿）。详见 .claude/skills/defect-analyze/SKILL.md。'
const writeResult = await agent(
  '任务：把下述分析结果写入缓存笔记的既有章节。\n' +
  '必做前置：Read 并完整阅读 .claude/skills/' + (isBR ? 'br-analyze' : 'defect-analyze') + '/SKILL.md，严格遵循其章节范式与写入规则。\n' +
  notePathLine +
  '先 Read 笔记全文（主体章节已有内容时，仍成立的可引用，已过时的指出并修订）。\n' +
  '章节范式：' + sectionSpec + '\n' +
  '回复与工作日志只进笔记开头的 log 代码块（格式 YYYY-MM-DD HH:mm 作者 : 内容），不进主体章节。\n' +
  '分析结果（JSON）：\n' + JSON.stringify(analysis, null, 2) + '\n\n' +
  'KB 知识检索结果（JSON）：\n' + JSON.stringify(kbResult, null, 2) + '\n\n' +
  '同步状态备注：' + wbSyncNote + '\n' +
  '写入规则：只写该笔记文件（Edit 追加/修订），不动其它文件；取证不到的标注「未验证」；不得编造。\n' +
  '最后在 Solution（defect）或建议回复处起草一条可直接粘贴到 ' + (isBR ? 'Jira' : 'ALM') + ' 的回复草稿（落款留空，语言与对方评论一致或中文）。\n' +
  '返回结构化结果（file/sectionsUpdated/summary/draftReply/openQuestions）。',
  { label: '写入:笔记章节', phase: '写入', schema: NOTE_WRITE_SCHEMA }
)

// ---- 第五步：总结与草拟回复（回写固定在主会话，须经用户确认）----
phase('总结')
log('分析完成，草稿已写入笔记。是否发布回复由主会话征求用户确认后执行（用户说「回复到 jira」）。')

return {
  id,
  type: isBR ? 'br' : 'defect',
  noteFile: writeResult ? writeResult.file : note.file,
  sectionsUpdated: writeResult ? writeResult.sectionsUpdated : [],
  summary: writeResult ? writeResult.summary : (analysis ? analysis.analysis : null),
  draftReply: writeResult ? writeResult.draftReply : null,
  openQuestions: (writeResult && writeResult.openQuestions) || (analysis && analysis.openQuestions) || [],
  wbSync: wbSyncNote,
  kbFindings: kbResult ? kbResult.findings : '（未启用 KB 渠道）',
  deepDive: analysis ? analysis.needDeepDive : false,
  deepDiveFindings: analysis ? (analysis.deepDiveFindings || '') : '',
  channels,
  // 主会话汇报与回写规范：
  // 1) 向用户转述分析总结与 openQuestions；
  // 2) 出示 draftReply 草稿原文，明确询问是否发布到 Jira/ALM；用户回复「回复到 jira」方可发布；
  // 3) 用户同意后直接发布（ALM 用 defect-alm-query skill 的评论更新；Jira 用 br-jira-query skill，REST POST /issue/<KEY>/comment）；
  // 4) 发布成功后把已发送回复（注明时间）追加到笔记 log 节。
  reportFormat: [
    '先给分析结论摘要（按笔记章节顺序，含关键技术细节与数据来源；注明是否做了深入取证、用了哪些许可渠道）。',
    '列出 openQuestions 请用户拍板。',
    '出示 draftReply 原文并询问：是否发布到 ' + (isBR ? 'Jira issue' : 'ALM defect') + '？仅当用户明确说「回复到 jira」等确认语才执行，未经确认严禁发布。',
  ].join('\n'),
}
