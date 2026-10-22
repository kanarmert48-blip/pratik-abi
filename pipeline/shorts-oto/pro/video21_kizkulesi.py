"""21. video (2K, ~33 sn): Siyah-beyaz Kız Kulesi fotoğrafını renkli gör (ters renk ardıl görüntü deneyi).
Kullanım: python3 video21_kizkulesi.py <WORK> [frames t1,t2,...]
WORK: ters.png, gri.png, orig.png (1440x2560), voice_cut.wav, words.json, zaman.json, muzik.wav"""
import os
os.environ.setdefault("PA_SCALE", str(4 / 3))
import json, math, subprocess, sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from engine import *  # noqa
from widgets import *  # noqa
import audio_tools as at
from abi_yuz import konusma
from rozet import Rozet

WORK = Path(sys.argv[1])
words = json.loads((WORK / "words.json").read_text(encoding="utf-8"))
TOTAL = at.duration(str(WORK / "voice_cut.wav"))


def _hits(key):
    k = trl(clean(key)).strip('"!?;,.…')
    return [w for w in words if trl(clean(w["w"])).strip('"!?;,.…') == k]


def T(key, nth=0):
    return _hits(key)[nth]["s"]


def E(key, nth=0):
    return _hits(key)[nth]["e"]


Z = json.loads((WORK / "zaman.json").read_text())
t_sad, t_sw = Z["sadece"], Z["switch"]
t_sonra, t_nokta, t_kirp_e = T("sonra"), T("noktaya"), E("kırpma")
t_goz2, t_renk2, t_beyn, t_gor = T("Gözündeki"), T("Renkleri"), T("beynin"), T("Gördüysen")
GRAY_END = t_goz2 - 0.3                      # bu ana kadar ekranda sadece gri fotoğraf + nokta

INV = Image.open(WORK / "ters.png").convert("RGB")
GRAY = Image.open(WORK / "gri.png").convert("RGB")
ORIG = Image.open(WORK / "orig.png").convert("RGB")
assert INV.size == (W, H)
DOT = (round(u(553)), round(u(911)))         # kulenin balkonu (sabit bakış noktası)

# üstte yazı okunsun diye koyu degrade
_g = np.zeros((H, W, 4), np.uint8)
_yy = np.arange(H)[:, None]
_g[..., 3] = np.clip((H * 0.30 - _yy) / (H * 0.30) * 150, 0, 150).astype(np.uint8)
TOPGRAD = Image.fromarray(_g, "RGBA")
_g2 = np.zeros((H, W, 4), np.uint8)
_g2[..., 3] = np.clip((_yy - H * 0.62) / (H * 0.38) * 120, 0, 120).astype(np.uint8)
BOTGRAD = Image.fromarray(_g2, "RGBA")


# ---------- Abi (yuvarlak rozet) ----------
ROZ = Rozet()
OPN, RND = konusma(WORK / "voice_cut.wav", FPS)


def roz_alpha(t):
    if t < t_sw:
        return 1 - eio(ph(t, t_kirp_e + 0.25, 0.4))
    return eo(ph(t, GRAY_END, 0.4))


def abi(im, t):
    a = roz_alpha(t)
    if a > 0.01:
        i = min(len(OPN) - 1, int(t * FPS))
        ROZ.draw(im, t, float(OPN[i]), alpha=a)


# ---------- yazılar ----------
_LOT = {}


def lottie(L, code, cx, cy, size, t, start, end=None):
    if t < start or (end is not None and t > end + 0.3):
        return
    if code not in _LOT:
        from ai_tools import Lottie
        _LOT[code] = Lottie(code)
    sc = eb(ph(t, start, 0.4)) * ((1 - eio(ph(t, end, 0.3))) if end is not None else 1)
    px = int(u(size))
    if sc <= 0.02:
        return
    fr = _LOT[code].frame(max(0.0, t - start), px)
    if abs(sc - 1) > 0.01:
        fr = fr.resize((max(1, int(px * sc)), max(1, int(px * sc))), Image.BICUBIC)
    comp(L, fr, u(cx) - fr.width / 2, u(cy) - fr.height / 2)


RAINBOW = [(255, 76, 76), (255, 150, 40), (255, 221, 51), (80, 222, 110), (50, 200, 255), (110, 125, 255), (200, 110, 255)]


def big_line(L, y, txt, size, alpha, cols=None, stroke=10):
    """Büyük satır; cols verilirse harf harf gökkuşağı."""
    f = font("black", round(u(size)))
    while f.getlength(txt) > u(1000) and size > 50:
        size -= 2
        f = font("black", round(u(size)))
    if alpha <= 0.01:
        return
    tmp = Image.new("RGBA", (W, round(u(size * 1.6))), (0, 0, 0, 0))
    d = ImageDraw.Draw(tmp)
    x = (W - f.getlength(txt)) / 2
    cy = tmp.height / 2
    sw = round(u(stroke))
    d.text((W / 2 + u(5), cy + u(8)), txt, font=f, fill=(0, 0, 0, 150), anchor="mm")
    if cols is None:
        d.text((W / 2, cy), txt, font=f, fill=ACC, anchor="mm", stroke_width=sw, stroke_fill=(8, 10, 18))
    else:
        k = 0
        for ch in txt:
            if ch != " ":
                d.text((x, cy), ch, font=f, fill=cols[k % len(cols)], anchor="lm", stroke_width=sw, stroke_fill=(8, 10, 18))
                k += 1
            x += f.getlength(ch)
    comp(L, set_alpha(tmp, alpha), 0, u(y) - tmp.height / 2)


def title(L, t, start, end, a_txt, b_txt, y=300, cols=None, size=124):
    if not (start <= t < end):
        return
    p = ph(t, start, 0.35) * (1 - ph(t, end - 0.2, 0.2))
    if p <= 0:
        return
    text_c(L, (540, y + (1 - eo(p)) * 30), a_txt, "black", 66, WHITE, alpha=eo(p), stroke=7, stroke_fill=(5, 6, 12))
    pop = 1 + 0.14 * (1 - eb(ph(t, start, 0.35)))
    big_line(L, y + 112, b_txt, round(size * pop), eo(p), cols=cols)


def bchip(L, t, start, end, text, y, bg=WHITE, fg=INK, size=46, icon=None):
    if t < start or t >= end:
        return
    chip(L, 540, y, text, bg=bg, fg=fg, size=size, icon_name=icon, k="black",
         scale=eb(ph(t, start, 0.35)) * (1 - eio(ph(t, end - 0.2, 0.2))))


_SPR = {}


def _sprite(r, col=(255, 245, 200)):
    r = int(r)
    key = (r, col)
    if key not in _SPR:
        n = 2 * r + 1
        yy, xx = np.mgrid[0:n, 0:n]
        d = np.sqrt((xx - r) ** 2 + (yy - r) ** 2) / r
        a = np.clip(1 - d, 0, 1) ** 1.6
        im = np.zeros((n, n, 4), np.uint8)
        im[..., 0], im[..., 1], im[..., 2] = col
        im[..., 3] = (a * 200).astype(np.uint8)
        _SPR[key] = Image.fromarray(im, "RGBA")
    return _SPR[key]


# ---------- bakış arayüzü ----------
def dot(L, t):
    d = ImageDraw.Draw(L)
    a = eo(ph(t, t_sad - 0.1, 0.25))
    r = u(12)
    d.ellipse([DOT[0] - r - u(5), DOT[1] - r - u(5), DOT[0] + r + u(5), DOT[1] + r + u(5)], fill=(255, 255, 255, int(255 * a)))
    d.ellipse([DOT[0] - r, DOT[1] - r, DOT[0] + r, DOT[1] + r], fill=(0, 0, 0, int(255 * a)))
    for k in range(2):                                   # "noktaya" derken iki halka dalgası
        q = ph(t, t_nokta - 0.1 + 0.45 * k, 0.8)
        if 0 < q < 1:
            rr = u(20 + 120 * eo(q))
            d.ellipse([DOT[0] - rr, DOT[1] - rr, DOT[0] + rr, DOT[1] + rr], outline=(255, 255, 255, int(230 * (1 - q))),
                      width=round(u(6)))


def timer(L, t):
    a = eo(ph(t, t_sad, 0.3))
    if a <= 0.01:
        return
    cx, cy, R = u(540), u(272), u(78)
    d = ImageDraw.Draw(L)
    d.ellipse([cx - R - u(10), cy - R - u(10), cx + R + u(10), cy + R + u(10)], fill=(8, 10, 18, int(150 * a)))
    d.ellipse([cx - R, cy - R, cx + R, cy + R], outline=(255, 255, 255, int(70 * a)), width=round(u(11)))
    q = clamp((t - t_sad) / (t_sw - t_sad))
    if q < 1:
        d.arc([cx - R, cy - R, cx + R, cy + R], -90 + 360 * q, 270, fill=ACC + (int(255 * a),), width=round(u(11)))
    n = max(1, int(math.ceil(t_sw - t - 1e-6)))
    frac = (t_sw - t) % 1.0
    pop = 1 + 0.10 * eo(clamp((frac - 0.85) / 0.15)) if t_sw - t < 5.5 else 1.0
    text_c(L, (540, 274), str(n), "black", round(92 * pop), WHITE, alpha=a)
    text_c(L, (540, 145), "Noktaya bak • gözünü kırpma", "black", 46, WHITE, alpha=a, stroke=6, stroke_fill=(5, 6, 12))


# ---------- fırça ile boyama ----------
NB = 8
_rng = np.random.default_rng(21)
BAND_D = [0.08 * i for i in _rng.permutation(NB)]
BRISTLE = np.convolve(_rng.standard_normal(H // 2 + 40), np.ones(5) / 5, mode="same")[:H // 2]
PAINT_DUR = 1.0


def paint_mask(t):
    """0..1 maske (yarım çözünürlük): soldan sağa 8 fırça darbesi."""
    hw, hh = W // 2, H // 2
    xs = np.arange(hw, dtype=np.float32)[None, :]
    ys = np.arange(hh, dtype=np.float32)
    bh = hh / NB
    m = np.zeros((hh, hw), np.float32)
    for i in range(NB):
        q = eio(ph(t, t_renk2 + 0.05 + BAND_D[i], PAINT_DUR))
        if q <= 0:
            continue
        c = (i + 0.5) * bh
        y0, y1 = int(max(0, c - bh * 0.85)), int(min(hh, c + bh * 0.85))
        yy = ys[y0:y1]
        dy = np.abs(yy - c) / (bh * 0.85)
        front = -0.25 * hw + 1.55 * hw * q - 120 * dy ** 2 + 22 * BRISTLE[y0:y1] + 10 * np.sin(yy * 0.07 + i)
        prof = np.clip((1 - dy) / 0.25, 0, 1)[:, None]
        mm = np.clip((front[:, None] - xs) / 14.0, 0, 1) * prof
        m[y0:y1] = np.maximum(m[y0:y1], mm)
    return m


def painted(t):
    if t < t_renk2:
        return GRAY.convert("RGBA")
    if t > t_renk2 + 0.05 + max(BAND_D) + PAINT_DUR + 0.05:
        return ORIG.convert("RGBA")
    m = Image.fromarray((paint_mask(t) * 255).astype(np.uint8), "L").resize((W, H), Image.BILINEAR)
    im = Image.composite(ORIG, GRAY, m).convert("RGBA")
    for i in range(NB):                                    # fırça ucunda parıltı
        q = ph(t, t_renk2 + 0.05 + BAND_D[i], PAINT_DUR)
        if 0.02 < q < 0.98:
            x = (-0.25 + 1.55 * eio(q)) * W
            y = (i + 0.5) * H / NB
            spr = _sprite(u(46))
            comp(im, set_alpha(spr, math.sin(q * math.pi)), x - spr.width / 2, y - spr.height / 2)
    return im


# ---------- kareler ----------
def hook_bg(t):
    z = 1 + 0.12 * (1 - eo(clamp(t / max(0.1, t_sad - 0.3))))
    cw, ch = W / z, H / z
    l, tp = DOT[0] - DOT[0] / z, DOT[1] - DOT[1] / z     # nokta sabit kalarak uzaklaş
    return INV.crop((l, tp, l + cw, tp + ch)).resize((W, H), Image.BICUBIC).convert("RGBA")


class Vid(Video):
    def frame(self, t):
        if t < t_sw:
            im = hook_bg(t) if t < t_sad else INV.convert("RGBA")
            ga = 1 - eio(ph(t, t_sad - 0.3, 0.5))
            if ga > 0.01:
                im.alpha_composite(set_alpha(TOPGRAD, ga))
            L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            title(L, t, -1.0, t_sonra - 0.05, "Bu fotoğrafa", "15 SANİYE BAK!")
            title(L, t, t_sonra, t_sad - 0.05, "Sonra siyah-beyazı", "RENKLİ GÖR!", cols=RAINBOW)
            if t >= t_sad - 0.1:
                dot(L, t)
                timer(L, t)
            im.alpha_composite(L)
            if 2.0 <= t < t_sad:
                brand(im, 540, 140)
            draw_caption(im, self.groups, t, y=1330)
            abi(im, t)
            return im.convert("RGB")
        if t < GRAY_END:                                   # saf gri fotoğraf + gri nokta
            im = GRAY.copy()
            d = ImageDraw.Draw(im)
            r = u(9)
            d.ellipse([DOT[0] - r, DOT[1] - r, DOT[0] + r, DOT[1] + r], fill=(150, 150, 150))
            return im
        im = painted(t)
        f = eo(ph(t, GRAY_END, 0.4))
        im.alpha_composite(set_alpha(TOPGRAD, f))
        im.alpha_composite(set_alpha(BOTGRAD, f))
        L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        title(L, t, GRAY_END + 0.15, t_renk2 - 0.02, "Renk hücrelerin", "YORULDU!", y=250, size=118)
        lottie(L, "1f62a", 905, 540, 190, t, GRAY_END + 0.35, end=t_renk2 - 0.2)
        title(L, t, t_renk2, TOTAL + 1, "Renkleri", "BEYNİN BOYADI!", y=250, cols=RAINBOW, size=112)
        lottie(L, "1f9e0", 905, 545, 200, t, t_beyn, end=None)
        bchip(L, t, t_gor, TOTAL + 1, "Gördüysen yorumlara yaz!", 1110, icon="speech_balloon", size=50)
        im.alpha_composite(L)
        brand(im, 540, 140) if f > 0.5 else None
        draw_caption(im, self.groups, t, y=1330)
        abi(im, t)
        return im.convert("RGB")


def tick_track(path, total, times):
    """Son saniyelerde hafif saat tıkırtısı (sfx.wav üstüne eklenir)."""
    SR = 44100
    r = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(path), "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"],
                       capture_output=True, check=True)
    y = np.frombuffer(r.stdout, np.float32).copy()
    rng = np.random.default_rng(5)
    m = int(0.025 * SR)
    tt = np.arange(m) / SR
    clk = (rng.standard_normal(m) * 0.5 + np.sin(2 * np.pi * 3200 * tt)) * np.exp(-tt * 260) * 0.22
    for s in times:
        i = int(s * SR)
        if i + m < len(y):
            y[i:i + m] += clk
    at._write(str(path), y)


if __name__ == "__main__":
    mode = sys.argv[2] if len(sys.argv) > 2 else "render"
    v = Vid([{"start": 0, "end": TOTAL, "draw": lambda *a: None}], words, "", TOTAL, bg=None)
    if mode == "frames":
        for tt in [float(x) for x in sys.argv[3].split(",")]:
            v.frame(tt).save(WORK / f"fr_{tt:05.2f}.png")
    else:
        sfx = [(0.0, "pop"), (t_sonra, "pop"), (t_sad, "pop"), (t_sw, "whoosh"), (GRAY_END + 0.15, "pop"),
               (t_renk2 + 0.05, "tink"), (t_gor, "pop")]
        at.sfx(str(WORK / "sfx.wav"), TOTAL, sfx)
        tick_track(WORK / "sfx.wav", TOTAL, [t_sw - k for k in range(1, 6)])
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(WORK / "muzik.wav"), "-af",
                        f"apad,atrim=0:{TOTAL:.3f},afade=t=in:d=0.15,afade=t=out:st={TOTAL - 0.5:.3f}:d=0.5",
                        "-ar", "44100", "-ac", "1", str(WORK / "music.wav")], check=True)
        at.final_mix(str(WORK / "voice_cut.wav"), str(WORK / "music.wav"), str(WORK / "sfx.wav"), str(WORK / "mix.m4a"))
        v.render(str(WORK / "mix.m4a"), str(WORK / "video.mp4"))
        print("render bitti", TOTAL, flush=True)
