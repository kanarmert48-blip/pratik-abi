"""29. video (2K, ~33 sn): Ağzın açıkken yutkunamazsın.
Görsel: x-ray kafa render'ı (Unsplash) + üstüne ışıyan organ katmanları (dil, damak, lokma, kaslar, gırtlak).
Kullanım: python3 video29_yutkunma.py <WORK> [frames t1,t2,...]"""
import os
os.environ.setdefault("PA_SCALE", str(4 / 3))
import json, math, subprocess, sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from engine import *  # noqa
from pa_ui import put_word, panel, txt, pop, win, captions
import audio_tools as at
from abi_yuz import konusma
from rozet import Rozet
import xr29 as X
import ov29 as O

WORK = Path(sys.argv[1])
VOICE = WORK / "voice_cut.wav"
words = json.loads((WORK / "words.json").read_text(encoding="utf-8"))
P = json.loads((WORK / "marks.json").read_text())["piece_ends"]
TOTAL = round(at.duration(str(VOICE)) + 0.35, 3)


def _hits(key):
    k = trl(clean(key)).strip('"!?;,.…')
    return [w for w in words if trl(clean(w["w"])).strip('"!?;,.…') == k]


def T(key, nth=0):
    return _hits(key)[nth]["s"]


t_simdi, t_try0, t_yapa = T("şimdi"), P[1] + 0.05, T("Yapamadın")
t_yutk = T("Yutkunmak")
X0 = t_yutk - 0.25
t_dil, t_dam, t_bas, t_lok = T("dilinin"), T("damağına"), T("bastırıp"), T("lokmayı")
t_bunun, t_kapali, t_sabit = T("Bunun"), T("kapalı"), T("sabit")
t_cunku, t_girt, t_yukari, t_kaslar, t_cene, t_tutun = T("Çünkü"), T("gırtlağını"), T("yukarı"), T("kaslar"), T("çene"), T("tutunuyor")
t_agzin, t_kaslar2, t_tutmak, t_girt2, t_kaldira = T("Ağzın"), T("kaslar", 1), T("tutmakla"), T("gırtlağını", 1), T("kaldıramıyor")
t_yani, t_nered, t_imk = T("Yani"), T("neredeyse"), T("imkânsız")
t_kac, t_yorum, t_daha = T("Kaçıncı"), T("Yorumlara"), T("Daha")
X1 = t_kac - 0.2

GOLD = (255, 200, 80)
INKC = (14, 18, 34)
GRN = (60, 210, 125)
REDC = (240, 72, 72)
PINKT = (255, 140, 185)
CYAN = (130, 220, 255)


def sm(x):
    return eio(clamp(x))


def ramp(t, a, b):
    return sm((t - a) / max(1e-6, b - a))


def wnd(t, a, b, fi=0.3, fo=0.3):
    return ramp(t, a, a + fi) * (1 - ramp(t, b - fo, b))


# ---------------- kamera ----------------
CAMK = [(0.0, 1930, 1960, 1760), (5.2, 1950, 1990, 1600), (6.25, 2000, 1975, 1290), (7.9, 2000, 1975, 1250),
        (8.7, 1800, 2200, 1400), (9.7, 1730, 2370, 1500), (10.5, 1960, 2070, 1680), (13.75, 1960, 2080, 1600),
        (14.4, 1940, 2370, 1320), (17.45, 1940, 2370, 1290), (18.05, 1960, 2170, 1560), (22.85, 1955, 2160, 1500),
        (23.3, 1930, 2120, 1660), (26.7, 1930, 2100, 1760)]


def cam_at(t):
    if t <= CAMK[0][0]:
        k = CAMK[0]
        return X.Cam(k[1], k[2], k[3])
    for (t0, *a), (t1, *b) in zip(CAMK, CAMK[1:]):
        if t0 <= t <= t1:
            q = sm((t - t0) / (t1 - t0))
            return X.Cam(*(a[i] + (b[i] - a[i]) * q for i in range(3)))
    k = CAMK[-1]
    return X.Cam(k[1], k[2], k[3])


# ---------------- organ durumu ----------------
B_ORAL = O.b_of_x(1640)          # lokma ağızdan çıkıyor
B_UES = O.b_of_y(2650)           # yemek borusu girişi
TB0, TB1, TB2, TB3 = t_bas + 0.1, t_lok + 0.62, t_lok + 1.12, t_lok + 2.15   # lokma zaman noktaları


def bol_b(t):
    if t < TB0:
        return 0.0
    if t < TB1:
        return B_ORAL * sm((t - TB0) / (TB1 - TB0))
    if t < TB2:
        return B_ORAL + (B_UES - B_ORAL) * ((t - TB1) / (TB2 - TB1))
    return B_UES + (1 - B_UES) * sm((t - TB2) / (TB3 - TB2))


def lift_try(t, starts):
    v = 0.0
    for s0 in starts:
        q = (t - s0) / 0.42
        if 0 <= q <= 1:
            v = max(v, math.sin(math.pi * q) * 0.16)
    return v


def state_at(t):
    st = O.state()
    # çene
    th = 0.0
    if t < X0 + 0.6:
        th = 3 + 8 * sm(t / 0.45) if t < X0 else 11 * (1 - sm((t - X0) / 0.5))
    elif t >= t_agzin - 0.05:
        th = 11 * sm((t - (t_agzin - 0.05)) / 0.6)
    st.th = th
    # gırtlak kalkışı
    lift = 0.0
    if X0 <= t < t_bunun:
        lift = ramp(t, TB1 - 0.05, TB1 + 0.35) * (1 - ramp(t, TB2 + 0.25, TB2 + 0.85))
    elif t_cunku - 0.2 <= t < t_agzin:
        lift = 0.85 * ramp(t, t_yukari, t_yukari + 0.5) * (1 - ramp(t, t_tutun + 0.15, t_tutun + 0.7))
    elif t >= t_agzin:
        lift = lift_try(t, [t_kaldira - 0.55, t_kaldira + 0.05, t_nered - 0.4])
    elif t < X0:
        lift = lift_try(t, [t_try0 + 0.2, t_try0 + 0.85, t_try0 + 1.5])
    oo = th / 11.0
    st.hyo = (70 * lift - 10 * oo, -100 * lift + 30 * oo)
    st.lar = (45 * lift - 8 * oo, -120 * lift + 25 * oo)
    # yumuşak damak, gırtlak kapağı
    if X0 <= t < t_bunun:
        st.vel = ramp(t, TB1 - 0.45, TB1 - 0.1) * (1 - ramp(t, TB2 + 0.3, TB2 + 0.8))
        st.epi = ramp(t, TB1 + 0.0, TB1 + 0.35) * (1 - ramp(t, TB2 + 0.2, TB2 + 0.7))
    # dil + lokma (normal yutkunma)
    if X0 <= t < t_bunun:
        b = bol_b(t)
        st.bol = b
        st.bol_a = ramp(t, X0 + 0.15, X0 + 0.5) * (1 - ramp(t, TB3 - 0.45, TB3))
        (bx, by), _ = O.bolus_at(b)
        if b <= B_ORAL + 1e-6:
            pre = O.s_near_x(2120 + 95) * ramp(t, t_dil - 0.05, t_bas)
            front = O.s_near_x(min(2350, bx + 95)) if t >= TB0 else -1.0
            st.wave = max(pre, front) if t >= t_dil - 0.05 else None
            st.cup = 1.0 - ramp(t, TB1 - 0.45, TB1)
            st.cup_s = O.s_near_x(bx)
        else:
            s0 = O.s_near_x(1700)
            st.wave = s0 + (1.12 - s0) * ramp(t, TB1, TB1 + 0.4)
            st.cup = 0.0
        st.press = 1 - ramp(t, TB2 + 0.4, TB2 + 1.1)
        st.reach = 0.9
        el = ramp(t, TB1 - 0.2, TB1 + 0.1)
        st.bol_shape = (1 + 0.38 * el, 1 - 0.2 * el)
        st.eso = wnd(t, TB2 - 0.15, TB3 + 0.1, 0.25, 0.4)
    # ağız açık: lokma dilin üstünde kalır
    if t_agzin + 0.25 <= t < X1 + 0.4:
        st.cup = 1.0
        st.cup_s = 0.3
        if t_yani + 0.2 <= t < t_imk + 0.5:     # dil dener ama yetişemez
            q = (t - (t_yani + 0.2)) / 1.0
            st.wave = 0.05 + 0.4 * (q - math.floor(q))
            st.reach = 0.32
        dx, dy = O.dorsum_point(st, 0.3)
        jig = 4 * math.sin(t * 7.0) if t >= t_yani else 0.0
        st.bol_xy = (dx + jig, dy - 40)
        st.bol_a = ramp(t, t_agzin + 0.25, t_agzin + 0.6)
    # vurgular
    F = {}
    F["tongue"] = wnd(t, t_dil - 0.15, TB1 + 0.1, 0.3, 0.4)
    F["palate"] = wnd(t, t_dam - 0.1, TB0 + 0.7, 0.25, 0.35)
    F["phar"] = wnd(t, TB1 - 0.2, TB2 + 0.4, 0.25, 0.4)
    F["hyoid"] = max(wnd(t, t_cunku - 0.1, t_agzin - 0.1, 0.3, 0.3), 0.6 * wnd(t, TB1, TB2 + 0.5))
    F["lar"] = wnd(t, t_girt - 0.1, t_agzin - 0.1, 0.3, 0.3)
    F["mus"] = max(wnd(t, t_kaslar - 0.15, t_agzin - 0.05, 0.3, 0.3), wnd(t, t_kaslar2 - 0.15, X1, 0.3, 0.4))
    F["lar_red"] = max(wnd(t, t_girt2 - 0.1, t_yani + 0.2, 0.25, 0.3), wnd(t, t_try0 + 0.05, t_yapa, 0.25, 0.25))
    st.focus = F
    st.tens = max(ramp(t, t_yukari - 0.1, t_yukari + 0.3) * (1 - ramp(t, t_tutun + 0.2, t_tutun + 0.6)),
                  wnd(t, t_kaslar2 - 0.1, X1, 0.3, 0.4))
    st.mand = max(wnd(t, t_bunun - 0.1, t_cunku - 0.1, 0.35, 0.35), 0.8 * wnd(t, t_agzin - 0.05, t_kaslar2 + 0.2, 0.2, 0.4))
    st.anchor = wnd(t, t_cene - 0.1, t_agzin - 0.2, 0.25, 0.3) * (0.75 + 0.25 * math.sin(t * 9))
    return st


# ---------------- UI ----------------
def tag(L, cam, p_src, text, col, a, lx, ly, size=44):
    """organ etiketi: noktadan çizgi + koyu hap"""
    if a <= 0.01:
        return
    ax, ay = cam.U(p_src)
    f = font("xb", round(u(size)))
    lay = Image.new("RGBA", L.size, (0, 0, 0, 0))
    dl = ImageDraw.Draw(lay)
    tw = dl.textlength(text, font=f)
    padx, hh = u(size * 0.62), u(size * 1.65)
    bx0, by0 = u(lx) - tw / 2 - padx, u(ly) - hh / 2
    bx1, by1 = u(lx) + tw / 2 + padx, u(ly) + hh / 2
    ex = min(max(u(ax), bx0 + hh / 2), bx1 - hh / 2)
    ey = by0 if u(ay) < by0 else (by1 if u(ay) > by1 else u(ay))
    A = int(255 * a)
    dl.line([(u(ax), u(ay)), (ex, ey)], fill=col + (int(A * 0.9),), width=round(u(4)))
    r = u(11)
    dl.ellipse([u(ax) - r * 1.9, u(ay) - r * 1.9, u(ax) + r * 1.9, u(ay) + r * 1.9], outline=col + (int(A * 0.6),),
               width=round(u(3)))
    dl.ellipse([u(ax) - r, u(ay) - r, u(ax) + r, u(ay) + r], fill=col + (A,))
    dl.rounded_rectangle([bx0, by0, bx1, by1], radius=hh / 2, fill=(10, 14, 30, int(A * 0.86)), outline=col + (A,),
                         width=round(u(3)))
    dl.text((u(lx), u(ly)), text, font=f, fill=(255, 255, 255, A), anchor="mm")
    L.alpha_composite(lay)


def arrow(L, p0, p1, col, a, w=12, head=34):
    """ekran birimlerinde düz ok"""
    if a <= 0.01:
        return
    lay = Image.new("RGBA", L.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    x0, y0, x1, y1 = u(p0[0]), u(p0[1]), u(p1[0]), u(p1[1])
    ang = math.atan2(y1 - y0, x1 - x0)
    hx, hy = x1 - math.cos(ang) * u(head) * 0.8, y1 - math.sin(ang) * u(head) * 0.8
    A = int(255 * a)
    d.line([(x0, y0), (hx, hy)], fill=(8, 10, 22, int(A * 0.6)), width=round(u(w + 8)))
    d.line([(x0, y0), (hx, hy)], fill=col + (A,), width=round(u(w)))
    s = u(head)
    pts = [(x1, y1), (x1 - math.cos(ang - 0.5) * s, y1 - math.sin(ang - 0.5) * s),
           (x1 - math.cos(ang + 0.5) * s, y1 - math.sin(ang + 0.5) * s)]
    d.polygon(pts, fill=col + (A,))
    L.alpha_composite(lay)


def arc_arrow(L, cam, th, col, a, w=13, head=36):
    """çenenin aşağı döndüğünü gösteren yay ok (TMJ merkezli)"""
    if a <= 0.01:
        return
    tx, ty = X.TMJ
    R = math.hypot(2470 - tx, 2330 - ty) + 40
    a0 = math.atan2(2330 - ty, 2470 - tx) - math.radians(9)
    a1 = a0 + math.radians(19)
    pts = []
    for i in range(24):
        q = a0 + (a1 - a0) * i / 23
        pts.append(cam.U((tx + R * math.cos(q) + 5 * th, ty + R * math.sin(q) + 1.5 * th)))
    lay = Image.new("RGBA", L.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    A = int(255 * a)
    P = [(u(x), u(y)) for x, y in pts]
    d.line(P[:-2], fill=(8, 10, 22, int(A * 0.6)), width=round(u(w + 8)), joint="curve")
    d.line(P[:-2], fill=col + (A,), width=round(u(w)), joint="curve")
    (x1, y1), (x0, y0) = P[-1], P[-4]
    ang = math.atan2(y1 - y0, x1 - x0)
    s_ = u(head)
    d.polygon([(x1, y1), (x1 - math.cos(ang - 0.5) * s_, y1 - math.sin(ang - 0.5) * s_),
               (x1 - math.cos(ang + 0.5) * s_, y1 - math.sin(ang + 0.5) * s_)], fill=col + (A,))
    L.alpha_composite(lay)


def ring(L, cx, cy, R, q, col, a, w=14):
    if a <= 0.01:
        return
    lay = Image.new("RGBA", L.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    box = [u(cx - R), u(cy - R), u(cx + R), u(cy + R)]
    d.arc(box, 0, 360, fill=(255, 255, 255, int(70 * a)), width=round(u(w)))
    if q > 0.001:
        d.arc(box, -90, -90 + 360 * q, fill=col + (int(255 * a),), width=round(u(w)))
    L.alpha_composite(lay)


def top_title(L, t):
    """kanca başlıkları"""
    if t >= X0 + 0.3:
        return
    a = 1 - ramp(t, X0 - 0.1, X0 + 0.25)
    if t < t_yapa - 0.08:
        p1 = 1 + 0.12 * (1 - pop(t, 0.0, 0.3))
        txt(L, (540, 236), "AĞZINI AÇ", round(128 * p1), WHITE, a, stroke=6)
        if t >= t_simdi - 0.08:
            txt(L, (540, 372), "ŞİMDİ YUTKUN", round(108 * pop(t, t_simdi - 0.08, 0.32)), GOLD, a, stroke=6)
    else:
        q = pop(t, t_yapa - 0.08, 0.32)
        txt(L, (540, 250), "YAPAMADIN", round(132 * q), WHITE, a, stroke=7)
        txt(L, (540, 384), "DEĞİL Mİ?", round(96 * q), GOLD, a, stroke=6)


def ui(L, t, cam, st):
    top_title(L, t)
    # deneme sayacı: boğaz çevresinde halka
    if t_try0 - 0.1 <= t < t_yapa + 0.3:
        a = wnd(t, t_try0 - 0.1, t_yapa + 0.3, 0.2, 0.25)
        q = 1 - clamp((t - t_try0) / (t_yapa - t_try0))
        cx, cy = cam.U((1715 + st.lar[0], 2540 + st.lar[1]))
        ring(L, cx, cy, 150, q, (255, 110, 110), a, w=14)
        chip(L, cx + 300, cy + 40, "DENE", bg=INKC, fg=WHITE, size=50, icon_name="stopwatch", k="black",
             alpha=a, scale=pop(t, t_try0 - 0.1, 0.3))
    if t_yapa - 0.08 <= t < X0 + 0.3:
        a = 1 - ramp(t, X0 - 0.1, X0 + 0.25)
        put_icon(L, "grinning_face_with_sweat", 840, 1080, 300 * pop(t, t_yapa - 0.05, 0.4), alpha=a)
    # bölüm çipleri
    segs = [(X0 + 0.15, t_bunun - 0.15, "NORMAL YUTKUNMA", GRN, INKC, "check_mark_button"),
            (t_bunun - 0.1, t_cunku - 0.15, "ÇENE KAPALI VE SABİT", GOLD, INKC, "locked"),
            (t_cunku - 0.1, t_agzin - 0.15, "GIRTLAĞI KALDIRAN KASLAR", (255, 104, 84), WHITE, None),
            (t_agzin - 0.1, X1, "AĞIZ AÇIKKEN", REDC, WHITE, "warning")]
    for a0, a1, s, bg, fg, ic in segs:
        if a0 <= t < a1:
            a = wnd(t, a0, a1, 0.2, 0.2)
            chip(L, 540, 250, s, bg=bg, fg=fg, size=46, icon_name=ic, k="black", alpha=a, scale=pop(t, a0, 0.32))
    # etiketler
    if X0 <= t < t_bunun:
        tag(L, cam, (2060, 2080), "DİL", PINKT, wnd(t, t_dil - 0.05, TB1, 0.25, 0.3), 815, 1330)
        tag(L, cam, (2150, 1797), "DAMAK", GOLD, wnd(t, t_dam - 0.05, TB0 + 0.6, 0.25, 0.3), 770, 560)
        if st.bol is not None:
            (bx, by), _ = O.bolus_at(st.bol)
            tag(L, cam, (bx, by), "LOKMA", CYAN, wnd(t, t_lok - 0.1, TB2 + 0.3, 0.25, 0.3), 300, 520 if t < TB1 else 610)
        tag(L, cam, (1575, 2300), "YUTAK", (255, 160, 190), wnd(t, TB1 - 0.1, TB2 + 0.4, 0.25, 0.3), 250, 1330)
    if t_bunun - 0.1 <= t < t_cunku:
        a = wnd(t, t_bunun, t_cunku - 0.1, 0.3, 0.3)
        tag(L, cam, X.jaw_pt((2300, 2475), st.th), "ALT ÇENE", GOLD, a, 820, 1360)
        b = wnd(t, t_sabit - 0.25, t_cunku - 0.1, 0.25, 0.3)
        lx, ly = cam.U((2470, 2000))
        put_icon(L, "locked", lx + 70, ly - 10, 120 * pop(t, t_sabit - 0.25, 0.35), alpha=b)
    if t_cunku - 0.1 <= t < t_agzin:
        tag(L, cam, (1735 + st.lar[0], 2560 + st.lar[1]), "GIRTLAK", GOLD, wnd(t, t_girt - 0.05, t_agzin - 0.1, 0.25, 0.3),
            300, 1390)
        tag(L, cam, (2050, 2400), "KASLAR", (255, 120, 100), wnd(t, t_kaslar - 0.1, t_agzin - 0.1, 0.25, 0.3), 820, 1340)
        tag(L, cam, X.jaw_pt(O.GENIAL, st.th), "ÇENE KEMİĞİ", GOLD, wnd(t, t_cene - 0.05, t_agzin - 0.1, 0.25, 0.3), 800, 700)
        ua = wnd(t, t_yukari - 0.1, t_tutun + 0.4, 0.25, 0.3)
        cx, cy = cam.U((1820 + st.lar[0], 2600 + st.lar[1]))
        arrow(L, (cx + 40, cy + 120), (cx + 40, cy - 110), GOLD, ua, w=14)
    if t_agzin - 0.1 <= t < X1 + 0.2:
        a = wnd(t, t_kaslar2 - 0.2, X1, 0.25, 0.3)
        arc_arrow(L, cam, st.th, (255, 110, 90), a)
        tag(L, cam, (2040, 2440 + 30 * st.th / 11), "ÇENEYİ AÇIK TUTUYOR", (255, 120, 100), a, 640, 1395, size=40)
        b = wnd(t, t_girt2 - 0.1, t_yani + 0.1, 0.25, 0.3)
        lx, ly = cam.U((1715 + st.lar[0], 2560 + st.lar[1]))
        put_icon(L, "cross_mark", lx, ly, 150 * pop(t, t_kaldira - 0.1, 0.35), alpha=b)
        tag(L, cam, (1715 + st.lar[0], 2640 + st.lar[1]), "GIRTLAK KALKAMIYOR", REDC, b, 330, 1300, size=40)
        if t >= t_yani - 0.1:
            e = wnd(t, t_yani - 0.1, X1 + 0.15, 0.25, 0.25)
            q = pop(t, t_nered - 0.12, 0.38)
            panel(L, 540, 470, 860, 230, scale=q, alpha=e, r=40)
            put_word(L, "NEREDEYSE", WHITE, 540, 420, 72, scale=q, alpha=e, glow=0.2)
            put_word(L, "İMKÂNSIZ", (255, 90, 90), 540, 520, 96, scale=q, alpha=e, glow=0.4)


def cta(L, t):
    if t < t_kac - 0.12:
        return
    if t < t_daha - 0.1:
        a = 1 - ramp(t, t_daha - 0.22, t_daha - 0.08)
        p = pop(t, t_kac - 0.12, 0.35)
        txt(L, (540, 290), "KAÇINCI DENEMEDE", round(84 * p), WHITE, a, stroke=6)
        txt(L, (540, 400), "PES ETTİN?", round(116 * p), GOLD, a, stroke=6)
        put_icon(L, "grinning_face_with_sweat", 540, 790, 380 * pop(t, t_kac, 0.4), alpha=a)
        for k, (s, x) in enumerate((("1.", 290), ("2.", 540), ("3+", 790))):
            chip(L, x, 1120, s, bg=WHITE, fg=INKC, size=64, k="black", alpha=a, scale=pop(t, t_kac + 0.25 + 0.15 * k, 0.3))
        if t >= t_yorum - 0.08:
            chip(L, 540, 1300, "Yorumlara yaz", bg=INKC, fg=WHITE, size=52, icon_name="speech_balloon", k="black",
                 alpha=a, scale=pop(t, t_yorum - 0.08, 0.35))
    else:
        a = ramp(t, t_daha - 0.1, t_daha + 0.15)
        txt(L, (540, 650), "Daha fazlası için", 62, WHITE, a, stroke=5)
        pulse = 1 + 0.045 * math.sin((t - t_daha) * 8) * ramp(t, t_daha + 0.4, t_daha + 0.7)
        chip(L, 540, 810, "TAKİP ET", bg=INKC, fg=WHITE, size=88, icon_name="bell", k="black",
             scale=pop(t, t_daha - 0.1, 0.4) * pulse)


# ---------------- kare ----------------
ROZ = Rozet()
OPN, RND = konusma(VOICE, FPS)
YY = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
GRADE = (1 - 0.42 * np.clip((0.27 - YY) / 0.27, 0, 1)) * (1 - 0.5 * np.clip((YY - 0.72) / 0.28, 0, 1))
CTA_CAM = X.Cam(1560, 1700, 2650)
_CTA_BG = {}


def cta_bg():
    if "im" not in _CTA_BG:
        b = X.base(CTA_CAM, 0.0)
        _CTA_BG["im"] = cv2.GaussianBlur(b, (0, 0), u(9)) * 0.33
    return _CTA_BG["im"]


class Vid(Video):
    def frame(self, t):
        cta_k = ramp(t, X1 - 0.05, X1 + 0.35)
        if cta_k < 1:
            tt = min(t, X1 + 0.35)
            cam = cam_at(tt)
            st = state_at(tt)
            buf = X.base(cam, st.th, st.hyo)
            O.draw(buf, cam, st)
            if cta_k > 0:
                buf = buf * (1 - cta_k) + cta_bg() * cta_k
        else:
            cam, st, buf = None, None, cta_bg().copy()
        if t < 0.95:      # açılışta tarama çizgisi
            yl = H * (-0.05 + 1.1 * ramp(t, 0.0, 0.9))
            band = np.exp(-((np.arange(H, dtype=np.float32) - yl) / u(36)) ** 2)[:, None, None]
            trail = np.clip((yl - np.arange(H, dtype=np.float32)) / u(260), 0, 1)[:, None, None]
            trail = (1 - trail) * (np.arange(H)[:, None, None] < yl)
            lum = buf.mean(axis=2, keepdims=True) / 255
            k = (1 - ramp(t, 0.7, 0.95))
            buf = buf + (band * (90 + 140 * lum) + trail * 40 * lum) * k * np.array([0.55, 0.85, 1.0], np.float32)
        buf = buf * GRADE
        im = Image.fromarray(np.clip(buf, 0, 255).astype(np.uint8), "RGB").convert("RGBA")
        L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        if cta_k < 1:
            ui(L, t, cam, st)
        cta(L, t)
        im.alpha_composite(L)
        brand(im, 540, 62, size=34)
        C = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        captions(C, self.groups, t)
        im.alpha_composite(C)
        i = min(len(OPN) - 1, int(t * FPS))
        ROZ.draw(im, t, float(OPN[i]))
        return im.convert("RGB")


def _rd(path):
    return np.frombuffer(subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(path), "-f", "f32le", "-ac", "1", "-ar",
                                         "44100", "-"], capture_output=True, check=True).stdout, np.float32).copy()


def gulp_track(path, times):
    SR = 44100
    y = _rd(path)
    m = int(0.32 * SR)
    tt = np.arange(m) / SR
    f = 320 * np.exp(-tt * 9) + 90
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 10) * 0.45
    for t0 in times:
        i = int(t0 * SR)
        if 0 <= i and i + m < len(y):
            y[i:i + m] += s
    at._write(str(path), y)


def tick_track(path, t0, t1):
    SR = 44100
    y = _rd(path)
    m = int(0.05 * SR)
    tt = np.arange(m) / SR
    s = np.sin(2 * np.pi * 1800 * tt) * np.exp(-tt * 90) * 0.22
    t = t0
    while t < t1:
        i = int(t * SR)
        if i + m < len(y):
            y[i:i + m] += s
        t += 0.5
    at._write(str(path), y)


if __name__ == "__main__":
    mode = sys.argv[2] if len(sys.argv) > 2 else "render"
    v = Vid([{"start": 0, "end": TOTAL, "draw": lambda *a: None}], words, "", TOTAL, bg=None)
    print("TOTAL", TOTAL, "X", round(X0, 2), round(X1, 2), "B", round(B_ORAL, 3), round(B_UES, 3), flush=True)
    if mode == "frames":
        (WORK / "test").mkdir(exist_ok=True)
        for tt in [float(x) for x in sys.argv[3].split(",")]:
            v.frame(tt).save(WORK / "test" / f"fr_{tt:05.2f}.jpg", quality=90)
    else:
        sfx = [(0.02, "whoosh"), (t_simdi - 0.08, "pop"), (t_try0, "whoosh"), (t_yapa - 0.05, "pop"), (X0, "whoosh"),
               (t_dil - 0.05, "pop"), (t_dam - 0.05, "pop"), (t_lok - 0.1, "pop"), (t_bunun - 0.1, "whoosh"),
               (t_sabit - 0.25, "pop"), (t_cunku - 0.1, "whoosh"), (t_kaslar - 0.1, "pop"), (t_tutun, "ding"),
               (t_agzin - 0.1, "whoosh"), (t_kaldira - 0.1, "pop"), (t_nered - 0.12, "whoosh"), (X1, "whoosh"),
               (t_kac + 0.25, "pop"), (t_kac + 0.4, "pop"), (t_kac + 0.55, "pop"), (t_yorum - 0.08, "pop"),
               (t_daha - 0.1, "pop")]
        at.sfx(str(WORK / "sfx.wav"), TOTAL, sfx)
        gulp_track(WORK / "sfx.wav", [TB1 + 0.05, t_yukari + 0.1])
        tick_track(WORK / "sfx.wav", t_try0 + 0.1, t_yapa - 0.1)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-stream_loop", "2", "-i", str(WORK / "muzik.wav"), "-af",
                        f"atrim=0:{TOTAL:.3f},afade=t=in:d=0.15,afade=t=out:st={TOTAL - 0.6:.3f}:d=0.6",
                        "-ar", "44100", "-ac", "1", str(WORK / "music.wav")], check=True)
        at.final_mix(str(VOICE), str(WORK / "music.wav"), str(WORK / "sfx.wav"), str(WORK / "mix.m4a"))
        v.render(str(WORK / "mix.m4a"), str(WORK / "video.mp4"))
        print("render bitti", TOTAL, flush=True)
