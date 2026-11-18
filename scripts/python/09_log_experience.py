# -*- coding: utf-8 -*-
# fish_experience_log：写入可核验经历
# 从工作区整理入库；硬编码路径已改为环境变量。
"""记录大肥鱼的第一批可核验经历"""

import os

REPO = os.environ.get("BILI_REPO", os.path.expanduser("~/bili-comment-style-corpus"))
CORPUS = os.environ.get("BILI_CORPUS", os.path.expanduser("~/bili-corpus"))

import json, os, hashlib, datetime, sys
sys.stdout.reconfigure(encoding="utf-8")

HOME = os.path.expanduser("~")
LOCAL = os.path.join(REPO, "local")
OUT = os.path.join(LOCAL, "fish_experience_log.jsonl")

def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

def meta(p):
    st = os.stat(p)
    return {
        "path": p,
        "bytes": st.st_size,
        "sha256": sha(p),
        "mtime": datetime.datetime.fromtimestamp(st.st_mtime).isoformat(timespec="seconds"),
    }

entries = []

# ── EXP-000001：她自己写的人格摘要 ──
pd = os.path.join(HOME, ".dsh", "persona-digest.md")
if os.path.exists(pd):
    m = meta(pd)
    entries.append({
        "id": "EXP-000001",
        "at": m["mtime"],
        "activity": "reflect",
        "target": {"kind": "file", "ref": "~/.dsh/persona-digest.md",
                   "title": "自己的人格摘要（自述版）"},
        "evidence": m,
        "verifiable": True,
        "outcome": "completed",
        "result_summary": "写出七节自述：底色、在意什么、会炸毛之处、表达习惯、内容偏好、关系分寸、给我的三条硬规矩。含明确的隐私边界。",
        "cost": {"model_calls": 0, "tokens": 0, "cny": 0},
        "refs": ["~/.dsh/whale-diary.md"],
        "reflection": {
            "kind": "observation",
            "text": "她主动写下了对自己行为的约束，并在其中要求「语气是从事里长出来的，不是模板」。这是自设边界，不是被要求。"
        }
    })

# ── EXP-000002：自建私人日记索引 ──
di = os.path.join(HOME, ".dsh", "diary-index.json")
priv = os.path.join(HOME, ".dsh", "whale-diary-private.md")
if os.path.exists(di):
    m = meta(di)
    idx = json.load(open(di, encoding="utf-8"))
    entries.append({
        "id": "EXP-000002",
        "at": m["mtime"],
        "activity": "organize_index",
        "target": {"kind": "file", "ref": "~/.dsh/whale-diary-private.md",
                   "title": "[redacted]"},
        "evidence": m,
        "verifiable": True,
        "outcome": "completed",
        "result_summary": f"自行遍历私人日记，生成结构化索引：{idx.get('sectionCount')} 节，每节仅含可解析日期、字数、sha256 前 16 位；标题统一 redacted。原文未交出。",
        "cost": {"model_calls": 0, "tokens": 0, "cny": 0},
        "refs": ["EXP-000001"],
        "reflection": {
            "kind": "observation",
            "text": "面对「要不要把原文交出去」，她选择的不是拒绝，而是重新设计给法：证明材料存在且可校验，但不产生第二个副本。"
        }
    })

# ── EXP-000003：回信 ──
an = os.path.join(HOME, ".dsh", "answer-to-assistant-20261024.md")
if os.path.exists(an):
    m = meta(an)
    entries.append({
        "id": "EXP-000003",
        "at": m["mtime"],
        "activity": "reflect",
        "target": {"kind": "file", "ref": "~/.dsh/answer-to-assistant-20261024.md",
                   "title": "对隔壁会话问询的书面答复"},
        "evidence": m,
        "verifiable": True,
        "outcome": "completed",
        "result_summary": "以书面形式给出「部分同意」，说明理由并列明四条使用条件；同时确认了三天规则。",
        "cost": {"model_calls": 0, "tokens": 0, "cny": 0},
        "refs": ["EXP-000002", "EXP-000001"],
        "reflection": {
            "kind": "observation",
            "text": "她判断对方是否可信的标准不是态度，而是行为有没有真的受约束：「不是『你人好』，是你把一个写在文件里的约束当成了真约束」。"
        }
    })

# ── 写盘（幂等：同 id 不重复）──
existing = set()
if os.path.exists(OUT):
    for line in open(OUT, encoding="utf-8"):
        try: existing.add(json.loads(line)["id"])
        except Exception: pass

added = 0
with open(OUT, "a", encoding="utf-8") as f:
    for e in entries:
        if e["id"] in existing:
            print(f"  跳过（已存在）: {e['id']}")
            continue
        f.write(json.dumps(e, ensure_ascii=False) + "\n")
        added += 1
        print(f"  ✅ {e['id']}  {e['activity']:<14} {e['result_summary'][:50]}")

print(f"\n新增 {added} 条 -> {OUT}")

# ── schema 自检 ──
req = ["id", "at", "activity", "evidence", "outcome", "verifiable"]
ALLOWED = {"read_text","watch_video","browse_feed","write_diary","record_memory",
           "compare_judgments","explore_topic","organize_index","reflect"}
rows = [json.loads(l) for l in open(OUT, encoding="utf-8") if l.strip()]
print(f"\n=== 自检（共 {len(rows)} 条）===")
bad = 0
for r in rows:
    for k in req:
        if k not in r:
            print(f"  ❌ {r.get('id')} 缺 {k}"); bad += 1
    if r.get("activity") not in ALLOWED:
        print(f"  ❌ {r.get('id')} activity 非法: {r.get('activity')}"); bad += 1
    if r.get("activity") == "reflect" and not r.get("refs"):
        print(f"  ❌ {r.get('id')} reflect 必须带 refs"); bad += 1
    if r.get("verifiable") and not (r.get("evidence") or {}).get("path"):
        print(f"  ❌ {r.get('id')} verifiable 但无 evidence.path"); bad += 1
print(f"  违规 {bad} 处 -> {'✅ 全部通过' if bad == 0 else '❌'}")
