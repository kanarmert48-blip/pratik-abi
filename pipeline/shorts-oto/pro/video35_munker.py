"""35. video (2K, ~29 sn): Bu toplar aynı renk — Munker illüzyonu (renk kıyaslama).
Kullanım: python3 video35_munker.py <WORK> [frames t1,t2,... | ses | render]"""
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


t_inan, t_simdi, t_cizgi, t_gordun, t_hepsi2 = T("İnanmıyorsan"), T("Şimdi"), T("çizgileri"), T("Gördün"), T("Hepsi", 1)
t_cunku, t_kiyas, t_topun, t_rengine = T("Çünkü"), T("kıyaslıyor"), T("Topun"), T("rengine")
t_bu, t_munker, t_sen, t_yorum, t_daha = T("Bu", 1), T("Munker"), T("Sen"), T("Yorumlara"), T("Daha")
S2, S3, S4, S5, S6 = t_simdi - 0.1, t_cunku - 0.1, t_topun - 0.1, t_bu - 0.1, t_sen - 0.1
CUTS = [S3, S4, S5, S6]

GOLD = (255, 204, 70)
INKC = (14, 16, 30)
GRN = (52, 200, 110)


def sm(x):
    return eio(clamp(x))


def ramp(t, a, b):
    return sm((t - a) / max(1e-6, b - a))


def wnd(t, a, b, fi=0.2, fo=0.2):
    return ramp(t, a, a + fi) * (1 - ramp(t, b - fo, b))


# ---------------- illüzyon ----------------
A = np.array([255, 214, 0], np.float32)       # sarı çizgi
B = np.array([40, 90, 255], np.float32)       # mavi çizgi
X = np.array([235, 40, 60], np.float32)       # topların gerçek rengi (ikisi de aynı)
HEX = "#EB283C"
P = 16
Y0, Y1 = int(u(390)), int(u(1450))
BALLS = [(W / 2, u(650), 0), (W / 2, u(1150), 1)]   # (cx, cy, üstteki çizgi paritesi)
R = u(215)
YY, XX = np.mgrid[0:H, 0:W].astype(np.float32)
ROW = ((YY // P) % 2).astype(np.int32)
BASE = np.zeros((H, W, 3), np.float32) + np.array([16, 18, 30], np.float32)
band = (YY >= Y0) & (YY < Y1)
BASE[band & (ROW == 0)] = A
BASE[band & (ROW == 1)] = B
MASKS = [((XX - cx) ** 2 + (YY - cy) ** 2 <= R * R) for cx, cy, _ in BALLS]


def illusion(t):
    img = BASE.copy()
    for k, ((cx, cy, par), m) in enumerate(zip(BALLS, MASKS)):
        # topun altta kalan satırları her zaman X
        img[m & (ROW == par)] = X
        # üstteki çizgiler: kaldırma (soldan sağa silinme) ve geri gelme
        t0 = t_cizgi + 0.15 + 0.45 * k
        rem = ramp(t, t0, t0 + 0.6) * (1 - ramp(t, t_kiyas - 0.2 + 0.25 * k, t_kiyas + 0.4 + 0.25 * k))
        if rem > 0.001:
            edge = cx - R + 2 * R * rem
            sel = m & (ROW != par) & (XX < edge)
            img[sel] = X
    return img


def cam(img, t):
    z = 1.0 + 0.04 * ramp(t, t_inan, S2)
    cx, cy = W / 2, u(900)
    if S4 <= t < S5:   # büyüteç: önce üst top kenarı, sonra alt top
        k1 = ramp(t, S4, S4 + 0.5)
        k2 = ramp(t, t_rengine - 0.35, t_rengine + 0.1)
        z = 1 + 2.2 * k1 * (1 - ramp(t, S5 - 0.35, S5))
        tx1, ty1 = BALLS[0][0] + R * 0.55, BALLS[0][1]
        tx2, ty2 = BALLS[1][0] + R * 0.55, BALLS[1][1]
        cx = W / 2 + (tx1 + (tx2 - tx1) * k2 - W / 2) * k1
        cy = u(900) + (ty1 + (ty2 - ty1) * k2 - u(900)) * k1
    if z <= 1.001:
        return img
    M = np.float32([[z, 0, W / 2 - cx * z], [0, z, u(900) - cy * z]])
    return cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_NEAREST if z > 1.5 else cv2.INTER_LINEAR,
                          borderValue=(16, 18, 30))


ROZ = Rozet()
OPN, RND = konusma(VOICE, FPS)


def swatch(L, x, y, a):
    if a <= 0.01:
        return
    lay = Image.new("RGBA", L.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    d.rounded_rectangle([u(x - 150), u(y - 46), u(x + 150), u(y + 46)], radius=u(46), fill=(255, 255, 255, int(240 * a)))
    d.ellipse([u(x - 132), u(y - 30), u(x - 72), u(y + 30)], fill=tuple(int(v) for v in X) + (int(255 * a),))
    lay2 = Image.new("RGBA", L.size, (0, 0, 0, 0))
    text_c(lay2, (x + 30, y), HEX, "black", 40, INKC, alpha=a)
    L.alpha_composite(lay)
    L.alpha_composite(lay2)


def ui(L, t):
    if t < S3:
        a = 1 - ramp(t, S3 - 0.25, S3)
        p = 1 + 0.1 * (1 - pop(t, 0.0, 0.28))
        if t < t_gordun - 0.1:
            put_word(L, "BU TOPLAR", WHITE, 540, 150, round(86 * p), alpha=a, glow=0.3)
            put_word(L, "AYNI RENK!", GOLD, 540, 275, round(118 * p), alpha=a, glow=0.45)
        if t_inan - 0.1 <= t < S2 + 0.2:
            chip(L, 540, 345, "İnanmıyorsan dikkatle izle", bg=WHITE, fg=INKC, size=44, icon_name="eye", k="black",
                 alpha=1 - ramp(t, S2, S2 + 0.2), scale=pop(t, t_inan - 0.1, 0.3))
        if t >= t_cizgi + 0.2:
            for k, (cx, cy, _) in enumerate(BALLS):
                t0 = t_cizgi + 0.75 + 0.45 * k
                if t >= t0:
                    swatch(L, 860, cy / S, a * ramp(t, t0, t0 + 0.25))
        if t >= t_gordun - 0.1:
            q = pop(t, t_gordun - 0.1, 0.32)
            put_icon(L, "check_mark_button", 540, 140, 130 * q, alpha=a)
            put_word(L, "HEPSİ AYNI RENK", GRN, 540, 275, max(8, round(104 * q)), alpha=a if q > 0.02 else 0, glow=0.5)
    elif t < S4:
        a = wnd(t, S3, S4 + 0.05)
        q = pop(t, S3, 0.3)
        put_word(L, "BEYİN RENGİ", WHITE, 540, 150, max(8, round(86 * q)), alpha=a if q > 0.02 else 0, glow=0.3)
        put_word(L, "KIYASLAYARAK GÖRÜR", GOLD, 540, 275, max(8, round(84 * q)), alpha=a if q > 0.02 else 0, glow=0.45)
    elif t < S5:
        a = wnd(t, S4, S5 + 0.05)
        k2 = t >= t_rengine - 0.2
        chip(L, 540, 170, "MAVİ ÇİZGİ → MOR GÖRÜNÜR" if not k2 else "SARI ÇİZGİ → TURUNCU GÖRÜNÜR", bg=WHITE, fg=INKC,
             size=46, k="black", alpha=a, scale=pop(t, t_rengine - 0.2 if k2 else S4, 0.3))
    elif t < S6:
        a = wnd(t, S5, S6 + 0.05)
        q = pop(t, t_munker - 0.1, 0.35) if t >= t_munker - 0.1 else 0
        if q > 0.02:
            panel(L, 540, 230, 760, 230, scale=q, alpha=a, r=40)
            put_word(L, "MUNKER ETKİSİ", GOLD, 540, 205, max(8, round(84 * q)), alpha=a, glow=0.45)
            txt(L, (540, 290), "İlk kez 1970'te bulundu", round(36 * q), WHITE, a, k="xb")
    elif t < t_daha - 0.1:
        a = wnd(t, S6, t_daha, 0.2, 0.15)
        q = pop(t, S6, 0.35)
        txt(L, (540, 160), "KAÇINCI SANİYEDE", round(78 * q), WHITE, a, stroke=7)
        txt(L, (540, 270), "İNANDIN?", round(110 * q), GOLD, a, stroke=7)
        if t >= t_yorum - 0.08:
            chip(L, 540, 1530, "Yorumlara yaz", bg=INKC, fg=WHITE, size=56, icon_name="speech_balloon", k="black", alpha=a,
                 scale=pop(t, t_yorum - 0.08, 0.35))
    else:
        S9 = t_daha - 0.1
        a = ramp(t, S9, S9 + 0.25)
        txt(L, (540, 170), "Daha fazlası için", 64, WHITE, a, stroke=6)
        pulse = 1 + 0.045 * math.sin((t - S9) * 8) * ramp(t, S9 + 0.4, S9 + 0.7)
        chip(L, 540, 300, "TAKİP ET", bg=INKC, fg=WHITE, size=90, icon_name="bell", k="black", scale=pop(t, S9, 0.4) * pulse)


class Vid(Video):
    def frame(self, t):
        bg = cam(illusion(t), t)
        for c in CUTS:
            if 0 <= t - c < 0.12:
                bg = bg + 90 * (1 - (t - c) / 0.12)
        im = Image.fromarray(np.clip(bg, 0, 255).astype(np.uint8), "RGB").convert("RGBA")
        L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ui(L, t)
        im.alpha_composite(L)
        brand(im, 540, 62, size=34)
        C = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        captions(C, self.groups, t, y=1660)
        im.alpha_composite(C)
        i = min(len(OPN) - 1, int(t * FPS))
        ROZ.draw(im, t, float(OPN[i]))
        return im.convert("RGB")


VID = Vid([{"start": 0, "end": TOTAL, "draw": lambda *a: None}], words, "", TOTAL, bg=None)


def make_audio():
    ev = [(c, "whoosh") for c in CUTS] + [(t_inan - 0.1, "pop"), (t_cizgi + 0.15, "whoosh"), (t_cizgi + 0.75, "pop"),
                                          (t_cizgi + 1.2, "pop"), (t_gordun - 0.1, "ding"), (t_rengine - 0.2, "pop"),
                                          (t_munker - 0.1, "pop"), (t_yorum - 0.08, "pop"), (t_daha - 0.1, "pop")]
    at.sfx(str(WORK / "sfx.wav"), TOTAL, ev)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-stream_loop", "2", "-i", str(WORK / "muzik.wav"), "-af",
                    f"atrim=0:{TOTAL:.3f},afade=t=in:d=0.15,afade=t=out:st={TOTAL - 0.6:.3f}:d=0.6",
                    "-ar", "44100", "-ac", "1", str(WORK / "music.wav")], check=True)
    at.final_mix(str(VOICE), str(WORK / "music.wav"), str(WORK / "sfx.wav"), str(WORK / "mix.m4a"))


if __name__ == "__main__":
    mode = sys.argv[2] if len(sys.argv) > 2 else "render"
    print("TOTAL", TOTAL, "cuts", [round(c, 2) for c in CUTS], flush=True)
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
