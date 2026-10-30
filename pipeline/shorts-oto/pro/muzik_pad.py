"""Sinematik yaylı pad müzik üretici (telifsiz, tamamen sentez).
mk(path, total, plan) -> wav. plan: [(t0, t1, akor_notaları(midi), seviye)]"""
import subprocess
import numpy as np

SR = 44100


def mf(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def saw(f, t, nh=10):
    y = np.zeros_like(t)
    for k in range(1, nh + 1):
        if np.max(f) * k > 9000:
            break
        y += np.sin(2 * np.pi * f * k * t) / k
    return y


def mk(path, total, plan, hits=(), swells=()):
    n = int(total * SR)
    y = np.zeros(n, np.float32)
    t_all = np.arange(n) / SR
    for t0, t1, notes, lv in plan:
        a, b = int(max(0, t0 - 0.5) * SR), int(min(total, t1 + 0.8) * SR)
        t = t_all[a:b]
        env = np.clip((t - (t0 - 0.5)) / 0.9, 0, 1) * np.clip(((t1 + 0.8) - t) / 1.1, 0, 1)
        seg = np.zeros_like(t)
        for m in notes:
            f = mf(m)
            for d in (-0.06, 0.0, 0.07):
                vib = 1 + 0.002 * np.sin(2 * np.pi * 5.1 * t + m)
                seg += saw(f * (1 + d / 12) * vib, t) * 0.33
        root = mf(notes[0] - 12)
        seg += 0.9 * np.sin(2 * np.pi * root * t) + 0.3 * np.sin(2 * np.pi * root * 2 * t)
        y[a:b] += (seg * env * lv).astype(np.float32)
    rng = np.random.default_rng(7)
    for th, amp in hits:            # timpani + zil
        i = int(th * SR)
        L = int(2.5 * SR)
        tt = np.arange(L) / SR
        hit = np.sin(2 * np.pi * (58 + 40 * np.exp(-tt * 18)) * tt) * np.exp(-tt * 2.2) * 1.6
        hit += rng.standard_normal(L) * np.exp(-tt * 3.0) * 0.22
        e = min(n, i + L)
        y[i:e] += (hit[:e - i] * amp).astype(np.float32)
    for t0, t1, amp in swells:      # yükselen zil/nefes
        a, b = int(t0 * SR), int(t1 * SR)
        L = b - a
        nz = rng.standard_normal(L)
        nz = np.convolve(nz, np.ones(6) / 6, mode="same")
        y[a:b] += (nz * np.linspace(0, 1, L) ** 2.5 * amp).astype(np.float32)
    y /= np.abs(y).max() + 1e-9
    raw = path + ".raw.f32"
    y.astype(np.float32).tofile(raw)
    af = ("lowpass=f=2600,highpass=f=40,aecho=0.8:0.85:60|130|210|330:0.32|0.24|0.18|0.12,"
          "aecho=0.8:0.7:520|900:0.12|0.08,loudnorm=I=-18:TP=-2")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", raw, "-af", af,
                    "-ar", "44100", "-ac", "1", path], check=True)
