"""Ağır üretim işleri (GitHub Actions'ta): müzik (MusicGen) ve Pratik Abi ağız senkronu (Wav2Lip).
Kullanım: python3 tools/uret.py <is> <jobs/klasör>   -> çıktı out/<id>_*.{wav,mp4}"""
import json, os, subprocess, sys
from pathlib import Path

is_, job = sys.argv[1], Path(sys.argv[2])
jid = job.name
ayar = json.loads((job / "ayar.json").read_text()) if (job / "ayar.json").exists() else {}
OUT = Path("out"); OUT.mkdir(exist_ok=True)


def sh(c):
    print("+", c, flush=True)
    subprocess.run(c, shell=True, check=True)


if is_ == "muzik":
    import numpy as np, scipy.io.wavfile as wf, torch
    from transformers import AutoProcessor, MusicgenForConditionalGeneration
    proc = AutoProcessor.from_pretrained("facebook/musicgen-small")
    model = MusicgenForConditionalGeneration.from_pretrained("facebook/musicgen-small")
    sr = model.config.audio_encoder.sampling_rate
    inp = proc(text=[ayar["prompt"]], padding=True, return_tensors="pt")
    with torch.no_grad():
        a = model.generate(**inp, do_sample=True, guidance_scale=3.0, max_new_tokens=int(min(30, ayar.get("sure", 30)) * 50))
    y = a[0, 0].numpy()
    need = int(ayar.get("sure", 30) * sr)
    xf = int(2.0 * sr)
    while len(y) < need:  # 30 sn'den uzunsa çapraz geçişle döngü
        seg = a[0, 0].numpy()
        r = np.linspace(0, 1, xf)
        y = np.concatenate([y[:-xf], y[-xf:] * (1 - r) + seg[:xf] * r, seg[xf:]])
    y = y[:need]
    y = y / (np.abs(y).max() + 1e-9) * 0.9
    wf.write(str(OUT / f"{jid}_muzik.wav"), sr, (y * 32767).astype(np.int16))

elif is_ == "wav2lip":
    from huggingface_hub import hf_hub_download
    sh("git clone -q https://github.com/Rudrabha/Wav2Lip.git w2l")
    # yeni librosa ile uyum
    sh("sed -i 's/librosa.filters.mel(hp.sample_rate, hp.n_fft, n_mels=hp.num_mels,/librosa.filters.mel(sr=hp.sample_rate, n_fft=hp.n_fft, n_mels=hp.num_mels,/' w2l/audio.py")
    ck = None
    for repo, fn in [("Nekochu/Wav2Lip", "wav2lip_gan.pth"), ("camenduru/Wav2Lip", "checkpoints/wav2lip_gan.pth"),
                     ("numz/wav2lip_studio", "Wav2lip/wav2lip_gan.pth"), ("rippertnt/wav2lip", "wav2lip_gan.pth")]:
        try:
            ck = hf_hub_download(repo, fn); print("ağırlık:", repo, fn); break
        except Exception as e:  # noqa
            print("yok:", repo, fn, str(e)[:120])
    assert ck, "wav2lip ağırlığı bulunamadı"
    b = ayar.get("box", [-1, -1, -1, -1])
    sh(f"cd w2l && python3 inference.py --checkpoint_path {ck} --face ../{job}/face.mp4 --audio ../{job}/voice.wav "
       f"--outfile ../out/{jid}_abi.mp4 --box {b[0]} {b[1]} {b[2]} {b[3]} --resize_factor 1 --wav2lip_batch_size 64")
