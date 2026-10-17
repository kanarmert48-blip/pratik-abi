"""Videolar arasında ortak kullanılan grafik parçaları ve kapanış sahnesi."""
import math
from engine import *  # noqa

GLASS = (14, 18, 32, 205)


def glass(L, x0, y0, w, h, alpha=1.0, r=36):
    card(L, x0, y0, w, h, r=r, fill=GLASS, outline=(255, 255, 255, 40), width=2, alpha=alpha)


def stamp(L, cx, cy, text, col, t, start, rot=-12, size=70):
    p = ph(t, start, 0.28)
    if p <= 0:
        return
    s = lerp(2.2, 1.0, eo(p))
    f = font("black", size)
    tw = int(ImageDraw.Draw(L).textlength(text, font=f))
    im = Image.new("RGBA", (tw + 80, size + 70), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([8, 8, im.width - 8, im.height - 8], radius=18, outline=col + (255,), width=10)
    d.text((im.width / 2, im.height / 2 + 2), text, font=f, fill=col + (255,), anchor="mm")
    im = im.rotate(rot, resample=Image.BICUBIC, expand=True)
    im = im.resize((int(im.width * s), int(im.height * s)), Image.BICUBIC)
    comp(L, set_alpha(im, min(1, p * 2)), cx - im.width / 2, cy - im.height / 2)


def toggle(L, x, y, on_p, col):
    d = ImageDraw.Draw(L)
    bgc = tuple(int(lerp(a, b, on_p)) for a, b in zip((90, 95, 110), col))
    d.rounded_rectangle([x, y, x + 120, y + 64], radius=32, fill=bgc + (255,))
    kx = lerp(x + 32, x + 88, eio(on_p))
    d.ellipse([kx - 26, y + 6, kx + 26, y + 58], fill=(255, 255, 255, 255))


def outro(v, sc, L, t, y_card=560):
    """Yorum + beğen + takip kapanışı ('senin', 'yorumlarda', 'beğenmeyi' kelimelerine göre)."""
    ts, tyo, tbe = v.wt(sc, "senin"), v.wt(sc, "yorumlarda"), v.wt(sc, "beğenmeyi")
    q = ph(t, ts - 0.1, 0.45)
    if q > 0:
        dy = (1 - eo(q)) * 60
        glass(L, 120, y_card + dy, 840, 300, alpha=eo(q))
        put_icon(L, "speech_balloon", 250, y_card + 150 + dy + 6 * math.sin(t * 2.5), 170 * eb(q))
        text_c(L, (370, y_card + 110 + dy), "Senin yöntemin ne?", "black", 50, WHITE, anchor="lm", alpha=eo(q))
        text_c(L, (370, y_card + 185 + dy), "Yorumlarda buluşalım", "b", 40, ACC, anchor="lm", alpha=eo(ph(t, tyo, 0.3)))
    q2 = ph(t, tbe - 0.1, 0.45)
    if q2 > 0:
        put_icon(L, "thumbs_up", 360, y_card + 440 + 8 * math.sin(t * 2.4), 190 * eb(q2), rot=-8)
        chip(L, 360, y_card + 570, "Beğen", bg=ACC, fg=INK, size=42, k="black", scale=eb(ph(t, tbe + 0.1, 0.4)))
        tb = tbe + 0.45
        put_icon(L, "bell", 720, y_card + 440 + 8 * math.sin(t * 2.4 + 1), 190 * eb(ph(t, tb, 0.45)),
                 rot=14 * math.sin(t * 9) * (1 - ph(t, tb + 1.0, 0.8)))
        chip(L, 720, y_card + 570, "Takip et", bg=RED, fg=WHITE, size=42, k="black", scale=eb(ph(t, tb + 0.15, 0.4)))


def build_bg(segs, out, M):
    import os, subprocess, tempfile
    tmp = tempfile.mkdtemp()
    parts = []
    for i, s in enumerate(segs):
        assert s["dur"] > 0, f"segment {i} süresi negatif: {s['dur']}"
        p = os.path.join(tmp, f"s{i}.mp4")
        vf = (f"{s.get('pre', '')}scale=1188:2112:force_original_aspect_ratio=increase:flags=lanczos,crop=1188:2112,"
              f"fps={FPS},eq=contrast=1.05:saturation=1.10,unsharp=5:5:0.5,setsar=1,format=yuv420p")
        if s["kind"] == "photo":
            inp = ["-loop", "1", "-t", f"{s['dur']:.3f}", "-i", s["src"]]
        else:
            dur_src = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of",
                                            "csv=p=0", s["src"]], capture_output=True, text=True).stdout or 0)
            ss = s.get("ss", 0)
            if dur_src - ss >= s["dur"] + 0.1:
                inp = ["-ss", f"{ss:.3f}", "-i", s["src"]]
            else:
                inp = ["-stream_loop", "-1", "-i", s["src"]]
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *inp, "-vf", vf, "-an", "-frames:v",
                        str(int(round(s["dur"] * FPS))), "-c:v", "libx264", "-preset", "veryfast", "-crf", "14", p],
                       check=True)
        parts.append(p)
    lst = os.path.join(tmp, "l.txt")
    open(lst, "w").write("".join(f"file '{p}'\n" for p in parts))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", out],
                   check=True)


def compress(src, dst):
    import subprocess
    # HEVC: aynı boyutta H.264'ten çok daha temiz görüntü (YouTube destekler)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", src, "-c:v", "libx265", "-preset", "medium", "-crf", "21",
                    "-x265-params", "vbv-maxrate=3900:vbv-bufsize=8000:log-level=error", "-tag:v", "hvc1",
                    "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart", dst], check=True)


def arrow(L, t, start, frm, tip, bend=0.28, col=(255, 255, 255), width=11, gap=22, dur=0.5):
    """Zarif, kendi kendine çizilen kavisli ok. frm: başlangıç noktası, tip: gösterilen nokta (ok ucu
    hedefin 'gap' kadar önünde durur). bend: kavis miktarı (+/- yön)."""
    p = ph(t, start, dur)
    if p <= 0:
        return
    p = eo(p)
    (x0, y0), (x1, y1) = frm, tip
    dx, dy = x1 - x0, y1 - y0
    dist = math.hypot(dx, dy) or 1
    x1, y1 = x1 - dx / dist * gap, y1 - dy / dist * gap  # hedefi kapatma
    nud = 6 * math.sin((t - start) * 4.2) * ph(t, start + dur, 0.3)  # hafif dürtme
    x1, y1 = x1 + dx / dist * nud, y1 + dy / dist * nud
    cx, cy = (x0 + x1) / 2 - dy * bend, (y0 + y1) / 2 + dx * bend
    n = 48
    pts = []
    for i in range(int(n * p) + 1):
        u = i / n
        pts.append(((1 - u) ** 2 * x0 + 2 * (1 - u) * u * cx + u * u * x1,
                    (1 - u) ** 2 * y0 + 2 * (1 - u) * u * cy + u * u * y1))
    if len(pts) < 2:
        return
    S = 2  # süper örnekleme
    mx = 60
    bx0 = int(min(min(q[0] for q in pts), x1) - mx); by0 = int(min(min(q[1] for q in pts), y1) - mx)
    bx1 = int(max(max(q[0] for q in pts), x1) + mx); by1 = int(max(max(q[1] for q in pts), y1) + mx)
    w, h = bx1 - bx0, by1 - by0
    big = Image.new("RGBA", (w * S, h * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(big)
    P = [((x - bx0) * S, (y - by0) * S) for x, y in pts]
    lw = width * S
    d.line(P, fill=col + (255,), width=lw, joint="curve")
    r = lw / 2
    d.ellipse([P[0][0] - r, P[0][1] - r, P[0][0] + r, P[0][1] + r], fill=col + (255,))
    if p > 0.82:  # ok ucu: zarif açık uç
        hx, hy = P[-1]
        ax, ay = P[-1][0] - P[-4][0], P[-1][1] - P[-4][1]
        al = math.hypot(ax, ay) or 1
        ax, ay = ax / al, ay / al
        hl = 30 * S * eb(ph(p, 0.82, 0.18))
        for sgn in (1, -1):
            ang = math.radians(150 * sgn)
            ex = hx + hl * (ax * math.cos(ang) - ay * math.sin(ang))
            ey = hy + hl * (ax * math.sin(ang) + ay * math.cos(ang))
            d.line([(hx, hy), (ex, ey)], fill=col + (255,), width=lw)
            d.ellipse([ex - r, ey - r, ex + r, ey + r], fill=col + (255,))
        d.ellipse([hx - r, hy - r, hx + r, hy + r], fill=col + (255,))
    small = big.resize((w, h), Image.LANCZOS)
    sh = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    sh.putalpha(small.getchannel("A").point(lambda v: int(v * 0.55)))
    sh = sh.filter(ImageFilter.GaussianBlur(5))
    comp(L, sh, bx0 + 2, by0 + 5)
    comp(L, small, bx0, by0)
