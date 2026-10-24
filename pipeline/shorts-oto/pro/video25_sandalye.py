"""25. video (2K, ~29 sn): Sandalyeden öne eğilmeden kalkamazsın (dene + ağırlık merkezi). Kendi karakter animasyonumuz.
Kullanım: python3 video25_sandalye.py <WORK> [frames t1,t2,...]"""
import os
os.environ.setdefault("PA_SCALE", str(4 / 3))
import json, math, subprocess, sys
from pathlib import Path

import numpy as np
import cv2

sys.path.insert(0, str(Path(__file__).resolve().parent))
from engine import *  # noqa
import audio_tools as at
from abi_yuz import konusma
from rozet import Rozet

WORK = Path(sys.argv[1])
words = json.loads((WORK / "words.json").read_text(encoding="utf-8"))
TOTAL = at.duration(str(WORK / "voice_cut.wav"))


def _hits(key):
    k = trl(clean(key)).strip('"!?;,.…')
    return [w for w in words if trl(clean(w["w"])).strip('"!?;,.…') == k]


def T(key, nth=0):
    return _hits(key)[nth]["s"]


def E(key, nth=0):
    return _hits(key)[nth]["e"]


t_sirt, t_ayak, t_kol = T("Sırtın"), T("ayakların"), T("kollarını")
t_simdi = T("Şimdi")
t_kalk_e = E("kalk")
t_kalkama = T("Kalkamadın")
t_seb = T("Sebebi")
t_agir = T("Ağırlık")
t_ayaga = T("Ayağa", 1)
t_bunu = T("Bunu")
t_egil = T("eğilerek")
t_cta = T("Kalkabildiysen")
ATT = [t_kalk_e + 0.25 + 0.95 * i for i in range(3)]       # üç zorlanma denemesi
GOLD = (255, 190, 60)
CORAL = (255, 112, 84)
NAVY = (36, 48, 84)
SKIN = (241, 194, 158)
INKC = (28, 30, 44)
GREEN = (60, 200, 120)
REDC = (235, 70, 70)

# ---------- oda arka planı ----------
FLOOR = 1380


def _room():
    im = Image.new("RGB", (W, H), (0, 0, 0))
    a = np.zeros((H, W, 3), np.float32)
    yy = np.arange(H, dtype=np.float32)[:, None]
    wall_t, wall_b = np.array([250, 238, 220]), np.array([238, 220, 196])
    q = np.clip(yy / u(FLOOR), 0, 1)
    a[:] = (wall_t * (1 - q) + wall_b * q)[:, None, :][:, 0, :][:, None, :]
    fl = yy >= u(FLOOR)
    fq = np.clip((yy - u(FLOOR)) / (H - u(FLOOR)), 0, 1)
    floor_c = np.array([188, 134, 92]) * (1 - 0.25 * fq) + np.array([0, 0, 0]) * 0
    a = np.where(fl[..., None], floor_c[:, None, :] if floor_c.ndim == 2 else floor_c, a)
    im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(im)
    for i in range(9):                                         # parke çizgileri
        y = u(FLOOR + 40 + i * i * 9)
        d.line([(0, y), (W, y)], fill=(160, 110, 74), width=round(u(2)))
    d.rectangle([0, u(FLOOR - 26), W, u(FLOOR)], fill=(252, 248, 242))
    d.line([(0, u(FLOOR)), (W, u(FLOOR))], fill=(205, 190, 170), width=round(u(3)))
    # pencere (sağ üst)
    x0, y0, x1, y1 = u(700), u(520), u(1010), u(900)
    d.rounded_rectangle([x0 - u(16), y0 - u(16), x1 + u(16), y1 + u(16)], radius=u(14), fill=(255, 255, 255))
    sky = Image.new("RGB", (int(x1 - x0), int(y1 - y0)))
    s = np.linspace(0, 1, sky.height)[:, None]
    sk = (np.array([150, 205, 245]) * (1 - s) + np.array([205, 232, 250]) * s)[:, None, :].repeat(sky.width, 1)
    im.paste(Image.fromarray(sk.astype(np.uint8)), (int(x0), int(y0)))
    d.rectangle([(x0 + x1) / 2 - u(6), y0, (x0 + x1) / 2 + u(6), y1], fill=(255, 255, 255))
    d.rectangle([x0, (y0 + y1) / 2 - u(6), x1, (y0 + y1) / 2 + u(6)], fill=(255, 255, 255))
    # çerçeveli tablo (sol)
    d.rounded_rectangle([u(90), u(600), u(250), u(800)], radius=u(8), fill=(70, 60, 52))
    d.rectangle([u(104), u(614), u(236), u(786)], fill=(255, 214, 120))
    d.ellipse([u(130), u(650), u(210), u(730)], fill=(255, 140, 90))
    # saksı bitki (sağ zemin)
    d.polygon([(u(880), u(1380)), (u(980), u(1380)), (u(995), u(1250)), (u(865), u(1250))], fill=(226, 120, 80))
    for ang, ln in ((-0.5, 230), (-0.15, 280), (0.25, 250), (0.6, 190), (-0.85, 170)):
        cx, cy = u(930), u(1250)
        ex, ey = cx + math.sin(ang) * u(ln), cy - math.cos(ang) * u(ln)
        d.line([(cx, cy), (ex, ey)], fill=(70, 140, 80), width=round(u(8)))
        d.ellipse([ex - u(40), ey - u(24), ex + u(40), ey + u(24)], fill=(90, 170, 95))
    return im


ROOM = _room()

# ---------- sandalye ----------
SEAT_Y, SEAT_X0, SEAT_X1 = 1060, 300, 560


def chair(d, k, ox, oy):
    c = (150, 96, 60)
    cd = (120, 74, 44)
    def R(x0, y0, x1, y1, col, r=6):
        d.rounded_rectangle([(u(x0) - ox) * k, (u(y0) - oy) * k, (u(x1) - ox) * k, (u(y1) - oy) * k], radius=u(r) * k, fill=col)
    R(SEAT_X0 + 4, 640, SEAT_X0 + 34, SEAT_Y, cd, 10)             # arkalık
    R(SEAT_X0 - 6, 650, SEAT_X0 + 44, 740, c, 12)
    R(SEAT_X0 + 10, SEAT_Y, SEAT_X0 + 36, FLOOR, cd, 6)           # arka bacak
    R(SEAT_X1 - 40, SEAT_Y, SEAT_X1 - 14, FLOOR, cd, 6)           # ön bacak
    R(SEAT_X0 - 6, SEAT_Y - 14, SEAT_X1 + 6, SEAT_Y + 24, c, 10)  # oturak


# ---------- karakter iskeleti ----------
THIGH, SHIN = 255, 285
ANKLE = (640, FLOOR - 42)
TORSO = 325


def ik(hip, ankle):
    """iki kemik ters kinematik: diz önde"""
    hx, hy = hip
    ax, ay = ankle
    dx, dy = ax - hx, ay - hy
    dd = min(math.hypot(dx, dy), THIGH + SHIN - 0.5)
    a = math.acos(clamp((THIGH ** 2 + dd ** 2 - SHIN ** 2) / (2 * THIGH * dd), -1, 1))
    base = math.atan2(dy, dx)
    ang = base - a                                              # dizi öne-yukarı büker
    return hx + THIGH * math.cos(ang), hy + THIGH * math.sin(ang)


def pose(t):
    """kalça (x,y), gövde açısı (derece, + öne), kollar (0 çapraz..1 yukarı), yüz ifadesi, titreme"""
    hip = [415.0, SEAT_Y - 42]
    th = 0.0
    arms = 0.0
    expr = "normal"
    shake = 0.0
    sweat = 0.0
    # kollarını çaprazla
    cross = eo(ph(t, t_kol, 0.6))
    # denemeler
    for i, st in enumerate(ATT):
        q = ph(t, st, 0.62)
        if 0 < q < 1:
            hip[1] -= 30 * math.sin(math.pi * q) ** 0.8
            shake = u(3) * math.sin(t * 60) * math.sin(math.pi * q)
            th -= 3 * math.sin(math.pi * q)
    if ATT[0] - 0.1 < t < t_seb:
        expr = "strain"
        sweat = eo(ph(t, ATT[0] + 0.3, 0.4))
    if t_kalkama - 0.1 <= t < t_bunu:
        expr = "sad"
        th = -4 * eo(ph(t, t_kalkama - 0.1, 0.4))
        sweat = 1 - eo(ph(t, t_seb, 0.6))
    # çözüm: öne eğil -> kalk
    if t >= t_bunu:
        q1 = eio(ph(t, t_bunu + 0.1, 1.2))
        th = -4 + 59 * q1
        hip[0] += 70 * q1
        expr = "focus"
        q2 = eio(ph(t, t_egil + 0.4, 1.1))
        if q2 > 0:
            hip[0] = 485 + (625 - 485) * q2
            hip[1] = (SEAT_Y - 42) + ((ANKLE[1] - (THIGH + SHIN) * 0.985) - (SEAT_Y - 42)) * q2
            th = 55 - 51 * q2
            expr = "happy" if q2 > 0.6 else "focus"
            arms = eo(ph(t, t_egil + 1.3, 0.6))
    return tuple(hip), th, cross, arms, expr, shake, sweat


def skeleton(t):
    hip, th, cross, arms, expr, shake, sweat = pose(t)
    a = math.radians(th)
    up = (math.sin(a), -math.cos(a))
    fw = (math.cos(a), math.sin(a))
    knee = ik(hip, ANKLE)
    sh = (hip[0] + up[0] * TORSO, hip[1] + up[1] * TORSO)
    head = (sh[0] + up[0] * 125 + fw[0] * 30, sh[1] + up[1] * 125 + fw[1] * 30)
    # kollar: yanda serbest (0) -> çapraz (1) -> yukarı (arms)
    def arm(side):
        free_e = (sh[0] - up[0] * 150 + fw[0] * 10, sh[1] - up[1] * 150 + fw[1] * 10)
        free_h = (free_e[0] - up[0] * 130 + fw[0] * 25, free_e[1] - up[1] * 130 + fw[1] * 25)
        cr_e = (sh[0] - up[0] * 150 + fw[0] * (58 + 6 * side), sh[1] - up[1] * 150 + fw[1] * (58 + 6 * side))
        cr_h = (cr_e[0] + up[0] * (34 + 8 * side) + fw[0] * (-46 + 10 * side), cr_e[1] + up[1] * (34 + 8 * side) + fw[1] * (-46 + 10 * side))
        up_e = (sh[0] + up[0] * 25 + fw[0] * (100 + 10 * side), sh[1] + up[1] * 25 + fw[1] * (100 + 10 * side))
        up_h = (up_e[0] + up[0] * 100 + fw[0] * (60 + 12 * side), up_e[1] + up[1] * 100 + fw[1] * (60 + 12 * side))
        e = [free_e[i] * (1 - cross) + cr_e[i] * cross for i in range(2)]
        hnd = [free_h[i] * (1 - cross) + cr_h[i] * cross for i in range(2)]
        e = [e[i] * (1 - arms) + up_e[i] * arms for i in range(2)]
        hnd = [hnd[i] * (1 - arms) + up_h[i] * arms for i in range(2)]
        return tuple(e), tuple(hnd)
    return dict(hip=hip, knee=knee, ankle=ANKLE, sh=sh, head=head, th=th, up=up, fw=fw, armN=arm(1), armF=arm(-1),
                expr=expr, shake=shake, sweat=sweat)


def com(sk):
    pts = [(sk["head"], 0.08), (((sk["hip"][0] + sk["sh"][0]) / 2, (sk["hip"][1] + sk["sh"][1]) / 2), 0.46),
           (((sk["hip"][0] + sk["knee"][0]) / 2, (sk["hip"][1] + sk["knee"][1]) / 2), 0.22),
           (((sk["knee"][0] + sk["ankle"][0]) / 2, (sk["knee"][1] + sk["ankle"][1]) / 2), 0.14),
           (sk["armN"][0], 0.10)]
    wsum = sum(w for _, w in pts)
    return sum(p[0] * w for p, w in pts) / wsum, sum(p[1] * w for p, w in pts) / wsum


# ---------- karakter çizimi (gölgeli illüstrasyon) ----------
CX0, CY0, CX1, CY1 = 150, 180, 980, 1460
HOOD = (44, 116, 136)
JEANS = (58, 82, 128)
HAIR = (58, 40, 30)
SKIN2 = (234, 184, 148)
WOODC = (156, 102, 64)


def _shade_local(ma, col, far=0.0, gloss=0.0):
    inner = cv2.GaussianBlur(ma, (0, 0), u(7))
    edge = np.clip(ma - inner, 0, 1) * 1.7
    hb = cv2.GaussianBlur(ma, (0, 0), u(13))
    gx = cv2.Sobel(hb, cv2.CV_32F, 1, 0, ksize=5)
    gy = cv2.Sobel(hb, cv2.CV_32F, 0, 1, ksize=5)
    nrm = np.sqrt(gx ** 2 + gy ** 2) + 1e-4
    light = (gx * 0.55 + gy * 0.85) / nrm * np.clip(nrm * 40, 0, 1)
    img = np.ones(ma.shape + (3,), np.float32) * np.array(col, np.float32)
    img *= (1 + 0.16 * light)[..., None]
    img *= (1 - 0.30 * edge)[..., None]
    if gloss:
        img += np.clip(light, 0, 1)[..., None] ** 3 * 60 * gloss
    img *= (1 - far)
    return np.dstack([np.clip(img, 0, 255), ma * 255]).astype(np.uint8)


def render_part(polys, col, far=0.0, details=None, gloss=0.0):
    """polys: birim koordinatlı çokgenler. Döner: (RGBA, (x0,y0) px) — yerel, 2x çizilip küçültülmüş."""
    xs = [u(p[0]) for pl in polys for p in pl]
    ys = [u(p[1]) for pl in polys for p in pl]
    m = u(30)
    x0, y0 = int(min(xs) - m), int(min(ys) - m)
    w, h = int(max(xs) + m) - x0, int(max(ys) + m) - y0
    k = 2
    mk = Image.new("L", (w * k, h * k), 0)
    dm = ImageDraw.Draw(mk)
    for pl in polys:
        dm.polygon([((u(x) - x0) * k, (u(y) - y0) * k) for x, y in pl], fill=255)
    ma = np.asarray(mk.resize((w, h), Image.LANCZOS)).astype(np.float32) / 255
    im = Image.fromarray(_shade_local(ma, col, far, gloss), "RGBA")
    if details:
        dl = Image.new("RGBA", (w * k, h * k), (0, 0, 0, 0))
        P2 = lambda x, y: ((u(x) - x0) * k, (u(y) - y0) * k)
        details(ImageDraw.Draw(dl), P2, k)
        im.alpha_composite(dl.resize((w, h), Image.LANCZOS))
    return im, (x0, y0)


def limb(p0, p1, w0, w1, bulge=0.0, bulge_side=-1, n=10):
    """tabandan uca incelen, uçları yuvarlak uzuv; bulge: baldır/pazı şişkinliği (birim)."""
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    L = math.hypot(dx, dy) + 1e-6
    ux, uy = dx / L, dy / L
    nx, ny = -uy, ux
    left, right = [], []
    for i in range(n + 1):
        s = i / n
        wdt = (w0 + (w1 - w0) * s) / 2
        b = bulge * math.sin(math.pi * min(1, s * 1.4)) ** 2
        cx, cy = p0[0] + dx * s, p0[1] + dy * s
        wl = wdt + (b if bulge_side < 0 else 0)
        wr = wdt + (b if bulge_side > 0 else 0)
        left.append((cx + nx * wl, cy + ny * wl))
        right.append((cx - nx * wr, cy - ny * wr))
    cap1 = [(p1[0] + (nx * math.cos(a) + ux * math.sin(a)) * w1 / 2, p1[1] + (ny * math.cos(a) + uy * math.sin(a)) * w1 / 2)
            for a in np.linspace(0, math.pi, 8)]
    cap0 = [(p0[0] - (nx * math.cos(a) + ux * math.sin(a)) * w0 / 2, p0[1] - (ny * math.cos(a) + uy * math.sin(a)) * w0 / 2)
            for a in np.linspace(0, math.pi, 8)]
    return left + cap1 + right[::-1] + cap0


def frame_pts(origin, ang_deg, pts, sc=1.0):
    """yerel (x ileri, y yukarı) -> ekran; ang + öne eğim"""
    a = math.radians(ang_deg)
    up = (math.sin(a), -math.cos(a))
    fw = (math.cos(a), math.sin(a))
    return [(origin[0] + (fw[0] * x + up[0] * y) * sc, origin[1] + (fw[1] * x + up[1] * y) * sc) for x, y in pts]


TORSO_PTS = [(-62, -18), (-72, 50), (-76, 140), (-72, 220), (-62, 280), (-44, 318), (-12, 336), (22, 334), (48, 318),
             (66, 292), (76, 248), (74, 180), (72, 110), (70, 40), (64, -8), (40, -26), (-30, -28)]
HEAD_PTS = [(-38, 4), (-58, 36), (-64, 80), (-52, 118), (-22, 142), (18, 146), (48, 128), (62, 100), (64, 84), (62, 76),
            (68, 68), (86, 50), (84, 44), (70, 40), (72, 31), (68, 26), (71, 19), (66, 6), (56, -6), (36, -12), (12, -4),
            (-10, 6)]
HAIR_PTS = [(-56, 30), (-68, 86), (-56, 124), (-24, 152), (20, 156), (54, 132), (64, 108), (54, 112), (40, 120), (12, 116),
            (-12, 104), (-20, 84), (-24, 58), (-36, 36)]
SHOE = [(-42, 30), (-48, 0), (-46, -40), (118, -40), (130, -28), (126, -8), (104, 6), (64, 14), (30, 30), (0, 36)]


def draw_character(t):
    sk = skeleton(t)
    out = Image.new("RGBA", (round(u(CX1 - CX0)), round(u(CY1 - CY0))), (0, 0, 0, 0))
    ox, oy = u(CX0) - sk["shake"], u(CY0)

    def paste(res):
        im, (x0, y0) = res
        out.alpha_composite(im, (int(x0 - ox), int(y0 - oy)))

    # sandalye
    def wood_det(d, P2, k):
        for yy in range(660, 1040, 46):
            d.line([P2(SEAT_X0 + 10, yy), P2(SEAT_X0 + 28, yy + 14)], fill=(120, 76, 46, 90), width=int(u(2) * k))
    paste(render_part([[(SEAT_X0 + 4, 630), (SEAT_X0 + 36, 630), (SEAT_X0 + 40, SEAT_Y), (SEAT_X0 + 8, SEAT_Y)]], WOODC, 0.12,
                      wood_det, gloss=0.5))
    paste(render_part([[(SEAT_X0 + 12, SEAT_Y), (SEAT_X0 + 38, SEAT_Y), (SEAT_X0 + 34, FLOOR), (SEAT_X0 + 14, FLOOR)],
                       [(SEAT_X1 - 42, SEAT_Y), (SEAT_X1 - 16, SEAT_Y), (SEAT_X1 - 18, FLOOR), (SEAT_X1 - 38, FLOOR)]],
                      WOODC, 0.2, gloss=0.3))
    paste(render_part([[(SEAT_X0 - 10, 650), (SEAT_X0 + 48, 650), (SEAT_X0 + 50, 742), (SEAT_X0 - 8, 742)]], WOODC, 0.05, gloss=0.6))
    paste(render_part([[(SEAT_X0 - 8, SEAT_Y - 16), (SEAT_X1 + 8, SEAT_Y - 16), (SEAT_X1 + 4, SEAT_Y + 22), (SEAT_X0 - 4, SEAT_Y + 22)]],
                      WOODC, 0.0, gloss=0.6))
    hip, knee, ank, sh = sk["hip"], sk["knee"], sk["ankle"], sk["sh"]
    th, up, fw = sk["th"], sk["up"], sk["fw"]
    expr = sk["expr"]

    def leg(far):
        f = 0.22 if far else 0.0
        o = (-16, -4) if far else (0, 0)
        h2, k2, a2 = (hip[0] + o[0], hip[1] + o[1]), (knee[0] + o[0], knee[1] + o[1]), (ank[0] + o[0], ank[1])
        def jean_det(d, P2, k):
            mx, my = (h2[0] + k2[0]) / 2, (h2[1] + k2[1]) / 2
            d.line([P2(mx - 10, my - 26), P2(mx + 30, my - 14)], fill=(40, 58, 96, 140), width=int(u(3) * k))
            d.line([P2(k2[0] - 18, k2[1] - 8), P2(k2[0] + 10, k2[1] + 22)], fill=(40, 58, 96, 120), width=int(u(3) * k))
        paste(render_part([limb(h2, k2, 100, 78, 8, -1)], JEANS, f, jean_det))
        paste(render_part([limb(k2, (a2[0], a2[1] - 4), 78, 50, 14, 1)], JEANS, f))
        # ayakkabı
        def shoe_det(d, P2, k):
            sole = [P2(a2[0] - 46, FLOOR - 12), P2(a2[0] + 124, FLOOR - 12), P2(a2[0] + 120, FLOOR - 2), P2(a2[0] - 44, FLOOR - 2)]
            d.polygon(sole, fill=(200, 196, 190, 255))
            for i in range(3):
                x = a2[0] + 20 + i * 18
                d.line([P2(x, FLOOR - 66 + i * 6), P2(x + 14, FLOOR - 62 + i * 6)], fill=(150, 150, 160, 220), width=int(u(3) * k))
            d.line([P2(a2[0] + 70, FLOOR - 36), P2(a2[0] + 112, FLOOR - 30)], fill=(220, 90, 70, 255), width=int(u(5) * k))
        pts = [(a2[0] + x, FLOOR - 2 - (y + 40)) for x, y in SHOE]
        paste(render_part([pts], (246, 246, 248), f * 0.6, shoe_det, gloss=0.4))

    def arm(far):
        f = 0.22 if far else 0.0
        e, hnd = sk["armF"] if far else sk["armN"]
        s0 = (sh[0] + fw[0] * 4 - up[0] * 14, sh[1] + fw[1] * 4 - up[1] * 14)
        if far:
            s0 = (s0[0] - 10, s0[1] - 4)
        paste(render_part([limb(s0, e, 66, 54, 6, -1)], HOOD, f))
        dx, dy = hnd[0] - e[0], hnd[1] - e[1]
        L = math.hypot(dx, dy) + 1e-6
        wr = (e[0] + dx * 0.86, e[1] + dy * 0.86)
        def cuff(d, P2, k):
            c = (wr[0] - dx / L * 14, wr[1] - dy / L * 14)
            d.line([P2(c[0] - dy / L * 24, c[1] + dx / L * 24), P2(c[0] + dy / L * 24, c[1] - dx / L * 24)], fill=(30, 90, 108, 200),
                   width=int(u(6) * k))
        paste(render_part([limb(e, wr, 54, 44, 4, 1)], HOOD, f, cuff))
        ang = math.atan2(dy, dx)
        hand = [(wr[0] + math.cos(ang) * 30 * math.cos(a) * 1.3 - math.sin(ang) * 22 * math.sin(a),
                 wr[1] + math.sin(ang) * 30 * math.cos(a) * 1.3 + math.cos(ang) * 22 * math.sin(a)) for a in np.linspace(-math.pi / 2, 1.5 * math.pi, 18)]
        hand = [(x + math.cos(ang) * 30, y + math.sin(ang) * 30) for x, y in hand]
        paste(render_part([hand], SKIN2, f))

    # uzak kol, uzak bacak
    arm(True)
    leg(True)
    # kapüşon (boyun arkası)
    hood = frame_pts(hip, th, [(-52, 300), (-74, 352), (-60, 396), (-24, 404), (6, 360), (-10, 318)])
    paste(render_part([hood], HOOD, 0.12))
    # gövde
    tor = frame_pts(hip, th, TORSO_PTS)
    def tor_det(d, P2, k):
        pk = frame_pts(hip, th, [(70, 70), (30, 66), (14, 112), (66, 120)])
        d.line([P2(*p) for p in pk], fill=(30, 92, 110, 170), width=int(u(3) * k), joint="curve")
        wb = frame_pts(hip, th, [(-66, 4), (68, 10)])
        d.line([P2(*p) for p in wb], fill=(30, 92, 110, 150), width=int(u(4) * k))
        for dxs in (0, 12):
            st = frame_pts(hip, th, [(44 + dxs, 322), (52 + dxs, 262)])
            d.line([P2(*p) for p in st], fill=(240, 240, 236, 230), width=int(u(3) * k))
        for yy in (150, 200):
            fl = frame_pts(hip, th, [(20, yy), (54, yy + 8)])
            d.line([P2(*p) for p in fl], fill=(30, 92, 110, 90), width=int(u(3) * k))
    paste(render_part([tor], HOOD, 0.0, tor_det))
    # yakın bacak
    leg(False)
    # boyun + baş
    nt = (sh[0] + up[0] * 52 + fw[0] * 16, sh[1] + up[1] * 52 + fw[1] * 16)
    nb = (sh[0] + fw[0] * 8, sh[1] + fw[1] * 8)
    paste(render_part([limb(nb, nt, 56, 50)], SKIN2, 0.08))
    hth = th * 0.35
    head = frame_pts(nt, hth, HEAD_PTS)

    def face(d, P2, k):
        F = lambda pts: [P2(*p) for p in frame_pts(nt, hth, pts)]
        lw = lambda w: int(u(w) * k)
        # sakal gölgesi
        d.polygon(F([(-6, 8), (14, -6), (40, -10), (60, -2), (66, 10), (60, 22), (44, 18), (24, 22), (2, 30)]), fill=(90, 62, 48, 70))
        # kulak
        ex = F([(-20, 48), (-4, 48), (-2, 84), (-20, 84)])
        d.ellipse([min(p[0] for p in ex), min(p[1] for p in ex), max(p[0] for p in ex), max(p[1] for p in ex)], fill=(222, 170, 136, 255))
        # yanak kızarması
        if expr == "strain":
            c = F([(36, 46)])[0]
            r = u(16) * k
            d.ellipse([c[0] - r, c[1] - r * 0.7, c[0] + r, c[1] + r * 0.7], fill=(235, 110, 100, 110))
        # göz
        ec = (46, 74)
        if expr == "strain":
            d.line(F([(36, 78), (54, 74), (36, 70)]), fill=(40, 28, 24, 255), width=lw(3), joint="curve")
        elif expr == "happy":
            d.line(F([(36, 72), (45, 78), (55, 73)]), fill=(40, 28, 24, 255), width=lw(3.5), joint="curve")
        else:
            lid = 0.55 if expr == "sad" else (0.8 if expr == "focus" else 1.0)
            eye = F([(36, 74), (42, 74 + 6 * lid), (52, 74 + 5 * lid), (56, 74), (50, 70), (40, 70)])
            d.polygon(eye, fill=(250, 248, 244, 255))
            ic = F([(47, 73)])[0]
            r = u(4.6) * k
            d.ellipse([ic[0] - r, ic[1] - r, ic[0] + r, ic[1] + r], fill=(70, 46, 30, 255))
            d.ellipse([ic[0] - r * 0.3, ic[1] - r * 0.8, ic[0] + r * 0.35, ic[1] - r * 0.1], fill=(255, 255, 255, 230))
            d.line(F([(35, 75), (42, 75 + 6.5 * lid), (52, 75 + 5.5 * lid), (57, 74)]), fill=(60, 40, 30, 255), width=lw(2.6))
        # kaş
        brows = {"strain": [(32, 82), (58, 86)], "focus": [(32, 88), (58, 86)], "sad": [(32, 84), (58, 92)],
                 "happy": [(32, 92), (58, 96)], "normal": [(32, 88), (58, 92)]}
        d.line(F(brows[expr]), fill=HAIR + (255,), width=lw(5))
        # ağız
        if expr == "happy":
            d.polygon(F([(52, 30), (70, 30), (66, 18), (56, 16)]), fill=(120, 40, 40, 255))
            d.line(F([(54, 28), (69, 28)]), fill=(255, 255, 255, 255), width=lw(3))
        elif expr == "strain":
            d.polygon(F([(50, 29), (70, 29), (70, 22), (50, 22)]), fill=(255, 255, 255, 255))
            d.line(F([(50, 25.5), (70, 25.5)]), fill=(150, 120, 110, 255), width=lw(1.5))
        elif expr == "sad":
            d.line(F([(54, 22), (62, 26), (70, 22)]), fill=(120, 60, 52, 255), width=lw(3), joint="curve")
        else:
            d.line(F([(54, 26), (62, 24), (70, 26)]), fill=(150, 80, 70, 255), width=lw(3), joint="curve")
        # burun deliği
        d.line(F([(72, 44), (78, 44)]), fill=(180, 120, 100, 200), width=lw(2))
    paste(render_part([head], SKIN2, 0.0, face))
    hair = frame_pts(nt, hth, HAIR_PTS)
    def hair_det(d, P2, k):
        for i in range(6):
            a = frame_pts(nt, hth, [(-40 + i * 14, 136 - abs(i - 2) * 4), (-50 + i * 16, 108)])
            d.line([P2(*p) for p in a], fill=(84, 60, 44, 120), width=int(u(3) * k))
    paste(render_part([hair], HAIR, 0.0, hair_det, gloss=0.6))
    # yakın kol
    arm(False)
    # ter
    if sk["sweat"] > 0.02:
        d = ImageDraw.Draw(out)
        hc = frame_pts(nt, hth, [(0, 120)])[0]
        for j, (ddx, ddy) in enumerate(((-30, -20), (40, -30), (-70, 30))):
            p_ = (t * 1.6 + j * 0.33) % 1
            sx, sy = u(hc[0] + ddx) - ox, u(hc[1] + ddy + p_ * 60) - oy
            a = int(220 * sk["sweat"] * (1 - p_))
            d.ellipse([sx - u(8), sy - u(12), sx + u(8), sy + u(12)], fill=(120, 190, 255, a))
    return out, sk


def floor_shadow(im, sk):
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(sh)
    cx = (SEAT_X0 + ANKLE[0] + 100) / 2
    d.ellipse([u(SEAT_X0 - 60), u(FLOOR - 22), u(ANKLE[0] + 170), u(FLOOR + 26)], fill=(60, 30, 10, 90))
    im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(u(10))))


# ---------- açıklama grafikleri ----------
_GL = {}


def glow(L, x, y, r, col, a):
    key = (int(r), col)
    if key not in _GL:
        n = 2 * int(r) + 1
        yy, xx = np.mgrid[0:n, 0:n]
        dd = np.sqrt((xx - r) ** 2 + (yy - r) ** 2) / r
        arr = np.zeros((n, n, 4), np.uint8)
        arr[..., :3] = col
        arr[..., 3] = (np.clip(1 - dd, 0, 1) ** 2 * 255).astype(np.uint8)
        _GL[key] = Image.fromarray(arr, "RGBA")
    if a > 0.01:
        comp(L, set_alpha(_GL[key], a), u(x) - int(r), u(y) - int(r))


def physics(L, t, sk):
    a = eo(ph(t, t_agir - 0.2, 0.5)) * (1 - eio(ph(t, t_cta - 0.3, 0.4)))
    if a <= 0.01:
        return
    cx, cy = com(sk)
    heel, toe = ANKLE[0] - 30, ANKLE[0] + 112
    inside = heel <= cx <= toe
    col = GREEN if inside else REDC
    d = ImageDraw.Draw(L)
    # destek alanı (ayaklar)
    qa = eo(ph(t, t_agir + 1.0, 0.5)) * a
    if qa > 0.01:
        d.rounded_rectangle([u(heel), u(FLOOR + 10), u(toe), u(FLOOR + 30)], radius=u(10), fill=GREEN + (int(230 * qa),))
        text_c(L, ((heel + toe) / 2, FLOOR + 75), "AYAKLARIN", "black", 38, GREEN, alpha=qa, stroke=6, stroke_fill=(255, 255, 255))
    # çekül çizgisi
    for yy in range(int(cy) + 30, FLOOR + 10, 34):
        d.line([(u(cx), u(yy)), (u(cx), u(min(yy + 18, FLOOR + 10)))], fill=col + (int(220 * a),), width=round(u(5)))
    glow(L, cx, cy, u(70), col, 0.6 * a)
    r = u(16)
    d.ellipse([u(cx) - r, u(cy) - r, u(cx) + r, u(cy) + r], fill=col + (int(255 * a),), outline=(255, 255, 255, int(255 * a)),
              width=round(u(4)))
    lab_a = a * (1 - eio(ph(t, t_bunu - 0.5, 0.3)))
    text_c(L, (cx - 40, cy - 70), "AĞIRLIK MERKEZİ", "black", 40, col, alpha=lab_a, stroke=6, stroke_fill=(255, 255, 255))
    # hedef oku (ayaklarının üstüne gelmeli)
    qb = eo(ph(t, t_ayaga + 0.3, 0.5)) * (1 - eio(ph(t, t_bunu + 0.6, 0.4))) * a
    if qb > 0.01:
        arrow_to(L, (cx + 30, cy), ((heel + toe) / 2, cy - 10), qb)
    if t >= t_bunu and inside:
        put_icon(L, "check_mark_button", (heel + toe) / 2 + 110, FLOOR - 120, 110 * eb(ph(t, t_egil + 0.2, 0.4)), alpha=a)
    elif t_agir + 1.2 < t < t_bunu + 0.4:
        put_icon(L, "cross_mark", (heel + toe) / 2 + 110, FLOOR - 120, 100 * eb(ph(t, t_agir + 1.2, 0.4)), alpha=a)


def arrow_to(L, p0, p1, a):
    d = ImageDraw.Draw(L)
    x0, y0, x1, y1 = u(p0[0]), u(p0[1]), u(p1[0]), u(p1[1])
    n = 24
    pts = [(x0 + (x1 - x0) * i / n, y0 + (y1 - y0) * i / n - math.sin(math.pi * i / n) * u(60)) for i in range(n + 1)]
    d.line(pts, fill=GOLD + (int(255 * a),), width=round(u(10)), joint="curve")
    ang = math.atan2(pts[-1][1] - pts[-3][1], pts[-1][0] - pts[-3][0])
    s = u(34)
    d.polygon([(x1 + math.cos(ang) * s * 0.6, y1 + math.sin(ang) * s * 0.6),
               (x1 + math.cos(ang + 2.4) * s, y1 + math.sin(ang + 2.4) * s),
               (x1 + math.cos(ang - 2.4) * s, y1 + math.sin(ang - 2.4) * s)], fill=GOLD + (int(255 * a),))


# ---------- yazılar ----------
def title(L, t):
    end = t_simdi - 0.15
    if t >= end + 0.4:
        return
    a = 1 - eio(ph(t, end, 0.4))
    pop = 1 + 0.1 * (1 - eb(ph(t, 0, 0.35)))
    text_c(L, (540, 175), "ŞİMDİ DENE", "black", 44, CORAL, alpha=a, stroke=6, stroke_fill=(255, 255, 255))
    text_c(L, (540, 280), "SANDALYEDEN", "black", round(112 * pop), INKC, alpha=a, stroke=10, stroke_fill=(255, 255, 255))
    text_c(L, (540, 400), "KALKAMAZSIN!", "black", round(118 * pop), CORAL, alpha=a, stroke=10, stroke_fill=(255, 255, 255))


def steps(L, t):
    """talimat kartları: sırt dik / ayaklar yerde / kollar çapraz"""
    items = [(t_sirt, "Sırtın dik"), (t_ayak, "Ayakların yerde"), (t_kol, "Kollar çapraz")]
    for i, (st, lab) in enumerate(items):
        a = eo(ph(t, st - 0.05, 0.3)) * (1 - eio(ph(t, t_simdi - 0.2, 0.3)))
        if a <= 0.01:
            continue
        y = 520 + i * 90
        chip(L, 760, y, lab, bg=WHITE, fg=INKC, size=40, icon_name="check_mark_button", k="black",
             scale=eb(ph(t, st - 0.05, 0.35)) * (1 - eio(ph(t, t_simdi - 0.2, 0.3))))


def try_text(L, t):
    a = eo(ph(t, t_simdi - 0.1, 0.3)) * (1 - eio(ph(t, t_kalkama - 0.2, 0.3)))
    if a > 0.01:
        text_c(L, (540, 260), "ÖNE EĞİLMEK YOK", "black", 78, REDC, alpha=a, stroke=9, stroke_fill=(255, 255, 255))
        text_c(L, (540, 360), "KALK BAKALIM", "black", 96, INKC, alpha=a, stroke=10, stroke_fill=(255, 255, 255))
    b = eo(ph(t, t_kalkama - 0.1, 0.3)) * (1 - eio(ph(t, t_seb - 0.1, 0.3)))
    if b > 0.01:
        text_c(L, (540, 300), "KALKAMADIN 😅".replace(" 😅", ""), "black", 110, REDC, alpha=b, stroke=10, stroke_fill=(255, 255, 255))
    for i, st in enumerate(ATT):
        q = ph(t, st + 0.35, 0.45)
        if 0 < q < 1:
            text_c(L, (300 + 140 * i, 700 - 60 * q), "BOİNG", "black", 46, GOLD, alpha=(1 - q), stroke=6, stroke_fill=(255, 255, 255))


def explain_title(L, t):
    a = eo(ph(t, t_seb - 0.05, 0.35)) * (1 - eio(ph(t, t_cta - 0.3, 0.3)))
    if a <= 0.01:
        return
    text_c(L, (540, 190), "SEBEBİ", "black", 44, CORAL, alpha=a, stroke=6, stroke_fill=(255, 255, 255))
    lab = "Ağırlık merkezin geride" if t < t_bunu + 1.0 else "Öne eğil, merkez ileri"
    text_c(L, (540, 285), lab, "black", 78, INKC, alpha=a, stroke=9, stroke_fill=(255, 255, 255))


def cta(L, t):
    if t < t_cta - 0.1:
        return
    chip(L, 540, 160, "Kalkabildin mi?", bg=INKC, fg=WHITE, size=58, icon_name="speech_balloon", k="black",
         scale=eb(ph(t, t_cta - 0.1, 0.4)))


def captions(L, groups, t):
    for st, en, g in groups:
        if st <= t < en:
            break
    else:
        return
    a = eo(ph(t, st, 0.12))
    f = font("black", round(u(56)))
    texts = [clean(w["w"]) for w in g]
    sp = f.getlength(" ")
    tw = sum(f.getlength(x) for x in texts) + sp * (len(texts) - 1)
    x = W / 2 - tw / 2 + u(70)
    tmp = Image.new("RGBA", (W, round(u(140))), (0, 0, 0, 0))
    d = ImageDraw.Draw(tmp)
    for w, tx in zip(g, texts):
        on = w["s"] - 0.04 <= t < w["e"] + 0.05
        d.text((x, tmp.height / 2), tx, font=f, fill=GOLD if on else WHITE, anchor="lm", stroke_width=round(u(6)),
               stroke_fill=(20, 16, 14))
        x += f.getlength(tx) + sp
    comp(L, set_alpha(tmp, a), 0, u(1560) - tmp.height / 2)


def confetti(L, t):
    st = t_egil + 1.2
    if t < st:
        return
    rng = np.random.default_rng(4)
    d = ImageDraw.Draw(L)
    cols = [CORAL, GOLD, GREEN, (90, 160, 255), (200, 110, 255)]
    for i in range(60):
        x0 = rng.uniform(150, 950)
        vy = rng.uniform(250, 520)
        dt = t - st - rng.uniform(0, 0.4)
        if dt <= 0:
            continue
        x = x0 + 40 * math.sin(dt * 3 + i)
        y = 380 + vy * dt - 0 * dt
        if y > FLOOR:
            continue
        s = u(rng.uniform(8, 14))
        c = cols[i % len(cols)]
        ang = dt * 6 + i
        pts = [(u(x) + math.cos(ang + q) * s, u(y) + math.sin(ang + q) * s * 0.5) for q in (0, 1.6, 3.14, 4.7)]
        d.polygon(pts, fill=c + (230,))


# ---------- Abi ----------
ROZ = Rozet()
OPN, RND = konusma(WORK / "voice_cut.wav", FPS)


def abi(im, t):
    i = min(len(OPN) - 1, int(t * FPS))
    ROZ.draw(im, t, float(OPN[i]))


class Vid(Video):
    def frame(self, t):
        im = ROOM.convert("RGBA")
        exp_dim = eo(ph(t, t_seb - 0.1, 0.4)) * (1 - eio(ph(t, t_cta - 0.3, 0.4)))
        if exp_dim > 0.01:
            im.alpha_composite(Image.new("RGBA", (W, H), (255, 250, 240, int(110 * exp_dim))))
        ch, sk = draw_character(t)
        floor_shadow(im, sk)
        im.alpha_composite(ch, (round(u(CX0)), round(u(CY0))))
        L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        physics(L, t, sk)
        title(L, t)
        steps(L, t)
        try_text(L, t)
        explain_title(L, t)
        confetti(L, t)
        cta(L, t)
        im.alpha_composite(L)
        z = 1.0 + 0.05 * (1 - eo(ph(t, 0, 0.6))) + 0.03 * clamp(t / TOTAL)
        if t_seb <= t < t_cta:
            z += 0.04 * eio(ph(t, t_seb, 0.8))
        cw, chh = W / z, H / z
        im = im.crop(((W - cw) / 2, (H - chh) * 0.55, (W + cw) / 2, (H - chh) * 0.55 + chh)).resize((W, H), Image.BICUBIC)
        if 2.0 <= t < t_cta - 0.2:
            brand(im, 540, 70, size=40)
        C = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        captions(C, self.groups, t)
        im.alpha_composite(C)
        abi(im, t)
        return im.convert("RGB")


def boing_track(path, times):
    SR = 44100
    y = np.frombuffer(subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(path), "-f", "f32le", "-ac", "1", "-ar",
                                      str(SR), "-"], capture_output=True, check=True).stdout, np.float32).copy()
    m = int(0.45 * SR)
    tt = np.arange(m) / SR
    f = 180 + 260 * np.exp(-tt * 6) + 40 * np.sin(2 * np.pi * 14 * tt)
    ph_ = 2 * np.pi * np.cumsum(f) / SR
    b = np.sin(ph_) * np.exp(-tt * 5.5) * 0.35
    for s in times:
        i = int(s * SR)
        if i + m < len(y):
            y[i:i + m] += b
    at._write(str(path), y)


if __name__ == "__main__":
    mode = sys.argv[2] if len(sys.argv) > 2 else "render"
    v = Vid([{"start": 0, "end": TOTAL, "draw": lambda *a: None}], words, "", TOTAL, bg=None)
    if mode == "frames":
        for tt in [float(x) for x in sys.argv[3].split(",")]:
            v.frame(tt).save(WORK / f"fr_{tt:05.2f}.png")
    else:
        sfx = [(0.0, "pop"), (t_sirt, "pop"), (t_ayak, "pop"), (t_kol, "pop"), (t_simdi, "whoosh"), (t_seb - 0.1, "whoosh"),
               (t_agir, "pop"), (t_egil + 1.2, "ding"), (t_cta - 0.1, "pop")]
        at.sfx(str(WORK / "sfx.wav"), TOTAL, sfx)
        boing_track(WORK / "sfx.wav", [s + 0.3 for s in ATT])
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-stream_loop", "2", "-i", str(WORK / "muzik.wav"), "-af",
                        f"atrim=0:{TOTAL:.3f},afade=t=in:d=0.15,afade=t=out:st={TOTAL - 0.5:.3f}:d=0.5",
                        "-ar", "44100", "-ac", "1", str(WORK / "music.wav")], check=True)
        at.final_mix(str(WORK / "voice_cut.wav"), str(WORK / "music.wav"), str(WORK / "sfx.wav"), str(WORK / "mix.m4a"))
        v.render(str(WORK / "mix.m4a"), str(WORK / "video.mp4"))
        print("render bitti", TOTAL, flush=True)
