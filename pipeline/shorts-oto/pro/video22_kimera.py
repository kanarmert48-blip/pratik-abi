"""22. video (uzun, 16:9 2K, ~5,5 dk): Annenin İçinde Hâlâ Senden Parçalar Var (mikrokimerizm belgeseli).
Kullanım: python3 video22_kimera.py <WORK> [frames t1,t2,..|render|ses]"""
import json, math, subprocess, sys
from pathlib import Path

import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parent))
from belgesel import *  # noqa

WORK = Path(sys.argv[1])
MED = Path("/home/claude/pratik-abi/media/v22-kimera")
ROZET = Path(__file__).resolve().parent.parent / "assets" / "abi_rozet.mp4"


def norm(w):
    return w.lower().strip(".,;:!?'\"").replace("â", "a").replace("'", "")


# ---------------- ses yerleşimi ----------------
DUR = {i: float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                 str(WORK / f"ses/v{i}.wav")], capture_output=True, text=True).stdout) for i in range(1, 10)}
WORDS = {i: json.loads((WORK / f"ses/v{i}.json").read_text(encoding="utf-8")) for i in range(1, 10)}
CARD = 2.8
G = {1: 1.0}
TITLE0 = G[1] + DUR[1] + 0.75
TITLE1 = TITLE0 + 4.4
CARDS = {}
t = TITLE1
for k in range(2, 9):
    CARDS[k] = (t, t + CARD)
    G[k] = t + CARD + 0.2
    t = G[k] + DUR[k] + 0.8
END8 = t
G[9] = END8 + 0.7
OUT0 = G[9] + DUR[9] + 1.0
TOTAL = OUT0 + 12.0


def T(seg, key, nth=0):
    if key[0].isupper():
        hits = [w for w in WORDS[seg] if w["w"].strip(".,;:!?'\"").startswith(key)]
    else:
        hits = [w for w in WORDS[seg] if norm(w["w"]).startswith(norm(key))]
    return G[seg] + hits[nth]["s"]


CHAPTERS = {2: "Kayıp DNA'nın İzi", 3: "Beyindeki Misafirler", 4: "Kalbi Onaran Hücreler", 5: "Tersi de Var",
            6: "Kalabalık Bir Beden", 7: "İçindeki Eski Bakteri", 8: "Rahmi Kuran Virüs"}

# ---------------- kesmeler ----------------
CLIPLEN = {}
for line in (WORK / "th/info.txt").read_text().splitlines():
    n, wh, d = line.split()
    CLIPLEN[n] = float(d)


def clip(name, t0, t1, off=0.0, z=(1.0, 1.07), dx=(0.0, 0.0), dy=(0.0, 0.0), xf=0.6, focus=0.5, speed=None):
    need = t1 - t0 + 1.0
    L = CLIPLEN[name] - off - 0.2
    sp = speed if speed else clamp(L / need, 0.55, 1.0)
    return {"src": MED / f"{name}.mp4", "t0": t0, "t1": t1, "off": off, "z": z, "dx": dx, "dy": dy, "xf": xf,
            "focus": focus, "speed": sp}


def dark(t0, t1, xf=0.7):
    return {"bg": "dark", "t0": t0, "t1": t1, "xf": xf}


g1 = G[1]
C = [
    # giriş
    clip("bebek_3", 0.0, T(1, "Belki"), z=(1.12, 1.0), xf=0.0),
    clip("anneogul_3", T(1, "Belki"), T(1, "beyninde"), off=6.0, dx=(0.01, -0.01)),
    clip("beyin_2", T(1, "beyninde"), T(1, "kanında"), xf=0.35),
    clip("kan_3", T(1, "kanında"), T(1, "Bu") - 0.1, off=5.0, xf=0.35),
    clip("mikroskop_1", T(1, "Bu") - 0.1, T(1, "Ve"), z=(1.0, 1.08)),
    clip("hucre_2", T(1, "Ve"), T(1, "Sen") - 0.2, z=(1.0, 1.1)),
    clip("dna_4", T(1, "Sen") - 0.2, TITLE0, z=(1.04, 1.12)),
    dark(TITLE0, TITLE1 + 0.01, xf=1.0),
]
for k, (a, b) in CARDS.items():
    C.append(dark(a, b, xf=0.8))
g = G
C += [
    # 2 - Bianchi
    clip("bakteri_4", CARDS[2][1], T(2, "Bazı"), z=(1.0, 1.08), dx=(0.02, -0.01)),
    clip("kan_3", T(2, "Bazı"), T(2, "Kaynağı"), off=20.0, z=(1.06, 1.12)),
    clip("hamile_3", T(2, "Kaynağı"), T(2, "Hamilelikte") - 0.2, off=2.0, z=(1.0, 1.06)),
    dark(T(2, "Hamilelikte") - 0.2, T(2, "Asıl") - 0.2),
    clip("kan_4", T(2, "Asıl") - 0.2, T(2, "Bir", 1) - 0.2, off=3.0),
    dark(T(2, "Bir", 1) - 0.2, T(2, "Bu") - 0.1),
    clip("hucre_1", T(2, "Bu") - 0.1, CARDS[3][0], z=(1.0, 1.1)),
    # 3 - beyin
    clip("beyin_1", CARDS[3][1], T(3, "59") - 0.3, z=(1.0, 1.08)),
    dark(T(3, "59") - 0.3, T(3, "Düşün") - 0.2),
    clip("aile_1", T(3, "Düşün") - 0.2, T(3, "Bu") - 0.2, off=2.0, z=(1.0, 1.06)),
    clip("beyin_4", T(3, "Bu") - 0.2, CARDS[4][0], off=8.0, z=(1.0, 1.08)),
    # 4 - kalp
    clip("pipet_2", CARDS[4][1], T(4, "Yavruların") - 0.2, off=4.0),
    clip("mikroskop_1", T(4, "Yavruların") - 0.2, T(4, "Sonuç") - 0.3, off=1.0, z=(1.06, 1.14)),
    dark(T(4, "Sonuç") - 0.3, T(4, "Ama") - 0.2),
    clip("kan_1", T(4, "Ama") - 0.2, CARDS[5][0], off=6.0, z=(1.0, 1.1)),
    # 5 - tersi
    clip("anneogul_3", CARDS[5][1], T(5, "Senin") - 0.2, off=14.0),
    dark(T(5, "Senin") - 0.2, T(5, "Bazı") - 0.2),
    clip("anneogul_1", T(5, "Bazı") - 0.2, T(5, "Yani") - 0.2, off=1.0),
    clip("aile_2", T(5, "Yani") - 0.2, CARDS[6][0], off=2.0, z=(1.0, 1.06)),
    # 6 - bakteri
    clip("bakteri_3", CARDS[6][1], T(6, "Vücudunda") - 0.2, off=4.0, z=(1.0, 1.08)),
    dark(T(6, "Vücudunda") - 0.2, T(6, "Üstelik") - 0.2),
    clip("bakteri_2", T(6, "Üstelik") - 0.2, CARDS[7][0], z=(1.0, 1.1)),
    # 7 - mitokondri
    clip("hucre_3", CARDS[7][1], T(7, "Mitokondriler") - 0.2, z=(1.0, 1.1)),
    dark(T(7, "Mitokondriler") - 0.2, T(7, "Hala") - 0.2),
    clip("dna_1", T(7, "Hala") - 0.2, T(7, "Ve") - 0.2, z=(1.0, 1.08)),
    dark(T(7, "Ve") - 0.2, CARDS[8][0]),
    # 8 - virüs
    clip("virus_2", CARDS[8][1], T(8, "DNA") - 0.2, z=(1.0, 1.08)),
    dark(T(8, "DNA") - 0.2, T(8, "Bunlardan") - 0.2),
    clip("virus_1", T(8, "Bunlardan") - 0.2, T(8, "Plasentanın") - 0.2, z=(1.0, 1.1)),
    clip("bebek_3", T(8, "Plasentanın") - 0.2, T(8, "Yani") - 0.2, off=5.0, z=(1.0, 1.08)),
    clip("ultrason_1", T(8, "Yani") - 0.2, END8, off=10.0, z=(1.05, 1.12)),
    # kapanış
    clip("anneogul_3", END8, T(9, "Bağırsağında") - 0.1, off=22.0, xf=0.9),
    clip("bakteri_2", T(9, "Bağırsağında") - 0.1, T(9, "hücrelerinde") - 0.1, off=6.0, xf=0.4),
    clip("hucre_4", T(9, "hücrelerinde") - 0.1, T(9, "DNA") - 0.1, xf=0.4),
    clip("dna_4", T(9, "DNA") - 0.1, T(9, "Sen", 1) - 0.2, off=4.0, xf=0.4),
    dark(T(9, "Sen", 1) - 0.2, T(9, "Bir") - 0.2),
    clip("aile_2", T(9, "Bir") - 0.2, OUT0 + 0.2, off=6.0, z=(1.0, 1.08), speed=0.6),
    dark(OUT0, TOTAL, xf=1.2),
]

# ---------------- prosedürel koyu arka plan ----------------
_yy, _xx = np.mgrid[0:H, 0:W].astype(np.float32)
_r = np.sqrt(((_xx - W * 0.5) / W) ** 2 + ((_yy - H * 0.46) / H) ** 2)
DARKBASE = np.zeros((H, W, 3), np.float32)
for c, (a, b) in enumerate(zip((22, 26, 36), (6, 7, 10))):
    DARKBASE[..., c] = b + (a - b) * np.clip(1 - _r * 1.6, 0, 1) ** 1.5
del _yy, _xx, _r
_pr = np.random.default_rng(22)
BOKEH = [(_pr.uniform(0, W), _pr.uniform(0, H), _pr.uniform(14, 70), _pr.uniform(-12, 12), _pr.uniform(-8, 8),
          _pr.uniform(0, 6.28), GOLD if _pr.random() < 0.6 else CYAN, _pr.uniform(0.05, 0.16)) for _ in range(46)]


def bgfn(name, t, lt):
    im = Image.fromarray(DARKBASE.astype(np.uint8)).convert("RGBA")
    for x, y, r, vx, vy, ph0, col, a in BOKEH:
        xx = (x + vx * t) % (W + 200) - 100
        yy = (y + vy * t + 14 * math.sin(t * 0.3 + ph0)) % (H + 200) - 100
        al = a * (0.6 + 0.4 * math.sin(t * 0.5 + ph0))
        dot(im, xx, yy, r, col, al, power=2.2)
    return np.asarray(im.convert("RGB"))


# ---------------- grafik yardımcıları ----------------
def lower_third(L, t, s, e, name, sub, x=170, y=1170):
    a = window(t, s, e, 0.6, 0.5)
    if a <= 0:
        return
    put(L, LT_SHADE, x - 170, y + 90, "lm", a)
    d = ImageDraw.Draw(L)
    ln = 110 * eo(ph(t, s, 0.7))
    d.rectangle([x, y, x + ln, y + 4], fill=GOLD + (int(255 * a),))
    q = eo(ph(t, s + 0.15, 0.7))
    text(L, x - 4, y + 58, name, "sans", "SemiBold", 54, WARM, a * q, track=0.01, anchor="lm", rise=(1 - q) * 14)
    q2 = eo(ph(t, s + 0.35, 0.7))
    text(L, x - 2, y + 116, sub, "sans", "Regular", 34, GREY, a * q2, track=0.02, anchor="lm", rise=(1 - q2) * 14)


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
_bot[..., 3] = (np.clip((_by - H * 0.62) / (H * 0.38), 0, 1) ** 1.3 * 175).astype(np.uint8)
BOT = Image.fromarray(_bot, "RGBA")
del _by, _bot


def cite(L, t, s, e, txt):
    a = window(t, s, e, 0.8, 0.6) * 0.75
    text(L, 170, 1372, "Kaynak: " + txt, "sans", "Italic", 26, GREY, a, anchor="lm", shadow=0.7)


def quote(L, t, s, e, txt, y=1180, size=86, color=WARM, italic=True):
    a = window(t, s, e, 0.8, 0.6)
    if a <= 0:
        return
    if y > 1000:
        L.alpha_composite(set_alpha(BOT, a))
    q = eo(ph(t, s, 1.2))
    text(L, W / 2, y, txt, "serif", "Regular", size, color, a, track=0.01 + 0.03 * (1 - q), italic=italic, shadow=0.8,
         rise=(1 - q) * 18)


def label(L, x, y, txt, a, size=30, color=WARM, anchor="mm", w="Medium", track=0.18):
    text(L, x, y, txt, "sans", w, size, color, a, track=track, anchor=anchor)


def shade(L, t, s, e, amt=0.45):
    a = window(t, s, e, 0.6, 0.6) * amt
    if a > 0.01:
        L.alpha_composite(Image.new("RGBA", (W, H), (4, 5, 8, int(255 * a))))


_SS = {}


def ss_canvas(w, h, k=2):
    return Image.new("RGBA", (w * k, h * k), (0, 0, 0, 0)), k


def capsule(d, cx, cy, ln, wd, ang, fill=None, outline=None, width=1):
    """Döndürülmüş kapsül (kromozom kolu / bakteri) çokgen olarak."""
    pts = []
    r = wd / 2
    hl = max(0.0, ln / 2 - r)
    ca, sa = math.cos(ang), math.sin(ang)
    for side, base in ((1, 0), (-1, math.pi)):
        ox = side * hl
        for k in range(13):
            th = base - math.pi / 2 + math.pi * k / 12
            px, py = ox + r * math.cos(th), r * math.sin(th)
            pts.append((cx + px * ca - py * sa, cy + px * sa + py * ca))
    d.polygon(pts, fill=fill, outline=outline, width=width)


# ---------------- sahne grafikleri ----------------
def g_chromosomes(L, t, s, e):
    a = window(t, s, e, 0.6, 0.5)
    if a <= 0:
        return
    shade(L, t, s, e, 0.62)
    cw, ch = 1400, 620
    cv, k = ss_canvas(cw, ch)
    d = ImageDraw.Draw(cv)
    def chrom(cx, cy, scale, col, al, y_only=False):
        c = col + (int(255 * al),)
        if y_only:
            capsule(d, cx * k - 26 * k * scale, (cy - 60 * scale) * k, 150 * k * scale, 46 * k * scale, math.radians(-60), fill=c)
            capsule(d, cx * k + 26 * k * scale, (cy - 60 * scale) * k, 150 * k * scale, 46 * k * scale, math.radians(60), fill=c)
            capsule(d, cx * k, (cy + 50 * scale) * k, 170 * k * scale, 46 * k * scale, math.radians(90), fill=c)
        else:
            capsule(d, cx * k, cy * k, 330 * k * scale, 50 * k * scale, math.radians(62), fill=c)
            capsule(d, cx * k, cy * k, 330 * k * scale, 50 * k * scale, math.radians(118), fill=c)
    q1 = eo(ph(t, s + 0.1, 0.8))
    chrom(330, 300, 1.0, CYAN, 0.85 * q1)
    chrom(610, 300, 1.0, CYAN, 0.85 * q1)
    q2 = eo(ph(t, s + 1.1, 0.9))
    chrom(1050, 300 + 30 * (1 - q2), 1.0, GOLD, q2, y_only=True)
    small = cv.resize((cw, ch), Image.LANCZOS).filter(ImageFilter.GaussianBlur(0.4))
    glow = small.filter(ImageFilter.GaussianBlur(18))
    ox, oy = (W - cw) // 2, 330
    L.alpha_composite(set_alpha(glow, a * 0.9), (ox, oy))
    L.alpha_composite(set_alpha(small, a), (ox, oy))
    label(L, ox + 470, oy + 600, "ANNE  ·  XX", a * q1, 34, CYAN)
    label(L, ox + 1050, oy + 600, "Y  ·  ERKEK DNA'SI", a * q2, 34, GOLD)


def flow_particles(L, t, s, e, p0, p1, bend, col, n=40, speed=0.32, rad=14, seed=1, a=1.0, spread=30):
    rng = np.random.default_rng(seed)
    offs = rng.uniform(0, 1, n)
    jit = rng.normal(0, spread, (n, 2))
    if t < s:
        return
    for i in range(n):
        q = ((t - s) * speed + offs[i]) % 1.0
        if t - s < offs[i] / speed:      # yavaş yavaş akmaya başlasın
            continue
        mx, my = (p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2 + bend
        x = (1 - q) ** 2 * p0[0] + 2 * (1 - q) * q * mx + q * q * p1[0] + jit[i, 0] * math.sin(q * math.pi)
        y = (1 - q) ** 2 * p0[1] + 2 * (1 - q) * q * my + q * q * p1[1] + jit[i, 1] * math.sin(q * math.pi)
        fa = math.sin(q * math.pi) ** 0.6 * a
        dot(L, x, y, rad * 2.2, col, fa * 0.45, power=2.5)
        dot(L, x, y, rad * 0.55, (255, 255, 255), fa * 0.9, power=1.2)


def node(L, x, y, r, txt, col, a, pulse=0.0):
    if a <= 0.01:
        return
    d = ImageDraw.Draw(L)
    rr = r * (1 + 0.03 * pulse)
    dot(L, x, y, rr * 1.6, col, a * 0.22, power=2.0)
    d.ellipse([x - rr, y - rr, x + rr, y + rr], outline=col + (int(230 * a),), width=4)
    label(L, x, y + r + 70, txt, a, 36, col)


def g_placenta(L, t, s, e):
    a = window(t, s, e, 0.6, 0.5)
    if a <= 0:
        return
    bx, ax, y = 760, 1800, 690
    node(L, bx, y, 150, "BEBEK", CYAN, a * eo(ph(t, s, 0.7)))
    node(L, ax, y, 210, "ANNE", GOLD, a * eo(ph(t, s + 0.3, 0.7)))
    # plasenta zarı: dalgalı dikey çizgi
    qa = eo(ph(t, s + 0.6, 0.8)) * a
    if qa > 0.01:
        d = ImageDraw.Draw(L)
        pts = [(1280 + 16 * math.sin(yy / 38 + t * 1.2), yy) for yy in range(430, 960, 6)]
        d.line(pts, fill=WARM + (int(150 * qa),), width=3)
        label(L, 1280, 1010, "PLASENTA", qa * 0.85, 28, WARM)
    flow_particles(L, t, s + 1.0, e, (bx + 120, y), (ax - 120, y + 20), -170, CYAN, n=44, speed=0.33, a=a)


def g_years(L, t, s, e):
    a = window(t, s, e, 0.6, 0.5)
    if a <= 0:
        return
    x0, x1, y = 520, 2040, 860
    d = ImageDraw.Draw(L)
    q = eio(ph(t, s + 0.8, 3.6))
    d.line([(x0, y), (x1, y)], fill=WARM + (int(70 * a),), width=3)
    d.line([(x0, y), (x0 + (x1 - x0) * q, y)], fill=GOLD + (int(255 * a),), width=5)
    for xx, lab in ((x0, "DOĞUM"), (x1, "27 YIL SONRA")):
        d.line([(xx, y - 18), (xx, y + 18)], fill=WARM + (int(160 * a),), width=3)
        label(L, xx, y + 70, lab, a * 0.9, 30, GREY)
    px = x0 + (x1 - x0) * q
    dot(L, px, y, 46, GOLD, a * 0.55, power=2.2)
    dot(L, px, y, 11, (255, 255, 255), a, power=1.0)
    n = int(round(27 * q))
    text(L, W / 2, 500, str(n), "serif", "Regular", 260, WARM, a, shadow=0.6)
    label(L, W / 2, 700, "YIL", a, 40, GOLD, track=0.5)


def g_word(L, t, s, e):
    a = window(t, s, e, 0.8, 0.6)
    if a <= 0:
        return
    shade(L, t, s, e, 0.66)
    q = eo(ph(t, s, 1.6))
    text(L, W / 2, 640, "Mikrokimerizm", "serif", "Regular", 170, WARM, a, track=0.06 * (1 - q) + 0.01, shadow=0.8)
    q2 = eo(ph(t, s + 1.2, 1.0))
    text(L, W / 2, 800, "vücudunda başka birine ait hücreler taşımak", "sans", "Light", 50, GOLD, a * q2, track=0.04,
         shadow=0.8, rise=(1 - q2) * 12)


def g_dots(L, t, s, e, t63, t94):
    a = window(t, s, e, 0.6, 0.5)
    if a <= 0:
        return
    cols, gap, x0, y0 = 10, 104, 330, 380
    order = np.random.default_rng(3).permutation(59)
    lit = set(order[:37].tolist())
    for i in range(59):
        r, c = divmod(i, cols)
        x, y = x0 + c * gap, y0 + r * gap
        qi = eo(ph(t, s + 0.4 + i * 0.03, 0.4))
        on = i in lit and t >= t63 + (np.where(order == i)[0][0]) * 0.025
        col = GOLD if on else (120, 124, 134)
        if on:
            dot(L, x, y, 40, GOLD, a * 0.35 * qi, power=2.2)
        dot(L, x, y, 17, col, a * qi, power=0.6, core=0.8)
    label(L, x0 + 4.5 * gap, y0 + 6 * gap + 40, "İNCELENEN 59 KADIN", a, 30, GREY)
    q = eo(ph(t, t63, 0.8))
    text(L, 1830, 640, "%63", "serif", "Regular", 300, GOLD, a * q, shadow=0.6)
    label(L, 1830, 830, "BEYNİNDE ERKEK DNA'SI", a * q, 32, WARM)
    q2 = eo(ph(t, t94, 0.8))
    text(L, 1830, 960, "en yaşlısı 94 yaşında", "serif", "Regular", 60, WARM, a * q2, italic=True, rise=(1 - q2) * 10)


def heart_pts(cx, cy, sc, beat=0.0):
    out = []
    for k in range(240):
        th = 2 * math.pi * k / 240
        x = 16 * math.sin(th) ** 3
        y = 13 * math.cos(th) - 5 * math.cos(2 * th) - 2 * math.cos(3 * th) - math.cos(4 * th)
        out.append((cx + x * sc * (1 + beat), cy - y * sc * (1 + beat)))
    return out


def g_heart(L, t, s, e, t_goc, t_donus, t_atma, t_end):
    a = window(t, s, e, 0.7, 0.5)
    if a <= 0:
        return
    cx, cy, sc = 1440, 700, 25
    beat = 0.0
    if t >= t_atma:
        ph_ = (t - t_atma) * 1.3
        beat = 0.045 * max(0.0, math.sin(ph_ * 2 * math.pi)) ** 6 * eo(ph(t, t_atma, 0.5))
    cvw, cvh = 1100, 1000
    cv, k = ss_canvas(cvw, cvh)
    d = ImageDraw.Draw(cv)
    pts = [((x - cx + cvw / 2) * k, (y - cy + cvh / 2) * k) for x, y in heart_pts(cx, cy, sc, beat)]
    q = eo(ph(t, s + 0.2, 1.4))
    n = max(2, int(len(pts) * q))
    d.line(pts[:n] + ([pts[0]] if q >= 1 else []), fill=WARM + (235,), width=5 * k, joint="curve")
    small = cv.resize((cvw, cvh), Image.LANCZOS)
    ox, oy = cx - cvw // 2, cy - cvh // 2
    L.alpha_composite(set_alpha(small.filter(ImageFilter.GaussianBlur(14)), a * 0.7), (ox, oy))
    L.alpha_composite(set_alpha(small, a), (ox, oy))
    # hasar bölgesi
    hx, hy = cx - 150, cy + 60
    heal = eo(ph(t, t_donus, 1.4))
    pul = 0.5 + 0.5 * math.sin(t * 5)
    hc = tuple(int(RED[i] * (1 - heal) + GREEN[i] * heal) for i in range(3))
    dot(L, hx, hy, 120 + 20 * pul * (1 - heal), hc, a * (0.55 + 0.2 * pul * (1 - heal)), power=2.0)
    dot(L, hx, hy, 18, (255, 255, 255), a * 0.8, power=1.0)
    label(L, hx - 330, hy + 40, "HASAR" if heal < 0.5 else "ONARIM", a * eo(ph(t, s + 1.2, 0.6)), 30, hc, anchor="rm")
    # yavrunun hücreleri sol üstten akar
    if t >= t_goc:
        flow_particles(L, t, t_goc, e, (220, 260), (hx, hy), 180, GREEN, n=46, speed=0.36, rad=13, seed=4, a=a, spread=40)
        label(L, 380, 200, "YAVRUNUN HÜCRELERİ", a * eo(ph(t, t_goc, 0.7)), 30, GREEN, anchor="lm")


def g_two_way(L, t, s, e, t_back):
    a = window(t, s, e, 0.6, 0.5)
    if a <= 0:
        return
    lx, rx, y = 820, 1740, 700
    node(L, lx, y, 170, "SEN", CYAN, a * eo(ph(t, s, 0.7)))
    node(L, rx, y, 210, "ANNEN", GOLD, a * eo(ph(t, s + 0.2, 0.7)))
    flow_particles(L, t, s + 0.5, e, (lx + 120, y - 60), (rx - 150, y - 60), -200, CYAN, n=40, speed=0.32, seed=5, a=a)
    if t >= t_back:
        flow_particles(L, t, t_back, e, (rx - 150, y + 60), (lx + 120, y + 60), 200, GOLD, n=40, speed=0.32, seed=6, a=a)


def g_bars(L, t, s, e, t38, t_oran):
    a = window(t, s, e, 0.6, 0.5)
    if a <= 0:
        return
    x0, full = 520, 1500
    d = ImageDraw.Draw(L)
    for i, (val, lab, col, st) in enumerate(((30, "İNSAN HÜCRESİ", CYAN, s + 0.5), (38, "BAKTERİ", GOLD, t38))):
        y = 600 + i * 300
        q = eio(ph(t, st, 1.6))
        if t < st - 0.01:
            continue
        al = a * eo(ph(t, st, 0.5))
        ln = full * val / 38 * q
        d.rounded_rectangle([x0, y - 14, x0 + full, y + 14], radius=14, fill=(255, 255, 255, int(18 * al)))
        if ln > 28:
            d.rounded_rectangle([x0, y - 14, x0 + ln, y + 14], radius=14, fill=col + (int(235 * al),))
            dot(L, x0 + ln, y, 60, col, al * 0.5, power=2.2)
        label(L, x0, y - 70, lab, al, 30, GREY, anchor="lm")
        text(L, x0 + full, y - 80, f"{val * q:.0f} trilyon", "serif", "Regular", 76, col, al, anchor="rm")
    q = eo(ph(t, t_oran, 0.8))
    text(L, W / 2, 1180, "Sayıca, sen biraz da onlarsın.", "serif", "Regular", 70, WARM, a * q, italic=True,
         rise=(1 - q) * 12)


def g_tags(L, t, times):
    labs = ("SİNDİRİM", "VİTAMİN", "BAĞIŞIKLIK")
    ab = window(t, times[0], times[-1] + 3.2, 0.5, 0.5)
    if ab > 0:
        L.alpha_composite(set_alpha(BOT, ab))
    for i, (lab, st) in enumerate(zip(labs, times)):
        a = window(t, st, times[-1] + 3.2, 0.5, 0.5)
        x = W / 2 + (i - 1) * 520
        if a > 0:
            dot(L, x, 1180, 9, GOLD, a, power=0.8)
            label(L, x, 1240, lab, a, 40, WARM, track=0.3)


def mito(d, cx, cy, ln, wd, ang, k, col, al):
    capsule(d, cx * k, cy * k, ln * k, wd * k, ang, outline=col + (int(255 * al),), width=int(5 * k))
    ca, sa = math.cos(ang), math.sin(ang)
    pts = []
    for j in range(80):
        u = -0.38 + 0.76 * j / 79
        px = u * ln
        py = (wd * 0.28) * math.sin(j / 79 * math.pi * 9)
        pts.append(((cx + px * ca - py * sa) * k, (cy + px * sa + py * ca) * k))
    d.line(pts, fill=col + (int(200 * al),), width=int(3 * k), joint="curve")


def g_mito(L, t, s, e, t2m, tgir):
    a = window(t, s, e, 0.6, 0.5)
    if a <= 0:
        return
    cvw, cvh = 2000, 1100
    cv, k = ss_canvas(cvw, cvh, 2)
    d = ImageDraw.Draw(cv)
    q = eo(ph(t, s, 0.9))
    if t < t2m:
        mito(d, 1000, 520, 720 * (0.9 + 0.1 * q), 300, math.radians(-8), k, GOLD, q)
    else:
        # hücre + içine giren bakteri
        qc = eo(ph(t, t2m, 0.8))
        d.ellipse([(1000 - 430) * k, (560 - 380) * k, (1000 + 430) * k, (560 + 380) * k], outline=CYAN + (int(220 * qc),),
                  width=int(5 * k))
        mv = eio(ph(t, tgir, 2.2))
        bx = 1720 - 700 * mv
        mito(d, bx, 560 + 40 * math.sin(t * 1.5) * (1 - mv), 260, 110, math.radians(-8 + 20 * mv), k, GOLD, qc)
    small = cv.resize((cvw, cvh), Image.LANCZOS)
    ox, oy = (W - cvw) // 2, 150
    L.alpha_composite(set_alpha(small.filter(ImageFilter.GaussianBlur(12)), a * 0.8), (ox, oy))
    L.alpha_composite(set_alpha(small, a), (ox, oy))
    if t < t2m:
        label(L, W / 2, 1180, "MİTOKONDRİ", a * q, 40, GOLD, track=0.4)
        text(L, W / 2, 1250, "hücrenin enerji santrali", "sans", "Light", 40, GREY, a * q)
    else:
        qq = eo(ph(t, t2m, 0.8))
        text(L, W / 2, 1230, "yaklaşık 2 milyar yıl önce", "serif", "Regular", 74, WARM, a * qq, italic=True,
             rise=(1 - qq) * 12)


def g_generations(L, t, s, e):
    a = window(t, s, e, 0.6, 0.6)
    if a <= 0:
        return
    xs, y = (700, 1280, 1860), 680
    labs = ("ANNEANNEN", "ANNEN", "SEN")
    d = ImageDraw.Draw(L)
    for i, (x, lab) in enumerate(zip(xs, labs)):
        qi = eo(ph(t, s + 0.2 + i * 0.35, 0.6))
        node(L, x, y, 120, lab, GOLD if i < 2 else CYAN, a * qi)
    ql = eio(ph(t, s + 0.6, 1.8))
    if ql > 0:
        xa, xb = xs[0] + 125, xs[0] + 125 + (xs[2] - 125 - xs[0] - 125) * ql
        d.line([(xa, y), (xb, y)], fill=GOLD + (int(220 * a),), width=4)
        dot(L, xb, y, 40, GOLD, a * 0.6, power=2.2)
    label(L, W / 2, 1060, "MİTOKONDRİ DNA'SI SADECE ANNEDEN GEÇER", a * eo(ph(t, s + 1.5, 0.7)), 32, WARM, track=0.2)


def g_strip(L, t, s, e, t8):
    a = window(t, s, e, 0.6, 0.5)
    if a <= 0:
        return
    n, x0, w, y, h = 100, 330, 1900, 700, 160
    bw = w / n
    vir = set(np.random.default_rng(8).choice(n, 8, replace=False).tolist())
    d = ImageDraw.Draw(L)
    for i in range(n):
        qi = eo(ph(t, s + 0.2 + i * 0.008, 0.4))
        on = i in vir and t >= t8
        col = RED if on else (150, 154, 164)
        hh = h * (1.0 if on else 0.82)
        x = x0 + i * bw
        d.rectangle([x + 2, y - hh / 2, x + bw - 3, y + hh / 2], fill=col + (int((235 if on else 110) * a * qi),))
        if on:
            dot(L, x + bw / 2, y, 70, RED, a * 0.35 * eo(ph(t, t8, 0.6)), power=2.2)
    label(L, x0, y - 150, "SENİN DNA'N", a, 30, GREY, anchor="lm")
    q = eo(ph(t, t8, 0.8))
    text(L, W / 2, 1010, "%8", "serif", "Regular", 200, RED, a * q)
    label(L, W / 2, 1150, "ESKİ VİRÜS KALINTILARI", a * q, 32, WARM, track=0.3)


# ---------------- kartlar ----------------
def title_card(L, t):
    a = window(t, TITLE0 + 0.2, TITLE1, 0.9, 0.7)
    if a <= 0:
        return
    label(L, W / 2, 470, "PRATİK ABİ", a * eo(ph(t, TITLE0 + 0.2, 1.0)) * 0.85, 30, GOLD, track=0.6)
    q1 = eo(ph(t, TITLE0 + 0.4, 1.6))
    text(L, W / 2, 640, "Annenin İçinde Hâlâ", "serif", "Regular", 132, WARM, a * q1, track=0.05 * (1 - q1) + 0.005,
         shadow=0.7, rise=(1 - q1) * 20)
    q2 = eo(ph(t, TITLE0 + 0.9, 1.6))
    text(L, W / 2, 800, "Senden Parçalar Var", "serif", "Regular", 132, GOLD, a * q2, italic=True,
         track=0.05 * (1 - q2) + 0.005, shadow=0.7, rise=(1 - q2) * 20)
    ln = 640 * eio(ph(t, TITLE0 + 1.4, 1.4))
    d = ImageDraw.Draw(L)
    d.rectangle([W / 2 - ln / 2, 925, W / 2 + ln / 2, 927], fill=GOLD + (int(200 * a),))


def chapter_card(L, t):
    for k, (s, e) in CARDS.items():
        a = window(t, s + 0.3, e + 0.4, 0.8, 0.6)
        if a <= 0:
            continue
        q = eo(ph(t, s + 0.3, 1.2))
        text(L, W / 2, 560, f"{k - 1:02d}", "serif", "Regular", 150, GOLD, a * q, italic=True, rise=(1 - q) * 16)
        q2 = eo(ph(t, s + 0.6, 1.2))
        text(L, W / 2, 740, CHAPTERS[k], "serif", "Regular", 112, WARM, a * q2, track=0.04 * (1 - q2) + 0.005,
             rise=(1 - q2) * 16)
        ln = 300 * eio(ph(t, s + 0.9, 1.0))
        ImageDraw.Draw(L).rectangle([W / 2 - ln / 2, 845, W / 2 + ln / 2, 847], fill=GOLD + (int(190 * a),))


_ROZ = None


def outro(L, t):
    global _ROZ
    a = window(t, OUT0 + 0.8, TOTAL + 1, 1.0, 0.5)
    if a <= 0:
        return
    if _ROZ is None:
        raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-ss", "0.5", "-i", str(ROZET), "-frames:v", "1", "-vf",
                              "scale=360:360", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
        im = Image.frombuffer("RGB", (360, 360), raw, "raw", "RGB", 0, 1).convert("RGBA")
        m = Image.new("L", (1440, 1440), 0)
        ImageDraw.Draw(m).ellipse([0, 0, 1439, 1439], fill=255)
        im.putalpha(m.resize((360, 360), Image.LANCZOS))
        ring = Image.new("RGBA", (384, 384), (0, 0, 0, 0))
        ImageDraw.Draw(ring).ellipse([0, 0, 383, 383], fill=GOLD + (255,))
        ring.alpha_composite(im, (12, 12))
        _ROZ = ring
    q = eo(ph(t, OUT0 + 0.8, 1.2))
    put(L, _ROZ, 640, 640, "mm", a * q, scale=0.92 + 0.08 * q)
    text(L, 640, 920, "Pratik Abi", "serif", "Regular", 96, WARM, a * q)
    label(L, 640, 1010, "ŞAŞIRTICI BİLİM, SADE ANLATIM", a * eo(ph(t, OUT0 + 1.4, 1.0)), 28, GOLD, track=0.3)


# ---------------- katman ----------------
def overlay(t):
    L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    # giriş
    quote(L, t, T(1, "hala") - 0.1, T(1, "Belki") - 0.3, "…hâlâ taşıyor.", y=1180, size=92)
    quote(L, t, T(1, "Sen") - 0.1, TITLE0 + 0.2, "Sen, sandığın kadar “sen” değilsin.", y=1170, size=92)
    title_card(L, t)
    chapter_card(L, t)
    # 2
    lower_third(L, t, T(2, "Diana") - 0.2, T(2, "Bazı") - 0.4, "Diana Bianchi", "Genetikçi · Tufts Üniversitesi, ABD")
    g_chromosomes(L, t, T(2, "erkek") - 0.3, T(2, "Kaynağı") - 0.1)
    g_placenta(L, t, T(2, "Hamilelikte"), T(2, "Asıl") - 0.3)
    g_years(L, t, T(2, "Bir", 1), T(2, "Bu") - 0.2)
    cite(L, t, T(2, "Bir", 1) + 1.0, T(2, "Bu") - 0.3, "Bianchi ve ark., PNAS, 1996")
    g_word(L, t, T(2, "Mikrokimerizm") - 0.2, CARDS[3][0] + 0.3)
    # 3
    lower_third(L, t, T(3, "2012") - 0.2, T(3, "59") - 0.5, "Seattle · 2012", "Fred Hutchinson Kanser Araştırma Merkezi")
    g_dots(L, t, T(3, "59") - 0.2, T(3, "Düşün") - 0.3, T(3, "%63") - 0.1, T(3, "94") - 0.3)
    cite(L, t, T(3, "Kadınların") - 0.2, T(3, "Düşün") - 0.4, "Chan ve ark., PLoS ONE, 2012")
    # 4
    lower_third(L, t, CARDS[4][1] + 0.4, T(4, "Yavruların") - 0.5, "Fare Deneyi", "Mount Sinai Tıp Fakültesi · New York")
    g_heart(L, t, T(4, "Sonuç") - 0.2, T(4, "Ama") - 0.3, T(4, "yavrunun") - 0.2, T(4, "dönüştü") - 0.4,
            T(4, "kendiliğinden") - 0.2, T(4, "Ama"))
    cite(L, t, T(4, "Sonuç") + 0.8, T(4, "Ama") - 0.4, "Kara ve ark., Circulation Research, 2012")
    quote(L, t, T(4, "Bazı") - 0.2, CARDS[5][0] + 0.3, "Otoimmün hastalıklarla da ilişkilendiriliyor.", y=1190, size=64)
    # 5
    g_two_way(L, t, T(5, "Senin") - 0.1, T(5, "Bazı") - 0.3, T(5, "annenin") - 0.2)
    quote(L, t, T(5, "Yani") - 0.1, CARDS[6][0] + 0.2, "Sende de annenden hücreler olabilir.", y=1190, size=76)
    # 6
    g_bars(L, t, T(6, "Vücudunda") - 0.1, T(6, "Üstelik") - 0.3, T(6, "38") - 0.2, T(6, "Yani") - 0.1)
    cite(L, t, T(6, "Vücudunda") + 0.5, T(6, "Üstelik") - 0.4, "Sender, Fuchs ve Milo, PLoS Biology, 2016")
    g_tags(L, t, (T(6, "besinini") - 0.1, T(6, "vitamin") - 0.1, T(6, "bağışıklığını") - 0.1))
    # 7
    g_mito(L, t, T(7, "Mitokondriler") - 0.1, T(7, "Hala") - 0.3, T(7, "Bilim") - 0.1, T(7, "başka") - 0.1)
    g_generations(L, t, T(7, "Ve") - 0.1, CARDS[8][0] + 0.3)
    # 8
    g_strip(L, t, T(8, "DNA") - 0.1, T(8, "Bunlardan") - 0.3, T(8, "yüzde") - 0.1)
    lower_third(L, t, T(8, "Plasentanın") - 0.1, T(8, "Yani") - 0.4, "Sinsitin Geni", "Kökeni eski bir virüs · Plasentayı kurar")
    cite(L, t, T(8, "Plasentanın") + 0.3, T(8, "Yani") - 0.4, "CNRS, 2016")
    # kapanış
    quote(L, t, T(9, "Sen", 1) - 0.1, T(9, "Bir") - 0.3, "Sen tek bir kişi değilsin.", y=640, size=104, italic=False)
    quote(L, t, T(9, "Milyarlarca") - 0.1, T(9, "Bir") - 0.3, "Milyarlarca yıllık bir kalabalıksın.", y=800, size=104,
          color=GOLD)
    quote(L, t, T(9, "Belki") - 0.1, T(9, "Sence") - 0.2, "Belki bir parçan hep onunla kaldı.", y=1190, size=84)
    quote(L, t, T(9, "Sence") - 0.1, OUT0 + 0.4, "Sence en şaşırtıcısı hangisiydi?", y=1190, size=84)
    outro(L, t)
    fb = max(1 - clamp(t / 0.9), clamp((t - (TOTAL - 1.2)) / 1.2))
    if fb > 0.01:
        L.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, int(255 * fb))))
    # filigran (kartlar hariç)
    if not (TITLE0 - 0.3 < t < TITLE1 + 0.3 or any(s - 0.3 < t < e + 0.3 for s, e in CARDS.values()) or t > OUT0):
        label(L, W - 120, 92, "PRATİK ABİ", 0.42 * clamp(t / 2.0), 24, WARM, anchor="rm", w="SemiBold", track=0.4)
    return L


TL = Timeline(C, TOTAL, overlay, bgfn)


def build_audio():
    SR = 44100
    n = int(TOTAL * SR) + SR
    voice = np.zeros(n, np.float32)
    for i in range(1, 10):
        r = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(WORK / f"ses/v{i}.wav"), "-f", "f32le", "-ac", "1",
                            "-ar", str(SR), "-"], capture_output=True, check=True)
        x = np.frombuffer(r.stdout, np.float32)
        a = int(G[i] * SR)
        voice[a:a + len(x)] += x
    import audio_tools as at
    at._write(str(WORK / "voice_full.wav"), voice[:int(TOTAL * SR)])
    # müzik: c (giriş) -> b (gizem) -> a (duygu) ... çapraz geçişli
    plan = [("c", 0.0), ("b", TITLE1 - 2.0), ("a", CARDS[5][0] - 1.0), ("b", CARDS[6][0] - 1.0), ("a", END8 - 2.0),
            ("c", OUT0 - 6.0)]
    def load(k):
        r = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(WORK / f"m{k}.wav"), "-f", "f32le", "-ac", "1",
                            "-ar", str(SR), "-"], capture_output=True, check=True)
        return np.frombuffer(r.stdout, np.float32)
    trk = {k: load(k) for k in "abc"}
    mus = np.zeros(n, np.float32)
    XF = int(3.0 * SR)
    def looped(src, L):
        out = src.copy()
        while len(out) < L:
            f = XF
            mixz = out[-f:] * np.linspace(1, 0, f) + src[:f] * np.linspace(0, 1, f)
            out = np.concatenate([out[:-f], mixz, src[f:]])
        return out[:L].copy()
    for j, (k, st) in enumerate(plan):
        en = plan[j + 1][1] + 3.0 if j + 1 < len(plan) else TOTAL
        a, b = int(st * SR), min(n, int(en * SR))
        seg = looped(trk[k], b - a)
        fi = XF if j > 0 else int(1.0 * SR)
        seg[:fi] *= np.linspace(0, 1, fi)
        if j + 1 < len(plan):
            seg[-XF:] *= np.linspace(1, 0, XF)
        else:
            seg[-int(4 * SR):] *= np.linspace(1, 0, int(4 * SR))
        mus[a:b] += seg
    mus = mus[:int(TOTAL * SR)]
    mus /= (np.max(np.abs(mus)) + 1e-9)
    at._write(str(WORK / "music.wav"), mus * 0.9)
    sfx = [(TITLE0 + 0.3, "tink")] + [(s + 0.25, "whoosh") for s, e in CARDS.values()]
    at.sfx(str(WORK / "sfx.wav"), TOTAL, sfx)
    # konuşma varken müzik kısılır (sidechain)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(WORK / "voice_full.wav"), "-i", str(WORK / "music.wav"),
                    "-i", str(WORK / "sfx.wav"), "-filter_complex",
                    "[0:a]highpass=f=70,acompressor=threshold=-20dB:ratio=3:attack=5:release=150,volume=1.0,asplit=2[v][vs];"
                    "[1:a]volume=0.30[m];[m][vs]sidechaincompress=threshold=0.02:ratio=6:attack=40:release=600[md];"
                    "[2:a]volume=0.35[s];[v][md][s]amix=inputs=3:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11",
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
            Image.fromarray(finish(np.asarray(im.convert("RGB")), 0)).save(WORK / f"fr_{tt:06.1f}.jpg", quality=90)
            for r in readers.values():
                r.close()
    elif mode == "ses":
        build_audio()
    else:
        a0 = float(sys.argv[3]) if len(sys.argv) > 3 else None
        build_audio()
        TL.render(WORK / "parts", str(WORK / "mix.wav"), str(WORK / "video.mp4"), workers=2, parts=12)
        print("render bitti", TOTAL, flush=True)
