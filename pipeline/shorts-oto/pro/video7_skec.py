"""7. video: SKEÇ formatı — Pratik Abi & Yenge: çay neden acı? + çamaşır neden kokuyor?
Yeni tarz: ortada yuvarlak köşeli video kartı, altta iki karakterli konuşma balonları."""
import json, math, subprocess, sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from engine import *  # noqa
from widgets import *  # noqa
import audio_tools as at

WORK = Path(sys.argv[1])
N = Path("/home/claude/pratik-abi/media/v7-cay-camasir")
GIRIS = "/mnt/user-data/uploads/CLAUDE DOWNLOAD/giris.mp4"
words = json.loads((WORK / "words.json").read_text(encoding="utf-8"))
TOTAL = at.duration(str(WORK / "voice_cut.wav"))
OUTRO = 1.9
OS = TOTAL - OUTRO
PINK = (236, 72, 153)
BLUE = (37, 99, 235)
CX0, CY0, CW, CH = 40, 330, 1000, 562  # video kartı


def T(key, clip=None, nth=0):
    k = trl(clean(key)).strip('"!?;')
    hits = [w for w in words if trl(clean(w["w"])).strip('"!?;') == k and (clip is None or w["clip"] == clip)]
    return hits[nth]["s"]


def C(clip):
    return [w for w in words if w["clip"] == clip][0]["s"]


A1, W2, A2, W3, A3, A4 = C("a1"), C("w2"), C("a2"), C("w3"), C("a3"), C("a4")
t_su, t_kirec, t_cayin = T("şu", "a1"), T("kireç", "a1"), T("çayın", "a1")
t_cdl, t_iki, t_kay, t_yar = T("çaydanlığı", "a1"), T("iki", "a1"), T("kaynat", "a1"), T("yarım", "a1")
t_pir, t_bua = T("pırıl", "a1"), T("bu", "a1", 1)
t_kok = T("kokuyor", "w2")
t_kap, t_iste, t_lst = T("kapağın", "a2"), T("işte", "a2"), T("lastiği", "a2")
t_det, t_son, t_ara, t_yik, t_koku = (T("deterjan", "a2"), T("sonra", "a2"), T("aramızda", "a2"), T("yıkamadan", "a2"),
                                      T("koku", "a2"))
t_prt = T("pratik", "a3")
t_kir4, t_kok4, t_yor, t_beg = T("kireç", "a4"), T("koku", "a4"), T("yorumlara", "a4"), T("beğenmeyi", "a4")

cuts = [0, A1, t_su, t_cayin, t_cdl, t_iki, t_kay, t_yar, t_pir, t_bua, W2, A2, t_iste, t_lst, t_det, t_son, t_ara,
        t_koku, W3, A4, OS]
cuts = [max(0, c - 0.15) if i else 0 for i, c in enumerate(cuts)]
CLIPS = [("cay-bardak_2.mp4", 2), ("cay-dok_2.mp4", 6), ("cay-bardak_3.mp4", 3), ("cay-dok_3.mp4", 2),
         ("su-doldur_1.mp4", 0), ("limon_2.mp4", 5), ("cay-bardak_3.mp4", 30), ("caydanlik_4.mp4", 10),
         ("cay-dok_1.mp4", 20), ("cay-bardak_1.mp4", 8), ("makine_1.mp4", 0), ("makine_4.mp4", 2),
         ("makine_4.mp4", 10), ("silme_1.mp4", 5), ("makine_2.mp4", 0), ("makine_2.mp4", 6), ("makine_1.mp4", 2),
         ("camasir_2.mp4", 3), ("cay-dok_1.mp4", 5), ("camasir_4.mp4", 0)]
SEGS = [dict(src=str(N / f), ss=ss, dur=cuts[i + 1] - cuts[i]) for i, (f, ss) in enumerate(CLIPS)]

# ---------- kart arka planı ----------
BW0, BH0 = 1100, 618


def build_card_track(segs, out):
    import os, tempfile
    tmp = tempfile.mkdtemp()
    parts = []
    for i, s in enumerate(segs):
        assert s["dur"] > 0, (i, s)
        p = os.path.join(tmp, f"s{i}.mp4")
        vf = (f"scale={BW0}:{BH0}:force_original_aspect_ratio=increase:flags=lanczos,crop={BW0}:{BH0},fps={FPS},"
              f"eq=contrast=1.05:saturation=1.12,unsharp=5:5:0.4,setsar=1,format=yuv420p")
        dur_src = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                        s["src"]], capture_output=True, text=True).stdout or 0)
        ss = s["ss"] if dur_src - s["ss"] >= s["dur"] + 0.1 else 0
        inp = ["-ss", f"{ss:.3f}", "-i", s["src"]] if dur_src - ss >= s["dur"] + 0.1 else ["-stream_loop", "-1", "-i",
                                                                                            s["src"]]
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *inp, "-vf", vf, "-an", "-frames:v",
                        str(int(round(s["dur"] * FPS))), "-c:v", "libx264", "-preset", "veryfast", "-crf", "14", p],
                       check=True)
        parts.append(p)
    lst = os.path.join(tmp, "l.txt")
    open(lst, "w").write("".join(f"file '{p}'\n" for p in parts))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", out],
                   check=True)


def _mask(w, h, r):
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, w - 1, h - 1], radius=r, fill=255)
    return m


class CardBG:
    def __init__(self, track, outro):
        self.track, self.outro = track, outro
        self.p, self.nt = None, None
        self.po, self.nto = None, None
        self.mask = _mask(CW, CH, 38)
        self.shadow = soft_shadow(CW, CH, 38, blur=30, op=0.55)
        g = np.zeros((H, W, 4), np.uint8)
        y = np.arange(H)[:, None]
        g[..., :3] = (8, 11, 24)
        g[..., 3] = np.clip(150 + 60 * np.abs(y - 900) / 1000, 0, 230).astype(np.uint8)
        self.dark = Image.fromarray(g, "RGBA")
        self.starts = [sum(s["dur"] for s in SEGS[:i]) for i in range(len(SEGS) + 1)]

    def _pipe(self, path, t, size):
        return subprocess.Popen(["ffmpeg", "-loglevel", "error", "-ss", f"{t:.4f}", "-i", path, "-vf",
                                 f"scale={size[0]}:{size[1]}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                                stdout=subprocess.PIPE)

    def _read(self, t):
        if self.p is None or abs(t - self.nt) > 0.5 / FPS:
            if self.p:
                self.p.kill()
            self.p = self._pipe(self.track, t, (BW0, BH0))
        buf = self.p.stdout.read(BW0 * BH0 * 3)
        self.nt = t + 1 / FPS
        if len(buf) < BW0 * BH0 * 3:
            return Image.new("RGB", (BW0, BH0), (20, 20, 30))
        return Image.frombuffer("RGB", (BW0, BH0), buf, "raw", "RGB", 0, 1)

    def _read_outro(self, lt):
        if self.po is None or abs(lt - self.nto) > 0.5 / FPS:
            if self.po:
                self.po.kill()
            self.po = self._pipe(self.outro, lt, (W, H))
        buf = self.po.stdout.read(W * H * 3)
        self.nto = lt + 1 / FPS
        if len(buf) < W * H * 3:
            return Image.new("RGB", (W, H), (0, 0, 0))
        return Image.frombuffer("RGB", (W, H), buf, "raw", "RGB", 0, 1)

    def frame(self, t):
        if t >= OS:
            return self._read_outro(t - OS).convert("RGBA")
        src = self._read(t)
        i = max(k for k in range(len(SEGS)) if self.starts[k] <= t + 1e-6) if t > 0 else 0
        i = min(i, len(SEGS) - 1)
        p = (t - self.starts[i]) / max(SEGS[i]["dur"], 0.01)
        d = 1 if i % 2 == 0 else -1
        ox = (BW0 - CW) / 2 + d * (p - 0.5) * (BW0 - CW) * 0.9
        oy = (BH0 - CH) / 2
        cardim = src.crop((int(ox), int(oy), int(ox) + CW, int(oy) + CH))
        cw9 = int(BH0 * 9 / 16)
        bg = src.crop(((BW0 - cw9) // 2, 0, (BW0 + cw9) // 2, BH0)).resize((18, 32), Image.BOX)
        bg = bg.resize((W, H), Image.BICUBIC).convert("RGBA")
        bg.alpha_composite(self.dark)
        sh, pad = self.shadow
        comp(bg, sh, CX0 - pad, CY0 - pad + 20)
        card_rgba = cardim.convert("RGBA")
        card_rgba.putalpha(self.mask)
        bg.alpha_composite(card_rgba, (CX0, CY0))
        ImageDraw.Draw(bg).rounded_rectangle([CX0 - 3, CY0 - 3, CX0 + CW + 2, CY0 + CH + 2], radius=40,
                                             outline=(255, 255, 255, 230), width=5)
        if i > 0 and t - self.starts[i] < 0.12:  # kart içi hızlı parlama
            fl = Image.new("RGBA", (CW, CH), (255, 255, 255, int(120 * (1 - (t - self.starts[i]) / 0.12))))
            fl.putalpha(Image.eval(self.mask, lambda v: int(v * (1 - (t - self.starts[i]) / 0.12) * 0.45)))
            bg.alpha_composite(fl, (CX0, CY0))
        return bg

    def finish(self, im, t):
        return im


# ---------- karakterler ----------
AV_R = 104
POS = {"Y": (190, 1400), "A": (850, 1400)}


def _circle(im, r, ring, ring_w=8):
    S = 2 * r
    im = im.resize((S, S), Image.LANCZOS).convert("RGBA")
    m = Image.new("L", (S * 4, S * 4), 0)
    ImageDraw.Draw(m).ellipse([0, 0, S * 4 - 1, S * 4 - 1], fill=255)
    im.putalpha(m.resize((S, S), Image.LANCZOS))
    out = Image.new("RGBA", (S + 2 * ring_w, S + 2 * ring_w), (0, 0, 0, 0))
    ImageDraw.Draw(out).ellipse([0, 0, out.width - 1, out.height - 1], fill=ring + (255,))
    out.alpha_composite(im, (ring_w, ring_w))
    return out


def _abi(t_frame):
    p = WORK / f"abi_{t_frame}.png"
    if not p.exists():
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", str(t_frame), "-i", GIRIS, "-frames:v", "1",
                        str(p)], check=True)
    return Image.open(p).convert("RGB").crop((145, 5, 435, 295))


def _yenge():
    base = Image.new("RGBA", (400, 400), (0, 0, 0, 0))
    d = ImageDraw.Draw(base)
    for k in range(200):  # yumuşak pembe degrade
        c = tuple(int(lerp(a, b, k / 200)) for a, b in zip((255, 214, 232), (249, 168, 212)))
        d.ellipse([k, k, 400 - k, 400 - k], fill=c + (255,))
    w = Image.open(ASSETS / "woman_3d.png").convert("RGBA").resize((330, 330), Image.LANCZOS)
    base.alpha_composite(w, (35, 60))
    return base


AV = {}


def avatar_img(sp, mood="open", ring=WHITE):
    key = (sp, mood, ring)
    if key not in AV:
        src = _yenge() if sp == "Y" else _abi(1.5 if mood == "laugh" else 0.2)
        AV[key] = _circle(src, AV_R, ring)
    return AV[key]


# ses seviyesi (konuşurken avatar hafifçe büyür)
def _env():
    r = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(WORK / "voice_cut.wav"), "-f", "s16le", "-ac", "1",
                        "-ar", "16000", "-"], capture_output=True, check=True)
    x = np.frombuffer(r.stdout, "<i2").astype(float) / 32768
    hop = 16000 // FPS
    e = np.array([np.sqrt(np.mean(x[i:i + hop] ** 2)) for i in range(0, len(x), hop)])
    e = e / (np.percentile(e, 95) + 1e-9)
    e = np.convolve(np.clip(e, 0, 1.2), np.ones(3) / 3, mode="same")
    return e


ENV = _env()
GROUPS = caption_groups(words, max_words=7, max_chars=34, gap=0.3)


def current_group(t):
    cur = None
    for k, (st, en, g) in enumerate(GROUPS):
        if st <= t:
            cur = k
    if cur is None:
        return None, None
    st, en, g = GROUPS[cur]
    nxt = GROUPS[cur + 1][0] if cur + 1 < len(GROUPS) else 1e9
    if t < max(en, min(g[-1]["e"] + 0.7, nxt)):
        return cur, GROUPS[cur]
    return None, None


def run_start(k):
    """Bu konuşma balonu dizisinin (aynı konuşmacı) başladığı an."""
    while k > 0 and GROUPS[k - 1][2][0]["sp"] == GROUPS[k][2][0]["sp"] and \
            GROUPS[k][0] - GROUPS[k - 1][2][-1]["e"] < 1.0:
        k -= 1
    return GROUPS[k][0]


def wrap(d, texts, f, maxw):
    lines, cur = [], []
    sp = d.textlength(" ", font=f)
    for i, tx in enumerate(texts):
        test = cur + [i]
        wdt = sum(d.textlength(texts[j], font=f) for j in test) + sp * (len(test) - 1)
        if cur and wdt > maxw:
            lines.append(cur)
            cur = [i]
        else:
            cur = test
    if cur:
        lines.append(cur)
    return lines


def bubble(im, t):
    k, grp = current_group(t)
    if grp is None:
        return None
    st, en, g = grp
    spk = g[0]["sp"]
    texts = [clean(w["w"]) for w in g]
    d = ImageDraw.Draw(im)
    for fs in range(60, 40, -4):
        f = font("black", fs)
        lines = wrap(d, texts, f, 840)
        if len(lines) <= 2:
            break
    lh = int(fs * 1.22)
    spw = d.textlength(" ", font=f)
    lw = [sum(d.textlength(texts[j], font=f) for j in ln) + spw * (len(ln) - 1) for ln in lines]
    bw = int(max(lw) + 2 * 46)
    bw = max(bw, 300)
    bh = int(len(lines) * lh + 2 * 30)
    ax, ay = POS[spk]
    x0 = 52 if spk == "Y" else W - 52 - bw
    y1 = ay - AV_R - 46
    y0 = y1 - bh
    fill = WHITE if spk == "Y" else ACC
    hi = PINK if spk == "Y" else BLUE
    S = bw + 80, bh + 120
    tmp = Image.new("RGBA", S, (0, 0, 0, 0))
    sh, pad = soft_shadow(bw, bh, 40, blur=16, op=0.4)
    comp(tmp, sh, 40 - pad, 40 - pad + 10)
    td = ImageDraw.Draw(tmp)
    td.rounded_rectangle([40, 40, 40 + bw, 40 + bh], radius=40, fill=fill + (255,))
    tx = ax - x0 + 40  # kuyruk avatarın üstüne
    tx = min(max(tx, 40 + 60), 40 + bw - 60)
    td.polygon([(tx - 30, 40 + bh - 2), (tx + 30, 40 + bh - 2), (tx + (-12 if spk == "Y" else 12), 40 + bh + 40)],
               fill=fill + (255,))
    yy = 40 + 30
    for li, ln in enumerate(lines):
        xx = 40 + (bw - lw[li]) / 2
        for j in ln:
            w = g[j]
            active = w["s"] - 0.04 <= t < w["e"] + 0.05
            done = t >= w["e"]
            col = hi + (255,) if active else (INK + (255,) if done else INK + (95,))
            td.text((xx, yy + (-4 if active else 0)), texts[j], font=f, fill=col)
            xx += td.textlength(texts[j], font=f) + spw
        yy += lh
    p = eb(ph(t, run_start(k) - 0.02, 0.32))
    q = eo(ph(t, st - 0.02, 0.14))
    sc = (0.55 + 0.45 * p) * (0.97 + 0.03 * q)
    if abs(sc - 1) > 0.005:
        ox, oy = (tx, 40 + bh + 40)  # kuyruk ucundan büyü
        nw, nh = max(1, int(S[0] * sc)), max(1, int(S[1] * sc))
        tmp = tmp.resize((nw, nh), Image.BICUBIC)
        comp(im, set_alpha(tmp, min(1, p * 1.5)), x0 - 40 + ox - ox * sc, y0 - 40 + oy - oy * sc)
    else:
        comp(im, tmp, x0 - 40, y0 - 40)
    return spk if st <= t <= g[-1]["e"] + 0.1 else None


def avatars(im, t, speaking):
    lvl = float(ENV[min(len(ENV) - 1, int(t * FPS))])
    for spk in ("Y", "A"):
        cx, cy = POS[spk]
        talk = speaking == spk
        mood = "laugh" if (spk == "A" and A3 - 0.1 <= t < t_prt) else "open"
        if spk == "A" and not talk and (t % 4.3) < 0.12:
            mood = "laugh"  # göz kırpma
        ring = (PINK if spk == "Y" else ACC) if talk else WHITE
        img = avatar_img(spk, mood, ring)
        s = (1.0 + 0.07 * lvl) if talk else 0.88
        if spk == "Y" and talk:
            s *= 1 + 0.02 * math.sin(t * 9)
        im2 = img.resize((int(img.width * s), int(img.height * s)), Image.BICUBIC)
        sh, pad = soft_shadow(im2.width, im2.height, im2.width // 2, blur=16, op=0.45)
        comp(im, sh, cx - im2.width / 2 - pad, cy - im2.height / 2 - pad + 12)
        comp(im, im2 if talk else set_alpha(im2, 0.92), cx - im2.width / 2, cy - im2.height / 2)
        if talk:  # ses dalgaları
            d = ImageDraw.Draw(im)
            side = 1 if spk == "Y" else -1
            for k in range(2):
                rr = AV_R + 26 + k * 22 + 10 * lvl
                a0 = -35 if side == 1 else 145
                d.arc([cx - rr, cy - rr, cx + rr, cy + rr], a0, a0 + 70, fill=ring + (int(220 - 80 * k),), width=7)
        name, bg, fg = ("Yenge", PINK, WHITE) if spk == "Y" else ("Pratik Abi", ACC, INK)
        chip(im, cx, cy + AV_R + 40, name, bg=bg, fg=fg, size=30, k="black", scale=0.95)


# ---------- sahne parçaları ----------
def card_pt(fx, fy):
    return CX0 + CW * fx, CY0 + CH * fy


def steps(L, t, items, y=950):
    act = -1
    for i, (st, ic, tx) in enumerate(items):
        if t >= st:
            act = i
    if act < 0:
        return
    st, ic, tx = items[act]
    chip(L, W / 2, y, f"{act + 1}. {tx}", bg=WHITE, fg=INK, size=44, icon_name=ic, k="black", scale=eb(ph(t, st, 0.35)))
    n = len(items)
    for i in range(n):  # ilerleme noktaları
        x = W / 2 + (i - (n - 1) / 2) * 34
        d = ImageDraw.Draw(L)
        r = 9 if i == act else 6
        col = ACC if i <= act else (255, 255, 255)
        d.ellipse([x - r, y + 62 - r, x + r, y + 62 + r], fill=col + (255 if i <= act else 120,))


def magnifier(L, t, start, end, x0, x1, y):
    if not (start <= t < end):
        return
    p = eio(ph(t, start, max(0.4, end - start - 0.2)))
    put_icon(L, "magnifying_glass_tilted_right", lerp(x0, x1, p), y + 12 * math.sin(t * 5), 200 * eb(ph(t, start, 0.35)),
             rot=-10)


def ring_mark(L, t, start, cx, cy, r):
    p = eo(ph(t, start, 0.45))
    if p <= 0:
        return
    d = ImageDraw.Draw(L)
    rr = r * (1 + 0.06 * math.sin(t * 7))
    d.arc([cx - rr, cy - rr * 0.8, cx + rr, cy + rr * 0.8], -90, -90 + 360 * p, fill=RED + (255,), width=12)


# 0: kanca
def s_hook(v, sc, L, t, dur):
    headline(L, [("Çay neden", False), ("acı?", True)], t, y0=212, size=78, start=-1)
    ta = T("acı", "w1") - sc["start"]
    put_icon(L, "face_with_steam_from_nose", *card_pt(0.86, 0.2), 200 * eb(ph(t, ta, 0.4)), rot=10 * math.sin(t * 6))
    put_icon(L, "hot_beverage", *card_pt(0.13, 0.78), 150 * eb(ph(t, 0.2, 0.4)), rot=-8)


# 1: kireç
def s_kirec(v, sc, L, t, dur):
    s0 = sc["start"]
    headline(L, [("Suç", False), ("çaydanlıkta!", True)], t, y0=212, size=78)
    magnifier(L, t, t_su - s0, t_kirec - s0, CX0 + 150, CX0 + 520, CY0 + 330)
    if t_kirec - s0 <= t < t_cayin - s0 - 0.1:
        ring_mark(L, t, t_kirec - s0, *card_pt(0.5, 0.75), 190)
        stamp(L, *card_pt(0.5, 0.3), "KİREÇ!", RED, t, t_kirec - s0, rot=-8, size=100)
    q = ph(t, t_cayin - s0, 0.35)
    if q > 0:
        chip(L, W / 2, 950, "Tadı bozan bu!", bg=RED, fg=WHITE, size=46, icon_name="warning", k="black", scale=eb(q))


# 2: çözüm (çay)
def s_cay(v, sc, L, t, dur):
    s0 = sc["start"]
    headline(L, [("Kireç", False), ("nasıl gider?", True)], t, y0=212, size=78)
    if t < t_bua - s0 - 0.1:
        steps(L, t, [(0.05, "droplet", "Yarıya kadar su"), (t_iki - s0, "lemon", "2 kaşık limon tuzu"),
                     (t_kay - s0, "fire", "Kaynat"), (t_yar - s0, "stopwatch", "30 dk bekle, durula")])
    tl = t_iki - s0
    if tl <= t < t_kay - s0:
        put_icon(L, "lemon", *card_pt(0.85, 0.25), 190 * eb(ph(t, tl, 0.4)), rot=12 * math.sin(t * 3))
        put_icon(L, "salt", *card_pt(0.15, 0.3), 150 * eb(ph(t, tl + 0.3, 0.4)), rot=-10)
    if t_kay - s0 <= t < t_yar - s0:
        put_icon(L, "fire", *card_pt(0.86, 0.72), 170 * eb(ph(t, t_kay - s0, 0.4)) * (1 + 0.05 * math.sin(t * 14)))
    tp = t_pir - s0
    if tp <= t < t_bua - s0:
        for k, (fx, fy) in enumerate([(0.2, 0.25), (0.78, 0.35), (0.55, 0.7)]):
            put_icon(L, "sparkles", *card_pt(fx, fy), (130 + 30 * math.sin(t * 8 + k)) * eb(ph(t, tp + k * 0.12, 0.35)))
        stamp(L, *card_pt(0.5, 0.5), "PIRIL PIRIL", GREEN, t, tp, rot=-6, size=84)
    tb = t_bua - s0
    q = ph(t, tb, 0.4)
    if q > 0:
        chip(L, W / 2, 950, "Ayda 1 kez yap", bg=ACC, fg=INK, size=48, icon_name="spiral_calendar", k="black",
             scale=eb(q))


# 3: çamaşır sorusu
def s_kokuq(v, sc, L, t, dur):
    s0 = sc["start"]
    headline(L, [("Çamaşır neden", False), ("kokuyor?", True)], t, y0=212, size=78)
    put_icon(L, "t_shirt", *card_pt(0.14, 0.25), 160 * eb(ph(t, 0.3, 0.4)), rot=-12)
    tk = t_kok - s0
    put_icon(L, "nauseated_face", *card_pt(0.85, 0.24), 200 * eb(ph(t, tk, 0.4)), rot=8 * math.sin(t * 5))


# 4: kaynak
def s_kaynak(v, sc, L, t, dur):
    s0 = sc["start"]
    headline(L, [("Kokunun", False), ("kaynağı", True)], t, y0=212, size=78)
    magnifier(L, t, t_kap - s0, t_iste - s0, CX0 + 200, CX0 + 560, CY0 + 300)
    ti = t_iste - s0
    if t >= ti:
        ring_mark(L, t, ti, *card_pt(0.5, 0.5), 230)
        stamp(L, *card_pt(0.5, 0.86), "KOKU BURADA!", RED, t, ti, rot=-6, size=80)
        put_icon(L, "nauseated_face", *card_pt(0.88, 0.2), 160 * eb(ph(t, ti + 0.2, 0.4)))


# 5: çözüm (çamaşır)
def s_camasir(v, sc, L, t, dur):
    s0 = sc["start"]
    headline(L, [("Kokuya", False), ("son!", True)], t, y0=212, size=78)
    steps(L, t, [(0.05, "sponge", "Lastiği bezle sil"), (t_det - s0, "soap", "Çekmeceyi yıka"),
                 (t_son - s0, "thermometer", "Sirke + 60° boş yıkama"), (t_yik - s0, "door", "Kapağı açık bırak")])
    ta = t_ara - s0
    if ta <= t < t_koku - s0:
        put_icon(L, "shushing_face", *card_pt(0.14, 0.24), 190 * eb(ph(t, ta, 0.4)), rot=-8 + 6 * math.sin(t * 3))
    tk = t_koku - s0
    if t >= tk:
        for k, (fx, fy) in enumerate([(0.18, 0.22), (0.82, 0.3), (0.5, 0.75)]):
            put_icon(L, "sparkles", *card_pt(fx, fy), (130 + 30 * math.sin(t * 8 + k)) * eb(ph(t, tk + k * 0.12, 0.35)))
        stamp(L, *card_pt(0.5, 0.5), "MİS GİBİ!", GREEN, t, tk + 0.3, rot=-6, size=90)


# 6: kapanış
def s_end(v, sc, L, t, dur):
    s0 = sc["start"]
    if t >= dur - OUTRO:
        lt = t - (dur - OUTRO)
        chip(L, 540, 1560, "Takip et, kaçırma!", bg=RED, fg=WHITE, size=50, icon_name="bell", k="black",
             scale=eb(ph(lt, 0.25, 0.4)))
        return
    a3, a4 = A3 - s0, A4 - s0
    if t < a4:
        headline(L, [("Nereden", False), ("biliyor?", True)], t, y0=212, size=78)
        put_icon(L, "face_with_monocle", *card_pt(0.15, 0.25), 180 * eb(ph(t, 0.3, 0.4)), rot=-6)
        q = ph(t, a3 + 0.1, 0.45)
        if q > 0:  # Pratik Abi büyük
            big = avatar_img("A", "laugh" if t < t_prt - s0 else "open", ACC)
            s = 1.55 * eb(q)
            im2 = big.resize((max(1, int(big.width * s)), max(1, int(big.height * s))), Image.BICUBIC)
            cx, cy = card_pt(0.5, 0.5)
            comp(L, im2, cx - im2.width / 2, cy - im2.height / 2)
            put_icon(L, "smiling_face_with_sunglasses", cx + 170, cy - 150, 150 * eb(ph(t, t_prt - s0, 0.4)), rot=12)
            chip(L, W / 2, 950, "Pratik Abi bilir!", bg=ACC, fg=INK, size=48, icon_name="crown", k="black",
                 scale=eb(ph(t, t_prt - s0, 0.4)))
    else:
        headline(L, [("Sende", False), ("hangisi?", True)], t, y0=212, size=78)
        tb = t_beg - s0
        fade = 1 - ph(t, tb - 0.1, 0.3)
        if fade > 0:
            glass(L, CX0 + 30, CY0 + 30, CW - 60, CH - 60, alpha=fade * eo(ph(t, a4, 0.3)))
            for i, (lab, ic, tt) in enumerate([("KİREÇ", "teapot", t_kir4 - s0), ("KOKU", "nauseated_face", t_kok4 - s0)]):
                cx = CX0 + CW * (0.28 + 0.44 * i)
                cy = CY0 + CH / 2
                pp = eb(ph(t, a4 + 0.15 + i * 0.15, 0.4))
                hl = ph(t, tt, 0.25) * (1 - ph(t, tt + 0.9, 0.3))
                s = pp * (1 + 0.12 * hl)
                card(L, cx - 190 * s, cy - 160 * s, 380 * s, 320 * s, r=40,
                     fill=(ACC if i == 0 else PINK) + (255,), alpha=fade)
                put_icon(L, ic, cx, cy - 40 * s, 150 * s, alpha=fade)
                text_c(L, (cx, cy + 95 * s), lab, "black", max(8, int(64 * s)), INK if i == 0 else WHITE, alpha=fade)
        q = ph(t, t_yor - s0, 0.4)
        if q > 0:
            chip(L, W / 2, 950, "Yorumlara yaz!", bg=WHITE, fg=INK, size=48, icon_name="speech_balloon", k="black",
                 scale=eb(q))
        q2 = ph(t, tb, 0.45)
        if q2 > 0:
            cy = CY0 + CH / 2
            put_icon(L, "thumbs_up", CX0 + CW * 0.3, cy - 30 + 8 * math.sin(t * 2.4), 220 * eb(q2), rot=-8)
            chip(L, CX0 + CW * 0.3, cy + 140, "Beğen", bg=ACC, fg=INK, size=42, k="black", scale=eb(ph(t, tb + 0.1, 0.4)))
            tb2 = tb + 0.45
            put_icon(L, "bell", CX0 + CW * 0.7, cy - 30, 220 * eb(ph(t, tb2, 0.45)),
                     rot=14 * math.sin(t * 9) * (1 - ph(t, tb2 + 1.0, 0.8)))
            chip(L, CX0 + CW * 0.7, cy + 140, "Takip et", bg=RED, fg=WHITE, size=42, k="black",
                 scale=eb(ph(t, tb2 + 0.15, 0.4)))


starts = [0.0, A1, t_cdl - 0.1, W2, A2, t_lst - 0.1, W3]
draws = [s_hook, s_kirec, s_cay, s_kokuq, s_kaynak, s_camasir, s_end]
scenes = [{"start": s, "end": (starts[i + 1] if i + 1 < len(starts) else TOTAL), "draw": d}
          for i, (s, d) in enumerate(zip(starts, draws))]


class Skec(Video):
    def frame(self, t):
        im = self.bg.frame(t)
        for i, sc in enumerate(self.scenes):
            if sc["start"] <= t < sc["end"] or (i == len(self.scenes) - 1 and t >= sc["start"]):
                lt, dur = t - sc["start"], sc["end"] - sc["start"]
                layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                sc["draw"](self, sc, layer, lt, dur)
                pin = 1.0 if i == 0 else eo(ph(lt, 0, 0.3))
                pout = eio(ph(lt, dur - 0.2, 0.2)) if i < len(self.scenes) - 1 else 0
                a = pin * (1 - pout)
                if a < 0.999:
                    layer = set_alpha(layer, a)
                comp(im, layer, (1 - pin) * 120 - pout * 120, 0)
                break
        brand(im, W / 2, 150)
        if t < OS:
            spk = bubble(im, t)
            avatars(im, t, spk)
        return im.convert("RGB")


if __name__ == "__main__":
    mode = sys.argv[2] if len(sys.argv) > 2 else "render"
    if not (WORK / "card.mp4").exists():
        build_card_track(SEGS, str(WORK / "card.mp4"))
    bg = CardBG(str(WORK / "card.mp4"), str(WORK / "outro.mp4"))
    v = Skec(scenes, words, "", TOTAL, bg=bg)
    if mode == "frames":
        for tt in [float(x) for x in sys.argv[3].split(",")]:
            v.bg.p = None
            v.frame(tt).save(WORK / f"fr_{tt:05.1f}.png")
    elif mode == "render":
        sfx = [(s["start"], "whoosh") for s in scenes[1:]] + [(OS, "whoosh"), (OS + 0.15, "tink")]
        prev = None
        for st, en, g in GROUPS:
            if g[0]["sp"] != prev:
                sfx.append((st - 0.05, "pop"))
                prev = g[0]["sp"]
        sfx += [(t_kirec, "ding"), (t_iste, "ding"), (t_pir, "ding"), (t_koku + 0.3, "ding"), (t_iki, "pop"),
                (t_kay, "pop"), (t_yar, "pop"), (t_det, "pop"), (t_son, "pop"), (t_yik, "pop"), (t_bua, "pop"),
                (t_yor, "pop"), (t_beg, "pop"), (t_prt, "ding")]
        at.music(str(WORK / "music.wav"), TOTAL, bpm=100, style="sitcom")
        at.sfx(str(WORK / "sfx.wav"), TOTAL, sfx)
        at.final_mix(str(WORK / "voice_cut.wav"), str(WORK / "music.wav"), str(WORK / "sfx.wav"), str(WORK / "mix.m4a"))
        v.render(str(WORK / "mix.m4a"), str(WORK / "video.mp4"))
        compress(str(WORK / "video.mp4"), str(WORK / "final.mp4"))
        print("bitti", TOTAL)
