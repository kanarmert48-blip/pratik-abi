"""14. video (2K, tek konu, döngülü): Soğan keserken neden ağlarız?
Arka plan: gerçek video klipler (Pixabay) + 1 Wan sahnesi (buzdolabı) + 1 fotoğraf (3D hareket).
Abi: tam boy, sol altta, sadece yüz ifadeleri. Sonda kapanış yok: son cümle başa bağlanır."""
import os
os.environ.setdefault("PA_SCALE", str(4 / 3))
import json, math, subprocess, sys, hashlib
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from engine import *  # noqa
from widgets import *  # noqa
import audio_tools as at
from abi_yuz import AbiYuz, mix

WORK = Path(sys.argv[1])
MED = Path("/home/claude/pratik-abi/media/v14-sogan")
V12C = Path("/tmp/claude-0/-home-claude-pratik-abi/b79e0552-bc51-522f-903a-0721ef74ac4f/scratchpad/v12/cache")
words = json.loads((WORK / "words.json").read_text(encoding="utf-8"))
TOTAL = at.duration(str(WORK / "voice_cut.wav"))
TW, TH = round(W * 1.04), round(H * 1.04)


def _hits(key):
    k = trl(clean(key)).strip('"!?;,.…')
    return [w for w in words if trl(clean(w["w"])).strip('"!?;,.…') == k]


def T(key, nth=0):
    return _hits(key)[nth]["s"]


t_bicak, t_bu, t_peki, t_sogani = T("Bıçak"), T("Bu"), T("Peki"), T("Soğanı")
t_soguk, t_keskin, t_kok, t_gaz4 = T("Soğuk"), T("Keskin"), T("Kökünü"), T("Gaz", 3)
t_bunu, t_cunku, t_yasar = T("Bunu"), T("Çünkü"), T("yaşarır")

# (tür, kaynak, başlangıç ofseti, yatay odak, başlangıç zamanı)
CUTS = [("vid", MED / "dogra_4.mp4", 1.2, 0.5, 0.0),
        ("vid", MED / "dogra_1.mp4", 1.0, 0.42, t_bicak),
        ("vid", MED / "aglama_3.mp4", 0.2, 0.5, t_bu),
        ("vid", MED / "dogra_2.mp4", 2.0, 0.55, t_peki),
        ("vid", V12C / "pp_g_raf_1792156191.mp4", 0.0, 0.5, t_sogani),
        ("vid", MED / "bicak_2.mp4", 0.4, 0.55, t_keskin),
        ("px", MED / "soganfoto_2.jpg", 0.0, 0.211, t_kok),
        ("vid", MED / "dogra_4.mp4", 4.6, 0.5, t_bunu)]
STARTS = [c[4] for c in CUTS] + [TOTAL]
SEGS = [(c, STARTS[i + 1] - c[4]) for i, c in enumerate(CUTS)]
assert all(d > 0.5 for _, d in SEGS), [round(d, 2) for _, d in SEGS]
GRADE = "eq=contrast=1.06:saturation=1.1:brightness=0.01"


def parallax(src, out, dur, focus, move=0.03, zoom=0.07, direction=1):
    import cv2
    from ai_tools import depth_map
    im = Image.open(src).convert("RGB")
    pad = 1 + zoom + move * 2
    s = max(TW * pad / im.width, TH * pad / im.height)
    im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    cw, ch = round(TW * pad), round(TH * pad)
    x0 = int(min(max(0, im.width * focus - cw / 2), im.width - cw))
    y0 = (im.height - ch) // 2
    im = im.crop((x0, y0, x0 + cw, y0 + ch))
    arr = np.asarray(im)
    d = cv2.GaussianBlur(depth_map(im), (0, 0), 8)
    yy, xx = np.mgrid[0:ch, 0:cw].astype(np.float32)
    cx, cy = cw / 2, ch / 2
    ox, oy = (cw - TW) // 2, (ch - TH) // 2
    hw, hh = TW // 2, TH // 2
    A = cv2.resize(xx[oy:oy + TH, ox:ox + TW] - cx, (hw, hh), interpolation=cv2.INTER_AREA)
    B = cv2.resize(yy[oy:oy + TH, ox:ox + TW] - cy, (hw, hh), interpolation=cv2.INTER_AREA)
    dd = cv2.resize(d[oy:oy + TH, ox:ox + TW], (hw, hh), interpolation=cv2.INTER_AREA).astype(np.float32)
    P = (0.35 + 0.65 * dd).astype(np.float32)
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{TW}x{TH}",
                          "-r", str(FPS), "-i", "-", "-vf", GRADE, "-c:v", "libx264", "-preset", "veryfast", "-crf", "14",
                          "-pix_fmt", "yuv420p", str(out)], stdin=subprocess.PIPE)
    n = int(round(dur * FPS))
    for i in range(n):
        q = i / max(1, n - 1)
        e = q * q * (3 - 2 * q)
        dx = direction * move * TW * (e - 0.5) * 2
        invz = 1.0 / (1.0 + np.float32(zoom * e) * P)
        mx = cv2.resize(np.float32(cx) + A * invz - np.float32(dx) * dd, (TW, TH), interpolation=cv2.INTER_LINEAR)
        my = cv2.resize(np.float32(cy) + B * invz, (TW, TH), interpolation=cv2.INTER_LINEAR)
        fr = cv2.remap(arr, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        p.stdin.write(np.ascontiguousarray(fr).tobytes())
    p.stdin.close()
    p.wait()


def build_track(out):
    cache = WORK / "cache"
    cache.mkdir(exist_ok=True)
    parts = []
    for i, ((kind, src, off, focus, _), dur) in enumerate(SEGS):
        key = hashlib.md5(f"{kind}{src}{off}{focus}{dur:.3f}{GRADE}{TW}".encode()).hexdigest()[:8]
        p = cache / f"{i}_{key}.mp4"
        if not p.exists():
            if kind == "px":
                parallax(src, p, dur, focus)
            else:
                n = int(round(dur * FPS))
                vf = (f"fps={FPS},scale={TW}:{TH}:force_original_aspect_ratio=increase:flags=lanczos,"
                      f"crop={TW}:{TH}:(iw-{TW})*{focus}:(ih-{TH})/2,{GRADE},format=yuv420p")
                subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-stream_loop", "-1", "-ss", str(off), "-i", str(src),
                                "-vf", vf, "-frames:v", str(n), "-an", "-c:v", "libx264", "-preset", "veryfast",
                                "-crf", "14", str(p)], check=True)
        parts.append(str(p))
    lst = cache / "l.txt"
    lst.write_text("".join(f"file '{p}'\n" for p in parts))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", out],
                   check=True)


class FullBG:
    def __init__(self, track):
        self.track = track
        self.p = None
        self.nt = 0
        y, x = np.mgrid[0:H, 0:W]
        dd = np.sqrt(((x - W / 2) / (W * 0.62)) ** 2 + ((y - H / 2) / (H * 0.64)) ** 2)
        v = np.zeros((H, W, 4), np.uint8)
        v[..., 3] = (np.clip(dd - 0.55, 0, 1) * 300).clip(0, 150).astype(np.uint8)
        g = np.zeros((H, W, 4), np.uint8)
        yy = np.arange(H)[:, None]
        g[..., 3] = (np.clip((yy - H * 0.5) / (H * 0.5) * 110, 0, 110) +
                     np.clip((H * 0.22 - yy) / (H * 0.22) * 120, 0, 120)).astype(np.uint8)
        self.ov = Image.alpha_composite(Image.fromarray(v, "RGBA"), Image.fromarray(g, "RGBA"))

    def _read(self, t):
        if self.p is None or abs(t - self.nt) > 0.5 / FPS:
            if self.p:
                self.p.kill()
            self.p = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-ss", f"{t:.4f}", "-i", self.track, "-f", "rawvideo",
                                       "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
        buf = self.p.stdout.read(TW * TH * 3)
        self.nt = t + 1 / FPS
        if len(buf) < TW * TH * 3:
            return Image.new("RGB", (TW, TH), (10, 10, 12))
        return Image.frombuffer("RGB", (TW, TH), buf, "raw", "RGB", 0, 1)

    def frame(self, t):
        src = self._read(t)
        i = max(k for k in range(len(SEGS)) if STARTS[k] <= t + 1e-6)
        lt, dur = t - STARTS[i], SEGS[i][1]
        z = 1.0 + 0.035 * min(1.0, lt / max(dur, 0.1))
        if i == 0:
            z += 0.07 * (1 - eo(ph(t, 0.0, 0.4)))      # ilk karede yakınlaşma vuruşu
        cw, ch = W / z, H / z
        cx, cy = TW / 2, TH / 2
        im = src.crop((cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2)).resize((W, H), Image.BICUBIC).convert("RGBA")
        im.alpha_composite(self.ov)
        if i > 0 and lt < 0.12:
            im.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 255, int(110 * (1 - lt / 0.12)))))
        return im


# ---------- Abi ----------
YUZ = AbiYuz()
AH = round(H * 0.25)
_sh = Image.new("RGBA", (round(AH * 0.42), round(AH * 0.06)), (0, 0, 0, 0))
ImageDraw.Draw(_sh).ellipse([0, 0, _sh.width - 1, _sh.height - 1], fill=(0, 0, 0, 130))
SHADOW = _sh.filter(ImageFilter.GaussianBlur(AH * 0.012))


def _env():
    r = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(WORK / "voice_cut.wav"), "-f", "s16le", "-ac", "1",
                        "-ar", "16000", "-"], capture_output=True, check=True)
    x = np.frombuffer(r.stdout, "<i2").astype(float) / 32768
    hop = 16000 // FPS
    e = np.array([np.sqrt(np.mean(x[i:i + hop] ** 2)) for i in range(0, len(x), hop)])
    e = e / (np.percentile(e, 95) + 1e-9)
    return np.convolve(np.clip(e, 0, 1.2), np.ones(2) / 2, mode="same")


ENV = _env()
EXPR_T = [(0.0, "saskin"), (t_bicak, "merak"), (t_bu, "korku"), (t_yasar, "normal"), (t_peki, "soru"),
          (t_sogani, "mutlu"), (t_soguk, "komik"), (t_keskin, "mutlu"), (t_kok, "supheli"), (t_gaz4, "saskin"),
          (t_bunu, "komik")]


def expr_at(t):
    k = max(i for i, (st, _) in enumerate(EXPR_T) if st <= t + 1e-9)
    cur, prev = EXPR_T[k][1], EXPR_T[k - 1][1] if k > 0 else EXPR_T[k][1]
    return mix(prev, cur, float(eio(ph(t, EXPR_T[k][0] - 0.12, 0.3))))


def abi(im, t):
    lvl = float(ENV[min(len(ENV) - 1, int(t * FPS))])
    wink = float(math.sin(min(1.0, max(0.0, (t - t_cunku) / 0.4)) * math.pi))
    fig = YUZ.frame(t, level=lvl, expr=expr_at(t), height=AH, wink=wink)
    feet_y = H - round(u(34))
    cx = round(u(45)) + round(174 * AH / 1024)
    comp(im, SHADOW, cx - SHADOW.width / 2, feet_y - SHADOW.height * 0.55)
    comp(im, fig, cx - fig.width * 346 / 687, feet_y - fig.height * 1005 / 1024)


# ---------- grafikler ----------
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
    fr = _LOT[code].frame(max(0.0, t - start), px)
    if abs(sc - 1) > 0.01:
        fr = fr.resize((max(1, int(px * sc)), max(1, int(px * sc))), Image.BICUBIC)
    comp(L, fr, u(cx) - fr.width / 2, u(cy) - fr.height / 2)


def title(L, t, start, end, a_txt, b_txt, col=WHITE, acc=ACC, y=300):
    if not (start <= t < end):
        return
    p = ph(t, start, 0.4) * (1 - ph(t, end - 0.2, 0.2))
    if p <= 0:
        return
    bs = 96
    while bs > 50 and font("black", round(u(bs))).getlength(b_txt) > u(990):
        bs -= 2
    pop = 1 + 0.12 * (1 - eb(ph(t, start, 0.35)))
    text_c(L, (540, y + (1 - eo(p)) * 30), a_txt, "black", 64, col, alpha=eo(p), stroke=6, stroke_fill=(5, 6, 12))
    text_c(L, (540, y + 94), b_txt, "black", round(bs * pop), acc, alpha=eo(p), stroke=8, stroke_fill=(5, 6, 12))


def bchip(L, t, start, end, text, y, bg=WHITE, fg=INK, size=46, icon=None):
    if t < start or t >= end:
        return
    chip(L, 540, y, text, bg=bg, fg=fg, size=size, icon_name=icon, k="black",
         scale=eb(ph(t, start, 0.35)) * (1 - eio(ph(t, end - 0.2, 0.2))))


# gaz parçacıkları: yumuşak, yükselen, hafif dalgalı kabarcıklar
_rng = np.random.default_rng(14)
PARTS = [(_rng.uniform(260, 820), _rng.uniform(0, 1), _rng.uniform(0.18, 0.32), _rng.uniform(16, 40),
          _rng.uniform(0, 6.28)) for _ in range(46)]
_SPR = {}


def _sprite(r):
    r = int(r)
    if r not in _SPR:
        n = 2 * r + 1
        yy, xx = np.mgrid[0:n, 0:n]
        d = np.sqrt((xx - r) ** 2 + (yy - r) ** 2) / r
        a = np.clip(1 - d, 0, 1) ** 1.6
        im = np.zeros((n, n, 4), np.uint8)
        im[..., 0], im[..., 1], im[..., 2] = 225, 255, 190
        im[..., 3] = (a * 150).astype(np.uint8)
        _SPR[r] = Image.fromarray(im, "RGBA")
    return _SPR[r]


def gas(L, t, start, end, y_from=1550, y_to=350):
    if not (start - 0.01 <= t < end + 0.5):
        return
    fade = eo(ph(t, start, 0.5)) * (1 - eio(ph(t, end, 0.5)))
    for x0, ph0, sp, r, wob in PARTS:
        q = (ph0 + (t - start) * sp) % 1.0
        y = y_from + (y_to - y_from) * q
        x = x0 + 40 * math.sin(t * 1.7 + wob) * q
        a = fade * math.sin(q * math.pi)
        if a < 0.05:
            continue
        spr = _sprite(u(r * (0.7 + 0.6 * q)))
        if a < 0.98:
            spr = set_alpha(spr, a)
        comp(L, spr, u(x) - spr.width / 2, u(y) - spr.height / 2)


ROOT = (575, 1600)  # kök noktası (1080 birim)


def draw(t):
    L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    # kanca: ilk karede hazır
    title(L, t, -1.0, t_bicak - 0.05, "Seni ağlatan şey", "BİR GAZ!", acc=(255, 96, 96))
    lottie(L, "1f62d", 870, 640, 190, t, -0.5, end=t_bicak - 0.3)
    # gaz oluşur
    title(L, t, t_bicak, t_bu - 0.05, "Bıçak hücreleri parçalayınca", "GAZ ÇIKAR")
    gas(L, t, t_bicak + 0.2, t_peki - 0.3)
    lottie(L, "1f9c5", 870, 640, 150, t, t_bicak + 0.2, end=t_bu - 0.25)
    # göz yaşarır
    title(L, t, t_bu, t_peki - 0.05, "Gaz gözüne ulaşınca", "GÖZÜN YAŞARIR", acc=(120, 210, 255))
    lottie(L, "1f622", 870, 640, 160, t, t_yasar - 0.1, end=t_peki - 0.25)
    # soru + yorum çağrısı (ekranda)
    title(L, t, t_peki, t_sogani - 0.05, "Peki nasıl", "AĞLAMAZSIN?")
    bchip(L, t, t_peki + 0.5, t_soguk, "Sen de ağlıyor musun? Yorumlara yaz!", 1140, icon="speech_balloon", size=42)
    # buzdolabı
    title(L, t, t_sogani, t_keskin - 0.05, "Yarım saat", "BUZDOLABINDA BEKLET", acc=(130, 220, 255))
    lottie(L, "2744_fe0f", 870, 650, 150, t, t_sogani + 0.2, end=t_keskin - 0.25)
    bchip(L, t, t_soguk - 0.05, t_keskin, "Soğuk, gazı yavaşlatır", 1140, bg=(56, 189, 248), fg=INK)
    # keskin bıçak
    title(L, t, t_keskin, t_kok - 0.05, "Keskin bıçak", "DAHA AZ GAZ")
    # kök
    title(L, t, t_kok, t_bunu - 0.05, "Kökünü", "EN SONA BIRAK")
    if t_kok + 0.3 <= t < t_bunu:
        arrow(L, t, t_kok + 0.3, (930, 980), (ROOT[0] + 50, ROOT[1] - 30), bend=-0.22, col=ACC, width=13, gap=28)
    bchip(L, t, t_gaz4 - 0.05, t_bunu, "Gaz en çok burada!", 640, bg=RED, fg=WHITE)
    # paylaş (döngü: "Çünkü..." başa bağlanır)
    title(L, t, t_bunu, TOTAL + 1, "Bunu bilmeyen", "ARKADAŞINA GÖNDER")
    if t >= t_bunu + 0.1:
        sc = eb(ph(t, t_bunu + 0.1, 0.4))
        put_icon(L, "mobile_phone", 540, 680, 210 * sc, rot=8 * math.sin(t * 6))
    return L


class Vid(Video):
    def frame(self, t):
        im = self.bg.frame(t)
        im.alpha_composite(draw(t))
        brand(im, 540, 140)
        draw_caption(im, self.groups, t, y=1290)
        abi(im, t)
        return im.convert("RGB")


if __name__ == "__main__":
    mode = sys.argv[2] if len(sys.argv) > 2 else "render"
    track = WORK / "track.mp4"
    if not track.exists():
        build_track(str(track))
    if mode == "track":
        sys.exit(0)
    bg = FullBG(str(track))
    v = Vid([{"start": 0, "end": TOTAL, "draw": lambda *a: None}], words, "", TOTAL, bg=bg)
    if mode == "frames":
        for tt in [float(x) for x in sys.argv[3].split(",")]:
            v.bg.p = None
            v.frame(tt).save(WORK / f"fr_{tt:05.1f}.png")
    else:
        sfx = [(st, "whoosh") for st in STARTS[1:-1]] + [(0.0, "pop"), (t_peki + 0.5, "pop"), (t_soguk, "pop"),
                                                         (t_gaz4, "pop"), (t_bunu + 0.1, "pop")]
        at.sfx(str(WORK / "sfx.wav"), TOTAL, sfx)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(WORK / "muzik.wav"), "-af",
                        f"apad,atrim=0:{TOTAL:.3f},afade=t=in:d=0.15,afade=t=out:st={TOTAL - 0.35:.3f}:d=0.35",
                        "-ar", "44100", "-ac", "1", str(WORK / "music.wav")], check=True)
        at.final_mix(str(WORK / "voice_cut.wav"), str(WORK / "music.wav"), str(WORK / "sfx.wav"), str(WORK / "mix.m4a"))
        v.render(str(WORK / "mix.m4a"), str(WORK / "video.mp4"))
        print("render bitti", TOTAL, flush=True)
