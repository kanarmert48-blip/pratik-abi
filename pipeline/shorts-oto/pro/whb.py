import sys, json
sys.path.insert(0, "/home/claude/shorts-oto/pro")
import ai_tools
m = ai_tools._whisper()
for i in range(1, 2):
    f = f"ses/raw{i}.wav"
    segs, _ = m.transcribe(ai_tools.load_audio(f), language="tr", word_timestamps=True, beam_size=5, vad_filter=False)
    ws = [{"w": w.word.strip(), "s": round(w.start, 3), "e": round(w.end, 3), "p": round(w.probability, 3)} for s in segs for w in s.words]
    json.dump(ws, open(f"ses/raw{i}.json", "w"), ensure_ascii=False)
    print(i, " ".join(f"{w['w']}[{w['s']:.1f}-{w['e']:.1f}]" for w in ws), flush=True)
    print("   şüpheli:", [(w['w'], w['p']) for w in ws if w['p'] < 0.5], flush=True)
