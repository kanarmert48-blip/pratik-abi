"""YouTube'a Short yükler (YouTube Data API v3, OAuth refresh token).
Gizli bilgiler sadece ortam değişkeninden gelir (GitHub secrets): YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN.
Kullanım: python3 yt_yukle.py <meta.json> <video.mp4> <sonuc.json>"""
import json, os, sys, urllib.parse, urllib.request

meta = json.load(open(sys.argv[1], encoding="utf-8"))
video, out = sys.argv[2], sys.argv[3]
for k in ("YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN"):
    if not os.environ.get(k):
        json.dump({"ok": False, "hata": f"{k} secret eksik"}, open(out, "w"), ensure_ascii=False)
        sys.exit(1)

tok = json.load(urllib.request.urlopen(urllib.request.Request(
    "https://oauth2.googleapis.com/token",
    data=urllib.parse.urlencode({"client_id": os.environ["YT_CLIENT_ID"], "client_secret": os.environ["YT_CLIENT_SECRET"],
                                 "refresh_token": os.environ["YT_REFRESH_TOKEN"], "grant_type": "refresh_token"}).encode())))["access_token"]

body = {"snippet": {"title": meta["title"][:100], "description": meta.get("description", ""),
                    "tags": meta.get("tags", []), "categoryId": str(meta.get("categoryId", "27")),
                    "defaultLanguage": meta.get("lang", "en"), "defaultAudioLanguage": meta.get("lang", "en")},
        "status": {"privacyStatus": meta.get("privacy", "public"), "selfDeclaredMadeForKids": False,
                   "containsSyntheticMedia": bool(meta.get("ai", False))}}
req = urllib.request.Request("https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status",
                             data=json.dumps(body).encode(), method="POST",
                             headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json; charset=UTF-8",
                                      "X-Upload-Content-Type": "video/mp4",
                                      "X-Upload-Content-Length": str(os.path.getsize(video))})
loc = urllib.request.urlopen(req).headers["Location"]
with open(video, "rb") as f:
    res = json.load(urllib.request.urlopen(urllib.request.Request(
        loc, data=f.read(), method="PUT", headers={"Authorization": f"Bearer {tok}", "Content-Type": "video/mp4"})))
json.dump({"ok": True, "id": res["id"], "url": f"https://youtube.com/shorts/{res['id']}"}, open(out, "w"))
print("yüklendi", res["id"])
