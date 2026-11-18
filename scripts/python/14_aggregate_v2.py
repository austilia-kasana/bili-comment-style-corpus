# -*- coding: utf-8 -*-
"""
Task 10：v2 结果聚合 + 与 v1 对比验证
检查 GPT 要求的四件事：
  ① unknown 占比是否下降（v1 = 26.5%）
  ② 新标签有没有被滥用（单个 > 30%）
  ③ category 分布是否合理
  ④ detail 是否都在 40 字内
输出：local/analysis_summary.v2.json
"""
import os
import json, sys
from collections import Counter
sys.stdout.reconfigure(encoding="utf-8")

REPO = os.environ.get("BILI_REPO", os.path.expanduser("~/bili-comment-style-corpus"))
LOCAL = os.path.join(REPO, "local")
V1 = os.path.join(LOCAL, "text_analysis.jsonl")
V2 = os.path.join(LOCAL, "text_analysis.v2.jsonl")
OUT = os.path.join(LOCAL, "analysis_summary.v2.json")

NEW_LABELS = {"disgust", "self_deprecation", "irony", "anticipation",
              "affection", "admiration", "helplessness", "playfulness"}
CATS = ["body", "mood", "self", "desire", "relationship", "work_money",
        "daily", "media", "creation", "society", "knowledge", "dream", "unknown"]


def load(p):
    if not os.path.exists(p):
        return []
    return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]


v2 = load(V2)
v1 = load(V1)
print(f"v1: {len(v1)} 条   v2: {len(v2)} 条")

if not v2:
    print("v2 尚无数据"); sys.exit(0)

n = len(v2)

# ── ① unknown 占比 ──
print("\n" + "=" * 62)
print("① unknown 占比（v1 26.5% 是否下降）")
print("=" * 62)
v2_val = Counter((r.get("emotion_signals") or {}).get("valence") for r in v2)
v1_val = Counter((r.get("emotion_signals") or {}).get("valence") for r in v1)
v2_unk = v2_val.get("unknown", 0) / n
v1_unk = (v1_val.get("unknown", 0) / len(v1)) if v1 else 0
print(f"  v2 valence 分布: {dict(v2_val)}")
print(f"  v2 unknown 占比: {v2_unk*100:.1f}%")
print(f"  v1 unknown 占比: {v1_unk*100:.1f}%")
delta = (v2_unk - v1_unk) * 100
verdict = "✅ 下降" if delta < -1 else ("⚠️ 基本持平" if abs(delta) <= 1 else "❌ 上升")
print(f"  变化: {delta:+.1f} 个百分点 → {verdict}")

# ── ② 标签滥用 ──
print("\n" + "=" * 62)
print("② 标签滥用检查（单个 > 30% 视为滥用）")
print("=" * 62)
labs = Counter()
for r in v2:
    for l in ((r.get("emotion_signals") or {}).get("labels") or []):
        labs[l] += 1
print(f"  {'标签':<20}{'次数':>6}{'占比':>9}  标记")
abuse = []
for k, c in labs.most_common():
    pct = c / n * 100
    flag = "❌ 滥用" if pct > 30 else ("⚠️ 偏高" if pct > 20 else "")
    if pct > 20:
        abuse.append((k, pct))
    print(f"  {k:<20}{c:>6}{pct:>8.1f}%  {flag}")
new_used = {k: labs[k] for k in NEW_LABELS if labs.get(k)}
print(f"\n  新增 8 个标签中已使用: {len(new_used)}/8")
print(f"  {new_used}")
print(f"  other 出现: {labs.get('other', 0)} {'✅' if labs.get('other', 0) == 0 else '❌'}")

# ── ③ category 分布 ──
print("\n" + "=" * 62)
print("③ category 分布")
print("=" * 62)
cats = Counter((r.get("topic") or {}).get("category") for r in v2)
for c in CATS:
    cnt = cats.get(c, 0)
    bar = "█" * int(cnt / max(cats.values()) * 34) if cats else ""
    print(f"  {c:<14}{cnt:>4}  {cnt/n*100:>5.1f}%  {bar}")
top_cat, top_cnt = cats.most_common(1)[0]
conc = top_cnt / n * 100
print(f"\n  最大类别: {top_cat} {conc:.1f}%  " +
      ("✅ 未过度集中" if conc < 40 else "❌ 过度集中（>40%）"))

# ── ④ detail 长度 ──
print("\n" + "=" * 62)
print("④ detail 长度")
print("=" * 62)
dl = [len(str((r.get("topic") or {}).get("detail") or "")) for r in v2]
over = sum(1 for x in dl if x > 40)
print(f"  min={min(dl)}  max={max(dl)}  中位={sorted(dl)[len(dl)//2]}")
print(f"  超过 40 字: {over} {'✅' if over == 0 else '❌'}")

# ── 其他完整性 ──
print("\n" + "=" * 62)
print("⑤ 其他完整性")
print("=" * 62)
miss_it = sum(1 for r in v2 if not isinstance(r.get("interpretation"), dict))
normed = sum(1 for r in v2 if r.get("_normalized"))
skipped = sum(1 for r in v2 if r.get("review_status") == "skipped")
print(f"  interpretation 缺失: {miss_it} {'✅' if miss_it == 0 else '❌'}")
print(f"  被 normalize 修正过: {normed}")
print(f"  skipped（极短文本）: {skipped}")
conf = Counter(r.get("confidence") for r in v2)
print(f"  confidence: {dict(conf)}")

# ── 与 v1 的 category 对照（v1 无 category，用 topic 文本长度对比）──
print("\n" + "=" * 62)
print("⑥ v1 topic vs v2 detail 的可聚合性")
print("=" * 62)
v1_tops = [(r.get("topic") or {}).get("primary") for r in v1]
v1_tops = [t for t in v1_tops if t]
v1_uniq = len(set(v1_tops))
v1_cnt = len(v1_tops)
v2_cats_n = len([c for c in cats if c])
print(f"  v1: {v1_cnt} 条主题，去重后 {v1_uniq} 个 → 可聚合度 {v1_uniq/max(1,v1_cnt)*100:.0f}% 唯一（越低越可聚合）")
print(f"  v2: {n} 条记录，{len(cats)} 个类别 → 可聚合度 {len(cats)/n*100:.1f}%")

# ── 输出 ──
summary = {
    "schema_version": "2.0.0",
    "total": n,
    "valence": dict(v2_val),
    "unknown_rate": round(v2_unk, 4),
    "v1_unknown_rate": round(v1_unk, 4),
    "unknown_delta_pct": round(delta, 1),
    "labels": dict(labs),
    "new_labels_used": new_used,
    "other_count": labs.get("other", 0),
    "category": dict(cats),
    "top_category": {"name": top_cat, "share_pct": round(conc, 1)},
    "detail_len": {"min": min(dl), "max": max(dl), "over40": over},
    "interpretation_missing": miss_it,
    "normalized": normed,
    "skipped": skipped,
    "confidence": dict(conf),
    "aggregability": {
        "v1_unique_topic_ratio_pct": round(v1_uniq / max(1, v1_cnt) * 100, 1),
        "v2_category_ratio_pct": round(len(cats) / n * 100, 1),
    },
}
json.dump(summary, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"\n摘要 -> {OUT}")
