#!/usr/bin/env python3
"""Senaryodan dikey (9:16) YouTube Shorts videosu üretir.
Görüntü: Pillow ile kodla çizilen animasyon. Ses: edge-tts (Türkçe).
Kullanım: python make_video.py [--index N] [--out cikti]
"""
import argparse, asyncio, json, math, os, random, shutil, subprocess, sys, tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1080, 1920, 30
ROOT = Path(__file__).resolve().parent
VOICES = ["tr-TR-EmelNeural", "tr-TR-AhmetNeural"]

# ---------- yazı tipi ----------
FONT_BOLD = [
    ROOT / "fonts/Montserrat-ExtraBold.ttf",
    "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf",
    "/usr/share/fonts/opentype/inter/Inter-Bold.otf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]
FONT_REG = [
    ROOT / "fonts/Montserrat-SemiBold.ttf",
    "/usr/share/fonts/opentype/inter/Inter-SemiBold.otf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]


def font_path(cands):
    for c in cands:
        if Path(c).exists():
            return str(c)
    raise SystemExit("Türkçe karakter destekli font bulunamadı")


FB, FR = font_path(FONT_BOLD), font_path(FONT_REG)
_fcache = {}


def font(path, size):
    k = (path, size)
    if k not in _fcache:
        _fcache[k] = ImageFont.truetype(path, size)
    return _fcache[k]


# ---------- renk temaları (her videoda değişir) ----------
THEMES = [
    {"bg": [(16, 42, 67), (10, 92, 84)], "acc": (255, 200, 61), "txt": (255, 255, 255), "sub": (220, 235, 240)},
    {"bg": [(43, 18, 76), (140, 40, 90)], "acc": (255, 214, 102), "txt": (255, 255, 255), "sub": (240, 225, 240)},
    {"bg": [(12, 56, 40), (34, 120, 70)], "acc": (250, 240, 140), "txt": (255, 255, 255), "sub": (225, 245, 230)},
    {"bg": [(255, 244, 228), (255, 214, 186)], "acc": (214, 72, 44), "txt": (34, 30, 40), "sub": (70, 60, 70)},
    {"bg": [(20, 20, 28), (48, 48, 70)], "acc": (88, 220, 160), "txt": (255, 255, 255), "sub": (210, 210, 225)},
    {"bg": [(232, 244, 255), (190, 220, 255)], "acc": (36, 90, 210), "txt": (20, 30, 50), "sub": (50, 65, 90)},
]


def ease_out(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def ease_back(t):
    t = max(0.0, min(1.0, t))
    c1, c3 = 1.70158, 2.70158
    return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2


def wrap(draw, text, fnt, maxw):
    words, lines, cur = text.split(), [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if draw.textlength(test, font=fnt) <= maxw:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def fit_font(draw, text, path, maxw, maxh, start, minsize=48):
    size = start
    while size > minsize:
        f = font(path, size)
        lines = wrap(draw, text, f, maxw)
        lh = int(size * 1.18)
        if len(lines) * lh <= maxh and all(draw.textlength(l, font=f) <= maxw for l in lines):
            return f, lines, lh
        size -= 4
    f = font(path, minsize)
    return f, wrap(draw, text, f, maxw), int(minsize * 1.18)


# ---------- arka plan ----------
def make_bg(theme):
    c1, c2 = np.array(theme["bg"][0], float), np.array(theme["bg"][1], float)
    y = np.linspace(0, 1, H * 2)[:, None, None]
    x = np.linspace(0, 1, W)[None, :, None]
    t = np.clip(0.75 * y + 0.25 * x, 0, 1)
    arr = (c1 * (1 - t) + c2 * t).astype(np.uint8)
    return Image.fromarray(arr, "RGB")  # 2x yükseklik: yavaşça kayar


def draw_blobs(img, theme, tsec, seed):
    rnd = random.Random(seed)
    ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    light = sum(theme["bg"][0]) > 450
    col = (0, 0, 0) if light else (255, 255, 255)
    for i in range(7):
        bx, by = rnd.uniform(0, W), rnd.uniform(0, H)
        r = rnd.uniform(60, 220)
        sp = rnd.uniform(0.15, 0.45)
        x = bx + math.sin(tsec * sp + i) * 60
        y = (by - tsec * 25 * sp) % (H + 400) - 200
        a = rnd.randint(10, 22)
        d.ellipse([x - r, y - r, x + r, y + r], fill=col + (a,))
    acc = theme["acc"]
    for i in range(3):
        x = rnd.uniform(80, W - 80) + math.cos(tsec * 0.6 + i) * 30
        y = rnd.uniform(200, H - 200) + math.sin(tsec * 0.5 + i * 2) * 40
        s = rnd.uniform(14, 26)
        d.rounded_rectangle([x - s, y - s, x + s, y + s], radius=8, outline=acc + (70,), width=4)
    img.alpha_composite(ov)


# ---------- sahne çizimi ----------
def render_frame(bg, theme, scene, idx, n, local_t, dur, global_t, total, seed, title):
    off = int((global_t / max(total, 1)) * H * 0.6)
    img = bg.crop((0, off, W, off + H)).convert("RGBA")
    draw_blobs(img, theme, global_t, seed)
    d = ImageDraw.Draw(img)
    acc, txt, sub = theme["acc"], theme["txt"], theme["sub"]
    kind = scene.get("kind", "item")

    # üst başlık şeridi
    tf = font(FR, 40)
    tw = d.textlength(title.upper(), font=tf)
    d.rounded_rectangle([W / 2 - tw / 2 - 30, 120, W / 2 + tw / 2 + 30, 190], radius=35, fill=acc + (235,))
    dark = (20, 20, 25) if sum(acc) > 450 else (255, 255, 255)
    d.text((W / 2, 155), title.upper(), font=tf, fill=dark, anchor="mm")

    # ilerleme çubuğu
    d.rounded_rectangle([90, 240, W - 90, 252], radius=6, fill=sub + (60,))
    d.rounded_rectangle([90, 240, 90 + (W - 180) * min(1, global_t / total), 252], radius=6, fill=acc + (255,))

    pop = ease_back(local_t / 0.45)
    fade = ease_out(local_t / 0.3)

    # numara rozeti
    cy = 640
    if kind == "item" and scene.get("num"):
        r = int(110 * pop)
        if r > 2:
            d.ellipse([W / 2 - r, cy - 260 - r, W / 2 + r, cy - 260 + r], fill=acc + (255,))
            nf = font(FB, max(10, int(120 * pop)))
            d.text((W / 2, cy - 255), str(scene["num"]), font=nf, fill=dark, anchor="mm")
    elif kind == "hook":
        r = int(90 * pop)
        if r > 2:
            d.regular_polygon((W / 2, cy - 250, r), n_sides=3, rotation=0, fill=acc + (255,))
            ef = font(FB, max(10, int(90 * pop)))
            d.text((W / 2, cy - 230), "!", font=ef, fill=dark, anchor="mm")
    elif kind == "cta":
        r = int(100 * pop)
        if r > 2:
            hy, hr = cy - 280, r * 0.55  # kalp
            d.ellipse([W / 2 - 1.9 * hr, hy - hr, W / 2 + 0.1 * hr, hy + hr], fill=acc + (255,))
            d.ellipse([W / 2 - 0.1 * hr, hy - hr, W / 2 + 1.9 * hr, hy + hr], fill=acc + (255,))
            d.polygon([(W / 2 - 1.93 * hr, hy + 0.5 * hr), (W / 2 + 1.93 * hr, hy + 0.5 * hr), (W / 2, hy + 2.3 * hr)], fill=acc + (255,))

    # ana başlık (pop-in)
    head = scene["text"]
    hf, lines, lh = fit_font(d, head, FB, W - 160, 520, 112)
    y0 = cy - 60
    shift = int((1 - ease_out(local_t / 0.4)) * 80)
    for i, ln in enumerate(lines):
        yy = y0 + i * lh + shift
        d.text((W / 2 + 4, yy + 5), ln, font=hf, fill=(0, 0, 0, int(70 * fade)), anchor="ma")
        d.text((W / 2, yy), ln, font=hf, fill=txt + (int(255 * fade),), anchor="ma")
    line_y = y0 + len(lines) * lh + 30
    lw = int((W - 500) * ease_out((local_t - 0.2) / 0.5))
    if lw > 0:
        d.rounded_rectangle([W / 2 - lw / 2, line_y, W / 2 + lw / 2, line_y + 12], radius=6, fill=acc + (255,))

    # altyazı (seslendirme, kelime kelime vurgulu)
    say = scene["say"].split()
    sf = font(FB, 54)
    slines, cur = [], []
    for w in say:
        test = " ".join(cur + [w])
        if d.textlength(test, font=sf) <= W - 200 or not cur:
            cur.append(w)
        else:
            slines.append(cur)
            cur = [w]
    if cur:
        slines.append(cur)
    spoken = len(say) * min(1.0, local_t / max(dur - 0.4, 0.5))
    box_top = 1330
    box_h = len(slines) * 72 + 60
    d.rounded_rectangle([70, box_top, W - 70, box_top + box_h], radius=36, fill=(0, 0, 0, 120))
    hl = acc if (0.299 * acc[0] + 0.587 * acc[1] + 0.114 * acc[2]) > 150 else (255, 214, 80)
    k = 0
    for li, words in enumerate(slines):
        lw_ = d.textlength(" ".join(words), font=sf)
        x = W / 2 - lw_ / 2
        y = box_top + 30 + li * 72
        for w in words:
            col = hl if k < spoken else (255, 255, 255)
            alpha = 255 if k < spoken + 3 else 150
            d.text((x, y), w, font=sf, fill=col + (alpha,))
            x += d.textlength(w + " ", font=sf)
            k += 1

    # alt: sahne noktaları
    for i in range(n):
        cx = W / 2 + (i - (n - 1) / 2) * 40
        rr = 11 if i == idx else 7
        d.ellipse([cx - rr, 1800 - rr, cx + rr, 1800 + rr], fill=(acc if i == idx else sub) + ((255,) if i == idx else (110,)))
    return img.convert("RGB")


# ---------- ses ----------
async def tts(text, voice, out):
    import edge_tts
    com = edge_tts.Communicate(text, voice, rate="+8%")
    await com.save(out)


def audio_dur(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path], capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def build_audio(scenes, voice, tmp, audio_dir=None, pad=0.35):
    files, durs, ok = [], [], True
    for i, s in enumerate(scenes):
        f = os.path.join(tmp, f"s{i}.mp3")
        hazir = Path(audio_dir) / f"s{i}.wav" if audio_dir else None
        if hazir and hazir.exists():
            files.append(str(hazir)); durs.append(audio_dur(str(hazir)) + pad); continue
        try:
            asyncio.run(tts(s["say"], voice, f))
            d = audio_dur(f)
            if d <= 0:
                raise RuntimeError("boş ses")
        except Exception as e:  # ağ yoksa sessiz yedek
            print(f"[uyarı] TTS başarısız ({e}); sessiz ses kullanılıyor", file=sys.stderr)
            ok = False
            d = max(2.0, len(s["say"].split()) / 2.6)
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", str(d), f], check=True)
        files.append(f)
        durs.append(d + pad)
    out = os.path.join(tmp, "voice.m4a")
    inputs, filt = [], ""
    for i, (f, d) in enumerate(zip(files, durs)):
        inputs += ["-i", f]
        filt += f"[{i}:a]aresample=44100,apad=whole_dur={d:.3f},atrim=0:{d:.3f}[a{i}];"
    filt += "".join(f"[a{i}]" for i in range(len(files))) + f"concat=n={len(files)}:v=0:a=1,loudnorm=I=-14:TP=-1.5[out]"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", filt, "-map", "[out]", "-c:a", "aac", "-b:a", "160k", out], check=True)
    return out, durs, ok


# ---------- ana akış ----------
def make(script, out_dir, seed, audio_dir=None, pad=0.35):
    rnd = random.Random(seed)
    theme = rnd.choice(THEMES)
    voice = script.get("voice") or rnd.choice(VOICES)
    scenes = script["scenes"]
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    tmp = tempfile.mkdtemp()
    audio, durs, tts_ok = build_audio(scenes, voice, tmp, audio_dir, pad)
    total = sum(durs)
    bg = make_bg(theme)
    mp4 = out_dir / f"{script['id']}.mp4"
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-i", audio, "-c:v", "libx264", "-preset", "medium", "-crf", "26", "-pix_fmt", "yuv420p", "-c:a", "copy",
           "-shortest", "-movflags", "+faststart", str(mp4)]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    gt = 0.0
    for i, (s, d) in enumerate(zip(scenes, durs)):
        nf = int(round(d * FPS))
        for f in range(nf):
            lt = f / FPS
            frame = render_frame(bg, theme, s, i, len(scenes), lt, d, gt + lt, total, seed, script["badge"])
            p.stdin.write(frame.tobytes())
        gt += nf / FPS
    p.stdin.close()
    p.wait()
    shutil.rmtree(tmp, ignore_errors=True)
    # kapak (ilk sahne, animasyon bitmiş hali)
    render_frame(bg, theme, scenes[0], 0, len(scenes), 2.0, durs[0], 0.5, total, seed, script["badge"]).save(out_dir / f"{script['id']}_kapak.jpg", quality=90)
    meta = (f"BAŞLIK:\n{script['title']}\n\nAÇIKLAMA:\n{script['description']}\n\n{' '.join(script['hashtags'])}\n\n"
            f"Süre: {total:.1f} sn | Ses: {('hazır ses' if audio_dir else voice) if tts_ok else 'YOK (sessiz)'}\n")
    (out_dir / f"{script['id']}.txt").write_text(meta, encoding="utf-8")
    print(f"OK {mp4} ({total:.1f} sn, {mp4.stat().st_size/1e6:.1f} MB)")
    return mp4


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--index", type=int, help="scripts.json içindeki sıra (yoksa sayac.txt kullanılır)")
    ap.add_argument("--out", default="cikti")
    ap.add_argument("--script", help="tek senaryo JSON dosyası")
    ap.add_argument("--audio-dir", help="hazır s0.wav, s1.wav ... klasörü")
    ap.add_argument("--pad", type=float, default=0.35)
    a = ap.parse_args()
    if a.script:
        sc = json.loads(Path(a.script).read_text(encoding="utf-8"))
        make(sc, a.out, seed=hash(sc["id"]) % 10000, audio_dir=a.audio_dir, pad=a.pad)
        return
    scripts = json.loads((ROOT / "scripts.json").read_text(encoding="utf-8"))
    counter = ROOT / "sayac.txt"
    if a.index is None:
        i = int(counter.read_text().strip()) if counter.exists() else 0
        counter.write_text(str(i + 1))
    else:
        i = a.index
    script = scripts[i % len(scripts)]
    make(script, a.out, seed=i * 7919 + 13)


if __name__ == "__main__":
    main()
