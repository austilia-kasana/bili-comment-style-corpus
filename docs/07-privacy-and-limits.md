# 07 · 隐私与边界

## 公开仓库里有什么 / 没有什么

**有**：方法、汇总统计、字段说明、脱敏样例、风格指南（5 条去标识示例）、A/B 测试结果（模型生成的评论）、盲评表。

**没有**（默认被 `.gitignore` 排除）：

- `raw.jsonl` —— 762 条原始 API 响应，含用户历史动态/评论文本
- `comments.csv` —— 归一化后的完整发言（含个人日记式动态）
- `context_review.csv` —— 原文 + 上下文
- `style_labels.csv` —— 729 条历史原文 + 标签
- `comment_context.json`、`video_meta.json`、各 `*_state.json`
- `credentials.json`、任何 cookie / SESSDATA / token

原因：`style_labels.csv` 与原始动态里包含个人日记、情绪自述、家庭/身体等敏感内容。**公开仓库 = 永久公开**，不适合放这些。

## 想让 GPT 读全文怎么办

1. 建一个 **Private** GitHub 仓库（不要 Public）。
2. 在本地把需要的数据文件从 `.gitignore` 里去掉（或 `git add -f`），确认仓库是 Private 后再 push。
3. 只给需要的人/服务开访问权限；不要把仓库临时改成 Public。

## 凭证

- cookie / SESSDATA / bili_jct 只在本地 `~/.bili-ai/credentials.json`。
- 仓库、报告、脚本输出里都没有凭证；采集脚本从本地文件读，不打印、不上传。

## 访问边界

- 没有读取私密观看历史/点赞记录；没有绕过平台限制。
- 没有发布任何评论、动态或私信。
- 没有把整份原始语料发给外部服务；风格指南只用了 5 条精选、去标识、非敏感示例。
