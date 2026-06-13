#!/usr/bin/env python
"""Capture weave (t=8s) and neural (t=24s) frames from each submission for quality judging."""
import http.server, socketserver, threading, functools, pathlib, subprocess
ROOT = pathlib.Path(__file__).resolve().parent
SHOTS = ROOT / "media" / "shots"
PORT = 8131
ORDER = ["claude-opus-4.8","gpt-5.5","grok-4","gemini-3-pro","glm-5.1","deepseek-v4","minimax-m3","mistral-large"]

def serve():
    h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(ROOT))
    httpd = socketserver.TCPServer(("127.0.0.1", PORT), h); httpd.allow_reuse_address = True
    threading.Thread(target=httpd.serve_forever, daemon=True).start(); return httpd

def main():
    from playwright.sync_api import sync_playwright
    SHOTS.mkdir(parents=True, exist_ok=True)
    httpd = serve()
    with sync_playwright() as p:
        b = p.chromium.launch()
        for i, mid in enumerate(ORDER):
            ctx = b.new_context(viewport={"width":800,"height":800})
            pg = ctx.new_page()
            pg.goto(f"http://127.0.0.1:{PORT}/submissions/{mid}/index.html", wait_until="load")
            pg.wait_for_timeout(8000)
            pg.screenshot(path=str(SHOTS / f"{i:02d}_{mid}_a.png"))
            pg.wait_for_timeout(16000)
            pg.screenshot(path=str(SHOTS / f"{i:02d}_{mid}_b.png"))
            ctx.close()
            print(f"  shot {mid}", flush=True)
        b.close()
    httpd.shutdown()
    # contact sheet: 2 cols (weave|neural) x 8 rows, scaled
    out = ROOT / "media" / "contact_sheet.png"
    subprocess.run(["ffmpeg","-y","-nostdin","-framerate","1","-pattern_type","glob",
                    "-i", str(SHOTS / "*.png"),
                    "-vf","scale=380:380,tile=2x8:padding=6:color=0x202838", str(out)],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"-> {out}")

if __name__ == "__main__":
    main()
