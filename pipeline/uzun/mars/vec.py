"""Mars bölümü için düz vektör 2D çizim kütüphanesi (pycairo). Bütün renkler uzun video paletinin karışımı."""
import math, random
import cairo
import numpy as np
from PIL import Image

W, H = 2560, 1440


def hx(s):
    s = s.lstrip('#'); return tuple(int(s[i:i + 2], 16) / 255 for i in (0, 2, 4))


D, L, M, A = hx('0F1A24'), hx('E8E4DA'), hx('8FA9B8'), hx('C9693C')
WH, BK = (1, 1, 1), (0, 0, 0)


def mix(a, b, t):
    return tuple(a[i] * (1 - t) + b[i] * t for i in range(3))


# türetilmiş tonlar
SKY_DAY_TOP = mix(mix(A, D, 0.35), L, 0.25)
SKY_DAY_LOW = mix(A, L, 0.62)
G1 = mix(A, L, 0.25)            # uzak zemin
G2 = A
G3 = mix(A, D, 0.28)
G4 = mix(A, D, 0.5)
G5 = mix(A, D, 0.68)
SKIN = mix(L, A, 0.28)
SKIN_SH = mix(SKIN, A, 0.35)
BEARD = mix(D, A, 0.32)
CAP = mix(D, M, 0.18)
SUIT = L
SUIT_SH = mix(L, M, 0.45)
SUIT_DK = mix(M, D, 0.35)
INK = mix(D, BK, 0.2)


def surface():
    s = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    return s, cairo.Context(s)


def to_pil(s):
    a = np.ndarray((H, W, 4), np.uint8, s.get_data()).copy()
    return Image.fromarray(a[..., [2, 1, 0]], 'RGB')


def col(c, rgb, a=1.0):
    c.set_source_rgba(*rgb, a)


def vgrad(c, y0, y1, stops):
    g = cairo.LinearGradient(0, y0, 0, y1)
    for p, rgb, *al in stops:
        g.add_color_stop_rgba(p, *rgb, al[0] if al else 1)
    return g


def rgrad(c, x, y, r0, r1, stops):
    g = cairo.RadialGradient(x, y, r0, x, y, r1)
    for p, rgb, *al in stops:
        g.add_color_stop_rgba(p, *rgb, al[0] if al else 1)
    return g


def rrect(c, x, y, w, h, r):
    r = min(r, w / 2, h / 2)
    c.new_sub_path()
    c.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    c.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    c.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    c.arc(x + r, y + r, r, math.pi, 1.5 * math.pi)
    c.close_path()


def capsule(c, x0, y0, x1, y1, w):
    c.save()
    c.set_line_cap(cairo.LINE_CAP_ROUND)
    c.set_line_width(w)
    c.move_to(x0, y0); c.line_to(x1, y1); c.stroke()
    c.restore()


def ridge(seed, y, amp, n=6, wl=900, x0=-100, x1=W + 100, step=12):
    rnd = random.Random(seed)
    comps = [(amp * rnd.uniform(0.3, 1) / (k + 1) ** 0.7, wl / (k + 1) * rnd.uniform(0.8, 1.2), rnd.uniform(0, 6.28)) for k in range(n)]
    pts = []
    for x in range(x0, x1 + step, step):
        pts.append((x, y + sum(a * math.sin(x / w * 6.283 + p) for a, w, p in comps)))
    return pts


def fill_ridge(c, pts, rgb, a=1.0, bottom=H + 10):
    c.move_to(pts[0][0], bottom)
    for x, y in pts:
        c.line_to(x, y)
    c.line_to(pts[-1][0], bottom); c.close_path()
    col(c, rgb, a); c.fill()


def ridge_y(pts, x):
    for (xa, ya), (xb, yb) in zip(pts, pts[1:]):
        if xa <= x <= xb:
            return ya + (yb - ya) * (x - xa) / (xb - xa)
    return pts[-1][1]


def rock(c, x, y, r, rgb, seed=0, light=0.18):
    rnd = random.Random(seed)
    n = 7
    pts = []
    for k in range(n):
        a = math.pi + k * math.pi / (n - 1)
        rr = r * rnd.uniform(0.75, 1.1)
        pts.append((x + math.cos(a) * rr * 1.25, y + math.sin(a) * rr * 0.8))
    c.move_to(*pts[0])
    for p in pts[1:]:
        c.line_to(*p)
    c.close_path(); col(c, rgb); c.fill_preserve()
    c.save(); c.clip()
    c.move_to(x - r * 2, y - r * 2); c.line_to(x + r * 0.1, y - r * 2); c.line_to(x - r * 0.3, y + r); c.line_to(x - r * 2, y + r)
    col(c, mix(rgb, L, light)); c.fill()
    c.restore()


def stars(c, seed, n, ymax, a=0.9):
    rnd = random.Random(seed)
    for _ in range(n):
        x, y = rnd.uniform(0, W), rnd.uniform(0, ymax)
        r = rnd.choice([1.2, 1.6, 2.0, 2.6, 3.4])
        col(c, L, a * rnd.uniform(0.35, 1) * (1 - y / ymax * 0.6))
        c.arc(x, y, r, 0, 6.283); c.fill()


# ------------------------------------------------------------------ karakter
ABI = dict(beard=True, cap=True, hair=None, skin=SKIN, hairc=BEARD, capc=CAP)
CREW1 = dict(beard=False, cap=False, hair='short', skin=mix(L, A, 0.42), hairc=mix(D, BK, 0.3), capc=CAP)
CREW2 = dict(beard=False, cap=False, hair='bun', skin=mix(L, A, 0.18), hairc=mix(A, D, 0.45), capc=CAP)


def head(c, R, blink=0.0, look=(0, 0), mouth=0.0, smile=0.6, brow=0.0, st=ABI, eyes_closed=False):
    skin = st['skin']; skin_sh = mix(skin, A, 0.35); hc = st['hairc']
    if st['hair'] == 'bun':
        c.arc(0, -R * 1.05, R * 0.42, 0, 6.283); col(c, hc); c.fill()
    for sx in (-1, 1):
        c.arc(sx * R * 0.98, R * 0.08, R * 0.2, 0, 6.283); col(c, skin_sh); c.fill()
    c.arc(0, 0, R, 0, 6.283); col(c, skin); c.fill()
    c.save(); c.arc(0, 0, R, 0, 6.283); c.clip()
    c.arc(R * 0.35, R * 0.25, R * 0.9, 0, 6.283); col(c, skin_sh, 0.22); c.fill()
    if st['beard']:
        c.move_to(-R * 1.05, -R * 0.05)
        c.curve_to(-R * 0.9, R * 0.45, -R * 0.55, R * 0.3, -R * 0.25, R * 0.32)
        c.curve_to(-R * 0.1, R * 0.26, R * 0.1, R * 0.26, R * 0.25, R * 0.32)
        c.curve_to(R * 0.55, R * 0.3, R * 0.9, R * 0.45, R * 1.05, -R * 0.05)
        c.line_to(R * 1.1, R * 1.2); c.line_to(-R * 1.1, R * 1.2); c.close_path()
        col(c, hc); c.fill()
    if st['hair'] in ('short', 'bun'):
        c.move_to(-R * 1.1, R * 0.05)
        c.curve_to(-R * 1.1, -R * 1.4, R * 1.1, -R * 1.4, R * 1.1, R * 0.05)
        c.curve_to(R * 0.9, -R * 0.45, R * 0.2, -R * 0.62, -R * 0.2, -R * 0.5)
        c.curve_to(-R * 0.6, -R * 0.42, -R * 0.95, -R * 0.4, -R * 1.1, R * 0.05)
        c.close_path(); col(c, hc); c.fill()
    c.restore()
    c.save(); c.translate(R * 0.02, R * 0.2); c.scale(R * 0.16, R * 0.12); c.arc(0, 0, 1, 0, 6.283); c.restore()
    col(c, skin_sh); c.fill()
    mw, my = R * 0.34, R * 0.5
    if mouth > 0.05:
        c.save(); c.translate(0, my); c.scale(1, 0.35 + mouth * 0.9)
        c.arc(0, 0, mw * 0.7, 0, math.pi); c.close_path(); c.restore()
        col(c, mix(D, A, 0.3)); c.fill()
    else:
        c.move_to(-mw, my - R * 0.02)
        c.curve_to(-mw * 0.4, my + R * 0.16 * smile, mw * 0.4, my + R * 0.16 * smile, mw, my - R * 0.02)
        c.set_line_width(R * 0.07); c.set_line_cap(cairo.LINE_CAP_ROUND); col(c, mix(skin, D, 0.25)); c.stroke()
    lx, ly = look
    for sx in (-1, 1):
        ex, ey = sx * R * 0.36 + lx * R * 0.08, -R * 0.08 + ly * R * 0.06
        if eyes_closed:
            c.arc(ex, ey - R * 0.02, R * 0.1, 0.15 * math.pi, 0.85 * math.pi)
            c.set_line_width(R * 0.06); col(c, INK); c.stroke()
        else:
            h = R * 0.17 * (1 - 0.92 * blink)
            c.save(); c.translate(ex, ey); c.scale(R * 0.12, max(h, R * 0.015)); c.arc(0, 0, 1, 0, 6.283); c.restore()
            col(c, INK); c.fill()
            if blink < 0.5:
                c.arc(ex + R * 0.04, ey - h * 0.4, R * 0.035, 0, 6.283); col(c, WH, 0.9); c.fill()
        c.move_to(sx * R * 0.18, -R * 0.36 - brow * R * 0.1)
        c.line_to(sx * R * 0.56, -R * 0.40 - brow * R * 0.12 + R * 0.04)
        c.set_line_width(R * (0.11 if st['beard'] else 0.08)); c.set_line_cap(cairo.LINE_CAP_ROUND); col(c, hc); c.stroke()
    if st['cap']:
        c.move_to(-R * 1.04, -R * 0.38)
        c.curve_to(-R * 1.0, -R * 1.35, R * 1.0, -R * 1.35, R * 1.04, -R * 0.38)
        c.curve_to(R * 0.5, -R * 0.52, -R * 0.5, -R * 0.52, -R * 1.04, -R * 0.38)
        c.close_path(); col(c, st['capc']); c.fill()
        c.move_to(-R * 0.3, -R * 0.47)
        c.curve_to(-R * 0.28, -R * 0.72, R * 0.28, -R * 0.72, R * 0.3, -R * 0.47)
        c.close_path(); col(c, hc); c.fill()
        c.move_to(-R * 0.34, -R * 0.66); c.line_to(R * 0.34, -R * 0.66)
        c.set_line_width(R * 0.07); col(c, mix(st['capc'], L, 0.25)); c.stroke()
        c.arc(0, -R * 1.1, R * 0.08, 0, 6.283); col(c, mix(st['capc'], L, 0.2)); c.fill()


def cap_brim_back(c, R, capc=CAP):
    c.save(); c.translate(R * 0.75, -R * 0.62); c.rotate(-0.55)
    c.scale(R * 0.62, R * 0.2); c.arc(0, 0, 1, 0, 6.283); c.restore()
    col(c, mix(capc, D, 0.3)); c.fill()


POSES = {  # (sol bacak, sağ bacak, sol kol, sağ kol, gövde inişi)
    'stand': (0.05, -0.05, -0.15, 0.15, 0),
    'arms_up': (0.12, -0.12, -2.5, 2.5, 0),
    'point': (0.05, -0.05, -0.15, 1.75, 0),
    'reach': (0.05, -0.05, -1.2, 1.3, 0),
    'hold': (0.05, -0.05, -1.0, 1.0, 0),
    'crouch': (0.75, -0.75, -0.9, 0.9, 0.55),
    'heavy': (0.08, -0.08, -0.05, 0.05, 0.12),
    'jump': (0.55, -0.35, -2.3, 2.1, 0),
    'kick': (0.0, -1.1, -0.7, 0.6, 0),
    'sit': (1.35, 1.25, 0.5, -0.4, 0.9),
    'float': (0.25, -0.35, -1.9, 1.6, 0),
}


def character(c, x, y, s=1.0, t=0.0, pose='stand', helmet=True, blink=0.0, look=(0, 0), mouth=0.0, flip=False, rot=0.0,
              wave=0.0, walk=0.0, smile=0.6, brow=0.0, st=ABI, outfit='suit', arms=None, eyes_closed=False, legs=None):
    """Ayaklar (x,y). R=60*s. outfit: suit | shirt"""
    R = 60
    c.save(); c.translate(x, y); c.rotate(rot); c.scale(-s if flip else s, s)
    if pose == 'walk':
        ph = walk * 2 * math.pi
        la, ra = 0.42 * math.sin(ph), -0.42 * math.sin(ph)
        aa, ab = -0.5 * math.sin(ph), 0.5 * math.sin(ph)
        bob = -abs(math.cos(ph)) * R * 0.12
    else:
        la, ra, aa, ab, bob = POSES[pose]
        bob *= R
        if pose == 'float':
            la += 0.1 * math.sin(t * 1.3); ra += 0.1 * math.sin(t * 1.1)
            aa += 0.15 * math.sin(t * 1.4); ab += 0.15 * math.sin(t * 1.2)
        if wave:
            ab = 0.15 + wave * (2.3 + 0.25 * math.sin(t * 9))
    if arms:
        aa, ab = arms
    if legs:
        la, ra = legs
    c.translate(0, bob)
    hipy, shy = -2.1 * R, -3.95 * R
    shirt = outfit == 'shirt'
    body, body_sh = (A, mix(A, D, 0.25)) if shirt else (SUIT, SUIT_SH)
    legc, legc_sh = (mix(D, M, 0.35), mix(D, M, 0.2)) if shirt else (SUIT, SUIT_SH)
    boot = mix(D, A, 0.25) if shirt else SUIT_DK
    hand = st['skin'] if shirt else SUIT_DK
    if helmet and not shirt:
        rrect(c, -1.22 * R, -4.35 * R, 2.44 * R, 2.2 * R, 0.4 * R); col(c, SUIT_DK); c.fill()

    def leg(ang, front):
        lx = 0.42 * R * (1 if front else -1)
        L1 = 2.0 * R
        if pose == 'sit':
            ex, ey = lx + L1 * 0.95, hipy + R * 0.25
            col(c, legc if front else legc_sh)
            capsule(c, lx, hipy, ex, ey, 0.7 * R)
            capsule(c, ex, ey, ex + R * 0.1, ey + 1.7 * R, 0.62 * R)
            rrect(c, ex - 0.35 * R, ey + 1.55 * R, 0.95 * R, 0.5 * R, 0.22 * R); col(c, boot); c.fill()
            return
        if pose == 'crouch':
            kx, ky = lx + (0.9 if front else -0.9) * R * 0.6, hipy + R * 0.95
            ex, ey = lx + (0.3 if front else -0.3) * R, hipy + 2.0 * R - bob
            col(c, legc if front else legc_sh)
            capsule(c, lx, hipy, kx, ky, 0.72 * R); capsule(c, kx, ky, ex, ey - 0.15 * R, 0.68 * R)
            rrect(c, ex - 0.42 * R, ey - 0.45 * R, 0.98 * R, 0.55 * R, 0.24 * R); col(c, boot); c.fill()
            return
        ex, ey = lx + math.sin(ang) * L1, hipy + math.cos(ang) * L1
        col(c, legc if front else legc_sh)
        capsule(c, lx, hipy, ex, ey - 0.15 * R, 0.72 * R)
        c.save(); c.translate(ex, ey - 0.17 * R); c.rotate(-ang * 0.6)
        rrect(c, -0.42 * R, -0.28 * R, 0.98 * R, 0.55 * R, 0.24 * R); col(c, boot); c.fill(); c.restore()

    def arm(ang, side, front):
        sx = side * 0.98 * R
        L1 = 1.85 * R
        ex, ey = sx + math.sin(ang) * L1, shy + math.cos(ang) * L1
        col(c, body if front else body_sh)
        capsule(c, sx, shy, ex, ey, 0.56 * R)
        c.arc(ex, ey, 0.33 * R if not shirt else 0.27 * R, 0, 6.283); col(c, hand); c.fill()

    leg(ra, False)
    arm(ab, 1, False)
    leg(la, True)
    rrect(c, -1.0 * R, -4.35 * R, 2.0 * R, 2.45 * R, 0.62 * R); col(c, body); c.fill()
    c.save(); rrect(c, -1.0 * R, -4.35 * R, 2.0 * R, 2.45 * R, 0.62 * R); c.clip()
    rrect(c, 0.25 * R, -4.6 * R, 1.2 * R, 3 * R, 0.3 * R); col(c, body_sh, 0.55); c.fill()
    if shirt:
        for k in range(5):
            c.rectangle(-1.2 * R + k * 0.55 * R, -4.6 * R, 0.12 * R, 3 * R); col(c, mix(A, D, 0.35), 0.45); c.fill()
        c.rectangle(-1.2 * R, -3.6 * R, 2.5 * R, 0.1 * R); col(c, mix(A, D, 0.35), 0.4); c.fill()
        c.rectangle(-1.2 * R, -2.8 * R, 2.5 * R, 0.1 * R); col(c, mix(A, D, 0.35), 0.4); c.fill()
        c.move_to(-0.35 * R, -4.4 * R); c.line_to(0, -3.75 * R); c.line_to(0.35 * R, -4.4 * R); c.close_path()
        col(c, L); c.fill()
    c.restore()
    if not shirt:
        rrect(c, -1.0 * R, -2.45 * R, 2.0 * R, 0.32 * R, 0.1 * R); col(c, SUIT_DK); c.fill()
        rrect(c, -0.55 * R, -3.75 * R, 0.85 * R, 0.62 * R, 0.12 * R); col(c, mix(M, D, 0.15)); c.fill()
        c.arc(-0.3 * R, -3.44 * R, 0.09 * R, 0, 6.283); col(c, A); c.fill()
        c.arc(0.02 * R, -3.44 * R, 0.09 * R, 0, 6.283); col(c, L); c.fill()
    arm(aa, -1, True)
    if not shirt:
        c.save(); c.translate(0, -4.32 * R); c.scale(1.05 * R, 0.3 * R); c.arc(0, 0, 1, 0, 6.283); c.restore()
        col(c, SUIT_DK); c.fill()
    c.save(); c.translate(0, -5.25 * R)
    if helmet:
        c.arc(0, 0, 1.5 * R, 0, 6.283); col(c, mix(M, D, 0.55)); c.fill()
    elif st['cap']:
        cap_brim_back(c, R, st['capc'])
    head(c, R, blink=blink, look=look, mouth=mouth, smile=smile, brow=brow, st=st, eyes_closed=eyes_closed)
    if helmet:
        c.arc(0, 0, 1.5 * R, 0, 6.283); col(c, M, 0.16); c.fill()
        c.arc(0, 0, 1.5 * R, 0, 6.283); c.set_line_width(0.16 * R); col(c, SUIT); c.stroke()
        c.set_line_cap(cairo.LINE_CAP_ROUND)
        c.arc(0, 0, 1.24 * R, math.radians(200), math.radians(255)); c.set_line_width(0.11 * R); col(c, WH, 0.75); c.stroke()
        c.arc(0, 0, 1.24 * R, math.radians(262), math.radians(270)); col(c, WH, 0.75); c.stroke()
    c.restore()
    c.restore()


def avatar(c, cx, cy, r, mouth=0.0, blink=0.0):
    c.save()
    c.arc(cx + 3, cy + 5, r + 5, 0, 6.283); col(c, BK, 0.28); c.fill()
    c.arc(cx, cy, r + 5, 0, 6.283); col(c, M); c.fill()
    c.arc(cx, cy, r, 0, 6.283); col(c, mix(D, M, 0.25)); c.fill()
    c.arc(cx, cy, r, 0, 6.283); c.clip()
    c.save(); c.translate(cx, cy + r * 1.08); c.scale(r * 0.95, r * 0.55); c.arc(0, 0, 1, 0, 6.283); c.restore()
    col(c, A); c.fill()
    c.save(); c.translate(cx, cy - r * 0.02)
    hr = r * 0.52
    cap_brim_back(c, hr)
    head(c, hr, blink=blink, mouth=mouth, smile=0.8)
    c.restore()
    c.restore()


# ------------------------------------------------------------------ nesneler
def planet(c, x, y, r, kind='mars', light=(-0.5, -0.4), glow=0.0):
    base = {'mars': A, 'earth': mix(M, D, 0.05), 'moon': mix(L, M, 0.35), 'sun': mix(L, WH, 0.6)}[kind]
    if glow:
        c.set_source(rgrad(c, x, y, r, r * (1 + glow), [(0, base, 0.35), (1, base, 0)])); c.paint()
    c.arc(x, y, r, 0, 6.283); col(c, base); c.fill()
    if kind == 'sun':
        return
    c.save(); c.arc(x, y, r, 0, 6.283); c.clip()
    rnd = random.Random(hash(kind) % 1000)
    if kind == 'mars':
        for _ in range(7):
            ax, ay, ar = rnd.uniform(-0.8, 0.8), rnd.uniform(-0.7, 0.7), rnd.uniform(0.12, 0.3)
            c.save(); c.translate(x + ax * r, y + ay * r); c.scale(ar * r * 1.6, ar * r * 0.7); c.arc(0, 0, 1, 0, 6.283); c.restore()
            col(c, mix(A, D, 0.3), 0.55); c.fill()
        c.save(); c.translate(x, y - r * 0.93); c.scale(r * 0.35, r * 0.1); c.arc(0, 0, 1, 0, 6.283); c.restore()
        col(c, L, 0.85); c.fill()
    elif kind == 'earth':
        for (ax, ay, ar) in [(-0.3, -0.25, 0.42), (0.35, 0.3, 0.32), (-0.1, 0.55, 0.22), (0.5, -0.45, 0.18)]:
            c.save(); c.translate(x + ax * r, y + ay * r); c.scale(ar * r, ar * r * 0.62); c.arc(0, 0, 1, 0, 6.283); c.restore()
            col(c, mix(M, L, 0.55)); c.fill()
    elif kind == 'moon':
        for _ in range(5):
            c.arc(x + rnd.uniform(-0.6, 0.6) * r, y + rnd.uniform(-0.6, 0.6) * r, rnd.uniform(0.08, 0.2) * r, 0, 6.283)
            col(c, mix(M, D, 0.2), 0.5); c.fill()
    lx, ly = light
    c.arc(x - lx * r * 0.9, y - ly * r * 0.9, r * 1.05, 0, 6.283); col(c, D, 0.38); c.fill()
    c.restore()


def rocket(c, x, y, s=1.0, flame=0.0, t=0.0, rot=0.0):
    """burun (x,y)'den aşağı; boy ~ 520*s"""
    c.save(); c.translate(x, y); c.rotate(rot); c.scale(s, s)
    if flame > 0:
        fl = 1 + 0.12 * math.sin(t * 40) + 0.08 * math.sin(t * 23)
        for k, (w, h, colr, a) in enumerate([(80, 300, A, 0.9), (55, 220, mix(A, L, 0.5), 0.95), (30, 140, L, 1)]):
            c.move_to(-w, 470); c.curve_to(-w, 470 + h * 0.5 * fl * flame, 0, 470 + h * fl * flame, 0, 470 + h * fl * flame)
            c.curve_to(0, 470 + h * fl * flame, w, 470 + h * 0.5 * fl * flame, w, 470); c.close_path()
            col(c, colr, a); c.fill()
    for sx in (-1, 1):
        c.move_to(sx * 75, 300); c.line_to(sx * 170, 470); c.line_to(sx * 75, 450); c.close_path(); col(c, mix(A, D, 0.15)); c.fill()
    c.move_to(0, 0); c.curve_to(75, 60, 95, 160, 95, 260); c.line_to(95, 470); c.line_to(-95, 470); c.line_to(-95, 260)
    c.curve_to(-95, 160, -75, 60, 0, 0); c.close_path(); col(c, L); c.fill()
    c.save(); c.move_to(0, 0); c.curve_to(75, 60, 95, 160, 95, 260); c.line_to(95, 470); c.line_to(20, 470); c.line_to(20, 0); c.close_path()
    col(c, SUIT_SH, 0.6); c.fill(); c.restore()
    c.move_to(0, 0); c.curve_to(45, 35, 62, 75, 70, 110); c.line_to(-70, 110); c.curve_to(-62, 75, -45, 35, 0, 0); c.close_path()
    col(c, A); c.fill()
    c.arc(0, 220, 40, 0, 6.283); col(c, mix(M, D, 0.25)); c.fill()
    c.arc(0, 220, 40, 0, 6.283); c.set_line_width(12); col(c, SUIT_DK); c.stroke()
    c.arc(-10, 210, 12, 0, 6.283); col(c, WH, 0.35); c.fill()
    rrect(c, -95, 470, 190, 30, 6); col(c, SUIT_DK); c.fill()
    c.restore()


def capsule_craft(c, x, y, s=1.0, rot=0.0, heat=0.0, t=0.0):
    c.save(); c.translate(x, y); c.rotate(rot); c.scale(s, s)
    if heat > 0:
        for k in range(4):
            c.move_to(-190, 40); c.curve_to(-110, 150 + 40 * k, 110, 150 + 40 * k, 190, 40)
            col(c, mix(A, L, k * 0.25), heat * (0.6 - k * 0.1)); c.fill()
        c.move_to(-170, 40)
        for k in range(14):
            xx = -170 + k * 26
            c.line_to(xx * 1.4, -160 - (700 + 200 * math.sin(k * 2.1 + t * 18)) * heat * (0.3 + 0.7 * random.Random(k).random()))
        c.line_to(170, 40); c.close_path(); col(c, mix(A, L, 0.25), 0.22 * heat); c.fill()
    c.move_to(-100, -160); c.line_to(100, -160); c.line_to(170, 40); c.line_to(-170, 40); c.close_path(); col(c, L); c.fill()
    c.move_to(20, -160); c.line_to(100, -160); c.line_to(170, 40); c.line_to(60, 40); c.close_path(); col(c, SUIT_SH, 0.6); c.fill()
    rrect(c, -60, -200, 120, 44, 10); col(c, SUIT_SH); c.fill()
    c.arc(-20, -70, 34, 0, 6.283); col(c, mix(M, D, 0.25)); c.fill()
    c.save(); c.translate(0, 40); c.scale(180, 42); c.arc(0, 0, 1, 0, math.pi); c.restore()
    col(c, mix(A, D, 0.2) if heat < 0.3 else mix(A, L, 0.35)); c.fill()
    c.restore()


def dome(c, x, y, r, light=1.0, door=True, glow=True):
    c.arc(x, y, r, math.pi, 2 * math.pi); c.close_path(); col(c, mix(M, D, 0.45)); c.fill()
    c.save(); c.arc(x, y, r, math.pi, 2 * math.pi); c.close_path(); c.clip()
    c.arc(x - r * 0.35, y - r * 0.2, r * 0.9, 0, 6.283); col(c, mix(M, L, 0.2), 0.25); c.fill()
    c.restore()
    for a in (200, 230, 260, 290, 320):
        c.move_to(x, y); c.line_to(x + r * math.cos(math.radians(a)), y + r * math.sin(math.radians(a)))
    c.set_line_width(max(2, r * 0.016)); col(c, mix(M, D, 0.25)); c.stroke()
    c.arc(x, y, r, math.pi, 2 * math.pi); c.set_line_width(max(3, r * 0.03)); col(c, mix(M, L, 0.2)); c.stroke()
    if glow and light > 0:
        c.set_source(rgrad(c, x + r * 0.25, y - r * 0.35, 0, r * 0.85, [(0, A, 0.45 * light), (1, A, 0)])); c.paint()
        rrect(c, x + r * 0.08, y - r * 0.46, r * 0.35, r * 0.23, r * 0.05); col(c, mix(A, L, 0.35), light); c.fill()
    if door:
        rrect(c, x - r * 0.5, y - r * 0.35, r * 0.27, r * 0.35, r * 0.06); col(c, mix(M, D, 0.7)); c.fill()


def rover(c, x, y, s=1.0, t=0.0, speed=0.0, panels=True, box_glow=0.0, dust=0.0):
    """tekerlek altı (x,y)"""
    c.save(); c.translate(x, y); c.scale(s, s)
    if panels:
        c.move_to(-230, -205); c.line_to(230, -205); c.line_to(250, -185); c.line_to(-250, -185); c.close_path()
        col(c, mix(M, D, 0.55)); c.fill()
        for k in range(-4, 5):
            c.move_to(k * 52, -205); c.line_to(k * 55, -185)
        c.set_line_width(3); col(c, mix(M, L, 0.3), 0.5); c.stroke()
        if dust > 0:
            c.move_to(-230, -205); c.line_to(230, -205); c.line_to(250, -185); c.line_to(-250, -185); c.close_path()
            col(c, G1, dust); c.fill()
    rrect(c, -170, -185, 340, 95, 18); col(c, L); c.fill()
    rrect(c, 20, -185, 150, 95, 18); col(c, SUIT_SH, 0.7); c.fill()
    rrect(c, -150, -170, 110, 60, 10); col(c, mix(M, D, 0.2)); c.fill()
    if box_glow:
        c.set_source(rgrad(c, -95, -140, 0, 160, [(0, L, 0.6 * box_glow), (1, L, 0)])); c.paint()
        rrect(c, -150, -170, 110, 60, 10); col(c, mix(M, L, 0.5), box_glow); c.fill()
    capsule(c, 120, -185, 140, -300, 12); c.set_source_rgb(*SUIT_DK)
    col(c, SUIT_DK); capsule(c, 120, -185, 140, -300, 12)
    rrect(c, 105, -340, 80, 50, 12); col(c, L); c.fill()
    c.arc(160, -315, 12, 0, 6.283); col(c, D); c.fill()
    for wx in (-130, 0, 130):
        col(c, SUIT_DK); capsule(c, wx, -90, wx, -40, 14)
        c.arc(wx, -38, 38, 0, 6.283); col(c, mix(D, M, 0.3)); c.fill()
        c.arc(wx, -38, 16, 0, 6.283); col(c, mix(M, L, 0.2)); c.fill()
        a = -t * speed / 38
        c.move_to(wx, -38); c.line_to(wx + 30 * math.cos(a), -38 + 30 * math.sin(a)); c.set_line_width(5); col(c, mix(M, L, 0.2)); c.stroke()
    c.restore()


def dog(c, x, y, s=1.0, t=0.0):
    c.save(); c.translate(x, y); c.scale(s, s)
    dc, dk = mix(A, L, 0.45), mix(A, D, 0.25)
    col(c, dc)
    for lx in (-50, -30, 30, 50):
        capsule(c, lx, -60, lx, -8, 16)
    rrect(c, -75, -110, 150, 65, 32); col(c, dc); c.fill()
    capsule(c, -70, -95, -105, -135 - 8 * math.sin(t * 10), 12)
    c.arc(80, -125, 40, 0, 6.283); col(c, dc); c.fill()
    c.save(); c.translate(70, -150); c.rotate(0.5); c.scale(14, 28); c.arc(0, 0, 1, 0, 6.283); c.restore(); col(c, dk); c.fill()
    c.arc(118, -118, 10, 0, 6.283); col(c, D); c.fill()
    c.arc(92, -132, 6, 0, 6.283); col(c, D); c.fill()
    c.restore()


def plant(c, x, y, s=1.0, grow=1.0, kind='lettuce'):
    c.save(); c.translate(x, y); c.scale(s * grow, s * grow)
    g1, g2 = mix(M, L, 0.15), mix(M, D, 0.2)
    if kind == 'lettuce':
        for k, a in enumerate([-1.2, -0.6, 0, 0.6, 1.2]):
            c.save(); c.rotate(a * 0.8); c.translate(0, -45); c.scale(28, 50); c.arc(0, 0, 1, 0, 6.283); c.restore()
            col(c, g1 if k % 2 else g2); c.fill()
    else:
        col(c, g2); capsule(c, 0, 0, 0, -110, 8)
        for k in range(3):
            c.save(); c.translate((-1) ** k * 26, -40 - k * 30); c.rotate((-1) ** k * 0.6); c.scale(30, 13); c.arc(0, 0, 1, 0, 6.283); c.restore()
            col(c, g1); c.fill()
    c.restore()


def dust_wall(c, x, h, a=1.0, t=0.0):
    """x: duvarın önü (sola doğru ilerler); kabaran toz bulutları"""
    dk, mid = mix(A, D, 0.5), mix(A, D, 0.32)
    c.rectangle(x + 250, H - h + 120, W + 400, h + 10); col(c, dk, a); c.fill()
    for k, xx in enumerate(range(int(x) + 200, W + 300, 170)):
        rnd = random.Random(300 + k)
        c.arc(xx, H - h + 130 + rnd.uniform(-60, 60), rnd.uniform(140, 210) * (1 + 0.04 * math.sin(t + k)), 0, 6.283)
        col(c, mix(dk, mid, rnd.random() * 0.5), a); c.fill()
    for k in range(26):
        rnd = random.Random(k)
        yy = H - rnd.uniform(0, h * 1.02)
        r = rnd.uniform(90, 230)
        xx = x + rnd.uniform(0, 320) + 30 * math.sin(t * 0.8 + k)
        c.arc(xx, yy, r * (1 + 0.04 * math.sin(t * 1.3 + k)), 0, 6.283)
        col(c, mix(mid, dk, rnd.random() * 0.6), a); c.fill()
    for k in range(10):
        rnd = random.Random(100 + k)
        c.arc(x + rnd.uniform(-60, 120), H - rnd.uniform(0, h * 0.9), rnd.uniform(60, 140), 0, 6.283)
        col(c, mix(A, L, 0.15), 0.35 * a); c.fill()
