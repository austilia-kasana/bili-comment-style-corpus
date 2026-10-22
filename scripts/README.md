# scripts/：采集与构建脚本

这些脚本来自本地工作目录，已把账号 mid/昵称替换为 `YOUR_MID` / `YOUR_NAME`。运行前需要：

- Node 18+（本地用的是 DSH 自带 Node 24）
- 本地凭证 `~/.bili-ai/credentials.json`（`sessdata` / `bili_jct` / `buvid3`），不要提交
- 数据目录与脚本同级的 `data/`

## 管线顺序

```bash
# 1) 空间动态（polymer 接口，游标翻页）
node scripts/collect_space.mjs --mid YOUR_MID --max-pages 60

# 2) 评论：逐视频分页 + mid 过滤（可加 --extra 用户投稿 BV）
node scripts/collect_comments.mjs --pages 30 --max-videos 30

# 3) 楼中楼：补 root/parent/回复对象，发现同楼二级回复
node scripts/enrich_threads.mjs

# 4) 归一化：raw.jsonl → comments.csv / context_review.csv / manifest
node scripts/build_corpus_v2.mjs

# 5) 逐行标签：canonical → style_labels.csv
node scripts/style_labels.mjs

# 6) 任务 04：选 20 个视频、补元信息/字幕
node scripts/select_test_videos.mjs
node scripts/fetch_subtitles.mjs BV1... BV1...

# 7) 任务 04：生成 test_results.csv / blind_review.md
node scripts/build_task04.mjs
```

## 每个脚本做什么

| 脚本 | 作用 |
|---|---|
| `collect_space.mjs` | 空间动态翻页、去重、断点、原始留存、manifest |
| `collect_comments.mjs` | 逐视频评论分页、mid 过滤、命中留存、失败即停 |
| `enrich_threads.mjs` | 楼中楼上下文、回复对象、同楼 L2 发现 |
| `build_corpus_v2.mjs` | 归一化、去重分组、上下文/来源字段、CSV/manifest/报告 |
| `style_labels.mjs` | 729 条逐行标签、30 条预览、对账/语境统计 |
| `select_test_videos.mjs` | 任务 04 的 20 个视频 + 元信息 |
| `fetch_subtitles.mjs` | 给指定视频补字幕片段（只取前 60 行） |
| `build_task04.mjs` | A/B 结果 CSV、盲评、X/Y 映射 |
| `list_candidates.mjs` | 按主题列候选视频 |

## 注意

- 脚本里的 `YOUR_MID` 需要替换成实际 mid（或通过参数传）。
- `data/` 里原始文件默认被 `.gitignore` 排除；脚本本身不含凭证。
- 遇到非 JSON / `code != 0` / 验证码/限流：脚本会停止并记录，不绕过。
