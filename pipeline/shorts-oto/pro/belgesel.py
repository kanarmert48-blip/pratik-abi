"""Uzun video (16:9, 2560x1440) belgesel motoru: kesmeler + yumuşak geçişler, Ken Burns, renk düzenleme,
film grenli doku, vinyet, zarif tipografi ve grafik katmanları. Parçalı (çok işlemli) render."""
import math, os, subprocess, json
from functools import lru_cache
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS = 2560, 1440, 30
FONTDIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"
INTER = "/usr/share/fonts/opentype/inter/Inter-{}.otf"

GOLD = (232, 196, 132)
CYAN = (126, 214, 228)
WARM = (246, 242, 234)
GREY = (176, 178, 184)
RED = (224, 92, 78)
GREEN = (126, 226, 150)
INKBG = (9, 11, 16)

GRADE = ("eq=contrast=1.04:saturation=0.86:gamma=0.98,"
         "colorbalance=rs=-0.03:gs=0.0:bs=0.04:rm=0.01:bm=-0.01:rh=0.04:gh=0.01:bh=-0.04,unsharp=5:5:0.35")


# ---------------- zaman / yumuşatma ----------------
def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def ph(t, s, d):
    return clamp((t - s) / d) if d > 0 else float(t >= s)


def eo(x):
    return 1 - (1 - x) ** 3


def eio(x):
    return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2


def window(t, s, e, fin=0.5, fout=0.5):
    """s..e arasında görünür, yumuşak giriş/çıkış -> 0..1"""
    if t < s or t > e:
        return 0.0
    return eo(ph(t, s, fin)) * (1 - eio(ph(t, e - fout, fout)))


# ---------------- yazı ----------------
@lru_cache(None)
def serif(size, wght="Regular", italic=False):
    f = ImageFont.truetype(str(FONTDIR / ("PlayfairItalic.ttf" if italic else "Playfair.ttf")), size)
    try:
        f.set_variation_by_name(wght)
    except Exception:
        pass
    return f


@lru_cache(None)
def sans(size, w="Regular"):
    return ImageFont.truetype(INTER.format(w), size)


@lru_cache(maxsize=512)
def text_img(txt, fkey, size, color, track=0.0, shadow=0.55, glow=0):
    """Metni şeffaf RGBA görüntü olarak döndürür (harf aralıklı, yumuşak gölgeli)."""
    kind, wt, it = fkey
    f = serif(size, wt, it) if kind == "serif" else sans(size, wt)
    sp = size * track
    widths = [f.getlength(c) for c in txt]
    tw = int(sum(widths) + sp * max(0, len(txt) - 1)) + 4
    asc, desc = f.getmetrics()
    pad = int(size * 0.5)
    w, h = tw + 2 * pad, asc + desc + 2 * pad
    m = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(m)
    x = pad
    for c, cw in zip(txt, widths):
        d.text((x, pad), c, font=f, fill=255)
        x += cw + sp
    col = Image.new("RGBA", (w, h), color + (0,))
    col.putalpha(m)
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    if shadow > 0:
        sh = m.filter(ImageFilter.GaussianBlur(max(2, size * 0.08)))
        sh = sh.point(lambda v: int(v * shadow))
        s_img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        s_img.putalpha(sh)
        out.alpha_composite(s_img, (0, max(1, size // 30)))
    if glow:
        g = m.filter(ImageFilter.GaussianBlur(glow)).point(lambda v: int(v * 0.6))
        g_img = Image.new("RGBA", (w, h), color + (0,))
        g_img.putalpha(g)
        out.alpha_composite(g_img)
    out.alpha_composite(col)
    return out


def set_alpha(im, a):
    if a >= 0.999:
        return im
    arr = np.asarray(im).copy()
    arr[..., 3] = (arr[..., 3].astype(np.float32) * a).astype(np.uint8)
    return Image.fromarray(arr, "RGBA")


def put(L, im, x, y, anchor="mm", alpha=1.0, scale=1.0):
    """x,y piksel; anchor: mm (orta), lm (sol-orta), rm, mt..."""
    if alpha <= 0.01:
        return
    if abs(scale - 1) > 0.005:
        im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.BICUBIC)
    im = set_alpha(im, alpha)
    ax = {"l": 0, "m": 0.5, "r": 1}[anchor[0]]
    ay = {"t": 0, "m": 0.5, "b": 1}[anchor[1]]
    L.alpha_composite(im, (int(round(x - im.width * ax)), int(round(y - im.height * ay))))


def text(L, x, y, txt, kind="sans", w="Regular", size=40, color=WARM, alpha=1.0, track=0.0, anchor="mm",
         italic=False, shadow=0.55, glow=0, rise=0.0):
    if alpha <= 0.01:
        return
    im = text_img(txt, (kind, w, italic), size, color, round(track, 3), shadow, glow)
    put(L, im, x, y + rise, anchor, alpha)


# ---------------- ışık parçacıkları ----------------
@lru_cache(None)
def sprite(r, color=GOLD, power=1.8, core=0.0):
    r = max(2, int(r))
    n = 2 * r + 1
    yy, xx = np.mgrid[0:n, 0:n]
    d = np.sqrt((xx - r) ** 2 + (yy - r) ** 2) / r
    a = np.clip(1 - d, 0, 1) ** power
    if core:
        a = np.maximum(a, np.clip(1 - d / core, 0, 1))
    im = np.zeros((n, n, 4), np.uint8)
    im[..., 0], im[..., 1], im[..., 2] = color
    im[..., 3] = (a * 255).astype(np.uint8)
    return Image.fromarray(im, "RGBA")


def dot(L, x, y, r, color=GOLD, alpha=1.0, power=1.8, core=0.0):
    if alpha <= 0.01:
        return
    s = sprite(int(r), color, power, core)
    put(L, s, x, y, "mm", alpha)


# ---------------- son işlem: grenli doku + vinyet ----------------
_rng = np.random.default_rng(7)
GRAIN = [(_rng.standard_normal((H // 2, W // 2)) * 5.5).astype(np.float32) for _ in range(6)]
_yy, _xx = np.mgrid[0:H, 0:W].astype(np.float32)
_d = np.sqrt(((_xx - W / 2) / (W * 0.62)) ** 2 + ((_yy - H / 2) / (H * 0.70)) ** 2)
VIG = (1 - 0.42 * np.clip(_d - 0.45, 0, 1) ** 1.6)[..., None].astype(np.float32)
del _yy, _xx, _d


def finish(arr, i, vig=True):
    f = arr.astype(np.float32)
    if vig:
        f *= VIG
    g = cv2.resize(GRAIN[i % len(GRAIN)], (W, H), interpolation=cv2.INTER_LINEAR)
    f += g[..., None]
    return np.clip(f, 0, 255).astype(np.uint8)


# ---------------- klip okuyucu ----------------
OVER = 1.12  # Ken Burns için fazla çözünürlük


class Reader:
    def __init__(self, src, off, speed=1.0, focus=0.5, grade=GRADE):
        self.TW, self.TH = int(W * OVER) // 2 * 2, int(H * OVER) // 2 * 2
        vf = (f"setpts={1 / speed:.4f}*PTS,fps={FPS},scale={self.TW}:{self.TH}:force_original_aspect_ratio=increase:"
              f"flags=lanczos,crop={self.TW}:{self.TH}:(iw-{self.TW})*{focus}:(ih-{self.TH})/2,{grade}")
        self.p = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-stream_loop", "-1", "-ss", f"{off:.3f}", "-i", str(src),
                                   "-vf", vf, "-an", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                                  stdout=subprocess.PIPE, bufsize=10 ** 8)
        self.last = None

    def read(self):
        n = self.TW * self.TH * 3
        buf = self.p.stdout.read(n)
        if len(buf) == n:
            self.last = np.frombuffer(buf, np.uint8).reshape(self.TH, self.TW, 3)
        return self.last if self.last is not None else np.zeros((self.TH, self.TW, 3), np.uint8)

    def close(self):
        try:
            self.p.kill()
        except Exception:
            pass


def kenburns(fr, q, z0, z1, dx0, dx1, dy0=0.0, dy1=0.0):
    """fr: OVER büyüklüğünde kare. q: 0..1 ilerleme. zoom W'ye göre (1 = tam kadraj)."""
    e = q * q * (3 - 2 * q)
    z = z0 + (z1 - z0) * e
    th, tw = fr.shape[:2]
    s = z * W / tw * OVER  # kaynağı büyütme oranı
    s = max(s, W / tw, H / th)
    cx = tw / 2 + (dx0 + (dx1 - dx0) * e) * tw
    cy = th / 2 + (dy0 + (dy1 - dy0) * e) * th
    M = np.float32([[s, 0, W / 2 - s * cx], [0, s, H / 2 - s * cy]])
    return cv2.warpAffine(fr, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


# ---------------- zaman çizelgesi render ----------------
class Timeline:
    """cuts: [{src|bg, t0, t1, off, speed, z:(z0,z1), dx:(a,b), dy:(a,b), xf: giriş geçişi sn, focus}]
    overlay(t) -> RGBA PIL ya da None ; bgfn(name, t) -> np RGB (W,H) prosedürel arka plan."""

    def __init__(self, cuts, total, overlay, bgfn=None):
        self.cuts = sorted(cuts, key=lambda c: c["t0"])
        self.total = total
        self.overlay = overlay
        self.bgfn = bgfn
        for i, c in enumerate(self.cuts):
            nxt = self.cuts[i + 1] if i + 1 < len(self.cuts) else None
            c["vis_end"] = c["t1"] + (nxt.get("xf", 0.0) if nxt else 0.0)

    def _cut_frame(self, c, t, readers):
        lt = t - c["t0"]
        dur = max(0.1, c["vis_end"] - c["t0"])
        q = clamp(lt / dur)
        if "bg" in c:
            return self.bgfn(c["bg"], t, lt)
        key = id(c)
        if key not in readers:
            readers[key] = Reader(c["src"], c.get("off", 0.0) + lt * c.get("speed", 1.0), c.get("speed", 1.0),
                                  c.get("focus", 0.5))
        fr = readers[key].read()
        z = c.get("z", (1.0, 1.06))
        dx = c.get("dx", (0.0, 0.0))
        dy = c.get("dy", (0.0, 0.0))
        return kenburns(fr, q, z[0], z[1], dx[0], dx[1], dy[0], dy[1])

    def frame(self, t, readers):
        act = [c for c in self.cuts if c["t0"] <= t + 1e-6 < c["vis_end"]]
        if not act:
            base = np.zeros((H, W, 3), np.uint8)
        else:
            base = self._cut_frame(act[0], t, readers).astype(np.float32)
            for c in act[1:]:
                xf = c.get("xf", 0.0)
                a = eio(ph(t, c["t0"], xf)) if xf > 0 else 1.0
                fr = self._cut_frame(c, t, readers).astype(np.float32)
                base = base * (1 - a) + fr * a
            base = base.astype(np.uint8)
        # artık görünmeyen okuyucuları kapat
        live = {id(c) for c in act}
        for k in [k for k in readers if k not in live]:
            readers.pop(k).close()
        return base

    def render_chunk(self, args):
        i0, i1, path = args
        readers = {}
        enc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                                "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "15",
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

    def render(self, out_dir, audio, out, workers=2, parts=None):
        out_dir = Path(out_dir)
        out_dir.mkdir(exist_ok=True)
        n = int(round(self.total * FPS))
        k = parts or workers * 3
        step = math.ceil(n / k)
        jobs = [(a, min(n, a + step), str(out_dir / f"p{j:02d}.mp4")) for j, a in enumerate(range(0, n, step))]
        with Pool(workers) as p:
            paths = p.map(self.render_chunk, jobs, chunksize=1)
        lst = out_dir / "list.txt"
        lst.write_text("".join(f"file '{x}'\n" for x in paths))
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-i", audio,
                        "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-shortest",
                        "-movflags", "+faststart", out], check=True)
