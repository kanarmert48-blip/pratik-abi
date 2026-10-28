"""26. video (2K, ~37 sn): Stroop testi – yazıyı okuma, rengini söyle (dene formatı).
Kullanım: python3 video26_stroop.py <WORK> [frames t1,t2,...]
WORK: voice_cut.wav, words.json, marks.json, muzik.wav"""
import os
os.environ.setdefault("PA_SCALE", str(4 / 3))
import json, math, subprocess, sys
from functools import lru_cache
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from engine import *  # noqa
from PIL import ImageChops  # noqa
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


# whisper'ın kaydırdığı son cümle başı: parça başı
for w in words:
    if w["s"] > P[13] - 0.05:
        pass
_d = [w for w in words if trl(clean(w["w"])).strip(".") == trl("Daha")]
if _d:
    _d[-1]["s"] = round(P[13] + 0.2 + 0.09, 3)

t_kural, t_yazi, t_sadece = T("Kural"), T("yazıyı"), T("sadece")
t_once, t_simdi, t_basla = T("Önce"), T("Şimdi"), T("Başla")
t_zor, t_cunku, t_rengi = T("Zorlandın"), T("Çünkü"), T("rengi")
t_ikisi, t_buna, t_kac = T("İkisi"), T("Buna"), T("Kaç")
t_yorum, t_daha = T("Yorumlara"), T("Daha")

# renkler (koyu zeminde net ayrışan)
KR = (255, 74, 74)
MV = (64, 148, 255)
YS = (40, 212, 112)
SR_ = (255, 214, 48)
MR = (176, 104, 255)
NAME = {KR: "kırmızı", MV: "mavi", YS: "yeşil", SR_: "sarı", MR: "mor"}
GOLD = (255, 196, 64)
CORAL = (255, 112, 84)
INKC = (22, 24, 38)
BG0 = (13, 16, 30)
BG1 = (30, 38, 70)

R1 = [("YEŞİL", KR), ("MAVİ", SR_), ("SARI", MV), ("KIRMIZI", YS)]
R1_DT = [1.55] * 4
R2 = [("KIRMIZI", MV), ("SARI", YS), ("MAVİ", KR), ("YEŞİL", SR_), ("SARI", KR), ("MAVİ", YS)]
R2_DT = [1.95, 1.9, 1.85, 1.8, 1.75, 1.7]
R1_T0 = P[4] + 0.25
R2_T0 = P[6] + 0.13
R1_END = R1_T0 + sum(R1_DT)
R2_END = R2_T0 + sum(R2_DT)
CLOUD = [("MAVİ", KR), ("SARI", MV), ("YEŞİL", SR_), ("KIRMIZI", YS), ("SARI", KR), ("MAVİ", YS), ("YEŞİL", MV),
         ("KIRMIZI", MV), ("YEŞİL", KR), ("MAVİ", SR_), ("SARI", YS), ("KIRMIZI", SR_), ("YEŞİL", SR_)]


def sched(t0, dts, t):
    """-> (index, local_t, dur) ya da None"""
    if t < t0:
        return None
    s = t0
    for i, d in enumerate(dts):
        if t < s + d:
            return i, t - s, d
        s += d
    return None


# ---------- arka plan ----------
def _bg():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt(((xx - W / 2) / W) ** 2 + ((yy - H * 0.45) / H) ** 2 * 0.6)
    k = np.clip(1 - r * 1.6, 0, 1)[..., None] ** 1.4
    img = np.array(BG0, np.float32) * (1 - k) + np.array(BG1, np.float32) * k
    rng = np.random.default_rng(2)
    img += rng.normal(0, 2.2, img.shape[:2])[..., None]
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), "RGB").convert("RGBA")


BG = _bg()
GS = 90


def _grid():
    g = Image.new("RGBA", (W, H + round(u(GS))), (0, 0, 0, 0))
    d = ImageDraw.Draw(g)
    for x in range(0, 1081, GS):
        d.line([(u(x), 0), (u(x), g.height)], fill=(255, 255, 255, 9), width=round(u(2)))
    for y in range(0, 1920 + GS + 1, GS):
        d.line([(0, u(y)), (W, u(y))], fill=(255, 255, 255, 9), width=round(u(2)))
    return g


GRID = _grid()
_yy, _xx = np.mgrid[0:H, 0:W].astype(np.float32)
VIG = Image.fromarray((np.clip(((_xx / W - 0.5) ** 2 + (_yy / H - 0.5) ** 2 * 0.8) * 2.6, 0, 1) ** 1.5 * 170).astype(np.uint8), "L")
VIGL = Image.new("RGBA", (W, H), (0, 0, 0, 0))
VIGL.putalpha(VIG)


# ---------- yazı görselleri ----------
@lru_cache(maxsize=400)
def word_img(txt, col, size, glow=0.55):
    f = font("black", round(u(size)))
    bb = f.getbbox(txt)
    w, h = bb[2] - bb[0], bb[3] - bb[1]
    pad = round(u(size * 0.45))
    im = Image.new("RGBA", (w + 2 * pad, h + 2 * pad), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((pad - bb[0], pad - bb[1]), txt, font=f, fill=col + (255,))
    out = Image.new("RGBA", im.size, (0, 0, 0, 0))
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
    sh.putalpha(im.getchannel("A").point(lambda v: int(v * 0.6)))
    out.alpha_composite(sh.filter(ImageFilter.GaussianBlur(u(size * 0.06))), (0, round(u(size * 0.05))))
    if glow:
        g = im.filter(ImageFilter.GaussianBlur(u(size * 0.16)))
        out.alpha_composite(set_alpha(g, glow))
    out.alpha_composite(im)
    return out


def put_word(L, txt, col, cx, cy, size, scale=1.0, alpha=1.0, glow=0.55, rot=0.0):
    if alpha <= 0.01 or scale <= 0.02:
        return
    im = word_img(txt, col, size, glow)
    if abs(scale - 1) > 0.005:
        im = im.resize((max(1, round(im.width * scale)), max(1, round(im.height * scale))), Image.BICUBIC)
    if rot:
        im = im.rotate(rot, resample=Image.BICUBIC, expand=True)
    comp(L, set_alpha(im, alpha), u(cx) - im.width / 2, u(cy) - im.height / 2)


@lru_cache(maxsize=16)
def panel_img(w, h, r=56, fill=(255, 255, 255, 16), line=(255, 255, 255, 46)):
    M = round(u(60))
    im = Image.new("RGBA", (round(u(w)) + 2 * M, round(u(h)) + 2 * M), (0, 0, 0, 0))
    sh, pad = soft_shadow(round(u(w)), round(u(h)), round(u(r)), blur=round(u(26)), op=0.55)
    comp(im, sh, M - pad, M - pad + u(14))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([M, M, M + round(u(w)), M + round(u(h))], radius=round(u(r)), fill=(26, 32, 58, 235),
                        outline=line, width=round(u(3)))
    # üst parlama
    hl = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(hl).rounded_rectangle([M + 4, M + 4, M + round(u(w)) - 4, M + round(u(h * 0.5))], radius=round(u(r)),
                                         fill=(255, 255, 255, 10))
    im.alpha_composite(hl)
    return im


def panel(L, cx, cy, w, h, scale=1.0, alpha=1.0, r=56):
    if alpha <= 0.01 or scale <= 0.02:
        return
    im = panel_img(w, h, r)
    if abs(scale - 1) > 0.005:
        im = im.resize((round(im.width * scale), round(im.height * scale)), Image.BICUBIC)
    comp(L, set_alpha(im, alpha), u(cx) - im.width / 2, u(cy) - im.height / 2)


def txt(L, xy, s, size, col=WHITE, a=1.0, k="black", anchor="mm", stroke=0):
    if a <= 0.01 or size < 4:
        return
    text_c(L, xy, s, k, size, col, anchor=anchor, alpha=a, stroke=stroke, stroke_fill=(10, 12, 24))


def pop(t, t0, d=0.35):
    return eb(ph(t, t0, d))


def win(t, a, b, fi=0.25, fo=0.22):
    return eo(ph(t, a, fi)) * (1 - eio(ph(t, b - fo, fo)))


# ---------- sahneler ----------
def s_hook(L, t):
    end = t_kural - 0.32
    if t >= end + 0.3:
        return
    out = eio(ph(t, end, 0.28))
    Lw = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    rows = [800, 945, 1090, 1235, 1380]
    for r, y in enumerate(rows):
        seq = CLOUD[r * 2:] + CLOUD[:r * 2]
        dirn = 1 if r % 2 == 0 else -1
        x = -300 + dirn * (t * 70) + (r * 137) % 260 - (1 + dirn) * 0 + dirn * out * 900
        k = 0
        xs = x - 1400 if dirn > 0 else x
        while xs < 1500:
            w_, c = seq[k % len(seq)]
            fw = font("black", round(u(92))).getlength(w_) / S
            put_word(Lw, w_, c, xs + fw / 2, y, 92, alpha=(1 - out) * (0.95 if r in (1, 2, 3) else 0.7), glow=0.4)
            xs += fw + 70
            k += 1
    Lw = Lw.rotate(-7, resample=Image.BICUBIC, center=(W / 2, u(1090)))
    L.alpha_composite(Lw)
    a = 1 - out
    p1 = 1 + 0.10 * (1 - pop(t, 0, 0.35))
    chip(L, 540, 250, "BU TESTTE", bg=GOLD, fg=INKC, size=40, k="black", alpha=a, scale=p1)
    txt(L, (540, 395), "BEYNİN", round(150 * p1), WHITE, a, stroke=4)
    txt(L, (540, 550), "TAKILACAK", round(150 * p1), CORAL, a, stroke=4)


def s_rules(L, t):
    a0, a1 = t_kural - 0.1, t_once - 0.05
    if not (a0 <= t < a1 + 0.3):
        return
    a = 1 - eio(ph(t, a1 - 0.1, 0.3))
    chip(L, 540, 330, "KURAL", bg=CORAL, fg=WHITE, size=46, k="black", scale=pop(t, a0), alpha=a)
    q = pop(t, t_yazi - 0.12, 0.4)
    panel(L, 540, 700, 760, 300, scale=q, alpha=a)
    put_word(L, "MAVİ", KR, 540, 700, 170, scale=q, alpha=a)
    # ❌ okuma
    qa = eo(ph(t, t_yazi + 0.25, 0.3)) * a
    if qa > 0.01:
        put_icon(L, "cross_mark", 250, 975, 78 * pop(t, t_yazi + 0.25), alpha=qa)
        txt(L, (310, 975), 'Okuma: "mavi"', 56, (210, 214, 232), qa, anchor="lm")
        f = font("black", round(u(56)))
        wd = f.getlength('Okuma: "mavi"') / S
        k = eo(ph(t, t_yazi + 0.45, 0.3))
        d = ImageDraw.Draw(L)
        d.line([(u(305), u(978)), (u(305 + (wd + 10) * k), u(978))], fill=KR + (int(255 * qa),), width=round(u(8)))
    qb = eo(ph(t, t_sadece + 0.35, 0.3)) * a
    if qb > 0.01:
        put_icon(L, "check_mark_button", 250, 1120, 80 * pop(t, t_sadece + 0.35), alpha=qb)
        txt(L, (310, 1120), "Söyle:", 56, WHITE, qb, anchor="lm")
        f = font("black", round(u(56)))
        x2 = 310 + f.getlength("Söyle: ") / S
        put_word(L, "KIRMIZI", KR, x2 + font("black", round(u(70))).getlength("KIRMIZI") / S / 2, 1118, 70,
                 scale=pop(t, t_sadece + 0.45), alpha=qb, glow=0.4)


def round_header(L, t):
    # ısınma
    a = win(t, t_once - 0.05, t_simdi, 0.25, 0.2)
    if a > 0.01:
        chip(L, 540, 300, "ISINMA TURU", bg=GOLD, fg=INKC, size=46, k="black", scale=pop(t, t_once - 0.05), alpha=a)
        txt(L, (540, 410), "Rengini söyle", 50, (190, 196, 220), a, k="b")
    b = win(t, t_simdi - 0.05, R2_END + 0.15, 0.25, 0.2)
    if b > 0.01:
        chip(L, 540, 300, "ASIL TEST", bg=KR, fg=WHITE, size=50, k="black", scale=pop(t, t_simdi - 0.05), alpha=b)
        txt(L, (540, 410), "Yazıyı okuma, rengini söyle", 46, (190, 196, 220), b, k="b")
    if t_basla - 0.05 <= t < R2_T0 + 0.1:
        c = 1 - eio(ph(t, R2_T0 - 0.08, 0.15))
        put_word(L, "BAŞLA!", WHITE, 540, 900, 190, scale=pop(t, t_basla - 0.05, 0.3), alpha=c, glow=0.25)


def round_card(L, t, t0, dts, items, label_speed=False):
    st = sched(t0, dts, t)
    endt = t0 + sum(dts)
    if st is None:
        if endt <= t < endt + 0.25:   # son kartın çıkışı
            q = eio(ph(t, endt, 0.22))
            panel(L, 540, 900, 900, 560, scale=1 - 0.08 * q, alpha=1 - q)
        return
    i, lt, d = st
    n = len(items)
    intro = pop(t, t0, 0.35)
    panel(L, 540, 900, 900, 560, scale=intro)
    w_, c = items[i]
    q = eo(ph(lt, 0, 0.16))
    put_word(L, w_, c, 540, 870, 190, scale=0.82 + 0.18 * eb(ph(lt, 0, 0.28)), alpha=q)
    # süre çubuğu
    d_ = ImageDraw.Draw(L)
    bw = 600
    x0, y0 = 540 - bw / 2, 1065
    d_.rounded_rectangle([u(x0), u(y0), u(x0 + bw), u(y0 + 14)], radius=u(7), fill=(255, 255, 255, 34))
    rem = 1 - clamp(lt / d)
    if rem > 0.01:
        col = (255, 255, 255) if rem > 0.3 else KR
        d_.rounded_rectangle([u(x0), u(y0), u(x0 + bw * rem), u(y0 + 14)], radius=u(7), fill=col + (230,))
    # sayaç
    txt(L, (900, 700), f"{i + 1}/{n}", 40, (170, 176, 205), 1.0, k="b", anchor="rm")
    # ilerleme noktaları
    gap = 54
    xs = 540 - gap * (n - 1) / 2
    for k in range(n):
        x = xs + gap * k
        y = 1250
        r = 13 if k == i else 10
        if k < i:
            d_.ellipse([u(x - r), u(y - r), u(x + r), u(y + r)], fill=(255, 255, 255, 200))
        elif k == i:
            d_.ellipse([u(x - r), u(y - r), u(x + r), u(y + r)], fill=GOLD + (255,))
        else:
            d_.ellipse([u(x - r), u(y - r), u(x + r), u(y + r)], outline=(255, 255, 255, 110), width=round(u(3)))
    if label_speed and i >= 4:
        a = eo(ph(t, t0 + sum(dts[:4]), 0.25))
        chip(L, 540, 1340, "HIZLANIYOR", bg=(40, 46, 80), fg=GOLD, size=34, icon_name="high_voltage", k="black",
             alpha=a, scale=pop(t, t0 + sum(dts[:4]), 0.3))


def s_timeup(L, t):
    if not (R2_END <= t < R2_END + 0.55):
        return
    a = 1 - eio(ph(t, R2_END + 0.35, 0.2))
    put_icon(L, "stopwatch", 540, 760, 170 * pop(t, R2_END, 0.3), alpha=a)
    put_word(L, "SÜRE BİTTİ", KR, 540, 960, 120, scale=pop(t, R2_END, 0.3), alpha=a, glow=0.3)


def s_answers(L, t):
    a0, a1 = R2_END + 0.4, t_cunku - 0.05
    if not (a0 <= t < a1 + 0.3):
        return
    a = 1 - eio(ph(t, a1 - 0.12, 0.3))
    chip(L, 540, 300, "CEVAPLAR", bg=YS, fg=INKC, size=46, k="black", icon_name="check_mark_button", scale=pop(t, a0),
         alpha=a)
    for k, (w_, c) in enumerate(R2):
        col, row = k % 2, k // 2
        x = 290 + col * 500
        y = 560 + row * 250
        q = pop(t, a0 + 0.05 + 0.07 * k, 0.32)
        panel(L, x, y, 450, 210, scale=q, alpha=a, r=40)
        put_word(L, w_, c, x, y - 24, 86, scale=q, alpha=a, glow=0.35)
        txt(L, (x, y + 58), NAME[c], 42, (205, 210, 230), a * eo(ph(t, a0 + 0.2 + 0.06 * k, 0.25)), k="b")


# yarış sahnesi
def bez(p0, p1, p2, s):
    return ((1 - s) ** 2 * p0[0] + 2 * (1 - s) * s * p1[0] + s * s * p2[0],
            (1 - s) ** 2 * p0[1] + 2 * (1 - s) * s * p1[1] + s * s * p2[1])


LP = ((400, 560), (190, 840), (455, 1085))
RP = ((680, 560), (890, 840), (625, 1085))
HEAD = (540, 1250)
T_COL = None


def s_race(L, t):
    global T_COL
    a0, a1 = t_cunku - 0.1, t_buna - 0.15
    if not (a0 <= t < a1 + 0.3):
        return
    a = 1 - eio(ph(t, a1 - 0.1, 0.3))
    tl0, tl1 = t_cunku + 0.35, t_cunku + 1.05          # okuma: hızlı
    tr0 = t_rengi + 0.05
    t_col = t_ikisi + 0.55
    tr1 = t_col - 0.02                                   # renk: yavaş
    q = pop(t, a0, 0.4)
    panel(L, 540, 430, 560, 230, scale=q, alpha=a)
    put_word(L, "MAVİ", KR, 540, 430, 140, scale=q, alpha=a)
    d = ImageDraw.Draw(L)
    # yollar
    for P_, col, tt0 in ((LP, GOLD, tl0 - 0.25), (RP, (140, 220, 255), tr0 - 0.25)):
        pa = eo(ph(t, tt0, 0.35)) * a
        if pa > 0.01:
            n = 26
            pts = [bez(*P_, k / n) for k in range(n + 1)]
            for k in range(0, n, 2):
                d.line([(u(pts[k][0]), u(pts[k][1])), (u(pts[k + 1][0]), u(pts[k + 1][1]))], fill=col + (int(150 * pa),),
                       width=round(u(7)))
    # etiketler
    la = eo(ph(t, tl0 - 0.1, 0.3)) * a
    txt(L, (175, 700), "otomatik", 38, GOLD, la, k="black")
    txt(L, (175, 748), "çok hızlı", 34, (230, 220, 190), la, k="b")
    ra = eo(ph(t, tr0 - 0.1, 0.3)) * a
    txt(L, (905, 700), "dikkat ister", 38, (140, 220, 255), ra, k="black")
    txt(L, (905, 748), "yavaş", 34, (200, 225, 240), ra, k="b")
    # hedef kafa
    col_t = t - t_col
    if col_t < 0:
        put_icon(L, "thinking_face", HEAD[0], HEAD[1], 190 * pop(t, a0 + 0.2, 0.4), alpha=a)
    else:
        sc = 230 * (1 + 0.25 * math.exp(-col_t * 6) * math.sin(col_t * 30))
        put_icon(L, "exploding_head", HEAD[0], HEAD[1], sc * pop(t, t_col, 0.3), alpha=a)
        # patlama halkası
        if col_t < 0.6:
            rr = u(120 + 420 * eo(col_t / 0.6))
            d.ellipse([u(HEAD[0]) - rr, u(HEAD[1]) - rr, u(HEAD[0]) + rr, u(HEAD[1]) + rr],
                      outline=(255, 255, 255, int(200 * (1 - col_t / 0.6))), width=round(u(10)))
            for k in range(12):
                an = k * math.pi / 6
                r0, r1 = u(150 + 300 * eo(col_t / 0.6)), u(190 + 360 * eo(col_t / 0.6))
                c = [KR, MV, YS, SR_, MR, GOLD][k % 6]
                d.line([(u(HEAD[0]) + math.cos(an) * r0, u(HEAD[1]) + math.sin(an) * r0),
                        (u(HEAD[0]) + math.cos(an) * r1, u(HEAD[1]) + math.sin(an) * r1)],
                       fill=c + (int(255 * (1 - col_t / 0.6)),), width=round(u(9)))
        # iki cevap çatışıyor
        ba = eo(ph(col_t, 0.05, 0.25)) * a
        wob = math.sin(col_t * 22) * 6 * math.exp(-col_t * 2)
        put_word(L, "mavi?", WHITE, 255 + wob, 1150, 66, alpha=ba, glow=0.2, rot=8)
        put_word(L, "kırmızı?", KR, 835 - wob, 1150, 66, alpha=ba, glow=0.3, rot=-8)
        # glitch başlık
        ga = eo(ph(col_t, 0.1, 0.2)) * a
        if ga > 0.01:
            jit = 8 * math.exp(-col_t * 3) * math.sin(col_t * 60)
            put_word(L, "TAKILMA!", (60, 220, 255), 540 - 6 + jit, 1440, 110, alpha=ga * 0.8, glow=0)
            put_word(L, "TAKILMA!", (255, 60, 90), 540 + 6 - jit, 1440, 110, alpha=ga * 0.8, glow=0)
            put_word(L, "TAKILMA!", WHITE, 540, 1440, 110, alpha=ga, glow=0.2)
    # hapler (yol üzerinde giden etiketler)
    if t >= tl0 - 0.05 and t < t_col + 0.05:
        s = eio(ph(t, tl0, tl1 - tl0))
        x, y = bez(*LP, s)
        chip(L, x, y, "OKUMA", bg=GOLD, fg=INKC, size=36, icon_name="high_voltage", k="black", alpha=a,
             scale=pop(t, tl0 - 0.05, 0.3))
        if s >= 1:
            txt(L, (x, y - 70), '"mavi"', 42, GOLD, eo(ph(t, tl1, 0.2)) * a, k="black")
    if t >= tr0 - 0.05 and t < t_col + 0.05:
        s = ph(t, tr0, tr1 - tr0)
        s = s * s * (3 - 2 * s) * 0.6 + s * 0.4
        x, y = bez(*RP, s)
        x += 4 * math.sin(t * 14)
        chip(L, x, y, "RENK", bg=(140, 220, 255), fg=INKC, size=36, icon_name="eye", k="black", alpha=a,
             scale=pop(t, tr0 - 0.05, 0.3))


def s_stroop(L, t):
    a0, a1 = t_buna - 0.1, t_kac - 0.12
    if not (a0 <= t < a1 + 0.3):
        return
    a = 1 - eio(ph(t, a1 - 0.1, 0.3))
    q = pop(t, a0, 0.4)
    panel(L, 540, 800, 900, 640, scale=q, alpha=a)
    put_icon(L, "memo", 540, 590, 130 * q, alpha=a)
    cols = [KR, MV, YS, SR_, MV, KR]
    f = font("black", round(u(150)))
    letters = "STROOP"
    ws = [f.getlength(c) / S for c in letters]
    tw = sum(ws) + 8 * 5
    x = 540 - tw / 2
    for k, c in enumerate(letters):
        qk = pop(t, a0 + 0.12 + 0.05 * k, 0.3)
        put_word(L, c, cols[k], x + ws[k] / 2, 790, 150, scale=qk, alpha=a, glow=0.45)
        x += ws[k] + 8
    txt(L, (540, 920), "ETKİSİ", 84, WHITE, a * eo(ph(t, a0 + 0.4, 0.3)))
    txt(L, (540, 1030), "J. R. Stroop · 1935", 38, (160, 168, 200), a * eo(ph(t, a0 + 0.6, 0.3)), k="b")


def s_cta(L, t):
    a0, a1 = t_kac - 0.1, t_daha - 0.12
    if not (a0 <= t < a1 + 0.3):
        return
    a = 1 - eio(ph(t, a1 - 0.1, 0.3))
    p1 = pop(t, a0, 0.4)
    txt(L, (540, 380), "KAÇTA KAÇ", round(110 * p1), WHITE, a, stroke=3)
    txt(L, (540, 510), "YAPTIN?", round(110 * p1), GOLD, a, stroke=3)
    opts = [("8/8  efsane", "trophy"), ("5-7  fena değil", "thinking_face"), ("0-4  beyin dondu", "grinning_face_with_sweat")]
    for k, (s, ic) in enumerate(opts):
        chip(L, 540, 720 + k * 150, s, bg=(36, 44, 80), fg=WHITE, size=50, icon_name=ic, k="black", alpha=a,
             scale=pop(t, a0 + 0.3 + 0.18 * k, 0.32))
    if t >= t_yorum - 0.08:
        chip(L, 540, 1230, "Yorumlara yaz", bg=WHITE, fg=INKC, size=52, icon_name="speech_balloon", k="black", alpha=a,
             scale=pop(t, t_yorum - 0.08, 0.35))


def s_follow(L, t):
    if t < t_daha - 0.1:
        return
    a = eo(ph(t, t_daha - 0.1, 0.25))
    txt(L, (540, 690), "Daha fazla test için", 56, (210, 214, 232), a, k="black")
    pulse = 1 + 0.045 * math.sin((t - t_daha) * 8) * eo(ph(t, t_daha + 0.4, 0.3))
    chip(L, 540, 860, "TAKİP ET", bg=CORAL, fg=WHITE, size=84, icon_name="bell", k="black",
         scale=pop(t, t_daha - 0.1, 0.4) * pulse)


def captions(L, groups, t, y=1560, xoff=70):
    for st, en, g in groups:
        if st <= t < en:
            break
    else:
        return
    a = eo(ph(t, st, 0.12))
    f = font("black", round(u(56)))
    texts = [clean(w["w"]) for w in g]
    sp = f.getlength(" ")
    tw = sum(f.getlength(x) for x in texts) + sp * (len(texts) - 1)
    x = W / 2 - tw / 2 + u(xoff)
    tmp = Image.new("RGBA", (W, round(u(140))), (0, 0, 0, 0))
    d = ImageDraw.Draw(tmp)
    for w, tx in zip(g, texts):
        on = w["s"] - 0.04 <= t < w["e"] + 0.05
        d.text((x, tmp.height / 2), tx, font=f, fill=GOLD if on else WHITE, anchor="lm", stroke_width=round(u(6)),
               stroke_fill=(8, 10, 20))
        x += f.getlength(tx) + sp
    comp(L, set_alpha(tmp, a), 0, u(y) - tmp.height / 2)


ROZ = Rozet()
OPN, RND = konusma(VOICE, FPS)
CUTS = [t_kural - 0.1, t_once - 0.05, t_simdi - 0.05, R2_END + 0.4, t_cunku - 0.1, t_buna - 0.1, t_kac - 0.1,
        t_daha - 0.1]


class Vid(Video):
    def frame(self, t):
        im = BG.copy()
        off = round((t * u(18)) % u(GS))
        im.alpha_composite(GRID.crop((0, off, W, off + H)))
        L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        s_hook(L, t)
        s_rules(L, t)
        round_header(L, t)
        round_card(L, t, R1_T0, R1_DT, R1)
        round_card(L, t, R2_T0, R2_DT, R2, label_speed=True)
        s_timeup(L, t)
        s_answers(L, t)
        s_race(L, t)
        s_stroop(L, t)
        s_cta(L, t)
        s_follow(L, t)
        # sahne kesmelerinde minik zoom vuruşu + çarpışma sarsıntısı
        z = 1.0
        for c in CUTS:
            if 0 <= t - c < 0.3:
                z += 0.035 * (1 - eo((t - c) / 0.3))
        sx = sy = 0
        tc = t - (t_ikisi + 0.55)
        if 0 <= tc < 0.45:
            e = math.exp(-tc * 9)
            sx, sy = u(14) * e * math.sin(tc * 70), u(18) * e * math.cos(tc * 83)
        if z != 1.0 or sx or sy:
            lw, lh = round(W * z), round(H * z)
            L2 = L.resize((lw, lh), Image.BICUBIC) if z != 1.0 else L
            comp(im, L2, (W - lw) / 2 + sx, (H - lh) / 2 + sy)
        else:
            im.alpha_composite(L)
        im.alpha_composite(VIGL)
        if t >= t_kural - 0.1:
            brand(im, 540, 70, size=38)
        C = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        captions(C, self.groups, t)
        im.alpha_composite(C)
        i = min(len(OPN) - 1, int(t * FPS))
        ROZ.draw(im, t, float(OPN[i]))
        return im.convert("RGB")


# ---------- ses efektleri ----------
SRATE = 44100


def synth_extra(path):
    y = np.frombuffer(subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(path), "-f", "f32le", "-ac", "1", "-ar",
                                      str(SRATE), "-"], capture_output=True, check=True).stdout, np.float32).copy()

    def add(t0, s):
        i = int(t0 * SRATE)
        if i < 0 or i >= len(y):
            return
        n = min(len(s), len(y) - i)
        y[i:i + n] += s[:n]

    def tick(f=1800, amp=0.18):
        m = int(0.05 * SRATE)
        tt = np.arange(m) / SRATE
        return (np.sin(2 * np.pi * f * tt) * np.exp(-tt * 90) * amp).astype(np.float32)

    def blip(f, amp=0.2):
        m = int(0.14 * SRATE)
        tt = np.arange(m) / SRATE
        return (np.sin(2 * np.pi * f * tt) * np.exp(-tt * 28) * amp + np.sin(2 * np.pi * f * 2 * tt) * np.exp(-tt * 40) * amp * 0.3).astype(np.float32)

    def buzzer():
        m = int(0.45 * SRATE)
        tt = np.arange(m) / SRATE
        sq = np.sign(np.sin(2 * np.pi * 150 * tt)) * 0.5 + np.sign(np.sin(2 * np.pi * 154 * tt)) * 0.5
        env = np.clip(tt / 0.01, 0, 1) * np.clip((0.45 - tt) / 0.08, 0, 1)
        return (sq * env * 0.12).astype(np.float32)

    def impact():
        m = int(0.9 * SRATE)
        tt = np.arange(m) / SRATE
        f = 120 * np.exp(-tt * 4) + 38
        s = np.sin(2 * np.pi * np.cumsum(f) / SRATE) * np.exp(-tt * 5) * 0.55
        rng = np.random.default_rng(1)
        nz = rng.standard_normal(m) * np.exp(-tt * 14) * 0.18
        return (s + nz).astype(np.float32)

    # test kelimeleri: blip (ısınma tiz, asıl test daha gergin)
    s = R1_T0
    for k, d in enumerate(R1_DT):
        add(s, blip(880 + 40 * k, 0.16))
        s += d
    s = R2_T0
    for k, d in enumerate(R2_DT):
        add(s, blip(660 + 30 * k, 0.2))
        for q in np.arange(0.25, d - 0.05, 0.25):     # saat tıkırtısı
            add(s + q, tick(2200, 0.07))
        s += d
    add(R2_END, buzzer())
    add(t_ikisi + 0.55, impact())
    at._write(str(path), y)


if __name__ == "__main__":
    mode = sys.argv[2] if len(sys.argv) > 2 else "render"
    v = Vid([{"start": 0, "end": TOTAL, "draw": lambda *a: None}], words, "", TOTAL, bg=None)
    print("TOTAL", TOTAL, "R1", round(R1_T0, 2), round(R1_END, 2), "R2", round(R2_T0, 2), round(R2_END, 2), flush=True)
    if mode == "frames":
        (WORK / "test").mkdir(exist_ok=True)
        for tt in [float(x) for x in sys.argv[3].split(",")]:
            v.frame(tt).save(WORK / "test" / f"fr_{tt:05.2f}.jpg", quality=90)
    else:
        sfx = [(0.02, "pop"), (t_kural - 0.1, "whoosh"), (t_yazi - 0.1, "pop"), (t_yazi + 0.45, "pop"),
               (t_sadece + 0.35, "ding"), (t_once - 0.05, "whoosh"), (t_simdi - 0.05, "whoosh"), (t_basla - 0.05, "pop"),
               (R2_END + 0.4, "whoosh"), (R2_END + 0.5, "ding"), (t_cunku - 0.1, "whoosh"), (t_cunku + 0.35, "whoosh"),
               (t_rengi + 0.05, "pop"), (t_buna - 0.1, "whoosh"), (t_buna + 0.1, "ding"), (t_kac - 0.1, "whoosh"),
               (t_kac + 0.2, "pop"), (t_kac + 0.38, "pop"), (t_kac + 0.56, "pop"), (t_yorum - 0.08, "pop"),
               (t_daha - 0.1, "pop")]
        at.sfx(str(WORK / "sfx.wav"), TOTAL, sfx)
        synth_extra(WORK / "sfx.wav")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-stream_loop", "2", "-i", str(WORK / "muzik.wav"), "-af",
                        f"atrim=0:{TOTAL:.3f},afade=t=in:d=0.15,afade=t=out:st={TOTAL - 0.6:.3f}:d=0.6",
                        "-ar", "44100", "-ac", "1", str(WORK / "music.wav")], check=True)
        at.final_mix(str(VOICE), str(WORK / "music.wav"), str(WORK / "sfx.wav"), str(WORK / "mix.m4a"))
        v.render(str(WORK / "mix.m4a"), str(WORK / "video.mp4"))
        print("render bitti", TOTAL, flush=True)
