"""37. video (uzun, 16:9 2K, ~7,5 dk): Dinozorlar Çağında Hayatta Kalma — komik + bilgi.
Kullanım: python3 video37_komik.py <WORK> [frames t1,t2,..|render [keep]|ses]"""
import json, math, subprocess, sys
from functools import lru_cache
from pathlib import Path

import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from belgesel import *  # noqa

WORK = Path(sys.argv[1])
MED = WORK / "med"
KEY = WORK / "key"
ROZET = Path(__file__).resolve().parent.parent / "assets" / "abi_rozet.mp4"
SR = 44100
NSEG = 11
YEL = (255, 212, 0)


def norm(w):
    return w.lower().strip(".,;:!?'\"").replace("'", "")


# ---------------- ses yerleşimi ----------------
DUR = {i: float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                 str(WORK / f"ses/v{i}.wav")], capture_output=True, text=True).stdout) for i in range(1, NSEG + 1)}
WORDS = {i: json.loads((WORK / f"ses/v{i}.json").read_text(encoding="utf-8")) for i in range(1, NSEG + 1)}
CARD = 2.3
CARDSEG = (2, 4, 6, 9, 11)
G = {1: 0.45}
TITLE0 = G[1] + DUR[1] + 0.4
TITLE1 = TITLE0 + 3.6
CARDS = {}
t_ = TITLE1
for k in range(2, NSEG + 1):
    if k in CARDSEG:
        CARDS[k] = (t_, t_ + CARD)
        G[k] = t_ + CARD + 0.15
    else:
        G[k] = t_ + 0.1
    t_ = G[k] + DUR[k] + 0.5
    if k == 5:
        t_ += 0.8
END = G[NSEG] + DUR[NSEG]
OUT0 = END + 0.5
TOTAL = OUT0 + 7.5
CHAP = {2: ("1. GÜN", "Neredeyim ben?"), 4: ("2. GÜN", "Su, Ateş ve Hayal Kırıklığı"), 6: ("3. GÜN", "Yeni Komşular"),
        9: ("4. GÜN", "Küçük Ama Tehlikeli"), 11: ("SON GÜN", "Kayan Yıldız")}


def T(seg, key, nth=0, exact=False):
    if exact:
        hits = [w for w in WORDS[seg] if norm(w["w"]) == norm(key)]
    elif key[0].isupper() or key[0].isdigit():
        hits = [w for w in WORDS[seg] if w["w"].strip(".,;:!?'\"").startswith(key)]
    else:
        hits = [w for w in WORDS[seg] if norm(w["w"]).startswith(norm(key))]
    return G[seg] + hits[nth]["s"]


def E(seg):
    return G[seg] + DUR[seg]


# ---------------- kesmeler ----------------
CLIPLEN = {}
for p in list(MED.glob("*.mp4")) + list(KEY.glob("*.mp4")):
    d = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
                       capture_output=True, text=True).stdout.strip()
    try:
        CLIPLEN[p.stem] = float(d)
    except ValueError:
        CLIPLEN[p.stem] = 5.0


def clip(name, t0, t1, off=0.0, z=(1.0, 1.07), dx=(0.0, 0.0), dy=(0.0, 0.0), xf=0.3, focus=0.5, speed=None, shake=0):
    src = (KEY if name.startswith("k_") else MED) / f"{name}.mp4"
    need = t1 - t0 + 0.5
    L = CLIPLEN.get(name, 10) - off - 0.15
    sp = speed if speed else clamp(L / need, 0.45, 1.0)
    return {"src": src, "t0": t0, "t1": t1, "off": off, "z": z, "dx": dx, "dy": dy, "xf": xf, "focus": focus, "speed": sp,
            "shake": shake}


def freeze(name, t0, t1, off=0.0, z=(1.08, 1.16), xf=0.0):
    return clip(name, t0, t1, off=off, z=z, xf=xf, speed=0.01)


def photo(name, t0, t1, z=(1.0, 1.1), dx=(0.0, 0.0), dy=(0.0, 0.0), xf=0.3, card=False, fy=0.5):
    return {"img": str(MED / name), "t0": t0, "t1": t1, "z": z, "dx": dx, "dy": dy, "xf": xf, "card": card, "fy": fy}


def dark(t0, t1, xf=0.4):
    return {"bg": "dark", "t0": t0, "t1": t1, "xf": xf}


C = [
    # 1 - uyanış
    clip("uyku_orman_1", 0.0, T(1, "Çünkü") - 0.15, off=3.0, z=(1.1, 1.0), xf=0.0),
    clip("selfie_2", T(1, "Çünkü") - 0.15, T(1, "Çünkü", 1) - 0.15, off=2.0, z=(1.0, 1.06)),
    clip("egrelti_5", T(1, "Çünkü", 1) - 0.15, T(1, "Çünkü", 2) - 0.15, off=4.0, z=(1.0, 1.08)),
    clip("meteor_2", T(1, "Çünkü", 2) - 0.15, T(1, "Evet") - 0.1, off=2.0, z=(1.0, 1.3), xf=0.15, speed=1.0),
    clip("k_troar", T(1, "Evet") - 0.1, T(1, "Yanında") - 0.15, off=0.3, z=(1.0, 1.12), xf=0.0, shake=10),
    clip("pil_3", T(1, "Yanında") - 0.15, T(1, "tek") - 0.15, off=1.0, z=(1.0, 1.04)),
    clip("terlik_1", T(1, "tek") - 0.15, T(1, "Soru") - 0.15, off=3.0, z=(1.6, 1.7), dy=(0.17, 0.17)),
    clip("raptor_3", T(1, "Soru") - 0.15, T(1, "Spoiler") - 0.1, z=(1.0, 1.1)),
    clip("raptor_4", T(1, "Spoiler") - 0.1, TITLE0 + 0.2, off=7.0, z=(1.0, 1.1), speed=0.8),
    clip("k_walk", TITLE0, TITLE1 + 0.1, off=1.0, z=(1.04, 1.1), xf=0.4),
]
CARDBG = {2: ("k_ptero", 1.0), 4: ("nehir_2", 10.0), 6: ("k_tw", 0.5), 9: ("sivrisinek_1", 3.0), 11: ("carpma_1", 1.0)}
for k, (a, b) in CARDS.items():
    C.append(clip(CARDBG[k][0], a, b, off=CARDBG[k][1], z=(1.04, 1.12), xf=0.45))
C += [
    # 2 - neredeyim
    clip("selfie_1", CARDS[2][1], T(2, "zaman") - 0.3, off=3.0, z=(1.0, 1.1), xf=0.0),
    clip("nehir_3", T(2, "zaman") - 0.3, T(2, "Sıcak") - 0.2, off=4.0, z=(1.0, 1.06)),
    clip("egrelti_2", T(2, "Sıcak") - 0.2, T(2, "Akşamı") - 0.2, off=1.0, z=(1.0, 1.08), dx=(0.02, -0.02)),
    clip("gunbatimi_1", T(2, "Akşamı") - 0.2, T(2, "Bu", exact=True) - 0.3, off=6.0, z=(1.0, 1.05)),
    dark(T(2, "Bu", exact=True) - 0.3, T(2, "Bunu") - 0.3),
    clip("fosil_3", T(2, "Bunu") - 0.3, E(2) + 0.2, off=2.0, z=(1.0, 1.1)),
    # 3 - nefes
    clip("uyku_orman_3", G[3] - 0.1, T(3, "araştırmaya") - 0.5, off=1.0, z=(1.0, 1.08)),
    dark(T(3, "araştırmaya") - 0.5, T(3, "Yani") - 0.3),
    clip("dino_orman_4", T(3, "Yani") - 0.3, CARDS[4][0] + 0.2, off=2.0, z=(1.0, 1.08)),
    # 4 - su ve ateş
    clip("nehir_2", CARDS[4][1], T(4, "Dur") - 0.05, off=4.0, z=(1.0, 1.1), xf=0.0),
    freeze("nehir_2", T(4, "Dur") - 0.05, T(4, "bu", exact=True) - 0.1, off=8.0),
    clip("fosil_3", T(4, "bu", exact=True) - 0.1, T(4, "Kaynatman") - 0.2, off=10.0, z=(1.06, 1.14)),
    dark(T(4, "Kaynatman") - 0.2, T(4, "Çakmak") - 0.2),
    clip("zaman_3", T(4, "Çakmak") - 0.2, T(4, "Belgesellerde") - 0.2, off=6.0, z=(1.0, 1.1)),
    clip("ates_1", T(4, "Belgesellerde") - 0.2, T(4, "dakika") - 0.6, off=2.0, z=(1.0, 1.06)),
    clip("cubuk_2", T(4, "dakika") - 0.6, G[5] - 0.1, off=45.5, z=(1.0, 1.1), speed=1.0),
    # 5 - yemek
    clip("uyku_orman_3", G[5] - 0.1, T(5, "Çayır") - 0.2, off=4.0, z=(1.04, 1.12)),
    clip("dino_orman_5", T(5, "Çayır") - 0.2, T(5, "Hangi") - 0.2, off=0.5, z=(1.0, 1.06)),
    clip("egrelti_1", T(5, "Hangi") - 0.2, T(5, "En") - 0.2, off=13.0, z=(1.02, 1.1)),
    clip("nehir_4", T(5, "En") - 0.2, T(5, "başka") - 0.3, off=8.0, z=(1.0, 1.06)),
    clip("timsah_1", T(5, "başka") - 0.3, T(5, "sen", exact=True) - 0.1, off=1.0, z=(1.0, 1.06)),
    clip("timsah_1", T(5, "sen", exact=True) - 0.1, CARDS[6][0] + 0.2, off=7.0, z=(1.35, 1.45), xf=0.0),
    # 6 - T. rex
    clip("gunbatimi_3", CARDS[6][1], T(6, "Senin") - 0.2, off=8.0, z=(1.06, 1.14), xf=0.0),
    clip("terlik_1", T(6, "Senin") - 0.2, T(6, "Tebrikler") - 0.2, off=10.0, z=(1.6, 1.7), dy=(0.17, 0.17)),
    clip("k_tw", T(6, "Tebrikler") - 0.2, T(6, "beyninde") - 0.6, off=2.0, z=(1.0, 1.05)),
    clip("k_sniff", T(6, "beyninde") - 0.6, T(6, "Isırma") - 0.3, off=0.0, z=(1.0, 1.08), speed=0.65),
    clip("k_trex", T(6, "Isırma") - 0.3, T(6, "Bu", exact=True) - 0.2, off=0.0, z=(1.0, 1.08), speed=0.85),
    clip("fil_3", T(6, "Bu", exact=True) - 0.2, T(6, "Karada") - 0.3, off=2.0, z=(1.0, 1.06)),
    clip("saldiri_1", T(6, "Karada") - 0.3, T(6, "Peki") - 0.2, off=1.0, z=(1.0, 1.08)),
    clip("k_trex", T(6, "Peki") - 0.2, T(6, "hesaplamaya") - 0.3, off=1.4, z=(1.45, 1.6), dy=(0.04, 0.05), speed=0.5),
    dark(T(6, "hesaplamaya") - 0.3, T(6, "Senin", 1) - 0.2),
    clip("selfie_2", T(6, "Senin", 1) - 0.2, G[7] - 0.05, off=8.0, z=(1.0, 1.08), shake=4),
    # 7 - kaçış
    clip("k_troar", G[7] - 0.05, T(7, "Koş") - 0.05, off=2.5, z=(1.0, 1.15), xf=0.0),
    clip("k_trun", T(7, "Koş") - 0.05, T(7, "Bilgisayar") - 0.3, off=2.2, z=(1.05, 1.15), shake=14, speed=1.0),
    dark(T(7, "Bilgisayar") - 0.3, T(7, "Ve", 1) - 0.2),
    clip("kosan_1", T(7, "Ve", 1) - 0.2, T(7, "Terlik") - 0.15, off=0.5, z=(1.0, 1.1), shake=6),
    clip("terlik_1", T(7, "Terlik") - 0.15, T(7, "Neyse") - 0.2, off=16.0, z=(1.6, 1.8), dy=(0.17, 0.17)),
    clip("egrelti_5", T(7, "Neyse") - 0.2, T(7, "Nefes") - 0.2, off=12.0, z=(1.0, 1.2), shake=5),
    clip("gunbatimi_3", T(7, "Nefes") - 0.2, T(7, "Bir") - 0.1, off=0.5, z=(1.0, 1.06)),
    clip("raptor_2", T(7, "Bir") - 0.1, T(7, "Gerçek") - 0.25, off=0.0, z=(1.15, 1.0), xf=0.0),
    clip("hindi_3", T(7, "Gerçek") - 0.25, T(7, "Yani") - 0.25, off=1.0, z=(1.0, 1.08)),
    clip("hindi_1", T(7, "Yani") - 0.25, G[8] - 0.05, off=2.0, z=(1.0, 1.1)),
    # 8 - triceratops
    clip("dino_orman_2", G[8] - 0.05, T(8, "Bir") - 0.02, off=0.4, z=(1.0, 1.06)),
    freeze("dino_orman_2", T(8, "Bir") - 0.02, T(8, "on", exact=True) - 0.2, off=6.5, z=(1.1, 1.22)),
    clip("k_trike2", T(8, "on", exact=True) - 0.2, T(8, "Bu", exact=True) - 0.2, off=0.0, z=(1.0, 1.08)),
    clip("k_trike", T(8, "Bu", exact=True) - 0.2, CARDS[9][0] + 0.2, off=0.5, z=(1.0, 1.06)),
    # 9 - böcekler
    clip("sivrisinek_1", CARDS[9][1], T(9, "Evet") - 0.2, off=10.0, z=(1.0, 1.08), xf=0.0),
    clip("sivrisinek_2", T(9, "Evet") - 0.2, T(9, "kene") - 0.2, off=1.0, z=(1.0, 1.06)),
    clip("kene_1", T(9, "kene") - 0.2, T(9, "99") - 0.3, off=2.0, z=(1.0, 1.06)),
    photo("kehribar_wm_1.jpg", T(9, "99") - 0.3, T(9, "dinozor") + 0.4, card=True, z=(1.0, 1.08)),
    photo("kehribar2_wm_1.jpg", T(9, "dinozor") + 0.4, T(9, "Yani") - 0.2, z=(1.0, 1.12), dx=(0.02, -0.03)),
    clip("kene_1", T(9, "Yani") - 0.2, T(9, "Vücudun") - 0.3, off=20.0, z=(1.06, 1.16)),
    clip("sivrisinek_2", T(9, "Vücudun") - 0.3, T(9, "Telefonunda") - 0.2, off=9.0, z=(1.06, 1.12)),
    clip("pil_2", T(9, "Telefonunda") - 0.2, T(9, "Son") - 0.2, off=4.0, z=(1.0, 1.04)),
    clip("k_trike2", T(9, "Son") - 0.2, G[10] - 0.05, off=3.0, z=(1.0, 1.05)),
    # 10 - kaç gün
    clip("gunbatimi_1", G[10] - 0.05, T(10, "Ama") - 0.2, off=1.0, z=(1.0, 1.06)),
    clip("cubuk_2", T(10, "Ama") - 0.2, T(10, "bizim") - 0.2, off=49.0, z=(1.06, 1.12), speed=1.0),
    dark(T(10, "bizim") - 0.2, T(10, "Sen") - 0.2),
    clip("ates_1", T(10, "Sen") - 0.2, T(10, "Ama", 1) - 0.2, off=7.0, z=(1.0, 1.06)),
    clip("dunya_3", T(10, "Ama", 1) - 0.2, CARDS[11][0] + 0.2, off=4.0, z=(1.0, 1.06)),
    # 11 - son gün
    clip("gunbatimi_1", CARDS[11][1], T(11, "Kayan") - 0.2, off=3.0, z=(1.0, 1.12), xf=0.0),
    clip("carpma_1", T(11, "Kayan") - 0.2, T(11, "kayan", 1) - 0.2, off=3.0, z=(1.0, 1.08)),
    freeze("carpma_1", T(11, "kayan", 1) - 0.2, T(11, "10") - 0.3, off=8.0, z=(1.05, 1.15)),
    clip("asteroit_4", T(11, "10") - 0.3, T(11, "Bugünkü") - 0.2, off=2.5, z=(1.0, 1.1)),
    clip("carpma_4", T(11, "Bugünkü") - 0.2, T(11, "Canlı") - 0.2, off=1.0, z=(1.0, 1.08), shake=8),
    clip("volkan_4", T(11, "Canlı") - 0.2, T(11, "Yani") - 0.2, off=2.0, z=(1.0, 1.08)),
    clip("volkan_5", T(11, "Yani") - 0.2, T(11, "Ama") - 0.2, off=4.0, z=(1.0, 1.06)),
    clip("kene_1", T(11, "Ama") - 0.2, T(11, "Bir") - 0.2, off=30.0, z=(1.0, 1.08)),
    clip("zaman_3", T(11, "Bir") - 0.2, T(11, "Daha") - 0.2, off=4.0, z=(1.0, 1.05)),
    dark(T(11, "Daha") - 0.2, TOTAL, xf=0.7),
]

# ---------------- fotoğraf karesi ----------------
TW, TH = int(W * OVER) // 2 * 2, int(H * OVER) // 2 * 2


@lru_cache(maxsize=4)
def photo_frame(path, card, fy):
    im = cv2.cvtColor(cv2.imread(path), cv2.COLOR_BGR2RGB)
    h, w = im.shape[:2]
    s = max(TW / w, TH / h)
    big_ = cv2.resize(im, (int(w * s) + 1, int(h * s) + 1), interpolation=cv2.INTER_CUBIC)
    y0 = int((big_.shape[0] - TH) * fy)
    x0 = (big_.shape[1] - TW) // 2
    cov = big_[y0:y0 + TH, x0:x0 + TW].astype(np.float32)
    if not card:
        return np.clip(cov * 0.97, 0, 255).astype(np.uint8)
    bg = cv2.GaussianBlur(cov, (0, 0), 40) * 0.38
    s2 = min(TW * 0.80 / w, TH * 0.80 / h)
    fw, fh = int(w * s2), int(h * s2)
    fg = cv2.resize(im, (fw, fh), interpolation=cv2.INTER_AREA).astype(np.float32)
    x, y = (TW - fw) // 2, (TH - fh) // 2
    bg[y - 4:y + fh + 4, x - 4:x + fw + 4] = (232, 196, 132)
    bg[y:y + fh, x:x + fw] = fg
    return np.clip(bg, 0, 255).astype(np.uint8)


_yy, _xx = np.mgrid[0:H, 0:W].astype(np.float32)
_r = np.sqrt(((_xx - W * 0.5) / W) ** 2 + ((_yy - H * 0.46) / H) ** 2)
DARKBASE = np.zeros((H, W, 3), np.float32)
for c, (a, b) in enumerate(zip((30, 24, 20), (8, 7, 6))):
    DARKBASE[..., c] = b + (a - b) * np.clip(1 - _r * 1.6, 0, 1) ** 1.5
del _yy, _xx, _r
_pr = np.random.default_rng(37)
EMBERS = [(_pr.uniform(0, W), _pr.uniform(0, H), _pr.uniform(10, 46), _pr.uniform(-10, 10), _pr.uniform(-22, -6),
           _pr.uniform(0, 6.28), GOLD if _pr.random() < 0.7 else (236, 140, 80), _pr.uniform(0.05, 0.15)) for _ in range(40)]
DARKIMG = Image.fromarray(DARKBASE.astype(np.uint8)).convert("RGBA")


def bgfn(name, t, lt):
    im = DARKIMG.copy()
    for x, y, r, vx, vy, ph0, col, a in EMBERS:
        xx = (x + vx * t + 18 * math.sin(t * 0.4 + ph0)) % (W + 200) - 100
        yy = (y + vy * t) % (H + 200) - 100
        dot(im, xx, yy, r, col, a * (0.6 + 0.4 * math.sin(t * 0.7 + ph0)), power=2.2)
    return np.asarray(im.convert("RGB"))


class TL37(Timeline):
    def _cut_frame(self, c, t, readers):
        if "img" in c:
            lt = t - c["t0"]
            q = clamp(lt / max(0.1, c["vis_end"] - c["t0"]))
            fr = photo_frame(c["img"], c["card"], c["fy"])
            z, dx, dy = c["z"], c["dx"], c["dy"]
            return kenburns(fr, q, z[0], z[1], dx[0], dx[1], dy[0], dy[1])
        fr = super()._cut_frame(c, t, readers)
        A = c.get("shake", 0)
        if A:
            lt = t - c["t0"]
            a = A * (0.55 + 0.45 * math.exp(-lt * 2))
            M = np.float32([[1, 0, a * math.sin(t * 53)], [0, 1, a * math.cos(t * 41)]])
            fr = cv2.warpAffine(fr, M, (W, H), borderMode=cv2.BORDER_REFLECT)
        return fr


# ---------------- grafik yardımcıları ----------------
def _lt_shade():
    w, h = 1500, 520
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.sqrt(((xx - 300) / 1100) ** 2 + ((yy - h / 2) / 230) ** 2)
    im = np.zeros((h, w, 4), np.uint8)
    im[..., 3] = (np.clip(1 - d, 0, 1) ** 1.4 * 150).astype(np.uint8)
    return Image.fromarray(im, "RGBA")


LT_SHADE = _lt_shade()
_by = np.arange(H, dtype=np.float32)[:, None]
_bot = np.zeros((H, W, 4), np.uint8)
_bot[..., 3] = (np.clip((_by - H * 0.58) / (H * 0.42), 0, 1) ** 1.3 * 185).astype(np.uint8)
BOT = Image.fromarray(_bot, "RGBA")
_top = np.zeros((H, W, 4), np.uint8)
_top[..., 3] = (np.clip((H * 0.24 - _by) / (H * 0.24), 0, 1) ** 1.5 * 130).astype(np.uint8)
TOP = Image.fromarray(_top, "RGBA")
del _by, _bot, _top


def lower_third(L, t, s, e, name, sub, x=170, y=1150):
    a = window(t, s, e, 0.5, 0.4)
    if a <= 0:
        return
    put(L, LT_SHADE, x - 170, y + 90, "lm", a)
    d = ImageDraw.Draw(L)
    d.rectangle([x, y, x + 110 * eo(ph(t, s, 0.6)), y + 4], fill=GOLD + (int(255 * a),))
    q = eo(ph(t, s + 0.1, 0.6))
    text(L, x - 4, y + 60, name, "sans", "SemiBold", 58, WARM, a * q, track=0.01, anchor="lm", rise=(1 - q) * 14)
    q2 = eo(ph(t, s + 0.3, 0.6))
    text(L, x - 2, y + 122, sub, "sans", "Regular", 36, GREY, a * q2, track=0.02, anchor="lm", rise=(1 - q2) * 14)


def cite(L, t, s, e, txt):
    text(L, 170, 1378, "Kaynak: " + txt, "sans", "Italic", 26, GREY, window(t, s, e, 0.6, 0.5) * 0.8, anchor="lm",
         shadow=0.8)


def quote(L, t, s, e, txt, y=1190, size=86, color=WARM, italic=True):
    a = window(t, s, e, 0.5, 0.4)
    if a <= 0:
        return
    if y > 1000:
        L.alpha_composite(set_alpha(BOT, a))
    q = eo(ph(t, s, 0.9))
    text(L, W / 2, y, txt, "serif", "Regular", size, color, a, track=0.01 + 0.03 * (1 - q), italic=italic, shadow=0.85,
         rise=(1 - q) * 18)


def label(L, x, y, txt, a, size=30, color=WARM, anchor="mm", w="Medium", track=0.18):
    text(L, x, y, txt, "sans", w, size, color, a, track=track, anchor=anchor)


def shade(L, t, s, e, amt=0.45):
    a = window(t, s, e, 0.4, 0.4) * amt
    if a > 0.01:
        L.alpha_composite(Image.new("RGBA", (W, H), (4, 5, 8, int(255 * a))))


def flash(L, t, s, d=0.3, col=(255, 255, 255), amt=0.85):
    if s <= t <= s + d:
        a = (1 - (t - s) / d) ** 2 * amt
        L.alpha_composite(Image.new("RGBA", (W, H), col + (int(255 * a),)))


def big(L, t, s, e, txt, sub="", x=W / 2, y=640, size=230, color=GOLD, subcol=WARM, subsize=52):
    a = window(t, s, e, 0.4, 0.4)
    if a <= 0:
        return
    q = eo(ph(t, s, 0.6))
    im = text_img(txt, ("serif", "Regular", False), size, color, 0.0, 0.85, 0)
    put(L, im, x, y, "mm", a * q, scale=1.0 + 0.12 * (1 - q))
    if sub:
        q2 = eo(ph(t, s + 0.25, 0.6))
        text(L, x, y + size * 0.74, sub, "sans", "Medium", subsize, subcol, a * q2, track=0.04, rise=(1 - q2) * 12)


@lru_cache(maxsize=256)
def meme_img(txt, size, col, stroke):
    f = ImageFont.truetype(INTER.format("Black"), size)
    bb = f.getbbox(txt, stroke_width=stroke)
    w, h = bb[2] - bb[0] + 60, bb[3] - bb[1] + 60
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    sh = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(sh).text((30 - bb[0] + 6, 30 - bb[1] + 10), txt, font=f, fill=(0, 0, 0, 170), stroke_width=stroke,
                           stroke_fill=(0, 0, 0, 170))
    im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(8)))
    ImageDraw.Draw(im).text((30 - bb[0], 30 - bb[1]), txt, font=f, fill=col + (255,), stroke_width=stroke,
                            stroke_fill=(0, 0, 0, 255))
    return im


def meme(L, t, s, e, txt, x=W / 2, y=1170, size=120, col=(255, 255, 255), rot=0.0, stroke=9):
    """komik başlık: kalın, konturlu, zıplayarak gelir"""
    a = window(t, s, e, 0.08, 0.25)
    if a <= 0:
        return
    lt = t - s
    sc = 1.0 + 0.35 * math.exp(-lt * 9) * math.cos(lt * 22)
    im = meme_img(txt, size, col, stroke)
    if rot:
        im = im.rotate(rot, resample=Image.BICUBIC, expand=True)
    put(L, im, x, y, "mm", a, scale=max(0.6, sc))


def aa(w, h, k=2):
    im = Image.new("RGBA", (w * k, h * k), (0, 0, 0, 0))
    return im, ImageDraw.Draw(im)


def check_icon(d, cx, cy, r, col, a, kind="ok"):
    c = col + (int(255 * a),)
    if kind == "ok":
        d.line([(cx - r * 0.55, cy), (cx - r * 0.1, cy + r * 0.45), (cx + r * 0.6, cy - r * 0.45)], fill=c,
               width=int(r * 0.22), joint="curve")
    elif kind == "no":
        d.line([(cx - r * 0.45, cy - r * 0.45), (cx + r * 0.45, cy + r * 0.45)], fill=c, width=int(r * 0.22))
        d.line([(cx - r * 0.45, cy + r * 0.45), (cx + r * 0.45, cy - r * 0.45)], fill=c, width=int(r * 0.22))
    else:
        d.line([(cx, cy - r * 0.5), (cx, cy + r * 0.12)], fill=c, width=int(r * 0.22))
        d.ellipse([cx - r * 0.13, cy + r * 0.32, cx + r * 0.13, cy + r * 0.58], fill=c)


# ---------------- özel grafikler ----------------
def g_eyelids(L, t):
    if t > 2.4:
        return
    if t < 0.45:
        o = 0.3 * eo(t / 0.45)
    elif t < 0.7:
        o = 0.3 - 0.22 * eio((t - 0.45) / 0.25)
    else:
        o = 0.08 + 0.92 * eo(clamp((t - 0.7) / 1.5))
    k = 8
    w, h = W // k, H // k
    m = Image.new("L", (w, h), 255)
    ry = (h / 2 + 30) * o * 1.6
    ImageDraw.Draw(m).ellipse([w / 2 - w * 0.85, h / 2 - ry, w / 2 + w * 0.85, h / 2 + ry], fill=0)
    m = m.filter(ImageFilter.GaussianBlur(6 + 10 * (1 - o))).resize((W, H), Image.BILINEAR)
    lid = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    lid.putalpha(m)
    L.alpha_composite(lid)


def g_warp(L, t, s, e):
    if t < s or t > e + 0.3:
        return
    q = eio(ph(t, s + 0.3, e - s - 0.6))
    val = 2026 - (10 ** (q * math.log10(66_000_000 + 2026)) - 1)
    a = window(t, s, e, 0.2, 0.2)
    s_ = f"{int(val)}" if val > 0 else "−" + f"{int(-val):,}".replace(",", ".")
    label(L, W / 2, 560, "YIL", a * 0.85, 36, GOLD, track=0.6, w="SemiBold")
    text(L, W / 2, 720, s_, "sans", "Bold", 190, WARM, a, track=0.02, shadow=0.9)
    flash(L, t, e - 0.05, 0.45, (255, 250, 238), 0.95)


def g_phone(L, t, s, e, msg="SİNYAL YOK", sub="", x=W * 0.72):
    a = window(t, s, e, 0.4, 0.4)
    if a <= 0:
        return
    q = eo(ph(t, s, 0.6))
    pw, ph_ = 420, 840
    im, d = aa(pw + 40, ph_ + 40)
    k = 2
    d.rounded_rectangle([20 * k, 20 * k, (pw + 20) * k, (ph_ + 20) * k], radius=54 * k, fill=(18, 20, 26, 245),
                        outline=(200, 200, 205, 255), width=5 * k)
    d.rounded_rectangle([34 * k, 34 * k, (pw + 6) * k, (ph_ + 6) * k], radius=42 * k, fill=(30, 34, 46, 255))
    bx, by = 70 * k, 92 * k
    for i in range(4):
        hh = (10 + i * 9) * k
        d.rectangle([bx + i * 14 * k, by - hh, bx + i * 14 * k + 9 * k, by], fill=(110, 112, 120, 255))
    d.line([(bx - 6 * k, by - 44 * k), (bx + 62 * k, by + 6 * k)], fill=RED + (255,), width=5 * k)
    im = im.resize((pw + 40, ph_ + 40), Image.LANCZOS)
    y = H * 0.5 + (1 - q) * 120
    dot(L, x, y, 520, (150, 180, 255), a * q * 0.22, power=2.0)
    put(L, im, x, y, "mm", a * q)
    text(L, x, y - 40, msg, "sans", "Bold", 50, WARM, a * q, track=0.1)
    if sub:
        text(L, x, y + 40, sub, "sans", "Medium", 40, RED, a * q, track=0.06)


def battery_at(t):
    if t < T(1, "%12") - 0.2:
        return None
    if t >= T(9, "%2") - 0.2:
        return 2
    if t >= G[9]:
        return 4
    if t >= G[6]:
        return 6
    if t >= G[4]:
        return 9
    return 12


def terlik_at(t):
    if t < T(1, "tek") - 0.1:
        return None
    return 0 if t >= T(7, "gitti") - 0.1 else 1


def g_hud(L, t):
    hide = (TITLE0 - 0.2 < t < TITLE1 + 0.2 or any(s - 0.2 < t < e + 0.15 for s, e in CARDS.values()) or t > OUT0 - 0.5)
    b = battery_at(t)
    if b is None or hide:
        return
    a = clamp((t - (T(1, "%12") - 0.2)) / 0.4)
    L.alpha_composite(set_alpha(TOP, a))
    day = None
    for k, lab in ((11, "SON GÜN"), (9, "GÜN 4"), (6, "GÜN 3"), (4, "GÜN 2"), (2, "GÜN 1")):
        if t >= G[k]:
            day = lab
            break
    x0, y0 = 150, 80
    d = ImageDraw.Draw(L)
    if day:
        col = RED if day == "SON GÜN" else GOLD
        d.rectangle([x0, y0 + 10, x0 + 6, y0 + 62], fill=col + (int(235 * a),))
        text(L, x0 + 24, y0 + 36, day, "sans", "Bold", 44, col, a, track=0.14, anchor="lm")
        yy = y0 + 104
    else:
        yy = y0 + 36
    # pil
    low = b <= 4
    blink = 1.0 if not low else (0.55 + 0.45 * math.sin(t * 8))
    bc = RED if b < 10 else (240, 200, 90)
    d.rounded_rectangle([x0, yy - 20, x0 + 76, yy + 20], radius=7, outline=(235, 235, 235, int(230 * a)), width=4)
    d.rectangle([x0 + 78, yy - 8, x0 + 84, yy + 8], fill=(235, 235, 235, int(230 * a)))
    d.rectangle([x0 + 6, yy - 14, x0 + 6 + max(4, int(64 * b / 100 * 2.2)), yy + 14], fill=bc + (int(255 * a * blink),))
    text(L, x0 + 100, yy, f"%{b}", "sans", "Bold", 40, bc, a * blink, anchor="lm")
    # terlik
    tr = terlik_at(t)
    if tr is not None:
        tx = x0 + 300
        im, dd = aa(64, 90)
        dd.rounded_rectangle([26, 8, 102, 172], radius=36, fill=(60, 130, 220, 255), outline=(20, 40, 80, 255), width=5)
        dd.line([(64, 46), (30, 104)], fill=(250, 250, 250, 255), width=14)
        dd.line([(64, 46), (98, 104)], fill=(250, 250, 250, 255), width=14)
        dd.ellipse([56, 38, 72, 54], fill=(250, 250, 250, 255))
        put(L, im.resize((64, 90), Image.LANCZOS), tx, yy, "mm", a * (0.45 if tr == 0 else 1.0))
        col = RED if tr == 0 else WARM
        text(L, tx + 50, yy, f"×{tr}", "sans", "Bold", 42, col, a, anchor="lm")
        tg = T(7, "gitti") - 0.1
        if tg <= t < tg + 1.2:
            q = (t - tg) / 1.2
            text(L, tx + 60, yy - 40 - 80 * q, "−1", "sans", "Black", 64, RED, a * (1 - q), anchor="mm")


def g_missing(L, t, s, e):
    """KAYIP İLANI: 1 adet terlik"""
    a = window(t, s, e, 0.3, 0.3)
    if a <= 0:
        return
    q = eo(ph(t, s, 0.5))
    pw, ph_ = 620, 760
    im = Image.new("RGBA", (pw, ph_), (245, 236, 210, 255))
    d = ImageDraw.Draw(im)
    d.rectangle([12, 12, pw - 12, ph_ - 12], outline=(40, 30, 20, 255), width=6)
    f1 = ImageFont.truetype(INTER.format("Black"), 110)
    f2 = ImageFont.truetype(INTER.format("Bold"), 46)
    d.text((pw / 2, 110), "KAYIP", font=f1, fill=(190, 30, 30, 255), anchor="mm")
    d.rounded_rectangle([215, 190, 405, 580], radius=90, fill=(60, 130, 220, 255), outline=(20, 40, 80, 255), width=8)
    d.line([(310, 270), (225, 410)], fill=(250, 250, 250, 255), width=30)
    d.line([(310, 270), (395, 410)], fill=(250, 250, 250, 255), width=30)
    d.ellipse([292, 252, 328, 288], fill=(250, 250, 250, 255))
    d.text((pw / 2, 620), "1 ADET TERLİK", font=f2, fill=(40, 30, 20, 255), anchor="mm")
    d.text((pw / 2, 690), "Görenler yorumlara yazsın", font=ImageFont.truetype(INTER.format("Medium"), 30),
           fill=(80, 70, 60, 255), anchor="mm")
    im = im.rotate(-4, resample=Image.BICUBIC, expand=True)
    put(L, im, W * 0.73, H * 0.5 + (1 - q) * 200, "mm", a)


def g_loading(L, t, s, e):
    a = window(t, s, e, 0.3, 0.3)
    if a <= 0:
        return
    cx, cy, r = W / 2, H / 2 - 40, 90
    im, d = aa(2 * r + 40, 2 * r + 40)
    k = 2
    st = (t * 360) % 360
    d.arc([20 * k, 20 * k, (2 * r + 20) * k, (2 * r + 20) * k], st, st + 270, fill=WARM + (int(240 * a),), width=16 * k)
    put(L, im.resize((2 * r + 40, 2 * r + 40), Image.LANCZOS), cx, cy, "mm", 1.0)
    dots = "." * (1 + int(t * 3) % 3)
    text(L, cx, cy + 170, "Yükleniyor" + dots, "sans", "Bold", 56, WARM, a, anchor="mm")


def g_pin(L, t, s, e, x=W * 0.52, y=H * 0.46):
    a = window(t, s, e, 0.2, 0.4)
    if a <= 0:
        return
    lt = t - s
    drop = max(0, 1 - lt / 0.35)
    bounce = abs(math.sin(lt * 9)) * math.exp(-lt * 4) * 40
    yy = y - 400 * drop ** 2 - bounce
    im, d = aa(160, 220)
    d.ellipse([20, 20, 300, 300], fill=RED + (255,))
    d.polygon([(40, 200), (280, 200), (160, 430)], fill=RED + (255,))
    d.ellipse([110, 110, 210, 210], fill=(255, 255, 255, 255))
    dot(L, x, y + 8, 60, (0, 0, 0), a * 0.35, power=1.5)
    put(L, im.resize((160, 220), Image.LANCZOS), x, yy - 110, "mm", a)
    text(L, x, yy - 290, "BURADASIN", "sans", "Black", 52, WARM, a * clamp((lt - 0.4) / 0.3), track=0.06)


def g_clock(L, t, s, e, t372):
    a = window(t, s, e, 0.5, 0.4)
    if a <= 0:
        return
    cx, cy, R = int(W * 0.29), 650, 250
    q = eio(ph(t, s + 0.2, 1.4))
    im, d = aa(2 * R + 80, 2 * R + 80)
    k = 2
    c0 = (R + 40) * k
    box = [c0 - R * k, c0 - R * k, c0 + R * k, c0 + R * k]
    d.ellipse(box, outline=(70, 72, 80, int(255 * a)), width=16 * k)
    ang = 360 * (23.5 / 24) * q
    if ang > 0.5:
        d.arc(box, -90, -90 + ang, fill=GOLD + (int(255 * a),), width=16 * k)
    if q > 0.98:
        d.arc(box, -90 + 352.5, 270, fill=RED + (int(255 * a * eo(ph(t, s + 1.6, 0.5))),), width=22 * k)
    for i in range(24):
        th = math.radians(i * 15 - 90)
        r1, r2 = (R - 30) * k, (R - (52 if i % 6 == 0 else 40)) * k
        d.line([(c0 + r1 * math.cos(th), c0 + r1 * math.sin(th)), (c0 + r2 * math.cos(th), c0 + r2 * math.sin(th))],
               fill=(150, 152, 160, int(200 * a)), width=(5 if i % 6 == 0 else 3) * k)
    put(L, im.resize((2 * R + 80, 2 * R + 80), Image.LANCZOS), cx, cy, "mm", a)
    text(L, cx, cy - 10, f"{23.5 * q:.1f}".replace(".", ","), "serif", "Regular", 150, WARM, a)
    label(L, cx, cy + 92, "SAAT", a, 34, GOLD, track=0.4, w="SemiBold")
    text(L, cx, cy + R + 110, "Bir gün · bugün 24 saat", "sans", "Medium", 44, GREY, a * eo(ph(t, s + 1.8, 0.6)))
    a2 = a * eo(ph(t, t372 - 0.2, 0.6))
    if a2 > 0.01:
        rx = int(W * 0.71)
        text(L, rx, cy - 30, str(int(365 + 7 * eo(ph(t, t372, 1.0)))), "serif", "Regular", 260, GOLD, a2)
        label(L, rx, cy + 120, "GÜN", a2, 34, GOLD, track=0.4, w="SemiBold")
        text(L, rx, cy + R + 110, "Bir yıl · bugün 365 gün", "sans", "Medium", 44, GREY, a2)


def g_pzt(L, t, s, e):
    """7 tane fazladan pazartesi"""
    a = window(t, s, e, 0.3, 0.4)
    if a <= 0:
        return
    shade(L, t, s, e, 0.55)
    for i in range(7):
        q = eo(ph(t, s + 0.15 + i * 0.17, 0.3))
        if q <= 0.01:
            continue
        x = W / 2 + (i - 3) * 300
        y = 640 + (1 - q) * -200
        im, d = aa(250, 300)
        d.rounded_rectangle([0, 0, 500, 600], radius=40, fill=(246, 242, 234, 255))
        d.rectangle([0, 0, 500, 150], fill=(214, 40, 40, 255))
        d.rounded_rectangle([0, 0, 500, 150], radius=40, fill=(214, 40, 40, 255))
        put(L, im.resize((250, 300), Image.LANCZOS), x, y, "mm", a * q)
        text(L, x, y - 112, "PZT", "sans", "Black", 44, (255, 255, 255), a * q, shadow=0)
        text(L, x, y + 30, "+1", "sans", "Black", 110, (30, 30, 36), a * q, shadow=0)
    meme(L, t, s + 1.4, e, "7 FAZLADAN PAZARTESİ", y=1120, size=110, col=YEL)


def g_shell(L, t, s, e):
    a = window(t, s, e, 0.5, 0.4)
    if a <= 0:
        return
    shade(L, t, s, e, 0.5)
    cx = W // 2
    q = ph(t, s + 0.3, 3.0)
    im, d = aa(1400, 760)
    k = 2
    ox, oy = 700 * k, 700 * k
    for i in range(int(64 * q) + 1):
        r = (70 + i * 9.5) * k
        alp = int(255 * a * (0.55 + 0.45 * (i % 7 == 0)))
        d.arc([ox - r, oy - r, ox + r, oy + r], 200, 340, fill=GOLD + (alp,), width=(4 if i % 7 == 0 else 2) * k)
    put(L, im.resize((1400, 760), Image.LANCZOS), cx, 680, "mm", a)
    text(L, cx, 300, "Fosil kabuktaki günlük büyüme çizgileri", "serif", "Regular", 70, WARM, a, italic=True)
    n = int(372 * q)
    text(L, cx, 1060, f"Sayılan çizgi: {n}", "sans", "Bold", 54, GOLD, a * eo(ph(t, s + 0.4, 0.5)))


O2PTS = [(205, 10), (190, 11.5), (170, 13), (150, 14.5), (130, 16), (110, 17), (90, 17.8), (75, 18.6), (66, 19.3),
         (58, 21.5), (50, 23.0), (40, 22.6), (25, 21.8), (10, 21.2), (0, 21.0)]


def g_o2(L, t, s, e, t_son, t50, t_sen):
    a = window(t, s, e, 0.5, 0.4)
    if a <= 0:
        return
    x0, x1, yb, yt = 420, 2180, 1120, 380
    X = lambda my: x0 + (210 - my) / 210 * (x1 - x0)
    Y = lambda p: yb - p / 28 * (yb - yt)
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    al = int(255 * a)
    d.line([(x0, yb), (x1, yb)], fill=(150, 150, 158, al), width=3)
    for my in (200, 150, 100, 50, 0):
        d.line([(X(my), yb), (X(my), yb + 14)], fill=(150, 150, 158, al), width=3)
    for p in (10, 20):
        d.line([(x0, Y(p)), (x1, Y(p))], fill=(90, 92, 100, int(al * 0.6)), width=2)
    for xx in range(x0, x1, 36):
        d.line([(xx, Y(21)), (xx + 18, Y(21))], fill=CYAN + (int(al * 0.9),), width=4)
    q1 = ph(t, s + 0.6, 1.0)
    q2 = ph(t, t_son, t50 - t_son + 0.6)
    q3 = ph(t, t50 + 0.5, 1.5)
    lim = 205 - 205 * (0.03 * q1) - (205 - 50) * 0.97 * eio(q2) - 50 * eio(q3)
    pts = []
    for (m0, p0), (m1, p1) in zip(O2PTS[:-1], O2PTS[1:]):
        for j in range(12):
            m = m0 + (m1 - m0) * j / 12
            if m < lim:
                break
            pts.append((X(m), Y(p0 + (p1 - p0) * j / 12)))
    if len(pts) > 1:
        d.line(pts, fill=GOLD + (al,), width=9, joint="curve")
        lx, ly = pts[-1]
        d.ellipse([lx - 12, ly - 12, lx + 12, ly + 12], fill=GOLD + (al,))
    L.alpha_composite(im)
    for my, lab in [(200, "200 milyon yıl önce"), (150, "150"), (100, "100"), (50, "50"), (0, "Bugün")]:
        label(L, X(my), yb + 50, lab, a * 0.9, 30, GREY, w="Regular", track=0.04)
    for p in (10, 20):
        label(L, x0 - 30, Y(p), f"%{p}", a * 0.9, 32, GREY, anchor="rm", w="Regular", track=0.02)
    label(L, x1, Y(21) - 32, "BUGÜN %21", a, 32, CYAN, anchor="rm", w="SemiBold", track=0.12)
    text(L, x0, 250, "Havadaki oksijen", "serif", "Regular", 84, WARM, a, anchor="lm")
    label(L, x0 + 4, 318, "YAKLAŞIK DEĞERLER", a * 0.8, 26, GREY, anchor="lm", w="Medium", track=0.3)
    label(L, X(205) + 20, Y(10) + 52, "~%10 · bugünün yarısı", a * eo(ph(t, s + 1.0, 0.6)), 34, GOLD, anchor="lm",
          w="SemiBold", track=0.04)
    label(L, X(50), Y(23) - 50, "~%23", a * eo(ph(t, t50 + 0.3, 0.6)), 36, GOLD, w="SemiBold", track=0.04)
    a3 = a * eo(ph(t, t_sen - 0.2, 0.6))
    if a3 > 0.01:
        px, py = X(66), Y(19.3)
        pulse = 0.5 + 0.5 * math.sin((t - t_sen) * 6)
        dot(L, px, py, 46 + 14 * pulse, RED, a3 * 0.8, power=1.6)
        dot(L, px, py, 14, (255, 236, 220), a3, power=0.6, core=0.6)
        ImageDraw.Draw(L).line([(px, py - 40), (px, py - 150)], fill=RED + (int(230 * a3),), width=4)
        label(L, px + 14, py - 185, "SEN BURADASIN", a3, 34, RED, anchor="rm", w="Bold", track=0.12)


def g_needs(L, t, s, e, rows, title, x=1880, y=300):
    a = window(t, s, e, 0.5, 0.4)
    if a <= 0:
        return
    n = len(rows)
    pw, rh = 580, 96
    put(L, Image.new("RGBA", (pw, 90 + rh * n), (8, 10, 14, int(175 * a))), x, y, "lt", 1.0)
    ImageDraw.Draw(L).rectangle([x, y, x + 6, y + 90 + rh * n], fill=GOLD + (int(230 * a),))
    label(L, x + 36, y + 48, title, a, 28, GOLD, anchor="lm", w="SemiBold", track=0.3)
    for i, (txt, ton, kind) in enumerate(rows):
        q = eo(ph(t, ton, 0.4))
        if q <= 0.01:
            continue
        yy = y + 90 + rh * i + rh / 2
        col = {"ok": GREEN, "no": RED, "warn": (240, 180, 80)}[kind]
        im, dd = aa(70, 70)
        dd.ellipse([4, 4, 136, 136], outline=col + (int(255 * a * q),), width=8)
        check_icon(dd, 70, 70, 52, col, a * q, kind=kind)
        put(L, im.resize((70, 70), Image.LANCZOS), x + 74, yy, "mm", 1.0, scale=1 + 0.3 * (1 - q))
        text(L, x + 130, yy, txt, "sans", "SemiBold", 46, WARM, a * q, anchor="lm", rise=(1 - q) * 10)


_mr = np.random.default_rng(5)
MICROBES = [(_mr.uniform(200, W - 200), _mr.uniform(200, H - 260), _mr.uniform(30, 70), _mr.uniform(0, 6.28),
             _mr.uniform(0.5, 1.4), (_mr.integers(90, 160), _mr.integers(200, 255), _mr.integers(90, 150))) for _ in range(26)]


def g_microbes(L, t, s, e):
    a = window(t, s, e, 0.4, 0.4)
    if a <= 0:
        return
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for i, (x, y, r, p0, sp, col) in enumerate(MICROBES):
        q = eo(ph(t, s + i * 0.04, 0.3))
        if q <= 0:
            continue
        xx = x + 40 * math.sin(t * sp + p0)
        yy = y + 30 * math.cos(t * sp * 1.3 + p0)
        rr = r * q
        wob = 1 + 0.15 * math.sin(t * 6 + p0)
        d.ellipse([xx - rr * wob, yy - rr / wob, xx + rr * wob, yy + rr / wob], fill=tuple(int(c) for c in col) + (int(150 * a),),
                  outline=(30, 90, 40, int(220 * a)), width=4)
        d.ellipse([xx - rr * 0.3, yy - rr * 0.3, xx + rr * 0.1, yy + rr * 0.1], fill=(30, 90, 40, int(200 * a)))
        tx = xx - rr * wob
        d.line([(tx, yy), (tx - rr * 0.8, yy + rr * 0.4 * math.sin(t * 10 + p0))], fill=(30, 90, 40, int(200 * a)), width=4)
    L.alpha_composite(im)


def g_chain(L, t, s, times):
    """SU → KAYNAT → ATEŞ → ÇAKMAK"""
    e = times[-1] + 2.6
    a = window(t, s, e, 0.3, 0.4)
    if a <= 0:
        return
    items = ["SU", "KAYNAT", "ATEŞ", "ÇAKMAK"]
    xs = [W * 0.17, W * 0.39, W * 0.61, W * 0.83]
    for i, (it, tt) in enumerate(zip(items, times)):
        q = eo(ph(t, tt, 0.35))
        if q <= 0.01:
            continue
        cw, chh = 460, 170
        im, d = aa(cw, chh)
        col = (214, 40, 40) if it == "ÇAKMAK" else (40, 44, 56)
        d.rounded_rectangle([3, 3, cw * 2 - 3, chh * 2 - 3], radius=40, fill=col + (235,), outline=GOLD + (255,), width=6)
        put(L, im.resize((cw, chh), Image.LANCZOS), xs[i], 700, "mm", a * q, scale=1 + 0.25 * (1 - q))
        text(L, xs[i], 700, it, "sans", "Black", 64, WARM, a * q, shadow=0)
        if i:
            text(L, (xs[i] + xs[i - 1]) / 2, 700, "→", "sans", "Bold", 80, GOLD, a * q)
    if t > times[-1] + 0.8:
        meme(L, t, times[-1] + 0.8, e, "?", x=xs[-1], y=520, size=150, col=YEL)


def g_timer(L, t, s, e):
    a = window(t, s, e, 0.2, 0.3)
    if a <= 0:
        return
    q = clamp((t - s) / 1.2)
    m = int(40 * q)
    sec = int((40 * q * 60) % 60) if q < 1 else 0
    put(L, Image.new("RGBA", (560, 150), (0, 0, 0, int(150 * a))), W - 150, 160, "rt", 1.0)
    text(L, W - 430, 235, f"{m:02d}:{sec:02d}", "sans", "Bold", 96, (255, 90, 80) if q >= 1 else WARM, a, anchor="mm")
    label(L, W - 430, 300, "SÜRTME SÜRESİ", a, 26, GOLD, w="SemiBold", track=0.3)


@lru_cache(None)
def footprint(sz):
    rim = _fp(sz, (214, 190, 150, 150), 1.12).filter(ImageFilter.GaussianBlur(sz * 0.03))
    rim.alpha_composite(_fp(sz, (26, 18, 12, 225), 1.0), (0, int(sz * 0.02)))
    return rim


def _fp(sz, c, grow):
    k = 3
    im, d = aa(sz, sz, k)
    S = sz * k
    cx, cy = S / 2, S * 0.62
    S = S * grow
    d.ellipse([cx - S * 0.16, cy - S * 0.1, cx + S * 0.16, cy + S * 0.2], fill=c)
    for ang in (-28, 0, 28):
        th = math.radians(ang - 90)
        ln = S * (0.36 if ang == 0 else 0.30)
        tx, ty = cx + ln * math.cos(th), cy + ln * math.sin(th)
        poly = []
        for j in range(24):
            u = j / 23 * 2 * math.pi
            px = 0.5 * ln * math.cos(u)
            py = S * 0.055 * math.sin(u) * (1.0 if math.cos(u) < 0 else 0.6)
            poly.append(((cx + tx) / 2 + px * math.cos(th) - py * math.sin(th),
                         (cy + ty) / 2 + px * math.sin(th) + py * math.cos(th)))
        d.polygon(poly, fill=c)
    return im.resize((sz, sz), Image.LANCZOS).filter(ImageFilter.GaussianBlur(1.2))


def g_footprints(L, t, s, e, times):
    a = window(t, s, e, 0.3, 0.4)
    if a <= 0:
        return
    spots = [(460, 1250, 560, 8), (1000, 1070, 440, -6), (1420, 950, 340, 9), (1760, 860, 260, -5), (2040, 790, 200, 7)]
    for (x, y, sz, rot), tt in zip(spots, times):
        q = eo(ph(t, tt, 0.2))
        if q <= 0.01:
            continue
        im = footprint(sz).rotate(rot - 12, resample=Image.BICUBIC, expand=True)
        im = im.resize((im.width, int(im.height * 0.62)), Image.LANCZOS)
        put(L, im, x, y, "mm", a * q, scale=1.15 - 0.15 * q)


def g_bigfoot(L, t, s, e):
    """terliğin yanına dev ayak izi"""
    a = window(t, s, e, 0.2, 0.3)
    if a <= 0:
        return
    q = eo(ph(t, s, 0.25))
    im = footprint(1500).rotate(-8, resample=Image.BICUBIC, expand=True)
    put(L, im, W * 0.68, H * 0.52, "mm", a * q * 0.92, scale=1.25 - 0.25 * q)


def g_counter(L, t, s, e, t0):
    a = window(t, s, e, 0.4, 0.4)
    if a <= 0:
        return
    L.alpha_composite(set_alpha(BOT, a))
    q = eo(ph(t, t0, 1.2))
    v = int(round(57000 * q / 100.0) * 100)
    label(L, 170, 1000, "ISIRMA GÜCÜ · TAHMİNİ ÜST SINIR", a, 32, GOLD, anchor="lm", w="SemiBold", track=0.24)
    text(L, 162, 1140, f"{v:,}".replace(",", ".") + " N", "sans", "Bold", 170, WARM, a, anchor="lm", shadow=0.9)


def g_stink(L, t, s, e, x=W * 0.5, y=H * 0.62):
    a = window(t, s, e, 0.3, 0.4)
    if a <= 0:
        return
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for j in range(4):
        x0 = x + (j - 1.5) * 120
        pts = []
        for i in range(30):
            u = i / 29
            yy = y - u * 420 - ((t * 120) % 60)
            pts.append((x0 + 34 * math.sin(u * 9 + t * 4 + j), yy))
        d.line(pts, fill=(140, 200, 70, int(210 * a)), width=14, joint="curve")
    L.alpha_composite(im.filter(ImageFilter.GaussianBlur(2)))


def g_circle(L, t, s, e, x, y, r, txt=""):
    a = window(t, s, e, 0.2, 0.3)
    if a <= 0:
        return
    q = eo(ph(t, s, 0.4))
    im, d = aa(int(2 * r + 40), int(2 * r + 40))
    k = 2
    d.arc([20 * k, 20 * k, (2 * r + 20) * k, (2 * r + 20) * k], -90, -90 + 360 * q, fill=RED + (int(255 * a),), width=14 * k)
    put(L, im.resize((int(2 * r + 40), int(2 * r + 40)), Image.LANCZOS), x, y, "mm", 1.0)
    if txt:
        meme(L, t, s + 0.3, e, txt, x=x, y=y + r + 90, size=80, col=YEL)


def g_speed(L, t, s, e, t_rex, t_bolt, t_sen):
    a = window(t, s, e, 0.4, 0.4)
    if a <= 0:
        return
    rows = [("T. REX", 20, t_rex, (240, 160, 70)), ("USAIN BOLT", 44.7, t_bolt, GREEN), ("SEN (TERLİKLE)", 0, t_sen, RED)]
    text(L, 200, 300, "En yüksek hız (km/sa)", "serif", "Regular", 84, WARM, a, anchor="lm")
    x0, x1 = 760, 2300
    for i, (nm, v, tt, col) in enumerate(rows):
        q = eo(ph(t, tt, 0.9))
        if q <= 0.01:
            continue
        y = 560 + i * 230
        text(L, 200, y, nm, "sans", "Bold", 56, WARM, a * clamp(q * 3), anchor="lm")
        if v:
            w = (x1 - x0) * v / 50 * q
            ImageDraw.Draw(L).rounded_rectangle([x0, y - 50, x0 + max(20, w), y + 50], radius=24,
                                                fill=col + (int(235 * a),))
            text(L, x0 + w + 30, y, f"~{int(round(v * q))}", "sans", "Black", 64, col, a, anchor="lm")
        else:
            text(L, x0 + 30, y, "?", "sans", "Black", 90, col, a * q, anchor="lm")


def g_selfie(L, t, s, e):
    a = window(t, s, e, 0.2, 0.3)
    if a <= 0:
        return
    d = ImageDraw.Draw(L)
    m = 120
    c = (255, 255, 255, int(230 * a))
    for (x, y, sx, sy) in ((m, m, 1, 1), (W - m, m, -1, 1), (m, H - m, 1, -1), (W - m, H - m, -1, -1)):
        d.line([(x, y), (x + 120 * sx, y)], fill=c, width=10)
        d.line([(x, y), (x, y + 120 * sy)], fill=c, width=10)
    if int(t * 2) % 2 == 0:
        d.ellipse([W - 330, 130, W - 300, 160], fill=RED + (int(255 * a),))
    text(L, W - 280, 145, "%2", "sans", "Bold", 40, RED, a, anchor="lm")
    d.ellipse([W / 2 - 70, H - 260, W / 2 + 70, H - 120], outline=c, width=10)
    tf = T(9, "çekiyorsun") + 0.3
    flash(L, t, tf, 0.35, (255, 255, 255), 0.95)


def g_skydot(L, t, s, e):
    a = window(t, s, e, 1.0, 0.4)
    if a <= 0:
        return
    q = eio(ph(t, s, e - s))
    x, y = W * 0.64, H * 0.27
    fl = 0.85 + 0.15 * math.sin(t * 23) * math.sin(t * 7)
    dot(L, x, y, 60 + 180 * q, (255, 214, 170), a * 0.35 * fl, power=2.4)
    dot(L, x, y, 14 + 40 * q, (255, 248, 236), a * fl, power=0.8, core=0.55)


def g_sparkle(L, t, s, e, x, y):
    a = window(t, s, e, 0.3, 0.3)
    if a <= 0:
        return
    for i in range(10):
        ang = i * 0.63 + t * 0.8
        r = 160 + 60 * math.sin(t * 3 + i)
        dot(L, x + r * math.cos(ang), y + r * math.sin(ang), 26, (255, 240, 180), a * (0.5 + 0.5 * math.sin(t * 7 + i)),
            power=1.2, core=0.4)


def g_comment(L, t, s, e):
    a = window(t, s, e, 0.4, 0.4)
    if a <= 0:
        return
    q = eo(ph(t, s, 0.5))
    bw, bh = 1100, 220
    im, d = aa(bw + 40, bh + 90)
    k = 2
    d.rounded_rectangle([20 * k, 20 * k, (bw + 20) * k, (bh + 20) * k], radius=60 * k, fill=(246, 242, 234, 245))
    d.polygon([(150 * k, (bh + 15) * k), (130 * k, (bh + 80) * k), (240 * k, (bh + 15) * k)], fill=(246, 242, 234, 245))
    x, y = W / 2, 640 + (1 - q) * 60
    put(L, im.resize((bw + 40, bh + 90), Image.LANCZOS), x, y, "mm", a * q)
    full = "Ben … gün dayanırdım"
    n = int(len(full) * clamp((t - s - 0.4) / 1.3))
    text(L, x - bw / 2 + 80, y - 40, full[:n] + ("|" if int(t * 3) % 2 == 0 else ""), "sans", "SemiBold", 70,
         (30, 30, 36), a * q, anchor="lm", shadow=0)
    label(L, x, y + 210, "YORUMLARA YAZ", a * eo(ph(t, s + 0.7, 0.5)), 40, GOLD, w="Bold", track=0.3)


def g_chips(L, t, s, e):
    a = window(t, s, e, 0.4, 0.4)
    if a <= 0:
        return
    shade(L, t, s, e, 0.6)
    text(L, W / 2, 430, "Sıradaki ışınlanma nereye?", "serif", "Regular", 104, WARM, a, italic=True)
    for i, it in enumerate(["BUZ ÇAĞI", "ANTİK ROMA", "GÖBEKLİTEPE"]):
        q = eo(ph(t, s + 0.3 + i * 0.22, 0.5))
        if q <= 0.01:
            continue
        cx = W / 2 + (i - 1) * 640
        cw, chh = 560, 150
        im, d = aa(cw, chh)
        d.rounded_rectangle([3, 3, cw * 2 - 3, chh * 2 - 3], radius=chh - 3, fill=(12, 14, 20, 210),
                            outline=GOLD + (255,), width=6)
        put(L, im.resize((cw, chh), Image.LANCZOS), cx, 720 + (1 - q) * 40, "mm", a * q)
        text(L, cx, 720 + (1 - q) * 40, it, "sans", "Bold", 52, WARM, a * q, track=0.12)
    label(L, W / 2, 900, "YORUMLARA YAZ", a * eo(ph(t, s + 1.1, 0.5)), 40, GOLD, w="Bold", track=0.3)


def title_card(L, t):
    a = window(t, TITLE0 + 0.1, TITLE1, 0.6, 0.5)
    if a <= 0:
        return
    shade(L, t, TITLE0, TITLE1 + 0.3, 0.5)
    label(L, W / 2, 470, "PRATİK ABİ", a * eo(ph(t, TITLE0 + 0.1, 0.8)) * 0.9, 30, GOLD, track=0.6)
    q1 = eo(ph(t, TITLE0 + 0.2, 1.0))
    text(L, W / 2, 640, "Dinozorlar Çağında", "serif", "Regular", 140, WARM, a * q1, shadow=0.85, rise=(1 - q1) * 20)
    q2 = eo(ph(t, TITLE0 + 0.5, 1.0))
    text(L, W / 2, 810, "Hayatta Kalma Rehberi", "serif", "Regular", 140, GOLD, a * q2, italic=True, shadow=0.85,
         rise=(1 - q2) * 20)
    meme(L, t, TITLE0 + 1.3, TITLE1, "(pek işe yaramaz)", y=980, size=64, col=WARM, rot=3, stroke=6)


def chapter_card(L, t):
    for k, (s, e) in CARDS.items():
        a = window(t, s + 0.1, e + 0.25, 0.5, 0.4)
        if a <= 0:
            continue
        shade(L, t, s, e + 0.25, 0.55)
        col = RED if k == 11 else GOLD
        q = eo(ph(t, s + 0.1, 0.8))
        text(L, W / 2, 600, CHAP[k][0], "sans", "Bold", 150, col, a * q, track=0.1 + 0.08 * (1 - q), rise=(1 - q) * 16)
        q2 = eo(ph(t, s + 0.35, 0.8))
        text(L, W / 2, 780, CHAP[k][1], "serif", "Regular", 96, WARM, a * q2, italic=True, rise=(1 - q2) * 16)


_ROZ = None


def outro(L, t):
    global _ROZ
    a = window(t, OUT0 - 0.6, TOTAL + 1, 0.8, 0.5)
    if a <= 0:
        return
    if _ROZ is None:
        raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-ss", "0.5", "-i", str(ROZET), "-frames:v", "1", "-vf",
                              "scale=400:400", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
        im = Image.frombuffer("RGB", (400, 400), raw, "raw", "RGB", 0, 1).convert("RGBA")
        m = Image.new("L", (1600, 1600), 0)
        ImageDraw.Draw(m).ellipse([0, 0, 1599, 1599], fill=255)
        im.putalpha(m.resize((400, 400), Image.LANCZOS))
        ring = Image.new("RGBA", (428, 428), (0, 0, 0, 0))
        ImageDraw.Draw(ring).ellipse([0, 0, 427, 427], fill=GOLD + (255,))
        ring.alpha_composite(im, (14, 14))
        _ROZ = ring
    q = eo(ph(t, OUT0 - 0.6, 1.0))
    put(L, _ROZ, W / 2, 560, "mm", a * q, scale=0.92 + 0.08 * q)
    text(L, W / 2, 870, "Pratik Abi", "serif", "Regular", 110, WARM, a * q)
    label(L, W / 2, 960, "ŞAŞIRTICI BİLİM, SADE ANLATIM", a * eo(ph(t, OUT0, 0.9)), 30, GOLD, track=0.3)
    q2 = eo(ph(t, OUT0 + 0.5, 0.6))
    if q2 > 0.01:
        bw, bh = 520, 130
        im, d = aa(bw, bh)
        d.rounded_rectangle([0, 0, bw * 2, bh * 2], radius=bh, fill=(214, 40, 40, 255))
        put(L, im.resize((bw, bh), Image.LANCZOS), W / 2, 1150, "mm", a * q2, scale=1 + 0.035 * math.sin((t - OUT0) * 5))
        text(L, W / 2, 1150, "TAKİP ET", "sans", "Bold", 60, (255, 255, 255), a * q2, track=0.14, shadow=0.3)


# ---------------- katman ----------------
def overlay(t):
    L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    # 1
    g_eyelids(L, t)
    meme(L, t, T(1, "alarm"), T(1, "Çünkü") - 0.2, "ALARM: ÇALMADI", y=1180, size=110)
    g_phone(L, t, T(1, "telefonunda") - 0.2, T(1, "Çünkü", 1) - 0.15, "ŞEBEKE YOK")
    meme(L, t, T(1, "burada"), T(1, "Çünkü", 2) - 0.2, "BURADA HİÇBİR ŞEY YOK", y=1180, size=110)
    g_warp(L, t, T(1, "Çünkü", 2) - 0.1, T(1, "Evet") - 0.1)
    meme(L, t, T(1, "dinozorlar"), T(1, "Yanında") - 0.2, "66 MİLYON YIL ÖNCE", y=1180, size=120, col=YEL)
    flash(L, t, T(1, "Evet") - 0.1, 0.25)
    meme(L, t, T(1, "%12"), T(1, "tek") - 0.2, "%12 ŞARJ", y=1180, size=130, col=RED)
    meme(L, t, T(1, "tek"), T(1, "Diğer") - 0.2, "1 ADET TERLİK", y=1180, size=120)
    g_missing(L, t, T(1, "Diğer") - 0.1, T(1, "Soru") - 0.2)
    quote(L, t, T(1, "Burada") - 0.2, T(1, "Spoiler") - 0.15, "Burada kaç gün hayatta kalırsın?", size=92)
    meme(L, t, T(1, "Spoiler") - 0.05, TITLE0 - 0.1, "SPOILER: TERLİK DE GİDİYOR", y=1180, size=100, col=YEL, rot=-3)
    title_card(L, t)
    chapter_card(L, t)
    # 2
    g_loading(L, t, T(2, "haritayı") - 0.1, T(2, "Açılmıyor") + 0.3)
    meme(L, t, T(2, "Açılmıyor") - 0.05, T(2, "zaman") - 0.4, "BAĞLANTI YOK", y=1180, size=110, col=RED)
    g_pin(L, t, T(2, "Burası") - 0.1, T(2, "Sıcak") - 0.3)
    lower_third(L, t, T(2, "Hell") - 0.2, T(2, "Sıcak") - 0.4, "Hell Creek", "Bugünkü Montana ve Dakotalar, ABD")
    meme(L, t, T(2, "Sıcak"), T(2, "dev") - 0.1, "SICAK + NEMLİ", y=1180, size=100)
    quote(L, t, T(2, "Güneş") - 0.2, T(2, "Saatin") - 0.1, "Güneş biraz erken batıyor…", size=88)
    meme(L, t, T(2, "Saatin") - 0.05, T(2, "Bu", exact=True) - 0.35, "SAATİN BOZUK DEĞİL", y=1180, size=100)
    g_clock(L, t, T(2, "Bu", exact=True) - 0.2, T(2, "Yani") - 0.25, T(2, "yılda") - 0.2)
    g_pzt(L, t, T(2, "Yani") - 0.15, T(2, "Bunu") - 0.35)
    g_shell(L, t, T(2, "Bunu") - 0.2, T(2, "Evet") - 0.2)
    cite(L, t, T(2, "Bunu") + 0.4, E(2), "de Winter ve ark., Paleoceanography and Paleoclimatology, 2020")
    meme(L, t, T(2, "Evet") - 0.05, T(2, "Bilim") - 0.2, "BİRİLERİ OTURUP SAYDI", y=1050, size=100)
    meme(L, t, T(2, "Bilim"), E(2) + 0.3, "BİLİM BU.", y=1050, size=150, col=YEL)
    # 3
    meme(L, t, T(3, "Bu", exact=True) - 0.05, T(3, "araştırmaya") - 0.6, "BU HAVA SOLUNUR MU?", y=1180, size=110)
    g_o2(L, t, T(3, "araştırmaya") - 0.3, T(3, "Yani") - 0.35, T(3, "Sonra"), T(3, "elli"), T(3, "Senin"))
    cite(L, t, T(3, "araştırmaya") + 0.3, T(3, "Yani") - 0.4, "Falkowski ve ark., Science, 2005")
    quote(L, t, T(3, "Yani") - 0.1, T(3, "Bugünkü") - 0.2, "Nefes alabilirsin.", size=96, color=GREEN)
    g_needs(L, t, T(3, "Bugünkü") - 0.2, CARDS[4][0], [("Ölmedin", T(3, "Ölmedin") - 0.1, "ok")], "BUGÜNÜN BAŞARILARI",
            x=1850, y=330)
    # 4
    flash(L, t, T(4, "Dur") - 0.05, 0.2, (255, 60, 60), 0.5)
    meme(L, t, T(4, "Dur") - 0.05, T(4, "bu", exact=True) - 0.15, "DUR!", y=H / 2, size=260, col=RED, rot=-4)
    g_microbes(L, t, T(4, "bu", exact=True) - 0.1, T(4, "Kaynatman") - 0.2)
    quote(L, t, T(4, "bağışıklık") - 0.2, T(4, "Kaynatman") - 0.3, "Bağışıklığının hiç tanımadığı mikroplar", size=80)
    g_chain(L, t, T(4, "Kaynatman") - 0.1, [T(4, "Kaynatman") - 0.1, T(4, "Kaynatmak"), T(4, "Ateş"), T(4, "çakmak")])
    meme(L, t, T(4, "Evde") - 0.05, T(4, "Belgesellerde") - 0.2, "ÇAKMAK: EVDE", y=520, size=130, col=YEL)
    meme(L, t, T(4, "66") - 0.05, T(4, "Belgesellerde") - 0.2, "(66.000.000 YIL İLERİDE)", y=700, size=72)
    meme(L, t, T(4, "Belgesellerde"), T(4, "dakika") - 0.6, "BELGESELDE:", x=W / 2, y=300, size=110, col=GREEN)
    meme(L, t, T(4, "dakika") - 0.55, G[5] - 0.2, "SENDE:", x=W / 2, y=300, size=110, col=RED)
    g_timer(L, t, T(4, "dakika") - 0.5, T(4, "yorgun") + 0.6)
    meme(L, t, T(4, "yorgun") - 0.25, T(4, "Ateş", 1) - 0.2, "2 YORGUN KOL + 1 SU TOPLAMIŞ AVUÇ", y=1180, size=84)
    meme(L, t, T(4, "Ateş", 1) - 0.05, G[5] - 0.2, "ATEŞ: YOK", y=1150, size=170, col=RED)
    # 5
    quote(L, t, T(5, "Çiçekli") - 0.2, T(5, "Çayır") - 0.3, "Çiçek var. Tanıdık meyve yok.", size=88)
    meme(L, t, T(5, "Çayır") - 0.05, T(5, "Hangi") - 0.3, "ÇAYIR ÇİMEN DE YOK", y=1180, size=110)
    meme(L, t, T(5, "zehirli") - 0.1, T(5, "En") - 0.3, "ZEHİRLİ Mİ?", y=1150, size=150, col=YEL, rot=3)
    quote(L, t, T(5, "En") - 0.1, T(5, "başka") - 0.4, "En mantıklısı: balık tutmak", size=88)
    lower_third(L, t, T(5, "başka") + 0.3, T(5, "sen", exact=True) - 0.2, "Hell Creek'te timsahlar da vardı",
                "Borealosuchus · Brachychampsa")
    meme(L, t, T(5, "sen", exact=True) - 0.05, CARDS[6][0], "SEN = BALIK", y=1150, size=170, col=YEL, rot=-3)
    # 6
    g_footprints(L, t, T(6, "Toprakta") - 0.1, T(6, "Senin") - 0.2, [T(6, "Toprakta") + 0.2 + 0.4 * i for i in range(5)])
    meme(L, t, T(6, "çok") - 0.05, T(6, "Senin") - 0.2, "ÇOK BÜYÜK", y=420, size=150, col=YEL)
    g_bigfoot(L, t, T(6, "Senin") + 0.6, T(6, "Tebrikler") - 0.2)
    meme(L, t, T(6, "Tebrikler") - 0.05, T(6, "Saklanmayı") - 0.2, "YENİ MAHALLEN", y=300, size=120, col=YEL)
    lower_third(L, t, T(6, "Tyrannosaurus") - 0.1, T(6, "beyninde") - 0.7, "Tyrannosaurus rex",
                "Boyu 12 metreyi bulabiliyordu")
    quote(L, t, T(6, "beyninde") - 0.2, T(6, "İki") - 0.2, "Seni görmeden kokunu alabilirdi", size=86)
    g_stink(L, t, T(6, "İki") - 0.1, T(6, "Isırma") - 0.3, x=W * 0.3, y=H * 0.95)
    meme(L, t, T(6, "duş") - 0.1, T(6, "Isırma") - 0.3, "DUŞ: 2 GÜNDÜR YOK", y=1180, size=110)
    g_counter(L, t, T(6, "57") - 0.5, T(6, "Bu", exact=True) - 0.3, T(6, "57") - 0.4)
    cite(L, t, T(6, "57"), T(6, "Bu", exact=True) - 0.4, "Bates & Falkingham, Biology Letters, 2012")
    big(L, t, T(6, "Bu", exact=True) + 0.1, T(6, "Karada") - 0.4, "≈ 5,8 ton", "oturan orta boy bir fil kadar", y=1060,
        size=170)
    quote(L, t, T(6, "Karada") - 0.1, T(6, "Peki") - 0.3, "Karada yaşamış en güçlü ısırık", size=90)
    g_circle(L, t, T(6, "kolları") - 0.1, T(6, "hesaplamaya") - 0.3, W * 0.5, H * 0.6, 170, "KISA")
    meme(L, t, T(6, "Ama") - 0.05, T(6, "hesaplamaya") - 0.3, "GÜLME.", y=300, size=130, col=RED)
    big(L, t, T(6, "200") - 0.3, T(6, "Senin", 1) - 0.25, "≈ 200 kg", "tek kolun kaldırabildiği (tahmini)", y=640, size=220)
    cite(L, t, T(6, "200") - 0.2, T(6, "Senin", 1) - 0.3, "Carpenter & Smith, 2001")
    meme(L, t, T(6, "Senin", 1) + 0.2, G[7] - 0.1, "SENİN KOLUN: KALKMIYOR", y=1180, size=100)
    # 7
    flash(L, t, T(7, "Arkanda") + 0.6, 0.2, (255, 255, 255), 0.4)
    meme(L, t, T(7, "Koş") - 0.05, T(7, "İyi") - 0.1, "KOŞ!", y=H / 2, size=300, col=YEL, rot=-6)
    quote(L, t, T(7, "İyi") - 0.05, T(7, "Bilgisayar") - 0.35, "İyi haber: arabayı kovalayamazdı", size=86, color=GREEN)
    g_speed(L, t, T(7, "Bilgisayar") - 0.2, T(7, "Ve", 1) - 0.25, T(7, "20") - 0.4, T(7, "44") - 0.4, T(7, "Kötü") - 0.1)
    cite(L, t, T(7, "Bilgisayar"), T(7, "Ve", 1) - 0.3, "Sellers ve ark., PeerJ, 2017")
    meme(L, t, T(7, "Terlik") - 0.05, T(7, "Neyse") - 0.25, "TERLİK GİTTİ", y=1150, size=150, col=RED)
    meme(L, t, T(7, "Bir") - 0.05, T(7, "Filmlerdeki", 1) - 0.1, "VELOZİRAPTOR!", y=1150, size=150, col=RED, rot=-3)
    meme(L, t, T(7, "Filmlerdeki", 1) - 0.05, T(7, "Gerçek") - 0.3, "FİLMLERDEKİ HALİ", y=260, size=100)
    if T(7, "değil", 1) - 0.1 < t < T(7, "Gerçek") - 0.3:
        ImageDraw.Draw(L).line([(W / 2 - 640, 270), (W / 2 + 640, 250)], fill=RED + (255,), width=18)
    meme(L, t, T(7, "hindi") - 0.1, T(7, "Üstelik") - 0.2, "GERÇEK BOYUTU: HİNDİ", y=1150, size=120, col=YEL)
    g_needs(L, t, T(7, "Gerçek") - 0.1, T(7, "Yani") - 0.3,
            [("Hindi büyüklüğünde", T(7, "hindi") - 0.1, "ok"), ("Tüylü", T(7, "tüylüydü") - 0.1, "ok"),
             ("Asya'da yaşadı", T(7, "Asya") - 0.1, "ok")], "GERÇEK VELOZİRAPTOR", x=1900, y=320)
    meme(L, t, T(7, "kuştu") - 0.3, T(7, "Sen", 1) - 0.1, "TEHLİKE SEVİYESİ: KUŞ", y=1170, size=110)
    meme(L, t, T(7, "Sen", 1) - 0.05, G[8] - 0.1, "SEN ONDAN DA KORKTUN", y=1170, size=110, col=YEL)
    # 8
    meme(L, t, T(8, "zararsız") - 0.1, T(8, "Bir") - 0.1, "ZARARSIZ :)", y=1170, size=120, col=GREEN)
    meme(L, t, T(8, "Bir") - 0.02, T(8, "on", exact=True) - 0.25, "…BİR DAKİKA.", y=H / 2, size=180, col=YEL)
    lower_third(L, t, T(8, "on", exact=True) - 0.1, T(8, "Bu", exact=True) - 0.3, "Triceratops", "10 tona kadar ulaşabiliyordu")
    quote(L, t, T(8, "Bu", exact=True) - 0.1, T(8, "Seni") - 0.2, "En tehlikelisi seni yemek isteyen değil…", size=84)
    meme(L, t, T(8, "Seni") - 0.05, CARDS[9][0], "SENİ HİÇ GÖRMEYEN", y=1170, size=130, col=RED)
    # 9
    meme(L, t, T(9, "vızıldadı") - 0.2, T(9, "Evet") - 0.2, "VIZZZZ", y=500, size=170, col=YEL, rot=6)
    quote(L, t, T(9, "Evet") - 0.1, T(9, "99") - 0.4, "Sivrisinekler de, keneler de vardı", size=86)
    lower_third(L, t, T(9, "99") + 0.1, T(9, "Yani") - 0.4, "99 milyon yıllık kehribar", "Dinozor tüyüne tutunmuş kene · Myanmar")
    cite(L, t, T(9, "99") + 0.5, T(9, "Başka") - 0.4, "Peñalver ve ark., Nature Communications, 2017")
    meme(L, t, T(9, "Seni") - 0.05, T(9, "Başka") - 0.3, "SENİ HİÇ BIRAKMAZ", y=1170, size=120, col=RED)
    big(L, t, T(9, "8") - 0.2, T(9, "Vücudun") - 0.4, "8 kat", "kan emerek şişmiş kene", y=1050, size=190)
    meme(L, t, T(9, "antibiyotik") - 0.1, T(9, "Telefonunda") - 0.25, "ANTİBİYOTİK: YOK", y=1170, size=130, col=RED)
    meme(L, t, T(9, "%2") - 0.1, T(9, "Son") - 0.25, "%2", y=H / 2 + 300, size=200, col=RED)
    g_selfie(L, t, T(9, "Son") - 0.2, G[10] - 0.1)
    meme(L, t, T(9, "Arkada") + 0.2, G[10] - 0.1, "*ESNER*", x=W * 0.68, y=360, size=110, col=YEL, rot=5)
    # 10
    g_needs(L, t, T(10, "Suyu") - 0.2, T(10, "Ama") - 0.25,
            [("Su kaynatmak", T(10, "Suyu"), "ok"), ("Ateş yakmak", T(10, "ateş"), "ok"),
             ("Saklanmak", T(10, "saklanmayı"), "ok")], "HEPSİNİ ÖĞRENİRSEN")
    big(L, t, T(10, "birkaç") - 0.1, T(10, "Ama") - 0.3, "Birkaç hafta", "", x=W * 0.36, y=700, size=150, color=GREEN)
    meme(L, t, T(10, "performansına") - 0.2, T(10, "bizim") - 0.25, "PERFORMANS: 0/10", y=1170, size=120, col=RED)
    label(L, W / 2, 470, "BİZİM TAHMİNİMİZ", window(t, T(10, "bizim"), T(10, "Sen") - 0.2, 0.4, 0.3), 40, GOLD,
          w="SemiBold", track=0.4)
    big(L, t, T(10, "birkaç", 1) - 0.1, T(10, "Sen") - 0.2, "Birkaç gün", "", y=700, size=210, color=RED)
    g_comment(L, t, T(10, "Sen") - 0.1, T(10, "Ama", 1) - 0.25)
    meme(L, t, T(10, "Hem") - 0.05, CARDS[11][0], "HEM DE EN BÜYÜĞÜ", y=1170, size=120, col=RED)
    # 11
    g_skydot(L, t, T(11, "gökyüzünde") - 0.3, T(11, "Kayan") - 0.2)
    g_sparkle(L, t, T(11, "dilek") - 0.2, T(11, "kayan", 1) - 0.2, W * 0.5, H * 0.45)
    meme(L, t, T(11, "Eve") - 0.1, T(11, "kayan", 1) - 0.25, "DİLEK: EVE DÖNMEK", y=1170, size=120, col=YEL)
    meme(L, t, T(11, "kayan", 1) - 0.15, T(11, "10") - 0.35, "O KAYAN YILDIZ DEĞİL.", y=H / 2, size=150, col=RED)
    big(L, t, T(11, "10") - 0.1, T(11, "Bugünkü") - 0.3, "≈ 10 km", "genişliğinde bir asteroit", y=1060, size=170)
    lower_third(L, t, T(11, "180") - 0.2, T(11, "Canlı") - 0.4, "Chicxulub Krateri", "Yucatán, Meksika · Çapı yaklaşık 180 km")
    big(L, t, T(11, "Canlı") - 0.1, T(11, "Yani") - 0.3, "%75", "canlı türlerinin yaklaşık dörtte üçü yok oldu", y=960,
        size=200, color=RED)
    quote(L, t, T(11, "son", exact=True) - 0.1, T(11, "Ama") - 0.3, "Son gün çoktan belli.", size=100)
    meme(L, t, T(11, "Artık") - 0.05, T(11, "Bir") - 0.25, "KENE DERDİ: BİTTİ", y=1170, size=120, col=GREEN)
    g_chips(L, t, T(11, "Bir") - 0.1, T(11, "Daha") - 0.2)
    outro(L, t)
    g_hud(L, t)
    fb = clamp((t - (TOTAL - 1.0)) / 1.0)
    if fb > 0.01:
        L.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, int(255 * fb))))
    if not (TITLE0 - 0.3 < t < TITLE1 + 0.3 or any(s - 0.3 < t < e + 0.3 for s, e in CARDS.values()) or t > OUT0 - 0.8
            or t < 3.0):
        label(L, W - 120, 92, "PRATİK ABİ", 0.42, 24, WARM, anchor="rm", w="SemiBold", track=0.4)
    return L


TL = TL37(C, TOTAL, overlay, bgfn)


# ---------------- ses ----------------
def load(path, sr=SR):
    r = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(path), "-f", "f32le", "-ac", "1", "-ar", str(sr), "-"],
                       capture_output=True, check=True)
    return np.frombuffer(r.stdout, np.float32).copy()


def sfx_track(n):
    from scipy.signal import butter, lfilter
    rng = np.random.default_rng(37)
    fx = np.zeros(n, np.float32)

    def add(t, y, g=1.0):
        a = int(t * SR)
        if a < 0:
            y, a = y[-a:], 0
        b = min(n, a + len(y))
        if b > a:
            fx[a:b] += (y[:b - a] * g).astype(np.float32)

    def bp(y, lo, hi, o=2):
        b, a = butter(o, [lo / (SR / 2), hi / (SR / 2)], "band")
        return lfilter(b, a, y)

    def lp(y, f, o=2):
        b, a = butter(o, f / (SR / 2))
        return lfilter(b, a, y)

    def nrm(y, g=0.9):
        return y / (np.abs(y).max() + 1e-9) * g

    def whoosh(d=0.8):
        m = int(d * SR)
        tt = np.linspace(0, 1, m)
        return nrm(bp(rng.standard_normal(m), 300, 5000) * np.sin(np.pi * tt ** 0.7) ** 2, 0.5)

    def boom(d=2.0, f0=70, f1=32):
        m = int(d * SR)
        tt = np.arange(m) / SR
        y = np.sin(2 * np.pi * np.cumsum(f1 + (f0 - f1) * np.exp(-tt * 3)) / SR) * np.exp(-tt * 2.2)
        y += lp(rng.standard_normal(m), 900) * np.exp(-tt * 18) * 0.6
        return nrm(y)

    def thud():
        m = int(0.7 * SR)
        tt = np.arange(m) / SR
        y = np.sin(2 * np.pi * np.cumsum(45 + 60 * np.exp(-tt * 25)) / SR) * np.exp(-tt * 7)
        y += lp(rng.standard_normal(m), 400) * np.exp(-tt * 30) * 0.5
        return nrm(y)

    def roar(d=2.4, f0=85):
        m = int(d * SR)
        tt = np.arange(m) / SR
        f = f0 * (0.8 + 0.35 * np.sin(np.pi * tt / d)) + lp(rng.standard_normal(m), 30) * 40
        ph_ = 2 * np.pi * np.cumsum(f) / SR
        src = sum(np.sign(np.sin(h * ph_)) / h for h in (1, 2, 3, 5)) + lp(rng.standard_normal(m), 3000) * 1.2
        am = 1 + 3 * lp(rng.standard_normal(m), 60)
        y = (bp(src, 180, 520) + bp(src, 600, 1200) * 0.6 + bp(src, 1500, 2600) * 0.25) * am
        y = lp(y * np.clip(tt / 0.3, 0, 1) * np.clip((d - tt) / 1.0, 0, 1), 1600)
        ir = rng.standard_normal(int(1.4 * SR)) * np.exp(-np.arange(int(1.4 * SR)) / SR * 3.5)
        out = np.zeros(m + len(ir) - 1)
        out[:m] += y * 0.55
        out += np.convolve(y, ir) * 0.02
        return nrm(out, 0.75)

    def scratch():
        m = int(0.45 * SR)
        tt = np.arange(m) / SR
        f = 900 + 700 * np.sin(2 * np.pi * 7 * tt)
        y = bp(rng.standard_normal(m), 400, 3000) * (0.6 + 0.4 * np.sin(2 * np.pi * np.cumsum(f) / SR))
        return nrm(y * np.exp(-tt * 3), 0.6)

    def boing():
        m = int(0.6 * SR)
        tt = np.arange(m) / SR
        f = 180 + 300 * np.exp(-tt * 6) + 30 * np.sin(2 * np.pi * 18 * tt)
        return nrm(np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 4), 0.55)

    def trombone():
        out = []
        for i, (f, d) in enumerate([(311, 0.42), (294, 0.42), (277, 0.42), (262, 1.3)]):
            m = int(d * SR)
            tt = np.arange(m) / SR
            vib = 1 + (0.012 * np.sin(2 * np.pi * 5.5 * tt) if i == 3 else 0)
            ph_ = 2 * np.pi * np.cumsum(f * vib * (1 - 0.02 * tt)) / SR
            y = sum(np.sin(h * ph_) / h ** 0.9 for h in range(1, 9))
            y = lp(y, 1800) * np.clip(tt / 0.04, 0, 1) * np.clip((d - tt) / 0.08, 0, 1)
            out.append(y)
        return nrm(np.concatenate(out), 0.5)

    def pop():
        m = int(0.1 * SR)
        tt = np.arange(m) / SR
        return np.sin(2 * np.pi * (900 - 4000 * tt) * tt) * np.exp(-tt * 45) * 0.35

    def ding():
        m = int(1.0 * SR)
        tt = np.arange(m) / SR
        return (np.sin(2 * np.pi * 1318 * tt) + 0.4 * np.sin(2 * np.pi * 2637 * tt)) * np.exp(-tt * 5) * 0.25

    def shutter():
        m = int(0.18 * SR)
        tt = np.arange(m) / SR
        y = bp(rng.standard_normal(m), 1500, 8000) * (np.exp(-tt * 60) + 0.7 * np.exp(-np.abs(tt - 0.09) * 80))
        return nrm(y, 0.6)

    def buzz(d=2.0):
        m = int(d * SR)
        tt = np.arange(m) / SR
        f = 560 + 40 * np.sin(2 * np.pi * 3 * tt)
        y = np.sign(np.sin(2 * np.pi * np.cumsum(f) / SR)) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.7 * tt) ** 2)
        y = bp(y, 400, 3000) * np.clip(tt / 0.3, 0, 1) * np.clip((d - tt) / 0.3, 0, 1)
        return nrm(y, 0.25)

    def ticks(d=1.2):
        out = np.zeros(int(d * SR))
        for i in range(int(d * 14)):
            a = int(i / 14 * SR)
            out[a:a + 300] += np.sin(2 * np.pi * 2500 * np.arange(300) / SR) * np.exp(-np.arange(300) / 40) * 0.3
        return out

    def rumble(d=6.0):
        m = int(d * SR)
        tt = np.arange(m) / SR
        return nrm(lp(rng.standard_normal(m), 120, 3) * np.clip(tt / 1.5, 0, 1) * np.clip((d - tt) / 2.0, 0, 1))

    def chime():
        m = int(1.6 * SR)
        tt = np.arange(m) / SR
        y = sum(np.sin(2 * np.pi * f * tt) * np.exp(-tt * 3) * np.clip((tt - i * 0.08) * 50, 0, 1)
                for i, f in enumerate((1568, 2093, 2637, 3136)))
        return nrm(y, 0.3)

    # --- olaylar ---
    add(T(1, "alarm"), pop(), 0.8)
    add(T(1, "Çünkü", 2) - 0.2, whoosh(1.2), 0.8)
    add(T(1, "Evet") - 0.25, boom(1.6, 90, 40), 0.7)
    add(T(1, "Evet") - 0.05, roar(2.2, 85), 0.55)
    for k in ("%12", "tek"):
        add(T(1, k) - 0.05, pop(), 0.9)
    add(T(1, "Diğer") - 0.05, boing(), 0.6)
    add(T(1, "Spoiler"), scratch(), 0.6)
    add(TITLE0 - 0.2, boom(), 0.8)
    for k, (s, e) in CARDS.items():
        add(s - 0.3, whoosh(0.9), 0.55)
        add(s + 0.1, boom(1.6, 75, 35), 0.4 if k != 11 else 0.8)
    add(T(2, "Açılmıyor"), trombone(), 0.35)
    add(T(2, "Burası") + 0.3, pop(), 0.9)
    for i in range(7):
        add(T(2, "Yani") + 0.0 + i * 0.17, pop(), 0.7)
    add(T(2, "Bilim"), ding(), 0.8)
    add(T(3, "Ölmedin") - 0.1, ding(), 0.8)
    add(T(4, "Dur") - 0.1, scratch(), 0.8)
    for k in ("Kaynatman", "Kaynatmak", "Ateş", "çakmak"):
        add(T(4, k), pop(), 0.8)
    add(T(4, "Evde"), boing(), 0.6)
    add(T(4, "dakika") - 0.5, ticks(1.2), 0.8)
    add(T(4, "Ateş", 1) - 0.1, trombone(), 0.55)
    add(T(5, "zehirli") - 0.1, boing(), 0.5)
    add(T(5, "başka") - 0.2, boom(1.4, 60, 30), 0.5)
    add(T(5, "sen", exact=True), scratch(), 0.5)
    for i in range(5):
        add(T(6, "Toprakta") + 0.2 + 0.4 * i, thud(), 0.55 + 0.08 * i)
    add(T(6, "Senin") + 0.6, thud(), 0.9)
    add(T(6, "Tebrikler") - 0.1, ding(), 0.6)
    add(T(6, "Tebrikler") + 0.8, roar(2.4, 72), 0.5)
    add(T(6, "İki") + 0.3, boing(), 0.4)
    add(T(6, "Isırma") - 0.1, roar(2.0, 95), 0.5)
    add(T(6, "57") - 0.4, whoosh(0.6), 0.35)
    add(T(6, "kolları") - 0.1, pop(), 0.8)
    add(T(6, "Ama") - 0.05, scratch(), 0.5)
    add(T(6, "Senin", 1) + 0.2, trombone(), 0.3)
    add(T(7, "Arkanda") + 0.5, roar(2.6, 78), 0.75)
    add(T(7, "Koş") - 0.1, boom(1.2, 90, 45), 0.6)
    add(T(7, "Terlik") - 0.1, trombone(), 0.5)
    add(T(7, "Bir") - 0.1, scratch(), 0.6)
    add(T(7, "hindi") - 0.1, boing(), 0.6)
    add(T(7, "Sen", 1) - 0.05, trombone(), 0.35)
    add(T(8, "Bir") - 0.05, scratch(), 0.8)
    add(T(8, "on", exact=True), boom(1.6, 60, 30), 0.5)
    add(T(9, "Gece"), buzz(2.4), 0.8)
    add(T(9, "Seni") - 0.05, boing(), 0.4)
    add(T(9, "%2") - 0.1, pop(), 0.9)
    add(T(9, "çekiyorsun") + 0.3, shutter(), 0.9)
    add(T(9, "Arkada") + 0.2, boing(), 0.5)
    for k in ("Suyu", "ateş", "saklanmayı"):
        add(T(10, k), ding(), 0.5)
    add(T(10, "performansına") - 0.2, trombone(), 0.35)
    add(T(10, "Ama", 1) - 0.1, scratch(), 0.6)
    add(T(11, "gökyüzünde") - 0.3, rumble(6.0), 0.3)
    add(T(11, "dilek") - 0.2, chime(), 0.7)
    add(T(11, "kayan", 1) - 0.15, scratch(), 0.7)
    add(T(11, "Bugünkü") - 0.2, boom(3.0, 60, 25), 0.9)
    add(T(11, "Bugünkü") + 0.2, rumble(5.0), 0.5)
    add(T(11, "Artık") - 0.05, ding(), 0.6)
    add(T(11, "Bir") - 0.2, whoosh(1.0), 0.45)
    add(OUT0 - 0.4, ding(), 0.5)
    return fx


def build_audio():
    n = int(TOTAL * SR) + SR
    voice = np.zeros(n, np.float32)
    for i in range(1, NSEG + 1):
        x = load(WORK / f"ses/v{i}.wav")
        a = int(G[i] * SR)
        voice[a:a + len(x)] += x
    import audio_tools as at
    at._write(str(WORK / "voice_full.wav"), voice[:int(TOTAL * SR)])
    trk = {k: load(WORK / f"m{k}.wav") for k in ("a", "b", "epic", "amb", "doom")}
    plan = [("amb", 0.0), ("epic", T(1, "Evet") - 0.3), ("a", TITLE1 - 0.5), ("b", T(6, "Saklanmayı") - 1.0),
            ("epic", T(7, "Arkanda") - 0.5), ("a", T(7, "Gerçek") - 0.8), ("b", CARDS[9][0] - 0.5),
            ("a", G[10] - 0.5), ("doom", T(10, "Ama", 1) - 0.5)]
    mus = np.zeros(n, np.float32)
    XF = int(1.5 * SR)

    def looped(src, Ln):
        out = src.copy()
        while len(out) < Ln:
            mixz = out[-XF:] * np.linspace(1, 0, XF) + src[:XF] * np.linspace(0, 1, XF)
            out = np.concatenate([out[:-XF], mixz, src[XF:]])
        return out[:Ln].copy()

    for j, (k, st) in enumerate(plan):
        en = plan[j + 1][1] + 1.5 if j + 1 < len(plan) else TOTAL
        a, b = int(st * SR), min(n, int(en * SR))
        seg = looped(trk[k], b - a)
        fi = XF if j > 0 else int(0.5 * SR)
        seg[:fi] *= np.linspace(0, 1, fi)
        if j + 1 < len(plan):
            seg[-XF:] *= np.linspace(1, 0, XF)
        else:
            seg[-int(4 * SR):] *= np.linspace(1, 0, int(4 * SR))
        seg /= (np.percentile(np.abs(seg), 99) + 1e-9)
        mus[a:b] += seg * 0.5
    mus = mus[:int(TOTAL * SR)]
    mus /= (np.max(np.abs(mus)) + 1e-9)
    at._write(str(WORK / "music.wav"), mus * 0.9)
    fx = sfx_track(int(TOTAL * SR))
    fx /= max(1.0, float(np.abs(fx).max()))
    at._write(str(WORK / "sfx.wav"), fx * 0.95)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(WORK / "voice_full.wav"), "-i", str(WORK / "music.wav"),
                    "-i", str(WORK / "sfx.wav"), "-filter_complex",
                    "[0:a]highpass=f=70,acompressor=threshold=-20dB:ratio=3:attack=5:release=150,volume=1.0,asplit=2[v][vs];"
                    "[1:a]volume=0.30[m];[m][vs]sidechaincompress=threshold=0.02:ratio=6:attack=40:release=500[md];"
                    "[2:a]volume=0.6[s];[v][md][s]amix=inputs=3:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11",
                    "-ar", "48000", "-c:a", "pcm_s16le", str(WORK / "mix.wav")], check=True)


if __name__ == "__main__":
    mode = sys.argv[2] if len(sys.argv) > 2 else "render"
    print("toplam", round(TOTAL, 1), "G", {k: round(v, 1) for k, v in G.items()}, flush=True)
    if mode == "frames":
        for tt in [float(x) for x in sys.argv[3].split(",")]:
            readers = {}
            base = TL.frame(tt, readers)
            im = Image.fromarray(base).convert("RGBA")
            im.alpha_composite(overlay(tt))
            Image.fromarray(finish(np.asarray(im.convert("RGB")), 0)).resize((1280, 720), Image.LANCZOS).save(
                WORK / f"fr_{tt:06.1f}.jpg", quality=88)
            for r in readers.values():
                r.close()
    elif mode == "ses":
        build_audio()
    else:
        build_audio()
        TL.render(WORK / "parts", str(WORK / "mix.wav"), str(WORK / "video.mp4"), workers=2, step=900,
                  keep=int(sys.argv[3]) if len(sys.argv) > 3 else 0)
        print("render bitti", TOTAL, flush=True)
