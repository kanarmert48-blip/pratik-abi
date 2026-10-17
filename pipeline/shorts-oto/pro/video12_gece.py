"""12. video (2K, tam ekran sinematik): Gece 3'te evde olanlar.
Sahneler: Kaggle GPU'da Wan 2.1 ile üretildi (Real-ESRGAN 3x). Abi: Wav2Lip. Müzik: MusicGen. Efektler: sentez."""
import os
os.environ.setdefault("PA_SCALE", str(4 / 3))
import json, math, subprocess, sys, random
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from engine import *  # noqa
from widgets import *  # noqa
import audio_tools as at

WORK = Path(sys.argv[1])
SC = WORK / os.environ.get("PA_SAHNE", "sahne")
TRACK = WORK / ("track_test.mp4" if os.environ.get("PA_SAHNE") else "track.mp4")
words = json.loads((WORK / "words.json").read_text(encoding="utf-8"))
TOTAL = at.duration(str(WORK / "voice_cut.wav"))
OUTRO = 1.9
OS = TOTAL - OUTRO
TW, TH = round(W * 1.04), round(H * 1.04)  # sarsıntı payı
COLD = (120, 190, 255)
HOT = (255, 120, 80)


def T(key, nth=0):
    k = trl(clean(key)).strip('"!?;,')
    hits = [w for w in words if trl(clean(w["w"])).strip('"!?;,') == k]
    return hits[nth]["s"]


def E(key, nth=0):
    k = trl(clean(key)).strip('"!?;,')
    hits = [w for w in words if trl(clean(w["w"])).strip('"!?;,') == k]
    return hits[nth]["e"]


t_gel_e, t_kork, t_ici, t_tik = E("geliyor"), T("Korkma"), T("İçindeki"), T("Tıkırtı")
t_peki, t_ses_e, t_kal, t_sicak, t_soguy = T("Peki"), E("ses", 2), T("Kalorifer"), T("Sıcak"), T("soğuyunca")
t_ve, t_urk_e, t_parke, t_gece2, t_ahsap = T("Ve", 1), E("ürkütücüsü"), T("Parkenin"), T("Gece", 1), T("ahşap")
t_yani, t_sadece, t_sen, t_yor, t_beg = T("Yani"), T("sadece"), T("Sen"), T("Yorumlara"), T("beğenmeyi")
SFX_EV = [(0.0, "boom"), (t_gel_e + 0.35, "crack"), (t_ses_e + 0.3, "ticks"), (t_urk_e + 0.25, "creak")]
SHAKE = [t_gel_e + 0.35, t_ses_e + 0.3, t_urk_e + 0.25]

# kesmeler: (sahne, başlangıç). Aynı sahne ikinci kez kullanılınca farklı yerinden başlar.
CUTS = [("a_koridor", 0.0), ("b_mutfak", t_gel_e + 0.3), ("g_raf", t_ici), ("c_buz", T("sıcaklık")),
        ("g_raf", T("genleşip")), ("a_koridor", t_peki), ("d_petek", t_ses_e + 0.25), ("e_parke", t_ve),
        ("f_kedi", t_yani)]
SEGS = [(n, (CUTS[i + 1][1] if i + 1 < len(CUTS) else OS) - st) for i, (n, st) in enumerate(CUTS)]
STARTS = [st for _, st in CUTS] + [OS]
assert all(d > 0.5 for _, d in SEGS), SEGS
GRADE = {
    "f_kedi": "eq=brightness=-0.01:saturation=0.95,colorbalance=rs=0.04:gs=0.01:bs=-0.04",
    "c_buz": "eq=brightness=-0.16:saturation=0.75:contrast=1.15:gamma=0.85,colorbalance=rs=-0.05:bs=0.05",
    "g_raf": "eq=brightness=-0.06:saturation=0.8:contrast=1.08,colorbalance=rs=-0.04:bs=0.06",
    "e_parke": "eq=brightness=0.0:saturation=0.85:contrast=1.04:gamma=1.25,colorbalance=rs=-0.03:bs=0.05",
}
GRADE_DEF = "eq=brightness=-0.035:saturation=0.78:contrast=1.08,colorbalance=rs=-0.05:gs=0.0:bs=0.07"


def build_track(out):
    cache = WORK / "cache"
    cache.mkdir(exist_ok=True)
    parts, pp, used = [], {}, {}
    for name in dict.fromkeys(n for n, _ in SEGS):  # ileri+geri, %30 yavaş, 30 fps (karışımlı)
        src = SC / f"{name}.mp4"
        q = cache / f"pp_{name}_{int(src.stat().st_mtime)}.mp4"
        if not q.exists():
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-filter_complex",
                            "[0:v]split[f][r];[r]reverse[rv];[f][rv]concat=n=2:v=1:a=0,setpts=1.3*PTS,"
                            f"framerate=fps={FPS},format=yuv420p", "-c:v", "libx264", "-preset", "veryfast",
                            "-crf", "12", str(q)], check=True)
        pp[name] = q
    for i, (name, dur) in enumerate(SEGS):
        ss = 2.0 * used.get(name, 0)
        used[name] = used.get(name, 0) + 1
        n = int(round(dur * FPS))
        vf = (f"scale={TW}:{TH}:force_original_aspect_ratio=increase:flags=lanczos,crop={TW}:{TH},"
              f"{GRADE.get(name, GRADE_DEF)},format=yuv420p")
        import hashlib
        p = cache / f"s_{pp[name].stem}_{ss}_{n}_{hashlib.md5(vf.encode()).hexdigest()[:6]}.mp4"
        if not p.exists():
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-stream_loop", "-1", "-ss", str(ss), "-i", str(pp[name]),
                            "-vf", vf, "-frames:v", str(n), "-r", str(FPS), "-c:v", "libx264", "-preset", "veryfast",
                            "-crf", "13", str(p)], check=True)
        parts.append(str(p))
    lst = WORK / "cache" / "l.txt"
    lst.write_text("".join(f"file '{p}'\n" for p in parts))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", out],
                   check=True)


class FullBG:
    def __init__(self, track, outro):
        self.track, self.outro = track, outro
        self.p = self.po = None
        self.nt = self.nto = 0
        y, x = np.mgrid[0:H, 0:W]
        dd = np.sqrt(((x - W / 2) / (W * 0.6)) ** 2 + ((y - H / 2) / (H * 0.62)) ** 2)
        v = np.zeros((H, W, 4), np.uint8)
        v[..., 3] = (np.clip(dd - 0.45, 0, 1) * 330).clip(0, 200).astype(np.uint8)
        self.vig = Image.fromarray(v, "RGBA")
        g = np.zeros((H, W, 4), np.uint8)  # alt kısım okunurluk için koyulaştırma
        yy = np.arange(H)[:, None]
        g[..., 3] = np.clip((yy - H * 0.5) / (H * 0.5) * 130, 0, 130).astype(np.uint8)
        self.low = Image.fromarray(np.repeat(g, 1, axis=1), "RGBA")
        rng = np.random.default_rng(3)
        self.grain = []
        for _ in range(4):
            nn = rng.integers(0, 255, (H // 3, W // 3), dtype=np.uint8)
            gg = np.zeros((H // 3, W // 3, 4), np.uint8)
            gg[..., 0] = gg[..., 1] = gg[..., 2] = nn
            gg[..., 3] = 14
            self.grain.append(Image.fromarray(gg, "RGBA").resize((W, H), Image.NEAREST))

    def _pipe(self, path, t, size):
        return subprocess.Popen(["ffmpeg", "-loglevel", "error", "-ss", f"{t:.4f}", "-i", path, "-vf",
                                 f"scale={size[0]}:{size[1]}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                                stdout=subprocess.PIPE)

    def _read(self, t):
        if self.p is None or abs(t - self.nt) > 0.5 / FPS:
            if self.p:
                self.p.kill()
            self.p = self._pipe(self.track, t, (TW, TH))
        buf = self.p.stdout.read(TW * TH * 3)
        self.nt = t + 1 / FPS
        if len(buf) < TW * TH * 3:
            return Image.new("RGB", (TW, TH), (5, 6, 10))
        return Image.frombuffer("RGB", (TW, TH), buf, "raw", "RGB", 0, 1)

    def _read_outro(self, lt):
        if self.po is None or abs(lt - self.nto) > 0.5 / FPS:
            if self.po:
                self.po.kill()
            self.po = self._pipe(self.outro, lt, (W, H))
        buf = self.po.stdout.read(W * H * 3)
        self.nto = lt + 1 / FPS
        if len(buf) < W * H * 3:
            return Image.new("RGB", (W, H), (0, 0, 0))
        return Image.frombuffer("RGB", (W, H), buf, "raw", "RGB", 0, 1)

    def seg(self, t):
        i = 0
        for k in range(len(SEGS)):
            if STARTS[k] <= t + 1e-6:
                i = k
        return i, t - STARTS[i]

    def frame(self, t):
        if t >= OS:
            return self._read_outro(t - OS).convert("RGBA")
        src = self._read(t)
        i, lt = self.seg(t)
        # yavaş yakınlaşma + sarsıntı
        z = 1.0 + 0.035 * min(1.0, lt / max(SEGS[i][1], 0.1))
        sx = sy = 0.0
        for st in SHAKE:
            q = t - st
            if 0 <= q < 0.45:
                a = (1 - q / 0.45) * u(16)
                sx, sy = a * math.sin(q * 90), a * math.cos(q * 77)
        cw, ch = W / z, H / z
        cx, cy = TW / 2 + sx, TH / 2 + sy
        im = src.crop((cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2)).resize((W, H), Image.BICUBIC).convert("RGBA")
        im.alpha_composite(self.vig)
        im.alpha_composite(self.low)
        dt = lt
        if i > 0 and dt < 0.10:  # sahne geçişi: kısa karartma
            im.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, int(200 * (1 - dt / 0.10)))))
        for st in SHAKE:  # efekt anında beyaz patlama
            q = t - st
            if 0 <= q < 0.12:
                im.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 255, int(70 * (1 - q / 0.12)))))
        im.alpha_composite(self.grain[int(t * FPS) % 4])
        return im


# ---------- Abi (Wav2Lip) ----------
AB = None
AX, AY = u(172), u(1575)


def load_abi():
    global AB
    Sz = round(u(216))
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(WORK / "abi_lipsync.mp4"), "-vf",
                          f"scale={Sz}:{Sz}:flags=lanczos,fps={FPS}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         capture_output=True, check=True).stdout
    n = len(raw) // (Sz * Sz * 3)
    m = Image.new("L", (Sz * 4, Sz * 4), 0)
    ImageDraw.Draw(m).ellipse([0, 0, Sz * 4 - 1, Sz * 4 - 1], fill=255)
    m = m.resize((Sz, Sz), Image.LANCZOS)
    b = round(u(8))
    ring = Image.new("RGBA", (Sz + 2 * b, Sz + 2 * b), (0, 0, 0, 0))
    ImageDraw.Draw(ring).ellipse([0, 0, Sz + 2 * b - 1, Sz + 2 * b - 1], fill=ACC + (255,))
    AB = (raw, n, Sz, m, ring)


def _env():
    r = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(WORK / "voice_cut.wav"), "-f", "s16le", "-ac", "1",
                        "-ar", "16000", "-"], capture_output=True, check=True)
    x = np.frombuffer(r.stdout, "<i2").astype(float) / 32768
    hop = 16000 // FPS
    e = np.array([np.sqrt(np.mean(x[i:i + hop] ** 2)) for i in range(0, len(x), hop)])
    e = e / (np.percentile(e, 95) + 1e-9)
    return np.convolve(np.clip(e, 0, 1.2), np.ones(3) / 3, mode="same")


ENV = _env()


def abi(im, t):
    raw, n, Sz, m, ring = AB
    i = min(n - 1, int(t * FPS))
    fr = Image.frombuffer("RGB", (Sz, Sz), raw[i * Sz * Sz * 3:(i + 1) * Sz * Sz * 3], "raw", "RGB", 0, 1).convert("RGBA")
    fr.putalpha(m)
    img = ring.copy()
    b = (img.width - Sz) // 2
    img.alpha_composite(fr, (b, b))
    l = float(ENV[min(len(ENV) - 1, int(t * FPS))])
    im2 = img.resize((int(img.width * (1 + 0.05 * l)), int(img.height * (1 + 0.05 * l))), Image.BICUBIC)
    sh, pad = soft_shadow(img.width, img.height, img.width // 2, blur=round(u(16)), op=0.55)
    comp(im, sh, AX - img.width / 2 - pad, AY - img.height / 2 - pad + u(12))
    comp(im, im2, AX - im2.width / 2, AY - im2.height / 2)
    d = ImageDraw.Draw(im)
    for k2 in range(2):
        rr = u(130 + k2 * 22 + 12 * l)
        d.arc([AX - rr, AY - rr, AX + rr, AY + rr], -40, 30, fill=ACC + (int(200 - 70 * k2),), width=round(u(7)))


# ---------- emoji ----------
_LOT = {}


def lottie(L, code, cx, cy, size, t, start, end=None):
    if t < start or (end is not None and t > end + 0.3):
        return
    if code not in _LOT:
        from ai_tools import Lottie
        _LOT[code] = Lottie(code)
    sc = eb(ph(t, start, 0.4)) * ((1 - eio(ph(t, end, 0.3))) if end is not None else 1)
    px = int(u(size))
    if sc <= 0.02:
        return
    fr = _LOT[code].frame(t - start, px)
    if abs(sc - 1) > 0.01:
        fr = fr.resize((max(1, int(px * sc)), max(1, int(px * sc))), Image.BICUBIC)
    comp(L, fr, u(cx) - fr.width / 2, u(cy) - fr.height / 2)


# ---------- grafikler ----------
def clock(L, t):
    """Kırmızı dijital saat 03:00 (yanıp sönen iki nokta)."""
    q = (1 - eio(ph(t, t_gel_e - 0.2, 0.4))) * (0.75 + 0.25 * eo(ph(t, 0, 0.25)))  # ilk karede görünür
    if q <= 0.01:
        return
    txt = "03:00" if int(t * 2) % 2 == 0 else "03 00"
    f = font("black", round(u(230)))
    tmp = Image.new("RGBA", (W, round(u(360))), (0, 0, 0, 0))
    d = ImageDraw.Draw(tmp)
    d.text((W / 2, tmp.height / 2), txt, font=f, fill=(255, 52, 52, int(255 * q)), anchor="mm")
    glow = tmp.filter(ImageFilter.GaussianBlur(u(22)))
    L.alpha_composite(glow, (0, round(u(560))))
    L.alpha_composite(glow, (0, round(u(560))))
    L.alpha_composite(tmp, (0, round(u(560))))
    text_c(L, (540, 870), "GECE", "black", 70, (255, 200, 200), alpha=q * 0.85)


def title(L, t, start, end, a_txt, b_txt, col=WHITE, acc=ACC, y=300):
    if not (start <= t < end):
        return
    p = ph(t, start, 0.45) * (1 - ph(t, end - 0.25, 0.25))
    if p <= 0:
        return
    text_c(L, (540, y + (1 - eo(p)) * 30), a_txt, "black", 70, col, alpha=eo(p), stroke=6, stroke_fill=(5, 6, 12))
    bs = 92
    while bs > 50 and font("black", round(u(bs))).getlength(b_txt) > u(980):
        bs -= 2
    text_c(L, (540, y + 92 + (1 - eo(p)) * 30), b_txt, "black", bs, acc, alpha=eo(p), stroke=7, stroke_fill=(5, 6, 12))


def expand_anim(L, t, start, end, cx, cy, label_hot, label_cold, phase=None):
    """Isınınca genleşen / soğuyunca büzülen kutu animasyonu (birim)."""
    if not (start <= t < end):
        return
    a = eo(ph(t, start, 0.4)) * (1 - eio(ph(t, end - 0.3, 0.3)))
    ph_ = phase(t) if phase else (math.sin((t - start) * 2.6) + 1) / 2  # 0 soğuk .. 1 sıcak
    w = 230 + 90 * ph_
    col = tuple(int(lerp(c, h, ph_)) for c, h in zip(COLD, HOT))
    glass(L, cx - 330, cy - 170, 660, 340, alpha=a)
    d = ImageDraw.Draw(L)
    d.rounded_rectangle([u(cx - w / 2), u(cy - 55), u(cx + w / 2), u(cy + 55)], radius=u(18),
                        fill=col + (int(235 * a),), outline=(255, 255, 255, int(220 * a)), width=round(u(4)))
    for sgn in (-1, 1):
        x0 = cx + sgn * (w / 2 + 18)
        x1 = cx + sgn * (w / 2 + 18 + 50 * (ph_ - 0.5) * 2)
        if abs(x1 - x0) > 6:
            arrow(L, 1.0, 0.0, (x0, cy), (x1, cy), bend=0.0, col=col, width=8, gap=0)
    lab = label_hot if ph_ > 0.5 else label_cold
    text_c(L, (cx, cy + 112), lab, "black", 46, col, alpha=a)
    lottie(L, "1f525" if ph_ > 0.5 else "1f976", cx - 250, cy - 105, 100, t, start)


def bottom_chip(L, t, start, text, bg=GREEN, fg=WHITE, size=46, icon=None, y=1240, end=None):
    if t < start or (end is not None and t >= end):
        return
    chip(L, 540, y, text, bg=bg, fg=fg, size=size, icon_name=icon, k="black",
         scale=eb(ph(t, start, 0.35)) * ((1 - eio(ph(t, end - 0.2, 0.2))) if end is not None else 1))


def draw(t):
    L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    if t >= OS:
        chip(L, 540, 1560, "Takip et, kaçırma!", bg=RED, fg=WHITE, size=50, icon_name="bell", k="black",
             scale=eb(ph(t - OS, 0.25, 0.4)))
        return L
    clock(L, t)
    # buzdolabı
    title(L, t, t_kork, t_peki - 0.1, "O ses...", "BUZDOLABI", y=330)
    expand_anim(L, t, t_ici + 0.2, t_peki - 0.05, 540, 820, "Isınınca genleşir", "Soğuyunca büzülür",
                phase=lambda q: 0.5 + 0.5 * math.sin(3.65 * (q - T("genleşip")) + math.pi / 2))
    bottom_chip(L, t, t_tik - 0.05, "Plastik raflar çıtırdıyor", bg=WHITE, fg=INK, end=t_peki)
    # petek
    title(L, t, t_peki, t_ses_e + 0.2, "Peki ya", "şu ses?", y=330)
    title(L, t, t_kal, t_ve - 0.1, "O ses...", "KALORİFER PETEĞİ", y=330)
    def pet(q):
        if q < T("tık"):
            return 1 - eio(ph(q, t_soguy, 0.6))
        return 0.5 + 0.5 * math.sin(7.0 * (q - T("tık")) - math.pi / 2)
    expand_anim(L, t, t_sicak + 0.1, t_ve - 0.05, 540, 820, "Sıcak su: metal genleşir", "Soğuyunca büzülür", phase=pet)
    # parke
    title(L, t, t_ve, t_urk_e + 0.4, "Ve en", "ürkütücüsü...", acc=(255, 90, 90), y=330)
    title(L, t, t_parke, t_yani - 0.1, "O ses...", "PARKE", y=330)
    bottom_chip(L, t, t_ahsap - 0.1, "Gece soğuyan ahşap büzülür", bg=(56, 189, 248), fg=INK, end=t_yani)
    lottie(L, "1f976", 880, 640, 150, t, t_gece2, end=t_yani - 0.2)
    # sonuç
    title(L, t, t_yani, t_sen - 0.1, "Evin perili değil...", "sadece soğuyor", y=330)
    lottie(L, "1f60c", 880, 640, 160, t, t_sadece) if os.path.exists(
        "/home/claude/araclar/noto/lottie/1f60c.json") else None
    title(L, t, t_sen, OS, "Sen gece en çok", "hangi sesten korkuyorsun?", y=330)
    bottom_chip(L, t, t_yor - 0.05, "Yorumlara yaz!", bg=WHITE, fg=INK, size=52, icon="speech_balloon")
    lottie(L, "1f44d", 300, 1000, 150, t, t_beg - 0.1)
    lottie(L, "1f514", 780, 1000, 150, t, t_beg + 0.3)
    return L


class Vid(Video):
    def frame(self, t):
        im = self.bg.frame(t)
        im.alpha_composite(draw(t))
        brand(im, 540, 140)
        if t < OS:
            draw_caption(im, self.groups, t, y=1395)
            abi(im, t)
        return im.convert("RGB")


if __name__ == "__main__":
    mode = sys.argv[2] if len(sys.argv) > 2 else "render"
    if not TRACK.exists():
        build_track(str(TRACK))
    load_abi()
    bg = FullBG(str(TRACK), str(WORK / "outro.mp4"))
    v = Vid([{"start": 0, "end": TOTAL, "draw": lambda *a: None}], words, "", TOTAL, bg=bg)
    if mode == "frames":
        for tt in [float(x) for x in sys.argv[3].split(",")]:
            v.bg.p = None
            v.frame(tt).save(WORK / f"fr_{tt:05.1f}.png")
    else:
        json.dump(SFX_EV, open(WORK / "sfx_events.json", "w"))
        subprocess.run([sys.executable, str(WORK / "sfx12.py"), str(TOTAL)], cwd=str(WORK), check=True)
        sfx = [(OS, "whoosh"), (OS + 0.15, "tink"), (t_yor, "pop"), (t_beg, "pop")]
        at.sfx(str(WORK / "sfx_ui.wav"), TOTAL, sfx)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(WORK / "sfx_gerilim.wav"), "-i",
                        str(WORK / "sfx_ui.wav"), "-filter_complex", "amix=inputs=2:normalize=0", str(WORK / "sfx.wav")],
                       check=True)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(WORK / "muzik.wav"), "-af",
                        f"apad,atrim=0:{TOTAL:.3f},afade=t=in:d=1.0,afade=t=out:st={TOTAL - 1.5:.3f}:d=1.5",
                        "-ar", "44100", "-ac", "1", str(WORK / "music.wav")], check=True)
        at.final_mix(str(WORK / "voice_cut.wav"), str(WORK / "music.wav"), str(WORK / "sfx.wav"), str(WORK / "mix.m4a"))
        v.render(str(WORK / "mix.m4a"), str(WORK / "video.mp4"))
        print("render bitti", TOTAL, flush=True)
