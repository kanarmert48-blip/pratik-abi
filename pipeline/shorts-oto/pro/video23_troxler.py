"""23. video (2K, ~35 sn): Ortadaki noktaya bak, renkler yok olsun (Troxler etkisi). Sinematik koyu tasarım.
Kullanım: python3 video23_troxler.py <WORK> [frames t1,t2,...]"""
import os
os.environ.setdefault("PA_SCALE", str(4 / 3))
import json, math, subprocess, sys
from pathlib import Path

import numpy as np
import cv2

sys.path.insert(0, str(Path(__file__).resolve().parent))
from engine import *  # noqa
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


Z = json.loads((WORK / "zaman.json").read_text())
t_st, t_sw = Z["stare"], Z["switch"]
t_kirp_e = _hits("kırpma")[0]["e"]
t_geri, t_ekr, t_beyn, t_kac = T("Geri"), T("Ekranda"), T("Beynin"), T("Kaçıncı")
QUIET_END = t_geri - 0.1           # bu ana kadar ekranda sadece ışıklar + nişangâh

GOLD = (255, 205, 96)
SOFT = (226, 230, 242)

# ---------- arka plan: koyu lacivert, vinyet, sabit doku ----------
_yy, _xx = np.mgrid[0:H, 0:W].astype(np.float32)
_r = np.sqrt(((_xx - W / 2) / W) ** 2 + ((_yy - H * 0.47) / H) ** 2)
BGF = np.zeros((H, W, 3), np.float32)
for c, (a, b) in enumerate(zip((20, 25, 46), (4, 5, 11))):
    BGF[..., c] = b + (a - b) * np.clip(1 - _r * 1.7, 0, 1) ** 1.4
BGF += np.random.default_rng(1).normal(0, 2.2, (H, W, 1)).astype(np.float32)
del _yy, _xx, _r

# ---------- ışık küreleri ----------
CX, CY = W / 2, u(900)
_rng = np.random.default_rng(31)
PAL = [(255, 64, 170), (40, 200, 255), (255, 186, 40), (120, 235, 90), (160, 100, 255), (255, 110, 70),
       (40, 230, 200), (255, 80, 110), (90, 150, 255), (230, 120, 255), (190, 240, 70), (255, 150, 60)]
ORBS = []
for i, col in enumerate(PAL):                                 # iç halka
    ang = i / len(PAL) * 2 * math.pi + _rng.uniform(-0.18, 0.18)
    rad = u(_rng.uniform(300, 470))
    ORBS.append((math.cos(ang) * rad, math.sin(ang) * rad * 1.3, u(_rng.uniform(105, 150)), col, _rng.uniform(0, 6.28)))
for i in range(10):                                           # dış halka
    ang = i / 10 * 2 * math.pi + 0.3 + _rng.uniform(-0.15, 0.15)
    rad = u(_rng.uniform(600, 760))
    col = PAL[(i * 5 + 3) % len(PAL)]
    ORBS.append((math.cos(ang) * rad, math.sin(ang) * rad * 1.25, u(_rng.uniform(120, 175)), col, _rng.uniform(0, 6.28)))
Q = 4
HW, HH = W // Q, H // Q
_gy, _gx = np.mgrid[0:HH, 0:HW].astype(np.float32)
_FC = {}


def orbs(t):
    """Katkılı parlayan küreler. 0-0.8 sn merkezden açılır, bakışta tamamen durur (önbellekten aynı kare)."""
    amp = 1.0 - eio(ph(t, t_st - 0.7, 1.0))
    if amp <= 0.001 and "s" in _FC:
        return _FC["s"]
    bloom = 0.75 + 0.25 * eo(ph(t, 0.0, 0.6))
    acc = np.zeros((HH, HW, 3), np.float32)
    for k, (ox, oy, r, col, p0) in enumerate(ORBS):
        b = 0.7 + 0.3 * eo(ph(t, 0.015 * k, 0.5))
        s = bloom
        x = CX + ox * s + amp * u(34) * math.sin(t * 0.8 + p0)
        y = CY + oy * s + amp * u(34) * math.cos(t * 0.65 + p0 * 1.3)
        rr = r * (0.6 + 0.4 * b) * (1 + amp * 0.07 * math.sin(t * 1.2 + p0))
        d2 = ((_gx - x / Q) ** 2 + (_gy - y / Q) ** 2) / (rr / Q) ** 2
        a = np.exp(-d2 * 1.25) * 0.82 * b
        acc += a[..., None] * np.array(col, np.float32)
    acc = cv2.GaussianBlur(acc, (0, 0), 5)
    big = cv2.resize(acc, (W, H), interpolation=cv2.INTER_CUBIC)
    img = BGF + big
    flash = 1 - eo(ph(t, 0.0, 0.35))                          # açılış ışık patlaması
    if flash > 0.01:
        img = img + 0 * flash
    im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).convert("RGBA")
    if amp <= 0.001:
        _FC["s"] = im
    return im


# ---------- nişangâh ----------
DOT = (CX, CY)
_SPR = {}


def glowdot(L, x, y, r, col, a, power=1.8):
    r = int(r)
    key = (r, col, power)
    if key not in _SPR:
        n = 2 * r + 1
        yy, xx = np.mgrid[0:n, 0:n]
        d = np.sqrt((xx - r) ** 2 + (yy - r) ** 2) / r
        al = np.clip(1 - d, 0, 1) ** power
        arr = np.zeros((n, n, 4), np.uint8)
        arr[..., :3] = col
        arr[..., 3] = (al * 255).astype(np.uint8)
        _SPR[key] = Image.fromarray(arr, "RGBA")
    if a > 0.01:
        comp(L, set_alpha(_SPR[key], a), x - r, y - r)


def reticle(L, t):
    a = 1.0
    x, y = DOT
    d = ImageDraw.Draw(L)
    glowdot(L, x, y, u(40), (255, 255, 255), 0.35 * a, 2.2)
    r = u(9)
    d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 255, 255, int(255 * a)))
    R = u(34)
    d.ellipse([x - R, y - R, x + R, y + R], outline=(255, 255, 255, int(120 * a)), width=round(u(3)))
    for k in range(4):                                     # dört ince işaret
        ang = k * math.pi / 2
        x0, y0 = x + math.cos(ang) * u(46), y + math.sin(ang) * u(46)
        x1, y1 = x + math.cos(ang) * u(62), y + math.sin(ang) * u(62)
        d.line([(x0, y0), (x1, y1)], fill=(255, 255, 255, int(170 * a)), width=round(u(3)))
    if t_st <= t < t_sw:                                   # bakış süresi halkası
        q = clamp((t - t_st) / (t_sw - t_st))
        b = eo(ph(t, t_st, 0.4)) * (1 - eio(ph(t, t_sw - 0.25, 0.25)))
        d.arc([x - R, y - R, x + R, y + R], -90, -90 + 360 * q, fill=GOLD + (int(235 * b),), width=round(u(4)))


# ---------- tipografi ----------
def ftext(L, x, y, txt, k, size, col, a=1.0, track=0.0, anchor="mm", glow=0.0):
    """Harf aralıklı, yumuşak gölgeli yazı (1080 birim)."""
    if a <= 0.01:
        return
    f = font(k, round(u(size)))
    sp = u(size) * track
    ws = [f.getlength(c) for c in txt]
    tw = sum(ws) + sp * max(0, len(txt) - 1)
    h = round(u(size) * 1.6)
    tmp = Image.new("RGBA", (int(tw + u(80)), h), (0, 0, 0, 0))
    m = Image.new("L", tmp.size, 0)
    dm = ImageDraw.Draw(m)
    cx = u(40)
    for c, w in zip(txt, ws):
        dm.text((cx, h / 2), c, font=f, fill=255, anchor="lm")
        cx += w + sp
    sh = m.filter(ImageFilter.GaussianBlur(u(size) * 0.12)).point(lambda v: int(v * 0.75))
    out = Image.new("RGBA", tmp.size, (0, 0, 0, 0))
    s_img = Image.new("RGBA", tmp.size, (0, 0, 0, 255))
    s_img.putalpha(sh)
    out.alpha_composite(s_img, (0, round(u(size) * 0.05)))
    if glow:
        g = m.filter(ImageFilter.GaussianBlur(u(size) * 0.35)).point(lambda v: int(v * glow))
        g_img = Image.new("RGBA", tmp.size, col + (255,))
        g_img.putalpha(g)
        out.alpha_composite(g_img)
    c_img = Image.new("RGBA", tmp.size, col + (255,))
    c_img.putalpha(m)
    out.alpha_composite(c_img)
    ax = {"l": 0, "m": 0.5, "r": 1}[anchor[0]]
    comp(L, set_alpha(out, a), u(x) - u(40) - tw * ax, u(y) - h / 2)


def hook_title(L, t):
    end = t_st - 0.1
    if t >= end + 0.4:
        return
    out = 1 - eio(ph(t, end - 0.3, 0.5))
    for i, (y, txt, k, sz, col, tr) in enumerate(((235, "ORTADAKİ NOKTAYA BAK", "xb", 40, GOLD, 0.28),
                                                   (350, "RENKLER", "black", 150, (255, 255, 255), 0.02),
                                                   (488, "YOK OLACAK", "black", 112, (255, 255, 255), 0.04))):
        q = 0.75 + 0.25 * eo(ph(t, 0.05 * i, 0.4))
        ftext(L, 540, y + (1 - q) * 60, txt, k, sz, col, a=q * out, track=tr, glow=0.25 if i else 0.0)


def captions(L, groups, t):
    for st, en, g in groups:
        if st <= t < en:
            break
    else:
        return
    a = eo(ph(t, st, 0.15)) * (1 - ph(t, en - 0.08, 0.08))
    f = font("black", round(u(56)))
    texts = [clean(w["w"]) for w in g]
    sp = f.getlength(" ")
    tw = sum(f.getlength(x) for x in texts) + sp * (len(texts) - 1)
    x = W / 2 - tw / 2
    y = u(1395)
    tmp = Image.new("RGBA", (W, round(u(140))), (0, 0, 0, 0))
    d = ImageDraw.Draw(tmp)
    for w, tx in zip(g, texts):
        on = w["s"] - 0.04 <= t < w["e"] + 0.05
        d.text((x, tmp.height / 2), tx, font=f, fill=GOLD if on else (255, 255, 255), anchor="lm",
               stroke_width=round(u(5)), stroke_fill=(6, 8, 14))
        x += f.getlength(tx) + sp
    comp(L, set_alpha(tmp, a), 0, y - tmp.height / 2)


# ---------- kanıt ve açıklama ----------
_TH = {}


def thumb():
    if "t" not in _TH:
        im = orbs(t_st + 2.0).copy()
        reticle(im, t_st - 1.0)
        s = round(u(560))
        cx, cy = int(CX), int(CY)
        im = im.crop((cx - s, cy - s, cx + s, cy + s)).resize((round(u(270)), round(u(270))), Image.LANCZOS)
        w = im.width
        m = Image.new("L", (w * 4, w * 4), 0)
        ImageDraw.Draw(m).ellipse([0, 0, w * 4 - 1, w * 4 - 1], fill=255)
        im.putalpha(m.resize((w, w), Image.LANCZOS))
        ring = Image.new("RGBA", (w + 12, w + 12), (0, 0, 0, 0))
        ImageDraw.Draw(ring).ellipse([0, 0, w + 11, w + 11], outline=(255, 255, 255, 220), width=5)
        ring.alpha_composite(im, (6, 6))
        _TH["t"] = ring
    return _TH["t"]


def dim(L, a):
    if a > 0.01:
        L.alpha_composite(Image.new("RGBA", (W, H), (4, 6, 12, int(200 * a))))


def proof(L, t):
    st, en = t_ekr - 0.15, t_beyn - 0.05
    a = eo(ph(t, st, 0.35)) * (1 - eio(ph(t, en - 0.25, 0.3)))
    if a <= 0.01:
        return 0.0
    th = thumb()
    for i, (x, lab) in enumerate(((300, "0. SANİYE"), (780, "14. SANİYE"))):
        q = eo(ph(t, st + 0.1 + 0.18 * i, 0.5))
        im = th.resize((max(1, int(th.width * (0.85 + 0.15 * q))),) * 2, Image.BICUBIC)
        comp(L, set_alpha(im, a * q), u(x) - im.width / 2, u(880) - im.height / 2)
        ftext(L, x, 1070, lab, "xb", 34, SOFT, a=a * q, track=0.22)
    q = eo(ph(t, st + 0.5, 0.4))
    ftext(L, 540, 880, "=", "black", 120, GOLD, a=a * q, glow=0.4)
    q2 = eo(ph(t, st + 0.7, 0.5))
    ftext(L, 540, 560, "EKRANDA", "xb", 44, GOLD, a=a * q2, track=0.3)
    ftext(L, 540, 650, "Hiçbir şey değişmedi", "black", 78, (255, 255, 255), a=a * q2)
    return a


def explain(L, t):
    st, en = t_beyn - 0.1, t_kac - 0.05
    a = eo(ph(t, st, 0.35)) * (1 - eio(ph(t, en - 0.25, 0.3)))
    if a <= 0.01:
        return 0.0
    q0 = eo(ph(t, st, 0.5))
    ftext(L, 540, 470, "Beynin", "black", 96, (255, 255, 255), a=a * q0)
    ftext(L, 540, 580, "değişmeyeni siler", "black", 84, GOLD, a=a * eo(ph(t, st + 0.15, 0.5)), glow=0.25)
    # sinyal grafiği: zamanla sönen çizgi
    x0, x1, y0, y1 = u(170), u(910), u(760), u(1120)
    d = ImageDraw.Draw(L)
    d.line([(x0, y1), (x1, y1)], fill=(255, 255, 255, int(90 * a)), width=round(u(3)))
    d.line([(x0, y0 - u(20)), (x0, y1)], fill=(255, 255, 255, int(90 * a)), width=round(u(3)))
    q = eio(ph(t, st + 0.4, 2.2))
    n = max(2, int(120 * q))
    pts = []
    for i in range(n):
        s = i / 119
        yv = y0 + (y1 - y0) * (1 - math.exp(-4.2 * s)) * 0.92
        pts.append((x0 + (x1 - x0) * s, yv))
    if len(pts) > 1:
        d.line(pts, fill=GOLD + (int(240 * a),), width=round(u(6)), joint="curve")
        glowdot(L, pts[-1][0], pts[-1][1], u(26), GOLD, 0.9 * a, 2.0)
    ftext(L, 175, 735, "SİNYAL", "xb", 28, SOFT, a=a * 0.85, track=0.25, anchor="lm")
    ftext(L, 905, 1160, "ZAMAN", "xb", 28, SOFT, a=a * 0.85, track=0.25, anchor="rm")
    q3 = eo(ph(t, st + 1.2, 0.6))
    ftext(L, 540, 1265, "TROXLER ETKİSİ  ·  1804", "xb", 36, SOFT, a=a * q3, track=0.22)
    return a


def cta(L, t):
    st = t_kac - 0.1
    if t < st:
        return
    q = eb(ph(t, st, 0.4))
    chip(L, 540, 1250, "Kaçıncı saniyede kayboldu?", bg=(255, 255, 255), fg=INK, size=50, icon_name="speech_balloon",
         k="black", scale=q)


def pulse(L, t):
    q = ph(t, t_geri - 0.05, 0.9)
    if 0 < q < 1:
        R = u(80 + 700 * eo(q))
        d = ImageDraw.Draw(L)
        d.ellipse([DOT[0] - R, DOT[1] - R, DOT[0] + R, DOT[1] + R], outline=(255, 255, 255, int(150 * (1 - q))),
                  width=round(u(6)))


# ---------- Abi ----------
ROZ = Rozet()
OPN, RND = konusma(WORK / "voice_cut.wav", FPS)


def abi(im, t):
    a = (1 - eio(ph(t, t_kirp_e + 0.3, 0.4))) if t < t_sw else eo(ph(t, QUIET_END + 0.3, 0.4))
    if a > 0.01:
        i = min(len(OPN) - 1, int(t * FPS))
        ROZ.draw(im, t, float(OPN[i]), alpha=a)


class Vid(Video):
    def frame(self, t):
        im = orbs(t).copy()
        L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        hook_title(L, t)
        if t >= QUIET_END:
            pulse(L, t)
            da = max(eo(ph(t, t_ekr - 0.2, 0.35)) * (1 - eio(ph(t, t_kac - 0.3, 0.5))), 0.0)
            dim(L, da)
            proof(L, t)
            explain(L, t)
        reticle(L, t) if not (t_ekr - 0.1 < t < t_kac - 0.1) else None
        cta(L, t)
        im.alpha_composite(L)
        if 2.0 <= t < t_st - 0.2 or t >= t_kac - 0.1:
            brand(im, 540, 110)
        if not (t_kirp_e + 0.2 < t < QUIET_END):
            C = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            captions(C, self.groups, t)
            im.alpha_composite(C)
        abi(im, t)
        return im.convert("RGB")


def tick_track(path, times):
    SR = 44100
    y = np.frombuffer(subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(path), "-f", "f32le", "-ac", "1", "-ar",
                                      str(SR), "-"], capture_output=True, check=True).stdout, np.float32).copy()
    rng = np.random.default_rng(5)
    m = int(0.025 * SR)
    tt = np.arange(m) / SR
    clk = (rng.standard_normal(m) * 0.5 + np.sin(2 * np.pi * 3200 * tt)) * np.exp(-tt * 260) * 0.2
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
        sfx = [(0.0, "whoosh"), (0.05, "tink"), (t_st, "pop"), (t_sw, "tink"), (t_geri, "whoosh"), (t_ekr - 0.1, "pop"),
               (t_beyn - 0.1, "pop"), (t_kac - 0.1, "pop")]
        at.sfx(str(WORK / "sfx.wav"), TOTAL, sfx)
        tick_track(WORK / "sfx.wav", [t_sw - k for k in range(1, 6)])
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-stream_loop", "2", "-i", str(WORK / "muzik.wav"), "-af",
                        f"atrim=0:{TOTAL:.3f},afade=t=in:d=0.15,afade=t=out:st={TOTAL - 0.5:.3f}:d=0.5",
                        "-ar", "44100", "-ac", "1", str(WORK / "music.wav")], check=True)
        at.final_mix(str(WORK / "voice_cut.wav"), str(WORK / "music.wav"), str(WORK / "sfx.wav"), str(WORK / "mix.m4a"))
        v.render(str(WORK / "mix.m4a"), str(WORK / "video.mp4"))
        print("render bitti", TOTAL, flush=True)
