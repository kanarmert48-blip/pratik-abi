"""Tam boy Pratik Abi: beden sabit, sadece yüz canlı (dudak, göz kırpma, bakış, kaş/göz/ağız ifadeleri).
Kaynak: assets/abi_rig/kapali_rgba.png (ağız kapalı, arka plan temiz) + acik.jpg (ağız açık, aynı hizada)."""
import math
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

RIG = Path(__file__).resolve().parent.parent / "assets" / "abi_rig"

# yüz ifadeleri (piksel/oran, kaynak görüntü ölçeğinde)
EXPR = {
    "normal":   {},
    "mutlu":    {"smile": 5.0, "brow_l": 2.0, "brow_r": 2.0},
    "komik":    {"smile": 4.5, "brow_r": 8.0, "brow_l": -2.0},                        # tek kaş havada, muzip
    "merak":    {"brow_l": 4.0, "brow_r": 8.0, "gx": 0.55, "gy": -0.45},              # meraklı, görsele bakar
    "soru":     {"brow_l": 4.0, "brow_r": 8.0, "smile": 1.5},                         # izleyiciye soran bakış
    "yukari":   {"gx": 0.15, "gy": -0.65, "brow_l": 2.0, "brow_r": 2.0},             # üstteki yazılara bakar
    "saskin":   {"brow_l": 9.0, "brow_r": 9.0, "eye": 1.2, "o": 1.0},                 # şaşkın
    "korku":    {"brow_in": 7.0, "brow_l": 3.0, "brow_r": 3.0, "eye": 1.2, "smile": -4.0, "o": 0.5},
    "dusunce":  {"knit": 3.0, "brow_r": 2.5, "gx": 0.6, "gy": -0.6, "smile": -1.0},  # düşünceli
    "supheli":  {"eye": 0.78, "brow_l": -3.0, "brow_r": 4.0, "gx": -0.3, "smile": 1.0},
}
KEYS = ("smile", "eye", "brow_l", "brow_r", "brow_in", "knit", "o", "gx", "gy")
DEF = {"eye": 1.0}


def mix(a, b, k):
    """İki ifade arasında yumuşak geçiş."""
    ea, eb_ = EXPR.get(a, a) if isinstance(a, str) else a, EXPR.get(b, b) if isinstance(b, str) else b
    return {key: ea.get(key, DEF.get(key, 0.0)) * (1 - k) + eb_.get(key, DEF.get(key, 0.0)) * k for key in KEYS}


def _g(X, Y, cx, cy, sx, sy):
    return np.exp(-(((X - cx) / sx) ** 2 + ((Y - cy) / sy) ** 2) / 2)


class AbiYuz:
    BOX = (232, 92, 470, 300)               # yüz bölgesi (x0, y0, x1, y1)
    EYES = ((317.0, 168.0), (381.0, 168.0))
    EYE_R = (19.0, 15.0)
    MOUTH = (350.0, 222.0, 54.0, 21.0)
    BROWS = ((311.0, 139.0), (381.0, 139.0))
    BROW_IN = ((331.0, 141.0), (364.0, 141.0))
    CORNERS = ((313.0, 223.0), (390.0, 223.0))

    def __init__(self, folder=RIG):
        folder = Path(folder)
        A = np.asarray(Image.open(folder / "kapali_rgba.png").convert("RGBA")).astype(np.float32)
        # kenar temizliği: beyaz fondan kalan açık renkli hale (renk arındırma + 1 piksel daraltma)
        al = A[..., 3:4] / 255.0
        edge = (al > 0.04) & (al < 0.98)
        clean = (A[..., :3] - (1 - al) * 255.0) / np.maximum(al, 0.04)
        A[..., :3] = np.where(edge, np.clip(clean, 0, 255), A[..., :3])
        er = cv2.erode(A[..., 3], np.ones((3, 3), np.uint8), iterations=1)
        A[..., 3] = cv2.GaussianBlur(er, (0, 0), 0.6)
        self.A = A
        self.B = np.asarray(Image.open(folder / "acik.jpg").convert("RGB")).astype(np.float32)
        self.h, self.w = self.A.shape[:2]
        x0, y0, x1, y1 = self.BOX
        Y, X = np.mgrid[y0:y1, x0:x1].astype(np.float32)
        self.X, self.Y = X, Y
        cx, cy, rx, ry = self.MOUTH
        m = (((X - cx) / rx) ** 2 + ((Y - cy) / ry) ** 2 <= 1).astype(np.float32)
        self.mmask = cv2.GaussianBlur(m, (0, 0), 5)[..., None]
        # "o" ağzı: açık ağız yatayda daralır, dikeyde uzar
        sx = cx + (X - cx) * 1.45
        sy = cy + (Y - cy) * 0.78
        self.Bo = cv2.remap(self.B, sx + 0 * X, sy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE) \
            if False else None
        Bc = self.B[y0:y1, x0:x1]
        self.Bc = Bc
        self.Bo = cv2.remap(self.B, sx.astype(np.float32), sy.astype(np.float32), cv2.INTER_LINEAR,
                            borderMode=cv2.BORDER_REPLICATE)
        om = (((X - cx) / (rx * 0.72)) ** 2 + ((Y - cy) / (ry * 1.25)) ** 2 <= 1).astype(np.float32)
        self.omask = cv2.GaussianBlur(om, (0, 0), 4)[..., None]
        self._cache_key, self._cache_img = None, None

    # ---------- yüz katmanları ----------
    def _lids(self, img, b_l, b_r):
        rx, ry = self.EYE_R
        x0, y0 = self.BOX[0], self.BOX[1]
        for (cx, cy), b in zip(self.EYES, (b_l, b_r)):
            if b <= 0.02:
                continue
            ex0, ex1 = int(cx - rx - 2) - x0, int(cx + rx + 3) - x0
            ey0, ey1 = int(cy - ry - 9) - y0, int(cy + ry + 2) - y0
            X, Y = self.X[ey0:ey1, ex0:ex1], self.Y[ey0:ey1, ex0:ex1]
            half = ry * np.sqrt(np.clip(1 - ((X - cx) / rx) ** 2, 0, 1))
            top, bot = cy - half, cy + half
            skin0 = top - 7.0
            edge = top + (bot - top) * b
            src_y = np.where(Y < edge,
                             skin0 + (Y - skin0) * (top - skin0) / np.maximum(edge - skin0, 1e-3),
                             top + (Y - edge) * (bot - top) / np.maximum(bot - edge, 1e-3))
            src_y = np.where((Y >= skin0) & (Y <= bot) & (half > 0.5), src_y, Y)
            patch = cv2.remap(img, (X - x0).astype(np.float32), (src_y - y0).astype(np.float32), cv2.INTER_LINEAR,
                              borderMode=cv2.BORDER_REPLICATE)
            line = (np.exp(-((Y - edge) / 1.2) ** 2) * (half > 1.5) * min(1.0, b * 1.4))[..., None]
            patch[..., :3] = patch[..., :3] * (1 - line) + np.array([50, 33, 26], np.float32) * line
            img[ey0:ey1, ex0:ex1] = patch
        return img

    def _warp(self, img, e):
        """Kaş, göz, ağız köşesi ve bakış: tek bir yer değiştirme alanında birleşir."""
        X, Y = self.X, self.Y
        ox = np.zeros_like(X)
        oy = np.zeros_like(Y)
        below = lambda cy: 1 / (1 + np.exp((Y - (cy + 12)) / 2.5))  # gözlere taşmasın
        for (bx, by), k in zip(self.BROWS, ("brow_l", "brow_r")):
            v = e[k]
            if abs(v) > 0.05:
                oy += v * _g(X, Y, bx, by, 26, 13) * below(by)
        for side, (ix, iy) in enumerate(self.BROW_IN):
            w = _g(X, Y, ix, iy, 11, 10) * below(iy)
            if abs(e["brow_in"]) > 0.05:
                oy += e["brow_in"] * w
            if abs(e["knit"]) > 0.05:
                oy -= e["knit"] * w
                ox += (-1 if side == 0 else 1) * e["knit"] * 0.8 * w
        # gözleri açma/kısma (göz merkezli ölçek)
        s = e["eye"]
        if abs(s - 1) > 0.01:
            for cx, cy in self.EYES:
                w = _g(X, Y, cx, cy, 20, 17)
                k = 1 + (s - 1) * w
                ox += (X - cx) * (1 / k - 1) * (k != 1)
                oy += (Y - cy) * (1 / k - 1)
        # ağız köşeleri (gülümseme +, üzgün -)
        if abs(e["smile"]) > 0.05:
            for cx, cy in self.CORNERS:
                oy += e["smile"] * _g(X, Y, cx, cy, 9, 8)
        sx = (X + ox - self.BOX[0]).astype(np.float32)
        sy = (Y + oy - self.BOX[1]).astype(np.float32)
        out = cv2.remap(img, sx, sy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        # bakış: göz bebekleri elips içinde kayar
        gx, gy = e["gx"], e["gy"]
        if abs(gx) > 0.02 or abs(gy) > 0.02:
            rx, ry = self.EYE_R
            for cx, cy in self.EYES:
                r2 = ((X - cx) / (rx - 2)) ** 2 + ((Y - cy) / (ry - 2)) ** 2
                w = np.clip(1 - 0.8 * r2, 0, 1) ** 0.4
                gsx = (X - gx * rx * 0.6 * w - self.BOX[0]).astype(np.float32)
                gsy = (Y - gy * ry * 0.4 * w - self.BOX[1]).astype(np.float32)
                moved = cv2.remap(out, gsx, gsy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
                inside = (r2 <= 1.3)[..., None]
                out = np.where(inside, moved, out)
        return out

    def face(self, t, level=0.0, expr="normal", wink=0.0):
        """Yüz bölgesi (RGBA float) — konuşma, ifade, bakış, göz kırpma."""
        e = mix(expr, expr, 0) if isinstance(expr, str) else expr
        x0, y0, x1, y1 = self.BOX
        img = self.A[y0:y1, x0:x1].copy()
        open_amt = float(np.clip((level - 0.12) / 0.38, 0, 1))
        open_amt = open_amt * open_amt * (3 - 2 * open_amt)
        o = e["o"] * (1 - open_amt)                                        # konuşmuyorken "o" ağız
        if open_amt > 0.01:
            k = self.mmask * open_amt
            img[..., :3] = img[..., :3] * (1 - k) + self.Bc * k
        if o > 0.01:
            k = self.omask * o
            img[..., :3] = img[..., :3] * (1 - k) + self.Bo * k
        # serbest bakış gezinmesi (ifade bakışına eklenir)
        e = dict(e)
        e["gx"] += 0.22 * math.sin(t * 0.7) * (1 - min(1, abs(e["gx"]) * 1.5))
        e["gy"] += 0.08 * math.sin(t * 0.5)
        img = self._warp(img, e)
        bt = (t + 0.7) % 3.6
        blink = 0.9 * float(1 - abs(bt - 0.08) / 0.08) if bt < 0.16 else 0.0
        sq = max(0.0, 1 - e["eye"]) * 1.2                                  # gözleri kısma: alt kapak
        img = self._lids(img, max(blink, sq), max(blink, sq, wink))
        return img

    def frame(self, t, level=0.0, expr="normal", height=640, wink=0.0):
        """Tam beden RGBA (PIL), yüksekliği height."""
        full = self.A.copy()
        x0, y0, x1, y1 = self.BOX
        f = self.face(t, level, expr, wink)
        a = full[y0:y1, x0:x1, 3:4].copy()
        full[y0:y1, x0:x1, :3] = f[..., :3]
        full[y0:y1, x0:x1, 3:4] = a                                        # siluet aynı kalır
        im = Image.fromarray(np.clip(full, 0, 255).astype(np.uint8), "RGBA")
        return im.resize((max(1, round(self.w * height / self.h)), height), Image.LANCZOS)
