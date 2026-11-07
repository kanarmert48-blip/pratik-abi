"""48. video (2K Shorts, ~30 sn): Spinosaurus vs T-Rex — görüntüler WanGP (Wan 2.2) ile üretildi.
Kullanım: python3 video44_uyku.py <WORK> [frames t1,t2,... | ses | render]
WORK/med/dino*.mp4 (WanGP) + shots.json gerekir."""
import os
os.environ.setdefault("PA_SCALE", str(4 / 3))
import json, math, subprocess, sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from engine import *  # noqa
from pa_ui import put_word, panel, txt, pop, captions
import audio_tools as at
from abi_yuz import konusma
from rozet import Rozet

WORK = Path(sys.argv[1])
MED = WORK / "med"
VOICE = WORK / "voice_cut.wav"
words = json.loads((WORK / "words.json").read_text(encoding="utf-8"))
TOTAL = round(at.duration(str(VOICE)) + 0.35, 3)
SHOTS_CFG = json.loads((WORK / "shots.json").read_text(encoding="utf-8"))


def _hits(key):
    k = trl(clean(key)).strip('"!?;,.…')
    return [w for w in words if trl(clean(w["w"])).strip('"!?;,.…') == k]


def T(key, nth=0):
    return _hits(key)[nth]["s"]


K = {k: T(k) for k in ["Spinosaurus", "uzun,", "yelken", "ağır,", "ısırığı", "parçalıyordu.", "Ama", "şok", "hiç",
                       "karşılaşmadı.", "Aralarında", "otuz", "Yani", "filmlerde.", "Sence", "Yorumlara", "Daha"]}
K["T-Rex"] = T("T-Rex", 1)
S_END = K["Daha"] - 0.1
K["TRex"] = K["T-Rex"]
K["Daha"] = T("Daha", 2)
S_END = K["Daha"] - 0.1
GOLD = (255, 204, 70)
INKC = (14, 16, 30)
GRN = (52, 200, 110)
RED = (255, 84, 89)
SKY = (120, 190, 255)


def sm(x):
    return eio(clamp(x))


def ramp(t, a, b):
    return sm((t - a) / max(1e-6, b - a))


def wnd(t, a, b, fi=0.2, fo=0.2):
    return ramp(t, a, a + fi) * (1 - ramp(t, b - fo, b))


# ---------------- klipler ----------------
class Clip:
    def __init__(self, path, off=0.0):
        self.path, self.off = str(path), off
        self.cap, self.pos, self.last = None, None, None

    def get(self, lt):
        tt = self.off + lt
        if self.cap is None or self.pos is None or tt < self.pos - 0.01 or tt > self.pos + 1.0:
            if self.cap is None:
                self.cap = cv2.VideoCapture(self.path)
            self.cap.set(cv2.CAP_PROP_POS_MSEC, tt * 1000)
            self.pos = tt - 1 / 30
        fps = self.cap.get(cv2.CAP_PROP_FPS) or 30
        while self.pos < tt - 0.5 / fps:
            ok, fr = self.cap.read()
            if not ok:
                self.cap.set(cv2.CAP_PROP_POS_MSEC, 0)
                ok, fr = self.cap.read()
                if not ok:
                    break
            self.last = fr
            self.pos += 1 / fps
        return self.last


def cover(fr, zoom=1.0, sx=0.0, sy=0.0, fx=0.5, fy=0.5, flip=False):
    """BGR kareyi 1440x2560'a kırp-doldur. fx/fy: kırpma odağı (0-1)."""
    h, w = fr.shape[:2]
    s = max(W / w, H / h) * zoom
    nw, nh = int(w * s), int(h * s)
    r = cv2.resize(fr, (nw, nh), interpolation=cv2.INTER_AREA if s < 1 else cv2.INTER_LINEAR)
    x0 = int(clamp((nw - W) * fx + sx, 0, nw - W))
    y0 = int(clamp((nh - H) * fy + sy, 0, nh - H))
    out = r[y0:y0 + H, x0:x0 + W]
    if flip:
        out = out[:, ::-1]
    return cv2.cvtColor(np.ascontiguousarray(out), cv2.COLOR_BGR2RGB)


def kt(key):
    """'Kelime' veya 'Kelime+0.3' / sayı -> zaman"""
    if isinstance(key, (int, float)):
        return float(key)
    if key == "END":
        return TOTAL
    off = 0.0
    for sep in ("+", "-"):
        if sep in key[1:]:
            i = key.rfind(sep)
            off = float(key[i:])
            key = key[:i]
            break
    return K[key] + off - 0.1 if key in K else T(key) + off - 0.1


SHOTS = []
for c in SHOTS_CFG:
    SHOTS.append(dict(a=kt(c["a"]), b=kt(c["b"]), clip=Clip(MED / c["f"], c.get("off", 0.0)), z0=c.get("z0", 1.0),
                      z1=c.get("z1", 1.08), fx=c.get("fx", 0.5), fy=c.get("fy", 0.5), speed=c.get("speed", 1.0),
                      shake=c.get("shake", 0.0), grade=c.get("grade", "none"), flip=c.get("flip", False),
                      dfx=c.get("dfx", 0.0), rot0=c.get("rot0", 0.0), rot1=c.get("rot1", 0.0),
                      dim=c.get("dim", 1.0)))
CUTS = [s["a"] for s in SHOTS[1:]]
JOLTS = [s["a"] for s in SHOTS if s["shake"] > 0]

# ışık / renk
YY = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
SHADE = (0.50 + 0.45 * np.clip((YY - 0.06) / 0.22, 0, 1)) * (1 - 0.45 * np.clip((YY - 0.72) / 0.22, 0, 1))
_xx = np.linspace(-1, 1, W, dtype=np.float32)[None, :, None]
_yy = np.linspace(-1, 1, H, dtype=np.float32)[:, None, None]
VIG = 1 - 0.28 * np.clip(_xx ** 2 * 0.8 + _yy ** 2 * 0.5, 0, 1)
GRADES = {"none": np.array([1.0, 1.0, 1.0], np.float32), "night": np.array([0.78, 0.9, 1.18], np.float32),
          "warm": np.array([1.08, 1.0, 0.9], np.float32), "cool": np.array([0.92, 0.98, 1.08], np.float32)}


def shot_at(t):
    for s in SHOTS:
        if s["a"] <= t < s["b"]:
            return s
    return SHOTS[-1]


def base(t):
    s = shot_at(t)
    lt = (t - s["a"]) * s["speed"]
    fr = s["clip"].get(lt)
    if fr is None:
        return np.full((H, W, 3), 20, np.float32)
    k = clamp((t - s["a"]) / max(0.1, s["b"] - s["a"]))
    z = s["z0"] + (s["z1"] - s["z0"]) * k
    sx = sy = 0.0
    if s["shake"] > 0:
        e = math.exp(-(t - s["a"]) * 5.0)
        amp = u(s["shake"]) * e
        sx, sy = amp * math.sin(t * 61), amp * math.cos(t * 47)
        z += 0.06 * e
    arr = cover(fr, z, sx, sy, s["fx"] + s["dfx"] * k, s["fy"], s["flip"])
    rot = s["rot0"] + (s["rot1"] - s["rot0"]) * k
    if abs(rot) > 0.01:
        th = math.radians(abs(rot))
        sc = math.cos(th) + (H / W) * math.sin(th)
        M = cv2.getRotationMatrix2D((W / 2, H / 2), rot, sc)
        arr = cv2.warpAffine(arr, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    arr = arr.astype(np.float32)
    if s["shake"] > 0:
        e = math.exp(-(t - s["a"]) * 6.0)
        d = int(u(16) * e)
        if d > 0:
            arr[:, d:, 0] = arr[:, :-d, 0]
            arr[:, :-d, 2] = arr[:, d:, 2]
    g = GRADES[s["grade"]]
    if s["grade"] == "night":
        lum = arr.mean(axis=2, keepdims=True)
        arr = (arr * 0.75 + lum * 0.25) * g * 0.9 + np.array([4, 8, 18], np.float32)
    else:
        arr = arr * g
    arr *= SHADE * VIG * s["dim"]
    # kesme flaşı
    for c in CUTS:
        if 0 <= t - c < 0.1:
            arr += (70 if c in JOLTS else 30) * (1 - (t - c) / 0.1)
    return arr


ORANGE = (255, 140, 40)


def AI_TAG(L, a=0.75):
    txt(L, (540, 112), "Görüntüler yapay zekâ ile üretildi", 26, WHITE, a * 0.75, k="b", stroke=3)


def timeline(L, t, t0, a):
    """95 milyon yıl önce — 67 milyon yıl önce, arada 30 milyon yıl"""
    d = ImageDraw.Draw(L)
    q = ramp(t, t0, t0 + 0.6)
    x0, x1, y = u(250), u(830), u(780)
    xe = x0 + (x1 - x0) * q
    d.rounded_rectangle([x0, y - u(9), xe, y + u(9)], radius=int(u(9)), fill=WHITE + (int(235 * a),))
    pts = [(x0, "Spinosaurus", "~95 milyon yıl önce", ORANGE, t0 + 0.15),
           (x1, "T-Rex", "~67 milyon yıl önce", RED, t0 + 0.55)]
    for x, nm, when, col, tt in pts:
        qq = pop(t, tt, 0.3)
        if qq <= 0.02:
            continue
        r = u(30) * qq
        d.ellipse([x - r, y - r, x + r, y + r], fill=col + (int(255 * a),), outline=WHITE + (int(255 * a),), width=int(u(5)))
        txt(L, (x / u(1), 690), nm, round(58 * qq), col, a, stroke=6)
        txt(L, (x / u(1), 870), when, round(36 * qq), WHITE, a, k="b", stroke=5)
    if t >= K["otuz"] - 0.15:
        chip(L, 540, 1010, "≈ 30 MİLYON YIL ARA", bg=GOLD, fg=INKC, size=58, k="black", alpha=a,
             scale=pop(t, K["otuz"] - 0.15, 0.35))


def ui(L, t):
    AI_TAG(L)
    if t < K["Spinosaurus"] - 0.1:
        a = 1 - ramp(t, K["Spinosaurus"] - 0.3, K["Spinosaurus"] - 0.1)
        p = 1 + 0.12 * (1 - pop(t, 0.0, 0.3))
        put_word(L, "SPİNOSAURUS", ORANGE, 540, 190, round(104 * p), alpha=a, glow=0.5)
        q = pop(t, 0.35, 0.3)
        if q > 0.02:
            put_word(L, "VS", WHITE, 540, 305, round(80 * q), alpha=a, glow=0.3)
        q2 = pop(t, 0.7, 0.3)
        if q2 > 0.02:
            put_word(L, "T-REX", RED, 540, 425, round(132 * q2), alpha=a, glow=0.55)
        if t >= 2.4:
            chip(L, 540, 640, "KİM KAZANIR?", bg=WHITE, fg=INKC, size=64, k="black", alpha=a, scale=pop(t, 2.4, 0.3))
    elif t < K["T-Rex"] - 0.1:
        a = wnd(t, K["Spinosaurus"] - 0.1, K["T-Rex"] - 0.05)
        two(L, t, a, "SPİNOSAURUS", ORANGE, 96, "", WHITE, 1, K["Spinosaurus"] - 0.1, y1=200)
        if t >= K["uzun,"] - 0.1:
            chip(L, 540, 650, "Boy: ~15 metre", bg=WHITE, fg=INKC, size=56, k="black",
                 alpha=a, scale=pop(t, K["uzun,"] - 0.1, 0.3))
        if t >= K["yelken"] - 0.1:
            chip(L, 540, 790, "Sırtında dev yelken", bg=ORANGE, fg=INKC, size=56, k="black", alpha=a,
                 scale=pop(t, K["yelken"] - 0.1, 0.3))
    elif t < K["Ama"] - 0.1:
        a = wnd(t, K["T-Rex"] - 0.1, K["Ama"] - 0.05)
        two(L, t, a, "T-REX", RED, 130, "", WHITE, 1, K["T-Rex"] - 0.1, y1=210)
        if t >= K["ağır,"] - 0.1:
            chip(L, 540, 650, "Daha ağır: ~8 ton", bg=WHITE, fg=INKC, size=56, k="black", alpha=a,
                 scale=pop(t, K["ağır,"] - 0.1, 0.3))
        if t >= K["ısırığı"] - 0.1:
            chip(L, 540, 790, "Isırığı kemik kırar", bg=RED, fg=WHITE, size=56, icon_name="exploding_head", k="black", alpha=a,
                 scale=pop(t, K["ısırığı"] - 0.1, 0.3))
    elif t < K["Aralarında"] - 0.1:
        a = wnd(t, K["Ama"] - 0.1, K["Aralarında"] - 0.05)
        two(L, t, a, "AMA ASIL ŞOK", WHITE, 92, "", WHITE, 1, K["Ama"] - 0.1, y1=200)
        if t >= K["hiç"] - 0.1:
            q = pop(t, K["hiç"] - 0.1, 0.32)
            put_word(L, "HİÇ", GOLD, 540, 330, max(8, round(120 * q)), alpha=a, glow=0.5)
            put_word(L, "KARŞILAŞMADILAR!", GOLD, 540, 460, max(8, round(98 * q)), alpha=a, glow=0.5)
    elif t < K["Yani"] - 0.1:
        a = wnd(t, K["Aralarında"] - 0.1, K["Yani"] - 0.05)
        two(L, t, a, "ARALARINDA", WHITE, 92, "", WHITE, 1, K["Aralarında"] - 0.1, y1=200)
        timeline(L, t, K["Aralarında"], a)
    elif t < K["Sence"] - 0.1:
        a = wnd(t, K["Yani"] - 0.1, K["Sence"] - 0.05)
        two(L, t, a, "BU KAVGA", WHITE, 96, "SADECE FİLMLERDE", GOLD, 96, K["Yani"] - 0.1, y1=200, y2=320)
        if t >= K["filmlerde."] - 0.1:
            put_icon(L, "television", 540, 520, 160 * pop(t, K["filmlerde."] - 0.1, 0.35), alpha=a)
    elif t < S_END:
        a = wnd(t, K["Sence"] - 0.1, S_END + 0.1, 0.2, 0.15)
        q = pop(t, K["Sence"] - 0.1, 0.35)
        txt(L, (540, 190), "SENCE KİM", round(96 * q), WHITE, a, stroke=7)
        txt(L, (540, 310), "KAZANIRDI?", round(110 * q), GOLD, a, stroke=7)
        chip(L, 300, 650, "SPİNOSAURUS", bg=ORANGE, fg=INKC, size=50, k="black", alpha=a, scale=pop(t, K["Sence"] + 0.3, 0.3))
        chip(L, 780, 650, "T-REX", bg=RED, fg=WHITE, size=50, k="black", alpha=a, scale=pop(t, K["Sence"] + 0.5, 0.3))
        if t >= K["Yorumlara"] - 0.08:
            chip(L, 540, 790, "Yorumlara yaz", bg=INKC, fg=WHITE, size=56, icon_name="speech_balloon", k="black",
                 alpha=a, scale=pop(t, K["Yorumlara"] - 0.08, 0.35))
    else:
        a = ramp(t, S_END, S_END + 0.25)
        txt(L, (540, 190), "Daha fazlası için", 64, WHITE, a, stroke=6)
        pulse = 1 + 0.045 * math.sin((t - S_END) * 8) * ramp(t, S_END + 0.4, S_END + 0.7)
        chip(L, 540, 320, "TAKİP ET", bg=INKC, fg=WHITE, size=90, icon_name="bell", k="black",
             scale=pop(t, S_END, 0.4) * pulse)


def two(L, t, a, l1, c1, s1, l2, c2, s2, t0, y1=165, y2=290):
    q = pop(t, t0, 0.3)
    if q <= 0.02:
        return
    put_word(L, l1, c1, 540, y1, max(8, round(s1 * q)), alpha=a, glow=0.3)
    if l2:
        put_word(L, l2, c2, 540, y2, max(8, round(s2 * q)), alpha=a, glow=0.45)


ROZ = Rozet()
OPN, RND = konusma(VOICE, FPS)


class Vid(Video):
    def frame(self, t):
        arr = base(t)
        im = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB").convert("RGBA")
        L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ui(L, t)
        im.alpha_composite(L)
        brand(im, 540, 62, size=34)
        C = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        captions(C, self.groups, t, y=1700)
        im.alpha_composite(C)
        i = min(len(OPN) - 1, int(t * FPS))
        ROZ.draw(im, t, float(OPN[i]))
        return im.convert("RGB")


VID = Vid([{"start": 0, "end": TOTAL, "draw": lambda *a: None}], words, "", TOTAL, bg=None)
SR = 44100
rng = np.random.default_rng(48)


def _lp(x, fc):
    a = math.exp(-2 * math.pi * fc / SR)
    y = np.empty_like(x)
    s = 0.0
    for i in range(len(x)):
        s = (1 - a) * x[i] + a * s
        y[i] = s
    return y


def roar(d=1.6, f0=70):
    n = int(d * SR)
    tt = np.arange(n) / SR
    f = f0 * (1 + 0.25 * np.sin(2 * np.pi * 3.1 * tt)) * (1 + 0.15 * tt)
    ph = 2 * np.pi * np.cumsum(f) / SR
    y = sum(np.sin(h * ph) / h for h in range(1, 7))
    y = y * (1 + 0.6 * rng.standard_normal(n))
    env = np.clip(tt / 0.15, 0, 1) * np.clip((d - tt) / 0.5, 0, 1)
    y = np.convolve(y * env, np.ones(12) / 12, mode="same")
    return y / (np.abs(y).max() + 1e-9)


def thud(d=0.9, f0=50):
    n = int(d * SR)
    tt = np.arange(n) / SR
    y = np.sin(2 * np.pi * f0 * tt * (1 - 0.3 * tt)) * np.exp(-tt * 6)
    y += np.convolve(rng.standard_normal(n), np.ones(40) / 40, mode="same") * np.exp(-tt * 12) * 0.8
    return y / (np.abs(y).max() + 1e-9)


def splash(d=0.8):
    n = int(d * SR)
    tt = np.arange(n) / SR
    y = rng.standard_normal(n) * np.exp(-tt * 5) * np.clip(tt / 0.02, 0, 1)
    y = y - np.convolve(y, np.ones(30) / 30, mode="same")
    return y / (np.abs(y).max() + 1e-9)


def make_audio():
    ev = [(c, "whoosh") for c in CUTS if c not in JOLTS] + [(j, "pop") for j in JOLTS]
    ev += [(0.35, "pop"), (0.7, "pop"), (2.4, "pop"), (K["uzun,"] - 0.1, "pop"), (K["yelken"] - 0.1, "pop"),
           (K["ağır,"] - 0.1, "pop"), (K["ısırığı"] - 0.1, "pop"), (K["hiç"] - 0.1, "ding"), (K["Aralarında"] + 0.15, "tink"),
           (K["Aralarında"] + 0.55, "tink"), (K["otuz"] - 0.15, "ding"), (K["filmlerde."] - 0.1, "pop"),
           (K["Sence"] + 0.3, "pop"), (K["Sence"] + 0.5, "pop"), (K["Yorumlara"] - 0.08, "pop"), (S_END, "pop")]
    ev = sorted(set((round(a, 3), b) for a, b in ev))
    at.sfx(str(WORK / "sfx.wav"), TOTAL, ev)
    fx = np.frombuffer(subprocess.run(["ffmpeg", "-v", "error", "-i", str(WORK / "sfx.wav"), "-ac", "1", "-ar", str(SR),
                                       "-f", "f32le", "-"], capture_output=True).stdout, np.float32).copy()
    fx = np.pad(fx, (0, max(0, int(TOTAL * SR) + SR - len(fx))))

    def add(t0, y, g):
        a = int(t0 * SR)
        b = min(len(fx), a + len(y))
        if a < len(fx):
            fx[a:b] += (y[:b - a] * g).astype(np.float32)
    add(0.05, roar(1.8, 62), 0.30)
    add(0.75, roar(1.4, 85), 0.22)
    add(K["Spinosaurus"] - 0.05, thud(), 0.45)
    add(K["Spinosaurus"] + 0.8, thud(), 0.35)
    add(K["T-Rex"] - 0.15, roar(1.6, 55), 0.32)
    add(K["parçalıyordu."] - 0.1, thud(1.0, 40), 0.6)
    add(K["Ama"] - 0.1, thud(1.2, 35), 0.5)
    add(K["Aralarında"] - 0.2, splash(), 0.25)
    add(K["Yani"] - 0.05, thud(), 0.35)
    add(K["Sence"] - 0.2, roar(1.5, 70), 0.22)
    fx = np.clip(fx, -1, 1)
    at._write(str(WORK / "sfx.wav"), fx[:int(TOTAL * SR)])
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-stream_loop", "4", "-i", str(WORK / "muzik.wav"), "-af",
                    f"atrim=0:{TOTAL:.3f},afade=t=in:d=0.15,afade=t=out:st={TOTAL - 0.6:.3f}:d=0.6",
                    "-ar", "44100", "-ac", "1", str(WORK / "music.wav")], check=True)
    at.final_mix(str(VOICE), str(WORK / "music.wav"), str(WORK / "sfx.wav"), str(WORK / "mix.m4a"))


if __name__ == "__main__":
    mode = sys.argv[2] if len(sys.argv) > 2 else "render"
    print("TOTAL", TOTAL, "shots", len(SHOTS), flush=True)
    if mode == "frames":
        (WORK / "test").mkdir(exist_ok=True)
        for tt in [float(x) for x in sys.argv[3].split(",")]:
            VID.frame(tt).save(WORK / "test" / f"fr_{tt:05.2f}.jpg", quality=90)
    elif mode == "ses":
        make_audio()
    else:
        make_audio()
        VID.render(str(WORK / "mix.m4a"), str(WORK / "video.mp4"))
        print("render bitti", TOTAL, flush=True)
