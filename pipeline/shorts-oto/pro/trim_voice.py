"""Seslendirmedeki uzun duraksamaları enerji zarfına göre kısaltır ve kelime zamanlarını yeni zamana taşır.
Kullanım: python trim_voice.py <klasör> <normal_duraksama> <sahne_duraksaması> <sahne_sınırları_virgüllü>
Klasörde voice.wav ve words_raw.txt ("kelime bas_ms bit_ms|...") olmalı."""
import json, subprocess, sys
import numpy as np
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from audio_tools import apply_cuts, duration, keep_segments, remap

S, normal, scene = sys.argv[1], float(sys.argv[2]), float(sys.argv[3])
bounds = [float(v) for v in sys.argv[4].split(",")] if len(sys.argv) > 4 and sys.argv[4] else []
sr = 24000
pcm = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", f"{S}/voice.wav", "-f", "s16le", "-ac", "1", "-ar", str(sr), "-"],
                     capture_output=True).stdout
x = np.frombuffer(pcm, dtype="<i2").astype(float) / 32768
hop = int(0.01 * sr)
n = len(x) // hop
env = np.sqrt((x[: n * hop].reshape(n, hop) ** 2).mean(axis=1))
quiet = 20 * np.log10(env + 1e-9) < -36
regs, i = [], 0
while i < n:
    if quiet[i]:
        j = i
        while j < n and quiet[j]:
            j += 1
        regs.append((i * 0.01, j * 0.01))
        i = j
    else:
        i += 1
cuts = []
for a, b in regs:
    if b - a < 0.12:
        continue
    target = scene if any(a - 0.4 <= t <= b + 0.4 for t in bounds) else normal
    if a < 0.05:
        target = 0.05
    if b - a > target + 0.04:
        mid, L = (a + b) / 2, b - a - target
        cuts.append((mid - L / 2, mid + L / 2))
total = duration(f"{S}/voice.wav")
segs = keep_segments(cuts, total)
LEAD = 0.15
apply_cuts(f"{S}/voice.wav", f"{S}/voice_cut.wav", segs, lead=LEAD, tail=1.0)
words = []
for it in open(f"{S}/words_raw.txt", encoding="utf-8").read().strip().split("|"):
    w, a, b = it.rsplit(" ", 2)
    words.append({"w": w, "s": round(remap(int(a) / 1000, segs, LEAD), 3), "e": round(remap(int(b) / 1000, segs, LEAD), 3)})
json.dump(words, open(f"{S}/words.json", "w", encoding="utf-8"), ensure_ascii=False)
print("yeni süre:", round(duration(f"{S}/voice_cut.wav"), 2))
