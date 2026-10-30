"""32. video (2K, ~38 sn): Kedi neden hep ayaklarının üstüne düşer? — tamamen gerçek görüntüler.
Görüntüler: É.-J. Marey 1894 kronofotoğrafları (kamu malı, Wikimedia Commons), Pixabay klipleri (kedi_yuksek_1, yavru_1,
yavru_2), "Salto - Cat Jump" (Record 124, CC BY 3.0, Wikimedia Commons).
Kullanım: python3 video32_kedi.py <WORK> [frames t1,t2,...]"""
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


t_ama, t_once, t_sonra, t_arka = T("ama"), T("Önce"), T("sonra"), T("Arka")
t_bu2, t_1894, t_foto = T("Bu", 1), T("1894'te"), T("fotoğraflarla")
t_daha, t_7, t_dusen, t_olur = T("Daha"), T("7"), T("düşen"), T("ölüyor.")
t_alcak, t_az = T("alçaktan"), T("az")
t_cunku, t_gevse, t_paras = T("Çünkü"), T("gevşeyip"), T("paraşüt")
t_ama2, t_kedinin, t_yorum, t_daha2 = T("Ama", 1), T("Kedinin"), T("Yorumlara"), T("Daha", 3)

S2, S3, S4, S5, S6, S7, S8 = t_once - 0.1, t_bu2 - 0.12, t_daha - 0.12, t_cunku - 0.12, t_ama2 - 0.12, t_kedinin - 0.12, t_daha2 - 0.1
CUTS = [S2, S3, S4, S5, S6, S7, S8]

GOLD = (255, 204, 70)
RED = (232, 40, 50)
INKC = (14, 16, 30)
GRN = (52, 200, 110)


def sm(x):
    return eio(clamp(x))


def ramp(t, a, b):
    return sm((t - a) / max(1e-6, b - a))


def wnd(t, a, b, fi=0.25, fo=0.25):
    return ramp(t, a, a + fi) * (1 - ramp(t, b - fo, b))


# ---------------- Marey kareleri ----------------
MAREY = np.asarray(Image.open(WORK / "foto" / "marey_1.jpg").convert("L"), np.float32)
FR = [(44, 195), (167, 192), (300, 192), (411, 190), (542, 192), (671, 205), (798, 218), (926, 224), (1055, 234),
      (1197, 245), (81, 531), (221, 545), (349, 560), (491, 580), (624, 603), (763, 611), (916, 623), (1059, 625),
      (1193, 632)]
CW, CH = 136, 160
SEP = np.array([1.0, 0.90, 0.74], np.float32)


@lru_cache(maxsize=40)
def mframe(i, w, h):
    cx, cy = FR[i]
    hh, ww = MAREY.shape
    x0, y0 = int(cx - CW / 2), int(cy - CH / 2)
    pad = np.pad(MAREY, 100, mode="edge")
    c = pad[y0 + 100:y0 + 100 + CH, x0 + 100:x0 + 100 + CW]
    c = cv2.bilateralFilter(c, 7, 40, 5)
    u_ = cv2.resize(c, (w, h), interpolation=cv2.INTER_LANCZOS4)
    g = cv2.GaussianBlur(u_, (0, 0), 2.0 * w / 816)
    u_ = np.clip(u_ + 0.75 * (u_ - g), 0, 255)
    u_ = np.clip((u_ - 12) * 1.12, 0, 255)
    return (u_[..., None] * SEP).astype(np.uint8)


def marey_at(f, w, h):
    f = clamp(f, 0, len(FR) - 1)
    i0 = int(math.floor(f))
    i1 = min(len(FR) - 1, i0 + 1)
    q = f - i0
    a = mframe(i0, w, h).astype(np.float32)
    if q > 0.02 and i1 != i0:
        b = mframe(i1, w, h).astype(np.float32)
        q = sm(clamp((q - 0.25) / 0.5))
        a = a * (1 - q) + b * q
    return a


def keys(t, ks):
    """parçalı doğrusal: [(t, değer)]"""
    if t <= ks[0][0]:
        return ks[0][1]
    for (a, va), (b, vb) in zip(ks, ks[1:]):
        if a <= t <= b:
            return va + (vb - va) * (t - a) / max(1e-6, b - a)
    return ks[-1][1]


def frame_index(t):
    if t < S2:
        return keys(t, [(0.0, 1.0), (1.35, 2.6), (2.75, 10.0), (3.45, 18.0)])
    return keys(t, [(S2, 0.0), (S2 + 0.25, 1.0), (t_sonra - 0.1, 4.0), (t_arka - 0.15, 8.2), (S3 - 0.5, 12.5), (S3, 13.0)])


RNG = np.random.default_rng(32)
GRAIN = [cv2.resize(RNG.normal(0, 1, (H // 3, W // 3)).astype(np.float32), (W, H), interpolation=cv2.INTER_LINEAR)
         for _ in range(6)]
YY, XX = np.mgrid[0:H, 0:W].astype(np.float32)
VIG = np.clip(1 - 0.5 * (((XX - W / 2) / (W * 0.65)) ** 2 + ((YY - H * 0.47) / (H * 0.58)) ** 2), 0.3, 1)[..., None]


def paste(dst, src, cx, cy):
    h, w = src.shape[:2]
    x0, y0 = int(round(cx - w / 2)), int(round(cy - h / 2))
    X0, Y0, X1, Y1 = max(0, x0), max(0, y0), min(W, x0 + w), min(H, y0 + h)
    if X0 < X1 and Y0 < Y1:
        dst[Y0:Y1, X0:X1] = src[Y0 - y0:Y1 - y0, X0 - x0:X1 - x0]
    return x0, y0, w, h


def archive_scene(t):
    """S1 + S2: Marey viewer (+ S2'de film şeridi)"""
    f = frame_index(t)
    k = ramp(t, S2 - 0.05, S2 + 0.35)            # S2'ye geçerken pencere küçülür
    vw = 960 - 220 * k
    vh = vw / 0.85
    vcy = 905 - 170 * k
    pw, ph = int(u(vw)), int(u(vh))
    img = marey_at(f, pw, ph)
    # arka plan: aynı karenin büyütülmüş, bulanık, koyu hali
    bg = cv2.resize(img, (W // 6, int(W / 6 * ph / pw)), interpolation=cv2.INTER_AREA)
    bg = cv2.resize(bg, (W, int(W * ph / pw)), interpolation=cv2.INTER_LINEAR)
    bg = cv2.GaussianBlur(bg, (0, 0), u(30)) * 0.33
    out = np.zeros((H, W, 3), np.float32)
    paste(out, bg[:min(H, bg.shape[0])], W / 2, H / 2)
    flick = 1 + 0.03 * math.sin(t * 27) + 0.02 * math.sin(t * 71)
    x0, y0, w, h = paste(out, img * flick, u(540), u(vcy))
    cv2.rectangle(out, (x0 - 3, y0 - 3), (x0 + w + 2, y0 + h + 2), (240, 222, 180), max(2, int(u(4))))
    # film şeridi (S2)
    if k > 0.01:
        sh = MAREY[60:300]
        sw = int(u(1040))
        shh = int(sw * sh.shape[0] / sh.shape[1])
        strip = cv2.resize(sh, (sw, shh), interpolation=cv2.INTER_AREA)
        strip = (np.clip((strip - 12) * 1.1, 0, 255)[..., None] * SEP) * 0.92
        sy = u(1300)
        sx0, sy0, _, _ = paste(out, strip * k + out[int(sy - shh / 2):int(sy - shh / 2) + shh,
                                                  int(W / 2 - sw / 2):int(W / 2 - sw / 2) + sw] * (1 - k), W / 2, sy)
        # şeritte aktif kare
        if f < 9.6:
            s = sw / 1251
            cx = sx0 + FR[int(round(f))][0] * s
            bw = 120 * s
            a = k
            col = np.array(GOLD, np.float32)
            y_a, y_b = int(sy0 + 2), int(sy0 + shh - 2)
            xa, xb = int(cx - bw / 2), int(cx + bw / 2)
            th = max(3, int(u(5)))
            out[y_a:y_b, max(0, xa):max(0, xa) + th] = col * a + out[y_a:y_b, max(0, xa):max(0, xa) + th] * (1 - a)
            out[y_a:y_b, xb - th:xb] = col * a + out[y_a:y_b, xb - th:xb] * (1 - a)
            out[y_a:y_a + th, xa:xb] = col * a + out[y_a:y_a + th, xa:xb] * (1 - a)
            out[y_b - th:y_b, xa:xb] = col * a + out[y_b - th:y_b, xa:xb] * (1 - a)
    g = GRAIN[int(t * 24) % len(GRAIN)]
    out = out + g[..., None] * 7
    return out * VIG, (x0, y0, w, h)


@lru_cache(maxsize=2)
def page_img():
    im = Image.open(WORK / "foto" / "marey_3.png").convert("L")
    w = int(u(1000))
    im = im.resize((w, int(w * im.height / im.width)), Image.LANCZOS)
    a = np.asarray(im, np.float32)
    return (np.clip((a - 10) * 1.1, 0, 255)[..., None] * SEP)


def page_scene(t):
    p = page_img()
    q = clamp((t - S3) / (S4 - S3))
    z = 1.0 + 0.10 * q
    h, w = p.shape[:2]
    pz = cv2.resize(p, (int(w * z), int(h * z)), interpolation=cv2.INTER_LINEAR)
    out = np.zeros((H, W, 3), np.float32) + np.array([18, 14, 10], np.float32)
    cy = H / 2 + u(60) + (pz.shape[0] - H * 0.8) * (0.5 - q) * 0.5
    paste(out, pz, W / 2, cy)
    g = GRAIN[int(t * 24) % len(GRAIN)]
    return (out + g[..., None] * 6) * VIG


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


def clip(name, t, t0, speed=1.0):
    if name not in _CL:
        _CL[name] = Clip(name)
    return _CL[name].get(max(0, int((t - t0) * 30 * speed)))


def vertical(name, t, t0, zoom=0.03, grade=1.0):
    f = clip(name, t, t0)
    z = 1.0 + zoom * clamp((t - t0) / 6)
    if z > 1.001:
        M = np.float32([[z, 0, W / 2 * (1 - z)], [0, z, H / 2 * (1 - z)]])
        f = cv2.warpAffine(f, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    return f * grade


def square(name, t, t0):
    f = clip(name, t, t0)
    bg = cv2.resize(f, (W // 8, W // 8), interpolation=cv2.INTER_AREA)
    bg = cv2.resize(bg, (H, H), interpolation=cv2.INTER_LINEAR)
    bg = cv2.GaussianBlur(bg, (0, 0), u(24)) * 0.45
    out = np.zeros((H, W, 3), np.float32)
    paste(out, bg[:, (H - W) // 2:(H - W) // 2 + W], W / 2, H / 2)
    paste(out, f, W / 2, u(880))
    return out


TOP = np.clip((0.30 - YY / H) / 0.30, 0, 1)[..., None]
BOT = np.clip((YY / H - 0.70) / 0.30, 0, 1)[..., None]


def legible(img):
    """üst ve altta yazılar için hafif karartma"""
    return img * (1 - 0.5 * TOP) * (1 - 0.55 * BOT)


# ---------------- yazılar ----------------
def hook_ui(L, t, box):
    if t >= S2 + 0.2:
        return
    a = 1 - ramp(t, S2 - 0.1, S2 + 0.15)
    if t < t_ama - 0.05:
        p = 1 + 0.12 * (1 - pop(t, 0.0, 0.28))
        put_word(L, "SIRT ÜSTÜ", WHITE, 540, 190, round(118 * p), alpha=a, glow=0.3)
        put_word(L, "BIRAKILDI...", WHITE, 540, 310, round(96 * p), alpha=a, glow=0.3)
    else:
        q = pop(t, t_ama - 0.05, 0.32)
        put_word(L, "AMA AYAKLARININ", GOLD, 540, 190, max(8, round(96 * q)), alpha=a if q > 0.02 else 0, glow=0.4)
        put_word(L, "ÜSTÜNE İNECEK", GOLD, 540, 310, max(8, round(104 * q)), alpha=a if q > 0.02 else 0, glow=0.4)
        if t >= 3.0:
            put_icon(L, "face_with_open_mouth", 880, 1300, 200 * pop(t, 3.0, 0.35), alpha=a)
    chip(L, 540, 1460, "GERÇEK GÖRÜNTÜ • 1894", bg=RED, fg=WHITE, size=40, icon_name="camera_with_flash" if False else None,
         k="black", alpha=a, scale=1.0 if t > 0.05 else 0.9)


def steps_ui(L, t, box):
    if not (S2 <= t < S3 + 0.1):
        return
    a = wnd(t, S2, S3 + 0.1, 0.25, 0.2)
    chip(L, 540, 200, "YAVAŞ ÇEKİM", bg=WHITE, fg=INKC, size=40, icon_name="stopwatch", k="black", alpha=a,
         scale=pop(t, S2, 0.3))
    steps = [(t_once - 0.05, t_sonra - 0.1, "1", "BAŞINI ÇEVİRİR"), (t_sonra - 0.05, t_arka - 0.12, "2", "ÖN YARIYI DÖNDÜRÜR"),
             (t_arka - 0.05, S3, "3", "ARKA YARI PEŞİNDEN")]
    for t0, t1, n, s in steps:
        if t0 <= t < t1:
            b = wnd(t, t0, t1, 0.18, 0.15) * a
            q = pop(t, t0, 0.3)
            chip(L, 540, 330, f"{n} · {s}", bg=GOLD, fg=INKC, size=50, k="black", alpha=b, scale=q)


def page_ui(L, t):
    if not (S3 - 0.05 <= t < S4 + 0.1):
        return
    a = wnd(t, S3 - 0.05, S4 + 0.1, 0.2, 0.2)
    if t >= t_1894 - 0.1:
        q = pop(t, t_1894 - 0.1, 0.35)
        panel(L, 540, 250, 620, 200, scale=q, alpha=a, r=40)
        put_word(L, "1894", GOLD, 540, 232, max(8, round(120 * q)), alpha=a if q > 0.02 else 0, glow=0.45)
        txt(L, (540, 318), "Étienne-Jules Marey", round(36 * q), WHITE, a, k="xb")
    if 0 <= t - t_foto < 0.18:
        L.alpha_composite(Image.new("RGBA", L.size, (255, 255, 255, int(150 * (1 - (t - t_foto) / 0.18)))))


def study_ui(L, t):
    if not (S4 - 0.05 <= t < S5 + 0.1):
        return
    a = wnd(t, S4 - 0.05, S5 + 0.1, 0.2, 0.2)
    chip(L, 540, 200, "DAHA DA İLGİNCİ", bg=WHITE, fg=INKC, size=42, k="black", alpha=a, scale=pop(t, S4, 0.3))
    if t >= t_7 - 0.1:
        q = pop(t, t_7 - 0.1, 0.35)
        put_word(L, "7+ KAT", GOLD, 540, 360, max(8, round(150 * q)), alpha=a if q > 0.02 else 0, glow=0.45)
    if t >= t_dusen - 0.05:
        b = a * ramp(t, t_dusen - 0.05, t_dusen + 0.25)
        q = pop(t, t_dusen - 0.05, 0.35)
        panel(L, 540, 1250, 920, 300, scale=q, alpha=b, r=40)
        txt(L, (290, 1180), "7+ kat", 54, GOLD, b, k="black")
        c2 = b * ramp(t, t_alcak - 0.1, t_alcak + 0.15)
        txt(L, (290, 1310), "2–6. kat", 54, WHITE, c2, k="black")
        chip(L, 715, 1310, "DAHA ÇOK ÖLÜM", bg=RED, fg=WHITE, size=40, k="black", alpha=c2, scale=pop(t, t_alcak - 0.1, 0.3))
        c1 = b * ramp(t, t_az - 0.25, t_az)
        chip(L, 715, 1180, "DAHA AZ ÖLÜM", bg=GRN, fg=INKC, size=40, k="black", alpha=c1, scale=pop(t, t_az - 0.25, 0.3))
        txt(L, (540, 1435), "Araştırma: 1987, New York • 132 kedi", 30, (230, 230, 230), b, k="xb", stroke=3)


def para_ui(L, t):
    if not (S5 - 0.05 <= t < S6 + 0.1):
        return
    a = wnd(t, S5 - 0.05, S6 + 0.1, 0.2, 0.2)
    if t >= t_gevse - 0.1:
        chip(L, 540, 230, "GEVŞER", bg=WHITE, fg=INKC, size=52, k="black", alpha=a, scale=pop(t, t_gevse - 0.1, 0.3))
    if t >= t_paras - 0.1:
        q = pop(t, t_paras - 0.1, 0.35)
        put_word(L, "PARAŞÜT GİBİ", GOLD, 540, 1290, max(8, round(110 * q)), alpha=a if q > 0.02 else 0, glow=0.45)


def warn_ui(L, t):
    if not (S6 - 0.05 <= t < S7 + 0.1):
        return
    a = wnd(t, S6 - 0.05, S7 + 0.1, 0.2, 0.2)
    q = pop(t, S6, 0.35)
    put_icon(L, "warning", 540, 250, 170 * q, alpha=a)
    put_word(L, "SAKIN DENEME!", (255, 80, 80), 540, 420, max(8, round(120 * q)), alpha=a if q > 0.02 else 0, glow=0.4)
    b = a * ramp(t, S6 + 1.4, S6 + 1.7)
    chip(L, 540, 1440, "Balkonuna ve pencerene file tak", bg=WHITE, fg=INKC, size=42, icon_name="check_mark_button",
         k="black", alpha=b, scale=pop(t, S6 + 1.4, 0.3))


def cta_ui(L, t):
    if t < S7 - 0.05:
        return
    if t < S8:
        a = wnd(t, S7 - 0.05, S8 + 0.05, 0.2, 0.15)
        q = pop(t, S7, 0.35)
        txt(L, (540, 230), "KEDİNİN BAŞKA", round(84 * q), WHITE, a, stroke=7)
        txt(L, (540, 340), "SÜPER GÜCÜ?", round(110 * q), GOLD, a, stroke=7)
        if t >= t_yorum - 0.08:
            chip(L, 540, 1430, "Yorumlara yaz", bg=INKC, fg=WHITE, size=56, icon_name="speech_balloon", k="black", alpha=a,
                 scale=pop(t, t_yorum - 0.08, 0.35))
    else:
        a = ramp(t, S8, S8 + 0.25)
        txt(L, (540, 300), "Daha fazlası için", 64, WHITE, a, stroke=6)
        pulse = 1 + 0.045 * math.sin((t - S8) * 8) * ramp(t, S8 + 0.4, S8 + 0.7)
        chip(L, 540, 460, "TAKİP ET", bg=INKC, fg=WHITE, size=90, icon_name="bell", k="black", scale=pop(t, S8, 0.4) * pulse)


ROZ = Rozet()
OPN, RND = konusma(VOICE, FPS)


class Vid(Video):
    def frame(self, t):
        box = None
        if t < S3:
            bg, box = archive_scene(t)
        elif t < S4:
            bg = page_scene(t)
        elif t < S5:
            bg = legible(vertical("yuksekA.mp4", t, S4, zoom=0.05))
        elif t < S6:
            bg = legible(square("salto.mp4", t, S5))
        elif t < S7:
            bg = legible(vertical("yuksekB.mp4", t, S6, zoom=0.04))
        elif t < S8:
            bg = legible(vertical("yavru1.mp4", t, S7, zoom=0.04))
        else:
            bg = legible(vertical("yavru2.mp4", t, S8, zoom=0.03))
        for c in CUTS:
            if 0 <= t - c < 0.14:
                bg = bg + 130 * (1 - (t - c) / 0.14)
        im = Image.fromarray(np.clip(bg, 0, 255).astype(np.uint8), "RGB").convert("RGBA")
        L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        hook_ui(L, t, box)
        steps_ui(L, t, box)
        page_ui(L, t)
        study_ui(L, t)
        para_ui(L, t)
        warn_ui(L, t)
        cta_ui(L, t)
        im.alpha_composite(L)
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
    print("TOTAL", TOTAL, "cuts", [round(c, 2) for c in CUTS], flush=True)
    if mode == "frames":
        (WORK / "test").mkdir(exist_ok=True)
        for tt in [float(x) for x in sys.argv[3].split(",")]:
            v.frame(tt).save(WORK / "test" / f"fr_{tt:05.2f}.jpg", quality=90)
    else:
        sfx = [(0.02, "whoosh"), (t_ama - 0.05, "pop"), (3.0, "ding")]
        sfx += [(c, "whoosh") for c in CUTS]
        sfx += [(t_once - 0.05, "pop"), (t_sonra - 0.05, "pop"), (t_arka - 0.05, "pop"), (t_1894 - 0.1, "pop"),
                (t_foto, "tink"), (t_7 - 0.1, "pop"), (t_alcak - 0.1, "pop"), (t_az - 0.25, "ding"), (t_paras - 0.1, "pop"),
                (S6, "pop"), (t_yorum - 0.08, "pop"), (S8, "pop")]
        at.sfx(str(WORK / "sfx.wav"), TOTAL, sfx)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-stream_loop", "2", "-i", str(WORK / "muzik.wav"), "-af",
                        f"atrim=0:{TOTAL:.3f},afade=t=in:d=0.15,afade=t=out:st={TOTAL - 0.6:.3f}:d=0.6",
                        "-ar", "44100", "-ac", "1", str(WORK / "music.wav")], check=True)
        at.final_mix(str(VOICE), str(WORK / "music.wav"), str(WORK / "sfx.wav"), str(WORK / "mix.m4a"))
        v.render(str(WORK / "mix.m4a"), str(WORK / "video.mp4"))
        print("render bitti", TOTAL, flush=True)
