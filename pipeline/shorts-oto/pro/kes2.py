import json, re, subprocess, numpy as np
SR = 44100
def norm(w): return re.sub(r"[^\wçğıöşü]", "", w.lower())
def load(f):
    return np.frombuffer(subprocess.run(["ffmpeg","-v","error","-i",f,"-ac","1","-ar",str(SR),"-f","f32le","-"],capture_output=True).stdout,np.float32).copy()
def sil(f):
    out = subprocess.run(["ffmpeg","-hide_banner","-i",f,"-af","silencedetect=noise=-40dB:d=0.12","-f","null","-"],capture_output=True,text=True).stderr
    return list(zip([float(x) for x in re.findall(r"silence_start: ([0-9.]+)",out)],[float(x) for x in re.findall(r"silence_end: ([0-9.]+)",out)]))
for i in range(1, 2):
    ws = json.load(open(f"ses/raw{i}.json")); n = [norm(w["w"]) for w in ws]
    k = max(k for k in range(1, len(n)//2+1) if n[-k:] == n[-2*k:-k])
    end_first = ws[-k-1]["e"]
    x = load(f"ses/raw{i}.wav")
    S = [(a,b) for a,b in sil(f"ses/raw{i}.wav") if b > 0.05]
    # konuşma bitişi: end_first'ten sonraki ilk sessizliğin başı
    cut = end_first + 0.06
    out, words, t, src = [], [], 0.0, 0.0
    prev_end = 0.0
    segs = []
    pos = 0.0
    for a, b in S:
        if a >= cut or b >= cut: break
        if a <= 0.02: pos = b - 0.05; continue
        # sessizlikten önceki kelime
        before = [w for w in ws if w["e"] <= a + 0.25]
        p = before[-1]["w"][-1] if before else ""
        keep = 0.34 if p in ".?!" else 0.2 if p in ",;:" else 0.1
        segs.append((pos, a + 0.04, keep))
        pos = b - 0.04
    segs.append((pos, cut + 0.08, None))
    y, mp = [], []
    for a, b, keep in segs:
        s = x[int(a*SR):int(b*SR)].copy(); f = int(0.006*SR); s[:f] *= np.linspace(0,1,f); s[-f:] *= np.linspace(1,0,f)
        mp.append((a, b, t)); y.append(s); t += b - a
        if keep: y.append(np.zeros(int(keep*SR), np.float32)); t += keep
    y = np.concatenate(y); f = int(0.12*SR); y[-f:] *= np.linspace(1,0,f)**2
    def rm(tt):
        for a, b, n0 in mp:
            if a - 0.3 <= tt <= b: return n0 + max(0, tt - a)
        for a, b, n0 in mp:
            if a >= tt: return n0
        return None
    W2 = []
    for w in ws[:len(ws)-k]:
        s0, e0 = rm(w["s"]), rm(w["e"])
        if s0 is None or e0 is None: continue
        W2.append({"w": w["w"], "s": round(s0,3), "e": round(e0,3)})
    pcm = (np.clip(y,-1,1)*32767).astype("<i2").tobytes()
    subprocess.run(["ffmpeg","-y","-loglevel","error","-f","s16le","-ar",str(SR),"-ac","1","-i","-",f"ses/v{i}.wav"],input=pcm,check=True)
    json.dump(W2, open(f"ses/v{i}.json","w"), ensure_ascii=False)
    print(i, round(len(y)/SR,2), "son:", " ".join(w["w"] for w in W2[-4:]))
