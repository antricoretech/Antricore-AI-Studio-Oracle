import os
import sys
import time
import torch
from pathlib import Path
from PIL import Image
from diffusers import StableDiffusionXLPipeline, DPMSolverMultistepScheduler

device = "mps" if torch.backends.mps.is_available() else "cpu"
dtype = torch.float16 if device == "mps" else torch.float32

out_dir = Path("generated/german_girl_glamour")
out_dir.mkdir(parents=True, exist_ok=True)

# 54-token verified prompt for German girl in black bikini dancing pose
prompt = (
    "8k raw photo, photorealistic full body portrait of 22yo German woman, "
    "athletic toned curves, slender waist, wearing a stylish luxury black bikini, "
    "radiant blue eyes, blonde hair, smiling playfully, dancing pose in modern luxury penthouse, 35mm"
)

negative_prompt = (
    "nude, bare, topless, clothes, dress, pants, shorts, fabric, "
    "deformed hands, extra fingers, missing fingers, mutated knuckles, "
    "blurry, cartoon, 3d, bad anatomy, deformed"
)

model_file = "models/juggernaut-xl-v10/Juggernaut-X-RunDiffusion-NSFW.safetensors"
out_path = out_dir / "german_girl_black_bikini.png"

print("=================================================================")
print("  GENERATING GERMAN GIRL IN BLACK BIKINI (DANCING POSE)")
print(f"  Device: {device} | Dtype: {dtype} | Resolution: 768x1152 | Seed: 444")
print("=================================================================\n")

pipe = StableDiffusionXLPipeline.from_single_file(model_file, torch_dtype=dtype).to(device)
pipe.scheduler = DPMSolverMultistepScheduler.from_config(pipe.scheduler.config, use_karras_sigmas=True)

generator = torch.Generator(device).manual_seed(444)
t0 = time.time()
image = pipe(
    prompt=prompt,
    negative_prompt=negative_prompt,
    width=768,
    height=1152,
    num_inference_steps=30,
    guidance_scale=5.0,
    generator=generator
).images[0]

image.save(str(out_path))
print(f"Generated German girl in black bikini in {time.time() - t0:.2f}s -> {out_path}")

del pipe
if device == "mps":
    torch.mps.empty_cache()
