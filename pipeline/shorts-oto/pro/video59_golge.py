"""59. video (2K Shorts, ~19 sn): Gölgeden futbolcuyu bil (cevap yok).
Kullanım: python3 video59_golge.py <WORK> [frames t1,t2,... | ses | render]"""
import os
os.environ.setdefault("PA_SCALE", str(4 / 3))
import json, math, subprocess, sys
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
INKC = (24, 30, 60)
NAVY = (20, 34, 80)
RED = (235, 60, 80)
SEG = MK["seg"]          # [(başla, bitir) x4]
T_END = MK["tC"]


def load(i):
    im = Image.open(WORK / "img" / f"s{i}.jpg").convert("RGB")
    return im.resize((W, H), Image.LANCZOS)


def blurbg(im):
    return im.resize((W // 8, H // 8)).filter(ImageFilter.GaussianBlur(6)).resize((W, H), Image.BILINEAR).point(lambda v: int(v * 0.55))


IMS = [load(i) for i in range(1, 5)]
BLUR = [blurbg(im) for im in IMS]
TILES = []
TW, TH = 500, 700
for im in IMS:
    cw = im.width * 1.0
    ch = cw * TH / TW
    cx, cy = im.width / 2, im.height * 0.55
    t = im.crop((int(cx - cw / 2), int(cy - ch / 2), int(cx + cw / 2), int(cy + ch / 2))).resize((round(u(TW)), round(u(TH))), Image.LANCZOS)
    m = Image.new("L", t.size, 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, t.width - 1, t.height - 1], radius=round(u(36)), fill=255)
    t = t.convert("RGBA"); t.putalpha(m)
    TILES.append(t)
BG = Image.new("RGBA", (W, H), (10, 16, 40, 255))
_g = np.linspace(0, 1, H)[:, None]
_bg = (np.array([14, 22, 56]) * (1 - _g)[..., None] + np.array([6, 60, 40]) * _g[..., None]).repeat(W, 1)
BG = Image.fromarray(_bg.astype(np.uint8)).convert("RGBA")


def full(i, t, a, b):
    im = IMS[i]
    p = clamp((t - a) / (b - a))
    sc = 0.86 + 0.04 * p
    fr = BLUR[i].copy().convert("RGBA")
    w, h = round(W * sc), round(H * sc)
    sm = im.resize((w, h), Image.BILINEAR).convert("RGBA")
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, w - 1, h - 1], radius=round(u(40)), fill=255)
    sm.putalpha(m)
    fr.alpha_composite(sm, ((W - w) // 2, round(u(250))))
    return fr


def grid(t, t0):
    im = BG.copy()
    pos = [(30, 330), (550, 330), (30, 1050), (550, 1050)]
    for k, (x, y) in enumerate(pos):
        q = pop(t, t0 + 0.08 * k, 0.35)
        if q <= 0:
            continue
        tl = TILES[k]
        if q < 0.999:
            tl = tl.resize((max(1, round(tl.width * q)), max(1, round(tl.height * q))), Image.LANCZOS)
        cx, cy = u(x + TW / 2), u(y + TH / 2)
        im.alpha_composite(tl, (round(cx - tl.width / 2), round(cy - tl.height / 2)))
        d = ImageDraw.Draw(im)
        r = 46
        d.ellipse([u(x + 20), u(y + 20), u(x + 20 + 2 * r), u(y + 20 + 2 * r)], fill=GOLD + (255,))
        txt(im, (x + 20 + r, y + 20 + r), str(k + 1), 64, INKC, 1.0, k="black", stroke=0)
    return im


def timer(L, t, a, b):
    d = ImageDraw.Draw(L)
    cx, cy, r = 900, 1690, 100
    q = clamp((t - a) / (b - a))
    left = (b - a) * (1 - q)
    n = max(0, int(math.ceil(left - 1e-6)))
    col = RED if left <= 1.0 else GOLD
    bx = [u(cx - r), u(cy - r), u(cx + r), u(cy + r)]
    d.ellipse(bx, fill=NAVY + (230,), outline=(255, 255, 255, 160), width=round(u(12)))
    if q < 1:
        d.arc(bx, -90 + 360 * q, 270, fill=col + (255,), width=round(u(14)))
    sc = 1 + 0.25 * max(0.0, 1 - ((t - a) % 1.0) / 0.25)
    txt(L, (cx, cy), str(n) if n > 0 else "?", round(112 * sc), WHITE, 1.0, k="black", stroke=0)


def title(L, line1, line2, q=1.0):
    ImageDraw.Draw(L).rounded_rectangle([u(55), u(110), u(1025), u(300)], radius=u(44), fill=(10, 16, 40, 215))
    txt(L, (540, 160), line1, round(62 * max(q, 0.8)), WHITE, 1.0, stroke=8, k="black")
    put_word(L, line2, GOLD, 540, 245, max(8, round(74 * max(q, 0.8))), alpha=1.0, glow=0.35)


class Vid(Video):
    def frame(self, t):
        i = min(len(OPN) - 1, int(t * FPS))
        L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        k = next((j for j, (a, b) in enumerate(SEG) if a <= t < b), None)
        if t < SEG[0][0]:
            im = grid(t, 0.0 if t > 0.05 else -1)
            title(L, "BU GÖLGELER KİMİN?", "SEVİNCİNDEN BİL!", 1.0 if t < 0.05 else pop(t, 0.0, 0.3))
        elif k is not None:
            a, b = SEG[k]
            im = full(k, t, a, b)
            # geçiş flaşı
            if t - a < 0.12:
                im.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 255, int(200 * (1 - (t - a) / 0.12)))))
            q = pop(t, a, 0.3)
            ImageDraw.Draw(L).rounded_rectangle([u(200), u(105), u(880), u(225)], radius=u(60), fill=(10, 16, 40, 225))
            put_word(L, f"GÖLGE {k + 1} / 4 · KİM?", GOLD, 540, 165, max(8, round(62 * max(q, 0.8))), alpha=1.0, glow=0.3)
            timer(L, t, a, b)
        else:
            im = grid(t, SEG[-1][1])
            title(L, "KAÇINI BİLDİN?", "YORUMLARA YAZ!", pop(t, SEG[-1][1], 0.3))
        im.alpha_composite(L)
        brand(im, 540, 62, size=34)
        ROZ.draw(im, t, float(OPN[i]))
        return im.convert("RGB")


ROZ = Rozet(cx=150, cy=1745)
OPN, RND = konusma(VOICE, FPS)
VID = Vid([{"start": 0, "end": TOTAL, "draw": lambda *a: None}], [], "", TOTAL, bg=None)


def make_audio():
    ev = [(0.0, "whoosh")]
    for a, b in SEG:
        ev.append((a, "whoosh"))
        ev += [(a + s, "tink") for s in range(int(round(b - a)))]
    ev.append((SEG[-1][1], "pop"))
    at.sfx(str(WORK / "sfx.wav"), TOTAL, ev)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-stream_loop", "3", "-i", str(WORK / "muzik.wav"), "-af",
                    f"atrim=0:{TOTAL:.3f},afade=t=in:d=0.2,afade=t=out:st={TOTAL - 0.5:.3f}:d=0.5",
                    "-ar", "44100", "-ac", "1", str(WORK / "music.wav")], check=True)
    at.final_mix(str(VOICE), str(WORK / "music.wav"), str(WORK / "sfx.wav"), str(WORK / "mix.m4a"))


if __name__ == "__main__":
    mode = sys.argv[2] if len(sys.argv) > 2 else "render"
    print("TOTAL", TOTAL, flush=True)
    if mode == "frames":
        (WORK / "test").mkdir(exist_ok=True)
        for tt in [float(x) for x in sys.argv[3].split(",")]:
            VID.frame(tt).save(WORK / "test" / f"f_{tt:05.2f}.jpg", quality=90)
    elif mode == "ses":
        make_audio()
    else:
        make_audio()
        VID.render(str(WORK / "mix.m4a"), str(WORK / "video.mp4"))
        print("render bitti", TOTAL, flush=True)
