# 20 · Task 10 第一轮验证：Schema v2 的实际表现

**日期**：2026-11-19
**成本**：**¥0.3399**（试跑 3 条 ¥0.0042 + 全量 214 条 ¥0.3357）
**规模**：223 条 → 202 条已分析 / 21 条跳过

---

## 一、执行结果

```
总记录        223
已分析        202
跳过          21（原文 < 5 字，直接标 skipped，不调用模型）
失败          0
耗时          1,530 秒（25 分钟）

输入 token    187,357
输出 token    164,120
成本          ¥0.3399
```

**21 条跳过的处理是 v2 相对 v1 的一个改进。** v1 对这类极短文本也会硬跑，产出的全是「unknown + 低置信度」的垃圾。

---

## 二、四项验证结果

### ① unknown 占比：✅ 通过

| | v1 | v2 |
|---|---|---|
| valence = unknown | **26.5%** | **18.4%** |

**下降 8.1 个百分点。**

完整分布：

| valence | v1 | v2 |
|---|---|---|
| negative | 96 | 86 |
| mixed | 38 | **57** |
| unknown | 59 | 41 |
| neutral | 12 | 21 |
| positive | 18 | 18 |

**值得注意：`mixed` 从 38 涨到 57。** 这是因为新标签（`irony`、`self_deprecation`、`playfulness`）本身带有「同时有两种情绪」的语义，让模型更愿意承认情绪是混合的。

**这可能是好事**——真实表达本来就更常是混合的。

### ② 标签滥用：❌ **未通过**

**两个标签都撞线：**

| 标签 | 次数 | 占比 | 判定 |
|---|---|---|---|
| `helplessness` | 72 | **32.3%** | ❌ 超过 30% |
| `frustration` | 72 | **32.3%** | ❌ 超过 30% |
| `playfulness` | 55 | 24.7% | ⚠️ 偏高 |
| `confusion` | 44 | 19.7% | 可接受 |

**更关键的发现：`helplessness` 和 `frustration` 次数完全相同（都是 72），且 51% 的 `helplessness` 记录同时标了 `frustration`。**

**这说明模型把它们当同义词在成对使用，而不是当成两个不同的情绪。**

**这两个标签是 v2 才加进枚举的**——`helplessness` 是我从 1 条样本推断的，`frustration` 是 v1 就有的。

**我预测的「新增标签可能被滥用」，应验了。**

### ③ category 分布：✅ 通过

```
self          43  19.3%  ← 最大
unknown       36  16.1%  ← 但见下方说明
media         26  11.7%
body          23  10.3%
daily         21   9.4%
mood          19   8.5%
society       12   5.4%
desire        11   4.9%
work_money    11   4.9%
creation       6   2.7%
relationship   5   2.2%
knowledge      5   2.2%
dream          5   2.2%
```

**最大类别 `self` 只占 19.3%，远低于 40% 的警戒线。✅**

**`unknown` 那 16.1% 需要拆开看：**

| | 条数 |
|---|---|
| 其中是极短文本（skipped） | **21** |
| 真正分析后仍归不进 12 类 | **15** |

**15 / 202 = 7.4%。** 对于一个 12 类的体系，**这个比例是可接受的**。

**所以 `unknown 16.1%` 这个数字有误导性**——它被 21 条空文本撑起来了。**看这个指标时必须先剔除 skipped。**

### ④ detail 长度：✅ 通过

```
min 0   max 31   中位 16   超过 40 字的 0
```

**最长 31 字，全部在限内。** v1 那种「写成小作文」的问题解决了。

---

## 三、其他完整性

| 项 | 结果 |
|---|---|
| `other` 出现 | **0**（v1 是 87） |
| `interpretation` 缺失 | **0**（v1 是 2） |
| 新增 8 个标签使用情况 | **8/8 全部被用到** |
| 平均标签数 | 2.19 个/条 |
| 有标签的记录 | 201/223 |
| 被 normalize 修正过的记录 | 见下 |

**新增标签的实际使用：**

```
playfulness   55       irony         41       self_deprecation 33
anticipation  23       affection     13       helplessness     72  ← 滥用
disgust        8       admiration     5
```

**8 个都真的用上了，说明它们不是多余的。**

---

## 四、判定：v2 是改进，但还不是定稿

| 项 | 结论 |
|---|---|
| `other` 与 `unknown` 语义重叠 | ✅ 已解决（other 归零） |
| topic 无法聚合 | ✅ 已解决（12 类，最大 19.3%） |
| `interpretation` 会漏 | ✅ 已解决（必填） |
| unknown 占比 | ✅ 从 26.5% 降到 18.4% |
| **新增标签滥用** | ❌ **`helplessness` 32.3%，与 `frustration` 重叠 51%** |

**一个结构性进步 + 一个遗留问题。**

---

## 五、v2.1 该怎么改

### 5.1 核心问题：`frustration` 与 `helplessness` 定义重叠

**现状：**

```
frustration   v1 就有，定义为「挫败/受阻」
helplessness  v2 新增，定义为「无力/无奈」
```

**两者在语义上确实不同：**

```
frustration   = 想做成但被挡住（有阻力，可以怪外部）
helplessness  = 明知做不成，连抵抗的力气都没有（无阻力，只能接受）
```

**但模型分不出来，52 次同时使用。**

### 5.2 三个选项

| 方案 | 做法 | 代价 |
|---|---|---|
| **A. 合并** | 只留 `frustration`，删 `helplessness` | 丢掉一个真实存在的情绪区分 |
| **B. 加定义 + 互斥规则** | 在 prompt 里写清区别，并规定「不得同时使用，除非能分别给出 quoted_cues」 | 需要一次重跑验证 |
| **C. 接受现状** | 承认模型分不出来，把两个当同义词 | 标签冗余，但数据可用 |

**我倾向 B**，理由：

- **A 丢信息**——「无力」和「挫败」在中文里确实是两种不同的感受
- **C 会让统计失真**——两个标签各占 32%，实际是同一个概念占了 32%
- **B 的成本只有一次重跑**

### 5.3 B 方案的具体改法

在 prompt 的字段说明里加：

```
frustration = 想做成某件事但被外部条件挡住，伴有烦躁/不甘
helplessness = 明知无法改变现状，连尝试的力气都没有，伴有认命/疲惫

⚠️ 这两个标签不要同时使用。
   只能二选一，选择更贴切的那个。
   如果确实两种感受都有，选主导的那个，并在 counterevidence 里说明另一种。
```

**同时在 schema 里加条件校验：**

```json
{
  "comment": "frustration 与 helplessness 互斥",
  "if": { "properties": { "emotion_signals": { "properties": {
    "labels": { "contains": { "const": "frustration" } } } } } },
  "then": { "properties": { "emotion_signals": { "properties": {
    "labels": { "not": { "contains": { "const": "helplessness" } } } } } } }
}
```

**加上后重跑，看这两个标签的占比是否回到 15~20% 的合理区间。**

---

## 六、下一步

| 顺序 | 事项 | 成本 | 说明 |
|---|---|---|---|
| 1 | 写 v2.1：加互斥规则 | ¥0 | 改 prompt 一行 + schema 一条校验 |
| 2 | 重跑全量验证 | 约 ¥0.35 | 看 helplessness/frustration 是否分开 |
| 3 | 若通过 → 接进 `fish_experience_log` | ¥0 | — |
| 4 | 若仍不通过 → 考虑方案 A（合并） | ¥0.35 | — |

**在 2 通过之前，v2 的结果不应作为长期记忆的依据。**

---

## 七、数据位置

| 文件 | 位置 | 公开 |
|---|---|---|
| v2 逐条结果 | `local/text_analysis.v2.jsonl` | ❌（含 quoted_cues） |
| v2 统计摘要 | `local/analysis_summary.v2.json` | 待脱敏 |
| v1 逐条结果 | `local/text_analysis.jsonl` | ❌ |
| schema v2 | `data/text_analysis_schema.v2.json` | ✅ |
