"""Depth Anything V2 (ONNX) ve CLIP (ONNX'e çevrilir) modellerini hazırlar -> out/ (GitHub Actions'ta)."""
import os, sys
from pathlib import Path

OUT = Path("out"); OUT.mkdir(exist_ok=True)
step = sys.argv[1]

if step == "depth":
    from huggingface_hub import hf_hub_download
    p = hf_hub_download("onnx-community/depth-anything-v2-small", "onnx/model.onnx")
    os.system(f"cp {p} {OUT}/depth-anything-v2-small.onnx")

elif step == "clip":
    import torch
    from transformers import CLIPModel, CLIPTokenizerFast
    name = "openai/clip-vit-base-patch32"
    m = CLIPModel.from_pretrained(name).eval()
    tok = CLIPTokenizerFast.from_pretrained(name)
    tok.backend_tokenizer.save(str(OUT / "clip-tokenizer.json"))

    class Img(torch.nn.Module):
        def forward(self, pixel_values):
            return m.get_image_features(pixel_values=pixel_values)

    class Txt(torch.nn.Module):
        def forward(self, input_ids, attention_mask):
            return m.get_text_features(input_ids=input_ids, attention_mask=attention_mask)

    torch.onnx.export(Img(), (torch.rand(1, 3, 224, 224),), str(OUT / "clip-image.onnx"), input_names=["pixel_values"],
                      output_names=["emb"], dynamic_axes={"pixel_values": {0: "b"}, "emb": {0: "b"}}, opset_version=17)
    ids = tok(["a photo"], padding="max_length", max_length=77, return_tensors="pt")
    torch.onnx.export(Txt(), (ids["input_ids"], ids["attention_mask"]), str(OUT / "clip-text.onnx"),
                      input_names=["input_ids", "attention_mask"], output_names=["emb"],
                      dynamic_axes={"input_ids": {0: "b"}, "attention_mask": {0: "b"}, "emb": {0: "b"}}, opset_version=17)
    print("clip ok")
