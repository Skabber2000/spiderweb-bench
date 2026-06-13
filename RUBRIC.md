# Scoring Rubric — Spider Web → Neural Network

Each submission is scored on 7 weighted criteria, total **100 points**. Score every
criterion **0–10**; the gallery applies the weights and computes the total.

Score blind where possible (judge the artifact, not the model name), and judge the
**first generation only**.

| # | Criterion | Weight | What 10/10 looks like | What 0–3 looks like |
|---|-----------|:------:|-----------------------|---------------------|
| 1 | **Spec compliance** | 20 | 800×800 canvas, single file, all four phases present (weave → neural → dissolve → loop), genuinely loops forever | Missing phases, wrong size, multiple files, runs once and stops |
| 2 | **Weaving believability** | 15 | A recognizable spider visibly *constructs* the web thread-by-thread (spokes, then spiral), motion follows the drawn thread | Web just fades in; no spider, or spider is a static dot teleporting |
| 3 | **Web→neural transition** | 15 | The actual woven threads become the network — nodes sit on real intersections, edges = real threads; smooth morph | Web vanishes and an unrelated random graph appears; no spatial relationship |
| 4 | **Neural firing** | 15 | Signals travel along edges between nodes, with propagation/branching and node activation; feels alive | A few dots drift on random straight lines unrelated to the web |
| 5 | **Visual polish** | 15 | Deliberate palette, glow/bloom, depth, composition, eased motion; looks like a finished piece | Flat primary colors, no glow, jittery, amateur |
| 6 | **Code quality** | 10 | Single file, no deps, no console errors, readable, sensible structure | Throws errors, dead code, copy-paste mess, needs a server/build |
| 7 | **Performance** | 10 | Smooth ~60 fps, no leaks over multiple loops, no growing memory | Janky, drops frames, slows down each loop, leaks |

**Total = Σ (score_i / 10 × weight_i)**, max 100.

## Tie-breakers (in order)
1. Higher **Spec compliance**.
2. Higher **Web→neural transition** (this is the conceptual crux of the task).
3. Lower output tokens for equal quality (efficiency).
4. Lower latency.

## Auto-checks the gallery performs (informational, not scored automatically)
- File present and non-empty.
- Contains a `<canvas>` at 800×800.
- Single `.html` (no sibling asset files in the folder besides `meta.json`).
- Uncaught errors surfaced by the iframe (when same-origin allows).

## Scoring discipline
- Watch **at least two full loops** before scoring (the dissolve→restart is where
  weak implementations break — leaks, state not reset, web doesn't regenerate).
- Reload each iframe to confirm a clean cold start.
- Keep one sentence of justification per model in `scores/notes.md`.
