#!/usr/bin/env python3
"""
Regenerate true 180-degree rear turnaround shot for Maya Bhutia with zero face visible
"""
from pathlib import Path
import shutil
import torch
from diffusers import StableDiffusionXLPipeline, DPMSolverMultistepScheduler

device = "mps" if torch.backends.mps.is_available() else "cpu"
dtype = torch.float16 if device == "mps" else torch.float32

model_file = "models/juggernaut-xl-v10/Juggernaut-X-RunDiffusion-NSFW.safetensors"
pipe = StableDiffusionXLPipeline.from_single_file(model_file, torch_dtype=dtype).to(device)
pipe.scheduler = DPMSolverMultistepScheduler.from_config(pipe.scheduler.config, use_karras_sigmas=True)

out_dir = Path("generated/master_persona_maya")
artifacts_dir = Path("/Users/guddugiri/.gemini/antigravity-ide/brain/739e6f68-e605-4993-ba1b-f78ad891d4d4")

# Strict 180 rear prompt
prompt = (
    "8k raw photo, shot directly from behind at 180 degrees, complete rear back view of a 24yo woman, "
    "facing completely away from camera towards the back wall, showing the back of the head with long silky obsidian black hair cascading straight down the center of upper back, "
    "wearing black ribbed sleeveless top, showing back of neck, bare arms, athletic shoulder blades, slim 24-inch waist from behind, "
    "clean neutral grey studio backdrop, 50mm portrait lens"
)

# Explicitly ban face, eyes, looking back, profile in negative prompt
negative_prompt = (
    "face, eyes, mouth, nose, lips, looking back, looking at camera, turned head, profile, side view, front view, "
    "deformed, bad anatomy, bad hands, blurry, watermark"
)

print("Generating true 180 rear turnaround back shot...")
generator = torch.Generator(device).manual_seed(9911)

image = pipe(
    prompt=prompt,
    negative_prompt=negative_prompt,
    width=768,
    height=1152,
    num_inference_steps=28,
    guidance_scale=5.5,
    generator=generator
).images[0]

save_p = out_dir / "maya_04_turnaround_back.png"
image.save(save_p, format="PNG")
shutil.copy2(save_p, artifacts_dir / save_p.name)
print(f"Saved true rear back turnaround: {save_p.name}")
