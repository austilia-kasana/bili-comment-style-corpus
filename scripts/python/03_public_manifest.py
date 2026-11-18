# -*- coding: utf-8 -*-
# Task 08：批次清单脱敏（公开版）
# 从工作区整理入库；硬编码路径已改为环境变量。
"""生成脱敏版批次清单（公开用）"""

import os

REPO = os.environ.get("BILI_REPO", os.path.expanduser("~/bili-comment-style-corpus"))
CORPUS = os.environ.get("BILI_CORPUS", os.path.expanduser("~/bili-corpus"))

import csv, os, hashlib, sys
sys.stdout.reconfigure(encoding="utf-8")

LOCAL = os.path.join(REPO, "local")
SALT = open(os.path.join(LOCAL, ".desensitize_salt"), encoding="utf-8").read().strip()

def key_of(rid):
    return hashlib.sha256((SALT + "|" + rid).encode()).hexdigest()[:12]

def len_bucket(n):
    if n == 0: return "0"
    if n < 30: return "1-29"
    if n < 80: return "30-79"
    if n < 150: return "80-149"
    if n < 300: return "150-299"
    return "300+"

src = os.path.join(LOCAL, "text_batch_manifest.csv")
rows = list(csv.DictReader(open(src, encoding="utf-8-sig")))
print(f"完整清单 {len(rows)} 行")

out = os.path.join(REPO, "data", "text_batch_manifest.csv")
with open(out, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f)
    w.writerow(["batch_id", "batch_seq", "record_key", "month",
                "dyn_type", "len_bucket", "processed", "needs_review", "output_version"])
    for r in rows:
        rid = r.get("record_id") or ""
        w.writerow([
            r["batch_id"], r["batch_seq"],
            key_of(rid) if rid else "none",
            (r.get("pub_iso") or "")[:7],
            r.get("dyn_type", ""),
            len_bucket(int(r.get("text_len") or 0)),
            r.get("processed", "0"), r.get("needs_review", "0"),
            r.get("output_version", ""),
        ])
print(f"脱敏清单 -> {out}")

# 验证
pub = list(csv.DictReader(open(out, encoding="utf-8-sig")))
orig = {r.get("record_id") for r in rows if r.get("record_id")}
bad = sum(1 for r in pub for v in r.values() if v in orig)
print(f"  行数 {len(pub)}")
print(f"  含原始 ID 的单元格: {bad} → {'✅ 无' if bad == 0 else '❌'}")
print(f"  批次数: {len(set(r['batch_id'] for r in pub))}")
