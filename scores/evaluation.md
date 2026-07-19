# Final Evaluation — Evidence-Based Review

_Method: full **source review** + **rendered animation** (9-frame filmstrips spanning a full
cycle per model). Weighted to **prompt fidelity** (does the woven web actually become the
network) and **biological realism** (organic asymmetry + true thread-by-thread weaving), then
visual polish and code quality. Supersedes the earlier auto-judge panel, which was unreliable
(judge leniency + still-frame polish noise scoring an animation)._

## Ranking

| # | Model | Quality | Verdict |
|---|-------|---------|---------|
| 1 | **GPT-5.5** | ★★★★½ | Only model that is organic/asymmetric **and** fully polished **and** shows the complete cycle in a normal window. Random oval squash + per-node wobble + offset center → most natural geometry; faithful web→neural; cyan+purple bloom; spider rappels down a thread on dissolve. |
| 2 | **Claude Opus 4.8** | ★★★★½ | Most authentic *weaving* — spider rides each thread as spokes then spiral are laid; jittered, asymmetric web; neural signals hop across the **actual** woven threads (real propagation). Understated thin-silk visuals + slow pacing means it under-shows its own neural payoff — the reason naive/visual scorers under-rate it. |
| 3 | MiniMax M3 | ★★★★ | Best weave *behaviour*: lays radials with return-trips to center, then the capture spiral (textbook orb-weaver). Faithful neural (ignition wave + signals on real threads), art-directed HUD. Geometry symmetric. |
| 4 | DeepSeek V4 Pro | ★★★★ | Proper graph: center+radial×ring nodes with an adjacency map driving real signal propagation. Dense, colorful, polished. Symmetric. Largest file (40 KB). |
| 5 | GLM-5.1 | ★★★★ | Complete warm-amber cycle, glowing node activation, particle dissolve, detailed spider. Symmetric. Extreme thinking cost (29k tok / 517 s). |
| 6 | Gemini 3.5 Flash | ★★★½ | Faithful and elaborate, mild asymmetry (subtle jitter), but busy on-screen HUD text and a slow weave that rarely reaches its neural payoff in-window. (Pro tiers were quota-blocked; this is the Flash model.) |
| 7 | Grok 4 | ★★½ | Builds neural edges from the web, but the **signal renderer is buggy** (pulses drawn between random node pairs, not along edges) and "weaving" is rings appearing while the spider teleports. Symmetric. Leanest (5.6 KB / 26 s). |
| 8 | Mistral Large | ★★ | **Prompt failure**: `initNeuralNetwork()` discards the web and spawns 50 random nodes with random links — the "neural network" is unrelated to the woven web. Basic blob-spider, symmetric, dim. |

## Key findings
- **Capability is near-solved**: 6 of 8 correctly implement all four phases with a faithful
  web→neural transition. Separation is in craft, realism, and pacing.
- **Biological realism is the rare differentiator**: only **GPT-5.5** and **Opus 4.8** produced
  organically *asymmetric* webs. Everyone else is mechanically symmetric (Gemini mildly jittered).
- **Two genuine defects**: Grok's signal renderer (random endpoints) and Mistral's random,
  web-unrelated graph.
- **Effort ≠ quality**: ~30× latency spread (26 s → 13 min) and ~15× tokens for the same task;
  the leanest (Grok) and heaviest (GLM/MiniMax) are not the best.
- **Why automated scoring failed Opus**: its payoff (the glowing neural net) is understated and
  arrives late, so still-frame/visual judges saw mostly its quiet weaving phase and under-scored it.

## Addendum — late entrants (2026-07-19)

Two submissions were added after the original 8-model review. They were **not** re-judged
by the same reviewer under the same conditions; placements in the README table (#3–#4)
were assigned by Fable 5 itself in the session that added them — treat as provisional.

| # | Model | Quality | Rationale |
|---|-------|:-------:|-----------|
| 3 | Claude Fable 5 | ★★★★ | True thread-by-thread weave (spokes with return trips, then a continuous accelerating spiral) over an **asymmetric** jittered web; neural nodes appear at real thread intersections and signals propagate along a spiral+spoke adjacency graph — no free-floating pulses. Web re-randomized every cycle. Main defect: glacial first-generation pacing (~107 s/cycle), so the neural payoff arrives very late in-window. Generated interactively in Claude Code (not raw API); strict first-generation file preserved (a post-hoc pacing fix exists outside the benchmark). |
| 4 | Kimi K3 | ★★★★ | The most deliberate orb-weaver *process* of the whole field: dragline drop from the top edge, radial spokes, then a sagging capture spiral — all planned upfront in a 54K-char reasoning stream (see `submissions/kimi-k3/reasoning_trace.md`) that includes self-verification arithmetic (~96 nodes, ~180 edges, ≤60 pulses, ~230 strokes/frame). Clean full cycle (weave ~57 s + neural 10 s + dissolve 4.4 s ≈ 74 s), 0 console errors, 120 fps. Costs: ~15 min generation wall time, largely symmetric geometry, and slow on-screen tempo. |

Measured head-to-head (identical headless Chromium harness, 2026-07-19): both 120 fps,
0 js errors; cycle ≈107 s (Fable first-gen) vs ≈74 s (Kimi); file 10.2 KB vs 14.7 KB.
A split-screen real-time recording of the two (with Kimi's reasoning trace running as a
terminal overlay) was produced outside the repo during the comparison session.
