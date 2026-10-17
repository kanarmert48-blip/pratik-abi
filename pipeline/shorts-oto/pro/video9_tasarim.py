"""9. video: Gizli tasarımlar — saat 10:10, pizza kutusundaki plastik, makarnaya yağ (doğru mu?)."""
import json, math, subprocess, sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from engine import *  # noqa
from widgets import *  # noqa
import audio_tools as at

WORK = Path(sys.argv[1])
N = Path("/home/claude/pratik-abi/media")
words = json.loads((WORK / "words.json").read_text(encoding="utf-8"))
TOTAL = at.duration(str(WORK / "voice_cut.wav"))
OUTRO = 1.9
OS = TOTAL - OUTRO
BLUE = (59, 130, 246)
QRED = (239, 68, 68)
CX0, CY0, CS = 60, 330, 960  # kare kart
PANEL = (16, 20, 34)


def T(key, nth=0):
    k = trl(clean(key)).strip('"!?;')
    hits = [w for w in words if trl(clean(w["w"])).strip('"!?;') == k]
    return hits[nth]["s"]


def E(key, nth=0):
    k = trl(clean(key)).strip('"!?;')
    hits = [w for w in words if trl(clean(w["w"])).strip('"!?;') == k]
    return hits[nth]["e"]


S2, S3, S7 = T("gelelim"), T("ve", 1), T("sen")
Q = [(T("neden"), E("acaba"), T("bak", 1)), (T("ne"), E("dersin"), T("kapak")), (T("doğru"), E("mı"), T("yanlış", 1))]
t_bir, t_hani, t_tam = T("bir", 1), T("hani"), T("tamamen")
t_yag, t_ara = T("yağ", 1), T("aramızda")
t_yor, t_beg = T("yorumlara"), T("beğenmeyi")

# ---------- kart görüntü izi ----------
BS = 1008


def ph_crop(name, x, y, s):
    return dict(src=str(N / name), kind="photo", pre=f"crop={s}:{s}:{x}:{y},")


def vid(name, ss=0, x=None):
    d = dict(src=str(N / name), kind="video", ss=ss)
    if x is not None:
        d["pre"] = f"crop=ih:ih:{x}:0,"
    return d


def P(path, x, y, s, extra=""):
    return dict(src=str(N / path), kind="photo", pre=f"crop={s}:{s}:{x}:{y},{extra}")


SAAT = P("v9d-saat/orient_2.jpg", 0, 213, 1465)
VITRIN = P("v9d-saat/orient_1.jpg", 300, 0, 1341)
PIZZA_KUTU = P("v9-gizli-tasarim/pizza-w_2.jpg", 240, 0, 1440)
SAVER = P("v9-gizli-tasarim/pizza-w_1.jpg", 171, 0, 849)
SAVER2 = P("v9-gizli-tasarim/pizza-w_4.jpg", 240, 0, 1440)
SPAG = vid("v9-gizli-tasarim/makarna-v_2.mp4", 0)
YAGSU = P("v9b-ek/yagsu-p_2.jpg", 0, 0, 0) if False else dict(src=str(N / "v9b-ek/yagsu-p_2.jpg"), kind="photo")
KARIS = vid("v9-gizli-tasarim/karistir-v_1.mp4", 0)
PIZZA_V = vid("v9-gizli-tasarim/pizza-v_4.mp4", 1)
SEGS = [dict(SAAT, dur=t_hani), dict(VITRIN, dur=S2 - t_hani),
        dict(PIZZA_KUTU, dur=Q[1][2] - S2), dict(SAVER, dur=(S3 - Q[1][2]) * 0.55), dict(SAVER2, dur=(S3 - Q[1][2]) * 0.45),
        dict(SPAG, dur=Q[2][2] - S3), dict(YAGSU, dur=t_ara - Q[2][2]), dict(KARIS, dur=S7 - t_ara),
        dict(PIZZA_V, dur=OS - S7)]


def build_track(segs, out):
    import os, tempfile
    tmp = tempfile.mkdtemp()
    parts = []
    for i, s in enumerate(segs):
        assert s["dur"] > 0, (i, s["dur"])
        p = os.path.join(tmp, f"s{i}.mp4")
        vf = (f"{s.get('pre', '')}scale={BS}:{BS}:force_original_aspect_ratio=increase:flags=lanczos,crop={BS}:{BS},"
              f"fps={FPS},eq=contrast=1.05:saturation=1.1,unsharp=5:5:0.5,setsar=1,format=yuv420p")
        n = int(round(s["dur"] * FPS))
        if s["kind"] == "photo":
            inp = ["-loop", "1", "-i", s["src"]]
        else:
            dsrc = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of",
                                         "csv=p=0", s["src"]], capture_output=True, text=True).stdout or 0)
            ss = s.get("ss", 0)
            inp = ["-ss", f"{ss:.3f}", "-i", s["src"]] if dsrc - ss >= s["dur"] + 0.1 else ["-stream_loop", "-1", "-i",
                                                                                          s["src"]]
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *inp, "-vf", vf, "-an", "-frames:v", str(n),
                        "-c:v", "libx264", "-preset", "veryfast", "-crf", "14", p], check=True)
        parts.append(p)
    lst = os.path.join(tmp, "l.txt")
    open(lst, "w").write("".join(f"file '{p}'\n" for p in parts))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", out],
                   check=True)


class CardBG:
    def __init__(self, track, outro):
        self.track, self.outro = track, outro
        self.p = self.po = None
        self.nt = self.nto = 0
        m = Image.new("L", (CS, CS), 0)
        ImageDraw.Draw(m).rounded_rectangle([0, 0, CS - 1, CS - 1], radius=44, fill=255)
        self.mask = m
        self.shadow = soft_shadow(CS, CS, 44, blur=30, op=0.55)
        g = np.zeros((H, W, 4), np.uint8)
        y = np.arange(H)[:, None]
        g[..., :3] = (8, 11, 24)
        g[..., 3] = np.clip(140 + 70 * np.abs(y - 820) / 1100, 0, 225).astype(np.uint8)
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
            self.p = self._pipe(self.track, t, (BS, BS))
        buf = self.p.stdout.read(BS * BS * 3)
        self.nt = t + 1 / FPS
        if len(buf) < BS * BS * 3:
            return Image.new("RGB", (BS, BS), (20, 20, 30))
        return Image.frombuffer("RGB", (BS, BS), buf, "raw", "RGB", 0, 1)

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

    def seg(self, t):
        i = 0
        for k in range(len(SEGS)):
            if self.starts[k] <= t + 1e-6:
                i = k
        return i, (t - self.starts[i]) / max(SEGS[i]["dur"], 0.01)

    def frame(self, t):
        if t >= OS:
            return self._read_outro(t - OS).convert("RGBA")
        src = self._read(t)
        i, p = self.seg(t)
        z = 1 + 0.045 * p  # yavaş yakınlaşma
        cw = (BS - 48) / z
        c = BS / 2
        cardim = src.crop((c - cw / 2, c - cw / 2, c + cw / 2, c + cw / 2)).resize((CS, CS), Image.BICUBIC)
        bg = src.resize((18, 18), Image.BOX).resize((W, W), Image.BICUBIC)
        bg = bg.crop((0, 0, W, W)).resize((W, H), Image.BICUBIC).convert("RGBA")
        bg.alpha_composite(self.dark)
        sh, pad = self.shadow
        comp(bg, sh, CX0 - pad, CY0 - pad + 20)
        cr = cardim.convert("RGBA")
        cr.putalpha(self.mask)
        bg.alpha_composite(cr, (CX0, CY0))
        ImageDraw.Draw(bg).rounded_rectangle([CX0 - 3, CY0 - 3, CX0 + CS + 2, CY0 + CS + 2], radius=46,
                                             outline=(255, 255, 255, 235), width=5)
        dt = t - self.starts[i]
        if i > 0 and dt < 0.12:
            fl = Image.new("RGBA", (CS, CS), (255, 255, 255, 0))
            fl.putalpha(self.mask.point(lambda v: int(v * 0.5 * (1 - dt / 0.12))))
            bg.alpha_composite(fl, (CX0, CY0))
        return bg

    def finish(self, im, t):
        return im


def zmap(px, py):
    """Kart içi koordinat (0-960, zoom yok sayılır) -> ekran (merkezden yakınlaşma hesaba katılır)."""
    return CX0 + px, CY0 + py


def card_xy(t, px, py):
    i, p = BGREF.seg(t)
    z = 1 + 0.045 * p
    s = CS / (BS - 48) * z * (BS - 48) / CS  # = z
    cx, cy = CS / 2, CS / 2
    return CX0 + cx + (px - cx) * z, CY0 + cy + (py - cy) * z


BGREF = None

# ---------- Pratik Abi (sol alt) ----------
AB_FR = None


def _abi_frames():
    global AB_FR
    if AB_FR is None:
        fs = sorted((WORK / "abi").glob("f*.png"))
        R = 108
        S = 2 * R
        m = Image.new("L", (S * 4, S * 4), 0)
        ImageDraw.Draw(m).ellipse([0, 0, S * 4 - 1, S * 4 - 1], fill=255)
        m = m.resize((S, S), Image.LANCZOS)

        def mk(p):
            im = Image.open(p).convert("RGBA").resize((S, S), Image.LANCZOS)
            im.putalpha(m)
            out = Image.new("RGBA", (S + 16, S + 16), (0, 0, 0, 0))
            ImageDraw.Draw(out).ellipse([0, 0, S + 15, S + 15], fill=ACC + (255,))
            out.alpha_composite(im, (8, 8))
            return out
        AB_FR = [mk(p) for p in fs], mk(WORK / "abi" / "blink.png")
    return AB_FR


def _env():
    r = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(WORK / "voice_cut.wav"), "-f", "s16le", "-ac", "1",
                        "-ar", "16000", "-"], capture_output=True, check=True)
    x = np.frombuffer(r.stdout, "<i2").astype(float) / 32768
    hop = 16000 // FPS
    e = np.array([np.sqrt(np.mean(x[i:i + hop] ** 2)) for i in range(0, len(x), hop)])
    e = e / (np.percentile(e, 95) + 1e-9)
    return np.convolve(np.clip(e, 0, 1.2), np.ones(3) / 3, mode="same")


ENV = _env()
AX, AY = 172, 1575


def abi(im, t):
    frs, blink = _abi_frames()
    n = len(frs)
    k = int(t * FPS) % (2 * n - 2)
    k = k if k < n else 2 * n - 2 - k
    img = blink if (t % 5.2) < 0.14 else frs[k]
    lvl = float(ENV[min(len(ENV) - 1, int(t * FPS))])
    s = 1 + 0.06 * lvl
    im2 = img.resize((int(img.width * s), int(img.height * s)), Image.BICUBIC)
    rot = 3 * math.sin(t * 2.1)
    im2 = im2.rotate(rot, resample=Image.BICUBIC, expand=True)
    sh, pad = soft_shadow(img.width, img.height, img.width // 2, blur=16, op=0.5)
    comp(im, sh, AX - img.width / 2 - pad, AY - img.height / 2 - pad + 12)
    comp(im, im2, AX - im2.width / 2, AY - im2.height / 2)
    d = ImageDraw.Draw(im)
    for k2 in range(2):  # ses dalgası
        rr = 130 + k2 * 22 + 12 * lvl
        d.arc([AX - rr, AY - rr, AX + rr, AY + rr], -40, 30, fill=ACC + (int(200 - 70 * k2),), width=7)


# ---------- ortak quiz parçaları ----------
def panel(L, alpha=1.0, col=PANEL):
    card(L, CX0, CY0, CS, CS, r=44, fill=col + (255,), shadow=False, alpha=alpha)


def pulse_ring(L, t, start, x, y, r=70, col=ACC):
    p = ph(t, start, 0.4)
    if p <= 0:
        return
    d = ImageDraw.Draw(L)
    rr = r * (1 + 0.08 * math.sin(t * 8)) * eb(p)
    d.ellipse([x - rr, y - rr, x + rr, y + rr], outline=col + (255,), width=10)
    ph2 = (t * 1.3) % 1
    r2 = r * (1 + 0.6 * ph2)
    d.ellipse([x - r2, y - r2, x + r2, y + r2], outline=col + (int(200 * (1 - ph2)),), width=5)


def quiz(L, t, i, s0, label="Sence ne işe yarar?"):
    qs, qe, ans = (x - s0 for x in Q[i])
    if qs - 0.1 <= t < ans - 0.05:
        chip(L, W / 2, CY0 + CS - 70, label, bg=WHITE, fg=INK, size=46, icon_name="thinking_face",
             k="black", scale=eb(ph(t, qs - 0.1, 0.35)))
    if qe <= t < ans:
        p = (t - qe) / max(ans - qe, 0.1)
        cx, cy, r = CX0 + CS - 90, CY0 + 90, 56
        d = ImageDraw.Draw(L)
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(14, 18, 32, 230))
        d.arc([cx - r, cy - r, cx + r, cy + r], -90, -90 + 360 * (1 - p), fill=ACC + (255,), width=10)
        text_c(L, (cx, cy + 2), str(max(1, math.ceil((1 - p) * 3))), "black", 52, WHITE)


def answer(L, t, s0, i, text, icon):
    ans = Q[i][2] - s0
    q = ph(t, ans - 0.05, 0.35)
    if q > 0:
        chip(L, W / 2, CY0 + CS - 70, text, bg=GREEN, fg=WHITE, size=48, icon_name=icon, k="black", scale=eb(q))




def title(L, segs, t):
    headline(L, segs, t, y0=205, size=76, start=-1 if t < 0.05 else 0.0)


# ---------- sahneler ----------
def s1(v, sc, L, t, dur):
    s0 = sc["start"]
    headline(L, [("Saat neden hep", False), ("10:10?", True)], t, y0=205, size=76, start=-1)
    a = Q[0][2] - s0
    if t < a:
        arrow(L, t, Q[0][0] - s0 - 1.4, (CX0 + 840, CY0 + 800), (CX0 + 470, CY0 + 490), bend=-0.25)
    elif t < t_bir - s0:
        arrow(L, t, a + 0.4, (CX0 + 860, CY0 + 120), (CX0 + 470, CY0 + 350), bend=0.22, col=ACC)
    else:
        put_icon(L, "grinning_face_with_sweat" if False else "smiling_face_with_sunglasses", CX0 + 820, CY0 + 140,
                 150 * eb(ph(t, t_bir - s0, 0.4)), rot=8)
    quiz(L, t, 0, s0)
    if t < t_hani - s0:
        answer(L, t, s0, 0, "Logoyu çerçeveliyor!", "sparkles")
    else:
        stamp(L, CX0 + 480, CY0 + 420, "UYDURMA!", QRED, t, t_tam - s0, rot=-8, size=110)
        chip(L, W / 2, CY0 + CS - 70, "Ölüm saati efsanesi", bg=WHITE, fg=INK, size=46, icon_name="ghost", k="black",
             scale=eb(ph(t, t_hani - s0, 0.35)))


def s2(v, sc, L, t, dur):
    s0 = sc["start"]
    headline(L, [("Pizzadaki", False), ("minik plastik", True)], t, y0=205, size=76)
    a = Q[1][2] - s0
    if t < a:
        arrow(L, t, 0.5, (CX0 + 860, CY0 + 720), (CX0 + 500, CY0 + 340), bend=-0.25)
    quiz(L, t, 1, s0)
    answer(L, t, s0, 1, "Kapak çökmesin diye!", "pizza")


def s3(v, sc, L, t, dur):
    s0 = sc["start"]
    headline(L, [("Makarnaya", False), ("yağ koymak?", True)], t, y0=205, size=76)
    a = Q[2][2] - s0
    quiz(L, t, 2, s0, label="Doğru mu, yanlış mı?")
    ta = t_ara - s0
    if a <= t < ta:
        stamp(L, CX0 + 480, CY0 + 300, "YANLIŞ!", QRED, t, a, rot=-8, size=120)
    if a <= t < ta:
        chip(L, W / 2, CY0 + CS - 70, "Yağ suyun üstünde yüzer", bg=QRED, fg=WHITE, size=44, icon_name="droplet",
             k="black", scale=eb(ph(t, t_yag - s0, 0.35)))
    if t >= ta:
        put_icon(L, "shushing_face", CX0 + 820, CY0 + 150, 160 * eb(ph(t, ta, 0.4)), rot=-6)
        chip(L, W / 2, CY0 + CS - 70, "Bol su + ilk dakikalar karıştır", bg=GREEN, fg=WHITE, size=42,
             icon_name="check_mark_button", k="black", scale=eb(ph(t, ta + 0.3, 0.35)))


def s_end(v, sc, L, t, dur):
    s0 = sc["start"]
    if t >= dur - OUTRO:
        lt = t - (dur - OUTRO)
        chip(L, 540, 1560, "Takip et, kaçırma!", bg=RED, fg=WHITE, size=50, icon_name="bell", k="black",
             scale=eb(ph(lt, 0.25, 0.4)))
        return
    headline(L, [("Kaçını", False), ("biliyordun?", True)], t, y0=205, size=80)
    q = ph(t, 0.1, 0.4)
    glass(L, CX0 + 160, CY0 + 120, CS - 320, 420, alpha=eo(q))
    put_icon(L, "trophy", W / 2, CY0 + 260, 200 * eb(q), rot=4 * math.sin(t * 3))
    qm = "?" if int(t * 2.5) % 2 == 0 else " "
    text_c(L, (W / 2, CY0 + 450), f"{qm} / 3", "black", 110, ACC, alpha=eo(q))
    chip(L, W / 2, CY0 + 640, "Yorumlara yaz!", bg=WHITE, fg=INK, size=48, icon_name="speech_balloon", k="black",
         scale=eb(ph(t, t_yor - s0, 0.4)))
    tb = t_beg - s0
    q2 = ph(t, tb - 0.1, 0.45)
    if q2 > 0:
        put_icon(L, "thumbs_up", 360, CY0 + 800, 150 * eb(q2), rot=-8)
        put_icon(L, "bell", 720, CY0 + 800, 150 * eb(ph(t, tb + 0.4, 0.45)),
                 rot=14 * math.sin(t * 9) * (1 - ph(t, tb + 1.4, 0.8)))


starts = [0.0, S2, S3, S7]
draws = [s1, s2, s3, s_end]
scenes = [{"start": s, "end": (starts[i + 1] if i + 1 < len(starts) else TOTAL), "draw": d}
          for i, (s, d) in enumerate(zip(starts, draws))]


class Quiz(Video):
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
                comp(im, layer, 0, (1 - pin) * 60 - pout * 60)
                break
        brand(im, W / 2, 140)
        if t < OS:
            draw_caption(im, self.groups, t, y=1395)
            abi(im, t)
        return im.convert("RGB")


if __name__ == "__main__":
    mode = sys.argv[2] if len(sys.argv) > 2 else "render"
    if not (WORK / "card.mp4").exists():
        build_track(SEGS, str(WORK / "card.mp4"))
    BGREF = CardBG(str(WORK / "card.mp4"), str(WORK / "outro.mp4"))
    v = Quiz(scenes, words, "", TOTAL, bg=BGREF)
    if mode == "frames":
        for tt in [float(x) for x in sys.argv[3].split(",")]:
            v.bg.p = None
            v.frame(tt).save(WORK / f"fr_{tt:05.1f}.png")
    elif mode == "render":
        sfx = [(s["start"], "whoosh") for s in scenes[1:]] + [(OS, "whoosh"), (OS + 0.15, "tink")]
        for qs, qe, ans in Q:
            sfx += [(qs - 0.1, "pop"), (ans - 0.05, "ding")]
        sfx += [(t_tam, "pop"), (t_ara, "pop"), (t_yor, "pop"), (t_beg, "pop")]
        at.music(str(WORK / "music.wav"), TOTAL, bpm=96, style="warm")
        at.sfx(str(WORK / "sfx.wav"), TOTAL, sfx)
        at.final_mix(str(WORK / "voice_cut.wav"), str(WORK / "music.wav"), str(WORK / "sfx.wav"), str(WORK / "mix.m4a"))
        v.render(str(WORK / "mix.m4a"), str(WORK / "video.mp4"))
        compress(str(WORK / "video.mp4"), str(WORK / "final.mp4"))
        print("bitti", TOTAL)

