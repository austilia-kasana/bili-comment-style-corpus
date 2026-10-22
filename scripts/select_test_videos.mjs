// 任务 04：选中 20 个测试视频并补元信息（不扩大采集范围）
import fs from 'node:fs'
import path from 'node:path'

const HOME = process.env.USERPROFILE || process.env.HOME || '.'
const ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1')), '..')
const DATA = path.join(ROOT, 'data')
const VMETA = path.join(DATA, 'video_meta.json')
const SEL = path.join(DATA, 'test_videos.json')

const SELECTED = [
  ['BV1d4g16mEse', '游戏'], ['BV1KZpX69Efe', '游戏'], ['BV1u7uS67Eqe', '游戏'], ['BV1SUFYzZEoA', '游戏'],
  ['BV1hnpm6CE16', '动物'], ['BV1RK4y1j75P', '动物'], ['BV12Dp26PET5', '动物'], ['BV1U3411u7m1', '动物'],
  ['BV1iS411w7s3', '搞笑'], ['BV1ox411i7rD', '搞笑'], ['BV1i6tCekEN8', '搞笑'],
  ['BV1Rzk1YwEK4', '音乐'], ['BV1kU421d718', '音乐'], ['BV19spM6qEh5', '音乐'],
  ['BV16c411V7XG', '剧情'], ['BV1EsBjYLEmC', '剧情'], ['BV1HMGfedET8', '剧情'],
  ['BV1We4y1871T', '知识'], ['BV1c9DWBwEXy', '知识'], ['BV1mC411W74W', '知识'],
]

const cred = JSON.parse(fs.readFileSync(path.join(HOME, '.bili-ai', 'credentials.json'), 'utf8'))
const COOKIE = `SESSDATA=${cred.sessdata}; bili_jct=${cred.bili_jct}; buvid3=${cred.buvid3}`
const UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
const H = { 'user-agent': UA, referer: 'https://www.bilibili.com/', cookie: COOKIE, 'accept-language': 'zh-CN,zh;q=0.9' }
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

let meta = {}
try { meta = JSON.parse(fs.readFileSync(VMETA, 'utf8')) } catch {}
const out = []
for (const [bvid, topic] of SELECTED) {
  let m = meta[bvid]
  if (!m || m.error) {
    const j = await (await fetch(`https://api.bilibili.com/x/web-interface/view?bvid=${bvid}`, { headers: H })).json()
    if (j.code === 0) {
      const d = j.data
      m = {
        bvid, aid: d.aid, title: d.title, desc: d.desc,
        desc_v2: (d.desc_v2 ?? []).map((x) => x.raw_text).join('\n'),
        tname: d.tname, duration: d.duration, pubdate: d.pubdate,
        owner: { mid: d.owner?.mid, name: d.owner?.name },
        stat: { view: d.stat?.view, reply: d.stat?.reply, danmaku: d.stat?.danmaku, like: d.stat?.like, favorite: d.stat?.favorite },
        pages: d.videos,
      }
      meta[bvid] = m
      console.log(`✓ ${bvid} desc=${String(d.desc ?? '').length} ${String(d.title).slice(0, 30)}`)
    } else {
      console.log(`✗ ${bvid} code=${j.code} ${j.message}`)
    }
    await sleep(800)
  } else {
    console.log(`= ${bvid} 已有元信息 desc=${String(m.desc ?? '').length}`)
  }
  out.push({ bvid, topic, title: m?.title ?? '', desc: m?.desc ?? '', tname: m?.tname ?? '', duration: m?.duration ?? 0 })
}
fs.writeFileSync(VMETA, JSON.stringify(meta, null, 2) + '\n')
fs.writeFileSync(SEL, JSON.stringify(out, null, 2) + '\n')
console.log(`saved ${out.length} → ${SEL}`)
