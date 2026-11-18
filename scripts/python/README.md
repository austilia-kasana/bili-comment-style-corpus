# scripts/python —— Task 07~09 的可执行管线

这 12 个脚本是 Task 07（记忆系统）、Task 08（分批）、Task 09（模型分析）**实际跑过的那一版**。
它们原先散落在工作区、没有入库；2026-11-18 整理进来，同时把硬编码路径改成环境变量。

> `scripts/` 根目录下的 `.mjs` 是 Task 01~06（语料采集与 A/B 测试）用的 Node 脚本。
> 两套脚本语言不同、用途不同，不要混着看。

---

## 零、前置条件

```bash
# 1) 原始语料（不在仓库里，需自行准备）
#    结构见 docs/02-data-sources.md
export BILI_CORPUS=~/bili-corpus        # 内含 data/raw.jsonl

# 2) 仓库路径（默认 ~/bili-comment-style-corpus）
export BILI_REPO=~/bili-comment-style-corpus

# 3) 只有 05/06 需要模型凭据
#    ~/.dsh/.credentials.yaml 里要有 DEEPSEEK_API_KEY
```

**Windows PowerShell 写法：**

```powershell
$env:BILI_CORPUS = "C:\path\to\bili-corpus"
$env:BILI_REPO   = "C:\path\to\bili-comment-style-corpus"
```

---

## 一、管线总览

```
raw.jsonl（762 条动态）
    │
    ├─ 01_build_index.py ──────► data/user_bili_original_index.csv   （745 行，不含原文）
    │                      └──► data/emotion_memory_candidates.csv   （80 条，仅评分）
    │
    ├─ 02_privacy_audit.py ────► data/user_bili_original_index.public.csv（脱敏版）
    │                      └──► local/user_bili_original_index.full.csv （完整版留本地）
    │
    ├─ 04_build_batches.py ────► local/text_batch_manifest.csv       （223 行，含行号）
    │
    ├─ 03_public_manifest.py ──► data/text_batch_manifest.csv        （脱敏版）
    │
    ├─ 05_run_analysis.py ─────► local/text_analysis.jsonl           （逐条模型分析）
    │   └─ 06_retry_one.py ────► 单条补跑（JSON 解析失败时）
    │
    └─ 07_aggregate.py ────────► local/analysis_summary.json         （统计）
                             └──► data/analysis_summary.json          （脱敏后公开）
```

**另一条线（Task 07 偏好盲测）：**

```
10_exp_build_pairs.py ──► runs/<ts>/pairs.json + batch.json + provenance.json
11_exp_run_pairs.py   ──► runs/<ts>/picks_v2.jsonl
12_exp_analyze.py     ──► runs/<ts>/analysis.json
```

**fish 侧（与上面的语料管线独立）：**

```
08_index_fish_diary.py ──► local/fish_diary_index.json   （只含日期/字数/校验值）
09_log_experience.py   ──► local/fish_experience_log.jsonl（可核验经历）
```

---

## 二、每个脚本干什么

| # | 脚本 | 输入 | 输出 | 调模型 |
|---|---|---|---|---|
| 01 | `01_build_index.py` | `raw.jsonl` | 索引 + 启发式候选 | ❌ |
| 02 | `02_privacy_audit.py` | 完整索引 | 脱敏索引 | ❌ |
| 03 | `03_public_manifest.py` | 完整清单 | 脱敏清单 | ❌ |
| 04 | `04_build_batches.py` | `raw.jsonl` | 批次清单 + 行号定位 | ❌ |
| 05 | `05_run_analysis.py` | 批次清单 + 原文 | `text_analysis.jsonl` | ✅ |
| 06 | `06_retry_one.py` | 单条 record_id | 补一行 | ✅ |
| 07 | `07_aggregate.py` | `text_analysis.jsonl` | 统计摘要 | ❌ |
| 08 | `08_index_fish_diary.py` | 私人日记 | 结构索引 | ❌ |
| 09 | `09_log_experience.py` | 产出文件 | 经历日志 | ❌ |
| 10 | `10_exp_build_pairs.py` | B 站公开接口 | 配对 + 验证 | ❌ |
| 11 | `11_exp_run_pairs.py` | 配对文件 | 30 组选择 | ✅ |
| 12 | `12_exp_analyze.py` | 选择结果 | 位置偏差/池效应 | ❌ |

---

## 三、常用的三条命令

```bash
# 全量重建索引（零成本）
python 01_build_index.py

# 切批（零成本）
python 04_build_batches.py

# 跑一批分析（有成本，约 ¥0.02/批）
python 05_run_analysis.py B001

# 聚合（零成本）
python 07_aggregate.py
```

---

## 四、已知缺陷（写在代码里的债）

这批脚本是**边做边改出来的**，有以下已知问题：

### 4.1 `05_run_analysis.py` 不增量写盘

它把整批结果放在内存里，**全部跑完才一次性写**。中途崩溃会丢掉整批进度。

**Task 09 实际就是这么跑的**——22 分钟里看不到进度，只能等。

**修法**：每处理完一条就 `f.write(...)` + `f.flush()`。

### 4.2 `05_run_analysis.py` 按 `todo` 全量处理，不跳过已完成

它对传入的每一批都重新分析，**不检查 `processed` 标记**。重复运行会产生重复条目。

**Task 09 补跑时就是因为这个，改用了 `06_retry_one.py` 而不是重跑 B008。**

**修法**：开头读 `text_analysis.jsonl` 已有的 `source_id` 集合，跳过。

### 4.3 `05_run_analysis.py` 输出 token 消耗偏高

`max_tokens=4096`，而 `deepseek-flash` 是推理模型，实际输出 236,918 token / 223 条 ≈ **1,062 token/条**，其中大部分是推理链。

**成本 ¥0.42 里，推理 token 占大头。**

**修法**：如果只要结论不要推理，换非推理模型，成本能降一个数量级。

### 4.4 `01_build_index.py` 的启发式已被证伪

它的关键词打分与模型结果**只有 20% 一致**（见 `docs/18`）。

**这个脚本仍保留**，因为：① 它是零成本的初筛；② 它的失败本身就是 Task 09 的对照基线。

**但不能再用它的 `valence_guess` 当结论。**

### 4.5 `10~12` 的实验设计有已知问题

- `topic` 字段是自由字符串，**无法聚合**（详见 `docs/18` §4.1）
- 情绪枚举不够用，`other` 出现 87 次（§4.2）
- 12 号脚本的 Bradley-Terry 在完全分离下会发散，**已改为报分层**

---

## 五、代码风格说明

**这批脚本不追求工程规范。** 它们是研究脚本：

```
✅ 单文件可跑，无外部依赖（除 sys/urllib/json 等标准库）
✅ 输出即写盘，不做中间态
✅ 失败就打印原因，不静默
❌ 没有单元测试
❌ 没有统一日志
❌ 函数粒度粗，主流程写在模块级
```

**如果要把它们工程化，第一优先级是 §4.1 和 §4.2**——这两个真会丢数据。
