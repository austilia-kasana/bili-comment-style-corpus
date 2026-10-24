# Task 08 · 本轮操作报告

**执行时间**：2026-10-24
**花费**：**¥0.00**（零模型调用）
**状态**：全部本地交付物完成；模型分析未执行（无授权）

---

## 一、完成的六份交付物

| # | 文件 | 大小 | 内容 |
|---|---|---|---|
| 1 | `docs/14-batch-processing-plan.md` | 8,112 B | 分批机制、断点续跑、增量更新、成本估算 |
| 2 | `data/text_batch_manifest.csv` | 12,922 B | **脱敏版**批次清单，223 行 / 23 批 |
| 3 | `data/text_analysis_schema.json` | 7,815 B | 单条归纳结构，10 字段 + 条件校验 |
| 4 | `data/text_analysis_template.jsonl` | 2,603 B | 3 条模板（pending / analyzed / skipped） |
| 5 | `docs/15-public-index-privacy-audit.md` | 6,421 B | 逐列风险审计 + 脱敏方案 |
| 6 | `docs/14-task-report.md` | 本文件 | — |

**另有 1 份新增公开文件**：`data/user_bili_original_index.public.csv`（50,508 B，脱敏索引）

---

## 二、批次清单

```
主集          223 条（Task 07 的 224 条，按 sha256 去重后 223）
每批          10 条
批次数        23（B001~B023，末批 3 条）
排序          按发布时间升序
时间跨度      2023-07-26 → 2026-10-04
全部 processed = 0（尚未分析）
```

### 2.1 两份清单

| 文件 | 位置 | 是否含真实 ID |
|---|---|---|
| `local/text_batch_manifest.csv` | 本地（gitignore） | ✅ 含 `record_id` / `pub_iso` / `raw_line` / `sha256_16` |
| `data/text_batch_manifest.csv` | 公开 | ❌ 仅 `record_key` / `month` / `len_bucket` / 状态 |

**公开版验证：含原始 ID 的单元格 = 0。**

### 2.2 只读定位符

完整清单里每条记录了 `raw_path` + `raw_line`（`raw.jsonl` 的 1-based 行号）。

**原文永远只有一份**，清单只记「在第几行」，不复制内容。

---

## 三、结构设计

### 3.1 十个字段

```
source_id / topic / emotion_signals / salience / value_tension /
life_event / interpretation / counterevidence / confidence / review_status
```

**三类信息强制分离：**

```
原文事实      life_event.described + basis="stated"
作者明确观点  topic.basis="explicit_in_text"
模型推断      interpretation.kind="inference"
```

### 3.2 允许未知

`valence` 默认 `unknown`，`salience.importance` 默认 `unknown`。

**并加了条件校验**：`valence = unknown` 时 `basis` 不得为 `explicit`——防止「声称原文明确说了，但归类为未知」的自相矛盾。

### 3.3 必备的相反证据

`counterevidence` 是 `minItems: 1` 的必填数组。确实没有时写「未搜寻到」，**不允许留空**。

---

## 四、隐私审计结果

### 4.1 核心发现

**`record_id` 是高风险列。**

```
https://t.bilibili.com/<record_id>
https://api.bilibili.com/x/polymer/web-dynamic/v1/detail?id=<record_id>
```

**745 个 ID = 745 个直达链接。** Task 07 推上去的那份索引，等于把 745 篇原文的地址列成了表。

**同时 `pub_iso`（秒级时间）也属中高风险**——连续序列可推断作息与情绪周期。

### 4.2 已执行的处置

| 动作 | 结果 |
|---|---|
| 完整索引移入本地 | `local/user_bili_original_index.full.csv`（102,656 B） |
| 生成脱敏版 | `data/user_bili_original_index.public.csv`（745 行） |
| `record_id` → `record_key` | `sha256(salt + id)[:12]`，salt 仅存本地 |
| `pub_iso` → `month` | 只留年月 |
| `text_len` → `len_bucket` | 五档分桶 |
| 删除 `pub_ts` / `collected_at` | — |

**验证：**

```
含原始 ID 的单元格            0
含秒级时间格式的单元格        0
```

### 4.3 ⚠️ 残留缺口

**git 历史中仍保留旧版。**

```
commit 0b53940 → data/user_bili_original_index.csv
```

**后续提交删掉文件，不会从历史里抹去。** 彻底清除需重写历史 + 强推，代价是全部分叉。

**是否执行，等主人决定。**

---

## 五、仍需未来模型调用的工作

| # | 工作 | 为什么本地做不了 | 预计成本 |
|---|---|---|---|
| 1 | **223 条原文的实际归纳** | 需要语义理解，规则做不到 | ¥0.07~0.22（见下表） |
| 2 | 主题聚类 | 同上 | 含在 1 内 |
| 3 | 情绪归类 | 关键词只能粗判，且已证明不可靠（Task 07 中 206/224 为 low） | 含在 1 内 |
| 4 | 价值冲突识别 | 需要理解语境 | 含在 1 内 |

**以下仍不需要模型：**

- 批次切分 ✅ 已完成
- 断点续跑 ✅ 机制已就绪
- 增量更新 ✅ 机制已就绪
- 索引与审计 ✅ 已完成

---

## 六、全量处理成本估算

### 6.1 数据量

```
223 条 × 约 150 字符 = 约 33,000 字符
中文约 1 字符 ≈ 1 token → 输入约 33K token
```

### 6.2 三方案

| 方案 | 输入 | 输出 | 合计 |
|---|---|---|---|
| **A. 非推理模型，一次全量** | 33K × ¥0.5/M = ¥0.017 | 33K × ¥1.5/M = ¥0.050 | **约 ¥0.07** |
| **B. 推理模型，一次全量** | 33K × ¥0.5/M = ¥0.017 | 134K（含推理链）× ¥1.5/M = ¥0.20 | **约 ¥0.22** |
| **C. 23 批分别调用** | 44K（含重复提示词） | 134K | **约 ¥0.22** |

**按单价：输入 ¥0.5/M，输出 ¥1.5/M（DeepSeek 系公开价目，实际以账单为准）**

### 6.3 结论

**¥7 余额足够跑 30 遍全量。**

**但真正的限制不是钱：**

```
一次跑完 223 条 → 单条质量必然下降
产出后仍需人复核 → 那个成本比 token 贵得多
任务书要求先报告成本、等授权 → 流程上必须先授权
```

**建议：先试跑 B001（10 条，约 ¥0.01），看产出质量再决定是否全量。**

---

## 七、本阶段明确未做的事

```
✗ 任何模型调用（0 次）
✗ 任何原文分析
✗ 任何情绪归类
✗ 任何主题提取
✗ 读取 ~/.dsh/whale-diary-private.md（一个字没碰）
✗ 把主人经历改写为大肥鱼经历
```

---

## 八、预算结算

```
本轮花费        ¥0.00
模型调用        0 次
余额            ¥7.00（未变动）
```

---

## 九、一项需要主人拍板的事

**git 历史里的旧索引要不要清？**

| 选项 | 代价 | 收益 |
|---|---|---|
| **保留** | 无 | 旧版可通过 `git log --all -- data/user_bili_original_index.csv` 取回 |
| **重写历史** | commit hash 全变，已克隆的副本分叉 | 旧版彻底消失 |

**这不是技术问题，是取舍问题。** 审计报告只负责指出，不替主人决定。
