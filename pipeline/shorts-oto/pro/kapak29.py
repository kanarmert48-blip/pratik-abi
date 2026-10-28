"""29. video kapağı: x-ray kafa (ağız açık) + başlık."""
import os
import sys
os.environ.setdefault("PA_SCALE", str(4 / 3))
WORK = sys.argv[1]
OUT = sys.argv[2]
sys.argv = [sys.argv[0], WORK, "frames", ""]
import numpy as np
from PIL import Image

import video29_yutkunma as V
from video29_yutkunma import X, O, txt, put_icon, put_word, GOLD, WHITE, u, W, H, brand

cam = X.Cam(1960, 2060, 1640)
st = V.state_at(1.0)
st.focus = {"lar_red": 1.0}
buf = X.base(cam, st.th, st.hyo)
O.draw(buf, cam, st)
buf = buf * V.GRADE
im = Image.fromarray(np.clip(buf, 0, 255).astype(np.uint8), "RGB").convert("RGBA")
L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
txt(L, (540, 250), "AĞZIN AÇIKKEN", 112, WHITE, 1.0, stroke=7)
txt(L, (540, 385), "YUTKUNAMAZSIN", 112, GOLD, 1.0, stroke=7)
put_icon(L, "face_with_open_mouth", 850, 1180, 300)
cx, cy = cam.U((1715 + st.lar[0], 2540 + st.lar[1]))
V.ring(L, cx, cy, 150, 0.7, (255, 110, 110), 1.0)
txt(L, (540, 1560), "HEMEN DENE", 92, WHITE, 1.0, stroke=7)
im.alpha_composite(L)
brand(im, 540, 62, size=34)
im.convert("RGB").save(OUT, quality=93)
print("kapak", OUT)
