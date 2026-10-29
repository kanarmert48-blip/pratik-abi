"""Son N günde TR'de patlayan Shorts'lar (ilgi çekici/dene türü) + kanal büyüklüğüne göre sıra dışılık.
Çıktı: out/trend_analiz.json"""
import json, os, urllib.request, urllib.parse, datetime
KEY = os.environ["YT_API_KEY"]
GUN = int(os.environ.get("GUN", "30"))
def api(path, **q):
    q["key"] = KEY
    with urllib.request.urlopen(f"https://www.googleapis.com/youtube/v3/{path}?" + urllib.parse.urlencode(q)) as r:
        return json.load(r)
SORGU = ["hemen dene", "yapamazsın", "bu videoya bak", "15 saniye bak", "bunu bilmiyordun", "ilginç bilgi",
         "beynin seni kandırıyor", "gözünü kırpma", "kimse fark etmedi", "bunu dene", "test et", "sakın kaydırma",
         "inanamayacaksın", "gizli özellik", "%99 bilmiyor", "dikkatli bak"]
after = (datetime.datetime.utcnow() - datetime.timedelta(days=GUN)).strftime("%Y-%m-%dT%H:%M:%SZ")
ids, kaynak = [], {}
for q in SORGU:
    try:
        r = api("search", part="snippet", q=q, type="video", videoDuration="short", order="viewCount", maxResults=50,
                regionCode="TR", relevanceLanguage="tr", publishedAfter=after)
    except Exception as e:
        print("hata", q, e); continue
    for i in r.get("items", []):
        v = i["id"]["videoId"]
        if v not in kaynak:
            ids.append(v); kaynak[v] = q
vids = []
for i in range(0, len(ids), 50):
    for v in api("videos", part="statistics,snippet,contentDetails", id=",".join(ids[i:i+50])).get("items", []):
        s = v["statistics"]
        vids.append({"id": v["id"], "baslik": v["snippet"]["title"], "kanal": v["snippet"]["channelTitle"],
                     "kanal_id": v["snippet"]["channelId"], "tarih": v["snippet"]["publishedAt"][:10],
                     "izlenme": int(s.get("viewCount", 0)), "begeni": int(s.get("likeCount", 0)),
                     "yorum": int(s.get("commentCount", 0)), "dil": v["snippet"].get("defaultAudioLanguage", ""),
                     "sorgu": kaynak[v["id"]]})
cids = list({v["kanal_id"] for v in vids})
abone = {}
for i in range(0, len(cids), 50):
    for c in api("channels", part="statistics", id=",".join(cids[i:i+50])).get("items", []):
        abone[c["id"]] = int(c["statistics"].get("subscriberCount", 0) or 0)
for v in vids:
    v["abone"] = abone.get(v["kanal_id"], 0)
    v["oran"] = round(v["izlenme"] / max(1000, v["abone"]), 1)
vids.sort(key=lambda x: -x["izlenme"])
os.makedirs("out", exist_ok=True)
json.dump({"gun": GUN, "videolar": vids}, open("out/trend_analiz.json", "w"), ensure_ascii=False, indent=1)
print("bitti", len(vids))
