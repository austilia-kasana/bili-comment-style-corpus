# -*- coding: utf-8 -*-
# Task 09：逐批调用模型分析
# 从工作区整理入库；硬编码路径已改为环境变量。
"""
run_analysis.py —— 逐批分析原创动态
用法: python run_analysis.py B001 [B002 ...] [--dry]
输出: local/text_analysis.jsonl（追加写入）
"""

import os

REPO = os.environ.get("BILI_REPO", os.path.expanduser("~/bili-comment-style-corpus"))
CORPUS = os.environ.get("BILI_CORPUS", os.path.expanduser("~/bili-corpus"))

import json, os, re, sys, csv, time, hashlib, datetime, urllib.request, urllib.error
sys.stdout.reconfigure(encoding="utf-8")

LOCAL = os.path.join(REPO, "local")
MAN = os.path.join(LOCAL, "text_batch_manifest.csv")
OUT = os.path.join(LOCAL, "text_analysis.jsonl")
RAW = os.path.join(CORPUS, "data", "raw.jsonl")

cred = os.path.join(os.path.expanduser("~"), ".dsh", ".credentials.yaml")
KEY = re.search(r"DEEPSEEK_API_KEY:\s*(\S+)", open(cred, encoding="utf-8").read()).group(1).strip()
MODEL = "deepseek-flash"
ENDPOINT = "https://api.deepseek.com/v1/chat/completions"

args = [a for a in sys.argv[1:] if not a.startswith("--")]
DRY = "--dry" in sys.argv
BATCHES = args or ["B001"]

# ── 读取批次清单 ──
man = list(csv.DictReader(open(MAN, encoding="utf-8-sig")))
todo = [r for r in man if r["batch_id"] in BATCHES]
print(f"选中 {len(todo)} 条记录，来自批次 {BATCHES}")

# ── 按行号取原文（只取该批用到的行）──
need_lines = {int(r["raw_line"]) for r in todo}
texts = {}
with open(RAW, encoding="utf-8") as f:
    for i, line in enumerate(f, 1):
        if i in need_lines:
            texts[i] = line.strip()

def get_text(rec):
    raw = json.loads(texts[int(rec["raw_line"])])
    it = raw.get("item") or {}
    md = (it.get("modules") or {}).get("module_dynamic") or {}
    desc = md.get("desc")
    if isinstance(desc, dict) and (desc.get("text") or "").strip():
        return desc["text"].strip()
    major = md.get("major") or {}
    opus = (major.get("opus") or {})
    summ = (opus.get("summary") or {})
    if (summ.get("text") or "").strip():
        return summ["text"].strip()
    draw = (major.get("draw") or {})
    parts = [(x.get("description") or "").strip() for x in (draw.get("items") or [])]
    return "\n".join(p for p in parts if p)

SYSTEM = """你是一个文本标注器。对给定的每条记录输出一个 JSON 对象。

硬规则：
1. 不确定就填 "unknown"，不要猜。unknown 是合法答案。
2. 区分三类：原文事实 / 作者明确表达的观点 / 你的推断。
3. counterevidence 至少一条；确实没有就写"未搜寻到"。
4. 不写心理诊断，不根据一句话断言性格。
5. 只输出 JSON 数组，不要任何解释、markdown 代码块或前后缀。

每个对象字段：
{"idx":记录序号,"topic":{"primary":字符串或null,"basis":"explicit_in_text|inferred_from_text|unknown"},
"emotion_signals":{"valence":"positive|negative|mixed|neutral|unknown","intensity":"low|medium|high|unknown","labels":[从 joy,sadness,anger,fear,anxiety,loneliness,fatigue,relief,gratitude,nostalgia,frustration,numbness,confusion,hope,other,unknown 中选≤4],"quoted_cues":[≤30字的原文片段,≤3条],"basis":"explicit|tone_only|insufficient"},
"salience":{"importance":"low|medium|high|unknown","reasons":[从 life_event_stated,value_conflict_stated,repeated_theme,high_emotional_load,reflects_change,unusual_for_author,no_signal 中选],"basis":"explicit|inferred|unknown"},
"value_tension":{"present":布尔,"poles":[≤2条,每条≤40字],"basis":"explicit|inferred|none"},
"life_event":{"described":布尔,"summary":字符串或null,"time_reference":字符串或null,"basis":"stated|implied|none"},
"interpretation":{"text":字符串或null,"kind":"restatement|inference|speculation|none"},
"counterevidence":[字符串,至少1条],
"confidence":"low|medium|high"}"""

def call(prompt, retries=3):
    body = json.dumps({
        "model": MODEL,
        "messages": [{"role": "system", "content": SYSTEM},
                     {"role": "user", "content": prompt}],
        "temperature": 0,
        "max_tokens": 4096,
    }, ensure_ascii=False).encode()
    req = urllib.request.Request(ENDPOINT, data=body, method="POST", headers={
        "Authorization": "Bearer " + KEY, "Content-Type": "application/json"})
    last = None
    for a in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                j = json.loads(r.read().decode())
            return j["choices"][0]["message"].get("content") or "", j.get("usage")
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}: {e.read().decode()[:200]}"
            if e.code in (429, 500, 502, 503, 504):
                time.sleep(3 * (a + 1)); continue
            raise RuntimeError(last)
        except Exception as e:
            last = str(e); time.sleep(3 * (a + 1))
    raise RuntimeError("重试耗尽: " + str(last))

def extract_json(s):
    s = s.strip()
    s = re.sub(r"^```(?:json)?\s*", "", s)
    s = re.sub(r"\s*```$", "", s)
    a, b = s.find("["), s.rfind("]")
    if a >= 0 and b > a:
        try: return json.loads(s[a:b+1])
        except Exception: pass
    return None

total_in = total_out = 0
results = []
t0 = time.time()

for rec in todo:
    txt = get_text(rec)
    prompt = f"记录序号 {rec['batch_seq']}（发布于 {(rec['pub_iso'] or '')[:7]}）：\n{txt}"
    try:
        content, usage = call(prompt)
        u = usage or {}
        total_in += u.get("prompt_tokens") or 0
        total_out += u.get("completion_tokens") or 0
        arr = extract_json(content)
        if not arr:
            print(f"  [{rec['batch_seq']}] ❌ JSON 解析失败: {content[:120]!r}")
            results.append({"idx": int(rec["batch_seq"]), "error": "json_parse", "raw": content[:500]})
            continue
        obj = arr[0] if isinstance(arr, list) and arr else (arr if isinstance(arr, dict) else None)
        if not obj:
            results.append({"idx": int(rec["batch_seq"]), "error": "empty"})
            continue
        obj["idx"] = int(rec["batch_seq"])
        results.append(obj)
        print(f"  [{rec['batch_seq']}] ✅ conf={obj.get('confidence')} valence={(obj.get('emotion_signals') or {}).get('valence')}")
    except Exception as e:
        print(f"  [{rec['batch_seq']}] ❌ {e}")
        results.append({"idx": int(rec["batch_seq"]), "error": str(e)[:200]})

elapsed = time.time() - t0
# 成本：输入 ¥0.5/M，输出 ¥1.5/M
cost = total_in/1e6*0.5 + total_out/1e6*1.5
print(f"\n=== 统计 ===")
print(f"  耗时        {elapsed:.1f}s")
print(f"  输入 token  {total_in:,}")
print(f"  输出 token  {total_out:,}")
print(f"  本次成本    ¥{cost:.4f}")
print(f"  成功        {sum(1 for r in results if 'error' not in r)}/{len(results)}")

if DRY:
    print("\n[dry] 未写盘")
    sys.exit(0)

# ── 追加写入 ──
now = datetime.datetime.now().isoformat(timespec="seconds")
with open(OUT, "a", encoding="utf-8") as f:
    for rec, obj in zip(todo, results):
        if "error" in obj:
            continue
        row = {
            "source_id": rec["record_id"],
            "batch_id": rec["batch_id"],
            "sha256_16": rec["sha256_16"],
            "review_status": "analyzed",
            "confidence": obj.get("confidence", "low"),
            "analyzed_at": now,
            "topic": obj.get("topic"),
            "emotion_signals": obj.get("emotion_signals"),
            "salience": obj.get("salience"),
            "value_tension": obj.get("value_tension"),
            "life_event": obj.get("life_event"),
            "interpretation": obj.get("interpretation"),
            "counterevidence": obj.get("counterevidence") or ["未搜寻到"],
            "analyzer": {"kind": "model", "model": MODEL, "cost_cny": round(cost/len(todo), 6)},
        }
        f.write(json.dumps(row, ensure_ascii=False) + "\n")

# ── 更新清单的 processed 标记 ──
done_sha = set()
if os.path.exists(OUT):
    for line in open(OUT, encoding="utf-8"):
        try: done_sha.add(json.loads(line)["sha256_16"])
        except Exception: pass
for r in man:
    if r["sha256_16"] in done_sha and r["processed"] != "1":
        r["processed"] = "1"
        r["output_version"] = "v1"
with open(MAN, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=man[0].keys())
    w.writeheader(); w.writerows(man)
print(f"  已写入 {OUT}")
print(f"  清单 processed 已更新（累计 {len(done_sha)} 条）")
