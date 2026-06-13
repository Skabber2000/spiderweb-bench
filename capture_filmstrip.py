#!/usr/bin/env python
"""Capture a 9-frame filmstrip (every 6s to 54s) per submission, tiled 3x3, to judge the
actual animation: weave -> web -> neural -> firing -> dissolve -> loop."""
import http.server, socketserver, threading, functools, pathlib
from PIL import Image, ImageDraw
ROOT = pathlib.Path(__file__).resolve().parent
OUT = ROOT / "media" / "film"
PORT = 8143
ORDER = ["claude-opus-4.8","gpt-5.5","grok-4","gemini-3-pro","glm-5.1","deepseek-v4","minimax-m3","mistral-large"]
N = 9; STEP = 6000  # 6,12,...,54s

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
            frames=[]
            for i in range(N):
                pg.wait_for_timeout(STEP); frames.append(pg.screenshot())
            ctx.close()
            cell=260; grid=Image.new("RGB",(cell*3+8,cell*3+8),(8,10,16)); d=ImageDraw.Draw(grid)
            from io import BytesIO
            for i,png in enumerate(frames):
                im=Image.open(BytesIO(png)).resize((cell,cell)); x=(i%3)*(cell+4); y=(i//3)*(cell+4)
                grid.paste(im,(x,y)); d.text((x+3,y+2),f"{(i+1)*6}s",fill=(150,180,220))
            grid.save(OUT/f"{mid}.png"); print(f"  film {mid}",flush=True)
        b.close()
    s.shutdown(); print("done")

if __name__ == "__main__":
    main()
