"""43. video (2K, ~46 sn): Bu iki çizgi aynı uzunlukta — Müller-Lyer illüzyonu.
Kullanım: python3 video43_ok.py <WORK> [frames t1,t2,... | ses | render]
WORK/img/bina.jpg (Unsplash j56VJGRkcRU) ve WORK/img/oda1.jpg (Unsplash UfDueCFmxUc) gerekir."""
import os
os.environ.setdefault("PA_SCALE", str(4 / 3))
import json, math, subprocess, sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from engine import *  # noqa
from pa_ui import put_word, panel, txt, pop, captions
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


t_cogu, t_alt, t_ama, t_inan, t_kald = T("Çoğu"), T("alttakini"), T("Ama"), T("İnanmıyorsan"), T("kaldıralım")
t_gordun, t_bir, t_simdi, t_cev, t_hic = T("Gördün"), T("Birebir"), T("Şimdi"), T("çevireyim"), T("hiç")
t_peki, t_en, t_ok, t_bina, t_yakin = T("Peki"), T("En"), T("ok"), T("binanın"), T("yakında")
t_acik, t_oda, t_uzak, t_uzk2, t_buyuk = T("Açık"), T("odanın"), T("uzakta"), T("Uzaktakini"), T("büyük")
t_bu, t_sen, t_yorum, t_daha = T("Bu", 1), T("Sen"), T("Yorumlara"), T("Daha", 2)
S2, S3, S4, S5 = t_ama - 0.1, t_simdi - 0.1, t_peki - 0.1, t_ok - 0.1
S6, S7, S8, S9, S10 = t_acik - 0.1, t_uzk2 - 0.1, t_bu - 0.1, t_sen - 0.1, t_daha - 0.1
CUTS = [S4, S8, S9]

GOLD = (255, 204, 70)
CYAN = (80, 200, 255)
INKC = (14, 16, 30)
GRN = (52, 200, 110)


def sm(x):
    return eio(clamp(x))


def ramp(t, a, b):
    return sm((t - a) / max(1e-6, b - a))


def wnd(t, a, b, fi=0.2, fo=0.2):
    return ramp(t, a, a + fi) * (1 - ramp(t, b - fo, b))


def mix(c1, c2, k):
    return tuple(c1[i] + (c2[i] - c1[i]) * k for i in range(3))


# ---------------- çizim ----------------
X0, X1, YT, YB, FIN = 260, 820, 760, 1100, 130     # taban (1080) birimleri
CXB, CYB = 540, 930
TH = u(13)


def fig(y, phi, x0=X0, x1=X1, f=FIN):
    """Yatay Müller-Lyer: phi=38 dışa açık kanat, phi=142 ok ucu."""
    c, s = math.cos(math.radians(phi)), math.sin(math.radians(phi))
    main = [((x0, y), (x1, y))]
    fins = [((x1, y), (x1 + f * c, y - f * s)), ((x1, y), (x1 + f * c, y + f * s)),
            ((x0, y), (x0 - f * c, y - f * s)), ((x0, y), (x0 - f * c, y + f * s))]
    return main, fins


def vfig(cx, cy, L, phi, f):
    """Dikey Müller-Lyer (piksel)."""
    c, s = math.cos(math.radians(phi)), math.sin(math.radians(phi))
    y0, y1 = cy - L / 2, cy + L / 2
    main = [((cx, y0), (cx, y1))]
    fins = [((cx, y1), (cx - f * s, y1 + f * c)), ((cx, y1), (cx + f * s, y1 + f * c)),
            ((cx, y0), (cx - f * s, y0 - f * c)), ((cx, y0), (cx + f * s, y0 - f * c))]
    return main + fins


def tobase_px(segs, z=1.0, dx=0.0, dy=0.0):
    out = []
    for p, q in segs:
        out.append(((u(CXB + (p[0] - CXB) * z + dx), u(CYB + (p[1] - CYB) * z + dy)),
                    (u(CXB + (q[0] - CXB) * z + dx), u(CYB + (q[1] - CYB) * z + dy))))
    return out


def dashes(x, ya, yb, k=1.0, dash=22, gap=16):
    out, y, ye = [], ya, ya + (yb - ya) * k
    while y < ye:
        out.append(((x, y), (x, min(y + dash, ye))))
        y += dash + gap
    return out


def draw_groups(base, groups, glow=0.9):
    small = np.zeros((H // 4, W // 4, 3), np.float32)
    any_g = False
    for segs, col, a, th in groups:
        if a <= 0.01 or not segs:
            continue
        any_g = True
        xs = [v for p, q in segs for v in (p[0], q[0])]
        ys = [v for p, q in segs for v in (p[1], q[1])]
        pad = int(th * 2 + 4)
        bx0, by0 = max(0, int(min(xs)) - pad), max(0, int(min(ys)) - pad)
        bx1, by1 = min(W, int(max(xs)) + pad), min(H, int(max(ys)) + pad)
        if bx1 <= bx0 or by1 <= by0:
            continue
        m = np.zeros((by1 - by0, bx1 - bx0), np.uint8)
        ms = np.zeros((H // 4, W // 4), np.uint8)
        for p, q in segs:
            cv2.line(m, (int((p[0] - bx0) * 16), int((p[1] - by0) * 16)), (int((q[0] - bx0) * 16), int((q[1] - by0) * 16)),
                     255, max(1, int(round(th))), cv2.LINE_AA, shift=4)
            cv2.line(ms, (int(p[0] * 4), int(p[1] * 4)), (int(q[0] * 4), int(q[1] * 4)), 255,
                     max(1, int(round(th / 4 * 1.8))), cv2.LINE_AA, shift=4)
        mf = (m.astype(np.float32) / 255 * a)[..., None]
        reg = base[by0:by1, bx0:bx1]
        reg *= (1 - mf)
        reg += mf * np.array(col, np.float32)
        small += (ms.astype(np.float32) / 255 * a)[..., None] * np.array(col, np.float32)
    if glow > 0 and any_g:
        small = cv2.GaussianBlur(small, (0, 0), u(10) / 4)
        base += cv2.resize(small, (W, H), interpolation=cv2.INTER_LINEAR) * glow
    return base


def make_bg():
    YY, XX = np.mgrid[0:H, 0:W].astype(np.float32)
    g = (YY / H)[..., None]
    bg = np.array([20, 24, 44], np.float32) * (1 - g) + np.array([7, 9, 18], np.float32) * g
    r = np.sqrt((XX - W / 2) ** 2 + (YY - H * 0.47) ** 2) / H
    bg = bg + (48 * np.clip(0.6 - r, 0, 1))[..., None] * np.array([0.65, 0.8, 1.0], np.float32)
    rng = np.random.default_rng(3)
    bg = bg + rng.normal(0, 1.6, (H, W, 1)).astype(np.float32)
    return bg.astype(np.float32)


BG = make_bg()

# ---------------- fotoğraf kartları ----------------
CW, CH = int(u(800)), int(u(1000))
CCX, CCY = u(540), u(958)


def _round_mask(w, h, r, k=4):
    im = Image.new("L", (w * k, h * k), 0)
    ImageDraw.Draw(im).rounded_rectangle([0, 0, w * k - 1, h * k - 1], radius=int(r * k), fill=255)
    return np.asarray(im.resize((w, h), Image.LANCZOS), np.float32) / 255


MASK = _round_mask(CW, CH, u(44))
SPAD = int(u(60))
_sh = np.zeros((CH + 2 * SPAD, CW + 2 * SPAD), np.float32)
_sh[SPAD:SPAD + CH, SPAD:SPAD + CW] = MASK
SHADOW = cv2.GaussianBlur(_sh, (0, 0), u(26))
_bd = Image.new("L", (CW * 4, CH * 4), 0)
ImageDraw.Draw(_bd).rounded_rectangle([0, 0, CW * 4 - 1, CH * 4 - 1], radius=int(u(44) * 4), outline=255, width=int(u(4) * 4))
BORDER = np.asarray(_bd.resize((CW, CH), Image.LANCZOS), np.float32) / 255


def _load(p):
    return cv2.cvtColor(cv2.imread(str(p)), cv2.COLOR_BGR2RGB).astype(np.float32)


BINA = dict(img=_load(WORK / "img" / "bina.jpg"), c=(705, 1185), cw=1176)
ODA = dict(img=_load(WORK / "img" / "oda1.jpg"), c=(628, 1085), cw=1256)
# köşe çizgileri (fotoğraf pikseli)
B_APEX = np.array([705, 628])
B_L, B_R = np.array([-0.727, 0.687]), np.array([0.804, 0.595])
O_T, O_B = np.array([550, 446]), np.array([550, 1616])
O_TL, O_TR, O_BL, O_BR = (np.array(v) / np.linalg.norm(v) for v in ([-0.811, -0.585], [0.962, -0.274],
                                                                      [-0.847, 0.531], [0.970, 0.243]))


def put_card(base, card, z, dx, a):
    """Kartı çiz, fotoğraf koordinatını kareye çeviren fonksiyonu döndür."""
    sc = CW / card["cw"] * z
    ccx, ccy = card["c"]
    M = np.float32([[sc, 0, CW / 2 - ccx * sc], [0, sc, CH / 2 - ccy * sc]])
    x0 = int(round(CCX - CW / 2 + dx))
    y0 = int(round(CCY - CH / 2))

    def P(x, y):
        return (x0 + CW / 2 + (x - ccx) * sc, y0 + CH / 2 + (y - ccy) * sc)

    if a <= 0.01 or x0 >= W or x0 + CW <= 0:
        return P, x0, y0
    img = cv2.warpAffine(card["img"], M, (CW, CH), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    # gölge
    sx0, sy0 = x0 - SPAD, y0 - SPAD + int(u(22))
    fx0, fy0 = max(0, sx0), max(0, sy0)
    fx1, fy1 = min(W, sx0 + SHADOW.shape[1]), min(H, sy0 + SHADOW.shape[0])
    if fx1 > fx0 and fy1 > fy0:
        s = SHADOW[fy0 - sy0:fy1 - sy0, fx0 - sx0:fx1 - sx0][..., None]
        base[fy0:fy1, fx0:fx1] *= (1 - 0.6 * a * s)
    fx0, fx1 = max(0, x0), min(W, x0 + CW)
    m = MASK[:, fx0 - x0:fx1 - x0][..., None] * a
    reg = base[y0:y0 + CH, fx0:fx1]
    reg *= (1 - m)
    reg += img[:, fx0 - x0:fx1 - x0] * m
    reg += BORDER[:, fx0 - x0:fx1 - x0][..., None] * a * 110
    return P, x0, y0


INS_W, INS_H = int(u(200)), int(u(370))
_ip = Image.new("RGBA", (INS_W, INS_H), (0, 0, 0, 0))
ImageDraw.Draw(_ip).rounded_rectangle([0, 0, INS_W - 1, INS_H - 1], radius=int(u(30)), fill=(12, 14, 28, 215),
                                      outline=(255, 255, 255, 90), width=int(u(3)))
_ipa = np.asarray(_ip, np.float32)
INS_RGB, INS_A = _ipa[..., :3], _ipa[..., 3:] / 255


def inset(base, x0, y0, phi, col, a, groups):
    if a <= 0.01:
        return
    ix, iy = int(x0 + CW - INS_W - u(28)), int(y0 + CH - INS_H - u(28))
    if ix >= W or ix + INS_W <= 0:
        return
    fx0, fx1 = max(0, ix), min(W, ix + INS_W)
    m = INS_A[:, fx0 - ix:fx1 - ix] * a
    reg = base[iy:iy + INS_H, fx0:fx1]
    reg *= (1 - m)
    reg += INS_RGB[:, fx0 - ix:fx1 - ix] * m
    groups.append((vfig(ix + INS_W / 2, iy + INS_H / 2, u(190), phi, u(55)), col, a, u(10)))


def grow(p, q, k):
    return (p, (p[0] + (q[0] - p[0]) * k, p[1] + (q[1] - p[1]) * k))


def bina_overlay(P, y0, t, a, groups):
    k1 = ramp(t, t_bina - 0.1, t_bina + 0.45)
    k2 = ramp(t, t_bina + 0.25, t_bina + 0.8)
    if k1 <= 0:
        return
    ap = P(*B_APEX)
    bt = P(B_APEX[0], 1920)
    bottom = (bt[0], min(bt[1], y0 + CH - u(34)))
    segs = [grow(ap, bottom, k1)]
    if k2 > 0:
        segs += [grow(ap, P(*(B_APEX + B_L * 430)), k2), grow(ap, P(*(B_APEX + B_R * 430)), k2)]
    groups.append((segs, GOLD, a, u(12)))


def oda_overlay(P, t, a, groups):
    k1 = ramp(t, t_oda - 0.1, t_oda + 0.45)
    k2 = ramp(t, t_oda + 0.25, t_oda + 0.8)
    if k1 <= 0:
        return
    tp, bp = P(*O_T), P(*O_B)
    mid = ((tp[0] + bp[0]) / 2, (tp[1] + bp[1]) / 2)
    segs = [grow(mid, tp, k1), grow(mid, bp, k1)]
    if k2 > 0:
        L = 170
        segs += [grow(tp, P(*(O_T + O_TL * L)), k2), grow(tp, P(*(O_T + O_TR * L)), k2),
                 grow(bp, P(*(O_B + O_BL * L)), k2), grow(bp, P(*(O_B + O_BR * L)), k2)]
    groups.append((segs, CYAN, a, u(12)))


# ---------------- illüzyon zaman çizelgesi ----------------
F0 = t_cev - 0.1
NCYC = max(1, round((S4 - F0) / 2.2))
PER = (S4 - F0) / NCYC


def phi_top(t):
    if t < F0 or t >= S4:
        return 142.0
    c = math.cos(2 * math.pi * (t - F0) / PER)
    return 90 + 52 * math.copysign(abs(c) ** 0.55, c)


def lines_alpha(t):
    return clamp(1 - ramp(t, S5 - 0.05, S5 + 0.3) + ramp(t, S7 - 0.05, S7 + 0.3))


def zoom(t):
    return 1.0 + 0.03 * ramp(t, 0, S2) - 0.03 * ramp(t, S2, S2 + 0.5) + 0.04 * ramp(t, S4, S5) \
        - 0.04 * ramp(t, S5, S5 + 0.3) + 0.03 * ramp(t, S8, S10)


def illusion_groups(t, groups):
    la = lines_alpha(t)
    if la <= 0.01:
        return
    z = zoom(t)
    pt = phi_top(t)
    pb = 180 - pt
    gk = ramp(t, t_bir - 0.15, t_bir + 0.15) * (1 - ramp(t, S3, S3 + 0.3))
    ct, cb = mix(GOLD, GRN, gk), mix(CYAN, GRN, gk)
    pulse_b = 0.0
    if t_alt - 0.1 <= t < S2:
        pulse_b = 0.5 + 0.5 * math.sin((t - t_alt) * 9)
    if t_buyuk - 0.1 <= t < S8:
        pulse_b = 0.5 + 0.5 * math.sin((t - t_buyuk) * 9)
    mt, ft = fig(YT, pt)
    mb, fb = fig(YB, pb)
    # okları kaldır / geri getir
    fa = 1.0
    off = 0.0
    if S2 <= t < S3:
        k = ramp(t, t_kald - 0.05, t_kald + 0.45)
        fa, off = 1 - k, 90 * k
    elif S3 <= t < S3 + 0.4:
        fa = ramp(t, S3, S3 + 0.35)

    def push(fins):
        out = []
        for p, q in fins:
            d = np.array(q) - np.array(p)
            d = d / (np.linalg.norm(d) + 1e-6) * off
            out.append(((p[0] + d[0], p[1] + d[1]), (q[0] + d[0], q[1] + d[1])))
        return out

    groups.append((tobase_px(mt, z), ct, la, TH))
    groups.append((tobase_px(mb, z), cb, la, TH * (1 + 0.25 * pulse_b)))
    groups.append((tobase_px(push(ft), z), ct, la * fa, TH))
    groups.append((tobase_px(push(fb), z), cb, la * fa, TH * (1 + 0.25 * pulse_b)))
    # kılavuz kesik çizgiler
    ga = 0.0
    gk2 = 1.0
    if S2 <= t < S3:
        gk2 = ramp(t, t_kald + 0.35, t_kald + 0.85)
        ga = 0.9 * (1 - ramp(t, S3 - 0.25, S3))
    elif t_hic - 0.1 <= t < S4:
        ga = 0.75 * ramp(t, t_hic - 0.1, t_hic + 0.2) * (1 - ramp(t, S4 - 0.2, S4))
    if ga > 0.01 and gk2 > 0:
        segs = dashes(X0, YT - 110, YB + 110, gk2) + dashes(X1, YT - 110, YB + 110, gk2)
        groups.append((tobase_px(segs, z), (235, 240, 255), la * ga, u(5)))


# ---------------- arayüz ----------------
def two(L, t, a, l1, c1, s1, l2, c2, s2, t0):
    q = pop(t, t0, 0.3)
    if q <= 0.02:
        return
    put_word(L, l1, c1, 540, 160, max(8, round(s1 * q)), alpha=a, glow=0.3)
    if l2:
        put_word(L, l2, c2, 540, 285, max(8, round(s2 * q)), alpha=a, glow=0.45)


def ui(L, t):
    if t < S2:
        a = 1 - ramp(t, S2 - 0.2, S2)
        p = 1 + 0.1 * (1 - pop(t, 0.0, 0.28))
        put_word(L, "HANGİSİ", WHITE, 540, 160, round(96 * p), alpha=a, glow=0.3)
        put_word(L, "DAHA UZUN?", GOLD, 540, 285, round(122 * p), alpha=a, glow=0.45)
        if t >= t_cogu - 0.1:
            chip(L, 540, 1290, "Çoğu kişi: ALTTAKİ", bg=WHITE, fg=INKC, size=46, icon_name="index_pointing_up", k="black",
                 alpha=a, scale=pop(t, t_cogu - 0.1, 0.3))
    elif t < S3:
        a = wnd(t, S2, S3 + 0.05)
        if t < t_inan - 0.1:
            two(L, t, a, "İKİSİ DE AYNI", WHITE, 92, "UZUNLUKTA!", GOLD, 120, S2)
        elif t < t_bir - 0.15:
            two(L, t, a, "İNANMIYORSAN", WHITE, 86, "OKLARI KALDIRALIM", GOLD, 92, t_inan - 0.1)
        else:
            q = pop(t, t_bir - 0.15, 0.32)
            put_icon(L, "check_mark_button", 540, 140, 130 * q, alpha=a)
            put_word(L, "BİREBİR AYNI!", GRN, 540, 285, max(8, round(118 * q)), alpha=a if q > 0.02 else 0, glow=0.5)
    elif t < S4:
        a = wnd(t, S3, S4 + 0.05)
        if t < t_hic - 0.1:
            two(L, t, a, "ŞİMDİ OKLARI", WHITE, 90, "ÇEVİRELİM", GOLD, 120, S3)
        else:
            two(L, t, a, "ÇİZGİ HİÇ", WHITE, 96, "DEĞİŞMİYOR!", GRN, 120, t_hic - 0.1)
    elif t < S5:
        a = wnd(t, S4, S5 + 0.05)
        two(L, t, a, "PEKİ", WHITE, 96, "NEDEN?", GOLD, 132, S4)
        put_icon(L, "thinking_face", 540, 470, 150 * pop(t, S4 + 0.15, 0.35), alpha=a)
        if t >= t_en - 0.1:
            chip(L, 540, 1290, "En bilinen açıklama", bg=WHITE, fg=INKC, size=46, icon_name="light_bulb", k="black",
                 alpha=a, scale=pop(t, t_en - 0.1, 0.3))
    elif t < S6:
        a = wnd(t, S5, S6 + 0.05, 0.25, 0.15)
        q = pop(t, S5, 0.3)
        put_word(L, "OK UÇLU ÇİZGİ", GOLD, 540, 160, max(8, round(96 * q)), alpha=a if q > 0.02 else 0, glow=0.45)
        if t >= t_bina - 0.15:
            q2 = pop(t, t_bina - 0.15, 0.3)
            put_word(L, "= BİNANIN DIŞ KÖŞESİ", WHITE, 540, 280, max(8, round(76 * q2)), alpha=a if q2 > 0.02 else 0,
                     glow=0.3)
        if t >= t_yakin - 0.1:
            chip(L, 540, 392, "YAKINDA SANILIR → KISA", bg=GOLD, fg=INKC, size=50, k="black", alpha=a,
                 scale=pop(t, t_yakin - 0.1, 0.3))
    elif t < S7:
        a = wnd(t, S6, S7 + 0.05, 0.25, 0.15)
        q = pop(t, S6, 0.3)
        put_word(L, "AÇIK UÇLU ÇİZGİ", CYAN, 540, 160, max(8, round(92 * q)), alpha=a if q > 0.02 else 0, glow=0.45)
        if t >= t_oda - 0.15:
            q2 = pop(t, t_oda - 0.15, 0.3)
            put_word(L, "= ODANIN İÇ KÖŞESİ", WHITE, 540, 280, max(8, round(80 * q2)), alpha=a if q2 > 0.02 else 0,
                     glow=0.3)
        if t >= t_uzak - 0.1:
            chip(L, 540, 392, "UZAKTA SANILIR → UZUN", bg=CYAN, fg=INKC, size=50, k="black", alpha=a,
                 scale=pop(t, t_uzak - 0.1, 0.3))
    elif t < S8:
        a = wnd(t, S7, S8 + 0.05)
        two(L, t, a, "UZAKTAKİNİ", WHITE, 96, "DAHA BÜYÜK GÖRÜR", GOLD, 96, S7)
        chip(L, 540, 600, "YAKIN SANILAN → KISA", bg=GOLD, fg=INKC, size=42, k="black", alpha=a, scale=pop(t, S7 + 0.25, 0.3))
        chip(L, 540, 1270, "UZAK SANILAN → UZUN", bg=CYAN, fg=INKC, size=42, k="black", alpha=a, scale=pop(t, S7 + 0.45, 0.3))
    elif t < S9:
        a = wnd(t, S8, S9 + 0.05)
        q = pop(t, S8, 0.35)
        panel(L, 540, 225, 900, 250, scale=q, alpha=a, r=40)
        put_word(L, "MÜLLER-LYER İLLÜZYONU", GOLD, 540, 195, max(8, round(70 * q)), alpha=a, glow=0.45)
        txt(L, (540, 285), "Franz Carl Müller-Lyer, 1889", round(38 * q), WHITE, a, k="xb")
    elif t < S10:
        a = wnd(t, S9, S10 + 0.1, 0.2, 0.15)
        q = pop(t, S9, 0.35)
        txt(L, (540, 160), "SEN HANGİSİNİ", round(84 * q), WHITE, a, stroke=7)
        txt(L, (540, 275), "SEÇTİN?", round(116 * q), GOLD, a, stroke=7)
        if t >= t_yorum - 0.08:
            chip(L, 540, 1290, "Yorumlara yaz", bg=INKC, fg=WHITE, size=56, icon_name="speech_balloon", k="black", alpha=a,
                 scale=pop(t, t_yorum - 0.08, 0.35))
    else:
        a = ramp(t, S10, S10 + 0.25)
        txt(L, (540, 170), "Daha fazlası için", 64, WHITE, a, stroke=6)
        pulse = 1 + 0.045 * math.sin((t - S10) * 8) * ramp(t, S10 + 0.4, S10 + 0.7)
        chip(L, 540, 300, "TAKİP ET", bg=INKC, fg=WHITE, size=90, icon_name="bell", k="black", scale=pop(t, S10, 0.4) * pulse)


ROZ = Rozet()
OPN, RND = konusma(VOICE, FPS)


def scene(t):
    base = BG.copy()
    gi = []
    illusion_groups(t, gi)
    base = draw_groups(base, gi)
    groups = []
    # kartlar
    if S5 - 0.1 <= t < S7 + 0.45:
        dxb = W * (1 - ramp(t, S5 - 0.05, S5 + 0.35)) - W * 1.1 * ramp(t, S6 - 0.05, S6 + 0.35)
        dxr = W * (1 - ramp(t, S6 - 0.05, S6 + 0.35)) - W * 1.1 * ramp(t, S7 - 0.05, S7 + 0.35)
        if -W * 1.05 < dxb < W:
            zb = 1.0 + 0.06 * ramp(t, S5, S6 + 0.3)
            P, x0, y0 = put_card(base, BINA, zb, dxb, 1.0)
            inset(base, x0, y0, 142, GOLD, ramp(t, t_ok + 0.1, t_ok + 0.4), groups)
            bina_overlay(P, y0, t, 1.0, groups)
        if -W * 1.05 < dxr < W:
            zr = 1.0 + 0.05 * ramp(t, S6, S7 + 0.3)
            P, x0, y0 = put_card(base, ODA, zr, dxr, 1.0)
            inset(base, x0, y0, 38, CYAN, ramp(t, t_acik + 0.1, t_acik + 0.4), groups)
            oda_overlay(P, t, 1.0, groups)
    base = draw_groups(base, groups)
    for c in CUTS:
        if 0 <= t - c < 0.12:
            base += 80 * (1 - (t - c) / 0.12)
    return base


class Vid(Video):
    def frame(self, t):
        bg = scene(t)
        im = Image.fromarray(np.clip(bg, 0, 255).astype(np.uint8), "RGB").convert("RGBA")
        L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ui(L, t)
        im.alpha_composite(L)
        brand(im, 540, 62, size=34)
        C = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        captions(C, self.groups, t, y=1660)
        im.alpha_composite(C)
        i = min(len(OPN) - 1, int(t * FPS))
        ROZ.draw(im, t, float(OPN[i]))
        return im.convert("RGB")


VID = Vid([{"start": 0, "end": TOTAL, "draw": lambda *a: None}], words, "", TOTAL, bg=None)


def make_audio():
    ev = [(c, "whoosh") for c in CUTS] + [(S2, "whoosh"), (S3, "whoosh"), (S5 - 0.05, "whoosh"), (S6 - 0.05, "whoosh"),
                                          (S7 - 0.05, "whoosh"), (t_cogu - 0.1, "pop"), (t_kald - 0.05, "whoosh"),
                                          (t_kald + 0.4, "tink"), (t_bir - 0.15, "ding"), (t_hic - 0.1, "ding"),
                                          (t_en - 0.1, "pop"), (t_ok + 0.1, "pop"), (t_bina - 0.1, "tink"),
                                          (t_yakin - 0.1, "pop"), (t_acik + 0.1, "pop"), (t_oda - 0.1, "tink"),
                                          (t_uzak - 0.1, "pop"), (S7 + 0.25, "pop"), (S7 + 0.45, "pop"),
                                          (t_yorum - 0.08, "pop"), (S10, "pop")]
    ev += [(F0 + PER * (k + 0.5) / 1.0, "tink") for k in range(NCYC)]
    ev = sorted(set(ev))
    at.sfx(str(WORK / "sfx.wav"), TOTAL, ev)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-stream_loop", "4", "-i", str(WORK / "muzik.wav"), "-af",
                    f"atrim=0:{TOTAL:.3f},afade=t=in:d=0.15,afade=t=out:st={TOTAL - 0.6:.3f}:d=0.6",
                    "-ar", "44100", "-ac", "1", str(WORK / "music.wav")], check=True)
    at.final_mix(str(VOICE), str(WORK / "music.wav"), str(WORK / "sfx.wav"), str(WORK / "mix.m4a"))


if __name__ == "__main__":
    mode = sys.argv[2] if len(sys.argv) > 2 else "render"
    print("TOTAL", TOTAL, "S", [round(x, 2) for x in (S2, S3, S4, S5, S6, S7, S8, S9, S10)], "PER", round(PER, 2), flush=True)
    if mode == "frames":
        (WORK / "test").mkdir(exist_ok=True)
        for tt in [float(x) for x in sys.argv[3].split(",")]:
            VID.frame(tt).save(WORK / "test" / f"fr_{tt:05.2f}.jpg", quality=90)
    elif mode == "ses":
        make_audio()
    else:
        make_audio()
        VID.render(str(WORK / "mix.m4a"), str(WORK / "video.mp4"))
        print("render bitti", TOTAL, flush=True)
