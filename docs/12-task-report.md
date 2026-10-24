# Task 07 · 本轮操作报告

**执行时间**：2026-10-24
**花费**：**¥0.00**（零模型调用，全部本地脚本）
**状态**：阶段一完成；阶段二、三为结构设计，内容未填充

---

## 一、做了什么

| # | 事项 | 状态 |
|---|---|---|
| 1 | 定位原始语料 | ✅ 找到 `C:\Users\19536\Documents\bili-corpus\data\raw.jsonl`（7.65 MB） |
| 2 | 解析 762 条动态 | ✅ 全部解析成功 |
| 3 | 去重 | ✅ 745 条（重复 17 条） |
| 4 | 区分转发/原创 | ✅ 520 转发排除，224 条原创主集 |
| 5 | 建立索引 | ✅ `data/user_bili_original_index.csv` |
| 6 | 启发式候选筛选 | ✅ `data/emotion_memory_candidates.csv`（224 条评分，输出前 80） |
| 7 | 架构文档 | ✅ `docs/12-text-personality-memory-plan.md` |
| 8 | 预算与隐私边界 | ✅ `docs/13-budget-privacy-and-safety.md` |
| 9 | 人格假设模板 | ✅ `data/personality_hypotheses_initial.md`（模板 + 5 个待验证问题） |
| 10 | 经历记录 schema | ✅ `data/experience_log_schema.json` |

---

## 二、数据统计

### 2.1 原始数据分布

```
原始记录        762
去重后          745   （重复 17）
时间跨度        2023-07-26 → 2026-10-21
```

| dynamic_type | 数量 | 说明 |
|---|---|---|
| `DYNAMIC_TYPE_FORWARD` | 520 | 转发，按要求排除出主集 |
| `DYNAMIC_TYPE_WORD` | 146 | 纯文字动态，**主集** |
| `DYNAMIC_TYPE_DRAW` | 78 | 图文动态，**主集** |
| `"1"` | 1 | 视频评论来源，非空间动态 |

### 2.2 主集（本次任务的处理对象）

```
非转发、非评论的动态    224 条
其中有正文              224 条（100%）
作者非本人              1 条（已标记 author_is_owner=0）
```

### 2.3 启发式评分结果

| 维度 | 分布 |
|---|---|
| 情绪极性（粗判） | neutral 183 · negative 21 · positive 16 · complex 4 |
| 置信度 | high 1 · medium 17 · low 206 |

**置信度以 low 为主是预期结果**：关键词启发式对短文本不敏感。**high + medium 共 18 条，这才是实际可复读的候选量。**

---

## 三、执行中遇到的问题

### 3.1 正文位置与预期不符（影响最大）

**现象**：第一版脚本对 224 条主集提取出 **0 条正文**。

**原因**：`DYNAMIC_TYPE_WORD` 和 `DYNAMIC_TYPE_DRAW` 的 `modules.module_dynamic.desc` 字段为 **`None`**。正文实际存放在：

```
modules.module_dynamic.major.opus.summary.text
```

**这是 B 站「图文/专栏（opus）」格式与「转发」格式的结构差异。** 转发动态用 `desc.text`，图文动态用 `major.opus.summary.text`。

**修复**：写了 `extract_text()` 做四级回退：

```
desc.text
  → major.opus.summary.text
  → major.opus.title
  → major.draw.items[].description
  → major.archive.title
```

索引文件里新增 `text_source` 字段，记录每条实际命中的是哪一级，便于审计。

### 3.2 转发动态含有主人自己的文字

520 条转发里，`desc.text` 是主人写的转发评语（并非原帖内容）。这些文字确实是主人原创，但**按任务要求「只处理非转发动态」，全部排除出主集**。

**代价**：损失了 520 条主人原创的短评。**若未来需要扩充 `user_writings`，这是最容易恢复的来源。**

### 3.3 一条记录无法归属

1 条 `dynamic_type = "1"` 的记录来自视频评论而非空间动态，`record_id` 为空，`author_is_owner = 0`。已在索引中标记 `included_in_primary_set = 0`，**未删除、未补全**。

---

## 四、产出文件

| 文件 | 大小 | 含原文 | 可公开 |
|---|---|---|---|
| `data/user_bili_original_index.csv` | 约 60 KB | ❌ | ✅ |
| `data/emotion_memory_candidates.csv` | 约 20 KB | ❌ | ✅ |
| `data/task07_corpus_stats.json` | 约 1 KB | ❌ | ✅ |
| `data/personality_hypotheses_initial.md` | 约 6 KB | ❌ | ✅ |
| `data/experience_log_schema.json` | 约 7 KB | ❌ | ✅ |
| `docs/12-text-personality-memory-plan.md` | 约 10 KB | ❌ | ✅ |
| `docs/13-budget-privacy-and-safety.md` | 约 8 KB | ❌ | ✅ |
| `docs/12-task-report.md` | 本文件 | ❌ | ✅ |

**验证**：脚本内的 `_text` 字段仅在内存中存在，写盘前已剔除。两份 CSV 的列中均不含任何正文内容。

---

## 五、未完成事项及原因

| # | 未完成 | 原因 | 可行后续 |
|---|---|---|---|
| 1 | **80 条候选的实际复读** | 需要逐条阅读原文并判断，属于人工操作；且涉及私人文本，不宜由模型批量处理 | 主人自己按 rank 顺序读，或授权小批量模型分析（约 ¥0.5） |
| 2 | **`fish_experience_log` 无真实条目** | 她还没有在结构化环境下执行过可记录的活动 | 下一次运行时开始记录第一条 |
| 3 | **人格假设只有模板** | 前提是候选复读；未复读就填假设等于把推断伪装成结论 | 见 `data/personality_hypotheses_initial.md` 的复读流程 |
| 4 | **`interaction_memory` 未建索引** | 会话记录可读但未结构化，且体量大 | 需要单独设计抽取规则 |
| 5 | **`fish_diary` 未纳入统计** | 公开日记 27 KB 可读，但**私人日记 61 KB 按约定不读** | 需要主人明确授权范围 |

---

## 六、一个必须指出的结构性问题

**本阶段建立了四类材料的隔离框架，但其中三类目前是空的。**

```
user_writings       ✅ 224 条已索引
fish_diary          ⚠️ 存在，未纳入索引
interaction_memory  ⚠️ 存在，未结构化
fish_experience_log ❌ 空
```

**这意味着：现在的系统能证明「主人写过什么」，但还不能证明「她经历过什么」。**

**验收标准里那条「主人和大肥鱼的经历能够明确区分」——目前只完成了一半。** 区分得开，是因为她那边还是空的。

**填补 `fish_experience_log` 是从「描述主人」走向「她有自己轨迹」的唯一实质步骤。** 而这不需要花钱，只需要她从下一次运行开始，把自己的动作如实记下来。

---

## 七、预算结算

```
本轮花费        ¥0.00
模型调用        0 次
余额            ¥7.00（未变动）
```

**没有任何需要报告的成本超支或例外。**
