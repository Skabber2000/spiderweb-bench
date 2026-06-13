#!/usr/bin/env python
"""
Blind judge panel for SpiderWeb_Bench (methodology v2).

These submissions are CODE artifacts, so behaviour is fully determined by the source.
- TEXT judges read the full HTML source and score the 6 FUNCTIONAL criteria
  (spec, weave, web->neural, firing, code, perf) — these are verifiable from code and
  do not depend on catching the right animation frame.
- VISION judges view a 4-phase montage and score ONLY visual POLISH — the one criterion
  that genuinely needs eyes and that a still can fairly assess.
Submissions are shown under random blind letters; a judge never scores its own family.
Per-criterion scores are averaged across judges, then weighted per RUBRIC.md to /100.

Keys: OPENAI_API_KEY, XAI_API_KEY, DEEPSEEK_API_KEY (text); + GEMINI_API_KEY (vision).
Usage: python judge_panel.py   ->  scores/eval_results.json + scores/evaluation.md
"""
import os, json, re, base64, time, pathlib, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent
JUDGE_IMG = ROOT / "media" / "judge"
SUBS = ROOT / "submissions"

MODELS = [  # id, display, family
    ("claude-opus-4.8","Claude Opus 4.8","claude"),
    ("gpt-5.5","GPT-5.5","gpt"),
    ("grok-4","Grok 4","grok"),
    ("gemini-3-pro","Gemini 3.5 Flash","gemini"),
    ("glm-5.1","GLM-5.1","glm"),
    ("deepseek-v4","DeepSeek V4 Pro","deepseek"),
    ("minimax-m3","MiniMax M3","minimax"),
    ("mistral-large","Mistral Large","mistral"),
]
BLIND = {"gpt-5.5":"A","deepseek-v4":"B","gemini-3-pro":"C","mistral-large":"D",
         "claude-opus-4.8":"E","glm-5.1":"F","minimax-m3":"G","grok-4":"H"}

FUNC_CRIT = [
 ("spec","all four phases present & correct in code: 800x800 single-file canvas; (1) spider weaves a web, (2) the web becomes a node+edge neural network, (3) signals/dissolve, (4) genuinely loops"),
 ("weave","weaving believability in code: a spider sprite that visibly CONSTRUCTS the web thread-by-thread (radials then spiral, sprite follows the drawn thread), not a web that just fades/pops in"),
 ("trans","web->neural fidelity: the neural nodes/edges are DERIVED FROM the woven web geometry (same intersections / the actual threads become edges), not an unrelated random graph"),
 ("fire","neural firing: signals are animated travelling ALONG edges between nodes, with propagation/branching or node activation — not static lines or random dots"),
 ("code","code quality: single self-contained file, no external deps, no obvious bugs, readable, sensible structure"),
 ("perf","performance: efficient requestAnimationFrame loop, bounded allocations, arrays/particles reset between loops (no unbounded growth/leaks), ~60fps feasible"),
]
VIS_CRIT = [("polish","visual polish & art direction: palette, glow/bloom, depth, composition, motion quality — does the rendered result look like a finished, intentional piece")]
WEIGHTS = {"spec":20,"weave":15,"trans":15,"fire":15,"polish":15,"code":10,"perf":10}

TEXT_JUDGES = [
    dict(name="gpt-5.5",  env="OPENAI_API_KEY",  base="https://api.openai.com/v1", model="gpt-5.5",        family="gpt"),
    dict(name="grok-4",   env="XAI_API_KEY",     base="https://api.x.ai/v1",       model="grok-4",         family="grok"),
    dict(name="deepseek", env="DEEPSEEK_API_KEY",base="https://api.deepseek.com",  model="deepseek-v4-pro",family="deepseek"),
]
VISION_JUDGES = [
    dict(name="gpt-5.5",      kind="openai", env="OPENAI_API_KEY", base="https://api.openai.com/v1", model="gpt-5.5",          family="gpt"),
    dict(name="grok-4",       kind="openai", env="XAI_API_KEY",    base="https://api.x.ai/v1",       model="grok-4",           family="grok"),
    dict(name="gemini-flash", kind="gemini", env="GEMINI_API_KEY", base="https://generativelanguage.googleapis.com/v1beta", model="gemini-3.5-flash", family="gemini"),
]

def post(url, headers, payload, timeout=600):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())

def parse_scores(text, keys):
    m = re.search(r"\{.*\}", text or "", re.S)
    if not m: return None
    try: obj = json.loads(m.group(0))
    except Exception: return None
    out = {k: max(0.0,min(10.0,float(obj[k]))) for k in keys if isinstance(obj.get(k),(int,float))}
    return out or None

def b64(p): return base64.b64encode(pathlib.Path(p).read_bytes()).decode()
def crit_text(c): return "\n".join(f"- {k}: {d}" for k,d in c)

def openai_chat(j, key, content, vision=False):
    url = j["base"] + "/chat/completions"
    h = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    p = {"model": j["model"], "messages":[{"role":"user","content":content}]}
    if "api.openai.com" in j["base"]: p["max_completion_tokens"] = 8000
    else: p["max_tokens"] = 4000; p["temperature"] = 0.2
    r = post(url, h, p)
    msg = r["choices"][0]["message"]
    return msg.get("content") or msg.get("reasoning_content") or ""

def text_call(j, key, letter, html):
    prompt = (f"You are an impartial judge in a blind benchmark. Submission '{letter}' is the SOURCE "
        "of a single-file HTML <canvas> animation that should: spider weaves an orb web -> the web's "
        "threads become a glowing neural network with signals firing between nodes -> dissolves -> loops. "
        "Judge ONLY from the code. Score each 0-10 (10=excellent, 0=absent/broken); be critical and use "
        "the full range.\n\nCRITERIA:\n" + crit_text(FUNC_CRIT) +
        "\n\nReturn ONLY JSON: {\"spec\":n,\"weave\":n,\"trans\":n,\"fire\":n,\"code\":n,\"perf\":n}\n\n"
        "--- SOURCE ---\n" + html[:48000])
    return parse_scores(openai_chat(j, key, prompt), [k for k,_ in FUNC_CRIT])

def vision_call(j, key, letter, img):
    prompt = (f"You are an impartial judge in a blind benchmark. The 4 images are frames sampled across "
        f"one run of submission '{letter}', an HTML <canvas> animation (spider->web->glowing neural "
        "network->dissolve->loop). Judge ONLY visual polish & art direction from what you see. Score 0-10 "
        "(10=looks like a finished, intentional, beautiful piece; 0=crude/ugly). Be critical.\n\nCRITERION:\n"
        + crit_text(VIS_CRIT) + "\n\nReturn ONLY JSON: {\"polish\":n}")
    if j["kind"] == "openai":
        content = [{"type":"text","text":prompt},
                   {"type":"image_url","image_url":{"url":"data:image/png;base64,"+b64(img)}}]
        return parse_scores(openai_chat(j, key, content, vision=True), ["polish"])
    else:
        url = f'{j["base"]}/models/{j["model"]}:generateContent?key={key}'
        p = {"contents":[{"role":"user","parts":[{"text":prompt},
             {"inline_data":{"mime_type":"image/png","data":b64(img)}}]}],
             "generationConfig":{"temperature":0.2,"maxOutputTokens":3000}}
        r = post(url, {"Content-Type":"application/json"}, p)
        parts = r["candidates"][0].get("content",{}).get("parts",[])
        return parse_scores("".join(x.get("text","") for x in parts), ["polish"])

def main():
    res = {mid:{"display":d,"family":f,"letter":BLIND[mid],"scores":{k:[] for k in WEIGHTS}}
           for mid,d,f in MODELS}
    # functional (text judges read source)
    for j in TEXT_JUDGES:
        key = os.environ.get(j["env"])
        if not key: print(f"[skip text] {j['name']}"); continue
        for mid,d,fam in MODELS:
            if fam == j["family"]: continue
            src = SUBS/mid/"index.html"
            if not src.exists(): continue
            try:
                sc = text_call(j, key, BLIND[mid], src.read_text(encoding="utf-8",errors="ignore"))
                if sc:
                    for k,v in sc.items(): res[mid]["scores"][k].append(v)
                    print(f"  [func] {j['name']:9s}->{BLIND[mid]}: {sc}", flush=True)
                else: print(f"  [func] {j['name']:9s}->{BLIND[mid]}: parse fail", flush=True)
            except Exception as e: print(f"  [func FAIL] {j['name']}->{BLIND[mid]}: {str(e)[:110]}", flush=True)
            time.sleep(1)
    # polish (vision judges)
    for j in VISION_JUDGES:
        key = os.environ.get(j["env"])
        if not key: print(f"[skip vis] {j['name']}"); continue
        for mid,d,fam in MODELS:
            if fam == j["family"]: continue
            img = JUDGE_IMG/f"{mid}.png"
            if not img.exists(): continue
            try:
                sc = vision_call(j, key, BLIND[mid], img)
                if sc:
                    res[mid]["scores"]["polish"].append(sc["polish"])
                    print(f"  [pol]  {j['name']:9s}->{BLIND[mid]}: {sc}", flush=True)
                else: print(f"  [pol]  {j['name']:9s}->{BLIND[mid]}: parse fail", flush=True)
            except Exception as e: print(f"  [pol FAIL] {j['name']}->{BLIND[mid]}: {str(e)[:110]}", flush=True)
            time.sleep(1)
    # aggregate
    table=[]
    for mid,d,fam in MODELS:
        sc=res[mid]["scores"]
        means={k:(round(sum(v)/len(v),2) if v else None) for k,v in sc.items()}
        total=sum((means[k]/10*w) for k,w in WEIGHTS.items() if means[k] is not None)
        res[mid]["means"]=means; res[mid]["total"]=round(total,1)
        res[mid]["n"]={k:len(v) for k,v in sc.items()}
        table.append((d,round(total,1),means))
    table.sort(key=lambda r:-r[1])
    (ROOT/"scores"/"eval_results.json").write_text(json.dumps(res,indent=2),encoding="utf-8")
    L=["# Blind Judge-Panel Evaluation (v2)\n",f"_Generated {time.strftime('%Y-%m-%d %H:%M')}._\n",
       "Functional criteria (spec/weave/trans/fire/code/perf) scored by **text judges from source**; "
       "**polish** by **vision judges** from a 4-phase montage. Blind letters; no model judges its own "
       "family; scores averaged across judges; weighted to /100 per RUBRIC.md.\n",
       "| Rank | Model | Total /100 | spec | weave | trans | fire | polish | code | perf |",
       "|---|---|---|---|---|---|---|---|---|---|"]
    for i,(d,t,m) in enumerate(table,1):
        cells=" | ".join(f"{m[k]:.1f}" if m[k] is not None else "—" for k in ["spec","weave","trans","fire","polish","code","perf"])
        L.append(f"| {i} | {d} | **{t}** | {cells} |")
    (ROOT/"scores"/"evaluation.md").write_text("\n".join(L)+"\n",encoding="utf-8")
    print("\n=== RANKING ===")
    for i,(d,t,m) in enumerate(table,1): print(f"  {i}. {d:18s} {t:5.1f}/100")
    print("\n-> scores/evaluation.md + eval_results.json")

if __name__ == "__main__":
    main()
