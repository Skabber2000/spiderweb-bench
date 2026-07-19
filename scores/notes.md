# Scoring Notes

## Final run — 2026-06-13 (8 models, all via API except MiniMax manual)
| Model | Region | Time | Tokens | Size | Quality★ |
|-------|--------|------|--------|------|----------|
| GPT-5.5 | US | 157 s | 8.7k | 13.8 KB | ★★★★★ |
| Gemini 3.5 Flash | US | 158 s | 9.9k | 37 KB | ★★★★½ |
| Claude Opus 4.8 | US | 41 s | 4.2k | 7.7 KB | ★★★★½ |
| Grok 4 | US | 26 s | 1.9k | 5.6 KB | ★★★☆☆ |
| DeepSeek V4 Pro | CN | 174 s | 16.9k | 40 KB | ★★★★☆ |
| MiniMax M3 | CN | manual | — | 17.7 KB | ★★★★☆ |
| GLM-5.1 | CN | 517 s | 29.4k | 13.7 KB | ★★★½☆ |
| Mistral Large | EU | 32 s | 2.7k | 11.6 KB | ★★½☆☆ |

Quality = first-look craft (spider believability · web→neural fidelity · signal life · polish), not full rubric.

Notes:
- Claude Opus 4.8 regenerated via API (claude-opus-4-8; `temperature` is deprecated on this model — dropped it). Leaner/faster than the hand-built baseline.
- Gemini: key has Flash-only quota (all Pro tiers 429); `gemini-3.5-flash` landed after 503 retries — largest-but-one build.
- GLM-5.1 needed a 65k token cap (29k consumed, 8.6 min) — extreme thinking budget.
- ~20× spread in both tokens and latency for the same deliverable.

### Deliverable
`media/spiderweb_bench_compare.mp4` — 1920×1080, 55 s live render, US-left / China-right /
Mistral-EU under the central results table. Rebuild: `python record_showcase.py --seconds 55`.

---

One-line verdict per model (filled in as you judge). Keep it blunt.

| Model | Verdict (1 sentence) | Standout | Failure mode |
|-------|----------------------|----------|--------------|
| Claude Opus 4.8 | baseline — full 4-phase loop, web threads *are* the neural edges | spider weaves thread-by-thread; signals propagate along real web | — |
| GPT-5.5 | _pending_ | | |
| Grok 4 | _pending_ | | |
| Gemini 3 Pro | _pending_ | | |
| GLM-5.1 | _pending_ | | |
| MiniMax M2 | _pending_ | | |
| Mistral Large | _pending_ | | |

## Common failure modes to watch for
- Web just fades in instead of being *woven* (no spider construction motion).
- Neural phase is a fresh random graph unrelated to the web that was drawn.
- Signals move on random straight lines, not along actual edges.
- Doesn't reset cleanly on loop (leaks, web doesn't regenerate, fps decays).
- Multiple files / CDN dependency / requires a build step.

## kimi-k3 (Moonshot, 2026-07-19)
- One-shot via API (streamed). Provider forces `temperature=1` (only allowed value) — runner gained a per-provider `temp` override.
- Reasoning model: several minutes of hidden thinking before code; ~15 min wall latency (slowest of all submissions).
- Output: clean single 14.7 KB file, finish=stop, zero console errors.
- Cycle: weave ~45 s (true thread-by-thread: anchors → radials → spiral, spider rides threads) → morph 1.7 s → neural 10 s → dissolve 4.4 s → loop.
- Neural phase is faithful: nodes at real web intersections, pulses travel along actual threads, per-cycle hue shift.
- Weaknesses: long quiet weave vs 10 s payoff (same pacing critique as Opus/Gemini); geometry only mildly irregular.
