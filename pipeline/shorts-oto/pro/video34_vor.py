"""34. video (2K, ~35 sn): Başını salla okursun, telefonu salla okuyamazsın (vestibülo-oküler refleks) — izleyici deneyi.
Görüntüler: Pixabay klipleri, Unsplash (göz: Umesh Soni, kulak: Sam Badmaeva).
Kullanım: python3 video34_vor.py <WORK> [frames t1,t2,... | ses | render]"""
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


t_ok, t_simdi, t_tel1 = T("Okuyabiliyorsun"), T("Şimdi"), T("telefonu")
t_yazi, t_okunmaz, t_cunku, t_ic, t_haber = T("Yazı"), T("okunmaz"), T("Çünkü"), T("iç"), T("haber")
t_goz, t_ters, t_tel, t_yetis = T("Gözlerin de"), T("ters"), T("Telefon"), T("yetişemiyor")
t_bu, t_yur, t_sende, t_yorum, t_daha = T("Bu", 3), T("yürürken"), T("Sende"), T("Yorumlara"), T("Daha")
S2, S3, S4, S5, S6, S7, S8, S9 = t_simdi - 0.1, t_yazi - 0.1, t_cunku - 0.1, t_goz - 0.1, t_tel - 0.1, t_bu - 0.1, t_sende - 0.1, t_daha - 0.1
CUTS = [S2, S4, S5, S6, S7, S8, S9]

GOLD = (255, 204, 70)
RED = (232, 40, 50)
INKC = (14, 16, 30)
GRN = (52, 200, 110)


def sm(x):
    return eio(clamp(x))


def ramp(t, a, b):
    return sm((t - a) / max(1e-6, b - a))


def wnd(t, a, b, fi=0.2, fo=0.2):
    return ramp(t, a, a + fi) * (1 - ramp(t, b - fo, b))


YY, XX = np.mgrid[0:H, 0:W].astype(np.float32)
TOP = np.clip((0.32 - YY / H) / 0.32, 0, 1)[..., None]
BOT = np.clip((YY / H - 0.70) / 0.30, 0, 1)[..., None]


def legible(img, top=0.55, bot=0.55):
    return img * (1 - top * TOP) * (1 - bot * BOT)


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


def clip(name, t, t0, zoom=0.04, dur=4.0):
    if name not in _CL:
        _CL[name] = Clip(name)
    f = _CL[name].get(max(0, int((t - t0) * 30)))
    z = 1.0 + zoom * clamp((t - t0) / dur)
    M = np.float32([[z, 0, W / 2 * (1 - z)], [0, z, H / 2 * (1 - z)]])
    return cv2.warpAffine(f, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


def photo(path, t, t0, t1, z0, z1, cx=0.5, cy=0.5):
    if path not in _CL:
        im = cv2.cvtColor(cv2.imread(str(path)), cv2.COLOR_BGR2RGB).astype(np.float32)
        h, w = im.shape[:2]
        s = max(W / w, H / h)
        _CL[path] = cv2.resize(im, (int(w * s) + 2, int(h * s) + 2), interpolation=cv2.INTER_AREA)
    im = _CL[path]
    z = z0 + (z1 - z0) * sm((t - t0) / (t1 - t0))
    h, w = im.shape[:2]
    M = np.float32([[z, 0, W / 2 - cx * w * z], [0, z, H / 2 - cy * h * z]])
    return cv2.warpAffine(im, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


def blurred(img, k=0.35):
    sm_ = cv2.resize(img, (W // 8, H // 8), interpolation=cv2.INTER_AREA)
    return cv2.resize(cv2.GaussianBlur(sm_, (0, 0), 3), (W, H)) * k


def shake_x(img, amp, t, blur=0):
    dx = amp * math.sin(t * 2 * math.pi * 4.2)
    M = np.float32([[1, 0, dx], [0, 1, 0]])
    img = cv2.warpAffine(img, M, (W, H), borderMode=cv2.BORDER_REFLECT)
    if blur > 1:
        k = np.ones((1, int(blur)), np.float32) / int(blur)
        img = cv2.filter2D(img, -1, k)
    return img


# ---------------- test kartı ----------------
CARD_CY = 860


def card_layer(lines, t, scale=1.0):
    """beyaz kart + koyu büyük yazı (okuma testi)"""
    L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    cw, ch = 980, 120 + 128 * len(lines)
    x0, y0 = u(540 - cw / 2), u(CARD_CY - ch / 2)
    sh, pad = soft_shadow(round(u(cw)), round(u(ch)), round(u(44)), blur=round(u(28)), op=0.6)
    comp(L, sh, x0 - pad, y0 - pad + u(16))
    ImageDraw.Draw(L).rounded_rectangle([x0, y0, x0 + u(cw), y0 + u(ch)], radius=u(44), fill=(250, 248, 242, 255))
    for i, (s, col) in enumerate(lines):
        text_c(L, (540, CARD_CY - ch / 2 + 124 + 128 * i), s, "black", 80, col)
    if abs(scale - 1) > 0.003:
        L2 = L.resize((int(W * scale), int(H * scale)), Image.BICUBIC)
        L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        comp(L, L2, (W - L2.width) / 2, (H - L2.height) / 2 + u(CARD_CY - 960) * (1 - scale))
    return L


def card_text(t):
    if t < S2:
        return [("BU YAZIYI OKURKEN", INKC), ("BAŞINI SAĞA SOLA", INKC), ("SALLA", (210, 30, 40))]
    if t < S8:
        return [("ŞİMDİ BAŞINI", INKC), ("SABİT TUT VE", INKC), ("TELEFONU SALLA", (210, 30, 40))]
    return [("SENDE DE", INKC), ("OLDU MU?", (210, 30, 40))]


def test_bg(t):
    if t < S2:
        return blurred(clip("tel_adam.mp4", t, 0.0, 0.0), 0.45)
    if t < S4:
        return blurred(clip("tel_red.mp4", t, S2, 0.0), 0.45)
    return blurred(clip("tel_adam.mp4", t, S8, 0.0), 0.45)


ROZ = Rozet()
OPN, RND = konusma(VOICE, FPS)


def frame_img(t):
    on_card = t < S4 or t >= S8
    if on_card:
        bg = test_bg(t)
    elif t < S5:
        bg = legible(photo(WORK / "foto" / "ear.jpg", t, S4, S5, 1.0, 1.25, 0.5, 0.48))
    elif t < S6:
        bg = legible(photo(WORK / "foto" / "eye.jpg", t, S5, S6, 1.0, 1.18, 0.5, 0.5))
        # göz, başın tersine kayıyor gibi küçük yatay hareket
        bg = shake_x(bg, 18 * ramp(t, t_ters - 0.1, t_ters + 0.2), t)
    elif t < S7:
        f = clip("tel_kadin.mp4", t, S6, 0.04)
        a = ramp(t, S6 + 0.3, S6 + 0.7)
        bg = legible(shake_x(f, 70 * a, t, 1 + 34 * a))
    else:
        bg = legible(clip("yuru.mp4", t, S7, 0.03))
    for c in CUTS:
        if 0 <= t - c < 0.14:
            bg = bg + 120 * (1 - (t - c) / 0.14)
    im = Image.fromarray(np.clip(bg, 0, 255).astype(np.uint8), "RGB").convert("RGBA")
    L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    if on_card and t < S9:
        sc = 1.0 if t < 0.02 else 1 + 0.06 * (1 - pop(t, S2 if S2 <= t < S8 else (S8 if t >= S8 else 0), 0.35))
        cl = card_layer(card_text(t), t, sc if t > 0.02 else 1.0)
        if S3 <= t < S4:  # telefon sallanıyor: yazı okunmaz
            a = ramp(t, S3, S3 + 0.25)
            arr = np.asarray(cl).astype(np.float32)
            dx = 60 * a * math.sin(t * 2 * math.pi * 5)
            arr = cv2.warpAffine(arr, np.float32([[1, 0, dx], [0, 1, 0]]), (W, H))
            k = int(2 + 70 * a)
            arr = cv2.filter2D(arr, -1, np.ones((1, k), np.float32) / k)
            cl = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGBA")
        im.alpha_composite(cl)
    ui(L, t)
    im.alpha_composite(L)
    brand(im, 540, 62, size=34)
    C = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    captions(C, VID.groups, t)
    im.alpha_composite(C)
    i = min(len(OPN) - 1, int(t * FPS))
    ROZ.draw(im, t, float(OPN[i]))
    return im.convert("RGB")


def arrows(L, t, y, a, flip=False):
    sw = math.sin(t * 2 * math.pi * 1.6)
    put_icon(L, "left_arrow", 250 + 30 * sw, y, 120, alpha=a)
    put_icon(L, "left_arrow", 830 + 30 * sw, y, 120, alpha=a, rot=180)


def ui(L, t):
    if t < S2:
        chip(L, 540, 300, "DENE: BAŞINI SALLA", bg=GOLD, fg=INKC, size=52, k="black")
        arrows(L, t, 1300, 1.0)
        if t >= t_ok - 0.08:
            q = pop(t, t_ok - 0.08, 0.32)
            put_icon(L, "check_mark_button", 540, 1330, 170 * q)
            put_word(L, "OKUYABİLİYORSUN", GRN, 540, 470, max(8, round(86 * q)), alpha=1 if q > 0.02 else 0, glow=0.45)
    elif t < S4:
        a = wnd(t, S2, S4 + 0.1)
        chip(L, 540, 300, "ŞİMDİ TELEFONU SALLA", bg=GOLD, fg=INKC, size=52, k="black", alpha=a, scale=pop(t, S2, 0.3))
        sw = math.sin(t * 2 * math.pi * 3.0) * ramp(t, t_tel1, t_tel1 + 0.3)
        put_icon(L, "mobile_phone", 540 + 70 * sw, 1310, 170, alpha=a, rot=8 * sw)
        if t >= t_yazi - 0.08:
            q = pop(t, t_yazi - 0.08, 0.3)
            put_word(L, "OKUNMAZ OLDU", (255, 90, 90), 540, 470, max(8, round(100 * q)), alpha=a if q > 0.02 else 0, glow=0.45)
    elif t < S5:
        a = wnd(t, S4, S5 + 0.1)
        q = pop(t, S4, 0.32)
        put_word(L, "ÇÜNKÜ", WHITE, 540, 190, max(8, round(80 * q)), alpha=a if q > 0.02 else 0, glow=0.3)
        if t >= t_ic - 0.1:
            q2 = pop(t, t_ic - 0.1, 0.32)
            put_word(L, "İÇ KULAK", GOLD, 540, 320, max(8, round(140 * q2)), alpha=a if q2 > 0.02 else 0, glow=0.5)
        if t >= t_haber - 0.1:
            chip(L, 540, 1420, "Gözlere anında haber verir", bg=WHITE, fg=INKC, size=46, icon_name="eye", k="black",
                 alpha=a, scale=pop(t, t_haber - 0.1, 0.3))
    elif t < S6:
        a = wnd(t, S5, S6 + 0.1)
        q = pop(t, S5, 0.32)
        put_word(L, "GÖZLERİN", WHITE, 540, 190, max(8, round(86 * q)), alpha=a if q > 0.02 else 0, glow=0.3)
        if t >= t_ters - 0.1:
            q2 = pop(t, t_ters - 0.1, 0.32)
            put_word(L, "TERS YÖNE KAYAR", GOLD, 540, 320, max(8, round(104 * q2)), alpha=a if q2 > 0.02 else 0, glow=0.5)
            b = a * q2
            chip(L, 300, 1420, "BAŞ", bg=WHITE, fg=INKC, size=50, k="black", alpha=b)
            put_icon(L, "left_arrow", 450, 1420, 90, alpha=b, rot=180)
            chip(L, 780, 1420, "GÖZ", bg=GOLD, fg=INKC, size=50, k="black", alpha=b)
            put_icon(L, "left_arrow", 630, 1420, 90, alpha=b)
    elif t < S7:
        a = wnd(t, S6, S7 + 0.1)
        q = pop(t, S6, 0.32)
        put_word(L, "TELEFON SALLANINCA", WHITE, 540, 190, max(8, round(76 * q)), alpha=a if q > 0.02 else 0, glow=0.3)
        if t >= t_yetis - 0.1:
            q2 = pop(t, t_yetis - 0.1, 0.32)
            put_word(L, "GÖZ YETİŞEMEZ", (255, 90, 90), 540, 320, max(8, round(116 * q2)), alpha=a if q2 > 0.02 else 0, glow=0.5)
            put_icon(L, "cross_mark", 540, 1380, 170 * pop(t, t_yetis + 0.1, 0.3), alpha=a)
    elif t < S8:
        a = wnd(t, S7, S8 + 0.1)
        q = pop(t, S7, 0.32)
        put_word(L, "SÜPER HIZLI REFLEKS", GOLD, 540, 190, max(8, round(84 * q)), alpha=a if q > 0.02 else 0, glow=0.45)
        if t >= t_yur - 0.1:
            q2 = pop(t, t_yur - 0.1, 0.32)
            put_word(L, "YÜRÜRKEN BİLE", WHITE, 540, 320, max(8, round(96 * q2)), alpha=a if q2 > 0.02 else 0, glow=0.3)
            put_word(L, "DÜNYA SALLANMAZ", WHITE, 540, 440, max(8, round(96 * q2)), alpha=a if q2 > 0.02 else 0, glow=0.3)
    elif t < S9:
        a = wnd(t, S8, S9 + 0.05)
        if t >= t_yorum - 0.08:
            chip(L, 540, 1330, "Yorumlara yaz", bg=INKC, fg=WHITE, size=56, icon_name="speech_balloon", k="black", alpha=a,
                 scale=pop(t, t_yorum - 0.08, 0.35))
    else:
        a = ramp(t, S9, S9 + 0.25)
        txt(L, (540, 300), "Daha fazlası için", 64, WHITE, a, stroke=6)
        pulse = 1 + 0.045 * math.sin((t - S9) * 8) * ramp(t, S9 + 0.4, S9 + 0.7)
        chip(L, 540, 460, "TAKİP ET", bg=INKC, fg=WHITE, size=90, icon_name="bell", k="black", scale=pop(t, S9, 0.4) * pulse)


class Vid(Video):
    def frame(self, t):
        return frame_img(t)


VID = Vid([{"start": 0, "end": TOTAL, "draw": lambda *a: None}], words, "", TOTAL, bg=None)


def make_audio():
    ev = [(c, "whoosh") for c in CUTS] + [(t_ok - 0.08, "ding"), (t_yazi - 0.08, "pop"), (t_ic - 0.1, "pop"),
                                          (t_haber - 0.1, "pop"), (t_ters - 0.1, "pop"), (t_yetis - 0.1, "pop"),
                                          (t_yur - 0.1, "pop"), (t_yorum - 0.08, "pop"), (S9, "pop")]
    at.sfx(str(WORK / "sfx.wav"), TOTAL, ev)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-stream_loop", "2", "-i", str(WORK / "muzik.wav"), "-af",
                    f"atrim=0:{TOTAL:.3f},afade=t=in:d=0.15,afade=t=out:st={TOTAL - 0.6:.3f}:d=0.6",
                    "-ar", "44100", "-ac", "1", str(WORK / "music.wav")], check=True)
    at.final_mix(str(VOICE), str(WORK / "music.wav"), str(WORK / "sfx.wav"), str(WORK / "mix.m4a"))


if __name__ == "__main__":
    mode = sys.argv[2] if len(sys.argv) > 2 else "render"
    print("TOTAL", TOTAL, "cuts", [round(c, 2) for c in CUTS], flush=True)
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
