"""54. video (2K Shorts, ~22 sn): Bu hayvanın 3 kalbi var, kanı mavi. Bulanık foto her ipucunda netleşir, cevap ahtapot.
Kullanım: python3 video54_ahtapot.py <WORK> [frames t1,t2,... | ses | render]
WORK/voice_cut.wav + words.json + muzik.wav gerekir."""
import os
os.environ.setdefault("PA_SCALE", str(4 / 3))
import json, math, random, subprocess, sys
from pathlib import Path

import numpy as np
from PIL import ImageEnhance

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
IMG = Path(__file__).resolve().parent / "v54img"


def ramp(t, a, b):
    return eio(clamp((t - a) / max(1e-6, b - a)))


def T(key, nth=0):
    k = trl(clean(key)).strip('"!?;,.…')
    return [w for w in words if trl(clean(w["w"])).strip('"!?;,.…') == k][nth]["s"]


GOLD = (255, 204, 70)
CYAN = (60, 230, 255)
BLUE = (70, 140, 255)
INKC = (20, 18, 40)
RED = (255, 80, 80)
GREEN = (80, 220, 120)

t_ip = [T("İpucu", 0), T("İpucu", 1), T("İpucu", 2)]
t_cev = T("Cevap")
t_aht = T("ahtapot")
t_kan = T("Kanı", 1)
t_dem, t_bak = T("demir"), T("bakır")
t_ilk = T("İlk")
t_yor = T("Yorumlara")
S_END = T("yaz") + 0.55

# ---- fotoğraflar ----
CX0, CY0, CW, CH = 90, 300, 900, 800


def fit_cover(im, w, h):
    r = max(w / im.width, h / im.height)
    im = im.resize((round(im.width * r), round(im.height * r)), Image.LANCZOS)
    x, y = (im.width - w) // 2, (im.height - h) // 2
    return im.crop((x, y, x + w, y + h))


def rounded(im, rad):
    m = Image.new("L", im.size, 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, im.width - 1, im.height - 1], radius=rad, fill=255)
    im = im.convert("RGBA")
    im.putalpha(m)
    return im


GZ = fit_cover(Image.open(IMG / "gizem.jpg").convert("RGB"), round(u(CW)), round(u(CH)))
BLUR = {}
for lv, r in enumerate([70, 46, 28, 14]):
    b = GZ.filter(ImageFilter.GaussianBlur(u(r) / 1.0))
    b = ImageEnhance.Brightness(b).enhance(0.55 + 0.1 * lv)
    BLUR[lv] = rounded(b, round(u(36)))
SHARP = rounded(GZ, round(u(36)))
KAN_BG = fit_cover(Image.open(IMG / "ahtapot2.jpg").convert("RGB"), W, H)
KAN_BG = ImageEnhance.Brightness(KAN_BG.filter(ImageFilter.GaussianBlur(u(3)))).enhance(0.45).convert("RGBA")

_bg = np.zeros((H, W, 3), np.float32)
yy = np.linspace(0, 1, H)[:, None]
_bg[:] = (np.array([10, 40, 90]) * (1 - yy) + np.array([4, 10, 30]) * yy)[:, None, :][:, 0, :][:, None, :]
BG = Image.fromarray(_bg.clip(0, 255).astype(np.uint8))
random.seed(54)
BUB = [(random.uniform(0, 1080), random.uniform(0, 1920), random.uniform(6, 18), random.uniform(30, 80)) for _ in range(28)]


def background(t):
    im = BG.copy().convert("RGBA")
    d = ImageDraw.Draw(im)
    for x, y, r, sp in BUB:                       # yükselen kabarcıklar
        yy2 = (y - t * sp) % 1980 - 30
        xx = x + 10 * math.sin(t * 1.3 + y)
        d.ellipse([u(xx - r), u(yy2 - r), u(xx + r), u(yy2 + r)], outline=(160, 220, 255, 70), width=round(u(2)))
    return im


def level(t):
    if t < t_ip[0]:
        return 0
    if t < t_ip[1]:
        return 1
    if t < t_ip[2]:
        return 2
    return 3


def photo(im, L, t):
    lv = level(t)
    a = ramp(t, t_aht - 0.05, t_aht + 0.35)
    shake = 0
    if t_cev <= t < t_aht:                        # davul: hafif titreme
        shake = u(4) * math.sin(t * 60)
    x, y = round(u(CX0) + shake), round(u(CY0))
    base = BLUR[lv]
    # seviye geçişlerinde yumuşak geçiş
    for k in range(3):
        if t_ip[k] <= t < t_ip[k] + 0.4 and k + 1 == lv:
            q = ramp(t, t_ip[k], t_ip[k] + 0.4)
            base = Image.blend(BLUR[lv - 1], BLUR[lv], q)
    im.alpha_composite(base, (x, y))
    if a > 0:
        im.alpha_composite(set_alpha(SHARP, a), (x, y))
    d = ImageDraw.Draw(L)
    d.rounded_rectangle([u(CX0 - 6), u(CY0 - 6), u(CX0 + CW + 6), u(CY0 + CH + 6)], radius=round(u(40)),
                        outline=(GOLD if a > 0.5 else WHITE) + (255,), width=round(u(7)))
    if a < 1:
        s = (1 + 0.06 * math.sin(t * 5)) * (1 - a)
        if s > 0.05:
            txt(L, (540, CY0 + CH / 2), "?", round(330 * s), WHITE, 1 - a, stroke=12)
    if t >= t_aht:
        k = pop(t, t_aht, 0.4)
        put_word(L, "AHTAPOT!", GOLD, 540, CY0 + CH - 70, max(8, round(130 * k)), alpha=1.0, glow=0.6)


CLUES = [("8 KOLU VAR", None, "8"), ("MÜREKKEP PÜSKÜRTÜR", "droplet", None), ("RENK DEĞİŞTİRİR", "artist_palette", None)]


def clue_cards(L, t):
    for k, (s, ic, num) in enumerate(CLUES):
        if t < t_ip[k] - 0.05:
            continue
        q = pop(t, t_ip[k] - 0.05, 0.35)
        y = 1215 + k * 150
        dim = 1.0 if t < t_aht else 0.0
        if dim <= 0:
            continue
        card(L, 90, y - 62, 900, 124, r=34, fill=(255, 255, 255, 235), alpha=q)
        d = ImageDraw.Draw(L)
        d.ellipse([u(118), u(y - 44), u(206), u(y + 44)], fill=BLUE + (255,))
        txt(L, (162, y), str(k + 1), round(54 * q), WHITE, 1.0, k="black", stroke=0)
        if ic:
            ico = icon(ic, round(u(84 * q)))
            comp(L, ico, u(930) - ico.width / 2, u(y) - ico.height / 2)
        else:
            txt(L, (930, y), num, round(80 * q), BLUE, 1.0, k="black", stroke=0)
        txt(L, (556, y), s, round((54 if len(s) < 15 else 44) * q), INKC, 1.0, k="black", stroke=0)


def hook(L, t):
    # üst başlık: 3 KALP + MAVİ KAN
    q1 = pop(t, T("üç") - 0.05, 0.35)
    q2 = pop(t, T("kanı") - 0.05, 0.35)
    if t < t_aht:
        txt(L, (540, 150), "BU HAYVANIN", round(50 * q1), WHITE, 1.0, stroke=6)
        if q1 > 0:
            put_word(L, "3 KALBİ VAR", (255, 110, 140), 300, 240, max(8, round(60 * q1)), alpha=1.0, glow=0.4)
        if q2 > 0:
            put_word(L, "KANI MAVİ!", CYAN, 790, 240, max(8, round(60 * q2)), alpha=1.0, glow=0.5)
    if T("Sence") - 0.05 <= t < t_ip[0]:
        chip(L, 540, 1300, "SENCE HANGİSİ?", bg=GOLD, fg=INKC, size=60, icon_name="thinking_face", k="black",
             scale=pop(t, T("Sence") - 0.05, 0.35))
    if t_ip[2] + 1.6 <= t < t_cev:
        chip(L, 540, 1720, "Düşün...", bg=INKC, fg=WHITE, size=48, icon_name="thinking_face", k="black",
             scale=pop(t, t_ip[2] + 1.6, 0.3))
    if t_cev - 0.05 <= t < t_aht:
        chip(L, 540, 1720, "CEVAP...", bg=GOLD, fg=INKC, size=56, k="black", scale=pop(t, t_cev - 0.05, 0.3))


def why(im, L, t):
    a = ramp(t, t_kan - 0.15, t_kan + 0.25)
    im.alpha_composite(set_alpha(KAN_BG, a))
    q = pop(t, t_kan - 0.1, 0.35)
    txt(L, (540, 330), "KANI NEDEN", round(64 * q), WHITE, 1.0, stroke=7)
    put_word(L, "MAVİ?", CYAN, 540, 450, max(8, round(140 * q)), alpha=1.0, glow=0.6)
    for k, (tt, s, ic, col) in enumerate([(t_dem, "DEMİR YOK", "cross_mark", RED), (t_bak, "BAKIR VAR", "check_mark_button", GREEN)]):
        if t >= tt - 0.08:
            qq = pop(t, tt - 0.08, 0.35)
            chip(L, 540, 760 + k * 190, s, bg=WHITE, fg=INKC, size=74, icon_name=ic, k="black", scale=qq)
    if t >= T("var", 2) + 0.2:
        qq = pop(t, T("var", 2) + 0.2, 0.35)
        txt(L, (540, 1200), "Bakır kanı maviye boyar", round(64 * qq), WHITE, 1.0, stroke=6)
        ico = icon("blue_heart", round(u(150 * qq)))
        comp(L, ico, u(540) - ico.width / 2, u(1360) - ico.height / 2)


def ask(im, L, t):
    im.alpha_composite(set_alpha(SHARP, 1.0), (round(u(CX0)), round(u(CY0))))
    d = ImageDraw.Draw(L)
    d.rounded_rectangle([u(CX0 - 6), u(CY0 - 6), u(CX0 + CW + 6), u(CY0 + CH + 6)], radius=round(u(40)),
                        outline=GOLD + (255,), width=round(u(7)))
    q = pop(t, t_ilk - 0.1, 0.35)
    txt(L, (540, 140), "İLK İPUCUNDA", round(58 * q), WHITE, 1.0, stroke=7)
    put_word(L, "BİLDİN Mİ?", GOLD, 540, 226, max(8, round(84 * q)), alpha=1.0, glow=0.45)
    chip(L, 600, 1250, "Yorumlara yaz!", bg=GOLD, fg=INKC, size=62, icon_name="speech_balloon", k="black",
         scale=pop(t, t_yor - 0.1, 0.35))


class Vid(Video):
    def frame(self, t):
        i = min(len(OPN) - 1, int(t * FPS))
        im = background(t)
        L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        if t < t_kan - 0.15:
            photo(im, L, t)
            hook(L, t)
            clue_cards(L, t)
        elif t < t_ilk - 0.1:
            why(im, L, t)
        elif t < S_END:
            ask(im, L, t)
        else:
            b = ramp(t, S_END, S_END + 0.25)
            txt(L, (540, 760), "Daha fazlası için", 64, WHITE, b, stroke=6)
            pulse = 1 + 0.045 * math.sin((t - S_END) * 8) * ramp(t, S_END + 0.4, S_END + 0.7)
            chip(L, 540, 900, "TAKİP ET", bg=INKC, fg=WHITE, size=90, icon_name="bell", k="black",
                 scale=pop(t, S_END, 0.4) * pulse)
        im.alpha_composite(L)
        brand(im, 540, 62, size=34)
        ROZ.draw(im, t, float(OPN[i]))
        return im.convert("RGB")


ROZ = Rozet(cx=150, cy=1745)
OPN, RND = konusma(VOICE, FPS)
VID = Vid([{"start": 0, "end": TOTAL, "draw": lambda *a: None}], words, "", TOTAL, bg=None)


def make_audio():
    ev = [(0.0, "pop"), (T("üç") - 0.05, "pop"), (T("kanı") - 0.05, "pop")]
    ev += [(t - 0.05, "whoosh") for t in t_ip]
    ev += [(t_aht - 0.05, "ding"), (t_kan - 0.15, "whoosh"), (t_dem - 0.08, "pop"), (t_bak - 0.08, "ding"),
           (t_ilk - 0.1, "whoosh"), (S_END, "pop")]
    at.sfx(str(WORK / "sfx.wav"), TOTAL, ev)
    SR = 44100
    fx = np.frombuffer(subprocess.run(["ffmpeg", "-v", "error", "-i", str(WORK / "sfx.wav"), "-ac", "1", "-ar", str(SR),
                                       "-f", "f32le", "-"], capture_output=True).stdout, np.float32).copy()
    fx = np.pad(fx, (0, max(0, int(TOTAL * SR) + SR - len(fx))))
    # davul: cevap öncesi hızlanan vuruşlar
    rng = np.random.default_rng(54)
    m = int(0.06 * SR)
    tt = np.arange(m) / SR
    hit = (np.sin(2 * np.pi * 110 * tt) * 0.8 + rng.standard_normal(m) * 0.25) * np.exp(-tt * 45)
    t = t_cev
    gap = 0.16
    while t < t_aht - 0.08:
        a = int(t * SR)
        fx[a:a + m] += (hit * 0.22).astype(np.float32)
        t += gap
        gap = max(0.06, gap * 0.9)
    at._write(str(WORK / "sfx.wav"), fx[:int(TOTAL * SR)])
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-stream_loop", "3", "-i", str(WORK / "muzik.wav"), "-af",
                    f"atrim=0:{TOTAL:.3f},afade=t=in:d=0.3,afade=t=out:st={TOTAL - 0.6:.3f}:d=0.6",
                    "-ar", "44100", "-ac", "1", str(WORK / "music.wav")], check=True)
    at.final_mix(str(VOICE), str(WORK / "music.wav"), str(WORK / "sfx.wav"), str(WORK / "mix.m4a"))


if __name__ == "__main__":
    mode = sys.argv[2] if len(sys.argv) > 2 else "render"
    print("TOTAL", TOTAL, "S_END", S_END, flush=True)
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
