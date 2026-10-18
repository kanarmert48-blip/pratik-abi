"""15. video (2K, tek konu, döngülü): 500 tonluk bulut neden düşmüyor?
Arka plan: gerçek video klipler (Pixabay) + 1 Wan sahnesi (buzdolabı) + 1 fotoğraf (3D hareket).
Abi: tam boy, sol altta, sadece yüz ifadeleri. Sonda kapanış yok: son cümle başa bağlanır."""
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
MED = Path("/home/claude/pratik-abi/media/v15-bulut")
V12C = Path("/tmp/claude-0/-home-claude-pratik-abi/b79e0552-bc51-522f-903a-0721ef74ac4f/scratchpad/v12/cache")
words = json.loads((WORK / "words.json").read_text(encoding="utf-8"))
TOTAL = at.duration(str(WORK / "voice_cut.wav"))
TW, TH = round(W * 1.04), round(H * 1.04)


def _hits(key):
    k = trl(clean(key)).strip('"!?;,.…')
    return [w for w in words if trl(clean(w["w"])).strip('"!?;,.…') == k]


def T(key, nth=0):
    return _hits(key)[nth]["s"]


t_100, t_peki, t_cunku, t_her, t_yuk = T("100"), T("Peki"), T("Çünkü"), T("Her"), T("Yükselen")
t_bir, t_milyon, t_ve, t_hamb, t_son, t_hat = T("Bir", 0), T("milyon"), T("Ve"), T("hamburger"), T("Bir", 1), T("hatırla")
t_bicak = t_100  # (şablon uyumu)

# (tür, kaynak, başlangıç ofseti, yatay odak, başlangıç zamanı)
CL = json.loads(os.environ.get("V15_CLIPS", "{}"))
def C(k, d):
    return MED / CL.get(k, d)
CUTS = [("vid", C("hook", "kumulus_1.mp4"), 0.0, 0.5, 0.0),
        ("vid", C("fil", "fil_1.mp4"), 0.5, 0.5, t_100),
        ("vid", C("yukari", "gokyuzu_1.mp4"), 0.0, 0.5, t_peki),
        ("vid", C("sis", "sis_1.mp4"), 0.0, 0.5, t_cunku),
        ("vid", C("damla", "damla_1.mp4"), 0.0, 0.5, t_her),
        ("vid", C("olusum", "kumulus_2.mp4"), 0.0, 0.5, t_yuk),
        ("vid", C("yagmur", "yagmur_1.mp4"), 0.0, 0.5, t_bir),
        ("vid", C("yagmur2", "yagmur_2.mp4"), 0.0, 0.5, t_ve),
        ("vid", C("hook", "kumulus_1.mp4"), 3.0, 0.5, t_son)]
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
EXPR_T = [(0.0, "saskin"), (t_100, "komik"), (t_peki, "merak"), (t_cunku, "dusunce"), (t_her, "saskin"),
          (t_yuk, "mutlu"), (t_bir, "saskin"), (t_ve, "komik"), (t_son, "mutlu")]
t_cunku_w = t_hat


def expr_at(t):
    k = max(i for i, (st, _) in enumerate(EXPR_T) if st <= t + 1e-9)
    cur, prev = EXPR_T[k][1], EXPR_T[k - 1][1] if k > 0 else EXPR_T[k][1]
    return mix(prev, cur, float(eio(ph(t, EXPR_T[k][0] - 0.12, 0.3))))


def abi(im, t):
    i = min(len(OPN) - 1, int(t * FPS))
    lvl = 0.12 + 0.38 * float(OPN[i])                                   # dümenden ağız: sesin hecelerine göre açılır
    wink = float(math.sin(min(1.0, max(0.0, (t - t_hat) / 0.4)) * math.pi))
    fig = YUZ.frame(t, level=lvl, expr=expr_at(t), height=AH, wink=wink, rnd=float(RND[i]))
    feet_y = H - round(u(34))
    cx = round(u(45)) + round(174 * AH / 1024)
    comp(im, SHADOW, cx - SHADOW.width / 2, feet_y - SHADOW.height * 0.55)
    comp(im, fig, cx - fig.width * 346 / 687, feet_y - fig.height * 1005 / 1024)


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


# gaz parçacıkları: yumuşak, yükselen, hafif dalgalı kabarcıklar
_rng = np.random.default_rng(14)
PARTS = [(_rng.uniform(260, 820), _rng.uniform(0, 1), _rng.uniform(0.18, 0.32), _rng.uniform(16, 40),
          _rng.uniform(0, 6.28)) for _ in range(46)]
_SPR = {}


def _sprite(r):
    r = int(r)
    if r not in _SPR:
        n = 2 * r + 1
        yy, xx = np.mgrid[0:n, 0:n]
        d = np.sqrt((xx - r) ** 2 + (yy - r) ** 2) / r
        a = np.clip(1 - d, 0, 1) ** 1.6
        im = np.zeros((n, n, 4), np.uint8)
        im[..., 0], im[..., 1], im[..., 2] = 225, 255, 190
        im[..., 3] = (a * 150).astype(np.uint8)
        _SPR[r] = Image.fromarray(im, "RGBA")
    return _SPR[r]


def gas(L, t, start, end, y_from=1550, y_to=350):
    if not (start - 0.01 <= t < end + 0.5):
        return
    fade = eo(ph(t, start, 0.5)) * (1 - eio(ph(t, end, 0.5)))
    for x0, ph0, sp, r, wob in PARTS:
        q = (ph0 + (t - start) * sp) % 1.0
        y = y_from + (y_to - y_from) * q
        x = x0 + 40 * math.sin(t * 1.7 + wob) * q
        a = fade * math.sin(q * math.pi)
        if a < 0.05:
            continue
        spr = _sprite(u(r * (0.7 + 0.6 * q)))
        if a < 0.98:
            spr = set_alpha(spr, a)
        comp(L, spr, u(x) - spr.width / 2, u(y) - spr.height / 2)


def card_glass(L, t, start, end, x0, y0, w, h):
    a = eo(ph(t, start, 0.3)) * (1 - eio(ph(t, end - 0.2, 0.2)))
    if a > 0.02:
        glass(L, x0, y0, w, h, alpha=a)
    return a


def hair_vs_drop(L, t, start, end):
    """Saç teli ve bulut damlası boyut karşılaştırması."""
    if not (start <= t < end):
        return
    a = card_glass(L, t, start, end, 160, 560, 760, 420)
    if a <= 0.02:
        return
    d = ImageDraw.Draw(L)
    k = eo(ph(t, start + 0.15, 0.5))
    # saç teli (kalın kahverengi şerit)
    d.rounded_rectangle([u(330 - 45), u(600), u(330 + 45), u(600 + 290 * k)], radius=u(40),
                        fill=(120, 78, 45, int(255 * a)))
    text_c(L, (330, 930), "Saç teli", "black", 40, WHITE, alpha=a)
    # bulut damlası (minicik)
    if t >= start + 0.6:
        b = eb(ph(t, start + 0.6, 0.4)) * a
        r = u(9) * b
        d.ellipse([u(720) - r, u(745) - r, u(720) + r, u(745) + r], fill=(140, 210, 255, int(255 * a)))
        text_c(L, (720, 930), "Bulut damlası", "black", 40, (140, 210, 255), alpha=b)
        arrow(L, t, start + 0.8, (720, 640), (720, 735), bend=0.0, col=(140, 210, 255), width=8, gap=6)


def rising(L, t, start, end):
    """Yükselen sıcak hava: yukarı süzülen ok başları."""
    if not (start - 0.01 <= t < end + 0.3):
        return
    fade = eo(ph(t, start, 0.4)) * (1 - eio(ph(t, end, 0.3)))
    d = ImageDraw.Draw(L)
    for col_x in (250, 540, 830):
        for k in range(5):
            q = ((t - start) * 0.55 + k / 5 + col_x / 1000) % 1.0
            y = 1250 - 700 * q
            al = fade * math.sin(q * math.pi)
            if al < 0.05:
                continue
            c = (255, 170, 90, int(220 * al))
            w = round(u(10))
            d.line([(u(col_x - 50), u(y + 40)), (u(col_x), u(y)), (u(col_x + 50), u(y + 40))], fill=c, width=w,
                   joint="curve")


def counter(L, t, start, end):
    if not (start <= t < end):
        return
    a = card_glass(L, t, start, end, 140, 600, 800, 300)
    if a <= 0.02:
        return
    q = eio(ph(t, start + 0.2, 1.3))
    n = int(round(1_000_000 * q))
    txt = f"{n:,}".replace(",", ".")
    text_c(L, (540, 720), txt, "black", 120, ACC, alpha=a, stroke=6, stroke_fill=(5, 6, 12))
    text_c(L, (540, 835), "damlacık = 1 yağmur damlası", "black", 42, WHITE, alpha=a)


def drop_shapes(L, t, start, end):
    """Gözyaşı şekli (yanlış) -> hamburger ekmeği şekli (doğru)."""
    if not (start <= t < end):
        return
    a = card_glass(L, t, start, end, 140, 560, 800, 440)
    if a <= 0.02:
        return
    d = ImageDraw.Draw(L)
    blue = (120, 200, 255)
    # sol: gözyaşı şekli
    cx, cy, R = 330, 790, 80
    d.ellipse([u(cx - R), u(cy - R), u(cx + R), u(cy + R)], fill=blue + (int(235 * a),))
    d.polygon([(u(cx - R * 0.72), u(cy - R * 0.69)), (u(cx), u(cy - R * 2.1)), (u(cx + R * 0.72), u(cy - R * 0.69))],
              fill=blue + (int(235 * a),))
    text_c(L, (cx, 955), "Sandığın", "black", 40, WHITE, alpha=a)
    if t >= start + 0.7:  # kırmızı çarpı
        p = eo(ph(t, start + 0.7, 0.3))
        w = round(u(16))
        d.line([(u(cx - 95), u(cy - 150)), (u(cx - 95 + 190 * p), u(cy - 150 + 230 * p))], fill=RED + (int(255 * a),), width=w)
        if p > 0.5:
            d.line([(u(cx + 95), u(cy - 150)), (u(cx + 95 - 190 * (p - 0.5) * 2), u(cy - 150 + 230 * (p - 0.5) * 2))],
                   fill=RED + (int(255 * a),), width=w)
    # sağ: hamburger ekmeği şekli (üstü yuvarlak, altı düz)
    if t >= start + 1.2:
        b = eb(ph(t, start + 1.2, 0.45)) * a
        cx2, cy2 = 750, 800
        rx, ry = 115 * b, 75 * b
        d.chord([u(cx2 - rx), u(cy2 - ry), u(cx2 + rx), u(cy2 + ry)], 180, 360, fill=blue + (int(245 * a),))
        d.rounded_rectangle([u(cx2 - rx), u(cy2 - 2), u(cx2 + rx), u(cy2 + 26 * b)], radius=u(12),
                            fill=blue + (int(245 * a),))
        text_c(L, (cx2, 955), "Gerçeği", "black", 40, ACC, alpha=b)


_rng2 = np.random.default_rng(15)
DROPS = [(_rng2.uniform(120, 960), _rng2.uniform(380, 1250), _rng2.uniform(4, 11), _rng2.uniform(0, 6.28))
         for _ in range(70)]


def droplets(L, t, start, end):
    """Havada asılı minicik damlacıklar (parlayan noktalar)."""
    if not (start - 0.01 <= t < end + 0.4):
        return
    fade = eo(ph(t, start, 0.5)) * (1 - eio(ph(t, end, 0.4)))
    for x, y, r, wob in DROPS:
        yy = y + 14 * math.sin(t * 1.3 + wob)
        xx = x + 10 * math.sin(t * 0.9 + wob * 2)
        spr = _sprite(u(r * 2.2))
        al = fade * (0.55 + 0.45 * math.sin(t * 2 + wob))
        if al < 0.05:
            continue
        comp(L, set_alpha(spr, al), u(xx) - spr.width / 2, u(yy) - spr.height / 2)


def draw(t):
    L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    # kanca: ilk karede hazır
    title(L, t, -1.0, t_100 - 0.05, "Şu pamuk gibi bulut", "TAM 500 TON!", acc=(255, 210, 60))
    lottie(L, "1f633", 870, 650, 170, t, -0.5, end=t_100 - 0.3)
    title(L, t, t_100, t_peki - 0.05, "Yaklaşık", "100 FİL KADAR!")
    title(L, t, t_peki, t_cunku - 0.05, "Peki neden", "DÜŞMÜYOR?", acc=(255, 120, 120))
    lottie(L, "1f914", 870, 650, 160, t, t_peki + 0.1, end=t_cunku - 0.25)
    title(L, t, t_cunku, t_her - 0.05, "O ağırlık bölünmüş:", "MİLYARLARCA DAMLA", acc=(140, 210, 255))
    droplets(L, t, t_cunku + 0.2, t_her)
    title(L, t, t_her, t_yuk - 0.05, "Her biri saç telinden", "KAT KAT İNCE", acc=(140, 210, 255))
    hair_vs_drop(L, t, t_her + 0.1, t_yuk)
    title(L, t, t_yuk, t_bir - 0.05, "Yükselen sıcak hava", "ONLARI TAŞIYOR", acc=(255, 170, 90))
    rising(L, t, t_yuk + 0.1, t_bir - 0.1)
    title(L, t, t_bir, t_ve - 0.05, "Az bilinen bilgi", "1 YAĞMUR DAMLASI =", acc=ACC)
    counter(L, t, t_bir + 0.3, t_ve)
    bchip(L, t, t_bir + 0.6, t_ve, "Sen bunu biliyor muydun? Yorumlara yaz!", 1140, icon="speech_balloon", size=42)
    title(L, t, t_ve, t_son - 0.05, "Yağmur damlası", "HAMBURGER EKMEĞİ GİBİ!", acc=(255, 210, 60))
    drop_shapes(L, t, t_ve + 0.2, t_son)
    title(L, t, t_son, TOTAL + 1, "Bir dahaki sefere", "GÖKYÜZÜNE BAK...", acc=ACC)
    lottie(L, "2601_fe0f", 870, 650, 170, t, t_son + 0.2) if os.path.exists(
        "/home/claude/araclar/noto/lottie/2601_fe0f.json") else None
    return L


class Vid(Video):
    def frame(self, t):
        im = self.bg.frame(t)
        im.alpha_composite(draw(t))
        brand(im, 540, 140)
        draw_caption(im, self.groups, t, y=1290)
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
        sfx = [(st, "whoosh") for st in STARTS[1:-1]] + [(0.0, "pop"), (t_her + 0.7, "pop"), (t_bir + 0.6, "pop"),
                                                         (t_ve + 0.9, "pop"), (t_ve + 1.4, "pop")]
        at.sfx(str(WORK / "sfx.wav"), TOTAL, sfx)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(WORK / "muzik.wav"), "-af",
                        f"apad,atrim=0:{TOTAL:.3f},afade=t=in:d=0.15,afade=t=out:st={TOTAL - 0.35:.3f}:d=0.35",
                        "-ar", "44100", "-ac", "1", str(WORK / "music.wav")], check=True)
        at.final_mix(str(WORK / "voice_cut.wav"), str(WORK / "music.wav"), str(WORK / "sfx.wav"), str(WORK / "mix.m4a"))
        v.render(str(WORK / "mix.m4a"), str(WORK / "video.mp4"))
        print("render bitti", TOTAL, flush=True)
