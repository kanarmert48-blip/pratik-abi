"""18. video (2K, tek konu 20-25 sn): Gözündeki kör nokta + ekranda deney."""
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


t_goz, t_cik, t_yok, t_ama, t_dol = T("Göz"), T("çıktığı"), T("yok"), T("Ama"), T("dolduruyor")
t_inan, t_sol, t_nokta, t_yor = T("İnanmıyor"), T("Sol"), T("Nokta", -1), T("Yorumlara")
t_hat = t_yor

# (tür, kaynak, başlangıç ofseti, yatay odak, başlangıç zamanı)
CL = json.loads(os.environ.get("V18_CLIPS", "{}"))
def C(k, d):
    return MED / CL.get(k, d)
CUTS = [("vid", C("hook", "goz_1.mp4"), 0.0, 0.5, 0.0),
        ("vid", C("anatomi", "anatomi_1.mp4"), 0.0, 0.5, t_goz),
        ("vid", C("doldur", "goz_2.mp4"), 0.0, 0.5, t_ama),
        ("vid", C("inan", "kirp_1.mp4"), 0.0, 0.5, t_inan),
        ("vid", C("test", "goz_3.mp4"), 0.0, 0.5, t_sol)]
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
EXPR_T = [(0.0, "saskin"), (t_goz, "dusunce"), (t_ama, "merak"), (t_inan, "soru"), (t_sol, "supheli"),
          (t_nokta, "saskin"), (t_yor, "mutlu")]
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


SUN = (255, 190, 60)
BLUE = (120, 200, 255)
PINK = (255, 120, 140)


def eye_card(L, t, start, end):
    """Göz kesiti: ışık ışınları retinaya gider, göz sinirinin çıktığı yer KÖR NOKTA."""
    if not (start <= t < end):
        return
    a = card_glass(L, t, start, end, 110, 500, 860, 560)
    if a <= 0.02:
        return
    d = ImageDraw.Draw(L)
    cx, cy, R = 470, 780, 200
    A = lambda c, k=1.0: c[:3] + (int(255 * a * k),)
    d.ellipse([u(cx - R), u(cy - R), u(cx + R), u(cy + R)], fill=A((245, 245, 250), 0.95), outline=A((200, 210, 230)),
              width=round(u(6)))
    # retina (arka yüzey) - pembe kalın yay
    d.arc([u(cx - R + 14), u(cy - R + 14), u(cx + R - 14), u(cy + R - 14)], -75, 75, fill=A(PINK), width=round(u(18)))
    # göz bebeği/lens (ön)
    d.ellipse([u(cx - R - 12), u(cy - 70), u(cx - R + 40), u(cy + 70)], fill=A((90, 160, 230)))
    d.ellipse([u(cx - R + 30), u(cy - 62), u(cx - R + 70), u(cy + 62)], fill=A((200, 230, 255), 0.9))
    # göz siniri (arkadan çıkan sarı bant)
    ny = cy + 40
    d.rounded_rectangle([u(cx + R - 30), u(ny - 34), u(cx + R + 170), u(ny + 34)], radius=u(30), fill=A((250, 205, 90)))
    text_c(L, (cx + R + 95, ny + 70), "Göz siniri", "black", 34, (250, 205, 90), alpha=a)
    # ışık ışınları (lensten retinaya, çizilerek)
    q = eio(ph(t, start + 0.3, 0.9))
    for dy in (-60, 0, 60):
        x0, y0 = cx - R - 110, cy + dy
        x1, y1 = cx - R + 40, cy + dy * 0.7
        x2, y2 = cx + R - 22, cy - dy * 0.9
        p = min(1.0, q * 2)
        d.line([(u(x0), u(y0)), (u(x0 + (x1 - x0) * p), u(y0 + (y1 - y0) * p))], fill=A((255, 240, 150)), width=round(u(6)))
        if q > 0.5:
            p2 = (q - 0.5) * 2
            d.line([(u(x1), u(y1)), (u(x1 + (x2 - x1) * p2), u(y1 + (y2 - y1) * p2))], fill=A((255, 240, 150)),
                   width=round(u(6)))
    # kör nokta işareti
    if t >= t_cik:
        b = eb(ph(t, t_cik, 0.35)) * a
        pul = 1 + 0.18 * math.sin((t - t_cik) * 9)
        r = 26 * pul * b
        bx, by = cx + R - 18, ny
        d.ellipse([u(bx - r), u(by - r), u(bx + r), u(by + r)], fill=(230, 40, 50, int(255 * b)))
        text_c(L, (650, 560), "KÖR NOKTA", "black", 62, (255, 80, 80), alpha=b, stroke=6, stroke_fill=(5, 6, 12))
        arrow(L, t, t_cik + 0.15, (650, 600), (bx - 10, by - 34), bend=-0.25, col=(255, 80, 80), width=8, gap=8)
    if t >= t_yok - 0.3:
        c = eo(ph(t, t_yok - 0.3, 0.3)) * a
        text_c(L, (470, 1010), "burada görme hücresi YOK", "black", 40, WHITE, alpha=c)


def hole_fx(im, t):
    """Görüntüde kör nokta deliği açılır, sonra beynin etraftan doldurması gibi kapanır."""
    st, en = t_ama + 0.25, t_inan - 0.1
    if not (st <= t < en):
        return
    import cv2
    cx, cy, R = W // 2, round(u(800)), round(u(190))
    x0, y0, x1, y1 = cx - 2 * R, cy - 2 * R, cx + 2 * R, cy + 2 * R
    reg = np.asarray(im.crop((x0, y0, x1, y1)).convert("RGB")).astype(np.float32)
    n = reg.shape[0]
    yy, xx = np.mgrid[0:n, 0:n]
    dd = np.sqrt((xx - n / 2) ** 2 + (yy - n / 2) ** 2) / R
    m = np.clip((1.08 - dd) / 0.12, 0, 1)[..., None]
    k1 = eo(ph(t, st, 0.35))                       # delik açılır
    f = eio(ph(t, t_dol - 0.05, 0.9))              # beyin doldurur
    g = eio(ph(t, t_dol + 1.2, 0.6))               # tamamen kaybolur
    sm = cv2.resize(reg.astype(np.uint8), (n // 4, n // 4), interpolation=cv2.INTER_AREA)
    mk = cv2.resize((m[..., 0] > 0.05).astype(np.uint8) * 255, (n // 4, n // 4), interpolation=cv2.INTER_NEAREST)
    fill = cv2.resize(cv2.inpaint(sm, mk, 6, cv2.INPAINT_TELEA), (n, n), interpolation=cv2.INTER_CUBIC).astype(np.float32)
    fill = cv2.GaussianBlur(fill, (0, 0), n / 60)
    inside = np.zeros_like(reg) * (1 - f) + fill * f
    inside = inside * (1 - g) + reg * g
    out = reg * (1 - m * k1) + inside * (m * k1)
    im.paste(Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)), (x0, y0))
    if k1 * (1 - f) > 0.05:                         # delik çevresinde kesik çizgi
        d = ImageDraw.Draw(im)
        al = int(255 * k1 * (1 - f))
        for i in range(24):
            a0 = i * 15 + (t * 40) % 15
            d.arc([cx - R - 8, cy - R - 8, cx + R + 8, cy + R + 8], a0, a0 + 8, fill=(255, 80, 80, al), width=round(u(6)))


def test_card(im, t):
    """Kör nokta deneyi: beyaz kart, solda artı, sağda nokta (telefonda ~16 cm'de nokta kaybolur)."""
    st = t_sol - 0.15
    if t < st:
        return
    a = eo(ph(t, st, 0.3))
    L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(L)
    d.rectangle([0, 0, W, H], fill=(250, 250, 250, int(255 * a)))
    yc = 960
    k, th = 70, 20
    xc = 200
    d.rectangle([u(xc - k), u(yc - th / 2), u(xc + k), u(yc + th / 2)], fill=(15, 15, 20, int(255 * a)))
    d.rectangle([u(xc - th / 2), u(yc - k), u(xc + th / 2), u(yc + k)], fill=(15, 15, 20, int(255 * a)))
    r = 46
    d.ellipse([u(880 - r), u(yc - r), u(880 + r), u(yc + r)], fill=(15, 15, 20, int(255 * a)))
    im.alpha_composite(L)
    if a > 0.5:
        text_c(im, (540, 560), "1. Sol gözünü kapat", "black", 54, INK, alpha=a)
        text_c(im, (540, 640), "2. Sağ gözünle + işaretine bak", "black", 46, INK, alpha=a * eo(ph(t, T("artıya") - 0.1, 0.3)))
        text_c(im, (540, 712), "3. Telefonu yavaşça yaklaştır", "black", 46, INK, alpha=a * eo(ph(t, T("telefonu") - 0.1, 0.3)))


def draw(t):
    L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    title(L, t, -1.0, min(3.0, t_goz - 0.05), "Gözünde", "KÖR BİR NOKTA VAR!", acc=ACC)
    lottie(L, "1f633", 870, 650, 170, t, -0.5, end=t_goz - 0.2)
    eye_card(L, t, t_goz + 0.1, t_ama - 0.05)
    lottie(L, "1f9e0", 870, 560, 170, t, t_dol - 0.1, end=t_inan - 0.2)
    lottie(L, "1f914", 870, 640, 160, t, t_inan + 0.05, end=t_sol - 0.2)
    if t >= t_nokta:
        bchip(L, t, t_nokta, TOTAL + 1, "Nokta kayboldu mu? Yorumlara yaz!", 1360, icon="speech_balloon", size=46)
    return L


class Vid(Video):
    def frame(self, t):
        im = self.bg.frame(t)
        hole_fx(im, t)
        test_card(im, t)
        im.alpha_composite(draw(t))
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
        sfx = [(st, "whoosh") for st in STARTS[1:-1]] + [(0.0, "pop"), (t_cik, "pop"), (t_ama + 0.25, "pop"),
                                                         (t_dol + 0.2, "pop"), (t_nokta, "pop")]
        at.sfx(str(WORK / "sfx.wav"), TOTAL, sfx)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(WORK / "muzik.wav"), "-af",
                        f"apad,atrim=0:{TOTAL:.3f},afade=t=in:d=0.15,afade=t=out:st={TOTAL - 0.35:.3f}:d=0.35",
                        "-ar", "44100", "-ac", "1", str(WORK / "music.wav")], check=True)
        at.final_mix(str(WORK / "voice_cut.wav"), str(WORK / "music.wav"), str(WORK / "sfx.wav"), str(WORK / "mix.m4a"))
        v.render(str(WORK / "mix.m4a"), str(WORK / "video.mp4"))
        print("render bitti", TOTAL, flush=True)
