"""44. video (2K, ~41 sn): Uyurken düşüyormuş gibi sıçramak — hipnik sarsıntı.
Kullanım: python3 video44_uyku.py <WORK> [frames t1,t2,... | ses | render]
WORK/med/*.mp4 klipleri (Pixabay) gerekir."""
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


K = {k: T(k) for k in ["Uyurken", "düşüyormuş", "sıçradın", "Yalnız", "Bunun", "hipnik", "insanların", "Uykuya",
                       "kasların", "Bir", "beynin", "düşmek", "sıçratıyor", "Psikolog", "ağaçlarda", "refleks",
                       "Kafein", "stres", "uykusuzluk", "yatmadan", "spor", "Ama", "zararsız", "Sen", "Yorumlara",
                       "Daha"]}
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


# ---------------- arayüz ----------------
def two(L, t, a, l1, c1, s1, l2, c2, s2, t0, y1=165, y2=290):
    q = pop(t, t0, 0.3)
    if q <= 0.02:
        return
    put_word(L, l1, c1, 540, y1, max(8, round(s1 * q)), alpha=a, glow=0.3)
    if l2:
        put_word(L, l2, c2, 540, y2, max(8, round(s2 * q)), alpha=a, glow=0.45)


def person(d, cx, cy, sc, col):
    r = u(22) * sc
    d.ellipse([cx - r, cy - u(60) * sc - r, cx + r, cy - u(60) * sc + r], fill=col)
    d.rounded_rectangle([cx - u(34) * sc, cy - u(30) * sc, cx + u(34) * sc, cy + u(52) * sc], radius=int(u(26) * sc), fill=col)


def people(L, t, t0, a):
    """10 kişiden 7'si: yüzde 70'e kadar"""
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    for i in range(10):
        row, col = divmod(i, 5)
        cx, cy = u(180 + col * 180), u(1000 + row * 185)
        q = pop(t, t0 + 0.06 * i, 0.25)
        if q <= 0.02:
            continue
        lit = i < 7 and t >= t0 + 0.7 + 0.08 * i
        c = GOLD + (int(255 * a),) if lit else (200, 205, 220, int(150 * a))
        person(d, cx, cy, q, c)
    L.alpha_composite(lay)


def ui(L, t):
    if t < K["Bunun"] - 0.1:
        a = 1 - ramp(t, K["Bunun"] - 0.3, K["Bunun"] - 0.1)
        jolt = K["sıçradın"] - 0.1
        p = 1 + 0.1 * (1 - pop(t, 0.0, 0.28))
        dx = u(14) * math.sin(t * 70) * math.exp(-max(0, t - jolt) * 6) * (t >= jolt)
        put_word(L, "UYURKEN DÜŞÜP", WHITE, 540 + dx / u(1), 165, round(92 * p), alpha=a, glow=0.3)
        put_word(L, "SIÇRADIN MI?", GOLD, 540 - dx / u(1), 290, round(124 * p), alpha=a, glow=0.5)
        if t >= K["Yalnız"] - 0.1:
            chip(L, 540, 1290, "Yalnız değilsin!", bg=WHITE, fg=INKC, size=54, k="black", alpha=a,
                 scale=pop(t, K["Yalnız"] - 0.1, 0.3))
    elif t < K["Uykuya"] - 0.1:
        a = wnd(t, K["Bunun"] - 0.1, K["Uykuya"] - 0.05)
        two(L, t, a, "BUNUN ADI", WHITE, 80, "HİPNİK SARSINTI", GOLD, 108, K["Bunun"] - 0.1)
        if t >= K["insanların"] - 0.1:
            people(L, t, K["insanların"] - 0.1, a)
            chip(L, 540, 1365, "İnsanların %70'ine kadarı yaşıyor", bg=GOLD, fg=INKC, size=46, k="black", alpha=a,
                 scale=pop(t, K["insanların"] + 0.5, 0.3))
    elif t < K["Bir"] - 0.1:
        a = wnd(t, K["Uykuya"] - 0.1, K["Bir"] - 0.05)
        two(L, t, a, "UYKUYA DALARKEN", WHITE, 86, "KASLAR GEVŞER", SKY, 112, K["Uykuya"] - 0.1)
        put_icon(L, "zzz", 860, 470, 150 * pop(t, K["kasların"] - 0.1, 0.35), alpha=a)
    elif t < K["Psikolog"] - 0.1:
        a = wnd(t, K["Bir"] - 0.1, K["Psikolog"] - 0.05)
        chip(L, 540, 150, "TEORİ 1", bg=GOLD, fg=INKC, size=50, k="black", alpha=a, scale=pop(t, K["Bir"] - 0.1, 0.3))
        if t < K["düşmek"] - 0.1:
            two(L, t, a, "BEYİN GEVŞEMEYİ", WHITE, 86, "", WHITE, 1, K["beynin"] - 0.1, y1=290)
        elif t < K["sıçratıyor"] - 0.1:
            two(L, t, a, "DÜŞMEK SANIYOR!", RED, 104, "", WHITE, 1, K["düşmek"] - 0.1, y1=290)
        else:
            two(L, t, a, "VE SENİ SIÇRATIYOR", GOLD, 92, "", WHITE, 1, K["sıçratıyor"] - 0.1, y1=290)
    elif t < K["Kafein"] - 0.1:
        a = wnd(t, K["Psikolog"] - 0.1, K["Kafein"] - 0.05)
        chip(L, 540, 150, "TEORİ 2", bg=GOLD, fg=INKC, size=50, k="black", alpha=a, scale=pop(t, K["Psikolog"] - 0.1, 0.3))
        if t >= K["ağaçlarda"] - 0.1:
            two(L, t, a, "AĞAÇTA UYUYAN ATALARDAN", WHITE, 64, "KALMA BİR REFLEKS?", GOLD, 92, K["ağaçlarda"] - 0.1,
                y1=270, y2=370)
        chip(L, 540, 1380, "Psikolog Frederick Coolidge", bg=INKC, fg=WHITE, size=42, k="black", alpha=a,
             scale=pop(t, K["Psikolog"] + 0.2, 0.3))
    elif t < K["Ama"] - 0.1:
        a = wnd(t, K["Kafein"] - 0.1, K["Ama"] - 0.05)
        two(L, t, a, "BUNLAR", WHITE, 92, "ARTIRABİLİR", RED, 120, K["Kafein"] - 0.1)
        items = [("Kafein", "hot_beverage", K["Kafein"]), ("Stres", "face_with_steam_from_nose", K["stres"]),
                 ("Uykusuzluk", "crescent_moon", K["uykusuzluk"]), ("Gece ağır spor", "fire", K["yatmadan"])]
        for i, (lab, ic, tt) in enumerate(items):
            if t >= tt - 0.1:
                chip(L, 540, 880 + i * 135, lab, bg=WHITE, fg=INKC, size=52, icon_name=ic, k="black", alpha=a,
                     scale=pop(t, tt - 0.1, 0.3))
    elif t < K["Sen"] - 0.1:
        a = wnd(t, K["Ama"] - 0.1, K["Sen"] - 0.05)
        if t < K["zararsız"] - 0.15:
            two(L, t, a, "AMA MERAK ETME", WHITE, 92, "", WHITE, 1, K["Ama"] - 0.1, y1=230)
        else:
            q = pop(t, K["zararsız"] - 0.15, 0.32)
            put_icon(L, "check_mark_button", 540, 150, 130 * q, alpha=a)
            put_word(L, "GENELDE ZARARSIZ", GRN, 540, 290, max(8, round(94 * q)), alpha=a if q > 0.02 else 0, glow=0.5)
            chip(L, 540, 1380, "Uykunu bozuyorsa doktora danış", bg=WHITE, fg=INKC, size=40, k="black", alpha=a,
                 scale=pop(t, K["zararsız"] + 0.25, 0.3))
    elif t < S_END:
        a = wnd(t, K["Sen"] - 0.1, S_END + 0.1, 0.2, 0.15)
        q = pop(t, K["Sen"] - 0.1, 0.35)
        txt(L, (540, 165), "SEN EN SON", round(88 * q), WHITE, a, stroke=7)
        txt(L, (540, 285), "NE ZAMAN YAŞADIN?", round(92 * q), GOLD, a, stroke=7)
        if t >= K["Yorumlara"] - 0.08:
            chip(L, 540, 1290, "Yorumlara yaz", bg=INKC, fg=WHITE, size=56, icon_name="speech_balloon", k="black", alpha=a,
                 scale=pop(t, K["Yorumlara"] - 0.08, 0.35))
    else:
        a = ramp(t, S_END, S_END + 0.25)
        txt(L, (540, 170), "Daha fazlası için", 64, WHITE, a, stroke=6)
        pulse = 1 + 0.045 * math.sin((t - S_END) * 8) * ramp(t, S_END + 0.4, S_END + 0.7)
        chip(L, 540, 300, "TAKİP ET", bg=INKC, fg=WHITE, size=90, icon_name="bell", k="black",
             scale=pop(t, S_END, 0.4) * pulse)


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


def make_audio():
    ev = [(c, "whoosh") for c in CUTS if c not in JOLTS] + [(j, "pop") for j in JOLTS]
    ev += [(0.05, "whoosh"), (K["Yalnız"] - 0.1, "pop"), (K["hipnik"] - 0.1, "ding"), (K["insanların"] + 0.6, "tink"),
           (K["Bir"] - 0.1, "pop"), (K["Psikolog"] - 0.1, "pop"), (K["Kafein"] - 0.1, "pop"), (K["stres"] - 0.1, "pop"),
           (K["uykusuzluk"] - 0.1, "pop"), (K["yatmadan"] - 0.1, "pop"), (K["zararsız"] - 0.15, "ding"),
           (K["Yorumlara"] - 0.08, "pop"), (S_END, "pop")]
    ev = sorted(set((round(a, 3), b) for a, b in ev))
    at.sfx(str(WORK / "sfx.wav"), TOTAL, ev)
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
