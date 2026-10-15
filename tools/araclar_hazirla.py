"""Araç modellerini indirir ve out/ klasörüne koyar (GitHub Actions'ta çalışır).
Çıktılar 'araclar' sürümüne (release) yüklenir; repoya commit edilmez."""
import concurrent.futures as cf, json, os, re, subprocess, sys, tarfile, urllib.request, zipfile
from pathlib import Path

OUT = Path("out"); OUT.mkdir(exist_ok=True)
UA = "PratikAbi/1.0 (https://github.com/kanarmert48-blip/pratik-abi)"
step = sys.argv[1]


def dl(url, dest):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=300) as r, open(dest, "wb") as f:
        while chunk := r.read(1 << 20):
            f.write(chunk)
    print("ok", dest, os.path.getsize(dest))


if step == "whisper":
    from huggingface_hub import snapshot_download
    p = snapshot_download("mobiuslabsgmbh/faster-whisper-large-v3-turbo", local_dir="w")
    with tarfile.open(OUT / "whisper-turbo.tar", "w") as t:
        for f in Path("w").iterdir():
            if f.is_file():
                t.add(f, arcname=f.name)

elif step == "rembg":
    base = "https://github.com/danielgatis/rembg/releases/download/v0.0.0/"
    dl(base + "isnet-general-use.onnx", OUT / "isnet-general-use.onnx")
    dl(base + "BiRefNet-general-bb_swin_v1_tiny-epoch_232.onnx", OUT / "birefnet-general-lite.onnx")

elif step == "esrgan":
    import torch, spandrel
    src = {"RealESRGAN_x4plus": "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth",
           "realesr-general-x4v3": "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesr-general-x4v3.pth"}
    for name, url in src.items():
        dl(url, f"{name}.pth")
        m = spandrel.ModelLoader().load_from_file(f"{name}.pth").model.eval()
        x = torch.rand(1, 3, 64, 64)
        kw = dict(input_names=["input"], output_names=["output"], opset_version=17,
                  dynamic_axes={"input": {2: "h", 3: "w"}, "output": {2: "h", 3: "w"}})
        try:
            torch.onnx.export(m, x, str(OUT / f"{name}.onnx"), dynamo=False, **kw)
        except TypeError:
            torch.onnx.export(m, x, str(OUT / f"{name}.onnx"), **kw)
        print("onnx", name, os.path.getsize(OUT / f"{name}.onnx"))

elif step == "lottie":
    api = "https://googlefonts.github.io/noto-emoji-animation/data/api.json"
    dl(api, "api.json")
    txt = open("api.json", encoding="utf-8").read()
    cps = sorted(set(re.findall(r'"codepoint"\s*:\s*"([0-9a-fA-F_]+)"', txt)))
    print("emoji sayısı:", len(cps))
    Path("lot").mkdir(exist_ok=True)

    def one(cp):
        try:
            dl(f"https://fonts.gstatic.com/s/e/notoemoji/latest/{cp}/lottie.json", f"lot/{cp}.json")
            return True
        except Exception as e:  # noqa
            print("yok", cp, e)
            return False

    with cf.ThreadPoolExecutor(16) as ex:
        n = sum(ex.map(one, cps))
    print("indirilen:", n)
    with zipfile.ZipFile(OUT / "noto-lottie.zip", "w", zipfile.ZIP_DEFLATED) as z:
        z.write("api.json", "api.json")
        for f in Path("lot").glob("*.json"):
            z.write(f, f"lottie/{f.name}")
