# -*- coding: utf-8 -*-
# Task 08：公开索引隐私审计 + 脱敏替换
# 从工作区整理入库；硬编码路径已改为环境变量。
"""
privacy_audit.py —— 审查已公开索引的隐私风险，生成脱敏版本
零模型调用。
"""

import os

REPO = os.environ.get("BILI_REPO", os.path.expanduser("~/bili-comment-style-corpus"))
CORPUS = os.environ.get("BILI_CORPUS", os.path.expanduser("~/bili-corpus"))

import csv, os, sys, hashlib, json, datetime
sys.stdout.reconfigure(encoding="utf-8")

PUB_IDX = os.path.join(REPO, "data", "user_bili_original_index.csv")
LOCAL = os.path.join(REPO, "local")
os.makedirs(LOCAL, exist_ok=True)

SALT_FILE = os.path.join(LOCAL, ".desensitize_salt")
if os.path.exists(SALT_FILE):
    SALT = open(SALT_FILE, encoding="utf-8").read().strip()
else:
    SALT = hashlib.sha256(os.urandom(32)).hexdigest()
    open(SALT_FILE, "w", encoding="utf-8").write(SALT)
print(f"salt 已就绪（保存在 local/，不入库）  长度={len(SALT)}")

def key_of(record_id):
    """不可逆的稳定假名：无 salt 无法反查"""
    return hashlib.sha256((SALT + "|" + record_id).encode()).hexdigest()[:12]

def len_bucket(n):
    if n == 0: return "0"
    if n < 30: return "1-29"
    if n < 80: return "30-79"
    if n < 150: return "80-149"
    if n < 300: return "150-299"
    return "300+"

rows = list(csv.DictReader(open(PUB_IDX, encoding="utf-8-sig")))
print(f"现有公开索引: {len(rows)} 行")

# ── 审计每列的风险 ──
COLS = {
    "record_id":    ("高", "B 站动态 ID。拼接 t.bilibili.com/<id> 可直接打开原帖，是原文的直接指针"),
    "pub_iso":      ("中高", "秒级发布时间。长期序列可推断作息、发布习惯，且能与其他数据源交叉比对"),
    "pub_ts":       ("中高", "同上（epoch 形式）"),
    "text_len":     ("低", "长度本身信息量小，但与发布时间组合后可形成指纹"),
    "collected_at": ("中低", "抓取时间，可暴露工具与操作习惯"),
    "dynamic_type": ("低", "类型标签，无识别性"),
    "text_source":  ("低", "正文所在字段，无识别性"),
    "is_forward":   ("低", "布尔标记"),
    "has_orig":     ("低", "布尔标记"),
    "author_is_owner": ("低", "布尔标记"),
    "included_in_primary_set": ("低", "布尔标记"),
    "source":       ("低", "来源类型"),
}
print("\n=== 列级风险 ===")
for c in rows[0].keys():
    lvl, why = COLS.get(c, ("未评估", ""))
    print(f"  {c:<26} {lvl:<4} {why}")

# ── 生成脱敏版 ──
out_path = os.path.join(REPO, "data", "user_bili_original_index.public.csv")
with open(out_path, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f)
    w.writerow(["record_key", "month", "dyn_type", "len_bucket",
                "has_text", "text_source", "author_is_owner",
                "included_in_primary_set"])
    seen = set()
    for r in rows:
        rid = r.get("record_id") or ""
        k = key_of(rid) if rid else "none"
        if k in seen:
            continue
        seen.add(k)
        month = (r.get("pub_iso") or "")[:7]   # 只留年月
        w.writerow([
            k, month, r.get("dynamic_type", ""),
            len_bucket(int(r.get("text_len") or 0)),
            r.get("has_text", ""), r.get("text_source", ""),
            r.get("author_is_owner", ""), r.get("included_in_primary_set", ""),
        ])
print(f"\n脱敏版 -> {out_path}")

# ── 把完整索引移到 local/ ──
local_full = os.path.join(LOCAL, "user_bili_original_index.full.csv")
if os.path.exists(PUB_IDX):
    os.replace(PUB_IDX, local_full)
    print(f"完整索引已移入本地: {local_full}")

# ── 验证脱敏版里没有原始 ID / 精确时间 ──
pub = list(csv.DictReader(open(out_path, encoding="utf-8-sig")))
bad = 0
orig_ids = {r.get("record_id") for r in rows if r.get("record_id")}
for r in pub:
    for v in r.values():
        if v in orig_ids:
            bad += 1
        # 精确时间格式 yyyy-mm-ddThh:mm:ss
        if len(v) >= 16 and v[4:5] == "-" and "T" in v:
            bad += 1
print(f"\n=== 验证 ===")
print(f"  行数: {len(pub)}")
print(f"  含原始 ID 或精确时间的单元格: {bad}  → {'✅ 无' if bad == 0 else '❌ 有泄漏'}")
print(f"  record_key 样例: {pub[0]['record_key']}  (12 位十六进制，无 salt 不可逆)")
print(f"  month 样例: {pub[0]['month']}")

# ── 审计报告数据 ──
json.dump({
    "audited_at": datetime.datetime.now().isoformat(timespec="seconds"),
    "audited_file": "data/user_bili_original_index.csv",
    "rows": len(rows),
    "columns": {c: {"risk": COLS.get(c, ("未评估",""))[0], "why": COLS.get(c, ("",""))[1]} for c in rows[0].keys()},
    "replacement": "data/user_bili_original_index.public.csv",
    "full_index_moved_to": "local/user_bili_original_index.full.csv",
    "desensitization": {
        "record_id": "sha256(salt + id)[:12]，salt 仅存本地",
        "pub_iso": "截断到年月",
        "pub_ts": "删除",
        "collected_at": "删除",
        "text_len": "分桶（1-29 / 30-79 / 80-149 / 150-299 / 300+）",
    },
    "residual_risk": [
        "git 历史中仍保留旧版文件；如需彻底清除需重写历史",
        "月份 + 分桶 + 类型 在极端情况下仍可能缩小范围，但无法定位具体条目",
        "原动态本身在 B 站公开，真正的风险是聚合后可被批量枚举"
    ],
}, open(os.path.join(LOCAL, "privacy_audit.json"), "w", encoding="utf-8"),
   ensure_ascii=False, indent=1)
print("\n审计数据 -> local/privacy_audit.json")
