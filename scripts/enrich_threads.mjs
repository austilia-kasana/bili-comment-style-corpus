// 只读补全：命中评论的楼中楼上下文（root/parent/回复对象），并发现用户在同楼的二级回复
import fs from 'node:fs'
import path from 'node:path'

const HOME = process.env.USERPROFILE || process.env.HOME || '.'
const ROOT_DIR = path.resolve(path.dirname(new URL(import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1')), '..')
const DATA = path.join(ROOT_DIR, 'data')
const RAW = path.join(DATA, 'raw.jsonl')
const STATE = path.join(DATA, 'thread_state.json')
const OUT = path.join(DATA, 'comment_context.json')
const MANIFEST = path.join(DATA, 'manifest.json')
const TARGET = 'YOUR_MID'

const cred = JSON.parse(fs.readFileSync(path.join(HOME, '.bili-ai', 'credentials.json'), 'utf8'))
const COOKIE = `SESSDATA=${cred.sessdata}; bili_jct=${cred.bili_jct}; buvid3=${cred.buvid3}`
const UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
const H = { 'user-agent': UA, referer: 'https://www.bilibili.com/', cookie: COOKIE, 'accept-language': 'zh-CN,zh;q=0.9' }
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

// 收集命中评论，按 (aid, root) 分组
const hits = []
const seenRpid = new Set()
for (const line of fs.readFileSync(RAW, 'utf8').split('\n')) {
  if (!line.trim()) continue
  let o; try { o = JSON.parse(line) } catch { continue }
  if (o._source !== 'video_comment_scan') continue
  const r = o.item || {}
  if (String(r.mid) !== TARGET) continue
  const root = Number(r.root ?? 0) || Number(r.rpid ?? 0)
  hits.push({ rpid: String(r.rpid), aid: o._video?.aid, bvid: o._video?.bvid, title: o._video?.title, root: String(root), parent: String(r.parent ?? 0) })
  seenRpid.add(String(r.rpid))
}
const groups = new Map()
for (const h of hits) {
  const key = `${h.aid}|${h.root}`
  if (!groups.has(key)) groups.set(key, { aid: h.aid, root: h.root, bvid: h.bvid, title: h.title, hits: [] })
  groups.get(key).hits.push(h)
}
console.log(`命中 ${hits.length} 条，${groups.size} 个楼层`)

let state = { done: {} }
try { state = JSON.parse(fs.readFileSync(STATE, 'utf8')) } catch {}
let ctx = {}
try { ctx = JSON.parse(fs.readFileSync(OUT, 'utf8')) } catch {}

const out = fs.createWriteStream(RAW, { flags: 'a' })
let newL2 = 0
for (const [key, g] of groups) {
  if (state.done[key]) continue
  console.log(`\n楼层 ${g.bvid} aid=${g.aid} root=${g.root}`)
  const replies = []
  let rootComment = null
  let pages = 0, err = null
  for (let pn = 1; pn <= 6; pn += 1) {
    let j
    try {
      j = await (await fetch(`https://api.bilibili.com/x/v2/reply/reply?type=1&oid=${g.aid}&root=${g.root}&pn=${pn}&ps=20`, { headers: H })).json()
    } catch (e) { err = String(e.message).slice(0, 200); break }
    if (j.code !== 0) { err = `code=${j.code} ${j.message}`; break }
    if (pn === 1) rootComment = j.data?.root ?? null
    const rs = j.data?.replies ?? []
    replies.push(...rs); pages += 1
    if (rs.length < 20) break
    await sleep(1200)
  }
  const byRpid = new Map()
  if (rootComment) byRpid.set(String(rootComment.rpid), rootComment)
  for (const r of replies) byRpid.set(String(r.rpid), r)

  // 为每个命中补 context
  for (const h of g.hits) {
    const parent = byRpid.get(h.parent) || (h.parent !== '0' ? null : null)
    const self = byRpid.get(h.rpid)
    ctx[h.rpid] = {
      root_rpid: String(g.root),
      parent_rpid: h.parent === '0' ? '' : h.parent,
      reply_to_mid: parent ? String(parent.mid) : '',
      reply_to_name: parent?.member?.uname ?? '',
      reply_to_text: String(parent?.content?.message ?? ''),
      root_author: rootComment?.member?.uname ?? '',
      root_mid: rootComment ? String(rootComment.mid) : '',
      root_text: String(rootComment?.content?.message ?? ''),
      thread_replies: replies.length,
      thread_pages: pages,
      thread_complete: replies.length < 120 && !err,
      mentions: (self?.content?.members ?? []).map((m) => ({ mid: String(m.mid), name: m.uname })),
      error: err,
      at: new Date().toISOString(),
    }
  }
  // 发现同楼里用户自己的二级回复（还没进 raw 的）
  for (const r of replies) {
    if (String(r.mid) !== TARGET) continue
    if (seenRpid.has(String(r.rpid))) continue
    seenRpid.add(String(r.rpid))
    newL2 += 1
    out.write(JSON.stringify({
      _collected_at: new Date().toISOString(),
      _source: 'video_comment_thread',
      _video: { bvid: g.bvid, aid: g.aid, title: g.title },
      item: r,
    }) + '\n')
    // 给新发现的二级回复也补上下文
    const p = byRpid.get(String(r.parent))
    ctx[String(r.rpid)] = {
      root_rpid: String(g.root),
      parent_rpid: String(r.parent ?? ''),
      reply_to_mid: p ? String(p.mid) : '',
      reply_to_name: p?.member?.uname ?? '',
      reply_to_text: String(p?.content?.message ?? ''),
      root_author: rootComment?.member?.uname ?? '',
      root_mid: rootComment ? String(rootComment.mid) : '',
      root_text: String(rootComment?.content?.message ?? ''),
      thread_replies: replies.length,
      thread_pages: pages,
      thread_complete: replies.length < 120 && !err,
      mentions: (r.content?.members ?? []).map((m) => ({ mid: String(m.mid), name: m.uname })),
      error: err,
      at: new Date().toISOString(),
    }
    console.log(`  + 发现同楼二级回复 rpid=${r.rpid} ${String(r.content?.message ?? '').slice(0, 40)}`)
  }
  state.done[key] = { pages, replies: replies.length, newL2: 0, error: err, at: new Date().toISOString() }
  await sleep(1200)
}
out.end()
fs.writeFileSync(STATE, JSON.stringify(state, null, 2) + '\n')
fs.writeFileSync(OUT, JSON.stringify(ctx, null, 2) + '\n')

let manifest = {}
try { manifest = JSON.parse(fs.readFileSync(MANIFEST, 'utf8')) } catch {}
manifest.sources.comment_thread_context = {
  source: 'api.bilibili.com/x/v2/reply/reply（楼中楼）',
  threads: Object.keys(state.done).length,
  new_l2_discovered: newL2,
  state: state.done,
  note: '用于补 root/parent/回复对象；同楼发现的用户二级回复已追加 raw.jsonl。',
}
manifest.generated_at = new Date().toISOString()
fs.writeFileSync(MANIFEST, JSON.stringify(manifest, null, 2) + '\n')
console.log(`\n完成楼层 ${Object.keys(state.done).length}，新发现二级回复 ${newL2}`)
