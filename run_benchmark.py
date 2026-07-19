#!/usr/bin/env python
"""
SpiderWeb_Bench — multi-provider one-shot runner.

Sends the canonical prompt (PROMPT.md) to one or more LLMs, extracts the HTML
from each response, and writes it to submissions/<model-id>/index.html plus a
meta.json with model/latency/token info.

API keys are read from environment variables ONLY (never hardcode secrets).
Set whichever you have; missing-key providers are skipped with a warning.

    OPENAI_API_KEY      -> gpt-5.5            (https://api.openai.com/v1)
    XAI_API_KEY         -> grok-4             (https://api.x.ai/v1)
    GEMINI_API_KEY      -> gemini-3-pro       (Google GenAI)
    ZHIPU_API_KEY       -> glm-5.1            (https://open.bigmodel.cn/api/paas/v4)
    MINIMAX_API_KEY     -> minimax-m2         (https://api.minimax.io/v1)
    MISTRAL_API_KEY     -> mistral-large      (https://api.mistral.ai/v1)
    ANTHROPIC_API_KEY   -> claude (optional; baseline already produced via Claude Code)

All OpenAI-compatible providers go through one code path (urllib, no SDK needed).
Gemini and Anthropic use their own request shapes.

Usage (Windows: use `python`, not `python3`):
    python run_benchmark.py --all
    python run_benchmark.py --models gpt-5.5 grok-4
    python run_benchmark.py --list

NOTE ON MODEL IDS: the exact provider model strings change often. Verify/override
the `model` field in PROVIDERS below against each vendor's current docs before a run.
The benchmark records whatever you actually called.
"""
import os, sys, json, time, re, argparse, urllib.request, urllib.error, pathlib

ROOT = pathlib.Path(__file__).resolve().parent
SUBS = ROOT / "submissions"
PROMPT_FILE = ROOT / "PROMPT.md"

def canonical_prompt() -> str:
    """Extract the fenced prompt block from PROMPT.md (single source of truth)."""
    txt = PROMPT_FILE.read_text(encoding="utf-8")
    blocks = re.findall(r"```(?:\w+)?\n(.*?)```", txt, re.S)
    for b in blocks:
        if "spider" in b.lower() and "canvas" in b.lower():
            return b.strip()
    raise SystemExit("Could not locate the canonical prompt in PROMPT.md")

# id -> how to call it. "kind" selects the request adapter.
PROVIDERS = {
    "gpt-5.5":       dict(kind="openai", env="OPENAI_API_KEY",  base="https://api.openai.com/v1",            model="gpt-5.5",            provider="OpenAI"),
    "grok-4":        dict(kind="openai", env="XAI_API_KEY",     base="https://api.x.ai/v1",                  model="grok-4",             provider="xAI"),
    "glm-5.1":       dict(kind="openai", env="ZHIPU_API_KEY",   base="https://open.bigmodel.cn/api/paas/v4", model="glm-5.1",            provider="Zhipu", maxtok=65000, timeout=600),
    "minimax-m2":    dict(kind="openai", env="MINIMAX_API_KEY", base="https://api.minimax.io/v1",            model="MiniMax-M2",         provider="MiniMax"),
    "mistral-large": dict(kind="openai", env="MISTRAL_API_KEY", base="https://api.mistral.ai/v1",            model="mistral-large-latest",provider="Mistral"),
    "deepseek-v4":   dict(kind="openai", env="DEEPSEEK_API_KEY",base="https://api.deepseek.com",             model="deepseek-v4-pro",    provider="DeepSeek", maxtok=65000, timeout=600),
    "kimi-k3":       dict(kind="openai", env="MOONSHOT_API_KEY",base="https://api.moonshot.ai/v1",           model="kimi-k3",            provider="Moonshot", maxtok=65000, timeout=600, temp=1),
    "gemini-3-pro":  dict(kind="gemini", env="GEMINI_API_KEY",  base="https://generativelanguage.googleapis.com/v1beta", model="gemini-3.5-flash", provider="Google"),
    "claude-opus-4.8":dict(kind="anthropic", env="ANTHROPIC_API_KEY", base="https://api.anthropic.com/v1",   model="claude-opus-4-8",    provider="Anthropic", maxtok=32000, timeout=600),
}

SYSTEM = "You are an expert creative coder. Output only a single complete HTML file. No explanation, no markdown fences."

def _post(url, headers, payload, timeout=180):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))

def call_openai(cfg, key, prompt):
    url = cfg["base"].rstrip("/") + "/chat/completions"
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    payload = {"model": cfg["model"],
               "messages": [{"role": "system", "content": SYSTEM},
                            {"role": "user", "content": prompt}]}
    # OpenAI GPT-5+ reasoning models: use max_completion_tokens, default temperature,
    # and need a larger budget (reasoning tokens count against the cap).
    is_oai_reasoning = "api.openai.com" in cfg["base"] and cfg["model"].startswith(("gpt-5", "o"))
    if is_oai_reasoning:
        payload["max_completion_tokens"] = cfg.get("maxtok", 32000)
    else:
        payload["temperature"] = cfg.get("temp", 0.7)
        payload["max_tokens"] = cfg.get("maxtok", 16000)
    j = _post(url, headers, payload, timeout=cfg.get("timeout", 300))
    msg = j["choices"][0]["message"]
    text = msg.get("content") or ""
    # Thinking models (e.g. GLM) may leave reasoning in a separate field; if the
    # answer field is empty, fall back to reasoning_content so we can salvage HTML.
    if not text.strip():
        text = msg.get("reasoning_content") or ""
    usage = j.get("usage", {})
    return text, usage.get("completion_tokens")

def call_gemini(cfg, key, prompt):
    url = f'{cfg["base"]}/models/{cfg["model"]}:generateContent?key={key}'
    headers = {"Content-Type": "application/json"}
    payload = {"systemInstruction": {"parts": [{"text": SYSTEM}]},
               "contents": [{"role": "user", "parts": [{"text": prompt}]}],
               "generationConfig": {"temperature": 0.7, "maxOutputTokens": 32000}}
    j = _post(url, headers, payload, timeout=cfg.get("timeout", 600))
    parts = j["candidates"][0].get("content", {}).get("parts", [])
    text = "".join(p.get("text", "") for p in parts)
    tok = j.get("usageMetadata", {}).get("candidatesTokenCount")
    return text, tok

def call_anthropic(cfg, key, prompt):
    url = cfg["base"].rstrip("/") + "/messages"
    headers = {"x-api-key": key, "anthropic-version": "2023-06-01", "Content-Type": "application/json"}
    payload = {"model": cfg["model"], "max_tokens": cfg.get("maxtok", 16000),
               "system": SYSTEM, "messages": [{"role": "user", "content": prompt}]}
    j = _post(url, headers, payload, timeout=cfg.get("timeout", 300))
    text = "".join(b.get("text", "") for b in j.get("content", []))
    u = j.get("usage", {})
    return text, u.get("output_tokens")

ADAPTERS = {"openai": call_openai, "gemini": call_gemini, "anthropic": call_anthropic}

def extract_html(text: str) -> str:
    """Pull the HTML doc out of a model response (strip prose / fences)."""
    m = re.search(r"```(?:html)?\s*(.*?)```", text, re.S | re.I)
    if m:
        text = m.group(1)
    i = text.lower().find("<!doctype")
    if i == -1:
        i = text.lower().find("<html")
    if i != -1:
        text = text[i:]
    j = text.lower().rfind("</html>")
    if j != -1:
        text = text[: j + len("</html>")]
    return text.strip()

def run_one(mid, prompt):
    cfg = PROVIDERS[mid]
    key = os.environ.get(cfg["env"])
    if not key:
        print(f"  [skip] {mid}: ${cfg['env']} not set")
        return False
    out_dir = SUBS / mid
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"  [call] {mid} ({cfg['provider']} {cfg['model']}) …", flush=True)
    t0 = time.time()
    try:
        text, toks = ADAPTERS[cfg["kind"]](cfg, key, prompt)
    except urllib.error.HTTPError as e:
        print(f"  [FAIL] {mid}: HTTP {e.code} {e.read().decode('utf-8','ignore')[:200]}")
        return False
    except Exception as e:
        print(f"  [FAIL] {mid}: {e}")
        return False
    dt = round(time.time() - t0, 1)
    html = extract_html(text)
    (out_dir / "index.html").write_text(html, encoding="utf-8")
    meta = {"model": cfg["model"], "provider": cfg["provider"],
            "date": time.strftime("%Y-%m-%d"), "tokens_out": toks,
            "latency_s": dt, "bytes": len(html),
            "has_canvas": "<canvas" in html.lower(), "notes": ""}
    (out_dir / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    flag = "" if meta["has_canvas"] else "  WARN no <canvas> found"
    print(f"  [ok]   {mid}: {len(html)} bytes, {dt}s, {toks} tok{flag}")
    return True

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true", help="run every provider with a key set")
    ap.add_argument("--models", nargs="+", help="subset of model ids to run")
    ap.add_argument("--list", action="store_true", help="list configured providers")
    a = ap.parse_args()
    if a.list:
        for mid, c in PROVIDERS.items():
            have = "[x]" if os.environ.get(c["env"]) else "[ ]"
            print(f"  {have} {mid:14s} {c['provider']:10s} {c['model']:22s} ({c['env']})")
        return
    prompt = canonical_prompt()
    ids = a.models or (list(PROVIDERS) if a.all else [])
    if not ids:
        ap.print_help(); print("\nNothing to run. Use --all, --models, or --list."); return
    print(f"Prompt ({len(prompt)} chars):\n  {prompt}\n")
    done = sum(run_one(m, prompt) for m in ids if m in PROVIDERS)
    print(f"\nDone: {done}/{len(ids)} produced output. Open viewer/gallery.html to compare & score.")

if __name__ == "__main__":
    main()
