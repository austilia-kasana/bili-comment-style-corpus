# -*- coding: utf-8 -*-
# Task 09：单条补跑（JSON 解析失败时用）
# 从工作区整理入库；硬编码路径已改为环境变量。
"""补跑单条失败记录（B008 seq2）"""

import os

REPO = os.environ.get("BILI_REPO", os.path.expanduser("~/bili-comment-style-corpus"))
CORPUS = os.environ.get("BILI_CORPUS", os.path.expanduser("~/bili-corpus"))

import json, os, re, sys, csv, time, hashlib, datetime, urllib.request, urllib.error
sys.stdout.reconfigure(encoding="utf-8")

LOCAL = os.path.join(REPO, "local")
MAN = os.path.join(LOCAL, "text_batch_manifest.csv")
OUT = os.path.join(LOCAL, "text_analysis.jsonl")
RAW = os.path.join(CORPUS, "data", "raw.jsonl")
TARGET = "883417185903443977"

cred = os.path.join(os.path.expanduser("~"), ".dsh", ".credentials.yaml")
KEY = re.search(r"DEEPSEEK_API_KEY:\s*(\S+)", open(cred, encoding="utf-8").read()).group(1).strip()
MODEL = "deepseek-flash"
ENDPOINT = "https://api.deepseek.com/v1/chat/completions"

# 找目标行
rows = list(csv.DictReader(open(MAN, encoding="utf-8-sig")))
rec = next((r for r in rows if r["record_id"] == TARGET), None)
if not rec:
    print("找不到目标记录"); sys.exit(1)
print(f"目标: {rec['batch_id']} seq{rec['batch_seq']} line={rec['raw_line']}")

# 取原文
raw_line = int(rec["raw_line"])
txt = ""
with open(RAW, encoding="utf-8") as f:
    for i, line in enumerate(f, 1):
        if i == raw_line:
            it = (json.loads(line).get("item") or {})
            md = (it.get("modules") or {}).get("module_dynamic") or {}
            desc = md.get("desc")
            if isinstance(desc, dict) and (desc.get("text") or "").strip():
                txt = desc["text"].strip()
            else:
                major = md.get("major") or {}
                opus = major.get("opus") or {}
                summ = opus.get("summary") or {}
                if (summ.get("text") or "").strip():
                    txt = summ["text"].strip()
                else:
                    draw = major.get("draw") or {}
                    parts = [(x.get("description") or "").strip() for x in (draw.get("items") or [])]
                    txt = "\n".join(p for p in parts if p)
            break
print(f"原文长度: {len(txt)}")

SYSTEM = """你是文本标注器。对给定记录输出一个 JSON 对象（不是数组），不要任何多余文字。

硬规则：
1. 不确定填 "unknown"，不要猜。
2. 区分：原文事实 / 作者明确观点 / 你的推断。
3. counterevidence 至少一条。
4. 不做心理诊断。

字段：
{"topic":{"primary":字符串或null,"basis":"explicit_in_text|inferred_from_text|unknown"},
"emotion_signals":{"valence":"positive|negative|mixed|neutral|unknown","intensity":"low|medium|high|unknown","labels":[≤4个],"quoted_cues":[≤30字,≤3条],"basis":"explicit|tone_only|insufficient"},
"salience":{"importance":"low|medium|high|unknown","reasons":[...],"basis":"explicit|inferred|unknown"},
"value_tension":{"present":布尔,"poles":[≤2条],"basis":"explicit|inferred|none"},
"life_event":{"described":布尔,"summary":字符串或null,"time_reference":字符串或null,"basis":"stated|implied|none"},
"interpretation":{"text":字符串或null,"kind":"restatement|inference|speculation|none"},
"counterevidence":[字符串,至少1条],
"confidence":"low|medium|high"}"""

body = json.dumps({
    "model": MODEL,
    "messages": [{"role": "system", "content": SYSTEM},
                 {"role": "user", "content": f"记录（发布于 {(rec['pub_iso'] or '')[:7]}）：\n{txt}"}],
    "temperature": 0,
    "max_tokens": 4096,
}, ensure_ascii=False).encode()

req = urllib.request.Request(ENDPOINT, data=body, method="POST", headers={
    "Authorization": "Bearer " + KEY, "Content-Type": "application/json"})

content = ""
usage = {}
for attempt in range(3):
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            j = json.loads(r.read().decode())
        content = j["choices"][0]["message"].get("content") or ""
        usage = j.get("usage") or {}
        break
    except Exception as e:
        print(f"  第{attempt+1}次失败: {e}")
        time.sleep(3)

def extract_obj(s):
    s = (s or "").strip()
    s = re.sub(r"^```(?:json)?\s*", "", s)
    s = re.sub(r"\s*```$", "", s)
    a, b = s.find("{"), s.rfind("}")
    if a >= 0 and b > a:
        try: return json.loads(s[a:b+1])
        except Exception: pass
    return None

obj = extract_obj(content)
if not obj:
    print("❌ 仍解析失败，原始输出前 300 字：")
    print(content[:300])
    sys.exit(1)

print(f"✅ 解析成功 conf={obj.get('confidence')} valence={(obj.get('emotion_signals') or {}).get('valence')}")

tin = usage.get("prompt_tokens") or 0
tout = usage.get("completion_tokens") or 0
cost = tin/1e6*0.5 + tout/1e6*1.5
print(f"token: in={tin} out={tout}  cost=¥{cost:.4f}")

# 追加（幂等）
existing = set()
if os.path.exists(OUT):
    for line in open(OUT, encoding="utf-8"):
        try: existing.add(json.loads(line)["source_id"])
        except Exception: pass

if TARGET in existing:
    print("已存在，跳过写入")
    sys.exit(0)

row = {
    "source_id": rec["record_id"],
    "batch_id": rec["batch_id"],
    "sha256_16": rec["sha256_16"],
    "review_status": "analyzed",
    "confidence": obj.get("confidence", "low"),
    "analyzed_at": datetime.datetime.now().isoformat(timespec="seconds"),
    "topic": obj.get("topic"),
    "emotion_signals": obj.get("emotion_signals"),
    "salience": obj.get("salience"),
    "value_tension": obj.get("value_tension"),
    "life_event": obj.get("life_event"),
    "interpretation": obj.get("interpretation"),
    "counterevidence": obj.get("counterevidence") or ["未搜寻到"],
    "analyzer": {"kind": "model", "model": MODEL, "cost_cny": round(cost, 6)},
}
with open(OUT, "a", encoding="utf-8") as f:
    f.write(json.dumps(row, ensure_ascii=False) + "\n")
print(f"已追加 -> {OUT}")

# 更新清单
for r in rows:
    if r["record_id"] == TARGET:
        r["processed"] = "1"
        r["output_version"] = "v1"
with open(MAN, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=rows[0].keys())
    w.writeheader(); w.writerows(rows)
print("清单已更新")
