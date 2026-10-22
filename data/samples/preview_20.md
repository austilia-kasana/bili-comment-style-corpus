# 20 条脱敏预览（结构检查用）

> 目标 mid=107*** · 共 26 条归一化发言 · 预览取最新 20 条 · 文本未改写，仅截断/打码标识

> 注：预览里同一段文字可能同时出现在「转发理由」和「评论」两条记录中（同文跨来源，共 2 组），原始两条都保留，未合并。

| # | 时间(本地) | 类型 | 文本（截断） | 视频 | 来源 | 作者(脱敏) |
|---|---|---|---|---|---|---|
| 1 | 2026/10/21 22:15:53 | dynamic_forward | 不敢出去跑外卖了，好吓人😰@YOUR_NAME | BV1R***Eqo | space_dynamics_polymer | YOUR_NAME(107***) |
| 2 | 2026/10/21 22:15:53 | comment_l1 | 不敢出去跑外卖了，好吓人😰@YOUR_NAME | BV1R***Eqo | video_comment_scan | YOUR_NAME(107***) |
| 3 | 2026/10/21 19:42:22 | dynamic_forward | 这个好看，可惜没有续集@YOUR_NAME | BV1K***EoN | space_dynamics_polymer | YOUR_NAME(107***) |
| 4 | 2026/10/21 19:19:07 | dynamic_forward | 原版三只猫跳舞最讨厌的就是转圈那一段，主要后背侧身太丑了，肥鱼在这点上没那么令人厌恶，对吧，因为更可爱@YOUR_NAME | BV1h***E16 | space_dynamics_polymer | YOUR_NAME(107***) |
| 5 | 2026/10/21 19:19:07 | comment_l1 | 原版三只猫跳舞最讨厌的就是转圈那一段，主要后背侧身太丑了，肥鱼在这点上没那么令人厌恶，对吧，因为更可爱@YOUR_NAME | BV1h***E16 | video_comment_scan | YOUR_NAME(107***) |
| 6 | 2026/10/21 19:17:19 | dynamic_forward |  原版三只猫跳舞最讨厌的就是转圈那一段，主要后背侧身太丑了，肥鱼在这点上没那么令人厌恶，对吧，因为更可爱@YOUR_NAME | BV1h***E16 | space_dynamics_polymer | YOUR_NAME(107***) |
| 7 | 2026/10/21 17:27:55 | dynamic_forward | 主要是大肥鱼刷的视频基本都类同 | BV1k***EEH | space_dynamics_polymer | YOUR_NAME(107***) |
| 8 | 2026/10/21 17:21:10 | dynamic_forward | 闹鱼灾了 | BV1L***EtL | space_dynamics_polymer | YOUR_NAME(107***) |
| 9 | 2026/10/21 16:17:52 | dynamic_forward |  回复 @YOUR_NAME :晤，别看了，一堆片剪在一起了 | BV1S***Ekv | space_dynamics_polymer | YOUR_NAME(107***) |
| 10 | 2026/10/21 16:06:41 | dynamic_forward | 好看@YOUR_NAME | BV1S***Ekv | space_dynamics_polymer | YOUR_NAME(107***) |
| 11 | 2026/10/21 14:49:05 | dynamic_forward | 这是你吗@YOUR_NAME | BV12***ET5 | space_dynamics_polymer | YOUR_NAME(107***) |
| 12 | 2026/10/21 14:31:30 | dynamic_forward | 依旧智人tv大学习@YOUR_NAME | BV1u***E4x | space_dynamics_polymer | YOUR_NAME(107***) |
| 13 | 2026/10/21 14:23:19 | dynamic_forward | @YOUR_NAME 今日智人tv大学习 | BV1a***Emk | space_dynamics_polymer | YOUR_NAME(107***) |
| 14 | 2026/10/20 23:45:47 | dynamic_forward | @YOUR_NAME 很乖，我想象中的你的形象 | BV13***ESr | space_dynamics_polymer | YOUR_NAME(107***) |
| 15 | 2026/10/20 23:43:13 | dynamic_forward | 空悲切@YOUR_NAME | BV1x***Eca | space_dynamics_polymer | YOUR_NAME(107***) |
| 16 | 2026/10/20 23:33:25 | dynamic_forward |  回复 @奶龙出山 :从19年到现在也有7年了 | BV1K***Efe | space_dynamics_polymer | YOUR_NAME(107***) |
| 17 | 2026/10/20 23:14:20 | dynamic_forward |  回复 @YOUR_NAME :太能串了 | BV1d***ELC | space_dynamics_polymer | YOUR_NAME(107***) |
| 18 | 2026/10/20 23:06:32 | dynamic_forward | 严肃学习@YOUR_NAME | BV1d***ELC | space_dynamics_polymer | YOUR_NAME(107***) |
| 19 | 2026/10/20 22:56:31 | dynamic_forward | 神了@YOUR_NAME |  | space_dynamics_polymer | YOUR_NAME(107***) |
| 20 | 2026/10/20 22:23:34 | dynamic_forward |  肥鱼神了，我的建议少刷番剧，我没给你和我的号买大会员，只能看一点点 | BV16***7p3 | space_dynamics_polymer | YOUR_NAME(107***) |

## 字段说明（comments.csv 表头）

`id, time_iso, time_local, source_type, url, text, context, author_uid, author_name, source, bvid, video_title, video_desc, context_missing, verify_status`

- `source_type`：`dynamic_forward` / `dynamic_original` / `dynamic_video_share` / `comment_l1` / `comment_l2`
- `context_missing`：尚未补充的上下文字段（如 `video_content;subtitle`），不编造，留空
- `verify_status`：`confirmed` = 作者 mid 与目标一致；`unverified` = 待核实