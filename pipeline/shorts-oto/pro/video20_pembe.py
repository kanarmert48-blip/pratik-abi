"""20. video (2K, ~19 sn): Gökkuşağında pembe yok. Yuvarlak Abi rozeti, ilk 2 sn logo yok."""
import os
os.environ.setdefault("PA_SCALE", str(4 / 3))
import json, math, subprocess, sys, hashlib
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from engine import *  # noqa
from widgets import *  # noqa
import audio_tools as at
from abi_yuz import AbiYuz, mix, konusma

WORK = Path(sys.argv[1])
MED = Path("/home/claude/pratik-abi/media/v20-pembe")
V12C = Path("/tmp/claude-0/-home-claude-pratik-abi/b79e0552-bc51-522f-903a-0721ef74ac4f/scratchpad/v12/cache")
words = json.loads((WORK / "words.json").read_text(encoding="utf-8"))
TOTAL = at.duration(str(WORK / "voice_cut.wav"))
TW, TH = round(W * 1.04), round(H * 1.04)


def _hits(key):
    k = trl(clean(key)).strip('"!?;,.…')
    return [w for w in words if trl(clean(w["w"])).strip('"!?;,.…') == k]


def T(key, nth=0):
    return _hits(key)[nth]["s"]


t_pem, t_cunku, t_yok2, t_gozun, t_kir, t_mavi = T("Pembe", 0), T("Çünkü"), T("yok", 1), T("Gözün"), T("kırmızı"), T("mavi")
t_beyn, t_uyd, t_yani, t_sen, t_yor = T("beynin"), T("uyduruyor"), T("Yani"), T("Sen"), T("Yorumlara")
t_hat = t_yor

# (tür, kaynak, başlangıç ofseti, yatay odak, başlangıç zamanı)
CL = json.loads(os.environ.get("V20_CLIPS", "{}"))
def C(k, d):
    return MED / CL.get(k, d)
CUTS = [("vid", C("hook", "gokkusagi_1.mp4"), 0.0, 0.5, 0.0),
        ("vid", C("prizma", "prizma_1.mp4"), 0.0, 0.5, t_cunku),
        ("vid", C("teker", "prizma_2.mp4"), 0.0, 0.5, t_gozun),
        ("vid", C("pembe", "pembe_1.mp4"), 0.0, 0.5, t_yani),
        ("vid", C("son", "gokkusagi_1.mp4"), 2.5, 0.5, t_sen)]
STARTS = [c[4] for c in CUTS] + [TOTAL]
SEGS = [(c, STARTS[i + 1] - c[4]) for i, c in enumerate(CUTS)]
assert all(d > 0.5 for _, d in SEGS), [round(d, 2) for _, d in SEGS]
GRADE = "eq=contrast=1.06:saturation=1.1:brightness=0.01"


def parallax(src, out, dur, focus, move=0.03, zoom=0.07, direction=1):
    import cv2
    from ai_tools import depth_map
    im = Image.open(src).convert("RGB")
    pad = 1 + zoom + move * 2
    s = max(TW * pad / im.width, TH * pad / im.height)
    im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    cw, ch = round(TW * pad), round(TH * pad)
    x0 = int(min(max(0, im.width * focus - cw / 2), im.width - cw))
    y0 = (im.height - ch) // 2
    im = im.crop((x0, y0, x0 + cw, y0 + ch))
    arr = np.asarray(im)
    d = cv2.GaussianBlur(depth_map(im), (0, 0), 8)
    yy, xx = np.mgrid[0:ch, 0:cw].astype(np.float32)
    cx, cy = cw / 2, ch / 2
    ox, oy = (cw - TW) // 2, (ch - TH) // 2
    hw, hh = TW // 2, TH // 2
    A = cv2.resize(xx[oy:oy + TH, ox:ox + TW] - cx, (hw, hh), interpolation=cv2.INTER_AREA)
    B = cv2.resize(yy[oy:oy + TH, ox:ox + TW] - cy, (hw, hh), interpolation=cv2.INTER_AREA)
    dd = cv2.resize(d[oy:oy + TH, ox:ox + TW], (hw, hh), interpolation=cv2.INTER_AREA).astype(np.float32)
    P = (0.35 + 0.65 * dd).astype(np.float32)
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{TW}x{TH}",
                          "-r", str(FPS), "-i", "-", "-vf", GRADE, "-c:v", "libx264", "-preset", "veryfast", "-crf", "14",
                          "-pix_fmt", "yuv420p", str(out)], stdin=subprocess.PIPE)
    n = int(round(dur * FPS))
    for i in range(n):
        q = i / max(1, n - 1)
        e = q * q * (3 - 2 * q)
        dx = direction * move * TW * (e - 0.5) * 2
        invz = 1.0 / (1.0 + np.float32(zoom * e) * P)
        mx = cv2.resize(np.float32(cx) + A * invz - np.float32(dx) * dd, (TW, TH), interpolation=cv2.INTER_LINEAR)
        my = cv2.resize(np.float32(cy) + B * invz, (TW, TH), interpolation=cv2.INTER_LINEAR)
        fr = cv2.remap(arr, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        p.stdin.write(np.ascontiguousarray(fr).tobytes())
    p.stdin.close()
    p.wait()


def build_track(out):
    cache = WORK / "cache"
    cache.mkdir(exist_ok=True)
    parts = []
    for i, ((kind, src, off, focus, _), dur) in enumerate(SEGS):
        key = hashlib.md5(f"{kind}{src}{off}{focus}{dur:.3f}{GRADE}{TW}".encode()).hexdigest()[:8]
        p = cache / f"{i}_{key}.mp4"
        if not p.exists():
            if kind == "px":
                parallax(src, p, dur, focus)
            else:
                n = int(round(dur * FPS))
                vf = (f"fps={FPS},scale={TW}:{TH}:force_original_aspect_ratio=increase:flags=lanczos,"
                      f"crop={TW}:{TH}:(iw-{TW})*{focus}:(ih-{TH})/2,{GRADE},format=yuv420p")
                subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-stream_loop", "-1", "-ss", str(off), "-i", str(src),
                                "-vf", vf, "-frames:v", str(n), "-an", "-c:v", "libx264", "-preset", "veryfast",
                                "-crf", "14", str(p)], check=True)
        parts.append(str(p))
    lst = cache / "l.txt"
    lst.write_text("".join(f"file '{p}'\n" for p in parts))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", out],
                   check=True)


class FullBG:
    def __init__(self, track):
        self.track = track
        self.p = None
        self.nt = 0
        y, x = np.mgrid[0:H, 0:W]
        dd = np.sqrt(((x - W / 2) / (W * 0.62)) ** 2 + ((y - H / 2) / (H * 0.64)) ** 2)
        v = np.zeros((H, W, 4), np.uint8)
        v[..., 3] = (np.clip(dd - 0.55, 0, 1) * 300).clip(0, 150).astype(np.uint8)
        g = np.zeros((H, W, 4), np.uint8)
        yy = np.arange(H)[:, None]
        g[..., 3] = (np.clip((yy - H * 0.5) / (H * 0.5) * 110, 0, 110) +
                     np.clip((H * 0.22 - yy) / (H * 0.22) * 120, 0, 120)).astype(np.uint8)
        self.ov = Image.alpha_composite(Image.fromarray(v, "RGBA"), Image.fromarray(g, "RGBA"))

    def _read(self, t):
        if self.p is None or abs(t - self.nt) > 0.5 / FPS:
            if self.p:
                self.p.kill()
            self.p = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-ss", f"{t:.4f}", "-i", self.track, "-f", "rawvideo",
                                       "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
        buf = self.p.stdout.read(TW * TH * 3)
        self.nt = t + 1 / FPS
        if len(buf) < TW * TH * 3:
            return Image.new("RGB", (TW, TH), (10, 10, 12))
        return Image.frombuffer("RGB", (TW, TH), buf, "raw", "RGB", 0, 1)

    def frame(self, t):
        src = self._read(t)
        i = max(k for k in range(len(SEGS)) if STARTS[k] <= t + 1e-6)
        lt, dur = t - STARTS[i], SEGS[i][1]
        z = 1.0 + 0.035 * min(1.0, lt / max(dur, 0.1))
        if i == 0:
            z += 0.07 * (1 - eo(ph(t, 0.0, 0.4)))      # ilk karede yakınlaşma vuruşu
        cw, ch = W / z, H / z
        cx, cy = TW / 2, TH / 2
        im = src.crop((cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2)).resize((W, H), Image.BICUBIC).convert("RGBA")
        im.alpha_composite(self.ov)
        if i > 0 and lt < 0.12:
            im.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 255, int(110 * (1 - lt / 0.12)))))
        return im


# ---------- Abi ----------
YUZ = AbiYuz()
AH = round(H * 0.25)
_sh = Image.new("RGBA", (round(AH * 0.42), round(AH * 0.06)), (0, 0, 0, 0))
ImageDraw.Draw(_sh).ellipse([0, 0, _sh.width - 1, _sh.height - 1], fill=(0, 0, 0, 130))
SHADOW = _sh.filter(ImageFilter.GaussianBlur(AH * 0.012))


def _env():
    r = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(WORK / "voice_cut.wav"), "-f", "s16le", "-ac", "1",
                        "-ar", "16000", "-"], capture_output=True, check=True)
    x = np.frombuffer(r.stdout, "<i2").astype(float) / 32768
    hop = 16000 // FPS
    e = np.array([np.sqrt(np.mean(x[i:i + hop] ** 2)) for i in range(0, len(x), hop)])
    e = e / (np.percentile(e, 95) + 1e-9)
    return np.convolve(np.clip(e, 0, 1.2), np.ones(2) / 2, mode="same")


ENV = _env()
OPN, RND = konusma(WORK / "voice_cut.wav", FPS)
EXPR_T = [(0.0, "saskin")]
t_cunku_w = t_hat


def expr_at(t):
    k = max(i for i, (st, _) in enumerate(EXPR_T) if st <= t + 1e-9)
    cur, prev = EXPR_T[k][1], EXPR_T[k - 1][1] if k > 0 else EXPR_T[k][1]
    return mix(prev, cur, float(eio(ph(t, EXPR_T[k][0] - 0.12, 0.3))))


from rozet import Rozet
ROZ = Rozet()


def abi(im, t):
    i = min(len(OPN) - 1, int(t * FPS))
    ROZ.draw(im, t, float(OPN[i]))


# ---------- grafikler ----------
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


def title(L, t, start, end, a_txt, b_txt, col=WHITE, acc=ACC, y=300):
    if not (start <= t < end):
        return
    p = ph(t, start, 0.4) * (1 - ph(t, end - 0.2, 0.2))
    if p <= 0:
        return
    bs = 96
    while bs > 50 and font("black", round(u(bs))).getlength(b_txt) > u(990):
        bs -= 2
    pop = 1 + 0.12 * (1 - eb(ph(t, start, 0.35)))
    text_c(L, (540, y + (1 - eo(p)) * 30), a_txt, "black", 64, col, alpha=eo(p), stroke=6, stroke_fill=(5, 6, 12))
    text_c(L, (540, y + 94), b_txt, "black", round(bs * pop), acc, alpha=eo(p), stroke=8, stroke_fill=(5, 6, 12))


def bchip(L, t, start, end, text, y, bg=WHITE, fg=INK, size=46, icon=None):
    if t < start or t >= end:
        return
    chip(L, 540, y, text, bg=bg, fg=fg, size=size, icon_name=icon, k="black",
         scale=eb(ph(t, start, 0.35)) * (1 - eio(ph(t, end - 0.2, 0.2))))


_SPR = {}


def _sprite(r, col=(225, 255, 190)):
    r = int(r)
    key = (r, col)
    if key not in _SPR:
        n = 2 * r + 1
        yy, xx = np.mgrid[0:n, 0:n]
        d = np.sqrt((xx - r) ** 2 + (yy - r) ** 2) / r
        a = np.clip(1 - d, 0, 1) ** 1.6
        im = np.zeros((n, n, 4), np.uint8)
        im[..., 0], im[..., 1], im[..., 2] = col
        im[..., 3] = (a * 170).astype(np.uint8)
        _SPR[key] = Image.fromarray(im, "RGBA")
    return _SPR[key]


def card_glass(L, t, start, end, x0, y0, w, h):
    a = eo(ph(t, start, 0.3)) * (1 - eio(ph(t, end - 0.2, 0.2)))
    if a > 0.02:
        glass(L, x0, y0, w, h, alpha=a)
    return a


import colorsys


def hue_rgb(h):
    r, g, b = colorsys.hsv_to_rgb(h % 1.0, 1.0, 1.0)
    return (int(r * 255), int(g * 255), int(b * 255))


MAGENTA = (255, 40, 200)


def spectrum_card(L, t, start, end):
    """Gökkuşağı tayfı (kırmızı->mor). Büyüteç tarar, pembe bulunamaz."""
    if not (start <= t < end):
        return
    a = card_glass(L, t, start, end, 100, 560, 880, 400)
    if a <= 0.02:
        return
    d = ImageDraw.Draw(L)
    x0, x1, y0, y1 = 160, 920, 690, 790
    q = eo(ph(t, start + 0.1, 0.6))
    n = 120
    for i in range(n):
        if i / n > q:
            break
        xa = x0 + (x1 - x0) * i / n
        d.rectangle([u(xa), u(y0), u(xa + (x1 - x0) / n + 1), u(y1)], fill=hue_rgb(0.75 * i / n) + (int(255 * a),))
    text_c(L, (x0 + 40, 620), "kırmızı", "black", 36, (255, 90, 90), alpha=a)
    text_c(L, (x1 - 30, 620), "mor", "black", 36, (190, 120, 255), alpha=a)
    text_c(L, (x0 + 40, 830), "700 nm", "black", 28, WHITE, alpha=a * 0.8)
    text_c(L, (x1 - 40, 830), "400 nm", "black", 28, WHITE, alpha=a * 0.8)
    # büyüteç taraması
    sw = eio(ph(t, start + 0.5, max(0.6, t_yok2 - start - 1.1)))
    mx = x0 + (x1 - x0) * sw
    if t < t_yok2 - 0.45:
        r = 62
        d.ellipse([u(mx - r), u(740 - r), u(mx + r), u(740 + r)], outline=(255, 255, 255, int(255 * a)), width=round(u(9)))
        d.line([(u(mx + r * 0.7), u(740 + r * 0.7)), (u(mx + r * 1.5), u(740 + r * 1.5))], fill=(255, 255, 255, int(255 * a)),
               width=round(u(14)))
        text_c(L, (mx, 900), "pembe?", "black", 44, MAGENTA, alpha=a, stroke=5, stroke_fill=(5, 6, 12))
    else:
        b = eb(ph(t, t_yok2 - 0.45, 0.35)) * a
        text_c(L, (540, 900), "PEMBE YOK!", "black", 64, (255, 80, 80), alpha=b, stroke=6, stroke_fill=(5, 6, 12))


def wheel_card(L, t, start, end):
    """Tayf halkaya döner; kırmızı ile mor arasındaki boşluğu beyin pembeyle doldurur."""
    if not (start <= t < end):
        return
    a = card_glass(L, t, start, end, 160, 470, 760, 640)
    if a <= 0.02:
        return
    d = ImageDraw.Draw(L)
    cx, cy, R, wd = 540, 780, 220, 64
    box = [u(cx - R), u(cy - R), u(cx + R), u(cy + R)]
    q = eo(ph(t, start + 0.1, 0.8))
    # tayf: -90 (üst) başlar, saat yönünde 270 derece
    span = 270 * q
    for k in range(int(span)):
        d.arc(box, -90 + k, -90 + k + 2, fill=hue_rgb(0.75 * k / 270) + (int(255 * a),), width=round(u(wd)))
    # boşluk: önce kesik çizgi, sonra beynin pembesi
    f = eio(ph(t, t_beyn, max(0.5, t_uyd - t_beyn + 0.4)))
    if f < 1:
        for k in range(0, 90, 10):
            d.arc(box, 180 + k, 180 + k + 5, fill=(255, 255, 255, int(150 * a * (1 - f))), width=round(u(10)))
    if f > 0:
        for k in range(int(90 * f)):
            m = k / 90
            c = tuple(int(v1 * (1 - m) + v2 * m) for v1, v2 in zip((190, 60, 255), (255, 30, 60)))
            mid = tuple(int(v) for v in MAGENTA)
            w2 = 1 - abs(m - 0.5) * 2
            c = tuple(int(c[i] * (1 - w2) + mid[i] * w2) for i in range(3))
            d.arc(box, 180 + k, 180 + k + 2, fill=c + (int(255 * a),), width=round(u(wd)))
        pul = 1 + 0.06 * math.sin((t - t_beyn) * 8)
        text_c(L, (cx, cy - 55), "BEYNİN", "black", round(46 * pul), MAGENTA, alpha=a * f, stroke=6, stroke_fill=(5, 6, 12))
        text_c(L, (cx, cy + 2), "UYDURDUĞU", "black", round(46 * pul), MAGENTA, alpha=a * f, stroke=6, stroke_fill=(5, 6, 12))
        text_c(L, (cx, cy + 59), "RENK", "black", round(46 * pul), MAGENTA, alpha=a * f, stroke=6, stroke_fill=(5, 6, 12))
    if t >= t_kir - 0.1:
        text_c(L, (cx, cy - R - 60), "kırmızı", "black", 38, (255, 90, 90), alpha=a * eo(ph(t, t_kir - 0.1, 0.3)))
    if t >= t_mavi - 0.1:
        text_c(L, (255, 860), "mavi-mor", "black", 34, (170, 130, 255), alpha=a * eo(ph(t, t_mavi - 0.1, 0.3)))


def glow(L, t, start, end):
    if not (start - 0.01 <= t < end + 0.4):
        return
    fade = eo(ph(t, start, 0.5)) * (1 - eio(ph(t, end, 0.4)))
    for x, y, r, wob in STARS:
        yy = y + 14 * math.sin(t * 1.3 + wob)
        xx = x + 10 * math.sin(t * 0.9 + wob * 2)
        spr = _sprite(u(r * 2.4), (255, 120, 210))
        al = fade * (0.5 + 0.5 * math.sin(t * 2.2 + wob))
        if al < 0.05:
            continue
        comp(L, set_alpha(spr, al), u(xx) - spr.width / 2, u(yy) - spr.height / 2)


_rng2 = np.random.default_rng(20)
STARS = [(_rng2.uniform(120, 960), _rng2.uniform(380, 1250), _rng2.uniform(4, 10), _rng2.uniform(0, 6.28)) for _ in range(55)]


def draw(t):
    L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    if t < min(3.0, t_cunku - 0.05):
        p = 1 - ph(t, min(3.0, t_cunku - 0.05) - 0.2, 0.2)
        pop = 1 + 0.12 * (1 - eb(ph(t, 0.0, 0.35)))
        text_c(L, (540, 330), "Gökkuşağında", "black", 80, WHITE, alpha=p, stroke=7, stroke_fill=(5, 6, 12))
        text_c(L, (540, 470), "PEMBE YOK!", "black", round(150 * pop), MAGENTA, alpha=p, stroke=10, stroke_fill=(5, 6, 12))
    spectrum_card(L, t, t_cunku + 0.1, t_gozun - 0.05)
    wheel_card(L, t, t_gozun + 0.05, t_yani - 0.05)
    glow(L, t, t_yani, t_sen)
    lottie(L, "1f9e0", 540, 760, 280, t, t_yani + 0.1, end=t_sen - 0.2)
    bchip(L, t, t_sen, TOTAL + 1, "Sen bunu biliyor muydun? Yorumlara yaz!", 1000, icon="speech_balloon", size=46)
    return L


class Vid(Video):
    def frame(self, t):
        im = self.bg.frame(t)
        im.alpha_composite(draw(t))
        if t >= 2.0:
            brand(im, 540, 140)
        draw_caption(im, self.groups, t, y=1160)
        abi(im, t)
        return im.convert("RGB")


if __name__ == "__main__":
    mode = sys.argv[2] if len(sys.argv) > 2 else "render"
    track = WORK / "track.mp4"
    if not track.exists():
        build_track(str(track))
    if mode == "track":
        sys.exit(0)
    bg = FullBG(str(track))
    v = Vid([{"start": 0, "end": TOTAL, "draw": lambda *a: None}], words, "", TOTAL, bg=bg)
    if mode == "frames":
        for tt in [float(x) for x in sys.argv[3].split(",")]:
            v.bg.p = None
            v.frame(tt).save(WORK / f"fr_{tt:05.1f}.png")
    else:
        sfx = [(st, "whoosh") for st in STARTS[1:-1]] + [(0.0, "pop"), (t_yok2, "pop"), (t_beyn, "pop"), (t_sen, "pop")]
        at.sfx(str(WORK / "sfx.wav"), TOTAL, sfx)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(WORK / "muzik.wav"), "-af",
                        f"apad,atrim=0:{TOTAL:.3f},afade=t=in:d=0.15,afade=t=out:st={TOTAL - 0.35:.3f}:d=0.35",
                        "-ar", "44100", "-ac", "1", str(WORK / "music.wav")], check=True)
        at.final_mix(str(WORK / "voice_cut.wav"), str(WORK / "music.wav"), str(WORK / "sfx.wav"), str(WORK / "mix.m4a"))
        v.render(str(WORK / "mix.m4a"), str(WORK / "video.mp4"))
        print("render bitti", TOTAL, flush=True)
