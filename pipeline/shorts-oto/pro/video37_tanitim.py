"""v37 tanıtım Shorts'u: uzun videodan seçilen parçalar -> 1440x2560 dikey, üst başlık, altyazı, sonda 'ilgili video' oku.
Kullanım: python3 compose.py <S> [test t1,t2,..|render]"""
import json, math, subprocess, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

S = Path(sys.argv[1]); Z = S / "tz"; L = Z / "lay"; L.mkdir(exist_ok=True)
SRC = "/mnt/user-data/uploads/PratikAbi/37-dinozor-komik.mp4"
W, H = 1440, 2560
FG_H = 1094; FG_Y = 640
BOLD = "/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf"
YEL = (255, 212, 0); WHITE = (255, 255, 255)

cuts = json.load(open(Z / "cuts.json"))
outs = []; o = 0.0
for s, e, v in cuts:
    outs.append(o); o += e - s
TOTAL = o


def om(i, src):  # kaynak saniyesi -> çıktı saniyesi (parça i içinde)
    return outs[i] + (src - cuts[i][0])


def font(sz):
    return ImageFont.truetype(BOLD, sz)


def fit(txt, sz, maxw):
    while sz > 30:
        f = font(sz)
        if f.getlength(txt) <= maxw:
            return f
        sz -= 4
    return font(sz)


def layer(name, draw_fn):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw_fn(ImageDraw.Draw(im))
    p = L / f"{name}.png"; im.save(p); return p


def ctext(d, y, txt, sz, col, maxw=1300, stroke=8):
    f = fit(txt, sz, maxw)
    d.text((W / 2, y), txt, font=f, fill=col, anchor="mm", stroke_width=stroke, stroke_fill=(0, 0, 0))


def wrap(txt, sz, maxw):
    f = font(sz); words = txt.split(); lines = [""]
    for w in words:
        t = (lines[-1] + " " + w).strip()
        if f.getlength(t) <= maxw: lines[-1] = t
        else: lines.append(w)
    return lines


def top(d):
    # marka etiketi + tik
    f = font(44); t = "PratikAbi"; tw = f.getlength(t)
    x0 = W / 2 - (tw + 56) / 2
    d.text((x0, 230), t, font=f, fill=WHITE, anchor="lm", stroke_width=3, stroke_fill=(0, 0, 0))
    cx, cy = x0 + tw + 34, 232
    d.ellipse((cx - 20, cy - 20, cx + 20, cy + 20), fill=(29, 155, 240))
    d.line([(cx - 9, cy + 1), (cx - 2, cy + 8), (cx + 10, cy - 7)], fill=WHITE, width=6, joint="curve")
    ctext(d, 375, "TEK TERLİKLE", 112, WHITE)
    ctext(d, 505, "DİNOZORLAR ÇAĞINDA", 112, YEL)


def cap(txt, col=WHITE):
    def fn(d):
        sz = 80
        lines = wrap(txt, sz, 1240)
        if len(lines) > 2:
            sz = 70; lines = wrap(txt, sz, 1330)
        y0 = 1880 - (len(lines) - 1) * 50 if len(lines) < 3 else 1820
        for k, ln in enumerate(lines):
            ctext(d, y0 + k * int(sz * 1.25), ln, sz, col, maxw=1340, stroke=8)
    return fn


def cta(d):
    ctext(d, 1850, "DEVAMI İLGİLİ VİDEODA", 92, YEL)
    # sola-aşağı kıvrılan zarif ok (ilgili video bağlantısına)
    p0, p1, p2 = (1010, 1930), (900, 2190), (330, 2215)
    pts = [((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0],
            (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1]) for t in [i / 40 for i in range(41)]]
    for col, wd in (((0, 0, 0), 26), (YEL, 14)):
        d.line(pts, fill=col, width=wd, joint="curve")
    ang = math.atan2(pts[-1][1] - pts[-4][1], pts[-1][0] - pts[-4][0])
    tip = pts[-1]
    def head(sc):
        return [(tip[0] + math.cos(ang) * 10 * sc, tip[1] + math.sin(ang) * 10 * sc),
                (tip[0] + math.cos(ang + 2.5) * 52 * sc, tip[1] + math.sin(ang + 2.5) * 52 * sc),
                (tip[0] + math.cos(ang - 2.5) * 52 * sc, tip[1] + math.sin(ang - 2.5) * 52 * sc)]
    d.polygon(head(1.25), fill=(0, 0, 0)); d.polygon(head(1.0), fill=YEL)


# (parça, kaynak_bas, kaynak_son, metin, renk)
CAPS = [
    (0, None, None, "Bir sabah uyanıyorsun ve alarm çalmıyor.", WHITE),
    (1, None, None, "Çünkü burası 66 milyon yıl önce.", YEL),
    (2, None, None, "Yanında bir telefon, %12 şarj ve tek bir terlik var.", WHITE),
    (3, None, None, "Ve o an geliyor.", WHITE),
    (4, None, 251.2, "Arkanda bir kükreme.", WHITE),
    (4, 251.2, None, "KOŞ!", YEL),
    (5, None, None, "Kötü haber:", YEL),
    (6, None, 271.5, "Sen Usain Bolt değilsin.", WHITE),
    (6, 271.5, None, "Ve terlikle koşuyorsun.", WHITE),
    (7, None, None, "Bir veloziraptor!", YEL),
    (8, None, None, "Gerçek veloziraptor hindi büyüklüğündeydi ve tüylüydü.", WHITE),
    (9, None, None, "Sen ondan da korktun.", WHITE),
    (10, None, 393.4, "Ama dur, bir sorun daha var.", WHITE),
    (10, 393.4, 395.6, "Hem de en büyüğü.", YEL),
]
ovs = [(layer("top", top), 0, TOTAL + 1)]
for k, (i, a, b, txt, col) in enumerate(CAPS):
    t0 = om(i, a) if a else outs[i]
    t1 = om(i, b) if b else outs[i] + cuts[i][1] - cuts[i][0]
    ovs.append((layer(f"c{k:02d}", cap(txt, col)), t0, t1))
ovs.append((layer("cta", cta), om(10, 395.6), TOTAL + 1))

# ffmpeg grafiği
args = ["ffmpeg", "-y", "-loglevel", "error"]
for s, e, v in cuts:
    vs = v if v else s
    args += ["-ss", f"{vs:.3f}", "-t", f"{e - s:.3f}", "-i", SRC]
for s, e, v in cuts:
    if v:
        args += ["-ss", f"{s:.3f}", "-t", f"{e - s:.3f}", "-i", SRC]
n = len(cuts); aud_extra = {i: n + j for j, i in enumerate([i for i, c in enumerate(cuts) if c[2]])}
for p, _, _ in ovs:
    args += ["-i", str(p)]
fc = []
for i, (s, e, v) in enumerate(cuts):
    d = e - s
    fc.append(f"[{i}:v]trim=0:{d:.3f},setpts=PTS-STARTPTS,fps=30,format=yuv420p[v{i}]")
    ai = aud_extra.get(i, i)
    fc.append(f"[{ai}:a]atrim=0:{d:.3f},asetpts=PTS-STARTPTS,aresample=48000,afade=t=in:d=0.015,"
              f"afade=t=out:st={d - 0.03:.3f}:d=0.03[a{i}]")
fc.append("".join(f"[v{i}][a{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=1[cv][ca]")
fc.append("[cv]split[b0][f0]")
fc.append("[b0]scale=-2:640,crop=360:640,boxblur=18:2,eq=brightness=-0.22:saturation=1.1,scale=1440:2560[bg]")
fc.append(f"[f0]scale=-2:{FG_H}:flags=lanczos,crop=1440:{FG_H}[fg]")
fc.append(f"[bg][fg]overlay=0:{FG_Y}[x0]")
base = n + len(aud_extra)
last = "x0"
for k, (p, t0, t1) in enumerate(ovs):
    fc.append(f"[{last}][{base + k}:v]overlay=0:0:enable='between(t,{t0:.3f},{t1:.3f})'[x{k + 1}]")
    last = f"x{k + 1}"
fc.append("[ca]loudnorm=I=-14:TP=-1.5:LRA=11[ao]")
mode = sys.argv[2] if len(sys.argv) > 2 else "render"
out = Z / "teaser.mp4"
args += ["-filter_complex", ";".join(fc), "-map", f"[{last}]", "-map", "[ao]",
         "-c:v", "libx264", "-preset", "veryfast", "-b:v", "5200k", "-maxrate", "7000k", "-bufsize", "14000k",
         "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", str(out)]
print("toplam", round(TOTAL, 2), "parça çıkış:", [round(x, 2) for x in outs])
if mode == "render":
    subprocess.run(args, check=True); print("render bitti", out)
