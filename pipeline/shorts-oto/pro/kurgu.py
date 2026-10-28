import sys, json, subprocess, numpy as np
sys.path.insert(0, "/home/claude/shorts-oto/pro")
import audio_tools as at
SR = 44100
SPD = 1.1
x = np.frombuffer(subprocess.run(["ffmpeg", "-loglevel", "error", "-i", "voice_raw.wav", "-af", f"atempo={SPD}", "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True, check=True).stdout, np.float32).copy()
ws = json.load(open("wh.json", encoding="utf-8"))
for w in ws:
    w["s"] /= SPD; w["e"] /= SPD
ka, kb = 0.06, 0.09
G1, G2 = 3.2, 2.8
raw = [(0.0, 1.424, 0.3), (2.152, 2.771, 0.32), (3.696, 5.944, 0.3), (6.71, 8.771, 1.8), (9.669, 12.346, 0.35),
       (13.232, 16.454, 0.35), (18.78, 23.206, 0.4), (28.13, 28.396, 0.21), (29.256, 31.105, 0.32), (31.80, 33.686, 0.2),
       (34.14, 37.304, 0.4), (38.137, 43.937, 0.4), (44.935, 46.787, 0.25), (47.358, 48.237, 0.35), (49.317, 51.94, None)]
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
fix = {"hala": "hâlâ", "Baş": "Baş"}
words = [{"w": fix.get(w["w"], w["w"]), "s": round(rm(w["s"]), 3), "e": round(rm(w["e"], False), 3)} for w in ws if any(a - 0.12 <= (w["s"] + w["e"]) / 2 <= b + 0.12 for a, b, _ in mp)]
json.dump(words, open("words.json", "w", encoding="utf-8"), ensure_ascii=False)
json.dump({"piece_ends": ends}, open("marks.json", "w"))
print("süre", round(len(y) / SR, 2))
print("parça sonları", ends)
print(" ".join(f"{w['w']}[{w['s']:.2f}]" for w in words))
