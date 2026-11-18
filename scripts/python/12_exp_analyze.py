# -*- coding: utf-8 -*-
# Task 07 偏好盲测：位置偏差/池效应/分层
# 从工作区整理入库；硬编码路径已改为环境变量。
"""
analyze.py —— 成对比较分析
  1. Bradley-Terry 强度估计
  2. 位置偏差检验（左/右被选中的比例）
  3. 池效应（热门 vs 冷门 的胜率）
  4. 置信度：无法稳健区分的标记为不确定
"""

import os

REPO = os.environ.get("BILI_REPO", os.path.expanduser("~/bili-comment-style-corpus"))
CORPUS = os.environ.get("BILI_CORPUS", os.path.expanduser("~/bili-corpus"))

import json, os, sys, math
from collections import defaultdict, Counter
sys.stdout.reconfigure(encoding="utf-8")

RUN = sys.argv[1]
batch = json.load(open(os.path.join(RUN, "batch.json"), encoding="utf-8"))
picks = [json.loads(l) for l in open(os.path.join(RUN, "picks_v2.jsonl"), encoding="utf-8") if l.strip()]
valid = [p for p in picks if p["valid"]]
print(f"记录 {len(picks)} 条，有效 {len(valid)} 条")

n = len(batch)
wins = Counter()
comp = Counter()
pair_count = Counter()
left_wins = 0
cross = {"cross_hot": 0, "cross_cold": 0, "same": 0}
pool_wins = Counter()
pool_appear = Counter()

for p in valid:
    a, b = p["chosen_idx"], (p["right_idx"] if p["chosen_idx"] == p["left_idx"] else p["left_idx"])
    wins[a] += 1
    comp[a] += 1; comp[b] += 1
    pair_count[(min(a,b), max(a,b))] += 1
    if p["chosen_idx"] == p["left_idx"]:
        left_wins += 1
    pool_wins[batch[a]["pool"]] += 1
    pool_appear[batch[p["left_idx"]]["pool"]] += 1
    pool_appear[batch[p["right_idx"]]["pool"]] += 1
    if p["cross_pool"]:
        cross["cross_hot" if batch[a]["pool"] == "rank" else "cross_cold"] += 1
    else:
        cross["same"] += 1

# ── 1) 位置偏差 ──
nb = len(valid)
print("\n" + "=" * 74)
print("① 位置偏差")
print("=" * 74)
print(f"  左侧(A)被选中 {left_wins}/{nb} = {left_wins/nb*100:.0f}%")
# 二项检验的粗判：期望 50%，±1.96*sqrt(n*0.25)
se = math.sqrt(nb * 0.25)
lo, hi = nb/2 - 1.96*se, nb/2 + 1.96*se
print(f"  95% 参考区间 [{lo:.1f}, {hi:.1f}]  ->  "
      f"{'✅ 未见显著偏差' if lo <= left_wins <= hi else '⚠️ 可能有位置偏差'}")
print(f"  注意：即使比例正常，也不能断言位置偏差已被消除（样本太小）")

# ── 2) 池效应 ──
print("\n" + "=" * 74)
print("② 池效应（热门 vs 冷门）")
print("=" * 74)
for pool in ("rank", "cold"):
    w, ap = pool_wins[pool], pool_appear[pool]
    print(f"  {pool:<6} 被选 {w}/{ap} 次出场 = {w/ap*100 if ap else 0:.0f}% 胜率")
print(f"  跨池比较中：热门胜 {cross['cross_hot']}，冷门胜 {cross['cross_cold']}，同池 {cross['same']}")

# ── 3) Bradley-Terry（MM 算法）──
print("\n" + "=" * 74)
print("③ Bradley-Terry 强度")
print("=" * 74)
# ── 3) 胜场与分层（BT 在 3 次比较/项 上会发散到无穷，不适合）──
print("\n" + "=" * 74)
print("③ 胜场与分层")
print("=" * 74)
print("  ⚠️ 每项仅 3 次比较；另有 3 项全胜、4 项全负，Bradley-Terry 的 MLE 在")
print("     这种完全分离的结构下趋于无穷，故不采用 BT，改报原始胜场与分层。")
print()
tiers = {3: "全胜", 2: "两胜", 1: "一胜", 0: "全负"}
order = sorted(range(n), key=lambda i: (-wins[i], batch[i]["pool"], batch[i]["title"]))
for i in order:
    it = batch[i]
    print(f"  {tiers[wins[i]]:<4} [{it['pool']:<4}] {it['title'][:46]}")
print()
print("  同层内部顺序不可区分（样本不足）")

# ── 4) 池效应的显著性 ──
def binom_two_tailed(k, nn, p=0.5):
    from math import comb
    def pmf(x): return comb(nn, x) * (p ** x) * ((1 - p) ** (nn - x))
    obs = pmf(k)
    return sum(pmf(x) for x in range(nn + 1) if pmf(x) <= obs + 1e-12)

cross_n = cross["cross_hot"] + cross["cross_cold"]
if cross_n:
    pval = binom_two_tailed(cross["cross_hot"], cross_n)
    print()
    print("=" * 74)
    print("④ 池效应显著性（跨池比较）")
    print("=" * 74)
    print(f"  跨池 {cross_n} 组：热门胜 {cross['cross_hot']}，冷门胜 {cross['cross_cold']}")
    print(f"  二项检验（p=0.5）双尾 p = {pval:.3f}")
    print(f"  -> {'⚠️ 边缘显著，提示可能有池偏好' if pval < 0.10 else '✅ 不显著，无证据支持池偏好'}")
    print(f"  注意：30 组样本下即使 p<0.10 也只是提示，不能当结论")

out = {
    "n_pairs_total": len(picks), "n_pairs_valid": nb,
    "left_chosen": left_wins,
    "position_95pct_interval": [round(lo,1), round(hi,1)],
    "position_bias_note": "比例正常不等于位置偏差已消除；样本小",
    "pool_win_rate": {p: {"wins": pool_wins[p], "appearances": pool_appear[p]} for p in ("rank","cold")},
    "cross_pool": cross,
    "bt_scores": {batch[i]["bvid"]: round(s[i], 4) for i in range(n)},
    "ranking": [{"rank": r, "bvid": batch[i]["bvid"], "pool": batch[i]["pool"],
                 "title": batch[i]["title"], "score": round(s[i],4),
                 "wins": wins[i], "comps": comp[i]} for r, i in enumerate(rank, 1)],
    "reliability_note": "每项仅 3 次比较，BT 排序为探索性结果，不可据此下强结论",
}
json.dump(out, open(os.path.join(RUN, "analysis.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"\n✅ -> {os.path.join(RUN, 'analysis.json')}")
