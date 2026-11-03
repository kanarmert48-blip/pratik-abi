"""40. video (2K, ~61 sn): Bu elbise ne renk? (elbise illüzyonu, kendi fotoğrafımızla)
Kullanım: python3 video39_thatcher.py <WORK> [frames t1,t2,... | ses | render]"""
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



t_mavi, t_beyaz, t_ilk, t_2015, t_milyon = T("Mavi"), T("beyaz"), T("İlk"), T("2015'te"), T("Milyonlarca")
t_o, t_peki, t_cunku, t_golge, t_beyaz2 = T("O"), T("Peki"), T("Çünkü"), T("Elbisenin", 1), T("beyaz", 1)
t_sari, t_mavi3, t_13, t_erken, t_gece = T("Sarı"), T("mavi", 2), T("13.000"), T("erken"), T("gece")
t_bu, t_peki2, t_yorum, t_daha = T("Bu", 1), T("Peki", 1), T("Yorumlara"), T("Daha", 1)
CUTS = [t_2015 - 0.1, t_peki - 0.1, t_golge - 0.1, t_sari - 0.1, t_13 - 0.1, t_peki2 - 0.1]
GOLD = (255, 204, 70)
INKC = (14, 16, 30)
BLUE = (70, 110, 230)


def sm(x):
    return eio(clamp(x))


def ramp(t, a, b):
    return sm((t - a) / max(1e-6, b - a))


def wnd(t, a, b, fi=0.2, fo=0.2):
    return ramp(t, a, a + fi) * (1 - ramp(t, b - fo, b))


DW = int(u(690))


def load(name):
    im = Image.open(WORK / name).convert("RGB")
    h = int(DW * im.height / im.width)
    a = im.resize((DW, h), Image.LANCZOS).convert("RGBA")
    m = Image.new("L", (DW, h), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, DW - 1, h - 1], radius=int(u(40)), fill=255)
    a.putalpha(m)
    return a


IM_E, IM_W, IM_B = load("elbise.jpg"), load("wg.jpg"), load("bb.jpg")
BG = np.zeros((H, W, 3), np.float32)
_yy, _xx = np.mgrid[0:H, 0:W].astype(np.float32)
_r = np.sqrt(((_xx - W / 2) / W) ** 2 + ((_yy - H * 0.4) / H) ** 2)
for c, (a, b) in enumerate(zip((34, 30, 52), (10, 10, 18))):
    BG[..., c] = b + (a - b) * np.clip(1 - _r * 1.5, 0, 1) ** 1.4
BGIMG = Image.fromarray(BG.astype(np.uint8)).convert("RGBA")
del _yy, _xx, _r
CY = u(880)


def put_img(im, f, alpha=1.0, scale=1.0):
    if scale != 1.0:
        f = f.resize((int(f.width * scale), int(f.height * scale)), Image.BICUBIC)
    if alpha < 0.999:
        f = set_alpha(f, alpha)
    sh = Image.new("RGBA", f.size, (0, 0, 0, 0))
    sh.putalpha(f.getchannel("A").point(lambda v: int(v * 0.5)))
    sh = sh.filter(ImageFilter.GaussianBlur(u(20)))
    x, y = int(W / 2 - f.width / 2), int(CY - f.height / 2)
    im.alpha_composite(sh, (x, y + int(u(16))))
    im.alpha_composite(f, (x, y))


def scene(im, t):
    sc = 1.0 + 0.04 * ramp(t, 0, t_2015)
    put_img(im, IM_E, 1.0, sc)
    kw = ramp(t, t_golge + 0.6, t_golge + 1.6) * (1 - ramp(t, t_sari - 0.2, t_sari + 0.4))
    kb = ramp(t, t_sari + 0.3, t_sari + 1.3) * (1 - ramp(t, t_13 - 0.3, t_13 + 0.3))
    if kw > 0.01:
        put_img(im, IM_W, kw, sc)
    if kb > 0.01:
        put_img(im, IM_B, kb, sc)
    # ışık ipucu: gölge (mavi) / lamba (sarı) kenar parlaması
    for k, col in ((wnd(t, t_golge, t_sari, 0.5, 0.4), (90, 130, 255)), (wnd(t, t_sari, t_13, 0.5, 0.4), (255, 200, 80))):
        if k > 0.01:
            g = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            d = ImageDraw.Draw(g)
            d.ellipse([-W * 0.3, -H * 0.15, W * 1.3, H * 0.25], fill=col + (int(110 * k),))
            im.alpha_composite(g.filter(ImageFilter.GaussianBlur(u(120))))
    return None


def swatch(L, x, y, col, lab, a, q):
    if a <= 0.01:
        return
    lay = Image.new("RGBA", L.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    d.rounded_rectangle([u(x - 200), u(y - 56), u(x + 200), u(y + 56)], radius=u(56), fill=(255, 255, 255, int(240 * a)))
    d.ellipse([u(x - 180), u(y - 40), u(x - 100), u(y + 40)], fill=col + (int(255 * a),))
    L.alpha_composite(lay)
    txt(L, (x + 40, y), lab, round(40 * q), INKC, a, k="black")


def ui(L, t, st):
    if t < t_2015 - 0.1:
        a = 1 - ramp(t, t_2015 - 0.3, t_2015 - 0.1)
        q = 1 + 0.1 * (1 - pop(t, 0.0, 0.28))
        put_word(L, "BU ELBİSE", WHITE, 540, 150, round(96 * q), alpha=a, glow=0.3)
        put_word(L, "NE RENK?", GOLD, 540, 272, round(120 * q), alpha=a, glow=0.45)
        if t >= t_mavi - 0.1:
            chip(L, 330, 1440, "MAVİ-SİYAH", bg=BLUE, fg=WHITE, size=50, k="black", alpha=a, scale=pop(t, t_mavi - 0.1, 0.3))
        if t >= t_beyaz - 0.1:
            chip(L, 760, 1440, "BEYAZ-ALTIN", bg=GOLD, fg=INKC, size=50, k="black", alpha=a, scale=pop(t, t_beyaz - 0.1, 0.3))
        if t >= t_ilk - 0.1:
            chip(L, 660, 1560, "İlk gördüğünü yaz", bg=INKC, fg=WHITE, size=46, icon_name="speech_balloon", k="black",
                 alpha=a, scale=pop(t, t_ilk - 0.1, 0.3))
    elif t < t_peki - 0.1:
        a = wnd(t, t_2015 - 0.1, t_peki, 0.2, 0.15)
        q = pop(t, t_2015 - 0.1, 0.35)
        panel(L, 540, 220, 860, 240, scale=q, alpha=a, r=40)
        put_word(L, "2015", GOLD, 540, 185, max(8, round(90 * q)), alpha=a, glow=0.45)
        txt(L, (540, 282), "İnterneti ikiye bölen elbise", round(40 * q), WHITE, a, k="xb")
        if t >= t_o - 0.1:
            chip(L, 660, 1530, "Gerçek rengi: MAVİ-SİYAH", bg=BLUE, fg=WHITE, size=46, k="black", alpha=a,
                 scale=pop(t, t_o - 0.1, 0.3))
    elif t < t_golge - 0.1:
        a = wnd(t, t_peki - 0.1, t_golge, 0.2, 0.15)
        q = pop(t, t_peki - 0.1, 0.3)
        put_word(L, "NEDEN FARKLI", WHITE, 540, 150, max(8, round(90 * q)), alpha=a, glow=0.3)
        put_word(L, "GÖRÜYORUZ?", GOLD, 540, 272, max(8, round(104 * q)), alpha=a, glow=0.45)
        if t >= t_cunku - 0.1:
            q2 = pop(t, t_cunku - 0.1, 0.3)
            txt(L, (580, 1378), "Fotoğraftaki gerçek pikseller:", round(38 * q2), WHITE, a, k="xb")
            swatch(L, 390, 1445, (134, 148, 203), "lila-mavi", a, q2)
            swatch(L, 800, 1445, (108, 88, 52), "kahverengi", a, q2)
    elif t < t_sari - 0.1:
        a = wnd(t, t_golge - 0.1, t_sari, 0.2, 0.15)
        q = pop(t, t_golge - 0.1, 0.3)
        put_word(L, "GÖLGE SANIRSAN", (150, 180, 255), 540, 150, max(8, round(86 * q)), alpha=a, glow=0.3)
        q2 = pop(t, t_beyaz2 - 0.1, 0.35) if t >= t_beyaz2 - 0.1 else 0
        if q2 > 0.02:
            put_word(L, "BEYAZ-ALTIN", GOLD, 540, 272, max(8, round(110 * q2)), alpha=a, glow=0.5)
        chip(L, 660, 1530, "Beyin maviyi siler", bg=WHITE, fg=INKC, size=46, icon_name="thinking_face", k="black",
             alpha=a, scale=pop(t, t_golge + 1.5, 0.3) if t > t_golge + 1.5 else 0.01)
    elif t < t_13 - 0.1:
        a = wnd(t, t_sari - 0.1, t_13, 0.2, 0.15)
        q = pop(t, t_sari - 0.1, 0.3)
        put_word(L, "SARI LAMBA SANIRSAN", (255, 210, 120), 540, 150, max(8, round(76 * q)), alpha=a, glow=0.3)
        q2 = pop(t, t_mavi3 - 0.1, 0.35) if t >= t_mavi3 - 0.1 else 0
        if q2 > 0.02:
            put_word(L, "MAVİ-SİYAH", (110, 150, 255), 540, 272, max(8, round(110 * q2)), alpha=a, glow=0.5)
        chip(L, 660, 1530, "Beyin sarıyı siler", bg=WHITE, fg=INKC, size=46, icon_name="thinking_face", k="black",
             alpha=a, scale=pop(t, t_sari + 1.5, 0.3) if t > t_sari + 1.5 else 0.01)
    elif t < t_peki2 - 0.1:
        a = wnd(t, t_13 - 0.1, t_peki2, 0.2, 0.15)
        q = pop(t, t_13 - 0.1, 0.35)
        panel(L, 540, 220, 860, 240, scale=q, alpha=a, r=40)
        put_word(L, "13.000 KİŞİ", GOLD, 540, 190, max(8, round(86 * q)), alpha=a, glow=0.45)
        txt(L, (540, 282), "Wallisch · Journal of Vision · 2017", round(34 * q), WHITE, a, k="xb")
        if t >= t_erken - 0.1 and t < t_bu - 0.1:
            chip(L, 660, 1440, "Erken kalkan → beyaz-altın", bg=GOLD, fg=INKC, size=44, k="black", alpha=a,
                 scale=pop(t, t_erken - 0.1, 0.3))
        if t >= t_gece - 0.1 and t < t_bu - 0.1:
            chip(L, 660, 1555, "Gece kuşu → mavi-siyah", bg=BLUE, fg=WHITE, size=44, k="black", alpha=a,
                 scale=pop(t, t_gece - 0.1, 0.3))
        if t >= t_bu - 0.1:
            chip(L, 660, 1530, "Bu elbise aynı renklerle hazırlandı", bg=WHITE, fg=INKC, size=40, k="black", alpha=a,
                 scale=pop(t, t_bu - 0.1, 0.3))
    elif t < t_daha - 0.1:
        a = wnd(t, t_peki2 - 0.1, t_daha, 0.2, 0.15)
        q = pop(t, t_peki2 - 0.1, 0.35)
        txt(L, (540, 160), "SEN NE", round(90 * q), WHITE, a, stroke=7)
        txt(L, (540, 272), "GÖRDÜN?", round(110 * q), GOLD, a, stroke=7)
        if t >= t_yorum - 0.08:
            chip(L, 660, 1530, "Yorumlara yaz", bg=INKC, fg=WHITE, size=56, icon_name="speech_balloon", k="black",
                 alpha=a, scale=pop(t, t_yorum - 0.08, 0.35))
    else:
        S9 = t_daha - 0.1
        a = ramp(t, S9, S9 + 0.25)
        txt(L, (540, 170), "Daha fazlası için", 64, WHITE, a, stroke=6)
        pulse = 1 + 0.045 * math.sin((t - S9) * 8) * ramp(t, S9 + 0.4, S9 + 0.7)
        chip(L, 540, 300, "TAKİP ET", bg=INKC, fg=WHITE, size=90, icon_name="bell", k="black", scale=pop(t, S9, 0.4) * pulse)


ROZ = Rozet()
OPN, RND = konusma(VOICE, FPS)


class Vid(Video):
    def frame(self, t):
        im = BGIMG.copy()
        st = scene(im, t)
        for c in CUTS:
            if 0 <= t - c < 0.12:
                im.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 255, int(70 * (1 - (t - c) / 0.12)))))
        L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ui(L, t, st)
        im.alpha_composite(L)
        brand(im, 540, 62, size=34)
        C = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        captions(C, self.groups, t, y=1680)
        im.alpha_composite(C)
        i = min(len(OPN) - 1, int(t * FPS))
        ROZ.draw(im, t, float(OPN[i]))
        return im.convert("RGB")


VID = Vid([{"start": 0, "end": TOTAL, "draw": lambda *a: None}], words, "", TOTAL, bg=None)


def make_audio():
    ev = [(c, "whoosh") for c in CUTS] + [(t_mavi - 0.1, "pop"), (t_beyaz - 0.1, "pop"), (t_ilk - 0.1, "pop"),
                                          (t_o - 0.1, "ding"), (t_cunku - 0.1, "pop"), (t_beyaz2 - 0.1, "ding"),
                                          (t_mavi3 - 0.1, "ding"), (t_erken - 0.1, "pop"), (t_gece - 0.1, "pop"),
                                          (t_bu - 0.1, "pop"), (t_yorum - 0.08, "pop"), (t_daha - 0.1, "pop")]
    at.sfx(str(WORK / "sfx.wav"), TOTAL, ev)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-stream_loop", "4", "-i", str(WORK / "muzik.wav"), "-af",
                    f"atrim=0:{TOTAL:.3f},afade=t=in:d=0.15,afade=t=out:st={TOTAL - 0.6:.3f}:d=0.6",
                    "-ar", "44100", "-ac", "1", str(WORK / "music.wav")], check=True)
    at.final_mix(str(VOICE), str(WORK / "music.wav"), str(WORK / "sfx.wav"), str(WORK / "mix.m4a"))


if __name__ == "__main__":
    mode = sys.argv[2] if len(sys.argv) > 2 else "render"
    print("TOTAL", TOTAL, flush=True)
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
