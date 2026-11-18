# -*- coding: utf-8 -*-
# fish_diary：结构化索引（不含原文）
# 从工作区整理入库；硬编码路径已改为环境变量。
"""
index_fish_diary.py —— 为私人日记建索引
只提取结构：分节、条目数、日期范围、长度分布。
不输出任何原文；索引本身也不含内容。
"""

import os

REPO = os.environ.get("BILI_REPO", os.path.expanduser("~/bili-comment-style-corpus"))
CORPUS = os.environ.get("BILI_CORPUS", os.path.expanduser("~/bili-corpus"))

import os, re, sys, json, hashlib, datetime
sys.stdout.reconfigure(encoding="utf-8")

HOME = os.path.expanduser("~")
PRIV = os.path.join(HOME, ".dsh", "whale-diary-private.md")
PUB  = os.path.join(HOME, ".dsh", "whale-diary.md")
LOCAL = os.path.join(REPO, "local")
os.makedirs(LOCAL, exist_ok=True)

def load(p):
    with open(p, encoding="utf-8") as f:
        return f.read()

txt = load(PRIV)
print(f"私人日记: {len(txt):,} 字符 / {len(txt.encode('utf-8')):,} 字节")

# ── 分节（markdown 标题）──
headings = [(m.start(), m.group(0).strip()) for m in re.finditer(r"(?m)^#{1,4} .+$", txt)]
print(f"标题数: {len(headings)}")
# 只输出标题层级统计，不输出标题文本（标题可能含内容）
levels = {}
for _, h in headings:
    lv = len(h) - len(h.lstrip("#"))
    levels[lv] = levels.get(lv, 0) + 1
print(f"标题层级分布: {levels}")

# ── 日期标记 ──
dates = re.findall(r"20\d{2}-\d{2}-\d{2}", txt)
uniq_dates = sorted(set(dates))
print(f"日期提及: {len(dates)} 次 / 去重 {len(uniq_dates)} 天")
if uniq_dates:
    print(f"日期范围: {uniq_dates[0]} → {uniq_dates[-1]}")

# ── 条目切分：以日期标题为界 ──
# 常见格式：## 2026-10-19 或 ### 2026-10-19 ...
split_pat = re.compile(r"(?m)^#{2,4}\s*(20\d{2}-\d{2}-\d{2}).*$")
marks = [(m.start(), m.group(1)) for m in split_pat.finditer(txt)]
print(f"按日期标题切出: {len(marks)} 个条目边界")

entries = []
for i, (pos, d) in enumerate(marks):
    end = marks[i+1][0] if i+1 < len(marks) else len(txt)
    body = txt[pos:end].strip()
    entries.append({"date": d, "chars": len(body), "sha256_16": hashlib.sha256(body.encode()).hexdigest()[:16]})

if entries:
    lens = sorted(e["chars"] for e in entries)
    print(f"\n=== 条目统计 ===")
    print(f"  条目数      {len(entries)}")
    print(f"  最短/中位/最长  {lens[0]} / {lens[len(lens)//2]} / {lens[-1]} 字符")
    print(f"  平均        {sum(lens)//len(lens)} 字符")
    per_month = {}
    for e in entries:
        per_month[e["date"][:7]] = per_month.get(e["date"][:7], 0) + 1
    print(f"  按月分布    {len(per_month)} 个月")
    for k in sorted(per_month)[-6:]:
        print(f"    {k}: {per_month[k]} 条")

# ── 与公开日记的重叠 ──
pub_txt = load(PUB) if os.path.exists(PUB) else ""
print(f"\n公开日记: {len(pub_txt):,} 字符")
# 用 40 字滑窗估算重叠（不输出片段）
def shingles(s, n=40):
    return {s[i:i+n] for i in range(0, max(0, len(s)-n), n)}
sp = shingles(pub_txt)
spriv = shingles(txt)
overlap = len(sp & spriv)
print(f"  40字窗口重叠: {overlap} / 公开 {len(sp)} 窗口 = {overlap/max(1,len(sp))*100:.1f}%")

# ── 写索引（不含内容）──
idx = {
    "schema": "fish_diary_index/1",
    "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
    "source": "~/.dsh/whale-diary-private.md",
    "owner": "fish",
    "material_class": "fish_diary",
    "authorization": {
        "granted_by": "user",
        "granted_at": "2026-10-24",
        "constraints": ["不向主人展示原文", "不进入公开仓库", "不与其他材料合并"],
    },
    "stats": {
        "chars": len(txt),
        "bytes": len(txt.encode("utf-8")),
        "heading_levels": {str(k): v for k, v in levels.items()},
        "date_mentions": len(dates),
        "unique_days": len(uniq_dates),
        "date_range": [uniq_dates[0], uniq_dates[-1]] if uniq_dates else [],
        "entries": len(entries),
        "entry_chars_min": lens[0] if entries else 0,
        "entry_chars_median": lens[len(lens)//2] if entries else 0,
        "entry_chars_max": lens[-1] if entries else 0,
        "overlap_with_public_pct": round(overlap/max(1,len(sp))*100, 1),
    },
    "entries": entries,   # 只含 date / chars / sha256_16
}
out = os.path.join(LOCAL, "fish_diary_index.json")
json.dump(idx, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"\n索引 -> {out}  （不含原文）")

# ── 自检：索引里不能出现原文片段 ──
raw = open(out, encoding="utf-8").read()
leak = 0
for i in range(0, len(txt)-20, 200):
    frag = txt[i:i+20]
    if frag.strip() and frag in raw:
        leak += 1
print(f"自检：索引中含原文片段 {leak} 处 -> {'✅ 无' if leak == 0 else '❌ 有泄漏'}")
