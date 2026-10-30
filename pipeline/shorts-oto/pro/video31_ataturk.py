"""31. video: 29 Ekim kutlaması – Atatürk'ün kendi sesiyle (10. Yıl Nutku, 1933, kamu malı).
Görüntüler: Wikimedia Commons kamu malı arşiv filmleri + Unsplash (bayrak, Anıtkabir).
Kullanım: python3 video31_ataturk.py <WORK> [frames t1,t2,...]"""
import os
os.environ.setdefault("PA_SCALE", str(4 / 3))
import json, math, subprocess, sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from engine import *  # noqa
from pa_ui import put_word, txt, pop
import audio_tools as at
import muzik_pad

WORK = Path(sys.argv[1])
VOICE = WORK / "voice_cut.wav"
TS = at.duration(str(VOICE))            # konuşma sonu
TOTAL = round(TS + 3.6, 3)
GOLD = (255, 204, 70)
RED = (227, 10, 23)
INKC = (14, 16, 30)

SUB = [([("Bugün,", 0.35), ("Cumhuriyetimizin", 1.4), ("onuncu", 4.1), ("yılını", 5.6), ("doldurduğu", 6.15), ("en", 7.15),
         ("büyük", 8.3), ("bayramdır.", 8.8)], 10.4),
       ([("Kutlu", 10.75), ("olsun!", 11.15)], 12.7),
       ([("Yurttaşlarım!", 12.95)], 14.65),
       ([("Az", 14.8), ("zamanda", 15.5), ("çok", 16.3), ("ve", 17.4), ("büyük", 17.85), ("işler", 18.15), ("yaptık.", 18.75)], 20.3),
       ([("Türk", 21.2), ("milleti", 21.95), ("çalışkandır.", 22.75)], 24.85),
       ([("Türk", 24.95), ("milleti", 25.3), ("zekidir.", 26.05)], 28.4)]
T_NM = [29.2, 29.6, 30.35, 31.2]            # Ne / mutlu / Türk'üm / diyene
V1, V2, V3, V4, V5 = 0.0, 12.75, 20.3, 28.35, TS + 0.15


def sm(x):
    return eio(clamp(x))


def ramp(t, a, b):
    return sm((t - a) / max(1e-6, b - a))


# ---------------- arşiv klipleri ----------------
def load_clip(name, crop):
    cap = cv2.VideoCapture(str(WORK / name))
    fr = []
    while True:
        ok, f = cap.read()
        if not ok:
            break
        h, w = f.shape[:2]
        x0, y0, x1, y1 = crop
        f = f[int(y0 * h):int(y1 * h), int(x0 * w):int(x1 * w)]
        g = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)
        fr.append(g)
    return fr


CLIPS = {"inonu": (load_clip("clip_inonu.mp4", (0.30, 0.22, 0.98, 1.0)), 0.0),
         "turhal": (load_clip("clip_Turhal.mp4", (0.12, 0.2, 0.88, 0.98)), 10.0),
         "ulku": (load_clip("clip_lk__ile.mp4", (0.22, 0.0, 0.86, 1.0)), 16.5)}
RNG = np.random.default_rng(29)
GRAIN = [RNG.normal(0, 1, (H // 2, W // 2)).astype(np.float32) for _ in range(8)]
YY, XX = np.mgrid[0:H, 0:W].astype(np.float32)
VIG = np.clip(1 - 0.55 * (((XX - W / 2) / (W * 0.62)) ** 2 + ((YY - H * 0.47) / (H * 0.55)) ** 2), 0.25, 1)[..., None]
SEPIA = np.array([1.0, 0.93, 0.80], np.float32)          # RGB çarpanı (hafif sıcak arşiv tonu)


def archive(key, t, t0):
    fr, off = CLIPS[key]
    i = int((off + (t - t0)) * 30) % len(fr)
    g = fr[i].astype(np.float32)
    g = (g - 20) * 1.12                      # kontrast
    h, w = g.shape
    # arka plan: bulanık, koyu, kırmızımsı
    s = max(W / w, H / h) * 1.1
    bg = cv2.resize(g, (int(w * s), int(h * s)), interpolation=cv2.INTER_LINEAR)
    bh, bw = bg.shape
    bg = bg[(bh - H) // 2:(bh - H) // 2 + H, (bw - W) // 2:(bw - W) // 2 + W]
    bg = cv2.GaussianBlur(bg, (0, 0), u(26))
    bg = np.dstack([bg * 0.42, bg * 0.16, bg * 0.15])
    # ön plan: tam genişlik film karesi, yavaş yakınlaşma
    z = 1.0 + 0.035 * (t - t0)
    fw = int(u(960))
    fh = int(fw * min(1.0, h / w * 1.0) if h / w > 0.8 else fw * h / w)
    fh = int(min(fh, u(980)))
    sc = max(fw / w, fh / h) * z
    fg = cv2.resize(g, (int(w * sc), int(h * sc)), interpolation=cv2.INTER_CUBIC)
    cy0 = (fg.shape[0] - fh) // 2
    cx0 = (fg.shape[1] - fw) // 2
    fg = fg[cy0:cy0 + fh, cx0:cx0 + fw]
    flick = 1 + 0.035 * math.sin(t * 23) + 0.02 * math.sin(t * 61)
    fg = np.clip(fg * flick, 0, 255)
    fg3 = fg[..., None] * SEPIA
    out = bg.copy()
    y0 = int(u(905) - fh / 2)
    x0 = int((W - fw) / 2)
    # gölge
    sh = np.zeros((H, W), np.float32)
    sh[y0 + int(u(10)):y0 + fh + int(u(16)), x0 + int(u(4)):x0 + fw + int(u(4))] = 1
    sh = cv2.GaussianBlur(sh, (0, 0), u(18))
    out *= (1 - 0.6 * sh)[..., None]
    out[y0:y0 + fh, x0:x0 + fw] = fg3
    # ince çerçeve
    cv2.rectangle(out, (x0 - 2, y0 - 2), (x0 + fw + 1, y0 + fh + 1), (235, 215, 170), max(2, int(u(3))))
    return out


def photo(name, wscale):
    im = Image.open(WORK / "foto" / name).convert("RGB")
    s = W * wscale / im.width
    return np.asarray(im.resize((round(W * wscale), round(im.height * s)), Image.LANCZOS), np.float32)


P_FLAG = photo("bayrak_gok.jpg", 1.25)
P_ANIT = photo("anitkabir.jpg", 1.15)


def view(img, z, cx, cy):
    h, w = img.shape[:2]
    M = np.float32([[z, 0, W / 2 - cx * w * z], [0, z, H / 2 - cy * h * z]])
    return cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


def grain(img, t, k=9):
    g = GRAIN[int(t * 30) % len(GRAIN)]
    g = cv2.resize(g, (W, H), interpolation=cv2.INTER_NEAREST)
    return img + g[..., None] * k


# ---------------- havai fişek ----------------
def _bursts():
    rng = np.random.default_rng(1923)
    out = []
    spec = [(T_NM[3] + 0.25, 300, 470, (255, 70, 70)), (T_NM[3] + 0.55, 800, 380, (255, 255, 255)),
            (V5 + 0.2, 540, 330, GOLD), (V5 + 0.6, 250, 520, (255, 70, 70)), (V5 + 1.0, 840, 460, (255, 255, 255)),
            (V5 + 1.5, 420, 280, GOLD), (V5 + 2.0, 720, 560, (255, 70, 70)), (V5 + 2.5, 300, 360, GOLD),
            (V5 + 2.9, 820, 300, (255, 255, 255))]
    for t0, x, y, col in spec:
        n = 80
        out.append((t0, x, y, col, rng.uniform(0, 2 * math.pi, n), rng.uniform(260, 540, n)))
    return out


BURSTS = _bursts()


def fireworks(L, t):
    lay = Image.new("RGBA", L.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    hit = False
    for t0, x, y, col, ang, sp in BURSTS:
        q = t - t0
        if not (0 <= q < 1.7):
            continue
        hit = True
        a = (1 - q / 1.7) ** 1.5
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
    if hit:
        L.alpha_composite(lay.filter(ImageFilter.GaussianBlur(u(7))))
        L.alpha_composite(lay)


# ---------------- yazılar ----------------
def subtitle(L, t):
    for wl, end in SUB:
        if wl[0][1] - 0.15 <= t < end:
            break
    else:
        return
    a = ramp(t, wl[0][1] - 0.15, wl[0][1] + 0.1) * (1 - ramp(t, end - 0.25, end))
    f = font("black", round(u(66)))
    d = ImageDraw.Draw(L)
    # satırlara böl (max ~16 karakter genişliği)
    lines, cur = [], []
    for w, ts in wl:
        test = " ".join(x for x, _ in cur + [(w, ts)])
        if d.textlength(test, font=f) > u(940) and cur:
            lines.append(cur)
            cur = []
        cur.append((w, ts))
    lines.append(cur)
    y = 1520 - (len(lines) - 1) * 42
    for ln in lines:
        tw = sum(d.textlength(w, font=f) for w, _ in ln) + d.textlength(" ", font=f) * (len(ln) - 1)
        x = W / 2 - tw / 2
        for w, ts in ln:
            on = t >= ts - 0.05
            col = (255, 255, 255) if on else (255, 255, 255)
            al = int(255 * a * (1.0 if on else 0.35))
            fill = GOLD if (on and t < ts + 0.45) else col
            d.text((x, u(y)), w, font=f, fill=fill + (al,), anchor="lm", stroke_width=round(u(6)), stroke_fill=(8, 6, 10, al))
            x += d.textlength(w + " ", font=f)
        y += 84


def header(L, t):
    if t >= V4 - 0.1:
        return
    a = 1 - ramp(t, V4 - 0.35, V4 - 0.05)
    p = 1 + 0.1 * (1 - pop(t, 0.0, 0.35))
    put_word(L, "29 EKİM", WHITE, 540, 205, round(124 * p), alpha=a, glow=0.3)
    chip(L, 540, 325, "ATATÜRK'ÜN KENDİ SESİNDEN • 1933", bg=RED, fg=WHITE, size=38, k="black", alpha=a)


def nemutlu(L, t):
    if not (V4 - 0.1 <= t < V5 + 0.1):
        return
    a = 1 - ramp(t, V5 - 0.15, V5 + 0.1)
    rows = [("NE MUTLU", T_NM[0], 560, WHITE, 140), ("TÜRK'ÜM", T_NM[2], 740, GOLD, 170), ("DİYENE!", T_NM[3], 920, WHITE, 150)]
    for s, ts, y, col, sz in rows:
        if t >= ts - 0.1:
            q = pop(t, ts - 0.1, 0.35)
            put_word(L, s, col, 540, y, max(6, round(sz * q)), alpha=a if q > 0.02 else 0, glow=0.45)


def outro(L, t):
    if t < V5 - 0.05:
        return
    a = ramp(t, V5 - 0.05, V5 + 0.3)
    q = pop(t, V5, 0.45)
    txt(L, (540, 300), "CUMHURİYETİMİZİN", round(78 * q), WHITE, a, stroke=7)
    put_word(L, "103. YILI", GOLD, 540, 440, max(6, round(150 * q)), alpha=a if q > 0.02 else 0, glow=0.45)
    txt(L, (540, 590), "KUTLU OLSUN", round(96 * q), WHITE, a, stroke=7)
    b = ramp(t, V5 + 0.9, V5 + 1.2)
    chip(L, 540, 1250, "TAKİP ET", bg=INKC, fg=WHITE, size=78, icon_name="bell", k="black", alpha=b,
         scale=pop(t, V5 + 0.9, 0.4) * (1 + 0.04 * math.sin(t * 8) * ramp(t, V5 + 1.4, V5 + 1.7)))


class Vid(Video):
    def frame(self, t):
        if t < V2:
            bg = archive("inonu", t, V1)
        elif t < V3:
            bg = archive("turhal", t, V2)
        elif t < V4:
            bg = archive("ulku", t, V3)
        elif t < V5:
            q = clamp((t - V4) / (V5 - V4))
            bg = view(P_FLAG, 1.0 + 0.12 * q, 0.42, 0.33) * 0.62
            # "Ne mutlu" anında kırmızı nabız
            for tn in T_NM:
                if 0 <= t - tn < 0.35:
                    bg = bg + np.array([90, 10, 10], np.float32) * (1 - (t - tn) / 0.35)
        else:
            q = clamp((t - V5) / 4)
            bg = view(P_ANIT, 1.0 + 0.06 * q, 0.55, 0.52) * 0.7
        # geçiş: beyaz flaş
        for tc in (V2, V3, V4, V5):
            if 0 <= t - tc < 0.22:
                bg = bg + 150 * (1 - (t - tc) / 0.22)
        bg = grain(bg * VIG, t, 7 if t < V4 else 4)
        im = Image.fromarray(np.clip(bg, 0, 255).astype(np.uint8), "RGB").convert("RGBA")
        L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        fireworks(L, t)
        header(L, t)
        subtitle(L, t)
        nemutlu(L, t)
        outro(L, t)
        im.alpha_composite(L)
        brand(im, 540, 62, size=34)
        return im.convert("RGB")


def _rd(path):
    return np.frombuffer(subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(path), "-f", "f32le", "-ac", "1", "-ar",
                                         "44100", "-"], capture_output=True, check=True).stdout, np.float32).copy()


if __name__ == "__main__":
    mode = sys.argv[2] if len(sys.argv) > 2 else "render"
    words = [{"w": w, "s": s, "e": s + 0.3} for wl, _ in SUB for w, s in wl]
    v = Vid([{"start": 0, "end": TOTAL, "draw": lambda *a: None}], words, "", TOTAL, bg=None)
    print("TOTAL", TOTAL, "TS", TS, flush=True)
    if mode == "frames":
        (WORK / "test").mkdir(exist_ok=True)
        for tt in [float(x) for x in sys.argv[3].split(",")]:
            v.frame(tt).save(WORK / "test" / f"fr_{tt:05.2f}.jpg", quality=90)
    else:
        # müzik: Dm–Bb–F–C döngüsü, sonda D majöre çözülme
        prog = [[62, 65, 69], [58, 62, 65], [60, 65, 69], [60, 64, 67]]
        plan, t0 = [], 0.0
        while t0 < V4 - 0.5:
            ch = prog[int(t0 / 2.6) % 4]
            plan.append((t0, t0 + 2.6, ch, 0.55 if t0 < V4 - 3 else 0.75))
            t0 += 2.6
        plan += [(V4 - 0.2, T_NM[2], [58, 62, 65, 70], 1.0), (T_NM[2], V5, [60, 64, 67, 72], 1.1),
                 (V5, V5 + 1.8, [62, 66, 69, 74], 1.25), (V5 + 1.8, TOTAL, [57, 62, 66, 69], 1.15)]
        muzik_pad.mk(str(WORK / "music.wav"), TOTAL, plan, hits=[(T_NM[0] - 0.02, 1.0), (V5, 1.2)],
                     swells=[(V4 - 1.6, T_NM[0] - 0.02, 0.5)])
        # müzik seviyesi: konuşma altında kısık, sonda yüksek
        mus = _rd(WORK / "music.wav")
        tt = np.arange(len(mus)) / 44100
        g = 0.22 + 0.5 * np.clip((tt - (V4 - 1.5)) / 1.5, 0, 1) + 0.25 * np.clip((tt - V5) / 0.5, 0, 1)
        g *= np.clip((TOTAL - tt) / 0.9, 0, 1)
        at._write(str(WORK / "music2.wav"), mus * g)
        at.sfx(str(WORK / "sfx.wav"), TOTAL, [(V2, "whoosh"), (V3, "whoosh"), (V4, "whoosh"), (V5 + 0.9, "pop")])
        y = _rd(WORK / "sfx.wav")
        Lb = int(0.8 * 44100)
        tb = np.arange(Lb) / 44100
        boom = (np.sin(2 * np.pi * (55 * np.exp(-tb * 3)) * tb * 6) * 0.5 + RNG.standard_normal(Lb) * 0.2) * np.exp(-tb * 6)
        for t0, *_ in BURSTS:
            i = int(t0 * 44100)
            if i + Lb < len(y):
                y[i:i + Lb] += boom * 0.3
        at._write(str(WORK / "sfx.wav"), y)
        # karışım: ses + müzik + efekt (müzik zaten zarflı; sidechain yok)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(VOICE), "-i", str(WORK / "music2.wav"), "-i",
                        str(WORK / "sfx.wav"), "-filter_complex",
                        f"[0]apad=whole_dur={TOTAL},volume=1.0[v];[1]volume=0.9[m];[2]volume=0.8[s];"
                        "[v][m][s]amix=inputs=3:normalize=0,loudnorm=I=-14:TP=-1.5[o]", "-map", "[o]", "-ar", "44100",
                        "-c:a", "aac", "-b:a", "192k", "-t", f"{TOTAL}", str(WORK / "mix.m4a")], check=True)
        v.render(str(WORK / "mix.m4a"), str(WORK / "video.mp4"))
        print("render bitti", TOTAL, flush=True)
