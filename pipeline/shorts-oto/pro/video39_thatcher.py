"""39. video (2K, ~44 sn): Telefonu ters çevir — Thatcher illüzyonu.
Kullanım: python3 video39_thatcher.py <WORK> [frames t1,t2,... | ses | render]"""
import os
os.environ.setdefault("PA_SCALE", str(4 / 3))
import json, math, subprocess, sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from engine import *  # noqa
from pa_ui import put_word, panel, txt, pop, captions
import audio_tools as at
from abi_yuz import konusma
from rozet import Rozet

WORK = Path(sys.argv[1])
VOICE = WORK / "voice_cut.wav"
words = json.loads((WORK / "words.json").read_text(encoding="utf-8"))
TOTAL = round(at.duration(str(VOICE)) + 0.35, 3)


def _hits(key):
    k = trl(clean(key)).strip('"!?;,.…')
    return [w for w in words if trl(clean(w["w"])).strip('"!?;,.…') == k]


def T(key, nth=0):
    return _hits(key)[nth]["s"]


t_ilk, t_cevir, t_iste, t_gozler = T("İlk"), T("çeviriyorum"), T("İşte"), T("gözler")
t_buna, t_1980, t_beynin, t_ama = T("Buna"), T("1980'de"), T("Beynin"), T("Ama")
t_gozler2, t_kacir, t_ustelik, t_sen, t_yorum, t_daha = T("Gözler"), T("kaçırırsın"), T("Üstelik"), T("Sen"), \
    T("Yorumlara"), T("Daha")
FLIP1 = (t_cevir + 0.05, t_cevir + 0.95)
FLIP2 = (t_ama - 0.05, t_ama + 0.75)        # ikili düzen ters döner
FLIP3 = (t_kacir + 0.1, t_kacir + 0.9)      # ikisi birden düz döner
CUTS = [FLIP1[1], t_buna - 0.1, t_beynin - 0.1, FLIP3[1], t_ustelik - 0.1, t_sen - 0.1]

GOLD = (255, 204, 70)
INKC = (14, 16, 30)


def sm(x):
    return eio(clamp(x))


def ramp(t, a, b):
    return sm((t - a) / max(1e-6, b - a))


def wnd(t, a, b, fi=0.2, fo=0.2):
    return ramp(t, a, a + fi) * (1 - ramp(t, b - fo, b))


# ---------------- yüzler ----------------
CROP = (250, 300, 1650, 1900)


def load_face(name, w):
    im = cv2.cvtColor(cv2.imread(str(WORK / name)), cv2.COLOR_BGR2RGB)
    x0, y0, x1, y1 = CROP
    im = im[y0:y1, x0:x1]
    h = int(w * (y1 - y0) / (x1 - x0))
    im = cv2.resize(im, (w, h), interpolation=cv2.INTER_AREA)
    a = Image.fromarray(im).convert("RGBA")
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, w - 1, h - 1], radius=int(u(44)), fill=255)
    a.putalpha(m)
    return a


BIGW, SMW = int(u(820)), int(u(470))
TH_BIG = load_face("thatcher.jpg", BIGW)
TH_SM = load_face("thatcher.jpg", SMW)
OR_SM = load_face("face.jpg", SMW)

# göz ve ağız konumları (kırpılmış yüz içinde, 0..1)
FEAT = [((688 - 250) / 1400, (922 - 300) / 1600, 0.105), ((1050 - 250) / 1400, (834 - 300) / 1600, 0.105),
        ((975 - 250) / 1400, (1268 - 300) / 1600, 0.17)]

BG = np.zeros((H, W, 3), np.float32)
_yy, _xx = np.mgrid[0:H, 0:W].astype(np.float32)
_r = np.sqrt(((_xx - W / 2) / W) ** 2 + ((_yy - H * 0.38) / H) ** 2)
for c, (a, b) in enumerate(zip((34, 30, 52), (10, 10, 18))):
    BG[..., c] = b + (a - b) * np.clip(1 - _r * 1.5, 0, 1) ** 1.4
BGIMG = Image.fromarray(BG.astype(np.uint8)).convert("RGBA")
del _yy, _xx, _r


def rot_at(t):
    """ana yüzün dönüş açısı (derece): 180 = ters"""
    if t < FLIP1[0]:
        return 180.0
    if t < FLIP1[1]:
        k = sm((t - FLIP1[0]) / (FLIP1[1] - FLIP1[0]))
        return 180 * (1 - k) - 14 * math.sin(math.pi * k)
    return 0.0


def place(im, face, cx, cy, ang, scale=1.0, alpha=1.0, shadow=True):
    f = face
    if abs(scale - 1) > 0.003:
        f = f.resize((max(1, int(f.width * scale)), max(1, int(f.height * scale))), Image.BICUBIC)
    if alpha < 0.999:
        f = set_alpha(f, alpha)
    if abs(ang) > 0.05:
        f = f.rotate(ang, resample=Image.BICUBIC, expand=True)
    if shadow:
        sh = Image.new("RGBA", f.size, (0, 0, 0, 0))
        sh.putalpha(f.getchannel("A").point(lambda v: int(v * 0.55)))
        sh = sh.filter(ImageFilter.GaussianBlur(u(22)))
        im.alpha_composite(sh, (int(cx - f.width / 2), int(cy - f.height / 2 + u(18))))
    im.alpha_composite(f, (int(cx - f.width / 2), int(cy - f.height / 2)))


def feat_xy(cx, cy, w, h, ang, fx, fy):
    px, py = (fx - 0.5) * w, (fy - 0.5) * h
    a = math.radians(-ang)
    return cx + px * math.cos(a) - py * math.sin(a), cy + px * math.sin(a) + py * math.cos(a)


def rings(L, t, cx, cy, w, h, ang, t0, col=RED):
    d = ImageDraw.Draw(L)
    for i, (fx, fy, fr) in enumerate(FEAT):
        q = pop(t, t0 + 0.18 * i, 0.3)
        if q <= 0.01:
            continue
        x, y = feat_xy(cx, cy, w, h, ang, fx, fy)
        r = fr * w * (1.0 + 0.25 * (1 - q))
        rx, ry = r * (1.25 if i == 2 else 1.1), r * (0.75 if i == 2 else 0.8)
        d.ellipse([x - rx, y - ry, x + rx, y + ry], outline=col + (255,), width=int(u(9)))


ROZ = Rozet()
OPN, RND = konusma(VOICE, FPS)


def scene(im, t):
    """yüz katmanı"""
    if t < FLIP2[0]:
        ang = rot_at(t)
        sc = 1.0 + 0.03 * ramp(t, 0, FLIP1[0]) + 0.05 * math.exp(-max(0, t - FLIP1[1]) * 5) * (t > FLIP1[1])
        cy = u(900)
        if t_iste - 0.1 < t < t_iste + 0.5:
            sh = u(10) * math.sin((t - t_iste) * 70) * (1 - ramp(t, t_iste, t_iste + 0.5))
        else:
            sh = 0
        place(im, TH_BIG, W / 2 + sh, cy, ang, sc)
        return ("big", ang, sc, cy)
    # iki yüz yan yana: solda normal, sağda Thatcher
    if t < FLIP2[1]:
        k = sm((t - FLIP2[0]) / (FLIP2[1] - FLIP2[0]))
        ang = 180 * k
        a2 = k
    elif t < FLIP3[0]:
        ang, a2 = 180.0, 1.0
    elif t < FLIP3[1]:
        k = sm((t - FLIP3[0]) / (FLIP3[1] - FLIP3[0]))
        ang, a2 = 180 * (1 - k), 1.0
    else:
        ang, a2 = 0.0, 1.0
    cy = u(960)
    place(im, OR_SM, W / 2 - u(255), cy, ang, 1.0, a2)
    place(im, TH_SM, W / 2 + u(255), cy, ang, 1.0, a2)
    return ("two", ang, 1.0, cy)


def ui(L, t, st):
    kind, ang, sc, cy = st
    if t < FLIP1[1]:
        a = 1 - ramp(t, FLIP1[1] - 0.2, FLIP1[1])
        q = 1 + 0.1 * (1 - pop(t, 0.0, 0.28))
        put_word(L, "BU YÜZDE", WHITE, 540, 150, round(92 * q), alpha=a, glow=0.3)
        put_word(L, "TERSLİK VAR MI?", GOLD, 540, 272, round(104 * q), alpha=a, glow=0.45)
        if t >= t_cevir - 0.1:
            chip(L, 660, 1515, "Çeviriyorum…", bg=WHITE, fg=INKC, size=48, icon_name="eye", k="black",
                 alpha=a, scale=pop(t, t_cevir - 0.1, 0.3))
    elif t < t_buna - 0.1:
        a = wnd(t, FLIP1[1], t_buna, 0.1, 0.15)
        q = pop(t, t_iste - 0.05, 0.3)
        put_word(L, "GÖZLER VE AĞIZ", WHITE, 540, 150, max(8, round(86 * q)), alpha=a, glow=0.3)
        put_word(L, "TERS!", RED, 540, 275, max(8, round(130 * q)), alpha=a, glow=0.5)
        rings(L, t, W / 2, cy, BIGW * sc, TH_BIG.height * sc, ang, t_gozler - 0.1)
    elif t < t_ama - 0.1:
        a = wnd(t, t_buna - 0.1, t_ama, 0.2, 0.15)
        q = pop(t, t_buna - 0.1, 0.35)
        panel(L, 540, 220, 820, 240, scale=q, alpha=a, r=40)
        put_word(L, "THATCHER İLLÜZYONU", GOLD, 540, 192, max(8, round(74 * q)), alpha=a, glow=0.45)
        if t >= t_1980 - 0.1:
            txt(L, (540, 282), "Peter Thompson · 1980", round(38 * pop(t, t_1980 - 0.1, 0.3)), WHITE, a, k="xb")
        if t >= t_beynin - 0.1:
            chip(L, 660, 1530, "Beyin yüzü BÜTÜN tanır", bg=WHITE, fg=INKC, size=46, icon_name="thinking_face",
                 k="black", alpha=a, scale=pop(t, t_beynin - 0.1, 0.3))
    elif t < FLIP3[1]:
        a = wnd(t, t_ama - 0.1, FLIP3[1] + 0.05, 0.2, 0.1)
        q = pop(t, t_ama - 0.1, 0.3)
        put_word(L, "TERS YÜZDE", WHITE, 540, 150, max(8, round(86 * q)), alpha=a, glow=0.3)
        put_word(L, "İKİSİ DE NORMAL!", GOLD, 540, 272, max(8, round(96 * q)), alpha=a, glow=0.45)
        if t >= FLIP2[1]:
            for x, lab in ((540 - 255, "1"), (540 + 255, "2")):
                chip(L, x, 1330, lab, bg=WHITE, fg=INKC, size=54, k="black", alpha=a, scale=pop(t, FLIP2[1], 0.3))
        if t >= t_gozler2 - 0.1:
            chip(L, 660, 1530, "Ters yüzde parçalara bakar", bg=WHITE, fg=INKC, size=46, icon_name="eye", k="black",
                 alpha=a, scale=pop(t, t_gozler2 - 0.1, 0.3))
    elif t < t_ustelik - 0.1:
        a = wnd(t, FLIP3[1], t_ustelik, 0.1, 0.15)
        q = pop(t, FLIP3[1], 0.3)
        put_word(L, "ŞİMDİ GÖRDÜN MÜ?", GOLD, 540, 200, max(8, round(98 * q)), alpha=a, glow=0.45)
        rings(L, t, W / 2 + u(255), cy, SMW, TH_SM.height, 0, FLIP3[1] + 0.05)
        put_icon(L, "exploding_head", 540, 1450, 150 * q, alpha=a)
    elif t < t_sen - 0.1:
        a = wnd(t, t_ustelik - 0.1, t_sen, 0.2, 0.15)
        q = pop(t, t_ustelik - 0.1, 0.35)
        panel(L, 540, 220, 860, 220, scale=q, alpha=a, r=40)
        put_word(L, "MAYMUNLARDA BİLE", GOLD, 540, 195, max(8, round(78 * q)), alpha=a, glow=0.45)
        txt(L, (540, 278), "çalışıyor (şempanze ve rhesus)", round(36 * q), WHITE, a, k="xb")
    elif t < t_daha - 0.1:
        a = wnd(t, t_sen - 0.1, t_daha, 0.2, 0.15)
        q = pop(t, t_sen - 0.1, 0.35)
        txt(L, (540, 160), "İLK BAKIŞTA", round(80 * q), WHITE, a, stroke=7)
        txt(L, (540, 272), "FARK ETTİN Mİ?", round(100 * q), GOLD, a, stroke=7)
        if t >= t_yorum - 0.08:
            chip(L, 660, 1530, "Yorumlara yaz", bg=INKC, fg=WHITE, size=56, icon_name="speech_balloon", k="black",
                 alpha=a, scale=pop(t, t_yorum - 0.08, 0.35))
    else:
        S9 = t_daha - 0.1
        a = ramp(t, S9, S9 + 0.25)
        txt(L, (540, 170), "Daha fazlası için", 64, WHITE, a, stroke=6)
        pulse = 1 + 0.045 * math.sin((t - S9) * 8) * ramp(t, S9 + 0.4, S9 + 0.7)
        chip(L, 540, 300, "TAKİP ET", bg=INKC, fg=WHITE, size=90, icon_name="bell", k="black", scale=pop(t, S9, 0.4) * pulse)


class Vid(Video):
    def frame(self, t):
        im = BGIMG.copy()
        st = scene(im, t)
        for c in CUTS:
            if 0 <= t - c < 0.12:
                im.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 255, int(70 * (1 - (t - c) / 0.12)))))
        L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ui(L, t, st)
        im.alpha_composite(L)
        brand(im, 540, 62, size=34)
        C = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        captions(C, self.groups, t, y=1680)
        im.alpha_composite(C)
        i = min(len(OPN) - 1, int(t * FPS))
        ROZ.draw(im, t, float(OPN[i]))
        return im.convert("RGB")


VID = Vid([{"start": 0, "end": TOTAL, "draw": lambda *a: None}], words, "", TOTAL, bg=None)


def make_audio():
    ev = [(FLIP1[0] + 0.15, "whoosh"), (t_iste - 0.05, "pop"), (t_gozler - 0.1, "pop"), (t_gozler + 0.08, "pop"),
          (t_gozler + 0.26, "pop"), (t_buna - 0.1, "ding"), (t_beynin - 0.1, "pop"), (FLIP2[0] + 0.15, "whoosh"),
          (t_gozler2 - 0.1, "pop"), (FLIP3[0] + 0.15, "whoosh"), (FLIP3[1], "ding"), (t_ustelik - 0.1, "pop"),
          (t_yorum - 0.08, "pop"), (t_daha - 0.1, "pop")]
    at.sfx(str(WORK / "sfx.wav"), TOTAL, ev)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-stream_loop", "3", "-i", str(WORK / "muzik.wav"), "-af",
                    f"atrim=0:{TOTAL:.3f},afade=t=in:d=0.15,afade=t=out:st={TOTAL - 0.6:.3f}:d=0.6",
                    "-ar", "44100", "-ac", "1", str(WORK / "music.wav")], check=True)
    at.final_mix(str(VOICE), str(WORK / "music.wav"), str(WORK / "sfx.wav"), str(WORK / "mix.m4a"))


if __name__ == "__main__":
    mode = sys.argv[2] if len(sys.argv) > 2 else "render"
    print("TOTAL", TOTAL, flush=True)
    if mode == "frames":
        (WORK / "test").mkdir(exist_ok=True)
        for tt in [float(x) for x in sys.argv[3].split(",")]:
            VID.frame(tt).save(WORK / "test" / f"fr_{tt:05.2f}.jpg", quality=90)
    elif mode == "ses":
        make_audio()
    else:
        make_audio()
        VID.render(str(WORK / "mix.m4a"), str(WORK / "video.mp4"))
        print("render bitti", TOTAL, flush=True)
