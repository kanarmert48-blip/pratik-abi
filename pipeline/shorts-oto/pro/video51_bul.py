"""51. video (2K Shorts, ~31 sn): 5 saniyede saklı 7'yi bul. 3 tur, her tur zorlaşır, süre kısalır (5-4-3 sn).
Kullanım: python3 video51_bul.py <WORK> [frames t1,t2,... | ses | render]
WORK/voice_cut.wav + words.json + muzik.wav gerekir."""
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
COLS, ROWS = 13, 15
CX0, CY0, CW, CH = 72, 440, 72, 66          # 1080 birim, ızgara sol üst + hücre boyu
CARD = (CX0 - 26, CY0 - 26, CX0 + COLS * CW + 26, CY0 + ROWS * CH + 26)
R = [  # (doldurma, hedef, süre, geri sayım başı, tur başı, tur sonu, başlık1, başlık2, renk, hedef hücre)
    dict(fill="1", target="7", dur=5, t0=4.85, a=0.0, b=10.9, h1="5 SANİYEDE", h2="7'Yİ BUL!", col=GOLD, cell=(9, 10)),
    dict(fill="9", target="6", dur=4, t0=14.15, a=10.9, b=19.2, h1="TUR 2 · 4 SANİYE", h2="6'YI BUL!", col=CYAN, cell=(3, 6)),
    dict(fill="O", target="Ö", dur=3, t0=22.35, a=19.2, b=S_END, h1="SON TUR · 3 SANİYE", h2="Ö'YÜ BUL!", col=PINK, cell=(10, 3)),
]
FN = font("black", round(u(50)))
PAL = [(235, 235, 255), (120, 225, 255), (255, 140, 200), (255, 214, 110), (170, 255, 170)]


def cell_xy(c, r):
    return CX0 + c * CW + CW / 2, CY0 + r * CH + CH / 2


def make_grid(rd, dim=False):
    """Koyu kart, renkli ve hafif kayık karakterler (daha zor)."""
    L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    card(L, CARD[0], CARD[1], CARD[2] - CARD[0], CARD[3] - CARD[1], r=34, fill=(28, 24, 64, 240),
         outline=(140, 110, 230, 255), width=round(u(3)))
    d = ImageDraw.Draw(L)
    rng = random.Random(hash(rd["fill"]) % 1000 + 7)
    a = 55 if dim else 255
    for r in range(ROWS):
        for c in range(COLS):
            col = rng.choice(PAL)
            jx, jy = rng.uniform(-5, 5), rng.uniform(-5, 5)
            if (c, r) == rd["cell"]:
                if dim:
                    continue
                ch = rd["target"]
            else:
                ch = rd["fill"]
            x, y = cell_xy(c, r)
            d.text((u(x + jx), u(y + jy)), ch, font=FN, fill=col + (a,), anchor="mm")
    return L


GRID = [make_grid(rd) for rd in R]
GRID_DIM = [make_grid(rd, True) for rd in R]

# arka plan: koyu mor degrade + yumuşak ışık lekeleri
_bg = np.zeros((H, W, 3), np.float32)
yy = np.linspace(0, 1, H)[:, None]
_bg[:] = (np.array([46, 20, 92]) * (1 - yy) + np.array([12, 10, 38]) * yy)[:, None, :][:, 0, :][:, None, :]
BG = Image.fromarray(_bg.clip(0, 255).astype(np.uint8))
random.seed(51)
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
    cx, cy, r = 540, 352, 56
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
    # başlık (son soruda yerini soruya bırakır)
    if i == 2 and t >= T("Kaç") - 0.1:
        qq = pop(t, T("Kaç") - 0.1, 0.35)
        txt(L, (540, 160), "KAÇ TANESİNİ", round(70 * qq), WHITE, 1.0, stroke=7)
        put_word(L, "BULDUN?", GOLD, 540, 258, max(8, round(96 * qq)), alpha=1.0, glow=0.45)
        chip(L, 540, 1800, "Yorumlara yaz: 1, 2 ya da 3", bg=GOLD, fg=INKC, size=48, icon_name="speech_balloon",
             k="black", scale=pop(t, T("Kaç") + 0.4, 0.35))
    else:
        txt(L, (540, 150), rd["h1"], round(54 * q), WHITE, 1.0, stroke=6)
        put_word(L, rd["h2"], rd["col"], 540, 238, max(8, round(92 * q)), alpha=1.0, glow=0.45)
        timer(L, t, rd)
    # ızgara (tur geçişinde aşağıdan kayarak gelir)
    dy = round(u(60) * (1 - ramp(t, rd["a"], rd["a"] + 0.35))) if i > 0 else 0
    if t < end:
        im.alpha_composite(GRID[i], (0, dy))
    else:
        im.alpha_composite(GRID_DIM[i], (0, dy))
        # hedef: altın kutu + büyüyen harf + kavisli ok
        c, r = rd["cell"]
        x, y = cell_xy(c, r)
        k = pop(t, end, 0.35)
        d = ImageDraw.Draw(L)
        hw = CW * 0.6 * k
        d.rounded_rectangle([u(x - hw), u(y - hw * 0.95), u(x + hw), u(y + hw * 0.95)], radius=round(u(16)),
                            fill=GOLD + (255,), outline=INKC + (255,), width=round(u(4)))
        txt(L, (x, y), rd["target"], max(8, round(70 * k)), INKC, 1.0, k="black", stroke=0)
        frm = (x + (260 if x < 540 else -260), y + 280 if r < 5 else y - 300)
        arrow(L, t, end + 0.05, frm, (x, y), bend=0.3 if x < 540 else -0.3, col=WHITE, width=10, gap=52, dur=0.4)


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


ROZ = Rozet()
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
    rng = np.random.default_rng(51)
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
