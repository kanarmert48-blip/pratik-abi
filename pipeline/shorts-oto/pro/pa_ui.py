"""Ortak UI yardımcıları (video26'dan çıkarıldı): parlayan kelime, cam panel, yazı, pop/win, altyazı."""
import os
from functools import lru_cache
from engine import *  # noqa
GOLD = (255, 196, 64)

@lru_cache(maxsize=400)
def word_img(txt, col, size, glow=0.55):
    f = font("black", round(u(size)))
    bb = f.getbbox(txt)
    w, h = bb[2] - bb[0], bb[3] - bb[1]
    pad = round(u(size * 0.45))
    im = Image.new("RGBA", (w + 2 * pad, h + 2 * pad), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((pad - bb[0], pad - bb[1]), txt, font=f, fill=col + (255,))
    out = Image.new("RGBA", im.size, (0, 0, 0, 0))
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
    sh.putalpha(im.getchannel("A").point(lambda v: int(v * 0.6)))
    out.alpha_composite(sh.filter(ImageFilter.GaussianBlur(u(size * 0.06))), (0, round(u(size * 0.05))))
    if glow:
        g = im.filter(ImageFilter.GaussianBlur(u(size * 0.16)))
        out.alpha_composite(set_alpha(g, glow))
    out.alpha_composite(im)
    return out


def put_word(L, txt, col, cx, cy, size, scale=1.0, alpha=1.0, glow=0.55, rot=0.0):
    if alpha <= 0.01 or scale <= 0.02:
        return
    im = word_img(txt, col, size, glow)
    if abs(scale - 1) > 0.005:
        im = im.resize((max(1, round(im.width * scale)), max(1, round(im.height * scale))), Image.BICUBIC)
    if rot:
        im = im.rotate(rot, resample=Image.BICUBIC, expand=True)
    comp(L, set_alpha(im, alpha), u(cx) - im.width / 2, u(cy) - im.height / 2)


@lru_cache(maxsize=16)
def panel_img(w, h, r=56, fill=(255, 255, 255, 16), line=(255, 255, 255, 46)):
    M = round(u(60))
    im = Image.new("RGBA", (round(u(w)) + 2 * M, round(u(h)) + 2 * M), (0, 0, 0, 0))
    sh, pad = soft_shadow(round(u(w)), round(u(h)), round(u(r)), blur=round(u(26)), op=0.55)
    comp(im, sh, M - pad, M - pad + u(14))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([M, M, M + round(u(w)), M + round(u(h))], radius=round(u(r)), fill=(26, 32, 58, 235),
                        outline=line, width=round(u(3)))
    # üst parlama
    hl = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(hl).rounded_rectangle([M + 4, M + 4, M + round(u(w)) - 4, M + round(u(h * 0.5))], radius=round(u(r)),
                                         fill=(255, 255, 255, 10))
    im.alpha_composite(hl)
    return im


def panel(L, cx, cy, w, h, scale=1.0, alpha=1.0, r=56):
    if alpha <= 0.01 or scale <= 0.02:
        return
    im = panel_img(w, h, r)
    if abs(scale - 1) > 0.005:
        im = im.resize((round(im.width * scale), round(im.height * scale)), Image.BICUBIC)
    comp(L, set_alpha(im, alpha), u(cx) - im.width / 2, u(cy) - im.height / 2)


def txt(L, xy, s, size, col=WHITE, a=1.0, k="black", anchor="mm", stroke=0):
    if a <= 0.01 or size < 4:
        return
    text_c(L, xy, s, k, size, col, anchor=anchor, alpha=a, stroke=stroke, stroke_fill=(10, 12, 24))


def pop(t, t0, d=0.35):
    return eb(ph(t, t0, d))


def win(t, a, b, fi=0.25, fo=0.22):
    return eo(ph(t, a, fi)) * (1 - eio(ph(t, b - fo, fo)))



def captions(L, groups, t, y=1560, xoff=70):
    for st, en, g in groups:
        if st <= t < en:
            break
    else:
        return
    a = eo(ph(t, st, 0.12))
    f = font("black", round(u(56)))
    texts = [clean(w["w"]) for w in g]
    sp = f.getlength(" ")
    tw = sum(f.getlength(x) for x in texts) + sp * (len(texts) - 1)
    x = W / 2 - tw / 2 + u(xoff)
    tmp = Image.new("RGBA", (W, round(u(140))), (0, 0, 0, 0))
    d = ImageDraw.Draw(tmp)
    for w, tx in zip(g, texts):
        on = w["s"] - 0.04 <= t < w["e"] + 0.05
        d.text((x, tmp.height / 2), tx, font=f, fill=GOLD if on else WHITE, anchor="lm", stroke_width=round(u(6)),
               stroke_fill=(8, 10, 20))
        x += f.getlength(tx) + sp
    comp(L, set_alpha(tmp, a), 0, u(y) - tmp.height / 2)


