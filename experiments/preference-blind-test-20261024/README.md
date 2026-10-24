# 偏好盲测 · 原始数据（2026-10-24）

本目录是该轮实验的**全部原始记录**，用于复核 `docs/11-preference-blind-test.md` 的每一项数字。

## 文件说明

| 文件 | 内容 | 是否含决策时不可见的信息 |
|---|---|---|
| `pool_rank.json` | 热门池快照（排行榜 + 热门，132 条去重） | — |
| `pool_cold.json` | 冷门池快照（8 个分区最新投稿，160 条） | — |
| `batch.json` | 参选的 20 条 | **是**（含分区、UP 主、播放量，仅供事后审计） |
| `pairs.json` | 30 组配对（左右位置、轮次、是否跨池） | — |
| `provenance.json` | 溯源：各阶段条数、排除项、接口地址、过滤区间 | — |
| `design_check.json` | 设计验证：出现次数、对手分布、连通性 | — |
| `picks_v2.jsonl` | **正式结果**，30 条有效记录 | 含完整提示词、SHA256、参数、耗时、token 用量 |
| `analysis.json` | 分析输出 | — |

## 复现方式

```bash
# 1) 建池 + 配对 + 验证（需要可访问 B 站公开接口）
python exp_build.py

# 2) 跑 30 组二选一（需要 DEEPSEEK_API_KEY）
python run_pairs_v2.py <运行目录>

# 3) 分析
python analyze.py <运行目录>
```

三个脚本位于 `default-workspace`，不在本仓库内（它们依赖本地凭证路径）。

## 关键参数

```json
{
  "model": "deepseek-flash",
  "temperature": 0,
  "max_tokens": 1024,
  "endpoint": "https://api.deepseek.com/v1/chat/completions",
  "system_prompt": "你在做一组二选一。\n重要：不要预测哪条更容易火、哪条播放量更高、别人会点哪条。\n只回答：你自己现在更想点开哪一个。\n只输出一个字母 A 或 B，不要任何解释、标点或空格。"
}
```

## 注意事项

- **视频标题与 BV 号均为 B 站公开内容**，本实验未采集任何用户身份信息。
- `picks_v2.jsonl` 中 `reasoning_aux` 字段是模型的内部推理链，**仅作辅助材料，不参与任何评分**。
- 本轮为**探索性测试**，30 组样本不足以支撑任何强结论。
- 首轮失败的记录（`max_tokens=8` 导致输出为空）保留在原始运行目录的 `picks.jsonl` 中，未纳入本仓库。
