// 只读：给指定视频补一段字幕/正文摘要（只取前 N 行，不下载视频/弹幕/抽帧）
// 用法: node fetch_subtitles.mjs BV1a BV1b ...
import fs from 'node:fs'
import path from 'node:path'
import crypto from 'node:crypto'

const HOME = process.env.USERPROFILE || process.env.HOME || '.'
const ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1')), '..')
const VMETA = path.join(ROOT, 'data', 'video_meta.json')
const cred = JSON.parse(fs.readFileSync(path.join(HOME, '.bili-ai', 'credentials.json'), 'utf8'))
const COOKIE = `SESSDATA=${cred.sessdata}; bili_jct=${cred.bili_jct}; buvid3=${cred.buvid3}`
const UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
const H = { 'user-agent': UA, referer: 'https://www.bilibili.com/', cookie: COOKIE, 'accept-language': 'zh-CN,zh;q=0.9' }
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
const MIXIN_TAB = [46,47,18,2,53,8,23,32,15,50,10,31,58,3,45,35,27,43,5,49,33,9,42,19,29,28,14,39,12,38,41,13,37,48,7,16,24,55,40,61,26,17,0,1,60,51,30,4,22,25,54,21,56,59,6,63,57,62,11,36,20,34,44,52]
const keyOf = (u) => String(u).slice(String(u).lastIndexOf('/') + 1, String(u).lastIndexOf('.'))
async function wbi(params) {
  const nav = await (await fetch('https://api.bilibili.com/x/web-interface/nav', { headers: H })).json()
  const raw = keyOf(nav?.data?.wbi_img?.img_url) + keyOf(nav?.data?.wbi_img?.sub_url)
  const mixin = MIXIN_TAB.map((i) => raw[i]).join('').slice(0, 32)
  const wts = Math.round(Date.now() / 1000)
  const clean = (v) => String(v).replace(/[!'()*]/g, '')
  const q = Object.keys({ ...params, wts }).sort().map((k) => `${encodeURIComponent(k)}=${encodeURIComponent(clean(k === 'wts' ? wts : params[k]))}`).join('&')
  return `${q}&w_rid=${crypto.createHash('md5').update(q + mixin).digest('hex')}`
}

const meta = JSON.parse(fs.readFileSync(VMETA, 'utf8'))
for (const bvid of process.argv.slice(2)) {
  const m = meta[bvid]
  if (!m) { console.log(`${bvid} 不在 video_meta`); continue }
  if (m.subtitle_snippet) { console.log(`${bvid} 已有字幕片段，跳过`); continue }
  const view = await (await fetch(`https://api.bilibili.com/x/web-interface/view?bvid=${bvid}`, { headers: H })).json()
  if (view.code !== 0) { m.subtitle_error = `view ${view.code}`; continue }
  const cid = view.data.pages?.[0]?.cid
  const qs = await wbi({ bvid, cid })
  const player = await (await fetch(`https://api.bilibili.com/x/player/wbi/v2?${qs}`, { headers: H })).json()
  const subs = player?.data?.subtitle?.subtitles ?? []
  if (!subs.length) { m.subtitle_snippet = ''; m.subtitle_note = '无官方字幕轨道'; console.log(`${bvid} 无字幕`); await sleep(1000); continue }
  const pick = subs.find((s) => s.lan === 'ai-zh') ?? subs.find((s) => s.lan === 'zh-CN') ?? subs[0]
  const url = String(pick.subtitle_url).startsWith('http') ? pick.subtitle_url : 'https:' + pick.subtitle_url
  const body = await (await fetch(url, { headers: { 'user-agent': UA } })).json().catch(() => null)
  const rows = (body?.body ?? []).slice(0, 60).map((x) => x.content).filter(Boolean)
  m.subtitle_snippet = rows.join(' / ').slice(0, 1200)
  m.subtitle_lan = pick.lan
  m.subtitle_lines = body?.body?.length ?? 0
  console.log(`${bvid} ✓ 字幕 ${m.subtitle_lines} 行（取前 60 行）`)
  await sleep(1000)
}
fs.writeFileSync(VMETA, JSON.stringify(meta, null, 2) + '\n')
