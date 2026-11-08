from PIL import Image, ImageDraw, ImageFont, ImageEnhance
import numpy as np, sys

S = sys.argv[1]
W, H = 1080, 1920
F = "/usr/share/fonts/opentype/inter/InterDisplay-Black.otf"
src = Image.open(f"{S}/foto/kapadokya.jpg").convert("RGB")
s = max(W / src.width, H / src.height)
src = src.resize((round(src.width * s), round(src.height * s)), Image.LANCZOS)
x0, y0 = (src.width - W) // 2, (src.height - H) // 2
im = src.crop((x0, y0, x0 + W, y0 + H))
im = ImageEnhance.Contrast(ImageEnhance.Color(im).enhance(1.35)).enhance(1.12)
im = Image.fromarray(255 - np.asarray(im))
# üst kararma (yazı okunur)
g = Image.new("L", (W, H))
gd = ImageDraw.Draw(g)
for y in range(H):
    gd.line([(0, y), (W, y)], fill=int(235 * max(0.0, 1 - y / (H * 0.42)) ** 1.2))
im = Image.composite(Image.new("RGB", (W, H), (8, 9, 14)), im, g)
d = ImageDraw.Draw(im)


def T(xy, t, size, fill, stroke=10):
    d.text(xy, t, font=ImageFont.truetype(F, size), fill=fill, stroke_width=stroke, stroke_fill=(0, 0, 0), anchor="mm")


T((540, 210), "BU FOTOĞRAFA", 96, (255, 255, 255), 8)
T((540, 390), "15 SANİYE", 190, (255, 204, 70), 14)
T((540, 560), "BAK!", 190, (255, 204, 70), 14)
# orta nokta
cx, cy = 540, 1180
d.ellipse([cx - 26, cy - 26, cx + 26, cy + 26], fill=(255, 255, 255))
d.ellipse([cx - 17, cy - 17, cx + 17, cy + 17], fill=(0, 0, 0))
# alt etiket
f = ImageFont.truetype(F, 62)
t = "GERÇEK RENKLERİ GÖR"
bb = d.textbbox((0, 0), t, font=f)
w, h = bb[2] - bb[0], bb[3] - bb[1]
lab = Image.new("RGBA", (w + 70, h + 50), (0, 0, 0, 0))
ld = ImageDraw.Draw(lab)
ld.rounded_rectangle([0, 0, w + 69, h + 49], radius=22, fill=(214, 36, 36, 255))
ld.text((35, 25 - bb[1]), t, font=f, fill=(255, 255, 255))
lab = lab.rotate(-3, expand=True, resample=Image.BICUBIC)
im.paste(lab, ((W - lab.width) // 2, 1560), lab)
im.save(f"{S}/49-kapadokya_kapak.jpg", quality=92)
im.resize((360, 640)).save(f"{S}/test/kapak_small.jpg")
