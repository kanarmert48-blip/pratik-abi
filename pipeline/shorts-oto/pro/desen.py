"""Periferik kayma (peripheral drift) deseni – kendi tasarımımız. 1440x2560 PNG üretir."""
import sys, numpy as np
from PIL import Image
OUT = sys.argv[1]
SS = 2
W, H = 1440 * SS, 2560 * SS
K = W / 1080.0                    # birim -> piksel
R = 172 * K
SP = 360 * K
RY = SP * np.sin(np.pi / 3)
CX, CY = 540 * K, 1000 * K
cols = {"blk": (12, 12, 16), "blu": (34, 78, 210), "wht": (250, 250, 246), "yel": (246, 206, 40)}
BG = (58, 64, 74)
img = np.zeros((H, W, 3), np.float32)
img[:] = BG
NR = 5
bands = [(0.0, 0.12, "blk"), (0.12, 0.5, "blu"), (0.5, 0.62, "wht"), (0.62, 1.0, "yel")]
r0 = int(np.floor(-CY / RY)) - 1
r1 = int(np.ceil((H - CY) / RY)) + 1
for rw in range(r0, r1 + 1):
    cy = CY + rw * RY
    off = SP / 2 if rw % 2 else 0.0
    k0 = int(np.floor((-CX - off) / SP)) - 1
    k1 = int(np.ceil((W - CX - off) / SP)) + 1
    for kc in range(k0, k1 + 1):
        cx = CX + off + kc * SP
        x0, x1 = int(max(0, cx - R - 2)), int(min(W, cx + R + 2))
        y0, y1 = int(max(0, cy - R - 2)), int(min(H, cy + R + 2))
        if x0 >= x1 or y0 >= y1:
            continue
        yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
        rr = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
        th = np.arctan2(yy - cy, xx - cx)
        dirn = 1.0 if ((2 * kc + (1 if rw % 2 else 0) + rw) % 4) < 2 else -1.0
        ring = np.floor(rr / (R / NR))
        nseg = 6 + 6 * ring
        fr = np.mod(th / (2 * np.pi) * nseg + ring * 0.37, 1.0)
        if dirn < 0:
            fr = 1 - fr
        sub = img[y0:y1, x0:x1]
        inside = rr < R
        for a_, b_, c in bands:
            m = inside & (fr >= a_) & (fr < b_)
            sub[m] = cols[c]
        sub[rr < R * 0.16] = (24, 26, 32)
        sub[inside & (np.mod(rr, R / NR) < 1.2 * SS) & (rr > R * 0.16)] = (30, 32, 40)
im = Image.fromarray(img.astype(np.uint8), "RGB").resize((1440, 2560), Image.LANCZOS)
im.save(OUT)
print("ok", OUT)
