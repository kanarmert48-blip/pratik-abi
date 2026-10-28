"""Konu doygunluk analizi: her aday için TR ve global Shorts araması -> out/konu_analiz.json
Kullanım: KONULAR env (json) = [{"ad":..,"tr":[sorgu..],"en":[sorgu..]}]"""
import json, os, urllib.request, urllib.parse
KEY = os.environ["YT_API_KEY"]
def api(path, **q):
    q["key"] = KEY
    with urllib.request.urlopen(f"https://www.googleapis.com/youtube/v3/{path}?" + urllib.parse.urlencode(q)) as r:
        return json.load(r)
konular = json.load(open("tools/konular.json", encoding="utf-8"))
out = []
for k in konular:
    res = {"ad": k["ad"]}
    for dil in ("tr", "en"):
        ids = []
        for q in k.get(dil, []):
            p = dict(part="snippet", q=q, type="video", videoDuration="short", order="relevance", maxResults=50)
            if dil == "tr":
                p.update(regionCode="TR", relevanceLanguage="tr")
            else:
                p.update(relevanceLanguage="en")
            try:
                r = api("search", **p)
            except Exception as e:
                res[dil + "_hata"] = str(e); continue
            ids += [i["id"]["videoId"] for i in r.get("items", [])]
        ids = list(dict.fromkeys(ids))
        vids = []
        for i in range(0, len(ids), 50):
            for v in api("videos", part="statistics,snippet", id=",".join(ids[i:i+50])).get("items", []):
                vids.append({"id": v["id"], "baslik": v["snippet"]["title"], "kanal": v["snippet"]["channelTitle"],
                             "tarih": v["snippet"]["publishedAt"][:10], "izlenme": int(v["statistics"].get("viewCount", 0)),
                             "dil": v["snippet"].get("defaultAudioLanguage", "")})
        vids.sort(key=lambda x: -x["izlenme"])
        import re
        rx = re.compile(k.get("kw_" + dil, k.get("kw", ".")), re.I)
        rel = [v for v in vids if rx.search(v["baslik"])]
        res[dil + "_ilgili"] = {"sayi": len(rel), "100k_ustu": sum(v["izlenme"] >= 100_000 for v in rel),
                                "1m_ustu": sum(v["izlenme"] >= 1_000_000 for v in rel), "liste": rel[:12]}
        res[dil] = {"sonuc": len(vids), "100k_ustu": sum(v["izlenme"] >= 100_000 for v in vids),
                    "1m_ustu": sum(v["izlenme"] >= 1_000_000 for v in vids), "en_iyi": vids[:6]}
    out.append(res)
os.makedirs("out", exist_ok=True)
json.dump(out, open("out/konu_analiz.json", "w"), ensure_ascii=False, indent=1)
print("bitti", len(out))
