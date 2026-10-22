# data/：放什么、不放什么

## 已包含（可公开）

| 文件 | 说明 |
|---|---|
| `samples/preview_diverse_20.md` | 20 条脱敏抽样（mid/昵称/BV 号已打码，文本截断） |
| `style_guide_v1.md` | 第一版个人风格指南（5 条去标识示例） |
| `test_prompts.md` | A/B 生成提示词（可复现） |
| `reports/manifest-summary.json` | 汇总统计（无原文、无 mid） |

## 默认不包含（`.gitignore` 排除）

| 文件 | 原因 |
|---|---|
| `raw.jsonl` | 762 条原始 API 响应，含历史动态/评论文本 |
| `comments.csv` | 归一化后的完整发言 |
| `context_review.csv` | 原文 + 上下文 |
| `style_labels.csv` | 729 条历史原文 + 标签，含个人日记/敏感自述 |
| `comment_context.json` | 楼中楼上下文 |
| `video_meta.json` | 视频元信息（可选） |
| `test_videos.json` | 测试视频选择（可选） |
| `*_state.json` | 采集断点 |

## 要在私有仓库里放全文

1. 确认仓库是 **Private**。
2. 从 `.gitignore` 删除对应行，或 `git add -f`。
3. 不要把 `credentials.json` / cookie 加进去。

字段定义见 [`schema.md`](schema.md)。
