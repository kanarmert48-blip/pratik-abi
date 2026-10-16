"""Wan 2.1 T2V 1.3B ile dikey sahneler (2 GPU paralel) + Real-ESRGAN 3x büyütme. Çıktı: /kaggle/working/<ad>.mp4"""
import os, subprocess, sys, json, time
subprocess.run("pip uninstall -y -q torchao; pip install -q -U diffusers transformers accelerate ftfy spandrel imageio imageio-ffmpeg", shell=True)
import torch, multiprocessing as mp

PROMPTS = {
 "b_mutfak": "A dark kitchen at night, a white refrigerator standing against the wall, faint light leaking from the edge of the refrigerator door, slow camera push toward the refrigerator, eerie suspense, cinematic, photorealistic",
 "d_petek": "A white aluminum sectional column radiator mounted on the wall under a window in a dark bedroom at night, cold moonlight on the radiator fins, slow cinematic camera push-in, quiet suspense, photorealistic",
 "f_kedi": "A cute cat sleeping peacefully curled up on a cozy bed at night, warm soft lamp light, gentle breathing, calm cozy atmosphere, slow camera move, photorealistic",
 "g_raf": "Inside of an open refrigerator at night, interior light on, white plastic shelves and transparent plastic drawers, a few food containers, slow camera push-in, cinematic, photorealistic",
}
NEG = "bright, overexposed, text, watermark, subtitles, deformed, distorted, blurry, low quality, static, cartoon, people"

def encode():
    from diffusers import WanPipeline
    pipe = WanPipeline.from_pretrained("Wan-AI/Wan2.1-T2V-1.3B-Diffusers", transformer=None, vae=None, torch_dtype=torch.float16)
    pipe.text_encoder.to("cuda:0")
    out = {}
    with torch.no_grad():
        for n, p in PROMPTS.items():
            pe, ne = pipe.encode_prompt(prompt=p, negative_prompt=NEG, do_classifier_free_guidance=True, max_sequence_length=512, device="cuda:0")
            out[n] = (pe.cpu(), ne.cpu())
    torch.save(out, "/kaggle/emb.pt")
    print("metin kodlandı", flush=True)


def run(gpu, names):
    torch.cuda.set_device(gpu)
    from diffusers import AutoencoderKLWan, WanPipeline
    from diffusers.utils import export_to_video
    mid = "Wan-AI/Wan2.1-T2V-1.3B-Diffusers"
    vae = AutoencoderKLWan.from_pretrained(mid, subfolder="vae", torch_dtype=torch.float32)
    dt = torch.float16
    pipe = WanPipeline.from_pretrained(mid, vae=vae, text_encoder=None, tokenizer=None, torch_dtype=dt).to(f"cuda:{gpu}")
    emb = torch.load("/kaggle/emb.pt")
    import spandrel, numpy as np, imageio
    sr = spandrel.ModelLoader().load_from_file("/kaggle/working/esr.pth").model.eval().to(f"cuda:{gpu}").half()
    for n in names:
        t = time.time()
        g = torch.Generator(device="cpu").manual_seed(7)
        pe, ne = emb[n]
        fr = pipe(prompt_embeds=pe.to(f"cuda:{gpu}"), negative_prompt_embeds=ne.to(f"cuda:{gpu}"), height=832, width=480, num_frames=65, guidance_scale=5.0,
                  num_inference_steps=30, generator=g, output_type="np").frames[0]
        if not np.isfinite(fr).all() or fr.max() < 0.02:
            print("UYARI fp16 bozuk", n, flush=True)
        export_to_video(list(fr), f"/kaggle/working/raw_{n}.mp4", fps=16)
        # 3x büyüt (Real-ESRGAN general x4v3 -> 1440x2496 sonra kırp/ölçekle)
        w = imageio.get_writer(f"/kaggle/working/{n}.mp4", fps=16, codec="libx264", quality=9, macro_block_size=1)
        with torch.no_grad():
            for f in fr:
                x = torch.from_numpy(np.ascontiguousarray(f.transpose(2, 0, 1))).unsqueeze(0).to(f"cuda:{gpu}").half()
                y = sr(x).clamp(0, 1)
                y = torch.nn.functional.interpolate(y.float(), size=(2496, 1440), mode="bicubic", align_corners=False)
                w.append_data((y[0].permute(1, 2, 0).cpu().numpy() * 255).astype(np.uint8))
        w.close()
        print("tamam", n, round(time.time() - t), "sn", flush=True)

if __name__ == "__main__":
    subprocess.run("wget -q -O /kaggle/working/esr.pth https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesr-general-x4v3.pth", shell=True)
    names = list(PROMPTS)
    n = torch.cuda.device_count(); print("GPU sayısı", n, flush=True)
    mp.set_start_method("spawn")
    e = mp.Process(target=encode); e.start(); e.join()
    names = ["b_mutfak", "f_kedi", "d_petek", "g_raf"]
    ps = [mp.Process(target=run, args=(g, names[g * 2:(g + 1) * 2] if n > 1 else names)) for g in range(n)]
    [p.start() for p in ps]; [p.join() for p in ps]
    os.remove("/kaggle/working/esr.pth"); [os.remove(f"/kaggle/working/{f}") for f in os.listdir("/kaggle/working") if f.startswith("raw_")]
    print(os.listdir("/kaggle/working"))
