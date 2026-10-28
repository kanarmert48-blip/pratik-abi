"""25. video (Veo görüntülü, 2K, ~27 sn): Sandalyeden öne eğilmeden kalkamazsın.
Tek 10 sn'lik Veo klibini sese göre kurgular: yavaşlatma (optik akış), donuk kare + yakın çekim, açıklama grafikleri, son montaj.
Kullanım: python3 video25v_sandalye_veo.py <WORK> [frames t1,t2,...]
WORK içinde: src/f001.jpg.. (klibin kareleri), voice_fast.wav, words_fast.json, muzik.wav"""
import os
os.environ.setdefault("PA_SCALE", str(4 / 3))
import json, math, subprocess, sys
from functools import lru_cache
from pathlib import Path

import numpy as np
import cv2

sys.path.insert(0, str(Path(__file__).resolve().parent))
from engine import *  # noqa
from PIL import ImageChops
import audio_tools as at
from abi_yuz import konusma
from rozet import Rozet

WORK = Path(sys.argv[1])
SRC = WORK / "src"
VOICE = WORK / "voice_fast.wav"
words = json.loads((WORK / "words_fast.json").read_text(encoding="utf-8"))
VD = at.duration(str(VOICE))
TOTAL = round(VD + 0.45, 3)


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
t_geri = T("ayaklarının", 0)
t_ayaga = T("Ayağa", 1)
t_bunu = T("Bunu")
t_egil = T("eğilerek")
t_cta = T("Kalkabildiysen")
t_follow = T("Daha")

GOLD = (255, 190, 60)
CORAL = (255, 112, 84)
INKC = (28, 30, 44)
GRN = (60, 205, 120)
REDC = (235, 70, 70)

# ---------- kaynak kareler ----------
NSRC = len(list(SRC.glob("f*.jpg")))
SW, SH = 2160, 3840          # kaynak piksel; çizim koordinatları 1080x1920 "kaynak birimi" (x2 = piksel)
K = SW / 1080


@lru_cache(maxsize=20)
def load(i):
    i = int(min(max(i, 0), NSRC - 1))
    return cv2.cvtColor(cv2.imread(str(SRC / f"f{i + 1:03d}.jpg")), cv2.COLOR_BGR2RGB)


_DIS = []


@lru_cache(maxsize=12)
def flows(i):
    if not _DIS:
        _DIS.append(cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM))
    g = lambda j: cv2.cvtColor(cv2.resize(load(j), (540, 960), interpolation=cv2.INTER_AREA), cv2.COLOR_RGB2GRAY)
    a, b = g(i), g(i + 1)
    return _DIS[0].calc(a, b, None), _DIS[0].calc(b, a, None)


def view(fi, box):
    """fi: kesirli kare no; box: (x0,y0,x1,y1) piksel. Ara kareler optik akışla."""
    x0, y0, x1, y1 = box
    i0 = int(math.floor(fi))
    fr = fi - i0
    if i0 >= NSRC - 1 or fr < 0.1:
        return load(min(i0, NSRC - 1))[y0:y1, x0:x1]
    if fr > 0.9:
        return load(i0 + 1)[y0:y1, x0:x1]
    f01, f10 = flows(i0)
    s = 540 / SW
    gx, gy = np.meshgrid(np.arange(x0, x1, dtype=np.float32), np.arange(y0, y1, dtype=np.float32))
    sx, sy = gx * s, gy * s
    F01 = cv2.remap(f01, sx, sy, cv2.INTER_LINEAR) / s
    F10 = cv2.remap(f10, sx, sy, cv2.INTER_LINEAR) / s
    A = cv2.remap(load(i0), gx - fr * F01[..., 0], gy - fr * F01[..., 1], cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    B = cv2.remap(load(i0 + 1), gx - (1 - fr) * F10[..., 0], gy - (1 - fr) * F10[..., 1], cv2.INTER_LINEAR,
                  borderMode=cv2.BORDER_REPLICATE)
    return cv2.addWeighted(A, 1 - fr, B, fr, 0)


# ---------- uzatılmış donuk kareler (alt + yanlara zemin uzantısı) ----------
PADX, PADB = 60, 420         # kaynak birimi


def extended(i):
    img = load(i).astype(np.float32)
    px, pb = int(PADX * K), int(PADB * K)
    band = img[SH - 120:SH]
    ext = cv2.resize(band, (SW, pb), interpolation=cv2.INTER_LINEAR)
    ext = cv2.GaussianBlur(ext, (0, 0), 10)
    yy = np.linspace(0, 1, pb, dtype=np.float32)[:, None, None]
    dark = np.array([34, 22, 14], np.float32)
    ext = ext * (1 - 0.8 * yy ** 0.8) + dark * 0.8 * yy ** 0.8
    full = np.vstack([img, ext])
    sm = 40                     # dikiş yumuşatma
    full[SH - sm:SH + sm] = cv2.GaussianBlur(full[SH - 2 * sm:SH + 2 * sm], (0, 0), 6)[sm:3 * sm]
    full = cv2.copyMakeBorder(full, 0, 0, px, px, cv2.BORDER_REFLECT)
    side = cv2.GaussianBlur(full, (0, 0), 14)
    m = np.ones(full.shape[1], np.float32)
    ramp = np.clip(np.arange(px + 30) / (px + 30), 0, 1)
    m[:px + 30] = ramp
    m[-(px + 30):] = ramp[::-1]
    m = m[None, :, None]
    full = full * m + side * (1 - m)
    return np.clip(full, 0, 255).astype(np.uint8)


_EXT = {}


def ext_img(i):
    if i not in _EXT:
        _EXT[i] = extended(i)
    return _EXT[i]


# ---------- kamera / çekim listesi ----------
FACE = (480, 690)                       # zorlanan yüz (kare ~112-140)
T5E = t_kalk_e + 60 / (24 * 1.4)        # 1-2. deneme biter
M1, M2 = t_cta + 0.6, t_cta + 1.2       # son montaj kesmeleri


def shot(t):
    """-> (kaynak, kare, merkez_x, merkez_y | None, zoom, y0_sabit | None, çekim_başı, sarsıntı)"""
    if t < t_sirt:   # açılış: dik oturuyor
        fi = 5 * eio(ph(t, 0.05, 0.9))
        z = 1.12 - 0.08 * eo(ph(t, 0, t_sirt))
        return "v", fi, 525, None, z, 0.0, 0.0, 0
    if t < t_ayak:   # sırt yakın
        lt = t - t_sirt
        return "e5", 5, 390, 1040, 1.45 + 0.06 * lt / (t_ayak - t_sirt), None, t_sirt, 0
    if t < t_kol:    # ayaklar yakın
        lt = t - t_ayak
        return "e5", 5, 690, 1640, 1.62 + 0.08 * lt / (t_kol - t_ayak), None, t_ayak, 0
    if t < t_simdi:  # kollar çapraz (yavaş çekim)
        lt = t - t_kol
        fi = 5 + 9 * eio(ph(lt, 0.05, 1.25))
        if lt > 1.3:
            fi = 14 + (lt - 1.3) * 24 * 0.45
        z = 1.3 - 0.12 * eio(ph(lt, 0, t_simdi - t_kol))
        return "v", fi, 440, 1010, z, None, t_kol, 0
    if t < t_kalk_e:  # "öne eğilmeden kalk"
        lt = t - t_simdi
        fi = min(33, 24 + lt * 24 * 0.38)
        z = 1.0 + 0.07 * eio(ph(lt, 0, t_kalk_e - t_simdi))
        return "v", fi, 540, None, z, 0.0, t_simdi, 0
    if t < T5E:      # 1-2. deneme (hızlandırılmış)
        lt = t - t_kalk_e
        return "v", 33 + lt * 24 * 1.4, 540, None, 1.06, 0.0, t_kalk_e, 0
    if t < t_kalkama:  # 3. deneme yüz yakın
        lt = t - T5E
        return "v", 112 + lt * 24, FACE[0], FACE[1], 2.25 + 0.1 * lt, None, T5E, 0
    if t < t_agir:   # omuz silkme
        lt = t - t_kalkama
        return "v", 176 + lt * 24, 560, 880, 1.22 + 0.05 * lt / (t_agir - t_kalkama), None, t_kalkama, 0
    if t < t_cta:    # açıklama (donuk kare)
        lt = t - t_agir
        z = 0.96 + 0.05 * eio(ph(lt, 0, t_cta - t_agir))
        return "e24", 24, 545, None, z, 250.0, t_agir, 0
    # son montaj
    if t < M1:
        return "v", 63 + (t - t_cta) * 24 * 1.25, 540, None, 1.1, 0.0, t_cta, 0
    if t < M2:
        return "v", 118 + (t - M1) * 24, FACE[0], FACE[1] - 20, 2.35, None, M1, 0
    km = min(1.0, 41 / ((TOTAL - M2) * 24))
    q = eio(ph(t, M2, TOTAL - M2))
    return "v", 198 + (t - M2) * 24 * km, 560, 860 - 90 * q, 1.28 + 0.22 * q, None, M2, 0


FALLS = [t_kalk_e + (55 - 33) / 33.6, t_kalk_e + (91 - 33) / 33.6, T5E + (121 - 112) / 24]


def camera(t):
    kind, fi, cx, cy, z, y0f, st, _ = shot(t)
    lt = t - st
    z *= 1 + 0.045 * (1 - eo(ph(lt, 0, 0.22)))          # kesmede minik zoom vuruşu
    if kind == "v":
        bx0, by0, bx1, by1 = 0, 0, 1080, 1920
    else:
        bx0, by0, bx1, by1 = -PADX, 0, 1080 + PADX, 1920 + PADB
    w, h = 1080 / z, 1920 / z
    x0 = min(max(cx - w / 2, bx0), bx1 - w)
    if y0f is not None:
        y0 = y0f
    else:
        y0 = cy - h / 2
    y0 = min(max(y0, by0), by1 - h)
    # sarsıntı (düşüşlerde)
    sx = sy = 0.0
    for f in FALLS:
        q = t - f
        if 0 <= q < 0.35:
            e = math.exp(-q * 11)
            sx += 9 * e * math.sin(q * 80) / z
            sy += 14 * e * math.cos(q * 95) / z
    x0 = min(max(x0 + sx, bx0), bx1 - w)
    y0 = min(max(y0 + sy, by0), by1 - h)
    return kind, fi, x0, y0, z, (bx0, by0)


def M(cam, x, y):
    """kaynak birimi -> çıktı birimi (1080x1920)"""
    _, _, x0, y0, z, _ = cam
    return (x - x0) * z, (y - y0) * z


def base_image(cam):
    kind, fi, x0, y0, z, (bx0, by0) = cam
    w, h = 1080 / z, 1920 / z
    px0, py0 = int(round((x0 - bx0) * K)), int(round((y0 - by0) * K))
    px1, py1 = px0 + int(round(w * K)), py0 + int(round(h * K))
    if kind == "v":
        px1, py1 = min(px1, SW), min(py1, SH)
        arr = view(fi, (px0, py0, px1, py1))
    else:
        E_ = ext_img(int(kind[1:]))
        arr = E_[py0:py1, px0:px1]
    arr = cv2.resize(arr, (W, H), interpolation=cv2.INTER_AREA if z < 1.5 else cv2.INTER_CUBIC)
    return arr


# alt karartma + hafif vinyet
_yy, _xx = np.mgrid[0:H, 0:W].astype(np.float32)
_vg = 1 - 0.22 * np.clip(((_xx / W - 0.5) ** 2 * 1.2 + (_yy / H - 0.5) ** 2) * 2.2, 0, 1)
_vg *= 1 - 0.38 * np.clip((_yy / H - 0.74) / 0.26, 0, 1) ** 1.6
VIG = _vg[..., None].astype(np.float32)


# ---------- çizim yardımcıları ----------
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


def gline(L, p0, p1, col, a, w=10, glow_w=34):
    """parlayan çizgi (çıktı birimi)"""
    if a <= 0.01:
        return
    G = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(G).line([(u(p0[0]), u(p0[1])), (u(p1[0]), u(p1[1]))], fill=col + (int(150 * a),), width=round(u(glow_w)))
    L.alpha_composite(G.filter(ImageFilter.GaussianBlur(u(12))))
    ImageDraw.Draw(L).line([(u(p0[0]), u(p0[1])), (u(p1[0]), u(p1[1]))], fill=col + (int(255 * a),), width=round(u(w)))


def dashed(L, p0, p1, col, a, w=6, dash=22, gap=14):
    d = ImageDraw.Draw(L)
    L_ = math.dist(p0, p1)
    if L_ < 1:
        return
    ux, uy = (p1[0] - p0[0]) / L_, (p1[1] - p0[1]) / L_
    s = 0.0
    while s < L_:
        e = min(s + dash, L_)
        d.line([(u(p0[0] + ux * s), u(p0[1] + uy * s)), (u(p0[0] + ux * e), u(p0[1] + uy * e))],
               fill=col + (int(235 * a),), width=round(u(w)))
        s += dash + gap


def arrow_to(L, p0, p1, a, bend=70):
    d = ImageDraw.Draw(L)
    x0, y0, x1, y1 = u(p0[0]), u(p0[1]), u(p1[0]), u(p1[1])
    n = 24
    pts = [(x0 + (x1 - x0) * i / n, y0 + (y1 - y0) * i / n - math.sin(math.pi * i / n) * u(bend)) for i in range(n + 1)]
    d.line(pts, fill=(255, 255, 255, int(255 * a)), width=round(u(17)), joint="curve")
    d.line(pts, fill=GOLD + (int(255 * a),), width=round(u(10)), joint="curve")
    ang = math.atan2(pts[-1][1] - pts[-3][1], pts[-1][0] - pts[-3][0])
    s = u(38)
    tri = [(x1 + math.cos(ang) * s * 0.6, y1 + math.sin(ang) * s * 0.6),
           (x1 + math.cos(ang + 2.4) * s, y1 + math.sin(ang + 2.4) * s),
           (x1 + math.cos(ang - 2.4) * s, y1 + math.sin(ang - 2.4) * s)]
    d.polygon(tri, fill=GOLD + (int(255 * a),), outline=(255, 255, 255, int(255 * a)))


def dot(L, x, y, col, a, r=17):
    glow(L, x, y, u(78), col, 0.65 * a)
    d = ImageDraw.Draw(L)
    R = u(r)
    d.ellipse([u(x) - R, u(y) - R, u(x) + R, u(y) + R], fill=col + (int(255 * a),), outline=(255, 255, 255, int(255 * a)),
              width=round(u(5)))


def label(L, xy, txt, col, a, size=40):
    if a <= 0.01 or size < 4:
        return
    text_c(L, xy, txt, "black", size, col, alpha=a, stroke=7, stroke_fill=(255, 255, 255))


# ---------- sahne grafikleri ----------
def g_title(L, t):
    if t >= t_sirt + 0.3:
        return
    a = 1 - eio(ph(t, t_sirt - 0.2, 0.3))
    pop = 1 + 0.12 * (1 - eb(ph(t, 0, 0.35)))
    chip(L, 540, 140, "ŞİMDİ DENE", bg=CORAL, fg=WHITE, size=38, k="black", alpha=a, scale=pop)
    text_c(L, (540, 262), "SANDALYEDEN", "black", round(108 * pop), INKC, alpha=a, stroke=10, stroke_fill=(255, 255, 255))
    text_c(L, (540, 380), "KALKAMAZSIN!", "black", round(112 * pop), CORAL, alpha=a, stroke=10, stroke_fill=(255, 255, 255))


def g_back(L, t, cam):
    if not (t_sirt <= t < t_ayak):
        return
    lt = t - t_sirt
    q = eo(ph(lt, 0.12, 0.4))
    p0, p1 = M(cam, 272, 1290), M(cam, 290, 790)
    pe = (p0[0] + (p1[0] - p0[0]) * q, p0[1] + (p1[1] - p0[1]) * q)
    gline(L, p0, pe, GRN, 1.0)
    # oturak çizgisi + dik açı işareti
    qa = eo(ph(lt, 0.45, 0.3))
    if qa > 0.01:
        s0, s1 = M(cam, 272, 1290), M(cam, 272 + 260 * qa, 1290)
        gline(L, s0, s1, GRN, qa)
        c = M(cam, 272, 1290)
        r = 46 * cam[4]
        d = ImageDraw.Draw(L)
        d.line([(u(c[0]), u(c[1] - r)), (u(c[0] + r), u(c[1] - r)), (u(c[0] + r), u(c[1]))], fill=(255, 255, 255, int(255 * qa)),
               width=round(u(5)))
    chip(L, 760, 1180, "Sırtın dik", bg=WHITE, fg=INKC, size=44, icon_name="check_mark_button", k="black",
         scale=eb(ph(lt, 0.3, 0.35)))


def g_feet(L, t, cam):
    if not (t_ayak <= t < t_kol):
        return
    lt = t - t_ayak
    q = eo(ph(lt, 0.12, 0.35))
    G = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    cx, cy = M(cam, 700, 1808)
    rx, ry = 230 * cam[4] * q, 48 * cam[4]
    if q > 0.01:
        ImageDraw.Draw(G).ellipse([u(cx - rx), u(cy - ry), u(cx + rx), u(cy + ry)], outline=GRN + (255,), width=round(u(9)))
        Gb = G.filter(ImageFilter.GaussianBlur(u(10)))
        L.alpha_composite(Gb)
        L.alpha_composite(Gb)
        L.alpha_composite(G)
    chip(L, 540, 760, "Ayakların yerde", bg=WHITE, fg=INKC, size=44, icon_name="check_mark_button", k="black",
         scale=eb(ph(lt, 0.25, 0.35)))


def g_arms(L, t, cam):
    if not (t_kol <= t < t_simdi):
        return
    lt = t - t_kol
    a = 1 - eio(ph(t, t_simdi - 0.2, 0.2))
    chip(L, 300, 1330, "Kollar çapraz", bg=WHITE, fg=INKC, size=44, icon_name="check_mark_button", k="black",
         scale=eb(ph(lt, 0.9, 0.35)), alpha=a)


def g_try(L, t, cam):
    a = eo(ph(t, t_simdi - 0.05, 0.3)) * (1 - eio(ph(t, t_kalk_e + 0.15, 0.3)))
    if a > 0.01:
        pop = 1 + 0.15 * (1 - eb(ph(t, t_simdi - 0.05, 0.35)))
        label(L, (540, 165), "ÖNE EĞİLMEK YOK", REDC, a, size=round(72 * pop))
        label(L, (540, 270), "KALK BAKALIM", INKC, a, size=round(92 * pop))
    for i, f in enumerate(FALLS):
        q = ph(t, f - 0.02, 0.55)
        if 0 < q < 1 and t < t_kalkama:
            x, y = [(300, 1180), (330, 1120), (520, 1350)][i]
            sc = eb(clamp(q * 3))
            label(L, (x, y - 70 * q), "BOİNG", GOLD, (1 - q ** 2), size=round(64 * sc))


def g_fail(L, t, cam):
    a = eo(ph(t, t_kalkama - 0.05, 0.25)) * (1 - eio(ph(t, t_agir - 0.15, 0.2)))
    if a <= 0.01:
        return
    sc = eb(ph(t, t_kalkama - 0.05, 0.35))
    if t < t_seb - 0.05:
        label(L, (540, 230), "KALKAMADIN", REDC, a, size=round(104 * sc))
    else:
        b = eb(ph(t, t_seb - 0.05, 0.3))
        label(L, (540, 230), "SEBEBİ?", INKC, a, size=round(104 * b))


# açıklama: F24 karesinde kaynak koordinatları
COM0 = (392, 1205)
TARGET = (720, 1185)
HEEL, TOE, FLOOR_Y = 562, 912, 1838
HIP = (318, 1300)
THMAX = 46.0


def lean_amt(t):
    return eio(ph(t, t_bunu + 0.15, 1.0))


def g_explain(L, t, cam):
    if not (t_agir - 0.05 <= t < t_cta):
        return
    out = 1 - eio(ph(t, t_cta - 0.18, 0.18))
    la = lean_amt(t)
    com = (COM0[0] + (TARGET[0] - COM0[0]) * la, COM0[1] + (TARGET[1] - COM0[1]) * la)
    inside = HEEL <= com[0] <= TOE
    col = GRN if inside else REDC
    # hayalet eğilme
    if la > 0.001:
        th = math.radians(THMAX * la)

        def rot(dx, dy):
            return (HIP[0] + dx * math.cos(th) - dy * math.sin(th), HIP[1] + dx * math.sin(th) + dy * math.cos(th))
        ga = min(1, la * 3) * out
        sc = cam[4]
        mask = Image.new("L", (W, H), 0)
        dm = ImageDraw.Draw(mask)
        a0, a1 = M(cam, *rot(40, -20)), M(cam, *rot(60, -455))
        tw = u(200 * sc)
        dm.line([(u(a0[0]), u(a0[1])), (u(a1[0]), u(a1[1]))], fill=255, width=round(tw))
        for c in (a0, a1):
            dm.ellipse([u(c[0]) - tw / 2, u(c[1]) - tw / 2, u(c[0]) + tw / 2, u(c[1]) + tw / 2], fill=255)
        hc = M(cam, *rot(85, -628))
        hr = u(100 * sc)
        dm.ellipse([u(hc[0]) - hr, u(hc[1]) - hr, u(hc[0]) + hr, u(hc[1]) + hr], fill=255)
        mask = mask.filter(ImageFilter.GaussianBlur(u(2)))
        edge = ImageChops.subtract(mask.filter(ImageFilter.MaxFilter(9)), mask)
        G = Image.new("RGBA", (W, H), (255, 255, 255, 0))
        G.putalpha(mask.point(lambda v: int(v * 0.30 * ga)))
        Ge = Image.new("RGBA", (W, H), (255, 255, 255, 0))
        Ge.putalpha(edge.point(lambda v: min(255, int(v * 2.2 * ga))))
        L.alpha_composite(Ge.filter(ImageFilter.GaussianBlur(u(8))))
        L.alpha_composite(G)
        L.alpha_composite(Ge)
        # omuz yolu (kesikli yay)
        if la > 0.05:
            R = 470
            n = max(2, int(14 * la))
            pts = []
            for k in range(n + 1):
                a = math.radians(4 + (THMAX * la - 8) * k / n)
                pts.append(M(cam, HIP[0] + R * math.sin(a), HIP[1] - R * math.cos(a)))
            for k in range(0, len(pts) - 1, 2):
                ImageDraw.Draw(L).line([(u(pts[k][0]), u(pts[k][1])), (u(pts[k + 1][0]), u(pts[k + 1][1]))],
                                       fill=GOLD + (int(255 * ga),), width=round(u(8)))
    # ayak bölgesi
    qa = eo(ph(t, t_geri - 0.05, 0.4)) * out
    if qa > 0.01:
        h0, h1 = M(cam, HEEL, FLOOR_Y + 6), M(cam, HEEL + (TOE - HEEL) * qa, FLOOR_Y + 6)
        ImageDraw.Draw(L).rounded_rectangle([u(h0[0]), u(h0[1] - 9), u(h1[0]), u(h1[1] + 9)], radius=u(9), fill=GRN + (int(235 * qa),),
                                            outline=(255, 255, 255, int(255 * qa)), width=round(u(3)))
        c = M(cam, (HEEL + TOE) / 2, FLOOR_Y)
        label(L, (c[0], c[1] + 62), "AYAKLARIN", GRN, qa, size=42)
    # çekül
    ca = eo(ph(t, t_agir - 0.05, 0.35)) * out
    pc = M(cam, *com)
    pf = M(cam, com[0], FLOOR_Y)
    if ca > 0.01:
        pl = eo(ph(t, t_geri - 0.1, 0.45))
        if pl > 0.01:
            dashed(L, (pc[0], pc[1] + 30), (pf[0], pc[1] + 30 + (pf[1] - pc[1] - 30) * pl), col, ca * pl)
        # hedef
        ta = eo(ph(t, t_ayaga + 0.2, 0.4)) * (1 - eio(ph(t, t_bunu + 0.3, 0.4))) * out
        if ta > 0.01:
            pt = M(cam, *TARGET)
            R = u(26) * (1 + 0.12 * math.sin(t * 9))
            ImageDraw.Draw(L).ellipse([u(pt[0]) - R, u(pt[1]) - R, u(pt[0]) + R, u(pt[1]) + R], outline=GOLD + (int(255 * ta),),
                                      width=round(u(6)))
            dashed(L, (pt[0], pt[1] + 32), M(cam, TARGET[0], FLOOR_Y - 4), GOLD, ta * 0.9, w=5)
            arrow_to(L, (pc[0] + 34, pc[1] - 8), (pt[0] - 40, pt[1] - 6), ta * eo(ph(t, t_ayaga + 0.35, 0.4)))
        dot(L, pc[0], pc[1], col, ca)
        sc = eb(ph(t, t_agir - 0.05, 0.4))
        if t < t_bunu + 0.2:
            label(L, (pc[0] - 30, pc[1] - 92), "AĞIRLIK MERKEZİ", col, ca * (1 - eio(ph(t, t_bunu, 0.2))), size=round(40 * sc))
    # çarpı / tik
    xa = eo(ph(t, t_geri + 0.6, 0.3)) * (1 - eio(ph(t, t_bunu + 0.5, 0.25))) * out
    if xa > 0.01:
        put_icon(L, "cross_mark", pf[0], pf[1] - 60, 92 * eb(ph(t, t_geri + 0.6, 0.35)), alpha=xa)
    if inside and la > 0.9:
        q = ph(t, t_bunu + 1.05, 0.4)
        put_icon(L, "check_mark_button", pf[0] + 150, pf[1] - 110, 120 * eb(q), alpha=out)
        label(L, (790, 430), "ŞİMDİ KALKARSIN", GRN, out * eo(q), size=round(50 * eb(q)))
    if t > t_bunu + 0.1:
        oa = eo(ph(t, t_bunu + 0.1, 0.3)) * out * (1 - eio(ph(t, t_bunu + 1.0, 0.25)))
        label(L, (800, 430), "ÖNE EĞİL", GOLD, oa, size=round(66 * eb(ph(t, t_bunu + 0.1, 0.35))))


def g_cta(L, t):
    if t < t_cta - 0.05:
        return
    if t < t_follow - 0.08:
        chip(L, 540, 165, "Kalkabildin mi?", bg=INKC, fg=WHITE, size=58, icon_name="speech_balloon", k="black",
             scale=eb(ph(t, t_cta - 0.05, 0.4)))
    else:
        pulse = 1 + 0.04 * math.sin((t - t_follow) * 9) * eo(ph(t, t_follow + 0.4, 0.3))
        chip(L, 540, 165, "TAKİP ET", bg=CORAL, fg=WHITE, size=64, icon_name="bell", k="black",
             scale=eb(ph(t, t_follow - 0.08, 0.4)) * pulse)


def captions(L, groups, t, y, xoff):
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
    x = W / 2 - tw / 2 + u(xoff)
    tmp = Image.new("RGBA", (W, round(u(140))), (0, 0, 0, 0))
    d = ImageDraw.Draw(tmp)
    for w, tx in zip(g, texts):
        on = w["s"] - 0.04 <= t < w["e"] + 0.05
        d.text((x, tmp.height / 2), tx, font=f, fill=GOLD if on else WHITE, anchor="lm", stroke_width=round(u(6)),
               stroke_fill=(20, 16, 14))
        x += f.getlength(tx) + sp
    comp(L, set_alpha(tmp, a), 0, u(y) - tmp.height / 2)


ROZ = Rozet()
OPN, RND = konusma(VOICE, FPS)
CUTS = [t_sirt, t_ayak, t_kol, t_simdi, t_kalk_e, T5E, t_kalkama, t_agir, t_cta, M1, M2]
FLASH = [t_agir, t_cta, M1, M2]


class Vid(Video):
    def frame(self, t):
        cam = camera(t)
        arr = base_image(cam).astype(np.float32) * VIG
        im = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB").convert("RGBA")
        L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        g_back(L, t, cam)
        g_feet(L, t, cam)
        g_arms(L, t, cam)
        g_explain(L, t, cam)
        g_title(L, t)
        g_try(L, t, cam)
        g_fail(L, t, cam)
        g_cta(L, t)
        im.alpha_composite(L)
        for f in FLASH:
            if 0 <= t - f < 0.14:
                im.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 255, int(120 * (1 - (t - f) / 0.14)))))
        if t_sirt + 0.1 <= t < t_agir - 0.1 and not (t_simdi - 0.1 <= t < t_kalk_e + 0.45) and not (t_kalkama - 0.1 <= t):
            brand(im, 540, 62, size=36)
        C = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        top = t_agir - 0.06 <= t < t_cta - 0.06
        captions(C, self.groups, t, 120 if top else 1560, 0 if top else 70)
        im.alpha_composite(C)
        i = min(len(OPN) - 1, int(t * FPS))
        ROZ.draw(im, t, float(OPN[i]))
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
    print("TOTAL", TOTAL, "cuts", [round(c, 2) for c in CUTS], flush=True)
    if mode == "frames":
        for tt in [float(x) for x in sys.argv[3].split(",")]:
            v.frame(tt).save(WORK / "test" / f"fr_{tt:05.2f}.jpg", quality=88)
    else:
        sfx = [(0.02, "pop"), (t_sirt, "whoosh"), (t_sirt + 0.3, "pop"), (t_ayak, "whoosh"), (t_ayak + 0.25, "pop"),
               (t_kol + 0.9, "pop"), (t_simdi, "whoosh"), (T5E, "whoosh"), (t_kalkama, "pop"), (t_agir, "whoosh"),
               (t_agir + 0.05, "pop"), (t_geri, "pop"), (t_ayaga + 0.35, "whoosh"), (t_bunu + 0.2, "whoosh"),
               (t_bunu + 1.05, "ding"), (t_cta, "whoosh"), (t_cta + 0.05, "pop"), (M1, "whoosh"), (M2, "whoosh"), (t_follow - 0.08, "pop")]
        at.sfx(str(WORK / "sfx.wav"), TOTAL, sfx)
        boing_track(WORK / "sfx.wav", FALLS + [M1 + (121 - 118) / 24])
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-stream_loop", "2", "-i", str(WORK / "muzik.wav"), "-af",
                        f"atrim=0:{TOTAL:.3f},afade=t=in:d=0.15,afade=t=out:st={TOTAL - 0.5:.3f}:d=0.5",
                        "-ar", "44100", "-ac", "1", str(WORK / "music.wav")], check=True)
        at.final_mix(str(VOICE), str(WORK / "music.wav"), str(WORK / "sfx.wav"), str(WORK / "mix.m4a"))
        v.render(str(WORK / "mix.m4a"), str(WORK / "video.mp4"))
        print("render bitti", TOTAL, flush=True)
