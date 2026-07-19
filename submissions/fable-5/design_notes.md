# Fable 5 design notes (spiderweb-bench one-shot, 2026-07-19)

Generated interactively in Claude Code (terminal session), single-pass write, ~2 min wall.
This folder preserves the strict first-generation file. Immediately after generation, a
pacing review (headless screenshots) found the weave ~2× too slow and a fix was applied
*outside the benchmark* (lay speed 170 → 500–950 px/s); that fixed variant is not included
here, per the "first generation only" rule.

## Architecture (as planned before writing code)

Four-phase state machine: `weave → toRest → morph → fire → dissolve → pause → (rebuild)`.

- **Web geometry**: 12–15 spokes with jittered angles and per-spoke anchor radii
  (315–360 px) — the source of the web's organic asymmetry. Capture spiral is a single
  continuous path: 8 turns × spokes steps, radius fraction interpolated 0.13 → 0.93.
- **Weaving**: the spider physically travels every segment as it is laid (spokes with
  return trips at travel speed, then the spiral end-to-end); thread appears behind it.
  Gait phase is tied to distance moved.
- **Web→neural**: every spiral point is a graph node; adjacency = spiral neighbors
  (s±1) + same-spoke ring neighbors (s±spokes) + center↔innermost ring. Signals only
  ever travel along these edges, i.e. along real rendered silk. Arrival flashes the node
  and chains 3–6 hops. Additive compositing during the firing phase.
- **Dissolve**: per-segment random fade offsets; spider walks back to center; the whole
  web (spoke count, angles, radii) is re-randomized for the next cycle.
- **Glow without shadowBlur**: double-stroke (wide low-alpha under thin bright) to keep
  the frame cheap; measured 120 fps in headless Chromium, 0 console errors.

## Known first-generation defect

Lay speed 170 px/s → full cycle ≈ 107 s, so the neural payoff arrives very late for a
casual viewer. The engineering is sound; the pacing judgment was not.
