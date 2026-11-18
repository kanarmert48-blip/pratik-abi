from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
B="/home/claude/shorts-oto/assets/Baloo2.ttf"
im=Image.open('img/20.jpg').convert('RGB')
W,H=1280,720
s=max(W/im.width,H/im.height)*1.12
im=im.resize((int(im.width*s),int(im.height*s)),Image.LANCZOS)
x0=int(im.width*0.02); y0=int((im.height-H)*0.35)
im=im.crop((x0,y0,x0+W,y0+H))
im=ImageEnhance.Contrast(im).enhance(1.12); im=ImageEnhance.Color(im).enhance(1.15)
L=Image.new('RGBA',(W,H),(0,0,0,0)); d=ImageDraw.Draw(L)
# sağ tarafa koyu degrade
for x in range(W):
    a=int(max(0,(x-600)/680)*90)
    d.line([(x,0),(x,H)],fill=(10,20,50,a))
im=im.convert('RGBA'); im.alpha_composite(L)
d=ImageDraw.Draw(im)
def T(xy,s,size,fill):
    f=ImageFont.truetype(B,size)
    d.text((xy[0]+6,xy[1]+7),s,font=f,anchor='mm',fill=(0,0,0,170))
    d.text(xy,s,font=f,anchor='mm',fill=fill,stroke_width=8,stroke_fill=(15,25,60))
T((975,95),'KUTUPTA',130,(255,255,255))
T((975,225),'7 GÜN',165,(255,205,40))
# eksi 30 rozeti
f=ImageFont.truetype(B,64)
d.rounded_rectangle([960,600,1220,690],radius=45,fill=(220,40,60))
d.text((1090,646),'-30°C',font=f,anchor='mm',fill='white')
d.ellipse([985,270,1185,420],outline=(255,60,60),width=9)
im.convert('RGB').save('kapak.jpg',quality=93)
