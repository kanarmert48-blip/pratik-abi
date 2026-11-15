"""56. video (2K Shorts, ~19 sn): Lastik kalem illüzyonu nasıl yapılır (kendi animasyonumuz).
El: Fluent 3D emoji, kalem: kodla çizilir ve gerçekten bükülerek titrer.
Kullanım: python3 video56_kalem.py <WORK> [frames t1,t2,... | ses | render]"""
import os
os.environ.setdefault("PA_SCALE", str(4 / 3))
import json, math, random, subprocess, sys
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
TOTAL = round(at.duration(str(VOICE)), 3)
ASSETS = Path(__file__).resolve().parent.parent / "assets"

GOLD = (255, 196, 40)
INKC = (24, 30, 60)
NAVY = (30, 50, 110)


def ramp(t, a, b):
    return eio(clamp((t - a) / max(1e-6, b - a)))


def T(key, nth=0):
    k = trl(clean(key)).strip('"!?;,.…')
    return [w for w in words if trl(clean(w["w"])).strip('"!?;,.…') == k][nth]["s"]


t_k2 = T("Kalemi", 1)          # adım 1
t_sik = T("Sıkma")             # adım 2
t_sim = T("Şimdi")             # adım 3
t_iste = T("İşte")             # etki
t_asl = T("Aslında")           # açıklama
t_hadi = T("Hadi")             # kapanış

# ---- arka plan: açık mavi degrade + yumuşak daireler ----
_bg = np.zeros((H, W, 3), np.float32)
yy = np.linspace(0, 1, H)[:, None]
_bg[:] = (np.array([178, 222, 255]) * (1 - yy) + np.array([120, 182, 240]) * yy)[:, None, :][:, 0, :][:, None, :]
BG = Image.fromarray(_bg.clip(0, 255).astype(np.uint8)).convert("RGBA")
_c = Image.new("RGBA", (W, H), (0, 0, 0, 0))
_cd = ImageDraw.Draw(_c)
for x, y, r in [(900, 300, 260), (120, 1500, 300), (980, 1700, 200)]:
    _cd.ellipse([u(x - r), u(y - r), u(x + r), u(y + r)], fill=(255, 255, 255, 60))
BG.alpha_composite(_c.filter(ImageFilter.GaussianBlur(u(60))))

HAND = Image.open(ASSETS / "pinching_hand_3d.png").convert("RGBA")
HS = 470                                   # el boyu (birim)
GAPX, GAPY = 203 / 256, 116 / 256          # başparmak-işaret arası boşluk
L_P = 900                                  # kalem boyu
G = 0.33                                   # tutma noktası (silgi ucundan oran)
PW_ = 54                                   # kalem kalınlığı
HAND_IMG = HAND.resize((round(u(HS)), round(u(HS))), Image.LANCZOS)
TIP = HAND.crop((150, 30, 240, 104)).resize((round(u(HS * 90 / 256)), round(u(HS * 74 / 256))), Image.LANCZOS)


def pencil_pts(gx, gy, bend, n=60):
    """Kalemin orta çizgisi: s=0 silgi, s=1 uç. bend: tutma noktasına göre yay genliği (birim)."""
    pts = []
    for i in range(n + 1):
        s = i / n
        x = gx + (s - G) * L_P
        d = (s - G) / (1 - G) if s >= G else (G - s) / G * 0.45
        y = gy + bend * d * d * (1 if s >= G else -1)
        pts.append((x, y))
    return pts


def draw_pencil(L, pts, alpha=255):
    d = ImageDraw.Draw(L)
    n = len(pts) - 1

    def seg(s0, s1, col, w0, w1=None):
        w1 = w0 if w1 is None else w1
        i0, i1 = int(s0 * n), max(int(s0 * n) + 1, int(s1 * n))
        left, right = [], []
        for i in range(i0, i1 + 1):
            x, y = pts[min(i, n)]
            xa, ya = pts[max(0, min(i, n) - 1)]
            xb, yb = pts[min(n, min(i, n) + 1)]
            tx, ty = xb - xa, yb - ya
            ln = math.hypot(tx, ty) or 1
            nx, ny = -ty / ln, tx / ln
            f = (i - i0) / max(1, i1 - i0)
            w = (w0 * (1 - f) + w1 * f) / 2
            left.append((u(x + nx * w), u(y + ny * w)))
            right.append((u(x - nx * w), u(y - ny * w)))
        d.polygon(left + right[::-1], fill=col + (alpha,))

    seg(0.0, 0.07, (255, 130, 150), PW_)            # silgi
    seg(0.07, 0.12, (200, 205, 215), PW_ + 4)       # metal halka
    seg(0.12, 0.86, (255, 196, 40), PW_)            # gövde
    seg(0.12, 0.86, (255, 222, 110), PW_ * 0.35)    # parlak şerit
    seg(0.86, 0.97, (240, 205, 160), PW_, 12)       # ahşap koni
    seg(0.97, 1.0, (60, 60, 70), 12, 2)             # grafit uç


def hand_y(t):
    if t < t_sim:
        return 0.0
    k = ramp(t, t_sim, t_sim + 0.4) * (1 - 0.6 * ramp(t, t_asl, t_asl + 0.5))
    return 32 * k * math.sin(t * 2 * math.pi * 3.2)


def bend_amt(t):
    """Lastik etkisi: el titredikçe kalem yay gibi bükülür (hareketin gecikmesi)."""
    if t < t_sim:
        if t < t_k2:                         # açılış: tanıtım titremesi
            return 70 * math.sin(t * 2 * math.pi * 3.0) * ramp(t, 0.1, 0.4)
        if t_sik <= t < t_sim:               # gevşek tut: hafif sallanma
            return 14 * math.sin((t - t_sik) * 2 * math.pi * 1.2)
        return 0.0
    k = ramp(t, t_sim, t_sim + 0.4) * (1 + 0.6 * ramp(t, t_iste - 0.1, t_iste + 0.3)) * (1 - 0.55 * ramp(t, t_asl, t_asl + 0.5))
    return 105 * k * math.sin(t * 2 * math.pi * 3.2 - 1.2)


def scene(L, t):
    gx, gy = 420, 900
    hy = hand_y(t)
    gy2 = gy + hy
    hx0 = gx - GAPX * HS
    hy0 = gy2 - GAPY * HS
    comp(L, HAND_IMG, u(hx0), u(hy0))
    b = bend_amt(t)
    shaking = t >= t_sim and b != 0
    if shaking:                                   # hayalet izler (gözün gördüğü bulanıklık)
        for k, dt in enumerate([0.05, 0.1, 0.15]):
            draw_pencil(L, pencil_pts(gx, gy + hand_y(t - dt), bend_amt(t - dt)), alpha=70 - k * 18)
    draw_pencil(L, pencil_pts(gx, gy2, b))
    comp(L, TIP, u(hx0 + HS * 150 / 256), u(hy0 + HS * 30 / 256))   # işaret parmağı ucu kalemin üstünde
    return gx, gy2


def step_chip(L, t, t0, n, s):
    q = pop(t, t0 - 0.05, 0.35)
    chip(L, 540, 1360, f"{n} · {s}", bg=WHITE, fg=INKC, size=58, k="black", scale=q)


class Vid(Video):
    def frame(self, t):
        i = min(len(OPN) - 1, int(t * FPS))
        im = BG.copy()
        L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        gx, gy = scene(L, t)
        d = ImageDraw.Draw(L)
        # başlık
        q = pop(t, 0.0, 0.45)
        txt(L, (540, 170), "LASTİK KALEM", round(64 * q), WHITE, 1.0, stroke=8, k="black")
        put_word(L, "NASIL YAPILIR?", (235, 60, 90), 540, 265, max(8, round(92 * q)), alpha=1.0, glow=0.35)
        if t_k2 <= t < t_sik:
            # tutma noktası vurgusu + 1/3 işareti
            k = pop(t, t_k2 - 0.05, 0.4)
            r = 58 * k * (1 + 0.08 * math.sin(t * 8))
            d.ellipse([u(gx - r), u(gy - r), u(gx + r), u(gy + r)], outline=GOLD + (255,), width=round(u(8)))
            x0 = gx - G * L_P
            d.line([u(x0), u(gy - 110), u(gx), u(gy - 110)], fill=NAVY + (230,), width=round(u(6)))
            for xx in (x0, gx):
                d.line([u(xx), u(gy - 128), u(xx), u(gy - 92)], fill=NAVY + (230,), width=round(u(6)))
            txt(L, ((x0 + gx) / 2, gy - 160), "1/3", round(56 * k), NAVY, 1.0, k="black", stroke=0)
            step_chip(L, t, t_k2, 1, "Ucuna yakın tut")
        elif t_sik <= t < t_sim:
            step_chip(L, t, t_sik, 2, "Sıkma, gevşek tut")
        elif t_sim <= t < t_iste:
            step_chip(L, t, t_sim, 3, "Hızlıca salla")
            for sgn in (-1, 1):                    # yukarı/aşağı oklar
                k = pop(t, t_sim, 0.35)
                ay = gy + sgn * (190 + 12 * math.sin(t * 10))
                ico = icon("up_arrow" if sgn < 0 else "down_arrow", round(u(110 * k)))
                comp(L, ico, u(gx - 230) - ico.width / 2, u(ay) - ico.height / 2)
        elif t_iste <= t < t_asl:
            k = pop(t, t_iste - 0.05, 0.4)
            put_word(L, "LASTİK GİBİ!", (255, 90, 120), 540, 1380, max(8, round(110 * k)), alpha=1.0, glow=0.5)
        elif t_asl <= t < t_hadi:
            k = pop(t, t_asl - 0.05, 0.4)
            chip(L, 540, 1360, "Aslında bükülmüyor!", bg=WHITE, fg=INKC, size=56, k="black", scale=k)
            if t >= T("gözün") - 0.05:
                kk = pop(t, T("gözün") - 0.05, 0.35)
                ico = icon("eyes", round(u(130 * kk)))
                comp(L, ico, u(540) - ico.width / 2, u(1470) - ico.height / 2)
                txt(L, (600, 1575), "Göz bu hızı takip edemiyor", round(52 * kk), WHITE, 1.0, stroke=7, k="black")
        else:
            k = pop(t, t_hadi - 0.05, 0.4)
            pulse = 1 + 0.05 * math.sin((t - t_hadi) * 8)
            chip(L, 540, 1380, "HADİ SEN DE DENE!", bg=GOLD, fg=INKC, size=74, icon_name="pencil", k="black", scale=k * pulse)
        im.alpha_composite(L)
        brand(im, 540, 62, size=34)
        ROZ.draw(im, t, float(OPN[i]))
        return im.convert("RGB")


ROZ = Rozet(cx=150, cy=1745)
OPN, RND = konusma(VOICE, FPS)
VID = Vid([{"start": 0, "end": TOTAL, "draw": lambda *a: None}], words, "", TOTAL, bg=None)


def make_audio():
    ev = [(0.0, "whoosh"), (t_k2 - 0.05, "pop"), (t_sik - 0.05, "pop"), (t_sim - 0.05, "pop"),
          (t_iste - 0.05, "whoosh"), (t_asl - 0.05, "pop"), (T("gözün") - 0.05, "tink"), (t_hadi - 0.05, "pop")]
    at.sfx(str(WORK / "sfx.wav"), TOTAL, ev)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-stream_loop", "3", "-i", str(WORK / "muzik.wav"), "-af",
                    f"atrim=0:{TOTAL:.3f},afade=t=in:d=0.3,afade=t=out:st={TOTAL - 0.6:.3f}:d=0.6",
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
