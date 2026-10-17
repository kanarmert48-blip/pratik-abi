"""Profesyonel Shorts görüntü motoru: katmanlı arka plan, 3D ikonlar, kinetik başlıklar,
kelime senkron altyazı, sahne geçişleri. Sahneler video dosyasında tanımlanır."""
import math, os, random, re, subprocess, tempfile
from functools import lru_cache
from multiprocessing import Pool
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

# PA_SCALE: 1 = 1080x1920, 4/3 = 1440x2560 (2K). Çizim fonksiyonları 1080 "birim" alır, piksele çevirir.
S = float(os.environ.get("PA_SCALE", "1"))
W, H, FPS = round(1080 * S), round(1920 * S), 30


def u(x):
    """1080 birimi -> piksel"""
    return x * S
ASSETS = Path(__file__).resolve().parent.parent / "assets"
FONTS = {
    "black": "/usr/share/fonts/opentype/inter/Inter-Black.otf",
    "xb": "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf",
    "b": "/usr/share/fonts/opentype/inter/Inter-Bold.otf",
    "sb": "/usr/share/fonts/opentype/inter/Inter-SemiBold.otf",
}
ACC = (255, 212, 59)
WHITE = (255, 255, 255)
RED = (255, 84, 89)
GREEN = (46, 204, 140)
INK = (22, 26, 40)


@lru_cache(None)
def font(k, size):
    return ImageFont.truetype(FONTS[k], size)


# ---------- zamanlama yardımcıları ----------
def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def ph(t, start, dur):
    return clamp((t - start) / dur) if dur > 0 else (1.0 if t >= start else 0.0)


def eo(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3


def eio(x):
    x = clamp(x)
    return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2


def eb(x):
    x = clamp(x)
    c1, c3 = 1.70158, 2.70158
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2


def bounce(x):
    x = clamp(x)
    n1, d1 = 7.5625, 2.75
    if x < 1 / d1:
        return n1 * x * x
    if x < 2 / d1:
        x -= 1.5 / d1
        return n1 * x * x + 0.75
    if x < 2.5 / d1:
        x -= 2.25 / d1
        return n1 * x * x + 0.9375
    x -= 2.625 / d1
    return n1 * x * x + 0.984375


def lerp(a, b, t):
    return a + (b - a) * t


# ---------- görsel yardımcılar ----------
def set_alpha(im, a):
    if a >= 0.999:
        return im
    im = im.copy()
    al = im.getchannel("A").point(lambda v: int(v * a))
    im.putalpha(al)
    return im


def comp(dst, src, x, y):
    """Kenar taşmalarını kırparak alpha birleştirme."""
    x, y = int(round(x)), int(round(y))
    sx, sy = max(0, -x), max(0, -y)
    dx, dy = max(0, x), max(0, y)
    w = min(src.width - sx, dst.width - dx)
    h = min(src.height - sy, dst.height - dy)
    if w <= 0 or h <= 0:
        return
    if sx or sy or w != src.width or h != src.height:
        src = src.crop((sx, sy, sx + w, sy + h))
    dst.alpha_composite(src, (dx, dy))


@lru_cache(maxsize=600)
def icon(name, size):
    im = Image.open(ASSETS / f"{name}_3d.png").convert("RGBA")
    return im.resize((size, size), Image.LANCZOS)


@lru_cache(maxsize=600)
def icon_shadow(name, size):
    pad = size // 4
    a = icon(name, size).getchannel("A")
    sh = Image.new("RGBA", (size + 2 * pad, size + 2 * pad), (0, 0, 0, 0))
    blk = Image.new("RGBA", (size, size), (0, 0, 0, 255))
    blk.putalpha(a.point(lambda v: int(v * 0.45)))
    sh.alpha_composite(blk, (pad, pad))
    return sh.filter(ImageFilter.GaussianBlur(size / 18)), pad


def put_icon(layer, name, cx, cy, size, alpha=1.0, rot=0.0, shadow=True):
    _put_icon_px(layer, name, cx * S, cy * S, size * S, alpha, rot, shadow)


def _put_icon_px(layer, name, cx, cy, size, alpha=1.0, rot=0.0, shadow=True):
    size = int(size)
    if size < 6 or alpha <= 0.01:
        return
    size = max(8, size // 4 * 4)
    im = icon(name, size)
    if shadow:
        sh, pad = icon_shadow(name, size)
        if rot:
            sh = sh.rotate(rot, resample=Image.BICUBIC, expand=True)
        comp(layer, set_alpha(sh, alpha), cx - sh.width / 2, cy - sh.height / 2 + size * 0.07)
    if rot:
        im = im.rotate(rot, resample=Image.BICUBIC, expand=True)
    comp(layer, set_alpha(im, alpha), cx - im.width / 2, cy - im.height / 2)


@lru_cache(maxsize=64)
def soft_shadow(w, h, r, blur=26, op=0.45):
    pad = blur * 3
    im = Image.new("RGBA", (w + 2 * pad, h + 2 * pad), (0, 0, 0, 0))
    ImageDraw.Draw(im).rounded_rectangle([pad, pad, pad + w, pad + h], radius=r, fill=(0, 0, 0, int(255 * op)))
    return im.filter(ImageFilter.GaussianBlur(blur)), pad


def card(layer, x0, y0, w, h, r=40, fill=(255, 255, 255, 255), outline=None, width=0, shadow=True, alpha=1.0):
    """Gölgeli yuvarlak kart (alpha destekli)."""
    x0, y0, w, h, r, width = x0 * S, y0 * S, int(w * S), int(h * S), int(r * S), int(round(width * S))
    if alpha <= 0.01 or w < 4 or h < 4:
        return
    if shadow:
        sh, pad = soft_shadow(w, h, r, blur=int(26 * S))
        comp(layer, set_alpha(sh, alpha), x0 - pad, y0 - pad + 18 * S)
    tmp = Image.new("RGBA", (w + 4, h + 4), (0, 0, 0, 0))
    ImageDraw.Draw(tmp).rounded_rectangle([1, 1, w + 1, h + 1], radius=r, fill=fill, outline=outline, width=width)
    comp(layer, set_alpha(tmp, alpha), x0 - 1, y0 - 1)


def chip(layer, cx, cy, text, bg=WHITE, fg=INK, size=44, icon_name=None, scale=1.0, alpha=1.0, k="xb"):
    if scale <= 0.02 or alpha <= 0.01:
        return
    cx, cy, size = cx * S, cy * S, int(round(size * S))
    f = font(k, size)
    tw = int(ImageDraw.Draw(layer).textlength(text, font=f))
    isz = int(size * 1.35) if icon_name else 0
    padx, h = int(size * 0.75), int(size * 1.9)
    gp = int(12 * S)
    w = tw + 2 * padx + (isz + gp if icon_name else 0)
    M = int(30 * S)
    tmp = Image.new("RGBA", (w + 2 * M, h + 2 * M + int(10 * S)), (0, 0, 0, 0))
    sh, pad = soft_shadow(w, h, h // 2, blur=int(14 * S), op=0.35)
    comp(tmp, sh, M - pad, M - pad + 8 * S)
    d = ImageDraw.Draw(tmp)
    d.rounded_rectangle([M, M, M + w, M + h], radius=h // 2, fill=bg + (255,))
    x = M + padx
    if icon_name:
        _put_icon_px(tmp, icon_name, x + isz / 2 - 6 * S, M + h / 2, isz, shadow=False)
        x += isz + gp
    d.text((x, M + h / 2), text, font=f, fill=fg, anchor="lm")
    if abs(scale - 1) > 0.01:
        tmp = tmp.resize((max(1, int(tmp.width * scale)), max(1, int(tmp.height * scale))), Image.BICUBIC)
    comp(layer, set_alpha(tmp, alpha), cx - tmp.width / 2, cy - tmp.height / 2)


def text_c(layer, xy, text, k, size, fill, anchor="mm", alpha=1.0, stroke=0, stroke_fill=(0, 0, 0)):
    d = ImageDraw.Draw(layer)
    a = int(255 * alpha)
    d.text((xy[0] * S, xy[1] * S), text, font=font(k, int(round(size * S))), fill=fill[:3] + (a,), anchor=anchor,
           stroke_width=int(round(stroke * S)), stroke_fill=stroke_fill[:3] + (a,))


# ---------- başlık ----------
def headline(layer, segs, t, y0=250, size=84, maxw=960, start=0.0):
    """segs: [(metin, vurgu_mu)] – satır satır kayarak gelir."""
    d = ImageDraw.Draw(layer)
    y0, size, maxw = y0 * S, int(round(size * S)), maxw * S
    words = []
    for txt, acc in segs:
        words += [(w, acc) for w in txt.split()]
    allw = " ".join(w for w, _ in words)
    for s1 in range(size, int(71 * S), -2):  # tek satıra sığıyorsa küçültüp tek satır yap
        if d.textlength(allw, font=font("black", s1)) <= maxw:
            size = s1
            break
    while True:
        f = font("black", size)
        lines, cur = [], []
        for w in words:
            test = " ".join(x for x, _ in cur + [w])
            if cur and d.textlength(test, font=f) > maxw:
                lines.append(cur)
                cur = [w]
            else:
                cur.append(w)
        if cur:
            lines.append(cur)
        if len(lines) <= 2 or size <= 60 * S:
            break
        size -= int(6 * S)
    lh = int(size * 1.12)
    sp = d.textlength(" ", font=f)
    for li, ln in enumerate(lines):
        p = eo(ph(t, start + li * 0.09, 0.45))
        if p <= 0:
            continue
        tw = sum(d.textlength(w, font=f) for w, _ in ln) + sp * (len(ln) - 1)
        x = W / 2 - tw / 2
        y = y0 + li * lh + (1 - p) * 50 * S
        for w, acc in ln:
            col = ACC if acc else WHITE
            d.text((x + 3 * S, y + 6 * S), w, font=f, fill=(0, 0, 0, int(90 * p)))
            d.text((x, y), w, font=f, fill=col + (int(255 * p),))
            x += d.textlength(w, font=f) + sp
    return (y0 + len(lines) * lh) / S


# ---------- arka plan ----------
class Background:
    def __init__(self, seed=1, top=(9, 16, 40), bottom=(12, 46, 64),
                 glows=((20, 184, 166, 95), (245, 158, 11, 70), (124, 58, 237, 60))):
        y = np.linspace(0, 1, H)[:, None, None]
        arr = np.array(top, float) * (1 - y) + np.array(bottom, float) * y
        self.base = Image.fromarray(np.repeat(arr, W, axis=1).astype(np.uint8), "RGB").convert("RGBA")
        self.glows = []
        for c in glows:
            r = 640
            g = np.linspace(-1, 1, 2 * r)
            dd = np.sqrt(g[None, :] ** 2 + g[:, None] ** 2)
            a = np.clip(1 - dd, 0, 1) ** 2.2 * c[3]
            im = np.zeros((2 * r, 2 * r, 4), np.uint8)
            im[..., 0], im[..., 1], im[..., 2] = c[0], c[1], c[2]
            im[..., 3] = a.astype(np.uint8)
            self.glows.append(Image.fromarray(im, "RGBA"))
        rnd = random.Random(seed)
        self.bokeh = []
        for _ in range(16):
            r = rnd.randint(6, 26)
            s = Image.new("RGBA", (r * 4, r * 4), (0, 0, 0, 0))
            ImageDraw.Draw(s).ellipse([r, r, r * 3, r * 3], fill=(255, 255, 255, rnd.randint(40, 90)))
            s = s.filter(ImageFilter.GaussianBlur(r / 3))
            self.bokeh.append((s, rnd.uniform(0, W), rnd.uniform(0, H), rnd.uniform(12, 40), rnd.uniform(0, 6.28)))
        vy, vx = np.mgrid[0:H, 0:W]
        dd = np.sqrt(((vx - W / 2) / (W * 0.62)) ** 2 + ((vy - H / 2) / (H * 0.6)) ** 2)
        va = (np.clip(dd - 0.55, 0, 1) * 330).clip(0, 170).astype(np.uint8)
        vig = np.zeros((H, W, 4), np.uint8)
        vig[..., 3] = va
        self.vignette = Image.fromarray(vig, "RGBA")
        self.grain = []
        rng = np.random.default_rng(seed)
        for _ in range(4):
            n = rng.integers(0, 255, (H // 2, W // 2), dtype=np.uint8)
            g = np.zeros((H // 2, W // 2, 4), np.uint8)
            g[..., 0] = g[..., 1] = g[..., 2] = n
            g[..., 3] = 9
            self.grain.append(Image.fromarray(g, "RGBA").resize((W, H), Image.NEAREST))

    def frame(self, t):
        im = self.base.copy()
        pos = [(260 + 140 * math.sin(t * 0.21), 380 + 120 * math.cos(t * 0.17)),
               (830 + 120 * math.cos(t * 0.19), 1500 + 140 * math.sin(t * 0.23)),
               (700 + 160 * math.sin(t * 0.13 + 2), 900 + 200 * math.cos(t * 0.11 + 1))]
        for g, (x, y) in zip(self.glows, pos):
            comp(im, g, x - g.width / 2, y - g.height / 2)
        for s, bx, by, sp, ph0 in self.bokeh:
            x = bx + 30 * math.sin(t * 0.4 + ph0)
            y = (by - t * sp) % (H + 200) - 100
            comp(im, s, x - s.width / 2, y - s.height / 2)
        return im

    def finish(self, im, t):
        im.alpha_composite(self.vignette)
        im.alpha_composite(self.grain[int(t * FPS) % 4])
        return im


# ---------- altyazı ----------
def trl(s):
    return s.replace("İ", "i").replace("I", "ı").lower()


def clean(w):
    return re.sub(r"[.,:;…]+$", "", w.replace("...", ""))


def caption_groups(words, max_words=3, max_chars=20, gap=0.32):
    groups, cur = [], []
    for i, w in enumerate(words):
        if cur and len(" ".join(clean(x["w"]) for x in cur + [w])) > max_chars:
            groups.append(cur)
            cur = []
        cur.append(w)
        nxt = words[i + 1] if i + 1 < len(words) else None
        txt = " ".join(clean(x["w"]) for x in cur)
        brk = (len(cur) >= max_words or re.search(r"[.,:?!…]$", w["w"]) or len(txt) >= max_chars
               or nxt is None or nxt["s"] - w["e"] > gap)
        if brk:
            groups.append(cur)
            cur = []
    out = []
    for i, g in enumerate(groups):
        st = g[0]["s"] - 0.06
        en = g[-1]["e"] + 0.25
        if i + 1 < len(groups):
            en = min(en, groups[i + 1][0]["s"] - 0.06)
        out.append((st, en, g))
    return out


def draw_caption(im, groups, t, y=1330):
    for st, en, g in groups:
        if st <= t < en:
            break
    else:
        return
    d = ImageDraw.Draw(im)
    texts = [clean(w["w"]) for w in g]
    for fs in range(80, 50, -4):
        f = font("black", int(round(fs * S)))
        sp = d.textlength(" ", font=f)
        tw = sum(d.textlength(x, font=f) for x in texts) + sp * (len(texts) - 1)
        if tw <= 940 * S:
            break
    pop = eb(ph(t, st, 0.16))
    tmp = Image.new("RGBA", (int(tw + 80 * S), int(160 * S)), (0, 0, 0, 0))
    td = ImageDraw.Draw(tmp)
    x = 40 * S
    for w, txt in zip(g, texts):
        active = w["s"] - 0.04 <= t < (w["e"] + 0.05)
        col = ACC if active else WHITE
        yy = (40 - (6 if active else 0)) * S
        td.text((x + 2 * S, yy + 7 * S), txt, font=f, fill=(0, 0, 0, 120))
        td.text((x, yy), txt, font=f, fill=col, stroke_width=int(round(7 * S)), stroke_fill=(10, 12, 20))
        x += td.textlength(txt, font=f) + sp
    sc = 0.86 + 0.14 * pop
    if abs(sc - 1) > 0.01:
        tmp = tmp.resize((int(tmp.width * sc), int(tmp.height * sc)), Image.BICUBIC)
    comp(im, tmp, W / 2 - tmp.width / 2, y * S - tmp.height / 2)


# ---------- üst arayüz ----------
def top_ui(im, label, scenes, t):
    """Üstte yalnızca kanal etiketi (ilerleme çizgileri kaldırıldı)."""
    brand(im, 540, 150)


def _brand_font(size):
    f = ImageFont.truetype(str(ASSETS / "Baloo2.ttf"), size)
    f.set_variation_by_axes([800])
    return f


def _rosette(d_size, col, check_col):
    """Dalgalı kenarlı rozet + tik."""
    S = d_size * 4
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c, R, n = S / 2, S * 0.46, 12
    pts = []
    for k in range(n * 8):
        a = 2 * math.pi * k / (n * 8)
        r = R * (0.88 + 0.12 * math.cos(n * a))
        pts.append((c + r * math.cos(a), c + r * math.sin(a)))
    d.polygon(pts, fill=col + (255,))
    d.ellipse([c - R * 0.70, c - R * 0.70, c + R * 0.70, c + R * 0.70], outline=check_col + (90,), width=int(S * 0.025))
    w = int(S * 0.10)
    d.line([(c - R * 0.40, c + R * 0.02), (c - R * 0.10, c + R * 0.32), (c + R * 0.44, c - R * 0.30)],
           fill=check_col + (255,), width=w, joint="curve")
    for x, y in [(c - R * 0.40, c + R * 0.02), (c + R * 0.44, c - R * 0.30)]:
        d.ellipse([x - w / 2, y - w / 2, x + w / 2, y + w / 2], fill=check_col + (255,))
    return im.resize((d_size, d_size), Image.LANCZOS)


_BRAND = {}


def brand(im, cx, cy, size=46):
    """'PratikAbi' etiketi + kanalın kendi tik rozeti (önbellekli)."""
    cx, cy, size = cx * S, cy * S, int(round(size * S))
    if size not in _BRAND:
        f = _brand_font(size)
        probe = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
        tw = probe.textlength("PratikAbi", font=f)
        h = int(size * 1.6)
        bd = int(size * 1.05)
        w = int(tw + size * 1.1 + bd + 10)
        M = int(30 * S)
        tmp = Image.new("RGBA", (w + 2 * M, h + 2 * M + int(10 * S)), (0, 0, 0, 0))
        sh, pad = soft_shadow(w, h, h // 2, blur=int(14 * S), op=0.35)
        comp(tmp, sh, M - pad, M - pad + 8 * S)
        td = ImageDraw.Draw(tmp)
        td.rounded_rectangle([M, M, M + w, M + h], radius=h // 2, fill=ACC + (255,))
        td.text((M + size * 0.55, M + h / 2 + size * 0.06), "PratikAbi", font=f, fill=INK, anchor="lm")
        ros = _rosette(bd, INK, ACC)
        comp(tmp, ros, M + size * 0.55 + tw + 10 * S, M + (h - bd) / 2)
        _BRAND[size] = tmp
    tmp = _BRAND[size]
    comp(im, tmp, cx - tmp.width / 2, cy - tmp.height / 2)


# ---------- render ----------
class Video:
    def __init__(self, scenes, words, label, total, bg=None, trans="slide"):
        self.trans = trans
        self.scenes = scenes
        self.words = words
        self.label = label
        self.total = total
        self.bg = bg or Background()
        self.groups = caption_groups(words)
        for s in scenes:
            s["words"] = [w for w in words if s["start"] - 0.01 <= w["s"] < s["end"]]

    def wt(self, scene, key, nth=0, default=None):
        k = trl(key)
        hits = [w for w in scene["words"] if trl(clean(w["w"])).startswith(k)]
        if len(hits) > nth:
            return hits[nth]["s"] - scene["start"]
        return default if default is not None else 0.5

    def frame(self, t):
        im = self.bg.frame(t)
        for i, sc in enumerate(self.scenes):
            if sc["start"] <= t < sc["end"] or (i == len(self.scenes) - 1 and t >= sc["start"]):
                lt = t - sc["start"]
                dur = sc["end"] - sc["start"]
                if sc.get("bgdraw"):  # arka plana sabit çizimler (geçişte kaymaz)
                    sc["bgdraw"](self, sc, im, lt, dur)
                layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                sc["draw"](self, sc, layer, lt, dur)
                pin = 1.0 if i == 0 else eo(ph(lt, 0, 0.32))  # ilk sahne ilk karede hazır
                pout = eio(ph(lt, dur - 0.22, 0.22)) if i < len(self.scenes) - 1 else 0
                a = pin * (1 - pout)
                if self.trans == "zoom" and (pin < 0.999 or pout > 0.001):
                    sc_ = 1.12 - 0.12 * pin + 0.08 * pout
                    lw, lh = int(W * sc_), int(H * sc_)
                    layer = layer.resize((lw, lh), Image.BILINEAR)
                    if a < 0.999:
                        layer = set_alpha(layer, a)
                    comp(im, layer, (W - lw) / 2, (H - lh) / 2)
                else:
                    dx = ((1 - pin) * 150 - pout * 150) * S
                    if a < 0.999:
                        layer = set_alpha(layer, a)
                    comp(im, layer, dx, 0)
                if i > 0 and lt < 0.18:  # sahne başında kısa beyaz parlama
                    fl = int(110 * (1 - lt / 0.18))
                    im.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 255, fl)))
                break
        top_ui(im, self.label, self.scenes, t)
        draw_caption(im, self.groups, t)
        return self.bg.finish(im, t).convert("RGB")

    def _chunk(self, args):
        a, b, path = args
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
               "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "faster", "-crf", "15",
               "-pix_fmt", "yuv420p", path]
        p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        for f in range(a, b):
            p.stdin.write(self.frame(f / FPS).tobytes())
        p.stdin.close()
        p.wait()
        return path

    def render(self, audio, out, workers=2):
        nf = int(round(self.total * FPS))
        tmp = tempfile.mkdtemp()
        step = math.ceil(nf / workers)
        jobs = [(i, min(nf, i + step), os.path.join(tmp, f"c{k}.mp4")) for k, i in enumerate(range(0, nf, step))]
        global _V
        _V = self
        with Pool(len(jobs)) as pool:
            parts = pool.map(_run_chunk, jobs)
        lst = os.path.join(tmp, "list.txt")
        Path(lst).write_text("".join(f"file '{p}'\n" for p in parts))
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-i", audio,
                        "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "copy", "-shortest",
                        "-movflags", "+faststart", out], check=True)
        return out


_V = None


def _run_chunk(args):
    return _V._chunk(args)
