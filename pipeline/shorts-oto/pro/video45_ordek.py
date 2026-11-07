"""45. video (2K, ~41 sn): Ördek mi tavşan mı?
Kullanım: python3 video45_ordek.py <WORK> [frames t1,t2,... | ses | render]"""
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
MED = WORK / "med"
VOICE = WORK / "voice_cut.wav"
words = json.loads((WORK / "words.json").read_text(encoding="utf-8"))
TOTAL = round(at.duration(str(VOICE)) + 0.35, 3)


def _hits(key):
    k = trl(clean(key)).strip('"!?;,.…')
    return [w for w in words if trl(clean(w["w"])).strip('"!?;,.…') == k]


def T(key, nth=0):
    return _hits(key)[nth]["s"]


t_ordek, t_tavsan, t_sola, t_gaga, t_ama = T("Ördek"), T("tavşan"), T("Sola"), T("gagası"), T("Ama")
t_saga, t_kulak, t_isin, t_beyin, t_sadece = T("sağa"), T("kulakları"), T("İşin"), T("beynin"), T("Sadece")
t_bu, t_alman, t_arast, t_pask, t_ekim = T("Bu", 1), T("Alman"), T("araştırmada"), T("Paskalya"), T("ekim")
t_yani, t_sen, t_yorum, t_daha = T("Yani"), T("Sen"), T("Yorumlara"), T("Daha", 2)
S2, S3, S4, S5, S6, S7, S8, S9 = (t_sola - 0.1, t_ama - 0.1, t_isin - 0.1, t_bu - 0.1, t_arast - 0.1, t_yani - 0.1,
                                  t_sen - 0.1, t_daha - 0.1)
CUTS = [S2, S3, S4, S5, S6, S7, S8]

GOLD = (255, 204, 70)
CYAN = (80, 200, 255)
INKC = (14, 16, 30)
GRN = (52, 200, 110)


def sm(x):
    return eio(clamp(x))


def ramp(t, a, b):
    return sm((t - a) / max(1e-6, b - a))


def wnd(t, a, b, fi=0.2, fo=0.2):
    return ramp(t, a, a + fi) * (1 - ramp(t, b - fo, b))


class Clip:
    def __init__(self, path, off=0.0):
        self.path, self.off = str(path), off
        self.cap, self.pos, self.last = None, None, None

    def get(self, lt):
        tt = self.off + lt
        if self.cap is None or self.pos is None or tt < self.pos - 0.01 or tt > self.pos + 1.0:
            if self.cap is None:
                self.cap = cv2.VideoCapture(self.path)
            self.cap.set(cv2.CAP_PROP_POS_MSEC, tt * 1000)
            self.pos = tt - 1 / 30
        fps = self.cap.get(cv2.CAP_PROP_FPS) or 30
        while self.pos < tt - 0.5 / fps:
            ok, fr = self.cap.read()
            if not ok:
                self.cap.set(cv2.CAP_PROP_POS_MSEC, 0)
                ok, fr = self.cap.read()
                if not ok:
                    break
            self.last = fr
            self.pos += 1 / fps
        return self.last


def cover_to(fr, w, h, zoom=1.0, fx=0.5, fy=0.5):
    fh, fw = fr.shape[:2]
    s = max(w / fw, h / fh) * zoom
    nw, nh = int(fw * s) + 1, int(fh * s) + 1
    r = cv2.resize(fr, (nw, nh), interpolation=cv2.INTER_AREA if s < 1 else cv2.INTER_LINEAR)
    x0, y0 = int((nw - w) * fx), int((nh - h) * fy)
    return cv2.cvtColor(np.ascontiguousarray(r[y0:y0 + h, x0:x0 + w]), cv2.COLOR_BGR2RGB)


CL_DUCK = Clip(MED / "ekim_2.mp4", 12.0)
CL_RAB = Clip(MED / "tavsan_3.mp4", 3.0)
CL_PASK = Clip(MED / "paskalya_2.mp4", 0.5)
CL_DUCK2 = Clip(MED / "ekim_2.mp4", 30.0)

# arka plan
YY, XX = np.mgrid[0:H, 0:W].astype(np.float32)
_g = (YY / H)[..., None]
DARK = np.array([22, 24, 40], np.float32) * (1 - _g) + np.array([8, 9, 16], np.float32) * _g
DARK = DARK + (40 * np.clip(0.6 - np.sqrt((XX - W / 2) ** 2 + (YY - H * 0.46) ** 2) / H, 0, 1))[..., None]
DARK = DARK.astype(np.float32)
SHADE = (0.55 + 0.45 * np.clip((YY / H - 0.05) / 0.2, 0, 1)) * (1 - 0.5 * np.clip((YY / H - 0.72) / 0.22, 0, 1))
SHADE = SHADE[..., None].astype(np.float32)


def blur_bg(clip, t, t0, dim=0.45):
    fr = clip.get(t - t0)
    if fr is None:
        return DARK.copy()
    small = cover_to(fr, W // 4, H // 4, 1.1)
    small = cv2.GaussianBlur(small, (0, 0), 6)
    return cv2.resize(small, (W, H), interpolation=cv2.INTER_LINEAR).astype(np.float32) * dim


# ördek-tavşan görseli (1920x1920, gri)
DR = cv2.imread(str(MED / "kaninchen_2.jpg"), cv2.IMREAD_GRAYSCALE)
DR = DR[350:1550, :]  # 1920x1200
DR_W, DR_H = 1920, 1200
OLD = cv2.cvtColor(np.asarray(Image.open(MED / "kaninchen_1.png").convert("RGB")), cv2.COLOR_RGB2BGR)

CARD_W = int(u(1000))
CARD_H = int(CARD_W * DR_H / DR_W)
CX, CY = u(540), u(880)


def _rmask(w, h, r):
    im = Image.new("L", (w * 3, h * 3), 0)
    ImageDraw.Draw(im).rounded_rectangle([0, 0, w * 3 - 1, h * 3 - 1], radius=int(r * 3), fill=255)
    return np.asarray(im.resize((w, h), Image.LANCZOS), np.float32)[..., None] / 255


MASK = _rmask(CARD_W, CARD_H, u(40))


def paste(base, img, cx, cy, mask, a=1.0, shadow=True):
    h, w = img.shape[:2]
    x0, y0 = int(cx - w / 2), int(cy - h / 2)
    if shadow:
        sh = cv2.GaussianBlur(mask[..., 0], (0, 0), u(20))
        y1 = y0 + int(u(18))
        base[y1:y1 + h, x0:x0 + w] *= (1 - 0.55 * a * sh[..., None])
    m = mask * a
    reg = base[y0:y0 + h, x0:x0 + w]
    reg *= (1 - m)
    reg += img.astype(np.float32) * m
    return x0, y0


def drawing_card(z, tint=(1.0, 1.0, 1.0)):
    sc = CARD_W / DR_W * z
    M = np.float32([[sc, 0, CARD_W / 2 - DR_W / 2 * sc], [0, sc, CARD_H / 2 - DR_H / 2 * sc]])
    g = cv2.warpAffine(DR, M, (CARD_W, CARD_H), flags=cv2.INTER_AREA, borderValue=255).astype(np.float32)
    paper = np.array([250, 246, 236], np.float32) * np.array(tint, np.float32)
    ink = np.array([18, 18, 22], np.float32)
    k = (g / 255)[..., None]
    return paper * k + ink * (1 - k), sc


def img_pt(x, y, sc, x0, y0):
    """çizim (1920x1200 kırpık) koordinatı -> kare"""
    return (x0 + CARD_W / 2 + (x - DR_W / 2) * sc, y0 + CARD_H / 2 + (y - DR_H / 2) * sc)


BEAK = (395, 670 - 350)   # gaga/kulak merkezi (kırpık koordinat)
MOUTH = (1397, 960 - 350)  # tavşan ağzı


def mode_at(t):
    """'duck' / 'rabbit' / None"""
    if S2 <= t < S3:
        return "duck"
    if S3 <= t < S4:
        return "rabbit"
    if S4 <= t < S5:
        ph = int((t - S4) / 0.9)
        return "duck" if ph % 2 == 0 else "rabbit"
    return None


def scene(t):
    m = mode_at(t)
    # arka plan
    if m == "duck":
        base = blur_bg(CL_DUCK, t, S2)
    elif m == "rabbit":
        base = blur_bg(CL_RAB, t, S3)
    else:
        base = DARK.copy()
    base *= SHADE
    over = []  # (tür, veri)
    if t < S5 or S7 <= t < S9 + 1:
        if t >= S9:
            a = 1 - ramp(t, S9, S9 + 0.3)
        else:
            a = 1.0 if t < S5 - 0.25 or t >= S7 else 1 - ramp(t, S5 - 0.25, S5)
            if S7 <= t < S7 + 0.3:
                a = ramp(t, S7, S7 + 0.3)
        if a > 0.01:
            z = 1.0 + 0.04 * ramp(t, 0, S2) + 0.03 * ramp(t, S7, S9)
            if m == "duck":
                z = 1.04 + 0.02 * ramp(t, S2, S3)
            card, sc = drawing_card(z)
            x0, y0 = paste(base, card, CX, CY, MASK, a)
            over.append(("geo", (sc, x0, y0, a)))
    elif S5 <= t < S6:
        a = wnd(t, S5, S6 + 0.05, 0.3, 0.25)
        w = int(u(880))
        h = int(w * OLD.shape[0] / OLD.shape[1])
        z = 1.0 + 0.05 * ramp(t, S5, S6)
        img = cover_to(OLD, w, h, z).astype(np.float32)
        lum = img.mean(axis=2, keepdims=True)
        img = lum * np.array([1.0, 0.93, 0.8]) * 0.97 + 6
        paste(base, img, CX, u(860), _rmask(w, h, u(30)), a)
    elif S6 <= t < S7:
        cw, ch = int(u(470)), int(u(720))
        mk = _rmask(cw, ch, u(36))
        a1 = ramp(t, t_pask - 0.15, t_pask + 0.2) * (1 - ramp(t, S7 - 0.25, S7))
        a2 = ramp(t, t_ekim - 0.15, t_ekim + 0.2) * (1 - ramp(t, S7 - 0.25, S7))
        if a1 > 0.01:
            fr = CL_PASK.get(t - t_pask)
            if fr is not None:
                paste(base, cover_to(fr, cw, ch, 1.05, 0.5, 0.35), u(285), u(880), mk, a1)
        if a2 > 0.01:
            fr = CL_DUCK2.get(t - t_ekim)
            if fr is not None:
                paste(base, cover_to(fr, cw, ch, 1.1, 0.45, 0.5), u(795), u(880), mk, a2)
    for c in CUTS:
        if 0 <= t - c < 0.1:
            base += 35 * (1 - (t - c) / 0.1)
    return base, over, m


def ring(L, cx, cy, rx, ry, col, a, w=10, ang=-12):
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    for k, (ww, aa) in enumerate([(w * 3.2, 0.25), (w * 1.8, 0.45), (w, 1.0)]):
        d.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], outline=col + (int(255 * a * aa),), width=int(u(ww)))
    lay = lay.rotate(ang, center=(cx, cy), resample=Image.BICUBIC)
    L.alpha_composite(lay)


def arrow_h(L, x, y, direction, col, a, length=150):
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    x0, x1 = u(x), u(x + direction * length)
    yy = u(y)
    d.line([(x0, yy), (x1 - direction * u(30), yy)], fill=col + (int(255 * a),), width=int(u(16)))
    d.polygon([(x1, yy), (x1 - direction * u(48), yy - u(30)), (x1 - direction * u(48), yy + u(30))], fill=col + (int(255 * a),))
    L.alpha_composite(lay)


def two(L, t, a, l1, c1, s1, l2, c2, s2, t0):
    q = pop(t, t0, 0.3)
    if q <= 0.02:
        return
    put_word(L, l1, c1, 540, 165, max(8, round(s1 * q)), alpha=a, glow=0.3)
    if l2:
        put_word(L, l2, c2, 540, 290, max(8, round(s2 * q)), alpha=a, glow=0.45)


def ui(L, t, over, m):
    geo = next((v for k, v in over if k == "geo"), None)
    if t < S2:
        a = 1 - ramp(t, S2 - 0.2, S2)
        p = 1 + 0.1 * (1 - pop(t, 0.0, 0.28))
        put_word(L, "ÖRDEK Mİ?", GOLD, 540, 165, round(118 * p), alpha=a, glow=0.45)
        if t >= t_tavsan - 0.15:
            q = pop(t, t_tavsan - 0.15, 0.3)
            put_word(L, "TAVŞAN MI?", CYAN, 540, 300, max(8, round(118 * q)), alpha=a, glow=0.45)
    elif t < S4:
        duck = t < S3
        a = wnd(t, S2 if duck else S3, (S3 if duck else S4) + 0.05)
        col = GOLD if duck else CYAN
        t0 = S2 if duck else S3
        q = pop(t, t0, 0.3)
        put_word(L, "SOLA BAKAN ÖRDEK" if duck else "SAĞA BAKAN TAVŞAN", col, 540, 200, max(8, round(90 * q)),
                 alpha=a if q > 0.02 else 0, glow=0.45)
        arrow_h(L, 540 + (75 if duck else -75), 330, -1 if duck else 1, col, a * ramp(t, t0 + 0.2, t0 + 0.5))
        th = t_gaga if duck else t_kulak
        if geo and t >= th - 0.15:
            sc, x0, y0, ga = geo
            cx, cy = img_pt(*BEAK, sc, x0, y0)
            k = pop(t, th - 0.15, 0.3)
            ring(L, cx, cy, u(250) * k, u(135) * k, col, a, ang=-12)
            chip(L, 300, 1290, "GAGA" if duck else "KULAKLAR", bg=col, fg=INKC, size=58, k="black", alpha=a,
                 scale=pop(t, th - 0.1, 0.3))
            if not duck:
                mx, my = img_pt(*MOUTH, sc, x0, y0)
                ring(L, mx, my, u(60) * k, u(60) * k, CYAN, a, w=8, ang=0)
                chip(L, 800, 1290, "AĞZI", bg=WHITE, fg=INKC, size=50, k="black", alpha=a, scale=pop(t, th + 0.2, 0.3))
    elif t < S5:
        a = wnd(t, S4, S5 + 0.05)
        if t < t_sadece - 0.1:
            two(L, t, a, "BEYNİN İKİSİNİ", WHITE, 88, "AYNI ANDA GÖREMEZ", GOLD, 96, S4)
        else:
            two(L, t, a, "SADECE BİRİNDEN", WHITE, 86, "DİĞERİNE GEÇER", CYAN, 104, t_sadece - 0.1)
        lab = "ÖRDEK" if m == "duck" else "TAVŞAN"
        col = GOLD if m == "duck" else CYAN
        ph = (t - S4) % 0.9
        chip(L, 540, 1290, lab, bg=col, fg=INKC, size=70, k="black", alpha=a, scale=pop(S4 + ph, S4, 0.25))
    elif t < S6:
        a = wnd(t, S5, S6 + 0.05)
        two(L, t, a, "İLK KEZ", WHITE, 92, "1892'DE YAYINLANDI", GOLD, 82, S5)
        if t >= t_alman - 0.1:
            chip(L, 540, 1390, "Fliegende Blätter · Alman mizah dergisi", bg=WHITE, fg=INKC, size=38, k="black", alpha=a,
                 scale=pop(t, t_alman - 0.1, 0.3))
    elif t < S7:
        a = wnd(t, S6, S7 + 0.05)
        two(L, t, a, "BİR ARAŞTIRMADA", WHITE, 88, "", WHITE, 1, S6)
        if t >= t_pask - 0.1:
            chip(L, 285, 1310, "Paskalya → TAVŞAN", bg=CYAN, fg=INKC, size=40, k="black", alpha=a, scale=pop(t, t_pask - 0.1, 0.3))
        if t >= t_ekim - 0.1:
            chip(L, 795, 1310, "Ekim → ÖRDEK", bg=GOLD, fg=INKC, size=40, k="black", alpha=a, scale=pop(t, t_ekim - 0.1, 0.3))
        chip(L, 540, 300, "Brugger & Brugger, 1993", bg=INKC, fg=WHITE, size=40, k="black", alpha=a, scale=pop(t, S6 + 0.3, 0.3))
    elif t < S8:
        a = wnd(t, S7, S8 + 0.05)
        two(L, t, a, "NE GÖRDÜĞÜN", WHITE, 92, "AKLINDAKİNE BAĞLI", GOLD, 96, S7)
    elif t < S9:
        a = wnd(t, S8, S9 + 0.1, 0.2, 0.15)
        q = pop(t, S8, 0.35)
        txt(L, (540, 165), "SEN İLK", round(92 * q), WHITE, a, stroke=7)
        txt(L, (540, 285), "NE GÖRDÜN?", round(116 * q), GOLD, a, stroke=7)
        if t >= t_yorum - 0.08:
            chip(L, 540, 1290, "Yorumlara yaz", bg=INKC, fg=WHITE, size=56, icon_name="speech_balloon", k="black", alpha=a,
                 scale=pop(t, t_yorum - 0.08, 0.35))
    else:
        a = ramp(t, S9, S9 + 0.25)
        txt(L, (540, 170), "Daha fazlası için", 64, WHITE, a, stroke=6)
        pulse = 1 + 0.045 * math.sin((t - S9) * 8) * ramp(t, S9 + 0.4, S9 + 0.7)
        chip(L, 540, 300, "TAKİP ET", bg=INKC, fg=WHITE, size=90, icon_name="bell", k="black", scale=pop(t, S9, 0.4) * pulse)


ROZ = Rozet()
OPN, RND = konusma(VOICE, FPS)


class Vid(Video):
    def frame(self, t):
        bg, over, m = scene(t)
        im = Image.fromarray(np.clip(bg, 0, 255).astype(np.uint8), "RGB").convert("RGBA")
        L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ui(L, t, over, m)
        im.alpha_composite(L)
        brand(im, 540, 62, size=34)
        C = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        captions(C, self.groups, t, y=1700)
        im.alpha_composite(C)
        i = min(len(OPN) - 1, int(t * FPS))
        ROZ.draw(im, t, float(OPN[i]))
        return im.convert("RGB")


VID = Vid([{"start": 0, "end": TOTAL, "draw": lambda *a: None}], words, "", TOTAL, bg=None)


def make_audio():
    ev = [(c, "whoosh") for c in CUTS] + [(t_tavsan - 0.15, "pop"), (t_gaga - 0.15, "pop"), (t_kulak - 0.15, "pop"),
                                          (t_kulak + 0.2, "pop"), (t_sadece - 0.1, "tink"), (t_alman - 0.1, "pop"),
                                          (t_pask - 0.1, "pop"), (t_ekim - 0.1, "pop"), (t_yorum - 0.08, "pop"), (S9, "pop")]
    ev += [(S4 + 0.9 * k, "tink") for k in range(1, int((S5 - S4) / 0.9))]
    ev = sorted(set((round(a, 3), b) for a, b in ev))
    at.sfx(str(WORK / "sfx.wav"), TOTAL, ev)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-stream_loop", "4", "-i", str(WORK / "muzik.wav"), "-af",
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
