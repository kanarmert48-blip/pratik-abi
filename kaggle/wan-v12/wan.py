"""Wan 2.1 T2V 1.3B ile dikey sahneler (2 GPU paralel) + Real-ESRGAN 3x büyütme. Çıktı: /kaggle/working/<ad>.mp4"""
import os, subprocess, sys, json, time
subprocess.run("pip uninstall -y -q torchao; pip install -q -U diffusers transformers accelerate ftfy spandrel imageio imageio-ffmpeg", shell=True)
import torch, multiprocessing as mp

PROMPTS = {
 "a_koridor": "A dark quiet apartment hallway at night, pale blue moonlight coming through a window, long shadows on the walls, slow cinematic dolly forward, eerie suspense atmosphere, photorealistic, film grain",
 "b_mutfak": "A dark kitchen at night, a white refrigerator standing against the wall, faint light leaking from the edge of the refrigerator door, slow camera push toward the refrigerator, eerie suspense, cinematic, photorealistic",
 "c_buz": "Extreme close-up of white frost and ice slowly melting on the cold inner wall of a freezer, water droplets forming and dripping down, soft cool light, macro photography, photorealistic",
 "d_petek": "An old white metal radiator under a window in a dark bedroom at night, moonlight on the radiator fins, slow cinematic camera push-in, quiet suspense, photorealistic",
 "e_parke": "Low angle shot of an empty dark wooden parquet floor in a hallway at night, moonlight streaks across the floorboards, a door slightly open in the background, slow camera glide forward, eerie, cinematic, photorealistic",
 "f_kedi": "A cute cat sleeping peacefully curled up on a cozy bed at night, warm soft lamp light, gentle breathing, calm cozy atmosphere, slow camera move, photorealistic",
}
NEG = "bright, overexposed, text, watermark, subtitles, deformed, distorted, blurry, low quality, static, cartoon, people"

def run(gpu, names):
    torch.cuda.set_device(gpu)
    from diffusers import AutoencoderKLWan, WanPipeline
    from diffusers.utils import export_to_video
    mid = "Wan-AI/Wan2.1-T2V-1.3B-Diffusers"
    vae = AutoencoderKLWan.from_pretrained(mid, subfolder="vae", torch_dtype=torch.float32)
    dt = torch.float16
    pipe = WanPipeline.from_pretrained(mid, vae=vae, torch_dtype=dt)
    pipe.enable_model_cpu_offload(gpu_id=gpu)
    import spandrel, numpy as np, imageio
    sr = spandrel.ModelLoader().load_from_file("/kaggle/working/esr.pth").model.eval().to(f"cuda:{gpu}").half()
    for n in names:
        t = time.time()
        g = torch.Generator(device="cpu").manual_seed(7)
        fr = pipe(prompt=PROMPTS[n], negative_prompt=NEG, height=832, width=480, num_frames=65, guidance_scale=5.0,
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
    ps = [mp.Process(target=run, args=(g, names[g::n])) for g in range(n)]
    [p.start() for p in ps]; [p.join() for p in ps]
    os.remove("/kaggle/working/esr.pth"); [os.remove(f"/kaggle/working/{f}") for f in os.listdir("/kaggle/working") if f.startswith("raw_")]
    print(os.listdir("/kaggle/working"))
