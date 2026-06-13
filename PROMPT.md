# Canonical Benchmark Prompt

> **Do not modify this prompt between models.** Every model receives this exact text,
> zero-shot, no follow-ups, no system prompt beyond the model's default. One generation,
> first attempt. Save the model's raw HTML output to `submissions/<model-id>/index.html`.

---

```
Create a single HTML file with an 800×800 <canvas> where a spider weaves a web,
and once complete the web's threads turn into a glowing neural network with signals
firing between nodes, then dissolves and the spider starts a new one. Loop.
```

---

## Submission rules

1. **Single file.** The model must return one self-contained `.html`. No external
   files, no CDN, no build step. If a model returns multiple files or requires a
   bundler, score **Code Quality** accordingly and inline what you can.
2. **First generation only.** No iterative prompting, no "fix the bug" follow-ups.
   The benchmark measures one-shot capability.
3. **Strip prose, keep code.** Save only the HTML document the model produced
   (remove surrounding markdown fences / explanation). Note in `scores/notes.md`
   if the model wrapped or truncated the code.
4. **Record metadata** in `submissions/<model-id>/meta.json`:
   `{ "model": "...", "provider": "...", "date": "YYYY-MM-DD", "tokens_out": N,
     "latency_s": N, "notes": "..." }`
5. **No human edits to the artifact.** The `index.html` must be exactly what the
   model produced. Fixes/observations go in notes, not in the file.

## Why this task

It exercises several skills at once that are hard to fake:
- **Procedural geometry** (radial orb-web: spokes, frame, capture spiral).
- **State-machine animation** over time (weave → neural → dissolve → loop).
- **Graph construction + simulation** (nodes/edges, signal propagation).
- **Aesthetic judgment** (glow, palette, composition, motion easing).
- **Self-contained engineering** (one file, no deps, 60 fps, no console errors).
