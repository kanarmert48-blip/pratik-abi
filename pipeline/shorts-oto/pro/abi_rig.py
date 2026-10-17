"""Tam boy Pratik Abi kuklası: nefes, sallanma, kafa hareketi, kol salınımı, göz kırpma, sese göre ağız.
Kaynak: kapali_rgba.png (ağız kapalı, arka planı temiz) + acik.jpg (ağız açık, aynı hizada)."""
import math
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

RIG = Path(__file__).resolve().parent.parent / "assets" / "abi_rig"


def _ss(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def _over(dst, src):
    """Önceden çarpılmamış RGBA float (0..255) üst üste bindirme."""
    sa = src[..., 3:4] / 255.0
    da = dst[..., 3:4] / 255.0
    oa = sa + da * (1 - sa)
    rgb = (src[..., :3] * sa + dst[..., :3] * da * (1 - sa)) / np.maximum(oa, 1e-6)
    return np.concatenate([rgb, oa * 255.0], axis=2)


PX = 150  # yatay pay (kaldırılan eller tuvalden taşmasın)


class AbiRig:
    # kaynak görüntüdeki (687x1024) önemli noktalar, PX kadar sağa kaydırılmış
    NECK = (346.0 + PX, 292.0)
    SH_L, SH_R = (258.0 + PX, 350.0), (436.0 + PX, 350.0)
    EL_L, EL_R = (208.0 + PX, 503.0), (487.0 + PX, 503.0)  # dirsekler (kıvrılmış kol ağzının içinde)
    FEET = (346.0 + PX, 1005.0)
    MOUTH = (350.0 + PX, 222.0, 54.0, 21.0)  # cx, cy, rx, ry
    EYES = ((317.0 + PX, 168.0), (381.0 + PX, 168.0))
    EYE_R = (19.0, 15.0)

    def __init__(self, folder=RIG):
        folder = Path(folder)
        A = np.asarray(Image.open(folder / "kapali_rgba.png").convert("RGBA")).astype(np.float32)
        B = np.asarray(Image.open(folder / "acik.jpg").convert("RGB")).astype(np.float32)
        self.A = np.pad(A, ((0, 0), (PX, PX), (0, 0)))
        self.B = np.pad(B, ((0, 0), (PX, PX), (0, 0)), mode="edge")
        self.h, self.w = self.A.shape[:2]
        yy, xx = np.mgrid[0:self.h, 0:self.w].astype(np.float32)
        self.xx, self.yy = xx, yy
        cx, cy, rx, ry = self.MOUTH
        m = (((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2 <= 1).astype(np.float32)
        self.mmask = cv2.GaussianBlur(m, (0, 0), 5)[..., None]
        self.w_head = 1 - _ss(262, 300, yy)
        # kol/gövde sınırı: omuzda eğik, kol ayrıldıktan sonra boşlukta, el hizasında içeride
        low = _ss(590, 610, yy)
        bl = (252 + np.clip(460 - yy, 0, None) * 0.12) * (1 - low) + 240 * low + PX
        br = (444 - np.clip(460 - yy, 0, None) * 0.12) * (1 - low) + 455 * low + PX
        band = 9 - 5 * _ss(440, 470, yy)
        vert = _ss(325, 400, yy) * (1 - _ss(698, 712, yy))
        self.w_l = (1 - _ss(bl - band, bl + band, xx)) * vert
        self.w_r = _ss(br - band, br + band, xx) * vert
        sep = _ss(430, 462, yy)  # kolun gövdeden ayrıldığı kısım: orada kol ile gövde arasında gerçek boşluk var
        self.sep = sep
        # ayrık bölgede sınır = her satırda kol ile gövde arasındaki gerçek boşluğun ortası
        alpha = self.A[..., 3] > 40
        gl, gr = np.zeros(self.h, np.float32), np.zeros(self.h, np.float32)
        pl, pr = 252.0 + PX, 444.0 + PX
        for y in range(self.h):
            if 440 <= y <= 715:
                for lo, hi, side in ((200 + PX, 272 + PX, "l"), (424 + PX, 496 + PX, "r")):
                    gap = np.where(~alpha[y, lo:hi])[0]
                    if len(gap):
                        # en uzun boş aralığın ortası
                        runs = np.split(gap, np.where(np.diff(gap) > 1)[0] + 1)
                        g = max(runs, key=len)
                        mid = lo + (g[0] + g[-1]) / 2
                        if side == "l":
                            pl = mid
                        else:
                            pr = mid
            gl[y], gr[y] = pl, pr
        hard_l = (xx < gl[:, None]).astype(np.float32) * vert
        hard_r = (xx > gr[:, None]).astype(np.float32) * vert
        self.w_l = self.w_l * (1 - sep) + hard_l * sep   # ayrık bölgede keskin maske: hayalet kenar kalmaz
        self.w_r = self.w_r * (1 - sep) + hard_r * sep
        self.body_keep = 1 - (hard_l + hard_r) * sep
        self.fore = _ss(506, 522, yy)  # ön kol + el (kol ağzının altı)

    # ---------- yüz ----------
    def _blink(self, img, b):
        """Üst kapak aşağı iner: göz içeriği alt kapağa doğru sıkışır, üstteki ten gerilerek kapak olur."""
        rx, ry = self.EYE_R
        for cx, cy in self.EYES:
            x0, x1 = int(cx - rx - 2), int(cx + rx + 3)
            y0, y1 = int(cy - ry - 9), int(cy + ry + 2)
            X, Y = self.xx[y0:y1, x0:x1], self.yy[y0:y1, x0:x1]
            half = ry * np.sqrt(np.clip(1 - ((X - cx) / rx) ** 2, 0, 1))
            top, bot = cy - half, cy + half
            skin0 = top - 7.0  # kapak dokusunun alındığı bant: [skin0, top]
            edge = top + (bot - top) * b
            src_y = np.where(Y < edge,
                             skin0 + (Y - skin0) * (top - skin0) / np.maximum(edge - skin0, 1e-3),
                             top + (Y - edge) * (bot - top) / np.maximum(bot - edge, 1e-3))
            src_y = np.where((Y >= skin0) & (Y <= bot) & (half > 0.5), src_y, Y)
            patch = cv2.remap(img, X.astype(np.float32), src_y.astype(np.float32), cv2.INTER_LINEAR,
                              borderMode=cv2.BORDER_REPLICATE)
            # kirpik çizgisi
            line = (np.exp(-((Y - edge) / 1.2) ** 2) * (half > 1.5) * min(1.0, b * 1.4))[..., None]
            patch[..., :3] = patch[..., :3] * (1 - line) + np.array([50, 33, 26], np.float32) * line
            img[y0:y1, x0:x1] = patch
        return img

    def _gaze(self, img, gx, gy):
        rx, ry = self.EYE_R
        for cx, cy in self.EYES:
            x0, x1, y0, y1 = int(cx - rx - 2), int(cx + rx + 3), int(cy - ry - 2), int(cy + ry + 3)
            X, Y = self.xx[y0:y1, x0:x1], self.yy[y0:y1, x0:x1]
            r2 = ((X - cx) / (rx - 2)) ** 2 + ((Y - cy) / (ry - 2)) ** 2
            w = np.clip(1 - 0.8 * r2, 0, 1) ** 0.4
            sx = X - gx * rx * 0.6 * w
            sy = Y - gy * ry * 0.4 * w
            img[y0:y1, x0:x1] = cv2.remap(img, sx.astype(np.float32), sy.astype(np.float32), cv2.INTER_LINEAR,
                                          borderMode=cv2.BORDER_REPLICATE)
        return img

    def _yaw(self, img, yaw):
        """Yüz hatları (göz, burun, ağız) dönüş yönüne kayar, kafa silueti yerinde kalır."""
        x0, x1, y0, y1 = 250 + PX, 445 + PX, 110, 285
        X, Y = self.xx[y0:y1, x0:x1], self.yy[y0:y1, x0:x1]
        w = np.clip(1 - ((X - 347 - PX) / 92) ** 2 - ((Y - 200) / 98) ** 2, 0, 1) ** 0.8
        sx = X - yaw * 9.0 * w
        img[y0:y1, x0:x1] = cv2.remap(img, sx.astype(np.float32), Y.astype(np.float32), cv2.INTER_LINEAR,
                                      borderMode=cv2.BORDER_REPLICATE)
        return img

    def _face(self, open_amt, blink, gx=0.0, gy=0.0, yaw=0.0):
        img = self.A.copy()
        if open_amt > 0.01:
            k = self.mmask * open_amt
            img[..., :3] = img[..., :3] * (1 - k) + self.B * k
        if abs(gx) > 0.02 or abs(gy) > 0.02:
            img = self._gaze(img, gx, gy)
        if blink > 0.02:
            img = self._blink(img, blink)
        if abs(yaw) > 0.02:
            img = self._yaw(img, yaw)
        return img

    # ---------- kare ----------
    @staticmethod
    def _aff(piv, deg, sy=1.0):
        """piv etrafında dönüş (+: saat yönü tersi) ve kolun kendi ekseni boyunca ölçek (sy)."""
        a = math.radians(deg)
        c, s = math.cos(a), math.sin(a)
        R = np.array([[c, s, 0], [-s, c, 0], [0, 0, 1]], np.float64)
        S = np.diag([1.0, sy, 1.0])
        T1 = np.array([[1, 0, -piv[0]], [0, 1, -piv[1]], [0, 0, 1]], np.float64)
        T2 = np.array([[1, 0, piv[0]], [0, 1, piv[1]], [0, 0, 1]], np.float64)
        return T2 @ R @ S @ T1

    def frame(self, t, level=0.0, height=640, nod=0.0, intro=1.0, look=0.0, hop=0.0, down=0.0, arms=None):
        """t: saniye, level: 0..1 ses, nod: vurgu, look: -1..1 yana/yukarı bakış (+: sağ üst),
        hop: zıplama, down: kendine bakma, arms: ((omuz_dışa, önkol, önkol_ölçek) sol, (...) sağ) derece.
        önkol: + dışa-yukarı, - içe-yukarı (göğüs önüne)."""
        bt = (t + 0.7) % 3.6  # ~3.6 sn'de bir göz kırpma
        blink = 0.9 * float(1 - abs(bt - 0.08) / 0.08) if bt < 0.16 else 0.0
        gx = 0.25 * math.sin(t * 0.7) * (1 - abs(look)) + 0.95 * look
        gy = -0.6 * max(0.0, look) + 0.1 * math.sin(t * 0.5) * (1 - down) + 0.9 * down
        img = self._face(float(_ss(0.12, 0.5, level)), blink, gx, gy, yaw=0.9 * look)
        th_head = 3.2 * math.sin(t * 1.3) + 1.6 * math.sin(t * 2.9) - 3.5 * nod + 6.0 * look
        th_body = 1.4 * math.sin(t * 0.9) - 2.5 * look
        if arms is None:
            arms = ((2 + 2.6 * math.sin(t * 1.7), 3 * math.sin(t * 1.3), 1.0),
                    (2 + 2.6 * math.sin(t * 1.5 + 1.1), 3 * math.sin(t * 1.1 + 0.5), 1.0))
        (ul, fl, sl), (ur, fr, sr) = arms
        # cv2 açıları (+ saat yönü tersi): sol kol dışa = eksi, sağ kol dışa = artı
        ang = {"l": (-ul, -fl, sl), "r": (ur, fr, sr)}
        breathe = 1 + 0.009 * math.sin(t * 2 * math.pi / 3.4)
        xx, yy = self.xx, self.yy
        # gövde: kafa dönüşü + omuz bölgesinin kolla birlikte bükülmesi (küçük açılar, ağırlıklı)
        body = img.copy()
        body[..., 3] *= self.body_keep

        def rot(px, py, piv, deg, w):
            a = np.deg2rad(deg) * w
            c, s = np.cos(a), np.sin(a)
            dx, dy = px - piv[0], py - piv[1]
            return piv[0] + c * dx + s * dy, piv[1] - s * dx + c * dy

        sx, sy = xx, yy
        sx, sy = rot(sx, sy, self.SH_L, ang["l"][0], self.w_l * (1 - self.sep))
        sx, sy = rot(sx, sy, self.SH_R, ang["r"][0], self.w_r * (1 - self.sep))
        sx, sy = rot(sx, sy, self.NECK, th_head, self.w_head)
        sy = sy - (4.0 * nod + 7.0 * down) * self.w_head
        out = cv2.remap(body, sx.astype(np.float32), sy.astype(np.float32), cv2.INTER_LINEAR,
                        borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
        # kollar: üst kol (kol ağzı dahil) + ön kol/el; ön kol dirsekte döner, kol ağzı eklemi örter
        for side, wgt, sh, el in (("l", self.w_l, self.SH_L, self.EL_L), ("r", self.w_r, self.SH_R, self.EL_R)):
            u_deg, f_deg, fsc = ang[side]
            Mu = self._aff(sh, u_deg)
            Mf = Mu @ self._aff(el, f_deg, fsc)
            fore = img.copy(); fore[..., 3] *= wgt * self.fore
            upper = img.copy(); upper[..., 3] *= wgt * (1 - self.fore)
            fore = cv2.warpAffine(fore, Mf[:2], (self.w, self.h), flags=cv2.INTER_LINEAR,
                                  borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
            upper = cv2.warpAffine(upper, Mu[:2], (self.w, self.h), flags=cv2.INTER_LINEAR,
                                   borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
            out = _over(_over(out, fore), upper)
        # bütün beden: ayak merkezli sallanma + nefes + ağırlık aktarma + zıplama
        M = cv2.getRotationMatrix2D(self.FEET, th_body, 1.0)
        M[1] = M[1] * np.array([breathe, breathe, 1.0]) + np.array([0, 0, self.FEET[1] * (1 - breathe)])
        M[0, 2] += 6.0 * math.sin(t * 0.55)
        M[1, 2] -= 22.0 * hop
        out = cv2.warpAffine(out, M, (self.w, self.h), flags=cv2.INTER_LINEAR,
                             borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
        im = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), "RGBA")
        hh = max(2, int(height * intro))
        return im.resize((max(1, round(self.w * hh / self.h)), hh), Image.LANCZOS)


# ---------- hazır jestler: (omuz_dışa, önkol, önkol_ölçek) ----------
POSES = {
    "dur":        ((3, 0, 1.0), (3, 0, 1.0)),
    "selam":      ((4, 4, 1.0), (22, 128, 0.95)),          # sağ el (ekranın içine doğru) havada
    "ben":        ((-6, -98, 0.82), (5, 6, 1.0)),          # sol el göğüste
    "sunum":      ((12, 30, 0.9), (12, 30, 0.9)),          # iki el yana açık: "işte!"
    "goster":     ((4, 6, 1.0), (24, 118, 0.92)),          # sağ el yukarı, arkadaki görseli gösterir
    "omuz":       ((8, 40, 0.85), (8, 40, 0.85)),          # soru: iki el yukarı açık
    "anlat_sol":  ((4, -62, 0.8), (4, 4, 1.0)),            # sol el göğüs önünde anlatır
    "anlat_sag":  ((4, 4, 1.0), (4, -62, 0.8)),
}
