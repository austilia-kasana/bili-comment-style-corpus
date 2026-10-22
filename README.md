# B站个人评论风格语料库（Bili Comment Style Corpus）

> 从「采集自己的 B 站发言」到「逐行风格标签」再到「20 个视频的 A/B 盲评」的一条完整工作线。
> 本项目是为 GPT 阅读/接力准备的**可浏览档案**：保留方法、统计、标签口径、测试设计，**不在公开仓库里放原始个人语料**。

## 这条线在做什么

1. **建语料**：读取用户本人公开的空间动态与视频评论，保留原始记录、唯一 ID、来源、上下文和作者确认状态。
2. **扩样本**：从 24 条动态扩到 762 条原始记录 / 729 条去重后的独立表达，覆盖转发、原创文字、原创图文、一级评论、二级回复。
3. **对账与打标**：拆开「本轮扫描命中」与「累计存档」；为 729 条独立表达逐行打轻量标签（主题 / 意图 / 风格 / 语境置信度）。
4. **对照测试**：选 20 个视频，用同一模型、同一上下文生成 A（基础提示词）/ B（基础 + 第一版个人风格指南），盲评 X/Y，不发布。

## 关键数字

| 指标 | 数值 |
|---|---|
| 原始记录 | 762 |
| 去重后独立表达 | 729 |
| 时间跨度 | 2023-07-26 → 2026-10-21 |
| 类型 | 转发 520 · 原创文字 146 · 原创图文 78 · 一级评论 16 · 二级回复 2 |
| 作者确认率 | 100%（762/762，按 mid 精确过滤） |
| 语境 | 有标题/卡片 398 · 非占位简介 213 · 字幕片段 5 条（2 个视频）· 仅标题/卡片 183 |
| A/B 测试 | 20 个视频 · 6 类主题 · 生成 15 组 · SKIP 5 个 |

## 阅读顺序（给 GPT）

1. [`transcript/conversation.md`](transcript/conversation.md) —— **这句话之后的全部对话**：任务 01→04 的用户消息原文 + 助手回复（含澄清与仓库搭建）
2. [`docs/01-overview.md`](docs/01-overview.md) —— 任务 01→04 的来龙去脉与关键决策
3. [`docs/04-quality-report.md`](docs/04-quality-report.md) —— 数据质量、对账口径、语境口径
4. [`docs/05-style-labels.md`](docs/05-style-labels.md) —— 逐行标签的字段、分布与局限
5. [`docs/06-ab-test.md`](docs/06-ab-test.md) —— A/B 盲评设计与产出
6. [`docs/07-privacy-and-limits.md`](docs/07-privacy-and-limits.md) —— 哪些数据不在公开仓库、为什么

## 目录

```
transcript/
  conversation.md     这句话之后的全部对话（任务 01-04 + 回复）
docs/                 方法与报告
  briefs/             四轮任务原文（任务 01-04）
  samples/            脱敏样例（已打码）
data/
  samples/            脱敏预览
  reports/            汇总统计（无原文）
  schema.md           CSV/字段说明
  style_guide_v1.md   第一版个人风格指南（测试用）
  test_prompts.md     A/B 生成提示词（可复现）
test_results.csv      A/B 结果（评论为模型生成，不含个人原文）
blind_review.md       X/Y 随机盲评表
PUSH.md               如何创建仓库、哪些不能公开
scripts/README.md     采集/构建脚本的位置与用法
```

## 重要边界

- **不发布评论**：本项目所有产出都是本地分析/测试，没有自动发过任何评论。
- **不推断人格**：标签只描述文本的可复核特征，不推断政治立场、心理状态或人格。
- **原始个人语料不公开**：`raw.jsonl`、`comments.csv`、`context_review.csv`、`style_labels.csv` 含用户历史原文与敏感自述，默认被 `.gitignore` 排除。要让 GPT 读全文，请用**私有仓库**并把数据加进去（见 `docs/07-privacy-and-limits.md`）。
- **凭证不入库**：cookie/SESSDATA 只在本地 `~/.bili-ai/credentials.json`，仓库里没有任何凭证。
