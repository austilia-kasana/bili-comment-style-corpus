// 列出候选视频（按主题分桶），供任务 04 选 20 个测试样本
import fs from 'node:fs'
import path from 'node:path'

const HOME = process.env.USERPROFILE || process.env.HOME || '.'
const ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1')), '..')
const DATA = path.join(ROOT, 'data')
const RAW = path.join(DATA, 'raw.jsonl')
const VMETA = path.join(DATA, 'video_meta.json')
const meta = JSON.parse(fs.readFileSync(VMETA, 'utf8'))

const vids = new Map()
for (const line of fs.readFileSync(RAW, 'utf8').split('\n')) {
  if (!line.trim()) continue
  let o; try { o = JSON.parse(line) } catch { continue }
  if (o._source !== 'space_dynamics_polymer') continue
  const it = o.item
  const arch = it.modules?.module_dynamic?.major?.archive || it.orig?.modules?.module_dynamic?.major?.archive
  if (!arch?.bvid) continue
  if (!vids.has(arch.bvid)) vids.set(arch.bvid, { bvid: arch.bvid, title: arch.title || '', desc: arch.desc || '', aid: arch.aid, time: Number(it.modules?.module_author?.pub_ts || 0) })
}

const TOPICS = [
  ['游戏', /游戏|LOL|世界赛|原神|明日方舟|我的世界|月圆|王者|吃鸡|CS|DOTA|崩坏|星穹|绝区零|三角洲|暗区|塔科夫|FPS|moba/],
  ['动物', /猫|喵|哈基米|狗|动物|薮猫|狮子|猴|宠物|兽|鸟|鱼/],
  ['搞笑', /搞笑|沙雕|爆笑|离谱|抽象|整活|挑战|翻车/],
  ['音乐', /歌|翻唱|音乐|樱花|术力口|洛天依|VOCALOID|钢琴|BGM|旋律|唱/],
  ['剧情', /剧情|电影|解说|故事|短剧|悬疑|恐怖|怪谈|都市传说/],
  ['知识', /知识|科普|教程|讲解|原理|历史|数学|物理|编程|AI|deepseek|模型/],
]
const bucket = (s) => { for (const [k, re] of TOPICS) if (re.test(s)) return k; return '其他' }

const groups = {}
for (const v of vids.values()) {
  const m = meta[v.bvid] || null
  const desc = (m?.desc && m.desc !== '-') ? m.desc : (v.desc && v.desc !== '-' ? v.desc : '')
  const t = bucket(`${v.title} ${desc}`)
  ;(groups[t] ??= []).push({ ...v, desc, tname: m?.tname || '', sub: !!m?.subtitle_snippet })
}
for (const [k, arr] of Object.entries(groups)) {
  console.log(`\n=== ${k} (${arr.length}) ===`)
  for (const v of arr.slice(0, 12)) console.log(`${v.bvid} | desc=${v.desc ? v.desc.length : 0} | sub=${v.sub ? 'Y' : 'N'} | ${String(v.title).slice(0, 46)}`)
}
