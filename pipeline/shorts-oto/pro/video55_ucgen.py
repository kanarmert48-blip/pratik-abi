"""55. video (2K Shorts, ~17 sn): Bu şekilde kaç üçgen var? 7 sn süre, cevap (13) verilmez, yorumlara yazdırılır.
Arka plan Gemini sınıf/kara tahta görseli, şekil tahtaya tebeşirle çizilir.
Kullanım: python3 video55_ucgen.py <WORK> [frames t1,t2,... | ses | render]
WORK/voice_cut.wav + marks.json + muzik.wav gerekir."""
import os
os.environ.setdefault("PA_SCALE", str(4 / 3))
import json, math, random, subprocess, sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from engine import *  # noqa
from PIL import ImageChops
from pa_ui import put_word, txt, pop
import audio_tools as at
from abi_yuz import konusma
from rozet import Rozet

WORK = Path(sys.argv[1])
VOICE = WORK / "voice_cut.wav"
MK = json.loads((WORK / "marks.json").read_text())
TOTAL = round(at.duration(str(VOICE)), 3)

GOLD = (255, 204, 70)
CYAN = (60, 230, 255)
PINK = (255, 80, 190)
RED = (255, 70, 70)
INKC = (20, 18, 40)


def ramp(t, a, b):
    return eio(clamp((t - a) / max(1e-6, b - a)))


# ---- şekil: kara tahtada 3 sıralı üçgen ızgara (hepsi üçgen, toplam 13) ----
IMG = Path(__file__).resolve().parent / "v55img"
SC = 1080 / 768
_t = Image.open(IMG / "tahta.jpg").convert("RGB")
_t = _t.resize((W, round(_t.height * W / _t.width)), Image.LANCZOS)
OFF = (_t.height - H) // 2
BG = _t.crop((0, OFF, W, OFF + H)).convert("RGBA")
OFFU = OFF / u(1)
_g = np.zeros((H, W), np.float32)
_hh = round(u(520))
_g[:_hh] = np.linspace(0.78, 0, _hh)[:, None] ** 1.2
TOPSHADE = Image.new("RGBA", (W, H), (14, 10, 40, 0))
TOPSHADE.putalpha(Image.fromarray((_g * 255).astype(np.uint8)))
BG.alpha_composite(TOPSHADE)
AX, AY = 540, 650
BY, BX0, BX1 = 1070, 225, 855
N3 = 3


def P(i, j):
    """i: satır (0 tepe .. 3 taban), j: o satırdaki nokta (0..i)."""
    y = AY + (BY - AY) * i / N3
    xl = AX + (BX0 - AX) * i / N3
    xr = AX + (BX1 - AX) * i / N3
    x = xl if i == 0 else xl + (xr - xl) * j / i
    return x, y


SEGS = []
for i in range(1, N3 + 1):
    SEGS.append((P(i, 0), P(i, i)))                 # yatay
for j in range(N3 + 1):
    SEGS.append((P(N3 - j, 0) if False else P(j, 0), P(N3, N3 - j) if False else P(N3, j)))  # sol-alt yönlü
for j in range(N3 + 1):
    SEGS.append((P(j, j), P(N3, N3 - (N3 - j)) if False else P(N3, j)))
SEGS = []
for k in range(N3 + 1):
    SEGS.append((P(k, 0), P(k, k)))                   # yatay çizgiler (k=0 nokta)
    SEGS.append((P(k, 0), P(N3, N3 - k)))             # sol kenara paralel olmayan: sağa inen
    SEGS.append((P(k, k), P(N3, k)))                  # sola inen
SEGS = [s for s in SEGS if s[0] != s[1]]


def chalk_layer(width, blur, alpha):
    m = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(m)
    w = round(u(width))
    for (x0, y0), (x1, y1) in SEGS:
        d.line([u(x0), u(y0), u(x1), u(y1)], fill=255, width=w)
        for x, y in ((x0, y0), (x1, y1)):
            d.ellipse([u(x) - w / 2, u(y) - w / 2, u(x) + w / 2, u(y) + w / 2], fill=255)
    if blur:
        m = m.filter(ImageFilter.GaussianBlur(u(blur)))
    a = np.asarray(m, np.float32) / 255
    rng = np.random.default_rng(55)
    noise = rng.uniform(0.55, 1.0, a.shape).astype(np.float32)     # tebeşir dokusu
    a = a * (noise if not blur else 1.0) * alpha
    im = Image.new("RGBA", (W, H), (245, 245, 235, 0))
    im.putalpha(Image.fromarray((a * 255).clip(0, 255).astype(np.uint8)))
    return im


CHALK = chalk_layer(9, 0, 1.0)
CHALK_GLOW = chalk_layer(16, 6, 0.35)
REVEAL_ORDER = sorted(range(len(SEGS)), key=lambda k: (SEGS[k][0][1] + SEGS[k][1][1]))


def draw_in(t):
    """Çizgiler 0.1-0.9 sn arasında soldan sağa açılan maske ile belirir."""
    q = ramp(t, 0.1, 0.9)
    if q >= 1:
        return CHALK, CHALK_GLOW
    m = Image.new("L", (W, H), 0)
    ImageDraw.Draw(m).rectangle([0, 0, round(u(BX0 - 20 + (BX1 - BX0 + 40) * q)), H], fill=255)
    a1, a2 = CHALK.copy(), CHALK_GLOW.copy()
    a1.putalpha(ImageChops.multiply(a1.getchannel("A"), m))
    a2.putalpha(ImageChops.multiply(a2.getchannel("A"), m))
    return a1, a2


random.seed(55)
DUST = [(random.uniform(200, 880), random.uniform(620, 1100), random.uniform(2, 4), random.uniform(0, 6.28)) for _ in range(18)]


def background(t):
    im = BG.copy()
    d = ImageDraw.Draw(im)
    for x, y, r, ph in DUST:                      # tahtada uçuşan tebeşir tozu
        a = max(0.0, math.sin(t * 1.7 + ph))
        yy2 = y - 8 * math.sin(t * 0.6 + ph)
        if a > 0.1:
            d.ellipse([u(x - r), u(yy2 - r), u(x + r), u(yy2 + r)], fill=(255, 255, 255, int(70 * a)))
    return im


def timer(L, t):
    d = ImageDraw.Draw(L)
    cx, cy, r = 540, 430, 62
    q = clamp((t - MK["t0"]) / MK["dur"])
    left = MK["dur"] * (1 - q)
    n = max(0, int(math.ceil(left - 1e-6)))
    hot = t >= MK["t0"] and left <= 3.0 and q < 1
    col = RED if hot else GOLD
    bx = [u(cx - r), u(cy - r), u(cx + r), u(cy + r)]
    d.ellipse(bx, fill=(10, 8, 30, 200), outline=(255, 255, 255, 50), width=round(u(12)))
    if q < 1:
        d.arc(bx, -90 + 360 * q, 270, fill=col + (255,), width=round(u(12)))
    s = 1 + 0.2 * max(0.0, 1 - ((t - MK["t0"]) % 1.0) / 0.25) if MK["t0"] <= t < MK["tend"] else 1.0
    txt(L, (cx, cy), str(n if t >= MK["t0"] else int(MK["dur"])), round(66 * s), WHITE, 1.0, k="black", stroke=5)


class Vid(Video):
    def frame(self, t):
        i = min(len(OPN) - 1, int(t * FPS))
        im = background(t)
        L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        # şekil: tebeşirle çizilir
        c1, c2 = draw_in(t)
        im.alpha_composite(c2)
        im.alpha_composite(c1)
        if t < MK["tC"] - 0.05:
            q = pop(t, 0.0, 0.45)
            txt(L, (540, 150), "BU ŞEKİLDE", round(56 * q), WHITE, 1.0, stroke=6)
            put_word(L, "KAÇ ÜÇGEN VAR?", GOLD, 540, 250, max(8, round(98 * q)), alpha=1.0, glow=0.55)
            if t >= MK["dikkat"] - 0.05:
                chip(L, 540, 1230, "DİKKATLİ SAY!", bg=PINK, fg=WHITE, size=50, k="black",
                     icon_name="eyes", scale=pop(t, MK["dikkat"] - 0.05, 0.35)) if t < MK["t0"] else None
            timer(L, t) if t >= MK["t0"] - 0.3 else None
        else:
            q = pop(t, MK["tC"] - 0.05, 0.4)
            txt(L, (540, 150), "SÜRE BİTTİ!", round(56 * q), WHITE, 1.0, stroke=6)
            put_word(L, "KAÇ TANE BULDUN?", GOLD, 540, 250, max(8, round(88 * q)), alpha=1.0, glow=0.55)
            if t >= MK["yor"] - 0.1:
                pulse = 1 + 0.04 * math.sin((t - MK["yor"]) * 8)
                chip(L, 600, 1230, "Cevabını yorumlara yaz!", bg=GOLD, fg=INKC, size=52, icon_name="speech_balloon",
                     k="black", scale=pop(t, MK["yor"] - 0.1, 0.35) * pulse)
        im.alpha_composite(L)
        brand(im, 540, 62, size=34)
        ROZ.draw(im, t, float(OPN[i]))
        return im.convert("RGB")


ROZ = Rozet(cx=150, cy=1745)
OPN, RND = konusma(VOICE, FPS)
VID = Vid([{"start": 0, "end": TOTAL, "draw": lambda *a: None}], [], "", TOTAL, bg=None)


def make_audio():
    ev = [(0.0, "whoosh"), (MK["dikkat"] - 0.05, "pop"), (MK["t0"] - 0.05, "pop")]
    ev += [(MK["t0"] + s, "tink") for s in range(int(MK["dur"]))]
    ev += [(MK["tC"] - 0.05, "whoosh"), (MK["yor"] - 0.1, "pop")]
    at.sfx(str(WORK / "sfx.wav"), TOTAL, ev)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-stream_loop", "3", "-i", str(WORK / "muzik.wav"), "-af",
                    f"atrim=0:{TOTAL:.3f},afade=t=in:d=0.3,afade=t=out:st={TOTAL - 0.6:.3f}:d=0.6",
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
