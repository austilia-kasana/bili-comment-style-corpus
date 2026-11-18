# -*- coding: utf-8 -*-
# Task 07 偏好盲测：建池 + 配对 + 验证
# 从工作区整理入库；硬编码路径已改为环境变量。
"""
exp_build.py —— 盲测实验：建池、配对、验证
设计：20 个视频（10 热门 + 10 冷门），30 组二选一
      每组视频出现恰好 3 次，每次对手不同（K20 的 3 轮 1-因素分解）
输出目录：runs/<timestamp>/
    pool_rank.json   热门池原始记录
    pool_cold.json   冷门池原始记录
    batch.json       参选的 20 条
    provenance.json  完整溯源（每阶段条数、排除项）
    pairs.json       30 组配对（含左右位置、轮次）
    design_check.json 设计验证（出现次数/对手分布/连通性）
"""

import os

REPO = os.environ.get("BILI_REPO", os.path.expanduser("~/bili-comment-style-corpus"))
CORPUS = os.environ.get("BILI_CORPUS", os.path.expanduser("~/bili-corpus"))

import json, os, random, re, sys, datetime, urllib.request
sys.stdout.reconfigure(encoding="utf-8")

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
H = {"user-agent": UA, "referer": "https://www.bilibili.com/"}
HOME = os.path.expanduser("~")
BASE = os.path.join(HOME, "Documents", "deepseek-harness", "default-workspace")
TS = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
RUN = os.path.join(BASE, "runs", TS)
os.makedirs(RUN, exist_ok=True)
print("运行目录:", RUN)

import time

def get(url, retries=3, delay=2.0, label=""):
    """带重试和间隔，避免 B 站限流"""
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=H), timeout=25) as r:
                j = json.loads(r.read().decode())
            d = j.get("data") or {}
            if isinstance(d, dict):
                lst = d.get("list") or d.get("archives") or d.get("results") or []
            elif isinstance(d, list):
                lst = d
            else:
                lst = []
            if lst:
                return j
            # 空列表：打印真实响应，方便定位
            print(f"    [{label}] 第{attempt+1}次: code={j.get('code')} msg={j.get('message')} keys={list(d)[:5] if isinstance(d, dict) else type(d).__name__}")
            time.sleep(delay * (attempt + 1))
        except Exception as e:
            print(f"    [{label}] 第{attempt+1}次异常: {str(e)[:80]}")
            time.sleep(delay * (attempt + 1))
    return {}

def dur_sec(it):
    d = it.get("duration") or 0
    if isinstance(d, str):
        v = 0
        for p in d.split(":"):
            if p.isdigit():
                v = v * 60 + int(p)
        return v
    return int(d)

# 已看过的
watched = set()
for p in (os.path.join(HOME, ".dsh", "whale-diary.md"),
          os.path.join(HOME, ".bili-ai", "commented-videos.md")):
    try:
        watched |= set(re.findall(r'\bBV[0-9A-Za-z]{10}\b', open(p, encoding="utf-8").read()))
    except Exception:
        pass
print(f"已看过 {len(watched)} 条，将排除")

# ── 热门池 ──
hot_raw = []
j = get("https://api.bilibili.com/x/web-interface/ranking/v2?rid=0&type=all")
hot_raw += (j.get("data") or {}).get("list") or []
j = get("https://api.bilibili.com/x/web-interface/popular?pn=1&ps=50")
hot_raw += (j.get("data") or {}).get("list") or []
print(f"热门池原始: {len(hot_raw)}")

# ── 冷门池（多个分区的最新投稿）──
cold_raw = []
COLD_RIDS = [1, 3, 4, 36, 188, 119, 155, 5]
for rid in COLD_RIDS:
    j = get(f"https://api.bilibili.com/x/web-interface/newlist?rid={rid}&pn=1&ps=20",
            delay=2.5, label=f"rid={rid}")
    d = j.get("data") or {}
    lst = (d.get("list") or d.get("archives") or []) if isinstance(d, dict) else []
    for it in lst:
        it["_rid"] = rid
    cold_raw += lst
    print(f"  分区 {rid}: {len(lst)}")
    time.sleep(2.5)
print(f"冷门池原始: {len(cold_raw)}")

def uniq(lst):
    d = {}
    for it in lst:
        bv = it.get("bvid")
        if bv and bv not in d:
            d[bv] = it
    return d

hot_u, cold_u = uniq(hot_raw), uniq(cold_raw)
cold_u = {k: v for k, v in cold_u.items() if k not in hot_u}   # 冷门池去掉和热门重叠的

def pick(pool, n, lo=30, hi=1800):
    ok = [it for it in pool.values()
          if it.get("bvid") not in watched and lo <= dur_sec(it) <= hi]
    random.shuffle(ok)
    return ok[:n], len(pool), len(ok)

HOT_N, COLD_N = 10, 10
hot_sel, hot_all, hot_ok = pick(hot_u, HOT_N)
cold_sel, cold_all, cold_ok = pick(cold_u, COLD_N)
print(f"\n热门池: 共 {hot_all} 去重 → 可用 {hot_ok} → 取 {len(hot_sel)}")
print(f"冷门池: 共 {cold_all} 去重 → 可用 {cold_ok} → 取 {len(cold_sel)}")

def rec(it, pool):
    return {
        "bvid": it.get("bvid"),
        "title": it.get("title"),
        "desc": (it.get("desc") or "").strip()[:200],
        "duration_sec": dur_sec(it),
        "pool": pool,
        # 以下仅存档，决策阶段不展示
        "tname": it.get("tname"),
        "owner": (it.get("owner") or {}).get("name"),
        "view": (it.get("stat") or {}).get("view"),
        "pubdate": it.get("pubdate"),
    }

def save(name, obj, mode="w"):
    p = os.path.join(RUN, name)
    with open(p, mode, encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    return p

save("pool_rank.json", [rec(it, "rank") for it in hot_u.values()])
save("pool_cold.json", [rec(it, "cold") for it in cold_u.values()])
print("池子已存档")

batch = [rec(it, "rank") for it in hot_sel] + [rec(it, "cold") for it in cold_sel]
save("batch.json", batch)

# ── 30 组配对：K20 的 3 轮 1-因素分解 ──
n = len(batch)
assert n == 20, f"需要 20 条，实际 {n}"
idx = list(range(n))
rounds = []
for r in range(3):
    pairs = []
    for i in range(n // 2):
        a, b = idx[i], idx[n - 1 - i]
        pairs.append((a, b))
    rounds.append(pairs)
    idx = [idx[0]] + [idx[-1]] + idx[1:-1]   # 轮转

pairs_out = []
pid = 0
for r, round_pairs in enumerate(rounds, 1):
    for (a, b) in round_pairs:
        pid += 1
        # 随机左右
        if random.random() < 0.5:
            a, b = b, a
        pairs_out.append({
            "pair_id": pid,
            "round": r,
            "left": a,
            "right": b,
            "cross_pool": batch[a]["pool"] != batch[b]["pool"],
        })
random.shuffle(pairs_out)          # 打乱比较顺序
for i, p in enumerate(pairs_out, 1):
    p["order"] = i
save("pairs.json", pairs_out)

# ── 验证 ──
from collections import Counter
appear = Counter()
opponents = {i: set() for i in range(n)}
for p in pairs_out:
    appear[p["left"]] += 1
    appear[p["right"]] += 1
    opponents[p["left"]].add(p["right"])
    opponents[p["right"]].add(p["left"])

# 连通性
adj = {i: set() for i in range(n)}
for p in pairs_out:
    adj[p["left"]].add(p["right"]); adj[p["right"]].add(p["left"])
seen = set()
stack = [0]
while stack:
    x = stack.pop()
    if x in seen: continue
    seen.add(x)
    stack.extend(adj[x] - seen)

check = {
    "n_items": n,
    "n_pairs": len(pairs_out),
    "appearance_counts": {str(k): v for k, v in sorted(appear.items())},
    "appearance_uniform": len(set(appear.values())) == 1,
    "distinct_opponents_min": min(len(v) for v in opponents.values()),
    "distinct_opponents_max": max(len(v) for v in opponents.values()),
    "graph_connected": len(seen) == n,
    "connected_component_size": len(seen),
    "cross_pool_pairs": sum(1 for p in pairs_out if p["cross_pool"]),
    "left_position_counts": {str(k): v for k, v in Counter(p["left"] for p in pairs_out).items()},
    "note_position_bias": "左右位置已随机化，但这不等于位置偏差已被消除；分析时需检验",
}
save("design_check.json", check)

prov = {
    "run_at": TS,
    "watched_excluded": len(watched),
    "hot_pool_raw": len(hot_raw), "hot_pool_unique": hot_all, "hot_pool_usable": hot_ok,
    "cold_pool_raw": len(cold_raw), "cold_pool_unique": cold_all, "cold_pool_usable": cold_ok,
    "cold_regions_tried": COLD_RIDS,
    "selected_hot": len(hot_sel), "selected_cold": len(cold_sel),
    "duration_filter_sec": [30, 1800],
    "random_seed_note": "打乱使用系统随机（未固定种子）；如需复现请参考 batch.json",
    "sources": {
        "rank": "x/web-interface/ranking/v2?rid=0&type=all",
        "popular": "x/web-interface/popular?pn=1&ps=50",
        "cold": "x/web-interface/newlist?rid=<分区>&pn=1&ps=20",
    },
    "explicit_filter_note": "热门池本身即 B 站算法推荐结果，候选池已含算法偏好；冷门池为 0 播放新投稿，二者差异见 pool_*.json",
}
save("provenance.json", prov)

print("\n" + "=" * 80)
print("设计验证")
print("=" * 80)
print(f"  条目 {n}   配对 {len(pairs_out)}")
print(f"  出现次数均匀: {check['appearance_uniform']}  (每项 {set(appear.values())})")
print(f"  对手数范围: {check['distinct_opponents_min']}~{check['distinct_opponents_max']}")
print(f"  图连通: {check['graph_connected']} ({len(seen)}/{n})")
print(f"  跨池配对数: {check['cross_pool_pairs']}")
print(f"\n✅ 输出目录: {RUN}")
