"""2. video: Markette daha az harcamanın 4 yolu."""
import json, math, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from engine import *  # noqa
import audio_tools as at

WORK = Path(sys.argv[1])
words = json.loads((WORK / "words.json").read_text(encoding="utf-8"))
TOTAL = at.duration(str(WORK / "voice_cut.wav"))
SFX = []


def first(key):
    for w in words:
        if trl(clean(w["w"])).startswith(trl(key)):
            return w["s"]
    raise KeyError(key)


# ---------- SAHNE 0: kanca ----------
HOOK_ITEMS = [("bread", 480, 800), ("cheese_wedge", 400, 805), ("chocolate_bar", 565, 805), ("cup_with_straw", 640, 790),
              ("cookie", 430, 730), ("doughnut", 525, 725), ("candy", 615, 728), ("canned_food", 475, 662),
              ("honey_pot", 570, 660)]


def hook_times(v, sc):
    t0 = v.wt(sc, "ekmek")
    t1 = v.wt(sc, "iki")
    return [t0] + [t1 + 0.16 * i for i in range(1, len(HOOK_ITEMS))]


def s_hook(v, sc, L, t, dur):
    headline(L, [("Ekmek almaya girdin,", False), ("2 poşetle", True), ("mi çıktın?", False)], t)
    times = hook_times(v, sc)
    landed = 0
    for (name, x, y), ti in zip(HOOK_ITEMS, times):
        p = ph(t, ti, 0.5)
        if p <= 0:
            continue
        landed += p >= 1
        yy = lerp(y - 520, y, bounce(p))
        put_icon(L, name, x, yy, 118, alpha=eo(p * 3), rot=(1 - p) * 25)
    cp = eb(ph(t, 0.05, 0.5))
    bob = 6 * math.sin(t * 2.2)
    put_icon(L, "shopping_cart", 540, 900 + bob, 420 * cp)
    tp = v.wt(sc, "ekmek")
    chip(L, 290, 1170, "Plan: 1 ürün", bg=WHITE, fg=INK, size=40, icon_name="check_mark_button",
         scale=eb(ph(t, tp, 0.35)), alpha=eo(ph(t, tp, 0.2)))
    ts = v.wt(sc, "iki")
    chip(L, 790, 1170, f"Sepet: {max(landed, 1)} ürün", bg=RED, fg=WHITE, size=40, icon_name="shopping_bags",
         scale=eb(ph(t, ts, 0.35)) * (1 + 0.06 * max(0, 1 - ph(t, times[min(landed, 8)], 0.15))), alpha=eo(ph(t, ts, 0.2)))
    tm = v.wt(sc, "merak")
    p = ph(t, tm, 0.45)
    if p > 0:
        put_icon(L, "grinning_face_with_sweat", 835, 650, 160 * eb(p), rot=8 * math.sin(t * 6) * (1 - ph(t, tm + 1.2, 0.6)))


# ---------- SAHNE 1: liste ----------
LIST = [("bread", "Ekmek"), ("glass_of_milk", "Süt"), ("egg", "Yumurta"), ("tomato", "Domates")]


def s_list(v, sc, L, t, dur):
    headline(L, [("1.", True), ("Listesiz", True), ("gitme", False)], t)
    p = eo(ph(t, 0.1, 0.5))
    y0 = 520 + (1 - p) * 80
    card(L, 250, y0, 580, 590, r=34, fill=(253, 252, 246, 255), alpha=p)
    if p > 0.05:
        text_c(L, (300, y0 + 66), "Alışveriş Listesi", "black", 48, INK, anchor="lm", alpha=p)
        ImageDraw.Draw(L).rounded_rectangle([300, y0 + 108, 520, y0 + 116], radius=4, fill=RED + (int(255 * p),))
        d = ImageDraw.Draw(L)
        for i, (ic, name) in enumerate(LIST):
            yy = y0 + 190 + i * 100
            put_icon(L, ic, 335, yy, 74, alpha=p, shadow=False)
            text_c(L, (395, yy), name, "b", 50, INK, anchor="lm", alpha=p)
            d.rounded_rectangle([724, yy - 30, 784, yy + 30], radius=14, outline=(190, 192, 200, int(255 * p)), width=5)
            tk = 0.9 + i * 0.42
            q = ph(t, tk, 0.3)
            if q > 0:
                put_icon(L, "check_mark_button", 754, yy, 78 * eb(q), shadow=False)
                tw = d.textlength(name, font=font("b", 50))
                d.line([395, yy + 3, 395 + tw * eo(q), yy + 3], fill=(120, 124, 135, 200), width=5)
    put_icon(L, "memo", 830, 545 + 8 * math.sin(t * 2), 180 * eb(ph(t, 0.35, 0.45)), rot=12)
    tc = v.wt(sc, "pahalı") - 0.2
    chip(L, 540, 1205, "Listede yoksa, sepete girmez", bg=GREEN, fg=WHITE, size=40, icon_name="light_bulb",
         scale=eb(ph(t, tc, 0.4)), alpha=eo(ph(t, tc, 0.2)))


# ---------- SAHNE 2: aç karnına ----------
FOODS = ["hamburger", "pizza", "doughnut", "cookie", "chocolate_bar", "candy"]


def s_hungry(v, sc, L, t, dur):
    headline(L, [("2.", True), ("Aç karnına", True), ("gitme", False)], t)
    ta = v.wt(sc, "acıkınca")
    cart_p = eb(ph(t, ta - 0.25, 0.45))
    face_s = eb(ph(t, 0.15, 0.5)) * (1 + 0.04 * math.sin(t * 4))
    put_icon(L, "face_savoring_food", 540, 800, 280 * face_s)
    if cart_p > 0:
        put_icon(L, "shopping_cart", 540, 1095, 230 * cart_p)
    for j, fd in enumerate(FOODS):
        appear = eb(ph(t, 0.35 + j * 0.12, 0.4))
        tf = ta + 0.35 + j * 0.14
        ang = lambda tt: j * (2 * math.pi / len(FOODS)) + min(tt, tf) * 0.7
        ox, oy = 540 + 300 * math.cos(ang(t)), 800 + 235 * math.sin(ang(t))
        q = ph(t, tf, 0.45)
        if q >= 1:
            continue
        if q > 0:
            sx, sy = 540 + 300 * math.cos(ang(tf)), 800 + 235 * math.sin(ang(tf))
            ex, ey = 540, 1060
            cx, cy = (sx + ex) / 2 + 60, min(sy, ey) - 160
            e = eio(q)
            x = (1 - e) ** 2 * sx + 2 * (1 - e) * e * cx + e * e * ex
            y = (1 - e) ** 2 * sy + 2 * (1 - e) * e * cy + e * e * ey
            put_icon(L, fd, x, y, lerp(125, 70, e), alpha=1 - ph(q, 0.75, 0.25), rot=q * 200)
        else:
            put_icon(L, fd, ox, oy, 125 * appear, rot=10 * math.sin(t * 3 + j))
    tc = v.wt(sc, "girer") + 0.25
    chip(L, 540, 560, "Önce ye, sonra alışverişe çık", bg=GREEN, fg=WHITE, size=40, icon_name="check_mark_button",
         scale=eb(ph(t, tc, 0.4)), alpha=eo(ph(t, tc, 0.2)))


# ---------- SAHNE 3: raflar ----------
SHELF = {700: [38, 29, 85], 905: [52, 41, 119], 1110: [35, 27, 79]}
PRODUCTS = ["canned_food", "glass_of_milk", "honey_pot"]


def s_shelf(v, sc, L, t, dur):
    headline(L, [("3.", True), ("Alt ve üst", True), ("raflara bak", False)], t)
    p = eo(ph(t, 0.1, 0.45))
    if p <= 0:
        return
    d = ImageDraw.Draw(L)
    a = int(255 * p)
    card(L, 160, 540, 760, 640, r=30, fill=(255, 255, 255, 22), outline=(255, 255, 255, 50), width=3, shadow=False, alpha=p)
    tg = v.wt(sc, "göz")
    glow = ph(t, tg, 0.35)
    if glow > 0:
        pulse = 0.75 + 0.25 * math.sin(t * 6)
        d.rounded_rectangle([175, 905 - 160, 905, 905 + 85], radius=22, fill=RED + (int(70 * glow * pulse),),
                            outline=RED + (int(220 * glow),), width=5)
    for x in (172, 886):
        d.rounded_rectangle([x, 560, x + 22, 1170], radius=8, fill=(120, 86, 60, a))
    states = {700: v.wt(sc, "üstüne"), 905: tg, 1110: v.wt(sc, "altına")}
    for ri, (by, prices) in enumerate(SHELF.items()):
        d.rounded_rectangle([172, by, 908, by + 24], radius=6, fill=(196, 140, 92, a))
        d.rectangle([172, by + 16, 908, by + 24], fill=(150, 104, 66, a))
        for ci, (prod, pr) in enumerate(zip(PRODUCTS, prices)):
            x = 330 + ci * 210
            q = eb(ph(t, 0.4 + ri * 0.15 + ci * 0.06, 0.4))
            put_icon(L, prod, x, by - 64, 124 * q)
            st = ph(t, states[by], 0.3)
            bad = by == 905
            base, hl = (255, 255, 255), (RED if bad else GREEN)
            col = tuple(int(lerp(base[i], hl[i], st)) for i in range(3))
            fg = tuple(int(lerp(INK[i], 255, st)) for i in range(3))
            if q > 0.05:
                s = 1 + 0.12 * math.sin(math.pi * clamp(st * 1.0))
                tw, th = 140 * s, 56 * s
                d.rounded_rectangle([x - tw / 2, by + 34, x + tw / 2, by + 34 + th], radius=12, fill=col + (a,))
                text_c(L, (x, by + 34 + th / 2), f"₺{pr}", "black", int(36 * s), fg, alpha=p)
    if glow > 0:
        put_icon(L, "eye", 105, 825, 130 * eb(glow), rot=5 * math.sin(t * 3))
    chip(L, 540, 470, "Göz hizası = en pahalı raf", bg=RED, fg=WHITE, size=40, icon_name="warning",
         scale=eb(ph(t, tg + 0.2, 0.4)), alpha=eo(ph(t, tg + 0.2, 0.2)))


# ---------- SAHNE 4: birim fiyat ----------
CARDS = [(80, "package", 210, "Büyük paket", "1 kg", "₺120", "₺120 / kg"),
         (580, "package", 150, "Küçük paket", "500 g", "₺55", "₺110 / kg")]


def s_unit(v, sc, L, t, dur):
    headline(L, [("4.", True), ("Birim fiyata", True), ("bak", False)], t)
    to = v.wt(sc, "önemlisi")
    chip(L, 540, 470, "EN ÖNEMLİSİ", bg=ACC, fg=INK, size=38, icon_name="sparkles", k="black",
         scale=eb(ph(t, to, 0.4)) * (1 + 0.04 * math.sin(t * 5)), alpha=eo(ph(t, to, 0.2)))
    te, tk, tb, tu = v.wt(sc, "etiketin"), v.wt(sc, "kilo"), v.wt(sc, "büyük"), v.wt(sc, "ucuz")
    d = ImageDraw.Draw(L)
    for i, (x0, ic, isz, name, wt_, price, unit) in enumerate(CARDS):
        p = eo(ph(t, 0.25 + i * 0.15, 0.5))
        if p <= 0:
            continue
        y0 = 560 + (1 - p) * 90
        win, lose = i == 1, i == 0
        vp = ph(t, tu if win else tb, 0.35)
        outline = GREEN + (255,) if (win and vp > 0) else None
        card(L, x0, y0, 420, 520, r=36, fill=(255, 255, 255, 255), outline=outline, width=int(10 * vp), alpha=p)
        put_icon(L, ic, x0 + 210, y0 + 120, isz * (1 + 0.03 * math.sin(t * 2 + i)), alpha=p)
        text_c(L, (x0 + 210, y0 + 235), name, "xb", 42, INK, alpha=p)
        text_c(L, (x0 + 210, y0 + 282), wt_, "sb", 34, (110, 115, 130), alpha=p)
        text_c(L, (x0 + 210, y0 + 365), price, "black", 92, INK, alpha=p)
        focus = ph(t, te + 0.4, 0.3) if i == 0 else ph(t, tk + 0.3, 0.3)
        sx = 1 + 0.14 * focus
        bw, bh = 370 * sx, 76 * sx
        bx, by = x0 + 210, y0 + 462
        col = tuple(int(lerp(a_, b_, focus)) for a_, b_ in zip((238, 240, 246), ACC))
        d.rounded_rectangle([bx - bw / 2, by - bh / 2, bx + bw / 2, by + bh / 2], radius=16, fill=col + (int(255 * p),))
        text_c(L, (bx, by), f"Birim: {unit}", "black", int(34 * sx), INK, alpha=p)
        if lose and vp > 0:
            ov = Image.new("RGBA", (420, 520), (0, 0, 0, 0))
            ImageDraw.Draw(ov).rounded_rectangle([0, 0, 419, 519], radius=36, fill=(20, 22, 35, int(120 * vp)))
            comp(L, ov, x0, y0)
            chip(L, x0 + 210, y0 + 590, "Pahalı", bg=RED, fg=WHITE, size=40, scale=eb(vp))
        if win and vp > 0:
            put_icon(L, "crown", x0 + 210, y0 - 20 - 8 * math.sin(t * 3), 140 * eb(vp), rot=-10)
            chip(L, x0 + 210, y0 + 590, "Daha ucuz!", bg=GREEN, fg=WHITE, size=40, icon_name="money_bag", scale=eb(vp))
    # büyüteç
    mp = ph(t, te, 0.5)
    if mp > 0 and t < tb + 0.4:
        m2 = ph(t, tk + 0.1, 0.5)
        x = lerp(lerp(1150, 430, eio(mp)), 930, eio(m2))
        y = lerp(lerp(1300, 1120, eio(mp)), 1120, eio(m2))
        put_icon(L, "magnifying_glass_tilted_right", x, y, 210, alpha=1 - ph(t, tb, 0.35), rot=-8)


# ---------- SAHNE 5: kapanış ----------
def s_cta(v, sc, L, t, dur):
    headline(L, [("Bu hafta", False), ("tek bir şey", True), ("dene", False)], t)
    td, tf, ty = v.wt(sc, "dördüncü"), v.wt(sc, "farkı"), v.wt(sc, "faydalı")
    d = ImageDraw.Draw(L)
    a1 = eb(ph(t, 0.45, 0.45)) * (1 - eo(ph(t, tf - 0.25, 0.25)))
    if a1 > 0.01:
        for k in range(2):
            rp = ((t * 0.8 + k * 0.5) % 1.0)
            r = 140 + rp * 110
            d.ellipse([540 - r, 690 - r, 540 + r, 690 + r], outline=ACC + (int(160 * (1 - rp) * a1),), width=6)
        r = 140 * a1
        d.ellipse([540 - r, 690 - r, 540 + r, 690 + r], fill=ACC + (255,))
        text_c(L, (540, 700), "4", "black", int(190 * a1), INK)
        chip(L, 540, 920, "Birim fiyata bak", bg=WHITE, fg=INK, size=48, icon_name="magnifying_glass_tilted_right",
             scale=eb(ph(t, td + 0.2, 0.4)) * a1)
    a2 = eb(ph(t, tf - 0.1, 0.45)) * (1 - eo(ph(t, ty - 0.25, 0.25)))
    if a2 > 0.01:
        put_icon(L, "receipt", 540, 770 + 8 * math.sin(t * 2.5), 300 * a2, rot=-6)
        chip(L, 540, 1010, "Farkı fişte göreceksin", bg=GREEN, fg=WHITE, size=44, icon_name="money_with_wings", scale=a2)
    a3 = ph(t, ty - 0.1, 0.45)
    if a3 > 0:
        put_icon(L, "bookmark", 360, 780 + 8 * math.sin(t * 2.4), 220 * eb(a3), rot=-8)
        chip(L, 360, 970, "Kaydet", bg=ACC, fg=INK, size=46, k="black", scale=eb(ph(t, ty + 0.1, 0.4)))
        tb = ty + 0.5
        put_icon(L, "bell", 720, 780 + 8 * math.sin(t * 2.4 + 1), 220 * eb(ph(t, tb, 0.45)),
                 rot=14 * math.sin(t * 9) * (1 - ph(t, tb + 1.0, 0.8)))
        chip(L, 720, 970, "Takip et", bg=RED, fg=WHITE, size=46, k="black", scale=eb(ph(t, tb + 0.15, 0.4)))


# ---------- sahne zamanları ----------
starts = [0.0, first("birincisi") - 0.28, first("ikincisi") - 0.28, first("üçüncüsü") - 0.28,
          first("dördüncüsü") - 0.28, [w["s"] for w in words if clean(w["w"]) == "Bu"][-1] - 0.28]
draws = [s_hook, s_list, s_hungry, s_shelf, s_unit, s_cta]
scenes = [{"start": s, "end": (starts[i + 1] if i + 1 < len(starts) else TOTAL), "draw": d}
          for i, (s, d) in enumerate(zip(starts, draws))]

if __name__ == "__main__":
    v = Video(scenes, words, "MARKET TASARRUFU", TOTAL)
    # efekt sesleri
    for s in scenes[1:]:
        SFX.append((s["start"], "whoosh"))
    sc0 = scenes[0]
    for ti in hook_times(v, sc0):
        SFX.append((sc0["start"] + ti + 0.42, "pop"))
    for i in range(4):
        SFX.append((scenes[1]["start"] + 0.9 + i * 0.42 + 0.1, "pop"))
    SFX.append((scenes[3]["start"] + v.wt(scenes[3], "göz") + 0.2, "pop"))
    SFX.append((scenes[4]["start"] + v.wt(scenes[4], "ucuz"), "ding"))
    SFX.append((scenes[5]["start"] + v.wt(scenes[5], "faydalı"), "pop"))
    at.music(str(WORK / "music.wav"), TOTAL)
    at.sfx(str(WORK / "sfx.wav"), TOTAL, SFX)
    at.final_mix(str(WORK / "voice_cut.wav"), str(WORK / "music.wav"), str(WORK / "sfx.wav"), str(WORK / "mix.m4a"))
    if len(sys.argv) > 2 and sys.argv[2] == "frames":
        for tt in [float(x) for x in sys.argv[3].split(",")]:
            v.frame(tt).save(WORK / f"fr_{tt:05.1f}.png")
    else:
        v.render(str(WORK / "mix.m4a"), str(WORK / "video2.mp4"))
        print("bitti", TOTAL)
