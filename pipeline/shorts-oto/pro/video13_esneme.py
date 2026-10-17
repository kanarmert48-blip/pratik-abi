"""13. video (2K, hızlı mod): Esneme + parmak buruşması + asansör aynası.
Sahneler: gerçek fotoğraflar + derinlik haritasıyla 3D kamera hareketi. Abi: Wav2Lip. Müzik: MusicGen."""
import os
os.environ.setdefault("PA_SCALE", str(4 / 3))
import json, math, subprocess, sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from engine import *  # noqa
from widgets import *  # noqa
import audio_tools as at

WORK = Path(sys.argv[1])
FOTO = WORK / "foto"
words = json.loads((WORK / "words.json").read_text(encoding="utf-8"))
TOTAL = at.duration(str(WORK / "voice_cut.wav"))
OUTRO = 1.9
OS = TOTAL - OUTRO


def _hits(key):
    k = trl(clean(key)).strip('"!?;,.…')
    return [w for w in words if trl(clean(w["w"])).strip('"!?;,.…') == k]


def T(key, nth=0):
    return _hits(key)[nth]["s"]


def E(key, nth=0):
    return _hits(key)[nth]["e"]


# ---------- zaman noktaları ----------
t_neden, t_bulas, t_gorm, t_duy, t_oku = T("Neden"), T("bulaşıcıdır"), T("görmek"), T("duymak"), T("okumak")
t_ust1, t_sevd, t_kopek = T("Üstelik", 0), T("sevdiğin"), T("Hatta", 1)
t_peki, t_sinir, t_arast, t_lastik = T("Peki"), T("sinir"), T("Araştırmalara"), T("lastik")
t_ve, t_teker, t_ust2, t_bekl = T("Ve"), T("Tekerlekli"), T("Üstelik", 1), T("bekleme")
t_sen, t_yor, t_beg = T("Sen"), T("Yorumlara"), T("beğenmeyi")

# kesmeler: (fotoğraf, başlangıç, hareket yönü)
CUTS = [("esneme", 0.0, 1), ("esneme_yakin", t_bulas, -1), ("sevgi", t_ust1, 1), ("kopek", t_kopek, 1), ("parmak", t_peki, -1),
        ("parmak2", t_arast, 1), ("asansor_ic", t_ve, -1), ("asansor_engelli", t_teker, 1),
        ("ayna", t_ust2, -1), ("esneme", t_sen, 1)]
SEGS = [(n, (CUTS[i + 1][1] if i + 1 < len(CUTS) else OS) - st, d) for i, (n, st, d) in enumerate(CUTS)]
STARTS = [c[1] for c in CUTS] + [OS]
assert all(s[1] > 0.6 for s in SEGS), SEGS
FOCUS = {"esneme": 0.5, "esneme_yakin": 0.5, "ayna": 0.5, "sevgi": 0.55, "kopek": 0.45, "parmak": 0.5, "parmak2": 0.5, "asansor_ic": 0.5,
         "asansor_engelli": 0.5}  # yatay kırpma merkezi


def parallax_portrait(src, out, dur, focus=0.5, move=0.03, zoom=0.08, direction=1):
    """Dikey (W x H) 3D kamera hareketi: yakın nesneler daha çok kayar."""
    import cv2
    from ai_tools import depth_map
    im = Image.open(src).convert("RGB")
    pad = 1 + zoom + move * 2
    s = max(W * pad / im.width, H * pad / im.height)
    im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    cw, ch = round(W * pad), round(H * pad)
    x0 = int(min(max(0, im.width * focus - cw / 2), im.width - cw))
    y0 = (im.height - ch) // 2
    im = im.crop((x0, y0, x0 + cw, y0 + ch))
    arr = np.asarray(im)
    d = cv2.GaussianBlur(depth_map(im), (0, 0), 8)
    yy, xx = np.mgrid[0:ch, 0:cw].astype(np.float32)
    cx, cy = cw / 2, ch / 2
    ox, oy = (cw - W) // 2, (ch - H) // 2
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                          "-r", str(FPS), "-i", "-", "-vf", "eq=contrast=1.05:saturation=1.08",
                          "-c:v", "libx264", "-preset", "veryfast", "-crf", "14", "-pix_fmt", "yuv420p", str(out)],
                         stdin=subprocess.PIPE)
    n = int(round(dur * FPS))
    hw, hh = W // 2, H // 2
    A = cv2.resize(xx[oy:oy + H, ox:ox + W] - cx, (hw, hh), interpolation=cv2.INTER_AREA)
    B = cv2.resize(yy[oy:oy + H, ox:ox + W] - cy, (hw, hh), interpolation=cv2.INTER_AREA)
    dd = cv2.resize(d[oy:oy + H, ox:ox + W], (hw, hh), interpolation=cv2.INTER_AREA).astype(np.float32)
    P = (0.35 + 0.65 * dd).astype(np.float32)
    for i in range(n):
        q = i / max(1, n - 1)
        e = q * q * (3 - 2 * q)
        dx = direction * move * W * (e - 0.5) * 2
        invz = 1.0 / (1.0 + np.float32(zoom * e) * P)
        mx = cv2.resize(np.float32(cx) + A * invz - np.float32(dx) * dd, (W, H), interpolation=cv2.INTER_LINEAR)
        my = cv2.resize(np.float32(cy) + B * invz, (W, H), interpolation=cv2.INTER_LINEAR)
        fr = cv2.remap(arr, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        p.stdin.write(np.ascontiguousarray(fr).tobytes())
    p.stdin.close()
    p.wait()


def _px(src, out, dur, focus, dr):
    parallax_portrait(src, out, dur, focus=focus, direction=dr)


def build_track(out):
    cache = WORK / "cache"
    cache.mkdir(exist_ok=True)
    parts, todo = [], []
    for i, (name, dur, dr) in enumerate(SEGS):
        p = cache / f"{i}_{name}_{dur:.2f}_{dr}.mp4"
        if not p.exists():
            todo.append((str(FOTO / f"{name}.jpg"), str(p), dur, FOCUS.get(name, 0.5), dr))
        parts.append(str(p))
    from multiprocessing import Pool
    with Pool(2) as pool:
        pool.starmap(_px, todo)
    lst = cache / "l.txt"
    lst.write_text("".join(f"file '{p}'\n" for p in parts))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", out],
                   check=True)


class FullBG:
    def __init__(self, track, outro):
        self.track, self.outro = track, outro
        self.p = self.po = None
        self.nt = self.nto = 0
        y, x = np.mgrid[0:H, 0:W]
        dd = np.sqrt(((x - W / 2) / (W * 0.62)) ** 2 + ((y - H / 2) / (H * 0.64)) ** 2)
        v = np.zeros((H, W, 4), np.uint8)
        v[..., 3] = (np.clip(dd - 0.55, 0, 1) * 300).clip(0, 160).astype(np.uint8)
        self.vig = Image.fromarray(v, "RGBA")
        g = np.zeros((H, W, 4), np.uint8)
        yy = np.arange(H)[:, None]
        g[..., 3] = np.clip((yy - H * 0.5) / (H * 0.5) * 120, 0, 120).astype(np.uint8) + \
            np.clip((H * 0.22 - yy) / (H * 0.22) * 110, 0, 110).astype(np.uint8)
        self.low = Image.fromarray(g, "RGBA")

    def _pipe(self, path, t):
        return subprocess.Popen(["ffmpeg", "-loglevel", "error", "-ss", f"{t:.4f}", "-i", path, "-vf", f"scale={W}:{H}",
                                 "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)

    def _rd(self, which, t):
        p, nt = (self.p, self.nt) if which == 0 else (self.po, self.nto)
        if p is None or abs(t - nt) > 0.5 / FPS:
            if p:
                p.kill()
            p = self._pipe(self.track if which == 0 else self.outro, t)
        buf = p.stdout.read(W * H * 3)
        if which == 0:
            self.p, self.nt = p, t + 1 / FPS
        else:
            self.po, self.nto = p, t + 1 / FPS
        if len(buf) < W * H * 3:
            return Image.new("RGB", (W, H), (10, 10, 14))
        return Image.frombuffer("RGB", (W, H), buf, "raw", "RGB", 0, 1)

    def frame(self, t):
        if t >= OS:
            return self._rd(1, t - OS).convert("RGBA")
        im = self._rd(0, t).convert("RGBA")
        im.alpha_composite(self.vig)
        im.alpha_composite(self.low)
        for st in STARTS[1:-1]:  # kesmede kısa beyaz parlama
            q = t - st
            if 0 <= q < 0.14:
                im.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 255, int(120 * (1 - q / 0.14)))))
        return im


# ---------- Abi (tam boy, beden sabit, yüz canlı) ----------
from abi_yuz import AbiYuz, mix
YUZ = None
AH = round(H * 0.25)                                   # ekran yüksekliğinin dörtte biri


def load_abi():
    global YUZ, SHADOW
    YUZ = AbiYuz()
    sh = Image.new("RGBA", (round(AH * 0.42), round(AH * 0.06)), (0, 0, 0, 0))
    ImageDraw.Draw(sh).ellipse([0, 0, sh.width - 1, sh.height - 1], fill=(0, 0, 0, 130))
    SHADOW = sh.filter(ImageFilter.GaussianBlur(AH * 0.012))


def _env():
    r = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(WORK / "voice_cut.wav"), "-f", "s16le", "-ac", "1",
                        "-ar", "16000", "-"], capture_output=True, check=True)
    x = np.frombuffer(r.stdout, "<i2").astype(float) / 32768
    hop = 16000 // FPS
    e = np.array([np.sqrt(np.mean(x[i:i + hop] ** 2)) for i in range(0, len(x), hop)])
    e = e / (np.percentile(e, 95) + 1e-9)
    return np.convolve(np.clip(e, 0, 1.2), np.ones(2) / 2, mode="same")


ENV = _env()

# yüz ifadesi zaman çizelgesi (konuşmanın anlamına göre)
EXPR_T = [(0.0, "komik"), (t_neden, "merak"), (t_bulas, "saskin"), (T("Birinin"), "yukari"), (t_ust1, "mutlu"),
          (t_kopek, "saskin"), (t_peki, "merak"), (T("Bu", 1), "supheli"), (t_sinir, "saskin"),
          (t_arast, "dusunce"), (t_ve, "supheli"), (t_teker, "mutlu"), (t_ust2, "komik"), (t_sen, "soru"),
          (t_yor, "mutlu")]
t_unut = T("unutma")


def expr_at(t):
    k = max(i for i, (st, _) in enumerate(EXPR_T) if st <= t + 1e-9)
    cur = EXPR_T[k][1]
    prev = EXPR_T[k - 1][1] if k > 0 else cur
    return mix(prev, cur, float(eio(ph(t, EXPR_T[k][0] - 0.12, 0.3))))


def abi(im, t):
    lvl = float(ENV[min(len(ENV) - 1, int(t * FPS))])
    wink = float(math.sin(min(1.0, max(0.0, (t - t_unut - 0.1) / 0.45)) * math.pi))  # sonda göz kırpar
    fig = YUZ.frame(t, level=lvl, expr=expr_at(t), height=AH, wink=wink)
    feet_y = H - round(u(34))
    cx = round(u(45)) + round(174 * AH / 1024)       # gövdenin sol kenarı ekrandan ~45 birim içeride
    comp(im, SHADOW, cx - SHADOW.width / 2, feet_y - SHADOW.height * 0.55)
    comp(im, fig, cx - fig.width * 346 / 687, feet_y - fig.height * 1005 / 1024)


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


def title(L, t, start, end, a_txt, b_txt, col=WHITE, acc=ACC, y=300):
    if not (start <= t < end):
        return
    p = ph(t, start, 0.45) * (1 - ph(t, end - 0.25, 0.25))
    if p <= 0:
        return
    bs = 92
    while bs > 50 and font("black", round(u(bs))).getlength(b_txt) > u(980):
        bs -= 2
    text_c(L, (540, y + (1 - eo(p)) * 30), a_txt, "black", 66, col, alpha=eo(p), stroke=6, stroke_fill=(5, 6, 12))
    text_c(L, (540, y + 92 + (1 - eo(p)) * 30), b_txt, "black", bs, acc, alpha=eo(p), stroke=7, stroke_fill=(5, 6, 12))


def bchip(L, t, start, end, text, y, bg=WHITE, fg=INK, size=46, icon=None):
    if t < start or t >= end:
        return
    chip(L, 540, y, text, bg=bg, fg=fg, size=size, icon_name=icon, k="black",
         scale=eb(ph(t, start, 0.35)) * (1 - eio(ph(t, end - 0.2, 0.2))))


def draw(t):
    L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    if t >= OS:
        chip(L, 540, 1560, "Takip et, kaçırma!", bg=RED, fg=WHITE, size=50, icon_name="bell", k="black",
             scale=eb(ph(t - OS, 0.25, 0.4)))
        return L
    # kanca
    title(L, t, -1.0, t_bulas - 0.1, "Bu videoda en az bir kere", "ESNEYECEKSİN", y=300)  # ilk karede hazır
    lottie(L, "1f971", 860, 600, 170, t, -0.5, end=t_bulas - 0.3)
    # esneme bulaşıcı
    title(L, t, t_bulas, t_ust1 - 0.05, "Esneme", "BULAŞICIDIR", acc=(255, 120, 120), y=300)
    for k, (tt, txt, code) in enumerate([(t_gorm, "Görmek", "1f440"), (t_duy, "Duymak", "1f442"),
                                         (t_oku, "Okumak", None)]):
        if tt <= t < t_ust1:
            a = eb(ph(t, tt, 0.35)) * (1 - eio(ph(t, t_ust1 - 0.2, 0.2)))
            y = 520 + k * 130
            chip(L, 330, y, txt, bg=WHITE, fg=INK, size=50, k="black", scale=a,
                 icon_name="bookmark" if code is None else None)
            if code:
                lottie(L, code, 120, y, 100, t, tt, end=t_ust1 - 0.2)
    # sevdiklerin
    title(L, t, t_ust1, t_kopek - 0.05, "Yabancıdan çok", "SEVDİKLERİNDEN", y=300)
    lottie(L, "2764_fe0f", 540, 650, 190, t, t_sevd, end=t_kopek - 0.25)
    # köpek
    title(L, t, t_kopek, t_peki - 0.05, "Köpekler bile", "SAHİBİNDEN KAPAR!", y=300)
    lottie(L, "1f415", 860, 640, 170, t, t_kopek + 0.2, end=t_peki - 0.25)
    # parmak
    title(L, t, t_peki, t_arast - 0.05, "Parmaklar suda", "NEDEN BURUŞUR?", y=300)
    bchip(L, t, t_sinir - 0.05, t_arast, "Sinir sistemin bilerek yapıyor", 1140, icon=None)
    lottie(L, "1f9e0", 540, 640, 180, t, t_sinir - 0.05, end=t_arast - 0.25)
    title(L, t, t_arast, t_ve - 0.05, "Islak yüzeyde", "DAHA İYİ KAVRAR", acc=(120, 220, 255), y=300)
    bchip(L, t, t_lastik - 0.05, t_ve, "Tıpkı lastik tırtılları gibi", 1140)
    # asansör
    title(L, t, t_ve, t_teker - 0.05, "Asansördeki ayna", "SÜS DEĞİL!", y=300)
    lottie(L, "1f914", 860, 640, 160, t, t_ve + 0.3, end=t_teker - 0.25)
    title(L, t, t_teker, t_ust2 - 0.05, "Tekerlekli sandalyedeki biri", "ARKASINI GÖRSÜN", acc=(120, 220, 255), y=300)
    title(L, t, t_ust2, t_sen - 0.05, "Ayrıca bekleme", "DAHA KISA GELİR", y=300)
    if t_bekl - 0.05 <= t < t_sen:
        put_icon(L, "stopwatch", 540, 680, 200 * eb(ph(t, t_bekl - 0.05, 0.4)), alpha=1 - eio(ph(t, t_sen - 0.25, 0.2)))
    # kapanış
    title(L, t, t_sen, OS, "Sen bunlardan", "HANGİSİNİ BİLİYORDUN?", y=300)
    bchip(L, t, t_yor - 0.05, OS, "Yorumlara yaz!", 1140, size=52, icon="speech_balloon")
    lottie(L, "1f44d", 300, 1000, 150, t, t_beg - 0.1)
    lottie(L, "1f514", 780, 1000, 150, t, t_beg + 0.3)
    return L


class Vid(Video):
    def frame(self, t):
        im = self.bg.frame(t)
        im.alpha_composite(draw(t))
        brand(im, 540, 140)
        if t < OS:
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
    load_abi()
    bg = FullBG(str(track), str(WORK / "outro.mp4"))
    v = Vid([{"start": 0, "end": TOTAL, "draw": lambda *a: None}], words, "", TOTAL, bg=bg)
    if mode == "frames":
        for tt in [float(x) for x in sys.argv[3].split(",")]:
            v.bg.p = None
            v.frame(tt).save(WORK / f"fr_{tt:05.1f}.png")
    else:
        sfx = [(st, "whoosh") for st in STARTS[1:-1]] + [(OS, "whoosh"), (OS + 0.15, "tink"), (t_yor, "pop"),
                                                          (t_beg, "pop")]
        sfx += [(x, "pop") for x in (t_gorm, t_duy, t_oku)]
        at.sfx(str(WORK / "sfx.wav"), TOTAL, sfx)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(WORK / "muzik.wav"), "-af",
                        f"apad,atrim=0:{TOTAL:.3f},afade=t=in:d=0.5,afade=t=out:st={TOTAL - 1.5:.3f}:d=1.5",
                        "-ar", "44100", "-ac", "1", str(WORK / "music.wav")], check=True)
        at.final_mix(str(WORK / "voice_cut.wav"), str(WORK / "music.wav"), str(WORK / "sfx.wav"), str(WORK / "mix.m4a"))
        v.render(str(WORK / "mix.m4a"), str(WORK / "video.mp4"))
        print("render bitti", TOTAL, flush=True)
