"""Tam boy Abi deneme videosu (2K, ~8 sn): arka plan + altyazı + sol altta konuşan Abi."""
import os
os.environ.setdefault("PA_SCALE", str(4 / 3))
import json, math, subprocess, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
from engine import *  # noqa
from abi_rig import AbiRig, POSES
import audio_tools as at

R = Path(sys.argv[1])
BG = sys.argv[2]
words = json.loads((R / "words.json").read_text(encoding="utf-8"))
VO = str(R / "ses.wav")
TOTAL = at.duration(VO) + 0.5
groups = caption_groups(words)

r = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", VO, "-f", "s16le", "-ac", "1", "-ar", "16000", "-"],
                   capture_output=True, check=True)
x = np.frombuffer(r.stdout, "<i2").astype(float) / 32768
hop = 16000 // FPS
env = np.array([np.sqrt(np.mean(x[i:i + hop] ** 2)) for i in range(0, len(x), hop)])
env = np.clip(env / (np.percentile(env, 95) + 1e-9), 0, 1.2)
env = np.convolve(env, np.ones(2) / 2, mode="same")
# vurgu: enerjinin hızlı yükseldiği anlar
rise = np.clip(np.diff(np.concatenate([[0], np.convolve(env, np.ones(4) / 4, mode="same")])), 0, None)
peaks = [i for i in range(1, len(rise) - 1) if rise[i] > 0.09 and rise[i] >= rise[i - 1] and rise[i] >= rise[i + 1]]


def lvl(t):
    i = int(t * FPS)
    return float(env[i]) if i < len(env) else 0.0


def nod(t):
    v = 0.0
    for p in peaks:
        q = t - p / FPS
        if 0 <= q < 0.45:
            v = max(v, math.sin(min(1, q / 0.12) * math.pi / 2) * (1 - q / 0.45))
    return v


def pulse(t, a, b, ramp=0.3):
    """a..b arasında yumuşak açılıp kapanan 0..1 değer."""
    return float(eio(ph(t, a, ramp)) * (1 - eio(ph(t, b - ramp, ramp))))


def look(t):     # "Nasıl" derken arkadaki görsele bakar, sonra izleyiciye döner
    return pulse(t, 4.9, 6.15, 0.35)


def down(t):     # "baştan aşağı" derken kendine bakar
    return pulse(t, 3.0, 4.5, 0.3)


def hop(t):
    v = 0.0
    for st in (0.05, 6.15):
        q = t - st
        if 0 <= q < 0.35:
            v = max(v, math.sin(q / 0.35 * math.pi))
    return v


KEYS = [(0.0, "selam"), (0.95, "ben"), (2.15, "anlat_sag"), (3.0, "sunum"), (4.85, "goster"), (6.1, "omuz"),
        (7.7, "dur")]


def arms(t):
    """Jest anahtarları arasında yumuşak geçiş + el sallama + konuşma vurgusunda el hareketi + mikro salınım."""
    k = max(i for i, (kt, _) in enumerate(KEYS) if kt <= t + 1e-9)
    cur = POSES[KEYS[k][1]]
    prev = POSES[KEYS[k - 1][1]] if k > 0 else POSES["dur"]
    e = float(eio(ph(t, KEYS[k][0], 0.38))) if k > 0 else 1.0
    out = []
    b = nod(t)
    for side in (0, 1):
        u_, f_, s_ = (lerp(prev[side][j], cur[side][j], e) for j in range(3))
        u_ += 1.6 * math.sin(t * 1.7 + side * 1.3)
        f_ += 2.5 * math.sin(t * 1.3 + side * 2.1)
        name = KEYS[k][1]
        if name == "selam" and side == 1:
            f_ += 16 * math.sin(2 * math.pi * 2.4 * t)         # el sallama
        elif name not in ("goster",):
            f_ += (7 if f_ >= 0 else -7) * b                     # vurguda el hafifçe kalkar
        out.append((u_, f_, s_))
    return tuple(out)


rig = AbiRig()
AH = round(H * 0.26)                       # ekran yüksekliğinin ~dörtte biri
X0, Y0 = round(u(30)) - round(172 * AH / 1024), H - round(u(34)) - AH
sh = Image.new("RGBA", (round(AH * 0.42), round(AH * 0.06)), (0, 0, 0, 0))
ImageDraw.Draw(sh).ellipse([0, 0, sh.width - 1, sh.height - 1], fill=(0, 0, 0, 120))
sh = sh.filter(ImageFilter.GaussianBlur(AH * 0.012))

p = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-ss", "12.7", "-i", BG, "-vf", f"scale={W}:{H}", "-f", "rawvideo",
                      "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
enc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                        "-r", str(FPS), "-i", "-", "-i", VO, "-c:v", "libx264", "-crf", "16", "-preset", "fast",
                        "-pix_fmt", "yuv420p", "-af", "apad", "-c:a", "aac", "-b:a", "192k", "-t", f"{TOTAL:.3f}",
                        str(R / "deneme_raw.mp4")],
                       stdin=subprocess.PIPE)
n = int(TOTAL * FPS)
for f in range(n):
    t = f / FPS
    buf = p.stdout.read(W * H * 3)
    im = Image.frombuffer("RGB", (W, H), buf, "raw", "RGB", 0, 1).convert("RGBA")
    brand(im, 540, 140)
    draw_caption(im, groups, t, y=1290)
    intro = eb(ph(t, 0.0, 0.4)) if t < 0.4 else 1.0
    a = rig.frame(t, level=lvl(t), height=AH, nod=nod(t), intro=max(0.05, intro), look=look(t), hop=hop(t),
                  down=down(t), arms=arms(t))
    cxf = round(u(55)) + round(174 * AH / 1024)   # gövdenin sol kenarı ekrandan ~55 birim içeride
    comp(im, sh, cxf - sh.width / 2, H - round(u(34)) - sh.height * 0.55)
    comp(im, a, cxf - a.width * rig.FEET[0] / rig.w, H - round(u(34)) - a.height)
    enc.stdin.write(im.convert("RGB").tobytes())
enc.stdin.close(); enc.wait(); p.kill()
print("bitti", round(TOTAL, 2))
