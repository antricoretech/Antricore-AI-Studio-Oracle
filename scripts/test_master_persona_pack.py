#!/usr/bin/env python3
"""
Refined Master Persona Profile Pack Generator for Elena Weber
Fixes CLIP 77-token truncation by putting angle, framing, and outfit in the first 25 tokens.
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

print(f"Loading pipeline from {model_file}...")
pipe = StableDiffusionXLPipeline.from_single_file(model_file, torch_dtype=dtype).to(device)
pipe.scheduler = DPMSolverMultistepScheduler.from_config(pipe.scheduler.config, use_karras_sigmas=True)

NEGATIVE_PROMPT = (
    "nude, bare, exposed breasts, deformed, distorted, bad eyes, crossed eyes, bad hands, "
    "extra fingers, missing fingers, plastic skin, smooth doll skin, 3d render, cartoon, "
    "anime, illustration, blurry, lowres, watermark, text"
)

# Optimized prompts: under 55 tokens, angle & outfit first
items_to_generate = [
    # 1. Turnaround Left Profile
    {
        "filename": "master_02_turnaround_left.png",
        "title": "Turnaround Left Profile (-90° / 3/4 side)",
        "prompt": (
            "8k raw photo, side profile view, left profile turned 75 degrees, waist-up portrait of 22yo German woman Elena Weber, "
            "showing left jawline, left cheekbone, wavy golden-blonde hair falling over shoulder, "
            "wearing elegant black ribbed sleeveless knit top, neutral studio lighting, light grey cyclorama backdrop, 50mm lens"
        ),
        "seed": 2201
    },
    # 2. Turnaround Right Profile
    {
        "filename": "master_03_turnaround_right.png",
        "title": "Turnaround Right Profile (+90° / 3/4 side)",
        "prompt": (
            "8k raw photo, side profile view, right profile turned 75 degrees, waist-up portrait of 22yo German woman Elena Weber, "
            "showing right jawline, right cheekbone, tiny gold earring in right ear, wavy blonde hair, "
            "wearing elegant black ribbed sleeveless knit top, neutral studio lighting, light grey cyclorama backdrop, 50mm lens"
        ),
        "seed": 2202
    },
    # 3. Micro-Detailing (Full face macro: both eyes, nose, and lips)
    {
        "filename": "master_05_micro_eyes_lips.png",
        "title": "Hyper-Realistic Macro: Eyes & Lips Beauty Close-Up",
        "prompt": (
            "8k raw macro beauty close-up portrait of 22yo German woman Elena Weber, focusing closely on eyes and lips, "
            "striking hazel-green irises with golden-brown flecks, natural dark eyelashes, defined blonde-brown eyebrows, "
            "soft full natural lips with hydrated gloss sheen, authentic skin pores and subtle freckles, 85mm macro lens"
        ),
        "seed": 2203
    },
    # 4. Category Baseline: High Fashion & Glamour
    {
        "filename": "master_06_baseline_fashion.png",
        "title": "Category Baseline: High Fashion & Glamour",
        "prompt": (
            "8k raw photo, waist-up portrait of 22yo German woman Elena Weber, "
            "wearing an ivory white tailored blazer dress with satin lapels and delicate gold chain necklace, "
            "standing in a luxury penthouse overlooking city skyline at dusk, striking hazel-green eyes, soft lips, wavy blonde hair, 50mm lens"
        ),
        "seed": 2204
    },
    # 5. Category Baseline: Fitness & Athleisure
    {
        "filename": "master_07_baseline_fitness.png",
        "title": "Category Baseline: Fitness & Athleisure",
        "prompt": (
            "8k raw photo, waist-up portrait of 22yo German woman Elena Weber, "
            "hair styled in a high ponytail, wearing a sage-green ribbed athletic sports top, "
            "standing in a sunlit modern aesthetic pilates studio, glowing natural dewy skin, athletic physique, hazel-green eyes, 50mm lens"
        ),
        "seed": 2205
    },
    # 6. Category Baseline: Casual Streetwear Lifestyle
    {
        "filename": "master_08_baseline_casual.png",
        "title": "Category Baseline: Casual Streetwear Lifestyle",
        "prompt": (
            "8k raw candid street photo, waist-up portrait of 22yo German woman Elena Weber, "
            "sitting at an outdoor European cafe marble table holding a ceramic coffee cup, "
            "wearing a classic beige trench coat over a cream knit sweater, cheerful smile, wavy blonde hair, hazel-green eyes, 35mm lens"
        ),
        "seed": 2206
    },
    # 7. Category Baseline: Resort & Beachwear (No Nudity)
    {
        "filename": "master_09_baseline_resort.png",
        "title": "Category Baseline: Resort & Beachwear (No Nudity)",
        "prompt": (
            "8k raw photo, waist-up portrait of 22yo German woman Elena Weber, "
            "sitting on teak lounge chair beside a luxury Mediterranean resort infinity pool, "
            "wearing a chic black one-piece designer swimsuit with a gold buckle, no nudity, designer sunglasses on head, "
            "hazel-green eyes, sun-kissed skin, 50mm lens"
        ),
        "seed": 2207
    }
]

total = len(items_to_generate)
print(f"\nRegenerating {total} targeted master profile images with optimized prompt layout...\n")

for i, item in enumerate(items_to_generate, start=1):
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
    
    print(f"  Diffusion complete in {time.time() - t0:.2f}s")
    
    clean_p = out_dir / item["filename"]
    image.save(clean_p, format="PNG")
    print(f"  Saved locally: {clean_p.name}")
    
    artifact_p = artifacts_dir / item["filename"]
    shutil.copy2(clean_p, artifact_p)
    print(f"  Copied to artifacts: {artifact_p.name}\n")

print("=================================================================")
print("  REFINED MASTER PROFILE GENERATION COMPLETE!")
print("=================================================================")
