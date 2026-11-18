# -*- coding: utf-8 -*-
# Task 08：按 10 条/批切分 + 只读行号定位
# 从工作区整理入库；硬编码路径已改为环境变量。
"""
build_batches.py —— Task 08 阶段一：建立分批清单
零模型调用。
产出（全部先落本地）：
  local/text_batch_manifest.csv        完整清单（含 ID / 精确时间 / 行号 / 校验值）
  local/record_locator.json            记录 -> raw.jsonl 行号 的只读定位表
"""

import os

REPO = os.environ.get("BILI_REPO", os.path.expanduser("~/bili-comment-style-corpus"))
CORPUS = os.environ.get("BILI_CORPUS", os.path.expanduser("~/bili-corpus"))

import json, os, re, sys, csv, hashlib, datetime
sys.stdout.reconfigure(encoding="utf-8")

SRC = os.path.join(CORPUS, "data", "raw.jsonl")
LOCAL = os.path.join(REPO, "local")
os.makedirs(LOCAL, exist_ok=True)

OWNER_MID = "107301447"

# ── 解析，记录行号 ──
recs = []
with open(SRC, encoding="utf-8") as f:
    for lineno, line in enumerate(f, 1):
        line = line.strip()
        if not line:
            continue
        try:
            recs.append((lineno, json.loads(line)))
        except Exception:
            pass
print(f"raw.jsonl 行数: {len(recs)}")

def iso(ts):
    try:
        return datetime.datetime.fromtimestamp(int(ts)).isoformat(timespec="seconds")
    except Exception:
        return ""

def extract_text(md):
    if not isinstance(md, dict):
        return "", ""
    desc = md.get("desc")
    if isinstance(desc, dict):
        t = (desc.get("text") or "").strip()
        if t:
            return t, "desc.text"
    major = md.get("major") or {}
    if isinstance(major, dict):
        opus = major.get("opus") or {}
        if isinstance(opus, dict):
            summ = opus.get("summary") or {}
            if isinstance(summ, dict):
                t = (summ.get("text") or "").strip()
                if t:
                    return t, "major.opus.summary.text"
        draw = major.get("draw") or {}
        if isinstance(draw, dict):
            parts = [ (it.get("description") or "").strip()
                      for it in (draw.get("items") or []) ]
            parts = [p for p in parts if p]
            if parts:
                return "\n".join(parts), "major.draw.items[].description"
    return "", ""

rows = []
for lineno, r in recs:
    it = r.get("item") or {}
    mods = it.get("modules") or {}
    auth = mods.get("module_author") or {}
    dtype = it.get("type") or ""
    if dtype == "DYNAMIC_TYPE_FORWARD" or str(dtype) == "1":
        continue
    if str(auth.get("mid")) != OWNER_MID:
        continue
    text, tsrc = extract_text(mods.get("module_dynamic") or {})
    if not text:
        continue
    h = hashlib.sha256(text.encode("utf-8")).hexdigest()
    rows.append({
        "record_id": it.get("id_str") or "",
        "pub_ts": int(auth.get("pub_ts") or 0),
        "pub_iso": iso(auth.get("pub_ts")),
        "dyn_type": dtype,
        "text_len": len(text),
        "text_source": tsrc,
        "sha256": h,
        "sha256_16": h[:16],
        "raw_line": lineno,
        "raw_path": SRC,
    })

print(f"主集记录: {len(rows)}")

# ── 按时间排序，按 sha256 去重（同一条记录重复处理时不产生重复分析）──
seen = {}
dups = 0
for x in rows:
    if x["sha256"] in seen:
        dups += 1
        continue
    seen[x["sha256"]] = x
uniq = sorted(seen.values(), key=lambda y: (y["pub_ts"], y["record_id"]))
print(f"按内容去重后: {len(uniq)}（重复 {dups}）")

# ── 分批：默认 10 条/批 ──
BATCH_SIZE = 10
batches = [uniq[i:i+BATCH_SIZE] for i in range(0, len(uniq), BATCH_SIZE)]
print(f"批次数: {len(batches)}（每批 {BATCH_SIZE}，末批 {len(batches[-1])}）")

# ── 写清单 ──
man_path = os.path.join(LOCAL, "text_batch_manifest.csv")
with open(man_path, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f)
    w.writerow([
        "batch_id", "batch_seq", "record_id", "pub_iso", "pub_ts",
        "dyn_type", "text_len", "text_source", "sha256_16",
        "raw_path", "raw_line",
        "processed", "needs_review", "output_version", "note"
    ])
    for bi, batch in enumerate(batches, 1):
        bid = f"B{bi:03d}"
        for seq, x in enumerate(batch, 1):
            w.writerow([
                bid, seq, x["record_id"], x["pub_iso"], x["pub_ts"],
                x["dyn_type"], x["text_len"], x["text_source"], x["sha256_16"],
                x["raw_path"], x["raw_line"],
                0, 0, "", ""
            ])
print(f"清单 -> {man_path}")

# ── 定位表（记录 ID -> 行号），供只读引用 ──
loc_path = os.path.join(LOCAL, "record_locator.json")
json.dump({
    "schema": "record_locator/1",
    "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
    "source_file": SRC,
    "note": "行号为 raw.jsonl 的 1-based 行号；只读引用，不复制原文",
    "records": {x["record_id"]: {"line": x["raw_line"], "sha256_16": x["sha256_16"],
                                 "len": x["text_len"]} for x in uniq},
}, open(loc_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"定位表 -> {loc_path}")

# ── 批次统计 ──
stats = {
    "primary_records": len(uniq),
    "batch_size": BATCH_SIZE,
    "batch_count": len(batches),
    "last_batch_size": len(batches[-1]),
    "duplicates_by_sha256": dups,
    "date_range": [uniq[0]["pub_iso"], uniq[-1]["pub_iso"]],
    "batches": [{"batch_id": f"B{i:03d}", "n": len(b), 
                 "from": b[0]["pub_iso"], "to": b[-1]["pub_iso"]}
                for i, b in enumerate(batches, 1)],
}
json.dump(stats, open(os.path.join(LOCAL, "batch_stats.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("\n=== 批次概览 ===")
print(f"  主集 {stats['primary_records']} 条 / {stats['batch_count']} 批")
print(f"  时间 {stats['date_range'][0]} → {stats['date_range'][1]}")
for b in stats["batches"][:5]:
    print(f"  {b['batch_id']}  {b['n']:>2} 条  {b['from'][:10]} → {b['to'][:10]}")
print("  ...")
