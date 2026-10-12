"""İstek dosyasındaki görselleri/klipleri indirir (GitHub Actions'ta çalışır).

İstek formatı (requests/<id>.json):
{
  "id": "deneme",
  "items": [
    {"name": "araba", "source": "pixabay_video", "q": "car highway", "n": 2},
    {"name": "volvo", "source": "wikimedia", "q": "Volvo PV544", "n": 1},
    {"name": "market", "source": "pixabay_photo", "q": "supermarket shelf", "n": 2},
    {"name": "ozel", "source": "url", "url": "https://..."}
  ]
}
Çıktı: media/<id>/<name>_<k>.<ext> ve media/<id>/manifest.json (kaynak + lisans bilgisi)
"""
import json, os, re, sys, time, urllib.parse, urllib.request
from pathlib import Path

UA = "PratikAbiMediaFetcher/1.0 (https://github.com/kanarmert48-blip/pratik-abi)"
KEY = os.environ.get("PIXABAY_API_KEY", "")
MAX_BYTES = 90 * 1024 * 1024


def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def download(url, dest):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=180) as r:
        size = int(r.headers.get("Content-Length") or 0)
        if size > MAX_BYTES:
            raise RuntimeError(f"çok büyük ({size} bayt)")
        data = r.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise RuntimeError("çok büyük")
    dest.write_bytes(data)
    return len(data)


def ext_of(url, default):
    m = re.search(r"\.([a-zA-Z0-9]{2,4})(?:$|\?)", urllib.parse.urlparse(url).path)
    return (m.group(1).lower() if m else default)


def pixabay_video(q, n, vid=None):
    params = {"key": KEY, "per_page": max(3, n), "safesearch": "true"}
    if vid:
        params["id"] = vid
    else:
        params["q"] = q[:100]
    url = "https://pixabay.com/api/videos/?" + urllib.parse.urlencode(params)
    out = []
    for h in get_json(url).get("hits", [])[:n]:
        v = h["videos"]
        pick = None
        for k in ("large", "medium", "small"):  # en yüksek çözünürlük (4K varsa 4K)
            c = v.get(k) or {}
            if c.get("url") and c.get("width", 0) <= 3840 and (c.get("size", 0) or 0) < MAX_BYTES:
                pick = c
                break
        if pick:
            out.append({"url": pick["url"], "ext": "mp4", "width": pick.get("width"), "height": pick.get("height"),
                        "duration": h.get("duration"), "page": h.get("pageURL"), "author": h.get("user"),
                        "license": "Pixabay Content License"})
    return out


def pixabay_photo(q, n):
    url = "https://pixabay.com/api/?" + urllib.parse.urlencode(
        {"key": KEY, "q": q[:100], "per_page": max(3, n), "image_type": "photo", "safesearch": "true"})
    out = []
    for h in get_json(url).get("hits", [])[:n]:
        out.append({"url": h["largeImageURL"], "ext": ext_of(h["largeImageURL"], "jpg"),
                    "width": h.get("imageWidth"), "height": h.get("imageHeight"), "page": h.get("pageURL"),
                    "author": h.get("user"), "license": "Pixabay Content License"})
    return out


def wikimedia(q, n):
    url = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode({
        "action": "query", "format": "json", "generator": "search", "gsrsearch": f"filetype:bitmap {q}",
        "gsrnamespace": 6, "gsrlimit": max(5, n * 3), "prop": "imageinfo",
        "iiprop": "url|size|extmetadata", "iiurlwidth": 1920})
    pages = sorted(get_json(url).get("query", {}).get("pages", {}).values(), key=lambda p: p.get("index", 0))
    out = []
    for p in pages:
        ii = (p.get("imageinfo") or [{}])[0]
        meta = ii.get("extmetadata", {})
        lic = (meta.get("LicenseShortName") or {}).get("value", "")
        if not lic:
            continue
        artist = re.sub("<[^>]+>", "", (meta.get("Artist") or {}).get("value", "")).strip()
        src = ii.get("thumburl") or ii.get("url")
        out.append({"url": src, "ext": ext_of(src, "jpg"), "width": ii.get("thumbwidth") or ii.get("width"),
                    "height": ii.get("thumbheight") or ii.get("height"), "page": ii.get("descriptionurl"),
                    "author": artist[:200], "license": lic, "title": p.get("title")})
        if len(out) >= n:
            break
    return out


def main(req_path):
    req = json.loads(Path(req_path).read_text(encoding="utf-8"))
    rid = re.sub(r"[^a-z0-9_-]", "-", req["id"].lower())
    outdir = Path("media") / rid
    outdir.mkdir(parents=True, exist_ok=True)
    manifest = []
    for it in req["items"]:
        name = re.sub(r"[^a-z0-9_-]", "-", it["name"].lower())
        src, n = it["source"], int(it.get("n", 1))
        try:
            if src == "pixabay_video":
                found = pixabay_video(it["q"], n)
            elif src == "pixabay_video_id":
                found = pixabay_video("", 1, vid=str(it["id"]))
            elif src == "pixabay_photo":
                found = pixabay_photo(it["q"], n)
            elif src == "wikimedia":
                found = wikimedia(it["q"], n)
            elif src == "url":
                found = [{"url": it["url"], "ext": ext_of(it["url"], "jpg"), "page": it.get("page", it["url"]),
                          "author": it.get("author", ""), "license": it.get("license", "")}]
            else:
                raise ValueError(f"bilinmeyen kaynak: {src}")
        except Exception as e:
            manifest.append({"name": name, "error": f"arama hatası: {e}"})
            print(f"[HATA] {name}: {e}")
            continue
        if not found:
            manifest.append({"name": name, "error": "sonuç yok", "q": it.get("q")})
            print(f"[YOK] {name}: {it.get('q')}")
        for k, f in enumerate(found, 1):
            dest = outdir / f"{name}_{k}.{f['ext']}"
            try:
                size = download(f["url"], dest)
                f.update({"name": name, "file": dest.name, "bytes": size, "q": it.get("q")})
                print(f"[OK] {dest} ({size // 1024} KB)")
            except Exception as e:
                f.update({"name": name, "error": f"indirme hatası: {e}"})
                print(f"[HATA] {dest}: {e}")
            f.pop("url", None) if src != "url" else None
            manifest.append(f)
            time.sleep(0.3)
    (outdir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    for p in sys.argv[1:]:
        main(p)
