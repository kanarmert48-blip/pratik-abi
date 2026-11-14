"""55. video (2K Shorts, ~17 sn): Bu şekilde kaç üçgen var? 5 sn süre, sonra 18 üçgen tek tek sayılır.
Kullanım: python3 video55_ucgen.py <WORK> [frames t1,t2,... | ses | render]
WORK/voice_cut.wav + marks.json + muzik.wav gerekir."""
import os
os.environ.setdefault("PA_SCALE", str(4 / 3))
import json, math, random, subprocess, sys
from itertools import combinations
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
PINK = (255, 90, 170)
RED = (255, 70, 70)
INKC = (20, 18, 40)
PAL = [(255, 90, 170), (60, 230, 255), (255, 204, 70), (120, 240, 120), (180, 120, 255), (255, 140, 60)]


def ramp(t, a, b):
    return eio(clamp((t - a) / max(1e-6, b - a)))


# ---- şekil: tepeden 4 çizgi (2 kenar + 2 iç), 3 yatay (2 iç + taban) -> C(4,2)*3 = 18 üçgen ----
AX, AY = 540, 440
BY, BX0, BX1 = 1430, 110, 970
FOOT = [BX0, BX0 + (BX1 - BX0) / 3, BX0 + 2 * (BX1 - BX0) / 3, BX1]   # çizgilerin tabandaki x'i
HF = [0.45, 0.72, 1.0]                                                 # yatayların yüksekliği (oran)


def pt(line, h):
    f = HF[h]
    return AX + (FOOT[line] - AX) * f, AY + (BY - AY) * f


TRI = []
for h in range(3):
    for i, j in combinations(range(4), 2):
        TRI.append((j - i, h, i, j))
TRI.sort()                                       # önce küçükler, sonra büyükler
TRI = [((AX, AY), pt(i, h), pt(j, h)) for _, h, i, j in TRI]
assert len(TRI) == 18
N = len(TRI)
STEP = (MK["cnt1"] - MK["cnt0"]) / N

_bg = np.zeros((H, W, 3), np.float32)
yy = np.linspace(0, 1, H)[:, None]
_bg[:] = (np.array([46, 20, 92]) * (1 - yy) + np.array([12, 10, 38]) * yy)[:, None, :][:, 0, :][:, None, :]
BG = Image.fromarray(_bg.clip(0, 255).astype(np.uint8))
random.seed(55)
STARS = [(random.uniform(0, 1080), random.uniform(0, 1920), random.uniform(2, 5), random.uniform(0, 6.28)) for _ in range(60)]


def background(t):
    im = BG.copy().convert("RGBA")
    d = ImageDraw.Draw(im)
    for x, y, r, ph in STARS:
        a = int(60 + 60 * math.sin(t * 2 + ph))
        d.ellipse([u(x - r), u(y - r), u(x + r), u(y + r)], fill=(255, 255, 255, a))
    return im


def draw_shape(L, t, glow=1.0):
    d = ImageDraw.Draw(L)
    w = round(u(9))
    segs = [((AX, AY), (FOOT[k], BY)) for k in range(4)]
    for h in range(3):
        segs.append((pt(0, h), pt(3, h)))
    for (x0, y0), (x1, y1) in segs:
        d.line([u(x0), u(y0), u(x1), u(y1)], fill=(255, 255, 255, 255), width=w)
    for (x0, y0), (x1, y1) in segs:                # uç noktaları yuvarla
        for x, y in ((x0, y0), (x1, y1)):
            d.ellipse([u(x) - w / 2, u(y) - w / 2, u(x) + w / 2, u(y) + w / 2], fill=(255, 255, 255, 255))


def timer(L, t):
    d = ImageDraw.Draw(L)
    cx, cy, r = 540, 335, 56
    q = clamp((t - MK["t0"]) / 5.0)
    left = 5.0 * (1 - q)
    n = max(0, int(math.ceil(left - 1e-6)))
    col = RED if (t >= MK["t0"] and left <= 1.0) else GOLD
    bx = [u(cx - r), u(cy - r), u(cx + r), u(cy + r)]
    d.ellipse(bx, fill=(0, 0, 0, 120), outline=(255, 255, 255, 60), width=round(u(10)))
    if q < 1:
        d.arc(bx, -90 + 360 * q, 270, fill=col + (255,), width=round(u(10)))
    s = 1 + 0.18 * max(0.0, 1 - ((t - MK["t0"]) % 1.0) / 0.25) if MK["t0"] <= t < MK["tend"] else 1.0
    txt(L, (cx, cy), str(n if t >= MK["t0"] else 5), round(68 * s), WHITE, 1.0, k="black", stroke=5)


class Vid(Video):
    def frame(self, t):
        i = min(len(OPN) - 1, int(t * FPS))
        im = background(t)
        L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        F = Image.new("RGBA", (W, H), (0, 0, 0, 0))      # dolgu katmanı (çizgilerin altında)
        k_in = pop(t, 0.0, 0.45)
        # başlık
        if t < MK["tC"]:
            txt(L, (540, 118), "BU ŞEKİLDE", round(52 * k_in), WHITE, 1.0, stroke=6)
            put_word(L, "KAÇ ÜÇGEN VAR?", GOLD, 540, 188, max(8, round(84 * k_in)), alpha=1.0, glow=0.45)
        if t < MK["tB"]:
            timer(L, t)
        # sayım
        cnt = 0
        if t >= MK["cnt0"]:
            cnt = min(N, int((t - MK["cnt0"]) / STEP) + 1)
            fd = ImageDraw.Draw(F)
            if t < MK["cnt1"]:
                a, b, c = TRI[cnt - 1]
                col = PAL[(cnt - 1) % len(PAL)]
                fd.polygon([(u(a[0]), u(a[1])), (u(b[0]), u(b[1])), (u(c[0]), u(c[1]))], fill=col + (190,))
            else:
                for k, (a, b, c) in enumerate(TRI[:3]):     # en küçük 3'ü renkli bırak
                    pass
                q = ramp(t, MK["cnt1"], MK["cnt1"] + 0.3)
                fd.polygon([(u(AX), u(AY)), (u(BX0), u(BY)), (u(BX1), u(BY))], fill=CYAN + (int(60 * q),))
        im.alpha_composite(F)
        draw_shape(L, t)
        if cnt:
            ks = 1 + 0.25 * max(0.0, 1 - ((t - MK["cnt0"]) % STEP) / (STEP * 0.6)) if t < MK["cnt1"] else 1.0
            if t < MK["tC"]:
                d = ImageDraw.Draw(L)
                d.ellipse([u(540 - 78), u(1560 - 78), u(540 + 78), u(1560 + 78)], fill=INKC + (230,), outline=GOLD + (255,), width=round(u(6)))
                txt(L, (540, 1560), str(cnt), round(84 * ks), GOLD, 1.0, k="black", stroke=0)
        if MK["tB"] - 0.05 <= t < MK["cnt0"]:
            chip(L, 540, 1600, "CEVAP...", bg=GOLD, fg=INKC, size=58, k="black", scale=pop(t, MK["tB"] - 0.05, 0.3))
        if t >= MK["tC"] - 0.05:
            q = pop(t, MK["tC"] - 0.05, 0.4)
            put_word(L, "18 ÜÇGEN!", GOLD, 540, 190, max(8, round(120 * q)), alpha=1.0, glow=0.6)
        if t >= MK["kac"] - 0.1:
            q = pop(t, MK["kac"] - 0.1, 0.35)
            txt(L, (540, 1560), "Sen kaç tane buldun?", round(62 * q), WHITE, 1.0, stroke=7)
        if t >= MK["yor"] - 0.1:
            chip(L, 640, 1720, "Yorumlara yaz!", bg=GOLD, fg=INKC, size=56, icon_name="speech_balloon", k="black",
                 scale=pop(t, MK["yor"] - 0.1, 0.35))
        im.alpha_composite(L)
        brand(im, 540, 62, size=34)
        ROZ.draw(im, t, float(OPN[i]))
        return im.convert("RGB")


ROZ = Rozet(cx=150, cy=1745)
OPN, RND = konusma(VOICE, FPS)
VID = Vid([{"start": 0, "end": TOTAL, "draw": lambda *a: None}], [], "", TOTAL, bg=None)


def make_audio():
    ev = [(0.0, "pop"), (MK["t0"] - 0.05, "whoosh")]
    ev += [(MK["t0"] + s, "tink") for s in range(5)]
    ev += [(MK["tB"] - 0.05, "whoosh")]
    ev += [(MK["cnt0"] + k * STEP, "pop") for k in range(N)]
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
