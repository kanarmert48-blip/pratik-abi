from PIL import Image, ImageDraw, ImageFont, ImageEnhance
import sys

S = sys.argv[1]
W, H = 1280, 720
F = "/usr/share/fonts/opentype/inter/InterDisplay-Black.otf"
bg = Image.open(f"{S}/med/w_jaguar_2.jpg").convert("RGB")
s = H * 1.6 / bg.height
bg = bg.resize((int(bg.width * s), int(bg.height * s)), Image.LANCZOS)
im = Image.new("RGB", (W, H), (5, 12, 6))
im.paste(bg, (-60, -170))
im = ImageEnhance.Contrast(ImageEnhance.Color(im).enhance(1.25)).enhance(1.1)
g = Image.new("L", (W, H))
gd = ImageDraw.Draw(g)
for x in range(W):
    gd.line([(x, 0), (x, H)], fill=int(225 * max(0.0, 1 - x / (W * 0.58)) ** 0.9))
im = Image.composite(Image.new("RGB", (W, H), (5, 12, 6)), im, g)
d = ImageDraw.Draw(im)


def T(xy, txt, size, fill, stroke=10, anchor="lm"):
    f = ImageFont.truetype(F, size)
    d.text(xy, txt, font=f, fill=fill, stroke_width=stroke, stroke_fill=(0, 0, 0), anchor=anchor)


T((52, 150), "AMAZON'DA", 92, (255, 255, 255), 8)
T((36, 330), "7 GÜN", 220, (255, 212, 0), 14)
f = ImageFont.truetype(F, 58)
txt = "HAYATTA KALIR MISIN?"
bb = d.textbbox((0, 0), txt, font=f)
w, h = bb[2] - bb[0], bb[3] - bb[1]
lab = Image.new("RGBA", (w + 60, h + 44), (0, 0, 0, 0))
ld = ImageDraw.Draw(lab)
ld.rounded_rectangle([0, 0, w + 59, h + 43], radius=18, fill=(214, 36, 36, 255))
ld.text((30, 22 - bb[1]), txt, font=f, fill=(255, 255, 255))
lab = lab.rotate(3, expand=True, resample=Image.BICUBIC)
im.paste(lab, (48, 500), lab)
im.save(f"{S}/47-amazon_kapak.jpg", quality=92)
im.resize((640, 360)).save(f"{S}/test/kapak_small.jpg")
