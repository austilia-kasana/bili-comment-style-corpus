# 15 · 公开索引隐私审计报告

**审计日期**：2026-10-24
**审计对象**：`data/user_bili_original_index.csv`（Task 07 已推送到公开仓库）
**结论**：**存在可逆向关联风险，已完成脱敏替换；但 git 历史中仍残留旧版**

---

## 一、为什么要审这个

Task 08 明确要求：

> 不把未经脱敏的动态 ID、精确发布时间或可逆向关联的索引默认视为安全。对现有公开索引进行隐私风险审查，提出脱敏方案。

**Task 07 我推上去的那份索引，正是这三样的集合。**

---

## 二、审计对象

```
文件      data/user_bili_original_index.csv
行数      745
列数      13
内容      record_id / source / dynamic_type / is_forward / has_orig /
          pub_ts / pub_iso / text_len / has_text / text_source /
          author_is_owner / collected_at / included_in_primary_set
```

**其中不含任何原文。** 但「不含原文」不等于「安全」。

---

## 三、逐列风险评级

| 列 | 风险 | 理由 |
|---|---|---|
| **`record_id`** | **高** | B 站动态 ID 是**全局唯一且可解析**的。拼接 `https://t.bilibili.com/<id>` 或调用 `https://api.bilibili.com/x/polymer/web-dynamic/v1/detail?id=<id>` 就能直接打开原帖全文 |
| **`pub_iso`** | **中高** | 秒级时间戳。745 条的连续序列可推断作息、活跃时段、情绪周期，且能与其他平台数据交叉比对 |
| **`pub_ts`** | **中高** | 同上，epoch 形式 |
| `text_len` | 低 | 单独看信息量小，但与精确时间组合后可形成指纹 |
| `collected_at` | 中低 | 抓取时间，可暴露工具与操作节奏 |
| `dynamic_type` | 低 | 类型标签 |
| `text_source` | 低 | 正文所在字段名 |
| `is_forward` / `has_orig` / `has_text` / `author_is_owner` / `included_in_primary_set` / `source` | 低 | 布尔标记或无识别性标签 |

### 3.1 核心问题

**`record_id` 单独一列就足以还原全部内容。**

**这不是「可能泄漏」，是「设计上就指向原文」。** 745 个 ID 等于 745 个直达链接。

### 3.2 一个缓解因素

**这些动态本身在 B 站是公开的**——我们正是从公开空间页采集的。

**所以风险不是「暴露了本来私密的内容」，而是：**

```
把散落在 B 站的内容，聚合成一份机器可读的索引
→ 可被批量枚举、统计、关联
→ 且明确标注"这 745 条属于同一个人"
```

**聚合才是问题，不是单条内容。**

---

## 四、已执行的处置

### 4.1 完整索引移入本地

```
data/user_bili_original_index.csv  →  local/user_bili_original_index.full.csv
```

**`local/` 已加入 `.gitignore`，不入库。**

### 4.2 生成脱敏版

```
data/user_bili_original_index.public.csv   （745 行）
```

| 新列 | 来自 | 处理 |
|---|---|---|
| `record_key` | `record_id` | `sha256(salt + "|" + id)[:12]` |
| `month` | `pub_iso` | **截断到年月**（`2024-03`），丢弃日与时分秒 |
| `dyn_type` | `dynamic_type` | 原样 |
| `len_bucket` | `text_len` | **分桶**：`1-29` / `30-79` / `80-149` / `150-299` / `300+` |
| `has_text` | 原样 | |
| `text_source` | 原样 | |
| `author_is_owner` | 原样 | |
| `included_in_primary_set` | 原样 | |

**已删除的列**：`record_id`、`pub_ts`、`pub_iso`、`collected_at`。

**salt 保存在 `local/.desensitize_salt`（64 位十六进制），不入库、不提交。** 没有 salt 无法从 `record_key` 反查出原 ID。

### 4.3 验证

```
脱敏版行数                              745
含原始 record_id 值的单元格              0
含 yyyy-mm-ddThh:mm:ss 格式的单元格      0
record_key 格式                         12 位小写十六进制
```

**✅ 全部通过。**

### 4.4 批次清单同步处理

| 文件 | 位置 | 内容 |
|---|---|---|
| `local/text_batch_manifest.csv` | 本地 | 223 行，含 `record_id` / `pub_iso` / `raw_line` / `sha256_16` |
| `data/text_batch_manifest.csv` | 公开 | 223 行，仅 `record_key` / `month` / `len_bucket` / 处理状态 |

**验证：公开版含原始 ID 的单元格 = 0。**

---

## 五、残留风险

### 5.1 ⚠️ git 历史中仍保留旧版

**这是本次处置唯一的实质缺口。**

```
commit 0b53940  （Task 07）
  └─ data/user_bili_original_index.csv  ← 含 745 个真实 record_id
```

**后续提交删除文件，不会从历史中抹去它。** 任何人克隆仓库并执行 `git log --all -- data/user_bili_original_index.csv`，仍能取回旧版。

**彻底清除需要重写历史 + 强推。** 代价：

```
✓ 旧版从所有分支和历史中消失
✗ 所有已克隆的副本会分叉，需要重新克隆
✗ commit hash 全部改变
```

### 5.1.1 决策记录（2026-10-24）

**主人决定：保留 git 历史，不重写。**

理由（主人原话）：

> git旧索引保留吧，本来就是小透明，泄露的也不是太重要的信息应该没人在乎。

**因此本项按「已知并接受」处理，不再作为待办。**

**接受的风险：**
- 任何克隆仓库的人可通过 `git log --all -- data/user_bili_original_index.csv` 取回含 745 个真实 `record_id` 的旧版
- 该旧版可逐条还原为 `t.bilibili.com/<id>` 直达链接

**不接受的后果（即如果未来情况变化，需要重新评估）：**
- 若仓库转为受关注状态，或采集范围扩大到非公开内容，此决定需要复审

**复审触发条件：**
```
① 仓库获得外部关注（star / fork / 被引用）
② 采集范围扩展到非公开发布的内容
③ 账号身份被公开关联到仓库
```

**记录人**：执行助手
**记录日期**：2026-10-24

### 5.2 其他残留

| 风险 | 程度 | 说明 |
|---|---|---|
| 月份 + 分桶 + 类型组合 | 低 | 极端情况下可缩小范围，但无法定位到具体条目 |
| `local/` 目录 | 中 | 若整机备份或误传到网盘，等于泄漏完整索引 |
| salt 文件 | 中 | 同 `local/`，必须与索引分开保管 |

### 5.3 已知的非风险

- **不含原文**：745 行里没有任何一条正文
- **不含 mid**：索引里没有账号 UID（虽然 README 的上下文能推知是谁）
- **不含凭证**：cookie / SESSDATA 从未入库

---

## 六、后续规则

**从本阶段起，公开仓库只放以下四类：**

```
1. 代码（脚本）
2. 结构（schema / 模板 / 清单表头）
3. 统计（数量、分布、分桶后的聚合值）
4. 不含私人原文的说明文档
```

**以下三类一律留本地：**

```
1. 原始文字
2. 完整索引（含真实 ID 与秒级时间）
3. 可反查的映射（salt、行号表）
```

**新增数据文件前必须回答三个问题：**

```
Q1  这里面有没有任何一条能指向具体某篇原文？
Q2  有没有精确到分钟以下的时间信息？
Q3  单独拿到这份文件，能否反查出「某人说过什么」？
```

**任何一题答「能」，就不进公开仓库。**

---

## 七、审计结论

| 项 | 状态 |
|---|---|
| 已完成脱敏替换 | ✅ |
| 公开版验证无泄漏 | ✅ |
| 完整索引转本地 | ✅ |
| `local/` 已 gitignore | ✅ |
| **git 历史清除** | ❌ **未做，需主人决定** |
| 批次清单同步脱敏 | ✅ |

**一句话：新的公开文件是安全的，但旧的还躺在历史里。**
