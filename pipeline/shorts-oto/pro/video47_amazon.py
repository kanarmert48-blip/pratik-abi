"""47. video (uzun, 16:9 2K, ~12 dk): Amazon Ormanında 7 Gün — komik + gerçek bilgi.
Kullanım: python3 video47_amazon.py <WORK> [frames t1,t2,..|render [keep]|ses|some i,j]"""
import json, math, re, subprocess, sys
from functools import lru_cache
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from belgesel import *  # noqa

WORK = Path(sys.argv[1])
MED = WORK / "med"
KEY = MED
ROZET = Path(__file__).resolve().parent.parent / "assets" / "abi_rozet.mp4"
SR = 44100
NSEG = 9
YEL = (255, 212, 0)
PINK = (255, 140, 190)


def norm(w):
    return re.sub(r"[^\wçğıöşüâî]", "", w.lower().replace("i̇", "i"))


DUR = {i: float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                 str(WORK / f"ses/v{i}.wav")], capture_output=True, text=True).stdout) for i in range(1, NSEG + 1)}
WORDS = {i: json.loads((WORK / f"ses/v{i}.json").read_text(encoding="utf-8")) for i in range(1, NSEG + 1)}
for _w in WORDS[8]:
    if _w["w"] in ("gün.",) and _w["s"] > 30:
        _w["w"] = "gün"
for _w in WORDS[9]:
    if _w["w"] == "hala":
        _w["w"] = "hâlâ"

TEASE = 7.0
G = {1: TEASE + 0.3}
TITLE0 = G[1] + DUR[1] + 0.3
TITLE1 = TITLE0 + 3.6
DC = {}
t_ = TITLE1 + 0.1
for k in range(2, 9):
    DC[k] = t_
    G[k] = DC[k] + 4.3
    t_ = G[k] + DUR[k] + 0.5
G[9] = G[8] + DUR[8] + 1.0
END = G[9] + DUR[9]
OUT0 = END + 0.6
TOTAL = OUT0 + 7.0


def T(seg, key, at=None, nth=0):
    """seg içinde key ile başlayan kelime; at verilirse (sn, segment içi) en yakını."""
    k = norm(key)
    hits = [w for w in WORDS[seg] if norm(w["w"]).startswith(k)]
    if not hits:
        raise KeyError(f"{seg}:{key}")
    if at is not None:
        w = min(hits, key=lambda w: abs(w["s"] - at))
    else:
        w = hits[nth]
    return G[seg] + w["s"]


def E(seg):
    return G[seg] + DUR[seg]


CLIPLEN = {}
for p in MED.glob("*.mp4"):
    d = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
                       capture_output=True, text=True).stdout.strip()
    try:
        CLIPLEN[p.stem] = float(d)
    except ValueError:
        CLIPLEN[p.stem] = 5.0


def pf(stem):
    c = sorted(MED.glob(stem + ".*"))
    c = [x for x in c if x.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp")]
    if not c:
        raise FileNotFoundError(stem)
    return c[0].name
def clip(name, t0, t1, off=0.0, z=(1.0, 1.07), dx=(0.0, 0.0), dy=(0.0, 0.0), xf=0.3, focus=0.5, speed=None, shake=0):
    src = (KEY if name.startswith("k_") else MED) / f"{name}.mp4"
    need = t1 - t0 + 0.5
    L = CLIPLEN.get(name, 10) - off - 0.15
    sp = speed if speed else clamp(L / need, 0.45, 1.0)
    return {"src": src, "t0": t0, "t1": t1, "off": off, "z": z, "dx": dx, "dy": dy, "xf": xf, "focus": focus, "speed": sp,
            "shake": shake}


def freeze(name, t0, t1, off=0.0, z=(1.08, 1.16), xf=0.0):
    return clip(name, t0, t1, off=off, z=z, xf=xf, speed=0.01)


def photo(name, t0, t1, z=(1.0, 1.1), dx=(0.0, 0.0), dy=(0.0, 0.0), xf=0.3, card=False, fy=0.5):
    return {"img": str(MED / name), "t0": t0, "t1": t1, "z": z, "dx": dx, "dy": dy, "xf": xf, "card": card, "fy": fy}


def dark(t0, t1, xf=0.4):
    return {"bg": "dark", "t0": t0, "t1": t1, "xf": xf}

# ---------------- fotoğraf karesi ----------------
TW, TH = int(W * OVER) // 2 * 2, int(H * OVER) // 2 * 2


@lru_cache(maxsize=4)
def photo_frame(path, card, fy):
    im = cv2.cvtColor(cv2.imread(path), cv2.COLOR_BGR2RGB)
    h, w = im.shape[:2]
    s = max(TW / w, TH / h)
    big_ = cv2.resize(im, (int(w * s) + 1, int(h * s) + 1), interpolation=cv2.INTER_CUBIC)
    y0 = int((big_.shape[0] - TH) * fy)
    x0 = (big_.shape[1] - TW) // 2
    cov = big_[y0:y0 + TH, x0:x0 + TW].astype(np.float32)
    if not card:
        return np.clip(cov * 0.97, 0, 255).astype(np.uint8)
    bg = cv2.GaussianBlur(cov, (0, 0), 40) * 0.38
    s2 = min(TW * 0.80 / w, TH * 0.80 / h)
    fw, fh = int(w * s2), int(h * s2)
    fg = cv2.resize(im, (fw, fh), interpolation=cv2.INTER_AREA).astype(np.float32)
    x, y = (TW - fw) // 2, (TH - fh) // 2
    bg[y - 4:y + fh + 4, x - 4:x + fw + 4] = (232, 196, 132)
    bg[y:y + fh, x:x + fw] = fg
    return np.clip(bg, 0, 255).astype(np.uint8)


_yy, _xx = np.mgrid[0:H, 0:W].astype(np.float32)
_r = np.sqrt(((_xx - W * 0.5) / W) ** 2 + ((_yy - H * 0.46) / H) ** 2)
DARKBASE = np.zeros((H, W, 3), np.float32)
for c, (a, b) in enumerate(zip((30, 24, 20), (8, 7, 6))):
    DARKBASE[..., c] = b + (a - b) * np.clip(1 - _r * 1.6, 0, 1) ** 1.5
del _yy, _xx, _r
_pr = np.random.default_rng(37)
EMBERS = [(_pr.uniform(0, W), _pr.uniform(0, H), _pr.uniform(10, 46), _pr.uniform(-10, 10), _pr.uniform(-22, -6),
           _pr.uniform(0, 6.28), GOLD if _pr.random() < 0.7 else (236, 140, 80), _pr.uniform(0.05, 0.15)) for _ in range(40)]
DARKIMG = Image.fromarray(DARKBASE.astype(np.uint8)).convert("RGBA")


def bgfn(name, t, lt):
    im = DARKIMG.copy()
    for x, y, r, vx, vy, ph0, col, a in EMBERS:
        xx = (x + vx * t + 18 * math.sin(t * 0.4 + ph0)) % (W + 200) - 100
        yy = (y + vy * t) % (H + 200) - 100
        dot(im, xx, yy, r, col, a * (0.6 + 0.4 * math.sin(t * 0.7 + ph0)), power=2.2)
    return np.asarray(im.convert("RGB"))


class TL37(Timeline):
    def _cut_frame(self, c, t, readers):
        if "img" in c:
            lt = t - c["t0"]
            q = clamp(lt / max(0.1, c["vis_end"] - c["t0"]))
            fr = photo_frame(c["img"], c["card"], c["fy"])
            z, dx, dy = c["z"], c["dx"], c["dy"]
            return kenburns(fr, q, z[0], z[1], dx[0], dx[1], dy[0], dy[1])
        fr = super()._cut_frame(c, t, readers)
        A = c.get("shake", 0)
        if A:
            lt = t - c["t0"]
            a = A * (0.55 + 0.45 * math.exp(-lt * 2))
            M = np.float32([[1, 0, a * math.sin(t * 53)], [0, 1, a * math.cos(t * 41)]])
            fr = cv2.warpAffine(fr, M, (W, H), borderMode=cv2.BORDER_REFLECT)
        return fr


# ---------------- grafik yardımcıları ----------------
def _lt_shade():
    w, h = 1500, 520
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.sqrt(((xx - 300) / 1100) ** 2 + ((yy - h / 2) / 230) ** 2)
    im = np.zeros((h, w, 4), np.uint8)
    im[..., 3] = (np.clip(1 - d, 0, 1) ** 1.4 * 150).astype(np.uint8)
    return Image.fromarray(im, "RGBA")


LT_SHADE = _lt_shade()
_by = np.arange(H, dtype=np.float32)[:, None]
_bot = np.zeros((H, W, 4), np.uint8)
_bot[..., 3] = (np.clip((_by - H * 0.58) / (H * 0.42), 0, 1) ** 1.3 * 185).astype(np.uint8)
BOT = Image.fromarray(_bot, "RGBA")
_top = np.zeros((H, W, 4), np.uint8)
_top[..., 3] = (np.clip((H * 0.24 - _by) / (H * 0.24), 0, 1) ** 1.5 * 130).astype(np.uint8)
TOP = Image.fromarray(_top, "RGBA")
del _by, _bot, _top


def lower_third(L, t, s, e, name, sub, x=170, y=1150):
    a = window(t, s, e, 0.5, 0.4)
    if a <= 0:
        return
    put(L, LT_SHADE, x - 170, y + 90, "lm", a)
    d = ImageDraw.Draw(L)
    d.rectangle([x, y, x + 110 * eo(ph(t, s, 0.6)), y + 4], fill=GOLD + (int(255 * a),))
    q = eo(ph(t, s + 0.1, 0.6))
    text(L, x - 4, y + 60, name, "sans", "SemiBold", 58, WARM, a * q, track=0.01, anchor="lm", rise=(1 - q) * 14)
    q2 = eo(ph(t, s + 0.3, 0.6))
    text(L, x - 2, y + 122, sub, "sans", "Regular", 36, GREY, a * q2, track=0.02, anchor="lm", rise=(1 - q2) * 14)


def cite(L, t, s, e, txt):
    text(L, 170, 1378, "Kaynak: " + txt, "sans", "Italic", 26, GREY, window(t, s, e, 0.6, 0.5) * 0.8, anchor="lm",
         shadow=0.8)


def quote(L, t, s, e, txt, y=1190, size=86, color=WARM, italic=True):
    a = window(t, s, e, 0.5, 0.4)
    if a <= 0:
        return
    if y > 1000:
        L.alpha_composite(set_alpha(BOT, a))
    q = eo(ph(t, s, 0.9))
    text(L, W / 2, y, txt, "serif", "Regular", size, color, a, track=0.01 + 0.03 * (1 - q), italic=italic, shadow=0.85,
         rise=(1 - q) * 18)


def label(L, x, y, txt, a, size=30, color=WARM, anchor="mm", w="Medium", track=0.18):
    text(L, x, y, txt, "sans", w, size, color, a, track=track, anchor=anchor)


def shade(L, t, s, e, amt=0.45):
    a = window(t, s, e, 0.4, 0.4) * amt
    if a > 0.01:
        L.alpha_composite(Image.new("RGBA", (W, H), (4, 5, 8, int(255 * a))))


def flash(L, t, s, d=0.3, col=(255, 255, 255), amt=0.85):
    if s <= t <= s + d:
        a = (1 - (t - s) / d) ** 2 * amt
        L.alpha_composite(Image.new("RGBA", (W, H), col + (int(255 * a),)))


def big(L, t, s, e, txt, sub="", x=W / 2, y=640, size=230, color=GOLD, subcol=WARM, subsize=52):
    a = window(t, s, e, 0.4, 0.4)
    if a <= 0:
        return
    q = eo(ph(t, s, 0.6))
    im = text_img(txt, ("serif", "Regular", False), size, color, 0.0, 0.85, 0)
    put(L, im, x, y, "mm", a * q, scale=1.0 + 0.12 * (1 - q))
    if sub:
        q2 = eo(ph(t, s + 0.25, 0.6))
        text(L, x, y + size * 0.74, sub, "sans", "Medium", subsize, subcol, a * q2, track=0.04, rise=(1 - q2) * 12)


@lru_cache(maxsize=256)
def meme_img(txt, size, col, stroke):
    f = ImageFont.truetype(INTER.format("Black"), size)
    bb = f.getbbox(txt, stroke_width=stroke)
    w, h = bb[2] - bb[0] + 60, bb[3] - bb[1] + 60
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    sh = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(sh).text((30 - bb[0] + 6, 30 - bb[1] + 10), txt, font=f, fill=(0, 0, 0, 170), stroke_width=stroke,
                           stroke_fill=(0, 0, 0, 170))
    im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(8)))
    ImageDraw.Draw(im).text((30 - bb[0], 30 - bb[1]), txt, font=f, fill=col + (255,), stroke_width=stroke,
                            stroke_fill=(0, 0, 0, 255))
    return im


def meme(L, t, s, e, txt, x=W / 2, y=1170, size=120, col=(255, 255, 255), rot=0.0, stroke=9):
    """komik başlık: kalın, konturlu, zıplayarak gelir"""
    a = window(t, s, e, 0.08, 0.25)
    if a <= 0:
        return
    lt = t - s
    sc = 1.0 + 0.35 * math.exp(-lt * 9) * math.cos(lt * 22)
    im = meme_img(txt, size, col, stroke)
    if rot:
        im = im.rotate(rot, resample=Image.BICUBIC, expand=True)
    put(L, im, x, y, "mm", a, scale=max(0.6, sc))


def aa(w, h, k=2):
    im = Image.new("RGBA", (w * k, h * k), (0, 0, 0, 0))
    return im, ImageDraw.Draw(im)


def check_icon(d, cx, cy, r, col, a, kind="ok"):
    c = col + (int(255 * a),)
    if kind == "ok":
        d.line([(cx - r * 0.55, cy), (cx - r * 0.1, cy + r * 0.45), (cx + r * 0.6, cy - r * 0.45)], fill=c,
               width=int(r * 0.22), joint="curve")
    elif kind == "no":
        d.line([(cx - r * 0.45, cy - r * 0.45), (cx + r * 0.45, cy + r * 0.45)], fill=c, width=int(r * 0.22))
        d.line([(cx - r * 0.45, cy + r * 0.45), (cx + r * 0.45, cy - r * 0.45)], fill=c, width=int(r * 0.22))
    else:
        d.line([(cx, cy - r * 0.5), (cx, cy + r * 0.12)], fill=c, width=int(r * 0.22))
        d.ellipse([cx - r * 0.13, cy + r * 0.32, cx + r * 0.13, cy + r * 0.58], fill=c)




def g_phone(L, t, s, e, msg="SİNYAL YOK", sub="", x=W * 0.72):
    a = window(t, s, e, 0.4, 0.4)
    if a <= 0:
        return
    q = eo(ph(t, s, 0.6))
    pw, ph_ = 420, 840
    im, d = aa(pw + 40, ph_ + 40)
    k = 2
    d.rounded_rectangle([20 * k, 20 * k, (pw + 20) * k, (ph_ + 20) * k], radius=54 * k, fill=(18, 20, 26, 245),
                        outline=(200, 200, 205, 255), width=5 * k)
    d.rounded_rectangle([34 * k, 34 * k, (pw + 6) * k, (ph_ + 6) * k], radius=42 * k, fill=(30, 34, 46, 255))
    bx, by = 70 * k, 92 * k
    for i in range(4):
        hh = (10 + i * 9) * k
        d.rectangle([bx + i * 14 * k, by - hh, bx + i * 14 * k + 9 * k, by], fill=(110, 112, 120, 255))
    d.line([(bx - 6 * k, by - 44 * k), (bx + 62 * k, by + 6 * k)], fill=RED + (255,), width=5 * k)
    im = im.resize((pw + 40, ph_ + 40), Image.LANCZOS)
    y = H * 0.5 + (1 - q) * 120
    dot(L, x, y, 520, (150, 180, 255), a * q * 0.22, power=2.0)
    put(L, im, x, y, "mm", a * q)
    text(L, x, y - 40, msg, "sans", "Bold", 50, WARM, a * q, track=0.1)
    if sub:
        text(L, x, y + 40, sub, "sans", "Medium", 40, RED, a * q, track=0.06)


def g_needs(L, t, s, e, rows, title, x=1880, y=300):
    a = window(t, s, e, 0.5, 0.4)
    if a <= 0:
        return
    n = len(rows)
    pw, rh = 580, 96
    put(L, Image.new("RGBA", (pw, 90 + rh * n), (8, 10, 14, int(175 * a))), x, y, "lt", 1.0)
    ImageDraw.Draw(L).rectangle([x, y, x + 6, y + 90 + rh * n], fill=GOLD + (int(230 * a),))
    label(L, x + 36, y + 48, title, a, 28, GOLD, anchor="lm", w="SemiBold", track=0.3)
    for i, (txt, ton, kind) in enumerate(rows):
        q = eo(ph(t, ton, 0.4))
        if q <= 0.01:
            continue
        yy = y + 90 + rh * i + rh / 2
        col = {"ok": GREEN, "no": RED, "warn": (240, 180, 80)}[kind]
        im, dd = aa(70, 70)
        dd.ellipse([4, 4, 136, 136], outline=col + (int(255 * a * q),), width=8)
        check_icon(dd, 70, 70, 52, col, a * q, kind=kind)
        put(L, im.resize((70, 70), Image.LANCZOS), x + 74, yy, "mm", 1.0, scale=1 + 0.3 * (1 - q))
        text(L, x + 130, yy, txt, "sans", "SemiBold", 46, WARM, a * q, anchor="lm", rise=(1 - q) * 10)


def g_circle(L, t, s, e, x, y, r, txt=""):
    a = window(t, s, e, 0.2, 0.3)
    if a <= 0:
        return
    q = eo(ph(t, s, 0.4))
    im, d = aa(int(2 * r + 40), int(2 * r + 40))
    k = 2
    d.arc([20 * k, 20 * k, (2 * r + 20) * k, (2 * r + 20) * k], -90, -90 + 360 * q, fill=RED + (int(255 * a),), width=14 * k)
    put(L, im.resize((int(2 * r + 40), int(2 * r + 40)), Image.LANCZOS), x, y, "mm", 1.0)
    if txt:
        meme(L, t, s + 0.3, e, txt, x=x, y=y + r + 90, size=80, col=YEL)


_ROZ = None


def outro(L, t):
    global _ROZ
    a = window(t, OUT0 - 0.6, TOTAL + 1, 0.8, 0.5)
    if a <= 0:
        return
    if _ROZ is None:
        raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-ss", "0.5", "-i", str(ROZET), "-frames:v", "1", "-vf",
                              "scale=400:400", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
        im = Image.frombuffer("RGB", (400, 400), raw, "raw", "RGB", 0, 1).convert("RGBA")
        m = Image.new("L", (1600, 1600), 0)
        ImageDraw.Draw(m).ellipse([0, 0, 1599, 1599], fill=255)
        im.putalpha(m.resize((400, 400), Image.LANCZOS))
        ring = Image.new("RGBA", (428, 428), (0, 0, 0, 0))
        ImageDraw.Draw(ring).ellipse([0, 0, 427, 427], fill=GOLD + (255,))
        ring.alpha_composite(im, (14, 14))
        _ROZ = ring
    q = eo(ph(t, OUT0 - 0.6, 1.0))
    put(L, _ROZ, W / 2, 560, "mm", a * q, scale=0.92 + 0.08 * q)
    text(L, W / 2, 870, "Pratik Abi", "serif", "Regular", 110, WARM, a * q)
    label(L, W / 2, 960, "ŞAŞIRTICI BİLİM, SADE ANLATIM", a * eo(ph(t, OUT0, 0.9)), 30, GOLD, track=0.3)
    q2 = eo(ph(t, OUT0 + 0.5, 0.6))
    if q2 > 0.01:
        bw, bh = 520, 130
        im, d = aa(bw, bh)
        d.rounded_rectangle([0, 0, bw * 2, bh * 2], radius=bh, fill=(214, 40, 40, 255))
        put(L, im.resize((bw, bh), Image.LANCZOS), W / 2, 1150, "mm", a * q2, scale=1 + 0.035 * math.sin((t - OUT0) * 5))
        text(L, W / 2, 1150, "TAKİP ET", "sans", "Bold", 60, (255, 255, 255), a * q2, track=0.14, shadow=0.3)


# ---------------- v38 özel grafikler ----------------
def stamp(L, t, s, e, txt, x=W * 0.5, y=H * 0.42, col=(214, 40, 40), size=150, rot=-8):
    a = window(t, s, e, 0.05, 0.35)
    if a <= 0:
        return
    lt = t - s
    sc = 1.0 + 1.2 * max(0.0, 1 - lt / 0.18) ** 2
    f = ImageFont.truetype(INTER.format("Black"), size)
    bb = f.getbbox(txt)
    w, h = bb[2] - bb[0] + 120, bb[3] - bb[1] + 90
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([8, 8, w - 8, h - 8], radius=28, outline=col + (255,), width=14)
    d.text((60 - bb[0], 45 - bb[1]), txt, font=f, fill=col + (255,))
    im = im.rotate(rot, resample=Image.BICUBIC, expand=True)
    put(L, im, x, y, "mm", a * min(1.0, lt / 0.12 + 0.2), scale=sc)


def profile(L, t, s, e, name, rows, stars, x=1700, y=250):
    a = window(t, s, e, 0.4, 0.4)
    if a <= 0:
        return
    q = eo(ph(t, s, 0.5))
    pw = 720
    ph_ = 200 + 86 * len(rows) + 90
    x = x + (1 - q) * 120
    card = Image.new("RGBA", (pw, ph_), (246, 242, 232, int(238 * a)))
    d = ImageDraw.Draw(card)
    d.rectangle([0, 0, pw, 70], fill=(214, 40, 40, int(255 * a)))
    put(L, card, x, y, "lt", 1.0)
    text(L, x + 30, y + 36, "SAHİPLENDİRME KARTI", "sans", "Black", 32, (255, 255, 255), a, track=0.12, anchor="lm", shadow=0)
    text(L, x + 30, y + 130, name, "serif", "Regular", 64, (30, 28, 26), a, anchor="lm", italic=True, shadow=0)
    for i, (k, v) in enumerate(rows):
        qq = eo(ph(t, s + 0.25 + i * 0.18, 0.4))
        yy = y + 220 + i * 86
        text(L, x + 30, yy, k, "sans", "Medium", 34, (110, 104, 96), a * qq, anchor="lm", shadow=0)
        text(L, x + pw - 30, yy, v, "sans", "Bold", 38, (30, 28, 26), a * qq, anchor="rm", shadow=0)
        ImageDraw.Draw(L).line([(x + 30, yy + 40), (x + pw - 30, yy + 40)], fill=(200, 194, 184, int(255 * a * qq)), width=2)
    yy = y + ph_ - 55
    text(L, x + 30, yy, "EVCİLLİK", "sans", "Black", 32, (214, 40, 40), a, anchor="lm", track=0.12, shadow=0)
    qs = ph(t, s + 0.4 + len(rows) * 0.18, 0.6)
    for k in range(5):
        on = k < stars and qs * 5 > k
        text(L, x + 300 + k * 72, yy, "★", "sans", "Black", 54, (240, 170, 20) if on else (200, 194, 184), a, anchor="mm",
             shadow=0)


def hint(L, t, s, e, txt):
    a = window(t, s, e, 0.4, 0.4)
    if a > 0:
        text(L, W - 150, 1370, txt, "sans", "Italic", 30, WARM, a * 0.85, anchor="rm", shadow=0.9)


_fr = np.random.default_rng(8)
FEATHERS = [(_fr.uniform(0, W), _fr.uniform(-H, 0), _fr.uniform(30, 70), _fr.uniform(0, 6.28), _fr.uniform(60, 140))
            for _ in range(34)]


@lru_cache(None)
def feather_img(sz):
    im, d = aa(sz, sz // 3)
    k = 2
    d.ellipse([0, 0, sz * k, sz * k // 3], fill=(240, 236, 226, 230))
    d.line([(4, sz * k // 6), (sz * k - 4, sz * k // 6)], fill=(170, 160, 150, 255), width=3)
    return im.resize((sz, sz // 3), Image.LANCZOS)


def g_feathers(L, t, s, e):
    a = window(t, s, e, 0.4, 0.6)
    if a <= 0:
        return
    lt = t - s
    for x, y0, sz, p0, sp in FEATHERS:
        y = y0 + lt * sp * 3
        if y < -60 or y > H + 60:
            continue
        xx = x + 60 * math.sin(lt * 1.6 + p0)
        im = feather_img(int(sz)).rotate(25 * math.sin(lt * 2 + p0), resample=Image.BICUBIC, expand=True)
        put(L, im, xx, y, "mm", a)


def g_ruler(L, t, s, e, x, y, hpx, txt):
    a = window(t, s, e, 0.3, 0.3)
    if a <= 0:
        return
    q = eo(ph(t, s, 0.6))
    d = ImageDraw.Draw(L)
    c = YEL + (int(255 * a),)
    hh = hpx * q
    d.line([(x, y), (x, y - hh)], fill=c, width=8)
    for k in range(11):
        yy = y - hh * k / 10
        d.line([(x - (30 if k % 5 == 0 else 16), yy), (x, yy)], fill=c, width=5)
    meme(L, t, s + 0.5, e, txt, x=x - 210, y=y - hpx / 2, size=90, col=YEL)


def g_calc(L, t, s, times):
    e = times[-1] + 3.0
    a = window(t, s, e, 0.4, 0.4)
    if a <= 0:
        return
    rows = [("5 kg", "× 700 TL", ""), ("", "= 3.500 TL", " / GÜN"), ("× 30", "= 105.000 TL", " / AY")]
    text(L, W / 2, 300, "Sadece büyüdüğü kısmın kıyma hesabı", "serif", "Regular", 70, WARM, a, italic=True)
    for i, ((l, m, r), tt) in enumerate(zip(rows, times)):
        q = eo(ph(t, tt, 0.4))
        if q <= 0.01:
            continue
        y = 560 + i * 200
        col = (255, 90, 80) if i == 2 else WARM
        text(L, 760, y, l, "sans", "Bold", 110, GOLD, a * q, anchor="rm")
        text(L, 820, y, m + r, "sans", "Black", 110 if i else 110, col, a * q, anchor="lm", rise=(1 - q) * 20)
    text(L, W / 2, 1180, "Kıyma: marketlerde kilosu 700 TL'nin üzerinde (Eylül 2026)", "sans", "Medium", 34, GREY,
         a * eo(ph(t, times[0] + 0.5, 0.5)))


def g_water(L, t, s, e, t_fil, t_tri):
    a = window(t, s, e, 0.4, 0.4)
    if a <= 0:
        return
    shade(L, t, s, e, 0.55)
    text(L, 200, 300, "Günlük su (litre)", "serif", "Regular", 84, WARM, a, anchor="lm")
    rows = [("FİL", 70, 200, t_fil, CYAN, "70–200"), ("TRICERATOPS", 200, 500, t_tri, GOLD, "birkaç yüz (kaba tahmin)")]
    x0, x1 = 760, 2300
    for i, (nm, lo, hi, tt, col, lab) in enumerate(rows):
        q = eo(ph(t, tt, 1.0))
        if q <= 0.01:
            continue
        y = 620 + i * 260
        text(L, 200, y, nm, "sans", "Bold", 60, WARM, a * clamp(q * 3), anchor="lm")
        w = (x1 - x0) * hi / 550 * q
        d = ImageDraw.Draw(L)
        d.rounded_rectangle([x0, y - 50, x0 + max(20, w), y + 50], radius=24, fill=col + (int(220 * a),))
        if i == 1:
            for k in range(0, int(w), 40):
                d.line([(x0 + k, y + 50), (x0 + k + 24, y - 50)], fill=(255, 255, 255, int(90 * a)), width=8)
        text(L, x0 + 30, y + 100, lab, "sans", "SemiBold", 44, col, a * q, anchor="lm")


def g_bill(L, t, s, e):
    a = window(t, s, e, 0.3, 0.4)
    if a <= 0:
        return
    q = eo(ph(t, s, 0.5))
    pw, ph_ = 700, 860
    im = Image.new("RGBA", (pw, ph_), (250, 248, 242, 255))
    d = ImageDraw.Draw(im)
    f1 = ImageFont.truetype(INTER.format("Black"), 64)
    f2 = ImageFont.truetype(INTER.format("Medium"), 36)
    d.rectangle([0, 0, pw, 120], fill=(40, 110, 200, 255))
    d.text((pw / 2, 60), "SU FATURASI", font=f1, fill=(255, 255, 255, 255), anchor="mm")
    for i, (k, v) in enumerate([("Abone", "Triceratops"), ("Tüketim", "çok"), ("Havuz", "yarım"), ("Komşu", "şikayetçi")]):
        d.text((50, 190 + i * 90), k, font=f2, fill=(110, 104, 96, 255), anchor="lm")
        d.text((pw - 50, 190 + i * 90), v, font=f2, fill=(30, 28, 26, 255), anchor="rm")
    d.line([(50, 540), (pw - 50, 540)], fill=(30, 28, 26, 255), width=4)
    d.text((50, 600), "TOPLAM", font=f2, fill=(30, 28, 26, 255), anchor="lm")
    n = int(clamp((t - s - 0.6) / 1.6) ** 2 * 999999)
    d.text((pw - 50, 720), f"{n:,}".replace(",", ".") + " TL", font=ImageFont.truetype(INTER.format("Black"), 84),
           fill=(214, 40, 40, 255), anchor="rm")
    im = im.rotate(3, resample=Image.BICUBIC, expand=True)
    put(L, im, W * 0.7, H * 0.5 + (1 - q) * 300, "mm", a)


_cr = np.random.default_rng(3)
CONF = [(_cr.uniform(0, W), _cr.uniform(-H * 0.6, 0), _cr.uniform(14, 28), _cr.uniform(0, 6.28), _cr.uniform(300, 600),
         [(214, 40, 40), YEL, GREEN, CYAN, (240, 140, 220)][int(_cr.integers(0, 5))]) for _ in range(140)]


def g_confetti(L, t, s, e):
    a = window(t, s, e, 0.1, 0.6)
    if a <= 0:
        return
    lt = t - s
    d = ImageDraw.Draw(L)
    for x, y0, sz, p0, sp, col in CONF:
        y = y0 + lt * sp
        if y > H + 30:
            continue
        xx = x + 40 * math.sin(lt * 3 + p0)
        w = sz * abs(math.cos(lt * 6 + p0))
        d.rectangle([xx - w / 2, y - sz / 3, xx + w / 2, y + sz / 3], fill=col + (int(255 * a),))


def info_card(L, t, s, e, title, lines, y=640):
    a = window(t, s, e, 0.4, 0.4)
    if a <= 0:
        return
    shade(L, t, s, e, 0.45)
    q = eo(ph(t, s, 0.6))
    text(L, W / 2, y - 160, title, "sans", "Black", 64, GOLD, a * q, track=0.12)
    for i, (txt, kind, sz) in enumerate(lines):
        qq = eo(ph(t, s + 0.4 + i * 0.5, 0.6))
        kd = ("serif", "Regular") if kind == "serif" else ("sans", "SemiBold")
        text(L, W / 2, y + i * 150, txt, kd[0], kd[1], sz, WARM if i == 0 else GREY, a * qq, italic=(kind == "serif"),
             rise=(1 - qq) * 16)


def g_montage_nums(L, t):
    for i in range(7):
        s = _m0 + i * _md
        if s <= t < s + _md:
            txt = str(i + 1) if i < 6 else "?"
            stamp(L, t, s, s + _md, txt, x=W * 0.5, y=H * 0.45, col=YEL if i < 6 else (214, 40, 40), size=300, rot=0)


def g_hud(L, t):
    spans = [(G[2], G[3] - 0.2, "ADAY 1/7"), (G[3], G[4] - 0.2, "ADAY 2/7"), (G[4], G[5] - 0.2, "ADAY 3/7"),
             (G[5], G[6] - 0.2, "ADAY 4/7"), (G[6], G[7] - 0.2, "ADAY 5/7"), (G[7], G[8] - 0.2, "ADAY 6/7"),
             (G[8], G[10] - 0.2, "ÖZEL ADAY"), (G[10], T(10, "Sen") - 0.2, "ADAY 7/7")]
    for s, e, txt in spans:
        a = window(t, s + 0.4, e, 0.4, 0.3)
        if a <= 0:
            continue
        L.alpha_composite(set_alpha(TOP, a))
        col = RED if txt == "ÖZEL ADAY" else GOLD
        ImageDraw.Draw(L).rectangle([150, 92, 156, 148], fill=col + (int(235 * a),))
        text(L, 176, 120, txt, "sans", "Bold", 44, col, a, track=0.14, anchor="lm")


def g_chips7(L, t, s, e):
    a = window(t, s, e, 0.4, 0.4)
    if a <= 0:
        return
    shade(L, t, s, e, 0.6)
    text(L, W / 2, 330, "Sen hangisini sahiplenirdin?", "serif", "Regular", 100, WARM, a, italic=True)
    items = ["COMPSOGNATHUS", "VELOZİRAPTOR", "TRICERATOPS", "BRACHIOSAURUS", "PACHYCEPHALOSAURUS", "SPINOSAURUS",
             "T. REX", "TAVUK"]
    for i, it in enumerate(items):
        q = eo(ph(t, s + 0.2 + i * 0.12, 0.4))
        if q <= 0.01:
            continue
        r, c = divmod(i, 4)
        cx = W / 2 + (c - 1.5) * 560
        cy = 620 + r * 210 + (1 - q) * 30
        cw, chh = 520, 140
        im, d = aa(cw, chh)
        d.rounded_rectangle([3, 3, cw * 2 - 3, chh * 2 - 3], radius=chh - 3, fill=(12, 14, 20, 215), outline=GOLD + (255,),
                            width=6)
        put(L, im.resize((cw, chh), Image.LANCZOS), cx, cy, "mm", a * q)
        text(L, cx, cy, it, "sans", "Bold", 38 if len(it) < 14 else 30, WARM, a * q, track=0.06)
    label(L, W / 2, 1100, "YORUMLARA YAZ", a * eo(ph(t, s + 1.2, 0.5)), 44, GOLD, w="Bold", track=0.3)


def title_card(L, t):
    a = window(t, TITLE0 + 0.1, TITLE1, 0.5, 0.5)
    if a <= 0:
        return
    shade(L, t, TITLE0, TITLE1 + 0.3, 0.5)
    label(L, W / 2, 470, "PRATİK ABİ", a * 0.9, 30, GOLD, track=0.6)
    q1 = eo(ph(t, TITLE0 + 0.2, 0.9))
    text(L, W / 2, 640, "Evcil Dinozor", "serif", "Regular", 150, WARM, a * q1, shadow=0.85, rise=(1 - q1) * 20)
    q2 = eo(ph(t, TITLE0 + 0.45, 0.9))
    text(L, W / 2, 810, "Sahiplendirme Rehberi", "serif", "Regular", 130, GOLD, a * q2, italic=True, shadow=0.85,
         rise=(1 - q2) * 20)
    meme(L, t, TITLE0 + 1.2, TITLE1, "(sorumluluk kabul edilmez)", y=980, size=60, col=WARM, rot=3, stroke=6)


CARD = {
    2: ("Compsognathus", [("Boy", "~70 cm (kuyrukla)"), ("Ağırlık", "~3 kg"), ("Mama", "kertenkele"), ("Yaşadığı yer", "Avrupa")], 4),
    3: ("Veloziraptor", [("Boy", "1,5–2 m"), ("Ağırlık", "~15 kg"), ("Pençe", "6,5+ cm"), ("Kanepe ömrü", "1 gün")], 2),
    4: ("Triceratops", [("Ağırlık", "6–12 ton"), ("Beslenme", "otçul"), ("Su", "yüzlerce L/gün"), ("Bahçe", "biter")], 2),
    5: ("Brachiosaurus", [("Ağırlık", "30+ ton"), ("Bitki", "200+ kg/gün (tahmin)"), ("Ulaşır", "üst kat balkonlar")], 1),
    6: ("Pachycephalosaurus", [("Kafa kubbesi", "25 cm'ye kadar"), ("Anahtar", "gereksiz"), ("Sigorta", "red")], 2),
    7: ("Spinosaurus", [("Boy", "~15 m"), ("Yüzme", "var"), ("Menü", "balık (ve sen)")], 1),
    8: ("Tyrannosaurus rex", [("Ağırlık", "9+ ton (Sue)"), ("Büyüme", "~5 kg/gün (ergen)"), ("Mama", "3.500+ TL/gün")], 0),
}



# ======================= v47: kurgu =======================
FALLBACK = {}


def have(name):
    return (MED / f"{name}.mp4").exists()


def C_(name, t0, t1, off=0.0, z=(1.0, 1.07), xf=0.3, **kw):
    if not have(name):
        name = FALLBACK.get(name, "hava_3")
        off = 2.0
    return clip(name, t0, t1, off=off, z=z, xf=xf, **kw)


PFB = {"w_suri_1": ("kurtcuk_2", 3.0), "w_suri_2": ("kurtcuk_2", 8.0), "w_boto_1": ("nehir_3", 12.0),
       "w_boto_2": ("nehir_1", 14.0), "w_boto2_1": ("nehir_3", 12.0), "w_boto2_2": ("nehir_1", 14.0)}


def P_(stem, t0, t1, z=(1.0, 1.1), xf=0.3, **kw):
    try:
        return photo(pf(stem), t0, t1, z=z, xf=xf, card=True, **kw)
    except FileNotFoundError:
        n, o = PFB.get(stem, ("hava_3", 5.0))
        return clip(n, t0, t1, off=o, xf=xf)


def seq(items, end):
    """items: [(t0, fn, args...)] -> kesimler; her kesim bir sonrakinin başına kadar sürer"""
    out = []
    for i, it in enumerate(items):
        t0 = it[0]
        t1 = items[i + 1][0] if i + 1 < len(items) else end
        kind = it[1]
        if kind == "c":
            name, off = it[2], it[3] if len(it) > 3 else 0.0
            kw = it[4] if len(it) > 4 else {}
            out.append(C_(name, t0, t1, off=off, **kw))
        elif kind == "p":
            kw = it[3] if len(it) > 3 else {}
            out.append(P_(it[2], t0, t1, **kw))
        else:
            out.append(dark(t0, t1, xf=it[2] if len(it) > 2 else 0.3))
    return out


def tw(seg, key, at=None, nth=0):
    return T(seg, key, at, nth) - 0.1


C = []
# --- teaser ---
C += seq([(0.0, "c", "hava_3", 2.0, dict(z=(1.18, 1.0), xf=0.0)),
          (0.9, "p", "w_jaguar_1", dict(z=(1.15, 1.25), xf=0.0)),
          (1.7, "c", "pirana_1", 5.0, dict(xf=0.0, z=(1.1, 1.2))),
          (2.5, "c", "simsek_2", 8.0, dict(xf=0.0)),
          (3.2, "c", "sinek_2", 4.0, dict(xf=0.0, z=(1.2, 1.35))),
          (3.9, "p", "w_anakonda_1", dict(z=(1.1, 1.25), xf=0.0)),
          (4.6, "c", "firtina_1", 3.0, dict(xf=0.0)),
          (5.3, "c", "kurbaga_1", 0.5, dict(xf=0.0)),
          (6.0, "d", 0.0)], G[1] - 0.1)
# --- 1: giriş ---
C += seq([(G[1] - 0.1, "c", "sarmasik_1", 2.0, dict(z=(1.0, 1.12), xf=0.5)),
          (tw(1, "Birkaç"), "c", "agac_2", 3.0),
          (tw(1, "Telefonun"), "d", 0.3),
          (tw(1, "Amazon", 11), "c", "hava_3", 0.0, dict(z=(1.0, 1.1))),
          (tw(1, "Burası"), "c", "nehir_1", 3.0),
          (tw(1, "İçinde"), "c", "kanopi_1", 1.0),
          (tw(1, "Bu", 21), "c", "sis_2", 2.0),
          (tw(1, "Aslında"), "c", "koy_2", 3.0),
          (tw(1, "Ama", 32), "c", "papagan_1", 1.0),
          (tw(1, "Bilinen"), "c", "tukan_2", 18.0),
          (tw(1, "Ve", 40), "c", "dere_1", 5.0),
          (tw(1, "Kulağa"), "c", "tembel_2", 1.0),
          (tw(1, "Bakalım"), "c", "hava_1", 5.0),
          (TITLE0 - 0.2, "c", "hava_3", 10.0, dict(z=(1.04, 1.12), xf=0.5))], TITLE1 + 0.2)
# --- gün kartları ---
DCBG = {2: ("sis_1", 2.0), 3: ("sinek_2", 6.0), 4: ("agac_1", 4.0), 5: ("gece_2", 8.0), 6: ("nehir_3", 2.0),
        7: ("ucak_2", 1.0), 8: ("dere_1", 15.0)}
for k in range(2, 9):
    n, o = DCBG[k]
    C.append(C_(n, DC[k] - 0.1, G[k] - 0.1, off=o, z=(1.12, 1.0), xf=0.5))
# --- 2: gün 1 su ---
C += seq([(G[2] - 0.1, "c", "sis_1", 6.0, dict(xf=0.4)),
          (tw(2, "İlk"), "c", "damla_1", 2.0),
          (tw(2, "Burada", 4), "c", "agac_2", 3.0),
          (tw(2, "Ter", 8), "c", "firtina_2", 0.0),
          (tw(2, "Bir", 13), "c", "yuruyen_1", 2.0),
          (tw(2, "En", 19), "c", "damla_2", 1.0),
          (tw(2, "İnsan"), "d", 0.2),
          (tw(2, "İşin"), "c", "nehir_1", 10.0),
          (tw(2, "Ama", 31), "c", "kaynat_2", 0.0),
          (tw(2, "İçinde", 35), "c", "nehir_1", 30.0),
          (tw(2, "Peki", 39), "c", "firtina_1", 6.0),
          (tw(2, "Yani", 45), "c", "damla_2", 6.0, dict(z=(1.1, 1.2))),
          (tw(2, "İkinci", 49), "c", "sarmasik_1", 10.0),
          (tw(2, "Bir", 55), "c", "agac_2", 8.0),
          (tw(2, "Çünkü", 60), "c", "kanopi_2", 1.0),
          (tw(2, "Ve", 70), "c", "karinca_2", 4.0),
          (tw(2, "Gece", 72), "c", "karinca_3", 2.0),
          (tw(2, "Yerel", 77), "c", "hamak_1", 1.0),
          (tw(2, "Tamam", 81), "c", "gece_2", 3.0),
          (tw(2, "Ve", 85), "d", 0.0),
          (tw(2, "Bu", 92), "c", "uluyan_2", 1.0, dict(xf=0.0)),
          (tw(2, "Karada"), "c", "uluyan_1", 12.0),
          (tw(2, "Yani", 100), "c", "gece_2", 12.0),
          (tw(2, "Amazon", 103), "c", "hava_3", 15.0)], DC[3] - 0.1)
# --- 3: gün 2 böcekler ---
C += seq([(G[3] - 0.1, "c", "sis_2", 8.0, dict(xf=0.4)),
          (tw(3, "Uyandın"), "c", "sinek_2", 2.0, dict(z=(1.0, 1.15))),
          (tw(3, "Ama", 6), "c", "sinek_3", 2.0),
          (tw(3, "Amazon", 10), "c", "sinek_2", 10.0, dict(z=(1.2, 1.3))),
          (tw(3, "Daha", 16), "d", 0.0),
          (tw(3, "Bazı", 17), "c", "kurtcuk_2", 3.0),
          (tw(3, "Sivrisinek", 21), "c", "sinek_3", 8.0),
          (tw(3, "Evet", 31), "c", "sinek_3", 5.0, dict(z=(1.3, 1.5))),
          (tw(3, "Bu", 33), "c", "sarmasik_2", 2.0),
          (tw(3, "Neyse"), "c", "sarmasik_1", 15.0),
          (tw(3, "Bir", 39), "c", "karinca_3", 5.0),
          (tw(3, "Ama", 43), "p", "w_kursun_1", dict(xf=0.0)),
          (tw(3, "Bilim", 47), "d", 0.3),
          (tw(3, "Acısı", 53), "p", "w_kursun_2"),
          (tw(3, "Daha", 58), "p", "w_kursun_3"),
          (tw(3, "Sen", 66), "c", "tembel_1", 1.0),
          (tw(3, "Ve", 70), "p", "w_ordu_1"),
          (tw(3, "Yuva"), "p", "w_ordu_2"),
          (tw(3, "Bazı", 86), "c", "yaprakkesen_1", 1.0),
          (tw(3, "İkinci", 93), "c", "karinca_2", 10.0)], DC[4] - 0.1)
# --- 4: gün 3 açlık ---
C += seq([(G[4] - 0.1, "c", "yuruyen_1", 2.0, dict(xf=0.4)),
          (tw(4, "Etrafında"), "c", "agac_1", 2.0),
          (tw(4, "Mesela"), "p", "w_ceviz_1"),
          (tw(4, "Bu", 13), "c", "kanopi_3", 1.0),
          (tw(4, "cevizler"), "p", "w_ceviz_3"),
          (tw(4, "Bu", 22), "p", "w_ceviz_1", dict(z=(1.25, 1.4))),
          (tw(4, "Yani", 26), "d", 0.0),
          (tw(4, "Peki", 31), "c", "kurbaga_1", 0.0, dict(xf=0.0)),
          (tw(4, "Doğada"), "p", "w_kurbaga_1"),
          (tw(4, "Bu", 43), "p", "w_kurbaga_2"),
          (tw(4, "Bir", 51), "p", "w_kakao_2"),
          (tw(4, "Yani", 58), "p", "w_kakao_1"),
          (tw(4, "Geriye"), "p", "w_suri_3"),
          (tw(4, "Hem", 72), "p", "w_suri_2"),
          (tw(4, "Ama", 75), "p", "w_suri_1")], DC[5] - 0.1)
# --- 5: gün 4 jaguar ---
C += seq([(G[5] - 0.1, "c", "karinca_3", 5.0, dict(xf=0.4)),
          (tw(5, "Bu", 7), "c", "gece_2", 15.0),
          (tw(5, "Jaguar", 10), "p", "w_jaguar_2", dict(xf=0.0, z=(1.0, 1.18))),
          (tw(5, "Amerika"), "p", "w_jaguar_3"),
          (tw(5, "Isırığı"), "p", "w_jaguar_1", dict(z=(1.05, 1.3))),
          (tw(5, "Kaplumbağa"), "p", "w_jaguar_4"),
          (tw(5, "Şimdi", 21), "c", "gece_2", 5.0),
          (tw(5, "Ama", 23), "c", "kanopi_3", 6.0),
          (tw(5, "Ama", 31), "p", "w_jaguar_2", dict(z=(1.15, 1.35), fy=0.4)),
          (tw(5, "Ama", 45), "p", "w_pekari_1"),
          (tw(5, "Beyaz"), "p", "w_pekari_2"),
          (tw(5, "Böyle"), "c", "kanopi_1", 8.0),
          (tw(5, "Dördüncü", 65), "p", "w_jaguar_2", dict(z=(1.3, 1.5), fy=0.35))], DC[6] - 0.1)
# --- 6: gün 5 nehir ---
C += seq([(G[6] - 0.1, "c", "nehir_3", 5.0, dict(xf=0.4)),
          (tw(6, "Aklına"), "c", "pirana_1", 2.0),
          (tw(6, "Filmlerde"), "c", "pirana_1", 15.0, dict(z=(1.2, 1.35))),
          (tw(6, "Bu", 16), "d", 0.0),
          (tw(6, "Hatta"), "c", "tekne_2", 5.0),
          (tw(6, "Gerçekte"), "c", "tekne_2", 18.0, dict(z=(1.1, 1.2))),
          (tw(6, "Ama", 39), "d", 0.0),
          (tw(6, "Mesela", 43), "p", "w_yilanbaligi_1"),
          (tw(6, "Evdeki"), "p", "w_yilanbaligi_2"),
          (tw(6, "Bir", 53), "p", "w_anakonda_1"),
          (tw(6, "5", 57), "p", "w_anakonda_2"),
          (tw(6, "Bir", 63), "p", "w_kayman_1"),
          (tw(6, "Ama", 68), "p", "w_boto2_1"),
          (tw(6, "Evet", 72), "p", "w_boto2_4"),
          (tw(6, "Yerel", 78), "p", "w_boto2_2"),
          (tw(6, "Yani", 84), "c", "nehir_1", 20.0),
          (tw(6, "Çünkü", 87), "p", "w_kayman_2", dict(z=(1.0, 1.35)))], DC[7] - 0.1)
# --- 7: gün 6 fırtına ---
C += seq([(G[7] - 0.1, "c", "ucak_2", 0.0, dict(xf=0.4)),
          (tw(7, "Amazon", 3), "c", "firtina_1", 2.0),
          (tw(7, "Burada", 7), "c", "firtina_3", 1.0),
          (tw(7, "Yani", 11), "d", 0.2),
          (tw(7, "Dakikalar"), "c", "firtina_2", 6.0),
          (tw(7, "dallar"), "c", "simsek_2", 6.0, dict(xf=0.0)),
          (tw(7, "sen", 21), "c", "firtina_2", 1.0),
          (tw(7, "Bu", 23), "c", "sis_2", 10.0),
          (tw(7, "Ağaçlar"), "c", "sis_1", 15.0),
          (tw(7, "Bilim"), "c", "hava_1", 20.0),
          (tw(7, "Ateş"), "c", "ates_2", 3.0),
          (tw(7, "Ama", 43), "c", "yuruyen_1", 8.0),
          (tw(7, "Günlerce"), "c", "firtina_3", 4.0),
          (tw(7, "Bu", 53), "c", "ates_1", 4.0),
          (tw(7, "Evet", 56), "c", "ates_1", 9.0, dict(z=(1.1, 1.2)))], DC[8] - 0.1)
# --- 8: gün 7 kurtuluş ---
C += seq([(G[8] - 0.1, "c", "yuruyen_1", 14.0, dict(xf=0.4)),
          (tw(8, "Ama", 6), "c", "dere_1", 10.0),
          (tw(8, "Çünkü", 9), "c", "dere_2", 2.0),
          (tw(8, "Bu", 14), "d", 0.3),
          (tw(8, "1971"), "c", "bulut_1", 1.0),
          (tw(8, "Juliane", 23), "c", "ucak_2", 2.0),
          (tw(8, "Ve", 28), "c", "hava_3", 20.0),
          (tw(8, "Köprücük"), "d", 0.3),
          (tw(8, "Ama", 35), "c", "dere_1", 30.0),
          (tw(8, "11"), "c", "kanopi_2", 6.0),
          (tw(8, "Ve", 45), "c", "hava_1", 30.0),
          (tw(8, "Önce", 57), "d", 0.3),
          (tw(8, "Ve", 62), "c", "dere_2", 4.0),
          (tw(8, "Dereyi"), "c", "nehir_3", 12.0),
          (tw(8, "uzaktan"), "c", "tekne_2", 0.0),
          (tw(8, "Kurtuldun"), "c", "nehir_1", 25.0, dict(xf=0.0))], G[9] - 0.1)
# --- 9: sonuç ---
C += seq([(G[9] - 0.1, "c", "hava_3", 22.0, dict(xf=0.5)),
          (tw(9, "Ama", 3), "c", "sinek_3", 4.0),
          (tw(9, "Amazon"), "c", "papagan_2", 1.0),
          (tw(9, "Ve", 16), "c", "kapibara_1", 1.0),
          (tw(9, "Sen", 21), "d", 0.4)], TOTAL)


# ======================= v47: grafikler =======================
_big0, _info0, _quote0 = big, info_card, quote


def big(L, t, s, e, *a, **k):
    shade(L, t, s, e, 0.5)
    _big0(L, t, s, e, *a, **k)


def info_card(L, t, s, e, *a, **k):
    shade(L, t, s, e, 0.55)
    _info0(L, t, s, e, *a, **k)


def quote(L, t, s, e, *a, **k):
    shade(L, t, s, e, 0.4)
    _quote0(L, t, s, e, *a, **k)


DAYS = {2: ("SU VE NEM", (60, 90, 80)), 3: ("BÖCEKLER", (45, 70, 50)), 4: ("AÇLIK", (55, 45, 30)),
        5: ("JAGUAR", (50, 30, 20)), 6: ("NEHİR", (55, 25, 35)), 7: ("FIRTINA", (80, 18, 12)), 8: ("KURTULUŞ", (70, 10, 60))}


def day_card(L, t, k):
    s, e = DC[k], G[k] + 0.2
    a = window(t, s, e, 0.4, 0.5)
    if a <= 0:
        return
    shade(L, t, s, e, 0.45)
    q = eo(ph(t, s + 0.1, 0.7))
    label(L, W / 2, 330, "AMAZON'DA 7 GÜN", a * 0.9, 30, GOLD, track=0.5)
    text(L, W / 2, 520, f"{k - 1}. GÜN", "sans", "Black", 200, WARM, a * q, track=0.04, shadow=0.85, rise=(1 - q) * 30)
    q2 = eo(ph(t, s + 0.4, 0.7))
    text(L, W / 2, 700, DAYS[k][0], "serif", "Regular", 110, GOLD, a * q2, italic=True, shadow=0.85, rise=(1 - q2) * 20)
    vals = DAYS[k][1]
    prev = DAYS[k - 1][1] if k > 2 else (100, 100, 100)
    for i, (nm, col) in enumerate((("SU", CYAN), ("ENERJİ", YEL), ("MORAL", (255, 120, 120)))):
        qq = eo(ph(t, s + 0.8 + i * 0.25, 0.9))
        v = prev[i] + (vals[i] - prev[i]) * qq
        y = 900 + i * 110
        x0, x1 = 900, 1800
        d = ImageDraw.Draw(L)
        text(L, x0 - 40, y, nm, "sans", "Bold", 44, WARM, a * min(1, qq * 3), anchor="rm")
        d.rounded_rectangle([x0, y - 26, x1, y + 26], radius=26, fill=(255, 255, 255, int(40 * a)))
        d.rounded_rectangle([x0, y - 26, x0 + max(52, (x1 - x0) * v / 100), y + 26], radius=26,
                            fill=col + (int(235 * a),))
        text(L, x1 + 40, y, f"%{int(round(v))}", "sans", "Bold", 44, col, a * min(1, qq * 3), anchor="lm")


def g_hud47(L, t):
    for k in range(2, 9):
        s, e = G[k] + 0.4, (DC[k + 1] if k < 8 else G[9]) - 0.3
        a = window(t, s, e, 0.4, 0.3)
        if a <= 0:
            continue
        L.alpha_composite(set_alpha(TOP, a))
        ImageDraw.Draw(L).rectangle([150, 92, 156, 148], fill=GOLD + (int(235 * a),))
        text(L, 176, 120, f"GÜN {k - 1}/7 · {DAYS[k][0]}", "sans", "Bold", 44, GOLD, a, track=0.12, anchor="lm")


def g_pain(L, t, s, e, t_top):
    a = window(t, s, e, 0.4, 0.4)
    if a <= 0:
        return
    shade(L, t, s, e, 0.5)
    text(L, W / 2, 260, "Böcek sokması acı ölçeği", "serif", "Regular", 90, WARM, a, italic=True)
    rows = [("1", "Ter arısı", 0.25), ("2", "Bal arısı", 0.5), ("3", "Hasat karıncası", 0.75), ("4+", "KURŞUN KARINCA", 1.0)]
    for i, (lv, nm, frac) in enumerate(rows):
        tt = s + 0.4 + i * 0.6 if i < 3 else t_top
        q = eo(ph(t, tt, 0.6))
        if q <= 0.01:
            continue
        y = 520 + i * 170
        col = (214, 40, 40) if i == 3 else GOLD
        d = ImageDraw.Draw(L)
        d.rounded_rectangle([700, y - 50, 700 + 1300 * frac * q, y + 50], radius=50, fill=col + (int(220 * a),))
        text(L, 640, y, lv, "sans", "Black", 80, col, a * q, anchor="rm")
        text(L, 740, y, nm, "sans", "Bold", 52, (255, 255, 255), a * q, anchor="lm")
    cite(L, t, s + 0.5, e, "Schmidt sokma acısı indeksi (Justin O. Schmidt)")


def g_rainbars(L, t, s, e):
    a = window(t, s, e, 0.4, 0.4)
    if a <= 0:
        return
    shade(L, t, s, e, 0.55)
    text(L, 200, 300, "Yıllık yağış", "serif", "Regular", 90, WARM, a, anchor="lm")
    rows = [("AMAZON", 2.3, CYAN, "2 metreden fazla"), ("İSTANBUL", 0.8, GOLD, "yaklaşık 0,8 metre")]
    for i, (nm, v, col, lab) in enumerate(rows):
        q = eo(ph(t, s + 0.3 + i * 0.5, 1.0))
        y = 620 + i * 260
        text(L, 200, y, nm, "sans", "Bold", 64, WARM, a * clamp(q * 3), anchor="lm")
        ImageDraw.Draw(L).rounded_rectangle([760, y - 55, 760 + max(30, 1500 * v / 2.4 * q), y + 55], radius=28,
                                            fill=col + (int(225 * a),))
        text(L, 790, y + 110, lab, "sans", "SemiBold", 44, col, a * q, anchor="lm")


def g_flow(L, t, s, e, times):
    a = window(t, s, e, 0.3, 0.4)
    if a <= 0:
        return
    items = ["DERE", "NEHİR", "İNSANLAR"]
    for i, (it, tt) in enumerate(zip(items, times)):
        q = eo(ph(t, tt, 0.4))
        if q <= 0.01:
            continue
        cx = W / 2 + (i - 1) * 720
        cw, chh = 520, 150
        im, d = aa(cw, chh)
        d.rounded_rectangle([3, 3, cw * 2 - 3, chh * 2 - 3], radius=chh - 3, fill=(12, 14, 20, 225), outline=CYAN + (255,),
                            width=7)
        put(L, im.resize((cw, chh), Image.LANCZOS), cx, 1120, "mm", a * q, scale=0.9 + 0.1 * q)
        text(L, cx, 1120, it, "sans", "Black", 60, WARM, a * q, track=0.08)
        if i > 0:
            text(L, cx - 360, 1120, "→", "sans", "Black", 90, CYAN, a * q)


def g_days_grid(L, t, s, e):
    a = window(t, s, e, 0.4, 0.4)
    if a <= 0:
        return
    shade(L, t, s, e, 0.6)
    text(L, W / 2, 330, "Sen kaçıncı günde pes ederdin?", "serif", "Regular", 100, WARM, a, italic=True)
    items = [f"{i}. GÜN" for i in range(1, 8)] + ["HİÇ!"]
    for i, it in enumerate(items):
        q = eo(ph(t, s + 0.2 + i * 0.12, 0.4))
        if q <= 0.01:
            continue
        r, c = divmod(i, 4)
        cx = W / 2 + (c - 1.5) * 560
        cy = 620 + r * 210 + (1 - q) * 30
        cw, chh = 480, 140
        im, d = aa(cw, chh)
        d.rounded_rectangle([3, 3, cw * 2 - 3, chh * 2 - 3], radius=chh - 3, fill=(12, 14, 20, 215), outline=GOLD + (255,),
                            width=6)
        put(L, im.resize((cw, chh), Image.LANCZOS), cx, cy, "mm", a * q)
        text(L, cx, cy, it, "sans", "Bold", 48, WARM, a * q, track=0.06)
    label(L, W / 2, 1100, "YORUMLARA YAZ", a * eo(ph(t, s + 1.2, 0.5)), 44, GOLD, w="Bold", track=0.3)


def title47(L, t):
    a = window(t, TITLE0 + 0.1, TITLE1, 0.5, 0.5)
    if a <= 0:
        return
    shade(L, t, TITLE0, TITLE1 + 0.3, 0.5)
    label(L, W / 2, 470, "PRATİK ABİ", a * 0.9, 30, GOLD, track=0.6)
    q1 = eo(ph(t, TITLE0 + 0.2, 0.9))
    text(L, W / 2, 640, "Amazon Ormanında", "serif", "Regular", 150, WARM, a * q1, shadow=0.85, rise=(1 - q1) * 20)
    q2 = eo(ph(t, TITLE0 + 0.45, 0.9))
    text(L, W / 2, 810, "7 Gün", "serif", "Regular", 170, GOLD, a * q2, italic=True, shadow=0.85, rise=(1 - q2) * 20)
    meme(L, t, TITLE0 + 1.2, TITLE1, "(hayatta kalabilir misin?)", y=990, size=64, col=WARM, rot=3, stroke=6)


def overlay(t):
    L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    # teaser
    meme(L, t, 0.15, 5.2, "7 GÜN", y=H * 0.45, size=300, col=YEL)
    meme(L, t, 5.3, 6.9, "HAYATTA KALABİLİR MİSİN?", y=H * 0.45, size=130, col=(255, 255, 255))
    for x in (0.9, 1.7, 2.5, 3.2, 3.9, 4.6, 5.3):
        flash(L, t, x, 0.12, amt=0.5)
    # 1 giriş
    g_phone(L, t, T(1, "Telefonun") - 0.1, T(1, "Amazon", 11) - 0.2, msg="SİNYAL YOK", sub="harita da yok")
    big(L, t, T(1, "Amazon", 11) - 0.1, T(1, "Burası") - 0.2, "AMAZON", "yağmur ormanı", y=620, size=230)
    big(L, t, T(1, "5,5") - 0.2, T(1, "İçinde") - 0.2, "5,5 milyon km²", "≈ Türkiye'nin 7 katı", y=640, size=190)
    big(L, t, T(1, "390") - 0.2, T(1, "Bu", 21) - 0.2, "390 milyar", "ağaç", y=640, size=210)
    cite(L, t, T(1, "390") - 0.2, T(1, "Bu", 21) - 0.2, "ter Steege ve ark., Science, 2013")
    meme(L, t, T(1, "akciğeri") - 0.2, T(1, "Aslında") - 0.15, "“DÜNYANIN AKCİĞERİ”?", y=1150, size=120, col=YEL)
    stamp(L, t, T(1, "tüketiyor") - 0.1, T(1, "Ama", 32) - 0.15, "EFSANE", y=H * 0.42, size=170)
    big(L, t, T(1, "onda") - 0.2, T(1, "Ve", 40) - 0.2, "1 / 10", "bilinen türlerin evi", y=640, size=230)
    stamp(L, t, T(1, "Kurtarma") - 0.1, T(1, "Kulağa") - 0.15, "GÖREV: 7 GÜN", y=H * 0.42, size=140)
    meme(L, t, T(1, "kolay") - 0.1, T(1, "Bakalım") - 0.15, "KOLAY MI?", y=1150, size=140, col=YEL)
    title47(L, t)
    # gün kartları + HUD
    for k in range(2, 9):
        day_card(L, t, k)
    g_hud47(L, t)
    # 2 gün 1
    meme(L, t, T(2, "nem") - 0.1, T(2, "Burada", 4) - 0.15, "SORUN: NEM", y=1150, size=130, col=YEL)
    big(L, t, T(2, "yüzde") - 0.2, T(2, "Ter", 8) - 0.2, "%80 nem", "çoğu zaman", y=640, size=220)
    meme(L, t, T(2, "kurumuyor") - 0.1, T(2, "Bir", 13) - 0.15, "TER KURUMUYOR", y=1150, size=120)
    meme(L, t, T(2, "çamaşır") - 0.1, T(2, "En", 19) - 0.15, "TİŞÖRT: SIKMALIK", y=1150, size=130, col=YEL, rot=-3)
    stamp(L, t, T(2, "susuzluk") - 0.1, T(2, "İnsan") - 0.15, "SUSUZLUK", y=H * 0.42, size=160)
    big(L, t, T(2, "üç", 24) - 0.2, T(2, "İşin") - 0.2, "3 gün", "susuz dayanma sınırı (yaklaşık)", y=640, size=240)
    meme(L, t, T(2, "kaynatmadan") - 0.1, T(2, "İçinde", 35) - 0.15, "KAYNATMADAN İÇME!", y=1150, size=120, col=RED)
    g_needs(L, t, T(2, "bakteri") - 0.1, T(2, "Peki", 39) - 0.15,
            [("Bakteri", T(2, "bakteri"), "no"), ("Parazit", T(2, "parazit"), "no"), ("...ne ararsan", T(2, "ararsan"), "warn")],
            "NEHİR SUYU", x=1850, y=330)
    meme(L, t, T(2, "yağmur", 41) - 0.1, T(2, "Yani", 45) - 0.15, "1. YOL: YAĞMUR SUYU", y=1150, size=120, col=CYAN)
    meme(L, t, T(2, "yaprak") - 0.1, T(2, "İkinci", 49) - 0.15, "BARDAK = YAPRAK", y=1150, size=130, col=YEL)
    meme(L, t, T(2, "sarmaşıklar") - 0.1, T(2, "Bir", 55) - 0.15, "2. YOL: SARMAŞIK", y=1150, size=120, col=CYAN)
    hint(L, t, T(2, "Kesince") - 0.1, T(2, "Bir", 55) - 0.2, "Not: Her sarmaşık içilmez. Hangisi olduğunu yerel halk bilir.")
    meme(L, t, T(2, "loş") - 0.1, T(2, "Çünkü", 60) - 0.15, "GÜNDÜZ BİLE LOŞ", y=1150, size=120)
    meme(L, t, T(2, "Kötü") - 0.1, T(2, "Gece", 72) - 0.15, "YERDE UYUMAK: KÖTÜ FİKİR", y=1150, size=110, col=RED)
    meme(L, t, T(2, "hamakta") - 0.1, T(2, "Tamam", 81) - 0.15, "HAMAK = HAYAT", y=1150, size=130, col=YEL)
    shade(L, t, T(2, "Ve", 85) - 0.1, T(2, "Bu", 92) - 0.1, 0.3)
    meme(L, t, T(2, "canavar", 87) - 0.1, T(2, "Korkma") - 0.1, "?!", y=H * 0.45, size=300, col=RED, rot=-6)
    lower_third(L, t, T(2, "uluyan") - 0.1, T(2, "Yani", 100) - 0.3, "Uluyan maymun", "Alouatta · karanın en gürültülülerinden")
    meme(L, t, T(2, "kilometrelerce") - 0.1, T(2, "Yani", 100) - 0.15, "KİLOMETRELERCE", y=1150, size=120, col=YEL)
    meme(L, t, T(2, "uyku") - 0.1, T(2, "Amazon", 103) - 0.15, "UYKU: 0", y=H * 0.45, size=220, col=RED, rot=-4)
    meme(L, t, T(2, "Amazon", 103) - 0.05, E(2) + 0.3, "AMAZON'A HOŞ GELDİN", y=1150, size=120, col=YEL)
    # 3 gün 2
    meme(L, t, T(3, "sivrisinek") - 0.1, T(3, "Ama", 6) - 0.15, "ISIRIK SAYISI: ∞", y=1150, size=130, col=RED)
    meme(L, t, T(3, "balkonda") - 0.1, T(3, "Amazon", 10) - 0.15, "BALKON SİVRİSİNEĞİ DEĞİL", y=1150, size=110, col=YEL)
    g_needs(L, t, T(3, "sıtma") - 0.15, T(3, "Daha", 16) - 0.15,
            [("Sıtma", T(3, "sıtma"), "warn"), ("Dang humması", T(3, "dang"), "warn")], "TAŞIYABİLİRLER", x=1850, y=330)
    info_card(L, t, T(3, "Bazı", 17) - 0.05, T(3, "Sivrisinek", 21) - 0.15, "AT SİNEĞİ",
              [("yumurtalarını sivrisineğe yapıştırır", "sans", 70), ("Dermatobia hominis", "serif", 56)])
    hint(L, t, T(3, "Sivrisinek", 21), T(3, "Evet", 31) - 0.2, "Temsili görüntü")
    meme(L, t, T(3, "kurtçuk") - 0.1, T(3, "Evet", 31) - 0.1, "DERİNİN ALTINDA KURTÇUK", y=1150, size=110, col=RED)
    meme(L, t, T(3, "Evet", 31) - 0.05, T(3, "Bu", 33) - 0.15, "EVET.", y=H * 0.45, size=240, col=YEL)
    meme(L, t, T(3, "uzun", 34) - 0.1, T(3, "Neyse") - 0.15, "UZUN KOL = HAYAT", y=1150, size=130, col=YEL)
    meme(L, t, T(3, "soktu") - 0.05, T(3, "Ama", 43) + 0.6, "AAAH!", y=H * 0.45, size=280, col=RED, rot=-8)
    flash(L, t, T(3, "soktu") - 0.05, 0.25, col=(255, 60, 40), amt=0.6)
    lower_third(L, t, T(3, "kurşun", 45) - 0.1, T(3, "Bilim", 47) - 0.3, "Kurşun karınca", "Paraponera clavata")
    g_pain(L, t, T(3, "Bilim", 47) - 0.05, T(3, "Acısı", 53) - 0.15, T(3, "tepede") - 0.3)
    big(L, t, T(3, "24") - 0.2, T(3, "Daha", 58) - 0.2, "24 saat", "acının sürebildiği süre", y=1000, size=200)
    info_card(L, t, T(3, "Sateré") - 0.2, T(3, "Sen", 66) - 0.15, "SATERÉ-MAWÉ HALKI",
              [("yetişkinliğe geçiş: karıncalı eldiven", "sans", 66), ("Brezilya Amazon'u", "sans", 46)])
    meme(L, t, T(3, "Sen", 66) - 0.05, T(3, "onlar") - 0.1, "SEN: 1 SOKMA = AĞLAMA", y=1150, size=110, col=YEL)
    meme(L, t, T(3, "onlar") - 0.05, T(3, "Ve", 70) - 0.15, "ONLAR: ELDİVENLE DANS", y=1150, size=110, col=GREEN)
    lower_third(L, t, T(3, "ordu") - 0.1, T(3, "Yuva") - 0.3, "Ordu karıncası", "Eciton · yuvası yok, hep yürür")
    big(L, t, T(3, "yüz", 74) - 0.2, T(3, "Yuva") - 0.2, "100.000+", "bir kolonideki karınca", y=1000, size=200)
    meme(L, t, T(3, "Ücretsiz") - 0.1, T(3, "İkinci", 93) - 0.15, "ÜCRETSİZ İLAÇLAMA", y=1150, size=130, col=YEL)
    stamp(L, t, T(3, "elini") - 0.2, E(3) + 0.3, "DOKUNMA!", y=H * 0.42, size=170)
    # 4 gün 3
    meme(L, t, T(4, "midenden") - 0.1, T(4, "Etrafında") - 0.15, "GURUL GURUL", y=1150, size=140, col=YEL, rot=-3)
    g_needs(L, t, T(4, "hangisi") - 0.1, T(4, "Mesela") - 0.15,
            [("Yenir mi?", T(4, "hangisi"), "warn"), ("Zehirli mi?", T(4, "zehirler"), "warn")], "BİLMİYORSUN", x=1850, y=330)
    lower_third(L, t, T(4, "Brezilya") - 0.1, T(4, "Bu", 13) - 0.3, "Brezilya cevizi", "Bertholletia excelsa")
    big(L, t, T(4, "18") - 0.2, T(4, "cevizler") - 0.2, "18 kat", "ağaç boyu (yaklaşık)", y=640, size=220)
    big(L, t, T(4, "2,5") - 0.2, T(4, "Bu", 22) - 0.2, "2,5 kg", "tek bir kabuk", y=1000, size=200)
    big(L, t, T(4, "80") - 0.2, T(4, "Yani", 26) - 0.2, "80 km/s", "düşüş hızı", y=1000, size=200)
    stamp(L, t, T(4, "Yani", 26) - 0.05, T(4, "Peki", 31) - 0.15, "DİKKAT: CEVİZ DÜŞEBİLİR", y=H * 0.45, size=110)
    meme(L, t, T(4, "Çok", 35) - 0.1, T(4, "Sakın") - 0.1, "ÇOK TATLI...", y=1150, size=130, col=YEL)
    stamp(L, t, T(4, "Sakın") - 0.1, T(4, "Doğada") - 0.15, "DOKUNMA!", y=H * 0.42, size=170)
    quote(L, t, T(4, "Beni") - 0.2, T(4, "Bu", 43) - 0.2, "Parlak renk = “Beni yeme, zehirliyim”", size=88)
    lower_third(L, t, T(4, "ok", 44) - 0.1, T(4, "Bir", 51) - 0.3, "Ok kurbağası", "Dendrobatidae ailesi")
    lower_third(L, t, T(4, "kakao") - 0.1, T(4, "Yani", 58) - 0.3, "Kakao", "anavatanı Amazon havzası")
    meme(L, t, T(4, "market") - 0.2, T(4, "Geriye") - 0.15, "EN YAKIN MARKET: ???", y=1150, size=120, col=YEL)
    lower_third(L, t, T(4, "palmiye") - 0.1, T(4, "Hem", 72) - 0.3, "Palmiye kurtçuğu", "bazı yerel halkların besini")
    meme(L, t, T(4, "protein") - 0.1, T(4, "Sen", 73) - 0.1, "PROTEİN!", y=1150, size=150, col=GREEN)
    meme(L, t, T(4, "sucuklu") - 0.1, E(4) + 0.4, "SUCUKLU YUMURTA?", y=1150, size=140, col=YEL, rot=-3)
    # 5 gün 4
    meme(L, t, T(5, "pençe") - 0.1, T(5, "Bu", 7) - 0.1, "PENÇE İZİ", y=1150, size=130, col=YEL)
    stamp(L, t, T(5, "Jaguar", 10) - 0.05, T(5, "Amerika") - 0.1, "JAGUAR", y=H * 0.42, size=200)
    lower_third(L, t, T(5, "Amerika") - 0.1, T(5, "Isırığı") - 0.3, "Jaguar", "Panthera onca · Amerika'nın en büyük kedisi")
    meme(L, t, T(5, "kafatasını") - 0.1, T(5, "Kaplumbağa") - 0.15, "KAFATASI DELEN ISIRIK", y=1150, size=110, col=RED)
    meme(L, t, T(5, "Kaplumbağa") - 0.1, T(5, "Şimdi", 21) - 0.15, "KAPLUMBAĞA KABUĞU: KIRILIR", y=1150, size=110, col=RED)
    meme(L, t, T(5, "kalbin") - 0.1, T(5, "Ama", 23) - 0.15, "TAK TAK TAK", y=H * 0.45, size=200, col=RED)
    stamp(L, t, T(5, "nadir") - 0.2, T(5, "Ama", 31) - 0.15, "SALDIRI: ÇOK NADİR", y=H * 0.42, size=130, col=(60, 170, 90))
    g_needs(L, t, T(5, "Sakın", 34) - 0.1, T(5, "Ama", 45) - 0.15,
            [("Koşma", T(5, "Sakın", 34), "no"), ("Göz temasını kesme", T(5, "Göz"), "ok"),
             ("Kendini büyük göster", T(5, "kendini"), "ok"), ("Yavaşça geri çekil", T(5, "yavaşça"), "ok")],
            "JAGUARLA KARŞILAŞIRSAN", x=1800, y=300)
    lower_third(L, t, T(5, "Beyaz") - 0.1, T(5, "Böyle") - 0.3, "Beyaz dudaklı pekari", "Tayassu pecari · sürü halinde")
    big(L, t, T(5, "yüzlerce") - 0.2, T(5, "Böyle") - 0.2, "YÜZLERCE", "bireylik sürüler", y=640, size=200)
    meme(L, t, T(5, "tırmanmak") - 0.3, T(5, "Dördüncü", 65) - 0.15, "PLAN: AĞACA TIRMAN", y=1150, size=120, col=YEL)
    meme(L, t, T(5, "kediyi") - 0.2, E(5) + 0.4, "PİSİ PİSİ YAPMA", y=1150, size=140, col=RED, rot=-3)
    # 6 gün 5
    stamp(L, t, T(6, "pirana") - 0.1, T(6, "Filmlerde") - 0.1, "PİRANA", y=H * 0.42, size=200)
    meme(L, t, T(6, "iskelete") - 0.2, T(6, "Sana") - 0.1, "FİLMLER: 3 SANİYEDE İSKELET", y=1150, size=110)
    stamp(L, t, T(6, "abartı") - 0.2, T(6, "Hatta") - 0.15, "ABARTI", y=H * 0.42, size=200)
    info_card(L, t, T(6, "1913") - 0.2, T(6, "Gerçekte") - 0.15, "1913 · BREZİLYA",
              [("Theodore Roosevelt'e izletilen pirana gösterisi", "sans", 62), ("günlerce aç bırakılmış piranalar", "sans", 46)])
    meme(L, t, T(6, "nadiren") - 0.1, T(6, "Ama", 39) - 0.15, "SALDIRI: NADİR", y=1150, size=130, col=GREEN)
    shade(L, t, T(6, "Ama", 39) - 0.1, T(6, "Mesela", 43) - 0.1, 0.2)
    meme(L, t, T(6, "Nehirde") - 0.1, T(6, "Mesela", 43) - 0.15, "AMA...", y=H * 0.45, size=220, col=RED)
    lower_third(L, t, T(6, "elektrikli") - 0.1, T(6, "Bazıları") - 0.2, "Elektrikli yılan balığı", "Electrophorus")
    big(L, t, T(6, "860") - 0.2, T(6, "Bir", 53) - 0.2, "860 volt", "evdeki prizin (220 V) ~4 katı", y=640, size=220)
    cite(L, t, T(6, "860") - 0.2, T(6, "Bir", 53) - 0.2, "de Santana ve ark., Nature Communications, 2019")
    lower_third(L, t, T(6, "anakonda") - 0.1, T(6, "5", 57) - 0.2, "Yeşil anakonda", "Eunectes murinus · en ağır yılan")
    big(L, t, T(6, "5", 57) - 0.2, T(6, "Bir", 63) - 0.2, "5+ metre", "zehirsiz ama sararak boğar", y=1000, size=200)
    lower_third(L, t, T(6, "kara") - 0.1, T(6, "Ama", 68) - 0.3, "Kara kayman", "Melanosuchus niger · 5 m'ye kadar")
    stamp(L, t, T(6, "pembe") - 0.1, T(6, "Evet", 72) - 0.1, "PEMBE YUNUS", y=H * 0.42, size=150, col=(220, 80, 140))
    lower_third(L, t, T(6, "Evet", 72) - 0.1, T(6, "Yerel", 78) - 0.3, "Amazon nehir yunusu", "Inia geoffrensis · yaşlandıkça pembeleşir")
    meme(L, t, T(6, "yakışıklı") - 0.1, T(6, "Yani", 84) - 0.15, "GECE: YAKIŞIKLI ADAM (EFSANE)", y=1150, size=100, col=PINK)
    meme(L, t, T(6, "nehir de", 89) - 0.1, E(6) + 0.4, "NEHİR DE SANA BAKIYOR", y=1150, size=120, col=RED)
    # 7 gün 6
    meme(L, t, T(7, "kararıyor") - 0.1, T(7, "Amazon", 3) - 0.1, "BULUTLAR GELDİ", y=1150, size=120)
    big(L, t, T(7, "iki", 8) - 0.2, T(7, "Yani", 11) - 0.2, "2+ metre", "yıllık yağış", y=640, size=220)
    g_rainbars(L, t, T(7, "Yani", 11) - 0.05, T(7, "Dakikalar") - 0.15)
    meme(L, t, T(7, "sele") - 0.2, T(7, "dallar") - 0.15, "SEL!", y=H * 0.45, size=240, col=RED)
    flash(L, t, T(7, "şimşekler") - 0.05, 0.25, amt=0.8)
    meme(L, t, T(7, "sırılsıklamsın") - 0.2, T(7, "Bu", 23) - 0.15, "SIRILSIKLAM", y=1150, size=150, col=CYAN)
    big(L, t, T(7, "milyarlarca") - 0.2, T(7, "Bilim", 33) - 0.2, "milyarlarca ton", "her gün havaya verilen su buharı", y=640, size=170)
    quote(L, t, T(7, "uçan") - 0.2, T(7, "Ateş") - 0.2, "“Uçan nehirler”", size=110)
    meme(L, t, T(7, "ıslak", 39) - 0.1, T(7, "Ama", 43) - 0.15, "ATEŞ: YANMIYOR", y=1150, size=130, col=RED)
    meme(L, t, T(7, "Ayakların") - 0.1, T(7, "Günlerce") - 0.15, "AYAKLARIN!", y=H * 0.45, size=220, col=YEL)
    g_needs(L, t, T(7, "yumuşar") - 0.1, T(7, "Bu", 53) - 0.15,
            [("Deri yumuşar", T(7, "yumuşar"), "warn"), ("Çatlar", T(7, "çatlar"), "warn"), ("Enfeksiyon", T(7, "enfeksiyon"), "no")],
            "ISLAK AYAK", x=1850, y=330)
    meme(L, t, T(7, "çoraplarını") - 0.1, T(7, "Evet", 56) - 0.15, "ÇORAPLARI KURUT", y=1150, size=130, col=YEL)
    stamp(L, t, T(7, "Annen") - 0.1, E(7) + 0.4, "ANNEN HAKLIYMIŞ", y=H * 0.42, size=140)
    # 8 gün 7
    meme(L, t, T(8, "kaşınıyor") - 0.2, T(8, "Ama", 6) - 0.15, "KAŞINTI: MAKSİMUM", y=1150, size=120, col=RED)
    stamp(L, t, T(8, "suyu") - 0.1, T(8, "Çünkü", 9) - 0.15, "KURAL: SUYU TAKİP ET", y=H * 0.42, size=120)
    g_flow(L, t, T(8, "dereler") - 0.15, T(8, "Bu", 14) - 0.15, [T(8, "dereler") - 0.1, T(8, "nehirlere") - 0.1, T(8, "insanlara") - 0.1])
    info_card(L, t, T(8, "1971") - 0.2, T(8, "Juliane", 23) - 0.15, "24 ARALIK 1971 · PERU",
              [("LANSA 508 seferi yıldırım çarpınca parçalandı", "sans", 60), ("Juliane Koepcke, 17 yaşında", "sans", 50)])
    flash(L, t, T(8, "yıldırım") - 0.05, 0.3, amt=0.9)
    big(L, t, T(8, "3000") - 0.2, T(8, "Ve", 28) - 0.2, "≈ 3.000 m", "koltuğuna bağlı halde düştü", y=640, size=220)
    stamp(L, t, T(8, "hayatta", 29) - 0.1, T(8, "Köprücük") - 0.15, "HAYATTA KALDI", y=H * 0.42, size=150, col=(60, 170, 90))
    g_needs(L, t, T(8, "Köprücük") - 0.1, T(8, "Ama", 35) - 0.15,
            [("Köprücük kemiği kırık", T(8, "Köprücük"), "no"), ("Kolunda derin yara", T(8, "Kolundaki"), "no"),
             ("Yarada kurtçuklar", T(8, "kurtçuklar"), "no")], "YARALARI", x=1750, y=330)
    meme(L, t, T(8, "dere", 39) - 0.1, T(8, "11") - 0.15, "DEREYİ TAKİP ETTİ", y=1150, size=130, col=CYAN)
    big(L, t, T(8, "11") - 0.2, T(8, "Ve", 45) - 0.2, "11 gün", "sonra ormancılar onu buldu", y=640, size=240)
    cite(L, t, T(8, "1971") - 0.2, T(8, "Ve", 45) - 0.2, "Juliane Koepcke, LANSA Uçuş 508 (1971)")
    info_card(L, t, T(8, "2023") - 0.2, T(8, "40") - 0.15, "2023 · KOLOMBİYA",
              [("uçak kazasından kurtulan 4 kardeş", "sans", 64), ("13, 9, 4 ve 1 yaşında", "sans", 50)])
    big(L, t, T(8, "40") - 0.2, T(8, "Önce", 57) - 0.2, "40 gün", "ormanda hayatta kaldılar", y=640, size=240)
    g_needs(L, t, T(8, "manyok") - 0.15, T(8, "Ve", 62) - 0.15,
            [("Manyok unu", T(8, "manyok"), "ok"), ("Tohumlar", T(8, "tohumlar"), "ok"), ("Meyveler", T(8, "meyveler"), "ok")],
            "NE YEDİLER?", x=1850, y=330)
    meme(L, t, T(8, "motor") - 0.2, T(8, "Bir", 69) - 0.1, "BU SES...?", y=1150, size=130, col=YEL)
    meme(L, t, T(8, "tekne") - 0.1, T(8, "Kurtuldun") - 0.1, "TEKNE!", y=H * 0.45, size=240, col=YEL)
    g_confetti(L, t, T(8, "Kurtuldun") - 0.1, G[9] - 0.2)
    stamp(L, t, T(8, "Kurtuldun") - 0.1, G[9] - 0.2, "KURTULDUN!", y=H * 0.42, size=180, col=(60, 170, 90))
    # 9 sonuç
    stamp(L, t, T(9, "7") - 0.2, T(9, "Ama", 3) - 0.15, "7 / 7", y=H * 0.42, size=200, col=(60, 170, 90))
    meme(L, t, T(9, "ikinci") - 0.2, T(9, "Amazon") - 0.15, "GERÇEKÇİ SONUÇ: 2. GÜN", y=1150, size=110, col=RED)
    meme(L, t, T(9, "acımasız") - 0.2, T(9, "Ve", 16) - 0.15, "GÜZEL AMA ACIMASIZ", y=1150, size=120, col=YEL)
    meme(L, t, T(9, "binlerce") - 0.2, T(9, "Sen", 21) - 0.15, "KEŞFEDİLMEYİ BEKLİYOR", y=1150, size=110, col=GREEN)
    g_days_grid(L, t, T(9, "Sen", 21) - 0.1, T(9, "Daha") - 0.15)
    outro(L, t)
    fb = clamp((t - (TOTAL - 1.0)) / 1.0)
    if fb > 0.01:
        L.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, int(255 * fb))))
    if not (TITLE0 - 0.3 < t < TITLE1 + 0.3 or t > OUT0 - 0.8 or t < 7.5):
        label(L, W - 120, 92, "PRATİK ABİ", 0.42, 24, WARM, anchor="rm", w="SemiBold", track=0.4)
    return L


class TL47(TL37):
    def render_chunk(self, args):
        i0, i1, path = args
        readers = {}
        enc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                                "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
                                "-pix_fmt", "yuv420p", path], stdin=subprocess.PIPE)
        for i in range(i0, i1):
            t = i / FPS
            base = self.frame(t, readers)
            ov = self.overlay(t)
            if ov is not None:
                im = Image.fromarray(base).convert("RGBA")
                im.alpha_composite(ov)
                base = np.asarray(im.convert("RGB"))
            enc.stdin.write(finish(base, i).tobytes())
            if i % 300 == 0:
                print(f"  kare {i}/{i1}", flush=True)
        enc.stdin.close()
        enc.wait()
        for r in readers.values():
            r.close()
        return path


TL = TL47(C, TOTAL, overlay, bgfn)


def load(path, sr=SR):
    r = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(path), "-f", "f32le", "-ac", "1", "-ar", str(sr), "-"],
                       capture_output=True, check=True)
    return np.frombuffer(r.stdout, np.float32).copy()
def sfx_track(n):
    from scipy.signal import butter, lfilter
    rng = np.random.default_rng(37)
    fx = np.zeros(n, np.float32)

    def add(t, y, g=1.0):
        a = int(t * SR)
        if a < 0:
            y, a = y[-a:], 0
        b = min(n, a + len(y))
        if b > a:
            fx[a:b] += (y[:b - a] * g).astype(np.float32)

    def bp(y, lo, hi, o=2):
        b, a = butter(o, [lo / (SR / 2), hi / (SR / 2)], "band")
        return lfilter(b, a, y)

    def lp(y, f, o=2):
        b, a = butter(o, f / (SR / 2))
        return lfilter(b, a, y)

    def nrm(y, g=0.9):
        return y / (np.abs(y).max() + 1e-9) * g

    def whoosh(d=0.8):
        m = int(d * SR)
        tt = np.linspace(0, 1, m)
        return nrm(bp(rng.standard_normal(m), 300, 5000) * np.sin(np.pi * tt ** 0.7) ** 2, 0.5)

    def boom(d=2.0, f0=70, f1=32):
        m = int(d * SR)
        tt = np.arange(m) / SR
        y = np.sin(2 * np.pi * np.cumsum(f1 + (f0 - f1) * np.exp(-tt * 3)) / SR) * np.exp(-tt * 2.2)
        y += lp(rng.standard_normal(m), 900) * np.exp(-tt * 18) * 0.6
        return nrm(y)

    def thud():
        m = int(0.7 * SR)
        tt = np.arange(m) / SR
        y = np.sin(2 * np.pi * np.cumsum(45 + 60 * np.exp(-tt * 25)) / SR) * np.exp(-tt * 7)
        y += lp(rng.standard_normal(m), 400) * np.exp(-tt * 30) * 0.5
        return nrm(y)

    def roar(d=2.4, f0=85):
        m = int(d * SR)
        tt = np.arange(m) / SR
        f = f0 * (0.8 + 0.35 * np.sin(np.pi * tt / d)) + lp(rng.standard_normal(m), 30) * 40
        ph_ = 2 * np.pi * np.cumsum(f) / SR
        src = sum(np.sign(np.sin(h * ph_)) / h for h in (1, 2, 3, 5)) + lp(rng.standard_normal(m), 3000) * 1.2
        am = 1 + 3 * lp(rng.standard_normal(m), 60)
        y = (bp(src, 180, 520) + bp(src, 600, 1200) * 0.6 + bp(src, 1500, 2600) * 0.25) * am
        y = lp(y * np.clip(tt / 0.3, 0, 1) * np.clip((d - tt) / 1.0, 0, 1), 1600)
        ir = rng.standard_normal(int(1.4 * SR)) * np.exp(-np.arange(int(1.4 * SR)) / SR * 3.5)
        out = np.zeros(m + len(ir) - 1)
        out[:m] += y * 0.55
        out += np.convolve(y, ir) * 0.02
        return nrm(out, 0.75)

    def scratch():
        m = int(0.45 * SR)
        tt = np.arange(m) / SR
        f = 900 + 700 * np.sin(2 * np.pi * 7 * tt)
        y = bp(rng.standard_normal(m), 400, 3000) * (0.6 + 0.4 * np.sin(2 * np.pi * np.cumsum(f) / SR))
        return nrm(y * np.exp(-tt * 3), 0.6)

    def boing():
        m = int(0.6 * SR)
        tt = np.arange(m) / SR
        f = 180 + 300 * np.exp(-tt * 6) + 30 * np.sin(2 * np.pi * 18 * tt)
        return nrm(np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 4), 0.55)

    def trombone():
        out = []
        for i, (f, d) in enumerate([(311, 0.42), (294, 0.42), (277, 0.42), (262, 1.3)]):
            m = int(d * SR)
            tt = np.arange(m) / SR
            vib = 1 + (0.012 * np.sin(2 * np.pi * 5.5 * tt) if i == 3 else 0)
            ph_ = 2 * np.pi * np.cumsum(f * vib * (1 - 0.02 * tt)) / SR
            y = sum(np.sin(h * ph_) / h ** 0.9 for h in range(1, 9))
            y = lp(y, 1800) * np.clip(tt / 0.04, 0, 1) * np.clip((d - tt) / 0.08, 0, 1)
            out.append(y)
        return nrm(np.concatenate(out), 0.5)

    def pop():
        m = int(0.1 * SR)
        tt = np.arange(m) / SR
        return np.sin(2 * np.pi * (900 - 4000 * tt) * tt) * np.exp(-tt * 45) * 0.35

    def ding():
        m = int(1.0 * SR)
        tt = np.arange(m) / SR
        return (np.sin(2 * np.pi * 1318 * tt) + 0.4 * np.sin(2 * np.pi * 2637 * tt)) * np.exp(-tt * 5) * 0.25

    def shutter():
        m = int(0.18 * SR)
        tt = np.arange(m) / SR
        y = bp(rng.standard_normal(m), 1500, 8000) * (np.exp(-tt * 60) + 0.7 * np.exp(-np.abs(tt - 0.09) * 80))
        return nrm(y, 0.6)

    def buzz(d=2.0):
        m = int(d * SR)
        tt = np.arange(m) / SR
        f = 560 + 40 * np.sin(2 * np.pi * 3 * tt)
        y = np.sign(np.sin(2 * np.pi * np.cumsum(f) / SR)) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.7 * tt) ** 2)
        y = bp(y, 400, 3000) * np.clip(tt / 0.3, 0, 1) * np.clip((d - tt) / 0.3, 0, 1)
        return nrm(y, 0.25)

    def ticks(d=1.2):
        out = np.zeros(int(d * SR))
        for i in range(int(d * 14)):
            a = int(i / 14 * SR)
            out[a:a + 300] += np.sin(2 * np.pi * 2500 * np.arange(300) / SR) * np.exp(-np.arange(300) / 40) * 0.3
        return out

    def rumble(d=6.0):
        m = int(d * SR)
        tt = np.arange(m) / SR
        return nrm(lp(rng.standard_normal(m), 120, 3) * np.clip(tt / 1.5, 0, 1) * np.clip((d - tt) / 2.0, 0, 1))

    def chime():
        m = int(1.6 * SR)
        tt = np.arange(m) / SR
        y = sum(np.sin(2 * np.pi * f * tt) * np.exp(-tt * 3) * np.clip((tt - i * 0.08) * 50, 0, 1)
                for i, f in enumerate((1568, 2093, 2637, 3136)))
        return nrm(y, 0.3)



    def rain(d=8.0):
        m = int(d * SR)
        tt = np.arange(m) / SR
        y = bp(rng.standard_normal(m), 800, 7000) * 0.5 + lp(rng.standard_normal(m), 500) * 0.6
        cr = (rng.random(m) > 0.9985) * rng.standard_normal(m) * 3
        y = y + bp(cr, 2000, 8000)
        return nrm(y * np.clip(tt / 1.5, 0, 1) * np.clip((d - tt) / 1.5, 0, 1), 0.6)

    def thunder():
        y = boom(3.5, 60, 24)
        m = len(y)
        tt = np.arange(m) / SR
        y = y + lp(rng.standard_normal(m), 300, 3) * np.exp(-tt * 0.9) * 2.0
        return nrm(y, 0.9)

    def heart(n_=4, gap=0.75):
        out = np.zeros(int((n_ * gap + 1) * SR))
        for i in range(n_):
            for dd, gg in ((0.0, 1.0), (0.22, 0.7)):
                a = int((i * gap + dd) * SR)
                th = thud() * gg
                out[a:a + len(th)] += th[:len(out) - a]
        return nrm(out, 0.8)

    def mosq(d=2.5):
        m = int(d * SR)
        tt = np.arange(m) / SR
        f = 620 + 60 * np.sin(2 * np.pi * 2.3 * tt) + 25 * np.sin(2 * np.pi * 7 * tt)
        y = np.sign(np.sin(2 * np.pi * np.cumsum(f) / SR))
        pan = 0.4 + 0.6 * np.sin(np.pi * tt / d) ** 2
        return nrm(bp(y, 500, 4000) * pan * np.clip(tt / 0.2, 0, 1) * np.clip((d - tt) / 0.3, 0, 1), 0.25)

    def zap():
        m = int(0.6 * SR)
        tt = np.arange(m) / SR
        y = np.sign(np.sin(2 * np.pi * 60 * tt)) * bp(rng.standard_normal(m), 1000, 6000) * 2
        y += np.sin(2 * np.pi * np.cumsum(2000 - 1500 * tt) / SR) * 0.5
        return nrm(y * np.exp(-tt * 5), 0.6)

    def splash():
        m = int(1.0 * SR)
        tt = np.arange(m) / SR
        return nrm(bp(rng.standard_normal(m), 300, 4000) * np.exp(-tt * 5) * np.clip(tt / 0.02, 0, 1), 0.6)

    def creak():
        m = int(0.9 * SR)
        tt = np.arange(m) / SR
        f = 90 + 40 * np.sin(2 * np.pi * 1.5 * tt)
        y = bp(np.sign(np.sin(2 * np.pi * np.cumsum(f) / SR)) * (rng.random(m) > 0.5), 300, 2500)
        return nrm(y * np.sin(np.pi * tt / 0.9), 0.4)

    def motor(d=5.0):
        m = int(d * SR)
        tt = np.arange(m) / SR
        f = 48 + 4 * np.sin(2 * np.pi * 0.5 * tt)
        y = sum(np.sign(np.sin(h * 2 * np.pi * np.cumsum(f) / SR)) / h for h in (1, 2, 3))
        y = lp(y, 900) * np.clip(tt / d, 0, 1) ** 1.5
        return nrm(y, 0.5)

    W_ = 0.05  # geçiş rüzgârı: kullanıcı isteği, çok kısık

    # --- teaser ---
    for x in (0.9, 1.7, 2.5, 3.2, 3.9, 4.6, 5.3):
        add(x - 0.05, thud(), 0.55)
        add(x - 0.25, whoosh(0.4), W_)
    add(2.5, thunder(), 0.35)
    add(3.2, mosq(0.8), 0.6)
    add(0.15, boom(1.5, 70, 30), 0.6)
    add(5.3, boom(2.0, 60, 28), 0.7)
    # --- 1 ---
    add(T(1, "Telefonun") - 0.05, ding(), 0.5)
    add(T(1, "Amazon", 11) - 0.1, boom(1.8, 70, 30), 0.5)
    add(T(1, "5,5") - 0.15, pop(), 0.8)
    add(T(1, "390") - 0.15, pop(), 0.8)
    add(T(1, "tüketiyor") - 0.1, thud(), 0.8)
    add(T(1, "onda") - 0.15, ding(), 0.5)
    add(T(1, "Kurtarma") - 0.1, thud(), 0.8)
    add(T(1, "kolay") - 0.1, boing(), 0.45)
    add(TITLE0 - 0.2, boom(), 0.6)
    add(TITLE0 + 1.2, scratch(), 0.35)
    # gün kartları
    for k in range(2, 9):
        add(DC[k] - 0.2, whoosh(0.6), W_)
        add(DC[k] + 0.05, thud(), 0.7)
        add(DC[k] + 0.8, ticks(1.0), 0.35)
    # --- 2 ---
    add(T(2, "kurumuyor") - 0.1, pop(), 0.7)
    add(T(2, "çamaşır") - 0.1, boing(), 0.45)
    add(T(2, "susuzluk") - 0.1, thud(), 0.8)
    add(T(2, "kaynatmadan") - 0.1, buzz(0.8), 0.5)
    add(T(2, "yaprak") - 0.1, pop(), 0.7)
    add(T(2, "Kötü") - 0.1, trombone(), 0.3)
    add(T(2, "hamakta") - 0.1, ding(), 0.5)
    add(T(2, "Ve", 85) - 0.2, rumble(5.0), 0.35)
    add(T(2, "canavar", 87) - 0.3, roar(2.6, 70), 0.55)
    add(T(2, "uyku") - 0.1, trombone(), 0.3)
    # --- 3 ---
    add(T(3, "Uyandın") - 0.2, mosq(3.0), 0.7)
    add(T(3, "sivrisinek") - 0.1, mosq(2.0), 0.6)
    add(T(3, "balkonda") + 0.3, mosq(2.0), 0.5)
    add(T(3, "Evet", 31) - 0.05, thud(), 0.7)
    add(T(3, "soktu") - 0.1, thud(), 0.9)
    add(T(3, "soktu"), scratch(), 0.6)
    add(T(3, "tepede") - 0.3, boom(1.0, 90, 40), 0.6)
    add(T(3, "Sen", 66) - 0.05, boing(), 0.4)
    add(T(3, "Ücretsiz") - 0.1, ding(), 0.5)
    add(T(3, "elini") - 0.2, thud(), 0.8)
    # --- 4 ---
    add(T(4, "midenden") - 0.15, rumble(1.6), 0.6)
    add(T(4, "2,5") - 0.15, pop(), 0.8)
    add(T(4, "80") - 0.2, whoosh(0.5), 0.08)
    add(T(4, "80") + 0.15, thud(), 1.0)
    add(T(4, "Yani", 26) - 0.05, thud(), 0.8)
    add(T(4, "Sakın") - 0.1, thud(), 0.8)
    add(T(4, "market") - 0.2, trombone(), 0.3)
    add(T(4, "protein") - 0.1, ding(), 0.5)
    add(T(4, "sucuklu") - 0.1, boing(), 0.45)
    # --- 5 ---
    add(T(5, "pençe") - 0.1, ticks(1.2), 0.4)
    add(T(5, "Jaguar", 10) - 0.1, roar(2.2, 95), 0.6)
    add(T(5, "Jaguar", 10) - 0.05, thud(), 0.8)
    add(T(5, "kalbin") - 0.1, heart(4, 0.7), 0.7)
    add(T(5, "nadir") - 0.2, thud(), 0.7)
    add(T(5, "Beyaz") - 0.2, rumble(3.0), 0.4)
    add(T(5, "kediyi") - 0.2, boing(), 0.45)
    # --- 6 ---
    add(G[6] + 0.1, splash(), 0.4)
    add(T(6, "pirana") - 0.1, thud(), 0.8)
    add(T(6, "abartı") - 0.2, thud(), 0.8)
    add(T(6, "Nehirde") - 0.1, rumble(2.0), 0.4)
    add(T(6, "860") - 0.2, zap(), 0.7)
    add(T(6, "anakonda") - 0.1, creak(), 0.5)
    add(T(6, "pembe") - 0.1, chime(), 0.5)
    add(T(6, "nehir de", 89) - 0.1, thud(), 0.7)
    # --- 7 ---
    add(T(7, "kararıyor") - 0.5, thunder(), 0.6)
    add(T(7, "Amazon", 3) - 0.2, rain(T(7, "Ateş") - T(7, "Amazon", 3) + 1.0), 0.45)
    add(T(7, "şimşekler") - 0.1, thunder(), 0.8)
    add(T(7, "sele") - 0.2, thud(), 0.7)
    add(T(7, "sırılsıklamsın") - 0.2, splash(), 0.5)
    add(T(7, "ıslak", 39) - 0.1, trombone(), 0.3)
    add(T(7, "Annen") - 0.1, thud(), 0.8)
    # --- 8 ---
    add(T(8, "suyu") - 0.1, thud(), 0.7)
    add(T(8, "dereler") - 0.1, pop(), 0.6)
    add(T(8, "nehirlere") - 0.1, pop(), 0.6)
    add(T(8, "insanlara") - 0.1, pop(), 0.6)
    add(T(8, "yıldırım") - 0.1, thunder(), 0.7)
    add(T(8, "hayatta", 29) - 0.1, chime(), 0.5)
    add(T(8, "11") - 0.15, ding(), 0.5)
    add(T(8, "40") - 0.15, ding(), 0.5)
    add(T(8, "motor") - 1.5, motor(T(8, "Kurtuldun") - T(8, "motor") + 1.8), 0.45)
    add(T(8, "Kurtuldun") - 0.1, chime(), 0.8)
    add(T(8, "Kurtuldun") - 0.05, boom(1.5, 80, 40), 0.4)
    # --- 9 ---
    add(T(9, "7") - 0.2, ding(), 0.5)
    add(T(9, "ikinci") - 0.2, trombone(), 0.3)
    add(T(9, "Sen", 21) - 0.1, pop(), 0.6)
    add(OUT0 - 0.4, ding(), 0.5)
    return fx


def build_audio():
    n = int(TOTAL * SR) + SR
    voice = np.zeros(n, np.float32)
    for i in range(1, NSEG + 1):
        x = load(WORK / f"ses/v{i}.wav")
        a = int(G[i] * SR)
        voice[a:a + len(x)] += x
    import audio_tools as at
    at._write(str(WORK / "voice_full.wav"), voice[:int(TOTAL * SR)])
    trk = {k: load(WORK / f"muzik-v47{k}_muzik.wav") for k in "abcd"}
    plan = [("c", 0.0), ("a", G[1] - 0.4), ("b", DC[2] - 0.3), ("c", T(2, "Tamam", 81) - 0.4), ("b", DC[3] - 0.3),
            ("a", DC[4] - 0.3), ("c", DC[5] - 0.3), ("b", T(6, "Ama", 68) - 0.4), ("c", DC[7] - 0.3),
            ("b", T(7, "Ayakların") - 0.4), ("a", DC[8] - 0.3), ("c", T(8, "1971") - 0.5), ("d", T(8, "Ama", 35) - 0.4),
            ("c", T(8, "motor") - 0.4), ("d", T(8, "Kurtuldun") - 0.3)]
    mus = np.zeros(n, np.float32)
    XF = int(1.2 * SR)

    def looped(src, Ln):
        out = src.copy()
        while len(out) < Ln:
            mixz = out[-XF:] * np.linspace(1, 0, XF) + src[:XF] * np.linspace(0, 1, XF)
            out = np.concatenate([out[:-XF], mixz, src[XF:]])
        return out[:Ln].copy()

    used = {}
    for j, (k, st) in enumerate(plan):
        en = plan[j + 1][1] + 1.2 if j + 1 < len(plan) else TOTAL
        a, b = int(st * SR), min(n, int(en * SR))
        src = trk[k]
        o = used.get(k, 0) % max(1, len(src) - SR * 20)  # aynı parçayı baştan tekrar etme
        used[k] = o + (b - a)
        src = np.concatenate([src[o:], src[:o]]) if o else src
        seg = looped(src, b - a)
        fi = XF if j > 0 else int(0.4 * SR)
        seg[:fi] *= np.linspace(0, 1, fi)
        if j + 1 < len(plan):
            seg[-XF:] *= np.linspace(1, 0, XF)
        else:
            seg[-int(4 * SR):] *= np.linspace(1, 0, int(4 * SR))
        seg /= (np.percentile(np.abs(seg), 99) + 1e-9)
        mus[a:b] += seg * 0.5
    mus = mus[:int(TOTAL * SR)]
    mus /= (np.max(np.abs(mus)) + 1e-9)
    at._write(str(WORK / "music.wav"), mus * 0.9)
    fx = sfx_track(int(TOTAL * SR))
    fx /= max(1.0, float(np.abs(fx).max()))
    at._write(str(WORK / "sfx.wav"), fx * 0.95)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(WORK / "voice_full.wav"), "-i", str(WORK / "music.wav"),
                    "-i", str(WORK / "sfx.wav"), "-filter_complex",
                    "[0:a]highpass=f=70,acompressor=threshold=-20dB:ratio=3:attack=5:release=150,volume=1.0,asplit=2[v][vs];"
                    "[1:a]volume=0.30[m];[m][vs]sidechaincompress=threshold=0.02:ratio=6:attack=40:release=500[md];"
                    "[2:a]volume=0.6[s];[v][md][s]amix=inputs=3:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11",
                    "-ar", "48000", "-c:a", "pcm_s16le", str(WORK / "mix.wav")], check=True)


def jobs_list():
    out_dir = WORK / "parts"
    out_dir.mkdir(exist_ok=True)
    n = int(round(TOTAL * FPS))
    return [(a, min(n, a + 900), str(out_dir / f"p{j:02d}.mp4")) for j, a in enumerate(range(0, n, 900))]


def concat_final(jobs):
    lst = WORK / "parts" / "list.txt"
    lst.write_text("".join(f"file '{x[2]}'\n" for x in jobs))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-i",
                    str(WORK / "mix.wav"), "-map", "0:v", "-map", "1:a", "-c:v", "libx264",
                    "-preset", "veryfast", "-b:v", "3800k", "-maxrate", "5000k", "-bufsize", "10000k", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", str(WORK / "final.mp4")],
                   check=True)


def render_all(keep=0):
    jobs = jobs_list()
    todo = [j for j in jobs if not (Path(j[2]).exists() and Path(j[2]).stat().st_size > 100000)]
    with Pool(2) as p:
        p.map(TL.render_chunk, todo, chunksize=1)
    concat_final(jobs)


if __name__ == "__main__":
    mode = sys.argv[2] if len(sys.argv) > 2 else "render"
    print("toplam", round(TOTAL, 1), "G", {k: round(v, 1) for k, v in G.items()}, flush=True)
    if mode == "frames":
        for tt in [float(x) for x in sys.argv[3].split(",")]:
            readers = {}
            base = TL.frame(tt, readers)
            im = Image.fromarray(base).convert("RGBA")
            im.alpha_composite(overlay(tt))
            Image.fromarray(finish(np.asarray(im.convert("RGB")), 0)).resize((1280, 720), Image.LANCZOS).save(
                WORK / "test" / f"fr_{tt:06.1f}.jpg", quality=86)
            for r in readers.values():
                r.close()
    elif mode == "ses":
        build_audio()
    elif mode == "some":
        jobs = jobs_list()
        with Pool(2) as p:
            p.map(TL.render_chunk, [jobs[int(i)] for i in sys.argv[3].split(",")], chunksize=1)
        concat_final(jobs)
    else:
        build_audio()
        render_all()
        print("render bitti", TOTAL, flush=True)
