// Task 05：审计表 / A-B-C 结果 / X-Y-Z 盲评 / key / 报告
import fs from 'node:fs'
import path from 'node:path'
import crypto from 'node:crypto'

const ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1')), '..')
const DATA = path.join(ROOT, 'data')
const cases = JSON.parse(fs.readFileSync(path.join(DATA, 'task05_cases.json'), 'utf8'))
const sha1 = (s) => crypto.createHash('sha1').update(s).digest('hex')
const q = (v) => `"${String(v ?? '').replace(/"/g, '""')}"`

// 1) 审计表
const auditCols = ['video_id', 'title', 'topic', 'context_quality', 'fact_id', 'fact_text', 'source_type', 'source_ref', 'status', 'note']
const audit = []
for (const c of cases) {
  for (const f of c.facts) {
    audit.push({
      video_id: c.bvid, title: c.title, topic: c.topic, context_quality: c.context_quality,
      fact_id: f.id, fact_text: f.text, source_type: f.source, source_ref: f.ref, status: f.status,
      note: f.status === 'needs_review' ? '动机/含义无直接依据，生成时不得写成事实' : '',
    })
  }
}
fs.writeFileSync(path.join(DATA, 'task05_context_audit.csv'),
  '\uFEFF' + [auditCols.join(','), ...audit.map((r) => auditCols.map((k) => q(r[k])).join(','))].join('\r\n') + '\r\n', 'utf8')

// 2) 结果 CSV
const resCols = ['video_id', 'url', 'topic', 'context_quality', 'baseline_comment', 'v1_comment', 'v2_comment', 'facts_used', 'unconfirmed', 'notes']
const res = cases.map((c) => ({
  video_id: c.bvid,
  url: `https://www.bilibili.com/video/${c.bvid}/`,
  topic: c.topic,
  context_quality: c.context_quality,
  baseline_comment: c.A,
  v1_comment: c.B,
  v2_comment: c.C,
  facts_used: c.facts.map((f) => `[${f.source}] ${f.text}`).join(' | '),
  unconfirmed: c.unconfirmed,
  notes: [
    c.issues.A?.length ? `A: ${c.issues.A.join('；')}` : '',
    c.issues.B?.length ? `B: ${c.issues.B.join('；')}` : '',
    c.issues.C?.length ? `C: ${c.issues.C.join('；')}` : '',
  ].filter(Boolean).join(' / '),
}))
fs.writeFileSync(path.join(DATA, 'task05_results.csv'),
  '\uFEFF' + [resCols.join(','), ...res.map((r) => resCols.map((k) => q(r[k])).join(','))].join('\r\n') + '\r\n', 'utf8')

// 3) 盲评 + key
const perms = [['A', 'B', 'C'], ['A', 'C', 'B'], ['B', 'A', 'C'], ['B', 'C', 'A'], ['C', 'A', 'B'], ['C', 'B', 'A']]
const keyRows = []
const md = [
  '# 盲评：三版个人风格对照（任务 05）',
  '',
  '> 每个视频下有三版候选，已随机标成 **X / Y / Z**，顺序逐条打乱。请不要参考 `data/task05_results.csv` 或 key，先只看这里。',
  '> 允许三版都不合格；也可以选“都不发”。不要按字数/条数打分。',
  '',
  '## 评分维度（每条 1–5 分）',
  '',
  '- **像本人**：语气、句式、用词像不像本人。',
  '- **贴合视频**：有没有接住这个视频的具体内容。',
  '- **有实际内容**：有没有给出反应/判断/细节，而不是空泛复述。',
  '- **不公式化**：1 = 很模板，5 = 不像模板。',
  '- **愿意直接发**：是 / 否。',
  '- **事实/立场问题**：无 / 有（写明具体原因；这一项单独统计，不能被其他高分抵消）。',
  '',
  '## 逐条',
  '',
]
cases.forEach((c, i) => {
  const perm = perms[parseInt(sha1(c.bvid).slice(0, 4), 16) % 6]
  const map = { A: c.A, B: c.B, C: c.C }
  const X = map[perm[0]], Y = map[perm[1]], Z = map[perm[2]]
  keyRows.push({ bvid: c.bvid, X: perm[0], Y: perm[1], Z: perm[2] })
  md.push(`### ${i + 1}. ${c.title}`)
  md.push('')
  md.push(`- 视频：${c.bvid} · ${c.topic} · 语境 ${c.context_quality}`)
  md.push('- 已核验事实：')
  for (const f of c.facts) md.push(`  - [${f.source}] ${f.text}`)
  md.push(`- 未确认：${c.unconfirmed}`)
  md.push('')
  md.push(`- **X**：${X}`)
  md.push(`- **Y**：${Y}`)
  md.push(`- **Z**：${Z}`)
  md.push('')
  for (const v of ['X', 'Y', 'Z']) {
    md.push(`- ${v}：像本人 __ / 贴合 __ / 有内容 __ / 不公式化 __；愿意直接发：是 / 否；事实/立场问题：无 / 有（说明：__）`)
  }
  md.push('')
})
md.push('---')
md.push('')
md.push(`共 ${cases.length} 个视频、${cases.length * 3} 条候选；本轮 SKIP 0（只选了上下文可核验的视频）。`)
fs.writeFileSync(path.join(ROOT, 'blind_review_task05.md'), md.join('\n'), 'utf8')
fs.writeFileSync(path.join(DATA, 'task05_blind_key.csv'),
  '\uFEFFvideo_id,X,Y,Z\r\n' + keyRows.map((r) => `${r.bvid},${r.X},${r.Y},${r.Z}`).join('\r\n') + '\r\n', 'utf8')

// 4) 统计
const bySource = {}, byStatus = {}
for (const f of audit) {
  bySource[f.source_type] = (bySource[f.source_type] ?? 0) + 1
  byStatus[f.status] = (byStatus[f.status] ?? 0) + 1
}
const issueCount = { A: 0, B: 0, C: 0 }
const issueList = []
for (const c of cases) {
  for (const k of ['A', 'B', 'C']) {
    const arr = c.issues[k] ?? []
    issueCount[k] += arr.length
    for (const x of arr) issueList.push({ video: c.bvid, group: k, issue: x })
  }
}
const stats = {
  videos: cases.length,
  candidates: cases.length * 3,
  skip: 0,
  context_quality: cases.reduce((m, c) => (m[c.context_quality] = (m[c.context_quality] ?? 0) + 1, m), {}),
  topics: cases.reduce((m, c) => (m[c.topic] = (m[c.topic] ?? 0) + 1, m), {}),
  facts: audit.length,
  facts_by_source: bySource,
  facts_by_status: byStatus,
  self_audit_issues: issueCount,
  self_audit_list: issueList,
}
fs.writeFileSync(path.join(DATA, 'task05_stats.json'), JSON.stringify(stats, null, 2) + '\n', 'utf8')

console.log(JSON.stringify(stats, null, 2))
