"""60. video — Gölgeden futbolcu Part 2 (profesyonel kurallar, Kasım 2026).
Palet: #121417 zemin, #F2EFE8 yazı, #3E8C7E ikincil, #E07A3F vurgu (en fazla 3-4 kez).
Font: Barlow Semi Condensed SemiBold (başlık), Inter SemiBold (altyazı). Kutu/bar/flaş/whoosh yok.
Kullanım: python3 video60_golge2.py <WORK> [frames t1,t2 | render]"""
import os
os.environ.setdefault("PA_SCALE", str(4 / 3))
import json, math, subprocess, sys, random
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from engine import u, W, H, FPS, Video, clamp, soft_shadow
import audio_tools as at
from abi_yuz import konusma
import rozet

WORK = Path(sys.argv[1])
FONTS = Path(__file__).resolve().parent.parent / "assets" / "fonts"
DARK, LIGHT, MID, ACCENT = (18, 20, 23), (242, 239, 232), (62, 140, 126), (224, 122, 63)

A_D, C_D = 5.205, 3.491
GAP0 = 0.25
S0 = A_D + GAP0                       # ilk sayaç başlangıcı
SEGD = 3.0
SEG = [(S0 + k * SEGD, S0 + (k + 1) * SEGD) for k in range(4)]
TC = SEG[-1][1] + 0.2
TOTAL = TC + C_D + 0.7
WR = json.loads((WORK / "words_raw.json").read_text(encoding="utf-8"))


def ease(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


def barlow(px):
    return ImageFont.truetype(str(FONTS / "BarlowSemiCondensed-SemiBold.ttf"), round(u(px)))


def inter(px):
    f = ImageFont.truetype(str(FONTS / "Inter-Var.ttf"), round(u(px)))
    f.set_variation_by_name("SemiBold")
    return f


# ---------- görseller: tek ton (hafif düşük doygunluk, kenar karartma, ince doku) ----------
def grade(im):
    a = np.asarray(im.convert("RGB"), np.float32) / 255
    g = a.mean(2, keepdims=True)
    a = g + (a - g) * 0.92                                   # doygunluk %8 düşük
    a = a * np.array([0.98, 1.0, 1.03])                      # hafif soğuk ton (gece stadyumu)
    yy, xx = np.mgrid[0:a.shape[0], 0:a.shape[1]]
    r = np.hypot((xx - a.shape[1] / 2) / (a.shape[1] / 2), (yy - a.shape[0] / 2) / (a.shape[0] / 2))
    a *= (1 - 0.13 * np.clip(r - 0.55, 0, 1) / 0.6)[..., None]  # %13 kenar karartma
    return Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))


IMS = []
for i in range(1, 5):
    im = Image.open(WORK / "img" / f"s{i}.jpg").convert("RGB")
    s = max(W * 1.06 / im.width, H * 1.06 / im.height)
    IMS.append(grade(im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)))
RNG = np.random.default_rng(7)
GRAIN = [Image.fromarray((RNG.normal(0, 4.5, (H // 2, W // 2))).clip(-12, 12).astype(np.int8).view(np.uint8) + 0, "L") for _ in range(6)]

# her plan için farklı kamera: (z0, z1, fx0, fy0, fx1, fy1) — 1.00→1.05, yön değişir, biri sabit
MOV = [(1.00, 1.05, .50, .50, .50, .47), (1.05, 1.00, .49, .46, .51, .50), (1.00, 1.00, .50, .52, .50, .52),
       (1.00, 1.045, .52, .50, .48, .49)]


def plate(i, t, a, b):
    im = IMS[i]
    z0, z1, fx0, fy0, fx1, fy1 = MOV[i]
    p = ease((t - a) / (b - a))
    z = z0 + (z1 - z0) * p
    fx, fy = fx0 + (fx1 - fx0) * p, fy0 + (fy1 - fy0) * p
    cw, ch = im.width / 1.06 / z, im.height / 1.06 / z
    cx = min(max(fx * im.width, cw / 2), im.width - cw / 2)
    cy = min(max(fy * im.height, ch / 2), im.height - ch / 2)
    return im.resize((W, H), Image.BILINEAR, box=(cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2))


def add_grain(fr, t):
    g = GRAIN[int(t * FPS) % len(GRAIN)].resize((W, H), Image.NEAREST)
    a = np.asarray(fr, np.int16) + (np.asarray(g, np.int8).astype(np.int16))[..., None] // 2
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


# ---------- yazı (gölge: siyah %45, 3px uzaklık, 6px yumuşaklık, kontur yok) ----------
def text(L, xy, s, font, fill, alpha=1.0, dy=0):
    if alpha <= 0.01:
        return
    xy = (u(xy[0]), u(xy[1]))
    sh = Image.new("RGBA", L.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).text((xy[0] + u(3), xy[1] + u(3) + dy), s, font=font, anchor="mm", fill=(0, 0, 0, int(115 * alpha)))
    L.alpha_composite(sh.filter(ImageFilter.GaussianBlur(u(3))))
    ImageDraw.Draw(L).text((xy[0], xy[1] + dy), s, font=font, anchor="mm", fill=fill + (int(255 * alpha),))


def rich(L, cx, cy, parts, font, alpha=1.0, dy=0):
    """parts: [(metin, renk)] tek satırda ortalanmış"""
    d = ImageDraw.Draw(L)
    widths = [d.textlength(p, font=font) for p, _ in parts]
    x = u(cx) - sum(widths) / 2
    for (p, c), w_ in zip(parts, widths):
        text(L, ((x + w_ / 2) / u(1), cy), p, font, c, alpha, dy)
        x += w_


def fade_in(t, a, d=0.4):
    return ease((t - a) / d)


SUBS = []   # (başla, bitir, metin)
def build_subs():
    groups = {"A": [("Gölgeler geri döndü.", 0, 2), ("Sadece gol sevincinden", 6, 8), ("tanıyabilir misin?", 9, 10)],
              "C": [("Kaçını bildin?", 0, 1), ("Dördünü de bildiysen", 2, 4), ("yorumlara yaz.", 5, 6)]}
    for key, off in (("A", 0.0), ("C", TC)):
        w = WR[key]
        for s, i0, i1 in groups[key]:
            SUBS.append((off + w[i0][1], off + w[i1][2] + 0.25, s))
build_subs()


class ProRozet(rozet.Rozet):
    """Sabit avatar: büyüme/sallanma/dalga yok, ince palet halkası."""
    def __init__(self, **kw):
        super().__init__(**kw)
        Sz, b = self.Sz, round(u(5))
        self.b = b
        ring = Image.new("RGBA", (Sz + 2 * b, Sz + 2 * b), (0, 0, 0, 0))
        ImageDraw.Draw(ring).ellipse([0, 0, Sz + 2 * b - 1, Sz + 2 * b - 1], fill=MID + (255,))
        self.ring = ring
        self.sh, self.pad = soft_shadow(ring.width, ring.height, ring.width // 2, blur=round(u(10)), op=0.35)
        self._cache = {}

    def draw(self, im, t, level=0.0, alpha=1.0):
        img = self._img(t)
        im.alpha_composite(self.sh, (round(self.cx - img.width / 2 - self.pad), round(self.cy - img.height / 2 - self.pad + u(6))))
        im.alpha_composite(img, (round(self.cx - img.width / 2), round(self.cy - img.height / 2)))


ROZ = ProRozet(size=150, cx=140, cy=1400)


def timer(L, t, a, b):
    d = ImageDraw.Draw(L)
    cx, cy, r = 800, 1420, 62
    q = clamp((t - a) / (b - a))
    left = (b - a) * (1 - q)
    n = max(1, int(math.ceil(left - 1e-6)))
    al = fade_in(t, a, 0.3)
    bx = [u(cx - r), u(cy - r), u(cx + r), u(cy + r)]
    d.ellipse(bx, outline=LIGHT + (int(70 * al),), width=round(u(4)))
    d.arc(bx, -90 + 360 * q, 270, fill=(ACCENT if left <= 1.0 else LIGHT) + (int(235 * al),), width=round(u(6)))
    text(L, (cx, cy - 3), str(n), barlow(64), LIGHT, al)


def frame(t):
    k = next((j for j, (a, b) in enumerate(SEG) if a <= t < b), None)
    if t < SEG[0][0]:
        fr = plate(0, t, 0, SEG[0][1])
    elif k is not None:
        a, b = SEG[k]
        fr = plate(k, t, (0 if k == 0 else a), b)
    elif t < TOTAL - 0.35:
        fr = plate(3, t, SEG[3][0], TOTAL)
    else:
        fr = plate(0, 0.0, 0, SEG[0][1])                    # döngü: son kare = ilk kare
    fr = add_grain(fr, t).convert("RGBA")
    L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    # açılış başlığı (ilk ~2.6 sn), ilk karede hazır
    if t < 2.6:
        al = 1.0 if t < 2.2 else 1 - ease((t - 2.2) / 0.3)
        rich(L, 540, 1120, [("4 ", ACCENT), ("gölge, ", LIGHT), ("4 ", ACCENT), ("futbolcu", LIGHT)], barlow(96), al)
    if k is not None:
        timer(L, t, *SEG[k])
        a = SEG[k][0]
        al = fade_in(t, a, 0.35) * (1 - ease((t - (SEG[k][1] - 0.3)) / 0.3))
        text(L, (540, 1225), f"{k + 1}. gölge", inter(46), LIGHT, al * 0.85, dy=u(12) * (1 - fade_in(t, a, 0.35)))
    for s, e, txt_ in SUBS:
        if s <= t < e and not (t < 2.6 and s < 1.5):
            al = fade_in(t, s, 0.3) * (1 - ease((t - (e - 0.2)) / 0.2))
            text(L, (540, 1240), txt_, inter(54), LIGHT, al)
    fr.alpha_composite(L)
    i = min(len(OPN) - 1, int(t * FPS))
    ROZ.draw(fr, t, float(OPN[i]))
    return fr.convert("RGB")


class Vid(Video):
    def frame(self, t):
        return frame(t)


def build_voice():
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(WORK / "ses/A.wav"), "-f", "lavfi", "-t", f"{TC - A_D:.3f}",
                    "-i", "anullsrc=r=44100:cl=mono", "-i", str(WORK / "ses/C.wav"), "-f", "lavfi", "-t", f"{TOTAL - TC - C_D + 0.05:.3f}",
                    "-i", "anullsrc=r=44100:cl=mono", "-filter_complex", "[0][1][2][3]concat=n=4:v=0:a=1", "-ar", "44100", "-ac", "1",
                    str(WORK / "voice_cut.wav")], check=True)


if not (WORK / "voice_cut.wav").exists():
    build_voice()
OPN, RND = konusma(WORK / "voice_cut.wav", FPS)


def make_audio():
    # sadece seslendirme + müzik (konuşma altında ~-20 dB), efekt yok
    v = WORK / "voice_cut.wav"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(v), "-stream_loop", "3", "-i", str(WORK / "muzik.wav"),
                    "-filter_complex",
                    f"[1:a]atrim=0:{TOTAL:.3f},volume=0.32,afade=t=in:d=0.3,afade=t=out:st={TOTAL - 0.6:.3f}:d=0.6[m];"
                    f"[m][0:a]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=400[md];"
                    f"[0:a][md]amix=inputs=2:duration=first:normalize=0,loudnorm=I=-14:TP=-1:LRA=9",
                    "-ar", "44100", "-c:a", "aac", "-b:a", "192k", str(WORK / "mix.m4a")], check=True)


if __name__ == "__main__":
    mode = sys.argv[2] if len(sys.argv) > 2 else "render"
    print("TOTAL", round(TOTAL, 2), flush=True)
    if mode == "frames":
        (WORK / "test").mkdir(exist_ok=True)
        for tt in [float(x) for x in sys.argv[3].split(",")]:
            frame(tt).save(WORK / "test" / f"f_{tt:05.2f}.jpg", quality=92)
    else:
        make_audio()
        V = Vid([{"start": 0, "end": TOTAL, "draw": lambda *a: None}], [], "", TOTAL, bg=None)
        V.render(str(WORK / "mix.m4a"), str(WORK / "video.mp4"))
        print("render bitti", flush=True)
