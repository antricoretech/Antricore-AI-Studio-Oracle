#!/usr/bin/env python3
"""
Generate 3 Intimate Partner Moments for Mehar Sahu using her Master Profile Anchor.
- Scene 1: Tender passionate embrace & close intimate portrait (Cheek-to-cheek, candlelight)
- Scene 2: Sensual overhead angle on luxury white silk bed (Reclining embrace)
- Scene 3: Standing romantic embrace by luxury Mumbai penthouse panoramic glass window (Night city lights)
"""
import os
import sys
import time
import shutil
from pathlib import Path
import torch
from diffusers import StableDiffusionXLPipeline, DPMSolverMultistepScheduler

out_dir = Path("generated/master_persona_mehar")
out_dir.mkdir(parents=True, exist_ok=True)

artifacts_dir = Path("/Users/guddugiri/.gemini/antigravity-ide/brain/739e6f68-e605-4993-ba1b-f78ad891d4d4")

device = "mps" if torch.backends.mps.is_available() else "cpu"
dtype = torch.float16 if device == "mps" else torch.float32

model_file = "models/juggernaut-xl-v10/Juggernaut-X-RunDiffusion-NSFW.safetensors"

print(f"Loading Juggernaut XL v10 pipeline on {device} ({dtype})...")
pipe = StableDiffusionXLPipeline.from_single_file(model_file, torch_dtype=dtype).to(device)
pipe.scheduler = DPMSolverMultistepScheduler.from_config(pipe.scheduler.config, use_karras_sigmas=True)

# Master Seed Anchor for Mehar Sahu
MASTER_SEED = 9142

UNIVERSAL_NEGATIVE = (
    "deformed, bad anatomy, distorted face, crossed eyes, bad hands, extra fingers, missing fingers, "
    "fake plastic skin, doll skin, 3d render, cartoon, anime, illustration, blurry, low quality, "
    "saggy, bad breasts, watermark, text, signature"
)

DNA = "21yo Indian woman Mehar Sahu from Mumbai, fair radiant skin, dark brown almond eyes, plump lips, silky dark wavy hair"
FIGURE = "voluptuous 40 36 30 figure, very tight large full 40E bust, 36-inch waist"

scenes = [
    {
        "id": "mehar_intimate_01_embrace",
        "title": "Intimate Moment [01/03] Tender Candlelight Embrace",
        "prompt": (
            f"8k raw photo, intimate medium close-up portrait of {DNA}, in passionate loving embrace with her handsome male partner, "
            f"partner gently holding her face and bare shoulders, cheek to cheek, romantic blissful closed-mouth smile, "
            f"wearing sheer crimson silk camisole showing {FIGURE}, warm glowing candlelight bedroom, 85mm portrait lens, shallow depth of field"
        ),
        "seed": MASTER_SEED,
        "filename": "mehar_intimate_01_embrace.png"
    },
    {
        "id": "mehar_intimate_02_silk_bed",
        "title": "Intimate Moment [02/03] Overhead Silk Bed Recline",
        "prompt": (
            f"8k raw photo, high-angle downward view, intimate bedroom photography of {DNA}, "
            f"lying back sensually across white silk bed sheets, partner lying close beside her gently caressing her waist, "
            f"topless, natural bare firm 40E breasts, soft morning sunbeams spilling through sheer curtains, deep romantic eye contact, 50mm lens"
        ),
        "seed": MASTER_SEED + 12,
        "filename": "mehar_intimate_02_silk_bed.png"
    },
    {
        "id": "mehar_intimate_03_window_night",
        "title": "Intimate Moment [03/03] Mumbai Skyline Window Embrace",
        "prompt": (
            f"8k raw photo, side 3/4 angle romantic embrace of {DNA}, "
            f"standing in luxury penthouse bedroom in front of floor-to-ceiling glass window overlooking sparkling Mumbai night skyline, "
            f"partner embracing her from behind with arms wrapped around her waist, gentle kiss on her neck, "
            f"wearing sheer black lace lingerie accentuating voluptuous 40 36 30 figure and tight large bust, dramatic rim lighting, 50mm lens"
        ),
        "seed": MASTER_SEED + 15,
        "filename": "mehar_intimate_03_window_night.png"
    }
]

total = len(scenes)
print(f"\n=================================================================")
print(f"  STARTING GENERATION OF 3 INTIMATE MOMENTS FOR MEHAR SAHU")
print("=================================================================\n")

for i, item in enumerate(scenes, start=1):
    print(f"[{i}/{total}] Generating: {item['title']} (Seed: {item['seed']})...")
    generator = torch.Generator(device).manual_seed(item["seed"])
    t0 = time.time()
    
    image = pipe(
        prompt=item["prompt"],
        negative_prompt=UNIVERSAL_NEGATIVE,
        width=768,
        height=1152,
        num_inference_steps=28,
        guidance_scale=5.0,
        generator=generator
    ).images[0]
    
    elapsed = time.time() - t0
    print(f"  Diffusion complete in {elapsed:.2f}s")
    
    save_path = out_dir / item["filename"]
    image.save(save_path, format="PNG")
    print(f"  Saved locally: {save_path}")
    
    artifact_path = artifacts_dir / item["filename"]
    shutil.copy2(save_path, artifact_path)
    print(f"  Saved to artifacts: {artifact_path}\n")

print("=================================================================")
print("  ALL 3 INTIMATE MOMENTS FOR MEHAR SAHU GENERATED!")
print("=================================================================")
