"""50. video (2K Shorts, ~30 sn): Kleopatra Ay'a inişe piramitlerden daha yakın yaşadı.
Kullanım: python3 video50_kleopatra.py <WORK> [frames t1,t2,... | ses | render]
WORK/foto/{piramit,tapinak,ay}.jpg (Unsplash) + voice_cut.wav + words.json + muzik.wav gerekir."""
import os
os.environ.setdefault("PA_SCALE", str(4 / 3))
import json, math, subprocess, sys
from pathlib import Path

import numpy as np
from PIL import ImageEnhance, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parent))
from engine import *  # noqa
from pa_ui import put_word, txt, pop, captions
import audio_tools as at
from abi_yuz import konusma
from rozet import Rozet

WORK = Path(sys.argv[1])
VOICE = WORK / "voice_cut.wav"
words = json.loads((WORK / "words.json").read_text(encoding="utf-8"))
TOTAL = round(at.duration(str(VOICE)), 3)


def ramp(t, a, b):
    return eio(clamp((t - a) / max(1e-6, b - a)))


def _hits(key):
    k = trl(clean(key)).strip('"!?;,.…')
    return [w for w in words if trl(clean(w["w"])).strip('"!?;,.…') == k]


def T(key, nth=0):
    return _hits(key)[nth]["s"]


K = {"bak": T("Bak"), "buyuk": T("Büyük"), "kleo2": T("Kleopatra", 1), "ondan": T("Ondan"),
     "yani": T("Yani"), "sen": T("Sen"), "yorum": T("Yorumlara"), "daha": T("Daha", -1)}
S_END = K["daha"] - 0.1
GOLD = (255, 204, 70)
SKY = (120, 200, 255)
INKC = (14, 16, 30)
DARK = (12, 12, 18)


# ---------- fotoğraflar (Ken Burns için biraz büyük hazırlanır) ----------
def cover(path, zoom=1.12, grade=1.0):
    im = Image.open(WORK / "foto" / path).convert("RGB")
    s = max(W * zoom / im.width, H * zoom / im.height)
    im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    if grade != 1.0:
        im = ImageEnhance.Brightness(im).enhance(grade)
    return im


PHOTOS = {"piramit": cover("piramit.jpg"), "tapinak": cover("tapinak.jpg", grade=0.92), "ay": cover("ay.jpg", zoom=1.18)}


def kb(name, t, t0, t1, z0=1.0, z1=1.07, dx=0.0):
    """Ken Burns: yavaş yakınlaşma + hafif kaydırma."""
    src = PHOTOS[name]
    q = clamp((t - t0) / max(1e-6, t1 - t0))
    z = z0 + (z1 - z0) * q
    cw, ch = W / z * (src.width / (W * 1.0)) / (src.width / W), H / z
    cw, ch = src.width / (1.12 if name != "ay" else 1.18) / z, src.height / (1.12 if name != "ay" else 1.18) / z
    cx = src.width / 2 + dx * q * src.width * 0.04
    cy = src.height / 2
    box = (cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2)
    return src.resize((W, H), Image.BILINEAR, box=box)


_g = Image.new("L", (1, H))
for y in range(H):
    v = y / H
    top = max(0.0, 1 - v / 0.40) ** 1.4 * 0.78
    bot = max(0.0, (v - 0.72) / 0.28) ** 1.3 * 0.70
    _g.putpixel((0, y), int(255 * max(top, bot)))
SHADE = Image.merge("RGBA", [Image.new("L", (W, H), 0)] * 3 + [_g.resize((W, H))])


def credit(L, s, a=0.6):
    txt(L, (540, 1880), s, 24, WHITE, a, k="b", stroke=3)


# ---------- zaman çizelgesi kartı ----------
YEARS = [(-2560, "Büyük Piramit", "MÖ 2560", GOLD), (-69, "Kleopatra", "MÖ 69", (255, 140, 120)),
         (1969, "Ay'a ilk adım", "1969", SKY)]
X0, X1 = 190, 890


def xpos(yr):
    return X0 + (X1 - X0) * (yr + 2560) / (1969 + 2560)


def timeline(L, t, t0, a=1.0, y=900, show_spans=True):
    d = ImageDraw.Draw(L)
    q = ramp(t, t0, t0 + 0.7)
    xe = X0 + (X1 - X0) * q
    d.rounded_rectangle([u(X0), u(y - 8), u(xe), u(y + 8)], radius=round(u(8)), fill=WHITE + (int(220 * a),))
    for i, (yr, nm, lab, col) in enumerate(YEARS):
        tt = t0 + 0.15 + i * 0.22
        qq = pop(t, tt, 0.3)
        if qq <= 0.02:
            continue
        x = xpos(yr)
        r = u(22) * qq
        d.ellipse([u(x) - r, u(y) - r, u(x) + r, u(y) + r], fill=col + (int(255 * a),), outline=INKC + (int(255 * a),), width=round(u(4)))
        up = i % 2 == 0
        ty = y - 95 if up else y + 85
        txt(L, (x, ty), nm, round(42 * qq), col, a, stroke=5)
        txt(L, (x, ty + 46), lab, round(34 * qq), WHITE, a * 0.9, k="b", stroke=4)
    if show_spans:
        # iki aralık: piramit -> Kleopatra (~2.500 yıl), Kleopatra -> Ay (~2.000 yıl)
        for (ya, yb, s, col, tt, yy) in [(-2560, -69, "~2.500 yıl", GOLD, t0 + 1.0, y + 230),
                                        (-69, 1969, "~2.000 yıl", SKY, t0 + 1.5, y + 230)]:
            qq = ramp(t, tt, tt + 0.4)
            if qq <= 0.01:
                continue
            xa, xb = xpos(ya) + 6, xpos(yb) - 6
            xm = xa + (xb - xa) * qq
            d.line([u(xa), u(yy), u(xm), u(yy)], fill=col + (int(255 * a),), width=round(u(8)))
            for xx in (xa, xb if qq > 0.98 else None):
                if xx is not None:
                    d.line([u(xx), u(yy - 22), u(xx), u(yy + 22)], fill=col + (int(255 * a),), width=round(u(6)))
            txt(L, ((xa + xb) / 2, yy + 62), s, round(46 * pop(t, tt + 0.2, 0.3)), col, a * qq, stroke=6)


class Vid(Video):
    def frame(self, t):
        i = min(len(OPN) - 1, int(t * FPS))
        L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        if t < K["bak"] - 0.05:                                 # kanca
            im = kb("piramit", t, 0, K["buyuk"], 1.04, 1.0)
            im = im.convert("RGBA"); im.alpha_composite(SHADE)
            put_word(L, "KLEOPATRA", GOLD, 540, 200, 112, alpha=1.0, glow=0.5)
            txt(L, (540, 330), "Ay'a inişe", 70, WHITE, 1.0, stroke=7)
            txt(L, (540, 420), "piramitlerden daha", 70, WHITE, 1.0, stroke=7)
            txt(L, (540, 510), "yakın yaşadı", 70, WHITE, 1.0, stroke=7)
            credit(L, "Fotoğraf: Alex Azabache / Unsplash")
        elif t < K["kleo2"] - 0.1:                              # piramit
            im = kb("piramit", t, 0, K["kleo2"], 1.0, 1.08).convert("RGBA"); im.alpha_composite(SHADE)
            q = pop(t, K["bak"], 0.3)
            txt(L, (540, 190), "BÜYÜK PİRAMİT", round(84 * q), GOLD, 1.0, stroke=7)
            if t >= K["buyuk"] + 0.6:
                chip(L, 540, 330, "yaklaşık 4.500 yıl önce", bg=WHITE, fg=INKC, size=54, k="black",
                     scale=pop(t, K["buyuk"] + 0.6, 0.3))
            credit(L, "Fotoğraf: Alex Azabache / Unsplash")
        elif t < K["ondan"] - 0.1:                              # Kleopatra dönemi
            im = kb("tapinak", t, K["kleo2"] - 0.1, K["ondan"], 1.0, 1.07, dx=1).convert("RGBA"); im.alpha_composite(SHADE)
            q = pop(t, K["kleo2"] - 0.1, 0.3)
            txt(L, (540, 180), "KLEOPATRA DOĞDUĞUNDA", round(64 * q), (255, 160, 140), 1.0, stroke=7)
            txt(L, (540, 260), "MÖ 69", round(52 * q), WHITE, 1.0, stroke=6)
            tt = K["kleo2"] + 1.2
            if t >= tt:
                chip(L, 540, 400, "piramit zaten ~2.500 yaşında", bg=GOLD, fg=INKC, size=54, k="black", scale=pop(t, tt, 0.3))
            credit(L, "Fotoğraf: Fatih Beki / Unsplash")
        elif t < K["yani"] - 0.1:                               # Ay
            im = kb("ay", t, K["ondan"] - 0.1, K["yani"], 1.0, 1.10).convert("RGBA"); im.alpha_composite(SHADE)
            q = pop(t, K["ondan"] - 0.1, 0.3)
            txt(L, (540, 180), "AY'A İLK ADIM", round(80 * q), SKY, 1.0, stroke=7)
            txt(L, (540, 270), "1969", round(56 * q), WHITE, 1.0, stroke=6)
            tt = K["ondan"] + 1.0
            if t >= tt:
                chip(L, 540, 410, "Kleopatra'dan ~2.000 yıl sonra", bg=WHITE, fg=INKC, size=52, k="black", scale=pop(t, tt, 0.3))
            credit(L, "Fotoğraf: NASA / Unsplash")
        elif t < S_END:                                         # zaman çizelgesi + soru
            im = Image.new("RGBA", (W, H), DARK + (255,))
            bg = kb("piramit", t, K["yani"], S_END, 1.0, 1.04).filter(ImageFilter.GaussianBlur(18))
            im = Image.blend(im.convert("RGB"), bg, 0.28).convert("RGBA")
            a = 1.0
            if t < K["sen"] - 0.1:
                q = pop(t, K["yani"] - 0.1, 0.3)
                txt(L, (540, 190), "KLEOPATRA İÇİN PİRAMİTLER", round(58 * q), (255, 160, 140), a, stroke=7)
                txt(L, (540, 280), "bizim için Kleopatra'dan", round(52 * q), WHITE, a, stroke=6)
                txt(L, (540, 355), "bile eskiydi", round(60 * q), GOLD, a, stroke=6)
            else:
                q = pop(t, K["sen"] - 0.1, 0.3)
                txt(L, (540, 200), "SEN BUNU", round(84 * q), WHITE, a, stroke=7)
                txt(L, (540, 300), "BİLİYOR MUYDUN?", round(84 * q), GOLD, a, stroke=7)
                if t >= K["yorum"] - 0.08:
                    chip(L, 540, 1500, "Yorumlara yaz", bg=GOLD, fg=INKC, size=56, icon_name="speech_balloon", k="black",
                         scale=pop(t, K["yorum"] - 0.08, 0.35))
            timeline(L, t, K["yani"] - 0.1, a)
        else:                                                   # son kart
            im = Image.new("RGBA", (W, H), DARK + (255,))
            bg = kb("ay", t, S_END, TOTAL, 1.05, 1.10).filter(ImageFilter.GaussianBlur(14))
            im = Image.blend(im.convert("RGB"), bg, 0.35).convert("RGBA")
            b = ramp(t, S_END, S_END + 0.25)
            txt(L, (540, 190), "Daha fazlası için", 64, WHITE, b, stroke=6)
            pulse = 1 + 0.045 * math.sin((t - S_END) * 8) * ramp(t, S_END + 0.4, S_END + 0.7)
            chip(L, 540, 320, "TAKİP ET", bg=INKC, fg=WHITE, size=90, icon_name="bell", k="black", scale=pop(t, S_END, 0.4) * pulse)
        im.alpha_composite(L)
        brand(im, 540, 62, size=34)
        if K["bak"] - 0.05 <= t < S_END:
            C = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            captions(C, self.groups, t, y=1700)
            im.alpha_composite(C)
        ROZ.draw(im, t, float(OPN[i]))
        return im.convert("RGB")


ROZ = Rozet()
OPN, RND = konusma(VOICE, FPS)
VID = Vid([{"start": 0, "end": TOTAL, "draw": lambda *a: None}], words, "", TOTAL, bg=None)


def make_audio():
    cuts = [K["bak"] - 0.05, K["kleo2"] - 0.1, K["ondan"] - 0.1, K["yani"] - 0.1]
    ev = [(0.0, "pop")] + [(c - 0.05, "whoosh") for c in cuts] + [(K["buyuk"] + 0.6, "pop"), (K["kleo2"] + 1.2, "pop"),
                                                               (K["ondan"] + 1.0, "pop"), (K["yorum"] - 0.08, "pop"), (S_END, "pop")]
    at.sfx(str(WORK / "sfx.wav"), TOTAL, ev)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-stream_loop", "3", "-i", str(WORK / "muzik.wav"), "-af",
                    f"atrim=0:{TOTAL:.3f},afade=t=in:d=0.3,afade=t=out:st={TOTAL - 0.6:.3f}:d=0.6",
                    "-ar", "44100", "-ac", "1", str(WORK / "music.wav")], check=True)
    at.final_mix(str(VOICE), str(WORK / "music.wav"), str(WORK / "sfx.wav"), str(WORK / "mix.m4a"))


if __name__ == "__main__":
    mode = sys.argv[2] if len(sys.argv) > 2 else "render"
    print("TOTAL", TOTAL, K, flush=True)
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
