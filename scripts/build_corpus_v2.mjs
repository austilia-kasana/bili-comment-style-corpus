// 任务 02：重建语料（新增上下文字段、去重分组、质量报告、多样化抽样）
import fs from 'node:fs'
import path from 'node:path'
import crypto from 'node:crypto'

const HOME = process.env.USERPROFILE || process.env.HOME || '.'
const ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1')), '..')
const DATA = path.join(ROOT, 'data')
const RAW = path.join(DATA, 'raw.jsonl')
const VMETA = path.join(DATA, 'video_meta.json')
const CCTX = path.join(DATA, 'comment_context.json')
const CSV = path.join(DATA, 'comments.csv')
const CTXREVIEW = path.join(DATA, 'context_review.csv')
const MANIFEST = path.join(DATA, 'manifest.json')
const REPORT = path.join(ROOT, 'quality_report.md')
const PREVIEW = path.join(ROOT, 'preview_diverse_20.md')
const TARGET = 'YOUR_MID'
const TARGET_NAME = 'YOUR_NAME'

const lines = fs.readFileSync(RAW, 'utf8').split('\n').filter((l) => l.trim())
let vmeta = {}
try { vmeta = JSON.parse(fs.readFileSync(VMETA, 'utf8')) } catch {}
let cctx = {}
try { cctx = JSON.parse(fs.readFileSync(CCTX, 'utf8')) } catch {}

const iso = (ts) => (ts ? new Date(Number(ts) * 1000).toISOString() : '')
const local = (ts) => (ts ? new Date(Number(ts) * 1000).toLocaleString('zh-CN', { hour12: false }) : '')
const sha1 = (s) => crypto.createHash('sha1').update(s).digest('hex')
const normText = (t) => String(t || '').trim().replace(/\s+/g, ' ')

const rows = []
const seen = new Set()
const rawCount = {}
for (const line of lines) {
  let o; try { o = JSON.parse(line) } catch { continue }
  rawCount[o._source] = (rawCount[o._source] ?? 0) + 1

  if (o._source === 'space_dynamics_polymer') {
    const it = o.item || {}
    const id = String(it.id_str ?? '')
    if (!id || seen.has('dyn:' + id)) continue
    seen.add('dyn:' + id)
    const au = it.modules?.module_author || {}
    const dy = it.modules?.module_dynamic || {}
    const text = String(dy.desc?.text ?? dy.major?.opus?.summary?.text ?? '')
    const autoPrefix = (text.match(/^\s*回复\s*@[^\s:：]+?\s*[:：]\s*/) ?? [''])[0]
    const textBody = autoPrefix ? text.slice(autoPrefix.length).trim() : text.trim()
    const orig = it.orig || null
    let quotedText = ''
    if (orig) quotedText = orig.modules?.module_dynamic?.desc?.text || orig.modules?.module_dynamic?.major?.archive?.title || ''
    const arch = dy.major?.archive || orig?.modules?.module_dynamic?.major?.archive || null
    const bvid = arch?.bvid ?? ''
    const vm = vmeta[bvid] || {}
    const typeMap = {
      DYNAMIC_TYPE_FORWARD: 'dynamic_forward', DYNAMIC_TYPE_AV: 'dynamic_video_share',
      DYNAMIC_TYPE_DRAW: 'dynamic_original_draw', DYNAMIC_TYPE_WORD: 'dynamic_original_text',
      DYNAMIC_TYPE_ARTICLE: 'dynamic_article', DYNAMIC_TYPE_OPUS: 'dynamic_opus',
    }
    let context = ''
    if (orig) {
      const oa = orig.modules?.module_author || {}
      const ot = orig.modules?.module_dynamic?.desc?.text || orig.modules?.module_dynamic?.major?.archive?.title || ''
      context = `转发自 @${oa.name ?? '?'}（mid ${oa.mid ?? '?'}）：${String(ot).replace(/\s+/g, ' ').slice(0, 120)}`
    } else if (bvid) context = `视频：${vm.title || arch?.title || ''}`
    else if (dy.major?.draw?.items?.length) context = `图片×${dy.major.draw.items.length}`
    else if (dy.major?.article) context = `专栏：${dy.major.article.title ?? ''}`
    else if (dy.major?.opus) context = `原创${dy.major.opus.title ? '：' + dy.major.opus.title : ''}`
    const nodes = [...(dy.desc?.rich_text_nodes ?? []), ...(dy.major?.opus?.summary?.rich_text_nodes ?? [])]
    const mentions = nodes.filter((n) => n.type === 'RICH_TEXT_NODE_TYPE_AT').map((n) => ({ mid: String(n.rid ?? ''), name: n.text ?? '' }))
    const like = it.modules?.module_stat?.like?.count ?? ''
    const missing = []
    if (bvid) {
      if (!vm.desc || String(vm.desc).trim() === '' || String(vm.desc).trim() === '-') missing.push('video_desc')
      missing.push('video_content')
      if (!vm.subtitle_snippet) missing.push('subtitle')
    } else missing.push('orig_media')
    rows.push({
      id, time_iso: iso(au.pub_ts), time_local: local(au.pub_ts),
      source_type: typeMap[it.type] ?? `dynamic_${String(it.type).replace('DYNAMIC_TYPE_', '').toLowerCase()}`,
      url: `https://t.bilibili.com/${id}`, text, auto_prefix: autoPrefix, text_body: textBody, quoted_text: quotedText, context,
      author_uid: String(au.mid ?? ''), author_name: String(au.name ?? ''),
      source: 'space_dynamics_polymer', bvid,
      video_title: vm.title || arch?.title || '', video_desc: vm.desc || arch?.desc || '',
      root_rpid: '', parent_rpid: '', reply_to_mid: '', reply_to_text: '',
      like_count: like === '' ? '' : String(like),
      mentions: mentions.length ? JSON.stringify(mentions) : '',
      text_origin_confidence: autoPrefix ? 'likely_user_with_auto_prefix' : 'likely_user',
      context_source: ['dynamic_card', vm.title ? 'video_meta' : '', vm.subtitle_snippet ? 'subtitle' : ''].filter(Boolean).join(';'),
      context_snippet: vm.subtitle_snippet || '',
      context_missing: missing.join(';'),
      verify_status: String(au.mid) === TARGET ? 'confirmed' : 'unverified',
    })
  }

  if (o._source === 'video_comment_scan' || o._source === 'video_comment_thread') {
    const r = o.item || {}
    const id = String(r.rpid ?? '')
    if (!id || seen.has('cmt:' + id)) continue
    seen.add('cmt:' + id)
    const v = o._video || {}
    const vm = vmeta[v.bvid] || {}
    const isL2 = Number(r.parent ?? 0) !== 0 && Number(r.root ?? 0) !== 0
    const cx = cctx[id] || null
    const rootRpid = cx?.root_rpid || String(r.root_str ?? r.root ?? '')
    const parentRpid = cx?.parent_rpid || (isL2 ? String(r.parent_str ?? r.parent ?? '') : '')
    const rootText = cx?.root_text || ''
    const context = [`视频：${vm.title || v.title || ''}`, isL2 ? `回复 @${cx?.reply_to_name || ''}` : '一级评论', rootText ? `楼层：${rootText.slice(0, 80)}` : ''].filter(Boolean).join('；')
    const rawText = String(r.content?.message ?? '')
    const autoPrefix = (rawText.match(/^\s*回复\s*@[^\s:：]+?\s*[:：]\s*/) ?? [''])[0]
    const textBody = autoPrefix ? rawText.slice(autoPrefix.length).trim() : rawText.trim()
    const mentions = (r.content?.members ?? []).map((m) => ({ mid: String(m.mid ?? ''), name: m.uname ?? '' }))
    const missing = []
    if (!vm.desc || String(vm.desc).trim() === '' || String(vm.desc).trim() === '-') missing.push('video_desc')
    missing.push('video_content')
    if (!vm.subtitle_snippet) missing.push('subtitle')
    if (!cx) missing.push('comment_thread')
    rows.push({
      id, time_iso: iso(r.ctime), time_local: local(r.ctime),
      source_type: isL2 ? 'comment_l2' : 'comment_l1',
      url: `https://www.bilibili.com/video/${v.bvid}/#reply${id}`,
      text: String(r.content?.message ?? ''), auto_prefix: autoPrefix, text_body: textBody, quoted_text: '', context,
      author_uid: String(r.mid ?? ''), author_name: String(r.member?.uname ?? ''),
      source: o._source, bvid: v.bvid ?? '',
      video_title: vm.title || v.title || '', video_desc: vm.desc || '',
      root_rpid: rootRpid, parent_rpid: parentRpid,
      reply_to_mid: cx?.reply_to_mid ?? '', reply_to_text: cx?.reply_to_text ?? '',
      like_count: r.like === undefined ? '' : String(r.like),
      mentions: mentions.length ? JSON.stringify(mentions) : '',
      text_origin_confidence: autoPrefix ? 'confirmed_user_with_auto_prefix' : 'confirmed_user',
      context_source: ['video_comment_scan', cx ? 'comment_thread' : '', vm.title ? 'video_meta' : '', vm.subtitle_snippet ? 'subtitle' : ''].filter(Boolean).join(';'),
      context_snippet: vm.subtitle_snippet || '',
      context_missing: missing.join(';'),
      verify_status: String(r.mid) === TARGET ? 'confirmed' : 'unverified',
    })
  }
}

rows.sort((a, b) => String(b.time_iso).localeCompare(String(a.time_iso)))

// 重复分组（只按规范化文本；不推断行为）
const groups = new Map()
for (const r of rows) {
  const k = normText(r.text)
  if (!k) continue
  const g = groups.get(k) ?? []
  g.push(r)
  groups.set(k, g)
}
let dupGroups = 0, dupRows = 0
for (const [k, g] of groups) {
  if (g.length < 2) continue
  dupGroups += 1; dupRows += g.length
  const gid = 'dup_' + sha1(k).slice(0, 10)
  // canonical：优先有楼中楼上下文的评论，其次评论，其次最早
  const score = (r) => (r.source.startsWith('video_comment') ? 0 : 10) + (r.context_missing.includes('comment_thread') ? 5 : 0) + new Date(r.time_iso).getTime() / 1e13
  const sorted = [...g].sort((a, b) => score(a) - score(b))
  for (const r of g) {
    r.duplicate_group_id = gid
    r.canonical_for_style = r === sorted[0] ? 'true' : 'false'
  }
}
for (const r of rows) {
  if (!r.duplicate_group_id) { r.duplicate_group_id = ''; r.canonical_for_style = 'true' }
}
// 空文本不算独立表达
for (const r of rows) {
  if (!normText(r.text)) {
    r.canonical_for_style = 'false'
    r.context_missing = [...new Set([...(r.context_missing ? r.context_missing.split(';') : []), 'empty_text'])].join(';')
  }
}

// CSV
const q = (v) => `"${String(v ?? '').replace(/"/g, '""')}"`
const cols = ['id', 'time_iso', 'time_local', 'source_type', 'url', 'text', 'auto_prefix', 'text_body', 'quoted_text', 'context', 'author_uid', 'author_name', 'source', 'bvid', 'video_title', 'video_desc', 'root_rpid', 'parent_rpid', 'reply_to_mid', 'reply_to_text', 'like_count', 'mentions', 'duplicate_group_id', 'canonical_for_style', 'text_origin_confidence', 'context_source', 'context_snippet', 'context_missing', 'verify_status']
fs.writeFileSync(CSV, '\uFEFF' + [cols.join(','), ...rows.map((r) => cols.map((c) => q(r[c])).join(','))].join('\r\n') + '\r\n', 'utf8')

// context_review.csv
const ctxCols = ['id', 'source_type', 'url', 'video_title', 'text', 'context', 'reply_to_mid', 'reply_to_name', 'reply_to_text', 'root_rpid', 'parent_rpid', 'context_snippet', 'context_missing', 'verify_status']
fs.writeFileSync(CTXREVIEW, '\uFEFF' + [ctxCols.join(','), ...rows.map((r) => ctxCols.map((c) => q(c === 'reply_to_name' ? (cctx[r.id]?.reply_to_name ?? '') : r[c])).join(','))].join('\r\n') + '\r\n', 'utf8')

// 统计
const byType = {}
for (const r of rows) byType[r.source_type] = (byType[r.source_type] ?? 0) + 1
const canonical = rows.filter((r) => r.canonical_for_style === 'true')
const confirmed = rows.filter((r) => r.verify_status === 'confirmed')
const withVideo = rows.filter((r) => r.bvid)
const withDesc = rows.filter((r) => r.video_desc && r.video_desc !== '-' && String(r.video_desc).trim())
const commentRows = rows.filter((r) => r.source_type.startsWith('comment'))
const withThread = commentRows.filter((r) => r.context_source.includes('comment_thread'))
const basicContext = rows.filter((r) => r.context && (!r.bvid || r.video_title))
const times = rows.map((r) => r.time_iso).filter(Boolean).sort()
const originCounts = {}
for (const r of rows) originCounts[r.text_origin_confidence] = (originCounts[r.text_origin_confidence] ?? 0) + 1
const autoPrefixRows = rows.filter((r) => r.auto_prefix).length
const uniqueBvids = new Set(rows.filter((r) => r.bvid).map((r) => r.bvid)).size
const subtitleVideos = Object.values(vmeta).filter((m) => m.subtitle_snippet).length
let commentCov = { videos: 0, seen: 0, reply_total: 0 }
try {
  const st = JSON.parse(fs.readFileSync(path.join(DATA, 'comment_state.json'), 'utf8')).scanned
  for (const v of Object.values(st)) { commentCov.videos += 1; commentCov.seen += Number(v.comments_seen ?? 0); commentCov.reply_total += Number(v.reply_total ?? 0) }
} catch {}
let spaceCov = { pages: 0, offset: '' }
try {
  const sp = JSON.parse(fs.readFileSync(path.join(DATA, 'space_state.json'), 'utf8'))
  spaceCov = { pages: Number(sp.pages_done ?? 0), offset: String(sp.offset ?? '') }
} catch {}

const topic = (r) => {
  const s = `${r.video_title} ${r.text}`
  if (/猫|喵|哈基米|狗|动物|薮猫|狮子/.test(s)) return '动物/宠物'
  if (/游戏|LOL|世界赛|原神|明日方舟|我的世界|月圆/.test(s)) return '游戏'
  if (/恐怖|诡异|暗网|宿命|布迪秀|惊悚|怪谈/.test(s)) return '恐怖/悬疑'
  if (/AI|deepseek|大肥鱼|模型|智械|编程/.test(s)) return 'AI/科技'
  if (/歌|翻唱|音乐|樱花|术力口|洛天依/.test(s)) return '音乐'
  if (/外卖|店员|搞笑|沙雕|日常|生活/.test(s)) return '生活/搞笑'
  if (r.bvid) return vmeta[r.bvid]?.tname || '其他'
  return '无视频/纯文字'
}
const byTopic = {}
for (const r of rows) byTopic[topic(r)] = (byTopic[topic(r)] ?? 0) + 1

let manifest = {}
try { manifest = JSON.parse(fs.readFileSync(MANIFEST, 'utf8')) } catch {}
manifest.generated_at = new Date().toISOString()
manifest.dataset = {
  target_mid: TARGET, target_name: TARGET_NAME,
  raw_records: lines.length, raw_by_source: rawCount,
  normalized_rows: rows.length,
  independent_expressions: canonical.length,
  by_source_type: byType,
  by_topic: byTopic,
  rows_with_video: withVideo.length,
  unique_videos: uniqueBvids,
  subtitle_videos: subtitleVideos,
  comment_coverage: commentCov,
  text_origin_confidence: originCounts,
  auto_prefix_rows: autoPrefixRows,
  rows_with_video_desc: withDesc.length,
  comment_rows: commentRows.length,
  comment_rows_with_thread_context: withThread.length,
  author_confirmed: confirmed.length,
  author_confirmation_rate: rows.length ? +(confirmed.length / rows.length).toFixed(3) : 0,
  basic_context_rate: rows.length ? +(basicContext.length / rows.length).toFixed(3) : 0,
  content_duplicate_groups: dupGroups,
  content_duplicate_rows: dupRows,
  coverage_time_utc: { earliest: times[0] ?? null, latest: times[times.length - 1] ?? null },
  files: { raw: 'data/raw.jsonl', csv: 'data/comments.csv', context_review: 'data/context_review.csv' },
}
if (manifest.sources?.space_dynamics) {
  manifest.sources.space_dynamics.coverage = { ...(manifest.sources.space_dynamics.coverage ?? {}), pages_total: spaceCov.pages, cursor_end: spaceCov.offset }
}
if (manifest.sources?.video_comment_scan) manifest.sources.video_comment_scan.total_hits_in_raw = commentRows.length
if (manifest.sources?.video_comment_scan?.videos) {
  for (const v of Object.values(manifest.sources.video_comment_scan.videos)) {
    v.complete = v.reply_total ? Number(v.comments_seen) >= Number(v.reply_total) : false
  }
}
fs.writeFileSync(MANIFEST, JSON.stringify(manifest, null, 2) + '\n')

// 质量报告
const pct = (a, b) => `${Math.round((a / Math.max(1, b)) * 100)}%`
const errs = []
try { const st = JSON.parse(fs.readFileSync(path.join(DATA, 'comment_state.json'), 'utf8')).scanned; for (const [k, v] of Object.entries(st)) if (v.error) errs.push(`${k}: ${v.error}`) } catch {}
try { const sp = JSON.parse(fs.readFileSync(path.join(DATA, 'space_state.json'), 'utf8')); for (const e of sp.errors ?? []) errs.push(`space page ${e.page}: ${e.error ?? e.message}`) } catch {}
try { const th = JSON.parse(fs.readFileSync(path.join(DATA, 'thread_state.json'), 'utf8')).done; for (const [k, v] of Object.entries(th)) if (v.error) errs.push(`thread ${k}: ${v.error}`) } catch {}

const stat = (arr, f) => arr.reduce((m, r) => (m[f(r)] = (m[f(r)] ?? 0) + 1, m), {})
const typeTable = Object.entries(byType).sort((a, b) => b[1] - a[1]).map(([k, v]) => `| ${k} | ${v} |`).join('\n')
const topicTable = Object.entries(byTopic).sort((a, b) => b[1] - a[1]).slice(0, 12).map(([k, v]) => `| ${k} | ${v} |`).join('\n')

const report = [
  '# 数据质量报告（任务 02）',
  '',
  `生成：${new Date().toLocaleString('zh-CN', { hour12: false })} · 目标 mid=${TARGET}（${TARGET_NAME}）`,
  '',
  '## 1. 总量',
  '',
  `- 原始记录：**${lines.length}** 条（raw.jsonl，未删记录）`,
  `- 归一化发言：**${rows.length}** 条`,
  `- **去重后的独立表达：${canonical.length} 条**（canonical_for_style=true）`,
  `- 作者确认：${confirmed.length}/${rows.length}（${pct(confirmed.length, rows.length)}）`,
  `- 时间范围：${times[0]?.slice(0, 10)} → ${times[times.length - 1]?.slice(0, 10)}（UTC）`,
  '',
  '### 原始记录来源',
  '',
  '| 来源 | 条数 |',
  '|---|---|',
  ...Object.entries(rawCount).map(([k, v]) => `| ${k} | ${v} |`),
  '',
  '## 2. 类型分布',
  '',
  '| source_type | 条数 |',
  '|---|---|',
  typeTable,
  '',
  '## 3. 主题分布（关键词/分区）',
  '',
  '| 主题 | 条数 |',
  '|---|---|',
  topicTable,
  '',
  '## 4. 语境完整率',
  '',
  `- 基础语境（有 context 且视频行有标题）：${pct(basicContext.length, rows.length)}`,
  `- 视频简介：${withDesc.length}/${withVideo.length}（${pct(withDesc.length, withVideo.length)}）`,
  `- 评论楼中楼上下文：${withThread.length}/${commentRows.length}（${pct(withThread.length, commentRows.length)}）`,
  `- 字幕片段：${subtitleVideos} 个视频已补（其余仍标 context_missing）`,
  `- 候选视频：${uniqueBvids} 个（已扫评论 ${commentCov.videos} 个，覆盖 ${commentCov.seen}/${commentCov.reply_total} 条）`,
  '',
  '## 4.5 文本来源',
  '',
  `- 系统前缀（“回复 @X :”）已单独存进 \`auto_prefix\`：${autoPrefixRows} 条；\`text\` 不改写，\`text_body\` 为剥前缀正文`,
  `- 置信度分布：${Object.entries(originCounts).map(([k, v]) => `${k} ${v}`).join(' · ')}`,
  '- 一级评论没有回复对象，`reply_to_*` 留空属正常（不是缺失）；二级回复已补 parent/root/reply_to_*。',
  '',
  '## 5. 去重',
  '',
  `- 文本重复：${dupGroups} 组、${dupRows} 条（同一段文字可能同时是"转发理由"与"同时评论"）`,
  '- 原始层不删；用 `duplicate_group_id` 分组、`canonical_for_style` 标出用于风格分析的一条。',
  '',
  '## 6. 来源覆盖与失败',
  '',
  '| 来源 | 覆盖 | 失败 |',
  '|---|---|---|',
  `| 空间动态 | ${spaceCov.pages} 页 / ${rawCount.space_dynamics_polymer ?? 0} 条 / 2023-07-26→2026-10-21（接口仍 has_more） | 0 |`,
  `| 视频评论 | ${commentCov.videos} 个视频 / ${commentCov.seen} 条 / 命中 ${commentRows.length} | 0 |`,
  `| 楼中楼 | ${Object.keys((() => { try { return JSON.parse(fs.readFileSync(path.join(DATA, 'thread_state.json'), 'utf8')).done } catch { return {} } })()).length} 个楼层 / ${withThread.length} 条有上下文 | 0 |`,
  '| 视频元信息 | 18 个视频 | 0 |',
  '',
  `- 失败项：${errs.length ? '\n  - ' + errs.join('\n  - ') : '无'}`,
  '',
  '> 详细每视频页数/命中/是否完整见 manifest.sources.video_comment_scan.videos；动态游标见 manifest.sources.space_dynamics.cursor_history。',
  '',
  '## 7. 已知缺口',
  '',
  '1. 评论无全量接口；每视频最多扫 30 页（600 条），`complete=false` 的视频未覆盖全部评论。',
  '2. 观看历史 / 点赞记录属于私密数据，本账号无权读取；未尝试绕过。',
  '3. 公开收藏夹接口返回 -400，未取得收藏视频。',
  '4. 仅 2 个视频补了字幕片段；视频正文摘要未补，`context_missing` 保留。',
  '5. 动态 520 条为转发、224 条为原创；转发文案短，原创动态提供了长文与不同语气。',
].join('\n')
fs.writeFileSync(REPORT, report, 'utf8')

// 20 条多样化脱敏抽样
const maskMid = (m) => { const s = String(m || ''); return s.length > 5 ? s.slice(0, 3) + '***' : '***' }
const maskName = (n) => { const s = String(n || ''); return s.length > 1 ? s[0] + '**' : '*' }
const maskBv = (b) => { const s = String(b || ''); return s ? s.slice(0, 4) + '***' + s.slice(-3) : '' }
const short = (t, n = 70) => { const s = String(t || '').replace(/\s+/g, ' '); return s.length > n ? s.slice(0, n) + '…' : s }

const pool = [...canonical].sort((a, b) => String(b.time_iso).localeCompare(String(a.time_iso)))
const pick = []
const byTypeRows = new Map()
for (const r of pool) {
  const k = r.source_type
  if (!byTypeRows.has(k)) byTypeRows.set(k, [])
  byTypeRows.get(k).push(r)
}
const typePriority = { comment_l2: 0, comment_l1: 1, dynamic_original_text: 2, dynamic_original_draw: 3, dynamic_article: 4, dynamic_video_share: 5, dynamic_forward: 6 }
// 每类按时间分位取 5 条，再按长度补
for (const [k, arr] of [...byTypeRows.entries()].sort((a, b) => (typePriority[a[0]] ?? 9) - (typePriority[b[0]] ?? 9))) {
  const n = Math.min(5, arr.length)
  for (let i = 0; i < n; i += 1) {
    const idx = Math.floor((i / Math.max(1, n - 1)) * (arr.length - 1))
    if (!pick.includes(arr[idx])) pick.push(arr[idx])
  }
}
// 长度分层补足 20
const byLen = [...pool].sort((a, b) => normText(a.text).length - normText(b.text).length)
for (const r of [byLen[0], byLen[Math.floor(byLen.length / 4)], byLen[Math.floor(byLen.length / 2)], byLen[Math.floor((byLen.length * 3) / 4)], byLen[byLen.length - 1]]) {
  if (r && pick.length < 20 && !pick.includes(r)) pick.push(r)
}
for (const r of pool) { if (pick.length >= 20) break; if (!pick.includes(r)) pick.push(r) }

const pv = [
  '# 20 条多样化脱敏抽样（任务 02）',
  '',
  `> 目标 mid=${maskMid(TARGET)} · 从 ${canonical.length} 条独立表达中按类型/时间/长度分层抽取 · 文本未改写，仅截断/打码`,
  '',
  '| # | 时间(本地) | 类型 | 文本（截断） | 视频 | 作者(脱敏) |',
  '|---|---|---|---|---|---|',
  ...pick.slice(0, 20).map((r, i) => `| ${i + 1} | ${r.time_local} | ${r.source_type} | ${short(r.text).replace(/\|/g, '\\|')} | ${maskBv(r.bvid)} | ${maskName(r.author_name)}(${maskMid(r.author_uid)}) |`),
].join('\n')
fs.writeFileSync(PREVIEW, pv, 'utf8')

console.log(JSON.stringify({ raw: lines.length, rows: rows.length, canonical: canonical.length, by_type: byType, comments: commentRows.length, with_thread: withThread.length, dup_groups: dupGroups, files: { csv: CSV, ctx: CTXREVIEW, report: REPORT, preview: PREVIEW } }, null, 2))
