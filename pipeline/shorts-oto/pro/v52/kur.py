import json, re, subprocess, numpy as np
SR=44100
def load(f): return np.frombuffer(subprocess.run(["ffmpeg","-v","error","-i",f,"-ac","1","-ar",str(SR),"-f","f32le","-"],capture_output=True).stdout,np.float32).copy()
def sil(f):
    o=subprocess.run(["ffmpeg","-hide_banner","-i",f,"-af","silencedetect=noise=-40dB:d=0.12","-f","null","-"],capture_output=True,text=True).stderr
    return list(zip([float(x) for x in re.findall(r"silence_start: ([0-9.]+)",o)],[float(x) for x in re.findall(r"silence_end: ([0-9.]+)",o)]))
raw=json.load(open("ses/rawf.json"))
fix={"Başta.":"Başla.","3":"Üç"}
DUR={"A":5,"B":4,"C":3}
out=[];words=[];t=0.0;marks={}
for s in "ABCD":
    x=load(f"ses/{s}f.wav"); n=len(x)/SR; ws=raw[s]
    for w in ws: w["w"]=fix.get(w["w"],w["w"])
    S=sil(f"ses/{s}f.wav")
    # kesilecek aralıklar
    cuts=[]
    for a,b in S:
        if a<=0.02: cuts.append((0,max(0,b-0.04))); continue
        if b>=n-0.02: cuts.append((a+0.08,n)); continue
        before=[w for w in ws if w["e"]<=a+0.25]; p=before[-1]["w"][-1] if before else ""
        keep=0.26 if p in ".?!" else 0.12
        if s=="C" and before and before[-1]["w"].startswith("Burada"): keep=0.9
        if b-a>keep: m=(a+b)/2; cuts.append((a+0.03, a+0.03+(b-a-keep)))
    def mp(tt):
        r=tt
        for a,b in cuts:
            if tt>=b: r-= (b-a)
            elif tt>a: r-= (tt-a)
        return r
    keepm=np.ones(len(x),bool)
    for a,b in cuts: keepm[int(a*SR):int(b*SR)]=False
    y=x[keepm]
    if s=="C":
        bw=[w for w in ws if w["w"].startswith("Burada")][0]; ins_t=mp(bw["e"])+0.15; k=int(ins_t*SR)
        y=np.concatenate([y[:k],np.zeros(int(0.6*SR),np.float32),y[k:]])
        _mp=mp; mp=lambda tt,_m=_mp,_i=ins_t: _m(tt)+(0.6 if _m(tt)>_i else 0)
    # 8 ms fade at joins is skipped; cuts are in silence
    for w in ws: words.append({"w":w["w"],"s":round(t+mp(w["s"]),3),"e":round(t+mp(w["e"]),3),"seg":s})
    out.append(y); t+=len(y)/SR
    if s in DUR:
        g=0.25+DUR[s]+0.15
        marks[s]={"t0":round(t+0.25,3),"end":round(t+0.25+DUR[s],3)}
        out.append(np.zeros(int(g*SR),np.float32)); t+=g
v=np.concatenate(out)
import wave
w16=(np.clip(v,-1,1)*32767).astype(np.int16)
with wave.open("voice_cut.wav","wb") as f: f.setnchannels(1);f.setsampwidth(2);f.setframerate(SR);f.writeframes(w16.tobytes())
json.dump(words,open("words.json","w"),ensure_ascii=False); json.dump(marks,open("marks.json","w"))
print(round(t,2),marks); print(" ".join(f"{w['w']}@{w['s']}" for w in words))
