"""Verilen kanalların son videolarını detaylı çeker -> out/inc_<handle>.json + en çok izlenenlerin kapakları"""
import json, os, sys, urllib.request, urllib.parse
KEY = os.environ["YT_API_KEY"]
def api(path, **q):
    q["key"] = KEY
    with urllib.request.urlopen(f"https://www.googleapis.com/youtube/v3/{path}?" + urllib.parse.urlencode(q)) as r:
        return json.load(r)
os.makedirs("out", exist_ok=True)
for H in sys.argv[1].split(","):
    H = H.strip()
    ch = api("channels", part="snippet,statistics,contentDetails", forHandle=H)["items"][0]
    up = ch["contentDetails"]["relatedPlaylists"]["uploads"]
    ids, tok = [], None
    while len(ids) < 150:
        r = api("playlistItems", part="contentDetails", playlistId=up, maxResults=50, **({"pageToken": tok} if tok else {}))
        ids += [i["contentDetails"]["videoId"] for i in r["items"]]
        tok = r.get("nextPageToken")
        if not tok: break
    vids = []
    for i in range(0, len(ids), 50):
        for v in api("videos", part="snippet,statistics,contentDetails", id=",".join(ids[i:i+50]))["items"]:
            s, sn = v["statistics"], v["snippet"]
            th = sn["thumbnails"].get("maxres") or sn["thumbnails"].get("high") or sn["thumbnails"]["default"]
            vids.append({"id": v["id"], "baslik": sn["title"], "tarih": sn["publishedAt"], "sure": v["contentDetails"]["duration"],
                         "izlenme": int(s.get("viewCount", 0)), "begeni": int(s.get("likeCount", 0)),
                         "yorum": int(s.get("commentCount", 0)), "etiket": sn.get("tags", [])[:15],
                         "aciklama": sn.get("description", "")[:400], "kapak": th["url"]})
    out = {"kanal": ch["snippet"]["title"], "handle": H, "abone": int(ch["statistics"].get("subscriberCount", 0)),
           "toplam": int(ch["statistics"].get("viewCount", 0)), "video_sayisi": int(ch["statistics"].get("videoCount", 0)),
           "acilis": ch["snippet"]["publishedAt"], "kanal_aciklama": ch["snippet"].get("description", "")[:500], "videolar": vids}
    slug = H.lstrip("@")
    json.dump(out, open(f"out/inc_{slug}.json", "w"), ensure_ascii=False, indent=1)
    for k, v in enumerate(sorted(vids, key=lambda v: -v["izlenme"])[:6]):
        try:
            urllib.request.urlretrieve(v["kapak"], f"out/kapak_{slug}_{k}_{v['id']}.jpg")
        except Exception as e:
            print("kapak", e, file=sys.stderr)
    print(H, len(vids))
