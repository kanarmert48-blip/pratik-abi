"""Arka plan videosundaki ön plan nesnesinin (köpek vb.) maskesini çıkarır -> occ.npy (N, H/2, W/2) uint8.
Kullanım: python3 occmask.py <video> <off> <dur> <out.npy> [step=2]"""
import subprocess, sys
import numpy as np
from PIL import Image

sys.path.insert(0, "/home/claude/shorts-oto/pro")
import ai_tools
from rembg import remove

W, H, FPS = 1920, 1080, 30
src, off, dur, out = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), sys.argv[4]
step = int(sys.argv[5]) if len(sys.argv) > 5 else 2
n = int(dur * FPS)
p = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-stream_loop", "-1", "-ss", str(off), "-i", src, "-vf",
                      f"fps={FPS},scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},scale=960:540", "-an",
                      "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
sess = ai_tools._rembg("isnet-general-use")
masks = np.zeros((n, 540, 960), np.uint8)
last = None
for i in range(n):
    b = p.stdout.read(960 * 540 * 3)
    if len(b) < 960 * 540 * 3:
        masks[i:] = last if last is not None else 0
        break
    if i % step == 0 or last is None:
        im = Image.frombuffer("RGB", (960, 540), b, "raw", "RGB", 0, 1)
        last = np.asarray(remove(im, session=sess, only_mask=True, post_process_mask=True))
    masks[i] = last
    if i % 30 == 0:
        print(i, n, flush=True)
p.kill()
np.save(out, masks)
