"""30. video (2K, ~32 sn): 29 Ekim testi – 3 soru, 3 saniye.
Görseller: Unsplash (bayrak yakın aS05L_TBF5Y, bayrak gökyüzü Zmt6S1VqZug, Anıtkabir hv7CpZwabYM).
Kullanım: python3 video30_29ekim.py <WORK> [frames t1,t2,...]"""
import os
os.environ.setdefault("PA_SCALE", str(4 / 3))
import json, math, subprocess, sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from engine import *  # noqa
from engine import _put_icon_px
from pa_ui import put_word, panel, txt, pop, captions
import audio_tools as at
from abi_yuz import konusma
from rozet import Rozet

WORK = Path(sys.argv[1])
VOICE = WORK / "voice_cut.wav"
words = json.loads((WORK / "words.json").read_text(encoding="utf-8"))
P = json.loads((WORK / "marks.json").read_text())["piece_ends"]
TOTAL = round(at.duration(str(VOICE)) + 0.35, 3)


def _hits(key):
    k = trl(clean(key)).strip('"!?;,.…')
    return [w for w in words if trl(clean(w["w"])).strip('"!?;,.…') == k]


def T(key, nth=0):
    return _hits(key)[nth]["s"]


t_uc = T("Üç")
t_q = [T("Birinci"), T("İkinci"), T("Üçüncü")]
t_cd = [P[1], P[3], P[5]]                     # geri sayım başlar
t_ans = [T("akşam"), T("yüz"), T("yüz", 1)]     # cevap
t_kac, t_yorum, t_cum, t_daha = T("Kaç", 2), T("Yorumlara"), T("Cumhuriyetimizin"), T("Daha")

GOLD = (255, 204, 70)
RED = (227, 10, 23)
INKC = (14, 16, 30)
GRN = (46, 200, 110)

SORU = [("Cumhuriyet saat", "kaçta ilan edildi?", ["09.00", "14.30", "20.30"], 2),
        ("Atatürk kaç oyla", "cumhurbaşkanı seçildi?", ["120", "158", "200"], 1),
        ("O gece kaç pare", "top atıldı?", ["21", "81", "101"], 2)]
NOT = ["29 Ekim 1923 akşamı", "158 vekilin tamamı", "Gece yarısından sonra"]


def sm(x):
    return eio(clamp(x))


def ramp(t, a, b):
    return sm((t - a) / max(1e-6, b - a))


def wnd(t, a, b, fi=0.25, fo=0.25):
    return ramp(t, a, a + fi) * (1 - ramp(t, b - fo, b))


# ---------------- arka planlar ----------------
FOTO = WORK / "foto"


def _load(name, w):
    im = Image.open(FOTO / name).convert("RGB")
    s = w / im.width
    return np.asarray(im.resize((w, round(im.height * s)), Image.LANCZOS), np.float32)


BG_FLAG = _load("bayrak_yakin.jpg", round(W * 1.18))
BG_SKY = _load("bayrak_gok.jpg", round(W * 1.25))
BG_ANIT = _load("anitkabir.jpg", round(W * 1.15))
_yy, _xx = np.mgrid[0:H, 0:W].astype(np.float32)


def view(img, z, cx, cy):
    """img'den W×H kesit: z yakınlaşma, (cx, cy) 0..1 merkez"""
    h, w = img.shape[:2]
    s = z * W / w * (w / W)            # img zaten ~W genişliğinde ölçekli
    cw, ch = W / z * (w / (w)), H / z
    M = np.float32([[z, 0, W / 2 - cx * w * z], [0, z, H / 2 - cy * h * z]])
    return cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


def flag_wave(t):
    """yakın bayrak: kumaş dalgası (yer değiştirme + gölge)"""
    h, w = BG_FLAG.shape[:2]
    z = 1.0 + 0.04 * t
    ph = _xx * 0.0042 + _yy * 0.0016 - t * 2.4
    dx = 14 * np.sin(ph)
    dy = 9 * np.sin(ph * 0.8 + 1.3)
    sx = (_xx - W / 2) / z + w / 2 + dx
    sy = (_yy - H / 2) / z + h * 0.42 + dy
    im = cv2.remap(BG_FLAG, sx.astype(np.float32), sy.astype(np.float32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    shade = 1 + 0.16 * np.cos(ph)[..., None]
    return im * shade


def sky_bg(t):
    q = clamp((t - t_q[0]) / 22)
    im = view(BG_SKY, 1.0 + 0.06 * q, 0.5 - 0.03 * q, 0.40)
    return im


def anit_bg(t):
    q = clamp((t - t_cum) / 6)
    return view(BG_ANIT, 1.0 + 0.07 * q, 0.55, 0.52)


YY = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
VIG = ((1 - 0.55 * np.clip((0.32 - YY) / 0.32, 0, 1)) * (1 - 0.6 * np.clip((YY - 0.66) / 0.34, 0, 1)))


# ---------------- havai fişek ----------------
def _bursts():
    rng = np.random.default_rng(1923)
    out = []
    for k, (t0, x, y, col) in enumerate([(t_ans[2] + 0.05, 300, 520, (255, 70, 70)), (t_ans[2] + 0.35, 800, 420, (255, 255, 255)),
                                         (t_cum - 0.05, 540, 360, GOLD), (t_cum + 0.4, 250, 560, (255, 70, 70)),
                                         (t_cum + 0.8, 840, 500, (255, 255, 255)), (t_cum + 1.3, 420, 300, GOLD),
                                         (t_cum + 1.8, 720, 620, (255, 70, 70)), (t_daha + 0.2, 300, 380, GOLD),
                                         (t_daha + 0.9, 800, 330, (255, 255, 255)), (t_daha + 1.6, 540, 520, (255, 70, 70))]):
        n = 70
        ang = rng.uniform(0, 2 * math.pi, n)
        sp = rng.uniform(260, 520, n)
        out.append((t0, x, y, col, ang, sp))
    return out


BURSTS = _bursts()


def fireworks(L, t):
    lay = Image.new("RGBA", L.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    any_ = False
    for t0, x, y, col, ang, sp in BURSTS:
        q = t - t0
        if not (0 <= q < 1.6):
            continue
        any_ = True
        a = (1 - q / 1.6) ** 1.5
        for an, v in zip(ang, sp):
            def pos(tt):
                r = v * (1 - math.exp(-tt * 2.6)) / 2.6
                return x + math.cos(an) * r, y + math.sin(an) * r + 120 * tt * tt
            p1, p0 = pos(q), pos(max(0, q - 0.12))
            d.line([(u(p0[0]), u(p0[1])), (u(p1[0]), u(p1[1]))], fill=col + (int(220 * a),), width=round(u(4)))
            d.ellipse([u(p1[0]) - u(4), u(p1[1]) - u(4), u(p1[0]) + u(4), u(p1[1]) + u(4)], fill=(255, 255, 230, int(255 * a)))
        if q < 0.15:
            r = u(60 * (q / 0.15))
            d.ellipse([u(x) - r, u(y) - r, u(x) + r, u(y) + r], fill=(255, 255, 240, int(160 * (1 - q / 0.15))))
    if any_:
        g = lay.filter(ImageFilter.GaussianBlur(u(7)))
        L.alpha_composite(g)
        L.alpha_composite(lay)


# ---------------- UI ----------------
def opt_bar(L, cy, letter, val, a, sc, state):
    """state: 0 normal, 1 doğru, 2 yanlış (soluk)"""
    if a <= 0.01 or sc <= 0.02:
        return
    w, h = 780, 136
    M = round(u(30))
    im = Image.new("RGBA", (round(u(w)) + 2 * M, round(u(h)) + 2 * M), (0, 0, 0, 0))
    sh, pad = soft_shadow(round(u(w)), round(u(h)), round(u(h / 2)), blur=round(u(16)), op=0.45)
    comp(im, sh, M - pad, M - pad + u(8))
    d = ImageDraw.Draw(im)
    fill = (46, 200, 110, 245) if state == 1 else (16, 20, 40, 225)
    out = (120, 255, 170, 255) if state == 1 else (255, 255, 255, 70)
    d.rounded_rectangle([M, M, M + round(u(w)), M + round(u(h))], radius=round(u(h / 2)), fill=fill, outline=out, width=round(u(4)))
    r = u(46)
    cx0, cy0 = M + u(76), M + u(h / 2)
    d.ellipse([cx0 - r, cy0 - r, cx0 + r, cy0 + r], fill=(255, 255, 255, 255) if state == 1 else RED + (255,))
    d.text((cx0, cy0), letter, font=font("black", round(u(52))), fill=(46, 160, 90) if state == 1 else (255, 255, 255), anchor="mm")
    d.text((M + u(w / 2 + 40), cy0), val, font=font("black", round(u(74))), fill=(255, 255, 255), anchor="mm")
    if state == 1:
        _put_icon_px(im, "check_mark_button", M + u(w - 76), cy0, u(84), shadow=False)
    if abs(sc - 1) > 0.01:
        im = im.resize((max(1, round(im.width * sc)), max(1, round(im.height * sc))), Image.BICUBIC)
    alpha = a * (0.32 if state == 2 else 1.0)
    comp(L, set_alpha(im, alpha), u(540) - im.width / 2, u(cy) - im.height / 2)


def ring(L, cx, cy, R, q, n, a):
    if a <= 0.01:
        return
    lay = Image.new("RGBA", L.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    box = [u(cx - R), u(cy - R), u(cx + R), u(cy + R)]
    d.ellipse(box, fill=(12, 14, 28, int(200 * a)))
    d.arc(box, 0, 360, fill=(255, 255, 255, int(60 * a)), width=round(u(12)))
    d.arc(box, -90, -90 + 360 * q, fill=GOLD + (int(255 * a),), width=round(u(12)))
    d.text((u(cx), u(cy)), str(n), font=font("black", round(u(R * 1.15))), fill=(255, 255, 255, int(255 * a)), anchor="mm")
    L.alpha_composite(lay)


def quiz(L, t, i):
    q0 = t_q[i]
    end = t_q[i + 1] - 0.05 if i < 2 else t_kac - 0.05
    if not (q0 - 0.1 <= t < end + 0.3):
        return
    a = wnd(t, q0 - 0.1, end + 0.3, 0.25, 0.3)
    l1, l2, ops, ok = SORU[i]
    chip(L, 540, 300, f"SORU {i + 1}/3", bg=RED, fg=WHITE, size=46, k="black", alpha=a, scale=pop(t, q0 - 0.1, 0.3))
    p = pop(t, q0, 0.35)
    panel(L, 540, 520, 940, 260, scale=p, alpha=a * 0.95, r=48)
    txt(L, (540, 470), l1, round(70 * p), WHITE, a, stroke=0)
    txt(L, (540, 565), l2, round(70 * p), GOLD, a, stroke=0)
    rev = t >= t_ans[i] - 0.05
    for k, (L_, v) in enumerate(zip("ABC", ops)):
        ts = q0 + 0.5 + 0.18 * k
        st = 0
        sc = pop(t, ts, 0.3)
        if rev:
            st = 1 if k == ok else 2
            if k == ok:
                sc *= 1 + 0.08 * (1 - ramp(t, t_ans[i] - 0.05, t_ans[i] + 0.35))
        opt_bar(L, 790 + 170 * k, L_, v, a, sc, st)
    # geri sayım
    if t_cd[i] - 0.05 <= t < t_ans[i] + 0.1:
        dur = t_ans[i] - t_cd[i]
        e = clamp((t - t_cd[i]) / dur)
        n = max(1, 3 - int(e * 3))
        ra = wnd(t, t_cd[i] - 0.05, t_ans[i] + 0.1, 0.15, 0.15)
        ring(L, 540, 1330, 92 * (1 + 0.06 * math.sin((e * 3 % 1) * math.pi)), 1 - e, n, ra)
    if rev:
        b = ramp(t, t_ans[i] + 0.1, t_ans[i] + 0.4)
        txt(L, (540, 1330), NOT[i], 46, (255, 255, 255), b * a, k="xb", stroke=5)


def hook(L, t):
    if t >= t_q[0] + 0.1:
        return
    a = 1 - ramp(t, t_q[0] - 0.25, t_q[0] + 0.05)
    p = 1 + 0.1 * (1 - pop(t, 0.0, 0.3))
    put_word(L, "29 EKİM", WHITE, 540, 330, round(150 * p), alpha=a, glow=0.3)
    put_word(L, "TESTİ", GOLD, 540, 480, round(150 * p), alpha=a, glow=0.35)
    if t >= t_uc - 0.08:
        chip(L, 540, 1250, "3 SORU  •  3 SANİYE", bg=WHITE, fg=INKC, size=58, icon_name="stopwatch", k="black", alpha=a,
             scale=pop(t, t_uc - 0.08, 0.35))


def skor(L, t):
    if not (t_kac - 0.1 <= t < t_cum + 0.1):
        return
    a = wnd(t, t_kac - 0.1, t_cum + 0.1, 0.25, 0.25)
    txt(L, (540, 360), "KAÇ TANESİNİ", round(92 * pop(t, t_kac - 0.1, 0.32)), WHITE, a, stroke=7)
    txt(L, (540, 480), "BİLDİN?", round(120 * pop(t, t_kac - 0.1, 0.32)), GOLD, a, stroke=7)
    for k, s in enumerate(["0/3", "1/3", "2/3", "3/3"]):
        chip(L, 160 + 253 * k, 760, s, bg=WHITE if k < 3 else GOLD, fg=INKC, size=60, k="black", alpha=a,
             scale=pop(t, t_kac + 0.25 + 0.12 * k, 0.3))
    if t >= t_yorum - 0.08:
        chip(L, 540, 960, "Yorumlara yaz", bg=INKC, fg=WHITE, size=56, icon_name="speech_balloon", k="black", alpha=a,
             scale=pop(t, t_yorum - 0.08, 0.35))


def final(L, t):
    if t < t_cum - 0.1:
        return
    if t < t_daha - 0.1:
        a = 1 - ramp(t, t_daha - 0.25, t_daha - 0.05)
        q = pop(t, t_cum - 0.1, 0.4)
        txt(L, (540, 300), "CUMHURİYETİMİZİN", round(80 * q), WHITE, a, stroke=7)
        put_word(L, "103. YILI", GOLD, 540, 440, round(150 * q), alpha=a, glow=0.45)
        txt(L, (540, 590), "KUTLU OLSUN", round(96 * q), WHITE, a, stroke=7)
        b = ramp(t, t_cum + 0.6, t_cum + 1.0) * a
        chip(L, 540, 1250, "29 EKİM 1923", bg=RED, fg=WHITE, size=54, k="black", alpha=b, scale=pop(t, t_cum + 0.6, 0.35))
    else:
        a = ramp(t, t_daha - 0.1, t_daha + 0.15)
        txt(L, (540, 560), "Daha fazlası için", 64, WHITE, a, stroke=6)
        pulse = 1 + 0.045 * math.sin((t - t_daha) * 8) * ramp(t, t_daha + 0.4, t_daha + 0.7)
        chip(L, 540, 720, "TAKİP ET", bg=INKC, fg=WHITE, size=90, icon_name="bell", k="black",
             scale=pop(t, t_daha - 0.1, 0.4) * pulse)


ROZ = Rozet()
OPN, RND = konusma(VOICE, FPS)


class Vid(Video):
    def frame(self, t):
        T1, T2 = t_q[0] - 0.15, t_cum - 0.15
        if t < T1 + 0.3:
            bg = flag_wave(t)
            if t > T1:
                k = ramp(t, T1, T1 + 0.3)
                bg = bg * (1 - k) + sky_bg(t) * 0.55 * k
        elif t < T2 + 0.35:
            bg = sky_bg(t) * 0.55
            bg = cv2.GaussianBlur(bg, (0, 0), u(3))
            if t > T2:
                k = ramp(t, T2, T2 + 0.35)
                bg = bg * (1 - k) + anit_bg(t) * 0.78 * k
        else:
            bg = anit_bg(t) * 0.78
        # geçiş flaşı
        for tc in (T1, T2):
            if 0 <= t - tc < 0.2:
                bg = bg + 140 * (1 - (t - tc) / 0.2)
        bg = bg * VIG
        im = Image.fromarray(np.clip(bg, 0, 255).astype(np.uint8), "RGB").convert("RGBA")
        L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        fireworks(L, t)
        hook(L, t)
        for i in range(3):
            quiz(L, t, i)
        skor(L, t)
        final(L, t)
        im.alpha_composite(L)
        brand(im, 540, 62, size=34)
        C = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        captions(C, self.groups, t)
        im.alpha_composite(C)
        i = min(len(OPN) - 1, int(t * FPS))
        ROZ.draw(im, t, float(OPN[i]))
        return im.convert("RGB")


def _rd(path):
    return np.frombuffer(subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(path), "-f", "f32le", "-ac", "1", "-ar",
                                         "44100", "-"], capture_output=True, check=True).stdout, np.float32).copy()


def extra_fx(path):
    SR = 44100
    y = _rd(path)
    def add(t0, s):
        i = int(t0 * SR)
        if 0 <= i and i + len(s) < len(y):
            y[i:i + len(s)] += s
    tt = np.arange(int(0.05 * SR)) / SR
    tick = np.sin(2 * np.pi * 1700 * tt) * np.exp(-tt * 90) * 0.25
    for i in range(3):
        dur = t_ans[i] - t_cd[i]
        for k in range(3):
            add(t_cd[i] + k * dur / 3, tick)
    tb = np.arange(int(0.7 * SR)) / SR
    rng = np.random.default_rng(3)
    boom = (np.sin(2 * np.pi * (55 * np.exp(-tb * 3)) * tb * 6) * 0.6 + rng.standard_normal(len(tb)) * 0.25) * np.exp(-tb * 6)
    for t0, *_ in BURSTS:
        add(t0, boom * 0.35)
    at._write(str(path), y)


if __name__ == "__main__":
    mode = sys.argv[2] if len(sys.argv) > 2 else "render"
    v = Vid([{"start": 0, "end": TOTAL, "draw": lambda *a: None}], words, "", TOTAL, bg=None)
    print("TOTAL", TOTAL, "q", t_q, "cd", t_cd, "ans", t_ans, flush=True)
    if mode == "frames":
        (WORK / "test").mkdir(exist_ok=True)
        for tt in [float(x) for x in sys.argv[3].split(",")]:
            v.frame(tt).save(WORK / "test" / f"fr_{tt:05.2f}.jpg", quality=90)
    else:
        sfx = [(0.02, "whoosh"), (t_uc - 0.08, "pop"), (t_q[0] - 0.15, "whoosh")]
        for i in range(3):
            sfx += [(t_q[i] + 0.5, "pop"), (t_q[i] + 0.68, "pop"), (t_q[i] + 0.86, "pop"), (t_ans[i] - 0.05, "ding")]
        sfx += [(t_kac - 0.1, "whoosh"), (t_yorum - 0.08, "pop"), (t_cum - 0.15, "whoosh"), (t_daha - 0.1, "pop")]
        at.sfx(str(WORK / "sfx.wav"), TOTAL, sfx)
        extra_fx(WORK / "sfx.wav")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-stream_loop", "2", "-i", str(WORK / "muzik.wav"), "-af",
                        f"atrim=0:{TOTAL:.3f},afade=t=in:d=0.15,afade=t=out:st={TOTAL - 0.6:.3f}:d=0.6",
                        "-ar", "44100", "-ac", "1", str(WORK / "music.wav")], check=True)
        at.final_mix(str(VOICE), str(WORK / "music.wav"), str(WORK / "sfx.wav"), str(WORK / "mix.m4a"))
        v.render(str(WORK / "mix.m4a"), str(WORK / "video.mp4"))
        print("render bitti", TOTAL, flush=True)
