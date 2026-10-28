import sys, json, subprocess, numpy as np
sys.path.insert(0, "/home/claude/shorts-oto/pro")
import audio_tools as at
SR = 44100
SPD = 1.08
x = np.frombuffer(subprocess.run(["ffmpeg", "-loglevel", "error", "-i", "voice_raw.wav", "-af", f"atempo={SPD}", "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True, check=True).stdout, np.float32).copy()
ws = json.load(open("wh.json", encoding="utf-8"))
for w in ws:
    w["s"] /= SPD; w["e"] /= SPD
ka, kb = 0.06, 0.09
R1, R2 = 7.0, 12.1
raw = [(0.0, 2.369, 0.35), (3.071, 3.637, 0.22), (4.340, 5.202, 0.18), (5.606, 7.654, 0.4), (8.346, 9.233, R1),
       (9.864, 11.124, 0.2), (11.622, 12.012, R2), (13.168, 14.115, 0.35), (14.563, 16.993, 0.22), (17.353, 19.376, 0.35),
       (20.134, 22.795, 0.35), (23.233, 25.115, 0.4), (25.926, 27.562, 0.22), (28.131, 28.917, 0.35), (29.550, 32.158, None)]
plan = []
for i, (a, b, g) in enumerate(raw):
    a, b = a / SPD, b / SPD
    plan.append((max(0, a - (kb if i else 0)), b + (ka if g is not None else 0.12), g))
out, mp, t = [], [], 0.0
ends = []
for a, b, gap in plan:
    seg = x[int(a * SR):int(b * SR)].copy(); n = int(0.008 * SR)
    seg[:n] *= np.linspace(0, 1, n); seg[-n:] *= np.linspace(1, 0, n)
    out.append(seg); mp.append((a, b, t)); t += b - a
    ends.append(round(t, 3))
    if gap:
        g = gap - ka - kb; out.append(np.zeros(int(round(g * SR)), np.float32)); t += g
y = np.concatenate(out); f = int(0.15 * SR); y[-f:] *= np.linspace(1, 0, f) ** 2
y = np.concatenate([y, np.zeros(int(0.25 * SR), np.float32)])
at._write("voice_cut.wav", y)
def rm(tt, start=True):
    best = None
    for a, b, n0 in mp:
        if a <= tt <= b: return n0 + tt - a
        if tt < a: return (n0 + min(kb, b - a)) if (start or best is None) else best
        best = n0 + (b - a)
    return best
fix = {"strop": "Stroop", "söylemekse": "söylemekse"}
words = [{"w": fix.get(w["w"], w["w"]), "s": round(rm(w["s"]), 3), "e": round(rm(w["e"], False), 3)} for w in ws if w["s"] < 32.0 / SPD]
json.dump(words, open("words.json", "w", encoding="utf-8"), ensure_ascii=False)
json.dump({"piece_ends": ends}, open("marks.json", "w"))
print("süre", round(len(y) / SR, 2))
print("parça sonları", ends)
print(" ".join(f"{w['w']}[{w['s']:.2f}]" for w in words))
