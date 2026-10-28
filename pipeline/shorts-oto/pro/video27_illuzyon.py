"""27. video (2K, ~35 sn): Durgun resim dönüyor (periferik kayma illüzyonu) – dene formatı.
Kullanım: python3 video27_illuzyon.py <WORK> [frames t1,t2,...]
WORK: voice_cut.wav, words.json, marks.json, muzik.wav, desen.png (1440x2560)"""
import os
os.environ.setdefault("PA_SCALE", str(4 / 3))
import json, math, subprocess, sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from engine import *  # noqa
from pa_ui import put_word, panel, txt, pop, win, captions
import audio_tools as at
from abi_yuz import konusma
from rozet import Rozet

WORK = Path(sys.argv[1])
VOICE = WORK / "voice_cut.wav"
words = json.loads((WORK / "words.json").read_text(encoding="utf-8"))
P = json.loads((WORK / "marks.json").read_text())["piece_ends"]
TOTAL = round(at.duration(str(VOICE)) + 0.3, 3)


def _hits(key):
    k = trl(clean(key)).strip('"!?;,.…')
    return [w for w in words if trl(clean(w["w"])).strip('"!?;,.…') == k]


def T(key, nth=0):
    return _hits(key)[nth]["s"]


# whisper kaymaları: parça başlarına sabitle
for w in _hits("Gözünü"):
    w["s"] = round(P[6] + 0.13 + 0.09, 3)

t_simdi, t_donuyor, t_simdi2 = T("Şimdi"), T("Dönüyor"), T("Şimdi", 1)
t_donme, t_hatta, t_cunku = T("Dönme"), T("Hatta"), T("Çünkü")
t_acik, t_koyu, t_gozun, t_gozunu = T("açık"), T("koyu"), T("Gözün"), T("Gözünü")
t_sende, t_yorum, t_daha = T("Sende"), T("Yorumlara"), T("Daha")

GOLD = (255, 196, 64)
CORAL = (255, 112, 84)
INKC = (22, 24, 38)
GRN = (60, 215, 120)
BLK, BLU, WHT, YEL = (12, 12, 16), (34, 78, 210), (250, 250, 246), (246, 206, 40)
FIX = (540, 1000)

DESEN = Image.open(WORK / "desen.png").convert("RGBA")
assert DESEN.size == (W, H)


def _grad():
    yy = np.linspace(0, 1, H, dtype=np.float32)[:, None]
    top = np.clip((0.215 - yy) / 0.215, 0, 1) ** 0.8 * 235
    bot = np.clip((yy - 0.75) / 0.25, 0, 1) ** 1.2 * 230
    a = np.maximum(top, bot)
    g = np.zeros((H, W, 4), np.uint8)
    g[..., :3] = (10, 12, 22)
    g[..., 3] = np.broadcast_to(a, (H, W)).astype(np.uint8)
    return Image.fromarray(g, "RGBA")


GRAD = _grad()
DARK = Image.new("RGBA", (W, H), (10, 12, 22, 255))


def title(L, t, lines, t0, t1, sub=None, sub_col=(200, 206, 226)):
    a = win(t, t0, t1, 0.18, 0.15)
    if a <= 0.01:
        return
    p = 1 + 0.12 * (1 - pop(t, t0, 0.32))
    y = 190 if len(lines) == 2 else 230
    for k, (s, col, size) in enumerate(lines):
        txt(L, (540, y + k * 118), s, round(size * p), col, a, stroke=4)
    if sub:
        chip(L, 540, y + len(lines) * 118 - 10, sub, bg=(36, 44, 80), fg=WHITE, size=36, k="black", alpha=a,
             scale=pop(t, t0 + 0.15, 0.3))


# ---------- açıklama ----------
def s_speed(L, t):
    a0, a1 = t_cunku - 0.1, t_gozun - 0.1
    if not (a0 <= t < a1 + 0.3):
        return
    a = 1 - eio(ph(t, a1 - 0.1, 0.3))
    chip(L, 540, 300, "BEYNİNİN HIZI", bg=GOLD, fg=INKC, size=44, k="black", scale=pop(t, a0), alpha=a)
    rows = [("AÇIK RENK", (WHT, YEL), "hızlı", "high_voltage", 0.55, 760),
            ("KOYU RENK", (BLK, BLU), "yavaş", "stopwatch", 1.9, 1090)]
    d = ImageDraw.Draw(L)
    for k, (lab, sw, sp, ic, dur, y) in enumerate(rows):
        q = pop(t, a0 + 0.15 + 0.15 * k, 0.35)
        panel(L, 540, y, 920, 270, scale=q, alpha=a, r=44)
        if q < 0.3:
            continue
        # renk örnekleri
        for j, c in enumerate(sw):
            x = 150 + j * 92
            d.rounded_rectangle([u(x - 38), u(y - 78), u(x + 38), u(y - 2)], radius=u(12), fill=c + (int(255 * a),),
                                outline=(255, 255, 255, int(90 * a)), width=round(u(2)))
        txt(L, (290, y - 40), lab, 50, WHITE, a, anchor="lm")
        # işlem çubuğu
        bx0, bx1, by = 112, 820, y + 62
        d.rounded_rectangle([u(bx0), u(by - 14), u(bx1), u(by + 14)], radius=u(14), fill=(255, 255, 255, int(30 * a)))
        f = eo(ph(t, t_acik + 0.1, dur))
        col = GOLD if k == 0 else (150, 160, 200)
        if f > 0.01:
            d.rounded_rectangle([u(bx0), u(by - 14), u(bx0 + (bx1 - bx0) * f), u(by + 14)], radius=u(14), fill=col + (int(255 * a),))
        put_icon(L, ic, 885, y - 40, 78, alpha=a)
        txt(L, (885, y + 62), sp, 38, col, a * eo(ph(t, t_acik + 0.1 + dur, 0.2)))


def s_strip(L, t):
    a0, a1 = t_gozun - 0.1, t_sende - 0.1
    if not (a0 <= t < a1 + 0.3):
        return
    a = 1 - eio(ph(t, a1 - 0.1, 0.3))
    fixed = t >= t_gozunu - 0.05
    if not fixed:
        chip(L, 540, 300, "GÖZ KIPIRDAYINCA", bg=CORAL, fg=WHITE, size=44, k="black", scale=pop(t, a0), alpha=a)
    else:
        chip(L, 540, 300, "GÖZ SABİTKEN", bg=GRN, fg=INKC, size=44, k="black", scale=pop(t, t_gozunu - 0.05), alpha=a)
    # göz ikonu: kıpırdarken sıçrar, sabitken durur
    ex = 540
    if not fixed:
        k = int((t - a0) / 0.45)
        rng = np.random.default_rng(k + 3)
        ex = 540 + rng.uniform(-160, 160)
    put_icon(L, "eye", ex, 560, 150 * pop(t, a0 + 0.1, 0.35), alpha=a)
    # renk şeridi
    q = pop(t, a0 + 0.2, 0.4)
    panel(L, 540, 860, 960, 230, scale=q, alpha=a, r=40)
    seq = [BLK, BLU, WHT, YEL]
    wts = [0.12, 0.38, 0.12, 0.38]
    d = ImageDraw.Draw(L)
    x = 100.0
    cell = 220
    if q > 0.3:
        for rep in range(4):
            for c, wt in zip(seq, wts):
                w_ = cell * wt
                d.rectangle([u(x), u(800), u(x + w_), u(920)], fill=c + (int(255 * a),))
                x += w_
        d.rectangle([u(100), u(800), u(980), u(920)], outline=(255, 255, 255, int(120 * a)), width=round(u(3)))
    # algılanan hareket oku
    if not fixed:
        aa = a * eo(ph(t, a0 + 0.6, 0.3))
        sh = 30 * ((t * 1.6) % 1)
        for k in range(3):
            xx = 330 + k * 170 + sh
            d.polygon([(u(xx), u(1010)), (u(xx - 40), u(985)), (u(xx - 40), u(1035))], fill=GOLD + (int(255 * aa * (0.5 + 0.25 * k)),))
        txt(L, (540, 1110), "HAREKET EDİYOR SANIYOR", 50, GOLD, aa)
    else:
        aa = a * eo(ph(t, t_gozunu + 0.1, 0.3))
        put_icon(L, "check_mark_button", 540, 1020, 90 * pop(t, t_gozunu + 0.1, 0.3), alpha=aa)
        txt(L, (540, 1120), "FARK KAYBOLUR, DURUR", 50, GRN, aa)


def s_cta(L, t):
    if t < t_sende - 0.1:
        return
    if t < t_daha - 0.1:
        a = 1 - eio(ph(t, t_daha - 0.2, 0.15))
        p = 1 + 0.1 * (1 - pop(t, t_sende - 0.1, 0.3))
        txt(L, (540, 175), "SENDE DE DÖNDÜ MÜ?", round(80 * p), WHITE, a, stroke=4)
        chip(L, 330, 300, "Döndü", bg=CORAL, fg=WHITE, size=46, icon_name="exploding_head", k="black", alpha=a,
             scale=pop(t, t_sende + 0.2, 0.3))
        chip(L, 750, 300, "Dönmedi", bg=(36, 44, 80), fg=WHITE, size=46, icon_name="thinking_face", k="black", alpha=a,
             scale=pop(t, t_sende + 0.4, 0.3))
        if t >= t_yorum - 0.08:
            chip(L, 540, 1400, "Yorumlara yaz", bg=WHITE, fg=INKC, size=50, icon_name="speech_balloon", k="black", alpha=a,
                 scale=pop(t, t_yorum - 0.08, 0.35))
    else:
        a = eo(ph(t, t_daha - 0.1, 0.25))
        txt(L, (540, 160), "Daha fazla illüzyon için", 50, (215, 220, 236), a)
        pulse = 1 + 0.045 * math.sin((t - t_daha) * 8) * eo(ph(t, t_daha + 0.4, 0.3))
        chip(L, 540, 290, "TAKİP ET", bg=CORAL, fg=WHITE, size=72, icon_name="bell", k="black",
             scale=pop(t, t_daha - 0.1, 0.4) * pulse)


# ---------- deney kısmı ----------
GUIDE = [(200, 640), (880, 760), (540, 1300), (180, 1180), (860, 1380), (520, 700)]


def s_test(L, t):
    if t >= t_cunku - 0.1:
        return
    title(L, t, [("BU RESİM", WHITE, 92), ("HİÇ HAREKET ETMİYOR", GOLD, 76)], -1, t_simdi - 0.1)
    title(L, t, [("GÖZLERİNİ", WHITE, 92), ("RESİMDE GEZDİR", GOLD, 92)], t_simdi - 0.1, t_donuyor - 0.1)
    title(L, t, [("DÖNÜYOR,", WHITE, 100), ("DEĞİL Mİ?", CORAL, 100)], t_donuyor - 0.1, t_simdi2 - 0.1)
    title(L, t, [("ORTADAKİ", WHITE, 92), ("NOKTAYA BAK", GOLD, 92)], t_simdi2 - 0.1, t_donme - 0.1)
    title(L, t, [("DURDU!", GRN, 130)], t_donme - 0.1, t_cunku - 0.1)
    # göz gezdirme kılavuzu: halka noktadan noktaya sıçrar
    g0, g1 = P[1] - 0.1, t_donuyor - 0.15
    if g0 <= t < g1:
        k = int((t - g0) / 0.6) % len(GUIDE)
        lt = ((t - g0) % 0.6)
        x, y = GUIDE[k]
        a = eo(lt / 0.12) * (1 - eio(ph(t, g1 - 0.15, 0.15)))
        d = ImageDraw.Draw(L)
        r = u(46)
        d.ellipse([u(x) - r, u(y) - r, u(x) + r, u(y) + r], outline=(255, 255, 255, int(235 * a)), width=round(u(7)))
        d.ellipse([u(x) - r - u(5), u(y) - r - u(5), u(x) + r + u(5), u(y) + r + u(5)], outline=(0, 0, 0, int(120 * a)),
                  width=round(u(3)))
    # sabitleme noktası
    f0 = t_simdi2 + 0.5
    if f0 <= t < t_cunku - 0.1:
        a = eo(ph(t, f0, 0.2)) * (1 - eio(ph(t, t_cunku - 0.3, 0.2)))
        d = ImageDraw.Draw(L)
        R1, R2 = u(30), u(18)
        x, y = u(FIX[0]), u(FIX[1])
        d.ellipse([x - R1, y - R1, x + R1, y + R1], fill=(255, 255, 255, int(255 * a)))
        d.ellipse([x - R2, y - R2, x + R2, y + R2], fill=(235, 40, 50, int(255 * a)))


ROZ = Rozet()
OPN, RND = konusma(VOICE, FPS)


class Vid(Video):
    def frame(self, t):
        im = DESEN.copy()
        im.alpha_composite(GRAD)
        # açıklama bölümünde desen kararır
        dk = eo(ph(t, t_cunku - 0.15, 0.3)) * (1 - eio(ph(t, t_sende - 0.2, 0.3)))
        if dk > 0.01:
            im.alpha_composite(set_alpha(DARK, 0.9 * dk))
        L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        s_test(L, t)
        s_speed(L, t)
        s_strip(L, t)
        s_cta(L, t)
        im.alpha_composite(L)
        brand(im, 540, 62, size=34)
        C = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        captions(C, self.groups, t)
        im.alpha_composite(C)
        i = min(len(OPN) - 1, int(t * FPS))
        ROZ.draw(im, t, float(OPN[i]))
        return im.convert("RGB")


if __name__ == "__main__":
    mode = sys.argv[2] if len(sys.argv) > 2 else "render"
    v = Vid([{"start": 0, "end": TOTAL, "draw": lambda *a: None}], words, "", TOTAL, bg=None)
    print("TOTAL", TOTAL, flush=True)
    if mode == "frames":
        (WORK / "test").mkdir(exist_ok=True)
        for tt in [float(x) for x in sys.argv[3].split(",")]:
            v.frame(tt).save(WORK / "test" / f"fr_{tt:05.2f}.jpg", quality=90)
    else:
        sfx = [(t_simdi - 0.1, "whoosh"), (t_donuyor - 0.1, "pop"), (t_simdi2 - 0.1, "whoosh"), (t_simdi2 + 0.5, "pop"),
               (t_donme - 0.1, "ding"), (t_cunku - 0.15, "whoosh"), (t_acik + 0.1, "whoosh"), (t_gozun - 0.1, "whoosh"),
               (t_gozunu - 0.05, "pop"), (t_gozunu + 0.1, "ding"), (t_sende - 0.1, "whoosh"), (t_sende + 0.2, "pop"),
               (t_sende + 0.4, "pop"), (t_yorum - 0.08, "pop"), (t_daha - 0.1, "pop")]
        g0 = P[1] - 0.1
        tt = g0
        while tt < t_donuyor - 0.2:
            sfx.append((tt, "tink"))
            tt += 0.6
        at.sfx(str(WORK / "sfx.wav"), TOTAL, sfx)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-stream_loop", "2", "-i", str(WORK / "muzik.wav"), "-af",
                        f"atrim=0:{TOTAL:.3f},afade=t=in:d=0.15,afade=t=out:st={TOTAL - 0.6:.3f}:d=0.6",
                        "-ar", "44100", "-ac", "1", str(WORK / "music.wav")], check=True)
        at.final_mix(str(VOICE), str(WORK / "music.wav"), str(WORK / "sfx.wav"), str(WORK / "mix.m4a"))
        v.render(str(WORK / "mix.m4a"), str(WORK / "video.mp4"))
        print("render bitti", TOTAL, flush=True)
