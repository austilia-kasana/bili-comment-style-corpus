# 21 · Task 10 第二轮：v2.1 互斥规则的效果

**日期**：2026-11-19
**成本**：**¥0.3675**
**规模**：223 条 → 202 条已分析 / 21 条跳过
**相对 v2 的唯一改动**：`frustration` 与 `helplessness` 加定义区分 + 强制互斥

---

## 一、改了什么

### 1.1 prompt 加定义

```
frustration  = 想做成某件事，但被外部条件挡住；伴有烦躁、不甘、想再试
helplessness = 明知无法改变现状，连尝试的力气都没有；伴有认命、疲惫、沉默

⚠️ 这两个标签不得同时使用。只能二选一。
```

### 1.2 本地归一化兜底

```python
if "frustration" in ls and "helplessness" in ls:
    ls = [x for x in ls if x != "frustration"]   # 保留较窄的 helplessness
```

**全量跑下来，只有 4 条触发这个兜底**（v2 是 51% 重叠）。

---

## 二、结果对比

| 指标 | v1 | v2 | **v2.1** |
|---|---|---|---|
| `other` 出现 | 87 | 0 | **0** |
| `interpretation` 缺失 | 2 | 0 | **0** |
| valence = unknown | 26.5% | 18.4% | **18.8%** |
| `frustration` | — | 32.3% | **11.7%** |
| `helplessness` | — | 32.3% | **17.9%** |
| 两者同时出现 | — | 51% 重叠 | **0** |
| 新增 8 标签被使用 | — | 8/8 | **8/8** |
| 成本 | ¥0.4238 | ¥0.3357 | **¥0.3675** |

### 2.1 互斥规则完全生效

```
frustration 26 条   helplessness 40 条   同时 0 条
```

**v2 的 51% 重叠归零。这一项彻底修好了。**

### 2.2 但 `playfulness` 升到 31.8%

```
playfulness 71 条 = 31.8%
```

**按我设的「单标签 > 30% 即滥用」阈值，它踩线了。**

---

## 三、深入检查：它到底是不是滥用

### 3.1 分布证据

**跨类别分布（12 个类别全都有）：**

| 类别 | 条数 |
|---|---|
| media | 17 |
| daily | 13 |
| self | 9 |
| work_money / dream / body / desire | 各 5 |
| knowledge | 4 |
| creation | 3 |
| society / mood | 各 2 |
| unknown | 1 |

**valence 分布：**

| valence | 条数 |
|---|---|
| mixed | 31 |
| neutral | 14 |
| positive | 14 |
| negative | 12 |

**只有 `playfulness` 一个标签的记录：4 条。**

### 3.2 共现

| 共现标签 | 条数 | 占 playfulness |
|---|---|---|
| self_deprecation | 22 | 31% |
| confusion | 16 | 23% |
| irony | 14 | 20% |
| anticipation | 12 | 17% |

### 3.3 判断：**不是滥用，是我把「语气」和「情绪」混进了同一个枚举**

**三条证据：**

1. **跨全部 12 个类别**——如果它代表某类内容，应该集中在几类
2. **正负valence都有**（positive 14 / negative 12）——情绪标签通常有极性倾向
3. **极少单独出现**（4/71）——它总是附着在别的情绪上

**结论：`playfulness`（调侃）、`irony`（反讽）、`self_deprecation`（自嘲）是**表达语气/register**，不是情绪状态。**

**把它们和 joy / sadness / fear 放在同一个 `labels` 数组里，就会出现「某个语气占了 32%」这种假警报。**

---

## 四、这个发现的含义

### 4.1 当前 schema 的结构性问题

现在的 v2/v2.1 schema：

```json
"emotion_signals": {
  "valence": "...",
  "intensity": "...",
  "labels": ["joy", "playfulness", "irony", ...]   ← 情绪和语气混在一起
}
```

**这导致两个后果：**

- **统计失真**：`playfulness 31.8%` 会被误读成「三分之一的动态是调侃情绪」
- **模型困惑**：prompt 里没说清哪个是情绪哪个是语气，模型只能自己猜

### 4.2 v3 应该怎么改

**拆成两个字段：**

```json
"emotion_signals": {
  "valence": "...",
  "intensity": "...",
  "emotions": ["joy", "sadness", "frustration", "helplessness", "anxiety", ...],
  "registers": ["playfulness", "irony", "self_deprecation", "sarcasm", ...],
  "quoted_cues": [...],
  "basis": "..."
}
```

**划分依据：**

| 归到 `emotions` | 归到 `registers` |
|---|---|
| joy, sadness, anger, fear, anxiety | **playfulness（调侃）** |
| loneliness, fatigue, relief, gratitude | **irony（反讽）** |
| nostalgia, frustration, numbness, confusion | **self_deprecation（自嘲）** |
| hope, disgust, anticipation, affection | |
| admiration, helplessness | |

**`anticipation`（期待）和 `affection`（喜爱）是情绪还是语气？**

- `anticipation` → **情绪**（有明确的心理指向）
- `affection` → **情绪**（指向特定对象）

**所以 `registers` 目前只有 3 个：playfulness / irony / self_deprecation。**

**这正好对应我最初从 13 条样本里推断出的 8 个新标签中的 3 个。** 剩下 5 个（disgust / anticipation / affection / admiration / helplessness）确实是情绪，留在 `emotions` 里是对的。

---

## 五、v2.1 是否可以定稿

### 5.1 通过的项

| 项 | 结论 |
|---|---|
| `other` 归零 | ✅ |
| `interpretation` 补齐 | ✅ |
| unknown 占比下降 | ✅ 26.5% → 18.8% |
| `frustration`/`helplessness` 互斥 | ✅ 重叠归零 |
| category 可聚合 | ✅ 最大 18.4% |
| detail 长度 | ✅ 全部 ≤40 字 |

### 5.2 未通过的项

| 项 | 结论 |
|---|---|
| 单标签占比 | ❌ `playfulness` 31.8% |

**但这一项失败的原因不是标签定错，而是**字段设计把语气当成了情绪**。**

### 5.3 判定

**v2.1 的「数据」可以用，但「结构」还需要 v3。**

**具体说：**

- **valence / intensity / category / salience / life_event 这些字段的结果可以直接用**
- **`labels` 数组需要拆成 `emotions` + `registers` 之后才能做统计**
- **在拆分之前，不要拿 `playfulness 31.8%` 当结论**

---

## 六、下一步

| 顺序 | 事项 | 成本 | 说明 |
|---|---|---|---|
| 1 | 写 v3：`labels` 拆成 `emotions` + `registers` | ¥0 | 纯 schema 改动 |
| 2 | 用 v3 重跑 | 约 ¥0.37 | 看统计是否变合理 |
| 3 | 若通过 → 接进 `fish_experience_log` | ¥0 | — |
| 4 | 若不通过 → 再查 | ¥0.37 | — |

**注意：v3 不需要重新设计标签，只需要把现有 23 个标签分成两组。** 这是最小改动。

**预期 v3 的结果：**

```
emotions  每个占比应更分散，最大可能 frustration 或 sadness ~15%
registers playfulness 仍会高（因为它是常见语气），但单独统计，不再污染情绪分布
```

---

## 七、累计成本

| 轮次 | 成本 |
|---|---|
| v1（Task 09） | ¥0.4238 |
| v2 验证 | ¥0.3399 |
| v2.1 | ¥0.3675 |
| **合计** | **¥1.1312** |

**预算 ¥17，已用约 6.7%。**

---

## 八、数据位置

| 文件 | 位置 |
|---|---|
| v2.1 逐条结果 | `local/text_analysis.v2.1.jsonl` |
| v2.1 统计摘要 | `local/analysis_summary.v21.json` |
| v2 逐条结果 | `local/text_analysis.v2.jsonl` |
| v1 逐条结果 | `local/text_analysis.jsonl` |
