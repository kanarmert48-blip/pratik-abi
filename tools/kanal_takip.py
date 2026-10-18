"""YouTube Data API ile kanal ve son videoların istatistiklerini toplar -> out/kanal_<tarih>.json + out/kanal_son.json"""
import json, os, sys, urllib.request, urllib.parse, datetime
KEY = os.environ["YT_API_KEY"]
H = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("KANAL", "")
def api(path, **q):
    q["key"] = KEY
    with urllib.request.urlopen(f"https://www.googleapis.com/youtube/v3/{path}?" + urllib.parse.urlencode(q)) as r:
        return json.load(r)
q = {"forHandle": H} if H.startswith("@") else {"id": H}
r0 = api("channels", part="snippet,statistics,contentDetails", **q)
if not r0.get("items"):
    sr = api("search", part="snippet", type="channel", q=H.lstrip("@"), maxResults=10)
    print("BULUNAMADI. Aday kanallar:", file=sys.stderr)
    for it in sr.get("items", []):
        print(it["snippet"]["channelId"], it["snippet"]["title"], file=sys.stderr)
    sys.exit(1)
ch = r0["items"][0]
up = ch["contentDetails"]["relatedPlaylists"]["uploads"]
ids, tok = [], None
while len(ids) < 200:
    r = api("playlistItems", part="contentDetails", playlistId=up, maxResults=50, **({"pageToken": tok} if tok else {}))
    ids += [i["contentDetails"]["videoId"] for i in r["items"]]
    tok = r.get("nextPageToken")
    if not tok: break
vids = []
for i in range(0, len(ids), 50):
    for v in api("videos", part="snippet,statistics,contentDetails", id=",".join(ids[i:i+50]))["items"]:
        s = v["statistics"]
        vids.append({"id": v["id"], "baslik": v["snippet"]["title"], "tarih": v["snippet"]["publishedAt"],
                     "sure": v["contentDetails"]["duration"], "izlenme": int(s.get("viewCount", 0)),
                     "begeni": int(s.get("likeCount", 0)), "yorum": int(s.get("commentCount", 0))})
out = {"zaman": datetime.datetime.utcnow().isoformat() + "Z", "kanal": ch["snippet"]["title"], "id": ch["id"],
       "abone": int(ch["statistics"].get("subscriberCount", 0)), "toplam_izlenme": int(ch["statistics"].get("viewCount", 0)),
       "video_sayisi": int(ch["statistics"].get("videoCount", 0)), "videolar": vids}
os.makedirs("out", exist_ok=True)
d = datetime.date.today().isoformat()
for f in (f"out/kanal_{d}.json", "out/kanal_son.json"):
    json.dump(out, open(f, "w"), ensure_ascii=False, indent=1)
print(out["kanal"], out["abone"], "abone,", len(vids), "video")
