"""4. video: Arabada cam buğusunu bir dakikada açmanın yolu."""
import json, math, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from engine import *  # noqa
from widgets import *  # noqa
import audio_tools as at
import video_bg as vb

WORK = Path(sys.argv[1])
M = Path("/home/claude/pratik-abi/media/v4-cam-bugusu")
words = json.loads((WORK / "words.json").read_text(encoding="utf-8"))
TOTAL = at.duration(str(WORK / "voice_cut.wav"))
INTRO = 0.0
OUTRO = 1.9


def T(key, nth=0):
    hits = [w for w in words if trl(clean(w["w"])).strip("!?") == trl(clean(key))]
    return hits[nth]["s"]


S1, S2, S3, S4, S5 = T("bir", 1) - 0.2, T("iki") - 0.2, T("üç") - 0.2, T("dört") - 0.2, T("bir", 3) - 0.2
C_ELLE = T("çoğu") - 0.1
C_YOL = T("camı") - 0.1
C_NEM = T("klima", 1) - 0.1
C_TAZE = T("dışarıdan") - 0.1
C_SICAK = T("sıcak") - 0.1
C_HAFTA = T("haftada") - 0.1
C_SON = T("senin") - 0.15

N = Path("/home/claude/pratik-abi/media/v4b-4k")
SEGS = [
    dict(src=str(N / "kis-sabah_1.mp4"), kind="video", ss=1, dur=C_ELLE, pan=(0, -1)),
    dict(src=str(N / "on-cam_3.mp4"), kind="video", ss=2, dur=C_YOL - C_ELLE, pan=(0, 0)),
    dict(src=str(N / "bugu-dikey_1.mp4"), kind="video", ss=0.5, dur=S1 - C_YOL, pan=(0, 0)),
    dict(src=str(N / "konsol-panel_1.mp4"), kind="video", ss=3, dur=C_NEM - S1, pan=(0, 0)),
    dict(src=str(N / "silme_3.mp4"), kind="video", ss=4, dur=S2 - C_NEM, pan=(0, 1)),
    dict(src=str(N / "araba-ic-gece_1.mp4"), kind="video", ss=0, dur=C_TAZE - S2, pan=(1, 0)),
    dict(src=str(N / "karli-yol_1.mp4"), kind="video", ss=3, dur=S3 - C_TAZE, pan=(0, 0)),
    dict(src=str(N / "on-cam_2.mp4"), kind="video", ss=2, dur=C_SICAK - S3, pan=(0, 0)),
    dict(src=str(N / "on-cam_1.mp4"), kind="video", ss=2, dur=S4 - C_SICAK, pan=(0, 0)),
    dict(src=str(N / "silme_4.mp4"), kind="video", ss=5, dur=C_HAFTA - S4, pan=(0, 0)),
    dict(src=str(N / "on-cam_4.mp4"), kind="video", ss=2, dur=S5 - C_HAFTA, pan=(0, -1)),
    dict(src=str(N / "gece-trafik_1.mp4"), kind="video", ss=1, dur=C_SON - S5, pan=(0, 0)),
    dict(src=str(N / "karli-orman_1.mp4"), kind="video", ss=2, dur=TOTAL - OUTRO - C_SON, pan=(0, 1)),
    dict(src=str(WORK / "outro.mp4"), kind="video", dur=OUTRO, zoom=0.06, pan=(0, 0)),
]

FOG = None


def fog_layer():
    global FOG
    if FOG is None:
        rng = np.random.default_rng(7)
        n = rng.random((H // 8, W // 8))
        a = (150 + 90 * n).astype(np.uint8)
        arr = np.zeros((H // 8, W // 8, 4), np.uint8)
        arr[..., 0] = arr[..., 1] = arr[..., 2] = 235
        arr[..., 3] = a
        FOG = Image.fromarray(arr, "RGBA").resize((W, H), Image.BICUBIC).filter(ImageFilter.GaussianBlur(18))
    return FOG


# ---------- 0: kanca ----------
def s_hook(v, sc, L, t, dur):
    te, tk, tc = v.wt(sc, "eliyle"), v.wt(sc, "kötüleştirir"), v.wt(sc, "camı")
    if t < C_YOL - 0.1:
        headline(L, [("Cam", False), ("bembeyaz", True), ("mı oldu?", False)], t, y0=250, start=-1)
    else:
        headline(L, [("1 dakikada", True), ("açmanın yolu", False)], t, y0=250, start=C_YOL - 0.05)
    q = ph(t, te, 0.4)
    if q > 0 and t < C_YOL:
        put_icon(L, "raised_hand", 540, 820 + 20 * math.sin(t * 9), 300 * eb(q), rot=10 * math.sin(t * 9))
        stamp(L, 540, 1040, "ELLE SİLME!", RED, t, tk - 0.3, rot=-8, size=72)
    q = ph(t, tc + 0.3, 0.45)
    if q > 0:
        put_icon(L, "stopwatch", 540, 820, 260 * eb(q), rot=-6 + 4 * math.sin(t * 3))


# ---------- 1: klima ----------
def s_ac(v, sc, L, t, dur):
    headline(L, [("1.", True), ("Klimayı aç", False)], t, y0=250)
    ta, tev, tn = v.wt(sc, "klimayı"), v.wt(sc, "evet"), v.wt(sc, "nemi")
    p = eo(ph(t, 0.2, 0.45))
    on = eio(ph(t, ta + 0.4, 0.3))
    cx, cy, r = 540, 760 + (1 - p) * 60, 190
    d = ImageDraw.Draw(L)
    glow = 0.5 + 0.5 * math.sin(t * 4)
    if on > 0:
        g = Image.new("RGBA", (600, 600), (0, 0, 0, 0))
        ImageDraw.Draw(g).ellipse([60, 60, 540, 540], fill=(90, 180, 255, int(120 * on * (0.6 + 0.4 * glow))))
        comp(L, g.filter(ImageFilter.GaussianBlur(40)), cx - 300, cy - 300)
    col = tuple(int(lerp(a, b, on)) for a, b in zip((60, 64, 78), (40, 130, 255)))
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(24, 26, 36, int(255 * p)), outline=col + (int(255 * p),), width=14)
    text_c(L, (cx, cy - 20), "A/C", "black", 120, tuple(int(lerp(a, b, on)) for a, b in zip((150, 155, 170), WHITE)), alpha=p)
    put_icon(L, "snowflake", cx, cy + 95, 80 * p, alpha=on)
    chip(L, cx, cy + r + 70, "AÇIK" if on > 0.5 else "KAPALI", bg=GREEN if on > 0.5 else (90, 95, 110), fg=WHITE,
         size=40, k="black", alpha=p)
    q = ph(t, tev, 0.35)
    if q > 0 and t < tn:
        chip(L, 540, 470, "Evet, kışın da!", bg=ACC, fg=INK, size=44, k="black", scale=eb(q))
    if t >= tn - 0.2:  # damlalar klimaya çekilir
        for k in range(6):
            st = tn - 0.2 + k * 0.18
            u = ph(t, st, 0.9)
            if u <= 0 or u >= 1:
                continue
            ang = k * 1.05 + 0.4
            sx, sy = cx + 430 * math.cos(ang), cy + 380 * math.sin(ang)
            x, y = lerp(sx, cx, eio(u)), lerp(sy, cy, eio(u))
            put_icon(L, "droplet", x, y, lerp(110, 30, eio(u)), alpha=1 - ph(u, 0.8, 0.2))
        chip(L, 540, 470, "Nemi çeker", bg=WHITE, fg=INK, size=44, icon_name="droplet", k="black",
             scale=eb(ph(t, tn, 0.35)))


# ---------- 2: iç hava modu ----------
def mode_icon(L, cx, cy, s, recirc, alpha):
    d = ImageDraw.Draw(L)
    a = int(255 * alpha)
    w, h = s * 1.2, s * 0.5
    d.rounded_rectangle([cx - w / 2, cy - h / 2 + s * 0.15, cx + w / 2, cy + h / 2 + s * 0.15], radius=int(s * 0.12),
                        outline=(255, 255, 255, a), width=max(4, int(s * 0.06)))
    d.line([cx - w * 0.3, cy - h / 2 + s * 0.15, cx - w * 0.15, cy - h * 0.9 + s * 0.15, cx + w * 0.2,
            cy - h * 0.9 + s * 0.15, cx + w * 0.35, cy - h / 2 + s * 0.15], fill=(255, 255, 255, a), width=max(4, int(s * 0.06)))
    if recirc:
        bb = [cx - s * 0.3, cy - s * 0.05, cx + s * 0.3, cy + s * 0.45]
        d.arc(bb, 200, 520, fill=ACC + (a,), width=max(4, int(s * 0.07)))
    else:
        for k in range(3):
            y = cy + s * (0.02 + k * 0.14)
            d.line([cx - s * 1.0, y, cx - s * 0.35, y], fill=ACC + (a,), width=max(4, int(s * 0.06)))


def s_recirc(v, sc, L, t, dur):
    headline(L, [("2.", True), ("İç havayı kapat", False)], t, y0=250)
    tk, tnem, td = v.wt(sc, "kapat"), v.wt(sc, "nemli"), v.wt(sc, "dışarıdan")
    p = eo(ph(t, 0.2, 0.45))
    if p <= 0:
        return
    y0 = 540 + (1 - p) * 60
    glass(L, 110, y0, 860, 500, alpha=p)
    sw = eio(ph(t, tk, 0.35))
    rows = [("İç hava (döngü)", True, RED, 1 - sw), ("Dış hava (taze)", False, GREEN, sw)]
    for i, (name, rec, col, on) in enumerate(rows):
        ry = y0 + 70 + i * 220
        mode_icon(L, 240, ry + 80, 120, rec, p)
        text_c(L, (360, ry + 70), name, "xb", 44, WHITE, anchor="lm", alpha=p)
        toggle(L, 800, ry + 45, on, col)
    q = ph(t, tnem, 0.4)
    if q > 0 and t < td:
        ang = t * 3
        for k in range(4):
            a = ang + k * math.pi / 2
            put_icon(L, "droplet", 240 + 100 * math.cos(a), y0 + 150 + 60 * math.sin(a), 60 * eb(q))
        chip(L, 540, y0 + 560, "Nemli hava içeride döner", bg=RED, fg=WHITE, size=38, icon_name="droplet", scale=eb(q))
    q = ph(t, td, 0.4)
    if q > 0:
        for k in range(3):
            u = ((t - td) * 0.9 + k / 3) % 1
            put_icon(L, "leaf_fluttering_in_wind", lerp(60, 240, u), y0 + 300 + 20 * math.sin(u * 6 + k), 70 * eb(q),
                     alpha=1 - abs(u - 0.5) * 1.6)
        chip(L, 540, y0 + 560, "Taze hava al", bg=GREEN, fg=WHITE, size=40, icon_name="check_mark_button", k="black",
             scale=eb(q))


# ---------- 3: cama üfle + ısı ----------
def s_heat_bg(v, sc, im, t, dur):
    ts, ta = v.wt(sc, "sıcak"), v.wt(sc, "açar")
    a = 0.75 * (1 - eio(ph(t, ts + 0.2, max(0.6, ta - ts + 0.4))))
    if a > 0.01:
        im.alpha_composite(set_alpha(fog_layer(), a))


def s_heat(v, sc, L, t, dur):
    headline(L, [("3.", True), ("Cama üfle, ısıyı aç", False)], t, y0=250)
    tc, ti = v.wt(sc, "cama"), v.wt(sc, "ısıyı")
    p = eo(ph(t, 0.2, 0.45))
    if p <= 0:
        return
    # ön cam üfleme simgesi
    q = ph(t, tc, 0.4)
    if q > 0:
        glass(L, 150, 470, 340, 300, alpha=eo(q))
        d = ImageDraw.Draw(L)
        d.polygon([(205, 640), (435, 640), (405, 540), (235, 540)], outline=(255, 255, 255, 255), width=8)
        for k in range(3):
            x = 260 + k * 60
            u = ((t - tc) * 1.2 + k * 0.3) % 1
            y = lerp(730, 650, u)
            d.line([x, y + 40, x, y], fill=ACC + (int(255 * (1 - u)),), width=8)
            d.polygon([(x - 14, y + 4), (x + 14, y + 4), (x, y - 16)], fill=ACC + (int(255 * (1 - u)),))
        text_c(L, (320, 730), "Cama", "black", 40, WHITE, alpha=eo(q))
    # ısı düğmesi
    q2 = ph(t, ti, 0.4)
    if q2 > 0:
        glass(L, 590, 470, 340, 300, alpha=eo(q2))
        cx, cy, r = 760, 610, 100
        d = ImageDraw.Draw(L)
        for k in range(30):
            a0 = math.radians(140 + k * 9)
            col = tuple(int(lerp(a, b, k / 29)) for a, b in zip((60, 140, 255), (255, 70, 60)))
            d.arc([cx - r, cy - r, cx + r, cy + r], math.degrees(a0), math.degrees(a0) + 8, fill=col + (255,), width=18)
        ang = math.radians(lerp(160, 400, eio(ph(t, ti + 0.2, 0.9))))
        d.line([cx, cy, cx + (r - 30) * math.cos(ang), cy + (r - 30) * math.sin(ang)], fill=WHITE + (255,), width=10)
        d.ellipse([cx - 16, cy - 16, cx + 16, cy + 16], fill=WHITE + (255,))
        text_c(L, (760, 730), "Isı: MAX", "black", 40, ACC, alpha=eo(q2))
    ts = v.wt(sc, "açar")
    chip(L, 540, 860, "Sıcak + kuru hava = net cam", bg=GREEN, fg=WHITE, size=40, icon_name="check_mark_button",
         k="black", scale=eb(ph(t, ts, 0.4)))


# ---------- 4: temiz cam ----------
def s_clean(v, sc, L, t, dur):
    headline(L, [("4.", True), ("Camın içini temizle", False)], t, y0=250)
    tk, th = v.wt(sc, "kirli"), v.wt(sc, "haftada")
    q = ph(t, tk, 0.45)
    if q > 0:
        glass(L, 140, 520 + (1 - eo(q)) * 60, 800, 260, alpha=eo(q))
        put_icon(L, "fog", 280, 650 + (1 - eo(q)) * 60, 150 * eb(q))
        text_c(L, (400, 610 + (1 - eo(q)) * 60), "Kirli cam", "black", 54, WHITE, anchor="lm", alpha=eo(q))
        text_c(L, (400, 690 + (1 - eo(q)) * 60), "buğuyu daha çabuk tutar", "b", 38, (220, 225, 235), anchor="lm",
               alpha=eo(q))
    q2 = ph(t, th, 0.45)
    if q2 > 0:
        put_icon(L, "sponge", 400, 920 + 10 * math.sin(t * 5), 190 * eb(q2), rot=15 * math.sin(t * 6))
        put_icon(L, "sparkles", 680, 900, 170 * eb(ph(t, th + 0.3, 0.4)))
        chip(L, 540, 1080, "Haftada 1 kez sil", bg=ACC, fg=INK, size=44, k="black", scale=eb(ph(t, th + 0.15, 0.4)))


# ---------- 5: bonus + kapanış ----------
def s_end(v, sc, L, t, dur):
    son = C_SON - sc["start"]
    if t < son:
        headline(L, [("Bonus:", True), ("camı biraz arala", False)], t, y0=250)
        ta = v.wt(sc, "arala")
        q = ph(t, ta - 0.3, 0.45)
        if q > 0:
            glass(L, 240, 560, 600, 420, alpha=eo(q))
            d = ImageDraw.Draw(L)
            gap = 40 * eio(ph(t, ta, 0.6))
            d.rounded_rectangle([320, 640 + gap, 760, 900], radius=26, fill=(120, 170, 220, 200), outline=WHITE + (255,), width=6)
            d.rounded_rectangle([300, 620, 780, 640 + gap], radius=8, fill=(14, 18, 32, 255))
            for k in range(3):
                u = ((t - ta) * 1.1 + k / 3) % 1
                put_icon(L, "droplet", 400 + k * 140, lerp(650, 520, u), 60, alpha=(1 - u) * clamp(gap / 30))
            chip(L, 540, 1030, "Nem dışarı çıksın", bg=WHITE, fg=INK, size=40, icon_name="wind_face", scale=eb(q))
    elif t < dur - OUTRO:
        headline(L, [("Yolun", False), ("açık olsun!", True)], t - son, y0=250)
        outro(v, sc, L, t)
    else:  # sonda Pratik Abi göz kırpar
        lt = t - (dur - OUTRO)
        chip(L, 540, 1560, "Takip et, kaçırma!", bg=RED, fg=WHITE, size=50, icon_name="bell", k="black",
             scale=eb(ph(lt, 0.25, 0.4)))


starts = [0.0, S1, S2, S3, S4, S5]
draws = [s_hook, s_ac, s_recirc, s_heat, s_clean, s_end]
scenes = [{"start": s, "end": (starts[i + 1] if i + 1 < len(starts) else TOTAL), "draw": d}
          for i, (s, d) in enumerate(zip(starts, draws))]
scenes[3]["bgdraw"] = s_heat_bg

if __name__ == "__main__":
    mode = sys.argv[2] if len(sys.argv) > 2 else "render"
    if not (WORK / "bg.mp4").exists() or mode == "bg":
        build_bg(SEGS, str(WORK / "bg.mp4"), M)
    bg = vb.VideoBackground(str(WORK / "bg.mp4"), SEGS)
    v = Video(scenes, words, "", TOTAL, bg=bg)
    if mode == "frames":
        for tt in [float(x) for x in sys.argv[3].split(",")]:
            v.frame(tt).save(WORK / f"fr_{tt:05.1f}.png")
    else:
        sfx = [(TOTAL - OUTRO, "whoosh"), (TOTAL - OUTRO + 0.15, "tink")] + [(s["start"], "whoosh") for s in scenes[1:]] + [(C_SON, "whoosh")]
        sfx += [(T("eliyle"), "pop"), (T("kötüleştirir") - 0.3, "pop"), (T("klimayı") + 0.4, "ding"), (T("evet"), "pop"),
                (T("kapat"), "pop"), (T("dışarıdan"), "ding"), (T("açar"), "ding"), (T("haftada"), "pop"),
                (T("senin"), "pop"), (T("beğenmeyi"), "pop")]
        at.music(str(WORK / "music.wav"), TOTAL, bpm=80)
        at.sfx(str(WORK / "sfx.wav"), TOTAL, sfx)
        at.final_mix(str(WORK / "voice_cut.wav"), str(WORK / "music.wav"), str(WORK / "sfx.wav"), str(WORK / "mix.m4a"))
        v.render(str(WORK / "mix.m4a"), str(WORK / "video.mp4"))
        compress(str(WORK / "video.mp4"), str(WORK / "final.mp4"))
        print("bitti", TOTAL)
