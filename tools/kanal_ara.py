"""Türkiye'de benzer konseptte (ilginç bilgi / neden / bilim) Shorts kanallarını bulur -> out/rakipler.json"""
import json, os, urllib.request, urllib.parse, datetime, collections
KEY = os.environ["YT_API_KEY"]
def api(path, **q):
    q["key"] = KEY
    with urllib.request.urlopen(f"https://www.googleapis.com/youtube/v3/{path}?" + urllib.parse.urlencode(q)) as r:
        return json.load(r)
Q = ["ilginç bilgiler", "bunu biliyor muydun", "neden", "bilmediğiniz bilgiler", "ilginç bilgi shorts",
     "hiç düşündün mü", "bilim shorts", "şaşırtıcı bilgiler", "günlük hayat bilgileri", "bilgi kanalı shorts"]
after = (datetime.datetime.utcnow() - datetime.timedelta(days=120)).strftime("%Y-%m-%dT%H:%M:%SZ")
hits = collections.defaultdict(lambda: {"n": 0, "views": 0, "videos": []})
vids = []
for q in Q:
    r = api("search", part="snippet", q=q, type="video", videoDuration="short", regionCode="TR",
            relevanceLanguage="tr", order="viewCount", publishedAfter=after, maxResults=50)
    vids += [(i["id"]["videoId"], i["snippet"]["channelId"], i["snippet"]["title"]) for i in r.get("items", [])]
ids = list({v[0] for v in vids})
vs = {}
for i in range(0, len(ids), 50):
    for v in api("videos", part="statistics,snippet", id=",".join(ids[i:i+50]))["items"]:
        vs[v["id"]] = (int(v["statistics"].get("viewCount", 0)), v["snippet"]["title"], v["snippet"]["channelId"],
                       v["snippet"].get("defaultAudioLanguage", ""))
for vid, (views, title, ch, lang) in vs.items():
    h = hits[ch]; h["n"] += 1; h["views"] += views; h["videos"].append((views, title))
chs = list(hits)
out = []
for i in range(0, len(chs), 50):
    for c in api("channels", part="snippet,statistics", id=",".join(chs[i:i+50]))["items"]:
        h = hits[c["id"]]
        out.append({"id": c["id"], "ad": c["snippet"]["title"], "handle": c["snippet"].get("customUrl", ""),
                    "ulke": c["snippet"].get("country", ""), "abone": int(c["statistics"].get("subscriberCount", 0)),
                    "toplam_izlenme": int(c["statistics"].get("viewCount", 0)), "video": int(c["statistics"].get("videoCount", 0)),
                    "eslesen_video": h["n"], "eslesen_izlenme": h["views"],
                    "ornekler": sorted(h["videos"], reverse=True)[:4]})
out.sort(key=lambda x: -x["eslesen_izlenme"])
os.makedirs("out", exist_ok=True)
json.dump(out, open("out/rakipler.json", "w"), ensure_ascii=False, indent=1)
print(len(out), "kanal")
