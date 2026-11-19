# -*- coding: utf-8 -*-
"""
Task 10：用 schema v2 重跑全量分析
相对 05_run_analysis.py 的改进：
  ① 每处理完一条立即 flush（修 §4.1 崩溃丢进度）
  ② 启动时读已有输出，跳过已完成（修 §4.2 重复条目）
  ③ 极短文本（<5 字）直接标 skipped，不浪费调用
  ④ 解析失败自动重试一次（更严格的指令）
输出：local/text_analysis.v2.jsonl（不覆盖 v1）
"""
import os
import json, re, sys, csv, time, hashlib, datetime, urllib.request, urllib.error

REPO = os.environ.get("BILI_REPO", os.path.expanduser("~/bili-comment-style-corpus"))
CORPUS = os.environ.get("BILI_CORPUS", os.path.expanduser("~/bili-corpus"))

sys.stdout.reconfigure(encoding="utf-8")

LOCAL = os.path.join(REPO, "local")
MAN = os.path.join(LOCAL, "text_batch_manifest.csv")
RAW = os.path.join(CORPUS, "data", "raw.jsonl")
# 版本化输出：v2 与 v2.1 不互相覆盖
VERSION = os.environ.get("BILI_SCHEMA_VERSION", "2.1")
OUT = os.path.join(LOCAL, "text_analysis.v2.jsonl" if VERSION == "2" else "text_analysis.v2.1.jsonl")

cred = os.path.join(os.path.expanduser("~"), ".dsh", ".credentials.yaml")
KEY = re.search(r"DEEPSEEK_API_KEY:\s*(\S+)", open(cred, encoding="utf-8").read()).group(1).strip()
MODEL = "deepseek-flash"
ENDPOINT = "https://api.deepseek.com/v1/chat/completions"

SYSTEM = """你是文本标注器。对给定的一条记录输出一个 JSON 对象（不是数组），不要任何多余文字。

硬规则：
1. 不确定就填 "unknown"，不要猜。unknown 是合法答案。
2. 严格区分三类：原文事实 / 作者明确表达的观点 / 你的推断。
3. counterevidence 至少一条；确实没有就写「未搜寻到」。
4. 不做心理诊断，不根据一句话断言性格。
5. 只输出 JSON，不要 markdown 代码块。

字段说明：

topic.category（必须从这 13 个里选一个）：
  body=身体与生理（不适/困倦/疼痛/饥饿/生病/睡眠）
  mood=情绪与心理状态（低落/焦虑/恐惧/压抑/孤独）
  self=自我评价与改变（自责/能力评价/想变强/反思/人生）
  desire=欲望与渴望（对角色或人的喜爱/性/想吃）
  relationship=人际关系（家人/同事/朋友/信任/拉黑）
  work_money=工作与经济（求职/收入/省钱/贷款/兼职）
  daily=日常生活琐事（做饭/购物/起居/小意外）
  media=游戏与二次元（游戏/番剧/角色/账号/社区）
  creation=创作与写作（写作/剧情规划/翻译）
  society=社会观察与评论（政策/道德/战争/垄断/公平）
  knowledge=知识追问（物理/科学/哲学问题）
  dream=梦境
  unknown=确实无法归入以上任何一类
topic.secondary：最多 2 个次要类别，确实只有一类时给 []
topic.detail：一句话描述这条具体讲了什么，**不超过 40 字**
topic.basis：explicit_in_text | inferred_from_text | unknown

emotion_signals.labels（多选，最多 4 个）：
  joy sadness anger fear anxiety loneliness fatigue relief gratitude
  nostalgia numbness confusion hope
  disgust（厌恶） self_deprecation（自嘲） irony（反讽/黑色幽默）
  anticipation（期待） affection（喜爱亲近） admiration（赞叹）
  helplessness（无力） playfulness（调侃戏谑）
  frustration（挫败）
  unknown（唯一表示「无法命名」的值，不要用 other）

⚠️ frustration 与 helplessness 的区别，务必分清：
  frustration  = 想做成某件事，但被外部条件挡住；伴有烦躁、不甘、想再试
  helplessness = 明知无法改变现状，连尝试的力气都没有；伴有认命、疲惫、沉默

⚠️ 这两个标签**不得同时使用**。只能二选一：
  - 有「不服气 / 想再试」的成分 → 用 frustration
  - 有「算了 / 改变不了」的成分 → 用 helplessness
  - 两种都有时，选**主导**的那个，另一种写进 counterevidence
emotion_signals.valence: positive | negative | mixed | neutral | unknown
emotion_signals.intensity: low | medium | high | unknown
emotion_signals.quoted_cues: 支撑判断的原文片段，每条≤30字，最多3条
emotion_signals.basis: explicit | tone_only | insufficient

salience.importance: low | medium | high | unknown
salience.reasons: life_event_stated value_conflict_stated repeated_theme high_emotional_load reflects_change unusual_for_author no_signal
salience.basis: explicit | inferred | unknown

value_tension: {present:布尔, poles:[最多2条,每条≤40字], basis:"explicit|inferred|none"}
life_event: {described:布尔, summary:字符串或null, time_reference:字符串或null, basis:"stated|implied|none"}
interpretation（必须给，不能省略）: {text:字符串或null, kind:"restatement|inference|speculation|none"}
counterevidence: [字符串, 至少1条]
confidence: low | medium | high

完整示例结构：
{"topic":{"category":"body","secondary":["mood"],"detail":"身体不适导致情绪低落","basis":"explicit_in_text"},"emotion_signals":{"valence":"negative","intensity":"medium","labels":["fatigue","frustration"],"quoted_cues":["好累"],"basis":"explicit"},"salience":{"importance":"low","reasons":["high_emotional_load"],"basis":"inferred"},"value_tension":{"present":false,"poles":[],"basis":"none"},"life_event":{"described":false,"summary":null,"time_reference":null,"basis":"none"},"interpretation":{"text":"表达持续疲惫","kind":"inference"},"counterevidence":["也可能只是随口抱怨"],"confidence":"medium"}"""


def dur_ok_text(t):
    return t


def load_manifest():
    return list(csv.DictReader(open(MAN, encoding="utf-8-sig")))


def load_raw_index():
    """行号 -> 文本（一次读完，避免重复 IO）"""
    need = {}
    rows = load_manifest()
    lines = {int(r["raw_line"]) for r in rows}
    with open(RAW, encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            if i in lines:
                need[i] = line.strip()
    return need


def extract_text(raw_line_str):
    raw = json.loads(raw_line_str)
    it = raw.get("item") or {}
    md = (it.get("modules") or {}).get("module_dynamic") or {}
    desc = md.get("desc")
    if isinstance(desc, dict) and (desc.get("text") or "").strip():
        return desc["text"].strip()
    major = md.get("major") or {}
    opus = major.get("opus") or {}
    summ = opus.get("summary") or {}
    if (summ.get("text") or "").strip():
        return summ["text"].strip()
    draw = major.get("draw") or {}
    parts = [(x.get("description") or "").strip() for x in (draw.get("items") or [])]
    return "\n".join(p for p in parts if p)


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
            return j["choices"][0]["message"].get("content") or "", j.get("usage") or {}
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}: {e.read().decode()[:200]}"
            if e.code in (429, 500, 502, 503, 504):
                time.sleep(3 * (a + 1)); continue
            raise RuntimeError(last)
        except Exception as e:
            last = str(e); time.sleep(3 * (a + 1))
    raise RuntimeError("重试耗尽: " + str(last))


def extract_obj(s):
    s = (s or "").strip()
    s = re.sub(r"^```(?:json)?\s*", "", s)
    s = re.sub(r"\s*```$", "", s)
    a, b = s.find("{"), s.rfind("}")
    if a >= 0 and b > a:
        try:
            return json.loads(s[a:b + 1])
        except Exception:
            pass
    return None


def normalize(obj):
    """补齐 + 校验，返回 (obj, 问题列表)"""
    problems = []
    # topic
    t = obj.get("topic")
    if not isinstance(t, dict):
        t = {"category": "unknown", "basis": "unknown"}
        problems.append("topic 缺失")
    if t.get("category") == "other":
        t["category"] = "unknown"
        problems.append("category=other → unknown")
    if t.get("category") not in (
        "body","mood","self","desire","relationship","work_money","daily",
        "media","creation","society","knowledge","dream","unknown"):
        problems.append(f"category 非法: {t.get('category')}")
        t["category"] = "unknown"
    if not isinstance(t.get("secondary"), list):
        t["secondary"] = []
    t["secondary"] = [x for x in t["secondary"][:2] if x != t.get("category")][:2]
    d = t.get("detail")
    if d is not None:
        t["detail"] = str(d)[:40]
    if "basis" not in t:
        t["basis"] = "unknown"
    obj["topic"] = t

    # emotion
    e = obj.get("emotion_signals")
    if not isinstance(e, dict):
        e = {"valence": "unknown", "basis": "insufficient"}
        problems.append("emotion_signals 缺失")
    ls = e.get("labels") or []
    if isinstance(ls, str):
        ls = [ls]
    ls = [x for x in ls if x != "other"][:4]
    # v2.1：frustration 与 helplessness 互斥，若同时出现保留较窄的 helplessness
    if "frustration" in ls and "helplessness" in ls:
        ls = [x for x in ls if x != "frustration"]
        problems.append("frustration+helplessness 同时出现 → 保留 helplessness")
    e["labels"] = ls
    if "valence" not in e:
        e["valence"] = "unknown"
    if "basis" not in e:
        e["basis"] = "insufficient"
    obj["emotion_signals"] = e

    # interpretation 必填
    it = obj.get("interpretation")
    if not isinstance(it, dict):
        it = {"text": None, "kind": "none"}
        problems.append("interpretation 缺失 → 补 none")
    if it.get("kind") not in ("restatement", "inference", "speculation", "none"):
        it["kind"] = "none"
    obj["interpretation"] = it

    # counterevidence 至少 1
    ce = obj.get("counterevidence")
    if not isinstance(ce, list) or not ce:
        obj["counterevidence"] = ["未搜寻到"]
        problems.append("counterevidence 空 → 补")
    else:
        obj["counterevidence"] = [str(x)[:200] for x in ce[:3]]

    if obj.get("confidence") not in ("low", "medium", "high"):
        obj["confidence"] = "low"

    for k in ("salience", "value_tension", "life_event"):
        if not isinstance(obj.get(k), dict):
            defaults = {
                "salience": {"importance": "unknown", "reasons": ["no_signal"], "basis": "unknown"},
                "value_tension": {"present": False, "poles": [], "basis": "none"},
                "life_event": {"described": False, "summary": None, "time_reference": None, "basis": "none"},
            }
            obj[k] = defaults[k]
            problems.append(f"{k} 缺失 → 补默认")
    return obj, problems


def main():
    rows = load_manifest()
    print(f"批次清单: {len(rows)} 条")

    done = set()
    if os.path.exists(OUT):
        for line in open(OUT, encoding="utf-8"):
            try:
                done.add(json.loads(line)["source_id"])
            except Exception:
                pass
    todo = [r for r in rows if r["record_id"] not in done]
    LIMIT = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    if LIMIT > 0:
        todo = todo[:LIMIT]
        print(f"⚠️ 限制模式：只跑前 {LIMIT} 条")
    print(f"已完成 {len(done)}，待跑 {len(todo)}")
    if not todo:
        print("全部已完成"); return

    raw_index = load_raw_index()
    print("原文已载入\n")

    tin = tout = 0
    ok = skip = fail = 0
    t0 = time.time()

    with open(OUT, "a", encoding="utf-8") as f:
        for n, rec in enumerate(todo, 1):
            rid = rec["record_id"]
            line_no = int(rec["raw_line"])
            txt = extract_text(raw_index.get(line_no, "{}"))

            # 极短文本直接跳过
            if len(txt) < 5:
                row = {
                    "schema_version": "2.0.0",
                    "source_id": rid, "batch_id": rec["batch_id"],
                    "sha256_16": rec["sha256_16"],
                    "review_status": "skipped",
                    "skipped_reason": f"原文仅 {len(txt)} 字，无归纳价值",
                    "confidence": "low",
                    "analyzed_at": datetime.datetime.now().isoformat(timespec="seconds"),
                    "topic": {"category": "unknown", "secondary": [], "detail": None, "basis": "unknown"},
                    "emotion_signals": {"valence": "unknown", "intensity": "unknown", "labels": [], "quoted_cues": [], "basis": "insufficient"},
                    "salience": {"importance": "unknown", "reasons": ["no_signal"], "basis": "unknown"},
                    "value_tension": {"present": False, "poles": [], "basis": "none"},
                    "life_event": {"described": False, "summary": None, "time_reference": None, "basis": "none"},
                    "interpretation": {"text": None, "kind": "none"},
                    "counterevidence": ["原文过短"],
                    "analyzer": {"kind": "local_rule", "model": None, "cost_cny": 0},
                }
                f.write(json.dumps(row, ensure_ascii=False) + "\n"); f.flush()
                skip += 1
                print(f"  [{n}/{len(todo)}] SKIP  len={len(txt)}")
                continue

            prompt = f"记录（发布于 {(rec['pub_iso'] or '')[:7]}）：\n{txt}"
            try:
                content, usage = call(prompt)
                obj = extract_obj(content)
                if not obj:
                    # 重试一次，更严格
                    content2, usage2 = call(prompt + "\n\n再次强调：只输出一个 JSON 对象，不要数组，不要解释。")
                    obj = extract_obj(content2)
                    tin += usage2.get("prompt_tokens") or 0
                    tout += usage2.get("completion_tokens") or 0
                if not obj:
                    raise RuntimeError("JSON 解析失败")
                tin += usage.get("prompt_tokens") or 0
                tout += usage.get("completion_tokens") or 0
                obj, problems = normalize(obj)
                row = {
                    "schema_version": "2.0.0",
                    "source_id": rid, "batch_id": rec["batch_id"],
                    "sha256_16": rec["sha256_16"],
                    "review_status": "analyzed",
                    "confidence": obj["confidence"],
                    "analyzed_at": datetime.datetime.now().isoformat(timespec="seconds"),
                    "topic": obj["topic"],
                    "emotion_signals": obj["emotion_signals"],
                    "salience": obj["salience"],
                    "value_tension": obj["value_tension"],
                    "life_event": obj["life_event"],
                    "interpretation": obj["interpretation"],
                    "counterevidence": obj["counterevidence"],
                    "analyzer": {"kind": "model", "model": MODEL},
                    "_provisional": {"emotion_enum": True,
                                     "note": "情绪枚举 v2 新增标签依据 13 条样本推断，未验证"},
                }
                if problems:
                    row["_normalized"] = problems
                f.write(json.dumps(row, ensure_ascii=False) + "\n"); f.flush()
                ok += 1
                cat = obj["topic"]["category"]
                val = obj["emotion_signals"]["valence"]
                flag = (" ⚠" + str(len(problems))) if problems else ""
                print(f"  [{n}/{len(todo)}] {cat:<12} {val:<9}{flag}")
            except Exception as e:
                fail += 1
                print(f"  [{n}/{len(todo)}] ❌ {str(e)[:80]}")

    el = time.time() - t0
    cost = tin / 1e6 * 0.5 + tout / 1e6 * 1.5
    print(f"\n=== 统计 ===")
    print(f"  耗时       {el:.0f}s")
    print(f"  成功 {ok}  跳过 {skip}  失败 {fail}")
    print(f"  输入 {tin:,}  输出 {tout:,}  token")
    print(f"  本次成本   ¥{cost:.4f}")
    print(f"  输出       {OUT}")


if __name__ == "__main__":
    main()
