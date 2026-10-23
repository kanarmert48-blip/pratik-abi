"""24. video (2K, ~31 sn): Yüzük parmağını kaldıramazsın (dene + tendon açıklaması). Kendi el çizimimiz.
Kullanım: python3 video24_parmak.py <WORK> [frames t1,t2,...]"""
import os
os.environ.setdefault("PA_SCALE", str(4 / 3))
import json, math, subprocess, sys
from pathlib import Path

import numpy as np
import cv2

sys.path.insert(0, str(Path(__file__).resolve().parent))
from engine import *  # noqa
import audio_tools as at
from abi_yuz import konusma
from rozet import Rozet

WORK = Path(sys.argv[1])
words = json.loads((WORK / "words.json").read_text(encoding="utf-8"))
TOTAL = at.duration(str(WORK / "voice_cut.wav"))


def _hits(key):
    k = trl(clean(key)).strip('"!?;,.…')
    return [w for w in words if trl(clean(w["w"])).strip('"!?;,.…') == k]


def T(key, nth=0):
    return _hits(key)[nth]["s"]


t_orta, t_bas, t_isa, t_ser = T("orta"), T("baş"), T("İşaret"), T("Serçe")
t_yuz = T("yüzük")
t_kald = T("Kaldıramıyorsun")
t_seb = T("Sebebi")
t_isa2, t_yuz2, t_onun, t_orta2 = T("İşaret", 1), T("Yüzük", 1), T("Onun"), T("orta", 2)
t_kil = T("kilitleniyor")
t_cta = T("Kaldırabildiysen")
GOLD = (255, 205, 96)
CYAN = (110, 220, 255)
SKIN = (238, 192, 160)


# ---------- arka plan ----------
def _wood():
    im = Image.open(WORK / "foto" / "ahsap.jpg").convert("RGB").rotate(90, expand=True)
    k = max(W / im.width, H / im.height)
    im = im.resize((round(im.width * k), round(im.height * k)), Image.LANCZOS)
    l, t = (im.width - W) // 2, (im.height - H) // 2
    im = im.crop((l, t, l + W, t + H)).filter(ImageFilter.GaussianBlur(4.5))
    a = np.asarray(im).astype(np.float32)
    a = a.mean(axis=(0, 1)) + (a - a.mean(axis=(0, 1))) * 0.7
    a = a * np.array([1.0, 0.93, 0.85]) * 0.86
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.sqrt(((xx - W / 2) / (W * 0.62)) ** 2 + ((yy - H * 0.45) / (H * 0.62)) ** 2)
    a *= (1 - 0.55 * np.clip(d - 0.35, 0, 1) ** 1.3)[..., None]
    top = np.clip((H * 0.26 - yy) / (H * 0.26), 0, 1) ** 1.3 * 0.55
    a *= (1 - top)[..., None]
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


WOOD = _wood()
_yy, _xx = np.mgrid[0:H, 0:W].astype(np.float32)
_r = np.sqrt(((_xx - W / 2) / W) ** 2 + ((_yy - H * 0.45) / H) ** 2)
NAVY = np.zeros((H, W, 3), np.float32)
for c, (a, b) in enumerate(zip((22, 32, 58), (4, 6, 14))):
    NAVY[..., c] = b + (a - b) * np.clip(1 - _r * 1.6, 0, 1) ** 1.4
NAVY = Image.fromarray(NAVY.astype(np.uint8))
del _yy, _xx, _r

# ---------- el geometrisi (1080 birim) ----------
HS = 1.08
HCX, HCY = 548, 930


def P(x, y):
    """el koordinatı -> birim"""
    return HCX + (x - 540) * HS, HCY + (y - 900) * HS


FINGERS = {  # taban (x,y), açı (derece, dikeyden), boy, taban eni
    "thumb": ((408, 1000), -54, 196, 96),
    "index": ((430, 800), -7, 232, 80),
    "middle": ((513, 785), 0, 258, 82),
    "ring": ((594, 795), 6, 240, 78),
    "pinky": ((668, 826), 14, 184, 68),
}
FOLD_MID = (t_orta + 0.25, 1.0)
PALM = [(386, 830), (420, 790), (470, 772), (540, 765), (610, 772), (668, 792), (708, 830), (716, 920), (704, 1010),
        (676, 1090), (646, 1150), (640, 1300), (452, 1300), (448, 1150), (414, 1090), (392, 1010), (382, 920)]


def chaikin(pts, n=3):
    for _ in range(n):
        out = []
        for i in range(len(pts)):
            a, b = pts[i], pts[(i + 1) % len(pts)]
            out += [(a[0] * 0.75 + b[0] * 0.25, a[1] * 0.75 + b[1] * 0.25), (a[0] * 0.25 + b[0] * 0.75, a[1] * 0.25 + b[1] * 0.75)]
        pts = out
    return pts


PALM_S = chaikin(PALM)


def finger_state(name, t):
    """(boy oranı, kalkma 0..1, titreme px)"""
    lift, shake, ln = 0.0, 0.0, 1.0
    if name == "middle":
        q = eio(ph(t, FOLD_MID[0], FOLD_MID[1]))
        ln = 1 - 0.72 * q
    seq = {"thumb": t_bas, "index": t_isa, "pinky": t_ser}
    if name in seq:
        st = seq[name]
        lift = eo(ph(t, st + 0.05, 0.35)) * (1 - eio(ph(t, st + 1.45, 0.35)))
    if name == "ring":
        a = eo(ph(t, t_yuz + 0.1, 0.3))
        b = 1 - eio(ph(t, t_kald + 1.2, 0.5))
        lift = 0.12 * a * b * (0.6 + 0.4 * math.sin(t * 38))
        shake = a * b * u(4) * math.sin(t * 47)
    return ln, lift, shake


def finger_pts(x0, y0, ang, length, wb, wt, k=1.0, n=16):
    """tabandan uca incelen parmak (birim -> px*k)"""
    a = math.radians(ang)
    dx, dy = math.sin(a), -math.cos(a)
    px, py = -dy, dx
    rt = wt / 2
    tipx, tipy = x0 + dx * (length - rt), y0 + dy * (length - rt)
    pts = [(x0 - px * wb / 2 + dx * -40, y0 - py * wb / 2 + dy * -40)]
    for i in range(n + 1):
        th = math.pi * i / n
        cx = -math.cos(th) * px + math.sin(th) * dx
        cy = -math.cos(th) * py + math.sin(th) * dy
        pts.append((tipx + rt * cx, tipy + rt * cy))
    pts.append((x0 + px * wb / 2 + dx * -40, y0 + py * wb / 2 + dy * -40))
    return [(u(x) * k, u(y) * k) for x, y in pts]


# Elin çizildiği yerel tuval
BX0, BY0, BX1, BY1 = 150, 380, 950, 1920
CW, CH = round(u(BX1 - BX0)), round(u(BY1 - BY0))
K = 2


def _loc(pts, k=K):
    return [(x - u(BX0) * k, y - u(BY0) * k) for x, y in pts]


def geom(name, t):
    (bx, by), ang, ln, wd = FINGERS[name]
    lnr, lift, shake = finger_state(name, t)
    x, y = P(bx, by)
    L = ln * HS * lnr * (1 - 0.10 * lift)
    wb = wd * HS * (1 + 0.12 * lift)
    return x + shake / S, y, ang, L, wb, wb * 0.82, lift


def part_mask(name, t, k=K):
    m = Image.new("L", (CW * k, CH * k), 0)
    d = ImageDraw.Draw(m)
    if name == "palm":
        d.polygon(_loc([(u(P(x, y)[0]) * k, u(P(x, y)[1]) * k) for x, y in PALM_S], k), fill=255)
        return m, 0.0, 0.0
    x, y, ang, L, wb, wt, lift = geom(name, t)
    d.polygon(_loc(finger_pts(x, y, ang, L, wb, wt, k), k), fill=255)
    return m, lift, L


def shade_mask(ma, lift=0.0, dark=0.0):
    """maske (0..1, yerel tuval) -> ışıklı ten RGBA: üst-sol ışık, kenar koyuluğu, kızarık kenar."""
    inner = cv2.GaussianBlur(ma, (0, 0), u(10))
    edge = np.clip(ma - inner, 0, 1) * 1.8
    hb = cv2.GaussianBlur(ma, (0, 0), u(16))
    gx = cv2.Sobel(hb, cv2.CV_32F, 1, 0, ksize=5)
    gy = cv2.Sobel(hb, cv2.CV_32F, 0, 1, ksize=5)
    nrm = np.sqrt(gx ** 2 + gy ** 2) + 1e-4
    light = (gx * 0.6 + gy * 0.8) / nrm * np.clip(nrm * 40, 0, 1)
    base = np.array([236, 186, 152], np.float32) * (1 + 0.05 * lift) * (1 - dark)
    img = np.ones(ma.shape + (3,), np.float32) * base
    img += light[..., None] * np.array([26, 22, 20])
    img = img * (1 - 0.35 * edge[..., None]) + edge[..., None] * np.array([70, 10, 0]) * 0.35
    return Image.fromarray(np.dstack([np.clip(img, 0, 255), ma * 255]).astype(np.uint8), "RGBA")


def details(im, name, t):
    """tırnak, boğum çizgisi, eklem tümseği (yerel tuval)."""
    dn = ImageDraw.Draw(im)
    if name == "palm":
        for fx in ("index", "middle", "ring", "pinky"):
            (bx, by), *_ = FINGERS[fx]
            x, y = P(bx, by + 30)
            r = u(26 * HS)
            pass
        return
    x, y, ang, L, wb, wt, lift = geom(name, t)
    if L <= 110:
        return
    a = math.radians(ang)
    dx, dy = math.sin(a), -math.cos(a)
    px, py = -dy, dx
    nl = min(0.26 * L, 58)
    nail = finger_pts(x + dx * (L - nl - 7), y + dy * (L - nl - 7), ang, nl + 40, wt * 0.66, wt * 0.6, 1.0)
    nail = [(qx - u(BX0), qy - u(BY0)) for qx, qy in nail]
    dn.polygon(nail, fill=(244, 206, 192, 255), outline=(206, 150, 132, 255))
    hx, hy = x + dx * (L - nl * 0.55) - px * wt * 0.12, y + dy * (L - nl * 0.55) - py * wt * 0.12
    dn.ellipse([u(hx) - u(BX0) - u(5), u(hy) - u(BY0) - u(9), u(hx) - u(BX0) + u(5), u(hy) - u(BY0) + u(9)],
               fill=(255, 250, 245, 150))
    for fr, wdt in ((0.36, 0.30), (0.64, 0.26)):
        cx, cy = x + dx * L * fr, y + dy * L * fr
        for off in (-3, 3):
            r = wb * wdt
            dn.arc([u(cx - r) - u(BX0), u(cy - r * 0.35 + off) - u(BY0), u(cx + r) - u(BX0), u(cy + r * 0.35 + off) - u(BY0)],
                   200, 340, fill=(196, 140, 116, 120), width=round(u(2)))


ORDER = ["thumb", "palm", "index", "middle", "ring", "pinky"]


def sleeve(lay):
    """Lacivert kazak kolu: kenarı yuvarlatılmış, gölgeli, örgü manşetli."""
    top = 1235
    pts = chaikin([(392, top + 10), (540, top - 12), (700, top + 10), (760, 2100), (340, 2100)], 3)
    poly_ = [(u(P(x, y)[0]) - u(BX0), u(P(x, y)[1]) - u(BY0)) for x, y in pts]
    m = Image.new("L", lay.size, 0)
    ImageDraw.Draw(m).polygon(poly_, fill=255)
    ma = np.asarray(m).astype(np.float32) / 255
    xs = np.linspace(-1, 1, lay.size[0])[None, :]
    shade = (1 - 0.45 * np.abs(xs) ** 2)
    col = np.array([40, 56, 100], np.float32)
    img = np.ones(ma.shape + (3,), np.float32) * col * shade[..., None]
    rib = (np.sin(np.arange(lay.size[0]) / u(5.5)) > 0.2).astype(np.float32)[None, :]
    yy = np.arange(lay.size[1])[:, None]
    ty = u(P(0, top)[1]) - u(BY0)
    band = ((yy > ty - u(14)) & (yy < ty + u(80))).astype(np.float32)
    img *= (1 - 0.18 * rib * band)[..., None]
    lay.alpha_composite(Image.fromarray(np.dstack([np.clip(img, 0, 255), ma * 255]).astype(np.uint8), "RGBA"))


def hand_layer(t, xray=0.0):
    """Gölge + ten (xray>0 iken saydam mavi siluet). Döner: tam ekran RGBA."""
    parts = []
    for n in ORDER:
        m, lift, L = part_mask(n, t)
        parts.append((n, m, lift, L))
    order = [p for p in parts if p[2] < 0.13] + sorted([p for p in parts if p[2] >= 0.13], key=lambda p: p[2])
    lay = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
    sh_all = np.zeros((CH, CW), np.float32)
    for n, m, lift, L in parts + [("sleeve", None, 0.0, 0)]:
        if n == "sleeve":
            sm = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
            sleeve(sm)
            ms = np.asarray(sm.getchannel("A").resize((CW // 2, CH // 2))).astype(np.float32) / 255
        else:
            ms = np.asarray(m.resize((CW // 2, CH // 2), Image.BILINEAR)).astype(np.float32) / 255
        bl = cv2.GaussianBlur(ms, (0, 0), u(6 + 16 * lift) / 2)
        bl = cv2.resize(bl, (CW, CH))
        M = np.float32([[1, 0, u(12 + 34 * lift)], [0, 1, u(18 + 50 * lift)]])
        bl = cv2.warpAffine(bl, M, (CW, CH))
        sh_all = np.maximum(sh_all, bl * (0.55 - 0.18 * lift))
    shadow = np.zeros((CH, CW, 4), np.uint8)
    shadow[..., :3] = (30, 14, 6)
    shadow[..., 3] = (sh_all * 255 * (1 - xray)).astype(np.uint8)
    lay.alpha_composite(Image.fromarray(shadow, "RGBA"))
    small = lambda m: np.asarray(m.resize((CW, CH), Image.LANCZOS)).astype(np.float32) / 255
    still = [p for p in parts if p[2] < 0.13]
    moving = sorted([p for p in parts if p[2] >= 0.13], key=lambda p: p[2])
    U = np.zeros((CH, CW), np.float32)
    for n, m, lift, L in still:
        U = np.maximum(U, small(m))
    sl = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
    sleeve(sl)
    U = U * (1 - np.asarray(sl.getchannel("A")).astype(np.float32) / 255 * 0)
    lay.alpha_composite(shade_mask(U))
    for n, m, lift, L in still:
        details(lay, n, t)
    for n, m, lift, L in moving:
        im = shade_mask(small(m), lift)
        details(im, n, t)
        lay.alpha_composite(im)
    lay.alpha_composite(sl)
    if xray > 0.01:
        a = np.asarray(lay).astype(np.float32)
        mask = (a[..., 3] > 8).astype(np.float32)
        ed = np.clip(mask - cv2.GaussianBlur(mask, (0, 0), u(6)), 0, 1)
        blue = np.zeros_like(a)
        blue[..., 0], blue[..., 1], blue[..., 2] = 60, 120, 190
        blue[..., 3] = (mask * 70 + ed * 200)
        blue[..., :3] += ed[..., None] * np.array([80, 120, 60])
        a = a * (1 - xray) + blue * xray
        lay = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "RGBA")
    out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    out.alpha_composite(lay, (round(u(BX0)), round(u(BY0))))
    return out


# ---------- tendonlar (x-ray) ----------
def tendon_path(name, t, to_tip=True):
    (bx, by), ang, ln, wd = FINGERS[name]
    lnr, lift, shake = finger_state(name, t)
    x, y = P(bx, by)
    a = math.radians(ang)
    dx, dy = math.sin(a), -math.cos(a)
    L = ln * HS * lnr * 0.9
    wx = {"index": 500, "middle": 528, "ring": 556, "pinky": 584}[name]
    sx, sy = P(wx, 1440)
    mx, my = P(wx + (bx - wx) * 0.5, 1000)
    pts = [(sx, sy), (mx, my), (x, y), (x + dx * L, y + dy * L)]
    out = []
    for i in range(len(pts) - 1):
        for s in range(12):
            q = s / 12
            out.append((pts[i][0] + (pts[i + 1][0] - pts[i][0]) * q, pts[i][1] + (pts[i + 1][1] - pts[i][1]) * q))
    out.append(pts[-1])
    return out


def poly(d, pts, col, w, a, draw_to=1.0):
    n = max(2, int(len(pts) * draw_to))
    d.line([(u(x), u(y)) for x, y in pts[:n]], fill=col + (int(255 * a),), width=round(u(w)), joint="curve")


def glow_line(L, pts, col, w, a, draw_to=1.0):
    if a <= 0.01:
        return
    g = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    poly(ImageDraw.Draw(g), pts, col, w * 3.2, a * 0.5, draw_to)
    L.alpha_composite(g.filter(ImageFilter.GaussianBlur(u(7))))
    poly(ImageDraw.Draw(L), pts, col, w, a, draw_to)


def xray_graphics(L, t, xr):
    if xr <= 0.01:
        return
    d = ImageDraw.Draw(L)
    for n in ("index", "middle", "ring", "pinky"):
        col = (230, 240, 255)
        if n == "ring" and t >= t_orta2:
            k = eo(ph(t, t_orta2 + 0.6, 0.5))
            col = tuple(int(230 * (1 - k) + (255, 90, 90)[i] * k) for i in range(3))
        glow_line(L, tendon_path(n, t), col, 7, xr * 0.95, eio(ph(t, t_seb + 0.2, 1.0)))
    # özel kaslar (işaret + serçe)
    q = eio(ph(t, t_isa2 + 0.1, 0.9))
    for n, off in (("index", -24), ("pinky", 22)):
        pts = [(x + off * HS * (1 - i / 60) , y) for i, (x, y) in enumerate(tendon_path(n, t))][:-6]
        glow_line(L, pts, GOLD, 7, xr * q, q)
    if q > 0.05:
        ix, iy = P(300, 640)
        px_, py_ = P(800, 690)
        text_c(L, (ix, iy), "ÖZEL KAS", "black", 44, GOLD, alpha=xr * q, stroke=5, stroke_fill=(6, 8, 14))
        text_c(L, (px_, py_), "ÖZEL KAS", "black", 44, GOLD, alpha=xr * q, stroke=5, stroke_fill=(6, 8, 14))
    # yüzük: özel kas yok
    q2 = eo(ph(t, t_yuz2, 0.4)) * (1 - eio(ph(t, t_onun + 0.2, 0.4)))
    if q2 > 0.01:
        rx, ry = P(660, 470)
        text_c(L, (rx, ry), "ÖZEL KAS YOK", "black", 40, (255, 120, 120), alpha=xr * q2, stroke=5, stroke_fill=(6, 8, 14))
    # bağ (juncturae): orta-yüzük arasında
    q3 = eo(ph(t, t_onun + 0.3, 0.6))
    if q3 > 0.01:
        mp = tendon_path("middle", t)[24 + 6]
        rp = tendon_path("ring", t)[24 + 2]
        red = eo(ph(t, t_orta2 + 0.6, 0.5))
        col = tuple(int(GOLD[i] * (1 - red) + (255, 80, 80)[i] * red) for i in range(3))
        pul = 0.75 + 0.25 * math.sin(t * 7)
        glow_line(L, [mp, ((mp[0] + rp[0]) / 2, (mp[1] + rp[1]) / 2 + 6), rp], col, 11, xr * q3 * pul)
        lx, ly = P(820, 920)
        text_c(L, (lx, ly), "BAĞ", "black", 52, col, alpha=xr * q3, stroke=6, stroke_fill=(6, 8, 14))
        d.line([(u(lx - 50), u(ly)), (u((mp[0] + rp[0]) / 2 + 24), u((mp[1] + rp[1]) / 2))], fill=col + (int(200 * xr * q3),),
               width=round(u(4)))
    # orta parmak çekiyor -> kilit
    q4 = eo(ph(t, t_kil - 0.2, 0.4))
    if q4 > 0.01:
        (bx, by), ang, ln, wd = FINGERS["ring"]
        x, y = P(bx, by)
        put_icon(L, "locked", x + 30, y - 200, 120 * eb(ph(t, t_kil - 0.2, 0.45)), alpha=xr)


# ---------- yazı / işaretler ----------
def ftitle(L, t):
    end = t_bas - 0.3
    if t > end + 0.4:
        return
    a = 1 - eio(ph(t, end, 0.4))
    pop = 1 + 0.1 * (1 - eb(ph(t, 0, 0.35)))
    text_c(L, (540, 150), "ŞİMDİ DENE", "black", 42, GOLD, alpha=a, stroke=5, stroke_fill=(10, 8, 6))
    text_c(L, (540, 250), "YÜZÜK PARMAĞINI", "black", round(92 * pop), WHITE, alpha=a, stroke=8, stroke_fill=(10, 8, 6))
    text_c(L, (540, 355), "KALDIRAMAZSIN!", "black", round(104 * pop), GOLD, alpha=a, stroke=9, stroke_fill=(10, 8, 6))


def marks(L, t):
    for n, st in (("thumb", t_bas), ("index", t_isa), ("pinky", t_ser)):
        a = eo(ph(t, st + 0.25, 0.3)) * (1 - eio(ph(t, st + 1.5, 0.3)))
        if a <= 0.01:
            continue
        (bx, by), ang, ln, wd = FINGERS[n]
        x, y = P(bx, by)
        r = math.radians(ang)
        tx, ty = x + math.sin(r) * (ln * HS + 70), y - math.cos(r) * (ln * HS + 70)
        put_icon(L, "check_mark_button", tx, ty, 100 * eb(ph(t, st + 0.25, 0.4)), alpha=a)
    a = eo(ph(t, t_yuz + 0.6, 0.3)) * (1 - eio(ph(t, t_seb - 0.1, 0.3)))
    if a > 0.01:
        (bx, by), ang, ln, wd = FINGERS["ring"]
        x, y = P(bx, by)
        put_icon(L, "cross_mark", x + 40, y - ln * HS - 80, 110 * eb(ph(t, t_yuz + 0.6, 0.4)), alpha=a)
        q = eo(ph(t, t_kald - 0.2, 0.4)) * a
        text_c(L, (540, 300), "KALKMIYOR!", "black", 104, (255, 95, 95), alpha=q, stroke=9, stroke_fill=(10, 8, 6))
    # parmak isim etiketi (hangi parmak kalkıyor)
    for n, st, lab in (("thumb", t_bas, "BAŞPARMAK"), ("index", t_isa, "İŞARET"), ("pinky", t_ser, "SERÇE"),
                       ("ring", t_yuz, "YÜZÜK")):
        en = t_seb - 0.1 if n == "ring" else st + 1.6
        a = eo(ph(t, st, 0.25)) * (1 - eio(ph(t, en, 0.3)))
        if a > 0.01 and n != "ring":
            text_c(L, (540, 300), lab, "black", 96, WHITE, alpha=a, stroke=8, stroke_fill=(10, 8, 6))
        elif a > 0.01 and t < t_kald - 0.2:
            text_c(L, (540, 300), lab + "?", "black", 96, WHITE, alpha=a, stroke=8, stroke_fill=(10, 8, 6))


def captions(L, groups, t):
    for st, en, g in groups:
        if st <= t < en:
            break
    else:
        return
    a = eo(ph(t, st, 0.12))
    f = font("black", round(u(58)))
    texts = [clean(w["w"]) for w in g]
    sp = f.getlength(" ")
    tw = sum(f.getlength(x) for x in texts) + sp * (len(texts) - 1)
    x = W / 2 - tw / 2 + u(60)
    tmp = Image.new("RGBA", (W, round(u(140))), (0, 0, 0, 0))
    d = ImageDraw.Draw(tmp)
    for w, tx in zip(g, texts):
        on = w["s"] - 0.04 <= t < w["e"] + 0.05
        d.text((x, tmp.height / 2), tx, font=f, fill=GOLD if on else WHITE, anchor="lm", stroke_width=round(u(6)),
               stroke_fill=(8, 6, 4))
        x += f.getlength(tx) + sp
    comp(L, set_alpha(tmp, a), 0, u(1520) - tmp.height / 2)


def cta(L, t):
    if t < t_cta - 0.1:
        return
    chip(L, 540, 300, "Kaldırabildin mi?", bg=WHITE, fg=INK, size=56, icon_name="speech_balloon", k="black",
         scale=eb(ph(t, t_cta - 0.1, 0.4)))


def explain_title(L, t, xr):
    if xr <= 0.01 or t >= t_cta - 0.2:
        return
    a = xr * (1 - eio(ph(t, t_cta - 0.5, 0.3)))
    text_c(L, (540, 175), "SEBEBİ", "black", 44, GOLD, alpha=a, stroke=5, stroke_fill=(6, 8, 14))
    text_c(L, (540, 265), "Tendonlar bağlı!", "black", 92, WHITE, alpha=a * eo(ph(t, t_seb + 0.3, 0.5)), stroke=7,
           stroke_fill=(6, 8, 14))


# ---------- Abi ----------
ROZ = Rozet()
OPN, RND = konusma(WORK / "voice_cut.wav", FPS)


def abi(im, t):
    i = min(len(OPN) - 1, int(t * FPS))
    ROZ.draw(im, t, float(OPN[i]))


class Vid(Video):
    def frame(self, t):
        xr = eio(ph(t, t_seb - 0.1, 0.7))
        bg = WOOD if xr < 0.01 else (NAVY if xr > 0.99 else Image.blend(WOOD, NAVY, xr))
        im = bg.convert("RGBA")
        z = 1.0 + 0.04 * clamp(t / TOTAL) + 0.05 * (1 - eo(ph(t, 0, 0.6)))
        im.alpha_composite(hand_layer(t, xr))
        L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        xray_graphics(L, t, xr)
        ftitle(L, t)
        if xr < 0.5:
            marks(L, t)
        explain_title(L, t, xr)
        cta(L, t)
        im.alpha_composite(L)
        if abs(z - 1) > 0.002:
            cw, ch = W / z, H / z
            im = im.crop(((W - cw) / 2, (H - ch) * 0.45, (W + cw) / 2, (H - ch) * 0.45 + ch)).resize((W, H), Image.BICUBIC)
        if t >= 2.0:
            brand(im, 540, 70, size=40)
        C = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        captions(C, self.groups, t)
        im.alpha_composite(C)
        abi(im, t)
        return im.convert("RGB")


if __name__ == "__main__":
    mode = sys.argv[2] if len(sys.argv) > 2 else "render"
    v = Vid([{"start": 0, "end": TOTAL, "draw": lambda *a: None}], words, "", TOTAL, bg=None)
    if mode == "frames":
        for tt in [float(x) for x in sys.argv[3].split(",")]:
            v.frame(tt).save(WORK / f"fr_{tt:05.2f}.png")
    else:
        sfx = [(0.0, "pop"), (t_bas + 0.25, "ding"), (t_isa + 0.25, "ding"), (t_ser + 0.25, "ding"), (t_yuz + 0.6, "pop"),
               (t_seb - 0.1, "whoosh"), (t_isa2 + 0.1, "pop"), (t_onun + 0.3, "pop"), (t_kil - 0.2, "tink"), (t_cta - 0.1, "pop")]
        at.sfx(str(WORK / "sfx.wav"), TOTAL, sfx)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-stream_loop", "2", "-i", str(WORK / "muzik.wav"), "-af",
                        f"atrim=0:{TOTAL:.3f},afade=t=in:d=0.15,afade=t=out:st={TOTAL - 0.5:.3f}:d=0.5",
                        "-ar", "44100", "-ac", "1", str(WORK / "music.wav")], check=True)
        at.final_mix(str(WORK / "voice_cut.wav"), str(WORK / "music.wav"), str(WORK / "sfx.wav"), str(WORK / "mix.m4a"))
        v.render(str(WORK / "mix.m4a"), str(WORK / "video.mp4"))
        print("render bitti", TOTAL, flush=True)
