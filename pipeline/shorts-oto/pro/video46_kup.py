"""46. video (2K, ~34 sn): Bu küp hangi yöne bakıyor? — Necker küpü.
Kullanım: python3 video46_kup.py <WORK> [frames t1,t2,... | ses | render]"""
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


t_on, t_sol, t_sag, t_biraz, t_kup = T("Ön"), T("Sol"), T("Sağ"), T("Biraz"), T("Küp")
t_cizgi, t_degisen, t_cunku, t_iki, t_beyin2 = T("Çizgiler"), T("Değişen"), T("Çünkü"), T("iki"), T("beynin", 1)
t_bu, t_louis, t_krist, t_sende, t_yorum, t_daha = T("Bu", 2), T("Louis"), T("kristali"), T("Sende"), T("Yorumlara"), T("Daha", 1)
S2, S3, S4, S5, S6, S7 = t_biraz - 0.1, t_cizgi - 0.1, t_cunku - 0.1, t_bu - 0.1, t_sende - 0.1, t_daha - 0.1
CUTS = [S3, S4, S5, S6]

GOLD = (255, 204, 70)
CYAN = (80, 200, 255)
INKC = (14, 16, 30)
GRN = (52, 200, 110)
WIRE = (235, 240, 255)


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


def cover(fr, zoom=1.0):
    fh, fw = fr.shape[:2]
    s = max(W / fw, H / fh) * zoom
    nw, nh = int(fw * s) + 1, int(fh * s) + 1
    r = cv2.resize(fr, (nw, nh), interpolation=cv2.INTER_LINEAR)
    x0, y0 = (nw - W) // 2, (nh - H) // 2
    return cv2.cvtColor(np.ascontiguousarray(r[y0:y0 + H, x0:x0 + W]), cv2.COLOR_BGR2RGB).astype(np.float32)


CL_KR = Clip(MED / "kristal_1.mp4", 0.5)

YY, XX = np.mgrid[0:H, 0:W].astype(np.float32)
_g = (YY / H)[..., None]
BG = np.array([20, 24, 44], np.float32) * (1 - _g) + np.array([7, 9, 18], np.float32) * _g
BG = (BG + (48 * np.clip(0.6 - np.sqrt((XX - W / 2) ** 2 + (YY - H * 0.46) ** 2) / H, 0, 1))[..., None]
      * np.array([0.65, 0.8, 1.0], np.float32)).astype(np.float32)
SHADE = ((0.5 + 0.5 * np.clip((YY / H - 0.05) / 0.2, 0, 1)) * (1 - 0.5 * np.clip((YY / H - 0.72) / 0.22, 0, 1)))[..., None]


# ---------- küp geometrisi (taban birimleri) ----------
def cube(cx, cy, s, d):
    a0 = np.array([cx - s / 2 - d / 2, cy - s / 2 + d / 2])
    A = [a0, a0 + (s, 0), a0 + (s, s), a0 + (0, s)]          # sol-alt kare
    B = [p + (d, -d) for p in A]                              # sağ-üst kare
    return A, B


def edges(A, B):
    e = [(A[i], A[(i + 1) % 4]) for i in range(4)] + [(B[i], B[(i + 1) % 4]) for i in range(4)]
    e += [(A[i], B[i]) for i in range(4)]
    return e


def hidden_edges(A, B, interp):
    """interp 1: A önde -> B[3] gizli; interp 2: B önde -> A[1] gizli"""
    if interp == 1:
        v = B[3]
        return [(B[2], B[3]), (B[3], B[0]), (A[3], B[3])]
    v = A[1]
    return [(A[0], A[1]), (A[1], A[2]), (A[1], B[1])]


def faces(A, B, interp):
    if interp == 1:
        return [([A[0], A[1], B[1], B[0]], 0.55), ([A[1], A[2], B[2], B[1]], 0.38), (A, 1.0)]
    return [([A[0], A[3], B[3], B[0]], 0.38), ([A[3], A[2], B[2], B[3]], 0.55), (B, 1.0)]


def P(p):
    return (u(p[0]), u(p[1]))


def draw_lines(base, groups, glow=0.9):
    small = np.zeros((H // 4, W // 4, 3), np.float32)
    for segs, col, a, th in groups:
        if a <= 0.01 or not segs:
            continue
        m = np.zeros((H, W), np.uint8)
        ms = np.zeros((H // 4, W // 4), np.uint8)
        for p, q in segs:
            p, q = P(p), P(q)
            cv2.line(m, (int(p[0] * 16), int(p[1] * 16)), (int(q[0] * 16), int(q[1] * 16)), 255, int(th), cv2.LINE_AA, shift=4)
            cv2.line(ms, (int(p[0] * 4), int(p[1] * 4)), (int(q[0] * 4), int(q[1] * 4)), 255, max(1, int(th / 4 * 1.8)),
                     cv2.LINE_AA, shift=4)
        mf = (m.astype(np.float32) / 255 * a)[..., None]
        base *= (1 - mf)
        base += mf * np.array(col, np.float32)
        small += (ms.astype(np.float32) / 255 * a)[..., None] * np.array(col, np.float32)
    small = cv2.GaussianBlur(small, (0, 0), u(10) / 4)
    base += cv2.resize(small, (W, H)) * glow
    return base


def dashed(segs, dash=20, gap=14):
    out = []
    for p, q in segs:
        p, q = np.array(p, float), np.array(q, float)
        L = np.linalg.norm(q - p)
        n = (q - p) / (L + 1e-6)
        s = 0.0
        while s < L:
            out.append((tuple(p + n * s), tuple(p + n * min(L, s + dash))))
            s += dash + gap
    return out


def fill_faces(base, A, B, interp, col, a):
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    for poly, k in faces(A, B, interp):
        c = tuple(int(v * k) for v in col)
        d.polygon([P(p) for p in poly], fill=c + (int(150 * a),))
    arr = np.asarray(lay, np.float32)
    al = arr[..., 3:] / 255
    base *= (1 - al)
    base += arr[..., :3] * al


def interp_at(t):
    """0: düz tel küp; 1/2: yorum"""
    if t_kup - 0.1 <= t < S3:
        return 1 + int((t - (t_kup - 0.1)) / 1.0) % 2
    if S6 <= t < S7:
        return 1 + int((t - S6) / 1.2) % 2
    return 0


MAIN = cube(540, 880, 400, 170)
MINI1 = cube(290, 1240, 200, 85)
MINI2 = cube(790, 1240, 200, 85)


def scene(t):
    if S5 <= t < S6:
        fr = CL_KR.get(t - S5)
        base = cover(fr, 1.05 + 0.05 * ramp(t, S5, S6)) * 0.42 if fr is not None else BG.copy()
    else:
        base = BG.copy()
    base *= SHADE
    groups = []
    A, B = MAIN
    z = 1.0
    if S4 <= t < S5:  # küçük küp yukarı, iki yorum aşağı
        k = ramp(t, S4, S4 + 0.4)
        A2, B2 = cube(540, 880 - 160 * k, 400 - 120 * k, 170 - 51 * k)
        A, B = A2, B2
    wa = 1.0
    if S5 <= t < S6:
        wa = 0.55
    it = interp_at(t)
    hl = None
    if S2 > t >= t_sol - 0.1:
        hl = ("A", GOLD) if t < t_sag - 0.1 else ("B", CYAN)
    if hl:
        sq = A if hl[0] == "A" else B
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(lay).polygon([P(p) for p in sq], fill=hl[1] + (110,))
        arr = np.asarray(lay, np.float32)
        al = arr[..., 3:] / 255
        base = base * (1 - al) + arr[..., :3] * al
    if it:
        col = GOLD if it == 1 else CYAN
        fill_faces(base, A, B, it, col, wa)
        hid = hidden_edges(A, B, it)
        vis = [e for e in edges(A, B) if not any((np.allclose(e[0], h[0]) and np.allclose(e[1], h[1])) for h in hid)]
        groups.append((vis, WIRE, wa, u(11)))
        groups.append((dashed(hid), WIRE, wa * 0.55, u(6)))
    else:
        groups.append((edges(A, B), WIRE, wa, u(11)))
    if S4 <= t < S5:
        k = ramp(t, S4 + 0.3, S4 + 0.7)
        for (a_, b_), it2, col in ((MINI1, 1, GOLD), (MINI2, 2, CYAN)):
            if k > 0.01:
                fill_faces(base, a_, b_, it2, col, k)
                hid = hidden_edges(a_, b_, it2)
                vis = [e for e in edges(a_, b_) if not any((np.allclose(e[0], h[0]) and np.allclose(e[1], h[1])) for h in hid)]
                groups.append((vis, WIRE, k, u(8)))
                groups.append((dashed(hid, 14, 10), WIRE, k * 0.5, u(5)))
    base = draw_lines(base, groups)
    for c in CUTS:
        if 0 <= t - c < 0.1:
            base += 35 * (1 - (t - c) / 0.1)
    return base


def two(L, t, a, l1, c1, s1, l2, c2, s2, t0):
    q = pop(t, t0, 0.3)
    if q <= 0.02:
        return
    put_word(L, l1, c1, 540, 165, max(8, round(s1 * q)), alpha=a, glow=0.3)
    if l2:
        put_word(L, l2, c2, 540, 290, max(8, round(s2 * q)), alpha=a, glow=0.45)


def ui(L, t):
    if t < S2:
        a = 1 - ramp(t, S2 - 0.2, S2)
        p = 1 + 0.1 * (1 - pop(t, 0.0, 0.28))
        if t < t_on - 0.1:
            put_word(L, "BU KÜPE BAK", WHITE, 540, 230, round(110 * p), alpha=a, glow=0.35)
        else:
            two(L, t, a, "ÖN YÜZÜ", WHITE, 100, "HANGİSİ?", GOLD, 130, t_on - 0.1)
        if t >= t_sol - 0.1:
            chip(L, 300, 1290, "Sol alttaki mi?", bg=GOLD, fg=INKC, size=44, k="black", alpha=a, scale=pop(t, t_sol - 0.1, 0.3))
        if t >= t_sag - 0.1:
            chip(L, 790, 1290, "Sağ üstteki mi?", bg=CYAN, fg=INKC, size=44, k="black", alpha=a, scale=pop(t, t_sag - 0.1, 0.3))
    elif t < S3:
        a = wnd(t, S2, S3 + 0.05)
        if t < t_kup - 0.1:
            two(L, t, a, "BAKMAYA", WHITE, 100, "DEVAM ET...", GOLD, 120, S2)
        else:
            two(L, t, a, "KÜP YÖN", WHITE, 100, "DEĞİŞTİRİYOR!", CYAN, 116, t_kup - 0.1)
    elif t < S4:
        a = wnd(t, S3, S4 + 0.05)
        if t < t_degisen - 0.1:
            two(L, t, a, "ÇİZGİLER", WHITE, 100, "HİÇ DEĞİŞMİYOR", GRN, 104, S3)
        else:
            two(L, t, a, "DEĞİŞEN", WHITE, 100, "SENİN BEYNİN", GOLD, 116, t_degisen - 0.1)
    elif t < S5:
        a = wnd(t, S4, S5 + 0.05)
        two(L, t, a, "İKİ FARKLI", WHITE, 100, "3D ŞEKİL", GOLD, 130, S4)
        if t >= S4 + 0.5:
            chip(L, 290, 1460, "1. ihtimal", bg=GOLD, fg=INKC, size=42, k="black", alpha=a, scale=pop(t, S4 + 0.5, 0.3))
            chip(L, 790, 1460, "2. ihtimal", bg=CYAN, fg=INKC, size=42, k="black", alpha=a, scale=pop(t, S4 + 0.7, 0.3))
    elif t < S6:
        a = wnd(t, S5, S6 + 0.05)
        q = pop(t, S5, 0.35)
        panel(L, 540, 225, 900, 250, scale=q, alpha=a, r=40)
        put_word(L, "NECKER KÜPÜ", GOLD, 540, 195, max(8, round(84 * q)), alpha=a, glow=0.45)
        txt(L, (540, 285), "İsviçreli bilim insanı Louis Albert Necker, 1832", round(32 * q), WHITE, a, k="xb")
        if t >= t_krist - 0.1:
            chip(L, 540, 1420, "Bir kristali çizerken fark etti", bg=WHITE, fg=INKC, size=44, k="black", alpha=a,
                 scale=pop(t, t_krist - 0.1, 0.3))
    elif t < S7:
        a = wnd(t, S6, S7 + 0.1, 0.2, 0.15)
        q = pop(t, S6, 0.35)
        txt(L, (540, 165), "SENDE KAÇ", round(92 * q), WHITE, a, stroke=7)
        txt(L, (540, 285), "SANİYEDE DÖNDÜ?", round(100 * q), GOLD, a, stroke=7)
        if t >= t_yorum - 0.08:
            chip(L, 540, 1350, "Yorumlara yaz", bg=INKC, fg=WHITE, size=56, icon_name="speech_balloon", k="black", alpha=a,
                 scale=pop(t, t_yorum - 0.08, 0.35))
    else:
        a = ramp(t, S7, S7 + 0.25)
        txt(L, (540, 170), "Daha fazlası için", 64, WHITE, a, stroke=6)
        pulse = 1 + 0.045 * math.sin((t - S7) * 8) * ramp(t, S7 + 0.4, S7 + 0.7)
        chip(L, 540, 300, "TAKİP ET", bg=INKC, fg=WHITE, size=90, icon_name="bell", k="black", scale=pop(t, S7, 0.4) * pulse)


ROZ = Rozet()
OPN, RND = konusma(VOICE, FPS)


class Vid(Video):
    def frame(self, t):
        bg = scene(t)
        im = Image.fromarray(np.clip(bg, 0, 255).astype(np.uint8), "RGB").convert("RGBA")
        L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ui(L, t)
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
    ev = [(c, "whoosh") for c in CUTS] + [(t_on - 0.1, "pop"), (t_sol - 0.1, "pop"), (t_sag - 0.1, "pop"),
                                          (t_degisen - 0.1, "ding"), (S4 + 0.5, "pop"), (S4 + 0.7, "pop"),
                                          (t_krist - 0.1, "pop"), (t_yorum - 0.08, "pop"), (S7, "pop")]
    k0 = t_kup - 0.1
    ev += [(k0 + k, "tink") for k in range(int(S3 - k0) + 1)]
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
