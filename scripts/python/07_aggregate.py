# -*- coding: utf-8 -*-
# Task 09：聚合统计 + 与启发式对比
# 从工作区整理入库；硬编码路径已改为环境变量。
"""聚合分析：只产出统计，不含原文片段"""

import os

REPO = os.environ.get("BILI_REPO", os.path.expanduser("~/bili-comment-style-corpus"))
CORPUS = os.environ.get("BILI_CORPUS", os.path.expanduser("~/bili-corpus"))

import json, os, sys, csv
from collections import Counter, defaultdict
sys.stdout.reconfigure(encoding="utf-8")

LOCAL = os.path.join(REPO, "local")
OUT = os.path.join(LOCAL, "text_analysis.jsonl")

rows = [json.loads(l) for l in open(OUT, encoding="utf-8") if l.strip()]
print(f"已分析记录: {len(rows)}")

# ── 1. 置信度 / 情绪极性 ──
print("\n=== 1. 置信度与情绪 ===")
conf = Counter(r.get("confidence") for r in rows)
val = Counter((r.get("emotion_signals") or {}).get("valence") for r in rows)
basis = Counter((r.get("emotion_signals") or {}).get("basis") for r in rows)
inten = Counter((r.get("emotion_signals") or {}).get("intensity") for r in rows)
print(f"  置信度: {dict(conf)}")
print(f"  极性:   {dict(val)}")
print(f"  依据:   {dict(basis)}")
print(f"  强度:   {dict(inten)}")

n = len(rows)
unk = val.get("unknown", 0)
print(f"  unknown 占比: {unk}/{n} = {unk/n*100:.1f}%")

# ── 2. 主题 ──
print("\n=== 2. 主题分布 ===")
tops = Counter()
tbasis = Counter()
nulltopic = 0
for r in rows:
    t = r.get("topic") or {}
    p = t.get("primary")
    tbasis[t.get("basis")] += 1
    if p is None:
        nulltopic += 1
    else:
        tops[p] += 1
print(f"  有主题: {n-nulltopic}/{n}   无主题(null): {nulltopic}")
print(f"  主题依据: {dict(tbasis)}")
print("  高频主题（模型生成的标签，非原文）:")
for k, v in tops.most_common(20):
    print(f"    {v:>3}  {k[:36]}")

# ── 3. 情绪标签 ──
print("\n=== 3. 情绪标签 ===")
labels = Counter()
nlab = 0
for r in rows:
    ls = (r.get("emotion_signals") or {}).get("labels") or []
    if ls:
        nlab += 1
    for l in ls:
        labels[l] += 1
print(f"  有标签: {nlab}/{n}")
for k, v in labels.most_common(15):
    print(f"    {v:>3}  {k}")

# ── 4. 重要度 / 事件 / 价值冲突 ──
print("\n=== 4. 重要度与结构 ===")
imp = Counter((r.get("salience") or {}).get("importance") for r in rows)
reasons = Counter()
for r in rows:
    for x in ((r.get("salience") or {}).get("reasons") or []):
        reasons[x] += 1
print(f"  重要度: {dict(imp)}")
print(f"  依据码: {dict(reasons)}")

le = sum(1 for r in rows if (r.get("life_event") or {}).get("described"))
vt = sum(1 for r in rows if (r.get("value_tension") or {}).get("present"))
print(f"  描述了事件: {le}/{n} = {le/n*100:.1f}%")
print(f"  有价值观冲突: {vt}/{n} = {vt/n*100:.1f}%")

ik = Counter((r.get("interpretation") or {}).get("kind") for r in rows)
print(f"  解释类型: {dict(ik)}")

# ── 5. 相反证据 ──
ce = [len(r.get("counterevidence") or []) for r in rows]
print(f"\n=== 5. 相反证据 ===")
print(f"  平均条数: {sum(ce)/len(ce):.2f}  最少 {min(ce)}  最多 {max(ce)}")
print(f"  空值: {sum(1 for x in ce if x == 0)}")

# ── 6. 与启发式对比 ──
print("\n=== 6. 与关键词启发式对比 ===")
hist = {}
cand = os.path.join(REPO, "data", "emotion_memory_candidates.csv")
if os.path.exists(cand):
    hrows = list(csv.DictReader(open(cand, encoding="utf-8-sig")))
    for h in hrows:
        hist[h["record_id"]] = h["valence_guess"]
    # 只比两边都有的
    both = []
    for r in rows:
        sid = r["source_id"]
        if sid in hist:
            mv = (r.get("emotion_signals") or {}).get("valence")
            both.append((hist[sid], mv))
    print(f"  可对比条目: {len(both)}")
    if both:
        agree = sum(1 for a, b in both if a == b)
        print(f"  完全一致: {agree}/{len(both)} = {agree/len(both)*100:.1f}%")
        # 交叉表（只看非 unknown）
        cross = Counter()
        for a, b in both:
            cross[(a, b)] += 1
        print("  交叉表（启发式 → 模型）:")
        for (a, b), c in sorted(cross.items(), key=lambda x: -x[1])[:12]:
            print(f"    {a:<9} → {b:<9} {c}")

# ── 输出 JSON 摘要（不含原文片段）──
summary = {
    "total_records": n,
    "confidence": dict(conf),
    "valence": dict(val),
    "valence_basis": dict(basis),
    "intensity": dict(inten),
    "unknown_rate": round(unk/n, 4),
    "topics": {"with_topic": n-nulltopic, "null": nulltopic, "basis": dict(tbasis),
               "top20": [{"topic": k, "count": v} for k, v in tops.most_common(20)]},
    "emotion_labels": dict(labels.most_common(20)),
    "salience": {"importance": dict(imp), "reasons": dict(reasons)},
    "life_event_described": le,
    "value_tension_present": vt,
    "interpretation_kind": dict(ik),
    "counterevidence": {"avg": round(sum(ce)/len(ce), 2), "min": min(ce), "max": max(ce)},
}
if os.path.exists(cand):
    summary["vs_heuristic"] = {"comparable": len(both), "agreement": agree if both else 0}
json.dump(summary, open(os.path.join(LOCAL, "analysis_summary.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print(f"\n摘要 -> {os.path.join(LOCAL, 'analysis_summary.json')}")
print("（摘要不含任何原文片段）")
