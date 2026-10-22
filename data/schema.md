# 字段说明

## raw.jsonl（原始层，未公开）

每行一个 JSON：

```json
{
  "_collected_at": "ISO 时间",
  "_source": "space_dynamics_polymer | video_comment_scan | video_comment_thread",
  "_host_mid": "目标 mid（公开版会打码）",
  "_page": 1,
  "_offset_in": "上一页游标",
  "item": { "原始 API 对象，不改写" }
}
```

## comments.csv（29 列）

`id, time_iso, time_local, source_type, url, text, auto_prefix, text_body, quoted_text, context, author_uid, author_name, source, bvid, video_title, video_desc, root_rpid, parent_rpid, reply_to_mid, reply_to_text, like_count, mentions, duplicate_group_id, canonical_for_style, text_origin_confidence, context_source, context_snippet, context_missing, verify_status`

| 字段 | 说明 |
|---|---|
| `source_type` | dynamic_forward / dynamic_original_text / dynamic_original_draw / dynamic_video_share / dynamic_article / comment_l1 / comment_l2 |
| `text` | 原文，不改写 |
| `auto_prefix` | 系统“回复 @X :”前缀（单独存） |
| `text_body` | 去掉前缀后的正文 |
| `quoted_text` | 转发时被引用的标题/原文（不当作作者文字） |
| `canonical_for_style` | 去重后用于风格分析的一条 |
| `duplicate_group_id` | 文本重复分组 |
| `text_origin_confidence` | confirmed_user / likely_user / *_with_auto_prefix |
| `context_missing` | 缺失的上下文字段，分号分隔 |
| `verify_status` | confirmed / unverified |

## context_review.csv（14 列）

`id, source_type, url, video_title, text, context, reply_to_mid, reply_to_name, reply_to_text, root_rpid, parent_rpid, context_snippet, context_missing, verify_status`

## style_labels.csv（11 列，未公开）

`id, text, text_body, source_type, url, video_title, topic_label, expression_intent, style_mode, context_confidence, label_reason`

## test_results.csv（11 列）

`video_id, url, topic, context_quality, baseline_comment, personalized_comment, skip_reason, title, context_summary, known_facts, unconfirmed`

## manifest.json（关键块）

| 块 | 内容 |
|---|---|
| `sources.space_dynamics` | 动态页数、游标、错误、覆盖时间 |
| `sources.video_comment_scan` | 每视频 pages_done / comments_seen / hits / complete / hits_current_run / hits_prior_run / hits_cumulative |
| `sources.comment_thread_context` | 楼中楼楼层数、新发现 L2 |
| `dataset.reconciliation` | 14 / 2 / 16 / 2 对账 |
| `dataset.context_completeness` | 398 / 213 / 5 / 2 / 183 / 364 |
| `dataset.style_labels` | 标签分布与行数 |
