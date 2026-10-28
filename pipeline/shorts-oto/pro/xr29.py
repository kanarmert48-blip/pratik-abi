"""29. video: x-ray kafa render'ı (Unsplash syaEIuKA-DA, Rohit Choudhari) üzerine katmanlı animasyon.
Kaynak koordinatları: aynalanmış görüntü pikselleri (yüz sağa bakar), 3132x4715.
Katmanlar: A (çene/dil kemiği bölgesi doldurulmuş zemin), B (alt çene, dönebilir), C (dil kemiği, kayabilir)."""
import math
import os
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

from engine import u, W, H

HERE = Path(__file__).resolve().parent
SRC = Path(os.environ.get("XR29_SRC", "/tmp/claude-0/-home-claude/b79e0552-bc51-522f-903a-0721ef74ac4f/scratchpad/v29/ref/xr_side_full.jpg"))
CACHE = Path(os.environ.get("XR29_CACHE", str(SRC.parent / "xr29_cache.npz")))

TMJ = (1505.0, 1650.0)
Y0PX = u(930)

# alt çene bölgesi (dönen parça)
JAW_POLY = [(1468, 1598), (1508, 1700), (1520, 1800), (1526, 1900), (1536, 1995), (1568, 2080), (1626, 2165), (1706, 2238),
            (1806, 2300), (1906, 2352), (2006, 2402), (2106, 2444), (2206, 2484), (2290, 2522), (2360, 2548), (2420, 2546),
            (2458, 2500), (2470, 2400), (2462, 2280), (2452, 2185), (2480, 2110), (2506, 2050), (2516, 2004), (2400, 2006),
            (2300, 2010), (2200, 2012), (2100, 2010), (2000, 2007), (1900, 2002), (1822, 1994), (1752, 1950), (1700, 1880),
            (1660, 1790), (1630, 1700), (1590, 1638)]
HYO_POLY = [(1722, 2292), (1818, 2292), (1826, 2380), (1818, 2464), (1722, 2464), (1714, 2380)]
HAND_POLY = [(1690, 2985), (2900, 2985), (3132, 3080), (3132, 4715), (1560, 4715), (1620, 3150)]


def _poly_mask(poly, shape, ss=1):
    h, w = shape
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).polygon([(x, y) for x, y in poly], fill=255)
    return np.asarray(m, np.float32) / 255.0


def _feather_out(hard, r):
    """içi 1, dışa doğru r pikselde sönen alfa"""
    d = cv2.distanceTransform((1 - hard).astype(np.uint8), cv2.DIST_L2, 5)
    return np.clip(1 - d / r, 0, 1).astype(np.float32)


def _inpaint(img, hard, down=3, rad=10):
    h, w = hard.shape
    ys, xs = np.where(hard > 0.5)
    y0, y1 = max(0, ys.min() - 200), min(h, ys.max() + 200)
    x0, x1 = max(0, xs.min() - 200), min(w, xs.max() + 200)
    sub = img[y0:y1, x0:x1]
    m = hard[y0:y1, x0:x1]
    sw, sh = (x1 - x0) // down, (y1 - y0) // down
    s8 = cv2.resize(sub, (sw, sh), interpolation=cv2.INTER_AREA)
    m8 = (cv2.resize(m, (sw, sh), interpolation=cv2.INTER_LINEAR) > 0.02).astype(np.uint8)
    m8 = cv2.dilate(m8, np.ones((5, 5), np.uint8))
    r = cv2.inpaint(s8, m8, rad, cv2.INPAINT_TELEA)
    r = cv2.GaussianBlur(r, (0, 0), 6)
    r = cv2.resize(r, (x1 - x0, y1 - y0), interpolation=cv2.INTER_CUBIC)
    out = img.copy()
    mm = cv2.GaussianBlur(m, (0, 0), 3)[..., None]
    out[y0:y1, x0:x1] = (sub * (1 - mm) + r * mm).astype(np.uint8)
    return out


def build():
    im = Image.open(SRC).convert("RGB").transpose(Image.FLIP_LEFT_RIGHT)
    O = np.asarray(im, np.uint8).copy()
    h, w = O.shape[:2]
    jaw_h = _poly_mask(JAW_POLY, (h, w))
    hyo_h = _poly_mask(HYO_POLY, (h, w))
    A = _inpaint(O, np.maximum(jaw_h, hyo_h)).astype(np.float32)
    # çene açılınca görünen yer: ağız içi koyu, yüzün önü siyah
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    front = np.clip((xx - 2250) / 140, 0, 1)
    gap = np.clip(1 - (yy - 2010) / 140, 0, 1) * np.clip((xx - 1850) / 200, 0, 1)
    inner = cv2.GaussianBlur(A, (0, 0), 10)
    jm = cv2.GaussianBlur(jaw_h, (0, 0), 2)[..., None]
    A = (A * (1 - jm) + inner * jm).astype(np.uint8)
    B_a = _feather_out(jaw_h, 26)
    C_a = _feather_out(hyo_h, 14)
    np.savez_compressed(CACHE, O=O, A=A, B_a=(B_a * 255).astype(np.uint8), C_a=(C_a * 255).astype(np.uint8))


_D = {}


def data():
    if not _D:
        if not CACHE.exists():
            build()
        z = np.load(CACHE)
        _D.update({k: z[k] for k in z.files})
        O = _D["O"]
        _D["B"] = np.dstack([O, _D["B_a"]])
        _D["C"] = np.dstack([O, _D["C_a"]])
    return _D


# ---------------- kamera ----------------
class Cam:
    def __init__(self, cx, cy, w):
        self.cx, self.cy, self.w = cx, cy, w
        self.s = W / w                    # çıkış pikseli / kaynak pikseli

    def M(self):
        s = self.s
        return np.float32([[s, 0, W / 2 - self.cx * s], [0, s, Y0PX - self.cy * s]])

    def S(self, p):
        return (W / 2 + (p[0] - self.cx) * self.s, Y0PX + (p[1] - self.cy) * self.s)

    def SL(self, pts):
        return [self.S(p) for p in pts]

    def U(self, p):
        x, y = self.S(p)
        return (x / u(1), y / u(1))


def jaw_M(th):
    """kaynak -> kaynak: TMJ etrafında dönüş + kondil kayması"""
    a = math.radians(th)
    c, s = math.cos(a), math.sin(a)
    tx = TMJ[0] - c * TMJ[0] + s * TMJ[1] + 5.0 * th
    ty = TMJ[1] - s * TMJ[0] - c * TMJ[1] + 1.5 * th
    return np.float32([[c, -s, tx], [s, c, ty]])


def jaw_pt(p, th, w=1.0):
    if th == 0 or w == 0:
        return p
    M = jaw_M(th * w)
    return (M[0, 0] * p[0] + M[0, 1] * p[1] + M[0, 2], M[1, 0] * p[0] + M[1, 1] * p[1] + M[1, 2])


def _cat(M1, M2):
    """M1 ∘ M2 (2x3 afin)"""
    A = np.vstack([M1, [0, 0, 1]]) @ np.vstack([M2, [0, 0, 1]])
    return A[:2].astype(np.float32)


def base(cam, th=0.0, hyo=(0.0, 0.0)):
    """çıkış boyutunda float32 RGB (0..255)"""
    D = data()
    M = cam.M()
    flag = cv2.INTER_CUBIC if cam.s > 0.9 else cv2.INTER_AREA if cam.s < 0.5 else cv2.INTER_LINEAR
    if th == 0 and hyo == (0.0, 0.0):
        return cv2.warpAffine(D["O"], M, (W, H), flags=flag, borderValue=(0, 0, 0)).astype(np.float32)
    out = cv2.warpAffine(D["A"], M, (W, H), flags=flag, borderValue=(0, 0, 0)).astype(np.float32)
    for key, Mx in (("C", _cat(M, np.float32([[1, 0, hyo[0]], [0, 1, hyo[1]]]))), ("B", _cat(M, jaw_M(th)))):
        lay = cv2.warpAffine(D[key], Mx, (W, H), flags=flag, borderValue=(0, 0, 0, 0)).astype(np.float32)
        a = lay[..., 3:4] / 255.0
        out = out * (1 - a) + lay[..., :3] * a
    return out
