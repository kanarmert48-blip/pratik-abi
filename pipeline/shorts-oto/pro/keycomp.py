"""Yeşil perde klibini (3B dinozor) bulanık, kararmış orman arka planına oturtur; ayak altına yumuşak gölge ekler.
Kullanım: python3 keycomp.py <yesil.mp4> <arka.mp4> <cikis.mp4> [sc=1.0] [x=0.5] [y=0.5] [flip=0] [bgoff=0] [dur=0]"""
import subprocess, sys
import numpy as np
import cv2

W, H, FPS = 1920, 1080, 30


def reader(path, off=0.0, blur=0):
    vf = f"fps={FPS},scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}"
    if blur:
        vf += f",gblur=sigma={blur}"
    return subprocess.Popen(["ffmpeg", "-loglevel", "error", "-stream_loop", "-1", "-ss", str(off), "-i", path, "-vf", vf,
                             "-an", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE, bufsize=10 ** 8)


def grab(p):
    b = p.stdout.read(W * H * 3)
    if len(b) < W * H * 3:
        return None
    return np.frombuffer(b, np.uint8).reshape(H, W, 3)


def main():
    a = sys.argv
    fg_path, bg_path, out = a[1], a[2], a[3]
    sc = float(a[4]) if len(a) > 4 else 1.0
    px = float(a[5]) if len(a) > 5 else 0.5
    py = float(a[6]) if len(a) > 6 else 0.5
    flip = int(a[7]) if len(a) > 7 else 0
    bgoff = float(a[8]) if len(a) > 8 else 0.0
    dur = float(a[9]) if len(a) > 9 else 0.0
    bgblur = float(a[10]) if len(a) > 10 else 14
    dark = float(a[11]) if len(a) > 11 else 0.62
    nfr = int(float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", fg_path],
                                   capture_output=True, text=True).stdout) * FPS) - 2
    if dur:
        nfr = min(nfr, int(dur * FPS))
    fg = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-i", fg_path, "-vf", f"fps={FPS},scale={W}:{H}", "-an", "-f",
                           "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE, bufsize=10 ** 8)
    bg = reader(bg_path, bgoff, blur=bgblur)
    enc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r",
                            str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "fast", "-crf", "14", "-pix_fmt", "yuv420p", out],
                           stdin=subprocess.PIPE)
    yy = np.linspace(0, 1, H, dtype=np.float32)[:, None]
    xx = np.linspace(-1, 1, W, dtype=np.float32)[None, :]
    floor = (1 - 0.55 * np.clip((yy - 0.55) / 0.45, 0, 1)) * (1 - 0.25 * xx ** 2)  # alt ve kenarlar koyu
    spot = 1 + 0.18 * np.exp(-((xx - (px * 2 - 1)) ** 2) / 0.35 - ((yy - 0.55) ** 2) / 0.25)
    shade = (floor * spot * dark)[..., None]
    for i in range(nfr):
        f = grab(fg)
        b = grab(bg)
        if f is None or b is None:
            break
        f = f.astype(np.float32)
        r, g, bl = f[..., 0], f[..., 1], f[..., 2]
        mx = np.maximum(r, bl)
        key = np.clip((g - mx * 1.12 - 18) / 40.0, 0, 1)  # 1 = perde
        al = 1 - key
        al = cv2.erode(al, np.ones((3, 3), np.uint8))
        al = cv2.GaussianBlur(al, (0, 0), 1.0)
        f[..., 1] = np.minimum(g, mx * 1.02 + 6)  # yeşil taşma temizliği
        if flip:
            f = f[:, ::-1]
            al = al[:, ::-1]
        # ölçek + konum
        M = np.float32([[sc, 0, W * px - sc * W / 2], [0, sc, H * py - sc * H / 2]])
        fs = cv2.warpAffine(f, M, (W, H), flags=cv2.INTER_LINEAR, borderValue=0)
        als = cv2.warpAffine(al, M, (W, H), flags=cv2.INTER_LINEAR, borderValue=0)
        base = b.astype(np.float32) * shade
        # gölge: siluetin alt kısmı
        ys, xs = np.nonzero(als > 0.5)
        if len(ys):
            y1 = ys.max()
            x0, x1 = np.percentile(xs, 3), np.percentile(xs, 97)
            sh = np.zeros((H, W), np.float32)
            cv2.ellipse(sh, (int((x0 + x1) / 2), int(y1 - 6)), (int((x1 - x0) * 0.42), 26), 0, 0, 360, 1.0, -1)
            sh = cv2.GaussianBlur(sh, (0, 0), 22)
            base *= (1 - 0.62 * sh)[..., None]
        # hafif renk eşleme: önü sıcak-koyu tona yaklaştır
        fs = fs * np.float32([0.93, 0.95, 0.92]) + base.mean(axis=(0, 1)) * 0.06
        out_f = base * (1 - als[..., None]) + fs * als[..., None]
        enc.stdin.write(np.clip(out_f, 0, 255).astype(np.uint8).tobytes())
    enc.stdin.close()
    enc.wait()
    fg.kill()
    bg.kill()


if __name__ == "__main__":
    main()
