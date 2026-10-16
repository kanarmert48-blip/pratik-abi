"""Kaggle'da GPU'lu not defteri çalıştırır (GitHub Actions'ta). Kullanım: python3 tools/kaggle_run.py kaggle/<klasör> <script.py>
Çıktılar out/ klasörüne iner."""
import json, os, subprocess, sys, time
from pathlib import Path
src, script = Path(sys.argv[1]), sys.argv[2]
def sh(c, check=True):
    print("+", c, flush=True); r = subprocess.run(c, shell=True, capture_output=True, text=True); print(r.stdout[-3000:], r.stderr[-3000:]); 
    if check and r.returncode: sys.exit(r.returncode)
    return r.stdout
# kullanıcı adını bul
user = os.environ.get("KAGGLE_USERNAME")
if not user:
    from kaggle.api.kaggle_api_extended import KaggleApi
    api = KaggleApi(); api.authenticate()
    user = api.get_config_value("username") or ""
    if not user:
        out = sh("kaggle kernels list --mine --page-size 1 --csv", check=False)
        print("liste:", out)
print("kullanıcı:", user, flush=True)
slug = "pratikabi-" + src.name
meta = {"id": f"{user}/{slug}", "title": slug, "code_file": script, "language": "python", "kernel_type": "script",
        "is_private": True, "enable_gpu": True, "enable_internet": True, "dataset_sources": [], "kernel_sources": [],
        "competition_sources": []}
(src / "kernel-metadata.json").write_text(json.dumps(meta))
sh(f"kaggle kernels push -p {src} --accelerator NvidiaTeslaT4")
t0 = time.time()
while time.time() - t0 < 3 * 3600:
    st = sh(f"kaggle kernels status {user}/{slug}", check=False)
    if any(k in st.lower() for k in ("complete", "error", "cancel")):
        break
    time.sleep(30)
os.makedirs("out", exist_ok=True)
sh(f"kaggle kernels output {user}/{slug} -p out", check=False)
