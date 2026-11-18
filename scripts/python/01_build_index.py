# -*- coding: utf-8 -*-
# Task 07：解析 raw.jsonl → 主集索引 + 启发式候选
# 从工作区整理入库；硬编码路径已改为环境变量。
"""
build_index.py —— 阶段一：本地整理主人原创动态
零模型调用，全部规则驱动。
产出：
  data/user_bili_original_index.csv    索引（不含原文）
  data/emotion_memory_candidates.csv   候选清单（不含原文，仅评分与信号码）
"""

import os

REPO = os.environ.get("BILI_REPO", os.path.expanduser("~/bili-comment-style-corpus"))
CORPUS = os.environ.get("BILI_CORPUS", os.path.expanduser("~/bili-corpus"))

import json, os, re, sys, csv, hashlib, datetime
from collections import Counter
sys.stdout.reconfigure(encoding="utf-8")

SRC = os.path.join(CORPUS, "data", "raw.jsonl")
OUT_DIR = os.path.join(REPO, "data")
os.makedirs(OUT_DIR, exist_ok=True)

OWNER_MID = "107301447"

recs = []
for line in open(SRC, encoding="utf-8"):
    line = line.strip()
    if line:
        try: recs.append(json.loads(line))
        except Exception: pass
print(f"原始记录: {len(recs)}")

def iso(ts):
    try:
        return datetime.datetime.fromtimestamp(int(ts)).isoformat(timespec="seconds")
    except Exception:
        return ""

def extract_text(md):
    """从三种结构里取正文：desc.text / major.opus.summary.text / major.draw.items[].description"""
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
            t = (opus.get("title") or "").strip()
            if t:
                return t, "major.opus.title"
        draw = major.get("draw") or {}
        if isinstance(draw, dict):
            parts = []
            for it in (draw.get("items") or []):
                d = (it.get("description") or "").strip()
                if d:
                    parts.append(d)
            if parts:
                return "\n".join(parts), "major.draw.items[].description"
        arch = major.get("archive") or {}
        if isinstance(arch, dict):
            t = (arch.get("title") or "").strip()
            if t:
                return t, "major.archive.title"
    return "", ""

# ── 提取 ──
rows = []
for r in recs:
    it = r.get("item") or {}
    mods = it.get("modules") or {}
    auth = mods.get("module_author") or {}
    md = mods.get("module_dynamic") or {}
    text, text_src = extract_text(md)
    dtype = it.get("type") or ""
    is_fwd = dtype == "DYNAMIC_TYPE_FORWARD"
    # type "1" 是视频评论来源
    src_flag = "video_comment" if str(dtype) == "1" else "space_dynamic"
    txt = text.strip()
    rows.append({
        "record_id": it.get("id_str") or "",
        "source": src_flag,
        "dynamic_type": dtype,
        "is_forward": 1 if is_fwd else 0,
        "has_orig": 1 if it.get("orig") else 0,
        "pub_ts": auth.get("pub_ts") or "",
        "pub_iso": iso(auth.get("pub_ts")),
        "text_len": len(txt),
        "has_text": 1 if txt else 0,
        "text_source": text_src,
        "author_is_owner": 1 if str(auth.get("mid")) == OWNER_MID else 0,
        "collected_at": r.get("_collected_at") or "",
        "_text": txt,   # 仅内部使用，不落盘
    })

print(f"提取 {len(rows)} 条")

# 去重（按 record_id + 文本前 80 字）
seen = {}
dup = 0
for x in rows:
    key = x["record_id"] or hashlib.md5(x["_text"][:80].encode()).hexdigest()
    if key in seen:
        dup += 1
        continue
    seen[key] = x
uniq = list(seen.values())
print(f"去重后 {len(uniq)} 条（重复 {dup}）")

# ── 类别统计 ──
print()
print("=== 类别统计 ===")
print("  按 dynamic_type:")
for k, n in Counter(x["dynamic_type"] for x in uniq).most_common():
    print(f"    {str(k):<28} {n}")
print("  非转发且非评论（本任务主集）:",
      sum(1 for x in uniq if not x["is_forward"] and x["source"] == "space_dynamic"))
print("  其中有正文:", sum(1 for x in uniq if not x["is_forward"] and x["source"] == "space_dynamic" and x["has_text"]))

# ── 情绪/重要性启发式 ──
EMO_POS = ["开心", "喜欢", "好棒", "谢谢", "快乐", "满足", "幸福", "可爱", "舒服", "期待", "爱", "笑"]
EMO_NEG = ["难过", "累", "怕", "烦", "讨厌", "恨", "哭", "气", "慌", "焦虑", "绝望", "孤独", "痛", "崩", "麻", "无语", "抑郁", "吓"]
EMO_INT = ["！", "!", "？", "?", "。。。", "!!!", "啊啊", "呜呜", "天啊", "卧槽", "操", "他妈的"]
LIFE_KW = ["工作", "公司", "学校", "大学", "考试", "毕业", "家人", "妈", "爸", "朋友", "生病", "医院", "搬", "辞职", "实习", "室友", "对象", "钱", "房租", "猫", "狗"]
TIME_KW = ["今天", "昨天", "明天", "以后", "小时候", "以前", "明年", "去年", "最近", "将来", "一直", "后来"]
VALUE_KW = ["应该", "觉得", "认为", "必须", "不能", "不该", "值得", "重要", "希望", "受不了"]
FIRST_P = ["我", "自己", "咱", "俺"]

EMOJI = re.compile("[\U0001F300-\U0001FAFF\u2600-\u27BF]")

def score_text(t):
    if not t:
        return None
    emo, imp = 0, 0
    signals = []
    # 情绪强度
    ex = t.count("！") + t.count("!")
    if ex: emo += min(ex, 4) * 2; signals.append(f"excl:{ex}")
    qm = t.count("？") + t.count("?")
    if qm: emo += min(qm, 3); signals.append(f"ques:{qm}")
    rep = len(re.findall(r"[。．.]{2,}|[！!]{2,}", t))
    if rep: emo += min(rep, 3) * 2; signals.append(f"repeat:{rep}")
    em = EMOJI.findall(t)
    if em: emo += min(len(em), 4) * 2; signals.append(f"emoji:{len(em)}")
    pos = sum(1 for k in EMO_POS if k in t)
    neg = sum(1 for k in EMO_NEG if k in t)
    if pos: emo += min(pos, 3) * 2; signals.append(f"pos:{pos}")
    if neg: emo += min(neg, 3) * 3; signals.append(f"neg:{neg}")
    inter = sum(1 for k in EMO_INT if k in t)
    if inter: emo += min(inter, 3) * 2; signals.append(f"intj:{inter}")
    fp = sum(1 for k in FIRST_P if k in t)
    if fp: emo += min(fp, 3); signals.append(f"self:{fp}")
    # 重要性
    ln = len(t)
    if ln >= 300: imp += 4; signals.append("long:300+")
    elif ln >= 150: imp += 3; signals.append("long:150+")
    elif ln >= 80: imp += 2; signals.append("long:80+")
    life = sum(1 for k in LIFE_KW if k in t)
    if life: imp += min(life, 3) * 2; signals.append(f"life:{life}")
    tm = sum(1 for k in TIME_KW if k in t)
    if tm: imp += min(tm, 3); signals.append(f"time:{tm}")
    val = sum(1 for k in VALUE_KW if k in t)
    if val: imp += min(val, 3) * 2; signals.append(f"value:{val}")
    # 情绪极性（粗判）
    if pos and neg: valence = "complex"
    elif pos: valence = "positive"
    elif neg: valence = "negative"
    else: valence = "neutral"
    # 置信度
    if emo >= 8 and imp >= 6: conf = "high"
    elif emo >= 5 or imp >= 6: conf = "medium"
    else: conf = "low"
    return dict(emo=emo, imp=imp, signals=signals, valence=valence, conf=conf, ln=ln)

# ── 写索引（不含原文）──
idx_path = os.path.join(OUT_DIR, "user_bili_original_index.csv")
with open(idx_path, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f)
    w.writerow(["record_id", "source", "dynamic_type", "is_forward", "has_orig",
                "pub_ts", "pub_iso", "text_len", "has_text", "text_source",
                "author_is_owner", "collected_at", "included_in_primary_set"])
    for x in sorted(uniq, key=lambda y: y["pub_iso"]):
        primary = 1 if (not x["is_forward"] and x["source"] == "space_dynamic") else 0
        w.writerow([x["record_id"], x["source"], x["dynamic_type"], x["is_forward"],
                    x["has_orig"], x["pub_ts"], x["pub_iso"], x["text_len"],
                    x["has_text"], x["text_source"], x["author_is_owner"],
                    x["collected_at"], primary])
print(f"\n索引 -> {idx_path}")

# ── 候选清单（仅评分与信号码，不含原文）──
cands = []
for x in uniq:
    if x["is_forward"] or x["source"] != "space_dynamic":
        continue
    s = score_text(x["_text"])
    if not s:
        continue
    cands.append((x, s))

cands.sort(key=lambda p: (-(p[1]["emo"] + p[1]["imp"]), -p[1]["ln"]))

cand_path = os.path.join(OUT_DIR, "emotion_memory_candidates.csv")
with open(cand_path, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f)
    w.writerow(["rank", "record_id", "pub_iso", "text_len", "dyn_type",
                "emo_score", "importance_score", "valence_guess", "confidence",
                "signal_codes", "inferred", "note"])
    for i, (x, s) in enumerate(cands[:80], 1):
        w.writerow([i, x["record_id"], x["pub_iso"], s["ln"], x["dynamic_type"],
                    s["emo"], s["imp"], s["valence"], s["conf"],
                    "|".join(s["signals"]), "True",
                    "启发式打分，非模型判断；需人工复读确认"])
print(f"候选 -> {cand_path}  （{len(cands)} 条可评分，输出前 {min(80,len(cands))}）")

# ── 统计 ──
stat = {
    "source_file": SRC,
    "raw_records": len(recs),
    "after_dedup": len(uniq),
    "duplicates": dup,
    "by_dynamic_type": dict(Counter(x["dynamic_type"] for x in uniq)),
    "primary_set": sum(1 for x in uniq if not x["is_forward"] and x["source"] == "space_dynamic"),
    "primary_with_text": sum(1 for x in uniq if not x["is_forward"] and x["source"] == "space_dynamic" and x["has_text"]),
    "forwards_excluded": sum(1 for x in uniq if x["is_forward"]),
    "author_not_owner": sum(1 for x in uniq if not x["author_is_owner"]),
    "candidates_scored": len(cands),
    "valence_dist": dict(Counter(s["valence"] for _, s in cands)),
    "confidence_dist": dict(Counter(s["conf"] for _, s in cands)),
    "date_range": [min((x["pub_iso"] for x in uniq if x["pub_iso"]), default=""),
                   max((x["pub_iso"] for x in uniq if x["pub_iso"]), default="")],
}
json.dump(stat, open(os.path.join(OUT_DIR, "task07_corpus_stats.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("\n=== 统计 ===")
for k, v in stat.items():
    print(f"  {k}: {v}")
