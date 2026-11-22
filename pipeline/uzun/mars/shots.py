"""Mars bölümü sahne kütüphanesi. Her fonksiyon f(c, t, d, **kw): t sahne içi zaman, d sahne süresi."""
import math, random
from functools import lru_cache
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from vec import *

FD = '/home/claude/shorts-oto/assets/fonts/'


def ease(p):
    p = max(0.0, min(1.0, p)); return p * p * (3 - 2 * p)


def fin(t, a, dur=0.4):
    return ease((t - a) / dur)


@lru_cache(None)
def _font(kind, sz):
    if kind == 'inter':
        f = ImageFont.truetype(FD + 'Inter-Var.ttf', sz)
        try:
            f.set_variation_by_name('SemiBold')
        except Exception:
            pass
        return f
    return ImageFont.truetype(FD + 'BarlowSemiCondensed-SemiBold.ttf', sz)


SIZES = {'num': ('barlow', 88), 'small': ('inter', 36), 'sub': ('inter', 56), 'chap': ('barlow', 88)}


@lru_cache(512)
def sprite(text, kind='small', rgb=L, shadow=True):
    fk, sz = SIZES[kind]
    f = _font(fk, sz)
    l, tp, r, b = f.getbbox(text)
    pad = 14
    w, h = r - l + pad * 2 + 4, b - tp + pad * 2 + 4
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    if shadow:
        sh = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        ImageDraw.Draw(sh).text((pad - l + 3, pad - tp + 3), text, font=f, fill=(0, 0, 0, 115))
        im = sh.filter(ImageFilter.GaussianBlur(3))
    ImageDraw.Draw(im).text((pad - l, pad - tp), text, font=f, fill=tuple(int(v * 255) for v in rgb) + (255,))
    a = np.asarray(im).astype(np.float32)
    al = a[..., 3:4] / 255
    pre = np.concatenate([a[..., 2:3] * al, a[..., 1:2] * al, a[..., 0:1] * al, a[..., 3:4]], axis=2).astype(np.uint8)
    surf = cairo.ImageSurface.create_for_data(bytearray(pre.tobytes()), cairo.FORMAT_ARGB32, w, h, w * 4)
    return surf, pad, sz, (r - l)


def label(c, text, x, y, kind='small', rgb=L, anchor='c', alpha=1.0, dy=0.0):
    """anchor: c (orta), l (sol), r (sağ); y = yazının dikey ortası"""
    if alpha <= 0.01:
        return
    s, pad, sz, tw = sprite(text, kind, rgb)
    w, h = s.get_width(), s.get_height()
    ox = {'c': -w / 2, 'l': -pad, 'r': -w + pad}[anchor]
    c.save(); c.set_source_surface(s, x + ox, y - h / 2 + dy * (1 - alpha)); c.paint_with_alpha(alpha); c.restore()


def line_draw(c, pts, p, width=4, rgb=L, alpha=1.0, dash=None):
    """polyline'ı p (0..1) oranında çizer"""
    if p <= 0:
        return
    segs = [math.dist(a, b) for a, b in zip(pts, pts[1:])]
    tot = sum(segs) * p
    c.save(); c.set_line_width(width); c.set_line_cap(cairo.LINE_CAP_ROUND); c.set_line_join(cairo.LINE_JOIN_ROUND)
    if dash:
        c.set_dash(dash)
    c.move_to(*pts[0])
    for (a, b), sl in zip(zip(pts, pts[1:]), segs):
        if tot <= 0:
            break
        if sl <= tot:
            c.line_to(*b); tot -= sl
        else:
            q = tot / sl; c.line_to(a[0] + (b[0] - a[0]) * q, a[1] + (b[1] - a[1]) * q); tot = 0
    col(c, rgb, alpha); c.stroke(); c.restore()


def arrow(c, x0, y0, x1, y1, p, rgb=L, width=4, bend=0.25):
    """ince, uçları yuvarlak, kendini çizen kavisli ok"""
    mx, my = (x0 + x1) / 2, (y0 + y1) / 2
    nx, ny = -(y1 - y0) * bend, (x1 - x0) * bend
    pts = [((1 - s) ** 2 * x0 + 2 * (1 - s) * s * (mx + nx) + s * s * x1, (1 - s) ** 2 * y0 + 2 * (1 - s) * s * (my + ny) + s * s * y1)
           for s in np.linspace(0, 1, 40)]
    line_draw(c, pts, p, width, rgb)
    if p > 0.95:
        a = math.atan2(pts[-1][1] - pts[-3][1], pts[-1][0] - pts[-3][0])
        c.save(); c.set_line_width(width); c.set_line_cap(cairo.LINE_CAP_ROUND)
        for da in (2.6, -2.6):
            c.move_to(x1, y1); c.line_to(x1 + 22 * math.cos(a + da), y1 + 22 * math.sin(a + da))
        col(c, rgb); c.stroke(); c.restore()


def blink_at(t, period=3.4, off=0.0):
    return 1.0 if ((t + off) % period) < 0.12 else 0.0


def particles(c, t, seed, n, rgb, amin=0.1, amax=0.35, vx=(15, 40), vy=(0, 0), y0=0, y1=H, rmin=1.5, rmax=3.5):
    rnd = random.Random(seed)
    for _ in range(n):
        x0, yy = rnd.uniform(0, W), rnd.uniform(y0, y1)
        x = (x0 + t * rnd.uniform(*vx)) % (W + 40) - 20
        y = (yy + t * rnd.uniform(*vy) - y0) % (y1 - y0) + y0
        col(c, rgb, rnd.uniform(amin, amax)); c.arc(x, y, rnd.uniform(rmin, rmax), 0, 6.283); c.fill()


# ============================================================ ortak arka planlar
def bg_mars_day(c, seed=1, hz=760, sun=(1950, 300), haze=0.0, far_volcano=False):
    c.rectangle(0, 0, W, H); c.set_source(vgrad(c, 0, hz + 140, [(0, SKY_DAY_TOP), (1, SKY_DAY_LOW)])); c.fill()
    if sun:
        c.set_source(rgrad(c, sun[0], sun[1], 0, 260, [(0, L, 0.55), (1, L, 0)])); c.paint()
        c.arc(sun[0], sun[1], 44, 0, 6.283); col(c, mix(L, WH, 0.5)); c.fill()
    far = ridge(seed * 3, hz, 70, wl=1400); fill_ridge(c, far, mix(G1, SKY_DAY_LOW, 0.45))
    if far_volcano:
        c.move_to(150, hz + 20); c.curve_to(450, hz - 110, 650, hz - 160, 820, hz - 160); c.curve_to(1000, hz - 160, 1200, hz - 100, 1500, hz + 30)
        c.close_path(); col(c, mix(G1, SKY_DAY_LOW, 0.55)); c.fill()
    mid = ridge(seed * 7, hz + 100, 40, wl=1100); fill_ridge(c, mid, G1)
    near = ridge(seed * 11, hz + 200, 30, wl=1600); fill_ridge(c, near, G2)
    return near


def fg_mars(c, seed=1, y=1180, rocks=True, colr=G3):
    front = ridge(seed * 21, y, 25, wl=2000); fill_ridge(c, front, colr)
    if rocks:
        rnd = random.Random(seed)
        for k in range(5):
            x = rnd.uniform(0, W); rock(c, x, ridge_y(front, x) + 18, rnd.uniform(30, 90), mix(colr, D, 0.3), seed * 10 + k)
    return front


def bg_space(c, seed=1, n=320):
    col(c, mix(D, BK, 0.45)); c.paint()
    c.set_source(rgrad(c, W * 0.3, H * 0.4, 0, W * 0.8, [(0, mix(D, M, 0.12)), (1, mix(D, BK, 0.5))])); c.paint()
    stars(c, seed, n, H, 0.9)


def bg_ship(c, light=1.0):
    wall = mix(D, M, 0.18 * light + 0.04)
    col(c, wall); c.paint()
    for x in range(-80, W + 200, 420):
        rrect(c, x + 14, 70, 392, 560, 26); col(c, mix(wall, M, 0.1 * light)); c.fill()
        rrect(c, x + 14, 660, 392, 700, 26); col(c, mix(wall, M, 0.07 * light)); c.fill()
    c.rectangle(0, 1300, W, 140); col(c, mix(D, M, 0.1)); c.fill()


def bg_hab(c, light=1.0, warm=0.0):
    """habitat içi: kavisli duvar, zemin"""
    wall = mix(mix(D, M, 0.28), A, 0.06 + warm * 0.1)
    wall = mix(D, wall, light)
    col(c, wall); c.paint()
    for k in range(7):
        x = 180 + k * 380
        c.move_to(x, 0); c.curve_to(x - 40, 400, x - 40, 900, x, 1150); c.set_line_width(6); col(c, mix(wall, D, 0.25)); c.stroke()
    c.rectangle(0, 1150, W, 300); col(c, mix(wall, D, 0.35)); c.fill()
    c.rectangle(0, 1150, W, 10); col(c, mix(wall, L, 0.12)); c.fill()


def bg_night(c, seed=2, hz=930, glow=None):
    c.rectangle(0, 0, W, H)
    c.set_source(vgrad(c, 0, hz + 50, [(0, mix(D, BK, 0.3)), (0.55, D), (1, mix(D, M, 0.4))])); c.fill()
    stars(c, seed, 260, hz - 100)
    if glow:
        sx, sy = glow
        c.set_source(rgrad(c, sx, sy, 0, 620, [(0, mix(M, L, 0.5), 0.9), (0.35, M, 0.45), (1, M, 0)])); c.paint()
    far = ridge(seed * 31, hz, 45, wl=1300); fill_ridge(c, far, mix(G5, M, 0.25))
    mid = ridge(seed * 37, hz + 80, 35, wl=1500); fill_ridge(c, mid, mix(G5, D, 0.35))
    return mid


def bg_earth_day(c, hz=900):
    c.rectangle(0, 0, W, H); c.set_source(vgrad(c, 0, hz, [(0, mix(M, D, 0.05)), (1, mix(M, L, 0.55))])); c.fill()
    c.set_source(rgrad(c, 2050, 260, 0, 300, [(0, L, 0.7), (1, L, 0)])); c.paint()
    c.arc(2050, 260, 60, 0, 6.283); col(c, mix(L, WH, 0.6)); c.fill()
    for (cx, cy, s) in [(500, 260, 1.0), (1500, 180, 0.7), (2300, 420, 0.8)]:
        for dx, dy, r in [(-60, 10, 50), (0, -15, 70), (70, 10, 50)]:
            c.arc(cx + dx * s, cy + dy * s, r * s, 0, 6.283)
        col(c, mix(L, WH, 0.4), 0.9); c.fill()
    g1, g2 = mix(M, D, 0.35), mix(M, D, 0.5)
    far = ridge(91, hz, 40, wl=1500); fill_ridge(c, far, mix(g1, L, 0.25))
    near = ridge(93, hz + 140, 30, wl=1800); fill_ridge(c, near, g1)
    return near


# ============================================================ 0 — açılış
def door(c, t, d, **kw):
    c.rectangle(0, 0, W, H); c.set_source(vgrad(c, 0, H, [(0, mix(M, L, 0.35)), (1, mix(M, L, 0.6))])); c.fill()
    c.rectangle(0, 0, 1500, H); col(c, mix(L, A, 0.12)); c.fill()                        # ev duvarı
    for y in range(80, 1240, 90):
        c.rectangle(0, y, 1500, 3); col(c, mix(L, A, 0.2)); c.fill()
    c.rectangle(0, 1240, W, 200); col(c, mix(M, D, 0.45)); c.fill()                      # zemin
    rrect(c, 700, 380, 520, 860, 16); col(c, mix(D, A, 0.35)); c.fill()                  # kapı boşluğu
    c.rectangle(720, 400, 480, 840); col(c, mix(D, A, 0.15)); c.fill()
    op = fin(t, 0.3, 0.8)
    c.save(); c.move_to(720, 400); c.line_to(720 + 470 * (1 - op * 0.75), 400 + 30 * op); c.line_to(720 + 470 * (1 - op * 0.75), 1240 - 30 * op)
    c.line_to(720, 1240); c.close_path(); col(c, mix(A, D, 0.2)); c.fill(); c.restore()
    c.arc(720 + 420 * (1 - op * 0.75), 830, 14, 0, 6.283); col(c, L); c.fill()
    character(c, 960, 1240, 1.25, t, pose='stand', helmet=False, outfit='shirt', blink=blink_at(t), brow=0.8 * fin(t, 1.2, 0.3),
              look=(1, 0), smile=0.2 + 0.6 * fin(t, 2.5, 0.5))
    # uzatılan bilet (eldivenli el sağdan)
    ex = 2600 - 900 * fin(t, 0.6, 0.9)
    col(c, SUIT); capsule(c, ex + 400, 820, ex + 60, 800, 90)
    c.arc(ex + 40, 800, 52, 0, 6.283); col(c, SUIT_DK); c.fill()
    c.save(); c.translate(ex - 30, 760); c.rotate(-0.12)
    rrect(c, -170, -60, 240, 120, 14); col(c, L); c.fill()
    c.rectangle(-170, -60, 34, 120); col(c, A); c.fill()
    c.restore()


def ticket(c, t, d, **kw):
    col(c, mix(D, M, 0.22)); c.paint()
    c.set_source(rgrad(c, W / 2, H / 2, 0, 1400, [(0, mix(D, M, 0.35)), (1, mix(D, BK, 0.2))])); c.paint()
    c.save(); c.translate(W / 2, H * 0.47); c.rotate(-0.05 + 0.02 * math.sin(t * 0.6))
    rrect(c, -560 + 10, -230 + 14, 1120, 460, 34); col(c, BK, 0.3); c.fill()
    rrect(c, -560, -230, 1120, 460, 34); col(c, L); c.fill()
    c.rectangle(-560, -230, 150, 460); col(c, A); c.fill()
    for k in range(9):
        c.arc(300, -200 + k * 50, 7, 0, 6.283); col(c, mix(L, M, 0.5)); c.fill()
    planet(c, -485, 0, 48, 'mars', light=(0.5, -0.4))
    label(c, 'BİLET', -360, -140, 'small', mix(D, M, 0.2), 'l', 1, )
    label(c, 'MARS', -360, -20, 'num', D, 'l', fin(t, 0.0, 0.01))
    label(c, 'TEK YÖN', -360, 110, 'small', A, 'l', fin(t, kw.get('ty', 0.9), 0.4), dy=12)
    label(c, 'Kalkış: 1', 430, -60, 'small', mix(D, M, 0.2), 'c', 1)
    label(c, 'Koltuk: 1A', 430, 30, 'small', mix(D, M, 0.2), 'c', 1)
    c.restore()


def space_rocket(c, t, d, earth=True, **kw):
    bg_space(c, 4)
    if earth:
        planet(c, 380, 1350, 520, 'earth', light=(-0.6, -0.5), glow=0.15)
    p = t / max(d, 1)
    rocket(c, 900 + 1100 * p, 900 - 520 * p, 0.85, flame=1.0, t=t, rot=1.05)


def helmet_air(c, t, d, **kw):
    near = bg_mars_day(c, 5, hz=700, sun=(2200, 240))
    fg_mars(c, 5, 1250)
    character(c, 1280, 1700, 2.3, t, pose='stand', blink=blink_at(t), look=(-0.5, -0.3), brow=0.3)
    rnd = random.Random(3)
    for k in range(10):
        x = (rnd.uniform(200, 2400) + t * rnd.uniform(10, 30)) % W
        y = rnd.uniform(150, 1000) - t * rnd.uniform(5, 15)
        a = 0.55 * fin(t, 0.2 + k * 0.1, 0.5)
        c.arc(x, y, 18, 0, 6.283); col(c, L, a * 0.5); c.fill()
        c.arc(x - 34, y, 13, 0, 6.283); col(c, mix(L, M, 0.4), a * 0.5); c.fill()
        c.arc(x + 34, y, 13, 0, 6.283); col(c, mix(L, M, 0.4), a * 0.5); c.fill()


def storm_far(c, t, d, **kw):
    near = bg_mars_day(c, 9, sun=(1900, 260))
    dust_wall(c, 1500 - t * 60, 900, 0.95, t)
    front = fg_mars(c, 9)
    character(c, 760, ridge_y(near, 760) + 200, 0.95, t, pose='stand', flip=True, look=(1, 0), blink=blink_at(t))
    particles(c, t, 2, 90, L, 0.08, 0.3, vx=(-160, -60), y0=200, y1=1300)


def moons_fast(c, t, d, **kw):
    mid = bg_night(c, 6, hz=980)
    p = (t / max(d, 0.1))
    for k in range(2):
        q = (p * 1.4 + k * 0.5) % 1.0
        x = W * (1.05 - 1.1 * q); y = 950 - math.sin(q * math.pi) * 650
        c.save(); c.translate(x, y); c.rotate(0.4); c.scale(40, 28); c.arc(0, 0, 1, 0, 6.283); c.restore()
        col(c, mix(L, M, 0.35), 0.9 if 0.03 < q < 0.97 else 0.3); c.fill()
    front = ridge(12, 1150, 22, wl=1900); fill_ridge(c, front, mix(G5, D, 0.55))
    dome(c, 1900, ridge_y(front, 1900) + 30, 190)


def journey_map(c, t, d, **kw):
    bg_space(c, 8, 220)
    ex, ey, mx, my = 520, 900, 2050, 560
    planet(c, ex, ey, 120, 'earth', glow=0.3)
    planet(c, mx, my, 90, 'mars', glow=0.3)
    pts = [((1 - s) ** 2 * ex + 2 * (1 - s) * s * 1250 + s * s * mx, (1 - s) ** 2 * ey + 2 * (1 - s) * s * 260 + s * s * my) for s in np.linspace(0.1, 0.9, 60)]
    p = fin(t, 0.3, max(1.0, d - 1.0))
    line_draw(c, pts, 1.0, 4, M, 0.35, dash=[14, 16])
    line_draw(c, pts, p, 4, L, 0.9)
    i = min(len(pts) - 2, int(p * (len(pts) - 1)))
    a = math.atan2(pts[i + 1][1] - pts[i][1], pts[i + 1][0] - pts[i][0])
    rocket(c, pts[i][0], pts[i][1], 0.22, flame=0.8, t=t, rot=a + math.pi / 2)
    if kw.get('lab'):
        label(c, kw['lab'], 1250, 300, 'num', L, 'c', fin(t, 0.6), dy=14)
    if kw.get('lab2'):
        label(c, kw['lab2'], 1250, 400, 'small', M, 'c', fin(t, 0.9), dy=14)


def night_sit(c, t, d, earth_arrow=False, **kw):
    mid = bg_night(c, 2, glow=(1820, 930) if kw.get('glow', True) else None)
    c.save(); c.translate(820, 300); c.rotate(0.4); c.scale(34, 24); c.arc(0, 0, 1, 0, 6.283); c.restore()
    col(c, mix(L, M, 0.35)); c.fill()
    c.arc(1240, 190, 9, 0, 6.283); col(c, mix(L, M, 0.25)); c.fill()
    tw = 0.85 + 0.15 * math.sin(t * 3)
    c.set_source(rgrad(c, 1560, 640, 0, 40, [(0, M, 0.6 * tw), (1, M, 0)])); c.paint()
    c.arc(1560, 640, 6.5, 0, 6.283); col(c, mix(M, WH, 0.5)); c.fill()
    if earth_arrow:
        arrow(c, 1340, 440, 1530, 615, fin(t, 0.6, 0.5), L, 4)
        label(c, 'Dünya', 1290, 400, 'small', L, 'c', fin(t, 1.0))
    if kw.get('glow', True):
        c.arc(1820, 930, 22, 0, 6.283); col(c, mix(L, WH, 0.6)); c.fill()
    hx_ = 620; dome(c, hx_, ridge_y(mid, hx_) + 30, 260)
    front = ridge(41, 1140, 22, wl=1900); fill_ridge(c, front, mix(G5, D, 0.6))
    rock(c, 1225, ridge_y(front, 1300) + 6, 92, mix(G5, M, 0.2), 8, light=0.12)
    character(c, 1205, ridge_y(front, 1300) - 18, 1.0, t, pose='sit', look=(1, -1), blink=blink_at(t, 3.6), smile=0.5)


# ============================================================ 1 — seçildin
def training_room(c, t, d, **kw):
    bg_hab(c, 1.0)
    rrect(c, 1250, 180, 1100, 700, 20); col(c, mix(D, M, 0.12)); c.fill()                # pano
    p = fin(t, 0.3, 1.5)
    ex, mx = 1420, 2180
    planet(c, ex, 530, 70, 'earth'); planet(c, mx, 530, 50, 'mars')
    line_draw(c, [(ex + 90, 530), (mx - 70, 530)], p, 4, L, 0.85, dash=[16, 14])
    label(c, 'milyonlarca km', (ex + mx) / 2, 460, 'small', L, 'c', fin(t, 1.2))
    character(c, 760, 1260, 1.35, t, pose='point', helmet=False, outfit='shirt', look=(1, -0.3), blink=blink_at(t), mouth=0)


def roles(c, t, d, **kw):
    bg_hab(c, 1.0, warm=0.3)
    character(c, W / 2, 1270, 1.4, t, pose='stand', helmet=False, outfit='shirt', blink=blink_at(t), smile=0.9)
    fr = d / 4
    items = [(820, 520, 'doktor'), (1280, 300, 'tamirci'), (1740, 520, 'çiftçi')]
    for k, (x, y, nm) in enumerate(items):
        a = fin(t, 0.6 + k * fr, 0.4)
        if a <= 0:
            continue
        c.save(); c.translate(x, y + 15 * (1 - a))
        c.arc(0, 0, 120, 0, 6.283); col(c, mix(D, M, 0.25), a * 0.85); c.fill()
        if k == 0:
            rrect(c, -22, -70, 44, 140, 10); col(c, L, a); c.fill(); rrect(c, -70, -22, 140, 44, 10); col(c, L, a); c.fill()
        elif k == 1:
            c.save(); c.rotate(0.8); rrect(c, -16, -80, 32, 130, 12); col(c, L, a); c.fill()
            c.arc(0, -80, 40, 0, 6.283); col(c, L, a); c.fill(); rrect(c, -14, -125, 28, 50, 4); col(c, mix(D, M, 0.25)); c.fill(); c.restore()
        else:
            c.save(); c.translate(0, 60); plant(c, 0, 0, 1.2, 1.0, 'sprout'); c.restore()
            rrect(c, -55, 40, 110, 50, 12); col(c, A, a); c.fill()
        c.restore()
        label(c, nm, x, y + 165, 'small', L, 'c', a)


def pool(c, t, d, **kw):
    c.rectangle(0, 0, W, H); c.set_source(vgrad(c, 0, H, [(0, mix(M, L, 0.15)), (1, mix(M, D, 0.55))])); c.fill()
    for k in range(6):
        x = (k * 520 + t * 40) % (W + 600) - 300
        c.move_to(x, 0); c.line_to(x + 160, 0); c.line_to(x - 200, H); c.line_to(x - 420, H); c.close_path(); col(c, L, 0.06); c.fill()
    c.rectangle(0, 1220, W, 220); col(c, mix(M, D, 0.62)); c.fill()
    for x in range(0, W, 160):
        c.rectangle(x, 1220, 4, 220); col(c, mix(M, D, 0.5)); c.fill()
    rrect(c, 1500, 560, 520, 660, 18); col(c, mix(M, D, 0.4)); c.fill()                 # maket modül
    for k in range(3):
        rrect(c, 1560, 620 + k * 180, 400, 120, 12); col(c, mix(M, D, 0.25)); c.fill()
    character(c, 1220, 1050 + 20 * math.sin(t * 0.8), 1.25, t, pose='reach', rot=0.2, blink=blink_at(t), look=(1, 0))
    particles(c, t, 7, 40, L, 0.2, 0.5, vx=(-4, 4), vy=(-60, -30), y0=0, y1=1300, rmin=4, rmax=11)


def small_room(c, t, d, **kw):
    bg_hab(c, 0.95, warm=0.2)
    rrect(c, 1700, 250, 300, 240, 12); col(c, L); c.fill()                                 # takvim
    c.rectangle(1700, 250, 300, 50); col(c, A); c.fill()
    for i in range(4):
        for j in range(5):
            x, y = 1725 + j * 55, 320 + i * 42
            col(c, mix(D, M, 0.3)); c.rectangle(x, y, 30, 20); c.fill()
            if (i * 5 + j) < 13:
                col(c, A); c.set_line_width(4); c.move_to(x, y); c.line_to(x + 30, y + 20); c.stroke()
    rrect(c, 700, 960, 1200, 50, 12); col(c, mix(L, M, 0.4)); c.fill()                     # masa
    col(c, mix(M, D, 0.3)); capsule(c, 1300, 1010, 1300, 1150, 30)
    for k, (x, st, fl) in enumerate([(850, CREW1, False), (1300, ABI, False), (1750, CREW2, True)]):
        character(c, x, 1150, 1.0, t, pose='stand', helmet=False, outfit='shirt', st=st, flip=fl, blink=blink_at(t, 3.1 + k * 0.4, k),
                  look=(0.6 if k == 0 else -0.6, 0), arms=(-1.0, 1.0), smile=0.3)
    for x in (900, 1300, 1700):
        c.save(); c.translate(x, 950); c.scale(70, 16); c.arc(0, 0, 1, 0, 6.283); c.restore(); col(c, L); c.fill()


def suit_reveal(c, t, d, **kw):
    col(c, mix(D, BK, 0.2)); c.paint()
    c.move_to(1300 - 120, 0); c.line_to(1300 + 120, 0); c.line_to(1300 + 520, 1260); c.line_to(1300 - 520, 1260); c.close_path()
    g = cairo.LinearGradient(0, 0, 0, 1260); g.add_color_stop_rgba(0, *L, 0.28); g.add_color_stop_rgba(1, *L, 0.05); c.set_source(g); c.fill()
    c.save(); c.translate(1300, 1270); c.scale(520, 60); c.arc(0, 0, 1, 0, 6.283); c.restore(); col(c, L, 0.12); c.fill()
    col(c, SUIT_DK); capsule(c, 1300, 1270, 1300, 480, 22)
    # boş giysi (kask boş)
    c.save(); character(c, 1300, 1240, 1.45, t, pose='stand', helmet=True, st=dict(ABI, beard=False, cap=False, skin=mix(M, D, 0.55), hairc=mix(M, D, 0.55)),
                         eyes_closed=False, blink=1.0, smile=0.0)
    c.restore()
    c.save(); c.translate(1300, 1240 - 5.25 * 60 * 1.45); c.arc(0, 0, 60 * 1.45 * 1.02, 0, 6.283); col(c, mix(M, D, 0.55)); c.fill(); c.restore()
    c.save(); c.translate(1300, 1240 - 5.25 * 60 * 1.45)
    c.set_line_cap(cairo.LINE_CAP_ROUND); c.arc(0, 0, 1.24 * 60 * 1.45, math.radians(200), math.radians(255)); c.set_line_width(10); col(c, WH, 0.7); c.stroke(); c.restore()
    character(c, 520, 1260, 1.2, t, pose='stand', helmet=False, outfit='shirt', look=(1, -0.5), blink=blink_at(t), brow=0.5, smile=0.9)
    if kw.get('labels'):
        for k, (nm, y) in enumerate([('hava', 640), ('ısıtma', 800), ('soğutma', 960)]):
            a = fin(t, 0.8 + k * 0.7, 0.4)
            line_draw(c, [(1480, y), (1700, y)], a, 3, M)
            label(c, nm, 1720, y, 'small', L, 'l', a)


# ============================================================ 2 — yolculuk
def launch(c, t, d, ignite=0.0, **kw):
    c.rectangle(0, 0, W, H); c.set_source(vgrad(c, 0, 1100, [(0, mix(D, M, 0.25)), (1, mix(M, A, 0.35))])); c.fill()
    c.set_source(rgrad(c, 2100, 1050, 0, 700, [(0, mix(A, L, 0.4), 0.6), (1, A, 0)])); c.paint()
    c.rectangle(0, 1100, W, 340); col(c, mix(D, M, 0.25)); c.fill()
    ig = fin(t, ignite, 0.4) if ignite is not None else 0
    lift = max(0.0, t - ignite - 1.2) if ignite is not None else 0
    up = 40 * lift * lift
    sh = (6 * math.sin(t * 60) * ig) if ig > 0 else 0
    col(c, mix(D, M, 0.35))                                                               # kule
    c.rectangle(1500, 380, 60, 720); c.fill()
    for y in range(400, 1100, 70):
        c.move_to(1500, y); c.line_to(1560, y + 70); c.set_line_width(5); c.stroke()
    rocket(c, 1280 + sh, 520 - up, 1.1, flame=ig, t=t)
    if ig > 0:
        rnd = random.Random(1)
        for k in range(26):
            x = 1280 + rnd.uniform(-1, 1) * (200 + 500 * ig) * (0.4 + 0.6 * min(1, (t - ignite) / 2))
            r = rnd.uniform(70, 170) * (0.5 + 0.5 * ig)
            c.arc(x, 1100 - rnd.uniform(0, 120), r, 0, 6.283); col(c, mix(L, M, rnd.uniform(0.1, 0.5)), 0.85 * ig); c.fill()


def cabin_seat(c, t, d, shake=1.0, **kw):
    sh = shake * (5 * math.sin(t * 57) + 3 * math.sin(t * 31))
    c.save(); c.translate(sh, sh * 0.5)
    bg_ship(c, 0.9)
    c.save(); c.translate(1200, 1240); c.rotate(-1.2)
    rrect(c, -40, -520, 230, 560, 40); col(c, mix(M, D, 0.4)); c.fill()
    c.restore()
    character(c, 1050, 1180, 1.35, t, pose='sit', rot=-0.0, blink=blink_at(t), brow=0.8 * shake, smile=0.0 if shake > 0.3 else 0.8,
              look=(0.3, -0.5))
    c.restore()


def ship_float(c, t, d, **kw):
    bg_ship(c)
    wx, wy, wr = 1700, 560, 330
    window(c, wx, wy, wr, t, kw.get('earth_r', 62), kind=kw.get('kind', 'earth'))
    rnd = random.Random(4)
    for k in range(9):
        bx = 700 + rnd.uniform(-260, 380) + 25 * math.sin(t * 0.8 + k)
        by = 760 + rnd.uniform(-320, 240) + 20 * math.cos(t * 0.7 + k * 1.7)
        br = rnd.uniform(10, 26)
        c.arc(bx, by, br, 0, 6.283); col(c, mix(M, L, 0.25), 0.85); c.fill()
        c.arc(bx - br * 0.3, by - br * 0.3, br * 0.28, 0, 6.283); col(c, WH, 0.8); c.fill()
    pxx, pyy = 1060 + 15 * math.sin(t * 0.9), 980 + 12 * math.cos(t * 0.8)
    c.save(); c.translate(pxx, pyy); c.rotate(0.15 + 0.05 * math.sin(t)); c.scale(110, 26); c.arc(0, 0, 1, 0, 6.283); c.restore(); col(c, L); c.fill()
    for k, (ox, oy) in enumerate([(-40, -90), (30, -130), (85, -70)]):
        c.arc(pxx + ox + 8 * math.sin(t + k), pyy + oy + 6 * math.cos(t * 1.2 + k), 22, 0, 6.283); col(c, A if k != 1 else mix(M, D, 0.1)); c.fill()
    character(c, 720, 1080 + 18 * math.sin(t * 0.9), 1.15, t, pose='float', rot=-0.22 + 0.04 * math.sin(t * 0.6), helmet=False,
              look=(1, -0.6), smile=1.0, brow=0.6, blink=blink_at(t))


def window(c, wx, wy, wr, t, er=62, kind='earth'):
    c.arc(wx, wy, wr + 40, 0, 6.283); col(c, mix(M, D, 0.25)); c.fill()
    c.arc(wx, wy, wr + 14, 0, 6.283); col(c, mix(M, L, 0.15)); c.fill()
    c.save(); c.arc(wx, wy, wr, 0, 6.283); c.clip()
    col(c, mix(D, BK, 0.45)); c.paint()
    rnd = random.Random(9)
    for _ in range(140):
        x, y = wx + rnd.uniform(-wr, wr), wy + rnd.uniform(-wr, wr)
        col(c, L, rnd.uniform(0.3, 0.95)); c.arc(x, y, rnd.choice([1.4, 2, 2.6, 3.2]), 0, 6.283); c.fill()
    if er > 0:
        if er < 8:
            c.set_source(rgrad(c, wx + 60, wy + 40, 0, 30, [(0, M if kind == 'earth' else A, 0.6), (1, M, 0)])); c.paint()
            c.arc(wx + 60, wy + 40, max(er, 4), 0, 6.283); col(c, mix(M if kind == 'earth' else A, WH, 0.4)); c.fill()
        else:
            planet(c, wx + 60, wy + 40, er, kind, glow=0.4)
    c.restore()
    c.arc(wx, wy, wr - 30, math.radians(200), math.radians(240)); c.set_line_width(14); c.set_line_cap(cairo.LINE_CAP_ROUND)
    col(c, WH, 0.18); c.stroke()


def window_view(c, t, d, er0=150, er1=8, kind='earth', **kw):
    bg_ship(c, 0.9)
    p = ease(t / max(d, 0.1))
    er = er0 + (er1 - er0) * p
    window(c, 1500, 640, 470, t, er, kind)
    character(c, 640, 1300, 1.35, t, pose='stand', helmet=False, look=(1, -0.4), blink=blink_at(t), arms=(-0.3, 1.2))


def sleep_bag(c, t, d, **kw):
    bg_ship(c, 0.55)
    for k, x in enumerate((900, 1600)):
        rrect(c, x - 150, 230, 300, 950, 120); col(c, mix(M, D, 0.25 + 0.1 * k)); c.fill()
        for y in (420, 700, 980):
            c.rectangle(x - 160, y, 320, 18); col(c, mix(D, M, 0.1)); c.fill()
    c.save(); c.translate(900, 330 + 8 * math.sin(t * 0.7))
    head(c, 75, eyes_closed=True, smile=0.4); c.restore()
    c.save(); c.translate(1600, 330 + 8 * math.sin(t * 0.6 + 1))
    head(c, 70, eyes_closed=True, smile=0.3, st=CREW2); c.restore()
    for k in range(3):
        a = (t * 0.6 + k * 0.33) % 1
        label(c, 'z', 1010 + a * 80 + k * 10, 230 - a * 140, 'small', L, 'c', math.sin(a * math.pi) * 0.8)


def treadmill(c, t, d, **kw):
    bg_ship(c)
    rrect(c, 800, 1140, 1000, 80, 30); col(c, mix(M, D, 0.4)); c.fill()
    for k in range(10):
        x = 820 + ((k * 100 - t * 300) % 960)
        c.rectangle(x, 1150, 8, 60); col(c, mix(M, D, 0.25)); c.fill()
    for sx in (-1, 1):
        col(c, mix(M, L, 0.1)); capsule(c, 1300 + sx * 120, 560, 1300 + sx * 420, 1150, 10)
    character(c, 1300, 1140, 1.35, t, pose='walk', walk=t * 1.6, helmet=False, blink=blink_at(t), brow=0.4)
    if kw.get('lab'):
        label(c, kw['lab'], 2130, 520, 'num', L, 'c', fin(t, 0.5), dy=14)
        label(c, 'her gün', 2130, 620, 'small', M, 'c', fin(t, 0.8), dy=14)


def lights_dim(c, t, d, **kw):
    lv = 0.55 + 0.45 * (0.5 + 0.5 * math.cos(t / max(d, 1) * 2 * math.pi))
    bg_ship(c, lv)
    for x in (500, 1300, 2100):
        rrect(c, x - 180, 40, 360, 30, 12); col(c, mix(L, A, 0.2), lv); c.fill()
        c.move_to(x - 180, 70); c.line_to(x + 180, 70); c.line_to(x + 380, 900); c.line_to(x - 380, 900); c.close_path()
        col(c, L, 0.08 * lv); c.fill()
    window(c, 2150, 600, 230, t, 0)
    character(c, 1100, 1250, 1.3, t, pose='stand', helmet=False, look=(-0.5, -1), blink=blink_at(t), eyes_closed=lv < 0.62, smile=0.4)


# ============================================================ 3 — banyo
def wipes(c, t, d, **kw):
    bg_ship(c)
    character(c, 1150, 1250, 1.45, t, pose='stand', helmet=False, arms=(-2.6 + 0.2 * math.sin(t * 4), 0.4), blink=blink_at(t), eyes_closed=True, smile=0.8)
    c.save(); c.translate(1150 - 120 + 40 * math.sin(t * 4), 1250 - 5.6 * 60 * 1.45); c.rotate(0.3 * math.sin(t * 4))
    rrect(c, -90, -50, 180, 100, 20); col(c, mix(L, M, 0.15)); c.fill(); c.restore()
    particles(c, t, 11, 22, mix(M, L, 0.4), 0.4, 0.8, vx=(-10, 10), vy=(-15, 15), y0=300, y1=900, rmin=6, rmax=14)
    rrect(c, 1700, 600, 200, 300, 30); col(c, L); c.fill(); rrect(c, 1750, 540, 100, 80, 16); col(c, A); c.fill()


def fan_device(c, t, d, **kw):
    bg_ship(c)
    rrect(c, 1050, 520, 520, 700, 40); col(c, mix(M, D, 0.35)); c.fill()
    c.arc(1310, 760, 150, 0, 6.283); col(c, mix(D, M, 0.15)); c.fill()
    c.save(); c.translate(1310, 760); c.rotate(t * 9)
    for k in range(5):
        c.rotate(2 * math.pi / 5); c.save(); c.translate(0, -70); c.scale(30, 70); c.arc(0, 0, 1, 0, 6.283); c.restore(); col(c, mix(M, L, 0.3)); c.fill()
    c.restore()
    for k in range(6):
        a = (t * 0.25 + k / 6) % 1
        ang = k * 1.1 + a * 6
        r = 650 * (1 - a)
        c.arc(1310 + r * math.cos(ang), 760 + r * math.sin(ang) * 0.6, 10 + 6 * (1 - a), 0, 6.283); col(c, L, 0.5 * (1 - a)); c.fill()
    obj = [(520, 420, 0), (2050, 380, 1), (2200, 900, 2), (420, 950, 3)]
    for x, y, k in obj:
        c.save(); c.translate(x + 30 * math.sin(t + k), y + 20 * math.cos(t * 0.8 + k)); c.rotate(t * 0.3 + k)
        if k % 2:
            rrect(c, -50, -30, 100, 60, 10); col(c, L); c.fill()
        else:
            c.arc(0, 0, 35, 0, 6.283); col(c, A if k == 0 else M); c.fill()
        c.restore()


def water_cycle(c, t, d, **kw):
    col(c, mix(D, M, 0.15)); c.paint()
    cx, cy, R = 1280, 660, 380
    pts = [(cx + R * math.cos(a), cy + R * 0.75 * math.sin(a)) for a in np.linspace(-math.pi / 2, 1.5 * math.pi, 120)]
    line_draw(c, pts, fin(t, 0.2, 1.0), 4, M, 0.9)
    nodes = [(-math.pi / 2, 'ter ve idrar'), (math.pi / 6, 'temizleme'), (5 * math.pi / 6, 'içme suyu')]
    for k, (a, nm) in enumerate(nodes):
        x, y = cx + R * math.cos(a), cy + R * 0.75 * math.sin(a)
        al = fin(t, 0.5 + k * 0.5)
        c.arc(x, y, 64, 0, 6.283); col(c, mix(D, M, 0.35), al); c.fill()
        c.move_to(x, y - 34); c.curve_to(x + 30, y + 4, x + 24, y + 34, x, y + 34); c.curve_to(x - 24, y + 34, x - 30, y + 4, x, y - 34)
        col(c, mix(M, L, 0.4) if k != 2 else L, al); c.fill()
        label(c, nm, x + (0 if k == 0 else (190 if k == 1 else -190)), y + (-110 if k == 0 else 110), 'small', L, 'c', al)
    for k in range(10):
        q = (t * 0.12 + k / 10) % 1
        i = int(q * (len(pts) - 1))
        c.arc(pts[i][0], pts[i][1], 9, 0, 6.283); col(c, L, 0.8 * fin(t, 1.2)); c.fill()
    if kw.get('count'):
        p = ease((t - 0.6) / 1.6)
        label(c, f'%{int(round(98 * p))}', cx, cy, 'num', A, 'c', fin(t, 0.5))
        label(c, 'geri kazanılan su', cx, cy + 90, 'small', M, 'c', fin(t, 0.8))


def drink(c, t, d, **kw):
    bg_ship(c)
    window(c, 2000, 560, 280, t, 30)
    sip = 0.5 + 0.5 * math.sin(t * 1.4)
    character(c, 1050, 1260, 1.5, t, pose='stand', helmet=False, arms=(-0.2, 2.5 + 0.2 * sip), blink=blink_at(t), smile=0.8,
              eyes_closed=sip > 0.75)
    c.save(); c.translate(1050 + 60 * 1.5 * 0.7, 1260 - 5.1 * 60 * 1.5); c.rotate(0.4)
    rrect(c, -30, -60, 60, 120, 18); col(c, mix(M, L, 0.45)); c.fill(); c.restore()


# ============================================================ 4 — iniş
def entry(c, t, d, phase='heat', **kw):
    if phase == 'heat':
        c.rectangle(0, 0, W, H); c.set_source(vgrad(c, 0, H, [(0, mix(D, BK, 0.3)), (1, mix(A, D, 0.4))])); c.fill()
        stars(c, 3, 120, 700, 0.6)
        shx = 4 * math.sin(t * 50)
        capsule_craft(c, 1280 + shx, 560 + t * 25, 1.4, rot=-0.35, heat=0.7 + 0.3 * math.sin(t * 7) ** 2, t=t)
        particles(c, t, 4, 60, mix(A, L, 0.4), 0.2, 0.6, vx=(-30, 30), vy=(-900, -500), y0=0, y1=H, rmin=2, rmax=5)
    elif phase == 'chute':
        c.rectangle(0, 0, W, H); c.set_source(vgrad(c, 0, H, [(0, SKY_DAY_TOP), (1, SKY_DAY_LOW)])); c.fill()
        far = ridge(17, 1250, 60, wl=1500); fill_ridge(c, far, G1)
        sw = 0.08 * math.sin(t * 1.3)
        c.save(); c.translate(1280, 520 + t * 15); c.rotate(sw)
        op = fin(t, 0.2, 0.5)
        c.save(); c.scale(1, 0.5 + 0.5 * op)
        c.arc(0, -150, 420 * (0.4 + 0.6 * op), math.pi, 2 * math.pi); c.close_path(); col(c, L); c.fill()
        for k in range(-3, 4, 2):
            c.save(); c.arc(0, -150, 420 * (0.4 + 0.6 * op), math.pi, 2 * math.pi); c.close_path(); c.clip()
            c.rectangle(k * 60 * (0.4 + 0.6 * op), -600, 60 * (0.4 + 0.6 * op), 600); col(c, A); c.fill(); c.restore()
        c.restore()
        for sx in (-1, 0, 1):
            c.move_to(sx * 380 * (0.4 + 0.6 * op), -150); c.line_to(sx * 40, 420)
        c.set_line_width(3); col(c, L, 0.8); c.stroke()
        capsule_craft(c, 0, 600, 0.9)
        c.restore()
    else:  # thrust — iniş motorları
        near = bg_mars_day(c, 13, hz=860)
        y = 300 + 520 * ease(t / max(d, 0.1))
        rnd = random.Random(2)
        for k in range(4):
            fl = 0.8 + 0.2 * math.sin(t * 40 + k)
            x = 1280 + (k - 1.5) * 120
            c.move_to(x - 30, y + 160); c.line_to(x, y + 160 + 180 * fl); c.line_to(x + 30, y + 160); c.close_path(); col(c, mix(A, L, 0.4), 0.9); c.fill()
        rrect(c, 1080, y - 60, 400, 220, 40); col(c, L); c.fill()
        rrect(c, 1080, y + 40, 400, 30, 6); col(c, A); c.fill()
        for sx in (-1, 1):
            col(c, mix(L, M, 0.5)); capsule(c, 1280 + sx * 160, y + 150, 1280 + sx * 260, y + 280, 14)
        dd = ease((t - d * 0.5) / (d * 0.5))
        for k in range(16):
            r = rnd.uniform(60, 140) * dd
            c.arc(1280 + rnd.uniform(-1, 1) * 700 * dd, 1080 - rnd.uniform(0, 120) * dd, r, 0, 6.283); col(c, G1, 0.8 * dd); c.fill()
        fg_mars(c, 13, 1200)


def signal(c, t, d, mode='one', **kw):
    bg_space(c, 21, 200)
    ex, mx = 450, 2110
    planet(c, ex, 700, 150, 'earth', glow=0.25); planet(c, mx, 700, 110, 'mars', glow=0.25)
    line_draw(c, [(ex + 180, 700), (mx - 140, 700)], 1.0, 3, M, 0.35, dash=[10, 18])
    if mode == 'one':
        q = ease((t - 0.3) / max(d - 0.6, 1))
        x = ex + 180 + (mx - 140 - ex - 180) * q
        line_draw(c, [(ex + 180, 700), (x, 700)], 1.0, 4, L, 0.9)
        c.arc(x, 700, 12, 0, 6.283); col(c, L); c.fill()
        label(c, kw.get('lab', 'dakikalar'), 1280, 560, 'num', L, 'c', fin(t, 0.6), dy=14)
    else:
        q1 = ease((t - 0.3) / max(d * 0.45, 1)); q2 = ease((t - 0.3 - d * 0.45) / max(d * 0.45, 1))
        x1 = ex + 180 + (mx - 140 - ex - 180) * q1
        line_draw(c, [(ex + 180, 680), (x1, 680)], 1.0, 4, L, 0.9)
        if q2 > 0:
            x2 = mx - 140 - (mx - 140 - ex - 180) * q2
            line_draw(c, [(mx - 140, 720), (x2, 720)], 1.0, 4, M, 0.9)
        label(c, kw.get('lab', '20+ dk'), 1280, 540, 'num', L, 'c', fin(t, 0.6), dy=14)
        label(c, 'tek yön', 1280, 830, 'small', M, 'c', fin(t, 0.9), dy=14)


def waiting(c, t, d, **kw):
    sh = 3 * math.sin(t * 41)
    c.save(); c.translate(sh, 0)
    col(c, mix(D, M, 0.1)); c.paint()
    c.set_source(rgrad(c, 1900, 500, 0, 900, [(0, A, 0.35 + 0.15 * math.sin(t * 6)), (1, A, 0)])); c.paint()
    c.arc(1900, 500, 220, 0, 6.283); col(c, mix(D, M, 0.3)); c.fill()
    c.arc(1900, 500, 180, 0, 6.283); col(c, mix(A, L, 0.3 + 0.1 * math.sin(t * 9))); c.fill()
    character(c, 1000, 1250, 1.45, t, pose='sit', blink=blink_at(t, 2.6), brow=0.9, smile=0.0, look=(1, -0.6))
    c.restore()


def touchdown(c, t, d, **kw):
    near = bg_mars_day(c, 15, hz=780)
    lx, ly = 1280, ridge_y(near, 1280) + 120
    bump = 12 * math.exp(-((t - 0.3) ** 2) * 30)
    c.save(); c.translate(0, -bump)
    col(c, mix(L, M, 0.55))
    for k in (-1, 1):
        capsule(c, lx + k * 80, ly - 180, lx + k * 250, ly, 22)
        c.save(); c.translate(lx + k * 250, ly); c.scale(58, 14); c.arc(0, 0, 1, 0, 6.283); c.restore(); c.fill()
    rrect(c, lx - 200, ly - 430, 400, 260, 50); col(c, L); c.fill()
    c.move_to(lx - 150, ly - 430); c.line_to(lx - 80, ly - 560); c.line_to(lx + 80, ly - 560); c.line_to(lx + 150, ly - 430); c.close_path(); col(c, SUIT_SH); c.fill()
    rrect(c, lx - 200, ly - 325, 400, 44, 8); col(c, A); c.fill()
    c.arc(lx, ly - 495, 34, 0, 6.283); col(c, mix(M, D, 0.4)); c.fill()
    c.restore()
    rnd = random.Random(5)
    dd = ease(t / 1.2) * (1 - 0.6 * ease((t - 2.5) / 3))
    for k in range(30):
        ang = rnd.uniform(0, math.pi)
        r0 = rnd.uniform(200, 1100) * ease(t / 2)
        r = rnd.uniform(60, 160)
        c.arc(lx + math.cos(ang) * r0 * (1 if k % 2 else -1), ly - rnd.uniform(0, 160) * ease(t / 2), r, 0, 6.283)
        col(c, mix(G1, L, 0.2), 0.75 * dd); c.fill()
    fg_mars(c, 15, 1230)


# ============================================================ 5 — sol 1
def sol_clock(c, t, d, **kw):
    col(c, mix(D, M, 0.12)); c.paint()
    for k, (x, kind, nm, val) in enumerate([(820, 'earth', 'Dünya günü', '24 sa'), (1740, 'mars', 'Mars günü (sol)', '24 sa 40 dk')]):
        al = fin(t, 0.2 + k * 0.8)
        planet(c, x, 560, 110, kind, glow=0.3)
        p = ease((t - 0.3 - k * 0.8) / 1.5)
        c.arc(x, 560, 200, -math.pi / 2, -math.pi / 2 + 2 * math.pi * p * (1.0 if k == 0 else 1.0)); c.set_line_width(5)
        col(c, L if k == 0 else A, 0.9 * al); c.stroke()
        if k == 1 and p >= 1:
            ext = ease((t - 2.1) / 0.6) * 0.17
            c.arc(x, 560, 200, -math.pi / 2, -math.pi / 2 + 2 * math.pi * ext); c.set_line_width(12); col(c, A); c.stroke()
        label(c, val, x, 870, 'num', L, 'c', al, dy=14)
        label(c, nm, x, 960, 'small', M, 'c', al, dy=14)


def first_step(c, t, d, **kw):
    near = bg_mars_day(c, 1, sun=(1950, 300))
    lx, ly = 1880, ridge_y(near, 1880) + 10
    col(c, mix(L, M, 0.55))
    for k in (-1, 1):
        capsule(c, lx + k * 60, ly - 140, lx + k * 190, ly, 18)
        c.save(); c.translate(lx + k * 190, ly); c.scale(46, 12); c.arc(0, 0, 1, 0, 6.283); c.restore(); c.fill()
    rrect(c, lx - 150, ly - 330, 300, 200, 40); col(c, L); c.fill()
    c.move_to(lx - 110, ly - 330); c.line_to(lx - 60, ly - 430); c.line_to(lx + 60, ly - 430); c.line_to(lx + 110, ly - 330); c.close_path(); col(c, SUIT_SH); c.fill()
    rrect(c, lx - 150, ly - 250, 300, 34, 6); col(c, A); c.fill()
    op = fin(t, 0.2, 0.8)
    rrect(c, lx - 54, ly - 205, 108, 70, 12); col(c, mix(M, D, 0.25 + 0.4 * op)); c.fill()
    front = fg_mars(c, 1)
    px = 1700 - 700 * ease((t - 0.8) / max(d - 0.8, 1))
    walking = 0.8 < t < d
    for k in range(int(max(0, (1700 - px) / 105))):
        fx = 1600 - k * 105
        fy = ridge_y(near, fx) + 150 + (k % 2) * 26
        c.save(); c.translate(fx, fy); c.scale(26, 9); c.arc(0, 0, 1, 0, 6.283); c.restore(); col(c, mix(G2, D, 0.22)); c.fill()
    character(c, px, ridge_y(near, px) + 175, 1.05, t, pose='walk' if walking else 'stand', walk=t * 0.6, flip=True, blink=blink_at(t))
    particles(c, t, 5, 60, L, 0.1, 0.35, y0=200, y1=1300)


def scale_weight(c, t, d, **kw):
    near = bg_mars_day(c, 19, hz=720, sun=(2250, 220))
    fg_mars(c, 19, 1220, rocks=False)
    rrect(c, 980, 1150, 600, 90, 20); col(c, mix(M, D, 0.3)); c.fill()
    rrect(c, 1180, 1165, 200, 60, 10); col(c, mix(D, BK, 0.3)); c.fill()
    character(c, 1280, 1150, 1.3, t, pose='stand', blink=blink_at(t), look=(0, 1), brow=0.6 * fin(t, 1.5))
    p = ease((t - 0.5) / 1.8)
    v = 40 - 25 * p
    label(c, f'{v:.0f} kg', 1280, 1196, 'small', L, 'c', 1)
    label(c, f'{v:.0f} kg', 1900, 560, 'num', L, 'c', fin(t, 0.3))
    label(c, 'Dünya: 40 kg', 1900, 660, 'small', L, 'c', fin(t, 0.6))


def jump(c, t, d, **kw):
    near = bg_mars_day(c, 23, hz=760)
    gy = ridge_y(near, 1280) + 190
    T = 2.4
    q = (t % T) / T
    h = 520 * 4 * q * (1 - q)
    hx = 800 + 900 * q
    pts = [(800 + 900 * s, gy - 520 * 4 * s * (1 - s)) for s in np.linspace(0, 1, 50)]
    line_draw(c, pts, 1.0, 3, L, 0.35, dash=[10, 14])
    pts2 = [(800 + 360 * s, gy - 210 * 4 * s * (1 - s)) for s in np.linspace(0, 1, 30)]
    line_draw(c, pts2, 1.0, 3, M, 0.6, dash=[10, 14])
    label(c, 'Dünya', 980, gy - 260, 'small', L, 'c', fin(t, 0.4))
    label(c, 'Mars', 1250, gy - 580, 'small', L, 'c', fin(t, 0.6))
    fg_mars(c, 23, 1230)
    character(c, hx, gy - h, 1.0, t, pose='jump' if 0.04 < q < 0.96 else 'crouch', blink=blink_at(t), smile=1.0)


def kick(c, t, d, **kw):
    near = bg_mars_day(c, 27, hz=760, far_volcano=True)
    gy = ridge_y(near, 600) + 190
    k = fin(t, 0.5, 0.25)
    character(c, 600, gy, 1.05, t, pose='kick' if 0.3 < t < 1.0 else 'stand', blink=blink_at(t), smile=1.0, look=(1, -0.3))
    q = max(0.0, t - 0.75)
    bx = 720 + q * 620
    by = gy - 40 - (q * 900 - q * q * 150)
    if t < 0.75:
        bx, by = 720, gy - 40
    by = min(by, gy - 40)
    c.arc(bx, by, 38, 0, 6.283); col(c, L); c.fill()
    c.arc(bx - 8, by - 6, 14, 0, 6.283); col(c, D); c.fill()
    fg_mars(c, 27, 1240)


def helmet_close(c, t, d, gauge=False, **kw):
    near = bg_mars_day(c, 29, hz=680, sun=None)
    character(c, 1000, 1950, 3.2, t, pose='stand', blink=blink_at(t), brow=0.7, smile=0.1, look=(0.5, 0))
    if gauge:
        x0, y0, w = 1750, 520, 600
        label(c, 'hava basıncı', x0, y0 - 90, 'small', L, 'l', fin(t, 0.3))
        p = ease((t - 0.4) / 1.0)
        rrect(c, x0, y0 - 18, w, 36, 18); col(c, mix(D, M, 0.3), 0.8); c.fill()
        rrect(c, x0, y0 - 18, w * p, 36, 18); col(c, L, 0.9); c.fill()
        label(c, 'Dünya', x0 + w, y0 + 70, 'small', L, 'r', fin(t, 0.8))
        q = ease((t - 1.2) / 0.8)
        rrect(c, x0, y0 + 140 - 18, w, 36, 18); col(c, mix(D, M, 0.3), 0.8 * q); c.fill()
        rrect(c, x0, y0 + 140 - 18, max(8, w * 0.006), 36, 4); col(c, A, q); c.fill()
        label(c, 'Mars: %1\'den az', x0, y0 + 220, 'small', L, 'l', fin(t, 1.4))
    else:
        rnd = random.Random(2)
        for k in range(8):
            x = 1650 + rnd.uniform(0, 700) + 20 * math.sin(t + k)
            y = (rnd.uniform(200, 1100) - t * 40) % 1200 + 100
            a = 0.7 * fin(t, 0.3 + k * 0.15)
            c.arc(x, y, 22, 0, 6.283); col(c, L, a * 0.6); c.fill()
            c.arc(x - 40, y, 16, 0, 6.283); col(c, M, a * 0.6); c.fill()
            c.arc(x + 40, y, 16, 0, 6.283); col(c, M, a * 0.6); c.fill()
        label(c, 'karbondioksit', 2000, 1150, 'small', L, 'c', fin(t, 0.8))


def sky_look(c, t, d, **kw):
    c.rectangle(0, 0, W, H); c.set_source(vgrad(c, 0, H, [(0, mix(SKY_DAY_TOP, D, 0.1)), (1, SKY_DAY_LOW)])); c.fill()
    c.set_source(rgrad(c, 1900, 380, 0, 300, [(0, L, 0.5), (1, L, 0)])); c.paint()
    c.arc(1900, 380, 46, 0, 6.283); col(c, mix(L, WH, 0.5)); c.fill()
    particles(c, t, 9, 120, L, 0.05, 0.25, y0=0, y1=H)
    front = ridge(55, 1250, 30, wl=1500); fill_ridge(c, front, G3)
    character(c, 900, 1500, 1.9, t, pose='stand', look=(0.8, -1), blink=blink_at(t), smile=0.6, brow=0.4)


def dust_hand(c, t, d, rust=False, **kw):
    near = bg_mars_day(c, 31, hz=700)
    fg_mars(c, 31, 1150, rocks=False, colr=G2)
    if not rust:
        character(c, 900, 1330, 1.5, t, pose='crouch', blink=blink_at(t), look=(1, 0.8), arms=(-0.6, 1.1 + 0.4 * fin(t, 0.4, 0.8)))
        gx, gy = 900 + 60 * 1.5 * 1.7, 1330 - 4.0 * 60 * 1.5 + 60 * 1.5 * 1.0
        for k in range(14):
            rnd = random.Random(k)
            c.arc(gx + rnd.uniform(-40, 40), gy - 20 + rnd.uniform(-12, 8) - 40 * fin(t, 0.6, 0.8), rnd.uniform(5, 12), 0, 6.283)
            col(c, mix(A, D, 0.15)); c.fill()
            if t > 1.6:
                q = (t - 1.6 + k * 0.13) % 1.6 / 1.6
                c.arc(gx + rnd.uniform(-30, 30), gy + 20 + q * 260, 4, 0, 6.283); col(c, A, 1 - q); c.fill()
    else:
        col(c, D, 0.35); c.paint()
        cx, cy = 1280, 640
        for k in range(9):
            x = cx - 640 + k * 160
            a = fin(t, 0.2 + k * 0.05)
            for sy in (-1, 1):
                rrect(c, x - 80, cy + sy * 40 - 26, 160, 52, 26); c.set_line_width(14)
                col(c, mix(mix(M, D, 0.3), A, min(1, max(0, (t - 0.8) / 1.5))), a); c.stroke()
            c.arc(x, cy, 18, 0, 6.283); col(c, mix(M, A, min(1, max(0, (t - 0.8) / 1.5))), a); c.fill()
        label(c, 'demir + oksijen = pas', cx, 900, 'small', L, 'c', fin(t, 1.0))


# ============================================================ 6 — ev
def dome_build(c, t, d, **kw):
    near = bg_mars_day(c, 33, hz=740)
    gy = ridge_y(near, 1280) + 120
    g = ease((t - 0.2) / 2.2)
    if g > 0:
        dome(c, 1280, gy, 420 * g, light=fin(t, 2.4), door=g > 0.9, glow=g > 0.9)
    fg_mars(c, 33, 1230)
    character(c, 520, 1290, 1.0, t, pose='point', blink=blink_at(t), look=(1, -0.3), flip=False)


def co2_split(c, t, d, **kw):
    col(c, mix(D, M, 0.15)); c.paint()
    cx, cy = 1280, 640
    s = ease((t - 1.0) / 1.0)
    c.arc(cx, cy, 90, 0, 6.283); col(c, mix(D, BK, 0.2)); c.fill()                       # C
    label(c, 'C', cx, cy, 'num', L)
    for sx in (-1, 1):
        ox = cx + sx * (170 + 260 * s); oy = cy - 60 * s
        if s > 0:
            line_draw(c, [(cx + sx * 90, cy), (ox - sx * 80, oy)], 1 - s, 10, L, 0.6)
        else:
            c.move_to(cx + sx * 90, cy); c.line_to(ox - sx * 80, oy); c.set_line_width(10); col(c, L, 0.6); c.stroke()
        c.arc(ox, oy, 80, 0, 6.283); col(c, A); c.fill()
        label(c, 'O', ox, oy, 'num', L)
    label(c, 'karbondioksit', cx, cy + 230, 'small', M, 'c', 1 - s)
    label(c, 'oksijen', cx, cy + 230, 'small', L, 'c', s)


def moxie(c, t, d, **kw):
    near = bg_mars_day(c, 35, hz=760)
    gy = ridge_y(near, 1100) + 160
    rover(c, 1100, gy, 1.5, t, 0, box_glow=0.5 + 0.5 * math.sin(t * 2.2) ** 2)
    rnd = random.Random(8)
    for k in range(8):
        q = (t * 0.25 + k / 8) % 1
        x = 960 + rnd.uniform(-40, 40) + 60 * math.sin(q * 6 + k)
        y = gy - 280 - q * 600
        c.arc(x, y, 16 + 8 * q, 0, 6.283); col(c, L, 0.6 * (1 - q)); c.fill()
    fg_mars(c, 35, 1240)
    if kw.get('lab'):
        label(c, '122 gram', 1900, 520, 'num', L, 'c', fin(t, 0.3), dy=14)
        label(c, 'toplam oksijen', 1900, 620, 'small', L, 'c', fin(t, 0.6), dy=14)


def dog_breath(c, t, d, **kw):
    col(c, mix(D, M, 0.15)); c.paint()
    c.rectangle(0, 1050, W, 390); col(c, mix(D, M, 0.25)); c.fill()
    dog(c, 900, 1050, 2.4, t)
    for k in range(3):
        q = (t * 0.5 + k / 3) % 1
        c.arc(900 + 330 + q * 260, 760 - q * 80, 18 + 30 * q, 0, 6.283); col(c, L, 0.5 * (1 - q)); c.fill()
    label(c, '10 saat', 1780, 620, 'num', L, 'c', fin(t, 0.4), dy=14)
    label(c, 'küçük bir köpeğin nefesi', 1780, 720, 'small', M, 'c', fin(t, 0.7), dy=14)


def ice_dig(c, t, d, **kw):
    c.rectangle(0, 0, W, 520); c.set_source(vgrad(c, 0, 520, [(0, SKY_DAY_TOP), (1, SKY_DAY_LOW)])); c.fill()
    top = ridge(61, 520, 12, wl=1600); fill_ridge(c, top, G2)
    c.rectangle(0, 620, W, 300); col(c, G3); c.fill()
    pts = ridge(63, 900, 30, wl=900); fill_ridge(c, pts, mix(M, L, 0.35))
    c.rectangle(0, 1160, W, 300); col(c, G4); c.fill()
    for k in range(20):
        rnd = random.Random(k)
        rock(c, rnd.uniform(0, W), rnd.uniform(640, 860), rnd.uniform(10, 25), G4, k)
    p = ease((t - 0.3) / 2.0)
    col(c, mix(M, D, 0.4)); capsule(c, 1300, 420, 1300, 520 + 440 * p, 34)
    rrect(c, 1240, 300, 120, 140, 20); col(c, L); c.fill()
    character(c, 1080, 545, 1.0, t, pose='hold', blink=blink_at(t), look=(1, 0.5))
    label(c, 'donmuş su', 1900, 1010, 'small', D, 'c', fin(t, 0.8))


def dome_water(c, t, d, **kw):
    bg_hab(c, 1.0, warm=0.25)
    for k, x in enumerate((700, 1100)):
        rrect(c, x - 130, 450, 260, 700, 40); col(c, mix(M, D, 0.25)); c.fill()
        lv = 0.5 + 0.2 * math.sin(t * 0.8 + k)
        c.save(); rrect(c, x - 130, 450, 260, 700, 40); c.clip()
        c.rectangle(x - 130, 1150 - 700 * lv, 260, 700 * lv); col(c, mix(M, L, 0.3), 0.85); c.fill(); c.restore()
    pts = [(830, 600), (970, 600)]
    line_draw(c, [(830, 1000), (900, 1000), (900, 600), (970, 600)], 1.0, 14, mix(M, D, 0.1))
    for k in range(5):
        q = (t * 0.4 + k / 5) % 1
        y = 1000 - 400 * q
        c.arc(900, y, 8, 0, 6.283); col(c, L, 0.9); c.fill()
    character(c, 1700, 1240, 1.4, t, pose='hold', helmet=False, blink=blink_at(t), look=(-1, 0), flip=True, smile=0.7)


def dome_dusk(c, t, d, **kw):
    c.rectangle(0, 0, W, H); c.set_source(vgrad(c, 0, 900, [(0, mix(D, A, 0.15)), (1, mix(A, D, 0.35))])); c.fill()
    far = ridge(71, 880, 50, wl=1300); fill_ridge(c, far, mix(G4, D, 0.2))
    mid = ridge(73, 1000, 30, wl=1500); fill_ridge(c, mid, mix(G5, D, 0.3))
    dome(c, 1280, ridge_y(mid, 1280) + 40, 330, light=0.9)
    p = 1 + 0.03 * t
    for k in range(3):
        x = 300 + k * 900
        c.save(); c.translate(x, 200); c.scale(p, p)
        c.move_to(-200, 0); c.line_to(200, 0); col(c, L, 0.0); c.stroke(); c.restore()
    front = ridge(75, 1180, 20, wl=1900); fill_ridge(c, front, mix(G5, D, 0.55))


# ============================================================ 7 — radyasyon
def radiation(c, t, d, mode='earth', **kw):
    bg_space(c, 31, 220)
    rnd = random.Random(4)
    if mode == 'earth':
        px, py, r, kind = 1400, 720, 230, 'earth'
    else:
        px, py, r, kind = 1400, 720, 170, 'mars'
    if mode == 'earth':
        a = fin(t, 0.4, 0.8)
        for k, s in enumerate([1.6, 2.1, 2.7]):
            c.save(); c.translate(px, py); c.scale(r * s, r * s * 0.62)
            c.arc(0, 0, 1, 0, 6.283); c.restore(); c.set_line_width(4); col(c, M, 0.55 * a); c.stroke()
    planet(c, px, py, r, kind, glow=0.25)
    for k in range(9):
        q = ((t * 0.45 + k / 9) % 1)
        y = 280 + k * 100
        x0 = -100 + q * 1300
        stop = px - (r * 2.7 if mode == 'earth' else r) - 40
        if mode == 'earth':
            x1 = min(x0 + 220, stop)
        else:
            x1 = min(x0 + 220, px - r * 0.9) if abs(y - py) < r else x0 + 220
        if x1 > x0:
            c.move_to(x0, y); c.line_to(x1, y + 6 * math.sin(k)); c.set_line_width(4); col(c, A, 0.8); c.stroke()
    label(c, 'manyetik alan' if mode == 'earth' else 'kalkan yok', px, py + (r * 2.0 if mode == 'earth' else r + 120), 'small', L, 'c', fin(t, 0.8))


def cave(c, t, d, **kw):
    c.rectangle(0, 0, W, 360); c.set_source(vgrad(c, 0, 360, [(0, SKY_DAY_TOP), (1, SKY_DAY_LOW)])); c.fill()
    top = ridge(81, 380, 15, wl=1500); fill_ridge(c, top, G2)
    c.rectangle(0, 470, W, H); col(c, G4); c.fill()
    c.save(); c.translate(1280, 900); c.scale(1150, 330); c.arc(0, 0, 1, 0, 6.283); c.restore(); col(c, mix(D, A, 0.3)); c.fill()
    c.rectangle(0, 1110, W, 400); col(c, G5); c.fill()
    for k in range(6):
        x = 180 + k * 450
        rnd = random.Random(k)
        c.move_to(x - 30, 570 + rnd.uniform(0, 30)); c.line_to(x, 640 + rnd.uniform(0, 40)); c.line_to(x + 30, 570); c.close_path(); col(c, G4); c.fill()
    dome(c, 1280, 1110, 300, light=1.0)
    character(c, 1800, 1110, 0.85, t, pose='walk', walk=t * 0.6, flip=True, blink=blink_at(t))
    for k in range(5):
        q = ((t * 0.4 + k / 5) % 1)
        x = 300 + k * 450
        y = -50 + q * 520
        c.move_to(x, y); c.line_to(x + 10, y + 120); c.set_line_width(4); col(c, A, 0.8 * (1 - max(0, q - 0.85) * 6)); c.stroke()


def walk_rule(c, t, d, **kw):
    mid = bg_night(c, 8, hz=900)
    front = ridge(85, 1150, 22, wl=1900); fill_ridge(c, front, mix(G5, D, 0.5))
    character(c, 600 + t * 55, ridge_y(front, 600 + t * 55) + 20, 1.0, t, pose='walk', walk=t * 0.6, blink=blink_at(t), look=(-0.5, -0.5))
    rnd = random.Random(3)
    for k in range(14):
        x = rnd.uniform(0, W); y = (rnd.uniform(0, 1000) + t * 150) % 1100
        col(c, A, 0.25); c.move_to(x, y); c.line_to(x + 6, y + 70); c.set_line_width(3); c.stroke()


# ============================================================ 8 — yemek
def food_crate(c, t, d, **kw):
    bg_hab(c, 1.0, warm=0.2)
    for i in range(3):
        for j in range(2):
            rrect(c, 1450 + i * 260, 1150 - (j + 1) * 200, 240, 190, 16); col(c, mix(L, M, 0.3)); c.fill()
            rrect(c, 1450 + i * 260 + 70, 1150 - (j + 1) * 200 + 70, 100, 40, 8); col(c, mix(M, D, 0.3)); c.fill()
    p = ease(t / max(d, 1))
    c.save(); c.rectangle(1440, 1150 - 420 * (1 - p * 0.75) - 10, 800, 430); c.clip(); c.restore()
    character(c, 800, 1250, 1.4, t, pose='hold', helmet=False, look=(1, 0), blink=blink_at(t), brow=0.5, smile=0.3)
    rrect(c, 1000, 1250 - 3.8 * 84, 160, 120, 14); col(c, mix(L, M, 0.3)); c.fill()


def soil_wash(c, t, d, **kw):
    bg_hab(c, 1.0)
    rrect(c, 800, 900, 1000, 220, 30); col(c, mix(M, D, 0.3)); c.fill()
    rrect(c, 830, 900, 940, 120, 20); col(c, G3); c.fill()
    label(c, 'perklorat', 1300, 760, 'small', L, 'c', fin(t, 0.4))
    p = fin(t, 0.8, 0.5)
    if p > 0:
        c.save(); c.translate(1300, 380); c.rotate(0.6)
        rrect(c, -110, -80, 220, 160, 30); col(c, mix(M, L, 0.2)); c.fill(); c.restore()
        for k in range(12):
            q = (t * 1.2 + k / 12) % 1
            c.arc(1360 + 20 * math.sin(k), 470 + q * 430, 9, 0, 6.283); col(c, mix(M, L, 0.4), 0.9 * p); c.fill()
    character(c, 2050, 1250, 1.3, t, pose='point', helmet=False, flip=True, look=(-1, 0.3), blink=blink_at(t))


def greenhouse(c, t, d, **kw):
    bg_hab(c, 1.0, warm=0.4)
    for x in (300, 900, 1500, 2100):
        rrect(c, x - 220, 40, 440, 30, 12); col(c, mix(L, A, 0.3)); c.fill()
        c.move_to(x - 220, 70); c.line_to(x + 220, 70); c.line_to(x + 340, 980); c.line_to(x - 340, 980); c.close_path(); col(c, mix(L, A, 0.4), 0.1); c.fill()
    for row, (y, s) in enumerate([(820, 0.8), (1040, 1.0)]):
        rrect(c, 120, y, 2320, 60, 16); col(c, mix(M, D, 0.35)); c.fill()
        for k in range(12):
            x = 220 + k * 190 + row * 60
            g = ease((t - 0.2 - k * 0.08 - row * 0.3) / 1.6)
            if g > 0:
                plant(c, x, y, s * 1.1, 0.4 + 0.6 * g, 'lettuce' if (k + row) % 2 else 'sprout')
    character(c, 1300, 1330, 1.1, t, pose='stand', helmet=False, blink=blink_at(t), smile=0.9, look=(-0.5, -0.5))


def first_leaf(c, t, d, **kw):
    bg_hab(c, 1.0, warm=0.5)
    c.set_source(rgrad(c, 1280, 500, 0, 900, [(0, mix(L, A, 0.3), 0.3), (1, L, 0)])); c.paint()
    rrect(c, 1080, 900, 400, 300, 40); col(c, A); c.fill()
    rrect(c, 1060, 880, 440, 60, 20); col(c, mix(A, D, 0.2)); c.fill()
    g = ease((t - 0.2) / 2.0)
    plant(c, 1280, 890, 2.6, 0.2 + 0.8 * g, 'sprout')
    c.save(); c.translate(560, 820); head(c, 170, blink=blink_at(t), look=(1, -0.2), smile=1.0, brow=0.6); c.restore()


def iss_plants(c, t, d, **kw):
    bg_ship(c)
    rrect(c, 900, 380, 900, 560, 30); col(c, mix(M, D, 0.4)); c.fill()
    c.set_source(rgrad(c, 1350, 400, 0, 700, [(0, mix(A, L, 0.4), 0.5), (1, A, 0)])); c.paint()
    for k in range(6):
        x = 1000 + (k % 3) * 300; y = 700 + (k // 3) * 220
        rrect(c, x - 60, y, 120, 70, 16); col(c, L); c.fill()
        plant(c, x, y, 0.9, 0.7 + 0.3 * ease(t / 2), 'lettuce' if k % 2 else 'sprout')
    character(c, 520, 1060 + 15 * math.sin(t), 1.1, t, pose='float', helmet=False, st=CREW1, blink=blink_at(t), look=(1, -0.3), smile=0.9)


# ============================================================ 9 — iletişim
def tablet_msg(c, t, d, reply=False, **kw):
    bg_hab(c, 0.7, warm=0.3)
    rrect(c, 300, 980, 1400, 180, 30); col(c, mix(M, D, 0.35)); c.fill()               # yatak
    character(c, 900, 1150, 1.25, t, pose='sit', helmet=False, blink=blink_at(t), look=(1, 0.4), smile=0.6, arms=(1.0, 1.4))
    c.save(); c.translate(1150, 840); c.rotate(-0.15)
    rrect(c, -110, -150, 220, 300, 26); col(c, mix(D, BK, 0.2)); c.fill()
    rrect(c, -95, -135, 190, 270, 18); col(c, mix(M, D, 0.1)); c.fill()
    c.restore()
    a = fin(t, 0.6, 0.4)
    c.save(); rrect(c, 1450, 420 + 14 * (1 - a), 560, 130, 40); col(c, L, a); c.fill(); c.restore()
    label(c, 'İyi geceler', 1730, 485 + 14 * (1 - a), 'small', D, 'c', a)
    if reply:
        q = ease((t - 1.2) / max(d - 1.5, 1))
        c.arc(1730, 700, 70, -math.pi / 2, -math.pi / 2 + 2 * math.pi * q); c.set_line_width(6); col(c, L, 0.8); c.stroke()
        label(c, 'cevap bekleniyor', 1730, 820, 'small', M, 'c', fin(t, 1.0))


def voice_letter(c, t, d, **kw):
    col(c, mix(D, M, 0.15)); c.paint()
    for k in range(2):
        x = 820 if k == 0 else 1740
        y = 640
        a = fin(t, 0.3 + k * 1.2)
        rrect(c, x - 300, y - 90, 600, 180, 60); col(c, L if k == 0 else mix(M, L, 0.3), a); c.fill()
        for j in range(18):
            hh = 20 + 50 * abs(math.sin(j * 1.7 + k)) * (0.6 + 0.4 * math.sin(t * 5 + j))
            c.rectangle(x - 220 + j * 25, y - hh / 2, 10, hh); col(c, mix(D, M, 0.2), a); c.fill()
    arrow(c, 1150, 600, 1420, 600, fin(t, 0.8, 0.5), L, 4, 0.1)
    label(c, 'Mars', 820, 820, 'small', M, 'c', fin(t, 0.3))
    label(c, 'Dünya', 1740, 820, 'small', M, 'c', fin(t, 1.5))


def conjunction(c, t, d, **kw):
    bg_space(c, 41, 200)
    planet(c, 1280, 680, 170, 'sun', glow=1.4)
    a = fin(t, 0.3, 1.0)
    planet(c, 420, 680, 90, 'earth', light=(0.6, -0.2))
    planet(c, 2140, 680, 70, 'mars', light=(-0.6, -0.2))
    p = ease((t - 0.6) / 1.2)
    line_draw(c, [(520, 680), (1060, 680)], p, 4, L, 0.9)
    if p >= 1:
        for sx in (-1, 1):
            c.move_to(1080 + sx * 22, 660); c.line_to(1080 - sx * 22, 700)
        c.set_line_width(6); col(c, A); c.stroke()
    label(c, 'günlerce, haftalarca sessizlik', 1280, 1000, 'small', L, 'c', fin(t, 1.6))


def alone_window(c, t, d, **kw):
    bg_hab(c, 0.55)
    rrect(c, 1000, 260, 900, 600, 280); col(c, mix(D, M, 0.25)); c.fill()
    c.save(); rrect(c, 1030, 290, 840, 540, 260); c.clip()
    c.rectangle(1030, 290, 840, 540); c.set_source(vgrad(c, 290, 830, [(0, mix(D, BK, 0.2)), (1, mix(A, D, 0.4))])); c.fill()
    stars(c, 7, 80, 700, 0.7)
    rr = ridge(91, 760, 25, wl=600, x0=1000, x1=1900); fill_ridge(c, rr, mix(G5, D, 0.4))
    if kw.get('omen'):
        o = fin(t, 1.0, 1.5)
        c.rectangle(1700 - 200 * o, 600, 400, 300); col(c, mix(A, D, 0.3), 0.7 * o); c.fill()
    c.restore()
    for k, (x, st) in enumerate([(900, ABI), (1950, CREW2)]):
        character(c, x, 1250, 1.2, t, pose='stand', helmet=False, st=st, flip=k == 1, look=(1 if k == 0 else -1, -0.3) if not kw.get('omen') else (1, -0.4),
                  blink=blink_at(t, 3.3, k), smile=0.2, brow=0.4 if kw.get('omen') else 0)


# ============================================================ 10 — fırtına
def storm_wall(c, t, d, **kw):
    near = bg_mars_day(c, 43, hz=760, sun=(1700, 300))
    x = 2300 - t * kw.get('speed', 120)
    dust_wall(c, x, 950, 1.0, t)
    fg_mars(c, 43)
    dome(c, 700, 1060, 250)
    character(c, 1150, 1190, 1.0, t, pose='stand', look=(1, -0.2), blink=blink_at(t), brow=0.7)


def globe_storm(c, t, d, **kw):
    bg_space(c, 47, 240)
    planet(c, 1280, 700, 420, 'mars', glow=0.2)
    p = ease((t - 0.3) / max(d * 0.7, 1))
    c.save(); c.arc(1280, 700, 420, 0, 6.283); c.clip()
    for k in range(10):
        rnd = random.Random(k)
        c.arc(1280 + rnd.uniform(-1, 1) * 380, 700 + rnd.uniform(-1, 1) * 380, (60 + 260 * p) * rnd.uniform(0.6, 1.2), 0, 6.283)
        col(c, mix(A, L, 0.45), 0.55 * min(1, p * 1.4)); c.fill()
    c.restore()
    label(c, '2018', 2100, 420, 'num', L, 'c', fin(t, 0.4), dy=14)
    label(c, 'küresel toz fırtınası', 2100, 520, 'small', M, 'c', fin(t, 0.7), dy=14)


def oppy_dark(c, t, d, **kw):
    dk = ease(t / max(d, 1))
    near = bg_mars_day(c, 49, hz=780, sun=(1900, 300))
    col(c, mix(A, D, 0.5), 0.35 + 0.45 * dk); c.paint()
    rover(c, 1280, 1150, 1.3, t, 0, dust=0.8 * dk)
    fg_mars(c, 49, 1240, colr=mix(G3, D, 0.3 * dk))
    col(c, mix(D, A, 0.2), 0.3 * dk); c.paint()
    x0, y0 = 1850, 360
    rrect(c, x0, y0, 220, 100, 16); c.set_line_width(5); col(c, L); c.stroke()
    rrect(c, x0 + 220, y0 + 30, 18, 40, 4); col(c, L); c.fill()
    lv = max(0.02, 1 - dk)
    rrect(c, x0 + 12, y0 + 12, 196 * lv, 76, 8); col(c, A if lv < 0.3 else L); c.fill()


def breeze(c, t, d, **kw):
    near = bg_mars_day(c, 51, hz=760, sun=(1700, 280))
    col(c, mix(A, L, 0.3), 0.25); c.paint()
    fg_mars(c, 51)
    col(c, mix(M, L, 0.2)); capsule(c, 1600, 1210, 1600, 760, 10)
    c.move_to(1600, 770)
    for k in range(12):
        x = 1600 + k * 22
        c.line_to(x, 770 + 10 * math.sin(t * 3 + k * 0.6))
    for k in range(11, -1, -1):
        x = 1600 + k * 22
        c.line_to(x, 900 + 10 * math.sin(t * 3 + k * 0.6))
    c.close_path(); col(c, A); c.fill()
    character(c, 1100, 1210, 1.1, t, pose='stand', blink=blink_at(t), smile=0.8, look=(1, -0.2))
    particles(c, t, 21, 120, L, 0.1, 0.35, vx=(40, 90), y0=200, y1=1300)


def dark_energy(c, t, d, **kw):
    near = bg_mars_day(c, 53, hz=760, sun=None)
    col(c, mix(A, D, 0.55), 0.7); c.paint()
    dome(c, 900, 1100, 300, light=0.35 + 0.15 * math.sin(t * 2))
    for k in range(4):
        x = 1600 + k * 180
        c.move_to(x, 1080); c.line_to(x + 150, 1080); c.line_to(x + 180, 1010); c.line_to(x + 30, 1010); c.close_path()
        col(c, mix(M, D, 0.6)); c.fill(); c.move_to(x, 1080); c.line_to(x + 150, 1080); c.line_to(x + 180, 1010); c.line_to(x + 30, 1010); c.close_path()
        col(c, G1, 0.75); c.fill()
    particles(c, t, 23, 100, mix(A, L, 0.3), 0.15, 0.4, vx=(30, 70), y0=100, y1=1300)
    fg_mars(c, 53, colr=mix(G3, D, 0.4))


def dust_devil(c, t, d, **kw):
    near = bg_mars_day(c, 57, hz=760, sun=(2100, 260))
    gy = ridge_y(near, 1280) + 170
    x = 2300 - t * 220
    for k in range(18):
        y = gy - k * 45
        w = 30 + k * 12
        c.save(); c.translate(x + 30 * math.sin(t * 3 + k * 0.4), y); c.scale(w, 14 + k)
        c.arc(0, 0, 1, 0, 6.283); c.restore(); col(c, mix(G1, L, 0.2), 0.12 + 0.012 * k); c.fill()
    cleaned = min(1.0, max(0.0, (1700 - x) / 500))
    rover(c, 1280, gy + 20, 1.2, t, 0, dust=0.8 * (1 - cleaned))
    fg_mars(c, 57)
    if kw.get('years'):
        label(c, '90 gün', 760, 440, 'num', L, 'c', fin(t, 0.3), dy=14)
        arrow(c, 920, 440, 1240, 440, fin(t, 1.0, 0.5), L, 4, 0.12)
        label(c, '15 yıl', 1420, 440, 'num', L, 'c', fin(t, 1.5), dy=14)


# ============================================================ 11 — gece
def thermo(c, t, d, **kw):
    mid = bg_night(c, 11, hz=1000)
    x, y0, y1 = 1280, 260, 1060
    rrect(c, x - 40, y0, 80, y1 - y0, 40); col(c, mix(D, M, 0.3)); c.fill()
    c.arc(x, y1, 80, 0, 6.283); col(c, mix(D, M, 0.3)); c.fill()
    c.arc(x, y1, 56, 0, 6.283); col(c, M); c.fill()
    lv = 1 - 0.55 * ease((t - 0.4) / 1.2) - 0.35 * ease((t - d * 0.55) / 1.2)
    rrect(c, x - 18, y0 + (y1 - y0) * (1 - lv), 36, (y1 - y0) * lv, 18); col(c, M); c.fill()
    label(c, '−53 °C', x + 140, y0 + (y1 - y0) * 0.45 + 120, 'num', L, 'l', fin(t, 0.8), dy=14)
    label(c, 'ortalama', x + 140, y0 + (y1 - y0) * 0.45 + 210, 'small', M, 'l', fin(t, 1.0))
    label(c, '−128 °C', x - 140, y0 + (y1 - y0) * 0.82, 'num', L, 'r', fin(t, d * 0.55), dy=14)
    label(c, 'kutuplarda kış', x - 140, y0 + (y1 - y0) * 0.82 + 90, 'small', M, 'r', fin(t, d * 0.55 + 0.3))


def phobos(c, t, d, **kw):
    bg_space(c, 51, 200)
    planet(c, 1280, 720, 300, 'mars', glow=0.2)
    c.save(); c.translate(1280, 720); c.scale(1, 0.32)
    c.arc(0, 0, 520, 0, 6.283); c.restore(); c.set_line_width(3); col(c, M, 0.5); c.stroke()
    c.save(); c.translate(1280, 720); c.scale(1, 0.28)
    c.arc(0, 0, 960, 0, 6.283); c.restore(); c.set_line_width(3); col(c, M, 0.3); c.stroke()
    a1 = t * 1.6; a2 = t * 0.35 + 2
    for (ang, R, sy, rr, nm) in [(a1, 520, 0.32, 26, 'Fobos'), (a2, 960, 0.28, 16, 'Deimos')]:
        x, y = 1280 + R * math.cos(ang), 720 + R * sy * math.sin(ang)
        front = math.sin(ang) > 0
        c.save(); c.translate(x, y); c.rotate(0.4); c.scale(rr * 1.3, rr); c.arc(0, 0, 1, 0, 6.283); c.restore()
        col(c, mix(L, M, 0.35), 1 if front or math.hypot(x - 1280, (y - 720)) > 300 else 0.0); c.fill()
        label(c, nm, x, y - 60, 'small', L, 'c', fin(t, 0.4) * (1 if front or math.hypot(x - 1280, (y - 720)) > 300 else 0))


def phobos_sky(c, t, d, **kw):
    mid = bg_night(c, 13, hz=960)
    q = ease(t / max(d, 1))
    x = 2500 - 2400 * q; y = 950 - math.sin(q * math.pi) * 600
    c.save(); c.translate(x, y); c.rotate(0.4); c.scale(44, 30); c.arc(0, 0, 1, 0, 6.283); c.restore(); col(c, mix(L, M, 0.35)); c.fill()
    pts = [(2500 - 2400 * s, 950 - math.sin(s * math.pi) * 600) for s in np.linspace(0, q, 40)]
    line_draw(c, pts, 1, 3, L, 0.3, dash=[8, 14])
    label(c, 'batı', 2380, 1080, 'small', M, 'c', fin(t, 0.3))
    label(c, 'doğu', 180, 1080, 'small', M, 'c', fin(t, 0.3))
    front = ridge(95, 1180, 22, wl=1900); fill_ridge(c, front, mix(G5, D, 0.55))
    character(c, 1280, 1220, 0.95, t, pose='stand', look=(-1 if q > 0.5 else 1, -1), blink=blink_at(t))


def sunset_compare(c, t, d, **kw):
    for k in range(2):
        x0 = k * W / 2
        c.save(); c.rectangle(x0, 0, W / 2, H); c.clip()
        if k == 0:
            c.rectangle(x0, 0, W / 2, H); c.set_source(vgrad(c, 0, 1000, [(0, mix(D, M, 0.4)), (1, mix(A, L, 0.3))])); c.fill()
            c.set_source(rgrad(c, x0 + 640, 980, 0, 600, [(0, A, 0.8), (1, A, 0)])); c.paint()
            c.arc(x0 + 640, 980, 60, 0, 6.283); col(c, mix(A, L, 0.5)); c.fill()
            rr = ridge(99, 1000, 20, wl=900); fill_ridge(c, rr, mix(D, M, 0.3))
        else:
            c.rectangle(x0, 0, W / 2, H); c.set_source(vgrad(c, 0, 1000, [(0, mix(D, BK, 0.3)), (1, mix(G4, D, 0.2))])); c.fill()
            c.set_source(rgrad(c, x0 + 640, 980, 0, 600, [(0, mix(M, L, 0.5), 0.9), (1, M, 0)])); c.paint()
            c.arc(x0 + 640, 980, 40, 0, 6.283); col(c, mix(L, WH, 0.6)); c.fill()
            rr = ridge(97, 1000, 20, wl=900); fill_ridge(c, rr, mix(G5, D, 0.4))
        c.restore()
    c.rectangle(W / 2 - 2, 0, 4, H); col(c, D); c.fill()
    label(c, 'Dünya', W / 4, 200, 'small', L, 'c', fin(t, 0.2))
    label(c, 'Mars', 3 * W / 4, 200, 'small', L, 'c', fin(t, 0.6))


# ============================================================ 12 — deprem / göl
def quake_bed(c, t, d, **kw):
    sh = 5 * math.sin(t * 38) * (0.4 + 0.6 * abs(math.sin(t * 1.3)))
    bg_hab(c, 0.5)
    c.save(); c.translate(sh, 0)
    rrect(c, 500, 980, 1300, 180, 30); col(c, mix(M, D, 0.35)); c.fill()
    rrect(c, 520, 930, 300, 90, 30); col(c, L); c.fill()
    c.save(); c.translate(680, 860); head(c, 85, look=(1, -0.5), brow=0.9, smile=0.0, blink=blink_at(t)); c.restore()
    rrect(c, 820, 960, 960, 120, 40); col(c, mix(A, D, 0.25)); c.fill()
    rrect(c, 1900, 900, 220, 260, 12); col(c, mix(M, D, 0.4)); c.fill()
    c.save(); c.translate(2010 + sh * 2, 870); rrect(c, -40, -60, 80, 90, 10); col(c, L); c.fill(); c.restore()
    c.restore()


def insight(c, t, d, **kw):
    near = bg_mars_day(c, 59, hz=780)
    gy = ridge_y(near, 1100) + 170
    col(c, mix(L, M, 0.5))
    for k in (-1, 1):
        capsule(c, 1100 + k * 120, gy - 160, 1100 + k * 200, gy, 18)
    rrect(c, 950, gy - 260, 300, 120, 30); col(c, L); c.fill()
    for sx in (-1, 1):
        c.arc(1100 + sx * 340, gy - 220, 150, 0, 6.283); col(c, mix(A, D, 0.2)); c.fill()
        for k in range(8):
            a = k * math.pi / 4
            c.move_to(1100 + sx * 340, gy - 220); c.line_to(1100 + sx * 340 + 150 * math.cos(a), gy - 220 + 150 * math.sin(a))
        c.set_line_width(3); col(c, mix(A, L, 0.3)); c.stroke()
    c.arc(1600, gy - 10, 70, math.pi, 2 * math.pi); c.close_path(); col(c, L); c.fill()
    pts = [(1820 + k * 6, 520 + (40 * math.sin(k * 0.9) * math.exp(-((k - 30 - (t * 20) % 60) ** 2) / 50) + 4 * math.sin(k * 2.3))) for k in range(100)]
    rrect(c, 1790, 400, 660, 240, 20); col(c, mix(D, M, 0.2), 0.8); c.fill()
    line_draw(c, pts, 1, 3, L)
    label(c, '1.300+', 2120, 720, 'num', L, 'c', fin(t, 0.6), dy=14)
    label(c, 'Mars depremi', 2120, 810, 'small', L, 'c', fin(t, 0.9), dy=14)
    fg_mars(c, 59, 1240)


def jezero(c, t, d, **kw):
    p = ease((t - 0.8) / max(d - 1.5, 1))
    c.rectangle(0, 0, W, H); c.set_source(vgrad(c, 0, 600, [(0, mix(SKY_DAY_TOP, M, 0.5 * (1 - p))), (1, mix(SKY_DAY_LOW, L, 0.3 * (1 - p)))])); c.fill()
    rim = ridge(101, 560, 60, wl=1600); fill_ridge(c, rim, mix(G1, G3, 0.4))
    c.rectangle(0, 680, W, H); col(c, mix(G2, G3, 0.3)); c.fill()
    c.save(); c.translate(1280, 960); c.scale(1200, 300); c.arc(0, 0, 1, 0, 6.283); c.restore()
    col(c, mix(M, D, 0.15), 1 - p); c.fill()
    c.save(); c.translate(1280, 960); c.scale(1200, 300); c.arc(0, 0, 1, 0, 6.283); c.restore()
    col(c, mix(G2, D, 0.15), p); c.fill()
    c.move_to(300, 600)
    for k in range(20):
        c.line_to(300 + k * 30 + 40 * math.sin(k * 0.8), 600 + k * 16)
    c.set_line_width(26 * (1 - p) + 6); col(c, mix(M, D, 0.1) if p < 0.5 else mix(G3, D, 0.2)); c.stroke()
    for k in range(5):
        c.move_to(880, 920); c.line_to(880 + 200 * math.cos(-0.6 + k * 0.3), 920 + 120 * math.sin(-0.6 + k * 0.3) + 60)
    c.set_line_width(8); col(c, mix(G1, L, 0.2), 0.7); c.stroke()
    if p > 0.6:
        rover(c, 1700, 1080, 0.7, t, 0)
    label(c, 'Jezero krateri', 1280, 1260, 'small', L, 'c', fin(t, 0.4))


def mystery(c, t, d, **kw):
    mid = bg_night(c, 17, hz=940, glow=None)
    front = ridge(103, 1150, 22, wl=1900); fill_ridge(c, front, mix(G5, D, 0.5))
    character(c, 1280, ridge_y(front, 1280) + 30, 1.4, t, pose='stand', look=(0, -1), blink=blink_at(t), smile=0.6 + 0.3 * fin(t, d * 0.6), brow=0.3)


# ============================================================ 13 — keşif
def rover_drive(c, t, d, **kw):
    near = bg_mars_day(c, 61, hz=780, far_volcano=kw.get('volcano', False), sun=(2200, 240))
    x = 300 + t * 140
    gy = ridge_y(near, x) + 150
    rover(c, x, gy, 1.1, t, 140)
    c.save(); c.translate(x + 30, gy - 285); head(c, 38, blink=blink_at(t), look=(1, -0.2), smile=0.9); c.restore()
    c.save(); c.translate(x + 30, gy - 285); c.arc(0, 0, 58, 0, 6.283); c.set_line_width(6); col(c, SUIT); c.stroke(); c.restore()
    for k in range(10):
        q = (t * 1.2 + k / 10) % 1
        c.arc(x - 220 - q * 300, gy - 30 - q * 60, 20 + 40 * q, 0, 6.283); col(c, G1, 0.5 * (1 - q)); c.fill()
    fg_mars(c, 61, 1260)


def olympus(c, t, d, **kw):
    c.rectangle(0, 0, W, H); c.set_source(vgrad(c, 0, 1100, [(0, SKY_DAY_TOP), (1, SKY_DAY_LOW)])); c.fill()
    g = fin(t, 0.2, 1.4)
    c.move_to(-200, 1150); c.curve_to(500, 1050, 900, 300 + 700 * (1 - g), 1180, 300 + 700 * (1 - g))
    c.line_to(1500, 300 + 700 * (1 - g)); c.curve_to(1800, 300 + 700 * (1 - g), 2200, 1050, 2800, 1150); c.close_path()
    col(c, mix(G1, SKY_DAY_LOW, 0.2)); c.fill()
    c.move_to(1180, 300 + 700 * (1 - g)); c.curve_to(1250, 330 + 700 * (1 - g), 1430, 330 + 700 * (1 - g), 1500, 300 + 700 * (1 - g))
    c.set_line_width(5); col(c, mix(G1, D, 0.2)); c.stroke()
    if kw.get('compare'):
        e = fin(t, 1.2, 0.8)
        c.move_to(2050, 1150); c.line_to(2200, 1150 - 820 * 0.34 * e); c.line_to(2350, 1150); c.close_path(); col(c, mix(M, D, 0.2), e); c.fill()
        label(c, 'Everest', 2200, 1150 - 820 * 0.34 - 60, 'small', L, 'c', e)
        label(c, '26 km', 1340, 220, 'num', L, 'c', fin(t, 0.9), dy=14)
    near = ridge(107, 1150, 20, wl=1800); fill_ridge(c, near, G2)
    rover(c, 520, 1190, 0.35, t, 0)


def curvature(c, t, d, **kw):
    c.rectangle(0, 0, W, H); c.set_source(vgrad(c, 0, H, [(0, SKY_DAY_TOP), (1, SKY_DAY_LOW)])); c.fill()
    R = 5200
    cx, cy = 1280, 900 + R
    c.arc(cx, cy, R, 0, 6.283); col(c, G2); c.fill()
    c.save(); c.arc(cx, cy, R, 0, 6.283); c.clip()
    c.move_to(1700, 830); c.curve_to(2100, 700, 2500, 620, 2900, 560); c.line_to(2900, 1440); c.line_to(1700, 1440); c.close_path()
    col(c, G3); c.fill(); c.restore()
    c.move_to(2900, 560); c.curve_to(2700, 420, 2620, 380, 2600, 380); c.set_line_width(4); c.set_dash([10, 14]); col(c, L, 0.5 * fin(t, 0.8)); c.stroke(); c.set_dash([])
    label(c, 'tepe ufkun ardında', 2200, 300, 'small', L, 'c', fin(t, 1.0))
    character(c, 900, 900 + 30, 0.6, t, pose='stand', look=(1, -1), blink=blink_at(t))


def canyon(c, t, d, **kw):
    c.rectangle(0, 0, W, H); c.set_source(vgrad(c, 0, 700, [(0, SKY_DAY_TOP), (1, SKY_DAY_LOW)])); c.fill()
    far = ridge(111, 620, 25, wl=2000); fill_ridge(c, far, mix(G1, SKY_DAY_LOW, 0.3))
    for k, colr in enumerate([mix(G2, D, 0.15), G3, G4, G5]):
        y = 700 + k * 120
        c.move_to(-100, y); c.line_to(980 - k * 120, y); c.line_to(1080 - k * 150, H); c.line_to(-100, H); c.close_path(); col(c, colr); c.fill()
        c.move_to(W + 100, y); c.line_to(1600 + k * 120, y); c.line_to(1480 + k * 150, H); c.line_to(W + 100, H); c.close_path(); col(c, mix(colr, L, 0.08)); c.fill()
    c.rectangle(0, 680, W, 30); col(c, G2); c.fill()
    rover(c, 300 + t * 60, 700, 0.45, t, 60)
    if kw.get('labs'):
        label(c, '4.000 km', 1290, 330, 'num', L, 'c', fin(t, 0.3), dy=14)
        label(c, 'uzunluk', 1290, 420, 'small', L, 'c', fin(t, 0.5), dy=14)
        line_draw(c, [(1290, 760), (1290, 1300)], fin(t, 1.4, 0.7), 4, L)
        label(c, '7 km', 1420, 1050, 'small', L, 'l', fin(t, 1.8))


def size_compare(c, t, d, **kw):
    bg_space(c, 61, 220)
    planet(c, 900, 700, 420, 'earth', glow=0.2)
    planet(c, 1840, 700 + 420 - 223, 223, 'mars', glow=0.2)
    label(c, 'Dünya', 900, 1220, 'small', L, 'c', fin(t, 0.3))
    label(c, 'Mars', 1840, 1220, 'small', L, 'c', fin(t, 0.6))


# ============================================================ 14 — doğum günü
def birthday(c, t, d, **kw):
    bg_hab(c, 0.8, warm=0.5)
    rrect(c, 900, 1000, 760, 40, 10); col(c, mix(L, M, 0.4)); c.fill()
    rrect(c, 1080, 820, 400, 180, 30); col(c, L); c.fill()
    rrect(c, 1080, 880, 400, 30, 6); col(c, A); c.fill()
    n = kw.get('n', 1)
    for k in range(n):
        x = 1280 + (k - (n - 1) / 2) * 60
        rrect(c, x - 8, 740, 16, 80, 6); col(c, M); c.fill()
        fl = 1 + 0.15 * math.sin(t * 12 + k)
        c.save(); c.translate(x, 720); c.scale(14, 24 * fl); c.arc(0, 0, 1, 0, 6.283); c.restore(); col(c, mix(A, L, 0.5)); c.fill()
    for k, (x, st) in enumerate([(600, ABI), (1960, CREW1)]):
        character(c, x, 1280, 1.15, t, pose='stand', helmet=False, outfit='shirt', st=st, flip=k == 1, blink=blink_at(t, 3, k), smile=1.0, look=(1 if k == 0 else -1, 0))


def orbit_year(c, t, d, **kw):
    bg_space(c, 71, 180)
    cx, cy = 1280, 700
    planet(c, cx, cy, 70, 'sun', glow=1.5)
    for R, s in [(300, 0.45), (520, 0.45)]:
        c.save(); c.translate(cx, cy); c.scale(1, s); c.arc(0, 0, R, 0, 6.283); c.restore(); c.set_line_width(3); col(c, M, 0.4); c.stroke()
    ae = t * 1.2; am = t * 1.2 * 365 / 687
    planet(c, cx + 300 * math.cos(ae), cy + 300 * 0.45 * math.sin(ae), 26, 'earth')
    planet(c, cx + 520 * math.cos(am), cy + 520 * 0.45 * math.sin(am), 22, 'mars')
    label(c, kw.get('lab', '687 gün'), cx, 160, 'num', L, 'c', fin(t, 0.3), dy=14)
    label(c, kw.get('lab2', 'bir Mars yılı'), cx, 250, 'small', M, 'c', fin(t, 0.6), dy=14)


def age_card(c, t, d, **kw):
    col(c, mix(D, M, 0.15)); c.paint()
    label(c, 'Dünya', 820, 460, 'small', M, 'c', fin(t, 0.2))
    label(c, '10 yaş', 820, 580, 'num', L, 'c', fin(t, 0.3), dy=14)
    arrow(c, 1080, 580, 1480, 580, fin(t, 0.8, 0.5), L, 4, 0.12)
    label(c, 'Mars', 1740, 460, 'small', M, 'c', fin(t, 1.2))
    label(c, '5 yaş', 1740, 580, 'num', A, 'c', fin(t, 1.3), dy=14)
    planet(c, 820, 900, 90, 'earth'); planet(c, 1740, 900, 70, 'mars')


def seasons(c, t, d, **kw):
    bg_space(c, 73, 200)
    cx, cy = 1280, 700
    c.save(); c.translate(cx, cy); c.rotate(0.44)
    planet(c, 0, 0, 330, 'mars', light=(0.6, 0.0))
    cap = 0.5 + 0.5 * math.sin(t * 1.2)
    c.save(); c.arc(0, 0, 330, 0, 6.283); c.clip()
    c.save(); c.translate(0, -330); c.scale(330 * (0.3 + 0.5 * cap), 90 * (0.4 + 0.8 * cap)); c.arc(0, 0, 1, 0, 6.283); c.restore(); col(c, L, 0.9); c.fill()
    c.save(); c.translate(0, 330); c.scale(330 * (0.3 + 0.5 * (1 - cap)), 90 * (0.4 + 0.8 * (1 - cap))); c.arc(0, 0, 1, 0, 6.283); c.restore(); col(c, L, 0.9); c.fill()
    c.restore()
    c.move_to(0, -460); c.line_to(0, 460); c.set_line_width(3); c.set_dash([10, 12]); col(c, L, 0.5); c.stroke(); c.set_dash([])
    c.restore()
    label(c, 'mevsimler ~2 kat uzun', 2100, 300, 'small', L, 'c', fin(t, 0.6))


# ============================================================ 15 — dönüş
def alignment(c, t, d, **kw):
    bg_space(c, 77, 180)
    cx, cy = 1280, 720
    planet(c, cx, cy, 60, 'sun', glow=1.4)
    for R, s in [(320, 0.5), (560, 0.5)]:
        c.save(); c.translate(cx, cy); c.scale(1, s); c.arc(0, 0, R, 0, 6.283); c.restore(); c.set_line_width(3); col(c, M, 0.4); c.stroke()
    q = ease(t / max(d * 0.8, 1))
    ae = -1.3 + q * 2.5; am = -0.2 + q * 1.15
    ex, ey = cx + 320 * math.cos(ae), cy + 320 * 0.5 * math.sin(ae)
    mx, my = cx + 560 * math.cos(am), cy + 560 * 0.5 * math.sin(am)
    planet(c, ex, ey, 28, 'earth'); planet(c, mx, my, 22, 'mars')
    if q > 0.95:
        line_draw(c, [(ex, ey), (mx, my)], fin(t, d * 0.8, 0.5), 3, L, 0.9, dash=[10, 10])
    label(c, '26 ayda bir', cx, 180, 'num', L, 'c', fin(t, 0.4), dy=14)


def total_years(c, t, d, **kw):
    col(c, mix(D, M, 0.15)); c.paint()
    x0, w, y = 380, 1800, 700
    segs = [('gidiş', 0.25, M), ('Mars\'ta', 0.5, A), ('dönüş', 0.25, M)]
    x = x0
    for k, (nm, f, colr) in enumerate(segs):
        a = fin(t, 0.3 + k * 0.5, 0.6)
        rrect(c, x, y - 30, w * f * a - 8, 60, 20); col(c, colr, 0.9); c.fill()
        label(c, nm, x + w * f / 2, y + 100, 'small', L, 'c', a)
        x += w * f
    label(c, '~3 yıl', 1280, 520, 'num', L, 'c', fin(t, 1.8), dy=14)


def heavy_return(c, t, d, **kw):
    near = bg_earth_day(c, 880)
    capsule_craft(c, 1800, 1050, 1.0, rot=0.25)
    c.save(); c.translate(1800, 700); c.scale(1, 0.6)
    c.arc(0, 0, 300, math.pi, 2 * math.pi); c.close_path(); col(c, L, 0.85); c.fill(); c.restore()
    character(c, 950, 1250, 1.3, t, pose='heavy', blink=blink_at(t, 2.5), brow=0.8, smile=0.0, look=(0.3, 0.6),
              arms=(-0.05 - 0.1 * fin(t, 1.5) * math.sin(t * 2) ** 2, 0.05 + 0.25 * fin(t, 2.0) * abs(math.sin(t * 1.5))))


def grass_breath(c, t, d, **kw):
    near = bg_earth_day(c, 860)
    c.rectangle(0, 1150, W, 300); col(c, mix(M, D, 0.45)); c.fill()
    rnd = random.Random(4)
    for k in range(160):
        x = rnd.uniform(0, W); y = rnd.uniform(1120, 1440)
        sw = 8 * math.sin(t * 2 + x * 0.01)
        c.move_to(x, y); c.line_to(x + sw, y - rnd.uniform(30, 70)); c.set_line_width(5); col(c, mix(M, D, rnd.uniform(0.25, 0.55))); c.stroke()
    character(c, 1280, 1300, 1.4, t, pose='arms_up' if kw.get('arms') else 'stand', helmet=False, eyes_closed=True, smile=1.0)
    particles(c, t, 31, 40, L, 0.1, 0.3, vx=(60, 120), y0=300, y1=1200)


def blue_sky(c, t, d, **kw):
    near = bg_earth_day(c, 1100)
    character(c, 1280, 1500, 2.0, t, pose='stand', helmet=False, look=(0.5, -1), blink=blink_at(t), smile=1.0)


# ============================================================ 16 — final
def final_ticket(c, t, d, **kw):
    mid = bg_night(c, 2, glow=(1820, 930))
    tw = 0.85 + 0.15 * math.sin(t * 3)
    c.set_source(rgrad(c, 1560, 640, 0, 40, [(0, M, 0.6 * tw), (1, M, 0)])); c.paint()
    c.arc(1560, 640, 6.5, 0, 6.283); col(c, mix(M, WH, 0.5)); c.fill()
    front = ridge(41, 1140, 22, wl=1900); fill_ridge(c, front, mix(G5, D, 0.6))
    character(c, 900, ridge_y(front, 900) + 20, 1.3, t, pose='stand', helmet=False, outfit='shirt', look=(1, -0.6), blink=blink_at(t),
              arms=(-0.15, 1.2), smile=0.8, wave=0)
    c.save(); c.translate(900 + 1.3 * 60 * 1.9, ridge_y(front, 900) + 20 - 1.3 * 60 * 3.5); c.rotate(-0.3)
    rrect(c, -80, -40, 160, 80, 10); col(c, L); c.fill(); c.rectangle(-80, -40, 24, 80); col(c, A); c.fill(); c.restore()


def next_ep(c, t, d, **kw):
    c.rectangle(0, 0, W, H); c.set_source(vgrad(c, 0, H, [(0, mix(D, BK, 0.4)), (1, mix(D, M, 0.2))])); c.fill()
    stars(c, 81, 160, 700, 0.6)
    c.rectangle(0, 980, W, 460); col(c, mix(D, M, 0.12)); c.fill()
    x = 1280 + 40 * math.sin(t * 0.3)
    c.move_to(x - 700, 900); c.line_to(x + 760, 900); c.line_to(x + 640, 1040); c.line_to(x - 620, 1040); c.close_path(); col(c, mix(D, BK, 0.3)); c.fill()
    c.rectangle(x - 560, 820, 1180, 80); col(c, mix(L, M, 0.4)); c.fill()
    for k in range(4):
        rrect(c, x - 360 + k * 260, 640, 110, 190, 10); col(c, mix(D, BK, 0.2) if k < 3 else mix(D, BK, 0.2)); c.fill()
        c.rectangle(x - 360 + k * 260, 640, 110, 45); col(c, mix(A, D, 0.3) if True else D); c.fill()
    for k in range(18):
        c.arc(x - 520 + k * 62, 860, 9, 0, 6.283); col(c, mix(A, L, 0.4), 0.9); c.fill()
    for k in range(6):
        c.move_to(x - 650 + k * 260, 1060); c.line_to(x - 500 + k * 260, 1060); c.set_line_width(4); col(c, L, 0.15); c.stroke()


def mars_pad(c, t, d, **kw):
    near = bg_mars_day(c, 63, hz=780, sun=(500, 320))
    gy = ridge_y(near, 1750) + 160
    rrect(c, 1450, gy - 20, 600, 50, 10); col(c, mix(M, D, 0.35)); c.fill()
    rocket(c, 1750, gy - 640, 1.25)
    col(c, mix(D, M, 0.35)); c.rectangle(2020, gy - 700, 50, 700); c.fill()
    fg_mars(c, 63)
    x = 600 + t * 50
    character(c, x, ridge_y(near, x) + 190, 1.0, t, pose='walk', walk=t * 0.6, blink=blink_at(t), look=(1, -0.3))
