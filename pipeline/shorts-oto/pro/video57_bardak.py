"""57. video (2K Shorts, ~15 sn): Hangi bardak önce dolar? Borulu 6 bardak, 6 sn süre, cevap verilmez.
Doğru cevap 5: 1'in alçak sol borusu tıkalı -> su sağdan 3'e gider; 3'ün en alçak çıkışı (sol) 5'e döker.
Kullanım: python3 video57_bardak.py <WORK> [frames t1,t2,... | ses | render]"""
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

GOLD = (255, 196, 40)
NAVY = (28, 44, 100)
RED = (255, 70, 70)
INKC = (24, 30, 60)
WATER = (60, 160, 255)


def ramp(t, a, b):
    return eio(clamp((t - a) / max(1e-6, b - a)))


CW, CH = 150, 190
CUPS = {1: (540, 520), 2: (270, 860), 3: (810, 860), 4: (540, 1250), 5: (230, 1250), 6: (850, 1250)}


def oy(c, h):
    x, y = CUPS[c]
    return y + CH - h * CH


PIPES = [
    # (yol noktaları, tıkalı mı)
    ([(465, oy(1, .25)), (270, oy(1, .25)), (270, 820)], True),
    ([(615, oy(1, .60)), (810, oy(1, .60)), (810, 820)], False),
    ([(345, oy(2, .30)), (540, oy(2, .30)), (540, 1210)], False),
    ([(735, oy(3, .20)), (690, oy(3, .20)), (690, 1160), (230, 1160), (230, 1210)], False),
    ([(885, oy(3, .55)), (950, oy(3, .55)), (950, 1160), (850, 1160), (850, 1210)], False),
]

_bg = np.zeros((H, W, 3), np.float32)
yy = np.linspace(0, 1, H)[:, None]
_bg[:] = (np.array([255, 243, 210]) * (1 - yy) + np.array([180, 222, 255]) * yy)[:, None, :][:, 0, :][:, None, :]
BG = Image.fromarray(_bg.clip(0, 255).astype(np.uint8)).convert("RGBA")


def poly(d, pts, col, w):
    P = [(u(x), u(y)) for x, y in pts]
    d.line(P, fill=col, width=round(u(w)), joint="curve")
    for x, y in P:
        r = u(w) / 2
        d.ellipse([x - r, y - r, x + r, y + r], fill=col)


def static_layer():
    L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(L)
    for pts, _ in PIPES:
        poly(d, pts, (60, 72, 96, 255), 30)
    for pts, _ in PIPES:
        poly(d, pts, (196, 206, 222, 255), 20)
    for pts, _ in PIPES:
        poly(d, [(x, y - 4) for x, y in pts], (240, 245, 252, 255), 5)
    # köprü: 2'nin borusu 3'ün borusunun altından geçer (üstte 3'ün borusu tekrar çizilir)
    seg = [(560, 1160), (520, 1160)]
    poly(d, seg, (60, 72, 96, 255), 30)
    poly(d, seg, (196, 206, 222, 255), 20)
    poly(d, [(x, y - 4) for x, y in seg], (240, 245, 252, 255), 5)
    # tıkaç
    for pts, blocked in PIPES:
        if blocked:
            (x0, y0), (x1, y1) = pts[0], pts[1]
            bx = x0 - 34
            d.rounded_rectangle([u(bx - 12), u(y0 - 15), u(bx + 12), u(y0 + 15)], radius=round(u(5)), fill=(70, 70, 78, 255))
    # boru ağızlarındaki küçük damla uçları
    for pts, _ in PIPES:
        x, y = pts[-1]
        d.ellipse([u(x - 13), u(y - 4), u(x + 13), u(y + 10)], fill=(60, 72, 96, 255))
    return L


def cup_layer():
    L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(L)
    for n, (cx, ty) in CUPS.items():
        x0, x1 = cx - CW / 2, cx + CW / 2
        pts = [(x0, ty), (x1, ty), (x1 - 10, ty + CH), (x0 + 10, ty + CH)]
        d.polygon([(u(x), u(y)) for x, y in pts], fill=(225, 245, 255, 120))
        d.line([(u(x), u(y)) for x, y in pts[1:] + pts[:1]][:3] + [(u(pts[0][0]), u(pts[0][1]))], fill=(255, 255, 255, 255),
               width=round(u(7)), joint="curve")
        d.line([u(x0 + 22), u(ty + 20), u(x0 + 28), u(ty + CH - 25)], fill=(255, 255, 255, 150), width=round(u(6)))
        d.ellipse([u(cx - 30), u(ty + CH + 18), u(cx + 30), u(ty + CH + 78)], fill=NAVY + (255,))
        txt(L, (cx, ty + CH + 48), str(n), 40, WHITE, 1.0, k="black", stroke=0)
    return L


STATIC = static_layer()
CUPSL = cup_layer()


def faucet(L, t):
    d = ImageDraw.Draw(L)
    cx, ty = CUPS[1]
    d.rounded_rectangle([u(cx - 150), u(300), u(cx + 20), u(345)], radius=round(u(18)), fill=(150, 160, 180, 255),
                        outline=(60, 72, 96, 255), width=round(u(5)))
    d.rounded_rectangle([u(cx - 25), u(320), u(cx + 25), u(400)], radius=round(u(12)), fill=(150, 160, 180, 255),
                        outline=(60, 72, 96, 255), width=round(u(5)))
    d.ellipse([u(cx - 95), u(268), u(cx - 55), u(300)], fill=RED + (255,), outline=(60, 72, 96, 255), width=round(u(4)))
    if t > 0.25:
        lvl = 0.03 + 0.15 * ramp(t, 0.3, MK["tend"])
        bot = ty + CH - lvl * CH
        for k in range(3):
            w = 16 + 4 * math.sin(t * 12 + k * 2)
            x = cx + 3 * math.sin(t * 18 + k)
            d.line([u(x), u(400), u(x), u(bot)], fill=WATER + (110 + 40 * k,), width=round(u(w - 4 * k)))
        # bardak 1'deki su
        x0, x1 = cx - CW / 2 + 9, cx + CW / 2 - 9
        wave = 4 * math.sin(t * 9)
        d.polygon([(u(x0), u(bot + wave)), (u(x1), u(bot - wave)), (u(x1 - 1), u(ty + CH - 4)), (u(x0 + 1), u(ty + CH - 4))],
                  fill=WATER + (190,))


def timer(L, t):
    d = ImageDraw.Draw(L)
    cx, cy, r = 540, 1625, 62
    q = clamp((t - MK["t0"]) / MK["dur"])
    left = MK["dur"] * (1 - q)
    n = max(0, int(math.ceil(left - 1e-6)))
    col = RED if (t >= MK["t0"] and left <= 3.0) else GOLD
    bx = [u(cx - r), u(cy - r), u(cx + r), u(cy + r)]
    d.ellipse(bx, fill=NAVY + (230,), outline=(255, 255, 255, 120), width=round(u(10)))
    if q < 1:
        d.arc(bx, -90 + 360 * q, 270, fill=col + (255,), width=round(u(10)))
    s = 1 + 0.2 * max(0.0, 1 - ((t - MK["t0"]) % 1.0) / 0.25) if MK["t0"] <= t < MK["tend"] else 1.0
    txt(L, (cx, cy), str(n if t >= MK["t0"] else int(MK["dur"])), round(66 * s), WHITE, 1.0, k="black", stroke=0)


class Vid(Video):
    def frame(self, t):
        i = min(len(OPN) - 1, int(t * FPS))
        im = BG.copy()
        k = ramp(t, 0.0, 0.35)
        im.alpha_composite(set_alpha(STATIC, k))
        L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        faucet(L, t)
        im.alpha_composite(L)
        im.alpha_composite(set_alpha(CUPSL, k))
        L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        q = pop(t, 0.0, 0.45)
        if t < MK["tC"] - 0.05:
            txt(L, (540, 120), "HANGİ BARDAK", round(60 * q), NAVY, 1.0, stroke=0, k="black")
            put_word(L, "ÖNCE DOLAR?", (240, 70, 90), 540, 205, max(8, round(96 * q)), alpha=1.0, glow=0.3)
            if t >= MK["t0"] - 0.3:
                timer(L, t)
        else:
            qq = pop(t, MK["tC"] - 0.05, 0.4)
            txt(L, (540, 120), "SÜRE BİTTİ!", round(60 * qq), NAVY, 1.0, stroke=0, k="black")
            put_word(L, "KAÇ NUMARA?", (240, 70, 90), 540, 205, max(8, round(96 * qq)), alpha=1.0, glow=0.3)
            if t >= MK["yor"] - 0.1:
                pulse = 1 + 0.04 * math.sin((t - MK["yor"]) * 8)
                chip(L, 650, 1625, "Cevabını yorumlara yaz!", bg=GOLD, fg=INKC, size=52, icon_name="speech_balloon",
                     k="black", scale=pop(t, MK["yor"] - 0.1, 0.35) * pulse)
        im.alpha_composite(L)
        brand(im, 540, 40, size=30)
        ROZ.draw(im, t, float(OPN[i]))
        return im.convert("RGB")


ROZ = Rozet(cx=150, cy=1745)
OPN, RND = konusma(VOICE, FPS)
VID = Vid([{"start": 0, "end": TOTAL, "draw": lambda *a: None}], [], "", TOTAL, bg=None)


def make_audio():
    ev = [(0.0, "whoosh"), (MK["t0"] - 0.05, "pop")]
    ev += [(MK["t0"] + s, "tink") for s in range(int(MK["dur"]))]
    ev += [(MK["tC"] - 0.05, "whoosh"), (MK["yor"] - 0.1, "pop")]
    at.sfx(str(WORK / "sfx.wav"), TOTAL, ev)
    SR = 44100
    fx = np.frombuffer(subprocess.run(["ffmpeg", "-v", "error", "-i", str(WORK / "sfx.wav"), "-ac", "1", "-ar", str(SR),
                                       "-f", "f32le", "-"], capture_output=True).stdout, np.float32).copy()
    fx = np.pad(fx, (0, max(0, int(TOTAL * SR) - len(fx))))
    rng = np.random.default_rng(57)                 # akan su sesi (filtrelenmiş gürültü)
    n = int(TOTAL * SR)
    wn = rng.standard_normal(n).astype(np.float32)
    k = np.ones(40, np.float32) / 40
    water = np.convolve(wn, k, mode="same") * 0.05
    env = np.clip((np.arange(n) / SR - 0.25) / 0.3, 0, 1) * np.clip((MK["tC"] + 0.6 - np.arange(n) / SR) / 0.6, 0, 1)
    fx[:n] += water * env
    at._write(str(WORK / "sfx.wav"), fx[:n])
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
