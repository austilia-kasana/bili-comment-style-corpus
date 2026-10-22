# 任务 03：数据报告对账与逐条风格标签

本轮先不要继续大规模爬取，也不要发布评论。现有 762 条记录足够开始第一版风格分析；当前任务是修正报告口径、给每条独立表达补充轻量标签，便于后续校准。

## A. 对账并明确“本轮新增”和“累计存档”

现有文件中：raw.jsonl 762 行，comments.csv 762 行，context_review.csv 762 行；三表 ID 集合一致。CSV 的 `canonical_for_style=true` 为 729 条，`false` 为 33 条，与报告一致。

但 manifest 的 `video_comment_scan` 逐视频 `hits` 合计为 14，而累计 raw/CSV 中有 16 条 `video_comment_scan` 记录。经按 ID 和采集时间核对，至少两条是上一轮已采集、此轮继续保留的记录：

- `321438556800`，视频 `BV1Rupi6HEqo`，采集时间 `2026-10-22T09:45:16Z`；当前逐视频统计 `hits=0`。
- `321420860864`，视频 `BV1hnpm6CE16`，采集时间 `2026-10-22T09:45:29Z`；当前逐视频统计 `hits=0`。

请保留原始记录，不要删数据；在 manifest 和质量报告中分别记录 `current_run_hits=14`、`previously_collected_rows_retained=2`、`cumulative_comment_l1_rows=16`、`comment_l2_rows=2`，或用等价字段清晰解释差异。不要继续把“当前扫描命中数”和“累计文件记录数”混在同一口径里。

## B. 重新说明上下文完整率

目前报告里的“基础语境 100%”主要代表有拼装后的 context / 标题元数据，并不代表模型真正获得了视频语义上下文。CSV 中 `context_snippet` 只有 5 条非空；仅 2 个视频补了字幕片段。

请在质量报告中分别列出：

- 有标题/关联卡片的记录数；
- 有非占位符视频简介的记录数；
- 有字幕或正文片段的记录数及涉及视频数；
- `context_snippet` 非空记录数；
- 仅靠标题/动态卡片的记录数。

不要将元数据存在率称为视频内容理解率。

## C. 为独立表达建立逐行标签

仅对 `canonical_for_style=true` 的 729 条记录生成一个新的 `style_labels.csv`，保留原 `id` 与原文，不覆盖 comments.csv。

推荐字段：

- `id`
- `topic_label`：游戏、动物/宠物、生活/搞笑、恐怖/悬疑、音乐、AI/科技、社会/时事、作品/虚拟主播、纯文字/个人动态、其他、unknown
- `expression_intent`：即时反应、梗/调侃、观点判断、解释/论证、提问/猜想、情绪/感慨、个人叙述、引用/转发理由、unknown
- `style_mode`：短反应、口语吐槽、分析解释、长推理、叙事/抒情、unknown
- `context_confidence`：high / medium / low
- `label_reason`：一句话说明判断依据

规则：

1. 标签必须针对每一行，而不仅是 manifest 中的汇总统计。
2. 先用原始文本、text_body、source_type、video_title、video_desc、context_snippet、quoted_text 作判断；没有充分上下文时标为 unknown/low，不要脑补。
3. `dynamic_forward` 的转发理由与被转发标题/原文要分开；不要把 `quoted_text` 当作作者本人文字。
4. 系统前缀单独处理，不要把“回复 @X”一类自动前缀当成稳定口癖。
5. 这一步只做可复核标签，不推断人格、政治立场或心理状态。
6. 先输出 30 条多样化标签预览供作者检查，再写完整文件。不要再抓取私人观看历史，不要尝试绕过平台访问限制。

## D. 交付

更新后的 `manifest.json`、`quality_report.md`、`style_labels.csv`，以及 30 条标签预览。保留原始 raw.jsonl / comments.csv / context_review.csv 的内容和 ID，不删改历史数据。
