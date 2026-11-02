import wave, numpy as np, json, sys
S=sys.argv[1]
wf=wave.open(S+"/t/a16.wav"); a=np.frombuffer(wf.readframes(wf.getnframes()),dtype=np.int16).astype(np.float32)/32768
sr=16000; hop=160
rms=np.sqrt(np.convolve(a**2,np.ones(400)/400,mode="same")[::hop])
def snap(t,lo,hi):
    i0,i1=int((t+lo)*100),int((t+hi)*100)
    return (i0+int(np.argmin(rms[i0:i1])))/100
# (ses_bas, ses_son, video_bas or None) — kaba sınırlar, sessizliğe oturtulur
P=[(0.00,3.80,None),(9.20,13.25,None),(16.90,22.00,None),(247.10,248.85,None),(249.30,252.20,None),
   (267.70,268.75,None),(269.25,273.35,None),(284.60,286.25,None),(290.00,295.15,None),
   (304.15,306.75,None),(390.40,397.00,397.6)]
out=[]
for s,e,v in P:
    s2=0.0 if s==0 else snap(s,-0.2,0.15); e2=snap(e,-0.15,0.2)
    out.append([s2,e2,v])
    print(f"{s:.2f}->{s2:.2f}  {e:.2f}->{e2:.2f}")
json.dump(out,open(S+"/tz/cuts.json","w"))
print("toplam", round(sum(e-s for s,e,_ in out),2))
