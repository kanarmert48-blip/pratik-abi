"""28. video (2K, ~38 sn): Bileğinde bu kas var mı? (palmaris longus testi) – dene formatı, avuç içi yukarı el çizimi.
Kullanım: python3 video28_bilek.py <WORK> [frames t1,t2,...]
WORK: voice_cut.wav, words.json, marks.json, muzik.wav, foto/ahsap.jpg, foto/orangutan.jpg"""
import os
os.environ.setdefault("PA_SCALE", str(4 / 3))
import json, math, subprocess, sys
from functools import lru_cache
from pathlib import Path

import numpy as np
import cv2

sys.path.insert(0, str(Path(__file__).resolve().parent))
from engine import *  # noqa
from pa_ui import put_word, panel, txt, pop, win, captions
import audio_tools as at
from abi_yuz import konusma
from rozet import Rozet

WORK = Path(sys.argv[1])
VOICE = WORK / "voice_cut.wav"
words = json.loads((WORK / "words.json").read_text(encoding="utf-8"))
TOTAL = round(at.duration(str(VOICE)) + 0.35, 3)


def _hits(key):
    k = trl(clean(key)).strip('"!?;,.…')
    return [w for w in words if trl(clean(w["w"])).strip('"!?;,.…') == k]


def T(key, nth=0):
    return _hits(key)[nth]["s"]


t_hemen, t_bas, t_simdi, t_buk = T("Hemen"), T("Baş"), T("Şimdi"), T("bük")
t_bilegin, t_ciktiysa, t_insan = T("Bileğinin"), T("Çıktıysa"), T("İnsanların")
t_ata, t_orang, t_ama = T("atalarımızdan") - 0.55, T("Orangutanlar"), T("ama")
t_gerek, t_cerr, t_yedek = T("O"), T("cerrahlar"), T("yedek")
t_sende, t_yorum, t_daha = T("Sende", 1), T("Yorumlara"), T("Daha")
T_RIDGE_OFF = (t_insan + 0.6, t_ata - 0.1)          # "bu kas hiç yok" gösterimi
X_ON = (t_ata - 0.05, t_sende - 0.15)                  # x-ray aralığı

GOLD = (255, 200, 80)
CORAL = (255, 112, 84)
INKC = (22, 24, 38)
GRN = (60, 205, 120)
REDC = (235, 70, 70)
CYAN = (140, 225, 255)

# ---------- dünya (el) koordinatları: 1080 birim genişlik ----------
WX0, WY0, WX1, WY1 = 120, 470, 960, 1960
SC = 2.2                                   # piksel / birim (el tuvali)
CWp, CHp = int((WX1 - WX0) * SC), int((WY1 - WY0) * SC)
WRIST = 1185


def wc(x, y):
    return (x - WX0) * SC, (y - WY0) * SC


def chaikin(pts, n=3, closed=True):
    for _ in range(n):
        out = []
        m = len(pts) if closed else len(pts) - 1
        for i in range(m):
            a, b = pts[i], pts[(i + 1) % len(pts)]
            out += [(a[0] * 0.75 + b[0] * 0.25, a[1] * 0.75 + b[1] * 0.25), (a[0] * 0.25 + b[0] * 0.75, a[1] * 0.25 + b[1] * 0.75)]
        if not closed:
            out = [pts[0]] + out + [pts[-1]]
        pts = out
    return pts


PALM = chaikin([(436, 1196), (418, 1132), (400, 1050), (392, 975), (398, 900), (418, 845), (452, 812), (500, 796), (560, 790),
                (622, 797), (668, 818), (694, 858), (706, 925), (716, 995), (722, 1062), (700, 1136), (658, 1196)])
FOREARM = chaikin([(432, 1175), (540, 1168), (662, 1175), (680, 1400), (700, 1700), (708, 1990), (372, 1990), (382, 1700),
                   (398, 1400)], 3)
FING = {  # taban, açı (dikeyden derece, + sağa), boy, taban eni
    "index": ((644, 818), 8, 300, 76),
    "middle": ((566, 800), 1, 330, 78),
    "ring": ((488, 810), -5, 306, 74),
    "pinky": ((418, 842), -13, 238, 64),
    "thumb": ((690, 1030), 46, 232, 90),
}


def gesture(t):
    if t < t_bas - 0.15:              # kanca: hazır poz
        return 1.0
    return eio(ph(t, t_bas + 0.2, 1.35))


def flex(t):
    if t < t_bas - 0.15:
        return 1.0
    return eio(ph(t, t_simdi + 0.35, 0.8))


def ridge(t):
    if t < t_bas - 0.15:
        return 1.0
    r = eo(ph(t, t_simdi + 0.75, 0.6))
    r *= 1 - eio(ph(t, T_RIDGE_OFF[0], 0.45)) * (1 - eio(ph(t, T_RIDGE_OFF[1], 0.4)))
    return r


def finger_geom(name, g):
    (bx, by), ang, ln, wd = FING[name]
    if name == "thumb":
        bx, by = bx + (680 - bx) * g, by + (1010 - by) * g
        ang = 46 + (-64 - 46) * eio(g)
        ln = ln * (1 + 0.03 * g)
    elif name == "pinky":
        ang = -13 + 163 * eio(clamp((g - 0.25) / 0.75))
        ln = ln * (1 - 0.68 * eo(clamp(g / 0.6)))
    elif name == "ring":
        ang = -5 + 3 * g
        ln = ln * (1 - 0.07 * g)
    return bx, by, ang, ln, wd


def nail(d, name, f, g, a):
    """bükülen parmakta görünen tırnak (ucun sırt tarafı)"""
    if a <= 0.01:
        return
    bx, by, ang, ln, wd = finger_geom(name, g)
    t = math.radians(ang)
    dx, dy = math.sin(t), -math.cos(t)
    px, py = -dy, dx
    nl, nw = wd * 0.52, wd * 0.26
    cx, cy = bx + dx * (ln - wd * 0.5), by + dy * (ln - wd * 0.5)
    pts = []
    for i in range(20):
        th = 2 * math.pi * i / 20
        ex, ey = math.cos(th) * nl / 2, math.sin(th) * nw
        pts.append((cx + dx * ex + px * ey, cy + dy * ex + py * ey))
    pp = [wc(x, y) for x, y in hf(pts, f)]
    d.polygon(pp, fill=(232, 184, 166, int(225 * a)), outline=(184, 122, 104, int(220 * a)))
    hx, hy = hf([(cx + dx * nl * 0.1 - px * nw * 0.35, cy + dy * nl * 0.1 - py * nw * 0.35)], f)[0]
    hx, hy = wc(hx, hy)
    r = 4 * SC
    d.ellipse([hx - r * 1.6, hy - r, hx + r * 1.6, hy + r], fill=(255, 250, 245, int(150 * a)))


def _wprof(s, wd):
    """parmak eni profili: incelen + boğum şişkinlikleri"""
    w = wd * (1 - 0.24 * s - (0.12 * (1 - s) ** 2 if wd > 85 else 0) * -1)
    for j in (0.36, 0.66):
        w *= 1 + 0.045 * math.exp(-((s - j) / 0.07) ** 2)
    return w


def finger_poly(bx, by, ang, ln, wd, n=14):
    a = math.radians(ang)
    dx, dy = math.sin(a), -math.cos(a)
    px, py = -dy, dx
    wt = _wprof(1.0, wd)
    rt = wt / 2
    body = max(ln - rt, 1)
    L_, R_ = [], []
    for i in range(13):
        s = i / 12
        w = _wprof(s, wd) / 2
        cx, cy = bx + dx * (body * s - 50 * (1 - s) ** 3 * 1.0), by + dy * (body * s - 50 * (1 - s) ** 3)
        L_.append((cx - px * w, cy - py * w))
        R_.append((cx + px * w, cy + py * w))
    tx, ty = bx + dx * body, by + dy * body
    tip = []
    for i in range(1, n):
        th = math.pi * i / n
        cx = -math.cos(th) * px + math.sin(th) * dx
        cy = -math.cos(th) * py + math.sin(th) * dy
        tip.append((tx + rt * cx, ty + rt * cy))
    return L_ + tip + R_[::-1]


def hf(pts, f):
    """bilek bükümü: bilek üstü noktalar kısalır/genişler (kameraya yaklaşma)"""
    out = []
    for x, y in pts:
        if y < WRIST:
            y = WRIST + (y - WRIST) * (1 - 0.15 * f)
            x = 540 + (x - 540) * (1 + 0.05 * f)
        out.append((x, y))
    return out


def mask_of(polys):
    m = Image.new("L", (CWp, CHp), 0)
    d = ImageDraw.Draw(m)
    for p in polys:
        d.polygon([wc(x, y) for x, y in p], fill=255)
    return np.asarray(m.filter(ImageFilter.GaussianBlur(0.9))).astype(np.float32) / 255


# ---------- yükseklik haritası + ışık: 3B ten ----------
LDIR = np.array([-0.42, -0.55, 0.72], np.float32)
LDIR /= np.linalg.norm(LDIR)
HV = LDIR + np.array([0, 0, 1.0], np.float32)
HV /= np.linalg.norm(HV)
_rng = np.random.default_rng(5)
NOISE_F = cv2.GaussianBlur(_rng.standard_normal((CHp, CWp)).astype(np.float32), (0, 0), 1.2)
NOISE_F /= NOISE_F.std()
NOISE_L = cv2.GaussianBlur(_rng.standard_normal((CHp // 8, CWp // 8)).astype(np.float32), (0, 0), 3)
NOISE_L = cv2.resize(NOISE_L / NOISE_L.std(), (CWp, CHp))
SKIN = np.array([234, 168, 128], np.float32)
PINK = np.array([240, 152, 132], np.float32)


def dome(ma, r):
    """yumuşak şişirme: maskenin çok ölçekli bulanıklığı (medial kırışık yok)"""
    sm = cv2.resize(ma, (CWp // 2, CHp // 2), interpolation=cv2.INTER_AREA)
    acc = np.zeros_like(sm)
    for k, wgt in ((0.35, 0.45), (0.7, 0.35), (1.2, 0.2)):
        acc += cv2.GaussianBlur(sm, (0, 0), r * k * SC / 2) * wgt
    acc = cv2.resize(acc, (CWp, CHp), interpolation=cv2.INTER_CUBIC)
    acc = np.clip((acc - 0.18) / 0.82, 0, 1) ** 0.75
    return r * acc * ma


def add_gauss(h, x, y, rx, ry, amp):
    cx, cy = wc(x, y)
    rxp, ryp = rx * SC, ry * SC
    x0, x1 = int(max(0, cx - 3 * rxp)), int(min(CWp, cx + 3 * rxp))
    y0, y1 = int(max(0, cy - 3 * ryp)), int(min(CHp, cy + 3 * ryp))
    if x0 >= x1 or y0 >= y1:
        return
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    h[y0:y1, x0:x1] += amp * np.exp(-(((xx - cx) / rxp) ** 2 + ((yy - cy) / ryp) ** 2))


def line_field(lines):
    """[(dünya noktaları, en birim, genlik)] -> yükseklik katkısı (birim)"""
    out = np.zeros((CHp, CWp), np.float32)
    groups = {}
    for pts, wdt, amp in lines:
        groups.setdefault((wdt, amp), []).append(pts)
    for (wdt, amp), pl in groups.items():
        m = np.zeros((CHp // 2, CWp // 2), np.float32)
        for pts in pl:
            pp = np.array([[wc(x, y)[0] / 2, wc(x, y)[1] / 2] for x, y in pts], np.int32)
            cv2.polylines(m, [pp], False, 1.0, thickness=max(1, int(wdt * SC / 2)), lineType=cv2.LINE_AA)
        m = cv2.GaussianBlur(m, (0, 0), wdt * SC / 3)
        out += cv2.resize(m, (CWp, CHp)) * amp
    return out


def lit(h, ma, albedo):
    hp = cv2.GaussianBlur(h * SC, (0, 0), 1.0)
    gx = cv2.Sobel(hp, cv2.CV_32F, 1, 0, ksize=3) / 8
    gy = cv2.Sobel(hp, cv2.CV_32F, 0, 1, ksize=3) / 8
    inv = 1 / np.sqrt(gx * gx + gy * gy + 1)
    nx, ny, nz = -gx * inv, -gy * inv, inv
    ndl = nx * LDIR[0] + ny * LDIR[1] + nz * LDIR[2]
    wrap = np.clip((ndl + 0.32) / 1.32, 0, 1)
    spec = np.clip(nx * HV[0] + ny * HV[1] + nz * HV[2], 0, 1) ** 34 * 0.13
    shade = 0.33 + 0.80 * wrap
    col = albedo * shade[..., None]
    col *= 1 + (1 - wrap)[..., None] * np.array([0.10, -0.03, -0.08])      # gölgede kırmızımsı (deri altı)
    col += spec[..., None] * np.array([255, 238, 224])
    # çok ince kenar çizgisi
    ol = np.clip((ma - cv2.GaussianBlur(ma, (0, 0), 1.2 * SC)) * 2.0, 0, 1)[..., None]
    col = col * (1 - 0.35 * ol) + ol * np.array([120, 64, 48]) * 0.35
    return col


def skin_albedo(tints):
    alb = np.ones((CHp, CWp, 3), np.float32) * SKIN
    alb *= (1 + 0.02 * NOISE_F + 0.015 * NOISE_L)[..., None]
    t = np.zeros((CHp, CWp), np.float32)
    for x, y, rx, ry, amp in tints:
        add_gauss(t, x, y, rx, ry, amp)
    t = np.clip(t, 0, 1)[..., None]
    return alb * (1 - t) + PINK * t


def finger_pts_along(name, g, f, fr):
    bx, by, ang, ln, wd = finger_geom(name, g)
    a = math.radians(ang)
    dx, dy = math.sin(a), -math.cos(a)
    return hf([(bx + dx * ln * fr, by + dy * ln * fr)], f)[0], (dx, dy), wd, ln


def finger_bumps(h, name, g, f, tints, lines):
    (x, y), (dx, dy), wd, ln = finger_pts_along(name, g, f, 0.86)
    if ln > 110:
        for fr, amp in ((0.86, 6), (0.52, 3.5), (0.2, 3.5)):
            (x, y), _, _, _ = finger_pts_along(name, g, f, fr)
            add_gauss(h, x, y, wd * 0.28, wd * 0.26, amp)
        tints.append((*finger_pts_along(name, g, f, 0.9)[0], wd * 0.35, wd * 0.35, 0.55))
        px, py = -dy, dx
        for fr in ((0.36, 0.66) if name != "thumb" else (0.48,)):
            (cx, cy), _, _, _ = finger_pts_along(name, g, f, fr)
            w = wd * 0.36
            lines.append(([(cx - px * w, cy - py * w), (cx + dx * 3, cy + dy * 3), (cx + px * w, cy + py * w)], 2.2, -3.0))
    else:
        add_gauss(h, x, y, wd * 0.3, wd * 0.3, 4)


def ridge_field(r, f):
    """kabarık tendon: analitik kesit (gauss) x boyuna zarf"""
    out = np.zeros((CHp, CWp), np.float32)
    if r <= 0.01:
        return out
    y0, y1 = int(wc(0, 1090)[1]), int(wc(0, 1540)[1])
    x0, x1 = int(wc(470, 0)[0]), int(wc(640, 0)[0])
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    uy, ux = yy / SC + WY0, xx / SC + WX0
    env = np.clip((uy - 1105) / 55, 0, 1) * np.clip((1530 - uy) / 300, 0, 1) ** 1.2
    for xc0, amp, sg in ((540, 13.0, 7.0), (594, 4.5, 6.0)):
        d = ux - (xc0 - (uy - WRIST) * 0.02)
        out[y0:y1, x0:x1] += amp * r * np.exp(-(d / sg) ** 2) * env * (0.85 + 0.15 * f)
    return out


def sleeve_layer():
    pts = chaikin([(352, 1735), (540, 1712), (728, 1735), (744, 2000), (336, 2000)], 3)
    m = Image.new("L", (CWp, CHp), 0)
    ImageDraw.Draw(m).polygon([wc(x, y) for x, y in pts], fill=255)
    ma = np.asarray(m.filter(ImageFilter.GaussianBlur(1))).astype(np.float32) / 255
    h = dome(ma, 70)
    xs = np.arange(CWp, dtype=np.float32)[None, :]
    yy = (np.arange(CHp, dtype=np.float32) / SC + WY0)[:, None]
    band = np.clip((1820 - yy) / 20, 0, 1) * np.clip((yy - 1712) / 6, 0, 1)
    h = h + (np.sin(xs / (5.0 * SC)) * 2.2) * band + band * 6
    alb = np.ones((CHp, CWp, 3), np.float32) * np.array([42, 58, 104], np.float32) * (1 + 0.05 * NOISE_F)[..., None]
    col = lit(h, ma, alb)
    return np.dstack([np.clip(col, 0, 255), ma * 255]).astype(np.uint8), ma


SLEEVE, SLEEVE_M = sleeve_layer()


def over(dst, src):
    a = src[..., 3:4] / 255
    dst[..., :3] = dst[..., :3] * (1 - a) + src[..., :3] * a
    dst[..., 3:4] = np.maximum(dst[..., 3:4], src[..., 3:4])


@lru_cache(maxsize=6)
def hand_canvas(gq, fq, rq):
    g, f, r = gq / 100, fq / 100, rq / 100
    pal = hf(PALM, f)
    fa = FOREARM
    fixed = [hf(finger_poly(*finger_geom(n, g)), f) for n in ("index", "middle", "ring")]
    pinky = hf(finger_poly(*finger_geom("pinky", g)), f)
    thumb = hf(finger_poly(*finger_geom("thumb", g)), f)
    base_m = mask_of([fa, pal] + fixed)
    pk_m = mask_of([pinky])
    th_m = mask_of([thumb])
    # masaya düşen gölge: yakın (koyu) + geniş (yumuşak)
    hand_m = np.maximum(np.maximum(mask_of([pal] + fixed), pk_m), th_m)
    arm_m = mask_of([fa])
    small = lambda m, s: cv2.resize(cv2.GaussianBlur(cv2.resize(m, (CWp // 3, CHp // 3)), (0, 0), s), (CWp, CHp))
    sh = np.maximum.reduce([
        cv2.warpAffine(small(arm_m, 1.5), np.float32([[1, 0, 4 * SC], [0, 1, 6 * SC]]), (CWp, CHp)) * 0.6,
        cv2.warpAffine(small(arm_m, 7), np.float32([[1, 0, 16 * SC], [0, 1, 24 * SC]]), (CWp, CHp)) * 0.45,
        cv2.warpAffine(small(hand_m, 2 + 6 * f), np.float32([[1, 0, (6 + 30 * f) * SC], [0, 1, (9 + 44 * f) * SC]]),
                       (CWp, CHp)) * (0.6 - 0.2 * f),
        cv2.warpAffine(small(hand_m, 8 + 6 * f), np.float32([[1, 0, (18 + 30 * f) * SC], [0, 1, (26 + 44 * f) * SC]]),
                       (CWp, CHp)) * 0.35])
    out = np.zeros((CHp, CWp, 4), np.float32)
    out[..., :3] = (28, 12, 4)
    out[..., 3] = sh * 255
    # --- taban katman (kol + avuç + 3 parmak)
    pf = lambda x, y: hf([(x, y)], f)[0]
    h = 1.25 * dome(base_m, 45) + 1.1 * dome(base_m, 130)
    tints = [(*pf(548, 990), 110, 95, 0.35), (*pf(440, 1060), 40, 70, 0.25)]
    lines = []
    add_gauss(h, *pf(652, 1078), 58, 80, 17)              # tenar (başparmak kası)
    add_gauss(h, *pf(442, 1060), 42, 90, 10)              # hipotenar
    add_gauss(h, *pf(548, 985), 80, 70, -15)              # avuç çukuru
    for n in ("index", "middle", "ring", "pinky"):
        (bx, by), *_ = FING[n]
        add_gauss(h, *pf(bx, by + 28), 32, 22, 7)          # parmak dibi yastıkları
    for n in ("index", "middle", "ring"):
        finger_bumps(h, n, g, f, tints, lines)
    cl = lambda pts: hf(chaikin(pts, 2, closed=False), f)
    lines += [(cl([(436, 1172), (500, 1180), (580, 1180), (650, 1170)]), 2.6, -4.5 * (0.7 + 0.5 * f)),
              (cl([(446, 1150), (520, 1158), (600, 1156), (652, 1146)]), 2.2, -3.0 * (0.6 + 0.6 * f)),
              (cl([(402, 905), (470, 888), (540, 882), (610, 872), (640, 852)]), 2.4, -3.4),
              (cl([(698, 900), (630, 930), (560, 950), (500, 975), (452, 1000)]), 2.4, -3.2),
              (cl([(700, 905), (668, 990), (650, 1070), (640, 1150)]), 2.6, -3.6)]
    h += line_field(lines)
    h += ridge_field(r, f)
    col = lit(h, base_m, skin_albedo(tints))
    over(out, np.dstack([col, base_m * 255]))
    # --- serçe ve başparmak (üst katmanlar)
    for m, n in ((pk_m, "pinky"), (th_m, "thumb")):
        shm = cv2.warpAffine(cv2.GaussianBlur(m, (0, 0), 5 * SC), np.float32([[1, 0, 5 * SC], [0, 1, 8 * SC]]), (CWp, CHp))
        shadow = np.zeros((CHp, CWp, 4), np.float32)
        shadow[..., :3] = (50, 18, 8)
        shadow[..., 3] = shm * 120 * (1 - m)
        over(out, shadow)
        hh = 1.35 * dome(m, 40) + 0.45 * dome(m, 70)
        t2, l2 = [], []
        finger_bumps(hh, n, g, f, t2, l2)
        if l2:
            hh += line_field(l2)
        cc = lit(hh, m, skin_albedo(t2))
        L = Image.fromarray(np.dstack([np.clip(cc, 0, 255), m * 255]).astype(np.uint8), "RGBA")
        nail(ImageDraw.Draw(L), n, f, g, eo(clamp((g - 0.45) / 0.4)) if n == "pinky" else 0.85 * eo(clamp((g - 0.3) / 0.5)))
        over(out, np.asarray(L).astype(np.float32))
    over(out, SLEEVE.astype(np.float32))
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), "RGBA")


# ---------- arka plan (ahşap masa, dünya ölçeğinde) ----------
BGX0, BGY0, BGX1, BGY1 = -500, -400, 1580, 2600
BSC = 1.1


def _wood():
    im = Image.open(WORK / "foto" / "ahsap.jpg").convert("RGB").rotate(90, expand=True)
    tw, th = int((BGX1 - BGX0) * BSC), int((BGY1 - BGY0) * BSC)
    k = max(tw / im.width, th / im.height)
    im = im.resize((round(im.width * k), round(im.height * k)), Image.LANCZOS)
    l, t = (im.width - tw) // 2, (im.height - th) // 2
    im = im.crop((l, t, l + tw, t + th)).filter(ImageFilter.GaussianBlur(3))
    a = np.asarray(im).astype(np.float32)
    a = a.mean(axis=(0, 1)) + (a - a.mean(axis=(0, 1))) * 0.7
    a = a * np.array([1.0, 0.93, 0.85]) * 0.86
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


WOOD = _wood()
_yy, _xx = np.mgrid[0:H, 0:W].astype(np.float32)
_d = np.sqrt(((_xx - W / 2) / (W * 0.62)) ** 2 + ((_yy - H * 0.47) / (H * 0.62)) ** 2)
_v = 1 - 0.5 * np.clip(_d - 0.35, 0, 1) ** 1.3
_v *= 1 - 0.5 * np.clip((H * 0.22 - _yy) / (H * 0.22), 0, 1) ** 1.3
_v *= 1 - 0.45 * np.clip((_yy - H * 0.78) / (H * 0.22), 0, 1) ** 1.4
VIGA = Image.fromarray(((1 - _v) * 255).astype(np.uint8), "L")
VIG = Image.new("RGBA", (W, H), (8, 4, 2, 255))
VIG.putalpha(VIGA)
del _yy, _xx, _d, _v

# ---------- kamera ----------
SHOTS = [  # (başlangıç, cx, cy, z)
    (-1, 540, 1150, 1.72),
    (t_bas - 0.15, 540, 1040, 0.86),
    (t_simdi + 0.15, 540, 1110, 1.12),
    (t_bilegin - 0.2, 540, 1175, 1.5),
    (t_insan - 0.1, 540, 1120, 1.08),
    (t_ata - 0.1, 540, 1280, 0.80),
    (t_sende - 0.15, 540, 1060, 0.92),
]
CUTS = {SHOTS[1][0]}                         # sert kesme (diğerleri yumuşak geçiş)


def camera(t):
    k = 0
    for i, s in enumerate(SHOTS):
        if t >= s[0]:
            k = i
    st, cx, cy, z = SHOTS[k]
    if k > 0 and SHOTS[k][0] not in CUTS:
        q = eio(ph(t, st, 0.55))
        _, px, py, pz = SHOTS[k - 1]
        cx, cy, z = px + (cx - px) * q, py + (cy - py) * q, pz + (z - pz) * q
    # yavaş kayma
    nxt = SHOTS[k + 1][0] if k + 1 < len(SHOTS) else TOTAL
    z *= 1 + 0.035 * clamp((t - st) / max(0.5, nxt - st))
    if k == 0:
        z *= 1 - 0.04 * clamp(t / 2.3)
    return cx, cy, z


def W2S(cam, x, y):
    cx, cy, z = cam
    return (x - cx) * z + 540, (y - cy) * z + 960


def render_world(cam, hand):
    cx, cy, z = cam
    x0, y0 = cx - 540 / z, cy - 960 / z
    x1, y1 = cx + 540 / z, cy + 960 / z
    bg = WOOD.transform((W, H), Image.EXTENT, ((x0 - BGX0) * BSC, (y0 - BGY0) * BSC, (x1 - BGX0) * BSC, (y1 - BGY0) * BSC),
                        resample=Image.BILINEAR).convert("RGBA")
    hl = hand.transform((W, H), Image.EXTENT, ((x0 - WX0) * SC, (y0 - WY0) * SC, (x1 - WX0) * SC, (y1 - WY0) * SC),
                        resample=Image.BICUBIC)
    return bg, hl


def xray_fx(hl, xr, cam=None):
    a = np.asarray(hl).astype(np.float32).copy()
    if cam is not None:                     # röntgende kol yeni kolun altını gizle
        ys = u(W2S(cam, 540, 1700)[1])
        yy = np.arange(H, dtype=np.float32)[:, None]
        a[..., 3] *= np.clip((ys - yy) / u(40), 0, 1) * xr + (1 - xr)
    mask = (a[..., 3] > 40).astype(np.float32) * (np.abs(a[..., 0] - 30) > 20)
    mask = cv2.GaussianBlur(mask, (0, 0), 1.2)
    ed = np.clip(mask - cv2.GaussianBlur(mask, (0, 0), u(5)), 0, 1)
    blue = np.zeros_like(a)
    blue[..., 0], blue[..., 1], blue[..., 2] = 40, 90, 160
    blue[..., 3] = mask * 120 + ed * 200
    blue[..., :3] += ed[..., None] * np.array([90, 140, 90])
    a = a * (1 - xr) + blue * xr
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "RGBA")


# ---------- çizim yardımcıları ----------
def glow_line(L, pts, col, w, a, draw_to=1.0, gw=3.0):
    if a <= 0.01 or len(pts) < 2:
        return
    n = max(2, int(len(pts) * draw_to))
    pp = [(u(x), u(y)) for x, y in pts[:n]]
    g = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(g).line(pp, fill=col + (int(150 * a),), width=round(u(w * gw)), joint="curve")
    L.alpha_composite(g.filter(ImageFilter.GaussianBlur(u(8))))
    ImageDraw.Draw(L).line(pp, fill=col + (int(255 * a),), width=round(u(w)), joint="curve")


def arrow(L, p0, p1, a, col=GOLD, bend=60, w=10):
    if a <= 0.01:
        return
    d = ImageDraw.Draw(L)
    n = 26
    pts = []
    for i in range(n + 1):
        q = i / n
        x = p0[0] + (p1[0] - p0[0]) * q
        y = p0[1] + (p1[1] - p0[1]) * q
        nx, ny = -(p1[1] - p0[1]), (p1[0] - p0[0])
        ln = math.hypot(nx, ny) + 1e-6
        x += nx / ln * math.sin(math.pi * q) * bend
        y += ny / ln * math.sin(math.pi * q) * bend
        pts.append((u(x), u(y)))
    d.line(pts, fill=(20, 12, 6, int(140 * a)), width=round(u(w + 7)), joint="curve")
    d.line(pts, fill=col + (int(255 * a),), width=round(u(w)), joint="curve")
    ang = math.atan2(pts[-1][1] - pts[-4][1], pts[-1][0] - pts[-4][0])
    s = u(36)
    x1, y1 = pts[-1]
    tri = [(x1 + math.cos(ang) * s * 0.5, y1 + math.sin(ang) * s * 0.5),
           (x1 + math.cos(ang + 2.45) * s, y1 + math.sin(ang + 2.45) * s),
           (x1 + math.cos(ang - 2.45) * s, y1 + math.sin(ang - 2.45) * s)]
    d.polygon(tri, fill=col + (int(255 * a),), outline=(20, 12, 6, int(140 * a)))


def tendon_world(f):
    pts = [(541, 1570)] + [(540 - (y - WRIST) * 0.02, y) for y in range(1540, 1150, -30)] + [(540, 1135)]
    return hf(pts, f)


def fan_world(f):
    tops = [hf([(FING[n][0][0], FING[n][0][1] + 30)], f)[0] for n in ("index", "middle", "ring", "pinky")]
    base = hf([(540, 1130)], f)[0]
    return base, tops


# ---------- sahneler ----------
def s_hook(L, t, cam):
    if t >= t_bas - 0.15:
        return
    a = 1.0
    p = 1 + 0.12 * (1 - pop(t, 0, 0.35))
    txt(L, (540, 225), "BİLEĞİNDE", round(118 * p), WHITE, a, stroke=5)
    txt(L, (540, 350), "BU VAR MI?", round(124 * p), GOLD, a, stroke=5)
    tx, ty = W2S(cam, 540, 1235)
    arrow(L, (820, 520), (tx + 30, ty - 40), eo(ph(t, 0.15, 0.35)), bend=-70, w=11)
    if t >= t_hemen - 0.08:
        chip(L, 540, 470, "HEMEN DENE", bg=CORAL, fg=WHITE, size=44, k="black", scale=pop(t, t_hemen - 0.08, 0.3))


def s_steps(L, t, cam):
    a = win(t, t_bas - 0.1, t_bilegin - 0.15, 0.2, 0.2)
    if a <= 0.01:
        return
    s1 = t < t_simdi - 0.08
    if s1:
        chip(L, 540, 260, "1 · Başparmak serçe parmağa", bg=WHITE, fg=INKC, size=46, k="black", alpha=a,
             scale=pop(t, t_bas - 0.1, 0.3))
    else:
        chip(L, 540, 260, "2 · Bileğini hafifçe bük", bg=WHITE, fg=INKC, size=46, k="black", alpha=a,
             scale=pop(t, t_simdi - 0.08, 0.3))
    # deneme molası: bileğe bak
    b = win(t, t_buk + 0.35, t_bilegin - 0.15, 0.2, 0.2)
    if b > 0.01:
        chip(L, 540, 380, "BİLEĞİNE BAK", bg=GOLD, fg=INKC, size=44, k="black", alpha=b, icon_name="eye",
             scale=pop(t, t_buk + 0.35, 0.3))
        tx, ty = W2S(cam, 540, 1240)
        bob = 10 * math.sin(t * 7)
        arrow(L, (300, 760), (tx - 30, ty - 30 + bob), b, bend=60)


def s_reveal(L, t, cam):
    a = win(t, t_bilegin - 0.1, t_insan - 0.1, 0.25, 0.2)
    if a <= 0.01:
        return
    tx, ty = W2S(cam, 540, 1240)
    if t < t_ciktiysa - 0.1:
        txt(L, (540, 300), "İP GİBİ ÇIKTI MI?", round(84 * pop(t, t_bilegin - 0.1, 0.3)), WHITE, a, stroke=5)
        arrow(L, (830, 560), (tx + 26, ty - 34), a * eo(ph(t, t_bilegin + 0.2, 0.3)), bend=-60)
        # tendon boyunca parlama
        pts = [W2S(cam, x, y) for x, y in tendon_world(1.0)[2:12]]
        glow_line(L, pts, (255, 236, 170), 4, 0.55 * a * eo(ph(t, t_bilegin + 0.5, 0.4)), gw=3.5)
    else:
        q = pop(t, t_ciktiysa - 0.1, 0.35)
        put_icon(L, "check_mark_button", 540, 220, 100 * q, alpha=a)
        txt(L, (540, 330), "SENDE VAR", round(92 * q), GRN, a, stroke=5)
        b = a * eo(ph(t, T("uzun") - 0.1, 0.3))
        txt(L, (540, 430), "Uzun avuç içi kası", 50, WHITE, b, stroke=4)
        txt(L, (540, 490), "(palmaris longus)", 38, (220, 210, 200), b, k="b", stroke=3)
        arrow(L, (300, 560), (tx - 26, ty - 30), b, bend=60)


def people(L, x0, y0, n, hi, a, sc=1.0):
    d = ImageDraw.Draw(L)
    for i in range(n):
        x = x0 + i * 82 * sc
        if i < int(hi):
            col, al = REDC, 1.0
        elif i < hi:
            col, al = REDC, 0.55
        else:
            col, al = (200, 205, 222), 0.85
        A = int(255 * a * al)
        r = 17 * sc
        d.ellipse([u(x - r), u(y0 - 52 * sc - r), u(x + r), u(y0 - 52 * sc + r)], fill=col + (A,))
        d.rounded_rectangle([u(x - 26 * sc), u(y0 - 28 * sc), u(x + 26 * sc), u(y0 + 34 * sc)], radius=u(18 * sc),
                            fill=col + (A,))


def s_stat(L, t, cam):
    a = win(t, t_insan - 0.1, t_ata - 0.1, 0.25, 0.25)
    if a <= 0.01:
        return
    q = pop(t, t_insan - 0.1, 0.4)
    panel(L, 540, 330, 960, 420, scale=q, alpha=a, r=48)
    put_word(L, "%10–20", GOLD, 540, 225, 130, scale=q, alpha=a, glow=0.35)
    txt(L, (540, 330), "insanda bu kas hiç yok", 50, WHITE, a * eo(ph(t, t_insan + 0.4, 0.3)))
    people(L, 172, 470, 10, 1.5 * eo(ph(t, t_insan + 1.0, 0.7)), a * eo(ph(t, t_insan + 0.6, 0.3)))
    # bilekte "YOK" etiketi (tendon sönükken)
    b = a * eo(ph(t, T_RIDGE_OFF[0] + 0.3, 0.3))
    tx, ty = W2S(cam, 540, 1240)
    if b > 0.01:
        put_icon(L, "cross_mark", tx + 150, ty - 10, 84 * pop(t, T_RIDGE_OFF[0] + 0.3, 0.3), alpha=b)
        txt(L, (tx + 150, ty + 70), "YOKSA", 46, REDC, b, stroke=5)


ORANG = Image.open(WORK / "foto" / "orangutan.jpg").convert("RGB")


@lru_cache(maxsize=2)
def orang_card(w, h):
    im = ORANG
    k = max(u(w) / im.width, u(h) / im.height)
    im = im.resize((round(im.width * k), round(im.height * k)), Image.LANCZOS)
    l, tp = (im.width - round(u(w))) // 2, int((im.height - round(u(h))) * 0.25)
    im = im.crop((l, tp, l + round(u(w)), tp + round(u(h)))).convert("RGBA")
    m = Image.new("L", im.size, 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, im.width - 1, im.height - 1], radius=round(u(40)), fill=255)
    im.putalpha(m)
    M = round(u(40))
    out = Image.new("RGBA", (im.width + 2 * M, im.height + 2 * M), (0, 0, 0, 0))
    sh, pad = soft_shadow(im.width, im.height, round(u(40)), blur=round(u(22)), op=0.6)
    comp(out, sh, M - pad, M - pad + u(12))
    ImageDraw.Draw(out).rounded_rectangle([M - 6, M - 6, M + im.width + 5, M + im.height + 5], radius=round(u(44)),
                                          fill=(255, 255, 255, 255))
    out.alpha_composite(im, (M, M))
    return out


def bones(L, cam, a, g=1.0, f=1.0):
    """stilize röntgen kemikleri (dünya geometrisinden)"""
    B = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(B)

    def cap(p0, p1, w):
        (x0, y0), (x1, y1) = W2S(cam, *hf([p0], f)[0]), W2S(cam, *hf([p1], f)[0])
        ww = w * cam[2]
        col = (226, 236, 250, int(170 * a))
        d.line([(u(x0), u(y0)), (u(x1), u(y1))], fill=col, width=round(u(ww)))
        for x, y in ((x0, y0), (x1, y1)):
            r = u(ww * 0.62)
            d.ellipse([u(x) - r, u(y) - r, u(x) + r, u(y) + r], fill=col)
    cap((600, 1960), (606, 1222), 40)      # radius
    cap((470, 1960), (470, 1232), 34)      # ulna
    for i, (x, y) in enumerate([(482, 1176), (520, 1172), (560, 1170), (600, 1176), (490, 1132), (530, 1126),
                                (570, 1126), (610, 1134)]):
        cap((x - 6, y), (x + 6, y), 30)    # el bileği kemikleri
    for n, cx in (("index", 604), ("middle", 562), ("ring", 520), ("pinky", 478)):
        (bx, by), *_ = FING[n]
        cap((cx, 1108), (bx, by + 8), 22)  # tarak kemikleri
        bx2, by2, ang, ln, wd = finger_geom(n, g)
        aa = math.radians(ang)
        dx, dy = math.sin(aa), -math.cos(aa)
        segs = ((0.04, 0.42), (0.47, 0.72), (0.77, 0.93)) if ln > 110 else ((0.05, 0.9),)
        for s0, s1 in segs:
            cap((bx2 + dx * ln * s0, by2 + dy * ln * s0), (bx2 + dx * ln * s1, by2 + dy * ln * s1), wd * 0.30)
    bx2, by2, ang, ln, wd = finger_geom("thumb", g)
    aa = math.radians(ang)
    dx, dy = math.sin(aa), -math.cos(aa)
    cap((622, 1126), (bx2, by2), 26)
    for s0, s1 in ((0.05, 0.5), (0.56, 0.9)):
        cap((bx2 + dx * ln * s0, by2 + dy * ln * s0), (bx2 + dx * ln * s1, by2 + dy * ln * s1), wd * 0.30)
    glow = B.filter(ImageFilter.GaussianBlur(u(6)))
    L.alpha_composite(glow)
    L.alpha_composite(B.filter(ImageFilter.GaussianBlur(u(1.2))))


def s_xray(L, t, cam, xr):
    if xr <= 0.01:
        return
    f = 1.0
    bones(L, cam, xr * 0.85 * (1 - 0.5 * eio(ph(t, t_cerr - 0.1, 0.6))))
    # kas karnı (dirseğe yakın)
    belly = [W2S(cam, 540 + 26 * math.sin(math.pi * q) * (1 if s else -1), 1560 + 400 * q) for s in (1, 0)
             for q in ([i / 16 for i in range(17)] if s else [1 - i / 16 for i in range(17)])]
    G = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(G).polygon([(u(x), u(y)) for x, y in belly], fill=(235, 80, 90, int(200 * xr)))
    L.alpha_composite(G.filter(ImageFilter.GaussianBlur(u(3))))
    glow_line(L, [W2S(cam, 540, 1570), W2S(cam, 540, 1950)], (255, 120, 130), 3, 0.6 * xr, gw=6)
    # tendon
    surg = eio(ph(t, t_cerr - 0.1, 0.8))
    tw = [W2S(cam, x, y) for x, y in tendon_world(f)]
    col = (255, 240, 200) if surg < 0.05 else GOLD
    glow_line(L, tw, col, 6, xr * (1 - 0.6 * surg), draw_to=eo(ph(t, X_ON[0] + 0.2, 0.7)))
    # avuç içi zarına yelpaze
    fb, tops = fan_world(f)
    fa = xr * eo(ph(t, X_ON[0] + 0.7, 0.5))
    for tp in tops:
        glow_line(L, [W2S(cam, *fb), W2S(cam, *tp)], (200, 235, 255), 2.5, 0.75 * fa, gw=3)
    # etiketler
    la = xr * eo(ph(t, X_ON[0] + 0.5, 0.3)) * (1 - eio(ph(t, t_orang - 0.2, 0.25)))
    bx, by = W2S(cam, 540, 1700)
    if la > 0.01:
        chip(L, 540, 300, "ATALARIMIZDAN KALMA", bg=GOLD, fg=INKC, size=44, k="black", alpha=la,
             scale=pop(t, X_ON[0] + 0.5, 0.3))
        txt(L, (bx + 190, by - 30), "kas", 46, (255, 150, 160), la, stroke=4)
        tx, ty = W2S(cam, 540, 1350)
        txt(L, (tx + 200, ty), "tendon", 46, (255, 240, 200), la, stroke=4)
    # orangutan
    oa = win(t, t_orang - 0.15, t_ama - 0.05, 0.3, 0.25)
    if oa > 0.01:
        card = orang_card(820, 560)
        q = pop(t, t_orang - 0.15, 0.4)
        c2 = card.resize((round(card.width * q), round(card.height * q)), Image.BICUBIC) if q < 0.995 else card
        comp(L, set_alpha(c2, oa), u(540) - c2.width / 2, u(420) - c2.height / 2)
        chip(L, 540, 690, "Orangutanlar hâlâ kullanıyor", bg=WHITE, fg=INKC, size=42, k="black", alpha=oa,
             scale=pop(t, t_orang + 0.2, 0.3))
    # kavrama gücü
    ga = win(t, t_ama - 0.1, t_gerek - 0.1, 0.25, 0.25)
    if ga > 0.01:
        q = pop(t, t_ama - 0.1, 0.4)
        panel(L, 540, 400, 940, 470, scale=q, alpha=ga, r=46)
        txt(L, (540, 230), "KAVRAMA GÜCÜ", 54, GOLD, ga)
        d = ImageDraw.Draw(L)
        for i, lab in enumerate(("Kası olan kişi", "Kası olmayan kişi")):
            y = 330 + i * 140
            txt(L, (110, y - 34), lab, 40, WHITE, ga, k="b", anchor="lm")
            d.rounded_rectangle([u(110), u(y), u(810), u(y + 36)], radius=u(18), fill=(255, 255, 255, int(40 * ga)))
            fl = eo(ph(t, t_ama + 0.2, 0.8))
            if fl > 0.01:
                d.rounded_rectangle([u(110), u(y), u(110 + 700 * fl), u(y + 36)], radius=u(18), fill=GRN + (int(255 * ga),))
            txt(L, (900, y + 18), f"%{round(100 * fl)}", 44, WHITE, ga * eo(ph(t, t_ama + 0.2, 0.2)))
        tq = t_ama + 1.0
        if t > tq:
            put_word(L, "=", GOLD, 540, 418, 90, scale=pop(t, tq, 0.3), alpha=ga, glow=0.3)
            chip(L, 540, 640, "FARK YOK", bg=GRN, fg=INKC, size=50, k="black", alpha=ga, scale=pop(t, tq + 0.1, 0.3))
    # yedek parça
    sa = win(t, t_gerek - 0.1, t_sende - 0.15, 0.25, 0.2)
    if sa > 0.01:
        if t < t_cerr - 0.1:
            txt(L, (540, 300), "O KADAR GEREKSİZ Kİ…", round(70 * pop(t, t_gerek - 0.1, 0.3)), WHITE, sa, stroke=5)
        else:
            chip(L, 540, 280, "AMELİYATTA YEDEK PARÇA", bg=CORAL, fg=WHITE, size=46, icon_name="wrench", k="black",
                 alpha=sa, scale=pop(t, t_cerr - 0.1, 0.35))
            # tendon kopyası yukarı-yana süzülür
            q = eio(ph(t, t_cerr + 0.3, 1.1))
            sx, sy = 170 * q, -120 * q
            cp = [(x + sx, y + sy) for x, y in tw]
            glow_line(L, cp, GOLD, 10, sa * eo(ph(t, t_cerr + 0.2, 0.3)))
            if t > t_yedek - 0.2:
                txt(L, (540, 390), "Kopan tendonların yerine takılıyor", 46, WHITE, sa * eo(ph(t, t_yedek - 0.2, 0.3)), stroke=4)


def s_cta(L, t, cam):
    if t < t_sende - 0.15:
        return
    if t < t_daha - 0.1:
        a = 1 - eio(ph(t, t_daha - 0.2, 0.12))
        txt(L, (540, 220), "SENDE VAR MI?", round(104 * pop(t, t_sende - 0.15, 0.3)), WHITE, a, stroke=5)
        chip(L, 330, 360, "Var", bg=GRN, fg=INKC, size=52, icon_name="check_mark_button", k="black", alpha=a,
             scale=pop(t, t_sende + 0.25, 0.3))
        chip(L, 750, 360, "Yok", bg=REDC, fg=WHITE, size=52, icon_name="cross_mark", k="black", alpha=a,
             scale=pop(t, t_sende + 0.55, 0.3))
        if t >= t_yorum - 0.08:
            chip(L, 540, 500, "Yorumlara yaz", bg=WHITE, fg=INKC, size=50, icon_name="speech_balloon", k="black", alpha=a,
                 scale=pop(t, t_yorum - 0.08, 0.35))
    else:
        a = eo(ph(t, t_daha - 0.1, 0.25))
        txt(L, (540, 210), "Daha fazlası için", 56, WHITE, a, stroke=4)
        pulse = 1 + 0.045 * math.sin((t - t_daha) * 8) * eo(ph(t, t_daha + 0.4, 0.3))
        chip(L, 540, 350, "TAKİP ET", bg=CORAL, fg=WHITE, size=80, icon_name="bell", k="black",
             scale=pop(t, t_daha - 0.1, 0.4) * pulse)


ROZ = Rozet()
OPN, RND = konusma(VOICE, FPS)
FLASH = [t_bas - 0.15]


class Vid(Video):
    def frame(self, t):
        cam = camera(t)
        g, f, r = gesture(t), flex(t), ridge(t)
        hand = hand_canvas(round(g * 50) * 2, round(f * 50) * 2, round(r * 25) * 4)
        bg, hl = render_world(cam, hand)
        xr = eo(ph(t, X_ON[0], 0.45)) * (1 - eio(ph(t, X_ON[1], 0.4)))
        if xr > 0.01:
            hl = xray_fx(hl, xr, cam)
            bg = Image.blend(bg, Image.new("RGBA", (W, H), (6, 10, 22, 255)), 0.72 * xr)
        im = bg
        im.alpha_composite(hl)
        im.alpha_composite(VIG)
        L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        s_xray(L, t, cam, xr)
        s_hook(L, t, cam)
        s_steps(L, t, cam)
        s_reveal(L, t, cam)
        s_stat(L, t, cam)
        s_cta(L, t, cam)
        im.alpha_composite(L)
        for fl in FLASH:
            if 0 <= t - fl < 0.12:
                im.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 255, int(110 * (1 - (t - fl) / 0.12)))))
        brand(im, 540, 62, size=34)
        C = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        captions(C, self.groups, t)
        im.alpha_composite(C)
        i = min(len(OPN) - 1, int(t * FPS))
        ROZ.draw(im, t, float(OPN[i]))
        return im.convert("RGB")


if __name__ == "__main__":
    mode = sys.argv[2] if len(sys.argv) > 2 else "render"
    v = Vid([{"start": 0, "end": TOTAL, "draw": lambda *a: None}], words, "", TOTAL, bg=None)
    print("TOTAL", TOTAL, flush=True)
    if mode == "frames":
        (WORK / "test").mkdir(exist_ok=True)
        for tt in [float(x) for x in sys.argv[3].split(",")]:
            v.frame(tt).save(WORK / "test" / f"fr_{tt:05.2f}.jpg", quality=90)
    else:
        sfx = [(0.02, "pop"), (t_hemen - 0.08, "pop"), (t_bas - 0.15, "whoosh"), (t_simdi - 0.08, "pop"),
               (t_simdi + 0.75, "tink"), (t_buk + 0.35, "pop"), (t_bilegin - 0.1, "whoosh"), (t_ciktiysa - 0.1, "ding"),
               (t_insan - 0.1, "whoosh"), (T_RIDGE_OFF[0] + 0.3, "pop"), (t_ata - 0.1, "whoosh"), (t_orang - 0.15, "pop"),
               (t_ama - 0.1, "whoosh"), (T("hiçbir") - 0.1, "pop"), (t_gerek - 0.1, "whoosh"), (t_cerr - 0.1, "pop"),
               (t_cerr + 0.3, "whoosh"), (t_sende - 0.15, "whoosh"), (t_sende + 0.25, "pop"), (t_sende + 0.55, "pop"),
               (t_yorum - 0.08, "pop"), (t_daha - 0.1, "pop")]
        at.sfx(str(WORK / "sfx.wav"), TOTAL, sfx)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-stream_loop", "2", "-i", str(WORK / "muzik.wav"), "-af",
                        f"atrim=0:{TOTAL:.3f},afade=t=in:d=0.15,afade=t=out:st={TOTAL - 0.6:.3f}:d=0.6",
                        "-ar", "44100", "-ac", "1", str(WORK / "music.wav")], check=True)
        at.final_mix(str(VOICE), str(WORK / "music.wav"), str(WORK / "sfx.wav"), str(WORK / "mix.m4a"))
        v.render(str(WORK / "mix.m4a"), str(WORK / "video.mp4"))
        print("render bitti", TOTAL, flush=True)
