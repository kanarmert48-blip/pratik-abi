"""16. video (2K, tek konu, döngülü): vücudundaki DNA Güneş'e 20 kez gidip gelir.
Arka plan: gerçek video klipler (Pixabay). Abi: tam boy, sol altta, yüz ifadeleri + sese göre ağız."""
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
MED = Path("/home/claude/pratik-abi/media/v16-dna")
V12C = Path("/tmp/claude-0/-home-claude-pratik-abi/b79e0552-bc51-522f-903a-0721ef74ac4f/scratchpad/v12/cache")
words = json.loads((WORK / "words.json").read_text(encoding="utf-8"))
TOTAL = at.duration(str(WORK / "voice_cut.wav"))
TW, TH = round(W * 1.04), round(H * 1.04)


def _hits(key):
    k = trl(clean(key)).strip('"!?;,.…')
    return [w for w in words if trl(clean(w["w"])).strip('"!?;,.…') == k]


def T(key, nth=0):
    return _hits(key)[nth]["s"]


t_gun, t_peki, t_tek, t_cunku = T("Güneş", 0), T("Peki"), T("Tek"), T("Çünkü")
t_bunu, t_bonus, t_gm, t_yor, t_son, t_hat = T("Bunu"), T("Bonus"), T("Güneş", 2), T("Yorumlara"), T("Bir", -1), T("hatırla")

# (tür, kaynak, başlangıç ofseti, yatay odak, başlangıç zamanı)
CL = json.loads(os.environ.get("V16_CLIPS", "{}"))
def C(k, d):
    return MED / CL.get(k, d)
CUTS = [("vid", C("hook", "dna_1.mp4"), 0.0, 0.5, 0.0),
        ("vid", C("gunes", "gunes_1.mp4"), 0.0, 0.5, t_gun),
        ("vid", C("peki", "dna_4.mp4"), 0.0, 0.5, t_peki),
        ("vid", C("hucre", "hucre_2.mp4"), 0.0, 0.5, t_tek),
        ("vid", C("makara", "makara_1.mp4"), 0.0, 0.5, t_cunku),
        ("vid", C("sarmal", "dna_3.mp4"), 0.0, 0.5, T("defalarca")),
        ("vid", C("uzay", "uzay_1.mp4"), 0.0, 0.5, t_bunu),
        ("vid", C("gunes2", "uzay_3.mp4"), 0.0, 0.5, T("Güneş", 1)),
        ("vid", C("muz", "muz_3.mp4"), 0.0, 0.5, t_bonus),
        ("vid", C("muz2", "muz_4.mp4"), 0.0, 0.5, T("muzda")),
        ("vid", C("soru", "muz_1.mp4"), 0.0, 0.5, t_gm),
        ("vid", C("ayna", "ayna_3.mp4"), 0.0, 0.5, t_son)]
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
EXPR_T = [(0.0, "saskin"), (t_peki, "merak"), (t_tek, "dusunce"), (t_cunku, "mutlu"), (t_bunu, "saskin"),
          (t_bonus, "komik"), (t_gm, "soru"), (t_son, "mutlu")]
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


SUN, EARTH = (255, 190, 60), (90, 170, 255)


def trips(L, t, start, end, n_max=20):
    """Dünya <-> Güneş arasında gidip gelen ışık noktası + x20 sayacı."""
    if not (start <= t < end):
        return
    a = card_glass(L, t, start, end, 140, 560, 800, 410)
    if a <= 0.02:
        return
    d = ImageDraw.Draw(L)
    ex, sx, cy = 270, 810, 700
    d.ellipse([u(ex - 38), u(cy - 38), u(ex + 38), u(cy + 38)], fill=EARTH + (int(255 * a),))
    for k, rr in ((0.35, 110), (0.6, 88), (1.0, 70)):
        d.ellipse([u(sx - rr), u(cy - rr), u(sx + rr), u(cy + rr)], fill=SUN + (int(255 * a * k * 0.6 if k < 1 else 255 * a),))
    text_c(L, (ex, 790), "Dünya", "black", 36, WHITE, alpha=a)
    text_c(L, (sx, 848), "Güneş", "black", 36, SUN, alpha=a)
    q = eio(ph(t, start + 0.2, 1.8))
    n = int(round(n_max * q))
    # gidip gelen nokta (hızlanan ping-pong)
    ph_ = (t - start) * (1.2 + 6 * q)
    f = abs((ph_ % 2.0) - 1.0)
    x = ex + 50 + (sx - 120 - ex - 50) * (1 - f)
    spr = _sprite(u(26), (255, 245, 200))
    comp(L, set_alpha(spr, a), u(x) - spr.width / 2, u(cy) - spr.height / 2)
    d.line([(u(ex + 45), u(cy)), (u(sx - 75), u(cy))], fill=(255, 255, 255, int(70 * a)), width=round(u(4)))
    text_c(L, (540, 905), f"{n} kez gidiş-dönüş", "black", 52, ACC, alpha=a, stroke=5, stroke_fill=(5, 6, 12))


def meter(L, t, start, end):
    """Tek hücredeki DNA: büyüyen 2 metrelik cetvel."""
    if not (start <= t < end):
        return
    a = card_glass(L, t, start, end, 140, 600, 800, 300)
    if a <= 0.02:
        return
    d = ImageDraw.Draw(L)
    q = eio(ph(t, start + 0.15, 1.1))
    x0, x1, y = 200, 880, 720
    d.rounded_rectangle([u(x0), u(y - 16), u(x0 + (x1 - x0) * q), u(y + 16)], radius=u(16),
                        fill=(110, 220, 170, int(255 * a)))
    for i in range(11):
        xx = x0 + (x1 - x0) * i / 10
        if xx <= x0 + (x1 - x0) * q + 1:
            hh = 34 if i % 5 == 0 else 20
            d.line([(u(xx), u(y + 24)), (u(xx), u(y + 24 + hh))], fill=(255, 255, 255, int(200 * a)), width=round(u(4)))
    text_c(L, (540, 830), f"≈ {2 * q:.1f} metre".replace(".", ","), "black", 56, ACC, alpha=a, stroke=5,
           stroke_fill=(5, 6, 12))


def coil(L, t, start, end):
    """Kıvrılıp sıkışan DNA: frekansı artan sarmal çizgi."""
    if not (start - 0.01 <= t < end + 0.3):
        return
    a = card_glass(L, t, start, end, 140, 600, 800, 300)
    if a <= 0.02:
        return
    q = eio(ph(t, start + 0.1, 2.5))
    f = 1.5 + 9 * q
    amp = 70 * (1 - 0.45 * q)
    w = 640 * (1 - 0.55 * q)
    for strand, col in ((0, (110, 220, 170)), (math.pi, (255, 150, 200))):
        pts = []
        for i in range(160):
            k = i / 159
            x = 540 - w / 2 + w * k
            yy = 750 + amp * math.sin(k * f * math.pi * 2 + t * 3 + strand)
            pts.append((u(x), u(yy)))
        ImageDraw.Draw(L).line(pts, fill=col + (int(255 * a),), width=round(u(9)), joint="curve")


def equation(L, t, start, end):
    """2 metre x trilyonlarca hücre = milyarlarca km."""
    if not (start <= t < end):
        return
    a = card_glass(L, t, start, end, 120, 560, 840, 420)
    if a <= 0.02:
        return
    rows = [("2 metre DNA", WHITE, 0.15), ("× trilyonlarca hücre", WHITE, 0.8), ("= MİLYARLARCA KM!", ACC, 1.6)]
    for i, (txt, col, dl) in enumerate(rows):
        if t < start + dl:
            continue
        b = eb(ph(t, start + dl, 0.35)) * a
        sz = 64 if i < 2 else 74
        text_c(L, (540, 650 + i * 110), txt, "black", round(sz * (0.8 + 0.2 * b)), col, alpha=b, stroke=6,
               stroke_fill=(5, 6, 12))


def percent(L, t, start, end, val=60):
    """%60 halka sayacı (muz sarısı)."""
    if not (start <= t < end):
        return
    a = card_glass(L, t, start, end, 290, 540, 500, 460)
    if a <= 0.02:
        return
    q = eio(ph(t, start + 0.15, 1.2))
    d = ImageDraw.Draw(L)
    cx, cy, r = 540, 760, 160
    box = [u(cx - r), u(cy - r), u(cx + r), u(cy + r)]
    d.arc(box, 0, 360, fill=(255, 255, 255, int(60 * a)), width=round(u(26)))
    d.arc(box, -90, -90 + 360 * val / 100 * q, fill=(255, 220, 60, int(255 * a)), width=round(u(26)))
    text_c(L, (cx, cy), f"%{int(round(val * q))}", "black", 110, (255, 220, 60), alpha=a, stroke=6, stroke_fill=(5, 6, 12))


_rng2 = np.random.default_rng(16)
STARS = [(_rng2.uniform(120, 960), _rng2.uniform(380, 1250), _rng2.uniform(4, 10), _rng2.uniform(0, 6.28))
         for _ in range(60)]


def sparkles(L, t, start, end, col=(200, 255, 230)):
    if not (start - 0.01 <= t < end + 0.4):
        return
    fade = eo(ph(t, start, 0.5)) * (1 - eio(ph(t, end, 0.4)))
    for x, y, r, wob in STARS:
        yy = y + 14 * math.sin(t * 1.3 + wob)
        xx = x + 10 * math.sin(t * 0.9 + wob * 2)
        spr = _sprite(u(r * 2.2), col)
        al = fade * (0.5 + 0.5 * math.sin(t * 2.2 + wob))
        if al < 0.05:
            continue
        comp(L, set_alpha(spr, al), u(xx) - spr.width / 2, u(yy) - spr.height / 2)


def draw(t):
    L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    title(L, t, -1.0, t_peki - 0.05, "Vücudundaki DNA", "GÜNEŞ'E 20 KEZ GİDİP GELİR!", acc=(255, 200, 60))
    lottie(L, "1f633", 870, 650, 170, t, -0.5, end=t_gun - 0.2)
    trips(L, t, t_gun + 0.05, t_peki)
    title(L, t, t_peki, t_tek - 0.05, "Peki bu kadar uzun ip", "SANA NASIL SIĞIYOR?", acc=(255, 140, 140))
    lottie(L, "1f914", 870, 650, 160, t, t_peki + 0.1, end=t_tek - 0.25)
    title(L, t, t_tek, t_cunku - 0.05, "Tek bir hücrende", "≈ 2 METRE DNA!", acc=(110, 220, 170))
    meter(L, t, t_tek + 0.2, t_cunku)
    title(L, t, t_cunku, t_bunu - 0.05, "Makaraya sarılan ip gibi", "KIVRILIP SIKIŞIYOR", acc=(255, 150, 200))
    coil(L, t, t_cunku + 0.2, t_bunu - 0.1)
    title(L, t, t_bunu, t_bonus - 0.05, "Trilyonlarca hücreyle çarp:", "GÜNEŞ'E UZANAN İP!", acc=(255, 200, 60))
    equation(L, t, t_bunu + 0.2, t_bonus)
    sparkles(L, t, t_bunu, t_bonus, col=(255, 230, 170))
    title(L, t, t_bonus, t_gm - 0.05, "BONUS: genlerimizin", "%60'ININ MUZDA BENZERİ VAR!", acc=(255, 220, 60))
    percent(L, t, t_bonus + 0.25, t_gm)
    lottie(L, "1f62e", 870, 1020, 150, t, t_bonus + 0.6, end=t_gm - 0.2)
    title(L, t, t_gm, t_son - 0.05, "Sence hangisi daha şaşırtıcı?", "GÜNEŞ Mİ, MUZ MU?", acc=(255, 200, 60))
    bchip(L, t, t_gm + 0.1, t_son, "Güneş mi? Muz mu? Yorumlara yaz!", 1140, icon="speech_balloon", size=42)
    title(L, t, t_son, TOTAL + 1, "Bir dahaki sefere", "AYNAYA BAKINCA HATIRLA...", acc=ACC)
    lottie(L, "1f440", 870, 650, 160, t, t_son + 0.2)
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
        sfx = [(st, "whoosh") for st in STARTS[1:-1]] + [(0.0, "pop"), (t_gun + 2.0, "pop"), (t_bunu + 1.0, "pop"),
                                                         (t_bunu + 1.8, "pop"), (t_bonus + 1.4, "pop"), (t_gm + 0.1, "pop")]
        at.sfx(str(WORK / "sfx.wav"), TOTAL, sfx)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(WORK / "muzik.wav"), "-af",
                        f"apad,atrim=0:{TOTAL:.3f},afade=t=in:d=0.15,afade=t=out:st={TOTAL - 0.35:.3f}:d=0.35",
                        "-ar", "44100", "-ac", "1", str(WORK / "music.wav")], check=True)
        at.final_mix(str(WORK / "voice_cut.wav"), str(WORK / "music.wav"), str(WORK / "sfx.wav"), str(WORK / "mix.m4a"))
        v.render(str(WORK / "mix.m4a"), str(WORK / "video.mp4"))
        print("render bitti", TOTAL, flush=True)
