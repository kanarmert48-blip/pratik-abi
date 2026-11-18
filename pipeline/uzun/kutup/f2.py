import sys, json, re
sys.path.insert(0,'/home/claude/shorts-oto/pro')
import ai_tools as a, parselmouth, numpy as np
def analyze(f):
    snd=parselmouth.Sound(f); fm=snd.to_formant_burg(max_number_of_formants=5, maximum_formant=5000)
    out=[]
    for w in a.transcribe(f):
        t=re.sub(r'[^\wâçğıöşü-]','',w['w'].lower())
        if t.startswith(('kar','kâr','ka-')) :
            s,e=float(w['s']),float(w['e']); d=e-s
            ts=np.linspace(s+0.12*d, s+0.45*d, 8)
            f1=np.nanmedian([fm.get_value_at_time(1,x) for x in ts]); f2=np.nanmedian([fm.get_value_at_time(2,x) for x in ts])
            out.append((t, round(s,2), round(d,2), int(f1), int(f2)))
    return out
for f in sys.argv[1:]:
    print(f, analyze(f))
