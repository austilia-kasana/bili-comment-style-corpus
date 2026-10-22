# 任务 06 生成提示词与执行方式

## 模型与参数

- 模型：`deepseek-official/deepseek-flash`（16 次全部相同）。
- 参数：未暴露 temperature/top_p；基础提示词、视频事实、输出约束一致。
- 生成方式：**16 次独立生成**（8 视频 × v1 / v2-lite），每次新上下文；不带入其他视频或其他候选的输出。
- 执行顺序：随机打散后逐条调用；顺序记录在 `data/task06_generation_order.csv`。
- 输出：结构化 `{ comment: string, skipped: boolean }`；SKIP 时 comment="SKIP", skipped=true。

## 基础提示词

```
你是 B 站用户。看完下面这个视频后，写一条中文评论。只输出评论正文，不要解释。

【标题】{title}
【已核验事实】
- [{source}{, reviewed_by_user=true}] {fact}
...
【未确认】{unknown}

【风格指南】
{guide}

【输出要求】
- 只输出评论正文；如果上下文不足以写出一条贴合视频的评论，输出 SKIP（skipped=true）。
- 不编造视频没给的事实，不编造个人经历，不误判角色身份。
```

## v1 / v2-lite

- v1：`data/style_guide_v1.md`（原文，不修改）。
- v2-lite：`data/style_guide_v2_lite.md`（三条硬规则 + 放松表达限制）。

## 独立性说明

- 每个候选由独立的一次生成完成；提示词只包含该视频的事实 + 一份风格指南。
- 生成时看不到同一视频的另一版，也看不到其他视频的输出。
- 盲评编号在生成完成后另行随机；版本映射单独存 `data/task06_blind_key.csv`。
- 限制：无法控制 temperature/top_p；同一模型/同一提供方，但不同次生成仍有随机性。

## 证据类型

- `subtitle`：实际字幕/转录。
- `user_report`：用户人工补充，标 `reviewed_by_user=true`；不等于 `video_visual`。
- `description` / `title`：简介/标题。
- `unknown`：未确认，不靠常识补。
