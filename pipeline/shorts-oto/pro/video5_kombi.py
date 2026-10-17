"""5. video: Kombide doğalgazı yakan 4 hata."""
import json, math, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from engine import *  # noqa
from widgets import *  # noqa
import audio_tools as at
import video_bg as vb

WORK = Path(sys.argv[1])
N = Path("/home/claude/pratik-abi/media/v5-kombi")
words = json.loads((WORK / "words.json").read_text(encoding="utf-8"))
TOTAL = at.duration(str(WORK / "voice_cut.wav"))
OUTRO = 1.9


def T(key, nth=0):
    hits = [w for w in words if trl(clean(w["w"])).strip("!?;") == trl(clean(key))]
    return hits[nth]["s"]


S1, S2, S3, S4, S5 = T("bir") - 0.2, T("iki") - 0.2, T("üç") - 0.2, T("dört", 1) - 0.2, T("bir", 1) - 0.2
C_TAN = T("tanıdık") - 0.1
C_SUC = T("bu") - 0.1
C_ICIN = T("içinde") - 0.2
C_ARA = T("aramızda") - 0.2
C_AKS = T("akşam") - 0.2
C_KAP = T("kapatma") - 0.2
C_YOG = T("yoğuşmalı") - 0.2
C_GECE = T("gece") - 0.2
C_SON = T("senin") - 0.2

SEGS = [
    dict(src=str(N / "soguk_1.mp4"), kind="video", ss=2, dur=C_TAN, pan=(0, 0)),
    dict(src=str(N / "soguk_4.mp4"), kind="video", ss=3, dur=C_SUC - C_TAN, pan=(0, 0)),
    dict(src=str(N / "alev_1.mp4"), kind="video", ss=1, dur=S1 - C_SUC, pan=(0, 0)),
    dict(src=str(N / "termostat_1.mp4"), kind="video", ss=0, dur=C_ICIN - S1, pan=(0, 0)),
    dict(src=str(N / "salon_4.mp4"), kind="video", ss=3, dur=S2 - C_ICIN, pan=(1, 0)),
    dict(src=str(N / "salon_1.mp4"), kind="video", ss=5, dur=C_ARA - S2, pan=(0, 0)),
    dict(src=str(N / "perde_4.mp4"), kind="video", ss=2, dur=S3 - C_ARA, pan=(0, 0)),
    dict(src=str(N / "kar-pencere_2.mp4"), kind="video", ss=3, dur=C_AKS - S3, pan=(0, 0)),
    dict(src=str(N / "soguk_3.mp4"), kind="video", ss=4, dur=C_KAP - C_AKS, pan=(0, 0)),
    dict(src=str(N / "termostat_1.mp4"), kind="video", ss=2, dur=S4 - C_KAP, pan=(0, 0)),
    dict(src=str(N / "alev_2.mp4"), kind="video", ss=2, dur=C_YOG - S4, pan=(0, 0)),
    dict(src=str(N / "salon_2.mp4"), kind="video", ss=5, dur=S5 - C_YOG, pan=(-1, 0)),
    dict(src=str(N / "gunes_2.mp4"), kind="video", ss=0, dur=C_GECE - S5, pan=(0, 0)),
    dict(src=str(N / "kar-pencere_3.mp4"), kind="video", ss=1, dur=C_SON - C_GECE, pan=(0, 0)),
    dict(src=str(N / "soguk_2.mp4"), kind="video", ss=2, dur=TOTAL - OUTRO - C_SON, pan=(0, 0)),
    dict(src=str(WORK / "outro.mp4"), kind="video", dur=OUTRO, zoom=0.06, pan=(0, 0)),
]


def radiator(L, x0, y0, w, h, cold_top, hot_all, alpha=1.0):
    """Petek çizimi: üst soğuk (mavi) -> alt sıcak (kırmızı); hot_all=1 iken hepsi sıcak."""
    d = ImageDraw.Draw(L)
    fins = 7
    fw = w / fins
    for i in range(fins):
        fx = x0 + i * fw + 6
        for k in range(int(h)):
            u = k / h  # 0 üst, 1 alt
            cold = max(0.0, (1 - u / 0.55)) * cold_top * (1 - hot_all)
            col = tuple(int(lerp(a, b, cold)) for a, b in zip((235, 95, 60), (70, 150, 255)))
            if k % 3 == 0:
                d.line([fx, y0 + k, fx + fw - 12, y0 + k], fill=col + (int(255 * alpha),), width=3)
    d.rounded_rectangle([x0 - 6, y0 - 14, x0 + w + 6, y0 + 6], radius=8, fill=(200, 205, 215, int(255 * alpha)))
    d.rounded_rectangle([x0 - 6, y0 + h - 6, x0 + w + 6, y0 + h + 14], radius=8, fill=(200, 205, 215, int(255 * alpha)))


# ---------- 0: kanca ----------
def s_hook(v, sc, L, t, dur):
    tf, ttan, tsuc, td = v.wt(sc, "fatura da"), v.wt(sc, "tanıdık"), v.wt(sc, "suç"), v.wt(sc, "dört")
    if t < td - 0.3:
        headline(L, [("Ev hâlâ", False), ("soğuk mu?", True)], t, y0=250, start=-1)
    else:
        headline(L, [("Asıl sebep:", False), ("4 hata", True)], t, y0=250, start=td - 0.3)
    q = ph(t, tf, 0.4)
    if q > 0 and t < tsuc:
        chip(L, 540, 470, "Fatura da cabası", bg=RED, fg=WHITE, size=44, icon_name="money_with_wings", k="black", scale=eb(q))
    q = ph(t, ttan, 0.4)
    if q > 0 and t < tsuc:
        put_icon(L, "cold_face", 540, 820, 280 * eb(q), rot=6 * math.sin(t * 7))
    if t >= tsuc:
        stamp(L, 540, 840, "SUÇ KOMBİDE DEĞİL", GREEN, t, tsuc, rot=-6, size=62)


# ---------- 1: petek havası ----------
def s_air(v, sc, L, t, dur):
    headline(L, [("1.", True), ("Peteğin havasını al", False)], t, y0=250)
    tu, ti, tv, tok = v.wt(sc, "üstü"), v.wt(sc, "içinde"), v.wt(sc, "vanasını"), v.wt(sc, "kadar")
    p = eo(ph(t, 0.2, 0.45))
    if p <= 0:
        return
    glass(L, 150, 470 + (1 - p) * 60, 780, 560, alpha=p)
    x0, y0, w, h = 240, 560 + (1 - p) * 60, 600, 380
    cold = ph(t, tu, 0.5)
    hot = eio(ph(t, tv + 1.2, 1.0))
    radiator(L, x0, y0, w, h, cold, hot, p)
    if cold > 0.5 and hot < 0.5:
        text_c(L, (x0 + w + 40, y0 + 60), "soğuk", "black", 34, (110, 170, 255), anchor="lm", alpha=p)
        text_c(L, (x0 + w + 40, y0 + h - 40), "sıcak", "black", 34, (255, 120, 90), anchor="lm", alpha=p)
    qb = ph(t, ti, 0.4)
    if qb > 0:
        for k in range(4):
            esc = ph(t, tv + 0.2 + k * 0.15, 0.8)
            bx = x0 + 90 + k * 140 + (w - 90 - k * 140) * eio(esc)
            by = y0 + 50 - 40 * math.sin(t * 3 + k) * (1 - esc) - 140 * eio(esc)
            put_icon(L, "bubbles", bx, by, 90 * eb(qb), alpha=1 - ph(esc, 0.7, 0.3))
    qv = ph(t, tv, 0.4)
    if qv > 0:
        put_icon(L, "wrench", x0 + w + 10, y0 - 30, 130 * eb(qv), rot=-30 + 20 * math.sin(t * 6))
    q = ph(t, tok, 0.4)
    if q > 0:
        chip(L, 540, 1100, "Petek baştan sona ısınır", bg=GREEN, fg=WHITE, size=40, icon_name="check_mark_button",
             k="black", scale=eb(q))


# ---------- 2: peteğin önü ----------
def s_block(v, sc, L, t, dur):
    headline(L, [("2.", True), ("Peteğin önünü kapatma", False)], t, y0=250)
    tk, tp, ta = v.wt(sc, "kanepe"), v.wt(sc, "perde"), v.wt(sc, "aramızda")
    p = eo(ph(t, 0.2, 0.45))
    if p <= 0:
        return
    glass(L, 110, 470 + (1 - p) * 60, 860, 560, alpha=p)
    x0, y0 = 170, 600 + (1 - p) * 60
    radiator(L, x0, y0, 150, 330, 0, 1, p)
    d = ImageDraw.Draw(L)
    couch = ph(t, tk, 0.5)
    curtain = ph(t, tp, 0.5)
    blocked = max(couch, curtain)
    reach = lerp(640, 120, eo(blocked))
    for k in range(4):
        yy = y0 + 40 + k * 80
        u = ((t * 1.2 + k * 0.25) % 1)
        length = reach * u
        pts = [(x0 + 170 + j * 8, yy + 10 * math.sin(j * 0.5 + t * 6 + k)) for j in range(int(length / 8))]
        if len(pts) > 1:
            d.line(pts, fill=(255, 110, 70, int(230 * (1 - u * 0.5))), width=7)
    if couch > 0:
        put_icon(L, "couch_and_lamp", lerp(1100, 470, eo(couch)), y0 + 230, 260)
    if curtain > 0:
        cw = 180 * eo(curtain)
        for k in range(6):
            xx = x0 + 160 - k * (cw / 6)
            d.rectangle([xx - 14, y0 - 60, xx, y0 + 380], fill=(150, 60, 70, 235))
    q = ph(t, ta, 0.4)
    if q > 0:
        chip(L, 540, 1100, "Sıcak hava perdenin arkasında kalıyor", bg=RED, fg=WHITE, size=34, icon_name="fire",
             scale=eb(q))


# ---------- 3: tamamen kapatma ----------
def dial(L, cx, cy, temp, col, label, alpha=1.0):
    d = ImageDraw.Draw(L)
    r = 170
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(20, 22, 32, int(255 * alpha)), outline=col + (int(255 * alpha),), width=14)
    text_c(L, (cx, cy - 15), temp, "black", 130, WHITE, alpha=alpha)
    text_c(L, (cx, cy + 85), label, "black", 38, col, alpha=alpha)


def s_off(v, sc, L, t, dur):
    headline(L, [("3.", True), ("Tamamen kapatma, kıs", False)], t, y0=250)
    tt, tak, tko, tka, tki = (v.wt(sc, "tamamen"), v.wt(sc, "akşam"), v.wt(sc, "kombi", 1), v.wt(sc, "kapatma", 1),
                              v.wt(sc, "kıs"))
    p = eo(ph(t, 0.2, 0.45))
    if p <= 0:
        return
    cy = 780
    if t < tak:
        off = ph(t, tt, 0.3)
        dial(L, 540, cy, "22°" if off < 0.5 else "–", RED if off >= 0.5 else ACC, "KAPALI" if off >= 0.5 else "AÇIK", p)
        if off > 0:
            stamp(L, 540, cy + 260, "TAMAMEN KAPATMA", RED, t, tt + 0.1, rot=-6, size=52)
    elif t < tka:
        q = ph(t, tak, 0.3)
        put_icon(L, "cold_face", 380, cy, 230 * eb(q))
        put_icon(L, "thermometer", 700, cy, 230 * eb(q), rot=-8)
        chip(L, 540, cy + 230, "Akşam ev buz gibi", bg=(70, 150, 255), fg=WHITE, size=42, k="black", scale=eb(q))
        q2 = ph(t, tko, 0.4)
        if q2 > 0:
            chip(L, 540, cy - 230, "Kombi sonuna kadar çalışır", bg=RED, fg=WHITE, size=40, icon_name="fire",
                 k="black", scale=eb(q2))
    else:
        q = ph(t, tki, 0.6)
        temp = int(round(lerp(22, 19, eio(q))))
        dial(L, 540, cy, f"{temp}°", GREEN if q > 0.5 else ACC, "BİRAZ KIS" if q > 0.5 else "AÇIK", 1.0)
        if q > 0.5:
            chip(L, 540, cy + 260, "Kapatma, birkaç derece kıs", bg=GREEN, fg=WHITE, size=40,
                 icon_name="check_mark_button", k="black", scale=eb(ph(t, tki + 0.2, 0.4)))


# ---------- 4: su sıcaklığı ----------
def s_water(v, sc, L, t, dur):
    headline(L, [("4.", True), ("Suyu MAX'a çekme", False)], t, y0=250)
    ts, ty, tv = v.wt(sc, "sonuna"), v.wt(sc, "yoğuşmalı"), v.wt(sc, "verimli")
    p = eo(ph(t, 0.2, 0.45))
    if p <= 0:
        return
    glass(L, 170, 480 + (1 - p) * 60, 740, 520, alpha=p)
    cx, cy, r = 540, 820 + (1 - p) * 60, 230
    d = ImageDraw.Draw(L)
    for k in range(36):
        a0 = 180 + k * 5
        u = k / 35
        col = (70, 150, 255) if u < 0.3 else (GREEN if u < 0.65 else RED)
        d.arc([cx - r, cy - r, cx + r, cy + r], a0, a0 + 4, fill=col + (int(255 * p),), width=34)
    text_c(L, (cx - r + 30, cy + 40), "düşük", "b", 30, (180, 185, 200), alpha=p)
    text_c(L, (cx, cy - r - 30), "orta", "b", 30, GREEN, alpha=p)
    text_c(L, (cx + r - 30, cy + 40), "MAX", "black", 30, RED, alpha=p)
    up = eio(ph(t, ts, 0.6))
    down = eio(ph(t, ty + 0.4, 0.8))
    ang = math.radians(lerp(lerp(250, 345, up), 280, down))
    d.line([cx, cy, cx + (r - 50) * math.cos(ang), cy + (r - 50) * math.sin(ang)], fill=WHITE + (int(255 * p),), width=12)
    d.ellipse([cx - 20, cy - 20, cx + 20, cy + 20], fill=WHITE + (int(255 * p),))
    if up > 0.5 and down < 0.5:
        put_icon(L, "money_with_wings", cx + 250, cy - 180, 140 * eb(ph(t, ts + 0.3, 0.4)))
    q = ph(t, ty, 0.4)
    if q > 0:
        chip(L, 540, 1080, "Yoğuşmalı kombilerde", bg=WHITE, fg=INK, size=40, icon_name="fire", scale=eb(q))
    q = ph(t, tv, 0.4)
    if q > 0:
        chip(L, 540, 470, "Orta sıcaklık = daha verimli", bg=GREEN, fg=WHITE, size=40, icon_name="check_mark_button",
             k="black", scale=eb(q))


# ---------- 5: bonus + kapanış ----------
def s_end(v, sc, L, t, dur):
    son = C_SON - sc["start"]
    if t < son:
        headline(L, [("Bonus:", True), ("perde taktiği", False)], t, y0=250)
        tg, tn = v.wt(sc, "gündüz"), v.wt(sc, "gece")
        q = ph(t, tg, 0.45)
        if q > 0:
            glass(L, 120, 520, 400, 420, alpha=eo(q))
            put_icon(L, "sun", 320, 680 + 8 * math.sin(t * 2), 190 * eb(q))
            text_c(L, (320, 840), "Gündüz", "black", 44, WHITE, alpha=eo(q))
            text_c(L, (320, 895), "perdeyi aç", "b", 36, ACC, alpha=eo(q))
        q = ph(t, tn, 0.45)
        if q > 0:
            glass(L, 560, 520, 400, 420, alpha=eo(q))
            put_icon(L, "crescent_moon", 760, 680 + 8 * math.sin(t * 2 + 1), 180 * eb(q))
            text_c(L, (760, 840), "Gece", "black", 44, WHITE, alpha=eo(q))
            text_c(L, (760, 895), "perdeyi kapat", "b", 36, ACC, alpha=eo(q))
    elif t < dur - OUTRO:
        headline(L, [("Sıcacık", False), ("kışlar!", True)], t - son, y0=250)
        outro(v, sc, L, t)
    else:
        lt = t - (dur - OUTRO)
        chip(L, 540, 1560, "Takip et, kaçırma!", bg=RED, fg=WHITE, size=50, icon_name="bell", k="black",
             scale=eb(ph(lt, 0.25, 0.4)))


starts = [0.0, S1, S2, S3, S4, S5]
draws = [s_hook, s_air, s_block, s_off, s_water, s_end]
scenes = [{"start": s, "end": (starts[i + 1] if i + 1 < len(starts) else TOTAL), "draw": d}
          for i, (s, d) in enumerate(zip(starts, draws))]

if __name__ == "__main__":
    mode = sys.argv[2] if len(sys.argv) > 2 else "render"
    if not (WORK / "bg.mp4").exists() or mode == "bg":
        build_bg(SEGS, str(WORK / "bg.mp4"), N)
    bg = vb.VideoBackground(str(WORK / "bg.mp4"), SEGS)
    v = Video(scenes, words, "", TOTAL, bg=bg)
    if mode == "frames":
        for tt in [float(x) for x in sys.argv[3].split(",")]:
            v.frame(tt).save(WORK / f"fr_{tt:05.1f}.png")
    else:
        sfx = [(s["start"], "whoosh") for s in scenes[1:]] + [(C_SON, "whoosh"), (TOTAL - OUTRO, "whoosh"),
                                                               (TOTAL - OUTRO + 0.15, "tink")]
        sfx += [(T("fatura da"), "pop"), (T("tanıdık"), "pop"), (T("suç"), "ding"), (T("vanasını"), "pop"),
                (T("kadar") , "pop"), (T("kanepe"), "pop"), (T("perde"), "pop"), (T("tamamen"), "pop"),
                (T("kıs"), "ding"), (T("verimli"), "ding"), (T("gündüz"), "pop"), (T("gece"), "pop"),
                (T("senin"), "pop"), (T("beğenmeyi"), "pop")]
        at.music(str(WORK / "music.wav"), TOTAL, bpm=76)
        at.sfx(str(WORK / "sfx.wav"), TOTAL, sfx)
        at.final_mix(str(WORK / "voice_cut.wav"), str(WORK / "music.wav"), str(WORK / "sfx.wav"), str(WORK / "mix.m4a"))
        v.render(str(WORK / "mix.m4a"), str(WORK / "video.mp4"))
        compress(str(WORK / "video.mp4"), str(WORK / "final.mp4"))
        print("bitti", TOTAL)
