export const meta = {
  name: 'tr-check',
  description: '在多个 SAP 系统并行核查一个 Transport Request 的内容（E070/E071/E07T/VRSD）',
  whenToUse: '用户给出一个 TR 编号，需要在单系统或多系统查它改了什么对象、状态如何',
  phases: [
    { title: '查表', detail: '每个系统一个只读 agent' },
    { title: '汇总', detail: '合并对比各系统结果' },
  ],
}

// ---- 参数（均可省略走默认值）----
// args = { trkorr: 'DL7K952170', systems: ['DL7'] }
const trkorr = args.trkorr
if (!trkorr) {
  throw new Error('缺少必填参数 trkorr（TR 编号，如 DL7K952170）')
}
const systems = args.systems && args.systems.length ? args.systems : ['DL7']

// ---- 阶段 1：并行查各系统（只读，无任何写操作）----
phase('查表')
const results = await parallel(systems.map(sys => () =>
  agent(
    '在 SAP 系统 ' + sys + ' 上执行以下只读查询（经 mcp-abap-adt-b 的 GetTableContents，' +
    '严禁任何 CreateObject/UpdateObjectSource/ActivateObject 写操作）：\n' +
    "1. E070 WHERE TRKORR = '" + trkorr + "' —— TR 类型、状态、目标系统、释放人/时间、下属任务(STRKORR)\n" +
    "2. E071 WHERE TRKORR = '" + trkorr + "' —— 对象清单（PGMID/OBJECT/OBJ_NAME），若含 CORR RELE 项须追查其子任务的对象\n" +
    "3. E07T WHERE TRKORR = '" + trkorr + "' —— TR 描述文本\n" +
    "4. 对每个主要对象名，查 VRSD WHERE OBJNAME = '<对象名>' AND DATUM >= '20260101' 的近期版本记录\n\n" +
    '以紧凑的结构化文本返回：TR 概要 / 对象清单（含对象类型中文名称，如 SFPF=Adobe 表单）/ 版本基线信息。' +
    '查无记录时明确说明「该系统无此 TR」，不要编造。',
    { label: '查:' + sys, phase: '查表' }
  )
))

const found = results.filter(Boolean)
if (!found.length) {
  return '所有系统均无结果（agent 全部失败或被跳过）。'
}

// ---- 阶段 2：汇总 ----
phase('汇总')
const report = await agent(
  '以下是同一 TR ' + trkorr + ' 在 ' + systems.length + ' 个系统（' + systems.join(', ') + '）的查询结果。' +
  '请输出 Markdown 汇总报告：若多系统结果存在差异（对象清单/状态/版本号不同）必须逐项标出。\n\n' +
  found.join('\n\n---\n\n'),
  { label: '汇总', phase: '汇总' }
)
return report
