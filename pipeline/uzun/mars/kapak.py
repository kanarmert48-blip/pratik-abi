from PIL import Image, ImageDraw, ImageFilter, ImageFont
import numpy as np
from shots import *

s, c = surface()
bg_mars_day(c, 1, hz=820, sun=None)
fg_mars(c, 4, 1260)
# Dünya: gökyüzünde küçük mavi nokta
c.set_source(rgrad(c, 1200, 330, 0, 60, [(0, M, 0.7), (1, M, 0)])); c.paint()
c.arc(1200, 330, 10, 0, 6.283); col(c, mix(M, WH, 0.5)); c.fill()
character(c, 760, 2050, 3.4, 0, pose='stand', look=(0.6, -0.4), smile=1.0, brow=0.6, arms=(-0.1, 2.25))
# bilet
c.save(); c.translate(1420, 880); c.rotate(-0.22)
rrect(c, -230 + 10, -110 + 14, 460, 220, 22); col(c, BK, 0.3); c.fill()
rrect(c, -230, -110, 460, 220, 22); col(c, L); c.fill()
c.rectangle(-230, -110, 70, 220); col(c, A); c.fill()
label(c, 'MARS', -130, 0, 'num', D, 'l', 1)
c.restore()
c.arc(1255, 1007, 68, 0, 6.283); col(c, SUIT_DK); c.fill()
im = to_pil(s)
d = ImageDraw.Draw(im)
f = ImageFont.truetype('/home/claude/shorts-oto/assets/fonts/BarlowSemiCondensed-SemiBold.ttf', 240)
f2 = ImageFont.truetype('/home/claude/shorts-oto/assets/fonts/BarlowSemiCondensed-SemiBold.ttf', 240)
lay = Image.new('RGBA', im.size, (0, 0, 0, 0))
dl = ImageDraw.Draw(lay)
for (txt, y, colr) in [('TEK YÖN', 120, (232, 228, 218)), ('BİLET', 380, (232, 228, 218))]:
    dl.text((1640 + 8, y + 10), txt, font=f, fill=(0, 0, 0, 150))
lay = lay.filter(ImageFilter.GaussianBlur(8))
im = im.convert('RGBA'); im.alpha_composite(lay)
d = ImageDraw.Draw(im)
d.text((1640, 120), 'TEK YÖN', font=f, fill=(232, 228, 218))
d.text((1640, 380), 'BİLET', font=f2, fill=(15, 26, 36))
im = im.convert('RGB').resize((1280, 720), Image.LANCZOS)
im.save('kapak.jpg', quality=92)
im.resize((320, 180), Image.LANCZOS).save('test/kapak_kucuk.jpg')
