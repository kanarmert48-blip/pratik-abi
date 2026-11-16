"""58b. video (2K Shorts, ~11 sn): Dilini burnuna değdirebilir misin? Gerçekçi Gemini fotoğrafları + Daniel sesi.
İki kare (kısa dil / uzun dil) aynı kadrajda; aralarında geçişle "zorlanma" hissi. Cevap yok.
Kullanım: python3 video58b_dil.py <WORK> [frames t1,t2,... | ses | render]"""
import os
os.environ.setdefault("PA_SCALE", str(4 / 3))
import json, math, subprocess, sys
from pathlib import Path

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


def T(key, nth=0):
    k = trl(clean(key)).strip('"!?;,.…')
    return [w for w in words if trl(clean(w["w"])).strip('"!?;,.…') == k][nth]["s"]


t_hem = T("Hemen")
t_on = MK["tC"]
t_biri = T("biri")
t_yapb = T("Yapabildin")
t_yor = T("Yorumlara")
T0, TEND = MK["t0"], MK["tend"]

# ---- fotoğraflar: 2K'ya cover-crop, %8 pay bırak (yakınlaşma için) ----
PAD = 1.08


def load(name):
    im = Image.open(WORK / "img" / name).convert("RGB")
    s = max(W * PAD / im.width, H * PAD / im.height)
    im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    return im.filter(ImageFilter.UnsharpMask(radius=2, percent=60, threshold=2))


UZUN = load("uzun.jpg")
KISA = load("kisa.jpg")
import numpy as np
A_U = np.asarray(UZUN, np.float32)
A_K = np.asarray(KISA, np.float32)

# alt kısım okunurluk için hafif koyu degrade
_g = np.linspace(0, 1, H)[:, None]
SHADE = Image.fromarray(np.dstack([np.zeros((H, W, 3)), (np.clip((_g - 0.62) / 0.38, 0, 1) * 150).repeat(W, 1)]).astype(np.uint8), "RGBA")
_top = np.clip((0.16 - _g) / 0.16, 0, 1) * 90
SHADE_T = Image.fromarray(np.dstack([np.zeros((H, W, 3)), _top.repeat(W, 1)]).astype(np.uint8), "RGBA")


def mix_amt(t):
    """1 = uzun dil, 0 = kısa dil."""
    if t < 0.6:
        return 1.0                                   # ilk kare = kapak (uzun dil)
    if t < T0:
        # kısa dile in, "Hemen dene" ile tekrar uzat
        a = 1 - eio(clamp((t - 0.6) / 0.5))
        b = eio(clamp((t - (t_hem + 0.1)) / 0.45))
        return max(a, b) if t >= t_hem else a
    if t < TEND + 0.2:
        # zorlanma: uzun/kısa arasında git-gel, giderek hızlanır
        q = (t - T0) / (TEND - T0)
        f = 1.4 + 1.2 * q
        return 0.5 + 0.5 * math.cos(2 * math.pi * f * (t - T0))
    if t < TOTAL - 0.6:
        return 1 - eio(clamp((t - (TEND + 0.2)) / 0.35))
    return eio(clamp((t - (TOTAL - 0.6)) / 0.5))    # döngü: sona doğru yine uzun dil


def photo(t):
    m = mix_amt(t)
    arr = A_K * (1 - m) + A_U * m
    im = Image.fromarray(arr.clip(0, 255).astype(np.uint8))
    # yavaş yakınlaşma + sayaçta küçük sarsıntı
    z = 1.0 + 0.05 * (t / TOTAL)
    shake = 0.0
    if T0 <= t < TEND:
        shake = 5 * math.sin(t * 2 * math.pi * 6.5)
    cw, ch = UZUN.width / PAD / z, UZUN.height / PAD / z
    cx = UZUN.width / 2 + u(shake)
    cy = UZUN.height * 0.47
    box = (cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2)
    return im.resize((W, H), Image.BILINEAR, box=box).convert("RGBA")


def timer(L, t):
    d = ImageDraw.Draw(L)
    cx, cy, r = 540, 1500, 118
    dur = TEND - T0
    q = clamp((t - T0) / dur)
    left = dur * (1 - q)
    n = max(0, int(math.ceil(left - 1e-6)))
    col = RED if left <= 1.0 else GOLD
    bx = [u(cx - r), u(cy - r), u(cx + r), u(cy + r)]
    d.ellipse(bx, fill=NAVY + (235,), outline=(255, 255, 255, 160), width=round(u(12)))
    if q < 1:
        d.arc(bx, -90 + 360 * q, 270, fill=col + (255,), width=round(u(14)))
    sc = 1 + 0.25 * max(0.0, 1 - ((t - T0) % 1.0) / 0.25)
    txt(L, (cx, cy), str(n) if n > 0 else "!", round(124 * sc), WHITE, 1.0, k="black", stroke=0)


def person(d, cx, cy, sc, col):
    r = 26 * sc
    d.ellipse([u(cx - r), u(cy - 62 * sc - r), u(cx + r), u(cy - 62 * sc + r)], fill=col + (255,))
    d.rounded_rectangle([u(cx - 34 * sc), u(cy - 28 * sc), u(cx + 34 * sc), u(cy + 50 * sc)], radius=u(26 * sc), fill=col + (255,))


def people_row(L, t):
    # yarı saydam koyu şerit
    d = ImageDraw.Draw(L)
    k0 = pop(t, t_on - 0.05, 0.3)
    if k0 > 0:
        d.rounded_rectangle([u(70), u(1255), u(1010), u(1475)], radius=u(40), fill=(15, 20, 45, round(190 * min(1, k0))))
    for k in range(10):
        q = pop(t, t_on + 0.04 * k, 0.3)
        if q <= 0:
            continue
        x = 540 + (k - 4.5) * 88
        if k == 6:
            hi = pop(t, t_biri - 0.05, 0.35)
            sc = q * (1 + 0.35 * hi)
            col = tuple(int(a * (1 - hi) + b * hi) for a, b in zip((200, 200, 215), GOLD))
            person(d, x, 1390 - 16 * hi, sc, col)
        else:
            person(d, x, 1390, q, (200, 200, 215))


class Vid(Video):
    def frame(self, t):
        i = min(len(OPN) - 1, int(t * FPS))
        im = photo(t)
        im.alpha_composite(SHADE)
        im.alpha_composite(SHADE_T)
        L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        q = 1.0 if t < 0.05 else pop(t, 0.0, 0.3)
        ImageDraw.Draw(L).rounded_rectangle([u(55), u(115), u(1025), u(360)], radius=u(44), fill=(15, 20, 45, 205))
        txt(L, (540, 180), "DİLİNİ BURNUNA", round(80 * max(q, 0.8)), WHITE, 1.0, stroke=10, k="black")
        put_word(L, "DEĞDİREBİLİR MİSİN?", GOLD, 540, 295, max(8, round(90 * max(q, 0.8))), alpha=1.0, glow=0.35)
        if t < T0:
            if t >= t_hem - 0.05:
                k = pop(t, t_hem - 0.05, 0.35)
                chip(L, 540, 1500, "HEMEN DENE!", bg=GOLD, fg=INKC, size=86, k="black", scale=k)
        elif t < t_on - 0.05:
            timer(L, t)
        elif t < t_yapb - 0.05:
            people_row(L, t)
            k = pop(t, t_on, 0.35)
            put_word(L, "10 KİŞİDEN SADECE 1'İ!", WHITE, 540, 1545, max(8, round(70 * k)), alpha=1.0, glow=0.4)
        else:
            k = pop(t, t_yapb - 0.05, 0.35)
            chip(L, 540, 1390, "Yapabildin mi?", bg=WHITE, fg=INKC, size=64, k="black", scale=k)
            kk = pop(t, t_yor - 0.05, 0.35)
            pulse = 1 + 0.04 * math.sin((t - t_yor) * 8)
            chip(L, 540, 1525, "Yorumlara YAPTIM yaz!", bg=GOLD, fg=INKC, size=70, icon_name="speech_balloon", k="black", scale=kk * pulse)
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
    ev += [(t_on - 0.05, "whoosh"), (t_biri - 0.05, "pop"), (t_yapb - 0.05, "pop"), (t_yor - 0.05, "pop")]
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
            VID.frame(tt).save(WORK / "test" / f"b_{tt:05.2f}.jpg", quality=90)
    elif mode == "ses":
        make_audio()
    else:
        make_audio()
        VID.render(str(WORK / "mix.m4a"), str(WORK / "video.mp4"))
        print("render bitti", TOTAL, flush=True)
