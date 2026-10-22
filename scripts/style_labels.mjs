// Task 03：对账字段 + 视频内容语境统计 + 逐行轻量标签
import fs from 'node:fs'
import path from 'node:path'

const ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1')), '..')
const DATA = path.join(ROOT, 'data')
const CSV = path.join(DATA, 'comments.csv')
const MANIFEST = path.join(DATA, 'manifest.json')
const REPORT = path.join(ROOT, 'quality_report.md')
const LABELS = path.join(DATA, 'style_labels.csv')
const PREVIEW = path.join(ROOT, 'preview_30_labels.md')

// ── 极简 RFC4180 CSV 解析（comments.csv 含引号内换行）──
function parseCSV(text) {
  text = text.replace(/^\uFEFF/, '')
  const rows = []
  let row = [], field = '', inQ = false
  for (let i = 0; i < text.length; i += 1) {
    const c = text[i]
    if (inQ) {
      if (c === '"') {
        if (text[i + 1] === '"') { field += '"'; i += 1 } else inQ = false
      } else field += c
    } else if (c === '"') inQ = true
    else if (c === ',') { row.push(field); field = '' }
    else if (c === '\n') { row.push(field); rows.push(row); row = []; field = '' }
    else if (c === '\r') { /* skip */ }
    else field += c
  }
  if (field.length || row.length) { row.push(field); rows.push(row) }
  return rows
}

const table = parseCSV(fs.readFileSync(CSV, 'utf8'))
const header = table[0]
const rows = table.slice(1).filter((r) => r.length === header.length).map((r) => Object.fromEntries(header.map((h, i) => [h, r[i]])))
const canonical = rows.filter((r) => r.canonical_for_style === 'true')
console.log(`CSV rows=${rows.length}, canonical=${canonical.length}`)

// ── 标签规则 ─────────────────────────────────────────────────────────
const TOPIC_RULES = [
  ['AI/科技', /AI|ai|deepseek|大模型|模型|智械|编程|代码|机器人|openai|gpt|算法|显卡|电脑|手机|大肥鱼/],
  ['游戏', /游戏|LOL|lol|世界赛|原神|明日方舟|我的世界|月圆之夜|王者|吃鸡|CS|DOTA|崩坏|星穹|绝区零|三角洲|暗区|塔科夫|FPS|moba|Steam|主机/],
  ['恐怖/悬疑', /恐怖|诡异|暗网|宿命|布迪秀|惊悚|怪谈|都市传说|灵异|悬疑|鬼/],
  ['音乐', /歌|翻唱|音乐|樱花|术力口|洛天依|VOCALOID|钢琴|BGM|旋律|唱|听歌/],
  ['社会/时事', /新闻|事件|社会|警方|通报|热搜|时事|政策|法院|事故|疫情|地震|火灾|判决/],
  ['作品/虚拟主播', /VTuber|虚拟主播|Vup|V圈|番剧|动漫|动画|漫画|偶像|管人|hololive|彩虹社|二创|同人|cos/i],
  ['动物/宠物', /猫|喵|哈基米|狗|动物|薮猫|狮子|猴|宠物|兽|小鸟|仓鼠|兔|熊猫|鱼/],
  ['生活/搞笑', /外卖|店员|搞笑|沙雕|日常|生活|美食|做饭|工作|上班|学校|考试|睡觉|吃饭|肚子|肠胃|同事|老员工|回家/],
]
const RE = {
  Q: /[?？]|吗|为什么|怎么|是不是|会不会|能不能|有没有|多少|哪里|哪个|啥|如何/,
  MEME: /梗|乐|绷不住|草|笑死|典|急|孝|赢|麻了|绝了|牛逼|逆天|离谱|狗头|doge|滑稽|蚌埠|泰裤辣|yyds|xswl|awsl|哈基米|666/,
  EXPLAIN: /因为|所以|但是|如果|说明|原因|意思是|比如|首先|其次|其实|本质上|也就是说|毕竟|导致|从而|一般|通常|理论上/,
  OPINION: /我觉得|感觉|应该|不如|最好|别(?![人处])|不要|就是|根本|显然|肯定|说实话|老实说|讲真|认为|觉得|确实|还是/,
  EMOTION: /唉|哎|累|难受|开心|难过|喜欢|讨厌|希望|可惜|遗憾|心疼|感动|害怕|吓|烦|气|哭|笑|幸福|孤独|emo/,
  NARRATIVE: /我|今天|昨天|刚才|早上|中午|晚上|下班|上班|吃了|去了|睡了|起来|回家|家里|同事|老员工|小时候|儿子/,
  REACT: /好看|好听|神了|好家伙|牛|强|可爱|笑|哈|哇|卧槽|我去|厉害|喜欢|赞|可以|不错|太.{0,3}了|！|!/,
}

const cleanText = (r) => String(r.text_body || r.text || '').replace(/@[^\s@]+/g, '').replace(/\[[^\]]*\]/g, '').replace(/\s+/g, ' ').trim()

function topicOf(r) {  const s = `${r.video_title} ${r.quoted_text} ${cleanText(r)}`
  for (const [name, re] of TOPIC_RULES) if (re.test(s)) return { name, why: `标题/正文命中「${name}」关键词` }
  if (!r.video_title && !r.quoted_text) {
    if (String(r.source_type).startsWith('dynamic_original')) return { name: '纯文字/个人动态', why: '原创文字/图文，无视频引用' }
    return { name: 'unknown', why: '转发但无可读的引用内容' }
  }
  if (r.video_title) return { name: '其他', why: '有视频但无主题关键词' }
  return { name: 'unknown', why: '无可用主题信号' }
}

function intentOf(r) {
  const t = cleanText(r)
  const len = t.length
  if (!len) return { name: 'unknown', why: '空文本' }
  if (RE.Q.test(t)) return { name: '提问/猜想', why: '含疑问词/问号' }
  if (RE.MEME.test(t)) return { name: '梗/调侃', why: '含梗/调侃用语' }
  if (RE.EXPLAIN.test(t) && len >= 30) return { name: '解释/论证', why: '含因果/解释连接词且较长' }
  if (RE.OPINION.test(t)) return { name: '观点判断', why: '含判断/主张用语' }
  if (RE.EMOTION.test(t)) return { name: '情绪/感慨', why: '含情绪词' }
  if (RE.NARRATIVE.test(t) && len >= 15) return { name: '个人叙述', why: '第一人称/时间线叙述' }
  if (RE.REACT.test(t)) return { name: '即时反应', why: '含反应词' }
  if (r.source_type === 'dynamic_forward' && len <= 40) return { name: '引用/转发理由', why: '转发短理由，未展开论证' }
  if (len <= 12) return { name: '即时反应', why: '短句' }
  if (len >= 25) return { name: '观点判断', why: '较长陈述，按判断处理' }
  if (len <= 40) return { name: '即时反应', why: '短句' }
  return { name: 'unknown', why: '无足够信号' }
}

function styleOf(r, intent) {
  const t = cleanText(r)
  const len = t.length
  const ex = RE.EXPLAIN.test(t), op = RE.OPINION.test(t)
  if (len >= 120 && (ex || op)) return { name: '长推理', why: '长文且含推理/判断' }
  if (len >= 30 && (ex || op)) return { name: '分析解释', why: '中等长度且含解释/判断' }
  if (len >= 20 && (RE.EMOTION.test(t) || RE.NARRATIVE.test(t))) return { name: '叙事/抒情', why: '含情绪/叙述' }
  if (len <= 12) return { name: '短反应', why: '≤12 字' }
  if (RE.MEME.test(t) || RE.REACT.test(t) || RE.Q.test(t)) return { name: '口语吐槽', why: '口语/吐槽标记' }
  if (len <= 40) return { name: '口语吐槽', why: '短口语' }
  return { name: 'unknown', why: '无足够信号' }
}

function contextOf(r) {
  const hasSnippet = String(r.context_snippet || '').trim() !== ''
  const hasTitle = String(r.video_title || '').trim() !== ''
  const desc = String(r.video_desc || '').trim()
  const hasDesc = desc !== '' && desc !== '-' && desc !== '简介'
  const hasQuoted = String(r.quoted_text || '').trim() !== ''
  if (hasSnippet) return { level: 'high', why: '有字幕/正文片段' }
  if (hasTitle && hasDesc) return { level: 'high', why: '有标题+非占位简介' }
  if (hasTitle) return { level: 'medium', why: '仅有标题/卡片' }
  if (hasQuoted) return { level: 'medium', why: '仅有引用内容' }
  return { level: 'low', why: '无视频/引用语境' }
}

const labeled = canonical.map((r) => {
  const topic = topicOf(r)
  const intent = intentOf(r)
  const style = styleOf(r, intent.name)
  const ctx = contextOf(r)
  const reason = `${topic.why}；${intent.why}；${style.why}；${ctx.why}`
  return { ...r, topic_label: topic.name, expression_intent: intent.name, style_mode: style.name, context_confidence: ctx.level, label_reason: reason }
})

// ── style_labels.csv ────────────────────────────────────────────────
const labelCols = ['id', 'text', 'text_body', 'source_type', 'url', 'video_title', 'topic_label', 'expression_intent', 'style_mode', 'context_confidence', 'label_reason']
const q = (v) => `"${String(v ?? '').replace(/"/g, '""')}"`
fs.writeFileSync(LABELS, '\uFEFF' + [labelCols.join(','), ...labeled.map((r) => labelCols.map((c) => q(r[c])).join(','))].join('\r\n') + '\r\n', 'utf8')

// ── 30 条多样化预览 ─────────────────────────────────────────────────
const prio = { comment_l2: 0, comment_l1: 1, dynamic_original_text: 2, dynamic_original_draw: 3, dynamic_forward: 4 }
const pool = [...labeled].sort((a, b) => String(b.time_iso).localeCompare(String(a.time_iso)))
const picked = []
const used = new Set()
const add = (r) => { if (r && !used.has(r.id)) { used.add(r.id); picked.push(r) } }
// 每个主题先取一条
const topics = [...new Set(pool.map((r) => r.topic_label))]
for (const tp of topics) add(pool.find((r) => r.topic_label === tp))
// 每种类型按时间分位取
for (const st of Object.keys(prio).sort((a, b) => prio[a] - prio[b])) {
  const arr = pool.filter((r) => r.source_type === st)
  for (let i = 0; i < Math.min(4, arr.length); i += 1) add(arr[Math.floor((i / Math.max(1, Math.min(4, arr.length) - 1)) * (arr.length - 1))])
}
// 补足偏好意图/风格
for (const r of pool) { if (picked.length >= 30) break; add(r) }
const short = (t, n = 60) => { const s = String(t || '').replace(/\s+/g, ' '); return s.length > n ? s.slice(0, n) + '…' : s }
const md = [
  '# 30 条多样化标签预览（任务 03）',
  '',
  `> 目标 mid=107*** · 从 ${labeled.length} 条 canonical 独立表达中按主题/类型/时间分层抽取 · 标签可复核，不推断人格`,
  '',
  '| # | id | 类型 | 文本（截断） | 主题 | 意图 | 风格 | 语境 | 依据 |',
  '|---|---|---|---|---|---|---|---|---|',
  ...picked.slice(0, 30).map((r, i) => `| ${i + 1} | ${r.id} | ${r.source_type} | ${short(r.text).replace(/\|/g, '\\|')} | ${r.topic_label} | ${r.expression_intent} | ${r.style_mode} | ${r.context_confidence} | ${String(r.label_reason).replace(/\|/g, '\\|')} |`),
].join('\n')
fs.writeFileSync(PREVIEW, md, 'utf8')

// ── 统计 ────────────────────────────────────────────────────────────
const countBy = (arr, f) => arr.reduce((m, r) => (m[f(r)] = (m[f(r)] ?? 0) + 1, m), {})
const labelStats = {
  rows: labeled.length,
  by_topic: countBy(labeled, (r) => r.topic_label),
  by_intent: countBy(labeled, (r) => r.expression_intent),
  by_style: countBy(labeled, (r) => r.style_mode),
  by_context: countBy(labeled, (r) => r.context_confidence),
}

// 语境统计（全量 rows）
const snippetRows = rows.filter((r) => String(r.context_snippet || '').trim() !== '')
const snippetVideos = new Set(snippetRows.map((r) => r.bvid).filter(Boolean))
const titleRows = rows.filter((r) => String(r.video_title || '').trim() !== '')
const descRows = rows.filter((r) => { const d = String(r.video_desc || '').trim(); return d !== '' && d !== '-' && d !== '简介' })
const titleOnlyRows = rows.filter((r) => String(r.video_title || '').trim() !== '' && !descRows.includes(r) && !snippetRows.includes(r))
const noVideoRows = rows.filter((r) => !String(r.video_title || '').trim() && !String(r.quoted_text || '').trim())
const contextStats = {
  records_with_title_or_card: titleRows.length,
  records_with_non_placeholder_desc: descRows.length,
  records_with_context_snippet: snippetRows.length,
  videos_with_context_snippet: snippetVideos.size,
  records_title_only: titleOnlyRows.length,
  records_without_video_or_quote: noVideoRows.length,
  note: '元数据存在率不等于视频内容理解率',
}

// 对账：按 raw 的 source 统计
let manifest = JSON.parse(fs.readFileSync(MANIFEST, 'utf8'))
const rawLines = fs.readFileSync(path.join(DATA, 'raw.jsonl'), 'utf8').split('\n').filter((l) => l.trim()).map((l) => JSON.parse(l))
const rawCmt = rawLines.filter((x) => x._source === 'video_comment_scan')
const rawL2 = rawLines.filter((x) => x._source === 'video_comment_thread')
const currentHits = manifest.sources.video_comment_scan.total_hits // 14
const cumulativeL1 = rawCmt.length // 16
const priorRetained = cumulativeL1 - currentHits // 2
const l2Rows = rawL2.length // 2
manifest.dataset.reconciliation = {
  current_run_hits: currentHits,
  previously_collected_rows_retained: priorRetained,
  cumulative_comment_l1_rows: cumulativeL1,
  comment_l2_rows: l2Rows,
  note: 'current_run_hits 是最后一轮扫描的新命中；previously_collected_rows_retained 是上轮已采集、本轮保留的记录；两者之和 = 累计一级评论。',
}
manifest.dataset.context_completeness = contextStats
manifest.dataset.style_labels = labelStats
// 每视频补累计口径
for (const [bvid, v] of Object.entries(manifest.sources.video_comment_scan.videos)) {
  const cum = rawCmt.filter((x) => x._video?.bvid === bvid).length
  v.hits_current_run = Number(v.hits ?? 0)
  v.hits_cumulative = cum
  v.hits_prior_run = Math.max(0, cum - Number(v.hits ?? 0))
}
fs.writeFileSync(MANIFEST, JSON.stringify(manifest, null, 2) + '\n')

// ── 质量报告追加（幂等）─────────────────────────────────────────────
let report = fs.readFileSync(REPORT, 'utf8')
report = report.replace('- 基础语境（有 context 且视频行有标题）：100%', '- 有标题/卡片元数据：100%（**不等于视频内容理解率**）')
const block = [
  '<!-- TASK03_START -->',
  '',
  '## 8. 对账：本轮新增 vs 累计存档',
  '',
  '| 口径 | 数量 |',
  '|---|---|',
  `| 本轮扫描新命中（current_run_hits） | ${currentHits} |`,
  `| 上轮已采集、本轮保留（previously_collected_rows_retained） | ${priorRetained} |`,
  `| 累计一级评论（cumulative_comment_l1_rows） | ${cumulativeL1} |`,
  `| 二级回复（comment_l2_rows） | ${l2Rows} |`,
  '',
  '> 两条上轮记录：`321438556800`（BV1Rupi6HEqo）、`321420860864`（BV1hnpm6CE16），逐视频 `hits_current_run=0`、`hits_prior_run=1`、`hits_cumulative=1`。',
  '',
  '## 9. 语境完整率（明确口径）',
  '',
  '| 指标 | 数量 |',
  '|---|---|',
  `| 有标题/关联卡片的记录 | ${contextStats.records_with_title_or_card} |`,
  `| 有非占位符视频简介的记录 | ${contextStats.records_with_non_placeholder_desc} |`,
  `| 有字幕/正文片段的记录 | ${contextStats.records_with_context_snippet} |`,
  `| 字幕片段涉及的视频数 | ${contextStats.videos_with_context_snippet} |`,
  `| 仅靠标题/动态卡片的记录 | ${contextStats.records_title_only} |`,
  `| 无视频/引用语境的记录 | ${contextStats.records_without_video_or_quote} |`,
  '',
  '> **元数据存在率 ≠ 视频内容理解率**。本轮只有 2 个视频补了字幕片段，绝大多数记录只有标题/卡片。',
  '',
  '## 10. 逐行标签（style_labels.csv）',
  '',
  `- 已为 ${labeled.length} 条 canonical 独立表达逐行打标；标签文件：\`data/style_labels.csv\``,
  `- 主题分布：${Object.entries(labelStats.by_topic).map(([k, v]) => `${k} ${v}`).join(' · ')}`,
  `- 意图分布：${Object.entries(labelStats.by_intent).map(([k, v]) => `${k} ${v}`).join(' · ')}`,
  `- 风格分布：${Object.entries(labelStats.by_style).map(([k, v]) => `${k} ${v}`).join(' · ')}`,
  `- 语境置信度：${Object.entries(labelStats.by_context).map(([k, v]) => `${k} ${v}`).join(' · ')}`,
  '',
  '> 规则：转发理由与被转发标题/原文分开；`auto_prefix`（回复 @X）不计入口癖；无充分上下文时标 unknown/low。',
  '<!-- TASK03_END -->',
].join('\n')
report = report.replace(/<!-- TASK03_START -->[\s\S]*?<!-- TASK03_END -->\n?/, '')
report = report.trimEnd() + '\n\n' + block + '\n'
fs.writeFileSync(REPORT, report, 'utf8')

console.log(JSON.stringify({ labeled: labeled.length, labelStats, contextStats, reconciliation: manifest.dataset.reconciliation, files: { labels: LABELS, preview: PREVIEW } }, null, 2))
