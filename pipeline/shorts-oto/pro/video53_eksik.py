"""53. video (2K Shorts, ~36 sn): Eksik olanı bul (Gemini görselleri). 3 tur, süre kısalır (5-4-3 sn).
Kullanım: python3 video53_eksik.py <WORK> [frames t1,t2,... | ses | render]
WORK/voice_cut.wav + words.json + marks.json + muzik.wav gerekir."""
import os
os.environ.setdefault("PA_SCALE", str(4 / 3))
import json, math, random, subprocess, sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from engine import *  # noqa
from pa_ui import put_word, txt, pop, captions
from widgets import arrow
import audio_tools as at
from abi_yuz import konusma
from rozet import Rozet

WORK = Path(sys.argv[1])
VOICE = WORK / "voice_cut.wav"
words = json.loads((WORK / "words.json").read_text(encoding="utf-8"))
TOTAL = round(at.duration(str(VOICE)), 3)


def ramp(t, a, b):
    return eio(clamp((t - a) / max(1e-6, b - a)))


def T(key, nth=0):
    k = trl(clean(key)).strip('"!?;,.…')
    return [w for w in words if trl(clean(w["w"])).strip('"!?;,.…') == k][nth]["s"]


GOLD = (255, 204, 70)
CYAN = (60, 230, 255)
PINK = (255, 90, 170)
RED = (255, 70, 70)
INKC = (20, 18, 40)
S_END = T("Daha") - 0.1

# ---------- turlar ----------
MK = json.loads((WORK / "marks.json").read_text())
IMG = Path(__file__).resolve().parent / "v53img"
R = [
    dict(sc="ciftlik", box=(634, 466, 754, 593), dur=5, t0=MK["A"]["t0"], a=0.0,
         h1="5 SANİYEDE", h2="EKSİK OLANI BUL!", col=GOLD),
    dict(sc="plaj", box=(357, 559, 468, 636), dur=4, t0=MK["B"]["t0"], a=T("Şimdi") - 0.1,
         h1="TUR 2 · 4 SANİYE", h2="PLAJDA NE EKSİK?", col=CYAN),
    dict(sc="parti", box=(722, 95, 832, 375), dur=3, t0=MK["C"]["t0"], a=T("Son") - 0.1,
         h1="SON TUR · 3 SANİYE", h2="PARTİDE NE EKSİK?", col=PINK),
]
PX0, PW, PH = 60, 960, 644
PY = (306, 306 + PH + 28)
K = PW / 1024


def load_panel(p):
    im = Image.open(p).convert("RGBA").resize((round(u(PW)), round(u(PH))), Image.LANCZOS)
    m = Image.new("L", im.size, 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, im.width - 1, im.height - 1], radius=round(u(30)), fill=255)
    im.putalpha(m)
    return im


TAM = [load_panel(IMG / f"g_{rd['sc']}_tam.png") for rd in R]
EKS = [load_panel(IMG / f"g_{rd['sc']}_eksik.png") for rd in R]


def frame_panel(L, y):
    d = ImageDraw.Draw(L)
    d.rounded_rectangle([u(PX0 - 6), u(y - 6), u(PX0 + PW + 6), u(y + PH + 6)], radius=round(u(34)),
                        outline=(255, 255, 255, 230), width=round(u(6)))


def box_units(rd, y):
    x0, y0, x1, y1 = rd["box"]
    return PX0 + x0 * K, y + y0 * K, PX0 + x1 * K, y + y1 * K


# arka plan: koyu mor degrade + yumuşak ışık lekeleri
_bg = np.zeros((H, W, 3), np.float32)
yy = np.linspace(0, 1, H)[:, None]
_bg[:] = (np.array([46, 20, 92]) * (1 - yy) + np.array([12, 10, 38]) * yy)[:, None, :][:, 0, :][:, None, :]
BG = Image.fromarray(_bg.clip(0, 255).astype(np.uint8))
random.seed(53)
BLOBS = [(random.uniform(0, 1080), random.uniform(0, 1920), random.uniform(90, 200), random.choice([CYAN, PINK, GOLD]),
          random.uniform(0, 6.28)) for _ in range(9)]


def background(t):
    im = BG.copy().convert("RGBA")
    L = Image.new("RGBA", (W // 4, H // 4), (0, 0, 0, 0))
    d = ImageDraw.Draw(L)
    for x, y, r, col, ph0 in BLOBS:
        x2 = x + 30 * math.sin(t * 0.6 + ph0)
        y2 = y + 30 * math.cos(t * 0.5 + ph0)
        rr = r * u(1) / 4
        d.ellipse([x2 * u(1) / 4 - rr, y2 * u(1) / 4 - rr, x2 * u(1) / 4 + rr, y2 * u(1) / 4 + rr], fill=col + (38,))
    L = L.filter(ImageFilter.GaussianBlur(18)).resize((W, H), Image.BILINEAR)
    im.alpha_composite(L)
    return im


def timer(L, t, rd):
    """Üstte geri sayım halkası. Geri sayım başlamadan önce tam dolu bekler."""
    d = ImageDraw.Draw(L)
    cx, cy, r = 540, PY[1] - 14, 56
    q = clamp((t - rd["t0"]) / rd["dur"])
    left = rd["dur"] * (1 - q)
    n = max(0, int(math.ceil(left - 1e-6)))
    hot = t >= rd["t0"] and left <= 1.0 and q < 1
    col = RED if hot else rd["col"]
    bx = [u(cx - r), u(cy - r), u(cx + r), u(cy + r)]
    d.ellipse(bx, fill=(0, 0, 0, 120), outline=(255, 255, 255, 60), width=round(u(10)))
    if q < 1:
        d.arc(bx, -90 + 360 * q, 270, fill=col + (255,), width=round(u(10)))
    s = 1.0
    if t >= rd["t0"] and q < 1:
        s = 1 + 0.18 * max(0.0, 1 - ((t - rd["t0"]) % 1.0) / 0.25)      # her saniye küçük nabız
    txt(L, (cx, cy), str(n if t >= rd["t0"] else rd["dur"]) if q < 1 else "0", round(64 * s), WHITE, 1.0, k="black", stroke=5)


def round_frame(im, L, t, i):
    rd = R[i]
    end = rd["t0"] + rd["dur"]
    q = pop(t, rd["a"], 0.35) if i > 0 else 1.0
    if i == 2 and t >= T("Kaç") - 0.1:
        qq = pop(t, T("Kaç") - 0.1, 0.35)
        txt(L, (540, 150), "KAÇ TANESİNİ", round(64 * qq), WHITE, 1.0, stroke=7)
        put_word(L, "BULDUN?", GOLD, 540, 236, max(8, round(88 * qq)), alpha=1.0, glow=0.45)
        chip(L, 690, 1745, "Yorumlara yaz: 1, 2 ya da 3", bg=GOLD, fg=INKC, size=44, icon_name="speech_balloon",
             k="black", scale=pop(t, T("Yorumlara") - 0.1, 0.35))
    else:
        txt(L, (540, 146), rd["h1"], round(52 * q), WHITE, 1.0, stroke=6)
        put_word(L, rd["h2"], rd["col"], 540, 232, max(8, round(80 * q)), alpha=1.0, glow=0.45)
    dx = round(u(1080) * (1 - ramp(t, rd["a"], rd["a"] + 0.4))) if i > 0 else 0
    for j, src_im in enumerate((TAM[i], EKS[i])):
        y = PY[j]
        im.alpha_composite(src_im, (round(u(PX0)) + dx, round(u(y))))
    Lp = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    frame_panel(Lp, PY[0]); frame_panel(Lp, PY[1])
    im.alpha_composite(Lp, (dx, 0))
    if t < end + 0.01 and not (i == 2 and t >= T("Kaç") - 0.1):
        timer(L, t, rd)
    if t >= end:
        k = pop(t, end, 0.35)
        d = ImageDraw.Draw(L)
        x0, y0, x1, y1 = box_units(rd, PY[1])
        # eksik nesne alttaki resimde belirir
        a2 = ramp(t, end + 0.15, end + 0.6)
        if a2 > 0:
            bx = [round(u(v)) for v in (rd["box"][0] * K, rd["box"][1] * K, rd["box"][2] * K, rd["box"][3] * K)]
            crop = TAM[i].crop(bx)
            comp(L, set_alpha(crop, a2), round(u(PX0)) + bx[0], round(u(PY[1])) + bx[1])
        pad = 22 + 6 * math.sin((t - end) * 8)
        for yy in (PY[0], PY[1]):
            xa, ya, xb, yb = box_units(rd, yy)
            w = 7 if yy == PY[1] else 4
            d.ellipse([u(xa - pad * k), u(ya - pad * k), u(xb + pad * k), u(yb + pad * k)],
                      outline=GOLD + (255,), width=round(u(w)))
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        frm = (cx + (260 if cx < 540 else -260), cy + 230 if cy < PY[1] + PH / 2 else cy - 230)
        arrow(L, t, end + 0.05, frm, (cx, cy), bend=0.3 if cx < 540 else -0.3, col=WHITE, width=10,
              gap=max(x1 - x0, y1 - y0) * 0.6 + 20, dur=0.4)


class Vid(Video):
    def frame(self, t):
        i = min(len(OPN) - 1, int(t * FPS))
        im = background(t)
        L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        if t < S_END:
            k = 0 if t < R[1]["a"] else (1 if t < R[2]["a"] else 2)
            round_frame(im, L, t, k)
        else:
            b = ramp(t, S_END, S_END + 0.25)
            txt(L, (540, 760), "Daha fazlası için", 64, WHITE, b, stroke=6)
            pulse = 1 + 0.045 * math.sin((t - S_END) * 8) * ramp(t, S_END + 0.4, S_END + 0.7)
            chip(L, 540, 900, "TAKİP ET", bg=INKC, fg=WHITE, size=90, icon_name="bell", k="black",
                 scale=pop(t, S_END, 0.4) * pulse)
        im.alpha_composite(L)
        brand(im, 540, 62, size=34)
        ROZ.draw(im, t, float(OPN[i]))
        return im.convert("RGB")


ROZ = Rozet(cx=150, cy=1745)
OPN, RND = konusma(VOICE, FPS)
VID = Vid([{"start": 0, "end": TOTAL, "draw": lambda *a: None}], words, "", TOTAL, bg=None)


def make_audio():
    ev = [(0.0, "pop")]
    for k, rd in enumerate(R):
        if k:
            ev.append((rd["a"], "whoosh"))
        ev.append((rd["t0"] + rd["dur"], "ding"))
    ev += [(T("Kaç") - 0.1, "pop"), (S_END, "pop")]
    at.sfx(str(WORK / "sfx.wav"), TOTAL, ev)
    SR = 44100
    fx = np.frombuffer(subprocess.run(["ffmpeg", "-v", "error", "-i", str(WORK / "sfx.wav"), "-ac", "1", "-ar", str(SR),
                                       "-f", "f32le", "-"], capture_output=True).stdout, np.float32).copy()
    fx = np.pad(fx, (0, max(0, int(TOTAL * SR) + SR - len(fx))))
    rng = np.random.default_rng(53)
    m = int(0.05 * SR)
    tt = np.arange(m) / SR
    tick = (np.sin(2 * np.pi * 2400 * tt) * 0.6 + rng.standard_normal(m) * 0.4) * np.exp(-tt * 90)
    for rd in R:                                  # her saniye tik, son saniye daha güçlü
        for s in range(rd["dur"]):
            a = int((rd["t0"] + s) * SR)
            g = 0.16 if s == rd["dur"] - 1 else 0.10
            fx[a:a + m] += (tick * g).astype(np.float32)
    at._write(str(WORK / "sfx.wav"), fx[:int(TOTAL * SR)])
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-stream_loop", "3", "-i", str(WORK / "muzik.wav"), "-af",
                    f"atrim=0:{TOTAL:.3f},afade=t=in:d=0.3,afade=t=out:st={TOTAL - 0.6:.3f}:d=0.6",
                    "-ar", "44100", "-ac", "1", str(WORK / "music.wav")], check=True)
    at.final_mix(str(VOICE), str(WORK / "music.wav"), str(WORK / "sfx.wav"), str(WORK / "mix.m4a"))


if __name__ == "__main__":
    mode = sys.argv[2] if len(sys.argv) > 2 else "render"
    print("TOTAL", TOTAL, "S_END", S_END, flush=True)
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
