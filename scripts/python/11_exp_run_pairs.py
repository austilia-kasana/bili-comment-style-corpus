# -*- coding: utf-8 -*-
# Task 07 偏好盲测：30 组二选一
# 从工作区整理入库；硬编码路径已改为环境变量。
"""
run_pairs_v2.py —— 第一阶段修正版
改动：
  1. max_tokens 提到 1024（deepseek-flash 是推理模型，8 个 token 不够）
  2. 提示词明确排除"预测点击率"，要求第一人称偏好
  3. 记录 reasoning_content 作为辅助材料（不参与评分）
  4. 写入 picks_v2.jsonl（旧的 picks.jsonl 保留为 bug 记录）
"""

import os

REPO = os.environ.get("BILI_REPO", os.path.expanduser("~/bili-comment-style-corpus"))
CORPUS = os.environ.get("BILI_CORPUS", os.path.expanduser("~/bili-corpus"))

import json, os, re, sys, time, hashlib, datetime, urllib.request, urllib.error
sys.stdout.reconfigure(encoding="utf-8")

BASE = os.path.join(os.path.expanduser("~"), "Documents", "deepseek-harness", "default-workspace")
RUN = sys.argv[1]
cred = os.path.join(os.path.expanduser("~"), ".dsh", ".credentials.yaml")
KEY = re.search(r"DEEPSEEK_API_KEY:\s*(\S+)", open(cred, encoding="utf-8").read()).group(1).strip()

MODEL = "deepseek-flash"
ENDPOINT = "https://api.deepseek.com/v1/chat/completions"
TEMPERATURE = 0
MAX_TOKENS = 1024
SYSTEM = (
    "你在做一组二选一。\n"
    "重要：不要预测哪条更容易火、哪条播放量更高、别人会点哪条。\n"
    "只回答：你自己现在更想点开哪一个。\n"
    "只输出一个字母 A 或 B，不要任何解释、标点或空格。"
)

pairs = json.load(open(os.path.join(RUN, "pairs.json"), encoding="utf-8"))
batch = json.load(open(os.path.join(RUN, "batch.json"), encoding="utf-8"))

def card(i):
    it = batch[i]
    d = it["duration_sec"]
    line = f"《{it['title']}》({d//60}分{d%60:02d}秒)"
    if it.get("desc"):
        line += f"\n简介：{it['desc'][:160]}"
    return line

def ask(prompt, retries=4):
    body = json.dumps({
        "model": MODEL,
        "messages": [{"role": "system", "content": SYSTEM},
                     {"role": "user", "content": prompt}],
        "temperature": TEMPERATURE,
        "max_tokens": MAX_TOKENS,
    }, ensure_ascii=False).encode()
    req = urllib.request.Request(ENDPOINT, data=body, method="POST", headers={
        "Authorization": "Bearer " + KEY, "Content-Type": "application/json"})
    last = None
    for a in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                j = json.loads(r.read().decode())
            m = j["choices"][0]["message"]
            return m.get("content") or "", m.get("reasoning_content") or "", j.get("usage")
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}: {e.read().decode()[:150]}"
            if e.code in (429, 500, 502, 503, 504):
                time.sleep(2 * (a + 1)); continue
            raise RuntimeError(last)
        except Exception as e:
            last = str(e); time.sleep(2 * (a + 1))
    raise RuntimeError("重试耗尽: " + str(last))

out = os.path.join(RUN, "picks_v2.jsonl")
done = set()
if os.path.exists(out):
    for line in open(out, encoding="utf-8"):
        try: done.add(json.loads(line)["pair_id"])
        except Exception: pass
print(f"已有 {len(done)}，待跑 {len(pairs)-len(done)}")

def norm_answer(s):
    s = (s or "").strip().upper()
    for ch in s:
        if ch in ("A", "B"):
            return ch
    return None

with open(out, "a", encoding="utf-8") as f:
    for p in pairs:
        if p["pair_id"] in done:
            continue
        prompt = (
            "下面两条视频，只根据标题、简介和时长判断。\n\n"
            f"A：{card(p['left'])}\n\n"
            f"B：{card(p['right'])}\n\n"
            "不是猜哪条更火、也不是猜别人会点哪条——是你自己现在更想点开哪一个？只回答 A 或 B。"
        )
        t0 = time.time()
        try:
            raw, reasoning, usage = ask(prompt)
            ans = norm_answer(raw)
        except Exception as e:
            raw, reasoning, usage, ans = f"ERROR: {e}", "", None, None
        chosen = p["left"] if ans == "A" else (p["right"] if ans == "B" else None)
        rec = {
            "pair_id": p["pair_id"], "order": p["order"], "round": p["round"],
            "left_idx": p["left"], "right_idx": p["right"],
            "left_bvid": batch[p["left"]]["bvid"], "right_bvid": batch[p["right"]]["bvid"],
            "cross_pool": p["cross_pool"],
            "answer": ans, "valid": ans in ("A", "B"), "chosen_idx": chosen,
            "raw": raw,
            "reasoning_aux": reasoning[:1200],
            "model": MODEL, "temperature": TEMPERATURE, "max_tokens": MAX_TOKENS,
            "system_prompt": SYSTEM, "user_prompt": prompt,
            "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest()[:16],
            "usage": usage,
            "elapsed_ms": int((time.time() - t0) * 1000),
            "at": datetime.datetime.now().isoformat(timespec="seconds"),
        }
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        f.flush()
        print(f"  [{p['pair_id']:>2}/{len(pairs)}] {ans or '?'}  ({rec['elapsed_ms']}ms)")

print(f"\n✅ -> {out}")
