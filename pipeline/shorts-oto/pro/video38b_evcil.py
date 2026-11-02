"""38. video (uzun, 16:9 2K, ~6,7 dk): Evcil Dinozor Sahiplendirme Rehberi — komik + gerçek bilgi.
Kullanım: python3 video38_evcil.py <WORK> [frames t1,t2,..|render [keep]|ses]"""
import json, math, subprocess, sys
from functools import lru_cache
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from belgesel import *  # noqa

WORK = Path(sys.argv[1])
MED = WORK / "med2"
KEY = WORK / "key2"
ROZET = Path(__file__).resolve().parent.parent / "assets" / "abi_rozet.mp4"
SR = 44100
NSEG = 10
YEL = (255, 212, 0)


def norm(w):
    return w.lower().strip(".,;:!?'\"").replace("'", "")


DUR = {i: float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                 str(WORK / f"ses/v{i}.wav")], capture_output=True, text=True).stdout) for i in range(1, NSEG + 1)}
WORDS = {i: json.loads((WORK / f"ses/v{i}.json").read_text(encoding="utf-8")) for i in range(1, NSEG + 1)}
G = {1: 0.3}
TITLE0 = G[1] + DUR[1] + 0.3
TITLE1 = TITLE0 + 3.4
t_ = TITLE1 + 0.1
for k in range(2, NSEG + 1):
    G[k] = t_
    t_ = G[k] + DUR[k] + (0.9 if k in (2, 3, 4, 5, 6, 7) else 0.6)
END = G[NSEG] + DUR[NSEG]
OUT0 = END + 0.5
TOTAL = OUT0 + 7.0


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



MONT = ["k_compy", "raptor_4", "dino_orman_2", "k_brachio", "k_pachy", "k_spino"]
MOFF = {"k_compy": 1.0, "raptor_4": 7.0, "dino_orman_2": 4.0, "k_brachio": 1.0, "k_pachy": 1.0, "k_spino": 1.5}
_m0 = T(1, "7") - 0.1
_m1 = T(1, "Son") - 0.15
_md = (_m1 - _m0) / 7
C = [
    clip("salon_4", 0.0, T(1, "Köpek") - 0.1, off=6.0, z=(1.06, 1.12), xf=0.0),
    clip("mama_1", T(1, "Köpek") - 0.1, T(1, "Peki") - 0.1, off=2.0, z=(1.0, 1.06)),
    clip("sin_trex2_2", T(1, "Peki") - 0.1, T(1, "Bugün") - 0.1, off=0.0, z=(1.0, 1.1), xf=0.0),
    clip("trex_kukre_2", T(1, "Bugün") - 0.1, T(1, "Ama") - 0.1, off=0.0, z=(1.0, 1.08)),
    clip("pencere_3", T(1, "Ama") - 0.1, T(1, "2") - 0.1, off=6.0, z=(1.0, 1.08)),
    clip("hesap_1", T(1, "2") - 0.1, _m0, off=2.0, z=(1.0, 1.06)),
]
for i, n in enumerate(MONT):
    C.append(clip(n, _m0 + i * _md, _m0 + (i + 1) * _md, off=MOFF[n], z=(1.1, 1.0), xf=0.0, speed=1.0))
C += [
    dark(_m0 + 6 * _md, _m1, xf=0.0),
    clip("salon_4", _m1, TITLE0 + 0.1, off=14.0, z=(1.0, 1.12)),
    clip("sin_trex_6", TITLE0, TITLE1 + 0.2, off=2.0, z=(1.04, 1.1), xf=0.4),
    # 2 - compsognathus
    clip("k_compy", G[2] - 0.1, T(2, "Tavuk") - 0.1, off=0.0, z=(1.0, 1.06), speed=1.0, xf=0.0),
    clip("tavuk_1", T(2, "Tavuk") - 0.1, T(2, "Kucağa") - 0.1, off=0.5, z=(1.0, 1.08)),
    clip("salon_4", T(2, "Kucağa") - 0.1, T(2, "Peki") - 0.1, off=20.0, z=(1.06, 1.14)),
    freeze("k_compy", T(2, "Peki") - 0.1, T(2, "Bilim") - 0.1, off=4.0, z=(1.2, 1.32)),
    dark(T(2, "Bilim") - 0.1, T(2, "Yani") - 0.1),
    clip("ev_kedi_1", T(2, "Yani") - 0.1, G[3] - 0.1, off=2.0, z=(1.0, 1.08)),
    # 3 - veloziraptor
    clip("raptor_4", G[3] - 0.1, T(3, "Filmlerden") - 0.1, off=6.0, z=(1.0, 1.08), xf=0.0, speed=0.85),
    clip("raptor_3", T(3, "Filmlerden") - 0.1, T(3, "Boyu") - 0.1, off=0.0, z=(1.0, 1.06)),
    clip("k_raptor", T(3, "Boyu") - 0.1, T(3, "köpek") - 0.2, off=0.0, z=(1.0, 1.06), speed=0.8),
    clip("mama_1", T(3, "köpek") - 0.2, T(3, "Fark") - 0.1, off=6.0, z=(1.0, 1.06)),
    clip("k_raptor", T(3, "Fark") - 0.1, T(3, "Kanepene") - 0.1, off=2.0, z=(1.6, 1.8), dy=(0.14, 0.15), speed=0.6),
    clip("ev_kanepe_1", T(3, "Kanepene") - 0.1, T(3, "Tüylüydü") - 0.1, off=0.0, z=(1.0, 1.06), speed=0.6),
    clip("ev_tuy_1", T(3, "Tüylüydü") - 0.1, T(3, "Ve", exact=True) - 0.1, off=1.0, z=(1.0, 1.06)),
    clip("raptor_2", T(3, "Ve", exact=True) - 0.1, T(3, "Kapı") - 0.1, off=1.0, z=(1.08, 1.18)),
    clip("pencere_2", T(3, "Kapı") - 0.1, G[4] - 0.1, off=1.0, z=(1.0, 1.1)),
    # 4 - triceratops
    clip("k_trike2", G[4] - 0.1, T(4, "Ağırlığı") - 0.1, off=0.0, z=(1.0, 1.06), xf=0.0, speed=1.0),
    clip("fil_2", T(4, "Ağırlığı") - 0.1, T(4, "İyi") - 0.1, off=1.0, z=(1.0, 1.08)),
    clip("dino_orman_2", T(4, "İyi") - 0.1, T(4, "Çim") - 0.1, off=3.0, z=(1.0, 1.08)),
    clip("cim_1", T(4, "Çim") - 0.1, T(4, "Çötü") - 0.1, off=3.0, z=(1.0, 1.06)),
    clip("k_trike2", T(4, "Çötü") - 0.1, T(4, "Su") - 0.1, off=4.0, z=(1.06, 1.12), speed=1.0),
    clip("havuz_3", T(4, "Su") - 0.1, T(4, "Havuzunu") - 0.1, off=1.0, z=(1.0, 1.06)),
    clip("hesap_2", T(4, "Havuzunu") - 0.1, G[5] - 0.1, off=1.0, z=(1.0, 1.06)),
    # 5 - brachiosaurus
    clip("k_brachio", G[5] - 0.1, T(5, "Ağırlığı") - 0.1, off=0.0, z=(1.0, 1.05), xf=0.0),
    clip("dino_orman_2", T(5, "Ağırlığı") - 0.1, T(5, "Senin") - 0.1, off=0.0, z=(1.0, 1.08)),
    clip("agac_1", T(5, "Senin") - 0.1, T(5, "Boynunu") - 0.1, off=3.0, z=(1.0, 1.06)),
    clip("k_brachio", T(5, "Boynunu") - 0.1, T(5, "saksılara") - 0.2, off=3.0, z=(1.5, 1.6), dx=(0.12, 0.14), dy=(-0.2, -0.2)),
    clip("balkon_3", T(5, "saksılara") - 0.2, T(5, "apartman") - 0.1, off=1.0, z=(1.04, 1.12)),
    clip("hesap_1", T(5, "apartman") - 0.1, G[6] - 0.1, off=8.0, z=(1.0, 1.06)),
    # 6 - pachycephalosaurus
    clip("k_pachy", G[6] - 0.1, T(6, "kafasının") - 0.1, off=0.2, z=(1.0, 1.04), xf=0.0, speed=1.0),
    clip("k_pachy", T(6, "kafasının") - 0.1, T(6, "Yani") - 0.1, off=2.0, z=(1.2, 1.3), dx=(0.1, 0.1), dy=(-0.06, -0.06),
         speed=0.5),
    clip("kapi_2", T(6, "Yani") - 0.1, T(6, "Kapıyı") - 0.1, off=1.0, z=(1.0, 1.06)),
    clip("ev_kapi_3", T(6, "Kapıyı") - 0.1, T(6, "Sigorta") - 0.1, off=1.0, z=(1.0, 1.1), shake=12),
    clip("hesap_2", T(6, "Sigorta") - 0.1, G[7] - 0.1, off=4.0, z=(1.0, 1.06)),
    # 7 - spinosaurus
    clip("k_spino", G[7] - 0.1, T(7, "2020") - 0.1, off=0.0, z=(1.0, 1.06), xf=0.0),
    clip("timsah_4", T(7, "2020") - 0.1, T(7, "Ana") - 0.1, off=1.0, z=(1.0, 1.08)),
    clip("havuz_1", T(7, "Ana") - 0.1, T(7, "Peki") - 0.1, off=1.0, z=(1.0, 1.08)),
    clip("havuz_4", T(7, "Peki") - 0.1, G[8] - 0.1, off=1.0, z=(1.0, 1.3)),
    # 8 - T. rex
    clip("sin_trex_6", G[8] - 0.1, T(8, "Önce") - 0.1, off=0.0, z=(1.0, 1.06), xf=0.0),
    clip("k_troar", T(8, "Önce") - 0.1, T(8, "Ergenlik") - 0.1, off=0.0, z=(1.0, 1.08), speed=1.0),
    clip("k_tw", T(8, "Ergenlik") - 0.1, T(8, "Şimdi") - 0.1, off=0.0, z=(1.0, 1.06)),
    clip("kasap_4", T(8, "Şimdi") - 0.1, T(8, "Kıymanın") - 0.1, off=3.0, z=(1.0, 1.08)),
    dark(T(8, "Kıymanın") - 0.1, T(8, "Üstelik") - 0.1),
    clip("kasap_1", T(8, "Üstelik") - 0.1, T(8, "Biz") - 0.1, off=4.0, z=(1.0, 1.08)),
    clip("hesap_1", T(8, "Biz") - 0.1, T(8, "Peki") - 0.1, off=12.0, z=(1.06, 1.12)),
    clip("ev_bos_2", T(8, "Peki") - 0.1, T(8, "Hatırla") - 0.1, off=2.0, z=(1.0, 1.08)),
    clip("k_sniff", T(8, "Hatırla") - 0.1, T(8, "sensin") - 0.4, off=0.0, z=(1.0, 1.08), speed=0.7),
    clip("sin_trex2_2", T(8, "sensin") - 0.4, G[9] - 0.1, off=2.0, z=(1.15, 1.3)),
    # 9 - yürüyüş
    clip("tasma_1", G[9] - 0.1, T(9, "Tasmayı") - 0.1, off=2.0, z=(1.0, 1.06), xf=0.0),
    clip("k_trex", T(9, "Tasmayı") - 0.1, T(9, "Komşular") - 0.1, off=0.5, z=(1.0, 1.06)),
    clip("pencere_1", T(9, "Komşular") - 0.1, T(9, "sokaktaki") - 0.1, off=0.5, z=(1.0, 1.06)),
    clip("ev_kedi_1", T(9, "sokaktaki") - 0.1, T(9, "belediye") - 0.1, off=6.0, z=(1.0, 1.08)),
    clip("tasma_3", T(9, "belediye") - 0.1, T(9, "Bu", exact=True) - 0.1, off=3.0, z=(1.0, 1.06)),
    clip("k_trex", T(9, "Bu", exact=True) - 0.1, T(9, "Kısacası") - 0.1, off=2.5, z=(1.3, 1.45), dy=(0.0, 0.02)),
    clip("sin_trex_6", T(9, "Kısacası") - 0.1, G[10] - 0.1, off=5.0, z=(1.0, 1.1)),
    # 10 - kuşlar
    clip("hindi_1", G[10] - 0.1, T(10, "Kuşlar") - 0.1, off=3.0, z=(1.0, 1.08), xf=0.0),
    clip("tavuk_1", T(10, "Kuşlar") - 0.1, T(10, "Yani") - 0.1, off=0.0, z=(1.0, 1.06)),
    clip("hindi_3", T(10, "Yani") - 0.1, T(10, "Mama") - 0.1, off=2.0, z=(1.0, 1.06)),
    clip("tavuk_1", T(10, "Mama") - 0.1, T(10, "Sen") - 0.1, off=3.0, z=(1.08, 1.14)),
    clip("mutfak_4", T(10, "Sen") - 0.1, T(10, "Daha") - 0.1, off=20.0, z=(1.0, 1.06)),
    dark(T(10, "Daha") - 0.1, TOTAL, xf=0.6),
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


# ---------------- v38 özel grafikler ----------------
def stamp(L, t, s, e, txt, x=W * 0.5, y=H * 0.42, col=(214, 40, 40), size=150, rot=-8):
    a = window(t, s, e, 0.05, 0.35)
    if a <= 0:
        return
    lt = t - s
    sc = 1.0 + 1.2 * max(0.0, 1 - lt / 0.18) ** 2
    f = ImageFont.truetype(INTER.format("Black"), size)
    bb = f.getbbox(txt)
    w, h = bb[2] - bb[0] + 120, bb[3] - bb[1] + 90
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([8, 8, w - 8, h - 8], radius=28, outline=col + (255,), width=14)
    d.text((60 - bb[0], 45 - bb[1]), txt, font=f, fill=col + (255,))
    im = im.rotate(rot, resample=Image.BICUBIC, expand=True)
    put(L, im, x, y, "mm", a * min(1.0, lt / 0.12 + 0.2), scale=sc)


def profile(L, t, s, e, name, rows, stars, x=1700, y=250):
    a = window(t, s, e, 0.4, 0.4)
    if a <= 0:
        return
    q = eo(ph(t, s, 0.5))
    pw = 720
    ph_ = 200 + 86 * len(rows) + 90
    x = x + (1 - q) * 120
    card = Image.new("RGBA", (pw, ph_), (246, 242, 232, int(238 * a)))
    d = ImageDraw.Draw(card)
    d.rectangle([0, 0, pw, 70], fill=(214, 40, 40, int(255 * a)))
    put(L, card, x, y, "lt", 1.0)
    text(L, x + 30, y + 36, "SAHİPLENDİRME KARTI", "sans", "Black", 32, (255, 255, 255), a, track=0.12, anchor="lm", shadow=0)
    text(L, x + 30, y + 130, name, "serif", "Regular", 64, (30, 28, 26), a, anchor="lm", italic=True, shadow=0)
    for i, (k, v) in enumerate(rows):
        qq = eo(ph(t, s + 0.25 + i * 0.18, 0.4))
        yy = y + 220 + i * 86
        text(L, x + 30, yy, k, "sans", "Medium", 34, (110, 104, 96), a * qq, anchor="lm", shadow=0)
        text(L, x + pw - 30, yy, v, "sans", "Bold", 38, (30, 28, 26), a * qq, anchor="rm", shadow=0)
        ImageDraw.Draw(L).line([(x + 30, yy + 40), (x + pw - 30, yy + 40)], fill=(200, 194, 184, int(255 * a * qq)), width=2)
    yy = y + ph_ - 55
    text(L, x + 30, yy, "EVCİLLİK", "sans", "Black", 32, (214, 40, 40), a, anchor="lm", track=0.12, shadow=0)
    qs = ph(t, s + 0.4 + len(rows) * 0.18, 0.6)
    for k in range(5):
        on = k < stars and qs * 5 > k
        text(L, x + 300 + k * 72, yy, "★", "sans", "Black", 54, (240, 170, 20) if on else (200, 194, 184), a, anchor="mm",
             shadow=0)


def hint(L, t, s, e, txt):
    a = window(t, s, e, 0.4, 0.4)
    if a > 0:
        text(L, W - 150, 1370, txt, "sans", "Italic", 30, WARM, a * 0.85, anchor="rm", shadow=0.9)


_fr = np.random.default_rng(8)
FEATHERS = [(_fr.uniform(0, W), _fr.uniform(-H, 0), _fr.uniform(30, 70), _fr.uniform(0, 6.28), _fr.uniform(60, 140))
            for _ in range(34)]


@lru_cache(None)
def feather_img(sz):
    im, d = aa(sz, sz // 3)
    k = 2
    d.ellipse([0, 0, sz * k, sz * k // 3], fill=(240, 236, 226, 230))
    d.line([(4, sz * k // 6), (sz * k - 4, sz * k // 6)], fill=(170, 160, 150, 255), width=3)
    return im.resize((sz, sz // 3), Image.LANCZOS)


def g_feathers(L, t, s, e):
    a = window(t, s, e, 0.4, 0.6)
    if a <= 0:
        return
    lt = t - s
    for x, y0, sz, p0, sp in FEATHERS:
        y = y0 + lt * sp * 3
        if y < -60 or y > H + 60:
            continue
        xx = x + 60 * math.sin(lt * 1.6 + p0)
        im = feather_img(int(sz)).rotate(25 * math.sin(lt * 2 + p0), resample=Image.BICUBIC, expand=True)
        put(L, im, xx, y, "mm", a)


def g_ruler(L, t, s, e, x, y, hpx, txt):
    a = window(t, s, e, 0.3, 0.3)
    if a <= 0:
        return
    q = eo(ph(t, s, 0.6))
    d = ImageDraw.Draw(L)
    c = YEL + (int(255 * a),)
    hh = hpx * q
    d.line([(x, y), (x, y - hh)], fill=c, width=8)
    for k in range(11):
        yy = y - hh * k / 10
        d.line([(x - (30 if k % 5 == 0 else 16), yy), (x, yy)], fill=c, width=5)
    meme(L, t, s + 0.5, e, txt, x=x - 210, y=y - hpx / 2, size=90, col=YEL)


def g_calc(L, t, s, times):
    e = times[-1] + 3.0
    a = window(t, s, e, 0.4, 0.4)
    if a <= 0:
        return
    rows = [("5 kg", "× 700 TL", ""), ("", "= 3.500 TL", " / GÜN"), ("× 30", "= 105.000 TL", " / AY")]
    text(L, W / 2, 300, "Sadece büyüdüğü kısmın kıyma hesabı", "serif", "Regular", 70, WARM, a, italic=True)
    for i, ((l, m, r), tt) in enumerate(zip(rows, times)):
        q = eo(ph(t, tt, 0.4))
        if q <= 0.01:
            continue
        y = 560 + i * 200
        col = (255, 90, 80) if i == 2 else WARM
        text(L, 760, y, l, "sans", "Bold", 110, GOLD, a * q, anchor="rm")
        text(L, 820, y, m + r, "sans", "Black", 110 if i else 110, col, a * q, anchor="lm", rise=(1 - q) * 20)
    text(L, W / 2, 1180, "Kıyma: marketlerde kilosu 700 TL'nin üzerinde (Eylül 2026)", "sans", "Medium", 34, GREY,
         a * eo(ph(t, times[0] + 0.5, 0.5)))


def g_water(L, t, s, e, t_fil, t_tri):
    a = window(t, s, e, 0.4, 0.4)
    if a <= 0:
        return
    shade(L, t, s, e, 0.55)
    text(L, 200, 300, "Günlük su (litre)", "serif", "Regular", 84, WARM, a, anchor="lm")
    rows = [("FİL", 70, 200, t_fil, CYAN, "70–200"), ("TRICERATOPS", 200, 500, t_tri, GOLD, "birkaç yüz (kaba tahmin)")]
    x0, x1 = 760, 2300
    for i, (nm, lo, hi, tt, col, lab) in enumerate(rows):
        q = eo(ph(t, tt, 1.0))
        if q <= 0.01:
            continue
        y = 620 + i * 260
        text(L, 200, y, nm, "sans", "Bold", 60, WARM, a * clamp(q * 3), anchor="lm")
        w = (x1 - x0) * hi / 550 * q
        d = ImageDraw.Draw(L)
        d.rounded_rectangle([x0, y - 50, x0 + max(20, w), y + 50], radius=24, fill=col + (int(220 * a),))
        if i == 1:
            for k in range(0, int(w), 40):
                d.line([(x0 + k, y + 50), (x0 + k + 24, y - 50)], fill=(255, 255, 255, int(90 * a)), width=8)
        text(L, x0 + 30, y + 100, lab, "sans", "SemiBold", 44, col, a * q, anchor="lm")


def g_bill(L, t, s, e):
    a = window(t, s, e, 0.3, 0.4)
    if a <= 0:
        return
    q = eo(ph(t, s, 0.5))
    pw, ph_ = 700, 860
    im = Image.new("RGBA", (pw, ph_), (250, 248, 242, 255))
    d = ImageDraw.Draw(im)
    f1 = ImageFont.truetype(INTER.format("Black"), 64)
    f2 = ImageFont.truetype(INTER.format("Medium"), 36)
    d.rectangle([0, 0, pw, 120], fill=(40, 110, 200, 255))
    d.text((pw / 2, 60), "SU FATURASI", font=f1, fill=(255, 255, 255, 255), anchor="mm")
    for i, (k, v) in enumerate([("Abone", "Triceratops"), ("Tüketim", "çok"), ("Havuz", "yarım"), ("Komşu", "şikayetçi")]):
        d.text((50, 190 + i * 90), k, font=f2, fill=(110, 104, 96, 255), anchor="lm")
        d.text((pw - 50, 190 + i * 90), v, font=f2, fill=(30, 28, 26, 255), anchor="rm")
    d.line([(50, 540), (pw - 50, 540)], fill=(30, 28, 26, 255), width=4)
    d.text((50, 600), "TOPLAM", font=f2, fill=(30, 28, 26, 255), anchor="lm")
    n = int(clamp((t - s - 0.6) / 1.6) ** 2 * 999999)
    d.text((pw - 50, 720), f"{n:,}".replace(",", ".") + " TL", font=ImageFont.truetype(INTER.format("Black"), 84),
           fill=(214, 40, 40, 255), anchor="rm")
    im = im.rotate(3, resample=Image.BICUBIC, expand=True)
    put(L, im, W * 0.7, H * 0.5 + (1 - q) * 300, "mm", a)


_cr = np.random.default_rng(3)
CONF = [(_cr.uniform(0, W), _cr.uniform(-H * 0.6, 0), _cr.uniform(14, 28), _cr.uniform(0, 6.28), _cr.uniform(300, 600),
         [(214, 40, 40), YEL, GREEN, CYAN, (240, 140, 220)][int(_cr.integers(0, 5))]) for _ in range(140)]


def g_confetti(L, t, s, e):
    a = window(t, s, e, 0.1, 0.6)
    if a <= 0:
        return
    lt = t - s
    d = ImageDraw.Draw(L)
    for x, y0, sz, p0, sp, col in CONF:
        y = y0 + lt * sp
        if y > H + 30:
            continue
        xx = x + 40 * math.sin(lt * 3 + p0)
        w = sz * abs(math.cos(lt * 6 + p0))
        d.rectangle([xx - w / 2, y - sz / 3, xx + w / 2, y + sz / 3], fill=col + (int(255 * a),))


def info_card(L, t, s, e, title, lines, y=640):
    a = window(t, s, e, 0.4, 0.4)
    if a <= 0:
        return
    shade(L, t, s, e, 0.45)
    q = eo(ph(t, s, 0.6))
    text(L, W / 2, y - 160, title, "sans", "Black", 64, GOLD, a * q, track=0.12)
    for i, (txt, kind, sz) in enumerate(lines):
        qq = eo(ph(t, s + 0.4 + i * 0.5, 0.6))
        kd = ("serif", "Regular") if kind == "serif" else ("sans", "SemiBold")
        text(L, W / 2, y + i * 150, txt, kd[0], kd[1], sz, WARM if i == 0 else GREY, a * qq, italic=(kind == "serif"),
             rise=(1 - qq) * 16)


def g_montage_nums(L, t):
    for i in range(7):
        s = _m0 + i * _md
        if s <= t < s + _md:
            txt = str(i + 1) if i < 6 else "?"
            stamp(L, t, s, s + _md, txt, x=W * 0.5, y=H * 0.45, col=YEL if i < 6 else (214, 40, 40), size=300, rot=0)


def g_hud(L, t):
    spans = [(G[2], G[3] - 0.2, "ADAY 1/7"), (G[3], G[4] - 0.2, "ADAY 2/7"), (G[4], G[5] - 0.2, "ADAY 3/7"),
             (G[5], G[6] - 0.2, "ADAY 4/7"), (G[6], G[7] - 0.2, "ADAY 5/7"), (G[7], G[8] - 0.2, "ADAY 6/7"),
             (G[8], G[10] - 0.2, "ÖZEL ADAY"), (G[10], T(10, "Sen") - 0.2, "ADAY 7/7")]
    for s, e, txt in spans:
        a = window(t, s + 0.4, e, 0.4, 0.3)
        if a <= 0:
            continue
        L.alpha_composite(set_alpha(TOP, a))
        col = RED if txt == "ÖZEL ADAY" else GOLD
        ImageDraw.Draw(L).rectangle([150, 92, 156, 148], fill=col + (int(235 * a),))
        text(L, 176, 120, txt, "sans", "Bold", 44, col, a, track=0.14, anchor="lm")


def g_chips7(L, t, s, e):
    a = window(t, s, e, 0.4, 0.4)
    if a <= 0:
        return
    shade(L, t, s, e, 0.6)
    text(L, W / 2, 330, "Sen hangisini sahiplenirdin?", "serif", "Regular", 100, WARM, a, italic=True)
    items = ["COMPSOGNATHUS", "VELOZİRAPTOR", "TRICERATOPS", "BRACHIOSAURUS", "PACHYCEPHALOSAURUS", "SPINOSAURUS",
             "T. REX", "TAVUK"]
    for i, it in enumerate(items):
        q = eo(ph(t, s + 0.2 + i * 0.12, 0.4))
        if q <= 0.01:
            continue
        r, c = divmod(i, 4)
        cx = W / 2 + (c - 1.5) * 560
        cy = 620 + r * 210 + (1 - q) * 30
        cw, chh = 520, 140
        im, d = aa(cw, chh)
        d.rounded_rectangle([3, 3, cw * 2 - 3, chh * 2 - 3], radius=chh - 3, fill=(12, 14, 20, 215), outline=GOLD + (255,),
                            width=6)
        put(L, im.resize((cw, chh), Image.LANCZOS), cx, cy, "mm", a * q)
        text(L, cx, cy, it, "sans", "Bold", 38 if len(it) < 14 else 30, WARM, a * q, track=0.06)
    label(L, W / 2, 1100, "YORUMLARA YAZ", a * eo(ph(t, s + 1.2, 0.5)), 44, GOLD, w="Bold", track=0.3)


def title_card(L, t):
    a = window(t, TITLE0 + 0.1, TITLE1, 0.5, 0.5)
    if a <= 0:
        return
    shade(L, t, TITLE0, TITLE1 + 0.3, 0.5)
    label(L, W / 2, 470, "PRATİK ABİ", a * 0.9, 30, GOLD, track=0.6)
    q1 = eo(ph(t, TITLE0 + 0.2, 0.9))
    text(L, W / 2, 640, "Evcil Dinozor", "serif", "Regular", 150, WARM, a * q1, shadow=0.85, rise=(1 - q1) * 20)
    q2 = eo(ph(t, TITLE0 + 0.45, 0.9))
    text(L, W / 2, 810, "Sahiplendirme Rehberi", "serif", "Regular", 130, GOLD, a * q2, italic=True, shadow=0.85,
         rise=(1 - q2) * 20)
    meme(L, t, TITLE0 + 1.2, TITLE1, "(sorumluluk kabul edilmez)", y=980, size=60, col=WARM, rot=3, stroke=6)


CARD = {
    2: ("Compsognathus", [("Boy", "~70 cm (kuyrukla)"), ("Ağırlık", "~3 kg"), ("Mama", "kertenkele"), ("Yaşadığı yer", "Avrupa")], 4),
    3: ("Veloziraptor", [("Boy", "1,5–2 m"), ("Ağırlık", "~15 kg"), ("Pençe", "6,5+ cm"), ("Kanepe ömrü", "1 gün")], 2),
    4: ("Triceratops", [("Ağırlık", "6–12 ton"), ("Beslenme", "otçul"), ("Su", "yüzlerce L/gün"), ("Bahçe", "biter")], 2),
    5: ("Brachiosaurus", [("Ağırlık", "30+ ton"), ("Bitki", "200+ kg/gün (tahmin)"), ("Ulaşır", "üst kat balkonlar")], 1),
    6: ("Pachycephalosaurus", [("Kafa kubbesi", "25 cm'ye kadar"), ("Anahtar", "gereksiz"), ("Sigorta", "red")], 2),
    7: ("Spinosaurus", [("Boy", "~15 m"), ("Yüzme", "var"), ("Menü", "balık (ve sen)")], 1),
    8: ("Tyrannosaurus rex", [("Ağırlık", "9+ ton (Sue)"), ("Büyüme", "~5 kg/gün (ergen)"), ("Mama", "3.500+ TL/gün")], 0),
}


def overlay(t):
    L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    # 1 - giriş
    meme(L, t, T(1, "sıkıcı") - 0.2, T(1, "Köpek") - 0.15, "SIKICI", y=1150, size=130)
    meme(L, t, T(1, "sıradan") - 0.2, T(1, "Peki") - 0.15, "SIRADAN", y=1150, size=130)
    meme(L, t, T(1, "dinozor") - 0.1, T(1, "Bugün") - 0.15, "EVCİL DİNOZOR?", y=1150, size=140, col=YEL)
    stamp(L, t, T(1, "sahiplendiriyoruz") - 0.1, T(1, "Ama") - 0.15, "SAHİPLENDİRME GÜNÜ", y=H * 0.3, size=110)
    meme(L, t, T(1, "1") - 0.05, T(1, "2") - 0.15, "KURAL 1: BÜYÜK BAHÇE", y=1150, size=120, col=YEL)
    meme(L, t, T(1, "2") - 0.05, _m0 - 0.1, "KURAL 2: DAHA BÜYÜK CÜZDAN", y=1150, size=120, col=YEL)
    g_montage_nums(L, t)
    meme(L, t, _m1, TITLE0, "SON ADAY: EVİNDE OLABİLİR", y=1150, size=110, col=YEL)
    title_card(L, t)
    g_hud(L, t)
    # 2 - compy
    stamp(L, t, G[2] + 0.1, G[2] + 2.6, "ADAY 1")
    profile(L, t, T(2, "Kompsognatus") - 0.1, T(2, "Peki") - 0.2, *CARD[2])
    meme(L, t, T(2, "Tavuk") - 0.05, T(2, "Kucağa") - 0.15, "≈ BU BOYDA", y=1150, size=120, col=YEL)
    meme(L, t, T(2, "Kucağa") - 0.05, T(2, "Peki") - 0.15, "KOLTUĞA SIĞAR", y=1150, size=120)
    info_card(L, t, T(2, "Peki") - 0.05, T(2, "Bilim") - 0.15, "BİR FOSİLİN MİDESİNDE",
              [("bütün olarak yutulmuş bir kertenkele", "sans", 72), ("Almanya · yaklaşık 150 milyon yıl önce", "sans", 46)])
    info_card(L, t, T(2, "Bilim") - 0.05, T(2, "Yani") - 0.15, "KERTENKELENİN ADI",
              [("Schoenesmahl dyspepsia", "serif", 120), ("≈ “güzel yemek, hazımsızlık”", "sans", 60)])
    meme(L, t, T(2, "gekon") - 0.2, G[3] - 0.1, "ELVEDA GEKON", y=1150, size=140, col=RED)
    # 3 - raptor
    stamp(L, t, G[3] + 0.1, G[3] + 2.6, "ADAY 2")
    hint(L, t, G[3] + 0.3, G[4] - 0.2, "Not: Gerçek veloziraptor tüylüydü. Bütçemiz tüylüsüne yetmedi.")
    meme(L, t, T(3, "Filmlerden") - 0.05, T(3, "Boyu") - 0.15, "FİLMDEKİ HALİ", y=260, size=110)
    profile(L, t, T(3, "Boyu") - 0.1, T(3, "köpek") - 0.25, *CARD[3])
    meme(L, t, T(3, "köpek") - 0.15, T(3, "Fark") - 0.15, "= ORTA BOY KÖPEK", y=1150, size=120, col=YEL)
    g_circle(L, t, T(3, "orak") - 0.3, T(3, "Kanepene") - 0.2, W * 0.5, H * 0.62, 190, "6,5+ CM")
    meme(L, t, T(3, "Kanepene") - 0.05, T(3, "Tüylüydü") - 0.15, "KANEPE: 1 GÜN", y=1150, size=140, col=RED, rot=-3)
    g_feathers(L, t, T(3, "Tüylüydü") + 0.3, T(3, "Ve", exact=True))
    meme(L, t, T(3, "tüy", exact=True) - 0.1, T(3, "Ve", exact=True) - 0.1, "HER YER TÜY", y=1150, size=140, col=YEL)
    info_card(L, t, T(3, "Bir") + 0.0, T(3, "Kapı") - 0.15, "“DÖVÜŞEN DİNOZORLAR” FOSİLİ",
              [("Veloziraptor ve Protoceratops, kavga ederken gömülmüş", "sans", 60), ("Gobi Çölü, Moğolistan", "sans", 46)])
    meme(L, t, T(3, "Kapı") - 0.05, G[4] - 0.1, "KOMŞUNUN KEDİSİ: TEHLİKEDE", y=1150, size=110, col=RED)
    # 4 - triceratops
    stamp(L, t, G[4] + 0.1, G[4] + 2.6, "ADAY 3")
    profile(L, t, T(4, "Ağırlığı") - 0.1, T(4, "İyi") - 0.2, *CARD[4])
    meme(L, t, T(4, "Yani") - 0.05, T(4, "İyi") - 0.15, "= 2–3 FİL", y=1150, size=150, col=YEL)
    meme(L, t, T(4, "Çim") - 0.1, T(4, "Çötü") - 0.15, "ÇİM BİÇME MAKİNESİ: EMEKLİ", y=1150, size=110, col=GREEN)
    g_needs(L, t, T(4, "Çötü") - 0.05, T(4, "Su") - 0.15,
            [("Çim", T(4, "çim", 1), "no"), ("Çit", T(4, "çit"), "no"), ("Komşunun gülleri", T(4, "gülleri"), "no")],
            "KÖTÜ HABER", x=1850, y=330)
    g_water(L, t, T(4, "Su") - 0.05, T(4, "Havuzunu") - 0.15, T(4, "fil", 1) - 0.2, T(4, "Kabaca") - 0.2)
    cite(L, t, T(4, "fil", 1) - 0.2, T(4, "Havuzunu") - 0.2, "Fil su tüketimi: elephant.se · Triceratops: kaba karşılaştırma")
    g_bill(L, t, T(4, "Havuzunu") - 0.05, G[5] - 0.1)
    # 5 - brachio
    stamp(L, t, G[5] + 0.1, G[5] + 2.6, "ADAY 4")
    profile(L, t, T(5, "Ağırlığı") - 0.1, T(5, "Senin") - 0.2, *CARD[5])
    meme(L, t, T(5, "Senin") - 0.05, T(5, "Boynunu") - 0.15, "BAHÇEN = 1 ÖĞÜN BİLE DEĞİL", y=1150, size=110, col=YEL)
    meme(L, t, T(5, "saksılara") - 0.2, T(5, "çamaşırlara") - 0.2, "SAKSILAR: GİTTİ", y=1150, size=120, col=RED)
    meme(L, t, T(5, "çamaşırlara") - 0.2, T(5, "apartman") - 0.15, "ÇAMAŞIRLAR: GİTTİ", y=1150, size=120, col=RED)
    meme(L, t, T(5, "aidat") - 0.1, G[6] - 0.1, "AİDAT ↑↑↑", y=H / 2, size=200, col=RED, rot=-4)
    # 6 - pachy
    stamp(L, t, G[6] + 0.6, G[6] + 3.0, "ADAY 5")
    profile(L, t, T(6, "kafasının") - 0.1, T(6, "Yani") - 0.2, *CARD[6])
    g_ruler(L, t, T(6, "25") - 0.3, T(6, "Yani") - 0.2, W * 0.40, H * 0.70, 420, "25 CM")
    meme(L, t, T(6, "anahtara") - 0.1, T(6, "Kapıyı") - 0.15, "ANAHTAR: GEREKSİZ", y=1150, size=120, col=YEL)
    for k, w_ in (("Kapıyı", "KAPI"), ("duvarı", "DUVAR"), ("arabanın", "ARABA")):
        meme(L, t, T(6, k) - 0.05, T(6, k) + 0.9, w_ + "!", y=H * 0.45, size=200, col=RED,
             rot=-6)
    stamp(L, t, T(6, "Sigorta") - 0.05, G[7] - 0.1, "SİGORTA: RED", y=H * 0.45, size=130)
    # 7 - spino
    stamp(L, t, G[7] + 0.1, G[7] + 2.6, "ADAY 6")
    profile(L, t, T(7, "Spinosaurus") - 0.1, T(7, "2020") - 0.2, *CARD[7])
    cite(L, t, T(7, "2020") - 0.05, T(7, "Ana") - 0.2, "Ibrahim ve ark., Nature, 2020")
    quote(L, t, T(7, "2020") - 0.05, T(7, "Ana") - 0.2, "Kuyruğu kürek gibi çalışıyordu", size=88)
    meme(L, t, T(7, "Havuzuna") - 0.1, T(7, "Peki") - 0.15, "HAVUZ ARTIK ONUN", y=1150, size=130, col=YEL)
    meme(L, t, T(7, "sen") - 0.05, G[8] - 0.1, "SEN = BALIK", y=1150, size=170, col=YEL, rot=-3)
    # 8 - T. rex
    stamp(L, t, G[8] + 0.1, G[8] + 3.0, "ÖZEL ADAY", size=130)
    profile(L, t, T(8, "Önce") - 0.1, T(8, "Şimdi") - 0.2, *CARD[8])
    big(L, t, T(8, "9") - 0.2, T(8, "Ergenlik") - 0.2, "9+ ton", "Sue'nun tahmini ağırlığı", x=W * 0.33, y=640, size=200)
    cite(L, t, T(8, "9") - 0.2, T(8, "Şimdi") - 0.2, "Hutchinson ve ark., PLoS ONE, 2011")
    big(L, t, T(8, "5") - 0.2, T(8, "Şimdi") - 0.2, "+5 kg / gün", "ergen T. rex'in büyüme hızı", y=1050, size=170)
    g_calc(L, t, T(8, "Kıymanın") - 0.1, [T(8, "700") - 0.3, T(8, "3500") - 0.3, T(8, "Ayda") - 0.2])
    meme(L, t, T(8, "kat") - 0.2, T(8, "Biz") - 0.15, "GERÇEK İŞTAH: KAT KAT FAZLASI", y=1150, size=100, col=RED)
    meme(L, t, T(8, "Biz") - 0.05, T(8, "Peki") - 0.15, "BÜTÇE: ALARM", y=H / 2, size=200, col=RED, rot=-4)
    meme(L, t, T(8, "unutursan") - 0.2, T(8, "Hatırla") - 0.15, "MAMA: UNUTULDU", y=1150, size=130, col=RED)
    meme(L, t, T(8, "sensin") - 0.3, G[9] - 0.1, "MENÜ: SEN", y=1150, size=180, col=RED, rot=-4)
    # 9 - yürüyüş
    meme(L, t, T(9, "Tasmayı") - 0.05, T(9, "Kolları") - 0.15, "TASMAYI KİM TAKACAK?", y=1150, size=120, col=YEL)
    g_circle(L, t, T(9, "Kolları") - 0.1, T(9, "Komşular") - 0.2, W * 0.36, H * 0.5, 150, "KISA")
    meme(L, t, T(9, "Komşular") - 0.05, T(9, "sokaktaki") - 0.15, "KOMŞULAR İZLİYOR", y=1150, size=120)
    meme(L, t, T(9, "sokaktaki") - 0.05, T(9, "belediye") - 0.15, "KEDİLER TAŞINIYOR", y=1150, size=120)
    g_phone(L, t, T(9, "belediye") - 0.1, T(9, "Bu") - 0.2, msg="BELEDİYE", sub="arıyor...")
    big(L, t, T(9, "200") - 0.3, T(9, "Kısacası") - 0.2, "≈ 200 kg", "tek kolun kaldırabildiği (tahmini)", y=1040, size=170)
    cite(L, t, T(9, "200") - 0.3, T(9, "Kısacası") - 0.2, "Carpenter & Smith, 2001")
    meme(L, t, T(9, "Sen", 1) - 0.05, G[10] - 0.1, "EVCİL HAYVAN: SEN", y=1150, size=150, col=RED, rot=-3)
    # 10 - kuşlar
    meme(L, t, T(10, "ötüyor") - 0.4, T(10, "Kuşlar") - 0.15, "?", y=H * 0.4, size=260, col=YEL)
    stamp(L, t, T(10, "Kuşlar") - 0.05, T(10, "Yani") - 0.15, "KUŞ = DİNOZOR", size=130)
    stamp(L, t, T(10, "tavuğun") - 0.1, T(10, "Mama") - 0.15, "ADAY 7", size=150)
    g_needs(L, t, T(10, "Mama") - 0.1, T(10, "Sen") - 0.2,
            [("Mama masrafı az", T(10, "Mama"), "ok"), ("Kapıyı kırmıyor", T(10, "kapıyı"), "ok"),
             ("Seni yemiyor", T(10, "seni"), "ok")], "TAVUK", x=1850, y=330)
    g_confetti(L, t, T(10, "Tebrikler") - 0.1, T(10, "Sen") - 0.1)
    meme(L, t, T(10, "Tebrikler") - 0.05, T(10, "Sen") - 0.15, "TEBRİKLER, DİNOZOR SAHİBİSİN", y=1150, size=110, col=YEL)
    g_chips7(L, t, T(10, "Sen") - 0.1, T(10, "Daha") - 0.15)
    outro(L, t)
    fb = clamp((t - (TOTAL - 1.0)) / 1.0)
    if fb > 0.01:
        L.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, int(255 * fb))))
    if not (TITLE0 - 0.3 < t < TITLE1 + 0.3 or t > OUT0 - 0.8 or t < 2.0):
        label(L, W - 120, 92, "PRATİK ABİ", 0.42, 24, WARM, anchor="rm", w="SemiBold", track=0.4)
    return L


TL = TL37(C, TOTAL, overlay, bgfn)


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
    add(T(1, "sıkıcı") - 0.1, pop(), 0.8)
    add(T(1, "sıradan") - 0.1, pop(), 0.8)
    add(T(1, "Peki") - 0.2, roar(2.2, 85), 0.5)
    add(T(1, "sahiplendiriyoruz") - 0.1, thud(), 0.9)
    add(T(1, "sahiplendiriyoruz") + 0.2, chime(), 0.5)
    add(T(1, "1") - 0.05, ding(), 0.6)
    add(T(1, "2") - 0.05, ding(), 0.6)
    for i in range(7):
        add(_m0 + i * _md, thud(), 0.6)
        add(_m0 + i * _md, whoosh(0.4), 0.3)
    add(TITLE0 - 0.2, boom(), 0.7)
    add(TITLE0 + 1.2, boing(), 0.5)
    stamps = [G[2] + 0.1, G[3] + 0.1, G[4] + 0.1, G[5] + 0.1, G[6] + 0.6, G[7] + 0.1, G[8] + 0.1,
              T(10, "Kuşlar") - 0.05, T(10, "tavuğun") - 0.1, T(1, "sahiplendiriyoruz") - 0.1, T(6, "Sigorta") - 0.05]
    for s in stamps:
        add(s, thud(), 0.8)
    add(T(2, "Tavuk"), boing(), 0.5)
    add(T(2, "gekon") - 0.2, trombone(), 0.35)
    add(G[3] + 0.3, roar(1.6, 140), 0.25)
    add(T(3, "Filmlerden") - 0.05, scratch(), 0.5)
    add(T(3, "orak") - 0.3, pop(), 0.8)
    add(T(3, "Kanepene"), scratch(), 0.4)
    add(T(3, "Kapı") - 0.05, boing(), 0.5)
    add(T(4, "Çim") - 0.1, ding(), 0.5)
    for k, n in (("çim", 1), ("çit", 0), ("gülleri", 0)):
        add(T(4, k, n), pop(), 0.8)
    add(T(4, "Havuzunu") - 0.05, ticks(1.6), 0.6)
    add(T(4, "bitirir") - 0.1, trombone(), 0.35)
    add(G[5] + 0.3, boom(1.6, 55, 28), 0.5)
    add(T(5, "Boynunu"), boing(), 0.4)
    add(T(5, "aidat") - 0.1, scratch(), 0.6)
    add(G[6] + 0.3, boom(1.0, 90, 40), 0.7)
    for k in ("Kapıyı", "duvarı", "arabanın"):
        add(T(6, k) - 0.05, boom(0.9, 110, 50), 0.8)
    add(G[7] + 0.4, rumble(3.0), 0.3)
    add(T(7, "sen") - 0.05, scratch(), 0.5)
    add(G[8] - 0.1, roar(2.6, 78), 0.7)
    add(G[8] + 0.1, boom(2.0, 70, 30), 0.6)
    add(T(8, "700") - 0.3, pop(), 0.8)
    add(T(8, "3500") - 0.3, ding(), 0.6)
    add(T(8, "Ayda") - 0.2, ding(), 0.6)
    add(T(8, "Biz") - 0.05, trombone(), 0.4)
    add(T(8, "Hatırla") + 0.3, roar(2.2, 90), 0.45)
    add(T(8, "sensin") - 0.3, scratch(), 0.7)
    add(T(9, "belediye"), shutter(), 0.3)
    add(T(9, "Bu") + 0.2, roar(2.0, 95), 0.4)
    add(T(10, "Kuşlar") - 0.1, chime(), 0.6)
    add(T(10, "Tebrikler") - 0.1, chime(), 0.8)
    for k in ("Mama", "kapıyı", "seni"):
        add(T(10, k), ding(), 0.5)
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
    trk = {k: load(WORK / f"m{k}.wav") for k in ("pet", "comic", "sneak", "epic")}
    plan = [("pet", 0.0), ("epic", TITLE0 - 0.6), ("comic", TITLE1 - 0.2), ("pet", G[4] - 0.5), ("comic", G[6] - 0.5),
            ("sneak", G[7] - 0.5), ("epic", G[8] - 0.6), ("comic", T(8, "Şimdi") - 0.5), ("sneak", T(8, "Peki") - 0.4),
            ("comic", G[9] - 0.4), ("pet", G[10] - 0.5)]
    mus = np.zeros(n, np.float32)
    XF = int(1.2 * SR)

    def looped(src, Ln):
        out = src.copy()
        while len(out) < Ln:
            mixz = out[-XF:] * np.linspace(1, 0, XF) + src[:XF] * np.linspace(0, 1, XF)
            out = np.concatenate([out[:-XF], mixz, src[XF:]])
        return out[:Ln].copy()

    for j, (k, st) in enumerate(plan):
        en = plan[j + 1][1] + 1.2 if j + 1 < len(plan) else TOTAL
        a, b = int(st * SR), min(n, int(en * SR))
        seg = looped(trk[k], b - a)
        fi = XF if j > 0 else int(0.4 * SR)
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


def render_all(keep=0):
    out_dir = WORK / "parts"
    out_dir.mkdir(exist_ok=True)
    n = int(round(TOTAL * FPS))
    step = 900
    jobs = [(a, min(n, a + step), str(out_dir / f"p{j:02d}.mp4")) for j, a in enumerate(range(0, n, step))]
    todo = [j for k, j in enumerate(jobs) if k >= keep]
    with Pool(2) as p:
        p.map(TL.render_chunk, todo, chunksize=1)
    lst = out_dir / "list.txt"
    lst.write_text("".join(f"file '{x[2]}'\n" for x in jobs))
    # birleştir + sıkıştır (ara dosya yok, <400 MB hedef)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-i",
                    str(WORK / "mix.wav"), "-map", "0:v", "-map", "1:a", "-vf", "hqdn3d=3:2:4:4", "-c:v", "libx264",
                    "-preset", "veryfast", "-b:v", "6500k", "-maxrate", "7500k", "-bufsize", "15000k", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(WORK / "final.mp4")],
                   check=True)


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
    elif mode == "some":
        pass
    else:
        build_audio()
        render_all(int(sys.argv[3]) if len(sys.argv) > 3 else 0)
        print("render bitti", TOTAL, flush=True)


def render_some(idx):
    out_dir = WORK / "parts"
    n = int(round(TOTAL * FPS))
    jobs = [(a, min(n, a + 900), str(out_dir / f"p{j:02d}.mp4")) for j, a in enumerate(range(0, n, 900))]
    with Pool(2) as p:
        p.map(TL.render_chunk, [jobs[i] for i in idx], chunksize=1)
    lst = out_dir / "list.txt"
    lst.write_text("".join(f"file '{x[2]}'\n" for x in jobs))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-i",
                    str(WORK / "mix.wav"), "-map", "0:v", "-map", "1:a", "-vf", "hqdn3d=3:2:4:4", "-c:v", "libx264",
                    "-preset", "veryfast", "-b:v", "6500k", "-maxrate", "7500k", "-bufsize", "15000k", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(WORK / "final.mp4")],
                   check=True)
    print("render bitti", flush=True)


if __name__ == "__main__" and mode == "some":
    render_some([int(x) for x in sys.argv[3].split(",")])
