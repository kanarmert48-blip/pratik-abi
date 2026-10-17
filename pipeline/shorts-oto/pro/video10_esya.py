"""10. video (2K): Diş macunu karesi, mikrodalga ızgarası, ayakkabıdaki boş delik.
Yeni araçlar: Manim animasyonları, Noto hareketli emojiler, Real-ESRGAN netleştirme, rembg kesik görsel."""
import os
os.environ.setdefault("PA_SCALE", str(4 / 3))  # 1440x2560
import json, math, subprocess, sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from engine import *  # noqa
from widgets import *  # noqa
import audio_tools as at

WORK = Path(sys.argv[1])
N = Path("/home/claude/pratik-abi/media")
words = json.loads((WORK / "words.json").read_text(encoding="utf-8"))
TOTAL = at.duration(str(WORK / "voice_cut.wav"))
OUTRO = 1.9
OS = TOTAL - OUTRO
QRED = (239, 68, 68)
CX0, CY0, CS, BS = 60, 330, 960, 1008  # birim (1080 ölçeği)
P_CX0, P_CY0, P_CS, P_BS = round(u(CX0)), round(u(CY0)), round(u(CS)), round(u(BS))
PANEL = (16, 20, 34)


def T(key, nth=0):
    k = trl(clean(key)).strip('"!?;,')
    hits = [w for w in words if trl(clean(w["w"])).strip('"!?;,') == k]
    return hits[nth]["s"]


def E(key, nth=0):
    k = trl(clean(key)).strip('"!?;,')
    hits = [w for w in words if trl(clean(w["w"])).strip('"!?;,') == k]
    return hits[nth]["e"]


t_yes, t_tam, t_O1, t_mak = T("Yeşilse"), T("Tamamen"), T("O"), T("makine")
t_gel, t_cam, t_O2, t_mik2 = T("Gelelim"), T("Camındaki"), T("O", 1), T("Mikrodalganın")
t_yani, t_kac, t_ve, t_spor = T("Yani"), T("kaçamıyor"), T("Ve"), T("spor")
t_ara, t_cogu, t_O3, t_bag, t_ayag = T("Aramızda"), T("çoğu"), T("O", 3), T("Bağcığı"), T("ayağın")
t_sen, t_yor, t_beg = T("Sen"), T("Yorumlara"), T("beğenmeyi")
Q = [(T("Diş"), E("demek"), t_yes), (t_cam, E("sence"), t_O2), (t_ve, E("orada"), t_ara)]

A = WORK / "assets"
MN = WORK / "mn/videos/sahneler/1344p30"


def ph_(path, pre=""):
    return dict(src=str(path), kind="photo", pre=pre)


def vid(path, ss=0, x=None, pre=None):
    d = dict(src=str(path), kind="video", ss=ss)
    if pre:
        d["pre"] = pre
    elif x is not None:
        d["pre"] = f"crop=ih:ih:{x}:0,"
    return d


SHOE1 = A / "shoe1.png"
SEGS = [dict(ph_(A / "crimp.png"), dur=t_yes),
        dict(vid(N / "v10-esya/macun-v_3.mp4", 0, pre="crop=iw:iw:0:(ih-iw)/2,"), dur=t_O1 - t_yes),
        dict(vid(MN / "Sensor.mp4"), dur=t_gel - t_O1),
        dict(vid(N / "v10b-mikro/mv-food_1.mp4", 1.0, x=240), dur=t_cam - t_gel),
        dict(ph_(A / "tosh.png"), dur=t_O2 - t_cam),
        dict(ph_(A / "toshz.png"), dur=t_mik2 - t_O2),
        dict(vid(MN / "Dalga.mp4"), dur=t_yani - t_mik2),
        dict(ph_(A / "akira.png"), dur=t_ve - t_yani),
        dict(ph_(N / "v10d-ayak/w-peg_5.png", pre="crop=1440:1440:200:0,"), dur=t_spor - t_ve),
        dict(ph_(A / "peg_zoom.png"), dur=t_ara - t_spor),
        dict(vid(N / "v10c-ayak/av-lace_2.mp4", 2.0, pre="crop=ih:ih:1050:0,"), dur=t_O3 - t_ara),
        dict(ph_(A / "peg_zoom.png"), dur=t_sen - t_O3),
        dict(vid(N / "v10-esya/macun-v_2.mp4", 0, pre="crop=iw:iw:0:(ih-iw)/2,"), dur=OS - t_sen)]
STARTS = [sum(s["dur"] for s in SEGS[:i]) for i in range(len(SEGS) + 1)]


def build_track(segs, out):
    import tempfile
    tmp = tempfile.mkdtemp()
    parts = []
    for i, s in enumerate(segs):
        assert s["dur"] > 0, (i, s["dur"])
        p = os.path.join(tmp, f"s{i}.mp4")
        vf = (f"{s.get('pre', '')}scale={P_BS}:{P_BS}:force_original_aspect_ratio=increase:flags=lanczos,crop={P_BS}:{P_BS},"
              f"fps={FPS},eq=contrast=1.04:saturation=1.08,unsharp=5:5:0.4,setsar=1,format=yuv420p")
        n = int(round(s["dur"] * FPS))
        if s["kind"] == "photo":
            inp = ["-loop", "1", "-i", s["src"]]
        else:
            dsrc = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of",
                                         "csv=p=0", s["src"]], capture_output=True, text=True).stdout or 0)
            ss = s.get("ss", 0)
            inp = (["-ss", f"{ss:.3f}", "-i", s["src"]] if dsrc - ss >= s["dur"] + 0.1
                   else ["-stream_loop", "-1", "-i", s["src"]])
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *inp, "-vf", vf, "-an", "-frames:v", str(n),
                        "-c:v", "libx264", "-preset", "veryfast", "-crf", "12", p], check=True)
        parts.append(p)
    lst = os.path.join(tmp, "l.txt")
    open(lst, "w").write("".join(f"file '{p}'\n" for p in parts))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", out],
                   check=True)


class CardBG:
    def __init__(self, track, outro):
        self.track, self.outro = track, outro
        self.p = self.po = None
        self.nt = self.nto = 0
        r = round(u(44))
        m = Image.new("L", (P_CS, P_CS), 0)
        ImageDraw.Draw(m).rounded_rectangle([0, 0, P_CS - 1, P_CS - 1], radius=r, fill=255)
        self.mask = m
        self.shadow = soft_shadow(P_CS, P_CS, r, blur=round(u(30)), op=0.55)
        g = np.zeros((H, W, 4), np.uint8)
        y = np.arange(H)[:, None]
        g[..., :3] = (8, 11, 24)
        g[..., 3] = np.clip(140 + 70 * np.abs(y - u(820)) / u(1100), 0, 225).astype(np.uint8)
        self.dark = Image.fromarray(g, "RGBA")

    def _pipe(self, path, t, size):
        return subprocess.Popen(["ffmpeg", "-loglevel", "error", "-ss", f"{t:.4f}", "-i", path, "-vf",
                                 f"scale={size[0]}:{size[1]}:flags=lanczos", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                                stdout=subprocess.PIPE)

    def _read(self, t):
        if self.p is None or abs(t - self.nt) > 0.5 / FPS:
            if self.p:
                self.p.kill()
            self.p = self._pipe(self.track, t, (P_BS, P_BS))
        buf = self.p.stdout.read(P_BS * P_BS * 3)
        self.nt = t + 1 / FPS
        if len(buf) < P_BS * P_BS * 3:
            return Image.new("RGB", (P_BS, P_BS), (20, 20, 30))
        return Image.frombuffer("RGB", (P_BS, P_BS), buf, "raw", "RGB", 0, 1)

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
        return i, (t - STARTS[i]) / max(SEGS[i]["dur"], 0.01)

    def frame(self, t):
        if t >= OS:
            return self._read_outro(t - OS).convert("RGBA")
        src = self._read(t)
        i, p = self.seg(t)
        z = zoom(i, p)
        cw = (P_BS - u(48)) / z
        c = P_BS / 2
        cardim = src.crop((c - cw / 2, c - cw / 2, c + cw / 2, c + cw / 2)).resize((P_CS, P_CS), Image.BICUBIC)
        bg = src.resize((18, 18), Image.BOX).resize((W, W), Image.BICUBIC)
        bg = bg.resize((W, H), Image.BICUBIC).convert("RGBA")
        bg.alpha_composite(self.dark)
        sh, pad = self.shadow
        comp(bg, sh, P_CX0 - pad, P_CY0 - pad + u(20))
        cr = cardim.convert("RGBA")
        cr.putalpha(self.mask)
        bg.alpha_composite(cr, (P_CX0, P_CY0))
        ImageDraw.Draw(bg).rounded_rectangle([P_CX0 - u(3), P_CY0 - u(3), P_CX0 + P_CS + u(2), P_CY0 + P_CS + u(2)],
                                             radius=u(46), outline=(255, 255, 255, 235), width=round(u(5)))
        dt = t - STARTS[i]
        if i > 0 and dt < 0.12:
            fl = Image.new("RGBA", (P_CS, P_CS), (255, 255, 255, 0))
            fl.putalpha(self.mask.point(lambda v: int(v * 0.5 * (1 - dt / 0.12))))
            bg.alpha_composite(fl, (P_CX0, P_CY0))
        return bg


def zoom(i, p):
    if i == 0:  # kanca: ilk karede hareket — hızlı içeri kayan yakınlaşma
        return 1.0 + 0.10 * (1 - eo(min(1, p * 3.0))) + 0.04 * p
    if SEGS[i]["kind"] == "video" and "sahneler" in SEGS[i]["src"]:
        return 1.0  # Manim: sabit
    return 1 + 0.045 * p


def card_xy(t, px, py):
    """Kart görüntüsündeki konum (0-960 birim, görüntünün tamamına göre) -> ekran birimi (yakınlaşma dahil)."""
    i, p = BGREF.seg(t)
    z = zoom(i, p)
    k = BS / (BS - 48) * z
    return CX0 + CS / 2 + (px - CS / 2) * k, CY0 + CS / 2 + (py - CS / 2) * k


BGREF = None

# ---------- Pratik Abi (sol alt) ----------
AB_FR = None


def _abi_frames():
    global AB_FR
    if AB_FR is None:
        fs = sorted((WORK / "abi").glob("f*.png"))
        Sz = round(u(216))
        m = Image.new("L", (Sz * 4, Sz * 4), 0)
        ImageDraw.Draw(m).ellipse([0, 0, Sz * 4 - 1, Sz * 4 - 1], fill=255)
        m = m.resize((Sz, Sz), Image.LANCZOS)
        b = round(u(8))

        def mk(p):
            im = Image.open(p).convert("RGBA").resize((Sz, Sz), Image.LANCZOS)
            im.putalpha(m)
            out = Image.new("RGBA", (Sz + 2 * b, Sz + 2 * b), (0, 0, 0, 0))
            ImageDraw.Draw(out).ellipse([0, 0, Sz + 2 * b - 1, Sz + 2 * b - 1], fill=ACC + (255,))
            out.alpha_composite(im, (b, b))
            return out
        AB_FR = [mk(p) for p in fs], mk(WORK / "abi" / "blink.png")
    return AB_FR


def _env():
    r = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(WORK / "voice_cut.wav"), "-f", "s16le", "-ac", "1",
                        "-ar", "16000", "-"], capture_output=True, check=True)
    x = np.frombuffer(r.stdout, "<i2").astype(float) / 32768
    hop = 16000 // FPS
    e = np.array([np.sqrt(np.mean(x[i:i + hop] ** 2)) for i in range(0, len(x), hop)])
    e = e / (np.percentile(e, 95) + 1e-9)
    return np.convolve(np.clip(e, 0, 1.2), np.ones(3) / 3, mode="same")


ENV = _env()
AX, AY = u(172), u(1575)


def abi(im, t):
    frs, blink = _abi_frames()
    n = len(frs)
    k = int(t * FPS) % (2 * n - 2)
    k = k if k < n else 2 * n - 2 - k
    img = blink if (t % 5.2) < 0.14 else frs[k]
    lvl = float(ENV[min(len(ENV) - 1, int(t * FPS))])
    s = 1 + 0.06 * lvl
    im2 = img.resize((int(img.width * s), int(img.height * s)), Image.BICUBIC)
    im2 = im2.rotate(3 * math.sin(t * 2.1), resample=Image.BICUBIC, expand=True)
    sh, pad = soft_shadow(img.width, img.height, img.width // 2, blur=round(u(16)), op=0.5)
    comp(im, sh, AX - img.width / 2 - pad, AY - img.height / 2 - pad + u(12))
    comp(im, im2, AX - im2.width / 2, AY - im2.height / 2)
    d = ImageDraw.Draw(im)
    for k2 in range(2):  # ses dalgası
        rr = u(130 + k2 * 22 + 12 * lvl)
        d.arc([AX - rr, AY - rr, AX + rr, AY + rr], -40, 30, fill=ACC + (int(200 - 70 * k2),), width=round(u(7)))


# ---------- hareketli emoji (Noto Lottie) ----------
_LOT = {}


def lottie(L, code, cx, cy, size, t, start, end=None, rot=0.0):
    """Hareketli emoji: start'ta zıplayarak gelir, end'de küçülerek gider (birim koordinat)."""
    if t < start or (end is not None and t > end + 0.3):
        return
    if code not in _LOT:
        from ai_tools import Lottie
        _LOT[code] = Lottie(code)
    sc = eb(ph(t, start, 0.4))
    if end is not None:
        sc *= 1 - eio(ph(t, end, 0.3))
    px = int(u(size))
    if sc <= 0.02 or px < 8:
        return
    fr = _LOT[code].frame(t - start, px)
    if abs(sc - 1) > 0.01:
        fr = fr.resize((max(1, int(px * sc)), max(1, int(px * sc))), Image.BICUBIC)
    if rot:
        fr = fr.rotate(rot, resample=Image.BICUBIC, expand=True)
    sh = Image.new("RGBA", fr.size, (0, 0, 0, 0))
    sh.putalpha(fr.getchannel("A").point(lambda v: int(v * 0.35)))
    sh = sh.filter(ImageFilter.GaussianBlur(u(8)))
    comp(L, sh, u(cx) - fr.width / 2, u(cy) - fr.height / 2 + u(10))
    comp(L, fr, u(cx) - fr.width / 2, u(cy) - fr.height / 2)


# ---------- ortak parçalar ----------
def quiz(L, t, i, label):
    qs, qe, ans = Q[i]
    if qs - 0.1 <= t < ans - 0.05:
        chip(L, 540, CY0 + CS - 70, label, bg=WHITE, fg=INK, size=46, k="black", scale=eb(ph(t, qs - 0.1, 0.35)))
    if qe <= t < ans:
        p = (t - qe) / max(ans - qe, 0.1)
        cx, cy, r = u(CX0 + CS - 90), u(CY0 + 90), u(56)
        d = ImageDraw.Draw(L)
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(14, 18, 32, 230))
        d.arc([cx - r, cy - r, cx + r, cy + r], -90, -90 + 360 * (1 - p), fill=ACC + (255,), width=round(u(10)))
        text_c(L, (CX0 + CS - 90, CY0 + 92), str(max(1, math.ceil((1 - p) * 3))), "black", 52, WHITE)


def bottom_chip(L, t, start, text, bg=GREEN, fg=WHITE, size=46, icon=None, y=None, end=None):
    if t < start or (end is not None and t >= end):
        return
    chip(L, 540, y or (CY0 + CS - 70), text, bg=bg, fg=fg, size=size, icon_name=icon, k="black",
         scale=eb(ph(t, start, 0.35)))


def myth(L, t):
    """'Yeşil doğal, siyah kimyasal' söylentisi tablosu."""
    a = eo(ph(t, t_yes - 0.05, 0.35))
    if a <= 0:
        return
    x0, y0, w, h = CX0 + 90, CY0 + 110, CS - 180, 600
    card(L, x0, y0, w, h, r=40, fill=(14, 18, 32, 228), outline=(255, 255, 255, 50), width=2, alpha=a)
    text_c(L, (540, y0 + 72), "Söylenti:", "black", 46, (200, 208, 228), alpha=a)
    rows = [((46, 204, 113), "Doğal"), ((59, 130, 246), "Doğal + ilaç"), ((239, 68, 68), "Doğal + kimyasal"),
            ((25, 25, 30), "Kimyasal")]
    d = ImageDraw.Draw(L)
    for k, (col, lab) in enumerate(rows):
        q = eo(ph(t, t_yes + 0.15 + k * 0.32, 0.3))
        if q <= 0:
            continue
        yy = y0 + 165 + k * 108
        sx = x0 + 120 + (1 - q) * 40
        d.rounded_rectangle([u(sx), u(yy - 36), u(sx + 72), u(yy + 36)], radius=u(10), fill=col + (int(255 * q),),
                            outline=(255, 255, 255, int(200 * q)), width=round(u(3)))
        text_c(L, (sx + 110, yy), "=  " + lab, "xb", 50, WHITE, anchor="lm", alpha=q)
    if t >= t_tam:
        stamp(L, 540, y0 + 330, "UYDURMA!", QRED, t, t_tam, rot=-9, size=120)


# ---------- sahneler ----------
def s1(v, sc, L, t, dur):
    headline(L, [("Tüpteki", False), ("renkli kare?", True)], t, y0=200, size=76, start=-1)
    if t < t_yes:  # göz işareti: ok
        tip = card_xy(t, 0.466 * 960, 0.228 * 960)
        frm = card_xy(t, 0.80 * 960, 0.62 * 960)
        arrow(L, t, 0.12, frm, tip, bend=-0.28, col=ACC, dur=0.45)
    quiz(L, t, 0, "Sence ne demek?")
    lottie(L, "1f914", CX0 + 120, CY0 + 120, 170, t, E("demek") - 0.5, end=t_yes)
    if t_yes <= t < t_O1:
        myth(L, t)
    if t >= t_O1:
        lottie(L, "1f4a1", CX0 + 115, CY0 + 115, 160, t, t_O1 + 0.1)
        bottom_chip(L, t, t_mak, "Makine için kesim işareti", bg=GREEN, size=44)


def s2(v, sc, L, t, dur):
    headline(L, [("Mikrodalga", False), ("ızgarası?", True)], t, y0=200, size=76)
    if t_cam <= t < t_O2:
        tip = card_xy(t, 0.46 * 960, 0.42 * 960)
        frm = card_xy(t, 0.80 * 960, 0.80 * 960)
        arrow(L, t, t_cam + 0.15, frm, tip, bend=0.25, col=WHITE, dur=0.45)
        lottie(L, "1f914", CX0 + 120, CY0 + 120, 170, t, E("sence") - 0.4, end=t_O2)
    quiz(L, t, 1, "Sence ne işe yarar?")
    if t_O2 <= t < t_mik2:
        bottom_chip(L, t, t_O2 + 0.05, "Metal bir kalkan!", bg=GREEN, icon="sparkles")
        lottie(L, "1f4a1", CX0 + 120, CY0 + 120, 160, t, t_O2 + 0.1, end=t_mik2 - 0.3)
    if t >= t_yani:
        lottie(L, "1f440", CX0 + CS - 120, CY0 + 120, 170, t, t_yani + 0.1)
        bottom_chip(L, t, t_yani + 0.25, "İçerisi görünür", bg=WHITE, fg=INK, icon="check_mark_button", y=CY0 + CS - 175)
        bottom_chip(L, t, t_kac - 0.05, "Dalga kaçamaz", bg=GREEN, icon="check_mark_button")


def P2C(x, y):
    """Pegasus yakın çekim fotoğrafındaki piksel -> kart birimi (0-960)."""
    return (x - 500) / 800 * 960, (y - 250) / 800 * 960


SLOT = P2C(832, 616)
LOOP0 = [P2C(*q) for q in [(868, 590), (915, 650), (890, 738), (815, 748), (774, 682), (832, 616)]]
LOOP1 = [P2C(*q) for q in [(868, 590), (884, 622), (862, 655), (834, 652), (826, 632), (832, 616)]]
CY_0 = [P2C(*q) for q in [(1005, 410), (935, 525), (880, 630), (848, 690), (812, 728), (755, 620), (730, 470)]]
CY_1 = [P2C(*q) for q in [(1005, 410), (940, 515), (885, 600), (852, 636), (828, 648), (770, 570), (745, 460)]]


def _smooth(pts, n=14):
    out = []
    P = [pts[0]] + pts + [pts[-1]]
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for k in range(n):
            s_ = k / n
            out.append(tuple(0.5 * ((2 * p1[j]) + (-p0[j] + p2[j]) * s_ + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * s_ ** 2
                                    + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * s_ ** 3) for j in range(2)))
    out.append(pts[-1])
    return out


def lace(L, t, pts, frac=1.0, col=ACC, width=15, sub=None):
    """Kart birimindeki noktalardan geçen bağcık (koyu kenarlı, kalın). frac: çizilen oran."""
    if frac <= 0:
        return
    sm = _smooth([card_xy(t, x, y) for x, y in pts])
    if sub:
        sm = sm[int(len(sm) * sub[0]):int(len(sm) * sub[1]) + 1]
    sm = sm[:max(2, int(len(sm) * frac))]
    SS = 2
    xs, ys = [u(q[0]) for q in sm], [u(q[1]) for q in sm]
    m = u(40)
    bx0, by0 = int(min(xs) - m), int(min(ys) - m)
    w, h = int(max(xs) + m) - bx0, int(max(ys) + m) - by0
    big = Image.new("RGBA", (w * SS, h * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(big)
    P = [((x - bx0) * SS, (y - by0) * SS) for x, y in zip(xs, ys)]
    for wd, c in ((u(width + 9), (20, 22, 30, 255)), (u(width), col + (255,))):
        lw = int(wd * SS)
        d.line(P, fill=c, width=lw, joint="curve")
        for q in (P[0], P[-1]):
            d.ellipse([q[0] - lw / 2, q[1] - lw / 2, q[0] + lw / 2, q[1] + lw / 2], fill=c)
    small = big.resize((w, h), Image.LANCZOS)
    comp(L, small, bx0, by0)


def lerp_pts(a, b, q):
    return [(lerp(p[0], r[0], q), lerp(p[1], r[1], q)) for p, r in zip(a, b)]


def tag(L, t, start, text, px, py, col=WHITE, fg=INK, size=38, end=None):
    if t < start or (end is not None and t >= end):
        return
    x, y = card_xy(t, px, py)
    chip(L, x, y, text, bg=col, fg=fg, size=size, k="black", scale=eb(ph(t, start, 0.35)))


def heel_lock(L, t):
    t0 = t_bag + 0.05
    t_loop, t_cy, t_tight = t0, t0 + 1.75, t0 + 2.75
    q = eio(ph(t, t_tight, 0.6))
    loop = lerp_pts(LOOP0, LOOP1, q)
    cy = lerp_pts(CY_0, CY_1, q)
    lace(L, t, loop, frac=eo(ph(t, t_loop, 1.3)), col=ACC)
    if t >= t_cy:
        lace(L, t, cy, frac=eo(ph(t, t_cy, 0.9)), col=(56, 189, 248))
        if ph(t, t_cy, 0.9) > 0.75:  # ilmekten geçiyor görünümü: ilmeğin alt kolu üstte
            lace(L, t, loop, col=ACC, sub=(0.55, 0.85))
    tag(L, t, t_loop + 1.55, "İlmek", *P2C(960, 735), col=ACC, end=t_cy)
    tag(L, t, t_cy + 0.1, "Karşı ucu ilmekten geçir", *P2C(900, 320), col=(56, 189, 248), size=34, end=t_tight + 0.1)
    if t >= t_tight:
        for ex in (CY_1[-1], ):
            x, y = card_xy(t, *ex)
            arrow(L, t, t_tight + 0.1, (x, y + 10), (x - 10, y - 120), bend=0.0, col=GREEN, width=10, dur=0.35)
        x, y = card_xy(t, *P2C(1005, 410))
        arrow(L, t, t_tight + 0.1, (x, y + 10), (x + 30, y - 110), bend=0.0, col=GREEN, width=10, dur=0.35)
        tag(L, t, t_tight + 0.15, "Sıkıca çek", *P2C(1010, 520), col=GREEN, fg=WHITE, size=36)


def s3(v, sc, L, t, dur):
    headline(L, [("Ayakkabıda", False), ("boş delik?", True)], t, y0=200, size=76)
    sx, sy = SLOT
    if t_spor <= t < t_ara:
        arrow(L, t, T("boş") - 0.35, card_xy(t, sx + 330, sy + 330), card_xy(t, sx, sy), bend=0.25, col=ACC, dur=0.45)
        tag(L, t, T("boş") + 0.1, "Boş delik", sx + 420, sy + 330, col=ACC, size=34)
    if t < t_ara:
        lottie(L, "1f914", CX0 + 120, CY0 + 120, 150, t, E("orada") - 0.6, end=t_ara)
    quiz(L, t, 2, "Sence neden orada?")
    if t_ara <= t < t_O3:
        lottie(L, "1f92b", CX0 + CS - 120, CY0 + 125, 180, t, t_ara + 0.05, end=t_O3 - 0.2)
        bottom_chip(L, t, t_cogu, "Çoğu kişi kullanmıyor", bg=WHITE, fg=INK, size=44)
    if t_O3 <= t < t_bag + 0.1:
        arrow(L, t, t_O3 + 0.05, card_xy(t, sx + 330, sy + 330), card_xy(t, sx, sy), bend=0.25, col=ACC, dur=0.4)
    if t >= t_O3:
        bottom_chip(L, t, t_O3 + 0.2, "Topuk kilidi!", bg=GREEN, icon="sparkles", end=t_bag + 2.9)
    if t >= t_bag:
        heel_lock(L, t)
        bottom_chip(L, t, t_bag + 2.95, "Topuk kaymaz", bg=GREEN, icon="check_mark_button", y=CY0 + CS - 175)
        bottom_chip(L, t, t_ayag, "Daha az su toplar", bg=WHITE, fg=INK, icon="check_mark_button")
    if t >= t_ayag:
        lottie(L, "1f44d", CX0 + 120, CY0 + 120, 150, t, t_ayag)


def s_end(v, sc, L, t, dur):
    if t >= OS:
        lt = t - OS
        chip(L, 540, 1560, "Takip et, kaçırma!", bg=RED, fg=WHITE, size=50, icon_name="bell", k="black",
             scale=eb(ph(lt, 0.25, 0.4)))
        return
    headline(L, [("Hangisini", False), ("biliyordun?", True)], t, y0=200, size=80)
    q = ph(t, t_sen + 0.05, 0.4)
    glass(L, CX0 + 70, CY0 + 90, CS - 140, 470, alpha=eo(q))
    thumbs = END_THUMBS
    for k, im in enumerate(thumbs):
        qq = eb(ph(t, t_sen + 0.15 + k * 0.18, 0.4))
        if qq <= 0.02:
            continue
        cx, cy, r = 260 + k * 280, CY0 + 270, 110
        rr = int(u(r) * qq)
        th = im.resize((2 * rr, 2 * rr), Image.LANCZOS)
        m = Image.new("L", th.size, 0)
        ImageDraw.Draw(m).ellipse([0, 0, th.width - 1, th.height - 1], fill=255)
        th.putalpha(m)
        ring = Image.new("RGBA", (th.width + round(u(12)), th.height + round(u(12))), (0, 0, 0, 0))
        ImageDraw.Draw(ring).ellipse([0, 0, ring.width - 1, ring.height - 1], fill=WHITE + (255,))
        comp(L, ring, u(cx) - ring.width / 2, u(cy) - ring.height / 2)
        comp(L, th, u(cx) - th.width / 2, u(cy) - th.height / 2)
        qm = "?" if int((t + k * 0.3) * 2.2) % 2 == 0 else "?"
        text_c(L, (cx, cy + 165), ["Kare", "Izgara", "Delik"][k], "black", 44, WHITE, alpha=min(1, qq))
    bottom_chip(L, t, t_yor - 0.05, "Yorumlara yaz!", bg=WHITE, fg=INK, size=50, y=CY0 + 700)
    lottie(L, "1f4ac", 250, CY0 + 700, 130, t, t_yor - 0.05)
    lottie(L, "1f44d", 380, CY0 + 855, 170, t, t_beg - 0.1, rot=-6)
    lottie(L, "1f514", 700, CY0 + 855, 170, t, t_beg + 0.35)


starts = [0.0, t_gel, t_ve, t_sen]
draws = [s1, s2, s3, s_end]
scenes = [{"start": s, "end": (starts[i + 1] if i + 1 < len(starts) else TOTAL), "draw": d}
          for i, (s, d) in enumerate(zip(starts, draws))]

END_THUMBS = []


class Vid(Video):
    def frame(self, t):
        im = self.bg.frame(t)
        for i, sc in enumerate(self.scenes):
            if sc["start"] <= t < sc["end"] or (i == len(self.scenes) - 1 and t >= sc["start"]):
                lt, dur = t - sc["start"], sc["end"] - sc["start"]
                layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                sc["draw"](self, sc, layer, t, dur)  # mutlak zaman
                pin = 1.0 if i == 0 else eo(ph(lt, 0, 0.3))
                pout = eio(ph(lt, dur - 0.2, 0.2)) if i < len(self.scenes) - 1 else 0
                a = pin * (1 - pout)
                if a < 0.999:
                    layer = set_alpha(layer, a)
                comp(im, layer, 0, u((1 - pin) * 60 - pout * 60))
                break
        brand(im, 540, 140)
        if t < OS:
            draw_caption(im, self.groups, t, y=1395)
            abi(im, t)
        return im.convert("RGB")


if __name__ == "__main__":
    mode = sys.argv[2] if len(sys.argv) > 2 else "render"
    END_THUMBS += [Image.open(A / n).convert("RGBA").resize((400, 400), Image.LANCZOS)
                   for n in ("crimp.png", "akira.png", "shoe_thumb.png")]
    if not (WORK / "card.mp4").exists():
        build_track(SEGS, str(WORK / "card.mp4"))
    BGREF = CardBG(str(WORK / "card.mp4"), str(WORK / "outro.mp4"))
    v = Vid(scenes, words, "", TOTAL, bg=BGREF)
    if mode == "frames":
        for tt in [float(x) for x in sys.argv[3].split(",")]:
            v.bg.p = None
            v.frame(tt).save(WORK / f"fr_{tt:05.1f}.png")
    elif mode == "render":
        sfx = [(s["start"], "whoosh") for s in scenes[1:]] + [(OS, "whoosh"), (OS + 0.15, "tink")]
        for qs, qe, ans in Q:
            sfx += [(qs + 0.05, "pop"), (ans - 0.05, "ding")]
        sfx += [(t_tam, "pop"), (t_O1, "pop"), (t_ara, "pop"), (t_O3, "ding"), (t_yor, "pop"), (t_beg, "pop")]
        at.music(str(WORK / "music.wav"), TOTAL, bpm=92, style="lofi")
        at.sfx(str(WORK / "sfx.wav"), TOTAL, sfx)
        at.final_mix(str(WORK / "voice_cut.wav"), str(WORK / "music.wav"), str(WORK / "sfx.wav"), str(WORK / "mix.m4a"))
        v.render(str(WORK / "mix.m4a"), str(WORK / "video.mp4"))
        print("render bitti", TOTAL, flush=True)
