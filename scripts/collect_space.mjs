// 只读采集：B 站用户空间动态（polymer 新版接口，WBI 签名）
// 特性：翻页游标、断点续采、去重、原始数据留存、manifest 记录
// 用法: node collect_space.mjs --mid YOUR_MID --max-pages 2
import fs from 'node:fs'
import path from 'node:path'
import crypto from 'node:crypto'

const HOME = process.env.USERPROFILE || process.env.HOME || '.'
const ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1')), '..')
const DATA = path.join(ROOT, 'data')
fs.mkdirSync(DATA, { recursive: true })

const arg = (k, d) => {
  const i = process.argv.indexOf('--' + k)
  return i >= 0 && process.argv[i + 1] && !process.argv[i + 1].startsWith('--') ? process.argv[i + 1] : d
}
const MID = String(arg('mid', 'YOUR_MID'))
const MAX_PAGES = Number(arg('max-pages', '2'))
const SLEEP_MS = Number(arg('sleep', '1800'))
const RAW = path.join(DATA, 'raw.jsonl')
const STATE = path.join(DATA, 'space_state.json')
const MANIFEST = path.join(DATA, 'manifest.json')

const cred = JSON.parse(fs.readFileSync(path.join(HOME, '.bili-ai', 'credentials.json'), 'utf8'))
const COOKIE = `SESSDATA=${cred.sessdata}; bili_jct=${cred.bili_jct}; buvid3=${cred.buvid3}`
const UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
const H = {
  'user-agent': UA,
  referer: `https://space.bilibili.com/${MID}/dynamic`,
  origin: 'https://space.bilibili.com',
  cookie: COOKIE,
  'accept-language': 'zh-CN,zh;q=0.9',
}

const MIXIN_TAB = [46,47,18,2,53,8,23,32,15,50,10,31,58,3,45,35,27,43,5,49,33,9,42,19,29,28,14,39,12,38,41,13,37,48,7,16,24,55,40,61,26,17,0,1,60,51,30,4,22,25,54,21,56,59,6,63,57,62,11,36,20,34,44,52]
const keyOf = (u) => String(u).slice(String(u).lastIndexOf('/') + 1, String(u).lastIndexOf('.'))
async function wbi(params) {
  const nav = await (await fetch('https://api.bilibili.com/x/web-interface/nav', {
    headers: { 'user-agent': UA, referer: 'https://www.bilibili.com/', cookie: COOKIE },
  })).json()
  const img = nav?.data?.wbi_img?.img_url, sub = nav?.data?.wbi_img?.sub_url
  if (!img || !sub) throw new Error('nav 无 wbi_img')
  const raw = keyOf(img) + keyOf(sub)
  const mixin = MIXIN_TAB.map((i) => raw[i]).join('').slice(0, 32)
  const wts = Math.round(Date.now() / 1000)
  const clean = (v) => String(v).replace(/[!'()*]/g, '')
  const q = Object.keys({ ...params, wts }).sort()
    .map((k) => `${encodeURIComponent(k)}=${encodeURIComponent(clean(k === 'wts' ? wts : params[k]))}`).join('&')
  return `${q}&w_rid=${crypto.createHash('md5').update(q + mixin).digest('hex')}`
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
const iso = (ts) => (ts ? new Date(ts * 1000).toISOString() : null)
const local = (ts) => (ts ? new Date(ts * 1000).toLocaleString('zh-CN', { hour12: false }) : null)

// 读取已采集 id（去重 + 断点）
const seen = new Set()
let existing = 0
if (fs.existsSync(RAW)) {
  for (const line of fs.readFileSync(RAW, 'utf8').split('\n')) {
    if (!line.trim()) continue
    try { const o = JSON.parse(line); if (o.item?.id_str) seen.add(String(o.item.id_str)); existing += 1 } catch {}
  }
}
let state = { mid: MID, offset: '', pages_done: 0, last_run: null, errors: [], cursor_history: [] }
if (fs.existsSync(STATE)) {
  try {
    const s = JSON.parse(fs.readFileSync(STATE, 'utf8'))
    if (String(s.mid) === MID) state = { ...state, ...s }
  } catch {}
}
if (!state.offset) state.offset = ''

const out = fs.createWriteStream(RAW, { flags: 'a' })
const stats = { pages_ok: 0, pages_fail: 0, items_new: 0, items_dup: 0, start_offset: state.offset || null, end_offset: null }
const startedAt = new Date().toISOString()

for (let p = 0; p < MAX_PAGES; p += 1) {
  let j
  try {
    const qs = await wbi({ host_mid: MID, offset: state.offset || '', timezone_offset: -480, features: 'itemOpusStyle', platform: 'web', web_location: '333.1387' })
    const r = await fetch(`https://api.bilibili.com/x/polymer/web-dynamic/v1/feed/space?${qs}`, { headers: H })
    const ct = r.headers.get('content-type') || ''
    if (!ct.includes('json')) {
      const t = await r.text()
      throw new Error(`非 JSON（HTTP ${r.status}）：${t.slice(0, 120).replace(/\s+/g, ' ')}`)
    }
    j = await r.json()
  } catch (e) {
    stats.pages_fail += 1
    state.errors.push({ at: new Date().toISOString(), page: p + 1, offset: state.offset, error: String(e.message).slice(0, 300) })
    console.error(`[page ${p + 1}] 失败：${String(e.message).slice(0, 200)} → 停止（可续采）`)
    break
  }
  if (j.code !== 0) {
    stats.pages_fail += 1
    state.errors.push({ at: new Date().toISOString(), page: p + 1, offset: state.offset, code: j.code, message: j.message ?? j.msg })
    console.error(`[page ${p + 1}] code=${j.code} ${j.message ?? j.msg} → 停止（风控/权限，不绕过）`)
    break
  }
  const items = j.data?.items ?? []
  stats.pages_ok += 1
  for (const it of items) {
    const id = String(it.id_str ?? '')
    if (!id) continue
    if (seen.has(id)) { stats.items_dup += 1; continue }
    seen.add(id)
    out.write(JSON.stringify({
      _collected_at: new Date().toISOString(),
      _source: 'space_dynamics_polymer',
      _host_mid: MID,
      _page: p + 1,
      _offset_in: state.offset || null,
      item: it,
    }) + '\n')
    stats.items_new += 1
  }
  const next = j.data?.offset ?? ''
  const prevOffset = state.offset || ''
  state.cursor_history.push({ page: p + 1, offset_in: prevOffset || null, offset_out: next, items: items.length, at: new Date().toISOString() })
  state.pages_done = (state.pages_done || 0) + 1
  state.offset = next
  state.last_run = new Date().toISOString()
  if (!j.data?.has_more || !next || next === prevOffset) {
    console.log(`[page ${p + 1}] 无更多（has_more=${j.data?.has_more}）`)
    break
  }
  await sleep(SLEEP_MS)
}
stats.end_offset = state.offset || null
out.end()
fs.writeFileSync(STATE, JSON.stringify(state, null, 2) + '\n')

// manifest（保留既有来源，更新本来源）
let manifest = { generated_at: null, sources: {}, limitations: [] }
try { manifest = JSON.parse(fs.readFileSync(MANIFEST, 'utf8')) } catch {}
manifest.generated_at = new Date().toISOString()
manifest.sources.space_dynamics = {
  source: 'api.bilibili.com/x/polymer/web-dynamic/v1/feed/space',
  host_mid: MID,
  method: 'WBI 签名 + 登录态 cookie（本地读取，未外泄）',
  authorization: '用户本人在其设备与账号环境下授权读取公开空间动态',
  started_at: startedAt,
  finished_at: new Date().toISOString(),
  pages_ok: stats.pages_ok,
  pages_fail: stats.pages_fail,
  items_new: stats.items_new,
  items_duplicate: stats.items_dup,
  total_raw_lines: existing + stats.items_new,
  cursor: { start: stats.start_offset, end: stats.end_offset },
  cursor_history: state.cursor_history.slice(-20),
  errors: state.errors.slice(-20),
  coverage: {
    time_range: null, // 由 build 步骤填充
  },
}
manifest.limitations = [
  '空间动态接口只返回该用户的公开动态；删除/私密/仅粉丝可见的动态不可见。',
  '评论没有"全量历史"接口：只能对已知视频逐页扫描并按 mid 过滤，覆盖不完整。',
  '接口可能因风控返回非 JSON 或 code != 0；遇到即停止，不绕过。',
]
fs.writeFileSync(MANIFEST, JSON.stringify(manifest, null, 2) + '\n')

console.log(JSON.stringify({ pages_ok: stats.pages_ok, pages_fail: stats.pages_fail, items_new: stats.items_new, items_dup: stats.items_dup, raw_lines: existing + stats.items_new, next_offset: state.offset }, null, 2))
