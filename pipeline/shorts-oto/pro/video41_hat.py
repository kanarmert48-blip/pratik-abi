"""41. video (2K, ~56 sn): Adına gizli hat açılmış olabilir — e-Devlet Mobil Hat Sorgulama adım adım.
Kullanım: python3 video41_hat.py <WORK> [frames t1,t2,... | ses | render]"""
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


t_ve, t_dol, t_30, t_once, t_arama = T("Ve"), T("dolandırıcılıkta"), T("30"), T("Önce"), T("Arama")
t_cikan, t_bilgi, t_gir, t_karsina = T("Çıkan"), T("Bilgi"), T("gir"), T("Karşına")
t_tt, t_tc, t_vf, t_her = T("Türk Telekom"), T("Turkcell"), T("Vodafone"), T("Her")
t_tani, t_kapat, t_gerek, t_bu, t_buyuk, t_daha = T("Tanımadığın"), T("kapattır"), T("Gerekirse"), T("Bu", 1), \
    T("büyüklerine"), T("Daha")
CUTS = [t_30 - 0.1, t_once - 0.1, t_arama - 0.1, t_cikan - 0.1, t_karsina - 0.1, t_tani - 0.1, t_bu - 0.1]

GOLD = (255, 204, 70)
INKC = (14, 16, 30)
EBLUE = (0, 92, 175)       # sade mavi başlık çubuğu (temsili arayüz)
EBG = (241, 244, 248)


def sm(x):
    return eio(clamp(x))


def ramp(t, a, b):
    return sm((t - a) / max(1e-6, b - a))


def wnd(t, a, b, fi=0.2, fo=0.2):
    return ramp(t, a, a + fi) * (1 - ramp(t, b - fo, b))


# ---------------- gerçek klipler ----------------
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
    """BGR kareyi dikey 1440x2560'a kırp-doldur"""
    h, w = fr.shape[:2]
    s = max(W / w, H / h) * zoom
    nw, nh = int(w * s), int(h * s)
    r = cv2.resize(fr, (nw, nh), interpolation=cv2.INTER_AREA if s < 1 else cv2.INTER_LINEAR)
    x0, y0 = (nw - W) // 2, (nh - H) // 2
    return cv2.cvtColor(r[y0:y0 + H, x0:x0 + W], cv2.COLOR_BGR2RGB)


CL_HOOK1 = Clip(MED / "dolandirici_1.mp4", 0.5)
CL_HOOK2 = Clip(MED / "telefon_el_3.mp4", 2.0)
CL_END = Clip(MED / "yasli_2.mp4", 0.5)

BG = np.zeros((H, W, 3), np.float32)
_yy, _xx = np.mgrid[0:H, 0:W].astype(np.float32)
_r = np.sqrt(((_xx - W / 2) / W) ** 2 + ((_yy - H * 0.45) / H) ** 2)
for c, (a, b) in enumerate(zip((26, 44, 78), (8, 10, 20))):
    BG[..., c] = b + (a - b) * np.clip(1 - _r * 1.4, 0, 1) ** 1.3
BGIMG = Image.fromarray(BG.astype(np.uint8)).convert("RGBA")
del _yy, _xx, _r

# ---------------- telefon (temsili ekran) ----------------
PW, PH = int(u(590)), int(u(1160))
PCX, PCY = W / 2, u(985)
SW, SH = PW - int(u(44)), PH - int(u(44))


def F(k, s):
    return font(k, int(u(s)))


def phone_frame():
    im = Image.new("RGBA", (PW + 80, PH + 80), (0, 0, 0, 0))
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle([40, 56, 40 + PW, 56 + PH], radius=int(u(86)), fill=(0, 0, 0, 170))
    im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(u(26))))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([40, 40, 40 + PW, 40 + PH], radius=int(u(86)), fill=(24, 26, 32, 255),
                        outline=(120, 124, 136, 255), width=int(u(5)))
    return im


PHONE = phone_frame()
MASK = Image.new("L", (SW, SH), 0)
ImageDraw.Draw(MASK).rounded_rectangle([0, 0, SW - 1, SH - 1], radius=int(u(66)), fill=255)


def status_bar(d):
    d.text((u(44), u(40)), "09:41", font=F("xb", 30), fill=(30, 30, 36), anchor="lm")
    for i in range(4):
        hh = u(10 + i * 6)
        d.rectangle([SW - u(150) + i * u(14), u(52) - hh, SW - u(150) + i * u(14) + u(9), u(52)], fill=(30, 30, 36))
    d.rounded_rectangle([SW - u(84), u(28), SW - u(40), u(52)], radius=u(6), outline=(30, 30, 36), width=int(u(3)))
    d.rectangle([SW - u(80), u(32), SW - u(52), u(48)], fill=(30, 30, 36))


def header(d, title):
    d.rectangle([0, u(76), SW, u(196)], fill=EBLUE)
    d.text((SW / 2, u(136)), title, font=F("black", 40), fill=(255, 255, 255), anchor="mm")


def field(d, y, label, val, focus=False):
    d.text((u(46), y), label, font=F("xb", 28), fill=(90, 96, 110), anchor="lm")
    d.rounded_rectangle([u(40), y + u(26), SW - u(40), y + u(116)], radius=u(18), fill=(255, 255, 255),
                        outline=EBLUE if focus else (200, 205, 215), width=int(u(4 if focus else 2)))
    d.text((u(66), y + u(71)), val, font=F("xb", 36), fill=(30, 30, 36), anchor="lm")


def tap(d, x, y, k):
    if k <= 0 or k >= 1:
        return
    r = u(40 + 70 * k)
    d.ellipse([x - r, y - r, x + r, y + r], outline=(255, 170, 0, int(255 * (1 - k))), width=int(u(8)))
    r2 = u(34)
    d.ellipse([x - r2, y - r2, x + r2, y + r2], fill=(255, 170, 0, int(200 * (1 - k) ** 0.5)))


def typed(s, t, t0, cps=16):
    n = int(max(0, t - t0) * cps)
    return s[:n]


OPS = [("Türk Telekom", None), ("Turkcell", "0532 *** ** 47"), ("Vodafone", "0542 *** ** 19")]


def screen(t):
    im = Image.new("RGBA", (SW, SH), EBG + (255,))
    d = ImageDraw.Draw(im, "RGBA")
    status_bar(d)
    if t < t_arama - 0.1:   # 1) giriş
        header(d, "e-Devlet Kapısı")
        d.text((SW / 2, u(270)), "Giriş Yap", font=F("black", 46), fill=(30, 30, 36), anchor="mm")
        lt = t - (t_once - 0.1)
        tc = "1234567****"[:int(max(0, lt) * 18)]
        pw = "●" * min(8, int(max(0, lt - 0.7) * 18))
        field(d, u(340), "T.C. Kimlik No", tc, focus=lt < 0.7)
        field(d, u(500), "e-Devlet Şifresi", pw, focus=lt >= 0.7)
        by = u(700)
        press = ramp(t, t_once + 1.3, t_once + 1.45) * (1 - ramp(t, t_once + 1.5, t_once + 1.7))
        d.rounded_rectangle([u(40), by, SW - u(40), by + u(110)], radius=u(20),
                            fill=tuple(int(c * (1 - 0.2 * press)) for c in EBLUE))
        d.text((SW / 2, by + u(55)), "Giriş Yap", font=F("black", 40), fill=(255, 255, 255), anchor="mm")
        tap(d, SW / 2, by + u(55), (t - (t_once + 1.3)) / 0.6)
    elif t < t_cikan - 0.1:  # 2) arama
        header(d, "e-Devlet Kapısı")
        q = typed("mobil hat sorgulama", t, t_arama + 0.3, 14)
        y = u(250)
        d.rounded_rectangle([u(36), y, SW - u(36), y + u(110)], radius=u(55), fill=(255, 255, 255),
                            outline=EBLUE, width=int(u(4)))
        d.ellipse([u(70), y + u(34), u(110), y + u(74)], outline=(90, 96, 110), width=int(u(5)))
        d.line([u(104), y + u(70), u(122), y + u(88)], fill=(90, 96, 110), width=int(u(6)))
        cur = "|" if int(t * 2.5) % 2 == 0 else ""
        d.text((u(140), y + u(55)), (q or "Hizmet ara…") + (cur if q else ""), font=F("xb", 36),
               fill=(30, 30, 36) if q else (150, 155, 165), anchor="lm")
        for i, nm in enumerate(["Popüler Hizmetler", "Adres Bilgilerim", "Vergi Borcu Sorgulama", "Tapu Bilgileri"]):
            yy = u(420 + i * 120)
            d.rounded_rectangle([u(36), yy, SW - u(36), yy + u(100)], radius=u(18), fill=(255, 255, 255))
            d.text((u(70), yy + u(50)), nm, font=F("xb", 32 if i else 30), fill=(120, 125, 135) if i else (60, 64, 74),
                   anchor="lm")
    elif t < t_karsina - 0.1:  # 3) sonuçlar
        header(d, "Arama Sonuçları")
        d.text((u(46), u(250)), "“mobil hat sorgulama”", font=F("xb", 30), fill=(90, 96, 110), anchor="lm")
        res = [("Mobil Hat Sorgulama", "Bilgi Teknolojileri ve İletişim Kurumu"),
               ("Sabit Hat Sorgulama", "İlgili kurum hizmeti"), ("Numara Taşıma Bilgisi", "İlgili kurum hizmeti")]
        hi = ramp(t, t_bilgi - 0.2, t_bilgi + 0.3)
        for i, (a, b) in enumerate(res):
            yy = u(310 + i * 190)
            col = (255, 255, 255)
            d.rounded_rectangle([u(36), yy, SW - u(36), yy + u(165)], radius=u(20), fill=col,
                                outline=(255, 170, 0) if i == 0 and hi > 0.5 else (220, 224, 232),
                                width=int(u(7 if i == 0 and hi > 0.5 else 2)))
            d.text((u(70), yy + u(58)), a, font=F("black", 36), fill=EBLUE if i == 0 else (60, 64, 74), anchor="lm")
            d.text((u(70), yy + u(112)), b, font=F("xb", 21), fill=(110, 115, 125), anchor="lm")
        tap(d, SW / 2, u(310 + 82), (t - (t_gir - 0.15)) / 0.6)
    else:  # 4) operatör listesi
        header(d, "Mobil Hat Sorgulama")
        d.text((u(46), u(250)), "Adınıza kayıtlı hatlar", font=F("black", 34), fill=(30, 30, 36), anchor="lm")
        times = [t_tt, t_tc, t_vf]
        flag = ramp(t, t_tani - 0.1, t_tani + 0.3)
        for i, ((op, num), tt) in enumerate(zip(OPS, times)):
            q = ramp(t, tt - 0.15, tt + 0.2)
            if q <= 0.01:
                continue
            yy = u(310 + i * 230) + (1 - q) * u(40)
            red = (i == 2 and flag > 0.01)
            d.rounded_rectangle([u(36), yy, SW - u(36), yy + u(200)], radius=u(22),
                                fill=(255, 235, 235, int(255 * q)) if red else (255, 255, 255, int(255 * q)),
                                outline=(220, 40, 40, int(255 * q)) if red else (220, 224, 232, int(255 * q)),
                                width=int(u(7 if red else 2)))
            d.text((u(70), yy + u(56)), op, font=F("black", 38), fill=(30, 30, 36, int(255 * q)), anchor="lm")
            if num:
                d.text((u(70), yy + u(130)), num, font=F("black", 44), fill=(EBLUE if not red else (200, 30, 30)) +
                       (int(255 * q),), anchor="lm")
                d.text((SW - u(70), yy + u(130)), "Aktif", font=F("xb", 28), fill=(40, 160, 90, int(255 * q)),
                       anchor="rm")
            else:
                d.text((u(70), yy + u(130)), "Kayıtlı hat yok", font=F("xb", 32), fill=(130, 135, 145, int(255 * q)),
                       anchor="lm")
        if t >= t_her - 0.1:
            d.text((SW / 2, u(1060)), "Bu bir temsili ekrandır", font=F("xb", 24), fill=(150, 155, 165), anchor="mm")
    out = Image.new("RGBA", (SW, SH), (0, 0, 0, 0))
    out.paste(im, (0, 0), MASK)
    return out


def draw_phone(im, t, a=1.0, dy=0.0, scale=1.0):
    ph_ = PHONE.copy()
    ph_.alpha_composite(screen(t), (40 + int(u(22)), 40 + int(u(22))))
    if abs(scale - 1) > 0.003:
        ph_ = ph_.resize((int(ph_.width * scale), int(ph_.height * scale)), Image.BICUBIC)
    if a < 0.999:
        ph_ = set_alpha(ph_, a)
    im.alpha_composite(ph_, (int(PCX - ph_.width / 2), int(PCY - ph_.height / 2 + dy)))


ROZ = Rozet()
OPN, RND = konusma(VOICE, FPS)
P0 = t_30 - 0.1          # telefonun geldiği an
P1 = t_bu - 0.1          # telefonun gittiği an


def step_badge(L, n, label, t, t0):
    q = pop(t, t0, 0.35)
    chip(L, 540, 300, f"ADIM {n}: {label}", bg=GOLD, fg=INKC, size=50, k="black", scale=q)


def ui(L, t):
    if t < P0:
        a = 1 - ramp(t, P0 - 0.2, P0)
        q = 1 + 0.1 * (1 - pop(t, 0.0, 0.28))
        put_icon(L, "warning", 540, 120, 120 * q, alpha=a)
        put_word(L, "ADINA GİZLİ HAT", WHITE, 540, 250, round(96 * q), alpha=a, glow=0.35)
        put_word(L, "AÇILMIŞ OLABİLİR!", RED, 540, 370, round(96 * q), alpha=a, glow=0.5)
        if t >= t_dol - 0.1:
            chip(L, 540, 1380, "Dolandırıcılıkta kullanılıyor olabilir", bg=RED, fg=WHITE, size=40, k="black",
                 alpha=a, scale=pop(t, t_dol - 0.1, 0.3))
    elif t < P1:
        if t < t_once - 0.1:
            q = pop(t, P0, 0.35)
            put_word(L, "30 SANİYEDE", WHITE, 540, 150, max(8, round(90 * q)), glow=0.3)
            put_word(L, "KONTROL ET", GOLD, 540, 270, max(8, round(104 * q)), glow=0.45)
        elif t < t_arama - 0.1:
            step_badge(L, 1, "e-Devlet'e gir", t, t_once - 0.1)
        elif t < t_cikan - 0.1:
            step_badge(L, 2, "Arama kutusuna yaz", t, t_arama - 0.1)
        elif t < t_karsina - 0.1:
            step_badge(L, 3, "Mobil Hat Sorgulama", t, t_cikan - 0.1)
        elif t < t_tani - 0.1:
            step_badge(L, 4, "Hatlarını kontrol et", t, t_karsina - 0.1)
        else:
            q = pop(t, t_tani - 0.1, 0.35)
            put_word(L, "TANIMIYOR MUSUN?", RED, 540, 175, max(8, round(90 * q)), glow=0.5)
            if t >= t_kapat - 0.6:
                chip(L, 540, 300, "Operatöre başvur → hattı kapattır", bg=WHITE, fg=INKC, size=44, k="black",
                     icon_name="check_mark_button", scale=pop(t, t_kapat - 0.6, 0.35))
            if t >= t_gerek - 0.1:
                chip(L, 660, 1612, "Gerekirse hukuki yol", bg=WHITE, fg=INKC, size=44, k="black",
                     scale=pop(t, t_gerek - 0.1, 0.35))
    elif t < t_daha - 0.1:
        a = wnd(t, P1, t_daha, 0.2, 0.15)
        q = pop(t, P1, 0.35)
        put_word(L, "AİLENE GÖNDER", WHITE, 540, 160, max(8, round(98 * q)), alpha=a, glow=0.35)
        if t >= t_buyuk - 0.1:
            put_word(L, "BÜYÜKLERİNE GÖSTER", GOLD, 540, 280, max(8, round(80 * pop(t, t_buyuk - 0.1, 0.3))),
                     alpha=a, glow=0.45)
    else:
        S9 = t_daha - 0.1
        a = ramp(t, S9, S9 + 0.25)
        txt(L, (540, 170), "Daha fazlası için", 64, WHITE, a, stroke=6)
        pulse = 1 + 0.045 * math.sin((t - S9) * 8) * ramp(t, S9 + 0.4, S9 + 0.7)
        chip(L, 540, 300, "TAKİP ET", bg=INKC, fg=WHITE, size=90, icon_name="bell", k="black", scale=pop(t, S9, 0.4) * pulse)


def base(t):
    if t < P0:
        cl, lt = (CL_HOOK1, t) if t < t_ve - 0.1 else (CL_HOOK2, t - (t_ve - 0.1))
        fr = cl.get(lt)
        if fr is None:
            return BGIMG.copy()
        z = 1.0 + 0.06 * (t / max(0.1, P0))
        arr = cover(fr, z).astype(np.float32) * 0.62
        return Image.fromarray(arr.astype(np.uint8)).convert("RGBA")
    if t >= P1:
        fr = CL_END.get(t - P1)
        if fr is not None:
            arr = cover(fr, 1.0 + 0.04 * (t - P1) / 6).astype(np.float32) * 0.65
            return Image.fromarray(arr.astype(np.uint8)).convert("RGBA")
    return BGIMG.copy()


class Vid(Video):
    def frame(self, t):
        im = base(t)
        if P0 <= t < P1:
            k = ramp(t, P0, P0 + 0.45)
            out = ramp(t, P1 - 0.35, P1)
            sc = 1.0 + 0.04 * math.exp(-max(0, t - (t_tani - 0.1)) * 4) * (t > t_tani - 0.1)
            draw_phone(im, t, k * (1 - out), dy=(1 - k) * u(500) + out * u(300), scale=sc)
        for c in CUTS:
            if 0 <= t - c < 0.12:
                im.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 255, int(60 * (1 - (t - c) / 0.12)))))
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
    ev = [(c, "whoosh") for c in CUTS] + [(0.05, "pop"), (t_dol - 0.1, "pop"), (t_once + 1.3, "pop"),
                                          (t_gir - 0.15, "pop"), (t_tt - 0.15, "pop"), (t_tc - 0.15, "pop"),
                                          (t_vf - 0.15, "pop"), (t_tani - 0.1, "ding"), (t_kapat - 0.6, "pop"),
                                          (t_gerek - 0.1, "pop"), (t_daha - 0.1, "pop")]
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
