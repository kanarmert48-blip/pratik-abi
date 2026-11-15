"""58. video (2K Shorts, ~11 sn): Dilini burnuna değdirebilir misin? (hemen dene, cevap yok)
Yüz kodla çizilir (2x süpersampling), dil burna uzanmaya çalışır ama değmez.
Kullanım: python3 video58_dil.py <WORK> [frames t1,t2,... | ses | render]"""
import os
os.environ.setdefault("PA_SCALE", str(4 / 3))
import json, math, subprocess, sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from engine import *  # noqa
from pa_ui import put_word, txt, pop
import audio_tools as at
from abi_yuz import konusma
from rozet import Rozet

WORK = Path(sys.argv[1])
VOICE = WORK / "voice_cut.wav"
words = json.loads((WORK / "words.json").read_text(encoding="utf-8"))
MK = json.loads((WORK / "marks.json").read_text())
TOTAL = round(at.duration(str(VOICE)), 3)

GOLD = (255, 196, 40)
INKC = (24, 30, 60)
NAVY = (30, 50, 110)
RED = (235, 60, 80)
PINK = (240, 96, 128)


def ramp(t, a, b):
    return eio(clamp((t - a) / max(1e-6, b - a)))


def T(key, nth=0):
    k = trl(clean(key)).strip('"!?;,.…')
    return [w for w in words if trl(clean(w["w"])).strip('"!?;,.…') == k][nth]["s"]


t_hem = T("Hemen")
t_on = MK["tC"]
t_yap = T("Yaptıysan")
T0, TEND = MK["t0"], MK["tend"]

# ---- arka plan: sıcak turuncu-pembe degrade + yumuşak daireler ----
yy = np.linspace(0, 1, H)[:, None, None]
_bg = np.array([255, 214, 150], np.float32) * (1 - yy) + np.array([255, 140, 160], np.float32) * yy
_bg = np.broadcast_to(_bg, (H, W, 3))
BG = Image.fromarray(_bg.clip(0, 255).astype(np.uint8)).convert("RGBA")
_c = Image.new("RGBA", (W, H), (0, 0, 0, 0))
_cd = ImageDraw.Draw(_c)
for x, y, r in [(920, 420, 240), (130, 1350, 280), (960, 1800, 220)]:
    _cd.ellipse([u(x - r), u(y - r), u(x + r), u(y + r)], fill=(255, 255, 255, 70))
BG.alpha_composite(_c.filter(ImageFilter.GaussianBlur(u(60))))

# ---- yüz (yerel kutu, birim koordinatı) ----
FX0, FY0, FS = 120, 440, 840          # kutu sol-üst ve boyu
CX, CY, R = 540, 860, 370             # yüz merkezi/yarıçap
SS = 2.0
PX = round(u(FS) * SS)


def P(x, y):
    """Birim koordinatı -> süpersample kutu pikseli."""
    return ((x - FX0) * PX / FS, (y - FY0) * PX / FS)


def L_(v):
    return v * PX / FS


def make_base():
    im = Image.new("RGBA", (PX, PX), (0, 0, 0, 0))
    # gölge
    sh = Image.new("RGBA", (PX, PX), (0, 0, 0, 0))
    ImageDraw.Draw(sh).ellipse([*P(CX - R + 10, CY - R + 30), *P(CX + R + 10, CY + R + 30)], fill=(120, 40, 40, 90))
    im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(L_(22))))
    # radyal degrade yüz
    n = PX
    ys, xs = np.mgrid[0:n, 0:n].astype(np.float32)
    cx, cy = P(CX, CY)
    hx, hy = P(CX - 110, CY - 140)
    rr = np.hypot(xs - hx, ys - hy) / L_(R * 1.6)
    c0 = np.array([255, 236, 120], np.float32)
    c1 = np.array([250, 170, 30], np.float32)
    rgb = c0 * (1 - rr[..., None].clip(0, 1)) + c1 * rr[..., None].clip(0, 1)
    mask = (np.hypot(xs - cx, ys - cy) <= L_(R)).astype(np.float32)
    face = np.dstack([rgb, mask * 255]).clip(0, 255).astype(np.uint8)
    im.alpha_composite(Image.fromarray(face, "RGBA"))
    d = ImageDraw.Draw(im)
    # yanaklar
    blush = Image.new("RGBA", (PX, PX), (0, 0, 0, 0))
    bd = ImageDraw.Draw(blush)
    for sx in (-1, 1):
        bd.ellipse([*P(CX + sx * 235 - 60, CY + 90 - 32), *P(CX + sx * 235 + 60, CY + 90 + 32)], fill=(255, 110, 110, 110))
    im.alpha_composite(blush.filter(ImageFilter.GaussianBlur(L_(14))))
    # burun (gölge + gövde + parlama)
    d.ellipse([*P(CX - 58, CY + 6), *P(CX + 58, CY + 94)], fill=(225, 135, 30, 255))
    d.ellipse([*P(CX - 54, CY - 4), *P(CX + 54, CY + 86)], fill=(248, 168, 50, 255))
    d.ellipse([*P(CX - 28, CY + 10), *P(CX + 2, CY + 34)], fill=(255, 226, 150, 255))
    for sx in (-1, 1):
        d.ellipse([*P(CX + sx * 24 - 11, CY + 62), *P(CX + sx * 24 + 11, CY + 77)], fill=(150, 70, 20, 255))
    return im


BASE = make_base()
NOSE_BOT = CY + 92


def strain(t):
    """0..1 zorlanma; açılışta da çalışıyor, sayaçta en yüksek, sonda yumuşar."""
    s = 0.55 + 0.25 * ramp(t, t_hem - 0.1, t_hem + 0.4) + 0.2 * ramp(t, T0, T0 + 0.5)
    s *= 1 - 0.45 * ramp(t, TEND, TEND + 0.4)
    s += 0.45 * ramp(t, TOTAL - 0.5, TOTAL)       # döngü: son kare ilk kareye bağlansın
    return min(1.0, s)


def tongue_tip(t):
    s = strain(t)
    wob = 6 * math.sin(t * 2 * math.pi * 2.6) + 3 * math.sin(t * 2 * math.pi * 5.3)
    shake = 4 * math.sin(t * 2 * math.pi * 7.0) * ramp(t, T0, T0 + 0.3) * (1 - ramp(t, TEND, TEND + 0.3))
    top = NOSE_BOT + 140 - 120 * s - wob             # dil ucunun üst noktası (en iyi ~burun altı +14)
    top = max(NOSE_BOT + 10, top)
    return CX + shake, top


def draw_dyn(t):
    im = Image.new("RGBA", (PX, PX), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    s = strain(t)
    # kaşlar (efor)
    for sx in (-1, 1):
        x0, x1 = CX + sx * 75, CX + sx * 205
        y0, y1 = CY - 195 + 10 * s, CY - 215 - 10 * s
        d.line([P(x0, y0), P(x1, y1)], fill=(150, 80, 20, 255), width=round(L_(16)))
        for (xx, yy_) in ((x0, y0), (x1, y1)):
            d.ellipse([*P(xx - 8, yy_ - 8), *P(xx + 8, yy_ + 8)], fill=(150, 80, 20, 255))
    # gözler: burna bakan şaşı bakış
    blink = 1.0
    for bt in (1.3, 7.2):
        if bt <= t < bt + 0.16:
            blink = 0.15
    for sx in (-1, 1):
        ex, ey = CX + sx * 135, CY - 105
        d.ellipse([*P(ex - 62, ey - 70 * blink), *P(ex + 62, ey + 70 * blink)], fill=(255, 255, 255, 255),
                  outline=(150, 80, 20, 255), width=round(L_(6)))
        if blink > 0.5:
            px = ex - sx * (8 + 20 * s)
            py = ey + 10 + 26 * s
            d.ellipse([*P(px - 30, py - 30), *P(px + 30, py + 30)], fill=(60, 40, 30, 255))
            d.ellipse([*P(px - 14, py - 20), *P(px - 2, py - 8)], fill=(255, 255, 255, 255))
    # ağız
    mh = 60 + 30 * s
    my = CY + 255
    d.ellipse([*P(CX - 120, my - mh / 2), *P(CX + 120, my + mh / 2)], fill=(120, 30, 40, 255))
    # dil: ağızdan yukarı, üst dudağın üstünden burna doğru
    tx, top = tongue_tip(t)
    rt = 64
    tipc = top + rt
    base_y = my + 10
    n = 28
    left, right = [], []
    for k in range(n + 1):
        f = k / n
        y = base_y + (tipc - base_y) * f
        x = CX + (tx - CX) * f * f
        w = (150 * (1 - f) + 2 * rt * f) / 2
        left.append(P(x - w, y))
        right.append(P(x + w, y))
    d.polygon(left + right[::-1], fill=PINK + (255,))
    d.ellipse([*P(tx - rt, tipc - rt), *P(tx + rt, tipc + rt)], fill=PINK + (255,))
    # orta çizgi ve parlama
    d.line([P(CX, base_y - 6), P((CX + tx) / 2, (base_y + tipc) / 2 + 10)], fill=(215, 72, 105, 255), width=round(L_(6)))
    d.ellipse([*P(tx - 40, tipc - 44), *P(tx - 12, tipc - 20)], fill=(255, 180, 195, 255))
    # dudak kenarları (dilin altında kalan ağzın alt dudağı)
    d.arc([*P(CX - 120, my - mh / 2), *P(CX + 120, my + mh / 2)], 20, 160, fill=(200, 90, 40, 255), width=round(L_(8)))
    return im


def face_layer(t):
    im = BASE.copy()
    im.alpha_composite(draw_dyn(t))
    return im.resize((round(u(FS)), round(u(FS))), Image.LANCZOS)


def timer(L, t):
    d = ImageDraw.Draw(L)
    cx, cy, r = 540, 1440, 125
    dur = TEND - T0
    q = clamp((t - T0) / dur)
    left = dur * (1 - q)
    n = max(0, int(math.ceil(left - 1e-6)))
    col = RED if left <= 1.0 else GOLD
    bx = [u(cx - r), u(cy - r), u(cx + r), u(cy + r)]
    d.ellipse(bx, fill=NAVY + (235,), outline=(255, 255, 255, 140), width=round(u(12)))
    if q < 1:
        d.arc(bx, -90 + 360 * q, 270, fill=col + (255,), width=round(u(14)))
    sc = 1 + 0.25 * max(0.0, 1 - ((t - T0) % 1.0) / 0.25)
    txt(L, (cx, cy), str(n) if n > 0 else "!", round(130 * sc), WHITE, 1.0, k="black", stroke=0)


def person(d, cx, cy, sc, col):
    r = 26 * sc
    d.ellipse([u(cx - r), u(cy - 62 * sc - r), u(cx + r), u(cy - 62 * sc + r)], fill=col + (255,))
    d.rounded_rectangle([u(cx - 34 * sc), u(cy - 28 * sc), u(cx + 34 * sc), u(cy + 50 * sc)], radius=u(26 * sc), fill=col + (255,))


def people_row(L, t):
    d = ImageDraw.Draw(L)
    for k in range(10):
        q = pop(t, t_on + 0.04 * k, 0.3)
        if q <= 0:
            continue
        x = 540 + (k - 4.5) * 92
        if k == 6:
            hi = pop(t, T("biri") - 0.05, 0.35)
            sc = q * (1 + 0.35 * hi)
            col = tuple(int(a * (1 - hi) + b * hi) for a, b in zip((120, 110, 140), GOLD))
            person(d, x, 1430 - 18 * hi, sc, col)
        else:
            person(d, x, 1430, q, (120, 110, 140))


class Vid(Video):
    def frame(self, t):
        i = min(len(OPN) - 1, int(t * FPS))
        im = BG.copy()
        bob = 6 * math.sin(t * 2 * math.pi * 0.8)
        F = face_layer(t)
        im.alpha_composite(F, (round(u(FX0)), round(u(FY0 + bob))))
        L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        # ter damlası (sayaç sırasında)
        if T0 <= t < TEND + 0.3:
            for j, (sx, ph) in enumerate(((1, 0.0), (-1, 0.5))):
                f = ((t - T0) * 0.9 + ph) % 1.0
                a = math.sin(math.pi * f)
                ico = icon("droplet", round(u(70)))
                comp(L, set_alpha(ico, a), u(CX + sx * 330) - ico.width / 2, u(CY - 220 + 90 * f + bob))
        # başlık (ilk kare = kapak)
        q = 1.0 if t < 0.05 else pop(t, 0.0, 0.3)
        txt(L, (540, 175), "DİLİNİ BURNUNA", round(74 * max(q, 0.8)), WHITE, 1.0, stroke=9, k="black")
        put_word(L, "DEĞDİREBİLİR MİSİN?", (230, 40, 80), 540, 285, max(8, round(86 * max(q, 0.8))), alpha=1.0, glow=0.35)
        if t < T0:
            if t >= t_hem - 0.05:
                k = pop(t, t_hem - 0.05, 0.35)
                chip(L, 540, 1440, "HEMEN DENE!", bg=GOLD, fg=INKC, size=82, k="black", scale=k)
        elif t < t_on - 0.05:
            timer(L, t)
        elif t < t_yap - 0.05:
            people_row(L, t)
            k = pop(t, t_on, 0.35)
            put_word(L, "10 KİŞİDEN SADECE 1'İ!", WHITE, 540, 1560, max(8, round(68 * k)), alpha=1.0, glow=0.4)
        else:
            k = pop(t, t_yap - 0.05, 0.35)
            pulse = 1 + 0.04 * math.sin((t - t_yap) * 8)
            chip(L, 540, 1440, "Yaptıysan yorumlara", bg=WHITE, fg=INKC, size=58, k="black", scale=k)
            kk = pop(t, T("yaptım") - 0.05, 0.35)
            chip(L, 540, 1570, "YAPTIM yaz!", bg=GOLD, fg=INKC, size=78, icon_name="speech_balloon", k="black", scale=kk * pulse)
        im.alpha_composite(L)
        brand(im, 540, 62, size=34)
        ROZ.draw(im, t, float(OPN[i]))
        return im.convert("RGB")


ROZ = Rozet(cx=150, cy=1745)
OPN, RND = konusma(VOICE, FPS)
VID = Vid([{"start": 0, "end": TOTAL, "draw": lambda *a: None}], [], "", TOTAL, bg=None)


def make_audio():
    ev = [(0.0, "whoosh"), (t_hem - 0.05, "pop")]
    ev += [(T0 + s, "tink") for s in range(3)]
    ev += [(t_on - 0.05, "whoosh"), (T("biri") - 0.05, "pop"), (t_yap - 0.05, "pop"), (T("yaptım") - 0.05, "pop")]
    at.sfx(str(WORK / "sfx.wav"), TOTAL, ev)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-stream_loop", "3", "-i", str(WORK / "muzik.wav"), "-af",
                    f"atrim=0:{TOTAL:.3f},afade=t=in:d=0.2,afade=t=out:st={TOTAL - 0.4:.3f}:d=0.4",
                    "-ar", "44100", "-ac", "1", str(WORK / "music.wav")], check=True)
    at.final_mix(str(VOICE), str(WORK / "music.wav"), str(WORK / "sfx.wav"), str(WORK / "mix.m4a"))


if __name__ == "__main__":
    mode = sys.argv[2] if len(sys.argv) > 2 else "render"
    print("TOTAL", TOTAL, flush=True)
    if mode == "frames":
        (WORK / "test").mkdir(exist_ok=True)
        for tt in [float(x) for x in sys.argv[3].split(",")]:
            VID.frame(tt).save(WORK / "test" / f"fr_{tt:05.2f}.jpg", quality=90)
    elif mode == "ses":
        make_audio()
    else:
        make_audio()
        VID.render(str(WORK / "mix.m4a"), str(WORK / "video.mp4"))
        print("render bitti", TOTAL, flush=True)
