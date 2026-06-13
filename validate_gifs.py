#!/usr/bin/env python
"""Tile each GIF (1 frame/sec across its 10s) into a labeled row, stack all -> _validate.png"""
import subprocess, pathlib
ROOT = pathlib.Path(__file__).resolve().parent
GIFS = ROOT/"media"/"gifs"; OUT = ROOT/"media"/"_validate"; OUT.mkdir(parents=True, exist_ok=True)
MODELS = ["claude-opus-4.8","gpt-5.5","grok-4","gemini-3-pro",
          "glm-5.1","deepseek-v4","minimax-m3","mistral-large"]
rows=[]
for m in MODELS:
    r = OUT/f"{m}.png"
    vf = "fps=1,eq=gamma=1.7:brightness=0.05,scale=220:220,tile=11x1:padding=2:color=0x333333"
    subprocess.run(["ffmpeg","-y","-v","error","-i",str(GIFS/f"{m}.gif"),
                    "-vf",vf,"-frames:v","1",str(r)],check=True)
    rows.append(str(r))
ins=[]; [ins.extend(["-i",r]) for r in rows]
fc="".join(f"[{i}:v]" for i in range(len(rows)))+f"vstack=inputs={len(rows)}[v]"
subprocess.run(["ffmpeg","-y","-v","error",*ins,"-filter_complex",fc,"-map","[v]",
                str(ROOT/"media"/"_validate.png")],check=True)
print("wrote", ROOT/"media"/"_validate.png")
