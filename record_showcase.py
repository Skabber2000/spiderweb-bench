#!/usr/bin/env python
"""
Record the flag-grouped showcase page (all submissions running live) to MP4.

1. Serves the project over http://127.0.0.1:<port> (iframes + fetch need http,
   not file://).
2. Opens viewer/showcase.html at 1920x1080 in Chromium and records video for
   DURATION seconds (long enough to capture full weave -> neural -> dissolve cycles).
3. Converts the Playwright .webm to an H.264 .mp4 with ffmpeg.

Usage:  python record_showcase.py [--seconds 50] [--port 8123]
Requires: playwright (+ chromium), ffmpeg on PATH.
"""
import argparse, sys, time, http.server, socketserver, threading, functools, pathlib, subprocess, glob, os

ROOT = pathlib.Path(__file__).resolve().parent
MEDIA = ROOT / "media"
RAW = MEDIA / "raw"

def serve(port):
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(ROOT))
    httpd = socketserver.TCPServer(("127.0.0.1", port), handler)
    httpd.allow_reuse_address = True
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    return httpd

def record(url, seconds):
    from playwright.sync_api import sync_playwright
    RAW.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--autoplay-policy=no-user-gesture-required",
                                           "--disable-gpu-vsync", "--force-color-profile=srgb"])
        ctx = browser.new_context(viewport={"width": 1920, "height": 1080},
                                  record_video_dir=str(RAW),
                                  record_video_size={"width": 1920, "height": 1080})
        page = ctx.new_page()
        page.goto(url, wait_until="load")
        page.wait_for_timeout(1500)   # let iframes mount + animations spin up
        print(f"  recording {seconds}s of live render ...", flush=True)
        page.wait_for_timeout(int(seconds * 1000))
        path = page.video.path()
        ctx.close()
        browser.close()
        return path

def to_mp4(webm):
    out = MEDIA / "spiderweb_bench_compare.mp4"
    cmd = ["ffmpeg", "-y", "-nostdin", "-i", webm,
           "-c:v", "libx264", "-preset", "medium", "-crf", "18",
           "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out)]
    print("  encoding mp4 ...", flush=True)
    subprocess.run(cmd, check=True, timeout=600,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=float, default=50)
    ap.add_argument("--port", type=int, default=8123)
    a = ap.parse_args()
    MEDIA.mkdir(exist_ok=True)
    httpd = serve(a.port)
    url = f"http://127.0.0.1:{a.port}/viewer/showcase.html"
    print(f"Serving {ROOT} at {url}")
    try:
        webm = record(url, a.seconds)
    finally:
        httpd.shutdown()
    print(f"  raw webm: {webm}")
    mp4 = to_mp4(webm)
    sz = os.path.getsize(mp4) / 1e6
    print(f"\nDone -> {mp4}  ({sz:.1f} MB)")

if __name__ == "__main__":
    main()
