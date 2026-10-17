"""Konuşan eşya yüzü: göz, kaş, ağız (ses seviyesine göre açılır), göz kırpma, bakış yönü.
Tüm ölçüler piksel; face(...) RGBA katmana çizer."""
import math
from PIL import Image, ImageDraw, ImageFilter

INK = (24, 20, 28)


def _ell(d, cx, cy, rx, ry, **kw):
    d.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], **kw)


def face(L, cx, cy, size, t, level=0.0, mood="normal", look=(0.0, 0.0), blink_seed=0.0, alpha=1.0, lid=(200, 205, 214)):
    """cx, cy: yüz merkezi (px). size: iki göz arası genişlik ölçeği (px).
    level: 0..1 ses seviyesi (ağız açıklığı). mood: normal | angry | tired | offended | happy"""
    if alpha <= 0.02 or size < 10:
        return
    SS = 3
    W = int(size * 2.2)
    H = int(size * 1.9)
    im = Image.new("RGBA", (W * SS, H * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    s = size * SS
    ox, oy = W * SS / 2, H * SS * 0.40
    er = s * 0.20  # göz yarıçapı
    gap = s * 0.30
    # göz kırpma
    bt = (t + blink_seed) % 3.7
    blink = 1.0 if bt > 0.14 else abs(bt - 0.07) / 0.07
    lidamt = {"tired": 0.45, "angry": 0.25, "offended": 0.15}.get(mood, 0.0)
    for side in (-1, 1):
        ex = ox + side * gap
        ey = oy
        open_ = max(0.08, blink * (1 - lidamt))
        ry = er * 1.12 * open_
        _ell(d, ex, ey, er, er * 1.12, fill=(255, 255, 255, 255), outline=INK + (255,), width=int(s * 0.035))
        # göz bebeği
        px = ex + look[0] * er * 0.42 + math.sin(t * 0.9 + side) * er * 0.05
        py = ey + look[1] * er * 0.35
        _ell(d, px, py, er * 0.46, er * 0.50, fill=INK + (255,))
        _ell(d, px - er * 0.14, py - er * 0.18, er * 0.13, er * 0.13, fill=(255, 255, 255, 255))
        # göz kapağı (üstten iner)
        top = ey - er * 1.12
        cover = (er * 1.12 * 2) * (1 - open_)
        if cover > 1:
            lidcol = (0, 0, 0, 0)
            m = Image.new("L", im.size, 0)
            ImageDraw.Draw(m).ellipse([ex - er, ey - er * 1.12, ex + er, ey + er * 1.12], fill=255)
            band = Image.new("L", im.size, 0)
            ImageDraw.Draw(band).rectangle([ex - er - 2, top - 2, ex + er + 2, top + cover], fill=255)
            from PIL import ImageChops
            mm = ImageChops.multiply(m, band)
            skin = Image.new("RGBA", im.size, tuple(lid) + (255,))
            im.paste(skin, (0, 0), mm)
            d = ImageDraw.Draw(im)
            d.line([(ex - er * 0.95, top + cover), (ex + er * 0.95, top + cover)], fill=INK + (255,), width=int(s * 0.035))
            _ell(d, ex, ey, er, er * 1.12, outline=INK + (255,), width=int(s * 0.035))
        # kaşlar
        by = ey - er * 1.45
        bw = er * 0.95
        if mood == "angry":
            p1, p2 = (ex - side * bw * 0.1 - side * 0, by + er * 0.45), (ex + side * bw, by - er * 0.15)
            p1 = (ex - side * bw * 0.25, by + er * 0.40)
        elif mood == "tired":
            p1, p2 = (ex - side * bw * 0.3, by - er * 0.05), (ex + side * bw, by + er * 0.35)
        elif mood == "offended":
            raise_ = er * 0.35 if side == 1 else 0
            p1, p2 = (ex - side * bw * 0.3, by - raise_), (ex + side * bw, by - er * 0.10 - raise_)
        else:
            p1, p2 = (ex - side * bw * 0.3, by), (ex + side * bw, by - er * 0.10)
        wob = math.sin(t * 6) * er * 0.04 * level
        d.line([(p1[0], p1[1] - wob), (p2[0], p2[1] - wob)], fill=INK + (255,), width=int(s * 0.07))
        for p in (p1, p2):
            _ell(d, p[0], p[1] - wob, s * 0.035, s * 0.035, fill=INK + (255,))
    # ağız
    my = oy + er * 2.15
    mw = s * (0.30 + 0.08 * level)
    mh = s * (0.03 + 0.30 * min(1.0, level * 1.3))
    if mh < s * 0.06:  # kapalı ağız: ruh haline göre eğri
        curve = {"angry": -1, "tired": -0.6, "offended": -0.8, "happy": 1}.get(mood, 0.4)
        bb = [ox - mw, my - s * 0.12, ox + mw, my + s * 0.12]
        if curve >= 0:
            d.arc([ox - mw, my - s * 0.15 * curve - s * 0.02, ox + mw, my + s * 0.15 * curve + s * 0.02], 20, 160,
                  fill=INK + (255,), width=int(s * 0.06))
        else:
            k = -curve
            d.arc([ox - mw, my, ox + mw, my + s * 0.24 * k + s * 0.02], 200, 340, fill=INK + (255,), width=int(s * 0.06))
    else:
        d.rounded_rectangle([ox - mw, my - mh / 2, ox + mw, my + mh / 2], radius=min(mw, mh / 2),
                            fill=(90, 18, 30, 255), outline=INK + (255,), width=int(s * 0.04))
        if mh > s * 0.14:  # dil
            tw, th = mw * 0.6, mh * 0.35
            _ell(d, ox, my + mh / 2 - th * 0.8, tw, th, fill=(232, 88, 98, 255))
        d.rounded_rectangle([ox - mw * 0.7, my - mh / 2 + s * 0.02, ox + mw * 0.7, my - mh / 2 + s * 0.07],
                            radius=s * 0.02, fill=(255, 255, 255, 255))
    # yanaklar
    for side in (-1, 1):
        _ell(d, ox + side * gap * 1.45, oy + er * 1.25, er * 0.42, er * 0.26, fill=(255, 120, 120, 70))
    out = im.resize((W, H), Image.LANCZOS)
    if alpha < 0.999:
        a = out.getchannel("A").point(lambda v: int(v * alpha))
        out.putalpha(a)
    sh = Image.new("RGBA", out.size, (0, 0, 0, 0))
    sh.putalpha(out.getchannel("A").point(lambda v: int(v * 0.28)))
    sh = sh.filter(ImageFilter.GaussianBlur(max(1, size * 0.03)))
    x0, y0 = int(cx - W / 2), int(cy - H * 0.40)
    L.alpha_composite(sh, (x0 + int(size * 0.02), y0 + int(size * 0.04))) if 0 <= x0 and 0 <= y0 else None
    from engine import comp
    comp(L, out, x0, y0)
