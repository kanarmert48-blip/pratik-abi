"""Açık kaynak yardımcı araçlar (modeller /home/claude/araclar altında, ~/.u2net'te).

transcribe(ses)          -> faster-whisper ile kelime zamanları + telaffuz kontrolü
cutout(resim)            -> rembg (isnet) ile arka planı sil, RGBA
upscale(resim, hedef_w)  -> Real-ESRGAN (ONNX) ile netleştirerek büyüt
Lottie(kod)              -> Noto animasyonlu emoji kareleri (rlottie)
manim_render(...)        -> Manim sahnesini şeffaf video olarak çiz
"""
import functools, json, os, subprocess
from pathlib import Path

import numpy as np
from PIL import Image

ARAC = Path("/home/claude/araclar")


# ---------------- faster-whisper ----------------
@functools.lru_cache(1)
def _whisper():
    from faster_whisper import WhisperModel
    return WhisperModel(str(ARAC / "whisper-turbo"), device="cpu", compute_type="int8", cpu_threads=os.cpu_count())


def load_audio(path, sr=16000):
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(path), "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32)


def transcribe(path, lang="tr", prompt=None):
    """[{'w','s','e','p'}] — p: modelin emin olma oranı (düşükse telaffuz şüpheli)."""
    segs, _ = _whisper().transcribe(load_audio(path), language=lang, word_timestamps=True, beam_size=5,
                                    initial_prompt=prompt, condition_on_previous_text=False)
    return [{"w": w.word.strip(), "s": round(w.start, 3), "e": round(w.end, 3), "p": round(w.probability, 3)}
            for s in segs for w in s.words]


def check_pronunciation(path, script, lang="tr"):
    """Metindeki kelimelerle duyulanı karşılaştırır, farklı / şüpheli olanları döndürür."""
    import difflib, re
    norm = lambda s: re.sub(r"[^\wçğıöşüâîû']", "", s.lower().replace("I", "ı").replace("İ", "i"))
    heard = transcribe(path, lang)
    a = [norm(x) for x in script.split() if norm(x)]
    b = [norm(w["w"]) for w in heard]
    out = []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if op != "equal":
            out.append({"metin": " ".join(a[i1:i2]), "duyulan": " ".join(b[j1:j2]),
                        "zaman": heard[j1]["s"] if j1 < len(heard) else None})
    out += [{"metin": w["w"], "duyulan": w["w"], "zaman": w["s"], "emin": w["p"]} for w in heard if w["p"] < 0.45]
    return out


# ---------------- rembg ----------------
@functools.lru_cache(2)
def _rembg(model):
    from rembg import new_session
    return new_session(model)


def cutout(src, dst=None, model="isnet-general-use", alpha_matting=False):
    from rembg import remove
    im = Image.open(src).convert("RGB") if not isinstance(src, Image.Image) else src.convert("RGB")
    out = remove(im, session=_rembg(model), alpha_matting=alpha_matting, post_process_mask=True)
    if dst:
        out.save(dst)
    return out


def sticker(rgba, border=14, col=(255, 255, 255), shadow=True):
    """Kesik görsele beyaz çerçeve + gölge (çıkartma görünümü)."""
    from PIL import ImageFilter
    pad = border * 3
    a = Image.new("L", (rgba.width + 2 * pad, rgba.height + 2 * pad), 0)
    a.paste(rgba.getchannel("A"), (pad, pad))
    edge = a.filter(ImageFilter.MaxFilter(border * 2 + 1)).filter(ImageFilter.GaussianBlur(1.2))
    out = Image.new("RGBA", a.size, (0, 0, 0, 0))
    if shadow:
        sh = Image.new("RGBA", a.size, (0, 0, 0, 0))
        sh.putalpha(edge.point(lambda v: int(v * 0.45)).filter(ImageFilter.GaussianBlur(10)))
        out.alpha_composite(sh, (4, 10))
    bd = Image.new("RGBA", a.size, col + (0,))
    bd.putalpha(edge)
    out.alpha_composite(bd)
    out.alpha_composite(rgba, (pad, pad))
    return out


# ---------------- Real-ESRGAN ----------------
@functools.lru_cache(2)
def _esr(model):
    import onnxruntime as ort
    o = ort.SessionOptions()
    o.intra_op_num_threads = os.cpu_count()
    return ort.InferenceSession(str(ARAC / f"{model}.onnx"), o, providers=["CPUExecutionProvider"])


def upscale(src, dst=None, target_w=None, model="realesr-general-x4v3", tile=256, pad=12):
    """4x büyütür (döşemeli), istenirse target_w genişliğine küçültür.
    model: realesr-general-x4v3 (hızlı, fotoğraf) | RealESRGAN_x4plus (yavaş, daha keskin)."""
    im = Image.open(src).convert("RGB") if not isinstance(src, Image.Image) else src.convert("RGB")
    x = np.asarray(im, np.float32).transpose(2, 0, 1) / 255.0
    _, H, W = x.shape
    S = 4
    out = np.zeros((3, H * S, W * S), np.float32)
    sess = _esr(model)
    for y0 in range(0, H, tile):
        for x0 in range(0, W, tile):
            y1, x1 = min(y0 + tile, H), min(x0 + tile, W)
            ya, xa, yb, xb = max(0, y0 - pad), max(0, x0 - pad), min(H, y1 + pad), min(W, x1 + pad)
            r = sess.run(None, {"input": x[None, :, ya:yb, xa:xb]})[0][0]
            out[:, y0 * S:y1 * S, x0 * S:x1 * S] = r[:, (y0 - ya) * S:(y1 - ya) * S, (x0 - xa) * S:(x1 - xa) * S]
    res = Image.fromarray((np.clip(out, 0, 1).transpose(1, 2, 0) * 255 + 0.5).astype(np.uint8))
    if target_w and res.width != target_w:
        res = res.resize((target_w, round(res.height * target_w / res.width)), Image.LANCZOS)
    if dst:
        res.save(dst, quality=94)
    return res


# ---------------- Noto animasyonlu emoji ----------------
NOTO = ARAC / "noto"


def noto_find(word):
    """İsim/etiketle emoji kodu bul: noto_find('thinking') -> ['1f914', ...]"""
    api = json.load(open(NOTO / "api.json", encoding="utf-8"))
    icons = api.get("icons", api) if isinstance(api, dict) else api
    word = word.lower().replace(" ", "-")
    exact, part = [], []
    for ic in icons:
        tags = [x.strip(":").lower() for x in ic.get("tags", [])]
        (exact if word in tags else part if any(word in x for x in tags) else []).append((ic["codepoint"], tags[0] if tags else ""))
    return exact + part


class Lottie:
    """Noto animasyonlu emoji. frame(t, size) -> RGBA PIL (döngülü)."""

    def __init__(self, code):
        from rlottie_python import LottieAnimation
        self.anim = LottieAnimation.from_file(str(NOTO / "lottie" / f"{code}.json"))
        self.n = self.anim.lottie_animation_get_totalframe()
        self.fps = self.anim.lottie_animation_get_framerate()
        self.cache = {}

    def frame(self, t, size):
        i = int(t * self.fps) % self.n
        k = (i, size)
        if k not in self.cache:
            self.cache[k] = self.anim.render_pillow_frame(frame_num=i, width=size, height=size)
        return self.cache[k]


# ---------------- Manim ----------------
def manim_render(py_file, scene, out_dir, quality="h", transparent=True, fps=30, size=None):
    """Manim sahnesini çizer. Şeffaf ise .mov (qtrle) çıkar; yolunu döndürür."""
    args = ["manim", "render", f"-q{quality}", "--fps", str(fps), "--media_dir", str(out_dir), "--disable_caching"]
    if transparent:
        args.append("--transparent")
    if size:
        args += ["-r", f"{size[0]},{size[1]}"]
    subprocess.run(args + [str(py_file), scene], check=True, capture_output=True)
    vids = sorted(Path(out_dir).rglob(f"{scene}.mov" if transparent else f"{scene}.mp4"), key=os.path.getmtime)
    return str(vids[-1])


# ---------------- Depth Anything V2 (2.5D hareket) ----------------
@functools.lru_cache(1)
def _depth_sess():
    import onnxruntime as ort
    o = ort.SessionOptions(); o.intra_op_num_threads = os.cpu_count()
    return ort.InferenceSession(str(ARAC / "depth-anything-v2-small.onnx"), o, providers=["CPUExecutionProvider"])


def depth_map(img, size=518):
    """0 (uzak) .. 1 (yakın) derinlik haritası, görüntüyle aynı boyutta (float32)."""
    im = img.convert("RGB") if isinstance(img, Image.Image) else Image.open(img).convert("RGB")
    x = np.asarray(im.resize((size, size), Image.BICUBIC), np.float32) / 255.0
    x = (x - [0.485, 0.456, 0.406]) / [0.229, 0.224, 0.225]
    sess = _depth_sess()
    d = sess.run(None, {sess.get_inputs()[0].name: x.transpose(2, 0, 1)[None].astype(np.float32)})[0]
    d = np.squeeze(d).astype(np.float32)
    d = (d - d.min()) / (d.max() - d.min() + 1e-6)
    return np.asarray(Image.fromarray(d).resize(im.size, Image.BICUBIC), np.float32)


def parallax_video(src, out, dur=5.0, size=1344, fps=30, move=0.035, zoom=0.07, direction=1):
    """Fotoğraftan 3D kamera hareketli video (yakın nesneler daha çok kayar)."""
    import cv2
    im = Image.open(src).convert("RGB") if not isinstance(src, Image.Image) else src.convert("RGB")
    w, h = im.size
    s = size / min(w, h) * (1 + zoom + move * 2)  # kenar boşluğu payı
    im = im.resize((round(w * s), round(h * s)), Image.LANCZOS)
    W_, H_ = im.size
    arr = np.asarray(im)
    d = cv2.GaussianBlur(depth_map(im), (0, 0), 6)
    yy, xx = np.mgrid[0:H_, 0:W_].astype(np.float32)
    cx, cy = W_ / 2, H_ / 2
    x0, y0 = int(cx - size / 2), int(cy - size / 2)
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{size}x{size}",
                          "-r", str(fps), "-i", "-", "-c:v", "libx264", "-crf", "14", "-pix_fmt", "yuv420p", str(out)],
                         stdin=subprocess.PIPE)
    n = int(round(dur * fps))
    for i in range(n):
        q = i / max(1, n - 1)
        e = q * q * (3 - 2 * q)
        dx = direction * move * size * (e - 0.5) * 2
        z = 1 + zoom * e * (0.35 + 0.65 * d)
        mx = cx + (xx - cx) / z - dx * d
        my = cy + (yy - cy) / z
        fr = cv2.remap(arr, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        p.stdin.write(np.ascontiguousarray(fr[y0:y0 + size, x0:x0 + size]).tobytes())
    p.stdin.close(); p.wait()
    return str(out)


# ---------------- CLIP (görsel-metin eşleştirme) ----------------
@functools.lru_cache(1)
def _clip():
    import onnxruntime as ort
    from tokenizers import Tokenizer
    o = ort.SessionOptions(); o.intra_op_num_threads = os.cpu_count()
    mk = lambda n: ort.InferenceSession(str(ARAC / n), o, providers=["CPUExecutionProvider"])
    return mk("clip-image.onnx"), mk("clip-text.onnx"), Tokenizer.from_file(str(ARAC / "clip-tokenizer.json"))


def _clip_img(path):
    if str(path).endswith((".mp4", ".mov", ".webm")):
        dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                                   capture_output=True, text=True).stdout or 1)
        raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-ss", str(dur / 2), "-i", str(path), "-frames:v", "1",
                              "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True).stdout
        import io
        im = Image.open(io.BytesIO(raw)).convert("RGB")
    else:
        im = Image.open(path).convert("RGB")
    w, h = im.size; s = 224 / min(w, h)
    im = im.resize((max(224, round(w * s)), max(224, round(h * s))), Image.BICUBIC)
    l, t = (im.width - 224) // 2, (im.height - 224) // 2
    x = np.asarray(im.crop((l, t, l + 224, t + 224)), np.float32) / 255.0
    x = (x - [0.48145466, 0.4578275, 0.40821073]) / [0.26862954, 0.26130258, 0.27577711]
    return x.transpose(2, 0, 1).astype(np.float32)


def clip_rank(paths, text):
    """Görselleri (foto/video) İngilizce açıklamaya benzerliğe göre sıralar: [(puan, yol), ...]"""
    si, st, tok = _clip()
    enc = tok.encode(text)
    ids = enc.ids[:77]; mask = [1] * len(ids)
    ids += [49407] * (77 - len(ids)); mask += [0] * (77 - len(mask))
    te = st.run(None, {"input_ids": np.array([ids], np.int64), "attention_mask": np.array([mask], np.int64)})[0][0]
    te /= np.linalg.norm(te)
    out = []
    for p in paths:
        try:
            ie = si.run(None, {"pixel_values": _clip_img(p)[None]})[0][0]
            out.append((float(ie @ te / np.linalg.norm(ie)), str(p)))
        except Exception as e:  # noqa
            print("atlandı", p, e)
    return sorted(out, reverse=True)
