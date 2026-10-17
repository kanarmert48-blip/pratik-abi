"""Ses işleme: sessizlik bulma, kesme, kelime zamanlarını yeni zaman çizgisine taşıma,
fon müziği ve efekt sesleri üretme, miks."""
import json, re, subprocess
import numpy as np

SR = 44100


def silences(path, noise="-38dB", d=0.25):
    r = subprocess.run(["ffmpeg", "-i", path, "-af", f"silencedetect=noise={noise}:d={d}", "-f", "null", "-"],
                       capture_output=True, text=True)
    st = [float(x) for x in re.findall(r"silence_start: ([0-9.]+)", r.stderr)]
    en = [float(x) for x in re.findall(r"silence_end: ([0-9.]+)", r.stderr)]
    return list(zip(st, en))


def duration(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                       capture_output=True, text=True)
    return float(r.stdout.strip())


def plan_cuts(sil, remove=(), max_pause=0.45, keep_pause=None):
    """remove: [(a,b)] silinecek bölgeler. Uzun sessizlikler max_pause'a kısaltılır.
    keep_pause: {yaklaşık_zaman: süre} sahne geçişlerinde daha uzun bırakılacak duraklar."""
    cuts = list(remove)
    keep_pause = keep_pause or {}
    for a, b in sil:
        if any(ra - 0.05 <= a and b <= rb + 0.05 for ra, rb in remove):
            continue
        target = max_pause
        for t, p in keep_pause.items():
            if a - 0.3 <= t <= b + 0.3:
                target = p
        if b - a > target + 0.04:
            mid = (a + b) / 2
            cuts.append((mid - (b - a - target) / 2, mid + (b - a - target) / 2))
    cuts.sort()
    return cuts


def keep_segments(cuts, total):
    segs, t = [], 0.0
    for a, b in cuts:
        if a > t:
            segs.append((t, a))
        t = max(t, b)
    if t < total:
        segs.append((t, total))
    return segs


def remap(t, segs, lead=0.0):
    acc = lead
    for a, b in segs:
        if t < a:
            return acc
        if t <= b:
            return acc + (t - a)
        acc += b - a
    return acc


def apply_cuts(src, dst, segs, lead=0.2, tail=0.0):
    parts, filt = [], ""
    for i, (a, b) in enumerate(segs):
        filt += f"[0:a]atrim={a:.4f}:{b:.4f},asetpts=PTS-STARTPTS,afade=t=in:d=0.012,afade=t=out:st={max(0, b - a - 0.012):.4f}:d=0.012[s{i}];"
        parts.append(f"[s{i}]")
    filt += "".join(parts) + f"concat=n={len(segs)}:v=0:a=1,aresample={SR},adelay={int(lead * 1000)}:all=1,apad=pad_dur={tail}[o]"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", src, "-filter_complex", filt, "-map", "[o]",
                    "-ac", "1", dst], check=True)


# ---------- sentez yardımcıları ----------
def _add(mix, s, y):
    n = len(mix)
    if s >= n or s < 0:
        return
    m = min(len(y), n - s)
    mix[s:s + m] += y[:m]


def _env(n, a=0.005, r=0.3):
    e = np.ones(n)
    na, nr = int(a * SR), int(r * SR)
    if na:
        e[:na] = np.linspace(0, 1, na)
    if nr and nr < n:
        e[-nr:] *= np.linspace(1, 0, nr)
    return e


def _note(f, dur, kind="ep"):
    n = int(dur * SR)
    t = np.arange(n) / SR
    if kind == "ep":  # elektrikli piyano benzeri
        y = (np.sin(2 * np.pi * f * t) + 0.35 * np.sin(2 * np.pi * 2 * f * t) * np.exp(-t * 3)
             + 0.12 * np.sin(2 * np.pi * 3 * f * t) * np.exp(-t * 6))
        y *= np.exp(-t * 1.6) * _env(n, 0.004, 0.05)
    elif kind == "pad":
        y = sum(np.sin(2 * np.pi * f * (1 + d) * t) for d in (-0.004, 0, 0.0045)) / 3
        y *= _env(n, 0.6, 0.8)
    else:  # bas
        y = np.sin(2 * np.pi * f * t) * _env(n, 0.01, 0.15) * np.exp(-t * 0.8)
    return y


def _lowpass(y, cutoff):
    a = np.exp(-2 * np.pi * cutoff / SR)
    out = np.empty_like(y)
    acc = 0.0
    for i in range(len(y)):  # tek kutuplu filtre (kısa sinyaller için yeterli)
        acc = (1 - a) * y[i] + a * acc
        out[i] = acc
    return out


STYLES = {
    # ad: (akor dizisi, arp deseni, arp ses seviyesi, hi-hat sıklığı, kick deseni)
    "lofi": ([(57, [57, 60, 64]), (53, [53, 57, 60]), (48, [48, 52, 55]), (55, [55, 59, 62])],  # Am F C G
             [0, 1, 2, 4, 5, 4, 2, 1], 0.07, 1, (0, 2)),
    "quiz": ([(48, [60, 64, 67]), (43, [55, 59, 62]), (45, [57, 60, 64]), (41, [53, 57, 60])],  # C G Am F
             [0, 2, 1, 2, 4, 2, 1, 2], 0.09, 2, (0, 1, 2, 3)),
    "warm": ([(50, [50, 53, 57]), (46, [46, 50, 53]), (53, [53, 57, 60]), (48, [48, 52, 55])],  # Dm Bb F C
             [0, 1, 2, 1, 4, 1, 2, 1], 0.06, 1, (0, 2)),
    "sitcom": ([(53, [65, 69, 72]), (48, [60, 64, 67]), (50, [62, 65, 69]), (46, [58, 62, 65])],  # F C Dm Bb
               [0, 2, 4, 2, 1, 3, 5, 3], 0.085, 2, (0, 2, 3)),
}


def music(path, total, bpm=78, style="lofi"):
    """Telifsiz fon müziği (burada üretilir). style: lofi | quiz | warm — her videoda farklı his."""
    beat = 60 / bpm
    bar = beat * 4
    hz = lambda m: 440 * 2 ** ((m - 69) / 12)
    prog, pattern, arp_vol, hat_div, kicks = STYLES[style]
    n = int((total + 2) * SR)
    mix = np.zeros(n)
    t0, k = 0.0, 0
    while t0 < total + 1:
        root, ch = prog[k % 4]
        i0 = int(t0 * SR)
        pad = sum(_note(hz(m), bar + 0.6, "pad") for m in ch) * 0.10
        _add(mix, i0, pad)
        bass = _note(hz(root - 12), bar * 0.95, "bass") * 0.22
        _add(mix, i0, bass)
        tones = ch + [ch[0] + 12, ch[1] + 12, ch[2] + 12]
        for j, idx in enumerate(pattern):
            s = int((t0 + j * beat / 2) * SR)
            nt = _note(hz(tones[idx] + 12), beat * 1.6, "ep") * (arp_vol if j % 2 == 0 else arp_vol * 0.7)
            _add(mix, s, nt)
        rng = np.random.default_rng(k)
        for j in range(4):  # kick + hi-hat
            s = int((t0 + j * beat) * SR)
            if j in kicks:
                tt = np.arange(int(0.25 * SR)) / SR
                kick = np.sin(2 * np.pi * (50 + 60 * np.exp(-tt * 30)) * tt) * np.exp(-tt * 14) * 0.25
                _add(mix, s, kick)
            for h in range(hat_div):
                hs = int((t0 + j * beat + beat * (h + 0.5) / hat_div) * SR)
                hat = rng.standard_normal(int(0.04 * SR)) * np.exp(-np.arange(int(0.04 * SR)) / SR * 90) * 0.025
                hat = np.diff(hat, prepend=0)
                _add(mix, hs, hat)
        t0 += bar
        k += 1
    mix = mix[: int(total * SR)]
    fade = int(1.5 * SR)
    mix[-fade:] *= np.linspace(1, 0, fade)
    mix[: int(0.8 * SR)] *= np.linspace(0, 1, int(0.8 * SR))
    mix /= np.max(np.abs(mix)) + 1e-9
    _write(path, mix * 0.8)


def sfx(path, total, events):
    """events: [(zaman, tür)] tür: whoosh | pop | ding"""
    n = int((total + 1) * SR)
    mix = np.zeros(n)
    rng = np.random.default_rng(3)
    for t, kind in events:
        s = int(t * SR)
        if kind == "whoosh":
            d = 0.45
            m = int(d * SR)
            noise = rng.standard_normal(m)
            tt = np.linspace(0, 1, m)
            env = np.sin(np.pi * tt) ** 2
            cut = 400 + 5000 * tt
            y = np.zeros(m)
            acc = 0.0
            for i in range(m):
                a = np.exp(-2 * np.pi * cut[i] / SR)
                acc = (1 - a) * noise[i] + a * acc
                y[i] = acc
            y = y * env * 0.5
            s = max(0, s - int(0.2 * SR))
        elif kind == "pop":
            m = int(0.09 * SR)
            tt = np.arange(m) / SR
            y = np.sin(2 * np.pi * (900 - 4000 * tt) * tt) * np.exp(-tt * 45) * 0.28
        elif kind == "tink":  # parlak, kısa "tink"
            m = int(1.2 * SR)
            tt = np.arange(m) / SR
            y = (np.sin(2 * np.pi * 2093 * tt) + 0.5 * np.sin(2 * np.pi * 3136 * tt) + 0.25 * np.sin(2 * np.pi * 4186 * tt))
            y *= np.exp(-tt * 4.5) * 0.22
        else:  # ding
            m = int(0.8 * SR)
            tt = np.arange(m) / SR
            y = (np.sin(2 * np.pi * 1318 * tt) + 0.4 * np.sin(2 * np.pi * 2637 * tt)) * np.exp(-tt * 5) * 0.16
        _add(mix, s, y)
    _write(path, mix[: int(total * SR)])


def _write(path, y):
    y = np.clip(y, -1, 1)
    pcm = (y * 32767).astype("<i2").tobytes()
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "s16le", "-ar", str(SR), "-ac", "1", "-i", "-", path],
                   input=pcm, check=True)


def final_mix(voice, mus, fx, out):
    filt = ("[0:a]highpass=f=70,acompressor=threshold=-20dB:ratio=3:attack=5:release=120,"
            "equalizer=f=3000:t=q:w=1:g=2,asplit=2[v][sc];"
            "[1:a]volume=0.20[m];[m][sc]sidechaincompress=threshold=0.03:ratio=6:attack=20:release=400[md];"
            "[2:a]volume=0.9[f];"
            "[v][md][f]amix=inputs=3:normalize=0:duration=longest,loudnorm=I=-14:TP=-1.5:LRA=9[o]")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", voice, "-i", mus, "-i", fx, "-filter_complex", filt,
                    "-map", "[o]", "-ar", "44100", "-c:a", "aac", "-b:a", "192k", out], check=True)
