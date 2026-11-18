"""Pratik Abi – Kutupta 7 Gün (16:9 uzun video).
python3 build.py audio   -> ses zaman çizelgesi + karışım + srt
python3 build.py frames t1,t2  -> test kareleri
python3 build.py render  -> video
"""
import json, math, random, subprocess, sys, wave
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, "/home/claude/shorts-oto/pro")
import audio_tools as at

K = Path("/home/claude/kutup")
W, H, FPS = 1920, 1080, 30
S = json.loads((K / "scenes.json").read_text(encoding="utf-8"))
BALOO = "/home/claude/shorts-oto/assets/Baloo2.ttf"
INTER = "/usr/share/fonts/opentype/inter/Inter-Black.otf"
DAYS = {1: "BARINAK", 2: "SU", 3: "DONMA", 4: "KUTUP AYISI", 5: "YEMEK", 6: "FIRTINA", 7: "KURTARILMA"}
GUN = {1: "1. GÜN", 2: "2. GÜN", 3: "3. GÜN", 4: "4. GÜN", 5: "5. GÜN", 6: "6. GÜN", 7: "7. GÜN"}
CARD = 2.0      # gün kartı süresi
GAP = 0.5       # sahneler arası
LEAD = 0.4


def F(path, size):
    return ImageFont.truetype(path, size)


def dur(p):
    with wave.open(str(p)) as w:
        return w.getnframes() / w.getframerate()


# ---------------- zaman çizelgesi ----------------
def timeline():
    t = LEAD
    tl = []
    prev_day = 0
    for x in S:
        card = None
        if x["day"] >= 1 and x["day"] != prev_day:
            card = (t, t + CARD)
            t += CARD
        prev_day = x["day"]
        d = dur(K / "ses" / f"s_{x['id']:02d}.wav")
        tl.append({"id": x["id"], "day": x["day"], "vs": card[0] if card else t, "as": t, "ae": t + d, "card": card})
        t += d + GAP
    total = t + 1.2
    for i, s in enumerate(tl):
        s["ve"] = tl[i + 1]["vs"] if i + 1 < len(tl) else total
    return tl, total


TL, TOTAL = timeline()


def build_audio():
    sr = 44100
    n = int(TOTAL * sr) + sr
    v = np.zeros(n, np.float32)
    for s in TL:
        a, r = sf_read(K / "ses" / f"s_{s['id']:02d}.wav")
        i = int(s["as"] * sr)
        v[i:i + len(a)] += a[: n - i]
    write_wav(K / "voice.wav", v, sr)
    ev = []
    for s in TL:
        if s["card"]:
            ev.append((s["card"][0], "whoosh"))
            ev.append((s["card"][0] + 0.25, "ding") if False else (s["card"][0] + 0.25, "pop"))
    at.sfx(str(K / "sfx.wav"), TOTAL, ev)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-stream_loop", "-1", "-i", str(K / "muzik.wav"), "-af",
                    f"atrim=0:{TOTAL:.3f},afade=t=in:d=1.5,afade=t=out:st={TOTAL - 3:.3f}:d=3",
                    "-ar", "44100", "-ac", "1", str(K / "music.wav")], check=True)
    at.final_mix(str(K / "voice.wav"), str(K / "music.wav"), str(K / "sfx.wav"), str(K / "mix.m4a"))
    json.dump({"tl": TL, "total": TOTAL}, open(K / "timeline.json", "w"), indent=1)
    print("ses tamam", round(TOTAL, 2))


def sf_read(p):
    with wave.open(str(p)) as w:
        raw = w.readframes(w.getnframes())
        a = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
        return a, w.getframerate()


def write_wav(p, a, sr):
    a = np.clip(a, -1, 1)
    with wave.open(str(p), "w") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes((a * 32767).astype(np.int16).tobytes())


# ---------------- görseller ----------------
SC = 1.18


def prep(im):
    im = im.convert("RGB")
    s = max(W * SC / im.width, H * SC / im.height)
    im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    return im.filter(ImageFilter.UnsharpMask(radius=2, percent=50, threshold=2))


def img(n):
    return Image.open(K / "img" / f"{n:02d}.jpg")


def emoji(name, size):
    e = Image.open(K / "emoji" / name).convert("RGBA")
    return e.resize((size, size), Image.LANCZOS)


def sos_image():
    im = img(1).convert("RGB")
    w, h = im.size
    L = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(L)
    f = F(INTER, 210)
    # perspektifli harfler: önce düz çiz, sonra dikeyde ez
    T = Image.new("RGBA", (900, 300), (0, 0, 0, 0))
    td = ImageDraw.Draw(T)
    td.text((450, 150), "SOS", font=f, anchor="mm", fill=(150, 175, 205, 255))
    T2 = Image.new("RGBA", (900, 300), (0, 0, 0, 0))
    ImageDraw.Draw(T2).text((456, 158), "SOS", font=f, anchor="mm", fill=(235, 242, 252, 255))
    T = Image.alpha_composite(T2, T)
    T = T.resize((620, 110), Image.LANCZOS)
    L.alpha_composite(T, (int(w * 0.10), int(h * 0.74)))
    d.polygon([(w * 0.58, h * 0.80), (w * 0.70, h * 0.79), (w * 0.72, h * 0.86), (w * 0.59, h * 0.875)], fill=(255, 120, 20, 255))
    im = im.convert("RGBA")
    im.alpha_composite(L)
    return im.convert("RGB")


def night_image():
    im = img(7).convert("RGB")
    orig = np.asarray(im.convert("L"))
    a = np.asarray(im, np.float32)
    a = a * np.array([0.32, 0.38, 0.62]) + np.array([4, 10, 30])
    im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(im)
    rnd = random.Random(4)
    for _ in range(160):
        x, y = rnd.randrange(im.width), rnd.randrange(int(im.height * 0.45))
        r = rnd.choice([1, 1, 2]); c = rnd.randrange(170, 255)
        if orig[y, x] < 175:
            continue
        d.ellipse([x - r, y - r, x + r, y + r], fill=(c, c, c))
    return im


def space_image():
    a = np.zeros((H, W, 3), np.float32)
    yy, xx = np.mgrid[0:H, 0:W]
    a[..., 0] = 8 + 10 * (yy / H); a[..., 1] = 10 + 14 * (yy / H); a[..., 2] = 30 + 30 * (yy / H)
    im = Image.fromarray(a.astype(np.uint8))
    d = ImageDraw.Draw(im)
    rnd = random.Random(3)
    for _ in range(260):
        x, y, r = rnd.randrange(W), rnd.randrange(H), rnd.choice([1, 1, 1, 2])
        c = rnd.randrange(150, 255)
        d.ellipse([x - r, y - r, x + r, y + r], fill=(c, c, c))
    return im


BASE = {}


def base_for(i):
    if i in BASE:
        return BASE[i]
    if i <= 30:
        b = prep(img(i))
    elif i in (31,):
        b = prep(night_image())
    elif i == 32:
        b = prep(space_image())
    elif i in (33, 34):
        b = prep(sos_image())
    elif i == 35:
        im = img(19); b = prep(im.crop((im.width // 2, 0, im.width, im.height)))
    elif i == 36:
        b = prep(img(2))
    else:
        b = prep(img(27))
    BASE[i] = b
    return b


def ease(x):
    x = min(1, max(0, x))
    return x * x * (3 - 2 * x)


# kamera hareketleri: (zoom0, zoom1, fx0, fy0, fx1, fy1) fx/fy: odak (0..1)
MOVES = [(1.0, 1.12, .5, .5, .5, .45), (1.12, 1.0, .45, .5, .55, .5), (1.04, 1.12, .35, .5, .65, .5),
         (1.1, 1.02, .6, .45, .4, .55), (1.0, 1.1, .5, .6, .5, .4)]
CUSTOM = {31: (1.0, 1.06, .5, .45, .5, .4), 37: (1.04, 1.04, .5, .5, .5, .5), 33: (1.0, 1.06, .40, .80, .45, .78), 34: (1.06, 1.25, .45, .78, .64, .83), 21: (1.0, 1.1, .4, .45, .45, .4),
          16: (1.0, 1.12, .55, .55, .6, .6), 2: (1.0, 1.08, .5, .45, .5, .4), 4: (1.0, 1.1, .5, .5, .5, .55)}


def cam(i, b, p):
    z0, z1, fx0, fy0, fx1, fy1 = CUSTOM.get(i, MOVES[i % len(MOVES)])
    e = ease(p)
    z = z0 + (z1 - z0) * e
    fx = fx0 + (fx1 - fx0) * e
    fy = fy0 + (fy1 - fy0) * e
    cw, ch = b.width / SC / z, b.height / SC / z
    cx = min(max(fx * b.width, cw / 2), b.width - cw / 2)
    cy = min(max(fy * b.height, ch / 2), b.height - ch / 2)
    return b.resize((W, H), Image.BILINEAR, box=(cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2))


# kar parçacıkları
RN = np.random.default_rng(5)
FLAKES = [(RN.uniform(0, W), RN.uniform(0, H), RN.uniform(1.5, 4.5), RN.uniform(40, 120), RN.uniform(0, 6.28)) for _ in range(160)]
SNOWY = set(range(1, 9)) | {11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 22, 23, 25, 29, 30, 33, 34, 35}
STORM = {3, 29, 30}


def snow(frame, t, i):
    if i not in SNOWY:
        return frame
    L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(L)
    k = 3.0 if i in STORM else 1.0
    for x0, y0, r, sp, ph in FLAKES[: 160 if i in STORM else 90]:
        y = (y0 + sp * k * t) % H
        x = (x0 + 25 * math.sin(t * 0.8 + ph) + (sp * 1.6 * t if i in STORM else 0)) % W
        a = 200 if r > 3 else 150
        d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 255, 255, a))
    fr = frame.convert("RGBA")
    fr.alpha_composite(L)
    return fr.convert("RGB")


def aurora(frame, t, strength=1.0):
    xs = np.arange(0, W, 2)
    Y = np.arange(0, 540, 2)[:, None].astype(np.float32)
    L = np.zeros((len(Y), len(xs), 4), np.float32)
    for k, (col, base, amp) in enumerate([((80, 255, 160), 220, 70), ((150, 90, 255), 160, 55), ((60, 230, 200), 280, 60)]):
        yc = base + amp * np.sin(xs / 260 + t * 0.6 + k * 1.7) + 25 * np.sin(xs / 90 - t * 0.9 + k)
        dist = Y - yc[None, :]
        a = np.exp(-(dist / 55) ** 2) * np.where(dist < 0, 0.55, 0.35)
        for c in range(3):
            L[..., c] += col[c] * a
        L[..., 3] += 255 * a
    L[..., 3] *= strength
    L = np.clip(L, 0, 255).astype(np.uint8)
    ov = Image.fromarray(L, "RGBA").resize((W, 1080 * 540 // 1080), Image.BILINEAR).filter(ImageFilter.GaussianBlur(5))
    fr = frame.convert("RGBA")
    fr.alpha_composite(ov, (0, 0))
    return fr.convert("RGB")


AUR_CACHE = {}


def aurora_cached(frame, t):
    key = round(t * 10) / 10
    if key not in AUR_CACHE:
        if len(AUR_CACHE) > 400:
            AUR_CACHE.clear()
        blank = Image.new("RGB", (W, H), (0, 0, 0))
        AUR_CACHE[key] = None
    return aurora(frame, t)


SUN = None


def space_fx(frame, t, p):
    global SUN
    fr = frame.convert("RGBA")
    d = ImageDraw.Draw(fr)
    sun = emoji("sun.png", 420)
    glob = emoji("globe.png", 360)
    sx, sy, ex, ey = 330, 540, 1480, 560
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse([sx - 300, sy - 300, sx + 300, sy + 300], fill=(255, 190, 60, 90))
    gd.ellipse([ex - 230, ey - 230, ex + 230, ey + 230], fill=(80, 255, 170, 40))
    fr.alpha_composite(glow.filter(ImageFilter.GaussianBlur(60)))
    rnd = random.Random(9)
    for k in range(70):
        ph = rnd.random()
        q = (ph + t * 0.25) % 1
        y0 = sy + rnd.uniform(-160, 160)
        x = sx + 150 + (ex - 200 - sx - 150) * q
        y = y0 + (ey - 150 - y0) * q * q
        r = 4 if k % 3 else 6
        d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 220, 120, int(230 * (1 - q * 0.5))))
    fr.alpha_composite(sun, (sx - 210, sy - 210))
    fr.alpha_composite(glob, (ex - 180, ey - 180))
    # kutupta yeşil halka
    ring = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    rd = ImageDraw.Draw(ring)
    pulse = 0.7 + 0.3 * math.sin(t * 3)
    rd.arc([ex - 150, ey - 230, ex + 150, ey - 110], 180, 360, fill=(90, 255, 160, int(255 * pulse)), width=16)
    fr.alpha_composite(ring.filter(ImageFilter.GaussianBlur(3)))
    return fr.convert("RGB")


def heli(frame, t, s, i):
    fr = frame.convert("RGBA")
    size = 230 if i == 35 else 180
    h = emoji("heli.png", size)
    h = h.transpose(Image.FLIP_LEFT_RIGHT)
    if i == 35:
        p = ease((t - s["vs"]) / max(1, s["ve"] - s["vs"]))
        x = W + 100 - (W * 0.55) * p
        y = 140 + 40 * math.sin(t * 2)
    else:
        x, y = 1500 + 20 * math.sin(t * 1.3), 90 + 15 * math.sin(t * 2.1)
    ang = 4 * math.sin(t * 3)
    fr.alpha_composite(h.rotate(ang, resample=Image.BICUBIC), (int(x - size / 2), int(y)))
    return fr.convert("RGB")


def pulse_ring(frame, t):
    fr = frame.convert("RGBA")
    L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(L)
    q = (t * 0.8) % 1
    r = 90 + 160 * q
    cx, cy = 1310, 760
    d.ellipse([cx - r, cy - r * 0.6, cx + r, cy + r * 0.6], outline=(255, 200, 40, int(255 * (1 - q))), width=10)
    fr.alpha_composite(L)
    return fr.convert("RGB")


def text_shadow(fr, xy, s, font, fill, anchor="mm", sh=6):
    d = ImageDraw.Draw(fr)
    d.text((xy[0] + sh, xy[1] + sh), s, font=font, anchor=anchor, fill=(0, 0, 0, 160))
    d.text(xy, s, font=font, anchor=anchor, fill=fill, stroke_width=4, stroke_fill=(20, 30, 60))


def day_card(frame, t, s):
    a, b = s["card"]
    p = (t - a) / (b - a)
    if p < 0 or p > 1.05:
        return frame
    alpha = ease(min(1, p / 0.15)) * (1 - ease((p - 0.8) / 0.2) if p > 0.8 else 1)
    fr = frame.convert("RGBA")
    ov = Image.new("RGBA", (W, H), (10, 25, 55, int(150 * alpha)))
    fr.alpha_composite(ov)
    L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sc = 0.8 + 0.2 * ease(p / 0.2)
    text_shadow(L, (W // 2, H // 2 - 40), GUN[s["day"]], F(BALOO, int(200 * sc)), (255, 210, 60, 255))
    text_shadow(L, (W // 2, H // 2 + 110), DAYS[s["day"]], F(BALOO, int(90 * sc)), (255, 255, 255, 255), sh=4)
    L.putalpha(L.getchannel("A").point(lambda v: int(v * alpha)))
    fr.alpha_composite(L)
    return fr.convert("RGB")


def corner_day(frame, s, t):
    if s["day"] < 1:
        return frame
    fr = frame.convert("RGBA")
    d = ImageDraw.Draw(fr)
    f = F(BALOO, 46)
    label = f"{GUN[s['day']]}  •  {DAYS[s['day']]}"
    w = d.textlength(label, font=f)
    d.rounded_rectangle([40, 34, 40 + w + 48, 34 + 74], radius=37, fill=(15, 30, 65, 200))
    d.text((40 + 24, 34 + 37), label, font=f, anchor="lm", fill=(255, 255, 255))
    return fr.convert("RGB")


def chip(fr, cx, cy, label, font, bg, fg):
    d = ImageDraw.Draw(fr)
    w = d.textlength(label, font=font)
    d.rounded_rectangle([cx - w / 2 - 34, cy - 50, cx + w / 2 + 34, cy + 50], radius=50, fill=bg)
    d.text((cx, cy + 2), label, font=font, anchor="mm", fill=fg)


def outro(frame, t, s):
    p = t - s["as"]
    fr = frame.convert("RGBA")
    ov = Image.new("RGBA", (W, H), (10, 20, 50, int(min(1, p / 0.6) * 120)))
    fr.alpha_composite(ov)
    if p > 0.3:
        text_shadow(fr, (W // 2, 230), "Sen olsan hangi günde zorlanırdın?", F(BALOO, 92), (255, 255, 255, 255))
    labels = ["BARINAK", "SU", "KUTUP AYISI", "FIRTINA"]
    f = F(BALOO, 64)
    ws = [ImageDraw.Draw(fr).textlength(lb, font=f) + 68 for lb in labels]
    gap = 40
    x0 = (W - (sum(ws) + gap * 3)) / 2
    xs = []
    for w_ in ws:
        xs.append(x0 + w_ / 2); x0 += w_ + gap
    for k, (lb, x) in enumerate(zip(labels, xs)):
        if p > 2.2 + 0.35 * k:
            chip(fr, x, 470, lb, f, (255, 200, 40), (20, 30, 60))
    if p > 4.6:
        chip(fr, W // 2, 660, "Yorumlara yaz!", F(BALOO, 70), (255, 255, 255), (20, 30, 60))
    if p > 6.8:
        text_shadow(fr, (W // 2, 880), "SONRAKİ BÖLÜM: ISSIZ ADADA 30 GÜN", F(BALOO, 80), (255, 210, 60, 255))
    return fr.convert("RGB")


def scene_frame(s, t):
    i = s["id"]
    b = base_for(i)
    p = (t - s["vs"]) / max(0.1, s["ve"] - s["vs"])
    fr = cam(i, b, p)
    if i == 31:
        fr = aurora(fr, t, strength=ease((t - s["vs"]) / 1.5))
    if i == 32:
        fr = space_fx(fr, t, p)
    if i == 34:
        fr = pulse_ring(fr, t)
    if i in (35, 36):
        fr = heli(fr, t, s, i)
    fr = snow(fr, t, i)
    return fr


def frame(t):
    k = 0
    while k + 1 < len(TL) and TL[k + 1]["vs"] <= t:
        k += 1
    s = TL[k]
    fr = scene_frame(s, t)
    XF = 0.4
    if k + 1 < len(TL) and t > TL[k + 1]["vs"] - XF:
        n = TL[k + 1]
        a = (t - (n["vs"] - XF)) / XF
        fr = Image.blend(fr, scene_frame(n, t), ease(a))
    if s["card"] and s["card"][0] <= t <= s["card"][1] + 0.1:
        fr = day_card(fr, t, s)
    elif not s["card"] or t > s["card"][1]:
        if s["id"] != 37:
            fr = corner_day(fr, s, t)
    if s["id"] == 37:
        fr = outro(fr, t, s)
    if t < 0.6:
        fr = Image.blend(Image.new("RGB", (W, H)), fr, ease(t / 0.6))
    if t > TOTAL - 1.0:
        fr = Image.blend(fr, Image.new("RGB", (W, H)), ease((t - (TOTAL - 1.0)) / 1.0))
    return fr


def render(a=0, b=None, out=None):
    n0 = int(a * FPS)
    n1 = int((b or TOTAL) * FPS)
    out = out or str(K / "video_raw.mp4")
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                          "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
                          "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
    for n in range(n0, n1):
        p.stdin.write(frame(n / FPS).tobytes())
        if n % 600 == 0:
            print("kare", n, "/", n1, flush=True)
    p.stdin.close(); p.wait()


if __name__ == "__main__":
    m = sys.argv[1]
    if m == "audio":
        build_audio()
    elif m == "frames":
        (K / "test").mkdir(exist_ok=True)
        for tt in [float(x) for x in sys.argv[2].split(",")]:
            frame(tt).save(K / "test" / f"f_{tt:06.2f}.jpg", quality=88)
    elif m == "part":
        render(float(sys.argv[2]), float(sys.argv[3]), sys.argv[4])
    elif m == "total":
        print(TOTAL)
