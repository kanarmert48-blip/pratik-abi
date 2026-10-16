import subprocess, torch
print(subprocess.run(["nvidia-smi"], capture_output=True, text=True).stdout)
print("cuda:", torch.cuda.is_available(), torch.cuda.get_device_name(0) if torch.cuda.is_available() else "-")
open("/kaggle/working/sonuc.txt", "w").write(f"GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'YOK'}\n")
