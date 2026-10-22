"""Sol altta yuvarlak Pratik Abi rozeti (profil görseli). Konuşurken hafif büyür ve yanında ses dalgaları atar.
Kullanım: R = Rozet(); R.draw(im, t, level)  # level: 0..1 (konusma() açıklığı)"""
import math, subprocess
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from engine import u, comp, soft_shadow, ACC, FPS

SRC = Path(__file__).resolve().parent.parent / "assets" / "abi_rozet.mp4"


class Rozet:
    def __init__(self, size=230, cx=170, cy=1590, src=SRC):
        self.Sz = Sz = round(u(size))
        self.cx, self.cy = u(cx), u(cy)
        raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(src), "-vf",
                              f"scale={Sz}:{Sz}:flags=lanczos,fps={FPS}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                             capture_output=True, check=True).stdout
        self.n = len(raw) // (Sz * Sz * 3)
        self.raw = raw
        m = Image.new("L", (Sz * 4, Sz * 4), 0)
        ImageDraw.Draw(m).ellipse([0, 0, Sz * 4 - 1, Sz * 4 - 1], fill=255)
        self.mask = m.resize((Sz, Sz), Image.LANCZOS)
        b = self.b = round(u(9))
        ring = Image.new("RGBA", (Sz + 2 * b, Sz + 2 * b), (0, 0, 0, 0))
        ImageDraw.Draw(ring).ellipse([0, 0, Sz + 2 * b - 1, Sz + 2 * b - 1], fill=ACC + (255,))
        self.ring = ring
        self.sh, self.pad = soft_shadow(ring.width, ring.height, ring.width // 2, blur=round(u(16)), op=0.5)
        self._cache = {}

    def _img(self, t):
        k = int(t * FPS) % (2 * self.n - 2) if self.n > 1 else 0
        i = k if k < self.n else 2 * self.n - 2 - k          # ileri-geri döngü
        if i not in self._cache:
            Sz = self.Sz
            fr = Image.frombuffer("RGB", (Sz, Sz), self.raw[i * Sz * Sz * 3:(i + 1) * Sz * Sz * 3], "raw", "RGB", 0, 1)
            fr = fr.convert("RGBA")
            fr.putalpha(self.mask)
            img = self.ring.copy()
            img.alpha_composite(fr, (self.b, self.b))
            self._cache[i] = img
        return self._cache[i]

    def draw(self, im, t, level=0.0, alpha=1.0):
        if alpha <= 0.01:
            return
        img = self._img(t)
        s = 1 + 0.05 * level
        im2 = img.resize((int(img.width * s), int(img.height * s)), Image.BICUBIC)
        im2 = im2.rotate(2.0 * math.sin(t * 2.1), resample=Image.BICUBIC, expand=True)
        if alpha < 0.99:
            a = np.asarray(im2).copy(); a[..., 3] = (a[..., 3] * alpha).astype(np.uint8); im2 = Image.fromarray(a, "RGBA")
        sh = self.sh if alpha >= 0.99 else Image.fromarray((np.asarray(self.sh) * np.array([1, 1, 1, alpha])).astype(np.uint8), "RGBA")
        comp(im, sh, self.cx - img.width / 2 - self.pad, self.cy - img.height / 2 - self.pad + u(12))
        comp(im, im2, self.cx - im2.width / 2, self.cy - im2.height / 2)
        if level > 0.08:
            d = ImageDraw.Draw(im)
            for k2 in range(2):
                rr = u(138 + k2 * 24 + 14 * level)
                d.arc([self.cx - rr, self.cy - rr, self.cx + rr, self.cy + rr], -40, 30,
                      fill=ACC + (int((200 - 70 * k2) * alpha * min(1, level * 2)),), width=round(u(7)))
