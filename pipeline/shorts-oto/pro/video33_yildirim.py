"""33. video (2K, ~40 sn): Arabana yıldırım düşerse hayatta kalır mısın? — gerçek görüntüler (kanca → bilgi → veri).
Görüntüler: "Lightning to a car" (Sunzi safari, CC BY-SA 3.0), "Lightning strikes in slow motion (240fps) in Muurame"
(MrNousia, CC BY 3.0), "Cage de Faraday" (Antoine Taveneaux, CC BY-SA 3.0), "Lightning and Cars" (A Guy Named Nyal,
CC BY-SA 2.0), NASA SDO güneş (kamu malı), Pixabay klipleri. Gök gürültüsü: Richard Humphries (CC BY).
Kullanım: python3 video33_yildirim.py <WORK> [frames t1,t2,...]"""
import os
os.environ.setdefault("PA_SCALE", str(4 / 3))
import json, math, subprocess, sys
from functools import lru_cache
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


t_icer, t_buyuk, t_evet = T("içeride"), T("Büyük"), T("evet")
t_ama, t_lastikler = T("Ama"), T("lastikler")
t_yil, t_km, t_delip = T("Yıldırım", 1), T("kilometrelerce"), T("delip")
t_birkac, t_sant, t_durd = T("birkaç"), T("santimlik"), T("durduramaz")
t_seni, t_metal = T("Seni", 1), T("metal")
t_akim, t_dolas, t_lastikl, t_yere, t_sen, t_koru = T("Akım"), T("dolaşıp"), T("lastiklerden"), T("yere"), T("sen"), T("korunuyorsun")
t_buna, t_far = T("Buna"), T("Faraday")
t_sira, t_300, t_volt, t_30, t_amper = T("Sıradan"), T("300"), T("volt"), T("30"), T("amper")
t_hava, t_gunes, t_5, t_sicak = T("Havayı", 1), T("güneşin"), T("5"), T("sıcak")
t_bu, t_lastik2, t_elek = T("Bu"), T("lastik", 1), T("elektronik")
t_ama2, t_ustu, t_kormaz = T("Ama", 1), T("üstü"), T("korumaz")
t_sen2, t_yorum, t_daha = T("sen", 1), T("Yorumlara"), T("Daha", 1)

S2, S3, S4, S5 = t_ama - 0.1, t_yil - 0.12, t_birkac - 0.12, t_seni - 0.12
S6, S7, S8, S9 = t_akim - 0.12, t_buna - 0.12, t_sira - 0.12, t_hava - 0.12
S10, S10b, S11, S12, S13 = t_bu - 0.12, t_elek - 0.1, t_ama2 - 0.12, t_sen2 - 0.12, t_daha - 0.1
CUTS = [S2, S3, S4, S5, S6, S7, S8, S9, S10, S10b, S11, S12, S13]

GOLD = (255, 204, 70)
RED = (232, 40, 50)
INKC = (14, 16, 30)
GRN = (52, 200, 110)
CYAN = (120, 210, 255)


def sm(x):
    return eio(clamp(x))


def ramp(t, a, b):
    return sm((t - a) / max(1e-6, b - a))


def wnd(t, a, b, fi=0.25, fo=0.25):
    return ramp(t, a, a + fi) * (1 - ramp(t, b - fo, b))


def keys(t, ks, ease=True):
    """parçalı geçiş: [(t, değer)] (değer sayı ya da demet)"""
    if t <= ks[0][0]:
        return ks[0][1]
    for (a, va), (b, vb) in zip(ks, ks[1:]):
        if a <= t <= b:
            q = (t - a) / max(1e-6, b - a)
            q = sm(q) if ease else q
            if isinstance(va, tuple):
                return tuple(x + (y - x) * q for x, y in zip(va, vb))
            return va + (vb - va) * q
    return ks[-1][1]


YY, XX = np.mgrid[0:H, 0:W].astype(np.float32)
TOP = np.clip((0.34 - YY / H) / 0.34, 0, 1)[..., None]
BOT = np.clip((YY / H - 0.70) / 0.30, 0, 1)[..., None]
VIG = np.clip(1 - 0.45 * (((XX - W / 2) / (W * 0.7)) ** 2 + ((YY - H * 0.5) / (H * 0.62)) ** 2), 0.35, 1)[..., None]


def legible(img, top=0.55, bot=0.55):
    return img * (1 - top * TOP) * (1 - bot * BOT)


# ---------------- fotoğraflar (Ken Burns) ----------------
class Photo:
    def __init__(self, path, orig_w):
        big = cv2.cvtColor(cv2.imread(str(path)), cv2.COLOR_BGR2RGB).astype(np.float32)
        self.big, self.k = big, big.shape[1] / orig_w
        self.mid = cv2.resize(big, (big.shape[1] // 2, big.shape[0] // 2), interpolation=cv2.INTER_AREA)

    def view(self, cx, cy, vis_w, ow=W, oh=H, border=cv2.BORDER_REFLECT):
        s_big = ow / (vis_w * self.k)
        src, k = (self.big, self.k) if s_big >= 0.75 else (self.mid, self.k / 2)
        s = ow / (vis_w * k)
        M = np.float32([[s, 0, ow / 2 - cx * k * s], [0, s, oh / 2 - cy * k * s]])
        return cv2.warpAffine(src, M, (int(ow), int(oh)), flags=cv2.INTER_LINEAR, borderMode=border)


def to_scr(p, cam, ow=W, oh=H, ox=0.0, oy=0.0):
    cx, cy, vw = cam
    s = ow / vw
    return ox + ow / 2 + (p[0] - cx) * s, oy + oh / 2 + (p[1] - cy) * s


CAR = Photo(WORK / "foto" / "car_x4.jpg", 1280)
FAR = Photo(WORK / "foto" / "faraday_x4.jpg", 1044)
LCARS = Photo(WORK / "foto" / "lcars_x4.jpg", 1920)
SUN = Photo(WORK / "foto" / "sun.jpg", 1920)

RNG = np.random.default_rng(33)
GRAIN = [cv2.resize(RNG.normal(0, 1, (H // 3, W // 3)).astype(np.float32), (W, H), interpolation=cv2.INTER_LINEAR)
         for _ in range(6)]


def grain(img, t, k=5.0):
    return img + GRAIN[int(t * 24) % len(GRAIN)][..., None] * k


# yıldırım titremesi: bir çakışın parlaklık zarfı
def flash_env(t, t0, peaks=((0.0, 1.0), (0.12, 0.55), (0.30, 0.8), (0.55, 0.35))):
    v = 0.0
    for dt, a in peaks:
        x = t - (t0 + dt)
        if x >= 0:
            v = max(v, a * math.exp(-x * 9.0))
    return v


# ---------------- akım yolları (araba fotoğrafı, orijinal 1280x960 koordinat) ----------------
STRIKE = (688, 557)
P_FRONT = [(688, 557), (640, 556), (600, 559), (545, 566), (500, 586), (455, 612), (420, 634), (360, 643), (300, 652),
           (240, 664), (190, 678), (168, 698), (196, 722), (228, 742), (252, 772), (266, 806), (276, 840)]
P_REAR = [(688, 557), (760, 558), (830, 569), (900, 600), (960, 630), (1010, 655), (1042, 684), (1055, 724), (1060, 770),
          (1063, 815), (1066, 856)]
P_RTIRE = [(960, 630), (948, 668), (930, 706), (905, 744), (880, 782), (866, 822), (858, 870)]
GROUNDS = [(276, 842), (1066, 856), (858, 872)]
CABIN = [(652, 588), (818, 590), (838, 672), (655, 678)]           # arka cam (içerideki kişi)
CABIN2 = [(470, 600), (640, 584), (640, 676), (455, 668)]          # ön cam


def _arclen(P):
    P = np.array(P, np.float32)
    d = np.r_[0, np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))]
    return P, d


PATHS = [_arclen(P) for P in (P_FRONT, P_REAR, P_RTIRE)]


def _sub(P, d, a, b):
    """yol üzerindeki [a,b] arc-length aralığının noktaları"""
    a, b = max(0, a), min(d[-1], b)
    if b <= a:
        return None
    pts = [np.interp(a, d, P[:, 0]), np.interp(a, d, P[:, 1])]
    out = [pts]
    for i in range(len(d)):
        if a < d[i] < b:
            out.append(list(P[i]))
    out.append([np.interp(b, d, P[:, 0]), np.interp(b, d, P[:, 1])])
    return np.array(out, np.float32)


def current_layer(t, cam, ow, oh, ox, oy, head, alpha):
    """akım ışığı (additive RGB, float). head: 0..1 yol ilerleme"""
    sc = 2
    L = np.zeros((int(oh) // sc, int(ow) // sc, 3), np.float32)
    s = ow / cam[2]
    th_core = max(1, int(round(1.3 * s / sc)))
    jit = np.random.default_rng(int(t * 30))
    for pi, (P, d) in enumerate(PATHS):
        delay = 0.0 if pi < 2 else 0.35
        h = clamp((head - delay) / (1 - delay)) if pi == 2 else head
        if h <= 0:
            continue
        L_end = d[-1] * h
        seg = _sub(P, d, 0, L_end)
        if seg is None:
            continue
        # hafif elektrik titremesi
        seg = seg + jit.normal(0, 0.7, seg.shape).astype(np.float32) * (np.arange(len(seg))[:, None] > 0)
        scr = np.array([to_scr(p, cam, ow, oh) for p in seg], np.float32) / sc
        cv2.polylines(L, [scr.astype(np.int32)], False, (0.25, 0.5, 1.0), th_core * 2, cv2.LINE_AA)
        cv2.polylines(L, [scr.astype(np.int32)], False, (0.8, 0.92, 1.0), th_core, cv2.LINE_AA)
        # ilerleyen parlak darbeler
        for k in range(4):
            c = ((t * 260 + k * d[-1] / 4) % (d[-1] + 60)) - 30
            if c > L_end:
                continue
            sg = _sub(P, d, c - 22, c + 22)
            if sg is None:
                continue
            sp = np.array([to_scr(p, cam, ow, oh) for p in sg], np.float32) / sc
            cv2.polylines(L, [sp.astype(np.int32)], False, (1.0, 1.0, 1.0), th_core * 2, cv2.LINE_AA)
        # baş noktası
        hx, hy = to_scr((np.interp(L_end, d, P[:, 0]), np.interp(L_end, d, P[:, 1])), cam, ow, oh)
        if h < 0.999:
            cv2.circle(L, (int(hx / sc), int(hy / sc)), int(3 * s / sc) + 2, (1, 1, 1), -1, cv2.LINE_AA)
    glow = cv2.GaussianBlur(L, (0, 0), 6) * 1.5 + cv2.GaussianBlur(L, (0, 0), 18) * 1.0
    out = (L + glow) * alpha
    return cv2.resize(out, (int(ow), int(oh)), interpolation=cv2.INTER_LINEAR) * 255


def ground_burst(img, t, t0, cam, ow, oh, ox, oy):
    """akım yere ulaşınca tekerlek altlarında parlama"""
    if t < t0:
        return img
    s = ow / cam[2]
    for i, g in enumerate(GROUNDS):
        x, y = to_scr(g, cam, ow, oh, ox, oy)
        q = t - t0 - 0.08 * i
        if q < 0:
            continue
        a = (0.55 + 0.45 * abs(math.sin(q * 23 + i))) * (1 - 0.5 * clamp(q / 2.0))
        r = (16 + 10 * math.sin(q * 17 + i)) * s
        d2 = ((XX - x) ** 2 + (YY - y) ** 2) / (r * r * 4)
        img = img + np.exp(-d2)[..., None] * np.array([150, 200, 255], np.float32) * a
    return img


def strike_glow(img, t, cam, ow, oh, ox, oy, amp):
    x, y = to_scr(STRIKE, cam, ow, oh, ox, oy)
    s = ow / cam[2]
    r = 26 * s
    d2 = ((XX - x) ** 2 + (YY - y) ** 2) / (r * r)
    return img + np.exp(-d2)[..., None] * np.array([170, 210, 255], np.float32) * amp


def poly_tint(img, poly, cam, ow, oh, ox, oy, col, a):
    if a <= 0.01:
        return img
    pts = np.array([to_scr(p, cam, ow, oh, ox, oy) for p in poly], np.int32)
    m = np.zeros((H, W), np.float32)
    cv2.fillPoly(m, [pts], 1.0, cv2.LINE_AA)
    m = cv2.GaussianBlur(m, (0, 0), 6)[..., None]
    return img * (1 - 0.35 * a * m) + np.array(col, np.float32) * (0.45 * a) * m


# ---------------- sahne: kanca (araba fotoğrafı, tam ekran) ----------------
def hook_cam(t):
    return keys(t, [(0.0, (662.0, 480.0, 540.0)), (t_buyuk - 0.1, (676.0, 492.0, 500.0)),
                    (t_buyuk + 0.45, (748.0, 628.0, 255.0)), (S2 + 0.2, (752.0, 630.0, 236.0))])


def hook_scene(t):
    cam = hook_cam(t)
    img = CAR.view(*cam)
    # çakış: kısa titreşimler + sarsıntı
    f = flash_env(t, 0.03) + 0.5 * flash_env(t, t_icer - 0.04, ((0, 0.6), (0.1, 0.3)))
    if f > 0.01:
        sx = RNG.normal(0, 7 * f)
        sy = RNG.normal(0, 7 * f)
        M = np.float32([[1, 0, sx], [0, 1, sy]])
        img = cv2.warpAffine(img, M, (W, H), borderMode=cv2.BORDER_REFLECT)
        img = img * (1 + 0.55 * f) + 40 * f
        img = strike_glow(img, t, cam, W, H, 0, 0, 1.2 * f)
    img = strike_glow(img, t, cam, W, H, 0, 0, 0.12 + 0.06 * math.sin(t * 31))
    return legible(img, 0.6, 0.45)


# ---------------- sahne: araba paneli (metal kasa + akım) ----------------
PANEL_W, PANEL_H = W, 1300         # panel
PANEL_Y = u(905) - PANEL_W / 2   # üst kenar


def panel_cam(t):
    return keys(t, [(S5 - 0.2, (615.0, 500.0, 1010.0)), (S6, (615.0, 500.0, 990.0)), (t_sen - 0.12, (622.0, 502.0, 960.0)),
                    (t_sen + 0.45, (742.0, 628.0, 430.0)), (S7, (746.0, 630.0, 400.0))])


def car_panel(t):
    cam = panel_cam(t)
    view = CAR.view(*cam, ow=PANEL_W, oh=PANEL_H)
    # arka plan: aynı görüntü, büyük-bulanık-koyu
    bg = CAR.view(cam[0], cam[1] + 40, cam[2] * 0.62)
    bg = cv2.GaussianBlur(cv2.resize(bg, (W // 6, H // 6), interpolation=cv2.INTER_AREA), (0, 0), 6)
    bg = cv2.resize(bg, (W, H), interpolation=cv2.INTER_LINEAR) * 0.32
    img = bg.copy()
    oy = int(PANEL_Y)
    # akım (S6..S7)
    if t >= S6 - 0.05:
        head = ramp(t, t_akim, t_yere + 0.25)
        a = 1 - ramp(t, t_sen + 0.1, t_sen + 0.6) * 0.85
        view = view + current_layer(t, cam, PANEL_W, PANEL_H, 0, oy, head, a)
    # metal kasa vurgusu (S5..S6)
    if S5 - 0.05 <= t < S6 + 0.4:
        view = shell_trace(view, t, cam)
    img[oy:oy + PANEL_H] = view
    if t_yere - 0.1 <= t < t_sen + 0.3:
        gb = ground_burst(img, t, t_yere - 0.05, cam, PANEL_W, PANEL_H, 0, oy)
        fa = 1 - ramp(t, t_sen - 0.1, t_sen + 0.25)
        img[oy:oy + PANEL_H] = img[oy:oy + PANEL_H] * (1 - fa) + gb[oy:oy + PANEL_H] * fa
    img = strike_glow(img, t, cam, PANEL_W, PANEL_H, 0, oy, 0.18 + 0.12 * abs(math.sin(t * 19)))
    if t >= t_sen:
        img = poly_tint(img, CABIN, cam, PANEL_W, PANEL_H, 0, oy, (80, 230, 140), ramp(t, t_sen, t_sen + 0.4))
    # panel çerçevesi
    cv2.rectangle(img, (0, oy), (W - 1, oy + PANEL_H - 1), (230, 230, 240), 3)
    return img


SHELL = [(150, 700), (182, 672), (300, 650), (420, 634), (470, 600), (545, 566), (620, 557), (690, 556), (760, 558),
         (830, 569), (905, 603), (1000, 650), (1046, 688), (1058, 740), (1052, 790)]


def shell_trace(view, t, cam):
    P, d = _arclen(SHELL)
    q = ramp(t, t_seni + 0.1, t_metal + 0.1)
    a = 1 - ramp(t, S6 + 0.05, S6 + 0.4)
    seg = _sub(P, d, 0, d[-1] * q)
    if seg is None or a <= 0.01:
        return view
    sc = 2
    L = np.zeros((PANEL_H // sc, PANEL_W // sc, 3), np.float32)
    scr = np.array([to_scr(p, cam, PANEL_W, PANEL_H) for p in seg], np.float32) / sc
    th = max(2, int(round(3.0 * PANEL_W / cam[2] / sc)))
    cv2.polylines(L, [scr.astype(np.int32)], False, (1.0, 0.85, 0.35), th, cv2.LINE_AA)
    glow = cv2.GaussianBlur(L, (0, 0), 6) * 1.8
    return view + cv2.resize(L + glow, (PANEL_W, PANEL_H)) * 255 * a * (0.85 + 0.15 * math.sin(t * 9))


# ---------------- sahne: Faraday kafesi ----------------
def faraday_scene(t):
    q = clamp((t - S7) / (S8 - S7))
    cam = (650 - 20 * q, 640 - 40 * q, 720 - 120 * sm(q))
    img = FAR.view(*cam)
    f = 0.5 + 0.5 * abs(math.sin(t * 27)) * abs(math.sin(t * 11))
    x, y = to_scr((575, 495), cam)
    s = W / cam[2]
    d2 = ((XX - x) ** 2 + (YY - y) ** 2) / ((60 * s) ** 2)
    img = img + np.exp(-d2)[..., None] * np.array([90, 120, 255], np.float32) * 0.55 * f
    return legible(img, 0.55, 0.4)


# ---------------- sahne: yıldırım + sayılar ----------------
def bolts_scene(t):
    q = clamp((t - S8) / (S9 - S8))
    cam = (keys(t, [(S8, 900.0), (t_30 - 0.3, 1160.0), (S9, 1640.0)]), 640.0, 720.0 - 60 * q)
    img = LCARS.view(*cam)
    f = flash_env(t, t_300 - 0.02, ((0, 1.0), (0.1, 0.5), (0.26, 0.7))) + 0.6 * flash_env(t, t_30 - 0.02, ((0, 0.7), (0.12, 0.4)))
    img = img * (1 + 0.6 * f) + 30 * f
    return legible(img, 0.65, 0.45)


# ---------------- sahne: güneş ----------------
def sun_scene(t):
    q = clamp((t - S9) / (S10 - S9))
    cam = (960.0, 900.0, 2050 - 330 * sm(q))
    img = SUN.view(*cam, border=cv2.BORDER_CONSTANT)
    ang = 1.5 * q
    M = cv2.getRotationMatrix2D((W / 2, H / 2), ang, 1.0)
    img = cv2.warpAffine(img, M, (W, H), borderMode=cv2.BORDER_CONSTANT)
    pul = 1 + 0.06 * math.sin(t * 5)
    return img * pul


# ---------------- gerçek klipler ----------------
class Clip:
    def __init__(self, name):
        self.path = str(WORK / "clip" / name)
        self.cap, self.idx, self.last = None, -1, None

    def get(self, i):
        if self.cap is None or i < self.idx:
            if self.cap is not None:
                self.cap.release()
            self.cap = cv2.VideoCapture(self.path)
            self.idx = -1
        while self.idx < i:
            ok, f = self.cap.read()
            if not ok:
                break
            self.idx += 1
            self.last = f
        return cv2.cvtColor(self.last, cv2.COLOR_BGR2RGB).astype(np.float32)


_CL = {}


def clip(name, t, t0, speed=1.0, off=0.0):
    if name not in _CL:
        _CL[name] = Clip(name)
    return _CL[name].get(max(0, int(((t - t0) * speed + off) * 30)))


def vertical(name, t, t0, zoom=0.04, speed=1.0, off=0.0, dur=3.0):
    f = clip(name, t, t0, speed, off)
    if f.shape[0] != H:
        return framed(f, t, t0, zoom, dur)
    z = 1.0 + zoom * clamp((t - t0) / dur)
    if z > 1.001:
        M = np.float32([[z, 0, W / 2 * (1 - z)], [0, z, H / 2 * (1 - z)]])
        f = cv2.warpAffine(f, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    return f


def framed(f, t, t0, zoom=0.04, dur=3.0):
    """4:5 klip, bulanık arka plan üstünde"""
    z = 1.0 + zoom * clamp((t - t0) / dur)
    fh, fw = f.shape[:2]
    bg = cv2.resize(f, (fw // 8, fh // 8), interpolation=cv2.INTER_AREA)
    bg = cv2.GaussianBlur(cv2.resize(bg, (int(H * fw / fh), H), interpolation=cv2.INTER_LINEAR), (0, 0), 18) * 0.42
    out = np.zeros((H, W, 3), np.float32)
    x0 = (bg.shape[1] - W) // 2
    out[:] = bg[:, x0:x0 + W]
    if z > 1.001:
        M = np.float32([[z, 0, fw / 2 * (1 - z)], [0, z, fh / 2 * (1 - z)]])
        f = cv2.warpAffine(f, M, (fw, fh), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    y0 = int(u(880) - fh / 2)
    out[y0:y0 + fh] = f
    cv2.rectangle(out, (0, y0), (W - 1, y0 + fh - 1), (230, 230, 240), 3)
    return out


# ---------------- yazılar ----------------
def hook_ui(L, t):
    if t >= S2 + 0.15:
        return
    a = 1 - ramp(t, t_buyuk - 0.1, t_buyuk + 0.15)
    p = 1 + 0.12 * (1 - pop(t, 0.0, 0.28))
    put_word(L, "ARABANA YILDIRIM", WHITE, 540, 175, round(84 * p), alpha=a, glow=0.3)
    put_word(L, "DÜŞERSE?", GOLD, 540, 300, round(132 * p), alpha=a, glow=0.45)
    q = 1 + 0.10 * math.exp(-max(0.0, t - t_icer) * 6) * (t >= t_icer - 0.05)   # ilk karede görünür, "içeride"de vurgu
    put_word(L, "HAYATTA KALIR MISIN?", WHITE, 540, 530, round(76 * q * p), alpha=a, glow=0.45)
    chip(L, 540, 408, "GERÇEK DENEY • YAPAY YILDIRIM", bg=RED, fg=WHITE, size=36, k="black", alpha=a)
    if t >= t_buyuk - 0.05:
        b = 1 - ramp(t, S2 - 0.1, S2 + 0.1)
        q = pop(t, t_buyuk - 0.05, 0.35)
        put_icon(L, "check_mark_button", 540, 250, 170 * q, alpha=b)
        put_word(L, "BÜYÜK İHTİMALLE", WHITE, 540, 400, max(8, round(70 * q)), alpha=b if q > 0.02 else 0, glow=0.3)
        if t >= t_evet - 0.08:
            q2 = pop(t, t_evet - 0.08, 0.3)
            put_word(L, "EVET", GRN, 540, 525, max(8, round(150 * q2)), alpha=b if q2 > 0.02 else 0, glow=0.5)


def tire_ui(L, t):
    if not (S2 - 0.05 <= t < S3 + 0.1):
        return
    a = wnd(t, S2 - 0.05, S3 + 0.1, 0.18, 0.18)
    q = pop(t, S2, 0.32)
    put_word(L, "AMA SENİ", WHITE, 540, 200, max(8, round(90 * q)), alpha=a if q > 0.02 else 0, glow=0.3)
    if t >= t_lastikler - 0.08:
        q2 = pop(t, t_lastikler - 0.08, 0.32)
        put_word(L, "LASTİKLER", GOLD, 540, 330, max(8, round(130 * q2)), alpha=a if q2 > 0.02 else 0, glow=0.45)
        put_word(L, "KURTARMIYOR", WHITE, 540, 460, max(8, round(96 * q2)), alpha=a if q2 > 0.02 else 0, glow=0.3)
        put_icon(L, "cross_mark", 540, 1250, 230 * pop(t, t_lastikler + 0.35, 0.35), alpha=a)


def km_ui(L, t):
    if not (S3 - 0.05 <= t < S4 + 0.1):
        return
    a = wnd(t, S3 - 0.05, S4 + 0.1, 0.2, 0.15)
    chip(L, 540, 200, "YAVAŞ ÇEKİM • GERÇEK YILDIRIM", bg=WHITE, fg=INKC, size=38, icon_name="stopwatch", k="black",
         alpha=a, scale=pop(t, S3, 0.3))
    if t >= t_km - 0.08:
        q = pop(t, t_km - 0.08, 0.35)
        put_word(L, "KİLOMETRELERCE", GOLD, 540, 340, max(8, round(104 * q)), alpha=a if q > 0.02 else 0, glow=0.45)
        put_word(L, "HAVAYI DELİYOR", WHITE, 540, 465, max(8, round(88 * q)), alpha=a if q > 0.02 else 0, glow=0.3)


def cm_ui(L, t):
    if not (S4 - 0.05 <= t < S5 + 0.1):
        return
    a = wnd(t, S4 - 0.05, S5 + 0.1, 0.18, 0.18)
    q = pop(t, S4, 0.32)
    put_word(L, "BİRKAÇ SANTİM", GOLD, 540, 210, max(8, round(110 * q)), alpha=a if q > 0.02 else 0, glow=0.45)
    put_word(L, "LASTİK", WHITE, 540, 340, max(8, round(110 * q)), alpha=a if q > 0.02 else 0, glow=0.3)
    if t >= t_durd - 0.08:
        q2 = pop(t, t_durd - 0.08, 0.3)
        chip(L, 540, 1300, "DURDURAMAZ", bg=RED, fg=WHITE, size=70, icon_name="cross_mark", k="black", alpha=a, scale=q2)


def shell_ui(L, t):
    if not (S5 - 0.05 <= t < S6 + 0.1):
        return
    a = wnd(t, S5 - 0.05, S6 + 0.1, 0.2, 0.18)
    q = pop(t, S5, 0.3)
    put_word(L, "SENİ KORUYAN", WHITE, 540, 175, max(8, round(84 * q)), alpha=a if q > 0.02 else 0, glow=0.3)
    if t >= t_metal - 0.08:
        q2 = pop(t, t_metal - 0.08, 0.35)
        put_word(L, "METAL KASA", GOLD, 540, 305, max(8, round(140 * q2)), alpha=a if q2 > 0.02 else 0, glow=0.5)


def flow_ui(L, t):
    if not (S6 - 0.05 <= t < S7 + 0.1):
        return
    a = wnd(t, S6 - 0.05, S7 + 0.1, 0.2, 0.18)
    q = pop(t, S6, 0.3)
    put_word(L, "AKIM DIŞTAN", CYAN, 540, 175, max(8, round(96 * q)), alpha=a * (1 - ramp(t, t_sen - 0.1, t_sen + 0.1)) if q > 0.02 else 0, glow=0.5)
    if t >= t_lastikl - 0.1:
        q2 = pop(t, t_lastikl - 0.1, 0.32)
        b = a * (1 - ramp(t, t_sen - 0.1, t_sen + 0.1))
        put_word(L, "YERE GEÇER", WHITE, 540, 305, max(8, round(110 * q2)), alpha=b if q2 > 0.02 else 0, glow=0.35)
    if t >= t_sen - 0.08:
        q3 = pop(t, t_sen - 0.08, 0.35)
        put_word(L, "İÇERİSİ", WHITE, 540, 175, max(8, round(96 * q3)), alpha=a if q3 > 0.02 else 0, glow=0.3)
        put_word(L, "GÜVENDE", GRN, 540, 310, max(8, round(140 * q3)), alpha=a if q3 > 0.02 else 0, glow=0.5)
        put_icon(L, "check_mark_button", 540, 1400, 150 * pop(t, t_sen + 0.2, 0.3), alpha=a)


def far_ui(L, t):
    if not (S7 - 0.05 <= t < S8 + 0.1):
        return
    a = wnd(t, S7 - 0.05, S8 + 0.1, 0.18, 0.15)
    if t >= t_far - 0.1:
        q = pop(t, t_far - 0.1, 0.35)
        put_word(L, "FARADAY", GOLD, 540, 200, max(8, round(140 * q)), alpha=a if q > 0.02 else 0, glow=0.5)
        put_word(L, "KAFESİ", WHITE, 540, 345, max(8, round(120 * q)), alpha=a if q > 0.02 else 0, glow=0.35)
    chip(L, 540, 1435, "Kafesteki kişiye akım işlemiyor", bg=WHITE, fg=INKC, size=36, k="black",
         alpha=a * ramp(t, S7 + 0.35, S7 + 0.6), scale=pop(t, S7 + 0.35, 0.3))


def fmt_tr(n):
    return f"{int(n):,}".replace(",", ".")


def volt_ui(L, t):
    if not (S8 - 0.05 <= t < S9 + 0.1):
        return
    a = wnd(t, S8 - 0.05, S9 + 0.1, 0.18, 0.15)
    chip(L, 540, 170, "SIRADAN BİR YILDIRIMDA", bg=WHITE, fg=INKC, size=40, icon_name="high_voltage", k="black", alpha=a,
         scale=pop(t, S8, 0.3))
    if t >= t_300 - 0.05:
        k = clamp((t - (t_300 - 0.05)) / 0.55)
        n = 300_000_000 * (1 - (1 - k) ** 3)
        q = pop(t, t_300 - 0.05, 0.3)
        put_word(L, fmt_tr(round(n / 1e6) * 1e6) if k < 1 else "300.000.000", GOLD, 540, 330, max(8, round(104 * q)),
                 alpha=a if q > 0.02 else 0, glow=0.5)
        if t >= t_volt - 0.1:
            put_word(L, "VOLT", WHITE, 540, 450, max(8, round(90 * pop(t, t_volt - 0.1, 0.3))), alpha=a, glow=0.3)
    if t >= t_30 - 0.05:
        k = clamp((t - (t_30 - 0.05)) / 0.45)
        n = 30_000 * (1 - (1 - k) ** 3)
        q = pop(t, t_30 - 0.05, 0.3)
        panel(L, 540, 1300, 760, 170, scale=q, alpha=a, r=40)
        txt(L, (540, 1285), f"{fmt_tr(round(n / 100) * 100)} AMPER" if k < 1 else "30.000 AMPER", round(76 * q), CYAN, a, k="black")
        txt(L, (540, 1352), "Evdeki priz: 230 volt", round(30 * q), (220, 220, 230), a * ramp(t, t_30 + 0.3, t_30 + 0.6), k="xb")


def sun_ui(L, t):
    if not (S9 - 0.05 <= t < S10 + 0.1):
        return
    a = wnd(t, S9 - 0.05, S10 + 0.1, 0.18, 0.15)
    chip(L, 540, 170, "GERÇEK NASA GÖRÜNTÜSÜ", bg=WHITE, fg=INKC, size=36, k="black", alpha=a * ramp(t, S9, S9 + 0.25))
    if t >= t_5 - 0.08:
        q = pop(t, t_5 - 0.08, 0.35)
        put_word(L, "5 KAT", GOLD, 540, 330, max(8, round(170 * q)), alpha=a if q > 0.02 else 0, glow=0.55)
        put_word(L, "DAHA SICAK", WHITE, 540, 480, max(8, round(96 * q)), alpha=a if q > 0.02 else 0, glow=0.35)
    # karşılaştırma çubukları
    if t >= t_gunes - 0.1:
        b = a * ramp(t, t_gunes - 0.1, t_gunes + 0.2)
        panel(L, 540, 1300, 940, 270, alpha=b, r=40)
        g = ramp(t, t_gunes, t_gunes + 0.5)
        x0, wmax = 120, 840
        txt(L, (x0, 1215), "Güneş yüzeyi", 32, (230, 230, 230), b, k="xb", anchor="lm")
        txt(L, (x0 + wmax, 1215), "≈5.500 °C", 32, (255, 170, 60), b, k="black", anchor="rm")
        bar(L, x0, 1255, wmax * 0.2 * g, 26, (255, 150, 40), b)
        if t >= t_5 - 0.1:
            y = ramp(t, t_5 - 0.1, t_5 + 0.55)
            txt(L, (x0, 1320), "Yıldırımın ısıttığı hava", 32, (230, 230, 230), b, k="xb", anchor="lm")
            txt(L, (x0 + wmax, 1320), "≈27.700 °C", 32, (255, 230, 120), b, k="black", anchor="rm")
            bar(L, x0, 1360, wmax * y, 26, (255, 236, 150), b)


def bar(L, x, y, w, h, col, a):
    if w < 2 or a <= 0.01:
        return
    lay = Image.new("RGBA", L.size, (0, 0, 0, 0))
    ImageDraw.Draw(lay).rounded_rectangle([u(x), u(y - h / 2), u(x + w), u(y + h / 2)], radius=u(h / 2),
                                          fill=col + (int(255 * a),))
    L.alpha_composite(lay)


def damage_ui(L, t):
    if not (S10 - 0.05 <= t < S11 + 0.1):
        return
    a = wnd(t, S10 - 0.05, S11 + 0.1, 0.18, 0.15)
    chip(L, 540, 170, "ARABA HASAR GÖREBİLİR", bg=WHITE, fg=INKC, size=40, icon_name="warning", k="black", alpha=a,
         scale=pop(t, S10, 0.3))
    if t >= t_lastik2 - 0.08 and t < S10b + 0.05:
        q = pop(t, t_lastik2 - 0.08, 0.32)
        b = a * (1 - ramp(t, S10b - 0.1, S10b + 0.05))
        put_word(L, "LASTİK", GOLD, 540, 320, max(8, round(130 * q)), alpha=b if q > 0.02 else 0, glow=0.45)
        put_word(L, "PATLAYABİLİR", WHITE, 540, 455, max(8, round(96 * q)), alpha=b if q > 0.02 else 0, glow=0.3)
    if t >= S10b:
        q = pop(t, S10b, 0.32)
        put_word(L, "ELEKTRONİK", GOLD, 540, 320, max(8, round(116 * q)), alpha=a if q > 0.02 else 0, glow=0.45)
        put_word(L, "YANABİLİR", WHITE, 540, 455, max(8, round(100 * q)), alpha=a if q > 0.02 else 0, glow=0.3)


def cabrio_ui(L, t):
    if not (S11 - 0.05 <= t < S12 + 0.1):
        return
    a = wnd(t, S11 - 0.05, S12 + 0.1, 0.18, 0.15)
    q = pop(t, S11, 0.32)
    put_word(L, "ÜSTÜ AÇIK", GOLD, 540, 200, max(8, round(130 * q)), alpha=a if q > 0.02 else 0, glow=0.45)
    put_word(L, "ARABALAR", WHITE, 540, 335, max(8, round(104 * q)), alpha=a if q > 0.02 else 0, glow=0.3)
    if t >= t_kormaz - 0.08:
        chip(L, 540, 470, "KORUMAZ", bg=RED, fg=WHITE, size=70, icon_name="cross_mark", k="black", alpha=a,
             scale=pop(t, t_kormaz - 0.08, 0.3))
    b = a * ramp(t, t_ustu + 0.1, t_ustu + 0.35)
    chip(L, 540, 1430, "Fırtınada camları kapat, metale dokunma", bg=WHITE, fg=INKC, size=34, icon_name="check_mark_button",
         k="black", alpha=b, scale=pop(t, t_ustu + 0.1, 0.3))


def cta_ui(L, t):
    if t < S12 - 0.05:
        return
    if t < S13:
        a = wnd(t, S12 - 0.05, S13 + 0.05, 0.2, 0.15)
        q = pop(t, S12, 0.35)
        txt(L, (540, 210), "SEN HİÇ FIRTINAYA", round(70 * q), WHITE, a, stroke=7)
        txt(L, (540, 320), "ARABADA YAKALANDIN MI?", round(70 * q), GOLD, a, stroke=7)
        if t >= t_yorum - 0.08:
            chip(L, 540, 1430, "Yorumlara yaz", bg=INKC, fg=WHITE, size=56, icon_name="speech_balloon", k="black", alpha=a,
                 scale=pop(t, t_yorum - 0.08, 0.35))
    else:
        a = ramp(t, S13, S13 + 0.25)
        txt(L, (540, 300), "Daha fazlası için", 64, WHITE, a, stroke=6)
        pulse = 1 + 0.045 * math.sin((t - S13) * 8) * ramp(t, S13 + 0.4, S13 + 0.7)
        chip(L, 540, 460, "TAKİP ET", bg=INKC, fg=WHITE, size=90, icon_name="bell", k="black", scale=pop(t, S13, 0.4) * pulse)


ROZ = Rozet()
OPN, RND = konusma(VOICE, FPS)


def background(t):
    if t < S2:
        return hook_scene(t)
    if t < S3:
        return legible(vertical("teker.mp4", t, S2, zoom=0.06, dur=2.0))
    if t < S4:  # gerçek yavaş çekim: öncüler -> çakış (beyaz) "delip geliyor" ile eş
        return legible(vertical("muurame.mp4", t, S3, zoom=0.05, off=MUUR_OFF))
    if t < S5:
        return legible(vertical("teker2.mp4", t, S4, zoom=0.07, dur=2.4))
    if t < S7:
        return car_panel(t)
    if t < S8:
        return faraday_scene(t)
    if t < S9:
        return bolts_scene(t)
    if t < S10:
        return sun_scene(t)
    if t < S10b:
        return legible(vertical("patla.mp4", t, S10, zoom=0.05, dur=2.0))
    if t < S11:
        return legible(vertical("elek.mp4", t, S10b, zoom=0.05, dur=1.3))
    if t < S12:
        return legible(vertical("cabrio.mp4", t, S11, zoom=0.04, dur=2.5))
    if t < S13:
        return legible(vertical("yagmur.mp4", t, S12, zoom=0.03, dur=3.0))
    return legible(vertical("muurame.mp4", t, S13, zoom=0.05, off=MUUR_END))


# Muurame klibi: çakış (beyaz) anı klip içinde ~3.17 sn -> "delip/geliyor" anına denk gelsin
MUUR_FLASH = 3.17
MUUR_OFF = MUUR_FLASH - (t_delip + 0.12 - S3)
MUUR_END = 3.8


class Vid(Video):
    def frame(self, t):
        bg = background(t)
        for c in CUTS:
            if 0 <= t - c < 0.14:
                bg = bg + 130 * (1 - (t - c) / 0.14)
        bg = grain(bg, t, 3.5)
        im = Image.fromarray(np.clip(bg, 0, 255).astype(np.uint8), "RGB").convert("RGBA")
        L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        hook_ui(L, t)
        tire_ui(L, t)
        km_ui(L, t)
        cm_ui(L, t)
        shell_ui(L, t)
        flow_ui(L, t)
        far_ui(L, t)
        volt_ui(L, t)
        sun_ui(L, t)
        damage_ui(L, t)
        cabrio_ui(L, t)
        cta_ui(L, t)
        im.alpha_composite(L)
        brand(im, 540, 62, size=34)
        C = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        captions(C, self.groups, t)
        im.alpha_composite(C)
        i = min(len(OPN) - 1, int(t * FPS))
        ROZ.draw(im, t, float(OPN[i]))
        return im.convert("RGB")


# ---------------- ses: gerçek gök gürültüsü + elektrik çıtırtısı + yağmur + müzik ----------------
SR = 44100


def _load(path, af=None, ss=0.0, dur=None):
    cmd = ["ffmpeg", "-v", "error", "-ss", f"{ss:.3f}", "-i", str(path)]
    if dur:
        cmd += ["-t", f"{dur:.3f}"]
    if af:
        cmd += ["-af", af]
    cmd += ["-ac", "1", "-ar", str(SR), "-f", "f32le", "-"]
    return np.frombuffer(subprocess.run(cmd, capture_output=True, check=True).stdout, np.float32).copy()


def _place(mix, y, t0, gain=1.0):
    i = int(t0 * SR)
    j = min(len(mix), i + len(y))
    if j > i:
        mix[i:j] += y[:j - i] * gain


def _norm(y, peak):
    return y / (np.abs(y).max() + 1e-9) * peak


def thunder(src, ss, dur, peak, lp_after=0.45):
    """çatırtı tam bant, devamındaki gürleme alçak geçiren ile (konuşmayı örtmesin)"""
    full = _load(src, None, ss, dur)
    low = _load(src, "lowpass=f=700", ss, dur)
    n = len(full)
    k = np.clip((np.arange(n) / SR - lp_after) / 0.35, 0, 1)
    y = full * (1 - k) + low * k * 0.9
    fade = np.clip((dur - np.arange(n) / SR) / 1.6, 0, 1) ** 1.5
    return _norm(y * fade, peak)


def crackle(dur, dens=60, peak=0.25, seed=1):
    """elektrik çıtırtısı: rastgele kısa darbeler + 100 Hz vızıltı"""
    rng = np.random.default_rng(seed)
    n = int(dur * SR)
    y = np.zeros(n, np.float32)
    for _ in range(int(dur * dens)):
        i = rng.integers(0, n - 400)
        L = rng.integers(40, 380)
        y[i:i + L] += rng.normal(0, 1, L) * np.exp(-np.arange(L) / (L / 4)) * rng.uniform(0.3, 1)
    tt = np.arange(n) / SR
    hum = (np.sign(np.sin(2 * np.pi * 100 * tt)) * 0.25 + np.sin(2 * np.pi * 200 * tt) * 0.15) * (0.5 + 0.5 * np.sin(2 * np.pi * 7 * tt))
    y = y + hum * 0.35
    env = np.clip(tt / 0.15, 0, 1) * np.clip((dur - tt) / 0.3, 0, 1)
    return _norm(y * env, peak)


def rain(dur, peak=0.05, seed=2):
    rng = np.random.default_rng(seed)
    n = int(dur * SR)
    w = rng.normal(0, 1, n).astype(np.float32)
    b = np.convolve(w, np.ones(3) / 3, mode="same") - np.convolve(w, np.ones(40) / 40, mode="same")
    drops = np.zeros(n, np.float32)
    for _ in range(int(dur * 25)):
        i = rng.integers(0, n - 300)
        drops[i:i + 300] += rng.normal(0, 1, 300) * np.exp(-np.arange(300) / 40) * rng.uniform(0.2, 1)
    y = b + drops * 0.6
    tt = np.arange(n) / SR
    y *= 0.8 + 0.2 * np.sin(2 * np.pi * 0.13 * tt)
    return _norm(y, peak)


def make_audio():
    CM = WORK / "cm"
    ev = [(c, "whoosh") for c in CUTS]
    ev += [(t_icer - 0.04, "pop"), (t_evet - 0.08, "ding"), (t_lastikler - 0.08, "pop"), (t_lastikler + 0.35, "pop"),
           (t_km - 0.08, "pop"), (S4, "pop"), (t_durd - 0.08, "pop"), (t_metal - 0.08, "tink"), (S6, "pop"),
           (t_lastikl - 0.1, "pop"), (t_sen - 0.08, "ding"), (t_far - 0.1, "pop"), (t_volt - 0.1, "pop"),
           (t_30 - 0.05, "pop"), (t_5 - 0.08, "ding"), (t_lastik2 - 0.08, "pop"), (S10b, "pop"), (S11, "pop"),
           (t_kormaz - 0.08, "pop"), (t_yorum - 0.08, "pop"), (S13, "pop")]
    at.sfx(str(WORK / "sfx_ev.wav"), TOTAL, ev)
    mix = _load(WORK / "sfx_ev.wav")
    mix = np.concatenate([mix, np.zeros(max(0, int(TOTAL * SR) - len(mix)), np.float32)])[:int(TOTAL * SR)]
    # gerçek gök gürültüleri (Richard Humphries, CC BY)
    _place(mix, thunder(CM / "th_nosf.wav", 3.22, 5.0, 0.62, 0.35), 0.0)
    t_flash = t_delip + 0.12
    _place(mix, thunder(CM / "th_rhum.ogg", 4.72, 4.2, 0.5), t_flash - 0.08)
    _place(mix, thunder(CM / "th_rhum.ogg", 17.22, 4.0, 0.42), t_300 - 0.1)
    # akım ve Faraday çıtırtıları
    _place(mix, crackle(t_sen + 0.4 - t_akim, 70, 0.09, 3), t_akim)
    _place(mix, crackle(0.5, 260, 0.22, 4), t_yere - 0.05)
    _place(mix, crackle(S8 - S7, 90, 0.09, 5), S7)
    # yağmur yatağı
    _place(mix, rain(TOTAL, 0.035), 0.0)
    at._write(str(WORK / "sfx.wav"), mix)
    # müzik (yapay zekâ, telifsiz): vuruşlar sahne geçişlerine denk gelsin diye 0.1 sn gecikme
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(WORK / "muzik_ai.wav"), "-af",
                    "adelay=100,acompressor=threshold=-26dB:ratio=3:attack=15:release=250:makeup=4,"
                    f"loudnorm=I=-20:TP=-2,atrim=0:{TOTAL:.3f},afade=t=in:d=0.1,afade=t=out:st={TOTAL - 0.7:.3f}:d=0.7",
                    "-ar", "44100", "-ac", "1", str(WORK / "music.wav")], check=True)
    at.final_mix(str(VOICE), str(WORK / "music.wav"), str(WORK / "sfx.wav"), str(WORK / "mix.m4a"))
    print("ses tamam", flush=True)


if __name__ == "__main__":
    mode = sys.argv[2] if len(sys.argv) > 2 else "render"
    v = Vid([{"start": 0, "end": TOTAL, "draw": lambda *a: None}], words, "", TOTAL, bg=None)
    print("TOTAL", TOTAL, "cuts", [round(c, 2) for c in CUTS], "muur_off", round(MUUR_OFF, 2), flush=True)
    if mode == "frames":
        (WORK / "test").mkdir(exist_ok=True)
        for tt in [float(x) for x in sys.argv[3].split(",")]:
            v.frame(tt).save(WORK / "test" / f"fr_{tt:05.2f}.jpg", quality=90)
    elif mode == "ses":
        make_audio()
    else:
        if not (WORK / "mix.m4a").exists():
            make_audio()
        v.render(str(WORK / "mix.m4a"), str(WORK / "video.mp4"))
        print("render bitti", TOTAL, flush=True)
