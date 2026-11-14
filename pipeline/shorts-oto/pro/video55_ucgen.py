"""55. video (2K Shorts, ~17 sn): Bu şekilde kaç üçgen var? 7 sn süre, cevap verilmez, yorumlara yazdırılır.
Neon çizgili şekil, cam kart, renkli ışık lekeleri.
Kullanım: python3 video55_ucgen.py <WORK> [frames t1,t2,... | ses | render]
WORK/voice_cut.wav + marks.json + muzik.wav gerekir."""
import os
os.environ.setdefault("PA_SCALE", str(4 / 3))
import json, math, random, subprocess, sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from engine import *  # noqa
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


# ---- şekil: tepeden 4 çizgi (2 kenar + 2 iç), 3 yatay (2 iç + taban) ----
AX, AY = 540, 470
BY, BX0, BX1 = 1400, 130, 950
FOOT = [BX0, BX0 + (BX1 - BX0) / 3, BX0 + 2 * (BX1 - BX0) / 3, BX1]
HF = [0.45, 0.72, 1.0]


def pt(line, h):
    f = HF[h]
    return AX + (FOOT[line] - AX) * f, AY + (BY - AY) * f


def grad_line_layer(width, blur):
    """Neon çizgiler: yukarıda camgöbeği, aşağıda pembe."""
    m = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(m)
    w = round(u(width))
    segs = [((AX, AY), (FOOT[k], BY)) for k in range(4)] + [(pt(0, h), pt(3, h)) for h in range(3)]
    for (x0, y0), (x1, y1) in segs:
        d.line([u(x0), u(y0), u(x1), u(y1)], fill=255, width=w)
        for x, y in ((x0, y0), (x1, y1)):
            d.ellipse([u(x) - w / 2, u(y) - w / 2, u(x) + w / 2, u(y) + w / 2], fill=255)
    if blur:
        m = m.filter(ImageFilter.GaussianBlur(u(blur)))
    yy = np.linspace(0, 1, H)[:, None, None]
    top, bot = np.array(CYAN, np.float32), np.array(PINK, np.float32)
    k = np.clip((yy - u(AY) / H) / ((u(BY) - u(AY)) / H), 0, 1)
    col = (top * (1 - k) + bot * k).astype(np.uint8)
    col = np.broadcast_to(col, (H, W, 3))
    im = Image.fromarray(np.ascontiguousarray(col)).convert("RGBA")
    a = np.asarray(m, np.float32)
    if blur:
        a = np.clip(a * 2.2, 0, 255)
    im.putalpha(Image.fromarray(a.astype(np.uint8)))
    return im


def cells_layer():
    """Hücrelere çok hafif renk (cevabı vermez, sadece güzellik)."""
    L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(L)
    cols = [(60, 230, 255), (150, 110, 255), (255, 80, 190)]
    for h in range(3):
        for k in range(3):
            if h == 0:
                poly = [(AX, AY), pt(k, 0), pt(k + 1, 0)]
            else:
                poly = [pt(k, h - 1), pt(k + 1, h - 1), pt(k + 1, h), pt(k, h)]
            c = cols[h]
            d.polygon([(u(x), u(y)) for x, y in poly], fill=c + (28 + 10 * ((k + h) % 2),))
    return L


GLOW = grad_line_layer(26, 14)
CORE = grad_line_layer(8, 0)
WHITECORE = Image.new("RGBA", (W, H), (0, 0, 0, 0))
_m = Image.new("L", (W, H), 0)
_d = ImageDraw.Draw(_m)
for (x0, y0), (x1, y1) in [((AX, AY), (FOOT[k], BY)) for k in range(4)] + [(pt(0, h), pt(3, h)) for h in range(3)]:
    _d.line([u(x0), u(y0), u(x1), u(y1)], fill=200, width=round(u(3)))
WHITECORE = Image.new("RGBA", (W, H), (255, 255, 255, 0))
WHITECORE.putalpha(_m)
CELLS = cells_layer()

# arka plan: koyu lacivert-mor degrade + bulanık renk lekeleri + nokta ızgara
_bg = np.zeros((H, W, 3), np.float32)
yy = np.linspace(0, 1, H)[:, None]
_bg[:] = (np.array([28, 14, 70]) * (1 - yy) + np.array([8, 6, 26]) * yy)[:, None, :][:, 0, :][:, None, :]
BG = Image.fromarray(_bg.clip(0, 255).astype(np.uint8)).convert("RGBA")
_bl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
_bd = ImageDraw.Draw(_bl)
for x, y, r, c in [(160, 380, 260, CYAN), (930, 820, 300, PINK), (300, 1450, 280, (150, 110, 255)), (900, 1750, 220, CYAN)]:
    _bd.ellipse([u(x - r), u(y - r), u(x + r), u(y + r)], fill=c + (70,))
_bl = _bl.filter(ImageFilter.GaussianBlur(u(120)))
BG.alpha_composite(_bl)
_gd = ImageDraw.Draw(BG)
for gx in range(0, 1081, 54):
    for gy in range(0, 1921, 54):
        _gd.ellipse([u(gx) - 2, u(gy) - 2, u(gx) + 2, u(gy) + 2], fill=(255, 255, 255, 26))
# cam kart
CARD = Image.new("RGBA", (W, H), (0, 0, 0, 0))
card(CARD, 70, 400, 940, 1080, r=56, fill=(255, 255, 255, 18), outline=(255, 255, 255, 60), width=round(u(3)))

random.seed(55)
SPARK = [(random.uniform(60, 1020), random.uniform(380, 1500), random.uniform(3, 7), random.uniform(0, 6.28), random.uniform(1.5, 3))
         for _ in range(26)]


def background(t):
    im = BG.copy()
    im.alpha_composite(CARD)
    d = ImageDraw.Draw(im)
    for x, y, r, ph, sp in SPARK:
        a = max(0.0, math.sin(t * sp + ph))
        if a > 0.05:
            rr = r * (0.6 + 0.4 * a)
            d.ellipse([u(x - rr), u(y - rr), u(x + rr), u(y + rr)], fill=(255, 255, 255, int(160 * a)))
    return im


def timer(L, t):
    d = ImageDraw.Draw(L)
    cx, cy, r = 540, 1590, 74
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
    txt(L, (cx, cy), str(n if t >= MK["t0"] else int(MK["dur"])), round(76 * s), WHITE, 1.0, k="black", stroke=5)


class Vid(Video):
    def frame(self, t):
        i = min(len(OPN) - 1, int(t * FPS))
        im = background(t)
        L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        # şekil: çizilerek gelir
        k = ramp(t, 0.05, 0.6)
        if k > 0:
            im.alpha_composite(set_alpha(CELLS, k))
            pulse = 0.75 + 0.25 * math.sin(t * 3.2)
            im.alpha_composite(set_alpha(GLOW, k * pulse))
            im.alpha_composite(set_alpha(CORE, k))
            im.alpha_composite(set_alpha(WHITECORE, k))
        if t < MK["tC"] - 0.05:
            q = pop(t, 0.0, 0.45)
            txt(L, (540, 150), "BU ŞEKİLDE", round(56 * q), WHITE, 1.0, stroke=6)
            put_word(L, "KAÇ ÜÇGEN VAR?", GOLD, 540, 250, max(8, round(98 * q)), alpha=1.0, glow=0.55)
            if t >= MK["dikkat"] - 0.05:
                chip(L, 540, 1590 if t < MK["t0"] else 1750, "DİKKATLİ SAY!", bg=PINK, fg=WHITE, size=50, k="black",
                     icon_name="eyes", scale=pop(t, MK["dikkat"] - 0.05, 0.35)) if t < MK["t0"] else None
            timer(L, t) if t >= MK["t0"] - 0.3 else None
        else:
            q = pop(t, MK["tC"] - 0.05, 0.4)
            txt(L, (540, 150), "SÜRE BİTTİ!", round(56 * q), WHITE, 1.0, stroke=6)
            put_word(L, "KAÇ TANE BULDUN?", GOLD, 540, 250, max(8, round(88 * q)), alpha=1.0, glow=0.55)
            if t >= MK["yor"] - 0.1:
                pulse = 1 + 0.04 * math.sin((t - MK["yor"]) * 8)
                chip(L, 610, 1560, "Cevabını yorumlara yaz!", bg=GOLD, fg=INKC, size=52, icon_name="speech_balloon",
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
