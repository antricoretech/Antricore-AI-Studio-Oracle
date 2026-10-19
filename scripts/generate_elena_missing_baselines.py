#!/usr/bin/env python3
"""
Generate Missing Adult Baselines (10-13) for Master Persona: Elena Weber
Fulfills the complete 13-image Master Persona Vault according to MASTER_PERSONA_ENGINEERING_SPEC.md.
"""
import os
import sys
import time
import shutil
from pathlib import Path
from PIL import Image
import torch
from diffusers import StableDiffusionXLPipeline, DPMSolverMultistepScheduler

out_dir = Path("generated/master_persona_elena")
out_dir.mkdir(parents=True, exist_ok=True)
artifacts_dir = Path("/Users/guddugiri/.gemini/antigravity-ide/brain/739e6f68-e605-4993-ba1b-f78ad891d4d4")

device = "mps" if torch.backends.mps.is_available() else "cpu"
dtype = torch.float16 if device == "mps" else torch.float32

model_file = "models/juggernaut-xl-v10/Juggernaut-X-RunDiffusion-NSFW.safetensors"

print(f"Loading pipeline from {model_file} on {device} ({dtype})...")
t0_load = time.time()
pipe = StableDiffusionXLPipeline.from_single_file(model_file, torch_dtype=dtype).to(device)
pipe.scheduler = DPMSolverMultistepScheduler.from_config(pipe.scheduler.config, use_karras_sigmas=True)
print(f"Pipeline ready in {time.time() - t0_load:.2f}s")

NEGATIVE_PROMPT = (
    "deformed, bad anatomy, distorted face, crossed eyes, bad hands, extra fingers, "
    "missing fingers, fake plastic skin, doll skin, 3d render, cartoon, anime, illustration, "
    "blurry, low quality, saggy, bad breasts, watermark, text, signature"
)

# 4 Missing Adult Baselines for Elena Weber (Section 4 of Master Persona Spec)
elena_adult_baselines = [
    {
        "id": "adult_10_boudoir_half",
        "filename": "master_10_boudoir_half.png",
        "title": "Adult Boudoir [10/13] Artistic Nude / Intimate (Half-Body)",
        "prompt": (
            "8k raw photo, intimate boudoir half-body portrait of 22yo German woman Elena Weber, "
            "topless, bare breasts, natural round firm breasts, sitting on luxury bed with white silk sheets, "
            "soft warm morning sunlight, sun-kissed golden honey skin, hazel-green eyes looking into camera, "
            "wavy golden-blonde hair draped over bare shoulder, fine art intimate boudoir photography, 85mm lens"
        ),
        "seed": 2204
    },
    {
        "id": "adult_11_boudoir_full",
        "filename": "master_11_boudoir_full.png",
        "title": "Adult Boudoir [11/13] Artistic Nude / Intimate (Full-Body)",
        "prompt": (
            "8k raw photo, full-body artistic nude photography of 22yo German woman Elena Weber, "
            "reclining gracefully on velvet chaise lounge, completely nude, natural 34-24-34 hourglass figure, "
            "firm natural breasts, toned 24-inch waist, slender 34-inch hips, smooth golden honey skin, "
            "wavy golden-blonde hair cascading across cushion, soft directional window light, fine art aesthetics, 50mm lens"
        ),
        "seed": 2209
    },
    {
        "id": "adult_12_lingerie_half",
        "filename": "master_12_lingerie_half.png",
        "title": "Erotic Glamour [12/13] Sheer Lace Lingerie (Half-Body)",
        "prompt": (
            "8k raw photo, half-body erotic glamour portrait of 22yo German woman Elena Weber, "
            "wearing seductive sheer champagne lace corset bustier, deep plunge showcasing full 34-inch cleavage, "
            "sultry alluring gaze directly at camera, plump lips, hazel-green eyes, wavy golden-blonde hair, "
            "candlelit luxury Munich penthouse bedroom background, 85mm portrait lens"
        ),
        "seed": 2204
    },
    {
        "id": "adult_13_lingerie_full",
        "filename": "master_13_lingerie_full.png",
        "title": "Erotic Glamour [13/13] Luxury Lingerie & Stockings (Full-Body)",
        "prompt": (
            "8k raw photo, full-body high-glamour lingerie portrait of 22yo German woman Elena Weber, "
            "standing in front of luxury hotel full-length mirror, wearing sheer champagne lace lingerie set with matching garter belt and stockings, "
            "highlighting 34-24-34 hourglass figure, firm bust, toned 24-inch waist, slender legs, "
            "golden honey skin, hazel-green eyes, wavy golden-blonde hair, elegant erotic glamour, 50mm lens"
        ),
        "seed": 2210
    }
]

total = len(elena_adult_baselines)
print(f"\n=================================================================")
print(f"  GENERATING {total} MISSING ADULT BASELINES FOR ELENA WEBER (10-13)")
print("=================================================================\n")

for i, item in enumerate(elena_adult_baselines, start=1):
    print(f"[{i}/{total}] Generating: {item['title']} (Seed: {item['seed']})...")
    generator = torch.Generator(device).manual_seed(item["seed"])
    t0 = time.time()
    
    image = pipe(
        prompt=item["prompt"],
        negative_prompt=NEGATIVE_PROMPT,
        width=768,
        height=1152,
        num_inference_steps=28,
        guidance_scale=5.0,
        generator=generator
    ).images[0]
    
    elapsed = time.time() - t0
    print(f"  Diffusion complete in {elapsed:.2f}s")
    
    clean_p = out_dir / item["filename"]
    image.save(clean_p, format="PNG")
    print(f"  Saved locally: {clean_p.name}")
    
    if artifacts_dir.exists():
        artifact_p = artifacts_dir / item["filename"]
        shutil.copy2(clean_p, artifact_p)
        print(f"  Copied to artifacts: {artifact_p.name}")
    print()

print("=================================================================")
print("  ALL REMAINING MASTER PERSONA IMAGES FOR ELENA WEBER COMPLETE!")
print("=================================================================")
