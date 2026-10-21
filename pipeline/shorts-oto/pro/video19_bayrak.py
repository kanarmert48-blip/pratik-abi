"""19. video (2K, ~34 sn): Ters renkli Türk bayrağı ardıl görüntü deneyi (tamamen kendi grafiğimiz)."""
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
MED = Path("/home/claude/pratik-abi/media/v18-kornokta")
V12C = Path("/tmp/claude-0/-home-claude-pratik-abi/b79e0552-bc51-522f-903a-0721ef74ac4f/scratchpad/v12/cache")
words = json.loads((WORK / "words.json").read_text(encoding="utf-8"))
TOTAL = at.duration(str(WORK / "voice_cut.wav"))
TW, TH = round(W * 1.04), round(H * 1.04)


def _hits(key):
    k = trl(clean(key)).strip('"!?;,.…')
    return [w for w in words if trl(clean(w["w"])).strip('"!?;,.…') == k]


def T(key, nth=0):
    return _hits(key)[nth]["s"]


Z = json.loads((WORK / "zaman.json").read_text())
t_sad, t_sw = Z["sadece"], Z["switch"]
t_kir, t_goz2, t_gor = T("Kırmızı"), T("Gözündeki"), T("Gördüysen")
t_hat = t_gor + 0.6

# (tür, kaynak, başlangıç ofseti, yatay odak, başlangıç zamanı)
CUTS = [("syn", None, 0.0, 0.5, 0.0)]
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
EXPR_T = [(0.0, "saskin"), (t_sad, "merak"), (t_sw, "saskin"), (t_goz2, "dusunce"), (t_gor, "mutlu")]
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


CYAN = (28, 245, 232)
FL_W = round(W * 0.94)
FL_H = round(FL_W / 1.5)
FL_CY = round(H * 0.47)
FL_X0, FL_Y0 = (W - FL_W) // 2, FL_CY - FL_H // 2
DOT = (W // 2, FL_CY)


def make_flag(bgc, fgc, ss=3):
    """TS 2196 ölçüleri: G=yükseklik, boy 1.5G; dış daire merkez 0.5G, çap 0.5G; iç daire 0.0625G sağda, çap 0.4G;
    yıldız çemberi iç daire merkezinden 0.333G sonra başlar, çap 0.25G; bir ucu direğe bakar."""
    G = FL_H * ss
    im = Image.new("RGB", (int(1.5 * G), G), bgc)
    d = ImageDraw.Draw(im)
    cy = G / 2
    r1, c1 = 0.25 * G, 0.5 * G
    d.ellipse([c1 - r1, cy - r1, c1 + r1, cy + r1], fill=fgc)
    r2, c2 = 0.2 * G, 0.5625 * G
    d.ellipse([c2 - r2, cy - r2, c2 + r2, cy + r2], fill=bgc)
    rs = 0.125 * G
    sx = c2 + 0.333 * G + rs
    pts = []
    for i in range(10):
        ang = math.pi + i * math.pi / 5
        rr = rs if i % 2 == 0 else rs * 0.382
        pts.append((sx + rr * math.cos(ang), cy + rr * math.sin(ang)))
    d.polygon(pts, fill=fgc)
    return im.resize((FL_W, FL_H), Image.LANCZOS)


FLAG_INV = np.asarray(make_flag(CYAN, (0, 0, 0)))
DARK = (12, 14, 20)


def flag_frame(t):
    import cv2
    im = Image.new("RGB", (W, H), DARK)
    amp = 1.0 - eio(ph(t, t_sad - 0.5, 0.6))          # dalgalanma -> 'Sadece'de durur
    if amp > 0.01:
        yy, xx = np.mgrid[0:FL_H, 0:FL_W].astype(np.float32)
        k = xx / FL_W
        dy = amp * u(18) * np.sin(xx / FL_W * 2 * math.pi * 1.4 - t * 5.5) * k
        dx = amp * u(6) * np.sin(yy / FL_H * math.pi * 2 - t * 4.0) * k
        fr = cv2.remap(FLAG_INV, xx + dx, yy + dy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=DARK)
        shade = (1 + 0.10 * amp * np.cos(xx / FL_W * 2 * math.pi * 1.4 - t * 5.5) * k)[..., None]
        fr = np.clip(fr * shade, 0, 255).astype(np.uint8)
    else:
        fr = FLAG_INV
    im.paste(Image.fromarray(fr), (FL_X0, FL_Y0))
    return im.convert("RGBA")


def stare_ui(L, t):
    if not (t_sad <= t < t_sw):
        return
    d = ImageDraw.Draw(L)
    a = eo(ph(t, t_sad, 0.3))
    r = u(11)
    d.ellipse([DOT[0] - r - u(4), DOT[1] - r - u(4), DOT[0] + r + u(4), DOT[1] + r + u(4)], fill=(255, 255, 255, int(255 * a)))
    d.ellipse([DOT[0] - r, DOT[1] - r, DOT[0] + r, DOT[1] + r], fill=(0, 0, 0, int(255 * a)))
    left = max(0.0, t_sw - t)
    n = int(math.ceil(left - 1e-6))
    text_c(L, (540, (FL_Y0 / S) - 70), str(max(1, n)), "black", 96, WHITE, alpha=a, stroke=6, stroke_fill=(5, 6, 12))
    q = (t - t_sad) / (t_sw - t_sad)
    y = FL_Y0 + FL_H + u(40)
    d.rounded_rectangle([FL_X0, y, FL_X0 + FL_W, y + u(14)], radius=u(7), fill=(255, 255, 255, int(60 * a)))
    d.rounded_rectangle([FL_X0, y, FL_X0 + FL_W * q, y + u(14)], radius=u(7), fill=CYAN + (int(230 * a),))
    text_c(L, (540, (FL_Y0 / S) - 175), "Noktaya bak • gözünü kırpma", "black", 46, WHITE, alpha=a)


def explain_card(L, t):
    st = t_goz2 - 0.1
    if t < st:
        return
    a = card_glass(L, t, st, TOTAL + 1, 140, 560, 800, 420)
    if a <= 0.02:
        return
    d = ImageDraw.Draw(L)
    for i, (c1, c2, lab) in enumerate((((28, 245, 232), (227, 10, 23), "camgöbeği → kırmızı"), ((0, 0, 0), (255, 255, 255), "siyah → beyaz"))):
        b = eb(ph(t, st + 0.2 + 0.5 * i, 0.35)) * a
        y = 660 + i * 150
        d.rounded_rectangle([u(230), u(y - 45), u(320), u(y + 45)], radius=u(14), fill=c1 + (int(255 * b),), outline=(255, 255, 255, int(200 * b)), width=round(u(3)))
        d.rounded_rectangle([u(760), u(y - 45), u(850), u(y + 45)], radius=u(14), fill=c2 + (int(255 * b),), outline=(255, 255, 255, int(200 * b)), width=round(u(3)))
        arrow(L, t, st + 0.35 + 0.5 * i, (350, y), (735, y), bend=-0.15, col=ACC, width=8, gap=6)
        text_c(L, (540, y + 72), lab, "black", 38, WHITE, alpha=b)
    if t >= T("zıt") - 0.1:
        c = eb(ph(t, T("zıt") - 0.1, 0.35)) * a
        text_c(L, (540, 925), "Beynin ZIT rengi gösterir", "black", 50, ACC, alpha=c, stroke=6, stroke_fill=(5, 6, 12))


def draw(t):
    L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    title(L, t, -1.0, min(3.0, t_sad - 0.05), "Bu bayrağa", "15 SANİYE BAK!", acc=ACC, y=230)
    stare_ui(L, t)
    if t >= t_sw:
        explain_card(L, t)
        bchip(L, t, t_gor, TOTAL + 1, "Gördüysen yorumlara yaz!", 1060, icon="speech_balloon", size=48)
    return L


WHITE_ONLY = t_goz2 - 0.3 - t_sw   # "gördün mü?" bitene kadar sadece beyaz + nokta


class Vid(Video):
    def frame(self, t):
        if t < t_sw:
            im = flag_frame(t)
            im.alpha_composite(draw(t))
            brand(im, 540, 110)
            draw_caption(im, self.groups, t, y=1330)
            abi(im, t)
            return im.convert("RGB")
        im = Image.new("RGBA", (W, H), (250, 250, 250, 255))
        d = ImageDraw.Draw(im)
        r = u(8)
        d.ellipse([DOT[0] - r, DOT[1] - r, DOT[0] + r, DOT[1] + r], fill=(150, 150, 150, 255))
        if t < t_sw + WHITE_ONLY:
            return im.convert("RGB")
        fade = eo(ph(t, t_sw + WHITE_ONLY, 0.4))
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        lay.alpha_composite(Image.new("RGBA", (W, H), (18, 20, 28, int(235 * fade))))
        lay.alpha_composite(draw(t))
        brand(lay, 540, 110)
        draw_caption(lay, self.groups, t, y=1330)
        abi(lay, t)
        im.alpha_composite(lay)
        return im.convert("RGB")


if __name__ == "__main__":
    mode = sys.argv[2] if len(sys.argv) > 2 else "render"
    v = Vid([{"start": 0, "end": TOTAL, "draw": lambda *a: None}], words, "", TOTAL, bg=None)
    if mode == "frames":
        for tt in [float(x) for x in sys.argv[3].split(",")]:
            v.frame(tt).save(WORK / f"fr_{tt:05.1f}.png")
    else:
        sfx = [(0.0, "pop"), (t_sad, "pop"), (t_sw, "whoosh"), (t_goz2, "pop"), (t_gor, "pop")]
        at.sfx(str(WORK / "sfx.wav"), TOTAL, sfx)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-stream_loop", "2", "-i", str(WORK / "muzik.wav"), "-af",
                        f"atrim=0:{TOTAL:.3f},afade=t=in:d=0.15,afade=t=out:st={TOTAL - 0.5:.3f}:d=0.5",
                        "-ar", "44100", "-ac", "1", str(WORK / "music.wav")], check=True)
        at.final_mix(str(WORK / "voice_cut.wav"), str(WORK / "music.wav"), str(WORK / "sfx.wav"), str(WORK / "mix.m4a"))
        v.render(str(WORK / "mix.m4a"), str(WORK / "video.mp4"))
        print("render bitti", TOTAL, flush=True)
