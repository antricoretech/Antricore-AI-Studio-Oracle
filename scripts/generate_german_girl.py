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

# 72-token strictly verified prompt for German persona
prompt = (
    "8k raw photo, photorealistic full body nude portrait of 22yo German woman, "
    "athletic toned curves, slender waist, firm bust, fair skin with light freckles. "
    "Hands resting on hips, five fingers, radiant blue eyes, blonde hair, clean natural hairline. "
    "Unclad, bare skin, luxury penthouse, soft window light, 35mm"
)

# 64-token verified negative prompt
negative_prompt = (
    "clothes, bra, panties, underwear, bodysuit, swimsuit, dress, fabric, "
    "hands on groin, pulling skin, skin string, double hairline, forehead smudge, "
    "deformed hands, extra fingers, missing fingers, mutated knuckles, "
    "blurry, cartoon, 3d, bad anatomy, deformed"
)

model_file = "models/juggernaut-xl-v10/Juggernaut-X-RunDiffusion-NSFW.safetensors"

print("=================================================================")
print("  GENERATING SAMPLE IMAGE: GERMAN GLAMOUR (JUGGERNAUT XL V10)")
print(f"  Device: {device} | Dtype: {dtype} | Resolution: 768x1152 | Seed: 777")
print("=================================================================\n")

t0 = time.time()
print("Loading Juggernaut XL v10 pipeline...")
pipe = StableDiffusionXLPipeline.from_single_file(model_file, torch_dtype=dtype).to(device)
pipe.scheduler = DPMSolverMultistepScheduler.from_config(pipe.scheduler.config, use_karras_sigmas=True)
print(f"Loaded in {time.time() - t0:.2f}s")

out_path = out_dir / "german_girl_juggernaut_v10.png"
generator = torch.Generator(device).manual_seed(777)

print("Starting generation (30 steps, guidance 5.0)...")
t_gen = time.time()
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
gen_time = time.time() - t_gen
print(f"Completed in {gen_time:.2f}s ({gen_time/30:.2f}s/step)")
print(f"Saved: {out_path}")

del pipe
if device == "mps":
    torch.mps.empty_cache()

print("\nDone generating German Glamour sample image!")
