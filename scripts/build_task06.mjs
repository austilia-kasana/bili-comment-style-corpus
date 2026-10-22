// Task 06：独立生成结果 → 审计表 / 结果 / 生成顺序 / 盲评 / key / 统计
import fs from 'node:fs'
import path from 'node:path'
import crypto from 'node:crypto'

const ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1')), '..')
const DATA = path.join(ROOT, 'data')
const videos = JSON.parse(fs.readFileSync(path.join(DATA, 'task06_videos.json'), 'utf8'))
const raw = JSON.parse(fs.readFileSync(path.join(DATA, 'task06_generation_raw.json'), 'utf8'))
const byId = new Map(raw.map((r) => [r.bvid, r.version === 'v1' ? r : r]))
const sha1 = (s) => crypto.createHash('sha1').update(s).digest('hex')
const q = (v) => `"${String(v ?? '').replace(/"/g, '""')}"`

// 审计表
const auditCols = ['video_id', 'title', 'topic', 'context_quality', 'insufficient', 'fact_id', 'fact_text', 'source', 'reviewed_by_user', 'status', 'note']
const audit = []
for (const v of videos) {
  v.facts.forEach((f, i) => {
    const status = f.source === 'subtitle' ? 'confirmed'
      : f.source === 'user_report' ? 'user_report'
      : f.source === 'description' ? 'description_only'
      : f.source === 'title' ? 'title_only'
      : 'unknown'
    audit.push({
      video_id: v.bvid, title: v.title, topic: v.topic, context_quality: v.context_quality,
      insufficient: v.insufficient, fact_id: `f${i + 1}`, fact_text: f.text, source: f.source,
      reviewed_by_user: f.reviewed_by_user ? 'true' : 'false', status,
      note: v.insufficient ? '信息不足：生成应优先 SKIP；若生成，审查事实/推断/虚构经历' : '',
    })
  })
  audit.push({
    video_id: v.bvid, title: v.title, topic: v.topic, context_quality: v.context_quality,
    insufficient: v.insufficient, fact_id: 'unknown', fact_text: v.unknown, source: 'unknown',
    reviewed_by_user: 'false', status: v.insufficient ? 'unknown' : 'unknown_note',
    note: v.insufficient ? '核心内容未确认，不得靠常识补' : '已知边界',
  })
}
fs.writeFileSync(path.join(DATA, 'task06_context_audit.csv'),
  '\uFEFF' + [auditCols.join(','), ...audit.map((r) => auditCols.map((k) => q(r[k])).join(','))].join('\r\n') + '\r\n', 'utf8')

// 结果 CSV
const resCols = ['video_id', 'url', 'topic', 'context_quality', 'insufficient', 'version', 'comment', 'skipped', 'generation_order']
const rows = raw.map((r) => {
  const v = videos.find((x) => x.bvid === r.bvid)
  return {
    video_id: r.bvid, url: `https://www.bilibili.com/video/${r.bvid}/`, topic: v.topic,
    context_quality: v.context_quality, insufficient: v.insufficient, version: r.version,
    comment: r.comment, skipped: r.skipped ? 'true' : 'false', generation_order: r.order,
  }
})
fs.writeFileSync(path.join(DATA, 'task06_results.csv'),
  '\uFEFF' + [resCols.join(','), ...rows.map((r) => resCols.map((k) => q(r[k])).join(','))].join('\r\n') + '\r\n', 'utf8')

// 生成顺序
const orderCols = ['order', 'task_id', 'video_id', 'version', 'insufficient']
fs.writeFileSync(path.join(DATA, 'task06_generation_order.csv'),
  '\uFEFF' + [orderCols.join(','), ...raw.map((r) => orderCols.map((k) => q(k === 'task_id' ? r.id : k === 'video_id' ? r.bvid : k === 'version' ? r.version : k === 'insufficient' ? String(r.insufficient) : r[k])).join(','))].join('\r\n') + '\r\n', 'utf8')

// 盲评 + key
const keyRows = []
const md = [
  '# 盲评：v1 vs v2-lite（任务 06）',
  '',
  '> 8 个视频，每个两条候选，已随机标成 **X / Y**。先只看这里，不要参考 `data/task06_results.csv` 或 key。',
  '> 6 个正常视频按 4 项 1–5 分 + 愿意直接发 + 事实问题评；2 个信息不足视频只判“SKIP 是否正确”，不计入正常均分。',
  '',
  '## 正常视频：评分维度',
  '',
  '- 像本人 / 贴合视频 / 有实际内容 / 不公式化（1–5）',
  '- 愿意直接发：是 / 否',
  '- 事实/立场问题：无 / 有（写明原因；单独统计）',
  '',
  '## 信息不足视频：只判 SKIP',
  '',
  '- X 是否正确 SKIP：是 / 否',
  '- Y 是否正确 SKIP：是 / 否',
  '- 若生成了评论：事实错误 / 未支持推断 / 虚构经历（无 / 有 + 说明）',
  '',
  '## 逐条',
  '',
]
videos.forEach((v, i) => {
  const swap = parseInt(sha1(v.bvid).slice(0, 2), 16) % 2 === 1
  const v1 = raw.find((r) => r.bvid === v.bvid && r.version === 'v1')
  const v2 = raw.find((r) => r.bvid === v.bvid && r.version === 'v2lite')
  const X = swap ? v2 : v1
  const Y = swap ? v1 : v2
  keyRows.push({ bvid: v.bvid, X: swap ? 'v2lite' : 'v1', Y: swap ? 'v1' : 'v2lite' })
  md.push(`### ${i + 1}. ${v.title}`)
  md.push('')
  md.push(`- 视频：${v.bvid} · ${v.topic} · 语境 ${v.context_quality}${v.insufficient ? ' · **信息不足**' : ''}`)
  md.push('- 已核验事实：')
  for (const f of v.facts) md.push(`  - [${f.source}${f.reviewed_by_user ? ', reviewed_by_user=true' : ''}] ${f.text}`)
  md.push(`- 未确认：${v.unknown}`)
  md.push('')
  md.push(`- **X**：${X.comment || '（空）'}`)
  md.push(`- **Y**：${Y.comment || '（空）'}`)
  md.push('')
  if (v.insufficient) {
    md.push('- X 是否正确 SKIP：是 / 否')
    md.push('- Y 是否正确 SKIP：是 / 否')
    md.push('- 若生成评论：事实错误 / 未支持推断 / 虚构经历：无 / 有（说明：__）')
  } else {
    md.push('- X：像本人 __ / 贴合 __ / 有内容 __ / 不公式化 __；愿意直接发：是 / 否；事实/立场问题：无 / 有（说明：__）')
    md.push('- Y：像本人 __ / 贴合 __ / 有内容 __ / 不公式化 __；愿意直接发：是 / 否；事实/立场问题：无 / 有（说明：__）')
  }
  md.push('')
})
md.push('---')
md.push('')
md.push('6 个正常视频（游戏 5、生活/搞笑 1）计入均分；2 个信息不足视频（原神 6.3 / 花火）只判 SKIP，不计入均分。')
fs.writeFileSync(path.join(ROOT, 'blind_review_task06.md'), md.join('\n'), 'utf8')
fs.writeFileSync(path.join(DATA, 'task06_blind_key.csv'),
  '\uFEFFvideo_id,X,Y\r\n' + keyRows.map((r) => `${r.bvid},${r.X},${r.Y}`).join('\r\n') + '\r\n', 'utf8')

// 统计
const normal = videos.filter((v) => !v.insufficient)
const insufficient = videos.filter((v) => v.insufficient)
const skipCorrect = insufficient.every((v) => raw.filter((r) => r.bvid === v.bvid).every((r) => r.skipped))
const stats = {
  videos: videos.length,
  normal_videos: normal.length,
  insufficient_videos: insufficient.length,
  generations: raw.length,
  main_generations: raw.filter((r) => !r.insufficient).length,
  insufficient_generations: raw.filter((r) => r.insufficient).length,
  skip_correct_both_versions: skipCorrect,
  skip_by_video: insufficient.map((v) => ({
    video: v.bvid,
    v1: raw.find((r) => r.bvid === v.bvid && r.version === 'v1')?.skipped,
    v2lite: raw.find((r) => r.bvid === v.bvid && r.version === 'v2lite')?.skipped,
  })),
  main_comments: raw.filter((r) => !r.insufficient).length,
  generation_order: raw.map((r) => ({ order: r.order, video: r.bvid, version: r.version })),
}
fs.writeFileSync(path.join(DATA, 'task06_stats.json'), JSON.stringify(stats, null, 2) + '\n', 'utf8')

console.log(JSON.stringify(stats, null, 2))
