# 03 · 方法

## 采集

- 动态：polymer 接口，`offset` 游标翻页；每页 12 条；按 `id_str` 去重；失败即停、保留游标。
- 评论：逐视频 `x/v2/reply`，`pn` 分页，`sort=0`，过滤 `mid == 目标`；每视频最多 30 页；记录 `pages_done / comments_seen / hits / complete / error`。
- 楼中楼：对命中的根评论抓 `x/v2/reply/reply`，补 `root_rpid / parent_rpid / reply_to_mid / reply_to_text`，并发现同楼里用户自己的二级回复。
- 语境：只对选中的视频补标题/简介/字幕；没有的字段留空并标 `context_missing`。

## 归一化

- 每条发言保留：`id`、`time_iso`、`source_type`、`url`、`text`、`context`、`author_uid`、`source`、`bvid`、`video_title`、`video_desc`。
- **文本不改写**：`text` 是原文；另存 `text_body`（去掉“回复 @X :”系统前缀）、`auto_prefix`（前缀本身）、`quoted_text`（转发时被引用的标题/原文）。
- 作者归属：空间动态由接口保证是本人；评论按 `mid` 精确过滤；全部 `verify_status=confirmed`。

## 去重

- 按 `id` 去重（动态 `id_str`、评论 `rpid`）。
- 文本重复：规范化后分组，写入 `duplicate_group_id`；每组用 `canonical_for_style` 选一条用于风格分析（优先有楼中楼上下文的评论，其次评论，其次最早）。
- 不因为“文本相同”就认定“同一次行为”：原始记录全部保留。

## 逐行标签（任务 03）

- 仅对 `canonical_for_style=true` 的 729 条打标。
- 字段：`topic_label`、`expression_intent`、`style_mode`、`context_confidence`、`label_reason`。
- 规则：先看 `text_body`，再看 `source_type / video_title / video_desc / context_snippet / quoted_text`；上下文不足标 `unknown/low`。
- 系统前缀、@ 提及、被引用内容不当作作者口癖；不推断人格/政治/心理。

## A/B 测试（任务 04）

- 20 个视频，6 类主题；上下文 = 标题 + 简介 + 可获得的字幕片段。
- A：中性基础提示词；B：同一提示词 + `data/style_guide_v1.md`。
- 同一模型、同一上下文；不发布；X/Y 随机盲评。
- SKIP 规则：只有标题/简介无内容时，宁可不写。

## 非目标

- 不推断人格、政治立场、心理状态。
- 不把标签当硬性人格规则。
- 不继续扩大采集，不抓私密观看历史，不绕过平台限制。
