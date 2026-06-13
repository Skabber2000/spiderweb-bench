#!/usr/bin/env python
"""Capture a 2x2 phase montage (t=7,18,30,44s) per submission for the judge panel."""
import http.server, socketserver, threading, functools, pathlib
from PIL import Image
ROOT = pathlib.Path(__file__).resolve().parent
OUT = ROOT / "media" / "judge"
PORT = 8141
ORDER = ["claude-opus-4.8","gpt-5.5","grok-4","gemini-3-pro","glm-5.1","deepseek-v4","minimax-m3","mistral-large"]
TS = [7000, 11000, 12000, 14000]  # cumulative waits -> 7,18,30,44s

def serve():
    h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(ROOT))
    s = socketserver.TCPServer(("127.0.0.1", PORT), h); s.allow_reuse_address = True
    threading.Thread(target=s.serve_forever, daemon=True).start(); return s

def main():
    from playwright.sync_api import sync_playwright
    OUT.mkdir(parents=True, exist_ok=True)
    s = serve()
    with sync_playwright() as p:
        b = p.chromium.launch()
        for mid in ORDER:
            ctx = b.new_context(viewport={"width":800,"height":800}); pg = ctx.new_page()
            pg.goto(f"http://127.0.0.1:{PORT}/submissions/{mid}/index.html", wait_until="load")
            frames = []
            for w in TS:
                pg.wait_for_timeout(w)
                fn = OUT / f"_{mid}_{len(frames)}.png"; pg.screenshot(path=str(fn)); frames.append(fn)
            ctx.close()
            # 2x2 montage at 400px
            m = Image.new("RGB", (800, 800), (10, 12, 18))
            for i, fn in enumerate(frames):
                im = Image.open(fn).resize((400, 400)); m.paste(im, ((i % 2)*400, (i//2)*400))
            m.save(OUT / f"{mid}.png")
            print(f"  montage {mid}", flush=True)
        b.close()
    s.shutdown()
    print("done")

if __name__ == "__main__":
    main()
