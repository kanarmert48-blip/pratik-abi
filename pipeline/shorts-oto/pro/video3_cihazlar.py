"""3. video: Evde fark etmeden para yakan 4 cihaz (gerçek görüntülü)."""
import json, math, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from engine import *  # noqa
import audio_tools as at
import video_bg as vb

WORK = Path(sys.argv[1])
M = Path("/home/claude/pratik-abi/media")
words = json.loads((WORK / "words.json").read_text(encoding="utf-8"))
TOTAL = at.duration(str(WORK / "voice_cut.wav"))


def T(key, nth=0):
    hits = [w for w in words if trl(clean(w["w"])) == trl(clean(key))]
    return hits[nth]["s"]


S1, S2, S3, S4, S5 = T("bir") - 0.2, T("iki") - 0.2, T("üç") - 0.2, T("dört") - 0.2, T("benim") - 0.2
CUT_GAME = T("enerji") - 0.15
CUT_SLEEP = T("kapat") + 0.3
CUT_METER = T("asıl") - 0.2


CUT_HOOK2 = T("o,") - 0.1
CUT_PAD = T("konsol", 0) - 0.1
CUT_KEY = T("bilgisayar", 1) - 0.1
CUT_SHELF = T("arkasında") - 0.1
INTRO = 1.5
SEGS = [
    dict(src=str(WORK / "intro.mp4"), kind="video", ss=0, dur=INTRO, pan=(0, 0), zoom=0.08),
    dict(src=str(M / "v3b-ek/sarj-priz-f_3.jpg"), kind="photo", dur=CUT_HOOK2 - INTRO, zoom=0.10, pan=(0, 0)),
    dict(src=str(M / "v3b-ek/sarj-priz-f_2.jpg"), kind="photo", dur=CUT_METER - CUT_HOOK2, zoom=0.08, pan=(0, 0)),
    dict(src=str(M / "v3b-ek/fatura-f_2.jpg"), kind="photo", dur=S1 - CUT_METER, zoom=0.08, pan=(0, 0)),
    dict(src=str(M / "v3-para-yakan-cihazlar/tv-gece_2.mp4"), kind="video", ss=0.3, dur=S2 - S1, pan=(0, 0)),
    dict(src=str(M / "v3c-modern/konsollar.jpg"), kind="photo", dur=S3 - S2, zoom=0.06, pan=(0, 0)),
    dict(src=str(M / "v3-para-yakan-cihazlar/bilgisayar_2.mp4"), kind="video", ss=0.5, dur=CUT_KEY - S3, pan=(-1, 0)),
    dict(src=str(M / "v3-para-yakan-cihazlar/bilgisayar_3.mp4"), kind="video", ss=10, dur=S4 - CUT_KEY, pan=(0, 0)),
    dict(src=str(M / "v3b-ek/buzdolabi-v_1.mp4"), kind="video", ss=1, dur=CUT_SHELF - S4, pan=(0, 1)),
    dict(src=str(M / "v3-para-yakan-cihazlar/buzdolabi_3.mp4"), kind="video", ss=0.3, dur=S5 - CUT_SHELF, pan=(0, 0)),
    dict(src=str(M / "v3b-ek/uzatma-anahtar-f_1.jpg"), kind="photo", dur=CUT_SLEEP - S5, zoom=0.07, pan=(0, 0),
         grade=",crop=iw*0.40:ih:iw*0.08:0"),
    dict(src=str(M / "v3b-ek/uyku-v_1.mp4"), kind="video", ss=0.5, dur=TOTAL - CUT_SLEEP, pan=(0, 0)),
]
TV_SEG = [s for s in SEGS if "tv-gece_2" in s["src"]][0]
for s in SEGS:  # ön kırpma, ölçeklemeden önce uygulanmalı
    if s.get("grade", "").startswith(",crop"):
        s["pre"] = s.pop("grade")[1:] + ","

LABEL = "PRATİK ABİ"
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


# ---------- 0: kanca ----------
def s_hook(v, sc, L, t, dur):
    ta, tasil = v.wt(sc, "ama"), v.wt(sc, "asıl")
    out = ph(t, tasil - 0.35, 0.3)
    if out < 1:
        a = 1 - out
        headline(L, [("Şarj aleti mi", False), ("para yakıyor?", True)], t, y0=250, start=INTRO - 0.05)
        chip(L, 540, 560, "Şüpheli: şarj aleti", bg=RED, fg=WHITE, size=38, icon_name="electric_plug",
             scale=eb(ph(t, INTRO + 0.25, 0.4)) * (1 - ph(t, ta, 0.25)), alpha=a)
        p = eo(ph(t, ta, 0.45)) * a
        if p > 0.01:
            glass(L, 130, 600 + (1 - p) * 60, 820, 330, alpha=p)
            put_icon(L, "electric_plug", 240, 765 + (1 - p) * 60, 150, alpha=p)
            text_c(L, (340, 680 + (1 - p) * 60), "Boşta bekleyen şarj aleti", "sb", 36, (220, 225, 235), anchor="lm", alpha=p)
            text_c(L, (340, 790 + (1 - p) * 60), "0,3 W'tan az", "black", 76, GREEN, anchor="lm", alpha=p)
            text_c(L, (340, 870 + (1 - p) * 60), "neredeyse hiç", "sb", 36, (220, 225, 235), anchor="lm", alpha=p)
            stamp(L, 800, 575, "SUÇSUZ", GREEN, t, v.wt(sc, "neredeyse"), rot=10, size=46)
    if t >= tasil - 0.35:
        headline(L, [("Asıl para yakan", False), ("4 cihaz", True)], t, y0=250, start=tasil - 0.35)
        items = [("television", "Uydu alıcısı"), ("video_game", "Oyun konsolu"),
                 ("desktop_computer", "Bilgisayar"), ("snowflake", "Buzdolabı")]
        for i, (ic, name) in enumerate(items):
            q = ph(t, tasil - 0.1 + i * 0.16, 0.45)
            if q <= 0:
                continue
            cx, cy = 300 + (i % 2) * 480, 690 + (i // 2) * 330
            glass(L, cx - 200, cy - 140, 400, 290, alpha=eo(q))
            put_icon(L, ic, cx, cy - 25 + 6 * math.sin(t * 3 + i), 150 * eb(q))
            text_c(L, (cx, cy + 100), name, "xb", 40, WHITE, alpha=eo(q))
            r = 34 * eb(q)
            ImageDraw.Draw(L).ellipse([cx - 170 - r, cy - 115 - r, cx - 170 + r, cy - 115 + r], fill=ACC + (255,))
            text_c(L, (cx - 170, cy - 113), str(i + 1), "black", int(44 * eb(q)) + 1, INK)


# ---------- 1: uydu alıcısı (TV ekranına çizim) ----------
TVB0, TVB1 = (646, 210, 1261, 555), (612, 175, 1295, 557)  # yeşil ekran kutusu, klip 0 s ve 9.8 s
SC = 2112 / 1080
OX = (1920 * SC - vb.BW) / 2
RECV = None


def tv_box(lt):
    ct = TV_SEG["ss"] + lt
    p = clamp(ct / 9.8)
    x0, y0, x1, y1 = [lerp(a, b, p) for a, b in zip(TVB0, TVB1)]
    ox, oy = (vb.BW - W) / 2, (vb.BH - H) / 2
    return (x0 * SC - OX - ox - 4, y0 * SC - oy - 4, x1 * SC - OX - ox + 4, y1 * SC - oy + 4)


def s_tv_bg(v, sc, im, t, dur):
    global RECV
    x0, y0, x1, y1 = tv_box(t)
    w, h = int(x1 - x0), int(y1 - y0)
    scr = Image.new("RGBA", (w, h), (8, 9, 14, 255))
    refl = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    rd = ImageDraw.Draw(refl)
    for k in range(0, h, 2):  # cam yansıması
        rd.line([(0, k), (w, k)], fill=(120, 140, 180, int(22 * (1 - k / h))), width=2)
    scr.alpha_composite(refl)
    d = ImageDraw.Draw(scr)
    tk, tu, t20 = v.wt(sc, "kumandayla"), v.wt(sc, "aslında"), v.wt(sc, "20")
    if t < tk:  # cihaz tanıtımı
        if RECV is None:
            RECV = Image.open(str(M / "v3c-modern/alici_kirp.jpg")).convert("RGBA")
            RECV.thumbnail((int(w * 0.92), int(h * 0.80)))
        p = eo(ph(t, 0.25, 0.4))
        scr.alpha_composite(Image.new("RGBA", (w, h), (245, 245, 245, int(255 * p))))
        comp(scr, set_alpha(RECV, p), (w - RECV.width) / 2, (h - RECV.height) / 2 + 20 * (1 - p))
    else:
        on = (math.sin(t * 5) > -0.3) if t < tu else True
        if on:
            d.ellipse([w - 70, h - 70, w - 40, h - 40], fill=(255, 40, 40, 255))
            glow = Image.new("RGBA", (120, 120), (0, 0, 0, 0))
            ImageDraw.Draw(glow).ellipse([30, 30, 90, 90], fill=(255, 40, 40, 120))
            comp(scr, glow.filter(ImageFilter.GaussianBlur(12)), w - 115, h - 115)
        if t < t20 - 0.2:
            text_c(scr, (w / 2, h / 2 - 30), "KAPALI", "black", 84, (90, 95, 110))
            q = ph(t, tu, 0.3)
            if q > 0:
                put_icon(scr, "eye", w / 2, h / 2 + 90, 130 * eb(q))
                d.line([w / 2 - 150, h / 2 - 30, w / 2 + 150, h / 2 - 30], fill=RED + (int(255 * q),), width=10)
        else:
            q = ph(t, t20 - 0.2, 1.1)
            val = int(round(20 * eo(q)))
            put_icon(scr, "high_voltage", w / 2 - 230, h / 2 - 20, 150 * eb(ph(t, t20 - 0.2, 0.4)))
            text_c(scr, (w / 2 + 60, h / 2 - 20), f"{val} W", "black", 170, ACC)
            text_c(scr, (w / 2 + 60, h / 2 + 110), "kapalıyken bile", "b", 42, (200, 205, 220))
    comp(im, scr, x0, y0)


def s_tv(v, sc, L, t, dur):
    x0, y0, x1, y1 = tv_box(t)
    headline(L, [("1.", True), ("Uydu alıcısı", False)], t, y0=y1 + 40, size=78)
    tc = v.wt(sc, "çekebiliyor") + 0.2
    q = ph(t, tc, 0.4)
    if q > 0:
        chip(L, 540, y1 + 210, "= 2 LED ampul gece gündüz yanıyor", bg=WHITE, fg=INK, size=36,
             icon_name="light_bulb", scale=eb(q))


# ---------- 2: oyun konsolu ----------
def toggle(L, x, y, on_p, col):
    d = ImageDraw.Draw(L)
    bgc = tuple(int(lerp(a, b, on_p)) for a, b in zip((90, 95, 110), col))
    d.rounded_rectangle([x, y, x + 120, y + 64], radius=32, fill=bgc + (255,))
    kx = lerp(x + 32, x + 88, eio(on_p))
    d.ellipse([kx - 26, y + 6, kx + 26, y + 58], fill=(255, 255, 255, 255))


def s_game(v, sc, L, t, dur):
    headline(L, [("2.", True), ("Oyun konsolu", False)], t, y0=250)
    ta, tg, te, tf = v.wt(sc, "anında"), v.wt(sc, "gece"), v.wt(sc, "enerji"), v.wt(sc, "fark")
    p = eo(ph(t, v.wt(sc, "anında") - 0.35, 0.45))
    if p <= 0:
        return
    y0 = 520 + (1 - p) * 60
    glass(L, 110, y0, 860, 470, alpha=p)
    text_c(L, (170, y0 + 70), "Güç modu", "black", 50, WHITE, anchor="lm", alpha=p)
    sw = eio(ph(t, te + 0.3, 0.35))
    rows = [("Anında açılma", "~10 W", RED, 1 - sw), ("Enerji tasarrufu", "1 W'tan az", GREEN, sw)]
    d = ImageDraw.Draw(L)
    for i, (name, watt, col, on) in enumerate(rows):
        ry = y0 + 150 + i * 150
        hl = ph(t, ta, 0.3) if i == 0 else ph(t, te, 0.3)
        if hl > 0 and on > 0.5:
            d.rounded_rectangle([140, ry - 20, 940, ry + 105], radius=24, fill=col + (int(45 * hl),),
                                outline=col + (int(200 * hl),), width=4)
        text_c(L, (175, ry + 25), name, "xb", 44, WHITE, anchor="lm", alpha=p)
        text_c(L, (175, ry + 75), watt, "b", 36, col, anchor="lm", alpha=p)
        toggle(L, 790, ry + 10, on, col)
    q = ph(t, tg, 0.4)
    if q > 0 and t < te + 0.2:
        put_icon(L, "crescent_moon", 900, y0 - 10, 150 * eb(q), rot=-15 + 5 * math.sin(t * 2))
    b = ph(t, tf, 0.6)
    if b > 0:
        by = y0 + 510
        glass(L, 110, by, 860, 230, alpha=eo(b))
        for i, (lab, val, col) in enumerate([("Anında açılma", 10, RED), ("Enerji tasarrufu", 1, GREEN)]):
            yy = by + 45 + i * 95
            text_c(L, (150, yy + 22), lab, "b", 32, WHITE, anchor="lm", alpha=eo(b))
            bw = 400 * (val / 10) * eo(ph(t, tf + 0.15 + i * 0.2, 0.6))
            d.rounded_rectangle([450, yy, 450 + max(bw, 14), yy + 46], radius=12, fill=col + (255,))
        chip(L, 540, 450, "10 kata kadar fark!", bg=ACC, fg=INK, size=42, icon_name="high_voltage", k="black",
             scale=eb(ph(t, v.wt(sc, "kata"), 0.4)))


# ---------- 3: bilgisayar ----------
def s_pc(v, sc, L, t, dur):
    headline(L, [("3.", True), ("Bilgisayar", False)], t, y0=250)
    td, tu = v.wt(sc, "değildir"), v.wt(sc, "uyku")
    p = eo(ph(t, 0.2, 0.45))
    if p <= 0:
        return
    mx, my, mw, mh = 140, 520 + (1 - p) * 60, 800, 470
    card(L, mx, my, mw, mh, r=28, fill=(30, 32, 40, 255), alpha=p)
    sx0, sy0, sx1, sy1 = mx + 24, my + 24, mx + mw - 24, my + mh - 24
    d = ImageDraw.Draw(L)
    sleep = ph(t, tu, 0.4)
    d.rectangle([sx0, sy0, sx1, sy1], fill=(6, 8, 14, int(255 * p)))
    d.rectangle([mx + mw / 2 - 60, my + mh, mx + mw / 2 + 60, my + mh + 50], fill=(60, 62, 72, int(255 * p)))
    d.rounded_rectangle([mx + mw / 2 - 170, my + mh + 45, mx + mw / 2 + 170, my + mh + 65], radius=8,
                        fill=(60, 62, 72, int(255 * p)))
    if sleep < 1:  # zıplayan ekran koruyucu
        a = (1 - sleep) * p
        bw_, bh_ = 330, 110
        rx, ry = (sx1 - sx0 - bw_), (sy1 - sy0 - bh_)
        px = abs(((t * 260) % (2 * rx)) - rx)
        py = abs(((t * 190) % (2 * ry)) - ry)
        hue = int(t * 1.3) % 4
        col = [(255, 212, 59), (46, 204, 140), (90, 160, 255), (255, 84, 89)][hue]
        d.rounded_rectangle([sx0 + px, sy0 + py, sx0 + px + bw_, sy0 + py + bh_], radius=20, fill=col + (int(255 * a),))
        text_c(L, (sx0 + px + bw_ / 2, sy0 + py + bh_ / 2), "Ekran koruyucu", "black", 36, INK, alpha=a)
        # işlemci çalışıyor göstergesi
        cy = my + mh + 110
        if t < tu:
            chip(L, 540, cy + 10, f"İşlemci çalışıyor  %{18 + int(6 * abs(math.sin(t * 7)))}", bg=RED, fg=WHITE,
                 size=36, icon_name="fire", scale=eb(ph(t, 1.0, 0.4)) * (1 - sleep))
    if sleep > 0:
        put_icon(L, "crescent_moon", 540 - 40, (sy0 + sy1) / 2, 170 * eb(sleep))
        put_icon(L, "zzz", 540 + 110, (sy0 + sy1) / 2 - 70 - 10 * math.sin(t * 3), 110 * eb(ph(t, tu + 0.2, 0.4)))
        chip(L, 540, my + mh + 120, "Uyku modu", bg=GREEN, fg=WHITE, size=44, icon_name="check_mark_button",
             k="black", scale=eb(ph(t, tu + 0.15, 0.4)))
    if td <= t < tu:
        stamp(L, 540, (sy0 + sy1) / 2, "TASARRUF DEĞİL", RED, t, td, rot=-10, size=64)


# ---------- 4: buzdolabı ----------
def s_fridge(v, sc, L, t, dur):
    headline(L, [("4.", True), ("Buzdolabı", False)], t, y0=250)
    tn, tm, ta = v.wt(sc, "nefes"), v.wt(sc, "motoru"), v.wt(sc, "arkasında")
    p = eo(ph(t, 0.2, 0.45))
    if p <= 0:
        return
    y0 = 500 + (1 - p) * 60
    glass(L, 110, y0, 860, 560, alpha=p)
    text_c(L, (540, y0 + 50), "Üstten görünüm", "sb", 32, (190, 195, 210), alpha=p)
    d = ImageDraw.Draw(L)
    wx = 190
    d.rectangle([wx, y0 + 100, wx + 34, y0 + 520], fill=(150, 150, 160, int(255 * p)))
    for k in range(0, 420, 28):
        d.line([wx, y0 + 100 + k + 28, wx + 34, y0 + 100 + k], fill=(110, 110, 120, int(255 * p)), width=3)
    text_c(L, (wx + 17, y0 + 560 - 20), "duvar", "sb", 28, (190, 195, 210), alpha=p)
    gap = 150 * eio(ph(t, ta + 0.1, 0.6))
    fx = wx + 34 + 4 + gap
    d.rounded_rectangle([fx, y0 + 140, fx + 380, y0 + 480], radius=28, fill=(235, 240, 248, int(255 * p)))
    d.rounded_rectangle([fx + 380 - 30, y0 + 160, fx + 380 - 12, y0 + 460], radius=8, fill=(180, 190, 205, int(255 * p)))
    put_icon(L, "snowflake", fx + 180, y0 + 310, 150, alpha=p)
    hot = ph(t, tn, 0.3) * (1 - ph(t, ta + 0.2, 0.4))
    if hot > 0:  # sıcak hava dalgaları
        for k in range(4):
            yy = y0 + 170 + k * 80
            pts = [(wx + 40 + 12 * math.sin(j * 0.6 + t * 8 + k), yy + j * 6) for j in range(10)]
            d.line(pts, fill=RED + (int(255 * hot),), width=6)
        put_icon(L, "hot_face", fx + 300, y0 + 150, 130 * eb(hot))
        chip(L, 540, y0 + 640, "Motor durmadan çalışır", bg=RED, fg=WHITE, size=38, icon_name="high_voltage",
             scale=eb(ph(t, tm, 0.4)) * hot)
    if gap > 20:
        ay = y0 + 310
        d.line([wx + 44, ay, fx - 10, ay], fill=ACC + (255,), width=8)
        d.polygon([(wx + 40, ay), (wx + 64, ay - 16), (wx + 64, ay + 16)], fill=ACC + (255,))
        d.polygon([(fx - 6, ay), (fx - 30, ay - 16), (fx - 30, ay + 16)], fill=ACC + (255,))
        text_c(L, ((wx + fx) / 2 + 20, ay - 50), "1 karış", "black", 40, ACC, alpha=clamp(gap / 120))
        q = ph(t, v.wt(sc, "boşluk"), 0.4)
        put_icon(L, "dashing_away", wx + 100, y0 + 450, 110 * eb(q))
        chip(L, 540, y0 + 640, "Hava alır, rahat çalışır", bg=GREEN, fg=WHITE, size=38,
             icon_name="check_mark_button", scale=eb(q))


# ---------- 5: kapanış ----------
SW = (420, 840)  # uzatmanın anahtarı (ekrandaki yaklaşık yer, önizlemeyle ayarlanır)


def s_cta(v, sc, L, t, dur):
    tk = CUT_SLEEP - sc["start"]
    tu, tcs, tan, ttek, tkap = (v.wt(sc, "uydu"), v.wt(sc, "konsolu"), v.wt(sc, "anahtarlı"), v.wt(sc, "tek"),
                                v.wt(sc, "kapat"))
    d = ImageDraw.Draw(L)
    if t < tk:
        headline(L, [("Tek tuşla", True), ("hepsini kapat", False)], t, y0=250)
        for k, (ic, name, st, x) in enumerate([("television", "Uydu alıcısı", tu, 330),
                                               ("video_game", "Konsol", tcs, 750)]):
            q = ph(t, st, 0.5)
            if q > 0:
                y = lerp(1500, 560, eo(q))
                put_icon(L, ic, x, y, 170 * (0.6 + 0.4 * eo(q)))
                chip(L, x, y + 120, name, bg=WHITE, fg=INK, size=34, scale=eb(ph(t, st + 0.3, 0.35)))
        q = ph(t, tan, 0.4)
        if q > 0 and t < tkap:
            rp = (t * 1.2) % 1
            r = 90 + rp * 70
            d.ellipse([SW[0] - r, SW[1] - r, SW[0] + r, SW[1] + r], outline=ACC + (int(220 * (1 - rp) * q),), width=8)
            chip(L, SW[0] + 250, SW[1] + 170, "Anahtarlı priz", bg=ACC, fg=INK, size=38, k="black", scale=eb(q))
        if t >= ttek:
            press = ph(t, ttek, 0.25)
            r = lerp(140, 70, eo(press))
            d.ellipse([SW[0] - r, SW[1] - r, SW[0] + r, SW[1] + r], outline=WHITE + (255,), width=10)
        if t >= tkap:
            q = ph(t, tkap, 0.2)
            L.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, int(200 * q))))
            chip(L, 540, 900, "0 W", bg=GREEN, fg=WHITE, size=90, k="black", scale=eb(q))
    else:
        lt = t - tk
        headline(L, [("Rahat uyu,", False), ("fatura da uyusun", True)], lt, y0=250)
        ts, tyo, tbe = v.wt(sc, "senin"), v.wt(sc, "yorumlarda"), v.wt(sc, "beğenmeyi")
        q = ph(t, ts - 0.1, 0.45)
        if q > 0:  # yorum çağrısı
            glass(L, 120, 560 + (1 - eo(q)) * 60, 840, 300, alpha=eo(q))
            put_icon(L, "speech_balloon", 250, 710 + (1 - eo(q)) * 60 + 6 * math.sin(t * 2.5), 170 * eb(q))
            text_c(L, (370, 670 + (1 - eo(q)) * 60), "Senin tavsiyen ne?", "black", 50, WHITE, anchor="lm", alpha=eo(q))
            text_c(L, (370, 745 + (1 - eo(q)) * 60), "Yorumlarda buluşalım", "b", 40, ACC, anchor="lm",
                   alpha=eo(ph(t, tyo, 0.3)))
        q2 = ph(t, tbe - 0.1, 0.45)
        if q2 > 0:  # beğen + takip
            put_icon(L, "thumbs_up", 360, 1000 + 8 * math.sin(t * 2.4), 190 * eb(q2), rot=-8)
            chip(L, 360, 1130, "Beğen", bg=ACC, fg=INK, size=42, k="black", scale=eb(ph(t, tbe + 0.1, 0.4)))
            tb = tbe + 0.45
            put_icon(L, "bell", 720, 1000 + 8 * math.sin(t * 2.4 + 1), 190 * eb(ph(t, tb, 0.45)),
                     rot=14 * math.sin(t * 9) * (1 - ph(t, tb + 1.0, 0.8)))
            chip(L, 720, 1130, "Takip et", bg=RED, fg=WHITE, size=42, k="black", scale=eb(ph(t, tb + 0.15, 0.4)))


starts = [0.0, S1, S2, S3, S4, S5]
draws = [s_hook, s_tv, s_game, s_pc, s_fridge, s_cta]
scenes = [{"start": s, "end": (starts[i + 1] if i + 1 < len(starts) else TOTAL), "draw": d}
          for i, (s, d) in enumerate(zip(starts, draws))]
scenes[1]["bgdraw"] = s_tv_bg


def build_bg():
    segs = []
    for s in SEGS:
        s2 = dict(s)
        if s2.get("pre"):
            s2["grade"] = ""
        segs.append(s2)
    # ön kırpmayı ölçeklemeden önce uygula
    import subprocess, tempfile, os
    tmp = tempfile.mkdtemp()
    parts = []
    for i, s in enumerate(SEGS):
        p = os.path.join(tmp, f"s{i}.mp4")
        vf = (f"{s.get('pre', '')}scale={vb.BW}:{vb.BH}:force_original_aspect_ratio=increase,crop={vb.BW}:{vb.BH},"
              f"fps={FPS},eq=contrast=1.06:saturation=1.12:brightness=-0.03,setsar=1,format=yuv420p")
        if s["kind"] == "photo":
            inp = ["-loop", "1", "-t", f"{s['dur']:.3f}", "-i", s["src"]]
        else:
            inp = ["-stream_loop", "-1", "-ss", f"{s.get('ss', 0):.3f}", "-i", s["src"]]
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *inp, "-vf", vf, "-an", "-frames:v",
                        str(int(round(s["dur"] * FPS))), "-c:v", "libx264", "-preset", "veryfast", "-crf", "14", p],
                       check=True)
        parts.append(p)
    lst = os.path.join(tmp, "l.txt")
    Path(lst).write_text("".join(f"file '{p}'\n" for p in parts))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy",
                    str(WORK / "bg.mp4")], check=True)


if __name__ == "__main__":
    mode = sys.argv[2] if len(sys.argv) > 2 else "render"
    if not (WORK / "bg.mp4").exists() or mode == "bg":
        build_bg()
    bg = vb.VideoBackground(str(WORK / "bg.mp4"), SEGS, grain_from=Background(seed=5))
    v = Video(scenes, words, LABEL, TOTAL, bg=bg)
    if mode == "frames":
        for tt in [float(x) for x in sys.argv[3].split(",")]:
            v.frame(tt).save(WORK / f"fr_{tt:05.1f}.png")
    else:
        sfx = [(s["start"], "whoosh") for s in scenes[1:]] + [(CUT_SLEEP, "whoosh")]
        sfx += [(0.12, "tink"), (INTRO, "whoosh")]
        sfx += [(T("asıl") - 0.1 + i * 0.16 + 0.35, "pop") for i in range(4)]
        sfx += [(T("neredeyse"), "pop"), (T("kata"), "ding"), (T("değildir"), "pop"), (T("uyku"), "ding"),
                (T("kapat"), "pop"), (T("senin"), "pop"), (T("beğenmeyi"), "pop"), (T("20") + 0.9, "ding")]
        at.music(str(WORK / "music.wav"), TOTAL, bpm=84)
        at.sfx(str(WORK / "sfx.wav"), TOTAL, sfx)
        at.final_mix(str(WORK / "voice_cut.wav"), str(WORK / "music.wav"), str(WORK / "sfx.wav"), str(WORK / "mix.m4a"))
        v.render(str(WORK / "mix.m4a"), str(WORK / "video3.mp4"))
        import subprocess
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(WORK / "video3.mp4"), "-c:v", "libx264",
                        "-preset", "faster", "-crf", "25", "-maxrate", "3.6M", "-bufsize", "7M", "-pix_fmt", "yuv420p",
                        "-c:a", "copy", "-movflags", "+faststart", str(WORK / "final.mp4")], check=True)
        print("bitti", TOTAL)
