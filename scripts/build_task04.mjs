// Task 04：生成 test_results.csv / blind_review.md / blind_key.csv
import fs from 'node:fs'
import path from 'node:path'
import crypto from 'node:crypto'

const ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1')), '..')
const DATA = path.join(ROOT, 'data')
const cases = JSON.parse(fs.readFileSync(path.join(DATA, 'test_cases.json'), 'utf8'))
const RESULTS = path.join(ROOT, 'test_results.csv')
const BLIND = path.join(ROOT, 'blind_review.md')
const KEY = path.join(DATA, 'blind_key.csv')
const PROMPTS = path.join(DATA, 'test_prompts.md')

const q = (v) => `"${String(v ?? '').replace(/"/g, '""')}"`
const sha1 = (s) => crypto.createHash('sha1').update(s).digest('hex')

const generated = cases.filter((c) => !c.skip_reason)
const skipped = cases.filter((c) => c.skip_reason)

// test_results.csv
const cols = ['video_id', 'url', 'topic', 'context_quality', 'baseline_comment', 'personalized_comment', 'skip_reason', 'title', 'context_summary', 'known_facts', 'unconfirmed']
const cell = (c, k) => {
  if (k === 'video_id') return c.bvid
  if (k === 'url') return `https://www.bilibili.com/video/${c.bvid}/`
  if (k === 'baseline_comment') return c.baseline
  if (k === 'personalized_comment') return c.personalized
  return c[k]
}
fs.writeFileSync(RESULTS, '\uFEFF' + [cols.join(','), ...cases.map((c) => cols.map((k) => q(cell(c, k))).join(','))].join('\r\n') + '\r\n', 'utf8')

// blind key + blind review
const keyRows = []
const md = [
  '# 盲评：A/B 个人风格对照（任务 04）',
  '',
  '> 每个视频下有两版候选，已随机标成 **X / Y**，顺序逐条打乱。请不要参考 `test_results.csv`，先只看这里。',
  '> 两版可能都不合格；也可以在“偏好”里选“都不行 / 都SKIP”。不要按字数或条数打分。',
  '',
  '## 评分维度（每条 1–5 分）',
  '',
  '- **像用户**：读起来像不像本人会说的话（语气、句式、用词）。',
  '- **贴合视频**：有没有接住这个视频的具体内容，而不是套话。',
  '- **有实际内容**：有没有给出反应/判断/细节，而不是空泛复述。',
  '- **不公式化**：1 = 很模板（“内容很丰富/感谢分享”），5 = 不像模板。',
  '- **事实/立场问题**：有没有编造视频没给的事实，或出现不合适的立场。',
  '',
  '## 逐条',
  '',
]
cases.forEach((c, i) => {
  md.push(`### ${i + 1}. ${c.title}`)
  md.push('')
  md.push(`- 视频：${c.bvid} · ${c.topic} · 语境 ${c.context_quality}`)
  md.push(`- 已知：${c.known_facts}`)
  md.push(`- 未确认：${c.unconfirmed}`)
  md.push('')
  if (c.skip_reason) {
    md.push(`**SKIP**：${c.skip_reason}`)
    md.push('')
    md.push('- 评分：跳过（不生成候选）')
    md.push('')
    return
  }
  const swap = parseInt(sha1(c.bvid).slice(0, 2), 16) % 2 === 1
  const X = swap ? c.personalized : c.baseline
  const Y = swap ? c.baseline : c.personalized
  keyRows.push({ bvid: c.bvid, X: swap ? 'personalized' : 'baseline', Y: swap ? 'baseline' : 'personalized' })
  md.push(`- **X**：${X}`)
  md.push(`- **Y**：${Y}`)
  md.push('')
  md.push('- X：像用户 __ / 贴合 __ / 有内容 __ / 不公式化 __')
  md.push('- Y：像用户 __ / 贴合 __ / 有内容 __ / 不公式化 __')
  md.push('- 事实/立场问题：无 / 有（说明：__）')
  md.push('- 偏好：X / Y / 都不行 / 都SKIP')
  md.push('')
})
md.push('---')
md.push('')
md.push(`共 ${cases.length} 个视频：生成 ${generated.length} 组、SKIP ${skipped.length} 个。`)
fs.writeFileSync(BLIND, md.join('\n'), 'utf8')

fs.writeFileSync(KEY, '\uFEFFvideo_id,X_role,Y_role\r\n' + keyRows.map((r) => `${r.bvid},${r.X},${r.Y}`).join('\r\n') + '\r\n', 'utf8')

// 提示词记录
const promptDoc = [
  '# 任务 04 生成提示词（可复现）',
  '',
  '## 共同设置',
  '',
  '- 模型：deepseek-v4-pro（本会话同一模型；A/B 相同）',
  '- 参数：会话内生成，未暴露 temperature/top_p；A/B 使用相同上下文与相同输出约束',
  '- 上下文：标题 + 简介 + 实际可获得的字幕片段（无字幕则只用标题/简介）',
  '- 约束：只写 B 站评论正文；不编造视频没给的信息；不搬运历史语料里的事实/立场/经历；不发布',
  '',
  '## A 组（基础提示词）',
  '',
  '```',
  '你是一个普通的 B 站用户。看完下面这个视频后，写一条自然的中文评论。',
  '直接输出评论正文，不要解释。',
  '',
  '【标题】{title}',
  '【简介】{desc}',
  '【字幕/正文片段】{subtitle_snippet 或 “（无）”}',
  '```',
  '',
  '## B 组（基础提示词 + 个人风格指南 v1）',
  '',
  '```',
  '你是一个普通的 B 站用户。看完下面这个视频后，写一条自然的中文评论。',
  '直接输出评论正文，不要解释。',
  '',
  '【标题】{title}',
  '【简介】{desc}',
  '【字幕/正文片段】{subtitle_snippet 或 “（无）”}',
  '',
  '请遵循下面的个人评论风格指南：',
  '（data/style_guide_v1.md 全文）',
  '```',
  '',
  '> 说明：为隔离“风格指南”这一个变量，A/B 都使用中性的“普通 B 站用户”基座，没有叠加“YOUR_NAME”人格。人格与风格的组合可以下一轮再测。',
].join('\n')
fs.writeFileSync(PROMPTS, promptDoc, 'utf8')

console.log(JSON.stringify({
  cases: cases.length,
  generated: generated.length,
  skipped: skipped.length,
  context_quality: cases.reduce((m, c) => (m[c.context_quality] = (m[c.context_quality] ?? 0) + 1, m), {}),
  topics: cases.reduce((m, c) => (m[c.topic] = (m[c.topic] ?? 0) + 1, m), {}),
  files: { results: RESULTS, blind: BLIND, key: KEY, prompts: PROMPTS },
}, null, 2))
