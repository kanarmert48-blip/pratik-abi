"""11. video (2K): Eşyalar konuşsaydı — çaydanlık, telefon, buzdolabı dert yanıyor, Pratik Abi çözüyor.
Araçlar: rembg (karakter kesikleri), Depth Anything (3D hareketli arka planlar), Real-ESRGAN, CLIP (görsel seçimi),
Wav2Lip (konuşan Abi), MusicGen (müzik), Noto Lottie (hareketli emojiler), faster-whisper (zamanlama)."""
import os
os.environ.setdefault("PA_SCALE", str(4 / 3))
import json, math, subprocess, sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from engine import *  # noqa
from widgets import *  # noqa
import audio_tools as at
from talk_face import face

WORK = Path(sys.argv[1])
A = WORK / "assets"
words = json.loads((WORK / "words.json").read_text(encoding="utf-8"))
SEG = json.loads((WORK / "segs.json").read_text())
TOTAL = at.duration(str(WORK / "voice_cut.wav"))
OUTRO = 1.9
OS = TOTAL - OUTRO
CX0, CY0, CS, BS = 60, 330, 960, 1008
P_CX0, P_CY0, P_CS, P_BS = round(u(CX0)), round(u(CY0)), round(u(CS)), round(u(BS))
QRED = (239, 68, 68)
BLUE = (56, 189, 248)


def T(key, nth=0):
    k = trl(clean(key)).strip('"!?;,')
    hits = [w for w in words if trl(clean(w["w"])).strip('"!?;,') == k]
    return hits[nth]["s"]


S = {s["name"]: s for s in SEG}
t_cay0, t_abi1 = S["01_cay"]["s"], S["02_abi"]["s"]
t_tel0, t_abi2 = S["03_tel"]["s"], S["04_abi"]["s"]
t_buz0, t_abi3 = S["05_buz"]["s"], S["06_abi"]["s"]
t_end = S["07_abi"]["s"]
t_tad, t_gec, t_yar, t_iki = T("tadını"), T("geç"), T("Yarısına"), T("iki")
t_kayn, t_yarim, t_dur, t_piril = T("Kaynat"), T("yarım"), T("durula"), T("Pırıl")
t_cok, t_lit, t_dolu, t_ayar, t_kor, t_sarj = T("Çok"), T("Lityum"), T("dolu"), T("Ayarlardan"), T("korumayı"), T("şarj")
t_sicak, t_kapak, t_isinan, t_sutu, t_kapakta = T("sıcak"), T("Kapak"), T("ısınan"), T("Sütü", 1), T("kapakta")
t_yor, t_beg = T("Yorumlara"), T("beğenmeyi")


def vid(path, ss=0):
    return dict(src=str(path), kind="video", ss=ss)


def photo(path):
    return dict(src=str(path), kind="photo")


SEGS = [dict(vid(A / "bg_cay.mp4"), dur=t_abi1),
        dict(vid(A / "kirec.mp4"), dur=t_yar - t_abi1),
        dict(vid(A / "limon.mp4"), dur=t_kayn - t_yar),
        dict(vid(A / "bg_cay.mp4", 0.2), dur=t_tel0 - t_kayn),
        dict(photo(A / "night.png"), dur=t_abi2 - t_tel0),
        dict(vid(A / "tel6.mp4"), dur=t_ayar - t_abi2),
        dict(photo(A / "night.png"), dur=t_buz0 - t_ayar),
        dict(vid(A / "bg_buz.mp4"), dur=t_kapak - t_buz0),
        dict(vid(A / "buz6.mp4"), dur=t_sutu - t_kapak),
        dict(vid(A / "buz1.mp4"), dur=t_end - t_sutu),
        dict(vid(A / "bg_end.mp4"), dur=OS - t_end)]
STARTS = [sum(s["dur"] for s in SEGS[:i]) for i in range(len(SEGS) + 1)]


def build_track(segs, out):
    import tempfile
    tmp = tempfile.mkdtemp()
    parts = []
    for i, s in enumerate(segs):
        assert s["dur"] > 0, (i, s["dur"])
        p = os.path.join(tmp, f"s{i}.mp4")
        vf = (f"scale={P_BS}:{P_BS}:force_original_aspect_ratio=increase:flags=lanczos,crop={P_BS}:{P_BS},"
              f"fps={FPS},eq=contrast=1.03:saturation=1.08,setsar=1,format=yuv420p")
        n = int(round(s["dur"] * FPS))
        if s["kind"] == "photo":
            inp = ["-loop", "1", "-i", s["src"]]
        else:
            dsrc = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of",
                                         "csv=p=0", s["src"]], capture_output=True, text=True).stdout or 0)
            ss = s.get("ss", 0)
            inp = (["-ss", f"{ss:.3f}", "-i", s["src"]] if dsrc - ss >= s["dur"] + 0.05
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
        z = 1 + (0.03 * p if SEGS[i]["kind"] == "photo" else 0)
        cw = (P_BS - u(48)) / z
        c = P_BS / 2
        cardim = src.crop((c - cw / 2, c - cw / 2, c + cw / 2, c + cw / 2)).resize((P_CS, P_CS), Image.BICUBIC)
        bg = src.resize((18, 18), Image.BOX).resize((W, W), Image.BICUBIC).resize((W, H), Image.BICUBIC).convert("RGBA")
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


def card_xy(t, px, py):
    i, p = BGREF.seg(t)
    z = 1 + (0.03 * p if SEGS[i]["kind"] == "photo" else 0)
    k = BS / (BS - 48) * z
    return CX0 + CS / 2 + (px - CS / 2) * k, CY0 + CS / 2 + (py - CS / 2) * k


BGREF = None


# ---------- ses seviyesi ----------
def _env(path):
    r = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(path), "-f", "s16le", "-ac", "1", "-ar", "16000", "-"],
                       capture_output=True, check=True)
    x = np.frombuffer(r.stdout, "<i2").astype(float) / 32768
    hop = 16000 // FPS
    e = np.array([np.sqrt(np.mean(x[i:i + hop] ** 2)) for i in range(0, len(x), hop)])
    e = e / (np.percentile(e, 95) + 1e-9)
    return np.convolve(np.clip(e, 0, 1.2), np.ones(3) / 3, mode="same")


ENV = _env(WORK / "voice_cut.wav")


def lvl(t):
    return float(ENV[min(len(ENV) - 1, max(0, int(t * FPS)))])


def who(t):
    for s in SEG:
        if s["s"] - 0.05 <= t < s["e"] + 0.05:
            return s["who"]
    return None


# ---------- konuşan Abi (Wav2Lip) ----------
AB_FR = None
AX, AY = u(172), u(1575)


def load_abi():
    global AB_FR
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
    AB_FR = (raw, n, Sz, m, ring)


def abi(im, t):
    raw, n, Sz, m, ring = AB_FR
    i = min(n - 1, int(t * FPS))
    fr = Image.frombuffer("RGB", (Sz, Sz), raw[i * Sz * Sz * 3:(i + 1) * Sz * Sz * 3], "raw", "RGB", 0, 1).convert("RGBA")
    fr.putalpha(m)
    img = ring.copy()
    b = (img.width - Sz) // 2
    img.alpha_composite(fr, (b, b))
    speaking = who(t) == "abi"
    l = lvl(t) if speaking else 0.0
    s = 1 + 0.05 * l
    im2 = img.resize((int(img.width * s), int(img.height * s)), Image.BICUBIC)
    im2 = im2.rotate(2.5 * math.sin(t * 2.1), resample=Image.BICUBIC, expand=True)
    sh, pad = soft_shadow(img.width, img.height, img.width // 2, blur=round(u(16)), op=0.5)
    comp(im, sh, AX - img.width / 2 - pad, AY - img.height / 2 - pad + u(12))
    comp(im, im2, AX - im2.width / 2, AY - im2.height / 2)
    if speaking:
        d = ImageDraw.Draw(im)
        for k2 in range(2):
            rr = u(130 + k2 * 22 + 12 * l)
            d.arc([AX - rr, AY - rr, AX + rr, AY + rr], -40, 30, fill=ACC + (int(200 - 70 * k2),), width=round(u(7)))


# ---------- hareketli emoji ----------
_LOT = {}


def lottie(L, code, cx, cy, size, t, start, end=None, rot=0.0):
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
    comp(L, fr, u(cx) - fr.width / 2, u(cy) - fr.height / 2)


# ---------- konuşan eşya karakterleri ----------
CH = {  # kesik, yüz konumu (oran), yüz boyu (genişlik oranı), göz kapağı rengi
    "cay": ("ch_cay.png", (0.33, 0.70), 0.36, (70, 70, 78)),
    "tel": ("ch_tel.png", (0.48, 0.56), 0.40, (24, 24, 30)),
    "buz": ("ch_buz.png", (0.50, 0.43), 0.46, (226, 218, 196)),
}
_CHC = {}


def char_img(name, hpx):
    k = (name, hpx)
    if k not in _CHC:
        im = Image.open(A / CH[name][0]).convert("RGBA")
        _CHC[k] = im.resize((max(1, round(im.width * hpx / im.height)), hpx), Image.LANCZOS)
    return _CHC[k]


def character(L, t, name, cx, cy_bottom, h, start, mood="normal", look=(0, 0), end=None, sparkle=False):
    """cx, cy_bottom, h: birim. Eşya konuşurken zıplar; yüz sesle oynar."""
    if t < start or (end is not None and t >= end + 0.25):
        return
    pin = eb(ph(t, start, 0.45))
    pout = 1 - eio(ph(t, end, 0.25)) if end is not None else 1
    sc = pin * pout
    if sc <= 0.03:
        return
    speaking = who(t) == name
    l = lvl(t) if speaking else 0.0
    hop = abs(math.sin(t * 9)) * 10 * l
    breath = 1 + 0.012 * math.sin(t * 2.4)
    hpx = round(u(h) * sc * breath * (1 + 0.03 * l))
    im = char_img(name, max(8, hpx // 4 * 4))
    rot = (2.5 * math.sin(t * 7) * l) if speaking else 0.8 * math.sin(t * 1.3)
    # yüz
    fx, fy = CH[name][1]
    fs = im.width * CH[name][2]
    lay = im.copy()
    face(lay, im.width * fx, im.height * fy, fs, t, level=l, mood=mood, look=look, blink_seed=hash(name) % 7,
         lid=CH[name][3])
    if rot:
        lay = lay.rotate(rot, resample=Image.BICUBIC, expand=True, center=(lay.width / 2, lay.height))
    # gölge
    sw = lay.width * 0.8
    shd = Image.new("RGBA", (int(sw), int(u(40))), (0, 0, 0, 0))
    ImageDraw.Draw(shd).ellipse([0, 0, shd.width - 1, shd.height - 1], fill=(0, 0, 0, 110))
    shd = shd.filter(ImageFilter.GaussianBlur(u(10)))
    comp(L, shd, u(cx) - shd.width / 2, u(cy_bottom) - shd.height / 2)
    comp(L, lay, u(cx) - lay.width / 2, u(cy_bottom) - u(hop) - lay.height)
    if sparkle:
        for k, (dx, dy) in enumerate([(-0.42, -0.85), (0.38, -0.6), (-0.2, -0.35)]):
            lottie(L, "2728", cx + dx * h, cy_bottom + dy * h, 110 - k * 15, t, sparkle + k * 0.15)


def name_tag(L, t, start, end, text, col):
    if start <= t < end:
        chip(L, 540, CY0 + 62, text, bg=col, fg=WHITE, size=40, k="black",
             scale=eb(ph(t, start, 0.35)) * (1 - eio(ph(t, end - 0.2, 0.2))))


def bottom_chip(L, t, start, text, bg=GREEN, fg=WHITE, size=44, icon=None, y=None, end=None):
    if t < start or (end is not None and t >= end):
        return
    chip(L, 540, y or (CY0 + CS - 70), text, bg=bg, fg=fg, size=size, icon_name=icon, k="black",
         scale=eb(ph(t, start, 0.35)))


def battery(L, cx, cy, w, frac, col, alpha=1.0, label=None):
    """Pil simgesi (birim)."""
    h = w * 0.48
    d = ImageDraw.Draw(L)
    x0, y0 = u(cx - w / 2), u(cy - h / 2)
    x1, y1 = u(cx + w / 2), u(cy + h / 2)
    a = int(255 * alpha)
    d.rounded_rectangle([x0, y0, x1, y1], radius=u(h * 0.18), outline=(255, 255, 255, a), width=round(u(w * 0.045)))
    d.rounded_rectangle([x1 + u(4), u(cy - h * 0.18), x1 + u(w * 0.07), u(cy + h * 0.18)], radius=u(6),
                        fill=(255, 255, 255, a))
    pad = u(w * 0.07)
    fw = (x1 - x0 - 2 * pad) * max(0.0, min(1.0, frac))
    if fw > 2:
        d.rounded_rectangle([x0 + pad, y0 + pad, x0 + pad + fw, y1 - pad], radius=u(h * 0.1), fill=col + (a,))
    if label:
        text_c(L, (cx, cy + 2), label, "black", w * 0.22, WHITE, alpha=alpha, stroke=4, stroke_fill=(10, 12, 20))


# ---------- sahneler ----------
def s_cay(v, sc, L, t, dur):
    headline(L, [("Eşyalar", False), ("konuşsaydı…", True)], t, y0=200, size=78, start=-1)
    name_tag(L, t, 0.0, t_abi1 - 0.1, "ÇAYDANLIK", (214, 64, 52))
    if t < t_abi1:
        character(L, t, "cay", 540, CY0 + 905, 760, -1, mood="angry", look=(0.15, 0.1))
        lottie(L, "1f624", CX0 + CS - 120, CY0 + 140, 170, t, T("Dibime") - 0.1)
    elif t < t_yar:  # kireç fotoğrafı
        arrow(L, t, t_abi1 + 0.6, card_xy(t, 0.85 * 960, 0.30 * 960), card_xy(t, 0.567 * 960, 0.66 * 960), bend=0.28,
              col=ACC)
        bottom_chip(L, t, t_tad - 0.05, "Tadı bozar", bg=QRED, y=CY0 + CS - 175)
        bottom_chip(L, t, t_gec - 0.05, "Geç kaynatır", bg=QRED)
    elif t < t_kayn:  # limon tuzu
        arrow(L, t, t_iki - 0.3, card_xy(t, 0.2 * 960, 0.25 * 960), card_xy(t, 0.64 * 960, 0.62 * 960), bend=-0.25,
              col=ACC)
        bottom_chip(L, t, t_yar + 0.2, "Yarısı su", bg=WHITE, fg=INK, y=CY0 + CS - 175)
        bottom_chip(L, t, t_iki - 0.05, "+ 2 kaşık limon tuzu", bg=GREEN)
    else:  # kaynat, beklet, durula -> pırıl pırıl
        happy = t >= t_piril - 0.1
        character(L, t, "cay", 540, CY0 + 830, 640, t_kayn - 0.05, mood="happy" if happy else "normal",
                  sparkle=(t_piril - 0.05) if happy else False)
        steps = [(t_kayn, "Kaynat"), (t_yarim, "30 dk beklet"), (t_dur, "Durula")]
        for k, (st, txt) in enumerate(steps):
            if t >= st:
                chip(L, 230 + k * 310, CY0 + 75, txt, bg=GREEN if k == 2 else WHITE, fg=WHITE if k == 2 else INK, size=36,
                     k="black", scale=eb(ph(t, st, 0.35)))
                if k < 2 and t >= steps[k + 1][0]:
                    text_c(L, (385 + k * 310, CY0 + 75), "›", "black", 54, WHITE)


def s_tel(v, sc, L, t, dur):
    headline(L, [("Eşyalar", False), ("konuşsaydı…", True)], t, y0=200, size=78)
    name_tag(L, t, t_tel0, t_abi2 - 0.1, "TELEFON", (99, 102, 241))
    if t < t_abi2:
        character(L, t, "tel", 540, CY0 + 915, 830, t_tel0, mood="tired", look=(0, 0.2))
        q = ph(t, T("yüzde") - 0.1, 0.4)
        if q > 0:
            fr = min(1.0, 0.3 + 0.7 * ph(t, T("yüzde"), 1.0))
            battery(L, CX0 + 170, CY0 + 190, 170, fr, (239, 68, 68) if fr > 0.95 else ACC, alpha=eo(q),
                    label=f"%{int(fr * 100)}")
        lottie(L, "1f971", CX0 + CS - 150, CY0 + 360, 170, t, t_cok - 0.1)
    elif t < t_ayar:  # gerçek fotoğraf: şarj olan telefon
        arrow(L, t, t_abi2 + 0.5, card_xy(t, 0.30 * 960, 0.20 * 960), card_xy(t, 0.66 * 960, 0.40 * 960), bend=0.25,
              col=ACC)
        bottom_chip(L, t, t_dolu - 0.1, "Hep %100 = hızlı yıpranma", bg=QRED, size=42)
    else:  # ayarlar kartı + pil %80'de duruyor
        q = eo(ph(t, t_ayar - 0.05, 0.4))
        glass(L, CX0 + 90, CY0 + 120, CS - 180, 300, alpha=q)
        text_c(L, (CX0 + 140, CY0 + 185), "Ayarlar  ›  Pil", "b", 36, (190, 198, 220), anchor="lm", alpha=q)
        text_c(L, (CX0 + 140, CY0 + 300), "Pil koruma", "black", 54, WHITE, anchor="lm", alpha=q)
        on = eio(ph(t, t_kor + 0.2, 0.35))
        if q > 0.3:
            toggle(L, CX0 + CS - 260, CY0 + 268, on, GREEN)
        fr = 0.3 + 0.5 * eo(ph(t, t_sarj - 0.4, 1.4))
        if t >= t_ayar + 0.2:
            battery(L, 540, CY0 + 600, 420, fr, GREEN if fr >= 0.79 else ACC, alpha=eo(ph(t, t_ayar + 0.2, 0.4)),
                    label=f"%{int(round(fr * 100))}")
        if fr >= 0.79:
            bottom_chip(L, t, t_sarj + 1.0, "Şarj %80'de durur", bg=GREEN, icon="check_mark_button")


def s_buz(v, sc, L, t, dur):
    headline(L, [("Eşyalar", False), ("konuşsaydı…", True)], t, y0=200, size=78)
    name_tag(L, t, t_buz0, t_abi3 - 0.1, "BUZDOLABI", (14, 165, 233))
    if t < t_kapak:
        smug = t >= t_abi3
        character(L, t, "buz", 540, CY0 + 915, 800, t_buz0, mood="happy" if smug else "offended",
                  look=(0.3, 0) if smug else (-0.2, 0))
        lottie(L, "1f975", CX0 + CS - 130, CY0 + 160, 170, t, t_sicak - 0.15, end=t_abi3 - 0.1)
        lottie(L, "1f92b", CX0 + CS - 130, CY0 + 160, 170, t, t_abi3 + 0.05)
    elif t < t_sutu:  # kapak en sıcak
        arrow(L, t, t_kapak + 0.4, card_xy(t, 0.70 * 960, 0.25 * 960), card_xy(t, 0.30 * 960, 0.48 * 960), bend=-0.25,
              col=QRED)
        bottom_chip(L, t, t_isinan - 0.1, "Kapak = en sıcak yer", bg=QRED, icon="thermometer")
    else:  # süt rafa, sos kapağa
        arrow(L, t, t_sutu, card_xy(t, 0.30 * 960, 0.80 * 960), card_xy(t, 0.50 * 960, 0.44 * 960), bend=0.25, col=GREEN)
        chip(L, *card_xy(t, 0.30 * 960, 0.86 * 960), "Süt: raf", bg=GREEN, fg=WHITE, size=38, k="black",
             scale=eb(ph(t, t_sutu + 0.2, 0.35)))
        if t >= t_kapakta - 0.2:
            arrow(L, t, t_kapakta - 0.2, card_xy(t, 0.78 * 960, 0.80 * 960), card_xy(t, 0.80 * 960, 0.42 * 960), bend=-0.2,
                  col=ACC)
            chip(L, *card_xy(t, 0.72 * 960, 0.88 * 960), "Kapak: sos, içecek", bg=ACC, fg=INK, size=34, k="black",
                 scale=eb(ph(t, t_kapakta, 0.35)))


def s_end(v, sc, L, t, dur):
    if t >= OS:
        lt = t - OS
        chip(L, 540, 1560, "Takip et, kaçırma!", bg=RED, fg=WHITE, size=50, icon_name="bell", k="black",
             scale=eb(ph(lt, 0.25, 0.4)))
        return
    headline(L, [("Sıradaki", False), ("kim konuşsun?", True)], t, y0=200, size=78)
    character(L, t, "tel", 250, CY0 + 830, 400, t_end + 0.0, mood="happy", look=(0.3, 0.1))
    character(L, t, "cay", 540, CY0 + 860, 380, t_end + 0.15, mood="happy", look=(0, 0.1))
    character(L, t, "buz", 830, CY0 + 860, 470, t_end + 0.3, mood="happy", look=(-0.3, 0.1))
    bottom_chip(L, t, t_yor - 0.05, "Yorumlara yaz!", bg=WHITE, fg=INK, size=50, icon="speech_balloon", y=CY0 + 120)
    lottie(L, "1f44d", 300, CY0 + 250, 150, t, t_beg - 0.1, rot=-6)
    lottie(L, "1f514", 780, CY0 + 250, 150, t, t_beg + 0.3)


starts = [0.0, t_tel0, t_buz0, t_end]
draws = [s_cay, s_tel, s_buz, s_end]
scenes = [{"start": s, "end": (starts[i + 1] if i + 1 < len(starts) else TOTAL), "draw": d}
          for i, (s, d) in enumerate(zip(starts, draws))]


class Vid(Video):
    def frame(self, t):
        im = self.bg.frame(t)
        for i, sc in enumerate(self.scenes):
            if sc["start"] <= t < sc["end"] or (i == len(self.scenes) - 1 and t >= sc["start"]):
                lt, dur = t - sc["start"], sc["end"] - sc["start"]
                layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                sc["draw"](self, sc, layer, t, dur)
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
    if not (WORK / "card.mp4").exists():
        build_track(SEGS, str(WORK / "card.mp4"))
    BGREF = CardBG(str(WORK / "card.mp4"), str(WORK / "outro.mp4"))
    load_abi()
    v = Vid(scenes, words, "", TOTAL, bg=BGREF)
    if mode == "frames":
        for tt in [float(x) for x in sys.argv[3].split(",")]:
            v.bg.p = None
            v.frame(tt).save(WORK / f"fr_{tt:05.1f}.png")
    elif mode == "render":
        sfx = [(s["start"], "whoosh") for s in scenes[1:]] + [(OS, "whoosh"), (OS + 0.15, "tink")]
        sfx += [(STARTS[k], "pop") for k in (1, 2, 5, 8, 9)]
        sfx += [(t_piril, "tink"), (t_kor + 0.2, "pop"), (t_sarj + 1.0, "ding"), (t_yor, "pop"), (t_beg, "pop")]
        at.sfx(str(WORK / "sfx.wav"), TOTAL, sfx)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(WORK / "muzik.wav"), "-af",
                        f"apad,atrim=0:{TOTAL:.3f},afade=t=in:d=0.6,afade=t=out:st={TOTAL - 1.5:.3f}:d=1.5",
                        "-ar", "44100", "-ac", "1", str(WORK / "music.wav")], check=True)
        at.final_mix(str(WORK / "voice_cut.wav"), str(WORK / "music.wav"), str(WORK / "sfx.wav"), str(WORK / "mix.m4a"))
        v.render(str(WORK / "mix.m4a"), str(WORK / "video.mp4"))
        print("render bitti", TOTAL, flush=True)
