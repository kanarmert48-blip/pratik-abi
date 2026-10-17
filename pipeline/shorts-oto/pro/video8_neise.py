"""8. video: Her gün görüyorsun ama ne işe yaradığını bilmiyorsun (6 obje).
Kare inceleme kartı + çizimli açıklamalar + sol altta hareketli Pratik Abi."""
import json, math, subprocess, sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from engine import *  # noqa
from widgets import *  # noqa
import audio_tools as at

WORK = Path(sys.argv[1])
N = Path("/home/claude/pratik-abi/media/v8-ne-ise-yarar")
words = json.loads((WORK / "words.json").read_text(encoding="utf-8"))
TOTAL = at.duration(str(WORK / "voice_cut.wav"))
OUTRO = 1.9
OS = TOTAL - OUTRO
BLUE = (59, 130, 246)
QRED = (239, 68, 68)
CX0, CY0, CS = 60, 330, 960  # kare kart
PANEL = (16, 20, 34)


def T(key, nth=0):
    k = trl(clean(key)).strip('"!?;')
    hits = [w for w in words if trl(clean(w["w"])).strip('"!?;') == k]
    return hits[nth]["s"]


def E(key, nth=0):
    k = trl(clean(key)).strip('"!?;')
    hits = [w for w in words if trl(clean(w["w"])).strip('"!?;') == k]
    return hits[nth]["e"]


S1, S2, S3, S4, S5, S6, S7 = T("bir"), T("iki"), T("üç"), T("dört"), T("beş"), T("altı"), T("peki")
Q = [(T("sence"), E("yarıyor"), T("depo")), (T("süs"), E("sence", 1), T("hayır")),
     (T("bil"), E("bakalım", 1), T("siyah", 1)), (T("ne", 2), E("dersin"), T("bakmadan")),
     (T("bozuk"), E("mi"), T("aslında")), (T("son"), E("soru"), T("içine"))]
t_hayat, t_kir, t_nok = T("hayat"), T("kiralık"), T("noktalar", 1)
t_bua, t_asl, t_yak, t_boy = T("bu"), T("aslında"), T("yaklaşık"), T("böylece")
t_yor, t_beg = T("yorumlara"), T("beğenmeyi")

# ---------- kart görüntü izi ----------
BS = 1008


def ph_crop(name, x, y, s):
    return dict(src=str(N / name), kind="photo", pre=f"crop={s}:{s}:{x}:{y},")


def vid(name, ss=0, x=None):
    d = dict(src=str(N / name), kind="video", ss=ss)
    if x is not None:
        d["pre"] = f"crop=ih:ih:{x}:0,"
    return d


GOST = dict(src="/home/claude/pratik-abi/media/v8e-ok/a_6.jpg", kind="photo", pre="crop=1346:1346:467:0,")
KAPAK = dict(src="/home/claude/pratik-abi/media/v8e-ok/f_2.jpg", kind="photo", pre="crop=1280:1280:320:0,")
POMPA = dict(src="/home/claude/pratik-abi/media/v8d-yakit/d1_1.jpg", kind="photo", pre="crop=2250:2250:150:0,hflip,")
KALEM1 = ph_crop("kalem-p_3.jpg", 0, 0, 853)
KALEM2 = ph_crop("kalem-w_3.jpg", 0, 0, 1280)
KLAV = ph_crop("klavye-p_3.jpg", 720, 0, 560)
KOT1 = ph_crop("kot-p_3.jpg", 204, 0, 853)
KOT2 = ph_crop("kot-w_2.jpg", 640, 0, 1280)
FRIT = dict(src="/tmp/claude-0/-home-claude-pratik-abi/b79e0552-bc51-522f-903a-0721ef74ac4f/scratchpad/v8/frit.jpg", kind="photo")
GLUE = dict(src="/home/claude/pratik-abi/media/v8c-unsplash/u-glue1_1.jpg", kind="photo", pre="crop=2400:2400:0:500,")
KILIT = vid("kilit-v_1.mp4", 0, 840)
d0 = S1 / 6
SEGS = [dict(GOST, dur=d0), dict(KALEM1, dur=d0), dict(FRIT, dur=d0), dict(KLAV, dur=d0), dict(KOT1, dur=d0),
        dict(KILIT, dur=S1 - 5 * d0),
        dict(GOST, dur=Q[0][2] - S1), dict(KAPAK, dur=t_kir - Q[0][2]), dict(POMPA, dur=S2 - t_kir), dict(KALEM1, dur=t_hayat - S2), dict(KALEM2, dur=S3 - t_hayat),
        dict(FRIT, dur=Q[2][2] - S3), dict(GLUE, dur=t_nok - Q[2][2]), dict(FRIT, dur=S4 - t_nok), dict(KLAV, dur=Q[3][2] - S4),
        dict(vid("klavye-v_2.mp4", 1), dur=S5 - Q[3][2]), dict(KOT1, dur=t_asl - S5),
        dict(vid("cepsaati-v_1.mp4", 1), dur=t_yak - t_asl), dict(KOT2, dur=S6 - t_yak),
        dict(KILIT, ss=1, dur=S7 - S6), dict(vid("cepsaati-v_3.mp4", 2), dur=OS - S7)]


def build_track(segs, out):
    import os, tempfile
    tmp = tempfile.mkdtemp()
    parts = []
    for i, s in enumerate(segs):
        assert s["dur"] > 0, (i, s["dur"])
        p = os.path.join(tmp, f"s{i}.mp4")
        vf = (f"{s.get('pre', '')}scale={BS}:{BS}:force_original_aspect_ratio=increase:flags=lanczos,crop={BS}:{BS},"
              f"fps={FPS},eq=contrast=1.05:saturation=1.1,unsharp=5:5:0.5,setsar=1,format=yuv420p")
        n = int(round(s["dur"] * FPS))
        if s["kind"] == "photo":
            inp = ["-loop", "1", "-i", s["src"]]
        else:
            dsrc = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of",
                                         "csv=p=0", s["src"]], capture_output=True, text=True).stdout or 0)
            ss = s.get("ss", 0)
            inp = ["-ss", f"{ss:.3f}", "-i", s["src"]] if dsrc - ss >= s["dur"] + 0.1 else ["-stream_loop", "-1", "-i",
                                                                                          s["src"]]
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *inp, "-vf", vf, "-an", "-frames:v", str(n),
                        "-c:v", "libx264", "-preset", "veryfast", "-crf", "14", p], check=True)
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
        m = Image.new("L", (CS, CS), 0)
        ImageDraw.Draw(m).rounded_rectangle([0, 0, CS - 1, CS - 1], radius=44, fill=255)
        self.mask = m
        self.shadow = soft_shadow(CS, CS, 44, blur=30, op=0.55)
        g = np.zeros((H, W, 4), np.uint8)
        y = np.arange(H)[:, None]
        g[..., :3] = (8, 11, 24)
        g[..., 3] = np.clip(140 + 70 * np.abs(y - 820) / 1100, 0, 225).astype(np.uint8)
        self.dark = Image.fromarray(g, "RGBA")
        self.starts = [sum(s["dur"] for s in SEGS[:i]) for i in range(len(SEGS) + 1)]

    def _pipe(self, path, t, size):
        return subprocess.Popen(["ffmpeg", "-loglevel", "error", "-ss", f"{t:.4f}", "-i", path, "-vf",
                                 f"scale={size[0]}:{size[1]}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                                stdout=subprocess.PIPE)

    def _read(self, t):
        if self.p is None or abs(t - self.nt) > 0.5 / FPS:
            if self.p:
                self.p.kill()
            self.p = self._pipe(self.track, t, (BS, BS))
        buf = self.p.stdout.read(BS * BS * 3)
        self.nt = t + 1 / FPS
        if len(buf) < BS * BS * 3:
            return Image.new("RGB", (BS, BS), (20, 20, 30))
        return Image.frombuffer("RGB", (BS, BS), buf, "raw", "RGB", 0, 1)

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
            if self.starts[k] <= t + 1e-6:
                i = k
        return i, (t - self.starts[i]) / max(SEGS[i]["dur"], 0.01)

    def frame(self, t):
        if t >= OS:
            return self._read_outro(t - OS).convert("RGBA")
        src = self._read(t)
        i, p = self.seg(t)
        z = 1 + 0.045 * p  # yavaş yakınlaşma
        cw = (BS - 48) / z
        c = BS / 2
        cardim = src.crop((c - cw / 2, c - cw / 2, c + cw / 2, c + cw / 2)).resize((CS, CS), Image.BICUBIC)
        bg = src.resize((18, 18), Image.BOX).resize((W, W), Image.BICUBIC)
        bg = bg.crop((0, 0, W, W)).resize((W, H), Image.BICUBIC).convert("RGBA")
        bg.alpha_composite(self.dark)
        sh, pad = self.shadow
        comp(bg, sh, CX0 - pad, CY0 - pad + 20)
        cr = cardim.convert("RGBA")
        cr.putalpha(self.mask)
        bg.alpha_composite(cr, (CX0, CY0))
        ImageDraw.Draw(bg).rounded_rectangle([CX0 - 3, CY0 - 3, CX0 + CS + 2, CY0 + CS + 2], radius=46,
                                             outline=(255, 255, 255, 235), width=5)
        dt = t - self.starts[i]
        if i > 0 and dt < 0.12:
            fl = Image.new("RGBA", (CS, CS), (255, 255, 255, 0))
            fl.putalpha(self.mask.point(lambda v: int(v * 0.5 * (1 - dt / 0.12))))
            bg.alpha_composite(fl, (CX0, CY0))
        return bg

    def finish(self, im, t):
        return im


def zmap(px, py):
    """Kart içi koordinat (0-960, zoom yok sayılır) -> ekran (merkezden yakınlaşma hesaba katılır)."""
    return CX0 + px, CY0 + py


def card_xy(t, px, py):
    i, p = BGREF.seg(t)
    z = 1 + 0.045 * p
    s = CS / (BS - 48) * z * (BS - 48) / CS  # = z
    cx, cy = CS / 2, CS / 2
    return CX0 + cx + (px - cx) * z, CY0 + cy + (py - cy) * z


BGREF = None

# ---------- Pratik Abi (sol alt) ----------
AB_FR = None


def _abi_frames():
    global AB_FR
    if AB_FR is None:
        fs = sorted((WORK / "abi").glob("f*.png"))
        R = 108
        S = 2 * R
        m = Image.new("L", (S * 4, S * 4), 0)
        ImageDraw.Draw(m).ellipse([0, 0, S * 4 - 1, S * 4 - 1], fill=255)
        m = m.resize((S, S), Image.LANCZOS)

        def mk(p):
            im = Image.open(p).convert("RGBA").resize((S, S), Image.LANCZOS)
            im.putalpha(m)
            out = Image.new("RGBA", (S + 16, S + 16), (0, 0, 0, 0))
            ImageDraw.Draw(out).ellipse([0, 0, S + 15, S + 15], fill=ACC + (255,))
            out.alpha_composite(im, (8, 8))
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
AX, AY = 172, 1575


def abi(im, t):
    frs, blink = _abi_frames()
    n = len(frs)
    k = int(t * FPS) % (2 * n - 2)
    k = k if k < n else 2 * n - 2 - k
    img = blink if (t % 5.2) < 0.14 else frs[k]
    lvl = float(ENV[min(len(ENV) - 1, int(t * FPS))])
    s = 1 + 0.06 * lvl
    im2 = img.resize((int(img.width * s), int(img.height * s)), Image.BICUBIC)
    rot = 3 * math.sin(t * 2.1)
    im2 = im2.rotate(rot, resample=Image.BICUBIC, expand=True)
    sh, pad = soft_shadow(img.width, img.height, img.width // 2, blur=16, op=0.5)
    comp(im, sh, AX - img.width / 2 - pad, AY - img.height / 2 - pad + 12)
    comp(im, im2, AX - im2.width / 2, AY - im2.height / 2)
    d = ImageDraw.Draw(im)
    for k2 in range(2):  # ses dalgası
        rr = 130 + k2 * 22 + 12 * lvl
        d.arc([AX - rr, AY - rr, AX + rr, AY + rr], -40, 30, fill=ACC + (int(200 - 70 * k2),), width=7)


# ---------- ortak quiz parçaları ----------
def panel(L, alpha=1.0, col=PANEL):
    card(L, CX0, CY0, CS, CS, r=44, fill=col + (255,), shadow=False, alpha=alpha)


def pulse_ring(L, t, start, x, y, r=70, col=ACC):
    p = ph(t, start, 0.4)
    if p <= 0:
        return
    d = ImageDraw.Draw(L)
    rr = r * (1 + 0.08 * math.sin(t * 8)) * eb(p)
    d.ellipse([x - rr, y - rr, x + rr, y + rr], outline=col + (255,), width=10)
    ph2 = (t * 1.3) % 1
    r2 = r * (1 + 0.6 * ph2)
    d.ellipse([x - r2, y - r2, x + r2, y + r2], outline=col + (int(200 * (1 - ph2)),), width=5)


def quiz(L, t, i, s0):
    qs, qe, ans = (x - s0 for x in Q[i])
    if qs - 0.1 <= t < ans - 0.05:
        chip(L, W / 2, CY0 + CS - 70, "Sence ne işe yarar?", bg=WHITE, fg=INK, size=46, icon_name="thinking_face",
             k="black", scale=eb(ph(t, qs - 0.1, 0.35)))
    if qe <= t < ans:
        p = (t - qe) / max(ans - qe, 0.1)
        cx, cy, r = CX0 + CS - 90, CY0 + 90, 56
        d = ImageDraw.Draw(L)
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(14, 18, 32, 230))
        d.arc([cx - r, cy - r, cx + r, cy + r], -90, -90 + 360 * (1 - p), fill=ACC + (255,), width=10)
        text_c(L, (cx, cy + 2), str(max(1, math.ceil((1 - p) * 3))), "black", 52, WHITE)


def answer(L, t, s0, i, text, icon):
    ans = Q[i][2] - s0
    q = ph(t, ans - 0.05, 0.35)
    if q > 0:
        chip(L, W / 2, CY0 + CS - 70, text, bg=GREEN, fg=WHITE, size=48, icon_name=icon, k="black", scale=eb(q))


def title(L, n, name, t):
    headline(L, [(f"{n}/6", True), (name, False)], t, y0=205, size=76)


# ---------- çizimler ----------
def pump_icon(d, cx, cy, s, col):
    """Yakıt pompası simgesi (gövde + pencere + hortum)."""
    w, h = 0.62 * s, s
    d.rounded_rectangle([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2], radius=s * 0.08, fill=col)
    d.rectangle([cx - w / 2 + s * 0.1, cy - h / 2 + s * 0.12, cx + w / 2 - s * 0.1, cy - h / 2 + s * 0.38],
                fill=PANEL + (255,))
    d.rectangle([cx - w / 2 - s * 0.08, cy + h / 2 - s * 0.06, cx + w / 2 + s * 0.08, cy + h / 2 + s * 0.04], fill=col)
    hx = cx + w / 2
    d.line([(hx, cy - h * 0.25), (hx + s * 0.22, cy - h * 0.15), (hx + s * 0.22, cy + h * 0.25),
            (hx + s * 0.32, cy + h * 0.3)], fill=col, width=int(s * 0.07), joint="curve")


def draw_fuel(L, t, a0, t_car):
    p = eo(ph(t, a0, 0.4))
    if p <= 0:
        return
    panel(L, p)
    d = ImageDraw.Draw(L)
    a = int(255 * p)
    gx, gy, R = CX0 + 480, CY0 + 470, 300
    d.arc([gx - R, gy - R, gx + R, gy + R], 200, 340, fill=(235, 238, 245, a), width=14)
    for k in range(5):
        ang = math.radians(200 + k * 35)
        d.line([gx + (R - 40) * math.cos(ang), gy + (R - 40) * math.sin(ang), gx + (R + 8) * math.cos(ang),
                gy + (R + 8) * math.sin(ang)], fill=(235, 238, 245, a), width=10)
    text_c(L, (gx - R * 0.95, gy - 40), "E", "black", 64, QRED, alpha=p)
    text_c(L, (gx + R * 0.95, gy - 40), "F", "black", 64, WHITE, alpha=p)
    ang = math.radians(212)
    d.line([gx, gy, gx + (R - 30) * math.cos(ang), gy + (R - 30) * math.sin(ang)], fill=QRED + (a,), width=12)
    d.ellipse([gx - 26, gy - 26, gx + 26, gy + 26], fill=(235, 238, 245, a))
    pump_icon(d, gx, gy - 130, 110, (235, 238, 245, a))
    pr = 1 + 0.15 * math.sin(t * 7)
    ax, ay = gx - 150, gy - 130
    d.polygon([(ax - 34 * pr, ay), (ax + 20 * pr, ay - 32 * pr), (ax + 20 * pr, ay + 32 * pr)], fill=ACC + (a,))
    pulse_ring(L, t, a0 + 0.3, ax - 5, ay, r=62)
    q = eo(ph(t, t_car, 0.45))
    if q > 0:  # üstten araba: depo kapağı solda
        cx, cy = CX0 + 480, CY0 + 700
        bw, bh = 150, 240
        ca = int(255 * q)
        d.rounded_rectangle([cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2], radius=60, fill=(200, 205, 215, ca))
        d.rounded_rectangle([cx - bw / 2 + 22, cy - bh / 2 + 60, cx + bw / 2 - 22, cy - bh / 2 + 120], radius=18,
                            fill=(70, 90, 120, ca))
        d.rounded_rectangle([cx - bw / 2 + 22, cy + bh / 2 - 95, cx + bw / 2 - 22, cy + bh / 2 - 50], radius=14,
                            fill=(70, 90, 120, ca))
        blink = 0.5 + 0.5 * math.sin(t * 9)
        fd = (int(255), int(170 + 42 * blink), 59, ca)
        d.rounded_rectangle([cx - bw / 2 - 6, cy + 40, cx - bw / 2 + 26, cy + 82], radius=8, fill=fd)
        pump_icon(d, cx - bw / 2 - 90, cy + 60, 70, ACC + (ca,))
        d.polygon([(cx - bw / 2 - 150, cy + 60), (cx - bw / 2 - 124, cy + 44), (cx - bw / 2 - 124, cy + 76)],
                  fill=ACC + (ca,))


def draw_pen(L, t, a0):
    p = eo(ph(t, a0, 0.4))
    if p <= 0:
        return
    panel(L, p, (232, 238, 248))
    tmp = Image.new("RGBA", (CS * 2, CS * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(tmp)
    cy = 760
    # kapak: solda kapalı uç (delikli), sağda açık ağız
    body = [(300, cy - 70), (1500, cy - 120), (1560, cy - 120), (1560, cy + 120), (1500, cy + 120), (300, cy + 70)]
    d.polygon(body, fill=(59, 130, 246, 215))
    d.ellipse([230, cy - 70, 370, cy + 70], fill=(59, 130, 246, 230))
    d.ellipse([1500, cy - 120, 1620, cy + 120], fill=(30, 64, 175, 255))
    d.ellipse([1525, cy - 95, 1595, cy + 95], fill=(15, 23, 42, 255))
    d.polygon([(380, cy - 72), (1300, cy - 112), (1300, cy - 150), (360, cy - 112)], fill=(37, 99, 235, 255))  # klips
    d.line([(420, cy - 40), (1450, cy - 80)], fill=(255, 255, 255, 120), width=14)
    d.ellipse([222, cy - 26, 274, cy + 26], fill=(15, 23, 42, 255))  # delik
    small = tmp.resize((CS, CS), Image.LANCZOS)
    comp(L, set_alpha(small, p), CX0, CY0)
    dd = ImageDraw.Draw(L)
    hx, hy = CX0 + 124, CY0 + cy / 2
    pulse_ring(L, t, a0 + 0.3, hx, hy, r=46, col=QRED)
    for k in range(6):  # hava akışı
        ph2 = ((t * 0.9) + k / 6) % 1
        x = CX0 + 760 - ph2 * 760
        y = hy + 6 * math.sin(ph2 * 12 + k)
        al = int(230 * p * (1 - abs(ph2 - 0.5) * 1.4))
        dd.line([(x, y), (x + 50, y)], fill=(14, 165, 233, max(0, al)), width=9)
        dd.polygon([(x - 18, y), (x, y - 12), (x, y + 12)], fill=(14, 165, 233, max(0, al)))
    put_icon(L, "child", CX0 + 220, CY0 + 640, 190 * eb(ph(t, a0 + 0.6, 0.4)), rot=-6)
    put_icon(L, "wind_face", CX0 + 740, CY0 + 640, 170 * eb(ph(t, a0 + 1.0, 0.4)), rot=6)


def draw_frit(L, t, a0, t_dots):
    p = eo(ph(t, a0, 0.4))
    if p <= 0:
        return
    panel(L, p, (196, 222, 240))
    d = ImageDraw.Draw(L)
    a = int(255 * p)
    x0, y0 = CX0, CY0
    band = 150
    d.rounded_rectangle([x0, y0, x0 + CS, y0 + band], radius=44, fill=(14, 16, 22, a))
    d.rectangle([x0, y0 + 40, x0 + band, y0 + CS - 44], fill=(14, 16, 22, a))
    d.rectangle([x0, y0 + 60, x0 + CS, y0 + band], fill=(14, 16, 22, a))
    for r in range(6):  # nokta geçişi (alt kenar)
        rad = 15 - r * 2.4
        yy = y0 + band + 22 + r * 34
        off = 17 if r % 2 else 0
        for xx in range(int(x0 + band + 20 + off), int(x0 + CS - 10), 34):
            d.ellipse([xx - rad, yy - rad, xx + rad, yy + rad], fill=(14, 16, 22, a))
        xx = x0 + band + 22 + r * 34
        for yy2 in range(int(y0 + band + 20 + off), int(y0 + CS - 50), 34):
            d.ellipse([xx - rad, yy2 - rad, xx + rad, yy2 + rad], fill=(14, 16, 22, a))
    # yapıştırıcı (röntgen görünümü)
    q = eo(ph(t, a0 + 0.5, 0.5))
    if q > 0:
        d.line([(x0 + 70, y0 + CS - 60), (x0 + 70, y0 + 75), (x0 + CS - 60, y0 + 75)], fill=(251, 191, 36, int(255 * q)),
               width=22, joint="curve")
        chip(L, x0 + 560, y0 + 75, "Yapıştırıcı", bg=(251, 191, 36), fg=INK, size=34, k="black", scale=eb(q))
    # güneş ışınları siyah şeride çarpar
    sx, sy = x0 + 760, y0 + 520
    put_icon(L, "sun", sx, sy, 190 * eb(ph(t, a0 + 0.2, 0.4)), rot=t * 10)
    for k in range(3):
        ph2 = ((t * 0.8) + k / 3) % 1
        bx, by = x0 + 350 + k * 120, y0 + band + 10
        px_, py_ = lerp(sx - 60, bx, ph2), lerp(sy - 60, by, ph2)
        d.line([(px_, py_), (px_ + (bx - sx) * 0.08, py_ + (by - sy) * 0.08)], fill=(250, 204, 21, int(230 * p)), width=8)
    if t >= t_dots:
        pulse_ring(L, t, t_dots, x0 + 420, y0 + band + 90, r=110, col=QRED)
        put_icon(L, "thermometer", x0 + 640, y0 + 700, 150 * eb(ph(t, t_dots + 0.3, 0.4)), rot=-8)


def draw_lock(L, t, a0, t_frz):
    p = eo(ph(t, a0, 0.4))
    if p <= 0:
        return
    panel(L, p)
    d = ImageDraw.Draw(L)
    a = int(255 * p)
    cx, cy = CX0 + 480, CY0 + 520
    bw, bh = 380, 300
    d.arc([cx - 125, cy - bh / 2 - 230, cx + 125, cy - bh / 2 + 30], 180, 360, fill=(170, 175, 185, a), width=46)
    d.line([(cx - 125, cy - bh / 2 - 100), (cx - 125, cy - bh / 2 + 10)], fill=(170, 175, 185, a), width=46)
    d.line([(cx + 125, cy - bh / 2 - 100), (cx + 125, cy - bh / 2 + 10)], fill=(170, 175, 185, a), width=46)
    d.rounded_rectangle([cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2], radius=40, fill=(212, 165, 60, a))
    d.rounded_rectangle([cx - bw / 2 + 18, cy - bh / 2 + 18, cx + bw / 2 - 18, cy - bh / 2 + 60], radius=20,
                        fill=(235, 195, 95, a))
    d.ellipse([cx - 30, cy - 40, cx + 30, cy + 20], fill=(40, 30, 20, a))
    d.polygon([(cx - 14, cy + 5), (cx + 14, cy + 5), (cx + 22, cy + 70), (cx - 22, cy + 70)], fill=(40, 30, 20, a))
    hx, hy = cx + 120, cy + bh / 2  # alttaki tahliye deliği
    d.ellipse([hx - 22, hy - 12, hx + 22, hy + 12], fill=(20, 15, 10, a))
    pulse_ring(L, t, a0 + 0.3, hx, hy, r=52, col=QRED)
    for k in range(5):  # içeri giren ve dışarı akan su
        ph2 = ((t * 0.9) + k / 5) % 1
        y = hy + 20 + ph2 * 260
        al = int(240 * p * (1 - ph2))
        d.ellipse([hx - 11, y - 16, hx + 11, y + 16], fill=(56, 189, 248, al))
        y2 = cy - bh / 2 - 200 + ph2 * 170
        d.ellipse([cx - 125 - 30 - 9, y2 - 13, cx - 125 - 30 + 9, y2 + 13], fill=(56, 189, 248, int(200 * p * ph2)))
    if t >= t_frz:
        put_icon(L, "snowflake", CX0 + 180, CY0 + 760, 150 * eb(ph(t, t_frz, 0.4)), rot=t * 20)
        put_icon(L, "check_mark_button", CX0 + 780, CY0 + 760, 140 * eb(ph(t, t_frz + 0.5, 0.4)))


# ---------- sahneler ----------
def s_hook(v, sc, L, t, dur):
    headline(L, [("Bunlar", False), ("ne işe yarıyor?", True)], t, y0=205, size=76, start=-1)
    for k in range(3):
        qx, qy = [(110, 110), (850, 110), (850, 830)][k]
        put_icon(L, "red_question_mark", CX0 + qx, CY0 + qy + 15 * math.sin(t * 4 + k),
                 150 * eb(ph(t, 0.1 + k * 0.15, 0.4)), rot=-12 + k * 12)
    tb = T("bakalım") - sc["start"]
    chip(L, W / 2, CY0 + CS - 70, "Kaçını biliyorsun?", bg=ACC, fg=INK, size=48, icon_name="trophy", k="black",
         scale=eb(ph(t, tb, 0.4)))


def s1(v, sc, L, t, dur):
    s0 = sc["start"]
    title(L, 1, "Benzin göstergesi", t)
    if t < Q[0][2] - s0:
        pulse_ring(L, t, 0.8, CX0 + 413, CY0 + 493, r=62)
    quiz(L, t, 0, s0)
    answer(L, t, s0, 0, "Depo kapağı o tarafta!", "fuel_pump")


def s2(v, sc, L, t, dur):
    s0 = sc["start"]
    title(L, 2, "Kalem kapağı", t)
    if t < t_hayat - s0:
        draw_pen(L, t, Q[1][2] - s0 - 0.05)
    else:
        put_icon(L, "red_heart", CX0 + 810, CY0 + 160, 170 * eb(ph(t, t_hayat - s0, 0.4)) * (1 + 0.06 * math.sin(t * 8)))
    quiz(L, t, 1, s0)
    if t < t_hayat - s0:
        answer(L, t, s0, 1, "Hava geçsin diye!", "wind_face")
    else:
        chip(L, W / 2, CY0 + CS - 70, "Hayat kurtaran delik", bg=QRED, fg=WHITE, size=48, icon_name="pen", k="black",
             scale=eb(ph(t, t_hayat - s0, 0.35)))


def s3(v, sc, L, t, dur):
    s0 = sc["start"]
    title(L, 3, "Ön camdaki noktalar", t)
    if t < Q[2][2] - s0:
        pulse_ring(L, t, 0.6, CX0 + 430, CY0 + 205, r=95)
    elif t < t_nok - s0:
        put_icon(L, "sun", CX0 + 820, CY0 + 150, 170 * eb(ph(t, Q[2][2] - s0 + 0.2, 0.4)), rot=t * 12)
    else:
        pulse_ring(L, t, t_nok - s0, CX0 + 430, CY0 + 205, r=95, col=QRED)
        put_icon(L, "thermometer", CX0 + 800, CY0 + 600, 160 * eb(ph(t, t_nok - s0 + 0.3, 0.4)), rot=-8)
    quiz(L, t, 2, s0)
    if t < t_nok - s0:
        answer(L, t, s0, 2, "Yapıştırıcıyı korur!", "sun")
    else:
        chip(L, W / 2, CY0 + CS - 70, "Cam dengeli ısınır", bg=GREEN, fg=WHITE, size=48, icon_name="thermometer",
             k="black", scale=eb(ph(t, t_nok - s0, 0.35)))


def s4(v, sc, L, t, dur):
    s0 = sc["start"]
    title(L, 4, "F ve J tuşları", t)
    if t < Q[3][2] - s0:
        pulse_ring(L, t, 0.6, CX0 + 570, CY0 + 345, r=75)
    quiz(L, t, 3, s0)
    if t < t_bua - s0:
        answer(L, t, s0, 3, "Bakmadan yazmak için!", "keyboard")
    else:
        chip(L, W / 2, CY0 + CS - 70, "İşaret parmakları burada", bg=ACC, fg=INK, size=46, icon_name="index_pointing_up",
             k="black", scale=eb(ph(t, t_bua - s0, 0.35)))


def s5(v, sc, L, t, dur):
    s0 = sc["start"]
    title(L, 5, "Kotun minik cebi", t)
    if t < Q[4][2] - s0:
        pulse_ring(L, t, 0.6, CX0 + 479, CY0 + 549, r=150)
    quiz(L, t, 4, s0)
    if t < t_yak - s0:
        answer(L, t, s0, 4, "Cep saati için!", "watch")
    else:
        chip(L, W / 2, CY0 + CS - 70, "1873'ten beri", bg=ACC, fg=INK, size=48, icon_name="jeans", k="black",
             scale=eb(ph(t, t_yak - s0, 0.35)))


def s6(v, sc, L, t, dur):
    s0 = sc["start"]
    title(L, 6, "Asma kilidin altı", t)
    draw_lock(L, t, Q[5][2] - s0 - 0.05, t_boy - s0)
    quiz(L, t, 5, s0)
    if t < t_boy - s0:
        answer(L, t, s0, 5, "Su buradan akar!", "droplet")
    else:
        chip(L, W / 2, CY0 + CS - 70, "Donmaz, paslanmaz", bg=GREEN, fg=WHITE, size=48, icon_name="locked", k="black",
             scale=eb(ph(t, t_boy - s0, 0.35)))


def s_end(v, sc, L, t, dur):
    s0 = sc["start"]
    if t >= dur - OUTRO:
        lt = t - (dur - OUTRO)
        chip(L, 540, 1560, "Takip et, kaçırma!", bg=RED, fg=WHITE, size=50, icon_name="bell", k="black",
             scale=eb(ph(lt, 0.25, 0.4)))
        return
    headline(L, [("Puanın", False), ("kaç?", True)], t, y0=205, size=80)
    q = ph(t, 0.1, 0.4)
    glass(L, CX0 + 160, CY0 + 120, CS - 320, 420, alpha=eo(q))
    put_icon(L, "trophy", W / 2, CY0 + 260, 200 * eb(q), rot=4 * math.sin(t * 3))
    qm = "?" if int(t * 2.5) % 2 == 0 else " "
    text_c(L, (W / 2, CY0 + 450), f"{qm} / 6", "black", 110, ACC, alpha=eo(q))
    ty = t_yor - s0
    chip(L, W / 2, CY0 + 640, "Yorumlara yaz!", bg=WHITE, fg=INK, size=48, icon_name="speech_balloon", k="black",
         scale=eb(ph(t, ty, 0.4)))
    tb = t_beg - s0
    q2 = ph(t, tb - 0.1, 0.45)
    if q2 > 0:
        put_icon(L, "thumbs_up", 360, CY0 + 800, 150 * eb(q2), rot=-8)
        put_icon(L, "bell", 720, CY0 + 800, 150 * eb(ph(t, tb + 0.4, 0.45)),
                 rot=14 * math.sin(t * 9) * (1 - ph(t, tb + 1.4, 0.8)))


starts = [0.0, S1, S2, S3, S4, S5, S6, S7]
draws = [s_hook, s1, s2, s3, s4, s5, s6, s_end]
scenes = [{"start": s, "end": (starts[i + 1] if i + 1 < len(starts) else TOTAL), "draw": d}
          for i, (s, d) in enumerate(zip(starts, draws))]


class Quiz(Video):
    def frame(self, t):
        im = self.bg.frame(t)
        for i, sc in enumerate(self.scenes):
            if sc["start"] <= t < sc["end"] or (i == len(self.scenes) - 1 and t >= sc["start"]):
                lt, dur = t - sc["start"], sc["end"] - sc["start"]
                layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                sc["draw"](self, sc, layer, lt, dur)
                pin = 1.0 if i == 0 else eo(ph(lt, 0, 0.3))
                pout = eio(ph(lt, dur - 0.2, 0.2)) if i < len(self.scenes) - 1 else 0
                a = pin * (1 - pout)
                if a < 0.999:
                    layer = set_alpha(layer, a)
                comp(im, layer, 0, (1 - pin) * 60 - pout * 60)
                break
        brand(im, W / 2, 140)
        if t < OS:
            draw_caption(im, self.groups, t, y=1395)
            abi(im, t)
        return im.convert("RGB")


if __name__ == "__main__":
    mode = sys.argv[2] if len(sys.argv) > 2 else "render"
    if not (WORK / "card.mp4").exists():
        build_track(SEGS, str(WORK / "card.mp4"))
    BGREF = CardBG(str(WORK / "card.mp4"), str(WORK / "outro.mp4"))
    v = Quiz(scenes, words, "", TOTAL, bg=BGREF)
    if mode == "frames":
        for tt in [float(x) for x in sys.argv[3].split(",")]:
            v.bg.p = None
            v.frame(tt).save(WORK / f"fr_{tt:05.1f}.png")
    elif mode == "render":
        sfx = [(s["start"], "whoosh") for s in scenes[1:]] + [(OS, "whoosh"), (OS + 0.15, "tink")]
        for qs, qe, ans in Q:
            sfx += [(qs - 0.1, "pop"), (ans - 0.05, "ding")]
        sfx += [(t_hayat, "pop"), (t_nok, "pop"), (t_bua, "pop"), (t_yak, "pop"), (t_boy, "pop"), (t_yor, "pop"),
                (t_beg, "pop"), (T("bakalım"), "pop")]
        at.music(str(WORK / "music.wav"), TOTAL, bpm=104, style="quiz")
        at.sfx(str(WORK / "sfx.wav"), TOTAL, sfx)
        at.final_mix(str(WORK / "voice_cut.wav"), str(WORK / "music.wav"), str(WORK / "sfx.wav"), str(WORK / "mix.m4a"))
        v.render(str(WORK / "mix.m4a"), str(WORK / "video.mp4"))
        compress(str(WORK / "video.mp4"), str(WORK / "final.mp4"))
        print("bitti", TOTAL)
