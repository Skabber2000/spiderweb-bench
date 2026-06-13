#!/usr/bin/env python
"""
Per-model animated GIFs, timing-aligned to a common 2-cycle duration.

Pipeline (all 8 models in parallel):
  1. Serve repo over http://127.0.0.1 (canvas + fetch need http, not file://).
  2. Record each submissions/<id>/index.html to webm at 800x800 (async, concurrent).
  3. Derive a luminance-vs-time signal FROM the recording (ffmpeg 10fps 16x16 gray).
  4. Autocorrelation -> loop period T; cycle start = darkest (dissolved/blank) frame.
  5. Trim to exactly 2*T, then time-scale to a COMMON target duration so slow
     animations are accelerated and fast ones eased -> all GIFs same length, phase-aligned.
  6. Encode GIF (lanczos + diff-palette) into media/gifs/<id>.gif.

Usage:  python record_gifs.py [--target 10] [--width 460] [--fps 12.5] [--port 8137]
Requires: playwright(+chromium), numpy, ffmpeg on PATH.
"""
import argparse, asyncio, functools, http.server, os, pathlib, socketserver
import subprocess, threading, concurrent.futures as cf
import numpy as np

ROOT  = pathlib.Path(__file__).resolve().parent
RAW   = ROOT / "media" / "raw"
GIFS  = ROOT / "media" / "gifs"
SIGFPS = 10          # fingerprint sampling rate (from webm)
CAP    = 92.0        # seconds to record (>= onset + 3 dissolve troughs even for ~30s cycles)
TMIN, TMAX = 3.0, 40.0

# leaderboard order (rank) — only ids matter for recording
MODELS = ["claude-opus-4.8","gpt-5.5","grok-4","gemini-3-pro",
          "glm-5.1","deepseek-v4","minimax-m3","mistral-large"]

# code-derived cycle seconds (real-time animations); used when pixel self-similarity is weak
FALLBACK_T = {
    "gpt-5.5":        28.4,   # WEAVE 16.5 + NEURAL 7.6 + DISSOLVE 4.3 (ms consts)
    "deepseek-v4":    20.2,   # DURATION 9.5 + 6.0 + 3.5 + 1.2
    "glm-5.1":        16.0,   # weave + NEURAL_DUR 8 + DISSOLVE_DUR 3.8 + pause
    "minimax-m3":     12.0,
    "gemini-3-pro":   12.0,
    "claude-opus-4.8":10.0,
    "mistral-large":  10.0,
    "grok-4":         19.3,
}
SELFSIM_OK = 0.45            # trust detected period above this; else fall back to code

INJECT_CSS = ("html,body{margin:0!important;padding:0!important;overflow:hidden!important;"
              "background:#000!important}canvas{display:block;margin:auto}")

def serve(port):
    h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(ROOT))
    httpd = socketserver.TCPServer(("127.0.0.1", port), h)
    httpd.allow_reuse_address = True
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd

async def record_one(browser, base, mid):
    vdir = RAW / mid
    vdir.mkdir(parents=True, exist_ok=True)
    ctx = await browser.new_context(viewport={"width":800,"height":800},
              record_video_dir=str(vdir),
              record_video_size={"width":800,"height":800})
    page = await ctx.new_page()
    await page.goto(f"{base}/submissions/{mid}/index.html", wait_until="load")
    await page.add_style_tag(content=INJECT_CSS)
    await page.wait_for_timeout(600)
    await page.wait_for_timeout(int(CAP*1000))
    vid = page.video
    await ctx.close()                       # flush video
    path = await vid.path()
    print(f"  [rec] {mid:18s} -> {os.path.basename(path)}", flush=True)
    return mid, path

async def record_all(base, port):
    from playwright.async_api import async_playwright
    RAW.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch(args=["--autoplay-policy=no-user-gesture-required",
                    "--disable-gpu-vsync","--force-color-profile=srgb"])
        print(f"  recording {len(MODELS)} models x {CAP:.0f}s in parallel ...", flush=True)
        res = await asyncio.gather(*(record_one(browser, base, m) for m in MODELS))
        await browser.close()
    return dict(res)

def frames_matrix(webm):
    """16x16 grayscale fingerprint per frame at SIGFPS -> (N,256) float32."""
    cmd = ["ffmpeg","-v","error","-i",webm,
           "-vf",f"fps={SIGFPS},scale=16:16,format=gray","-f","rawvideo","-"]
    out = subprocess.run(cmd, capture_output=True, check=True).stdout
    a = np.frombuffer(out, dtype=np.uint8)
    n = (len(a)//256)*256
    return a[:n].reshape(-1,256).astype(np.float32)

def _autocorr_T(G, mid):
    """Fundamental period via multi-dim self-similarity; fallback to code-derived."""
    M = G.shape[0]
    Gc = G - G.mean(axis=0, keepdims=True)
    lo, hi = int(TMIN*SIGFPS), min(int(TMAX*SIGFPS), M//2)
    if hi <= lo + 2 or (Gc*Gc).sum() < 1e-3:
        return FALLBACK_T.get(mid, 12.0), 0.0
    c = np.empty(hi-lo)
    for j, lag in enumerate(range(lo, hi)):
        a, b = Gc[:M-lag], Gc[lag:]
        c[j] = float((a*b).sum()) / (np.sqrt(float((a*a).sum())*float((b*b).sum()))+1e-9)
    pk = [j for j in range(1, len(c)-1) if c[j] >= c[j-1] and c[j] > c[j+1]]
    if pk:
        vmax = max(c[j] for j in pk)
        cand = [j for j in pk if c[j] >= 0.85*vmax] if vmax > 0 else [max(pk, key=lambda j: c[j])]
        j0 = min(cand)
    else:
        j0 = int(np.argmax(c))
    peak = float(c[j0])
    return ((lo+j0)/SIGFPS if peak >= SELFSIM_OK else FALLBACK_T.get(mid, 12.0)), peak

def detect_period(F, mid):
    """2-cycle window from dissolve troughs (cycle boundaries); autocorr/code fallback.

    Returns (T, offset, marker) where span = 2*T and marker encodes method:
      >=0.9 trough-based, else self-sim peak (autocorr) / 0 = code fallback.
    """
    N = F.shape[0]
    total = N / SIGFPS
    on = 0
    diff = np.sqrt(((F - F[:3].mean(axis=0))**2).sum(axis=1))
    if diff.max() > 0:
        on = int(np.argmax(diff > 0.20*diff.max()))

    # content metric = time-varying "ink": mean of (frame - per-pixel min over time).
    # Subtracting the per-pixel minimum removes static elements (HUDs, vignettes) so even
    # sparse webs register a build->dissolve swing; works for dense and sparse alike.
    ink = (F - F.min(axis=0, keepdims=True)).mean(axis=1).astype(float)
    k = max(1, int(1.5*SIGFPS)); sv = np.convolve(ink, np.ones(k)/k, "same")
    rng = sv.max() - sv.min()
    bounds = []                                      # dissolve-completion frames (cycle ends)
    if rng > 1e-6:
        nrm = (sv - sv.min()) / rng
        HI, LO = 0.55, 0.20                          # Schmitt trigger: must build high then dissolve low
        state = "low"
        for i in range(len(nrm)):
            if state == "low" and nrm[i] > HI:
                state = "high"
            elif state == "high" and nrm[i] < LO:
                bounds.append(i); state = "low"

    if len(bounds) >= 3:                              # full cycle = bound[i]->bound[i+1]
        offset = bounds[0] / SIGFPS
        T, marker = (bounds[2] - bounds[0]) / (2.0*SIGFPS), 0.99
    else:
        T, peak = _autocorr_T(F[on:], mid)
        offset, marker = on / SIGFPS, peak
    if offset + 2*T > total:                          # clamp to captured span
        if 2*T <= total: offset = max(total - 2*T, 0.0)
        else:            T = max(total/2.0, TMIN)
    return T, offset, marker

def make_gif(webm, mid, T, offset, target, width, fps):
    GIFS.mkdir(parents=True, exist_ok=True)
    out = GIFS / f"{mid}.gif"
    span = 2*T
    sf = target / span                            # <1 = accelerate (slow originals), >1 = ease
    vf = (f"setpts=PTS*{sf:.6f},fps={fps},scale={width}:-1:flags=lanczos,"
          f"split[a][b];[a]palettegen=stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=3")
    cmd = ["ffmpeg","-y","-v","error","-ss",f"{offset:.3f}","-t",f"{span:.3f}",
           "-i",webm,"-filter_complex",vf,"-loop","0",str(out)]
    subprocess.run(cmd, check=True, timeout=300)
    mb = out.stat().st_size/1e6
    print(f"  [gif] {mid:18s} T={T:5.2f}s 2cyc={span:5.1f}s x{1/sf:4.2f} -> {target:.0f}s  "
          f"{mb:5.2f} MB", flush=True)
    return mid, T, span, 1/sf, mb

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", type=float, default=10.0, help="common GIF duration (2 cycles)")
    ap.add_argument("--width",  type=int,   default=460)
    ap.add_argument("--fps",    type=float, default=12.5)
    ap.add_argument("--port",   type=int,   default=8137)
    ap.add_argument("--reuse",  action="store_true", help="reuse cached webms in media/raw/<id>/")
    ap.add_argument("--cap",    type=float, default=None, help="override record seconds")
    ap.add_argument("--only",   type=str,   default=None, help="comma-list of model ids")
    a = ap.parse_args()

    global CAP, MODELS
    if a.cap:  CAP = a.cap
    if a.only: MODELS = [m.strip() for m in a.only.split(",")]

    if a.reuse:
        webms = {}
        for m in MODELS:
            cand = sorted((RAW/m).glob("*.webm"), key=lambda p: p.stat().st_mtime)
            if not cand: raise SystemExit(f"no cached webm for {m} in {RAW/m}")
            webms[m] = str(cand[-1])
        print(f"Reusing cached webms for {len(webms)} models")
    else:
        httpd = serve(a.port)
        base = f"http://127.0.0.1:{a.port}"
        print(f"Serving {ROOT} at {base}")
        try:
            webms = asyncio.run(record_all(base, a.port))
        finally:
            httpd.shutdown()

    # period detection + GIF encode in parallel
    def work(mid):
        F = frames_matrix(webms[mid])
        T, off, peak = detect_period(F, mid)
        print(f"  [det] {mid:18s} T={T:5.2f}s offset={off:4.1f}s self-sim={peak:+.2f}", flush=True)
        return make_gif(webms[mid], mid, T, off, a.target, a.width, a.fps)

    print("  detecting periods + encoding GIFs in parallel ...", flush=True)
    rows = []
    with cf.ThreadPoolExecutor(max_workers=8) as ex:
        for r in ex.map(work, MODELS):
            rows.append(r)
    tot = sum(r[4] for r in rows)
    print(f"\nDone -> {GIFS}  ({len(rows)} GIFs, {tot:.1f} MB total, each {a.target:.0f}s / 2 cycles)")

if __name__ == "__main__":
    main()
