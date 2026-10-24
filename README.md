# B站个人评论风格语料库（Bili Comment Style Corpus）

> 从「采集自己的 B 站发言」到「逐行风格标签」再到「20 个视频的 A/B 盲评」的一条完整工作线。
> 本项目是为 GPT 阅读/接力准备的**可浏览档案**：保留方法、统计、标签口径、测试设计，**不在公开仓库里放原始个人语料**。

## 这条线在做什么

1. **建语料**：读取用户本人公开的空间动态与视频评论，保留原始记录、唯一 ID、来源、上下文和作者确认状态。
2. **扩样本**：从 24 条动态扩到 762 条原始记录 / 729 条去重后的独立表达，覆盖转发、原创文字、原创图文、一级评论、二级回复。
3. **对账与打标**：拆开「本轮扫描命中」与「累计存档」；为 729 条独立表达逐行打轻量标签（主题 / 意图 / 风格 / 语境置信度）。
4. **对照测试**：选 20 个视频，用同一模型、同一上下文生成 A（基础提示词）/ B（基础 + 第一版个人风格指南），盲评 X/Y，不发布。

## 关键数字

| 指标 | 数值 |
|---|---|
| 原始记录 | 762 |
| 去重后独立表达 | 729 |
| 时间跨度 | 2023-07-26 → 2026-10-21 |
| 类型 | 转发 520 · 原创文字 146 · 原创图文 78 · 一级评论 16 · 二级回复 2 |
| 作者确认率 | 100%（762/762，按 mid 精确过滤） |
| 语境 | 有标题/卡片 398 · 非占位简介 213 · 字幕片段 5 条（2 个视频）· 仅标题/卡片 183 |
| A/B 测试 | 20 个视频 · 6 类主题 · 生成 15 组 · SKIP 5 个 |

## 任务 05（本轮）

- **先读 Task 04 的实际盲评**：15 组、5 SKIP；v1 比模板好（B 赢 12/15），但 **12/15 仍然“都不行”**，“像用户”只有 1.73/5，且 B 有 5 条事实/立场问题。
- **v2 指南**：在 v1 上增加 7 条硬规则 + “像本人”写法（不写“这个视频/UP主”、不感谢/不总结/不夸 UP 主、不用大词、不会说就 SKIP）。
- **上下文审计**：**12 个全新视频**（不复用 Task 04 的 20 个）/ 34 条事实；标 `subtitle / description / title / inference`，区分“简介写了”与“视频演了”。
- **三组盲测**：A（基础）/ B（v1）/ C（v2），12 × 3 = 36 条，X/Y/Z 随机。
- **冲突处理**：Task 04 被指出的镜子 B、司凤头部姿态、19sp 音乐主题均标 `needs_review` 并排除，不擅自选一个当事实。
- **盲评结果（已填）**：B（v1）赢 6 · C（v2）赢 3 · 平 3。均值：B 像本人 1.67 / 不公式化 3.00 / 愿意发 3；C 像本人 1.33 / 有内容 3.08 / 愿意发 1。**v2 没有赢**；C 只在“有内容”上更高，事实/立场问题反而更多（3 vs 2）。
- 新视频 SKIP 0；下一步先补 #4/#9/#12 的画面与角色关系，再改 v3。

详见 [`docs/09-task05-report.md`](docs/09-task05-report.md)。

## 任务 06（探索性）

- **只比 v1 vs v2-lite**：6 个正常视频 + 2 个信息不足视频；16 次独立生成（v1 / v2-lite 各 8），执行顺序随机、每次新上下文。
- **修正 3 个上下文**：手机密码/羊村用 `user_report` + `reviewed_by_user=true`；原神 6.3 拉了完整字幕仍无法确认核心争议 → `unknown`，移出主测、作为信息不足测试。
- **v2-lite**：三条硬规则（不虚构事实/不误判身份/不编造个人经历）+ 放松机械禁令；不写 v3、不扩语料。
- **结果（已填）**：v2-lite 总分 **6/6 赢**；贴合 4.17 / 有内容 4.67 / 不公式化 4.33，事实问题 2 条；但 **“像本人” 2.00，低于 v1 的 2.33**。2 个信息不足视频 **4/4 正确 SKIP**。结论：v2-lite 改善了准确/内容，没解决“像本人”；不写 v3。样本小、探索性；盲评在时间压力下完成、标准偏宽松，只作方向性参考。
- 详见 [`docs/10-task06-report.md`](docs/10-task06-report.md)。
- **暂行指南**：[`data/style_guide_v1.1_interim.md`](data/style_guide_v1.1_interim.md)（Task 06 后整合版；**不覆盖** v1 / v2-lite 原件）。

## 任务 07（探索性）：偏好盲测 —— AI 会喜欢什么视频？

- **问题**：她的「爱看」写在配置里，而配置是主人写的，于是任何「喜欢」都可能是回声。本轮把偏好提示完全抽掉，只给标题/简介/时长，看她会不会收敛到某类内容。
- **设计**：两个候选池对冲偏差——**热门池**（算法推荐）与**冷门池**（0 播放新投稿）；20 条目 / 30 组配对（K₂₀ 三轮 1-因素分解），每项恰好 3 次出场、3 个不同对手、比较图全连通；左右位置与比较顺序随机化。
- **结果**：位置偏差 14/30（47%，未见显著）；池效应 19:11，跨池 16:8，二项检验 **p = 0.152（不显著）**；分层 4 全胜 / 6 两胜 / 6 一胜 / 4 全负。**未采用 Bradley-Terry**——完全分离结构下 MLE 发散。
- **核心发现**：**本轮测到的不是「她的偏好」**。模型在推理链中明写「作为 AI 没有个人偏好，但必须选」，且 10/30 的推理仍在使用「预测点击率」的词汇。全负 4 条中 3 条是带货广告——说明模型能识别广告感，但这不等于「不喜欢」。
- 详见 [`docs/11-preference-blind-test.md`](docs/11-preference-blind-test.md)，原始数据在 `experiments/preference-blind-test-20261024/`。

## 任务 07：文本人格与连续记忆系统（零付费原型）

- **目标转向**：从"模仿评论风格"转向"建立可追溯的连续记忆"——让过去发生的事真的影响未来的选择，而不是让日记写得更像人。
- **四类材料隔离**：`user_writings`（主人原创）/ `fish_diary`（她的日记，原样保留）/ `interaction_memory`（真实互动）/ `fish_experience_log`（她实际执行的活动）。**任何合并都会导致身份错位。**
- **阶段一（已完成，¥0）**：本地规则解析 762 条动态 → 去重 745 → 排除 520 条转发 → **224 条原创主集全部有正文**；建立索引与启发式候选清单（224 条评分，输出前 80）。
- **发现的结构坑**：`DYNAMIC_TYPE_WORD/DRAW` 的 `desc` 为 `None`，正文实际在 `major.opus.summary.text`——第一版脚本因此提取出 0 条正文。
- **未完成且必须说明的**：`fish_experience_log` **仍是空的**。这意味着系统目前能证明"主人写过什么"，但还**不能证明"她经历过什么"**——验收标准只完成了一半。
- 详见 [`docs/12-text-personality-memory-plan.md`](docs/12-text-personality-memory-plan.md)、[`docs/13-budget-privacy-and-safety.md`](docs/13-budget-privacy-and-safety.md)、[`docs/12-task-report.md`](docs/12-task-report.md)；数据在 `data/`。

## 阅读顺序（给 GPT）

1. [`transcript/conversation.md`](transcript/conversation.md) —— **这句话之后的全部对话**：任务 01→04 的用户消息原文 + 助手回复（含澄清与仓库搭建）
2. [`docs/01-overview.md`](docs/01-overview.md) —— 任务 01→04 的来龙去脉与关键决策
3. [`docs/04-quality-report.md`](docs/04-quality-report.md) —— 数据质量、对账口径、语境口径
4. [`docs/05-style-labels.md`](docs/05-style-labels.md) —— 逐行标签的字段、分布与局限
5. [`docs/06-ab-test.md`](docs/06-ab-test.md) —— Task 04 A/B 盲评设计与产出
6. [`docs/08-task05-plan.md`](docs/08-task05-plan.md) —— Task 05 计划
7. [`docs/09-task05-report.md`](docs/09-task05-report.md) —— Task 05 审计、v2、三组盲测
8. [`docs/10-task06-report.md`](docs/10-task06-report.md) —— Task 06 v2-lite、独立生成、SKIP 测试
9. [`docs/11-preference-blind-test.md`](docs/11-preference-blind-test.md) —— 偏好盲测：20 条目 / 30 组配对，热门池 vs 冷门池
10. [`docs/07-privacy-and-limits.md`](docs/07-privacy-and-limits.md) —— 哪些数据不在公开仓库、为什么

## 目录

```
transcript/
  conversation.md     这句话之后的全部对话（任务 01-04 + 回复）
docs/                 方法与报告
  briefs/             四轮任务原文（任务 01-04）
  samples/            脱敏样例（已打码）
data/
  samples/            脱敏预览
  reports/            汇总统计（无原文）
  schema.md           CSV/字段说明
  style_guide_v1.md   第一版个人风格指南（测试用）
  test_prompts.md     A/B 生成提示词（可复现）
test_results.csv      A/B 结果（评论为模型生成，不含个人原文）
blind_review.md       Task 04 X/Y 随机盲评表
blind_review_task05.md Task 05 X/Y/Z 随机盲评表
blind_review_task06.md Task 06 X/Y 随机盲评表
data/style_guide_v2.md Task 05 v2 指南
data/style_guide_v2_lite.md Task 06 v2-lite 指南
data/style_guide_v1.1_interim.md 暂行整合版（不覆盖 v1 / v2-lite）
data/task05_*.csv     审计 / 结果 / key
data/task06_*.csv     审计 / 结果 / 生成顺序 / key
docs/08-task05-plan.md / docs/09-task05-report.md
docs/10-task06-report.md
docs/11-preference-blind-test.md  偏好盲测报告
experiments/preference-blind-test-20261024/  盲测原始数据（8 份 + README）
PUSH.md               如何创建仓库、哪些不能公开
scripts/README.md     采集/构建脚本的位置与用法
```

## 重要边界

- **不发布评论**：本项目所有产出都是本地分析/测试，没有自动发过任何评论。
- **不推断人格**：标签只描述文本的可复核特征，不推断政治立场、心理状态或人格。
- **原始个人语料不公开**：`raw.jsonl`、`comments.csv`、`context_review.csv`、`style_labels.csv` 含用户历史原文与敏感自述，默认被 `.gitignore` 排除。要让 GPT 读全文，请用**私有仓库**并把数据加进去（见 `docs/07-privacy-and-limits.md`）。
- **凭证不入库**：cookie/SESSDATA 只在本地 `~/.bili-ai/credentials.json`，仓库里没有任何凭证。
