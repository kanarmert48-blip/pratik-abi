"""Gerçek görüntülü arka plan: klip/fotoğraf parçalarını 9:16'ya kırpıp tek bir arka plan videosu yapar,
render sırasında kare kare okur ve yavaş kaydırma (Ken Burns) uygular."""
import subprocess, tempfile, os
from pathlib import Path

import numpy as np
from PIL import Image

from engine import FPS, H, W, comp

BW, BH = 1188, 2112  # %10 büyük: kaydırma payı


def build(segments, out):
    """segments: [{src, kind: 'video'|'photo', dur, ss=0, grade=''}] sırayla."""
    tmp = tempfile.mkdtemp()
    parts = []
    for i, s in enumerate(segments):
        p = os.path.join(tmp, f"s{i}.mp4")
        vf = (f"scale={BW}:{BH}:force_original_aspect_ratio=increase,crop={BW}:{BH},fps={FPS},"
              f"eq=contrast=1.06:saturation=1.12:brightness=-0.03{s.get('grade', '')},setsar=1,format=yuv420p")
        if s["kind"] == "photo":
            inp = ["-loop", "1", "-t", f"{s['dur']:.3f}", "-i", s["src"]]
        else:
            inp = ["-stream_loop", "-1", "-ss", f"{s.get('ss', 0):.3f}", "-t", f"{s['dur']:.3f}", "-i", s["src"]]
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *inp, "-vf", vf, "-an", "-t", f"{s['dur']:.3f}",
                        "-c:v", "libx264", "-preset", "veryfast", "-crf", "14", p], check=True)
        parts.append(p)
    lst = os.path.join(tmp, "l.txt")
    Path(lst).write_text("".join(f"file '{p}'\n" for p in parts))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", out],
                   check=True)


def _grad():
    a = np.zeros((H, W, 4), np.uint8)
    y = np.arange(H)[:, None]
    top = np.clip(1 - y / 560, 0, 1) ** 1.6 * 165
    bot = np.clip((y - 1150) / 650, 0, 1) ** 1.3 * 135
    yy, xx = np.mgrid[0:H, 0:W]
    dd = np.sqrt(((xx - W / 2) / (W * 0.7)) ** 2 + ((yy - H / 2) / (H * 0.7)) ** 2)
    vig = np.clip(dd - 0.75, 0, 1) * 160
    a[..., 3] = np.clip(top + bot + vig + 8, 0, 255).astype(np.uint8)
    return Image.fromarray(a, "RGBA")


class VideoBackground:
    def __init__(self, path, segments, grain_from=None):
        self.path = path
        self.segs = []
        t = 0.0
        for s in segments:
            self.segs.append((t, t + s["dur"], s.get("pan", (0, -1)), s.get("zoom", 0.0)))
            t += s["dur"]
        self.proc = None
        self.next_t = None
        self.grad = _grad()
        self.extra = grain_from  # engine.Background (vinyet + gren)

    def open(self, t):
        if self.proc:
            self.proc.kill()
        self.proc = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-ss", f"{t:.4f}", "-i", self.path,
                                      "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
        self.next_t = t

    def _read(self, t):
        if self.proc is None or self.next_t is None or abs(t - self.next_t) > 0.5 / FPS:
            self.open(t)
        buf = self.proc.stdout.read(BW * BH * 3)
        self.next_t = t + 1 / FPS
        if len(buf) < BW * BH * 3:
            return Image.new("RGB", (BW, BH), (0, 0, 0))
        return Image.frombuffer("RGB", (BW, BH), buf, "raw", "RGB", 0, 1)

    def seg_at(self, t):
        for i, (a, b, pan, z) in enumerate(self.segs):
            if a <= t < b:
                return i, a, b, pan, z
        a, b, pan, z = self.segs[-1]
        return len(self.segs) - 1, a, b, pan, z

    def offset(self, t):
        i, a, b, pan, z = self.seg_at(t)
        p = (t - a) / max(b - a, 0.01)
        dx, dy = pan
        ox = (BW - W) / 2 + dx * (p - 0.5) * (BW - W)
        oy = (BH - H) / 2 + dy * (p - 0.5) * (BH - H)
        return ox, oy, i, p, z

    def frame(self, t):
        src = self._read(t)
        ox, oy, i, p, z = self.offset(t)
        if z:
            s = 1 + z * p  # hafif yakınlaşma
            cw, ch = W / s, H / s
            cx, cy = ox + W / 2, oy + H / 2
            im = src.crop((cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2)).resize((W, H), Image.BILINEAR)
        else:
            im = src.crop((int(ox), int(oy), int(ox) + W, int(oy) + H))
        im = im.convert("RGBA")
        im.alpha_composite(self.grad)
        return im

    def finish(self, im, t):
        if self.extra:
            return self.extra.finish(im, t)
        return im
