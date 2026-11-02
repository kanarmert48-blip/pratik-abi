"""36. video (uzun, 16:9 2K, ~4,8 dk): Dinozorlar Çağına Işınlansan Kaç Gün Yaşardın?
Kullanım: python3 video36_dino.py <WORK> [frames t1,t2,..|render [keep]|ses]"""
import json, math, subprocess, sys
from functools import lru_cache
from pathlib import Path

import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parent))
from belgesel import *  # noqa

WORK = Path(sys.argv[1])
MED = WORK / "med"
KEY = WORK / "key"
ROZET = Path(__file__).resolve().parent.parent / "assets" / "abi_rozet.mp4"
SR = 44100


def norm(w):
    return w.lower().strip(".,;:!?'\"").replace("'", "")


# ---------------- ses yerleşimi ----------------
DUR = {i: float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                 str(WORK / f"ses/v{i}.wav")], capture_output=True, text=True).stdout) for i in range(1, 9)}
WORDS = {i: json.loads((WORK / f"ses/v{i}.json").read_text(encoding="utf-8")) for i in range(1, 9)}
CARD = 2.6
G = {1: 0.95}
TITLE0 = G[1] + DUR[1] + 0.45
TITLE1 = TITLE0 + 4.3
CARDS = {}
t_ = TITLE1
for k in range(2, 9):
    if k in (2, 4, 5, 6, 8):
        CARDS[k] = (t_, t_ + CARD)
        G[k] = t_ + CARD + 0.2
    else:
        G[k] = t_ + 0.15
    t_ = G[k] + DUR[k] + 0.55
    if k == 4:
        t_ += 1.3  # timsah anı
END8 = G[8] + DUR[8]
OUT0 = END8 + 0.6
TOTAL = OUT0 + 8.0
CHAP = {2: ("1. GÜN", "Varış"), 4: ("2. GÜN", "Su ve Ateş"), 5: ("3. GÜN", "Avcılar"), 6: ("4. GÜN", "Görünmez Tehlike"),
        8: ("SON GÜN", "Gökyüzündeki Nokta")}


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
_cl = WORK / "cliplen.json"
if _cl.exists():
    CLIPLEN = json.loads(_cl.read_text())
else:
    CLIPLEN = {}
    for p in list(MED.glob("*.mp4")) + list(KEY.glob("*.mp4")):
        d = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
                           capture_output=True, text=True).stdout.strip()
        CLIPLEN[p.stem] = float(d or 0)
    _cl.write_text(json.dumps(CLIPLEN))


def clip(name, t0, t1, off=0.0, z=(1.0, 1.07), dx=(0.0, 0.0), dy=(0.0, 0.0), xf=0.45, focus=0.5, speed=None):
    src = (KEY if name.startswith("k_") else MED) / f"{name}.mp4"
    need = t1 - t0 + 0.6
    L = CLIPLEN.get(name, 10) - off - 0.15
    sp = speed if speed else clamp(L / need, 0.5, 1.0)
    return {"src": src, "t0": t0, "t1": t1, "off": off, "z": z, "dx": dx, "dy": dy, "xf": xf, "focus": focus, "speed": sp}


def photo(name, t0, t1, z=(1.0, 1.08), dx=(0.0, 0.0), dy=(0.0, 0.0), xf=0.45, card=False, fy=0.5):
    return {"img": str(MED / name), "t0": t0, "t1": t1, "z": z, "dx": dx, "dy": dy, "xf": xf, "card": card, "fy": fy}


def dark(t0, t1, xf=0.5):
    return {"bg": "dark", "t0": t0, "t1": t1, "xf": xf}


C = [
    # giriş
    clip("meteor_2", 0.0, G[1] - 0.05, off=3.0, z=(1.0, 1.25), xf=0.0, speed=1.0),
    clip("egrelti_5", G[1] - 0.05, T(1, "sıcak") - 0.2, off=2.0, z=(1.12, 1.02), xf=0.0),
    clip("nehir_4", T(1, "sıcak") - 0.2, T(1, "Etrafında") - 0.15, off=3.0, z=(1.0, 1.06)),
    clip("egrelti_2", T(1, "Etrafında") - 0.15, T(1, "Uzaktan") - 0.15, off=1.0, z=(1.0, 1.08), dx=(0.02, -0.02)),
    clip("trex_kukre_2", T(1, "Uzaktan") - 0.15, T(1, "milyon") - 0.55, z=(1.0, 1.08), speed=0.85),
    clip("dino_orman_2", T(1, "milyon") - 0.55, T(1, "ne", exact=True) - 0.15, off=0.4, z=(1.0, 1.06)),
    clip("gunbatimi_3", T(1, "ne", exact=True) - 0.15, T(1, "burada") - 0.3, off=2.5, z=(1.0, 1.06)),
    clip("raptor_3", T(1, "burada") - 0.3, T(1, "gün", 0) - 0.4, off=0.0, z=(1.0, 1.1)),
    clip("raptor_4", T(1, "gün", 0) - 0.4, TITLE1 + 0.05, off=6.2, z=(1.0, 1.1), speed=0.75),
]
for k, (a, b) in CARDS.items():
    bgc = {2: ("k_ptero", 0.5), 4: ("ates_2", 1.0), 5: ("volkan_5", 2.0), 6: ("sivrisinek_1", 3.0),
           8: ("asteroit_4", 0.0)}[k]
    C.append(clip(bgc[0], a, b, off=bgc[1], z=(1.04, 1.12), xf=0.6))
C += [
    # 2 - varış
    clip("k_ptero", CARDS[2][1], T(2, "Burası") - 0.2, off=3.2, z=(1.0, 1.05), xf=0.0),
    photo("hellcreek_wm_1.jpg", T(2, "Burası") - 0.2, T(2, "Ve") - 0.25, z=(1.02, 1.12), dx=(0.02, -0.02)),
    clip("gunbatimi_1", T(2, "Ve") - 0.25, T(2, "bu", exact=True) - 0.3, off=6.0, z=(1.0, 1.05)),
    dark(T(2, "bu", exact=True) - 0.3, T(2, "bilim") - 0.3),
    clip("fosil_3", T(2, "bilim") - 0.3, T(2, "da", exact=True) - 0.3, off=2.0, z=(1.0, 1.08)),
    clip("egrelti_4", T(2, "da", exact=True) - 0.3, T(2, "Kutuplarda") - 0.2, off=1.0, z=(1.0, 1.06)),
    clip("dunya_2", T(2, "Kutuplarda") - 0.2, G[3] + 0.1, off=3.0, z=(1.0, 1.06)),
    # 3 - oksijen
    clip("egrelti_1", G[3] + 0.1, T(3, "araştırmaya") - 0.4, off=4.0, z=(1.0, 1.06)),
    dark(T(3, "araştırmaya") - 0.4, T(3, "İlk") - 0.3),
    clip("dino_orman_4", T(3, "İlk") - 0.3, CARDS[4][0] + 0.2, off=2.0, z=(1.0, 1.08)),
    # 4 - su, ateş, yemek
    clip("nehir_2", CARDS[4][1], T(4, "bu", exact=True) - 0.2, off=4.0, z=(1.0, 1.06), xf=0.0),
    clip("fosil_3", T(4, "bu", exact=True) - 0.2, T(4, "Kaynatmak") - 0.2, off=10.0, z=(1.06, 1.14)),
    clip("ates_2", T(4, "Kaynatmak") - 0.2, T(4, "çakmak") - 0.3, off=3.0, z=(1.0, 1.06)),
    clip("ates_1", T(4, "çakmak") - 0.3, T(4, "ise", exact=True) - 0.6, off=2.0, z=(1.0, 1.06)),
    clip("egrelti_5", T(4, "ise", exact=True) - 0.6, T(4, "Çayırlar") - 0.2, off=9.0, z=(1.0, 1.06)),
    clip("dino_orman_5", T(4, "Çayırlar") - 0.2, T(4, "bitkinin") - 0.3, off=0.5, z=(1.0, 1.06)),
    clip("egrelti_1", T(4, "bitkinin") - 0.3, T(4, "En") - 0.2, off=13.0, z=(1.02, 1.1)),
    clip("nehir_4", T(4, "En") - 0.2, T(4, "nehrin") - 0.2, off=8.0, z=(1.0, 1.06)),
    clip("timsah_1", T(4, "nehrin") - 0.2, CARDS[5][0] + 0.2, off=1.0, z=(1.0, 1.1)),
    # 5 - avcılar
    clip("gunbatimi_3", CARDS[5][1], T(5, "Burası") - 0.2, off=8.0, z=(1.06, 1.12), xf=0.0),
    clip("k_walk", T(5, "Burası") - 0.2, T(5, "beyninde") - 0.5, off=0.3, z=(1.0, 1.04)),
    clip("k_sniff", T(5, "beyninde") - 0.5, T(5, "Isırma") - 0.3, off=0.0, z=(1.0, 1.06), speed=0.8),
    clip("k_trex", T(5, "Isırma") - 0.3, T(5, "Bu", 0, exact=True) - 0.2, off=0.0, z=(1.0, 1.08), speed=0.9),
    clip("fil_3", T(5, "Bu", 0, exact=True) - 0.2, T(5, "Karada") - 0.3, off=2.0, z=(1.0, 1.06)),
    photo("trex_wm_2.jpg", T(5, "Karada") - 0.3, T(5, "Bu", 1, exact=True) - 0.2, z=(1.0, 1.1), dx=(-0.02, 0.02)),
    clip("raptor_2", T(5, "Bu", 1, exact=True) - 0.2, T(5, "Gerçek") - 0.25, off=0.0, z=(1.0, 1.05)),
    photo("velo_wm_1.jpg", T(5, "Gerçek") - 0.25, T(5, "asıl") - 0.3, z=(1.0, 1.12), dx=(0.03, -0.03)),
    clip("dino_orman_2", T(5, "asıl") - 0.3, T(5, "10") - 0.3, off=1.0, z=(1.02, 1.1)),
    clip("k_trike", T(5, "10") - 0.3, CARDS[6][0] + 0.2, off=0.5, z=(1.0, 1.06)),
    # 6 - görünmez tehlike
    clip("sivrisinek_1", CARDS[6][1], T(6, "Dördüncü") - 0.2, off=8.0, z=(1.0, 1.06), xf=0.0),
    clip("sivrisinek_2", T(6, "Dördüncü") - 0.2, T(6, "Bu") - 0.2, off=1.0, z=(1.0, 1.06)),
    clip("sivrisinek_3", T(6, "Bu") - 0.2, T(6, "keneler") - 0.2, off=0.5, z=(1.0, 1.06)),
    clip("kene_1", T(6, "keneler") - 0.2, T(6, "99") - 0.3, off=2.0, z=(1.0, 1.06)),
    photo("kehribar_wm_1.jpg", T(6, "99") - 0.3, T(6, "dinozor", 1) - 0.2, card=True, z=(1.0, 1.06)),
    photo("kehribar2_wm_1.jpg", T(6, "dinozor", 1) - 0.2, T(6, "Başka") - 0.2, z=(1.0, 1.1), dx=(0.02, -0.02)),
    clip("kene_1", T(6, "Başka") - 0.2, T(6, "böceklerin") - 0.3, off=20.0, z=(1.08, 1.18)),
    clip("sivrisinek_2", T(6, "böceklerin") - 0.3, T(6, "Bir") - 0.2, off=9.0, z=(1.06, 1.12)),
    clip("gunbatimi_3", T(6, "Bir") - 0.2, G[7] + 0.1, off=0.5, z=(1.0, 1.05)),
    # 7 - kaç gün
    clip("gunbatimi_1", G[7] + 0.1, T(7, "bizim") - 0.3, off=1.0, z=(1.0, 1.06)),
    dark(T(7, "bizim") - 0.3, T(7, "kaç", 1) - 0.3),
    clip("ates_1", T(7, "kaç", 1) - 0.3, T(7, "asıl") - 0.3, off=7.0, z=(1.0, 1.06)),
    clip("dunya_3", T(7, "asıl") - 0.3, CARDS[8][0] + 0.2, off=4.0, z=(1.0, 1.06)),
    # 8 - son gün
    clip("gunbatimi_1", CARDS[8][1], T(8, "10") - 0.3, off=3.0, z=(1.0, 1.12), xf=0.0),
    clip("asteroit_4", T(8, "10") - 0.3, T(8, "Bugünkü") - 0.2, off=2.5, z=(1.0, 1.1)),
    clip("asteroit_3", T(8, "Bugünkü") - 0.2, T(8, "180") - 0.3, off=0.0, z=(1.0, 1.08)),
    photo("chicxulub_wm_1.jpg", T(8, "180") - 0.3, T(8, "Canlı") - 0.2, card=True, z=(1.0, 1.06)),
    clip("volkan_4", T(8, "Canlı") - 0.2, T(8, "Yani") - 0.2, off=2.0, z=(1.0, 1.08)),
    clip("volkan_5", T(8, "Yani") - 0.2, T(8, "son", exact=True) - 0.3, off=4.0, z=(1.0, 1.06)),
    clip("asteroit_1", T(8, "son", exact=True) - 0.3, T(8, "Bir") - 0.2, off=4.0, z=(1.0, 1.06)),
    clip("zaman_3", T(8, "Bir") - 0.2, T(8, "Daha") - 0.2, off=4.0, z=(1.0, 1.05)),
    dark(T(8, "Daha") - 0.2, TOTAL, xf=0.8),
]

# ---------------- fotoğraf karesi ----------------
TW, TH = int(W * OVER) // 2 * 2, int(H * OVER) // 2 * 2


@lru_cache(maxsize=4)
def photo_frame(path, card, fy):
    im = cv2.cvtColor(cv2.imread(path), cv2.COLOR_BGR2RGB)
    h, w = im.shape[:2]
    s = max(TW / w, TH / h)
    big = cv2.resize(im, (int(w * s) + 1, int(h * s) + 1), interpolation=cv2.INTER_CUBIC)
    y0 = int((big.shape[0] - TH) * fy)
    x0 = (big.shape[1] - TW) // 2
    cov = big[y0:y0 + TH, x0:x0 + TW].astype(np.float32)
    if not card:
        return np.clip(cov * 0.97, 0, 255).astype(np.uint8)
    bg = cv2.GaussianBlur(cov, (0, 0), 40) * 0.38
    s2 = min(TW * 0.80 / w, TH * 0.80 / h)
    fw, fh = int(w * s2), int(h * s2)
    fg = cv2.resize(im, (fw, fh), interpolation=cv2.INTER_AREA).astype(np.float32)
    x, y = (TW - fw) // 2, (TH - fh) // 2
    sh = np.zeros((TH, TW), np.float32)
    sh[y + 20:y + fh + 30, x + 10:x + fw + 10] = 1
    sh = cv2.GaussianBlur(sh, (0, 0), 30)
    bg *= (1 - 0.7 * sh)[..., None]
    bg[y - 4:y + fh + 4, x - 4:x + fw + 4] = (232, 196, 132)
    bg[y:y + fh, x:x + fw] = fg
    return np.clip(bg, 0, 255).astype(np.uint8)


# ---------------- prosedürel koyu arka plan (kor parçacıkları) ----------------
_yy, _xx = np.mgrid[0:H, 0:W].astype(np.float32)
_r = np.sqrt(((_xx - W * 0.5) / W) ** 2 + ((_yy - H * 0.46) / H) ** 2)
DARKBASE = np.zeros((H, W, 3), np.float32)
for c, (a, b) in enumerate(zip((30, 24, 20), (8, 7, 6))):
    DARKBASE[..., c] = b + (a - b) * np.clip(1 - _r * 1.6, 0, 1) ** 1.5
del _yy, _xx, _r
_pr = np.random.default_rng(36)
EMBERS = [(_pr.uniform(0, W), _pr.uniform(0, H), _pr.uniform(10, 46), _pr.uniform(-10, 10), _pr.uniform(-22, -6),
           _pr.uniform(0, 6.28), GOLD if _pr.random() < 0.7 else (236, 140, 80), _pr.uniform(0.05, 0.15)) for _ in range(40)]
DARKIMG = Image.fromarray(DARKBASE.astype(np.uint8)).convert("RGBA")


def bgfn(name, t, lt):
    im = DARKIMG.copy()
    for x, y, r, vx, vy, ph0, col, a in EMBERS:
        xx = (x + vx * t + 18 * math.sin(t * 0.4 + ph0)) % (W + 200) - 100
        yy = (y + vy * t) % (H + 200) - 100
        al = a * (0.6 + 0.4 * math.sin(t * 0.7 + ph0))
        dot(im, xx, yy, r, col, al, power=2.2)
    return np.asarray(im.convert("RGB"))


class TL36(Timeline):
    def _cut_frame(self, c, t, readers):
        if "img" in c:
            lt = t - c["t0"]
            q = clamp(lt / max(0.1, c["vis_end"] - c["t0"]))
            fr = photo_frame(c["img"], c["card"], c["fy"])
            z, dx, dy = c["z"], c["dx"], c["dy"]
            return kenburns(fr, q, z[0], z[1], dx[0], dx[1], dy[0], dy[1])
        return super()._cut_frame(c, t, readers)


# ---------------- grafik yardımcıları ----------------
def _lt_shade():
    w, h = 1500, 520
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.sqrt(((xx - 300) / 1100) ** 2 + ((yy - h / 2) / 230) ** 2)
    a = (np.clip(1 - d, 0, 1) ** 1.4 * 150).astype(np.uint8)
    im = np.zeros((h, w, 4), np.uint8)
    im[..., 3] = a
    return Image.fromarray(im, "RGBA")


LT_SHADE = _lt_shade()
_by = np.arange(H, dtype=np.float32)[:, None]
_bot = np.zeros((H, W, 4), np.uint8)
_bot[..., 3] = (np.clip((_by - H * 0.58) / (H * 0.42), 0, 1) ** 1.3 * 185).astype(np.uint8)
BOT = Image.fromarray(_bot, "RGBA")
_top = np.zeros((H, W, 4), np.uint8)
_top[..., 3] = (np.clip((H * 0.22 - _by) / (H * 0.22), 0, 1) ** 1.5 * 120).astype(np.uint8)
TOP = Image.fromarray(_top, "RGBA")
del _by, _bot, _top


def lower_third(L, t, s, e, name, sub, x=170, y=1150):
    a = window(t, s, e, 0.6, 0.5)
    if a <= 0:
        return
    put(L, LT_SHADE, x - 170, y + 90, "lm", a)
    d = ImageDraw.Draw(L)
    ln = 110 * eo(ph(t, s, 0.7))
    d.rectangle([x, y, x + ln, y + 4], fill=GOLD + (int(255 * a),))
    q = eo(ph(t, s + 0.15, 0.7))
    text(L, x - 4, y + 60, name, "sans", "SemiBold", 58, WARM, a * q, track=0.01, anchor="lm", rise=(1 - q) * 14)
    q2 = eo(ph(t, s + 0.35, 0.7))
    text(L, x - 2, y + 122, sub, "sans", "Regular", 36, GREY, a * q2, track=0.02, anchor="lm", rise=(1 - q2) * 14)


def cite(L, t, s, e, txt):
    a = window(t, s, e, 0.8, 0.6) * 0.8
    text(L, 170, 1378, "Kaynak: " + txt, "sans", "Italic", 26, GREY, a, anchor="lm", shadow=0.8)


def quote(L, t, s, e, txt, y=1190, size=86, color=WARM, italic=True, x=None):
    a = window(t, s, e, 0.6, 0.5)
    if a <= 0:
        return
    if y > 1000:
        L.alpha_composite(set_alpha(BOT, a))
    q = eo(ph(t, s, 1.0))
    text(L, W / 2 if x is None else x, y, txt, "serif", "Regular", size, color, a, track=0.01 + 0.03 * (1 - q),
         italic=italic, shadow=0.85, rise=(1 - q) * 18)


def label(L, x, y, txt, a, size=30, color=WARM, anchor="mm", w="Medium", track=0.18):
    text(L, x, y, txt, "sans", w, size, color, a, track=track, anchor=anchor)


def shade(L, t, s, e, amt=0.45):
    a = window(t, s, e, 0.6, 0.6) * amt
    if a > 0.01:
        L.alpha_composite(Image.new("RGBA", (W, H), (4, 5, 8, int(255 * a))))


def big(L, t, s, e, txt, sub="", x=W / 2, y=640, size=230, color=GOLD, subcol=WARM, subsize=52):
    a = window(t, s, e, 0.5, 0.5)
    if a <= 0:
        return
    q = eo(ph(t, s, 0.7))
    sc = 1.0 + 0.12 * (1 - q)
    im = text_img(txt, ("serif", "Regular", False), size, color, 0.0, 0.85, 0)
    put(L, im, x, y, "mm", a * q, scale=sc)
    if sub:
        q2 = eo(ph(t, s + 0.3, 0.7))
        text(L, x, y + size * 0.62, sub, "sans", "Medium", subsize, subcol, a * q2, track=0.04, rise=(1 - q2) * 12)


def aa(w, h, k=2):
    im = Image.new("RGBA", (w * k, h * k), (0, 0, 0, 0))
    return im, ImageDraw.Draw(im)


def check_icon(d, cx, cy, r, col, a, k=2, kind="ok"):
    c = col + (int(255 * a),)
    if kind == "ok":
        d.line([(cx - r * 0.55, cy), (cx - r * 0.1, cy + r * 0.45), (cx + r * 0.6, cy - r * 0.45)], fill=c,
               width=int(r * 0.22), joint="curve")
    elif kind == "no":
        d.line([(cx - r * 0.45, cy - r * 0.45), (cx + r * 0.45, cy + r * 0.45)], fill=c, width=int(r * 0.22))
        d.line([(cx - r * 0.45, cy + r * 0.45), (cx + r * 0.45, cy - r * 0.45)], fill=c, width=int(r * 0.22))
    else:  # uyarı
        d.line([(cx, cy - r * 0.5), (cx, cy + r * 0.12)], fill=c, width=int(r * 0.22))
        d.ellipse([cx - r * 0.13, cy + r * 0.32, cx + r * 0.13, cy + r * 0.58], fill=c)


# ---------------- özel grafikler ----------------
def g_warp(L, t):
    """açılış: yıl sayacı 2026 -> 66 milyon yıl önce + beyaz parlama"""
    if t > G[1] + 0.3:
        return
    q = eio(ph(t, 0.05, G[1] - 0.25))
    val = 2026 - (10 ** (q * math.log10(66_000_000 + 2026)) - 1)
    a = window(t, 0.0, G[1] - 0.05, 0.12, 0.15)
    if val > 0:
        s = f"{int(val)}"
    else:
        s = "−" + f"{int(-val):,}".replace(",", ".")
    label(L, W / 2, 560, "YIL", a * 0.85, 36, GOLD, track=0.6, w="SemiBold")
    text(L, W / 2, 720, s, "sans", "Bold", 190, WARM, a, track=0.02, shadow=0.9)
    fl = window(t, G[1] - 0.3, G[1] + 0.25, 0.25, 0.3)
    if fl > 0.01:
        L.alpha_composite(Image.new("RGBA", (W, H), (255, 250, 238, int(235 * fl))))


def g_eyelids(L, t):
    s = G[1] - 0.05
    if t < s or t > s + 2.2:
        return
    lt = t - s
    # aç-kapa-aç (göz kırpma)
    if lt < 0.45:
        o = 0.35 * eo(lt / 0.45)
    elif lt < 0.7:
        o = 0.35 - 0.25 * eio((lt - 0.45) / 0.25)
    else:
        o = 0.10 + 0.9 * eo(clamp((lt - 0.7) / 1.4))
    k = 8
    w, h = W // k, H // k
    m = Image.new("L", (w, h), 255)
    ry = (h / 2 + 30) * o * 1.6
    ImageDraw.Draw(m).ellipse([w / 2 - w * 0.85, h / 2 - ry, w / 2 + w * 0.85, h / 2 + ry], fill=0)
    m = m.filter(ImageFilter.GaussianBlur(6 + 10 * (1 - o))).resize((W, H), Image.BILINEAR)
    lid = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    lid.putalpha(m)
    L.alpha_composite(lid)


def g_phone(L, t, s, e):
    a = window(t, s, e, 0.5, 0.5)
    if a <= 0:
        return
    q = eo(ph(t, s, 0.8))
    pw, ph_ = 420, 840
    im, d = aa(pw + 40, ph_ + 40)
    k = 2
    d.rounded_rectangle([20 * k, 20 * k, (pw + 20) * k, (ph_ + 20) * k], radius=54 * k, fill=(18, 20, 26, 245),
                        outline=(200, 200, 205, 255), width=5 * k)
    d.rounded_rectangle([34 * k, 34 * k, (pw + 6) * k, (ph_ + 6) * k], radius=42 * k, fill=(30, 34, 46, 255))
    # sinyal çubukları (çarpılı)
    bx, by = 70 * k, 92 * k
    for i in range(4):
        hh = (10 + i * 9) * k
        d.rectangle([bx + i * 14 * k, by - hh, bx + i * 14 * k + 9 * k, by], fill=(110, 112, 120, 255))
    d.line([(bx - 6 * k, by - 44 * k), (bx + 62 * k, by + 6 * k)], fill=RED + (255,), width=5 * k)
    # pil
    d.rounded_rectangle([(pw - 70) * k, 66 * k, (pw - 20) * k, 92 * k], radius=5 * k, outline=(200, 200, 205, 255),
                        width=3 * k)
    d.rectangle([(pw - 66) * k, 70 * k, (pw - 56) * k, 88 * k], fill=RED + (255,))
    im = im.resize((pw + 40, ph_ + 40), Image.LANCZOS)
    x, y = W * 0.72, H * 0.5 + (1 - q) * 120
    shade(L, t, s, e, 0.35)
    dot(L, x, y, 520, (150, 180, 255), a * q * 0.25, power=2.0)
    put(L, im, x, y, "mm", a * q)
    text(L, x, y - 50, "SİNYAL YOK", "sans", "Bold", 52, WARM, a * q, track=0.12)
    text(L, x, y + 40, "Pil %12", "sans", "Medium", 44, RED, a * q, track=0.08)


def g_hud(L, t):
    """sol üst gün sayacı"""
    spans = [(G[2], CARDS[4][0], "GÜN 1"), (G[4], CARDS[5][0], "GÜN 2"), (G[5], CARDS[6][0], "GÜN 3"),
             (G[6], CARDS[8][0], "GÜN 4"), (G[8], T(8, "Bir") - 0.4, "SON GÜN")]
    for s, e, txt in spans:
        a = window(t, s + 0.3, e - 0.1, 0.6, 0.4)
        if a <= 0:
            continue
        L.alpha_composite(set_alpha(TOP, a))
        d = ImageDraw.Draw(L)
        col = RED if txt == "SON GÜN" else GOLD
        d.rectangle([150, 92, 150 + 6, 152], fill=col + (int(235 * a),))
        text(L, 176, 106, txt, "sans", "Bold", 40, col, a, track=0.16, anchor="lm")
        text(L, 176, 146, "66 milyon yıl önce · Hell Creek", "sans", "Regular", 26, GREY, a * 0.9, track=0.04, anchor="lm")


def g_clock(L, t, s, e, t372):
    a = window(t, s, e, 0.6, 0.5)
    if a <= 0:
        return
    cx, cy, R = int(W * 0.29), 650, 250
    q = eio(ph(t, s + 0.2, 1.6))
    im, d = aa(2 * R + 80, 2 * R + 80)
    k = 2
    c0 = (R + 40) * k
    box = [c0 - R * k, c0 - R * k, c0 + R * k, c0 + R * k]
    d.ellipse(box, outline=(70, 72, 80, int(255 * a)), width=16 * k)
    ang = 360 * (23.5 / 24) * q
    if ang > 0.5:
        d.arc(box, -90, -90 + ang, fill=GOLD + (int(255 * a),), width=16 * k)
    if q > 0.98:
        qm = eo(ph(t, s + 1.8, 0.6))
        d.arc(box, -90 + 352.5, 270, fill=RED + (int(255 * a * qm),), width=22 * k)
    for i in range(24):
        th = math.radians(i * 15 - 90)
        r1, r2 = (R - 30) * k, (R - (52 if i % 6 == 0 else 40)) * k
        d.line([(c0 + r1 * math.cos(th), c0 + r1 * math.sin(th)), (c0 + r2 * math.cos(th), c0 + r2 * math.sin(th))],
               fill=(150, 152, 160, int(200 * a)), width=(5 if i % 6 == 0 else 3) * k)
    im = im.resize((2 * R + 80, 2 * R + 80), Image.LANCZOS)
    put(L, im, cx, cy, "mm", a)
    hrs = 23.5 * q
    text(L, cx, cy - 10, f"{hrs:.1f}".replace(".", ","), "serif", "Regular", 150, WARM, a)
    label(L, cx, cy + 92, "SAAT", a, 34, GOLD, track=0.4, w="SemiBold")
    q2 = eo(ph(t, s + 2.0, 0.8))
    text(L, cx, cy + R + 110, "Bir gün · bugün 24 saat", "sans", "Medium", 44, GREY, a * q2)
    # 372 gün
    a2 = a * eo(ph(t, t372 - 0.2, 0.7))
    if a2 > 0.01:
        rx = int(W * 0.71)
        n = int(365 + 7 * eo(ph(t, t372, 1.2)))
        text(L, rx, cy - 30, str(n), "serif", "Regular", 260, GOLD, a2)
        label(L, rx, cy + 120, "GÜN", a2, 34, GOLD, track=0.4, w="SemiBold")
        text(L, rx, cy + R + 110, "Bir yıl · bugün 365 gün", "sans", "Medium", 44, GREY, a2)
        d2 = ImageDraw.Draw(L)
        d2.rectangle([W / 2 - 1, cy - 260, W / 2 + 1, cy + 260], fill=(120, 120, 128, int(120 * a2)))


def g_shell(L, t, s, e):
    """fosil kabuktaki günlük büyüme çizgileri"""
    a = window(t, s, e, 0.6, 0.5)
    if a <= 0:
        return
    shade(L, t, s, e, 0.5)
    cx, cy = W // 2, 1010
    n = 64
    q = ph(t, s + 0.3, 3.5)
    im, d = aa(1400, 760)
    k = 2
    ox, oy = 700 * k, 700 * k
    for i in range(int(n * q) + 1):
        r = (70 + i * 9.5) * k
        alp = int(255 * a * (0.55 + 0.45 * (i % 7 == 0)))
        d.arc([ox - r, oy - r, ox + r, oy + r], 200, 340, fill=GOLD + (alp,), width=(4 if i % 7 == 0 else 2) * k)
    im = im.resize((1400, 760), Image.LANCZOS)
    put(L, im, cx, cy - 330, "mm", a)
    text(L, cx, 300, "Fosil kabuktaki günlük büyüme çizgileri", "serif", "Regular", 70, WARM, a, italic=True)
    q2 = eo(ph(t, s + 1.2, 0.8))
    label(L, cx, 1080, "70 MİLYON YIL ÖNCE · 1 YIL = 372 ÇİZGİ", a * q2, 34, GOLD, track=0.22, w="SemiBold")


O2PTS = [(205, 10), (190, 11.5), (170, 13), (150, 14.5), (130, 16), (110, 17), (90, 17.8), (75, 18.6), (66, 19.3),
         (58, 21.5), (50, 23.0), (40, 22.6), (25, 21.8), (10, 21.2), (0, 21.0)]


def g_o2(L, t, s, e, t_son, t50, t_sen):
    a = window(t, s, e, 0.6, 0.5)
    if a <= 0:
        return
    x0, x1, yb, yt = 420, 2180, 1120, 380
    X = lambda my: x0 + (210 - my) / 210 * (x1 - x0)
    Y = lambda p: yb - p / 28 * (yb - yt)
    im, d = aa(W, H, 1)
    al = int(255 * a)
    d.line([(x0, yb), (x1, yb)], fill=(150, 150, 158, al), width=3)
    for my, lab in [(200, "200"), (150, "150"), (100, "100"), (50, "50"), (0, "Bugün")]:
        d.line([(X(my), yb), (X(my), yb + 14)], fill=(150, 150, 158, al), width=3)
    for p in (10, 20):
        d.line([(x0, Y(p)), (x1, Y(p))], fill=(90, 92, 100, int(al * 0.6)), width=2)
    # bugün çizgisi (kesikli)
    for xx in range(x0, x1, 36):
        d.line([(xx, Y(21)), (xx + 18, Y(21))], fill=CYAN + (int(al * 0.9),), width=4)
    # veri çizgisi: başlangıç -> 66 (son'a kadar), sonra -> 50, sonra bugüne
    q1 = ph(t, s + 0.6, 1.0)
    q2 = ph(t, t_son, t50 - t_son + 0.6)
    q3 = ph(t, t50 + 0.5, 1.5)
    lim = 205 - 205 * (0.03 * q1) - (205 - 50) * 0.97 * eio(q2) - 50 * eio(q3)
    pts = []
    for (m0, p0), (m1, p1) in zip(O2PTS[:-1], O2PTS[1:]):
        steps = 12
        for j in range(steps):
            m = m0 + (m1 - m0) * j / steps
            if m < lim:
                break
            pts.append((X(m), Y(p0 + (p1 - p0) * j / steps)))
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
    a1 = a * eo(ph(t, s + 1.0, 0.6))
    label(L, X(205) + 20, Y(10) + 52, "~%10 · bugünün yarısı", a1, 34, GOLD, anchor="lm", w="SemiBold", track=0.04)
    a2 = a * eo(ph(t, t50 + 0.3, 0.6))
    label(L, X(50), Y(23) - 50, "~%23", a2, 36, GOLD, w="SemiBold", track=0.04)
    a3 = a * eo(ph(t, t_sen - 0.2, 0.6))
    if a3 > 0.01:
        px, py = X(66), Y(19.3)
        pulse = 0.5 + 0.5 * math.sin((t - t_sen) * 6)
        dot(L, px, py, 46 + 14 * pulse, RED, a3 * 0.8, power=1.6)
        dot(L, px, py, 14, (255, 236, 220), a3, power=0.6, core=0.6)
        ImageDraw.Draw(L).line([(px, py - 40), (px, py - 150)], fill=RED + (int(230 * a3),), width=4)
        label(L, px + 14, py - 185, "SEN BURADASIN · 66 MİLYON YIL ÖNCE", a3, 32, RED, anchor="rm", w="Bold", track=0.12)


def g_needs(L, t, s, e, rows, title, x=1880, y=300):
    """sağda liste paneli: rows = [(yazı, t_on, tür)] tür: warn | ok | no"""
    a = window(t, s, e, 0.6, 0.5)
    if a <= 0:
        return
    n = len(rows)
    pw, rh = 560, 96
    panel = Image.new("RGBA", (pw, 90 + rh * n), (8, 10, 14, int(170 * a)))
    put(L, panel, x, y, "lt", 1.0)
    d = ImageDraw.Draw(L)
    d.rectangle([x, y, x + 6, y + 90 + rh * n], fill=GOLD + (int(230 * a),))
    label(L, x + 36, y + 48, title, a, 28, GOLD, anchor="lm", w="SemiBold", track=0.3)
    for i, (txt, ton, kind) in enumerate(rows):
        q = eo(ph(t, ton, 0.5))
        if q <= 0.01:
            continue
        yy = y + 90 + rh * i + rh / 2
        col = {"ok": GREEN, "no": RED, "warn": (240, 180, 80)}[kind]
        im, dd = aa(70, 70)
        dd.ellipse([4, 4, 136, 136], outline=col + (int(255 * a * q),), width=8)
        check_icon(dd, 70, 70, 52, col, a * q, kind=kind)
        put(L, im.resize((70, 70), Image.LANCZOS), x + 74, yy, "mm", 1.0)
        text(L, x + 130, yy, txt, "sans", "SemiBold", 46, WARM, a * q, anchor="lm", rise=(1 - q) * 10)


@lru_cache(None)
def footprint(sz):
    rim = _fp(sz, (214, 190, 150, 150), 1.12).filter(ImageFilter.GaussianBlur(sz * 0.03))
    core = _fp(sz, (26, 18, 12, 225), 1.0)
    rim.alpha_composite(core, (0, int(sz * 0.02)))
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
            rx = px * math.cos(th) - py * math.sin(th)
            ry = px * math.sin(th) + py * math.cos(th)
            poly.append(((cx + tx) / 2 + rx, (cy + ty) / 2 + ry))
        d.polygon(poly, fill=c)
    return im.resize((sz, sz), Image.LANCZOS).filter(ImageFilter.GaussianBlur(1.2))


def g_footprints(L, t, s, e, times):
    a = window(t, s, e, 0.3, 0.5)
    if a <= 0:
        return
    spots = [(460, 1250, 560, 8), (1000, 1070, 440, -6), (1420, 950, 340, 9), (1760, 860, 260, -5), (2040, 790, 200, 7)]
    for (x, y, sz, rot), tt in zip(spots, times):
        q = eo(ph(t, tt, 0.25))
        if q <= 0.01:
            continue
        im = footprint(sz).rotate(rot - 12, resample=Image.BICUBIC, expand=True)
        im = im.resize((im.width, int(im.height * 0.62)), Image.LANCZOS)
        put(L, im, x, y, "mm", a * q, scale=1.15 - 0.15 * q)


def g_counter(L, t, s, e, t0):
    a = window(t, s, e, 0.5, 0.5)
    if a <= 0:
        return
    L.alpha_composite(set_alpha(BOT, a))
    q = eo(ph(t, t0, 1.3))
    v = int(round(57000 * q / 100.0) * 100)
    s_ = f"{v:,}".replace(",", ".")
    label(L, 170, 1000, "ISIRMA GÜCÜ · TAHMİNİ ÜST SINIR", a, 32, GOLD, anchor="lm", w="SemiBold", track=0.24)
    text(L, 162, 1140, s_ + " N", "sans", "Bold", 170, WARM, a, anchor="lm", shadow=0.9)


def g_raptor_tags(L, t, s_film, e_film, s_real, e_real, t_h, t_t, t_a):
    a = window(t, s_film, e_film, 0.4, 0.3)
    if a > 0:
        L.alpha_composite(set_alpha(TOP, a))
        text(L, W / 2, 230, "FİLMLERDEKİ VELOZİRAPTOR", "sans", "Bold", 72, WARM, a, track=0.08)
        q = eio(ph(t, s_film + 1.6, 0.5))
        if q > 0:
            tw = 1240
            ImageDraw.Draw(L).rectangle([W / 2 - tw / 2, 226, W / 2 - tw / 2 + tw * q, 238], fill=RED + (int(240 * a),))
    a = window(t, s_real, e_real, 0.5, 0.4)
    if a > 0:
        rows = [("Hindi büyüklüğünde", t_h, "ok"), ("Tüylü", t_t, "ok"), ("Asya'da yaşadı", t_a, "ok")]
        g_needs(L, t, s_real, e_real, rows, "GERÇEK VELOZİRAPTOR", x=1930, y=420)


def g_skydot(L, t, s, e):
    a = window(t, s, e, 1.2, 0.4)
    if a <= 0:
        return
    q = eio(ph(t, s, e - s))
    x, y = W * 0.64, H * 0.27
    fl = 0.85 + 0.15 * math.sin(t * 23) * math.sin(t * 7)
    dot(L, x, y, 60 + 180 * q, (255, 214, 170), a * 0.35 * fl, power=2.4)
    dot(L, x, y, 14 + 40 * q, (255, 248, 236), a * fl, power=0.8, core=0.55)
    if q > 0.2:
        ImageDraw.Draw(L)
        r = 120 + 30 * math.sin(t * 3)
        im, d = aa(400, 400)
        d.ellipse([400 - r * 2, 400 - r * 2, 400 + r * 2, 400 + r * 2], outline=RED + (int(220 * a * clamp((q - 0.2) * 3)),),
                  width=6)
        put(L, im.resize((400, 400), Image.LANCZOS), x, y, "mm", 1.0)


def g_comment(L, t, s, e):
    a = window(t, s, e, 0.5, 0.4)
    if a <= 0:
        return
    q = eo(ph(t, s, 0.6))
    bw, bh = 1100, 220
    im, d = aa(bw + 40, bh + 90)
    k = 2
    d.rounded_rectangle([20 * k, 20 * k, (bw + 20) * k, (bh + 20) * k], radius=60 * k, fill=(246, 242, 234, 245))
    d.polygon([(150 * k, (bh + 15) * k), (130 * k, (bh + 80) * k), (240 * k, (bh + 15) * k)], fill=(246, 242, 234, 245))
    im = im.resize((bw + 40, bh + 90), Image.LANCZOS)
    x, y = W / 2, 640 + (1 - q) * 60
    put(L, im, x, y, "mm", a * q)
    full = "Ben … gün dayanırdım"
    n = int(len(full) * clamp((t - s - 0.5) / 1.4))
    text(L, x - bw / 2 + 80, y - 40, full[:n] + ("|" if int(t * 3) % 2 == 0 else ""), "sans", "SemiBold", 70,
         (30, 30, 36), a * q, anchor="lm", shadow=0)
    label(L, x, y + 210, "YORUMLARA YAZ", a * eo(ph(t, s + 0.8, 0.6)), 40, GOLD, w="Bold", track=0.3)


def g_chips(L, t, s, e):
    a = window(t, s, e, 0.5, 0.4)
    if a <= 0:
        return
    shade(L, t, s, e, 0.6)
    text(L, W / 2, 430, "Sıradaki çağı sen seç", "serif", "Regular", 104, WARM, a, italic=True)
    items = ["BUZ ÇAĞI", "ANTİK ROMA", "GÖBEKLİTEPE"]
    for i, it in enumerate(items):
        q = eo(ph(t, s + 0.4 + i * 0.25, 0.6))
        if q <= 0.01:
            continue
        cx = W / 2 + (i - 1) * 640
        cw, chh = 560, 150
        im, d = aa(cw, chh)
        d.rounded_rectangle([3, 3, cw * 2 - 3, chh * 2 - 3], radius=chh - 3, fill=(12, 14, 20, 200),
                            outline=GOLD + (255,), width=6)
        put(L, im.resize((cw, chh), Image.LANCZOS), cx, 720 + (1 - q) * 40, "mm", a * q)
        text(L, cx, 720 + (1 - q) * 40, it, "sans", "Bold", 52, WARM, a * q, track=0.12)
    label(L, W / 2, 900, "YORUMLARA YAZ", a * eo(ph(t, s + 1.3, 0.6)), 40, GOLD, w="Bold", track=0.3)


# ---------------- kartlar ----------------
def title_card(L, t):
    a = window(t, TITLE0 + 0.1, TITLE1, 0.7, 0.6)
    if a <= 0:
        return
    shade(L, t, TITLE0, TITLE1 + 0.3, 0.5)
    label(L, W / 2, 470, "PRATİK ABİ BELGESEL", a * eo(ph(t, TITLE0 + 0.1, 1.0)) * 0.9, 30, GOLD, track=0.6)
    q1 = eo(ph(t, TITLE0 + 0.25, 1.3))
    text(L, W / 2, 640, "Dinozorlar Çağında", "serif", "Regular", 140, WARM, a * q1, track=0.05 * (1 - q1) + 0.005,
         shadow=0.85, rise=(1 - q1) * 20)
    q2 = eo(ph(t, TITLE0 + 0.65, 1.3))
    text(L, W / 2, 810, "Kaç Gün Yaşardın?", "serif", "Regular", 150, GOLD, a * q2, italic=True,
         track=0.05 * (1 - q2) + 0.005, shadow=0.85, rise=(1 - q2) * 20)
    ln = 700 * eio(ph(t, TITLE0 + 1.1, 1.2))
    ImageDraw.Draw(L).rectangle([W / 2 - ln / 2, 940, W / 2 + ln / 2, 943], fill=GOLD + (int(210 * a),))


def chapter_card(L, t):
    for k, (s, e) in CARDS.items():
        a = window(t, s + 0.15, e + 0.3, 0.6, 0.5)
        if a <= 0:
            continue
        shade(L, t, s, e + 0.3, 0.55)
        col = RED if k == 8 else GOLD
        q = eo(ph(t, s + 0.15, 1.0))
        text(L, W / 2, 600, CHAP[k][0], "sans", "Bold", 150, col, a * q, track=0.1 + 0.08 * (1 - q), rise=(1 - q) * 16)
        q2 = eo(ph(t, s + 0.45, 1.0))
        text(L, W / 2, 780, CHAP[k][1], "serif", "Regular", 104, WARM, a * q2, italic=True, rise=(1 - q2) * 16)
        ln = 320 * eio(ph(t, s + 0.7, 0.9))
        ImageDraw.Draw(L).rectangle([W / 2 - ln / 2, 880, W / 2 + ln / 2, 883], fill=col + (int(200 * a),))


_ROZ = None


def outro(L, t):
    global _ROZ
    a = window(t, OUT0 - 0.6, TOTAL + 1, 0.9, 0.5)
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
    q = eo(ph(t, OUT0 - 0.6, 1.1))
    put(L, _ROZ, W / 2, 560, "mm", a * q, scale=0.92 + 0.08 * q)
    text(L, W / 2, 870, "Pratik Abi", "serif", "Regular", 110, WARM, a * q)
    label(L, W / 2, 960, "ŞAŞIRTICI BİLİM, SADE ANLATIM", a * eo(ph(t, OUT0, 1.0)), 30, GOLD, track=0.3)
    q2 = eo(ph(t, OUT0 + 0.6, 0.7))
    if q2 > 0.01:
        pulse = 1 + 0.035 * math.sin((t - OUT0) * 5)
        bw, bh = 520, 130
        im, d = aa(bw, bh)
        d.rounded_rectangle([0, 0, bw * 2, bh * 2], radius=bh, fill=(214, 40, 40, 255))
        btn = im.resize((bw, bh), Image.LANCZOS)
        put(L, btn, W / 2, 1150, "mm", a * q2, scale=pulse)
        text(L, W / 2, 1150, "TAKİP ET", "sans", "Bold", 60, (255, 255, 255), a * q2, track=0.14, shadow=0.3)


# ---------------- katman ----------------
def overlay(t):
    L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    # 1 - giriş
    g_warp(L, t)
    g_eyelids(L, t)
    quote(L, t, T(1, "milyon") - 0.5, T(1, "ne", exact=True) - 0.4, "66 milyon yıl önce", y=1190, size=96, italic=False,
          color=GOLD)
    g_phone(L, t, T(1, "Sadece") - 0.2, T(1, "burada") - 0.35)
    quote(L, t, T(1, "burada") - 0.2, TITLE0 + 0.1, "Burada kaç gün hayatta kalabilirsin?", y=1190, size=92)
    title_card(L, t)
    chapter_card(L, t)
    g_hud(L, t)
    # 2 - varış
    lower_third(L, t, T(2, "Burası") + 0.1, T(2, "Ve") - 0.4, "Hell Creek", "Montana ve Dakotalar, ABD · Fotoğraf: bugünkü görünümü")
    quote(L, t, T(2, "Güneş") - 0.2, T(2, "bu", exact=True) - 0.4, "Güneş biraz erken batıyor…", size=90)
    g_clock(L, t, T(2, "bu", exact=True) - 0.2, T(2, "bilim") - 0.4, T(2, "372") - 0.4)
    g_shell(L, t, T(2, "bilim") - 0.2, T(2, "da", exact=True) - 0.4)
    cite(L, t, T(2, "bilim") + 0.4, T(2, "da", exact=True) - 0.5, "de Winter ve ark., Paleoceanography and Paleoclimatology, 2020")
    quote(L, t, T(2, "da", exact=True) - 0.1, T(2, "Kutuplarda") - 0.3, "Bugünkünden çok daha sıcak", size=90)
    quote(L, t, T(2, "Kutuplarda") - 0.1, G[3] - 0.1, "Kutuplarda bile kalıcı buz yok", size=90)
    # 3 - oksijen
    quote(L, t, G[3] - 0.05, T(3, "araştırmaya") - 0.5, "Bu havayı solumak güvenli mi?", size=92)
    g_o2(L, t, T(3, "araştırmaya") - 0.3, T(3, "İlk") - 0.35, T(3, "Sonra"), T(3, "50"), T(3, "sen", exact=True))
    cite(L, t, T(3, "araştırmaya") + 0.3, T(3, "İlk") - 0.4, "Falkowski ve ark., Science, 2005")
    quote(L, t, T(3, "İlk") - 0.1, CARDS[4][0] + 0.1, "İlk iyi haber: nefes alabilirsin.", size=92, color=GREEN)
    # 4 - su, ateş, yemek
    needs4 = [("Temiz su", T(4, "Susadın"), "warn"), ("Ateş", T(4, "Kaynatmak"), "warn"),
              ("Yemek", T(4, "ise", exact=True) - 0.3, "warn")]
    g_needs(L, t, T(4, "Susadın") - 0.3, T(4, "nehrin") - 0.3, needs4, "İHTİYAÇLAR")
    quote(L, t, T(4, "bu", exact=True) - 0.1, T(4, "Kaynatmak") - 0.3, "Bağışıklığının hiç tanımadığı mikroplar", size=84)
    quote(L, t, T(4, "çakmak") - 0.2, T(4, "ise", exact=True) - 0.6, "Çakmak yok. Kibrit yok.", size=88)
    quote(L, t, T(4, "meyvelerin") - 0.3, T(4, "Çayırlar") - 0.3, "Bildiğin meyvelerin çoğu henüz yok", size=84)
    quote(L, t, T(4, "Çayırlar") - 0.1, T(4, "bitkinin") - 0.4, "Çayır yok · Otlar daha yeni ortaya çıkıyor", size=80)
    quote(L, t, T(4, "bitkinin") - 0.1, T(4, "En") - 0.3, "Hangisi zehirli?", size=96, color=RED)
    lower_third(L, t, E(4) + 0.1, CARDS[5][0] + 0.1, "Hell Creek'te timsahlar da vardı", "Borealosuchus · Brachychampsa")
    # 5 - avcılar
    g_footprints(L, t, T(5, "Toprakta") - 0.1, T(5, "Burası") - 0.2,
                 [T(5, "Toprakta") + 0.2 + 0.42 * i for i in range(5)])
    lower_third(L, t, T(5, "Burası") + 0.2, T(5, "beyninde") - 0.6, "Tyrannosaurus rex", "Boyu 12 metreyi bulabiliyordu")
    quote(L, t, T(5, "koku") - 0.2, T(5, "Isırma") - 0.4, "Seni görmeden kokunu alabilirdi", size=86)
    g_counter(L, t, T(5, "57") - 0.6, T(5, "Bu", 0, exact=True) - 0.3, T(5, "57") - 0.4)
    cite(L, t, T(5, "57"), T(5, "Bu", 0, exact=True) - 0.4, "Bates & Falkingham, Biology Letters, 2012")
    big(L, t, T(5, "Bu", 0, exact=True) + 0.1, T(5, "Karada") - 0.4, "≈ 5,8 ton", "oturan orta boy bir fil kadar", y=1060, size=170)
    quote(L, t, T(5, "Karada") - 0.1, T(5, "Bu", 1, exact=True) - 0.3, "Karada yaşamış en güçlü ısırık", size=90)
    g_raptor_tags(L, t, T(5, "Bu", 1, exact=True) - 0.1, T(5, "Gerçek") - 0.3, T(5, "Gerçek") - 0.1, T(5, "asıl") - 0.4,
                  T(5, "hindi") - 0.1, T(5, "tüylüydü") - 0.1, T(5, "Asya") - 0.1)
    quote(L, t, T(5, "asıl") - 0.1, T(5, "10") - 0.4, "Asıl tehlike: otla beslenen devler", size=88)
    lower_third(L, t, T(5, "10") - 0.1, CARDS[6][0] + 0.1, "Triceratops", "10 tona kadar ulaşabiliyordu")
    # 6 - görünmez tehlike
    quote(L, t, CARDS[6][1] + 0.1, T(6, "Dördüncü") - 0.3, "Seni büyük ihtimalle bir dinozor öldürmeyecek", size=82)
    quote(L, t, T(6, "Bu") - 0.1, T(6, "99") - 0.4, "Sivrisinekler de, keneler de vardı", size=88)
    lower_third(L, t, T(6, "99") + 0.1, T(6, "Başka") - 0.4, "99 milyon yıllık kehribar",
                "Dinozor tüyüne tutunmuş kene bulundu · Myanmar")
    cite(L, t, T(6, "99") + 0.5, T(6, "Başka") - 0.4, "Peñalver ve ark., Nature Communications, 2017")
    big(L, t, T(6, "8") - 0.2, T(6, "böceklerin") - 0.4, "8 kat", "kan emerek şişmiş kene", y=1050, size=190)
    quote(L, t, T(6, "Bir") - 0.1, G[7] - 0.1, "Antibiyotik yok.", size=100, color=RED)
    # 7 - kaç gün
    needs7 = [("Su", T(7, "Suyu"), "ok"), ("Ateş", T(7, "ateşi"), "ok"), ("Saklanma", T(7, "saklanmayı"), "ok")]
    g_needs(L, t, T(7, "Suyu") - 0.3, T(7, "bizim") - 0.3, needs7, "HEPSİNİ ÇÖZERSEN")
    big(L, t, T(7, "birkaç") - 0.1, T(7, "bizim") - 0.4, "Birkaç hafta", "", x=W * 0.36, y=700, size=150, color=GREEN)
    label(L, W / 2, 470, "BİZİM TAHMİNİMİZ", window(t, T(7, "bizim"), T(7, "kaç", 1) - 0.3, 0.5, 0.4), 40, GOLD,
          w="SemiBold", track=0.4)
    big(L, t, T(7, "birkaç", 1) - 0.1, T(7, "kaç", 1) - 0.3, "Birkaç gün", "", y=700, size=210, color=RED)
    g_comment(L, t, T(7, "kaç", 1) - 0.1, T(7, "asıl") - 0.3)
    quote(L, t, T(7, "asıl") - 0.1, CARDS[8][0] + 0.1, "Ama asıl sorun bambaşka.", size=96)
    # 8 - son gün
    g_skydot(L, t, T(8, "gökyüzünde") - 0.3, T(8, "10") - 0.3)
    big(L, t, T(8, "10") - 0.1, T(8, "Bugünkü") - 0.3, "≈ 10 km", "genişliğinde bir asteroit", y=1060, size=170)
    lower_third(L, t, T(8, "180") - 0.1, T(8, "Canlı") - 0.4, "Chicxulub Krateri", "Yucatán, Meksika · Çapı yaklaşık 180 km")
    big(L, t, T(8, "Canlı") - 0.1, T(8, "Yani") - 0.3, "%75", "canlı türlerinin yaklaşık dörtte üçü yok oldu", y=960,
        size=200, color=RED)
    quote(L, t, T(8, "son", exact=True) - 0.1, T(8, "Bir") - 0.3, "Son gün çoktan belli.", size=100)
    g_chips(L, t, T(8, "Bir") - 0.1, T(8, "Daha") - 0.2)
    outro(L, t)
    fb = clamp((t - (TOTAL - 1.0)) / 1.0)
    if fb > 0.01:
        L.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, int(255 * fb))))
    if not (TITLE0 - 0.3 < t < TITLE1 + 0.3 or any(s - 0.3 < t < e + 0.3 for s, e in CARDS.values()) or t > OUT0 - 0.8
            or t < G[1] + 2.0):
        label(L, W - 120, 92, "PRATİK ABİ", 0.42, 24, WARM, anchor="rm", w="SemiBold", track=0.4)
    return L


TL = TL36(C, TOTAL, overlay, bgfn)


# ---------------- ses ----------------
def load(path, sr=SR):
    r = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(path), "-f", "f32le", "-ac", "1", "-ar", str(sr), "-"],
                       capture_output=True, check=True)
    return np.frombuffer(r.stdout, np.float32).copy()


def sfx_track(n):
    from scipy.signal import butter, lfilter
    rng = np.random.default_rng(36)
    fx = np.zeros(n, np.float32)

    def add(t, y, g=1.0):
        a = int(t * SR)
        if a < 0:
            y, a = y[-a:], 0
        b = min(n, a + len(y))
        fx[a:b] += (y[:b - a] * g).astype(np.float32)

    def bp(y, lo, hi, o=2):
        b, a = butter(o, [lo / (SR / 2), hi / (SR / 2)], "band")
        return lfilter(b, a, y)

    def lp(y, f, o=2):
        b, a = butter(o, f / (SR / 2))
        return lfilter(b, a, y)

    def whoosh(d=0.9, up=True):
        m = int(d * SR)
        tt = np.linspace(0, 1, m)
        y = rng.standard_normal(m)
        env = np.sin(np.pi * tt ** (0.7 if up else 1.4)) ** 2
        y = bp(y, 300, 5000) * env
        return y / (np.abs(y).max() + 1e-9) * 0.5

    def boom(d=2.2, f0=70, f1=32):
        m = int(d * SR)
        tt = np.arange(m) / SR
        ph_ = 2 * np.pi * np.cumsum(f1 + (f0 - f1) * np.exp(-tt * 3)) / SR
        y = np.sin(ph_) * np.exp(-tt * 2.2)
        y += lp(rng.standard_normal(m), 900) * np.exp(-tt * 18) * 0.6
        return y / (np.abs(y).max() + 1e-9) * 0.9

    def thud():
        m = int(0.7 * SR)
        tt = np.arange(m) / SR
        y = np.sin(2 * np.pi * np.cumsum(45 + 60 * np.exp(-tt * 25)) / SR) * np.exp(-tt * 7)
        y += lp(rng.standard_normal(m), 400) * np.exp(-tt * 30) * 0.5
        return y / (np.abs(y).max() + 1e-9) * 0.9

    def roar(d=2.6, f0=88):
        m = int(d * SR)
        tt = np.arange(m) / SR
        jit = lp(rng.standard_normal(m), 30) * 40
        f = f0 * (0.8 + 0.35 * np.sin(np.pi * tt / d)) + jit
        ph_ = 2 * np.pi * np.cumsum(f) / SR
        src = sum(np.sign(np.sin(h * ph_)) / h for h in (1, 2, 3, 5))
        src += lp(rng.standard_normal(m), 3000) * 1.2
        am = 1 + 0.5 * lp(rng.standard_normal(m), 60) * 6
        y = (bp(src, 180, 520) * 1.0 + bp(src, 600, 1200) * 0.6 + bp(src, 1500, 2600) * 0.25) * am
        env = np.clip(tt / 0.35, 0, 1) * np.clip((d - tt) / 1.2, 0, 1)
        y = lp(y * env, 1600)
        ir = rng.standard_normal(int(1.6 * SR)) * np.exp(-np.arange(int(1.6 * SR)) / SR * 3.5)
        wet = np.convolve(y, ir)[:m + len(ir) - 1] * 0.02
        out = np.zeros(m + len(ir) - 1)
        out[:m] += y * 0.55
        out += wet
        return out / (np.abs(out).max() + 1e-9) * 0.75

    def rumble(d=6.0):
        m = int(d * SR)
        tt = np.arange(m) / SR
        y = lp(rng.standard_normal(m), 120, 3) * np.clip(tt / 1.5, 0, 1) * np.clip((d - tt) / 2.0, 0, 1)
        return y / (np.abs(y).max() + 1e-9)

    def tink():
        m = int(1.4 * SR)
        tt = np.arange(m) / SR
        y = (np.sin(2 * np.pi * 1568 * tt) + 0.5 * np.sin(2 * np.pi * 2349 * tt)) * np.exp(-tt * 4)
        return y * 0.35

    add(0.0, whoosh(1.0), 0.8)
    add(G[1] - 0.35, boom(1.6, 90, 40), 0.5)
    add(T(1, "Uzaktan") + 0.7, roar(2.8, 80), 0.6)
    add(TITLE0 - 0.2, boom(), 0.85)
    add(TITLE0 + 0.4, tink(), 0.5)
    for k, (s, e) in CARDS.items():
        add(s - 0.3, whoosh(0.9), 0.55)
        add(s + 0.1, boom(1.8, 75, 35), 0.45 if k != 8 else 0.8)
    for i in range(5):
        add(T(5, "Toprakta") + 0.2 + 0.42 * i, thud(), 0.55 + 0.08 * i)
    add(T(5, "Burası") + 0.3, roar(2.4, 72), 0.55)
    add(T(5, "Isırma") - 0.1, roar(2.0, 95), 0.5)
    add(T(5, "57") - 0.4, whoosh(0.6), 0.35)
    add(E(4) + 0.05, boom(1.4, 60, 30), 0.5)
    add(T(5, "10") - 0.1, boom(1.6, 60, 30), 0.45)
    add(T(8, "gökyüzünde") - 0.3, rumble(8.0), 0.35)
    add(T(8, "Bugünkü") - 0.2, boom(3.0, 60, 25), 0.9)
    add(T(8, "Bugünkü") + 0.2, rumble(6.0), 0.5)
    add(T(8, "Bir") - 0.2, whoosh(1.0), 0.45)
    add(OUT0 - 0.4, tink(), 0.45)
    return fx


def build_audio():
    n = int(TOTAL * SR) + SR
    voice = np.zeros(n, np.float32)
    for i in range(1, 9):
        x = load(WORK / f"ses/v{i}.wav")
        a = int(G[i] * SR)
        voice[a:a + len(x)] += x
    import audio_tools as at
    at._write(str(WORK / "voice_full.wav"), voice[:int(TOTAL * SR)])
    trk = {k: load(WORK / f"m{k}.wav") for k in "abc"}
    plan = [("b", 0.0), ("a", TITLE0 - 1.5), ("b", G[2] + 4.0), ("a", CARDS[5][0] - 0.8), ("b", CARDS[6][0] - 0.8),
            ("c", T(7, "asıl") - 1.5)]
    mus = np.zeros(n, np.float32)
    XF = int(2.5 * SR)

    def looped(src, Ln):
        out = src.copy()
        while len(out) < Ln:
            f = XF
            mixz = out[-f:] * np.linspace(1, 0, f) + src[:f] * np.linspace(0, 1, f)
            out = np.concatenate([out[:-f], mixz, src[f:]])
        return out[:Ln].copy()

    for j, (k, st) in enumerate(plan):
        en = plan[j + 1][1] + 2.5 if j + 1 < len(plan) else TOTAL
        a, b = int(st * SR), min(n, int(en * SR))
        seg = looped(trk[k], b - a)
        fi = XF if j > 0 else int(0.6 * SR)
        seg[:fi] *= np.linspace(0, 1, fi)
        if j + 1 < len(plan):
            seg[-XF:] *= np.linspace(1, 0, XF)
        else:
            seg[-int(4 * SR):] *= np.linspace(1, 0, int(4 * SR))
        g = 1.0 if k != "b" else 1.15
        mus[a:b] += seg * g
    mus = mus[:int(TOTAL * SR)]
    mus /= (np.max(np.abs(mus)) + 1e-9)
    at._write(str(WORK / "music.wav"), mus * 0.9)
    fx = sfx_track(int(TOTAL * SR))
    fx /= max(1.0, float(np.abs(fx).max()))
    at._write(str(WORK / "sfx.wav"), fx * 0.95)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(WORK / "voice_full.wav"), "-i", str(WORK / "music.wav"),
                    "-i", str(WORK / "sfx.wav"), "-filter_complex",
                    "[0:a]highpass=f=70,acompressor=threshold=-20dB:ratio=3:attack=5:release=150,volume=1.0,asplit=2[v][vs];"
                    "[1:a]volume=0.32[m];[m][vs]sidechaincompress=threshold=0.02:ratio=6:attack=40:release=600[md];"
                    "[2:a]volume=0.55[s];[v][md][s]amix=inputs=3:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11",
                    "-ar", "48000", "-c:a", "pcm_s16le", str(WORK / "mix.wav")], check=True)


if __name__ == "__main__":
    mode = sys.argv[2] if len(sys.argv) > 2 else "render"
    print("toplam", round(TOTAL, 1), "G", {k: round(v, 1) for k, v in G.items()}, flush=True)
    if mode == "frames":
        for tt in [float(x) for x in sys.argv[3].split(",")]:
            readers = {}
            base = TL.frame(tt, readers)
            ov = overlay(tt)
            im = Image.fromarray(base).convert("RGBA")
            im.alpha_composite(ov)
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
