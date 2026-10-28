"""29. video: x-ray render üzerine ışıyan organ katmanları (kaynak piksel koordinatları, yüz sağa)."""
import math
from types import SimpleNamespace as NS

import cv2
import numpy as np
from PIL import Image, ImageDraw

from engine import u, W, H
from xr29 import jaw_pt, HYO_POLY
from anat29 import cr, ribbon

# ---------------- geometri (kaynak px) ----------------
DORSUM = [(2350, 1992), (2346, 1960), (2318, 1918), (2268, 1882), (2200, 1857), (2120, 1843), (2035, 1838), (1950, 1840),
          (1872, 1852), (1806, 1876), (1752, 1912), (1712, 1962), (1686, 2030), (1672, 2110), (1670, 2190), (1680, 2258),
          (1704, 2302)]
DORSUM_W = [1, 1, 1, 0.98, 0.95, 0.92, 0.88, 0.84, 0.78, 0.7, 0.62, 0.55, 0.5, 0.45, 0.42, 0.4, 0.4]
# (nokta, çene ağırlığı, dil kemiği ağırlığı)
FLOOR = [((1750, 2320), 0.35, 0.9), ((1840, 2312), 0.45, 0.8), ((1950, 2302), 0.6, 0.45), ((2065, 2294), 0.8, 0.2),
         ((2170, 2276), 0.95, 0.05), ((2238, 2238), 1, 0), ((2282, 2172), 1, 0), ((2312, 2100), 1, 0), ((2336, 2036), 1, 0)]
ROOF = [(2366, 1985), (2350, 1915), (2296, 1858), (2200, 1830), (2080, 1823), (1960, 1823), (1862, 1830), (1782, 1846),
        (1700, 1852), (1622, 1858), (1560, 1874), (1522, 1925), (1512, 2000), (1512, 2100), (1515, 2200), (1522, 2290)]
VEL_REST = [(1842, 1808), (1804, 1832), (1770, 1862), (1746, 1896), (1734, 1928)]
VEL_UP = [(1842, 1808), (1778, 1802), (1708, 1797), (1638, 1795), (1572, 1802)]
VEL_W = [62, 60, 50, 40, 46]
EPI_REST = [(1716, 2520), (1694, 2450), (1672, 2384), (1655, 2322), (1646, 2280)]
EPI_DOWN = [(1716, 2520), (1686, 2482), (1642, 2466), (1598, 2468), (1566, 2484)]
EPI_W = [16, 26, 32, 28, 16]
AIR = [(1830, 1798), (1790, 1735), (1690, 1705), (1580, 1712), (1508, 1748), (1494, 1830), (1494, 1960), (1498, 2120),
       (1504, 2280), (1512, 2420), (1525, 2520), (1545, 2620), (1600, 2640), (1640, 2560), (1655, 2470), (1660, 2350),
       (1690, 2300), (1760, 1990), (1820, 1880)]
THYROID = [(1802, 2458), (1796, 2520), (1786, 2580), (1772, 2632), (1740, 2648), (1700, 2650), (1660, 2652), (1640, 2670),
           (1628, 2664), (1630, 2648), (1624, 2600), (1622, 2540), (1626, 2482), (1618, 2428), (1630, 2422), (1642, 2470),
           (1680, 2486), (1730, 2492), (1766, 2478), (1788, 2462)]
CRICOID = [(1640, 2652), (1774, 2640), (1778, 2690), (1700, 2702), (1626, 2704), (1620, 2672)]
PHAR_WALL = [(1610, 1716), (1540, 1745), (1505, 1830), (1500, 1960), (1503, 2120), (1508, 2280), (1514, 2420), (1526, 2540),
             (1532, 2650)]
CRICOID = [(1640, 2604), (1648, 2662), (1700, 2674), (1768, 2666), (1772, 2702), (1700, 2714), (1630, 2718), (1612, 2702),
           (1614, 2612)]
TRACHEA = [(1628, 2640), (1778, 2640), (1764, 2706), (1742, 2800), (1708, 2900), (1672, 3010), (1520, 3010), (1556, 2900),
           (1586, 2800), (1610, 2706)]
ESO_PATH = [(1540, 2650), (1522, 2760), (1496, 2880), (1470, 2990), (1440, 3110), (1410, 3240)]
BPATH = [(2120, 1868), (2030, 1862), (1940, 1866), (1858, 1884), (1790, 1912), (1700, 1955), (1620, 2000), (1585, 2080),
         (1574, 2180), (1572, 2280), (1574, 2380), (1570, 2470), (1556, 2560), (1540, 2650), (1522, 2760), (1496, 2880),
         (1470, 2990), (1440, 3110), (1410, 3240)]
MAND = [(1528, 1688), (1534, 1800), (1540, 1950), (1580, 2060), (1640, 2140), (1720, 2215), (1850, 2300), (2000, 2380),
        (2150, 2440), (2280, 2472), (2342, 2484), (2404, 2470), (2418, 2380), (2420, 2250), (2418, 2150), (2402, 2080)]
GENIO = ((2262, 2338), (1800, 2352), [18, 62, 68, 54, 22])
DIGAS = ((2286, 2452), (1800, 2424), [18, 54, 60, 48, 20])
GENIAL = (2262, 2338)      # kasların çeneye tutunduğu yer


def _arc(P):
    P = np.array(P, np.float64)
    d = np.r_[0, np.cumsum(np.hypot(*np.diff(P, axis=0).T))]
    return P, d


_DP, _DD = _arc(DORSUM)
DORSUM_S = _DD / _DD[-1]
_RP, _RD = _arc(cr(ROOF, 5, closed=False))
_BP, _BD = _arc(BPATH)


def b_of_y(y):
    """lokma yolunda verilen y'ye ilk ulaştığı b"""
    for i in range(len(BPATH) - 1):
        if BPATH[i + 1][1] >= y and BPATH[i][1] <= y and BPATH[i + 1][1] != BPATH[i][1]:
            q = (y - BPATH[i][1]) / (BPATH[i + 1][1] - BPATH[i][1])
            return float((_BD[i] + q * (_BD[i + 1] - _BD[i])) / _BD[-1])
    return 1.0


def b_of_x(x):
    """ağız bölümünde verilen x'e karşılık gelen b"""
    for i in range(6):
        if BPATH[i][0] >= x >= BPATH[i + 1][0]:
            q = (BPATH[i][0] - x) / (BPATH[i][0] - BPATH[i + 1][0])
            return float((_BD[i] + q * (_BD[i + 1] - _BD[i])) / _BD[-1])
    return 0.0


def roof_at(s):
    d = s * _RD[-1]
    return float(np.interp(d, _RD, _RP[:, 0])), float(np.interp(d, _RD, _RP[:, 1]))


def bolus_at(b):
    d = min(max(b, 0.0), 1.0) * _BD[-1]
    x, y = float(np.interp(d, _BD, _BP[:, 0])), float(np.interp(d, _BD, _BP[:, 1]))
    d2 = min(_BD[-1], d + 30)
    x2, y2 = float(np.interp(d2, _BD, _BP[:, 0])), float(np.interp(d2, _BD, _BP[:, 1]))
    if d2 - d < 5:
        return (x, y), 90.0
    return (x, y), math.degrees(math.atan2(y2 - y, x2 - x + 1e-9))


def s_near_x(x):
    """dorsum ön yarısında verilen x'e karşılık gelen s"""
    xs = _DP[:12, 0][::-1]
    ss = DORSUM_S[:12][::-1]
    return float(np.interp(x, xs, ss))


def state():
    return NS(th=0.0, hyo=(0.0, 0.0), lar=(0.0, 0.0), vel=0.0, epi=0.0, wave=None, reach=1.0, press=1.0, cup=0.0, cup_s=0.3,
              bol=None, bol_xy=None, bol_a=1.0, bol_shape=(1.0, 1.0), tens=0.0, focus={}, a=1.0, air=0.0, eso=0.0,
              mand=0.0, anchor=0.0)


def add(p, o, k=1.0):
    return (p[0] + o[0] * k, p[1] + o[1] * k)


def lp(a, b, t):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


def tongue_pts(st):
    pts = []
    for (x, y), s, w in zip(DORSUM, DORSUM_S, DORSUM_W):
        c = 0.0
        if st.wave is not None:
            c = min(1.0, max(0.0, (st.wave - s) / 0.12))
            behind = min(1.0, max(0.0, (st.wave - 0.38 - s) / 0.2))
            c = c * (1 - 0.45 * behind) * st.reach * st.press
        tx, ty = roof_at(s)
        dx, dy = tx - x, ty - y
        ln = math.hypot(dx, dy) + 1e-6
        tx, ty = tx - dx / ln * 18, ty - dy / ln * 18
        nx, ny = x + (tx - x) * c, y + (ty - y) * c
        if st.cup > 0:
            ny += 72 * st.cup * math.exp(-((s - st.cup_s) / 0.11) ** 2)
        if s > 0.65:
            nx, ny = add((nx, ny), st.hyo, 0.4 * (s - 0.65) / 0.35)
        pts.append(jaw_pt((nx, ny), st.th, w))
    for p, w, hw in FLOOR:
        pts.append(jaw_pt(add(p, st.hyo, hw), st.th, w))
    return pts


def dorsum_point(st, s):
    """deforme dorsum üzerinde s noktası"""
    tp = tongue_pts(st)[:len(DORSUM)]
    P = np.array(tp)
    return float(np.interp(s, DORSUM_S, P[:, 0])), float(np.interp(s, DORSUM_S, P[:, 1]))


# ---------------- çizim yardımcıları ----------------
def _bbox(pp, pad):
    a = np.array([q for p in pp for q in p])
    x0, y0 = int(a[:, 0].min() - pad), int(a[:, 1].min() - pad)
    x1, y1 = int(a[:, 0].max() + pad + 1), int(a[:, 1].max() + pad + 1)
    return x0, y0, x1, y1


def _mask(pp, x0, y0, w, h, ss=2):
    m = Image.new("L", (w * ss, h * ss), 0)
    d = ImageDraw.Draw(m)
    for p in pp:
        if len(p) >= 3:
            d.polygon([((x - x0) * ss, (y - y0) * ss) for x, y in p], fill=255)
    return np.asarray(m.resize((w, h), Image.BOX), np.float32) / 255.0


def _lines_mask(lines, x0, y0, w, h, wd, ss=2):
    m = Image.new("L", (w * ss, h * ss), 0)
    d = ImageDraw.Draw(m)
    for ln in lines:
        d.line([((x - x0) * ss, (y - y0) * ss) for x, y in ln], fill=255, width=max(1, int(wd * ss)), joint="curve")
    return np.asarray(m.resize((w, h), Image.BOX), np.float32) / 255.0


def _blur(a, s):
    if s < 0.6:
        return a
    f = max(1, int(s / 6))
    if f > 1:
        h, w = a.shape
        sm = cv2.resize(a, (max(2, w // f), max(2, h // f)), interpolation=cv2.INTER_AREA)
        sm = cv2.GaussianBlur(sm, (0, 0), s / f)
        return cv2.resize(sm, (w, h), interpolation=cv2.INTER_LINEAR)
    return cv2.GaussianBlur(a, (0, 0), s)


def _screen(buf, x0, y0, light):
    h, w = light.shape[:2]
    X0, Y0, X1, Y1 = max(0, x0), max(0, y0), min(W, x0 + w), min(H, y0 + h)
    if X0 >= X1 or Y0 >= Y1:
        return
    L = light[Y0 - y0:Y1 - y0, X0 - x0:X1 - x0]
    o = buf[Y0:Y1, X0:X1]
    buf[Y0:Y1, X0:X1] = 255 - (255 - o) * (1 - np.clip(L, 0, 255) / 255)


def _mul(out, x0, y0, k):
    h, w = k.shape
    X0, Y0, X1, Y1 = max(0, x0), max(0, y0), min(W, x0 + w), min(H, y0 + h)
    if X0 >= X1 or Y0 >= Y1:
        return
    out[Y0:Y1, X0:X1] *= (1 - k[Y0 - y0:Y1 - y0, X0 - x0:X1 - x0])[..., None]


LDIR = np.array([-0.45, -0.62, 0.64], np.float32)
LDIR /= np.linalg.norm(LDIR)
HV = LDIR + np.array([0, 0, 1], np.float32)
HV /= np.linalg.norm(HV)


def xglow(buf, cam, polys, color, a=1.0, r=40, inner=0.12, fres=1.0, fpow=1.6, spec=0.3, shin=24, glow_k=0.35,
          glow_r=26, lines=None, line_k=0.3, line_w=3, edge=0.25):
    """x-ray render'ına uyan hacimli, yarı saydam (fresnel) organ ışığı -> buf"""
    if a <= 0.004:
        return
    pp = [cam.SL(p) for p in polys]
    s = cam.s
    gr = glow_r * s
    x0, y0, x1, y1 = _bbox(pp, gr * 2.2 + 6)
    x0, y0 = max(x0, -int(gr * 3)), max(y0, -int(gr * 3))
    x1, y1 = min(x1, W + int(gr * 3)), min(y1, H + int(gr * 3))
    w, h = x1 - x0, y1 - y0
    if w <= 2 or h <= 2:
        return
    m = _mask(pp, x0, y0, w, h)
    rp = max(2.0, r * s)
    f = max(1.0, rp * 1.2 / 10.0)
    sw, sh = max(4, int(w / f)), max(4, int(h / f))
    sm = cv2.resize(m, (sw, sh), interpolation=cv2.INTER_AREA)
    rs = rp / f
    acc = (cv2.GaussianBlur(sm, (0, 0), max(0.5, rs * 0.35)) * 0.45 + cv2.GaussianBlur(sm, (0, 0), max(0.5, rs * 0.7)) * 0.35
           + cv2.GaussianBlur(sm, (0, 0), max(0.5, rs * 1.2)) * 0.2)
    acc = np.clip((acc - 0.18) / 0.82, 0, 1) ** 0.75
    hgt = cv2.GaussianBlur(rs * acc * sm, (0, 0), 0.8)
    gx = cv2.Sobel(hgt, cv2.CV_32F, 1, 0, ksize=3) / 8
    gy = cv2.Sobel(hgt, cv2.CV_32F, 0, 1, ksize=3) / 8
    inv = 1 / np.sqrt(gx * gx + gy * gy + 1)
    nx, ny, nz = -gx * inv, -gy * inv, inv
    fr_s = (1 - nz) ** fpow
    sp_s = np.clip(nx * HV[0] + ny * HV[1] + nz * HV[2], 0, 1) ** shin * spec
    up = lambda a_: cv2.GaussianBlur(cv2.resize(a_, (w, h), interpolation=cv2.INTER_LINEAR), (0, 0), max(0.6, f * 0.35))
    fr, sp = up(fr_s), up(sp_s)
    ol = np.clip((m - _blur(m, 1.6 * s + 0.6)) * 2.0, 0, 1)
    lv = m * (inner + fres * fr) + ol * edge
    if lines:
        lm = _lines_mask([cam.SL(l) for l in lines], x0, y0, w, h, line_w * s)
        lv = lv + _blur(lm, 1.0) * m * line_k
    if glow_k:
        lv = lv + _blur(m, gr) * glow_k
    light = np.clip(lv * a, 0, 1.5)[..., None] * np.array(color, np.float32) + (sp * m * a)[..., None] * 255
    _screen(buf, x0, y0, light)


def darken(out, cam, polys, k=0.5, blur_r=14):
    if k <= 0.004:
        return
    pp = [cam.SL(p) for p in polys]
    br = blur_r * cam.s
    x0, y0, x1, y1 = _bbox(pp, br * 2.5 + 4)
    w, h = x1 - x0, y1 - y0
    if w <= 2 or h <= 2:
        return
    m = _blur(_mask(pp, x0, y0, w, h), br)
    _mul(out, x0, y0, m * k)


def line_glow(buf, cam, pts, color, a=1.0, wd=6, glow_k=0.6, glow_r=14, closed=False):
    if a <= 0.004:
        return
    q = cam.SL(pts)
    if closed:
        q = q + [q[0]]
    s = cam.s
    gr = glow_r * s
    x0, y0, x1, y1 = _bbox([q], gr * 2.5 + 6)
    w, h = x1 - x0, y1 - y0
    if w <= 2 or h <= 2:
        return
    lm = _lines_mask([q], x0, y0, w, h, wd * s)
    lv = lm + _blur(lm, gr) * glow_k
    _screen(buf, x0, y0, np.clip(lv * a, 0, 1.3)[..., None] * np.array(color, np.float32))


def ellipse(cx, cy, rx, ry, ang=0.0, n=40):
    a = math.radians(ang)
    ca, sa = math.cos(a), math.sin(a)
    return [(cx + rx * math.cos(2 * math.pi * i / n) * ca - ry * math.sin(2 * math.pi * i / n) * sa,
             cy + rx * math.cos(2 * math.pi * i / n) * sa + ry * math.sin(2 * math.pi * i / n) * ca) for i in range(n)]


# ---------------- sahne ----------------
PINK = (255, 112, 165)
VELC = (255, 150, 190)
MUSC = (255, 92, 60)
GOLD = (255, 196, 70)
BONEW = (186, 226, 255)
BAR = (236, 251, 255)
EPIC = (255, 224, 165)
REDL = (255, 84, 84)


def draw(out, cam, st):
    """out: (H,W,3) float32 x-ray zemini; organlar ayrı ışık tamponunda toplanıp hafif yumuşatılır"""
    A = st.a
    F = st.focus
    fk = lambda k: F.get(k, 0.0)
    LA = lambda pts: [add(p, st.lar) for p in pts]
    # hava yolu (koyu kanal)
    darken(out, cam, [cr(AIR, 4)], 0.38 * A * (1 - 0.6 * st.air), 20)
    tp = tongue_pts(st)
    if st.th > 0.3:
        # ağız açıkken damak ile dil sırtı arasında açılan hava boşluğu
        roof = [(2372, 1990), (2350, 1912), (2296, 1852), (2200, 1822), (2080, 1815), (1960, 1815), (1862, 1822)]
        dors = [p for p in tp[:len(DORSUM)] if p[0] >= 1862]
        darken(out, cam, [roof + dors[::-1] if dors and dors[0][0] < dors[-1][0] else roof + dors],
               0.5 * A * min(1.0, st.th / 6), 12)
    buf = np.zeros_like(out)
    # yutağın arka duvarı (lokmanın geçtiği tüp)
    pw, _, _, _ = ribbon(PHAR_WALL, [30, 40, 46, 48, 48, 46, 44, 42, 40], 40)
    xglow(buf, cam, [pw], (255, 150, 180), a=A * (0.55 + 0.45 * fk("phar")), r=20, inner=0.1, fres=0.9, spec=0.2,
          glow_k=0.12 + 0.4 * fk("phar"), glow_r=18, edge=0.15)
    # yemek borusu: lokma geçerken belirir
    if st.eso > 0.01:
        ep_, _, _, _ = ribbon(ESO_PATH, [70, 72, 72, 70, 66, 60], 40)
        xglow(buf, cam, [ep_], (255, 150, 175), a=A * st.eso, r=30, inner=0.08, fres=0.9, spec=0.15, glow_k=0.25,
              glow_r=22, edge=0.15)
    # gırtlak, soluk borusu
    lk = max(fk("lar"), fk("lar_red"))
    lcol = GOLD if fk("lar") >= fk("lar_red") and fk("lar") > 0.01 else (REDL if fk("lar_red") > 0.01 else BONEW)
    rings = []
    for i in range(8):
        y = 2740 + i * 34
        sh = (y - 2712) * 0.33
        rings.append(LA([(1600 - sh, y + 6), (1680 - sh, y - 5), (1758 - sh, y)]))
    xglow(buf, cam, [LA(cr(TRACHEA, 3))], BONEW, a=A * 0.8, r=40, inner=0.04, fres=0.75, spec=0.2, glow_k=0.1,
          glow_r=20, lines=rings, line_k=0.6, line_w=9, edge=0.2)
    xglow(buf, cam, [LA(cr(CRICOID, 3))], lcol, a=A * (0.7 + 0.3 * lk), r=14, inner=0.1, fres=1.0, spec=0.3,
          glow_k=0.1 + 0.4 * lk, glow_r=18, edge=0.3)
    xglow(buf, cam, [LA(cr(THYROID, 3))], lcol, a=A * (0.8 + 0.2 * lk), r=30, inner=0.07, fres=1.05, spec=0.35,
          glow_k=0.15 + 0.6 * lk, glow_r=26, edge=0.35)
    # gırtlak kapağı
    ec = [add(lp(a, b, st.epi), st.lar) for a, b in zip(EPI_REST, EPI_DOWN)]
    epp, _, _, _ = ribbon(ec, EPI_W, 30)
    xglow(buf, cam, [epp], EPIC, a=A * 0.7, r=12, inner=0.16, fres=0.9, spec=0.3, glow_k=0.15, glow_r=12, edge=0.2)
    # dil kemiği (render bloğu üstüne altın)
    hk = fk("hyoid")
    if hk > 0.01:
        xglow(buf, cam, [[add(p, st.hyo) for p in HYO_POLY]], GOLD, a=A * hk, r=24, inner=0.4, fres=1.0, spec=0.4,
              glow_k=0.85, glow_r=30, edge=0.5)
    # yumuşak damak
    vc = [lp(a, b, st.vel) for a, b in zip(VEL_REST, VEL_UP)]
    vp, _, _, _ = ribbon(vc, VEL_W, 30)
    pk = fk("palate")
    xglow(buf, cam, [vp], VELC, a=A * 0.9, r=26, inner=0.12 + 0.12 * pk, fres=1.0, spec=0.3, glow_k=0.15 + 0.4 * pk,
          glow_r=18, edge=0.2)
    if pk > 0.01:
        line_glow(buf, cam, [(1842, 1800), (2000, 1796), (2200, 1794), (2440, 1792)], GOLD, a=A * pk, wd=12,
                  glow_k=0.9, glow_r=22)
    # dil
    tc = cr(tp, 5)
    gt = jaw_pt((2262, 2300), st.th)
    fib = [[gt, lp(gt, tp[k], 0.45), lp(gt, tp[k], 0.9)] for k in range(2, 15)]
    tk = fk("tongue")
    xglow(buf, cam, [tc], PINK, a=A, r=120, inner=0.09 + 0.08 * tk, fres=1.0, fpow=1.4, spec=0.28, shin=18,
          glow_k=0.18 + 0.35 * tk, glow_r=34, lines=fib, line_k=0.12, line_w=4, edge=0.18)
    # dil kemiği kasları
    mk = fk("mus")
    thk = 1 + 0.22 * st.tens
    for o, i, wd in (GENIO, DIGAS):
        a0, a1 = jaw_pt(o, st.th), add(i, st.hyo)
        mid = lp(a0, a1, 0.5)
        dx, dy = a1[0] - a0[0], a1[1] - a0[1]
        ln = math.hypot(dx, dy) + 1e-6
        nrm = (-dy / ln, dx / ln)
        mid = (mid[0] + nrm[0] * 12, mid[1] + nrm[1] * 12)
        poly, C, N, w2 = ribbon([a0, lp(a0, mid, 0.5), mid, lp(mid, a1, 0.5), a1], [w * thk for w in wd], 36)
        fibs = [[tuple(C[j] + N[j] * w2[j] * f) for j in range(0, 36, 3)] for f in np.linspace(-0.34, 0.34, 6)]
        xglow(buf, cam, [poly], MUSC, a=A * (0.75 + 0.25 * mk), r=26, inner=0.12 + 0.14 * mk, fres=1.0, spec=0.3,
              glow_k=0.15 + 0.65 * mk * (0.6 + 0.4 * st.tens), glow_r=26, lines=fibs, line_k=0.3, line_w=3, edge=0.25)
    # alt çene vurgusu
    if st.mand > 0.01:
        mp = [jaw_pt(p, st.th) for p in cr(MAND, 4, closed=False)]
        line_glow(buf, cam, mp, GOLD, a=A * st.mand, wd=13, glow_k=1.0, glow_r=30)
    # kasın çeneye tutunduğu nokta
    if st.anchor > 0.01:
        gp = jaw_pt(GENIAL, st.th)
        xglow(buf, cam, [ellipse(gp[0], gp[1], 30, 30)], GOLD, a=A * st.anchor, r=14, inner=0.6, fres=0.8, glow_k=1.0,
              glow_r=34)
    # lokma (baryum gibi parlak)
    if st.bol is not None or st.bol_xy is not None:
        if st.bol_xy is not None:
            (bx, by), ang = st.bol_xy, 0.0
        else:
            (bx, by), ang = bolus_at(st.bol)
        sx, sy = st.bol_shape
        r = 46
        xglow(buf, cam, [ellipse(bx, by, r * sx, r * sy, ang)], BAR, a=A * st.bol_a, r=26, inner=0.8, fres=0.5, spec=0.6,
              glow_k=0.85, glow_r=32, edge=0.2)
    # hafif yumuşatma (render'ın odak yumuşaklığına uysun) + ekran karışımı
    buf = cv2.GaussianBlur(buf, (0, 0), 1.3)
    np.copyto(out, 255 - (255 - out) * (1 - np.clip(buf, 0, 255) / 255))
    return tp
