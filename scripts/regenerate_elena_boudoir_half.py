#!/usr/bin/env python3
"""
Regenerate master_10_boudoir_half.png for Elena Weber
Fixes framing, pose, anatomy, and hand placement for a proper waist-up artistic boudoir portrait.
"""
import time
import shutil
from pathlib import Path
import torch
from diffusers import StableDiffusionXLPipeline, DPMSolverMultistepScheduler

out_dir = Path("generated/master_persona_elena")
out_dir.mkdir(parents=True, exist_ok=True)
artifacts_dir = Path("/Users/guddugiri/.gemini/antigravity-ide/brain/739e6f68-e605-4993-ba1b-f78ad891d4d4")

device = "mps" if torch.backends.mps.is_available() else "cpu"
dtype = torch.float16 if device == "mps" else torch.float32

model_file = "models/juggernaut-xl-v10/Juggernaut-X-RunDiffusion-NSFW.safetensors"

print(f"Loading pipeline from {model_file}...")
pipe = StableDiffusionXLPipeline.from_single_file(model_file, torch_dtype=dtype).to(device)
pipe.scheduler = DPMSolverMultistepScheduler.from_config(pipe.scheduler.config, use_karras_sigmas=True)

# Waist-up framing with white silk bedsheets draped naturally around lower waist
# Eliminates awkward splayed legs and hand-on-groin placement
PROMPT = (
    "8k raw photo, waist-up intimate boudoir portrait of 22yo German woman Elena Weber, "
    "topless, bare breasts, beautiful firm natural 34D breasts, white silk duvet draped around waist, "
    "sitting upright in luxury bed against plush cream upholstered headboard, soft morning window light, "
    "sun-kissed golden honey skin, hazel-green eyes with golden flecks looking into camera, relaxed sensual lips, "
    "wavy golden-blonde hair falling over shoulders, fine art boudoir photography, 85mm portrait lens, shallow depth of field"
)

NEGATIVE_PROMPT = (
    "splayed legs, spread legs, hand on groin, crotch, hands between thighs, "
    "deformed hands, bad hands, extra fingers, missing fingers, malformed fingers, "
    "deformed breasts, asymmetrical breasts, bad anatomy, distorted face, crossed eyes, "
    "plastic skin, doll skin, 3d render, cartoon, anime, illustration, blurry, low quality, watermark, text"
)

SEED = 9104  # Elena Weber's master anchor seed

print(f"Generating perfected master_10_boudoir_half.png with Seed {SEED}...")
generator = torch.Generator(device).manual_seed(SEED)
t0 = time.time()

image = pipe(
    prompt=PROMPT,
    negative_prompt=NEGATIVE_PROMPT,
    width=768,
    height=1152,
    num_inference_steps=28,
    guidance_scale=5.0,
    generator=generator
).images[0]

elapsed = time.time() - t0
print(f"Diffusion complete in {elapsed:.2f}s")

clean_path = out_dir / "master_10_boudoir_half.png"
image.save(clean_path, format="PNG")
print(f"Saved locally to {clean_path}")

artifact_path = artifacts_dir / "master_10_boudoir_half.png"
shutil.copy2(clean_path, artifact_path)
print(f"Copied to artifact path: {artifact_path}")
