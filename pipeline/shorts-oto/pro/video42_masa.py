"""42. video (2K, ~33 sn): Bu iki masa aynı boyda — Shepard masaları illüzyonu.
Kullanım: python3 video42_masa.py <WORK> [frames t1,t2,... | ses | render]"""
import os
os.environ.setdefault("PA_SCALE", str(4 / 3))
import json, math, subprocess, sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from engine import *  # noqa
from pa_ui import put_word, panel, txt, pop, captions
import audio_tools as at
from abi_yuz import konusma
from rozet import Rozet

WORK = Path(sys.argv[1])
VOICE = WORK / "voice_cut.wav"
words = json.loads((WORK / "words.json").read_text(encoding="utf-8"))
TOTAL = round(at.duration(str(VOICE)) + 0.35, 3)


def _hits(key):
    k = trl(clean(key)).strip('"!?;,.…')
    return [w for w in words if trl(clean(w["w"])).strip('"!?;,.…') == k]


def T(key, nth=0):
    return _hits(key)[nth]["s"]


t_inan, t_sol, t_sag, t_simdi, t_kald = T("İnanmadın"), T("Soldaki"), T("sağdaki"), T("Şimdi"), T("kaldırıp")
t_don, t_ve, t_bir, t_cunku, t_uzaga = T("döndürelim"), T("Ve", 2), T("birebir"), T("Çünkü"), T("Uzağa")
t_sani, t_bu, t_roger, t_sen, t_yorum, t_daha = T("sanıyor"), T("Bu", 2), T("Roger"), T("Sen"), T("Yorumlara"), T("Daha", 2)
S2, S3, S4, S5 = t_simdi - 0.1, t_cunku - 0.1, t_bu - 0.1, t_sen - 0.1
CUTS = [S2, S3, S4, S5]

GOLD = (255, 204, 70)
INKC = (14, 16, 30)
GRN = (52, 200, 110)
RED = (255, 84, 89)


def sm(x):
    return eio(clamp(x))


def ramp(t, a, b):
    return sm((t - a) / max(1e-6, b - a))


def wnd(t, a, b, fi=0.2, fo=0.2):
    return ramp(t, a, a + fi) * (1 - ramp(t, b - fo, b))


# ---------------- masalar ----------------
SS = 2  # süper örnekleme
LP, SP = u(440), u(190)
E1 = np.array([math.cos(math.radians(-62)), math.sin(math.radians(-62))]) * LP   # uzun kenar (uzağa)
E2 = np.array([math.cos(math.radians(20)), math.sin(math.radians(20))]) * SP     # kısa kenar


def rot(v, deg):
    a = math.radians(deg)
    return np.array([v[0] * math.cos(a) - v[1] * math.sin(a), v[0] * math.sin(a) + v[1] * math.cos(a)])


CA = np.array([u(300), u(860)])
CB = np.array([u(790), u(905)])
TH, LEG = u(26), u(250)


def quad(c, e1, e2):
    return [c - e1 / 2 - e2 / 2, c + e1 / 2 - e2 / 2, c + e1 / 2 + e2 / 2, c - e1 / 2 + e2 / 2]


TOPA = quad(CA, E1, E2)
TOPB = quad(CB, rot(E1, 90), rot(E2, 90))
WOOD, SIDE, LEGC = (206, 146, 92), (138, 88, 50), (92, 58, 34)


def draw_table(d, top, k):
    P = [p * k for p in top]
    c = sum(P) / 4
    th, lg = TH * k, LEG * k
    # bacaklar (önce)
    for p in sorted(P, key=lambda q: q[1]):
        q = p + (c - p) * 0.1
        d.line([tuple(q + (0, th * 0.5)), tuple(q + (0, th + lg))], fill=LEGC, width=int(u(24) * k))
        d.line([tuple(q + (-u(4) * k, th)), tuple(q + (-u(4) * k, th + lg))], fill=(118, 76, 44), width=int(u(8) * k))
    # yan yüzler: aşağı bakan kenarlar
    n = len(P)
    area = sum(P[i][0] * P[(i + 1) % n][1] - P[(i + 1) % n][0] * P[i][1] for i in range(n))
    for i in range(n):
        a, b = P[i], P[(i + 1) % n]
        e = b - a
        nrm = np.array([e[1], -e[0]]) * (1 if area > 0 else -1)
        if nrm[1] > 0:
            shade = 0.75 + 0.25 * abs(nrm[0]) / (np.linalg.norm(nrm) + 1e-6)
            d.polygon([tuple(a), tuple(b), tuple(b + (0, th)), tuple(a + (0, th))], fill=tuple(int(v * shade) for v in SIDE))
    d.polygon([tuple(p) for p in P], fill=WOOD)
    # ahşap damar çizgileri (uzun kenara paralel)
    e1 = P[1] - P[0]
    e2 = P[3] - P[0]
    if np.linalg.norm(e1) < np.linalg.norm(e2):
        e1, e2 = e2, e1
        base = P[0]
    else:
        base = P[0]
    for f in np.linspace(0.12, 0.88, 7):
        a0 = base + e2 * f + e1 * 0.04
        d.line([tuple(a0), tuple(a0 + e1 * 0.92)], fill=(192, 134, 82), width=max(1, int(u(3) * k)))


def make_static():
    YY, XX = np.mgrid[0:H, 0:W].astype(np.float32)
    g = (YY / H)[..., None]
    bg = (np.array([22, 26, 44], np.float32) * (1 - g) + np.array([10, 12, 22], np.float32) * g)
    r = np.sqrt((XX - W / 2) ** 2 + (YY - H * 0.45) ** 2) / H
    bg = bg + (40 * np.clip(0.55 - r, 0, 1))[..., None] * np.array([1.0, 0.9, 0.7])
    # zemin gölgeleri
    sh = Image.new("L", (W, H), 0)
    ds = ImageDraw.Draw(sh)
    for top in (TOPA, TOPB):
        c = sum(top) / 4
        ds.ellipse([c[0] - u(250), c[1] + LEG + u(5), c[0] + u(250), c[1] + LEG + u(85)], fill=120)
    sh = np.asarray(sh.filter(ImageFilter.GaussianBlur(u(30))), np.float32)[..., None] / 255
    bg = bg * (1 - 0.6 * sh)
    im = Image.fromarray(np.clip(bg, 0, 255).astype(np.uint8), "RGB").convert("RGBA")
    big = Image.new("RGBA", (W * SS, H * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(big)
    draw_table(d, TOPA, SS)
    draw_table(d, TOPB, SS)
    im.alpha_composite(big.resize((W, H), Image.LANCZOS))
    return im


STATIC = make_static()


def poly_layer(pts, fill, line, lw, alpha):
    lay = Image.new("RGBA", (W * SS, H * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    P = [tuple(p * SS) for p in pts]
    if fill:
        d.polygon(P, fill=fill[:3] + (int(fill[3] * alpha),))
    d.line(P + [P[0]], fill=line + (int(255 * alpha),), width=int(lw * SS), joint="curve")
    return lay.resize((W, H), Image.LANCZOS)


def ghost(t):
    """B'nin üst yüzünün kopyası: kalk, dön, A'nın üstüne otur."""
    if t < t_kald - 0.15 or t > t_uzaga + 0.2:
        return None
    lift = ramp(t, t_kald - 0.15, t_kald + 0.35)
    mv = ramp(t, t_don - 0.05, t_bir - 0.15)
    ang = -90 * mv
    c = CB + (CA - CB) * mv + np.array([0, -u(80)]) * lift * (1 - mv)
    pts = [c + rot(p - CB, ang) for p in TOPB]
    land = ramp(t, t_bir - 0.2, t_bir + 0.05)
    col = tuple(int(GOLD[i] + (GRN[i] - GOLD[i]) * land) for i in range(3))
    a = 1 - ramp(t, t_uzaga - 0.25, t_uzaga + 0.2)
    return poly_layer(pts, (255, 214, 120, 150), col, u(9), a)


def arrow(L, p0, p1, col, a, w=u(12)):
    lay = Image.new("RGBA", (W * SS, H * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    p0, p1 = np.array(p0) * SS, np.array(p1) * SS
    v = p1 - p0
    n = v / (np.linalg.norm(v) + 1e-6)
    hl = u(48) * SS
    q = p1 - n * hl
    pr = np.array([-n[1], n[0]])
    d.line([tuple(p0), tuple(q)], fill=col + (int(255 * a),), width=int(w * SS))
    d.polygon([tuple(p1), tuple(q + pr * hl * 0.55), tuple(q - pr * hl * 0.55)], fill=col + (int(255 * a),))
    L.alpha_composite(lay.resize((W, H), Image.LANCZOS))


ROZ = Rozet()
OPN, RND = konusma(VOICE, FPS)


def edge_pts(top, long=True):
    e01 = np.linalg.norm(top[1] - top[0])
    e03 = np.linalg.norm(top[3] - top[0])
    if (e01 > e03) == long:
        return top[0], top[1]
    return top[0], top[3]


def ui(L, t):
    # --- kanca ---
    if t < S2:
        a = 1 - ramp(t, S2 - 0.2, S2)
        p = 1 + 0.1 * (1 - pop(t, 0.0, 0.28))
        put_word(L, "BU İKİ MASA", WHITE, 540, 160, round(88 * p), alpha=a, glow=0.3)
        put_word(L, "AYNI BOYDA!", GOLD, 540, 285, round(120 * p), alpha=a, glow=0.45)
        if t >= t_sol - 0.1:
            chip(L, 300, 1395, "Uzun ve ince?", bg=WHITE, fg=INKC, size=42, k="black", alpha=a, scale=pop(t, t_sol - 0.1, 0.3))
        if t >= t_sag - 0.1:
            chip(L, 790, 1395, "Kısa ve geniş?", bg=WHITE, fg=INKC, size=42, k="black", alpha=a, scale=pop(t, t_sag - 0.1, 0.3))
    # --- kanıt ---
    elif t < S3:
        a = wnd(t, S2, S3 + 0.05)
        if t < t_bir - 0.15:
            q = pop(t, S2, 0.3)
            put_word(L, "SAĞDAKİNİN ÜSTÜNÜ", WHITE, 540, 160, max(8, round(76 * q)), alpha=a if q > 0.02 else 0, glow=0.3)
            put_word(L, "DÖNDÜRELİM", GOLD, 540, 280, max(8, round(110 * q)), alpha=a if q > 0.02 else 0, glow=0.45)
        else:
            q = pop(t, t_bir - 0.15, 0.32)
            put_icon(L, "check_mark_button", 540, 140, 130 * q, alpha=a)
            put_word(L, "BİREBİR AYNI!", GRN, 540, 280, max(8, round(116 * q)), alpha=a if q > 0.02 else 0, glow=0.5)
    # --- açıklama ---
    elif t < S4:
        a = wnd(t, S3, S4 + 0.05)
        q = pop(t, S3, 0.3)
        put_word(L, "BEYİN RESMİ", WHITE, 540, 160, max(8, round(86 * q)), alpha=a if q > 0.02 else 0, glow=0.3)
        put_word(L, "3 BOYUTLU GÖRÜR", GOLD, 540, 280, max(8, round(96 * q)), alpha=a if q > 0.02 else 0, glow=0.45)
        if t >= t_uzaga - 0.1:
            k = ramp(t, t_uzaga - 0.1, t_uzaga + 0.5)
            p0, p1 = edge_pts(TOPA, True)
            if p0[1] < p1[1]:
                p0, p1 = p1, p0
            off = np.array([-u(40), -u(12)])
            arrow(L, p0 + off, p0 + off + (p1 - p0) * k, GOLD, a)
            chip(L, 300, 1395, "Uzağa gidiyor → uzun sanılır", bg=GOLD, fg=INKC, size=36, k="black", alpha=a,
                 scale=pop(t, t_uzaga - 0.1, 0.3))
        if t >= t_sani - 0.1:
            p0, p1 = edge_pts(TOPB, True)
            if p0[0] > p1[0]:
                p0, p1 = p1, p0
            k = ramp(t, t_sani - 0.1, t_sani + 0.4)
            off = np.array([0, u(70)])
            arrow(L, p0 + off, p0 + off + (p1 - p0) * k, WHITE, a, w=u(10))
            chip(L, 790, 1490, "Yana uzanıyor → kısa sanılır", bg=WHITE, fg=INKC, size=34, k="black", alpha=a,
                 scale=pop(t, t_sani - 0.1, 0.3))
    # --- Shepard ---
    elif t < S5:
        a = wnd(t, S4, S5 + 0.05)
        q = pop(t, S4, 0.35)
        panel(L, 540, 225, 840, 250, scale=q, alpha=a, r=40)
        put_word(L, "SHEPARD MASALARI", GOLD, 540, 195, max(8, round(78 * q)), alpha=a, glow=0.45)
        txt(L, (540, 285), "Psikolog Roger Shepard, 1990", round(38 * q), WHITE, a, k="xb")
    elif t < t_daha - 0.1:
        a = wnd(t, S5, t_daha, 0.2, 0.15)
        q = pop(t, S5, 0.35)
        txt(L, (540, 160), "SANA HANGİSİ", round(78 * q), WHITE, a, stroke=7)
        txt(L, (540, 270), "UZUN GÖRÜNDÜ?", round(100 * q), GOLD, a, stroke=7)
        if t >= t_yorum - 0.08:
            chip(L, 540, 1395, "Yorumlara yaz", bg=INKC, fg=WHITE, size=56, icon_name="speech_balloon", k="black", alpha=a,
                 scale=pop(t, t_yorum - 0.08, 0.35))
    else:
        S9 = t_daha - 0.1
        a = ramp(t, S9, S9 + 0.25)
        txt(L, (540, 170), "Daha fazlası için", 64, WHITE, a, stroke=6)
        pulse = 1 + 0.045 * math.sin((t - S9) * 8) * ramp(t, S9 + 0.4, S9 + 0.7)
        chip(L, 540, 300, "TAKİP ET", bg=INKC, fg=WHITE, size=90, icon_name="bell", k="black", scale=pop(t, S9, 0.4) * pulse)


def cam(im, t):
    z = 1.0 + 0.035 * ramp(t, 0, S2) - 0.035 * ramp(t, S2, S2 + 0.4) + 0.03 * ramp(t, S3, S4)
    if abs(z - 1) < 0.002:
        return im
    a = np.asarray(im)
    cx, cy = W / 2, u(900)
    M = np.float32([[z, 0, cx - cx * z], [0, z, cy - cy * z]])
    return Image.fromarray(cv2.warpAffine(a, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE), "RGBA")


class Vid(Video):
    def frame(self, t):
        im = STATIC.copy()
        g = ghost(t)
        if g is not None:
            im.alpha_composite(g)
        im = cam(im, t)
        for c in CUTS:
            if 0 <= t - c < 0.12:
                arr = np.asarray(im).astype(np.float32)
                arr[..., :3] += 90 * (1 - (t - c) / 0.12)
                im = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGBA")
        L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ui(L, t)
        im.alpha_composite(L)
        brand(im, 540, 62, size=34)
        C = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        captions(C, self.groups, t, y=1660)
        im.alpha_composite(C)
        i = min(len(OPN) - 1, int(t * FPS))
        ROZ.draw(im, t, float(OPN[i]))
        return im.convert("RGB")


VID = Vid([{"start": 0, "end": TOTAL, "draw": lambda *a: None}], words, "", TOTAL, bg=None)


def make_audio():
    ev = [(c, "whoosh") for c in CUTS] + [(t_sol - 0.1, "pop"), (t_sag - 0.1, "pop"), (t_kald - 0.15, "whoosh"),
                                          (t_don - 0.05, "whoosh"), (t_bir - 0.15, "ding"), (t_uzaga - 0.1, "pop"),
                                          (t_sani - 0.1, "pop"), (t_yorum - 0.08, "pop"), (t_daha - 0.1, "pop")]
    at.sfx(str(WORK / "sfx.wav"), TOTAL, ev)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-stream_loop", "2", "-i", str(WORK / "muzik.wav"), "-af",
                    f"atrim=0:{TOTAL:.3f},afade=t=in:d=0.15,afade=t=out:st={TOTAL - 0.6:.3f}:d=0.6",
                    "-ar", "44100", "-ac", "1", str(WORK / "music.wav")], check=True)
    at.final_mix(str(VOICE), str(WORK / "music.wav"), str(WORK / "sfx.wav"), str(WORK / "mix.m4a"))


if __name__ == "__main__":
    mode = sys.argv[2] if len(sys.argv) > 2 else "render"
    print("TOTAL", TOTAL, "cuts", [round(c, 2) for c in CUTS], flush=True)
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
