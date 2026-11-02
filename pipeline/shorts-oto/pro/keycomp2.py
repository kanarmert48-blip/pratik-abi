"""Gerçekçi kompozit: yeşil perdedeki 3B dinozoru gerçek bir sahneye (bahçe, salon...) yerleştirir.
Ayaklar zemine oturur, sahne boyunca yürüyebilir (x0 -> x1), gölge + renk eşleme + kenar ışığı.
Kullanım: python3 keycomp2.py '<json>'
json: fg, bg, out, sc(1.0), x0(0.5), x1(x0), y(0.85: ayak çizgisi), flip(0), fgoff(0), bgoff(0), dur(0),
      fgspeed(1.0), bgblur(0), match(0.35), shadow(0.55), soft(0.6), bright(1.0)"""
import json, subprocess, sys
import numpy as np
import cv2

W, H, FPS = 1920, 1080, 30


def dur_of(p):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p],
                                capture_output=True, text=True).stdout)


def reader(path, off=0.0, blur=0, speed=1.0, loop=True):
    vf = f"setpts={1 / speed:.4f}*PTS,fps={FPS},scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}"
    if blur:
        vf += f",gblur=sigma={blur}"
    args = ["ffmpeg", "-loglevel", "error"] + (["-stream_loop", "-1"] if loop else []) + ["-ss", str(off), "-i", path,
                                                                                          "-vf", vf, "-an", "-f",
                                                                                          "rawvideo", "-pix_fmt", "rgb24",
                                                                                          "-"]
    return subprocess.Popen(args, stdout=subprocess.PIPE, bufsize=10 ** 8)


def grab(p):
    b = p.stdout.read(W * H * 3)
    if len(b) < W * H * 3:
        return None
    return np.frombuffer(b, np.uint8).reshape(H, W, 3)


def keyit(f):
    f = f.astype(np.float32)
    r, g, b = f[..., 0], f[..., 1], f[..., 2]
    mx = np.maximum(r, b)
    al = 1 - np.clip((g - mx * 1.12 - 18) / 40.0, 0, 1)
    al = cv2.erode(al, np.ones((3, 3), np.uint8))
    al = cv2.GaussianBlur(al, (0, 0), 1.0)
    f[..., 1] = np.minimum(g, mx * 1.02 + 6)
    return f, al


def main():
    c = json.loads(sys.argv[1])
    sc = c.get("sc", 1.0)
    x0 = c.get("x0", 0.5)
    x1 = c.get("x1", x0)
    yfoot = c.get("y", 0.85)
    flip = c.get("flip", 0)
    fgsp = c.get("fgspeed", 1.0)
    dur = c.get("dur", 0) or (dur_of(c["fg"]) - c.get("fgoff", 0)) / fgsp - 0.1
    nfr = int(dur * FPS)
    fg = reader(c["fg"], c.get("fgoff", 0), 0, fgsp, loop=True)
    bg = reader(c["bg"], c.get("bgoff", 0), c.get("bgblur", 0))
    enc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r",
                            str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "fast", "-crf", "14", "-pix_fmt", "yuv420p",
                            c["out"]], stdin=subprocess.PIPE)
    anchor = None
    occ = np.load(c["occ"], mmap_mode="r") if c.get("occ") else None
    match, shadow, soft, bright = c.get("match", 0.35), c.get("shadow", 0.55), c.get("soft", 0.6), c.get("bright", 1.0)
    for i in range(nfr):
        f = grab(fg)
        b = grab(bg)
        if f is None or b is None:
            break
        f, al = keyit(f)
        if flip:
            f, al = f[:, ::-1], al[:, ::-1]
        if anchor is None:
            ys, xs = np.nonzero(al > 0.5)
            anchor = (float(np.median(xs)), float(ys.max())) if len(ys) else (W / 2, H * 0.9)
        q = i / max(1, nfr - 1)
        q = q * q * (3 - 2 * q) * 0.3 + q * 0.7
        tx, ty = (x0 + (x1 - x0) * q) * W, yfoot * H
        M = np.float32([[sc, 0, tx - sc * anchor[0]], [0, sc, ty - sc * anchor[1]]])
        fs = cv2.warpAffine(f, M, (W, H), flags=cv2.INTER_LINEAR, borderValue=0)
        als = cv2.warpAffine(al, M, (W, H), flags=cv2.INTER_LINEAR, borderValue=0)
        if c.get("ymax"):
            ym = int(c["ymax"] * H)
            fade = np.clip((ym - np.arange(H, dtype=np.float32)) / 6.0, 0, 1)[:, None]
            als = als * fade
        om = None
        if occ is not None:
            om = cv2.resize(np.asarray(occ[min(i, len(occ) - 1)]), (W, H)).astype(np.float32) / 255.0
            om = cv2.GaussianBlur(om, (0, 0), 1.2)
            als = als * (1 - om)
        if soft:
            fs = cv2.GaussianBlur(fs, (0, 0), soft)
        base = b.astype(np.float32)
        ys, xs = np.nonzero(als > 0.5)
        if len(ys) > 50 and (shadow or match):
            y1 = ys.max()
            xa, xb = np.percentile(xs, 4), np.percentile(xs, 96)
            sh = np.zeros((H, W), np.float32)
            cv2.ellipse(sh, (int((xa + xb) / 2), int(y1 - 4)), (max(4, int((xb - xa) * 0.45)), max(6, int(sc * 30))), 0, 0,
                        360, 1.0, -1)
            sh = cv2.resize(cv2.GaussianBlur(cv2.resize(sh, (W // 4, H // 4)), (0, 0), max(1.5, sc * 5)), (W, H))
            # silüetten aşağı doğru yumuşak gölge (sahne ışığı tepeden)
            sil = cv2.resize(cv2.GaussianBlur(cv2.resize(als, (W // 4, H // 4)), (0, 0), 6), (W, H))
            sil = np.roll(sil, int(20 * sc), axis=0) * 0.35
            shm = shadow * np.clip(sh + sil * (np.arange(H)[:, None] > y1 - 160 * sc), 0, 1)
            if om is not None:
                shm = shm * (1 - om)
            base *= (1 - shm)[..., None]
            # renk eşleme
            m = als > 0.6
            fm = fs[m].mean(axis=0) + 1e-3
            bm = b.reshape(-1, 3).mean(axis=0) + 1e-3
            lum_f, lum_b = fm.mean(), bm.mean()
            gain = (1 - match) + match * (bm / bm.mean()) / (fm / fm.mean())
            lg = (1 - match) + match * np.clip(lum_b / lum_f, 0.6, 1.4)
            fs = fs * gain * lg * bright
            # kenar ışığı (arka plan rengi kenarlara sızar)
            edge = np.clip(als - cv2.erode(als, np.ones((9, 9), np.uint8)), 0, 1)[..., None]
            bb = cv2.resize(cv2.GaussianBlur(cv2.resize(base, (W // 4, H // 4)), (0, 0), 3), (W, H))
            fs = fs * (1 - 0.35 * edge) + bb * 0.35 * edge
        out_f = base * (1 - als[..., None]) + fs * als[..., None]
        enc.stdin.write(np.clip(out_f, 0, 255).astype(np.uint8).tobytes())
    enc.stdin.close()
    enc.wait()
    fg.kill()
    bg.kill()


if __name__ == "__main__":
    main()
