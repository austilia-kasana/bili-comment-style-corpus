// 只读采集：候选视频评论区里目标 mid 的一级评论（分页 + 断点 + 失败即停）
// 用法: node collect_comments.mjs --pages 30 --extra "BV1a,BV1b" [--max-videos 30]
import fs from 'node:fs'
import path from 'node:path'

const HOME = process.env.USERPROFILE || process.env.HOME || '.'
const ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1')), '..')
const DATA = path.join(ROOT, 'data')
const RAW = path.join(DATA, 'raw.jsonl')
const STATE = path.join(DATA, 'comment_state.json')
const MANIFEST = path.join(DATA, 'manifest.json')
const VMETA = path.join(DATA, 'video_meta.json')

const arg = (k, d) => {
  const i = process.argv.indexOf('--' + k)
  return i >= 0 && process.argv[i + 1] && !process.argv[i + 1].startsWith('--') ? process.argv[i + 1] : d
}
const PAGES = Number(arg('pages', '30'))
const MAX_VIDEOS = Number(arg('max-videos', '30'))
const TARGET = String(arg('mid', 'YOUR_MID'))
const SLEEP = Number(arg('sleep', '1400'))
const EXTRA = String(arg('extra', '')).split(',').map((s) => s.trim()).filter(Boolean)

const cred = JSON.parse(fs.readFileSync(path.join(HOME, '.bili-ai', 'credentials.json'), 'utf8'))
const COOKIE = `SESSDATA=${cred.sessdata}; bili_jct=${cred.bili_jct}; buvid3=${cred.buvid3}`
const UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
const H = { 'user-agent': UA, referer: 'https://www.bilibili.com/', cookie: COOKIE, 'accept-language': 'zh-CN,zh;q=0.9' }
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

let vmeta = {}
try { vmeta = JSON.parse(fs.readFileSync(VMETA, 'utf8')) } catch {}

// 候选：动态里出现过的视频 + 用户投稿
const cand = []
const seen = new Set()
for (const line of fs.readFileSync(RAW, 'utf8').split('\n')) {
  if (!line.trim()) continue
  let o; try { o = JSON.parse(line) } catch { continue }
  if (o._source !== 'space_dynamics_polymer') continue
  const it = o.item || {}
  const arch = it.modules?.module_dynamic?.major?.archive || it.orig?.modules?.module_dynamic?.major?.archive
  if (arch?.bvid && !seen.has(arch.bvid)) { seen.add(arch.bvid); cand.push({ bvid: arch.bvid, source: 'dynamic_repost' }) }
}
for (const bvid of EXTRA) if (!seen.has(bvid)) { seen.add(bvid); cand.push({ bvid, source: 'user_video' }) }

let state = { scanned: {} }
try { state = JSON.parse(fs.readFileSync(STATE, 'utf8')) } catch {}
const todo = cand.filter((v) => !state.scanned[v.bvid]?.done).slice(0, MAX_VIDEOS)
console.log(`候选 ${cand.length}，未完成 ${cand.filter((v) => !state.scanned[v.bvid]?.done).length}，本次 ${todo.length}，每视频上限 ${PAGES} 页`)

const out = fs.createWriteStream(RAW, { flags: 'a' })
let runHits = 0
let fatal = null

// 已有评论 rpid（避免续采重复写入）
const seenRpids = new Set()
for (const line of fs.readFileSync(RAW, 'utf8').split('\n')) {
  if (!line.trim()) continue
  try { const o = JSON.parse(line); if (o._source === 'video_comment_scan' && o.item?.rpid) seenRpids.add(String(o.item.rpid)) } catch {}
}

for (const v of todo) {
  const vm = vmeta[v.bvid] || {}
  let aid = vm.aid || v.aid
  let title = vm.title || v.title || ''
  let replyTotal = vm.stat?.reply ?? null
  if (!aid) {
    const j = await (await fetch(`https://api.bilibili.com/x/web-interface/view?bvid=${v.bvid}`, { headers: H })).json().catch(() => null)
    if (!j || j.code !== 0) { state.scanned[v.bvid] = { done: true, error: `view ${j?.code ?? '?'} ${j?.message ?? ''}`, at: new Date().toISOString() }; continue }
    aid = j.data.aid; title = j.data.title; replyTotal = j.data.stat?.reply ?? null
  }
  console.log(`\n[${v.source}] ${v.bvid} aid=${aid} 评论总数=${replyTotal ?? '?'} ${String(title).slice(0, 36)}`)
  let total = 0, donePages = 0, hits = 0, err = null, lastPage = 0
  for (let pn = 1; pn <= PAGES; pn += 1) {
    let j
    try {
      const r = await fetch(`https://api.bilibili.com/x/v2/reply?type=1&oid=${aid}&pn=${pn}&ps=20&sort=0&nohot=1`, { headers: H })
      const ct = r.headers.get('content-type') || ''
      if (!ct.includes('json')) { err = `non-JSON HTTP ${r.status}：${(await r.text()).slice(0, 80).replace(/\s+/g, ' ')}`; fatal = err; break }
      j = await r.json()
    } catch (e) { err = String(e.message).slice(0, 200); fatal = err; break }
    if (j.code !== 0) { err = `code=${j.code} ${j.message}`; fatal = err; break }
    const reps = j.data?.replies ?? []
    lastPage = pn
    total += reps.length
    donePages += 1
    for (const rr of reps) {
      if (String(rr.mid) !== TARGET) continue
      if (seenRpids.has(String(rr.rpid))) continue
      seenRpids.add(String(rr.rpid))
      hits += 1; runHits += 1
      out.write(JSON.stringify({
        _collected_at: new Date().toISOString(),
        _source: 'video_comment_scan',
        _video: { bvid: v.bvid, aid, title, reply_total: replyTotal, source: v.source },
        item: rr,
      }) + '\n')
      console.log(`  ✓ rpid=${rr.rpid} ${new Date(rr.ctime * 1000).toLocaleString('zh-CN', { hour12: false })} ${String(rr.content?.message ?? '').slice(0, 40)}`)
    }
    if (reps.length < 20) break
    await sleep(SLEEP)
  }
  const complete = completePage(total, replyTotal, lastPage, PAGES)
  state.scanned[v.bvid] = { aid, title, reply_total: replyTotal, pages_cap: PAGES, pages_done: donePages, comments_seen: total, hits, complete, error: err, at: new Date().toISOString() }
  console.log(`  完成 ${donePages} 页 / ${total} 条 / 命中 ${hits}${complete ? '' : '（未完整：受页数上限或中断）'}${err ? ' 中断：' + err : ''}`)
  if (fatal) { console.log('  → 触发风控/接口异常，停止本轮（不绕过）'); break }
  await sleep(SLEEP)
}
out.end()
fs.writeFileSync(STATE, JSON.stringify(state, null, 2) + '\n')

function completePage(seen, total, lastPage, cap) {
  if (!total) return false
  return seen >= total || lastPage < cap
}

let manifest = {}
try { manifest = JSON.parse(fs.readFileSync(MANIFEST, 'utf8')) } catch {}
manifest.generated_at = new Date().toISOString()
manifest.sources.video_comment_scan = {
  source: 'api.bilibili.com/x/v2/reply（逐视频分页 + mid 过滤）',
  target_mid: TARGET,
  page_cap_per_video: PAGES,
  videos: state.scanned,
  total_hits: Object.values(state.scanned).reduce((s, x) => s + Number(x.hits ?? 0), 0),
  note: '评论无全量接口；每视频最多扫 pages_cap 页，未达 reply_total 的标 complete=false。',
}
manifest.limitations = [...new Set([...(manifest.limitations ?? []), '评论按视频逐页扫描，受页数上限与接口可用性限制，不等于全量历史。'])]
fs.writeFileSync(MANIFEST, JSON.stringify(manifest, null, 2) + '\n')
console.log(`\n本轮命中 ${runHits} 条；累计 ${manifest.sources.video_comment_scan.total_hits} 条`)
