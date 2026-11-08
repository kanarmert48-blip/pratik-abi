"""49. video (2K Shorts, ~30 sn): Ters renkli Kapadokya fotoğrafına 15 saniye bak -> siyah-beyaz fotoğraf renkli görünür (ardıl görüntü).
Kullanım: python3 video49_kapadokya.py <WORK> [frames t1,t2,... | ses | render]
WORK/foto/kapadokya.jpg (Unsplash, Aleks) + voice_cut.wav + words.json + zaman.json + muzik.wav gerekir."""
import os
os.environ.setdefault("PA_SCALE", str(4 / 3))
import json, math, subprocess, sys
from pathlib import Path

import numpy as np
from PIL import ImageEnhance, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parent))
from engine import *  # noqa
from pa_ui import put_word, panel, txt, pop, captions
import audio_tools as at
from abi_yuz import konusma
from rozet import Rozet

WORK = Path(sys.argv[1])
VOICE = WORK / "voice_cut.wav"
words = json.loads((WORK / "words.json").read_text(encoding="utf-8"))
TOTAL = round(at.duration(str(VOICE)), 3)
Z = json.loads((WORK / "zaman.json").read_text())
T0, TSW = Z["stare0"], Z["switch"]          # bakış başlangıcı, beyaza geçiş (15 sn)


def ramp(t, a, b):
    return eio(clamp((t - a) / max(1e-6, b - a)))


def _hits(key):
    k = trl(clean(key)).strip('"!?;,.…')
    return [w for w in words if trl(clean(w["w"])).strip('"!?;,.…') == k]


def T(key, nth=0):
    return _hits(key)[nth]["s"]


t_kap, t_goz, t_gor, t_daha = T("Kapadokya'yı"), T("Gözün"), T("Gördüysen"), T("Daha", 1)
REVEAL = t_goz - 0.25          # gerçek fotoğraf belirir
S_END = t_daha - 0.1
GOLD = (255, 204, 70)
CYAN = (40, 230, 230)
INKC = (14, 16, 30)

# ---------- fotoğraf ----------
PW, PH = round(u(990)), round(u(1320))       # 3:4 alan
PX0, PY0 = (W - PW) // 2, round(u(420))
DOT = (W // 2, PY0 + PH // 2)
_src = Image.open(WORK / "foto" / "kapadokya.jpg").convert("RGB")
_s = max(PW / _src.width, PH / _src.height)
_src = _src.resize((round(_src.width * _s), round(_src.height * _s)), Image.LANCZOS)
_x0, _y0 = (_src.width - PW) // 2, (_src.height - PH) // 2
REAL = _src.crop((_x0, _y0, _x0 + PW, _y0 + PH))
_boost = ImageEnhance.Contrast(ImageEnhance.Color(REAL).enhance(1.35)).enhance(1.12)
NEG = Image.fromarray(255 - np.asarray(_boost))          # ters renk (negatif)
_mask = Image.new("L", (PW, PH), 0)
ImageDraw.Draw(_mask).rounded_rectangle([0, 0, PW - 1, PH - 1], radius=round(u(36)), fill=255)
DARK = (10, 11, 16)
BASE_NEG = Image.new("RGB", (W, H), DARK)
BASE_NEG.paste(NEG, (PX0, PY0), _mask)
BASE_REAL = Image.new("RGB", (W, H), DARK)
BASE_REAL.paste(REAL, (PX0, PY0), _mask)
GRAYP = ImageOps.grayscale(REAL).convert("RGB")          # siyah-beyaz (beyin renklendirir)
BASE_GRAY = Image.new("RGB", (W, H), DARK)
BASE_GRAY.paste(GRAYP, (PX0, PY0), _mask)


def dot(d, r=11, a=1.0, col=(0, 0, 0)):
    r = u(r)
    d.ellipse([DOT[0] - r - u(5), DOT[1] - r - u(5), DOT[0] + r + u(5), DOT[1] + r + u(5)], fill=(255, 255, 255, int(255 * a)))
    d.ellipse([DOT[0] - r, DOT[1] - r, DOT[0] + r, DOT[1] + r], fill=col + (int(255 * a),))


def stare_ui(L, t):
    d = ImageDraw.Draw(L)
    dot(d)
    left = max(0.0, TSW - t)
    n = max(1, int(math.ceil(left - 1e-6)))
    # başlık / talimat
    if t < 2.5:
        q = pop(t, 0.0, 0.3)
        put_word(L, "BU FOTOĞRAFA", WHITE, 540, 150, max(8, round(78 * q)), alpha=1.0, glow=0.2)
        put_word(L, "15 SANİYE BAK!", GOLD, 540, 255, max(8, round(104 * q)), alpha=1.0, glow=0.45)
    else:
        a = ramp(t, 2.5, 2.8)
        txt(L, (540, 150), "Ortadaki noktaya bak", 58, WHITE, a, stroke=6)
        txt(L, (540, 225), "gözünü kırpma", 50, GOLD, a, stroke=6)
    # geri sayım halkası
    cx, cy, r = 540, 335, 52
    q = clamp((t - T0) / (TSW - T0))
    bx = [u(cx - r), u(cy - r), u(cx + r), u(cy + r)]
    if t >= 2.5:                                   # başlık bitince halka (yazıyla çakışmasın)
        d.ellipse(bx, outline=(255, 255, 255, 70), width=round(u(9)))
        if q < 1:
            d.arc(bx, -90 + 360 * q, 270, fill=CYAN + (255,), width=round(u(9)))
        txt(L, (cx, cy), str(n), 56, WHITE, 1.0, k="black", stroke=5)
    # alt ilerleme çubuğu
    y = PY0 + PH + u(34)
    d.rounded_rectangle([PX0, y, PX0 + PW, y + u(14)], radius=round(u(7)), fill=(255, 255, 255, 60))
    d.rounded_rectangle([PX0, y, PX0 + PW * q, y + u(14)], radius=round(u(7)), fill=CYAN + (230,))


def reveal_ui(L, t):
    a = ramp(t, REVEAL, REVEAL + 0.4)
    if t < S_END:
        q = pop(t, REVEAL, 0.35)
        txt(L, (540, 150), "GERÇEK RENKLERİ", round(72 * q), GOLD, a, stroke=7)
        txt(L, (540, 245), "işte böyle!", round(56 * q), WHITE, a, stroke=6)
        if t >= t_goz + 0.3:
            b = ramp(t, t_goz + 0.3, t_goz + 0.6)
            chip(L, 540, 1060, "Göz yoruldu → beyin ZIT rengi gösterdi", bg=WHITE, fg=INKC, size=40, k="black",
                 alpha=b, scale=pop(t, t_goz + 0.3, 0.3))
        if t >= t_gor - 0.08:
            chip(L, 540, 1180, "Gördüysen yorumlara yaz", bg=GOLD, fg=INKC, size=50, icon_name="speech_balloon", k="black",
                 alpha=1.0, scale=pop(t, t_gor - 0.08, 0.35))
        txt(L, (540, (PY0 + PH) / u(1) + 40), "Fotoğraf: Aleks / Unsplash", 26, WHITE, 0.55 * a, k="b", stroke=3)
    else:
        b = ramp(t, S_END, S_END + 0.25)
        txt(L, (540, 175), "Daha fazlası için", 64, WHITE, b, stroke=6)
        pulse = 1 + 0.045 * math.sin((t - S_END) * 8) * ramp(t, S_END + 0.4, S_END + 0.7)
        chip(L, 540, 300, "TAKİP ET", bg=INKC, fg=WHITE, size=90, icon_name="bell", k="black", scale=pop(t, S_END, 0.4) * pulse)


ROZ = Rozet()
OPN, RND = konusma(VOICE, FPS)


class Vid(Video):
    def frame(self, t):
        i = min(len(OPN) - 1, int(t * FPS))
        if t < TSW:
            im = BASE_NEG.copy().convert("RGBA")
            L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            stare_ui(L, t)
            im.alpha_composite(L)
            brand(im, 540, 62, size=34)
            ra = 1 - ramp(t, 2.3, 2.8)                 # bakış sırasında Abi gizlenir (dikkat dağıtmasın)
            if ra > 0.01:
                ROZ.draw(im, t, float(OPN[i]), alpha=ra)
            return im.convert("RGB")
        if t < REVEAL:
            # aynı yerde siyah-beyaz fotoğraf + nokta: beyin onu renkli gösterir (Kız Kulesi videosu gibi)
            im = BASE_GRAY.copy().convert("RGBA")
            L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            dot(ImageDraw.Draw(L))
            if t < t_kap - 0.1:
                txt(L, (540, 150), "ŞİMDİ SİYAH-BEYAZ", 62, WHITE, 1.0, stroke=6)
                txt(L, (540, 235), "fotoğrafa bak!", 56, GOLD, 1.0, stroke=6)
                txt(L, (540, 330), "Noktadan gözünü ayırma", 40, WHITE, 0.8, k="b", stroke=4)
            else:
                q = pop(t, t_kap - 0.1, 0.3)
                txt(L, (540, 160), "RENKLİ GÖRDÜN", round(76 * q), GOLD, 1.0, stroke=7)
                txt(L, (540, 260), "değil mi?", round(58 * q), WHITE, 1.0, stroke=6)
            im.alpha_composite(L)
            brand(im, 540, 62, size=34)
            return im.convert("RGB")
        f = ramp(t, REVEAL, REVEAL + 0.5)
        im = Image.blend(BASE_GRAY, BASE_REAL, f).convert("RGBA")
        L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        reveal_ui(L, t)
        im.alpha_composite(L)
        brand(im, 540, 62, size=34)
        C = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        captions(C, self.groups, t, y=1700)
        im.alpha_composite(C)
        ROZ.draw(im, t, float(OPN[i]))
        return im.convert("RGB")


VID = Vid([{"start": 0, "end": TOTAL, "draw": lambda *a: None}], words, "", TOTAL, bg=None)


def make_audio():
    ev = [(0.0, "pop"), (2.5, "tink"), (TSW - 0.02, "ding"), (REVEAL, "pop"), (t_goz + 0.3, "pop"),
          (t_gor - 0.08, "pop"), (S_END, "pop")]
    at.sfx(str(WORK / "sfx.wav"), TOTAL, ev)
    SR = 44100
    fx = np.frombuffer(subprocess.run(["ffmpeg", "-v", "error", "-i", str(WORK / "sfx.wav"), "-ac", "1", "-ar", str(SR),
                                       "-f", "f32le", "-"], capture_output=True).stdout, np.float32).copy()
    fx = np.pad(fx, (0, max(0, int(TOTAL * SR) + SR - len(fx))))
    rng = np.random.default_rng(49)
    m = int(0.05 * SR)
    tt = np.arange(m) / SR
    tick = (np.sin(2 * np.pi * 2400 * tt) * 0.6 + rng.standard_normal(m) * 0.4) * np.exp(-tt * 90)
    for k in range(1, 15):                      # saat tiki: her saniye, son 3 saniye biraz daha güçlü
        a = int((T0 + k) * SR)
        g = 0.10 if k < 12 else 0.16
        fx[a:a + m] += (tick * g).astype(np.float32)
    at._write(str(WORK / "sfx.wav"), fx[:int(TOTAL * SR)])
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-stream_loop", "3", "-i", str(WORK / "muzik.wav"), "-af",
                    f"atrim=0:{TOTAL:.3f},afade=t=in:d=0.3,afade=t=out:st={TOTAL - 0.6:.3f}:d=0.6",
                    "-ar", "44100", "-ac", "1", str(WORK / "music.wav")], check=True)
    at.final_mix(str(VOICE), str(WORK / "music.wav"), str(WORK / "sfx.wav"), str(WORK / "mix.m4a"))


if __name__ == "__main__":
    mode = sys.argv[2] if len(sys.argv) > 2 else "render"
    print("TOTAL", TOTAL, "REVEAL", REVEAL, flush=True)
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
