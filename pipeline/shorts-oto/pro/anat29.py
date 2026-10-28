"""29. video anatomisi: orta sagital baş-boyun kesiti.
Koordinatlar mm (orijin: sert damak arka ucu PNS), x+ öne (yüz sağa), y+ aşağı.
Her kare kamera (cx, cy, k=birim/mm) ile doğrudan ekran pikseline çizilir; organlar yükseklik haritasıyla gölgelenir."""
import math
from types import SimpleNamespace as NS

import cv2
import numpy as np
from PIL import Image, ImageDraw

from engine import u, W, H

Y0 = 930            # anatominin ekrandaki dikey merkezi (birim)
TMJ = (-20.0, -20.0)

# ---------------- yardımcılar ----------------
LDIR = np.array([-0.45, -0.62, 0.64], np.float32)
LDIR /= np.linalg.norm(LDIR)
HV = LDIR + np.array([0, 0, 1], np.float32)
HV /= np.linalg.norm(HV)


def cr(pts, n=6, closed=True):
    """Catmull-Rom eğrisi"""
    P = np.array(pts, np.float64)
    if len(P) < 3:
        return [tuple(p) for p in P]
    P = np.vstack([P[-1], P, P[0], P[1]]) if closed else np.vstack([P[0], P, P[-1]])
    out = []
    tt = np.arange(n) / n
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        t = tt[:, None]
        seg = 0.5 * (2 * p1 + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t ** 2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3)
        out.extend(map(tuple, seg))
    if not closed:
        out.append(tuple(P[-2]))
    return out


def resample(pts, n):
    P = np.array(pts, np.float64)
    d = np.r_[0, np.cumsum(np.hypot(*np.diff(P, axis=0).T))]
    s = np.linspace(0, d[-1], n)
    return np.c_[np.interp(s, d, P[:, 0]), np.interp(s, d, P[:, 1])]


def ribbon(center, widths, n=40):
    """merkez çizgisi + genişlik profili (mm) -> kapalı çokgen"""
    C = resample(cr(center, 6, closed=False), n)
    wd = np.interp(np.linspace(0, 1, n), np.linspace(0, 1, len(widths)), widths)
    d = np.gradient(C, axis=0)
    d /= np.hypot(d[:, 0], d[:, 1])[:, None] + 1e-9
    nrm = np.c_[-d[:, 1], d[:, 0]]
    left = C + nrm * wd[:, None] / 2
    right = C - nrm * wd[:, None] / 2
    return [tuple(p) for p in left] + [tuple(p) for p in right[::-1]], C, nrm, wd


def offset_curve(pts, dist):
    C = np.array(pts, np.float64)
    d = np.gradient(C, axis=0)
    d /= np.hypot(d[:, 0], d[:, 1])[:, None] + 1e-9
    nrm = np.c_[-d[:, 1], d[:, 0]]
    dist = np.broadcast_to(np.asarray(dist, np.float64), (len(C),))
    return C + nrm * dist[:, None]


def ell(cx, cy, rx, ry, ang=0.0, n=40):
    a = math.radians(ang)
    ca, sa = math.cos(a), math.sin(a)
    out = []
    for i in range(n):
        q = 2 * math.pi * i / n
        x, y = rx * math.cos(q), ry * math.sin(q)
        out.append((cx + x * ca - y * sa, cy + x * sa + y * ca))
    return out


def gblur(a, s):
    if s <= 0.3:
        return a
    return cv2.GaussianBlur(a, (0, 0), s)


class Cam:
    def __init__(self, cx, cy, k):
        self.cx, self.cy, self.k = cx, cy, k
        self.pm = u(k)                      # piksel / mm

    def S(self, p):
        return (u(540 + (p[0] - self.cx) * self.k), u(Y0 + (p[1] - self.cy) * self.k))

    def SL(self, pts):
        return [self.S(p) for p in pts]

    def U(self, p):
        """mm -> ekran birimi"""
        return (540 + (p[0] - self.cx) * self.k, Y0 + (p[1] - self.cy) * self.k)


def _mask(polys, x0, y0, w, h, ss=3):
    m = Image.new("L", (w * ss, h * ss), 0)
    d = ImageDraw.Draw(m)
    for poly in polys:
        d.polygon([((x - x0) * ss, (y - y0) * ss) for x, y in poly], fill=255)
    return np.asarray(m.resize((w, h), Image.BOX), np.float32) / 255.0


_RNG = np.random.default_rng(29)
_NOISE = cv2.GaussianBlur(_RNG.standard_normal((900, 600)).astype(np.float32), (0, 0), 2.2)
_NOISE /= _NOISE.std()
_NOISE_MM = 2.0      # gürültü pikseli / mm ; orijin (-150, -250)


def _noise_for(cam, x0, y0, w, h):
    # ekran pikseli -> mm -> gürültü pikseli
    k = cam.pm
    a = _NOISE_MM / k
    M = np.float32([[a, 0, ((x0 - u(540)) / k + cam.cx + 150) * _NOISE_MM],
                    [0, a, ((y0 - u(Y0)) / k + cam.cy + 250) * _NOISE_MM]])
    return cv2.warpAffine(_NOISE, M, (w, h), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP,
                          borderMode=cv2.BORDER_REFLECT)


def organ(L, cam, polys_mm, albedo, alpha=1.0, r_mm=5.0, spec=0.22, shin=30, rim=(0, 0, 0), rimk=0.0,
          glow=None, tex=0.0, fibers=None, fib_amp=0.22, edge=(0, 0, 0), edgek=0.25, amb=0.36, holes=None,
          bump=0.25, cortex=0.0, vgrad=0.0):
    """polys_mm: mm çokgen listesi (birleşim). Gölgeli RGBA'yı L'ye bindirir."""
    if alpha <= 0.004:
        return
    pp = [cam.SL(p) for p in polys_mm]
    allp = np.array([q for p in pp for q in p])
    r = max(1.0, r_mm * cam.pm)
    gpad = 0 if glow is None else glow[2] * cam.pm * 2.5
    pad = int(4 + gpad)
    x0, y0 = int(allp[:, 0].min()) - pad, int(allp[:, 1].min()) - pad
    x1, y1 = int(allp[:, 0].max()) + pad + 1, int(allp[:, 1].max()) + pad + 1
    cx0, cy0, cx1, cy1 = max(0, x0), max(0, y0), min(W, x1), min(H, y1)
    if cx0 >= cx1 or cy0 >= cy1:
        return
    w, h = x1 - x0, y1 - y0
    ma = _mask(pp, x0, y0, w, h)
    if holes:
        ma = ma * (1 - _mask([cam.SL(p) for p in holes], x0, y0, w, h))
    # kubbe yüksekliği (küçültülmüş ölçekte bulanıklık)
    f = max(1.0, r * 1.2 / 10.0)
    sw, sh = max(4, int(w / f)), max(4, int(h / f))
    sm = cv2.resize(ma, (sw, sh), interpolation=cv2.INTER_AREA)
    rs = r / f
    acc = gblur(sm, rs * 0.35) * 0.45 + gblur(sm, rs * 0.7) * 0.35 + gblur(sm, rs * 1.2) * 0.2
    acc = cv2.resize(acc, (w, h), interpolation=cv2.INTER_CUBIC)
    acc = np.clip((acc - 0.18) / 0.82, 0, 1) ** 0.75
    hgt = r * acc * ma
    alb = np.ones((h, w, 3), np.float32) * np.array(albedo, np.float32)
    if tex:
        nz = _noise_for(cam, x0, y0, w, h)
        alb *= (1 + tex * nz)[..., None]
        hgt = hgt + nz * tex * r * bump * ma
    if cortex:
        alb *= (1 - cortex * np.clip(acc * 1.6 - 0.25, 0, 1))[..., None]
    if vgrad:
        yy = np.linspace(0, 1, h, dtype=np.float32)[:, None]
        alb *= (1 - vgrad * yy)[..., None]
    if fibers:
        fm = np.zeros((h, w), np.float32)
        for line in fibers:
            q = np.array([[x - x0, y - y0] for x, y in cam.SL(line)], np.int32)
            cv2.polylines(fm, [q], False, 1.0, thickness=max(1, int(cam.pm * 0.55)), lineType=cv2.LINE_AA)
        fm = gblur(fm, max(0.6, cam.pm * 0.25)) * ma
        alb *= (1 - fib_amp * fm)[..., None]
        hgt = hgt - fm * r * 0.08
    hp = gblur(hgt, 1.0)
    gx = cv2.Sobel(hp, cv2.CV_32F, 1, 0, ksize=3) / 8
    gy = cv2.Sobel(hp, cv2.CV_32F, 0, 1, ksize=3) / 8
    inv = 1 / np.sqrt(gx * gx + gy * gy + 1)
    nx, ny, nz_ = -gx * inv, -gy * inv, inv
    ndl = nx * LDIR[0] + ny * LDIR[1] + nz_ * LDIR[2]
    wrap = np.clip((ndl + 0.3) / 1.3, 0, 1)
    sp = np.clip(nx * HV[0] + ny * HV[1] + nz_ * HV[2], 0, 1) ** shin * spec
    col = alb * (amb + (1.02 - amb) * wrap)[..., None]
    col += sp[..., None] * 255
    if rimk:
        col += ((1 - nz_) ** 1.6 * rimk)[..., None] * np.array(rim, np.float32)
    if edgek:
        ol = np.clip((ma - gblur(ma, 1.3)) * 2.2, 0, 1)[..., None]
        col = col * (1 - edgek * ol) + np.array(edge, np.float32) * edgek * ol
    rgba = np.dstack([np.clip(col, 0, 255), np.clip(ma * alpha * 255, 0, 255)]).astype(np.uint8)
    img = Image.fromarray(rgba, "RGBA")
    if glow is not None:
        gc, gk, gr = glow
        if gk > 0.01:
            gs = max(1.0, gr * cam.pm)
            f2 = max(1.0, gs / 6)
            g = cv2.resize(ma, (max(4, int(w / f2)), max(4, int(h / f2))), interpolation=cv2.INTER_AREA)
            g = cv2.resize(gblur(g, gs / f2), (w, h), interpolation=cv2.INTER_LINEAR)
            ga = np.clip(g * gk * 1.6 * alpha, 0, 1)
            gl = np.dstack([np.ones((h, w, 3), np.float32) * np.array(gc, np.float32), ga * 255]).astype(np.uint8)
            _paste(L, Image.fromarray(gl, "RGBA"), x0, y0)
    _paste(L, img, x0, y0)


def _paste(L, img, x0, y0):
    w, h = img.size
    cx0, cy0 = max(0, x0), max(0, y0)
    cx1, cy1 = min(W, x0 + w), min(H, y0 + h)
    if cx0 >= cx1 or cy0 >= cy1:
        return
    if (cx0, cy0, cx1, cy1) != (x0, y0, x0 + w, y0 + h):
        img = img.crop((cx0 - x0, cy0 - y0, cx1 - x0, cy1 - y0))
    L.alpha_composite(img, (cx0, cy0))


def line_mm(L, cam, pts, col, a, w_mm=0.8, glow=0.0, closed=False, min_px=2):
    if a <= 0.004:
        return
    q = cam.SL(pts)
    if closed:
        q = q + [q[0]]
    wpx = max(min_px, round(w_mm * cam.pm))
    allp = np.array(q)
    pad = int(wpx * 6 + 4)
    x0, y0 = int(allp[:, 0].min()) - pad, int(allp[:, 1].min()) - pad
    x1, y1 = int(allp[:, 0].max()) + pad, int(allp[:, 1].max()) + pad
    w, h = x1 - x0, y1 - y0
    if w <= 0 or h <= 0:
        return
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    qq = [(x - x0, y - y0) for x, y in q]
    if glow:
        g = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        ImageDraw.Draw(g).line(qq, fill=tuple(col) + (int(255 * a * glow),), width=wpx * 4, joint="curve")
        arr = np.asarray(g).copy()
        arr[..., 3] = cv2.GaussianBlur(arr[..., 3], (0, 0), wpx * 1.6)
        im.alpha_composite(Image.fromarray(arr, "RGBA"))
    d.line(qq, fill=tuple(col) + (int(255 * a),), width=wpx, joint="curve")
    _paste(L, im, x0, y0)


# ---------------- geometri (dinlenme, mm) ----------------
# (nokta, çene ağırlığı, gırtlak ağırlığı)
SKIN = [((-25, -170), 0, 0), ((22, -163), 0, 0), ((50, -142), 0, 0), ((65, -112), 0, 0), ((70, -84), 0, 0),
        ((65.5, -63), 0, 0), ((72, -46), 0, 0), ((80, -27), 0, 0), ((87.5, -10), 0, 0), ((85, -2), 0, 0), ((76, 2.5), 0, 0),
        ((66.5, 5), 0, 0), ((67, 13), 0, 0), ((72, 21), 0, 0), ((69.5, 27.5), 0, 0), ((63, 29.6), 0, 0), ((54, 29.9), 0, 0),
        ((54, 30.1), 0.55, 0), ((63, 30.6), 1, 0), ((70, 35), 1, 0), ((70.5, 41), 1, 0), ((65, 50), 1, 0), ((67, 58), 1, 0),
        ((67.5, 66), 1, 0), ((62, 77), 1, 0), ((52, 84.5), 1, 0), ((36, 90), 0.9, 0), ((19, 94), 0.55, 0.1), ((12, 100), 0.25, 0.4),
        ((16.5, 106), 0.05, 0.9), ((13, 117), 0, 0.5), ((9, 150), 0, 0), ((8, 420), 0, 0), ((-97, 420), 0, 0), ((-96, 150), 0, 0),
        ((-92, 70), 0, 0), ((-95, 25), 0, 0), ((-107, -10), 0, 0), ((-117, -55), 0, 0), ((-120, -95), 0, 0),
        ((-108, -135), 0, 0), ((-75, -161), 0, 0)]
VAULT_IDX = (40, 41, 0, 1, 2, 3, 4)   # kafatası kubbesi boyunca (arka->ön)

PALATE = [(0, -1.2), (15, -3), (35, -3.8), (50, -3.2), (57, -2.4), (55.5, 0.5), (57.5, 6), (58.5, 12), (52.5, 13.5),
          (48.5, 9), (42, 6.2), (30, 4.6), (15, 4.2), (2, 3.4)]
UP_INC = [(50.5, 1), (54, 2), (58.4, 12), (59.2, 21), (57.8, 27.6), (55.6, 27.4), (53.2, 20), (51, 12)]
LO_INC = [(54.2, 25.3), (55.9, 30.5), (55.8, 37), (53, 50), (50.8, 51), (50.4, 38), (51.2, 31)]
SYMPH = [(56, 33), (57.6, 41), (55.6, 48.5), (58.2, 57), (60.2, 64), (58, 71), (52, 76.5), (45, 78), (38.5, 75.5),
         (34.8, 68.5), (34, 60.5), (36.5, 51), (42, 42), (49.5, 35.2), (52.5, 33)]
MAND_GHOST = [(-20.5, -23), (-14.5, -21), (-12.5, -13), (-8.5, -6.5), (-3, -11), (3, -17), (6.5, -11), (5, 3), (3, 17),
              (8, 25.5), (22, 27), (40, 28), (52, 31), (56.5, 34), (58, 45), (60.2, 64), (52, 77), (45, 78.5), (24, 69),
              (4, 60.5), (-12, 53.5), (-20.5, 46), (-25.5, 33), (-26, 12), (-25, -6), (-24.5, -16)]
NASAL = [(1, -3.5), (30, -5.5), (50, -5), (60, -6.5), (70, -4.5), (75, -11), (64, -22), (54, -38), (42, -47), (22, -48),
         (6, -43), (-1, -31), (-1.5, -12)]
CONCHAE = [((26, -13), 17, 4.2, -4), ((24, -25.5), 14.5, 3.4, -8), ((13, -36), 8, 2.4, -14)]
PHAR = [(-1.5, -32), (-10, -34), (-21, -32), (-29, -25), (-32.5, -12), (-33.6, 8), (-33.6, 40), (-33, 70), (-32, 95),
        (-31, 110), (-30, 119), (-16, 119), (-14, 100), (-10, 80), (-6, 60), (-6, 30), (-2, 10), (-1, -3)]
WALL_FRONT = [(-29, -27), (-32.5, -12), (-33.6, 8), (-33.6, 40), (-33, 70), (-32, 95), (-31, 110), (-30.5, 119)]
PREV_BACK = [(-36, -26), (-38.5, -10), (-39.5, 30), (-38.5, 55), (-38, 75), (-39.5, 100), (-41.5, 120)]
# omur gövdeleri: (üst y, alt y, ön x)
VERT = [(-4, 32, -41.5), (37, 51, -40.5), (55, 69, -40), (73, 87, -40.5), (91, 105, -42), (109, 123, -44), (127, 142, -46.5),
        (146, 161, -49.5), (165, 180, -53)]
DORSUM = [(51.5, 27.5), (48, 22.5), (43, 17.2), (35, 12.6), (26, 10.2), (16, 9.2), (6, 9.6), (-3, 11.6), (-10.5, 16),
          (-16.5, 23.5), (-20, 32.5), (-21, 42), (-20, 50), (-17, 57)]
DORSUM_S = None
FLOOR = [((-11, 63), 0.4, 0.6), ((-5, 68), 0.6, 1.0), ((2, 70), 0.7, 1.0), ((14, 65.5), 0.9, 0.5), ((27, 59), 1, 0.15),
         ((36, 50.5), 1, 0), ((42.5, 41.5), 1, 0), ((48.5, 33.5), 1, 0)]
VELUM_REST = [(1, -0.5), (-8, 4), (-15.5, 10.5), (-21, 18.5), (-24, 26)]
VELUM_UP = [(1, -0.5), (-9, -0.5), (-18, -1.5), (-25.5, -2), (-30.5, 0)]
VELUM_W = [8.5, 9, 8, 6, 4.5]
EPI_REST = [(5, 92), (-1, 81), (-9.5, 68.5), (-16.5, 57.5), (-20, 48)]
EPI_DOWN = [(5, 92), (-1, 83), (-8, 78.5), (-15.5, 78.5), (-21, 82)]
BPATH = [(29, 8.8), (21, 8.6), (12, 8.4), (3, 8.6), (-7, 11), (-16.5, 17.5), (-24.5, 26), (-27, 36), (-27, 48), (-26.5, 62),
         (-25.5, 76), (-24.5, 90), (-23.8, 104), (-23.5, 118), (-23.5, 140), (-23.5, 170), (-23.5, 210), (-23.5, 260)]


def _dorsum_s():
    P = np.array(DORSUM)
    d = np.r_[0, np.cumsum(np.hypot(*np.diff(P, axis=0).T))]
    return d / d[-1]


DORSUM_S = _dorsum_s()
# dorsum çene ağırlıkları
DORSUM_W = [1, 1, 1, 0.95, 0.9, 0.85, 0.75, 0.65, 0.55, 0.45, 0.4, 0.38, 0.38, 0.4]


ROOF = [(52, 26), (50.5, 15), (47.5, 8.6), (40, 6.1), (28, 5.3), (15, 5.0), (4, 4.9), (-4, 5.6), (-12, 6.6), (-20, 7.8),
        (-26.5, 9.6), (-30.5, 14), (-32, 21), (-32.3, 31), (-32, 42), (-31, 52)]


def _roof_fn():
    P = np.array(cr(ROOF, 4, closed=False))
    d = np.r_[0, np.cumsum(np.hypot(*np.diff(P, axis=0).T))]
    d /= d[-1]
    return lambda s: (float(np.interp(s, d, P[:, 0])), float(np.interp(s, d, P[:, 1])))


ROOF_AT = _roof_fn()


def pal_y(x):
    """damak/yumuşak damak alt yüzeyi (dil hedefi)"""
    if x >= 44:
        return 6.2 + (x - 44) * 0.75
    if x >= 0:
        return 3.6 + (44 - x) * 0.012
    return None


def default_state():
    return NS(th=0.0, lift=0.0, vel=0.0, epi=0.0, wave=None, reach=1.0, press=1.0, cup=0.0, cup_s=0.33, bol=None,
              tens=0.0, focus=set(), jit=(0.0, 0.0), squeeze=None, a=1.0, xr_bones=1.0,
              bol_xy=None, bol_shape=(1.0, 1.0), ghost=0.0)


def jaw(p, st, w=1.0):
    if w <= 0 or (st.th == 0):
        return p
    a = math.radians(st.th * w)
    sl = st.th / 14.0
    dx, dy = p[0] - TMJ[0], p[1] - TMJ[1]
    return (TMJ[0] + dx * math.cos(a) - dy * math.sin(a) + 12.0 * sl * w,
            TMJ[1] + dx * math.sin(a) + dy * math.cos(a) + 3.0 * sl * w)


def hyo_off(st):
    o = st.th / 14.0
    return (9.0 * st.lift + st.jit[0] - 2 * o, -14.0 * st.lift + st.jit[1] + 4 * o)


def lar_off(st):
    o = st.th / 14.0
    return (5.0 * st.lift + st.jit[0] * 0.8 - 1.5 * o, -17.0 * st.lift + st.jit[1] * 0.8 + 3 * o)


def add(p, o, k=1.0):
    return (p[0] + o[0] * k, p[1] + o[1] * k)


def tongue_poly(st):
    ho = hyo_off(st)
    pts = []
    for i, ((x, y), s, w) in enumerate(zip(DORSUM, DORSUM_S, DORSUM_W)):
        c = 0.0
        if st.wave is not None:
            c = clamp01((st.wave - s) / 0.16) * st.reach * st.press
        tx, ty = ROOF_AT(s)
        nx, ny = x + (tx - x) * c, y + (ty - y) * c
        if st.cup > 0:
            ny += 6.0 * st.cup * math.exp(-((s - st.cup_s) / 0.1) ** 2)
        if s > 0.6:   # dil kökü gırtlakla biraz kalkar
            nx, ny = add((nx, ny), ho, 0.35 * (s - 0.6) / 0.4)
        pts.append(jaw((nx, ny), st, w))
    for (p, w, hw) in FLOOR:
        q = add(p, ho, hw)
        pts.append(jaw(q, st, w * (1 - hw * 0.5)))
    return pts


def clamp01(x):
    return 0.0 if x < 0 else (1.0 if x > 1 else x)


def velum_poly(st):
    c = [lp(a, b, st.vel) for a, b in zip(VELUM_REST, VELUM_UP)]
    poly, C, N, wd = ribbon(c, VELUM_W, 30)
    return poly, C


def lp(a, b, t):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


def bolus_xy(b):
    P = np.array(BPATH)
    d = np.r_[0, np.cumsum(np.hypot(*np.diff(P, axis=0).T))]
    s = clamp01(b) * d[-1]
    x, y = np.interp(s, d, P[:, 0]), np.interp(s, d, P[:, 1])
    s2 = min(d[-1], s + 3)
    x2, y2 = np.interp(s2, d, P[:, 0]), np.interp(s2, d, P[:, 1])
    return (float(x), float(y)), math.degrees(math.atan2(y2 - y, x2 - x + 1e-9))


# ---------------- çizim ----------------
BONE = (246, 241, 229)
TOOTH = (252, 253, 255)
TONGUE = (226, 92, 112)
VELC = (236, 128, 148)
MUSC = (214, 46, 62)
CART = (176, 214, 242)
AIR = (6, 10, 24)
PINKW = (200, 96, 122)
CYAN = (120, 220, 255)
GOLD = (255, 200, 80)
REDG = (255, 70, 70)


def skin_layer(L, cam, st):
    pts = [add(jaw(p, st, wj), lar_off(st), wl) for p, wj, wl in SKIN]
    curve = cr(pts, 5)
    q = cam.SL(curve)
    ss = 2
    m = Image.new("L", (W // ss, H // ss), 0)
    ImageDraw.Draw(m).polygon([(x / ss, y / ss) for x, y in q], fill=255)
    ma = np.asarray(m, np.float32) / 255
    sm = cv2.resize(ma, (W // 8, H // 8), interpolation=cv2.INTER_AREA)
    inner = cv2.resize(gblur(sm, cam.pm * 9 / 8), (W // ss, H // ss), interpolation=cv2.INTER_LINEAR)
    rim = np.clip(ma - inner, 0, 1)
    a = (0.20 + 0.75 * rim ** 1.2) * ma * st.a
    col = np.zeros((H // ss, W // ss, 3), np.float32)
    col[:] = (42, 108, 176)
    col += rim[..., None] * np.array([70, 110, 80], np.float32)
    rgba = np.dstack([np.clip(col, 0, 255), np.clip(a * 255, 0, 255)]).astype(np.uint8)
    L.alpha_composite(Image.fromarray(rgba, "RGBA").resize((W, H), Image.BILINEAR))
    line_mm(L, cam, curve, CYAN, 0.95 * st.a, w_mm=0.55, glow=0.55, closed=True)
    return pts


def vault(L, cam, st):
    pts = [SKIN[i][0] for i in VAULT_IDX]
    c = cr(pts, 8, closed=False)
    mid = offset_curve(c, 7.5)
    n = len(mid)
    wd = np.minimum(1, np.minimum(np.arange(n), n - 1 - np.arange(n)) / 10.0) * 6.5
    poly, C, N, w2 = ribbon([tuple(p) for p in mid[::3]] + [tuple(mid[-1])], list(wd[::3]) + [0], 60)
    organ(L, cam, [poly], BONE, alpha=0.30 * st.a * st.xr_bones, r_mm=3, spec=0.1, tex=0.08, edgek=0)


def draw(L, cam, st):
    """L: ekran boyutunda RGBA katman"""
    A = st.a
    F = st.focus
    ho, lo = hyo_off(st), lar_off(st)
    skin_layer(L, cam, st)
    vault(L, cam, st)
    # hava yolları
    organ(L, cam, [cr(NASAL, 4)], AIR, alpha=0.62 * A, r_mm=2, spec=0, edgek=0, amb=1)
    for (cx, cy), rx, ry, an in CONCHAE:
        organ(L, cam, [ell(cx, cy, rx, ry, an)], (214, 120, 140), alpha=0.26 * A, r_mm=3, spec=0.15, tex=0.05, bump=0.0)
    organ(L, cam, [cr(PHAR, 4)], AIR, alpha=0.70 * A, r_mm=2, spec=0, edgek=0, amb=1)
    # omurga + omurilik
    cord = [(-64, -40), (-64, 0), (-63, 60), (-65, 120), (-69, 200), (-72, 260)]
    for i, (yt, yb, xf) in enumerate(VERT):
        body = [(xf, yt + 1.5), (xf - 1, (yt + yb) / 2), (xf, yb - 1.5), (xf - 2, yb), (xf - 14, yb), (xf - 15.5, yb - 2),
                (xf - 15.5, yt + 2), (xf - 14, yt), (xf - 2, yt)]
        if i == 0:
            body = [(xf - 3, yt - 13), (xf - 2, yt - 4)] + body[:-1] + [(xf - 12, yt - 4), (xf - 11, yt - 13), (xf - 7, yt - 15.5)]
        organ(L, cam, [cr(body, 4)], BONE, alpha=0.9 * A * st.xr_bones, r_mm=4.5, spec=0.2, tex=0.05, bump=0.0, cortex=0.12)
        if i < len(VERT) - 1:
            nt = VERT[i + 1][0]
            organ(L, cam, [[(xf + 0.5, yb + 0.4), (xf - 15, yb + 0.4), (VERT[i + 1][2] - 15, nt - 0.4), (VERT[i + 1][2] + 0.5, nt - 0.4)]],
                  (120, 170, 220), alpha=0.6 * A, r_mm=1.5, spec=0.1, edgek=0)
        # diken çıkıntısı (silik)
    organ(L, cam, [ell(-46, -10, 4.5, 6)], BONE, alpha=0.85 * A * st.xr_bones, r_mm=3, spec=0.15)   # atlas ön kemeri
    # yutak arka duvarı (kas) + yemek borusu
    sq = st.squeeze
    wf = []
    for x, y in cr(WALL_FRONT, 5, closed=False):
        if sq is not None:
            x += sq[1] * math.exp(-((y - sq[0]) / 9.0) ** 2)
        wf.append((x, y))
    prev = wf + [(-31, 420), (-42, 420)] + cr(PREV_BACK, 5, closed=False)[::-1]
    organ(L, cam, [prev], PINKW, alpha=0.5 * A, r_mm=3.5, spec=0.18, tex=0.05, bump=0.0, rim=(255, 180, 200), rimk=0.2)
    by = None
    if st.bol is not None:
        (bx, by), _ = bolus_xy(st.bol)
    ys = np.linspace(116, 420, 50)
    bul = np.array([4.0 * math.exp(-((y - by) / 11) ** 2) if by is not None and by > 108 else 0.0 for y in ys])
    eso = [(-31 - b, y) for b, y in zip(bul, ys)] + [(-16 + b, y) for b, y in zip(bul[::-1], ys[::-1])]
    organ(L, cam, [eso], (206, 104, 132), alpha=0.7 * A, r_mm=4, spec=0.25, tex=0.04, bump=0.0)
    line_mm(L, cam, [(-23.5, 121), (-23.5, 420)], (90, 30, 50), 0.7 * A, w_mm=0.7)
    # alt çene (yan, hayalet)
    mg = cr([jaw(p, st) for p in MAND_GHOST], 5)
    jf = "jaw" in F
    if st.ghost > 0.01:
        organ(L, cam, [mg], GOLD, alpha=0.2 * st.ghost * A, r_mm=5, spec=0.05, edgek=0, amb=1, glow=(GOLD, 0.55 * st.ghost, 5))
        line_mm(L, cam, mg, GOLD, 0.95 * st.ghost * A, w_mm=0.7, glow=0.8, closed=True)
    # burun boşluğu tabanı: sert damak
    pf = "palate" in F
    organ(L, cam, [cr(PALATE, 4)], BONE, alpha=0.95 * A * st.xr_bones, r_mm=3.5, spec=0.25, tex=0.05, bump=0.0, cortex=0.1,
          glow=(GOLD, 0.6, 4) if pf else None)
    organ(L, cam, [cr(UP_INC, 4)], TOOTH, alpha=0.97 * A, r_mm=2.5, spec=0.45, shin=40, rim=(160, 200, 255), rimk=0.3)
    # yumuşak damak
    vp, vc = velum_poly(st)
    organ(L, cam, [vp], VELC, alpha=0.95 * A, r_mm=4, spec=0.25, tex=0.1, rim=(255, 190, 210), rimk=0.25,
          glow=(GOLD, 0.6, 4) if pf else None)
    # dil kemiği arkasındaki gırtlak grubu (hava, kıkırdak)
    LA = lambda pts: [add(p, lo) for p in pts]
    organ(L, cam, [LA([(-13, 121), (7, 121), (7, 420), (-13, 420)])], AIR, alpha=0.8 * A, r_mm=2, spec=0, edgek=0, amb=1)
    organ(L, cam, [LA([(-17, 86), (-11, 84), (0, 86.5), (5.5, 92), (7, 121), (-13, 121), (-15, 100)])], AIR, alpha=0.85 * A,
          r_mm=2, spec=0, edgek=0, amb=1)
    rings = [LA(cr([(6.5, y), (11.5, y - 0.3), (12, y + 1.9), (11.5, y + 3.8), (6.5, y + 3.6)], 3)) for y in np.arange(124, 330, 6.5)]
    organ(L, cam, rings, CART, alpha=0.85 * A, r_mm=1.8, spec=0.3, rim=(220, 240, 255), rimk=0.2)
    organ(L, cam, [LA([(-13.5, 121), (-16, 121), (-16, 420), (-13.5, 420)])], PINKW, alpha=0.7 * A, r_mm=1.2, edgek=0)
    lf = "lar" in F
    lg = (GOLD, 0.6, 4) if lf else ((REDG, 0.5, 4) if "lar_red" in F else None)
    organ(L, cam, [LA(cr([(9.5, 83), (15.5, 85.5), (15, 96), (12.8, 111), (9.8, 112.5), (8.6, 100), (8, 88)], 4))], CART,
          alpha=0.92 * A, r_mm=2.2, spec=0.35, rim=(220, 240, 255), rimk=0.3, glow=lg)
    line_mm(L, cam, LA(cr([(15, 86), (-14, 84), (-17, 71), (-12, 88), (-13, 108), (-6, 112), (12, 112)], 4)), CART, 0.35 * A,
            w_mm=0.5)
    organ(L, cam, [LA(cr([(8.5, 115), (12.2, 115.8), (12.6, 121.4), (8.8, 122), (7, 119)], 3)),
                   LA(cr([(-22.5, 98), (-16, 97), (-15, 121.5), (-21, 122.5), (-23.5, 110)], 3))], CART, alpha=0.9 * A,
          r_mm=2.2, spec=0.3, glow=lg)
    organ(L, cam, [LA(cr([(-19.5, 97.5), (-15.5, 96.5), (-12, 89.5), (-17.5, 85.5)], 3))], (215, 140, 160), alpha=0.9 * A,
          r_mm=2, spec=0.25)
    # gırtlak kapağı
    ec = [add(lp(a, b, st.epi), lo) for a, b in zip(EPI_REST, EPI_DOWN)]
    ep, _, _, _ = ribbon(ec, [2.0, 3.6, 5.0, 5.2, 3.2], 30)
    organ(L, cam, [ep], (240, 214, 170), alpha=0.95 * A, r_mm=2, spec=0.35, rim=(255, 240, 210), rimk=0.25, glow=lg)
    line_mm(L, cam, [ec[-1], add((-18, 84), lo)], (230, 150, 170), 0.45 * A, w_mm=0.9)
    # dil kemiği
    hf = "hyoid" in F
    hyc = add((3, 74), ho)
    line_mm(L, cam, [add((4, 78), ho), add((12, 84), lo)], CART, 0.3 * A, w_mm=0.6)
    organ(L, cam, [cr([add((hyc[0] + dx, hyc[1] + dy), (0, 0)) for dx, dy in
                       [(-3.5, -5), (2, -6.5), (5.5, -3), (6, 2), (3, 6), (-2.5, 5.5), (-1, 2), (-2.5, -1.5)]], 4)],
          GOLD if hf else BONE, alpha=0.97 * A * st.xr_bones, r_mm=3, spec=0.3, tex=0.06, glow=(GOLD, 0.75, 5) if hf else None)
    # dil
    tp = tongue_poly(st)
    tf = "tongue" in F
    tc = cr(tp, 5)
    s_fib = []
    gt = jaw((34.5, 61), st)
    for k in range(9):
        q = DORSUM[1 + k]
        tgt = jaw(q, st, DORSUM_W[1 + k])
        s_fib.append([gt, lp(gt, tgt, 0.55), lp(gt, tgt, 0.92)])
    organ(L, cam, [tc], TONGUE, alpha=0.97 * A, r_mm=11, spec=0.32, shin=22, tex=0.05, bump=0.0, rim=(255, 170, 190),
          rimk=0.35, fibers=s_fib, fib_amp=0.08, vgrad=0.25, glow=((255, 150, 175), 0.55, 5) if tf else None)
    # dil kemiği kasları
    mf = "mus" in F
    th_ = 1 + 0.28 * st.tens
    for o, i, wd in (((34.5, 61.5), (6, 70), [2.5, 7.0, 7.5, 6.0, 3.0]), ((41, 75), (6.5, 77.5), [2.5, 6.2, 6.6, 5.4, 2.8])):
        a0, a1 = jaw(o, st), add(i, ho)
        mid = lp(a0, a1, 0.5)
        dx, dy = a1[0] - a0[0], a1[1] - a0[1]
        ln = math.hypot(dx, dy) + 1e-6
        nrm = (-dy / ln, dx / ln)
        bow = 1.4
        mid = (mid[0] + nrm[0] * bow, mid[1] + nrm[1] * bow)
        poly, C, N, w2 = ribbon([a0, lp(a0, mid, 0.5), mid, lp(mid, a1, 0.5), a1], [w * th_ for w in wd], 36)
        fib = [[tuple(C[j] + N[j] * w2[j] * f) for j in range(0, 36, 3)] for f in np.linspace(-0.36, 0.36, 7)]
        organ(L, cam, [poly], (236, 64, 78) if mf else MUSC, alpha=0.95 * A, r_mm=3.2, spec=0.3, tex=0.04, bump=0.0, fibers=fib,
              fib_amp=0.3, rim=(255, 150, 150), rimk=0.3,
              glow=((255, 80, 90), 0.5 + 0.4 * st.tens, 5) if mf else None)
    # dil altı kası (askı kası, aşağı)
    strap, C, N, w2 = ribbon([add((7, 79), ho), add((16, 100), lo), add((16, 140), lo), (15, 260)], [3, 4, 4, 4], 30)
    organ(L, cam, [strap], MUSC, alpha=0.42 * A, r_mm=2, spec=0.15, edgek=0)
    # çene kemiği kesiti + alt diş
    organ(L, cam, [cr([jaw(p, st) for p in SYMPH], 4)], (255, 214, 120) if jf else BONE, alpha=0.97 * A * st.xr_bones, r_mm=5,
          spec=0.25, tex=0.05, bump=0.0, cortex=0.12, glow=(GOLD, 0.7, 5) if jf else None)
    organ(L, cam, [cr([jaw(p, st) for p in LO_INC], 4)], TOOTH, alpha=0.97 * A, r_mm=2.5, spec=0.45, shin=40,
          rim=(160, 200, 255), rimk=0.3)
    # dudaklar
    up = [(64.5, 8), (65, 13.5), (69, 21), (67, 26.8), (62, 28.9), (59, 28.8), (59.8, 20), (61.5, 11)]
    lo_l = [jaw(p, st) for p in [(59, 31.2), (62.5, 31.3), (67.5, 35.5), (67.8, 41), (63.5, 46.5), (60, 45), (59, 38)]]
    organ(L, cam, [cr(up, 4), cr(lo_l, 4)], (232, 120, 140), alpha=0.55 * A, r_mm=3, spec=0.3, edgek=0)
    # lokma
    if st.bol is not None:
        (bx, by), ang = bolus_xy(st.bol)
        if st.bol_xy is not None:
            bx, by = st.bol_xy
        sx, sy = st.bol_shape
        organ(L, cam, [ell(bx, by, 5.2 * sx, 5.2 * sy, ang)], (90, 190, 255), alpha=0.88 * A, r_mm=5, spec=0.9, shin=50,
              rim=(220, 245, 255), rimk=0.6, edgek=0.3, edge=(200, 240, 255), glow=((90, 190, 255), 0.45, 4))
    return tp
