"""6. video: Kışın arabayla ilgili herkesin doğru sandığı 3 yanlış (Doğru mu / Yanlış mı formatı)."""
import json, math, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from engine import *  # noqa
from widgets import *  # noqa
import audio_tools as at
import video_bg as vb

WORK = Path(sys.argv[1])
N = Path("/home/claude/pratik-abi/media/v6-kis-yanlislar")
words = json.loads((WORK / "words.json").read_text(encoding="utf-8"))
TOTAL = at.duration(str(WORK / "voice_cut.wav"))
OUTRO = 1.9
BLUE = (59, 130, 246)
QRED = (239, 68, 68)


def T(key, nth=0):
    k = trl(clean(key)).strip('"!?;')
    hits = [w for w in words if trl(clean(w["w"])).strip('"!?;') == k]
    return hits[nth]["s"]


S1, S2, S3, S4 = T("bir") - 0.2, T("iki") - 0.2, T("üç", 1) - 0.2, T("evet") - 0.2
C_AMA = T("ama") - 0.1
C_BAK = T("bakalım") - 0.2
C_YAN1 = T("yanlış", 1) - 0.1
C_SONRA = T("sonra") - 0.2
C_BU = T("bu") - 0.1
C_UST = T("üstelik") - 0.2
C_YANI = T("yani") - 0.2
C_SICAK = T("sıcak") - 0.1
C_CAT = T("ama", 1) - 0.1
C_EN = T("en") - 0.2
C_ARK = T("arkadaşın") - 0.3

SEGS = [
    dict(src=str(N / "kis-surus_2.mp4"), kind="video", ss=2, dur=C_AMA, pan=(0, 0)),
    dict(src=str(N / "karli-araba_4.mp4"), kind="video", ss=3, dur=C_BAK - C_AMA, pan=(0, 0)),
    dict(src=str(N / "buzlu-cam_4.mp4"), kind="video", ss=4, dur=S1 - C_BAK, pan=(0, 0)),
    dict(src=str(N / "egzoz_3.mp4"), kind="video", ss=1, dur=C_YAN1 - S1, pan=(0, 0)),
    dict(src=str(N / "egzoz_1.mp4"), kind="video", ss=3, dur=C_SONRA - C_YAN1, pan=(0, 0)),
    dict(src=str(N / "kis-surus_3.mp4"), kind="video", ss=3, dur=S2 - C_SONRA, pan=(0, 1)),
    dict(src=str(N / "lastik_1.mp4"), kind="video", ss=1, dur=C_BU - S2, pan=(0, 0)),
    dict(src=str(N / "karda-teker_1.mp4"), kind="video", ss=1, dur=C_UST - C_BU, pan=(0, 0)),
    dict(src=str(N / "lastik-basinc_2.mp4"), kind="video", ss=3, dur=C_YANI - C_UST, pan=(0, 0)),
    dict(src=str(N / "lastik_4.mp4"), kind="video", ss=2, dur=S3 - C_YANI, pan=(0, 0)),
    dict(src=str(N / "kaziyici_1.mp4"), kind="video", ss=2, dur=C_SICAK - S3, pan=(0, 0)),
    dict(src=str(N / "sicak-su_1.mp4"), kind="video", ss=4, dur=C_CAT - C_SICAK, pan=(0, 0)),
    dict(src=str(N / "catlak-cam_1.mp4"), kind="video", ss=1, dur=C_EN - C_CAT, pan=(0, 0)),
    dict(src=str(N / "kaziyici_1.mp4"), kind="video", ss=8, dur=S4 - C_EN, pan=(0, 0)),
    dict(src=str(N / "kis-surus_1.mp4"), kind="video", ss=2, dur=C_ARK - S4, pan=(0, 1)),
    dict(src=str(N / "karli-araba_3.mp4"), kind="video", ss=3, dur=TOTAL - OUTRO - C_ARK, pan=(0, 0)),
    dict(src=str(WORK / "outro.mp4"), kind="video", dur=OUTRO, zoom=0.06, pan=(0, 0)),
]


# ---------- quiz parçaları ----------
def myth_card(L, n, text, t, start=0.15, y0=470):
    """Efsane kartı: 'EFSANE #n' + tırnaklı cümle."""
    p = eb(ph(t, start, 0.45))
    if p <= 0.01:
        return
    w, h = 940, 340
    x0 = 70
    yy = y0 + (1 - p) * 80
    card(L, x0, yy, w, h, r=36, fill=(255, 255, 255, 255), alpha=min(1, p))
    d = ImageDraw.Draw(L)
    d.rounded_rectangle([x0 + 30, yy - 28, x0 + 260, yy + 32], radius=30, fill=QRED + (255,))
    text_c(L, (x0 + 145, yy + 2), f"EFSANE #{n}", "black", 32, WHITE)
    f = font("black", 62)
    lines, cur = [], ""
    for wd in text.split():
        test = (cur + " " + wd).strip()
        if d.textlength(test, font=f) > w - 120 and cur:
            lines.append(cur)
            cur = wd
        else:
            cur = test
    lines.append(cur)
    text_c(L, (x0 + 40, yy + 40), "“", "black", 120, (210, 215, 225), anchor="la")
    for i, ln in enumerate(lines[:3]):
        text_c(L, (x0 + w / 2, yy + 175 + (i - (len(lines[:3]) - 1) / 2) * 76), ln, "black", 62, INK)


def answer_buttons(L, t, show, reveal, answer="YANLIŞ", y=900):
    """DOĞRU / YANLIŞ butonları; reveal anında doğru cevap parlar."""
    p = eb(ph(t, show, 0.4))
    if p <= 0.01:
        return
    r = ph(t, reveal, 0.3)
    for i, (lab, col) in enumerate([("DOĞRU", BLUE), ("YANLIŞ", QRED)]):
        cx = 300 + i * 480
        win = lab == answer
        sc = p * (1 + (0.12 * math.sin(math.pi * clamp(r * 1.0)) if win else 0))
        dim = (1 - 0.65 * r) if not win else 1
        w, h = int(380 * sc), int(130 * sc)
        shake = (10 * math.sin(t * 60) * (1 - r)) if (win and 0 < r < 1) else 0
        c = tuple(int(v * dim + 30 * (1 - dim)) for v in col)
        card(L, cx - w / 2 + shake, y - h / 2, w, h, r=h // 2, fill=c + (255,), alpha=1.0)
        text_c(L, (cx + shake, y), lab, "black", int(54 * sc) + 1, WHITE, alpha=dim)
        if win and r > 0:
            put_icon(L, "cross_mark" if lab == "YANLIŞ" else "check_mark_button", cx + w / 2 - 10, y - h / 2 + 5,
                     90 * eb(r))


def countdown(L, t, start, end, cx=540, cy=1110):
    if not (start <= t < end):
        return
    p = (t - start) / max(end - start, 0.1)
    d = ImageDraw.Draw(L)
    r = 52
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(14, 18, 32, 220))
    d.arc([cx - r, cy - r, cx + r, cy + r], -90, -90 + 360 * (1 - p), fill=ACC + (255,), width=10)
    put_icon(L, "thinking_face", cx, cy, 70, shadow=False)


def crack(L, t, start, cx=560, cy=760):
    """Ekranda büyüyen cam çatlağı."""
    p = eo(ph(t, start, 0.35))
    if p <= 0:
        return
    rnd = random.Random(4)
    d = ImageDraw.Draw(L)
    for k in range(11):
        ang = k * (2 * math.pi / 11) + rnd.uniform(-0.2, 0.2)
        length = rnd.uniform(260, 620) * p
        x, y = cx, cy
        pts = [(x, y)]
        steps = 6
        for s in range(steps):
            ang2 = ang + rnd.uniform(-0.35, 0.35)
            x += math.cos(ang2) * length / steps
            y += math.sin(ang2) * length / steps
            pts.append((x, y))
        d.line(pts, fill=(255, 255, 255, 230), width=5)
        d.line([(px + 2, py + 2) for px, py in pts], fill=(0, 0, 0, 90), width=3)
    for rr in (60, 140):
        rr2 = rr * p
        d.ellipse([cx - rr2, cy - rr2, cx + rr2, cy + rr2], outline=(255, 255, 255, 120), width=3)


# ---------- 0: kanca ----------
def s_hook(v, sc, L, t, dur):
    ta, tb = v.wt(sc, "ama"), v.wt(sc, "bakalım")
    headline(L, [("Kışın arabayla", False), ("3 YANLIŞ", True)], t, y0=250, start=-1)
    q = ph(t, ta, 0.4)
    if q > 0:
        for i in range(3):
            qi = eb(ph(t, ta + 0.25 + i * 0.25, 0.4))
            put_icon(L, "red_question_mark", 300 + i * 240, 760 + 15 * math.sin(t * 4 + i), 190 * qi, rot=-10 + i * 10)
    q = ph(t, tb, 0.4)
    if q > 0:
        chip(L, 540, 1060, "Sen kaçını biliyorsun?", bg=ACC, fg=INK, size=48, icon_name="trophy", k="black",
             scale=eb(q))


# ---------- 1: rölanti ----------
def s_m1(v, sc, L, t, dur):
    ts, ty, tb, tso = v.wt(sc, "sence"), v.wt(sc, "yanlış"), v.wt(sc, "bugünkü"), v.wt(sc, "sonra")
    if t < tb:
        myth_card(L, 1, "Motoru 10 dakika rölantide ısıtmak lazım", t)
        answer_buttons(L, t, ts - 0.2, ty)
        countdown(L, t, ts + 0.3, ty)
        if t >= ty:
            stamp(L, 540, 1110, "YANLIŞ!", QRED, t, ty, rot=-8, size=110)
    else:
        headline(L, [("1 dakika", True), ("yeter", False)], t, y0=250, start=tb - 0.05)
        q = ph(t, tb, 0.45)
        put_icon(L, "stopwatch", 540, 720, 300 * eb(q), rot=-6 + 4 * math.sin(t * 3))
        chip(L, 540, 950, "Rölanti = boşa yakıt", bg=QRED, fg=WHITE, size=42, icon_name="money_with_wings",
             scale=eb(ph(t, tb + 0.6, 0.4)) * (1 - ph(t, tso, 0.25)))
        q2 = ph(t, tso, 0.4)
        if q2 > 0:
            chip(L, 540, 950, "İlk birkaç km sakin sür", bg=GREEN, fg=WHITE, size=42, icon_name="automobile", k="black",
                 scale=eb(q2))


# ---------- 2: lastik ----------
def gauge(L, cx, cy, val, label_col, alpha=1.0):
    d = ImageDraw.Draw(L)
    r = 190
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(20, 22, 32, int(235 * alpha)), outline=(200, 205, 215, int(255 * alpha)),
              width=10)
    for k in range(9):
        a = math.radians(150 + k * 30)
        d.line([cx + (r - 30) * math.cos(a), cy + (r - 30) * math.sin(a), cx + (r - 10) * math.cos(a),
                cy + (r - 10) * math.sin(a)], fill=WHITE + (int(255 * alpha),), width=5)
    a = math.radians(150 + 240 * clamp(val / 3.0))
    d.line([cx, cy, cx + (r - 45) * math.cos(a), cy + (r - 45) * math.sin(a)], fill=label_col + (int(255 * alpha),), width=12)
    d.ellipse([cx - 18, cy - 18, cx + 18, cy + 18], fill=WHITE + (int(255 * alpha),))
    text_c(L, (cx, cy + 95), f"{val:.1f} bar", "black", 46, label_col, alpha=alpha)


def s_m2(v, sc, L, t, dur):
    ttu, tbu, td, tus, tya = (v.wt(sc, "tutar"), v.wt(sc, "bu"), v.wt(sc, "düşük"), v.wt(sc, "üstelik"),
                              v.wt(sc, "yani"))
    if t < td:
        myth_card(L, 2, "Lastiğin havasını indirirsen karda daha iyi tutar", t)
        answer_buttons(L, t, ttu - 0.3, tbu)
        countdown(L, t, ttu + 0.2, tbu)
        if t >= tbu:
            stamp(L, 540, 1110, "YANLIŞ!", QRED, t, tbu, rot=8, size=110)
    else:
        headline(L, [("Düşük basınç", False), ("= kötü tutuş", True)], t, y0=250, start=td - 0.05)
        cold = eio(ph(t, tus + 0.6, 1.4))
        val = lerp(2.4, 2.0, cold)
        gauge(L, 540, 720, val, QRED if cold > 0.5 else WHITE)
        if t >= tus:
            put_icon(L, "snowflake", 820, 560, 130 * eb(ph(t, tus, 0.4)), rot=20 * math.sin(t))
            chip(L, 540, 1000, "Soğukta basınç kendiliğinden düşer", bg=(70, 150, 255), fg=WHITE, size=36,
                 icon_name="thermometer", scale=eb(ph(t, tus + 0.2, 0.4)) * (1 - ph(t, tya, 0.25)))
        q = ph(t, tya, 0.4)
        if q > 0:
            chip(L, 540, 1000, "İndirme, kontrol et", bg=GREEN, fg=WHITE, size=46, icon_name="check_mark_button",
                 k="black", scale=eb(q))


# ---------- 3: sıcak su ----------
def s_m3(v, sc, L, t, dur):
    ta, tac, tama, ten, tpl = (v.wt(sc, "açılır"), v.wt(sc, "açılır", 1), v.wt(sc, "ama"), v.wt(sc, "en"),
                               v.wt(sc, "plastik"))
    if t < ten:
        if t < tama:
            myth_card(L, 3, "Buzlanan cama sıcak su dökersen anında açılır", t)
            answer_buttons(L, t, ta - 0.3, 99)
            countdown(L, t, ta + 0.4, tac)
            q = ph(t, tac, 0.3)
            if q > 0:
                chip(L, 540, 1060, "Açılır, orası doğru…", bg=BLUE, fg=WHITE, size=44, icon_name="teapot", scale=eb(q))
        else:
            crack(L, t, v.wt(sc, "çatlayabilir"))
            stamp(L, 540, 1000, "CAM ÇATLAR!", QRED, t, v.wt(sc, "çatlayabilir"), rot=-8, size=96)
    else:
        headline(L, [("En güvenlisi", True)], t, y0=250, start=ten - 0.05)
        glass(L, 140, 500, 800, 520, alpha=eo(ph(t, ten, 0.4)))
        q1 = ph(t, ten + 0.4, 0.4)
        if q1 > 0:
            put_icon(L, "wind_face", 280, 640, 150 * eb(q1))
            text_c(L, (390, 640), "Üflemeyi cama ver", "black", 50, WHITE, anchor="lm", alpha=eo(q1))
        q2 = ph(t, tpl, 0.4)
        if q2 > 0:
            put_icon(L, "check_mark_button", 280, 860, 130 * eb(q2))
            text_c(L, (390, 860), "Plastik kazıyıcı", "black", 50, WHITE, anchor="lm", alpha=eo(q2))


# ---------- 4: puan + kapanış ----------
def s_end(v, sc, L, t, dur):
    tk, tsk, tbe, tar = v.wt(sc, "kaçını"), v.wt(sc, "üçte"), v.wt(sc, "beğenmeyi"), v.wt(sc, "arkadaşın")
    if t < dur - OUTRO:
        headline(L, [("Puanın", False), ("kaç?", True)], t, y0=250)
        q = ph(t, 0.15, 0.45)
        if q > 0 and t < tar:
            glass(L, 240, 470, 600, 420, alpha=eo(q))
            put_icon(L, "trophy", 540, 600, 200 * eb(q), rot=4 * math.sin(t * 3))
            qm = "?" if int(t * 2.5) % 2 == 0 else " "
            text_c(L, (540, 810), f"{qm} / 3", "black", 110, ACC, alpha=eo(q))
            if t >= tsk:
                put_icon(L, "party_popper", 820, 520, 150 * eb(ph(t, tsk, 0.4)), rot=-15)
                chip(L, 540, 1000, "Yorumlara yaz!", bg=ACC, fg=INK, size=46, icon_name="speech_balloon", k="black",
                     scale=eb(ph(t, tsk, 0.4)))
        if t >= tar:
            qa = ph(t, tar, 0.4)
            glass(L, 120, 520, 840, 280, alpha=eo(qa))
            put_icon(L, "automobile", 250, 660, 150 * eb(qa))
            text_c(L, (370, 625), "Arabayı 10 dk ısıtan", "black", 46, WHITE, anchor="lm", alpha=eo(qa))
            text_c(L, (370, 695), "arkadaşına gönder", "b", 40, ACC, anchor="lm", alpha=eo(qa))
        q2 = ph(t, tbe - 0.1, 0.45)
        if q2 > 0:
            put_icon(L, "thumbs_up", 360, 960 + 8 * math.sin(t * 2.4), 170 * eb(q2), rot=-8)
            chip(L, 360, 1080, "Beğen", bg=ACC, fg=INK, size=42, k="black", scale=eb(ph(t, tbe + 0.1, 0.4)))
            tb = tbe + 0.45
            put_icon(L, "bell", 720, 960, 170 * eb(ph(t, tb, 0.45)), rot=14 * math.sin(t * 9) * (1 - ph(t, tb + 1.0, 0.8)))
            chip(L, 720, 1080, "Takip et", bg=RED, fg=WHITE, size=42, k="black", scale=eb(ph(t, tb + 0.15, 0.4)))
    else:
        lt = t - (dur - OUTRO)
        chip(L, 540, 1560, "Takip et, kaçırma!", bg=RED, fg=WHITE, size=50, icon_name="bell", k="black",
             scale=eb(ph(lt, 0.25, 0.4)))


starts = [0.0, S1, S2, S3, S4]
draws = [s_hook, s_m1, s_m2, s_m3, s_end]
scenes = [{"start": s, "end": (starts[i + 1] if i + 1 < len(starts) else TOTAL), "draw": d}
          for i, (s, d) in enumerate(zip(starts, draws))]

if __name__ == "__main__":
    mode = sys.argv[2] if len(sys.argv) > 2 else "render"
    if not (WORK / "bg.mp4").exists():
        build_bg(SEGS, str(WORK / "bg.mp4"), N)
    bg = vb.VideoBackground(str(WORK / "bg.mp4"), SEGS)
    v = Video(scenes, words, "", TOTAL, bg=bg, trans="zoom")
    if mode == "frames":
        for tt in [float(x) for x in sys.argv[3].split(",")]:
            v.frame(tt).save(WORK / f"fr_{tt:05.1f}.png")
    elif mode == "render":
        sfx = [(s["start"], "whoosh") for s in scenes[1:]] + [(TOTAL - OUTRO, "whoosh"), (TOTAL - OUTRO + 0.15, "tink")]
        sfx += [(T("yanlış", 1), "ding"), (T("yanlış", 2), "ding"), (T("çatlayabilir"), "pop"), (T("ama"), "pop"),
                (T("bakalım"), "pop"), (T("sonra"), "pop"), (T("yani"), "pop"), (T("plastik"), "pop"),
                (T("üçte"), "ding"), (T("beğenmeyi"), "pop")]
        at.music(str(WORK / "music.wav"), TOTAL, bpm=108, style="quiz")
        at.sfx(str(WORK / "sfx.wav"), TOTAL, sfx)
        at.final_mix(str(WORK / "voice_cut.wav"), str(WORK / "music.wav"), str(WORK / "sfx.wav"), str(WORK / "mix.m4a"))
        v.render(str(WORK / "mix.m4a"), str(WORK / "video.mp4"))
        compress(str(WORK / "video.mp4"), str(WORK / "final.mp4"))
        print("bitti", TOTAL)
