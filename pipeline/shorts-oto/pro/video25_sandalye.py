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
THIGH, SHIN = 245, 300
ANKLE = (640, FLOOR - 42)
TORSO = 290


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
    head = (sh[0] + up[0] * 125 + fw[0] * 10, sh[1] + up[1] * 125 + fw[1] * 10)
    # kollar: yanda serbest (0) -> çapraz (1) -> yukarı (arms)
    def arm(side):
        free_e = (sh[0] - up[0] * 150 + fw[0] * 10, sh[1] - up[1] * 150 + fw[1] * 10)
        free_h = (free_e[0] - up[0] * 130 + fw[0] * 25, free_e[1] - up[1] * 130 + fw[1] * 25)
        cr_e = (sh[0] - up[0] * 125 + fw[0] * 55, sh[1] - up[1] * 125 + fw[1] * 55)
        cr_h = (cr_e[0] + up[0] * 75 + fw[0] * (20 + side * 18), cr_e[1] + up[1] * 75 + fw[1] * (20 + side * 18))
        up_e = (sh[0] + up[0] * 40 + fw[0] * (110 + 10 * side), sh[1] + up[1] * 40 + fw[1] * (110 + 10 * side))
        up_h = (up_e[0] + up[0] * 115 + fw[0] * (40 + 15 * side), up_e[1] + up[1] * 115 + fw[1] * (40 + 15 * side))
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


# ---------- karakter çizimi ----------
CX0, CY0, CX1, CY1 = 150, 180, 980, 1460
CWp, CHp = round(u(CX1 - CX0)), round(u(CY1 - CY0))
KS = 2


def cap(d, p0, p1, wd, col, k=KS, ox=0, oy=0):
    x0, y0 = (u(p0[0]) - ox) * k, (u(p0[1]) - oy) * k
    x1, y1 = (u(p1[0]) - ox) * k, (u(p1[1]) - oy) * k
    r = u(wd) * k / 2
    d.line([(x0, y0), (x1, y1)], fill=col, width=int(2 * r))
    d.ellipse([x0 - r, y0 - r, x0 + r, y0 + r], fill=col)
    d.ellipse([x1 - r, y1 - r, x1 + r, y1 + r], fill=col)


def shade(col, f):
    return tuple(int(clamp(c * f, 0, 255)) for c in col)


def draw_character(t):
    sk = skeleton(t)
    lay = Image.new("RGBA", (CWp * KS, CHp * KS), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    ox, oy = u(CX0) - sk["shake"], u(CY0)
    k = KS
    chair(d, k, u(CX0), u(CY0))
    hip, knee, ank, sh, head = sk["hip"], sk["knee"], sk["ankle"], sk["sh"], sk["head"]
    up, fw = sk["up"], sk["fw"]
    # uzak bacak + uzak kol (koyu)
    off = (-14, -6)
    def leg(dx, dy, f):
        h2, k2, a2 = (hip[0] + dx, hip[1] + dy), (knee[0] + dx, knee[1] + dy), (ank[0] + dx, ank[1] + dy)
        cap(d, h2, k2, 96, shade(NAVY, f), k, ox, oy)
        cap(d, k2, a2, 84, shade(NAVY, f), k, ox, oy)
        # ayakkabı
        sx0, sy = a2[0] - 30, FLOOR - 26 + dy * 0
        d.rounded_rectangle([(u(sx0) - ox) * k, (u(FLOOR - 62) - oy) * k, (u(a2[0] + 112) - ox) * k, (u(FLOOR - 4) - oy) * k],
                            radius=u(28) * k, fill=shade((248, 248, 250), f))
        d.rounded_rectangle([(u(sx0) - ox) * k, (u(FLOOR - 20) - oy) * k, (u(a2[0] + 114) - ox) * k, (u(FLOOR) - oy) * k],
                            radius=u(10) * k, fill=shade((90, 96, 110), f))
    leg(*off, 0.78)
    eF, hF = sk["armF"]
    cap(d, sh, eF, 66, shade(CORAL, 0.78), k, ox, oy)
    cap(d, eF, hF, 58, shade(CORAL, 0.78), k, ox, oy)
    cap(d, hF, hF, 54, shade(SKIN, 0.85), k, ox, oy)
    # gövde (kapüşonlu)
    cap(d, (hip[0] + fw[0] * 8, hip[1] + fw[1] * 8), sh, 170, CORAL, k, ox, oy)
    cap(d, (hip[0] + up[0] * 40 - fw[0] * 10, hip[1] + up[1] * 40 - fw[1] * 10), (sh[0] - fw[0] * 30, sh[1] - fw[1] * 30), 80,
        shade(CORAL, 1.08), k, ox, oy)                                # ışık
    # yakın bacak
    leg(0, 0, 1.0)
    # kapüşon arkası + baş
    hx, hy = head
    R = 104
    cap(d, (sh[0] - fw[0] * 30 + up[0] * 10, sh[1] - fw[1] * 30 + up[1] * 10), (sh[0] - fw[0] * 45 + up[0] * 55, sh[1] - fw[1] * 45 + up[1] * 55), 110,
        shade(CORAL, 0.88), k, ox, oy)
    d.ellipse([(u(hx - R) - ox) * k, (u(hy - R) - oy) * k, (u(hx + R) - ox) * k, (u(hy + R) - oy) * k], fill=SKIN)
    # saç
    d.chord([(u(hx - R - 4) - ox) * k, (u(hy - R - 8) - oy) * k, (u(hx + R + 4) - ox) * k, (u(hy + R) - oy) * k],
            155 + sk["th"], 345 + sk["th"], fill=(70, 48, 36))
    # kulak
    ex_, ey_ = hx - fw[0] * 18 + up[0] * -4, hy - fw[1] * 18 + up[1] * -4
    d.ellipse([(u(ex_ - 22) - ox) * k, (u(ey_ - 28) - oy) * k, (u(ex_ + 22) - ox) * k, (u(ey_ + 28) - oy) * k], fill=shade(SKIN, 0.92))
    # yüz (sağa bakıyor)
    fx, fy = hx + fw[0] * 52 + up[0] * 18, hy + fw[1] * 52 + up[1] * 18
    expr = sk["expr"]
    def L(p, q, col=INKC, w=7):
        d.line([((u(p[0]) - ox) * k, (u(p[1]) - oy) * k), ((u(q[0]) - ox) * k, (u(q[1]) - oy) * k)], fill=col, width=int(u(w) * k))
    if expr == "strain":
        L((fx - 16, fy - 14), (fx + 6, fy), w=8)
        L((fx + 6, fy), (fx - 16, fy + 14), w=8)
    elif expr == "happy":
        d.arc([(u(fx - 18) - ox) * k, (u(fy - 12) - oy) * k, (u(fx + 18) - ox) * k, (u(fy + 18) - oy) * k], 200, 340,
              fill=INKC, width=int(u(8) * k))
    else:
        r = 15 if expr != "focus" else 13
        d.ellipse([(u(fx - r) - ox) * k, (u(fy - r * 1.25) - oy) * k, (u(fx + r) - ox) * k, (u(fy + r * 1.25) - oy) * k], fill=INKC)
        d.ellipse([(u(fx - 3) - ox) * k, (u(fy - 12) - oy) * k, (u(fx + 5) - ox) * k, (u(fy - 4) - oy) * k], fill=(255, 255, 255))
    # kaş
    by = fy - 40
    if expr in ("strain", "focus"):
        L((fx - 24, by - 6), (fx + 20, by + 8), w=8)
    elif expr == "sad":
        L((fx - 24, by + 8), (fx + 20, by - 6), w=8)
    else:
        L((fx - 22, by), (fx + 20, by - 4), w=8)
    # burun + ağız
    nx, ny = hx + fw[0] * 100 + up[0] * -5, hy + fw[1] * 100 + up[1] * -5
    d.ellipse([(u(nx - 16) - ox) * k, (u(ny - 14) - oy) * k, (u(nx + 14) - ox) * k, (u(ny + 14) - oy) * k], fill=shade(SKIN, 0.95))
    mx, my = hx + fw[0] * 60 + up[0] * -48, hy + fw[1] * 60 + up[1] * -48
    if expr == "happy":
        d.chord([(u(mx - 26) - ox) * k, (u(my - 20) - oy) * k, (u(mx + 26) - ox) * k, (u(my + 22) - oy) * k], 0, 180, fill=(140, 40, 40))
    elif expr == "sad":
        d.arc([(u(mx - 20) - ox) * k, (u(my - 2) - oy) * k, (u(mx + 20) - ox) * k, (u(my + 26) - oy) * k], 200, 340,
              fill=INKC, width=int(u(6) * k))
    elif expr == "strain":
        d.rounded_rectangle([(u(mx - 22) - ox) * k, (u(my - 8) - oy) * k, (u(mx + 22) - ox) * k, (u(my + 10) - oy) * k],
                            radius=u(6) * k, fill=(255, 255, 255), outline=INKC, width=int(u(4) * k))
    else:
        d.arc([(u(mx - 18) - ox) * k, (u(my - 14) - oy) * k, (u(mx + 18) - ox) * k, (u(my + 10) - oy) * k], 20, 160,
              fill=INKC, width=int(u(6) * k))
    # yakın kol
    eN, hN = sk["armN"]
    cap(d, sh, eN, 70, shade(CORAL, 1.02), k, ox, oy)
    cap(d, eN, hN, 62, shade(CORAL, 1.02), k, ox, oy)
    cap(d, hN, hN, 58, SKIN, k, ox, oy)
    # ter damlaları
    if sk["sweat"] > 0.02:
        for j, (ddx, ddy) in enumerate(((-40, -120), (30, -135), (-90, -60))):
            ph_ = (t * 1.6 + j * 0.33) % 1
            sx, sy = hx + ddx, hy + ddy + ph_ * 60
            a = int(220 * sk["sweat"] * (1 - ph_))
            d.ellipse([(u(sx - 9) - ox) * k, (u(sy - 13) - oy) * k, (u(sx + 9) - ox) * k, (u(sy + 13) - oy) * k], fill=(120, 190, 255, a))
    small = lay.resize((CWp, CHp), Image.LANCZOS)
    return small, sk


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
