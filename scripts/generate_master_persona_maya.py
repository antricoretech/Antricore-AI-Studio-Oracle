#!/usr/bin/env python3
"""
Complete Master Persona Profile Generator: Maya Bhutia (Sikkimese Heritage)
Persona: 24yo, Gangtok Sikkim (Northeast India), porcelain fair, 36-24-30 figure.
Generates:
1. 4-Angle Spatial Turnaround Pack (Front 0°, Left -90°, Right +90°, True Back 180°)
2. Hyper-Realistic Macro: Eyes, Lips & Authentic Skin Texture
3. 4 Standard Category Baselines (Fashion, Fitness, Casual, Resort)
4. 4 Adult Intimate Baselines (Artistic Boudoir Half & Full, Erotic Lingerie Half & Full)
Total: 13 Master Profile Reference Images
"""
import os
import sys
import time
import shutil
from pathlib import Path
from PIL import Image
import torch
from diffusers import StableDiffusionXLPipeline, DPMSolverMultistepScheduler

out_dir = Path("generated/master_persona_maya")
out_dir.mkdir(parents=True, exist_ok=True)

artifacts_dir = Path("/Users/guddugiri/.gemini/antigravity-ide/brain/739e6f68-e605-4993-ba1b-f78ad891d4d4")

device = "mps" if torch.backends.mps.is_available() else "cpu"
dtype = torch.float16 if device == "mps" else torch.float32

model_file = "models/juggernaut-xl-v10/Juggernaut-X-RunDiffusion-NSFW.safetensors"

print(f"Loading SDXL pipeline from {model_file}...")
pipe = StableDiffusionXLPipeline.from_single_file(model_file, torch_dtype=dtype).to(device)
pipe.scheduler = DPMSolverMultistepScheduler.from_config(pipe.scheduler.config, use_karras_sigmas=True)

# Master Seed Anchor for Maya Bhutia to lock facial identity
MASTER_SEED = 8824

# Core Negative Prompts
NEGATIVE_PROMPT = (
    "deformed, bad anatomy, distorted face, crossed eyes, bad hands, extra fingers, missing fingers, "
    "fake plastic skin, doll skin, 3d render, cartoon, anime, illustration, blurry, low quality, "
    "saggy, bad breasts, watermark, text, signature"
)

# 13 Master Persona Image Specifications
maya_master_pack = [
    # --------------------------------------------------------------------------
    # 1. 4-ANGLE SPATIAL TURNAROUND PACK (Studio Neutral)
    # --------------------------------------------------------------------------
    {
        "id": "maya_01_turnaround_front",
        "title": "Turnaround [01/04] Front Profile (0° Direct)",
        "prompt": (
            "8k raw photo, direct front view at 0 degrees, standing medium portrait of 24yo Northeast Indian woman Maya Bhutia from Sikkim, "
            "porcelain fair skin, rosy cheekbones, dark amber almond eyes, delicate epicanthic fold, plump natural lips, "
            "silky black hair falling over shoulders, 36 24 30 figure, full 36D bust in black ribbed sleeveless crop top, "
            "neutral studio lighting, light grey background, 50mm lens"
        ),
        "seed": MASTER_SEED,
        "filename": "maya_01_turnaround_front.png"
    },
    {
        "id": "maya_02_turnaround_left",
        "title": "Turnaround [02/04] Left Side Profile (-90° True Profile)",
        "prompt": (
            "8k raw photo, true 90-degree left profile view, side angle portrait of 24yo Northeast Indian woman Maya Bhutia from Sikkim, "
            "showing left jawline, delicate ear, refined straight nose profile, lips contour, silky black hair cascading down back, "
            "wearing black ribbed sleeveless crop top, side view of 36-inch bust and tiny 24-inch waist, "
            "neutral studio lighting, light grey background, 50mm lens"
        ),
        "seed": MASTER_SEED + 1,
        "filename": "maya_02_turnaround_left.png"
    },
    {
        "id": "maya_03_turnaround_right",
        "title": "Turnaround [03/04] Right Side Profile (+90° True Profile)",
        "prompt": (
            "8k raw photo, true 90-degree right profile view, side angle portrait of 24yo Northeast Indian woman Maya Bhutia from Sikkim, "
            "showing right jawline, cheekbone, straight nose slope, ear, silky black hair, "
            "wearing black ribbed sleeveless crop top, side profile of 36D bust and slender 24 waist, "
            "neutral studio lighting, light grey background, 50mm lens"
        ),
        "seed": MASTER_SEED + 2,
        "filename": "maya_03_turnaround_right.png"
    },
    {
        "id": "maya_04_turnaround_back",
        "title": "Turnaround [04/04] True Back Profile (180° Direct Rear View)",
        "prompt": (
            "8k raw photo, view directly from behind at 180 degrees, full rear view of the back of 24yo woman Maya Bhutia, "
            "facing completely away from camera, showing back of head with silky straight obsidian black hair cascading past shoulders, "
            "wearing black ribbed sleeveless top, showing back of neck, toned shoulder blades, slender 24-inch waist from behind, "
            "zero facial features visible, studio light grey background, 50mm lens"
        ),
        "seed": MASTER_SEED + 3,
        "filename": "maya_04_turnaround_back.png"
    },

    # --------------------------------------------------------------------------
    # 2. HYPER-REALISTIC EYES & LIPS MICRO-DETAILING
    # --------------------------------------------------------------------------
    {
        "id": "maya_05_micro_eyes_lips",
        "title": "Micro-Detailing [05/13] Eyes & Lips Macro Close-Up",
        "prompt": (
            "8k raw extreme macro beauty close-up portrait of 24yo Northeast Indian woman Maya Bhutia from Sikkim, "
            "focusing closely on eyes and lips, striking dark amber-brown almond eyes, delicate epicanthic fold, "
            "individual dark eyelashes, soft natural arch eyebrows, plump full lips with defined cupid's bow and natural hydration sheen, "
            "porcelain fair skin with subtle rosy cheeks and authentic skin pores, 100mm f/2.8 macro lens"
        ),
        "seed": MASTER_SEED,
        "filename": "maya_05_micro_eyes_lips.png"
    },

    # --------------------------------------------------------------------------
    # 3. STANDARD CATEGORY BASELINES
    # --------------------------------------------------------------------------
    {
        "id": "maya_06_baseline_fashion",
        "title": "Baseline [06/13] High Fashion & Glamour",
        "prompt": (
            "8k raw photo, waist-up fashion editorial portrait of 24yo Northeast Indian woman Maya Bhutia from Sikkim, "
            "wearing tailored ivory silk blazer dress with deep plunge neckline showing 36-inch cleavage, delicate gold pendant, "
            "standing in luxury mountain resort penthouse overlooking misty Himalayan peaks, porcelain skin, dark amber almond eyes, "
            "silky black hair, confident sophisticated gaze, 85mm portrait lens"
        ),
        "seed": MASTER_SEED,
        "filename": "maya_06_baseline_fashion.png"
    },
    {
        "id": "maya_07_baseline_fitness",
        "title": "Baseline [07/13] Fitness & Athleisure",
        "prompt": (
            "8k raw photo, waist-up portrait of 24yo Northeast Indian woman Maya Bhutia from Sikkim, "
            "hair in sleek high ponytail, wearing lavender ribbed sports bra and leggings, showing toned 24-inch waist, "
            "radiant glowing dewy skin, standing in sunlit modern yoga studio with wooden floors, "
            "porcelain fair skin, dark amber eyes, athletic 36 24 30 figure, 50mm lens"
        ),
        "seed": MASTER_SEED + 4,
        "filename": "maya_07_baseline_fitness.png"
    },
    {
        "id": "maya_08_baseline_casual",
        "title": "Baseline [08/13] Casual Streetwear Lifestyle",
        "prompt": (
            "8k raw candid street photo, waist-up portrait of 24yo Northeast Indian woman Maya Bhutia from Sikkim, "
            "sitting at outdoor Gangtok cafe wooden table holding warm ceramic tea cup, "
            "wearing cozy oversized cream knit cardigan falling off one shoulder over fitted black top, "
            "warm joyful smile, silky black hair caught in mountain breeze, porcelain rosy skin, dark amber eyes, 35mm street photo"
        ),
        "seed": MASTER_SEED + 5,
        "filename": "maya_08_baseline_casual.png"
    },
    {
        "id": "maya_09_baseline_resort",
        "title": "Baseline [09/13] Resort & Swimwear (No Nudity)",
        "prompt": (
            "8k raw photo, waist-up portrait of 24yo Northeast Indian woman Maya Bhutia from Sikkim, "
            "sitting beside luxury heated infinity pool overlooking pine mountains, wearing elegant emerald green one-piece designer swimsuit with gold belt, "
            "accentuating natural 36-inch bust and 24-inch waist, no nudity, sunglasses on head, wet silky black hair, "
            "porcelain fair skin, dark amber eyes, 50mm lens"
        ),
        "seed": MASTER_SEED + 6,
        "filename": "maya_09_baseline_resort.png"
    },

    # --------------------------------------------------------------------------
    # 4. ADULT INTIMATE & EROTIC GLAMOUR BASELINES (UNCENSORED)
    # --------------------------------------------------------------------------
    {
        "id": "maya_10_boudoir_half",
        "title": "Adult Boudoir [10/13] Artistic Nude / Intimate (Half-Body)",
        "prompt": (
            "8k raw photo, intimate boudoir half-body portrait of 24yo Northeast Indian woman Maya Bhutia from Sikkim, "
            "sitting on luxury bed with white silk sheets, topless, bare breasts, natural round 36D breasts, "
            "soft warm morning sunlight on porcelain fair skin, dark amber almond eyes looking softly into camera, "
            "silky black hair draped over one shoulder, tiny 24-inch waist, fine art intimate boudoir photography, 85mm lens"
        ),
        "seed": MASTER_SEED,
        "filename": "maya_10_boudoir_half.png"
    },
    {
        "id": "maya_11_boudoir_full",
        "title": "Adult Boudoir [11/13] Artistic Nude / Intimate (Full-Body)",
        "prompt": (
            "8k raw photo, full-body artistic nude photography of 24yo Northeast Indian woman Maya Bhutia from Sikkim, "
            "reclining gracefully on velvet chaise lounge, completely nude, beautiful natural 36 24 30 figure, "
            "full natural 36-inch breasts, narrow 24-inch waist, slender 30-inch hips, smooth porcelain fair skin, "
            "silky long black hair flowing across lounge, moody soft directional studio light, fine art aesthetics, 50mm lens"
        ),
        "seed": MASTER_SEED + 7,
        "filename": "maya_11_boudoir_full.png"
    },
    {
        "id": "maya_12_lingerie_half",
        "title": "Erotic Glamour [12/13] Sheer Lace Lingerie (Half-Body)",
        "prompt": (
            "8k raw photo, half-body erotic glamour portrait of 24yo Northeast Indian woman Maya Bhutia from Sikkim, "
            "wearing seductive black sheer lace corset bustier, deep plunge showcasing full 36-inch cleavage, "
            "looking directly at viewer with sultry alluring gaze, plump lips, porcelain fair skin, "
            "silky black hair, soft ambient candlelit bedroom background, 85mm lens"
        ),
        "seed": MASTER_SEED,
        "filename": "maya_12_lingerie_half.png"
    },
    {
        "id": "maya_13_lingerie_full",
        "title": "Erotic Glamour [13/13] Luxury Lingerie & Stockings (Full-Body)",
        "prompt": (
            "8k raw photo, full-body high-glamour lingerie portrait of 24yo Northeast Indian woman Maya Bhutia from Sikkim, "
            "standing in front of full-length luxury hotel mirror, wearing sheer black lace lingerie set with matching garter belt and stockings, "
            "highlighting 36 24 30 hourglass figure, full 36D bust, tiny 24-inch waist, slender athletic legs, "
            "porcelain fair skin, dark amber eyes, silky black hair, high-fashion erotic glamour, 50mm lens"
        ),
        "seed": MASTER_SEED + 8,
        "filename": "maya_13_lingerie_full.png"
    }
]

total = len(maya_master_pack)
print(f"\n=================================================================")
print(f"  STARTING GENERATION OF ALL {total} MASTER PERSONA IMAGES")
print(f"  Persona: Maya Bhutia (24yo, Sikkim Northeast India, 36-24-30)")
print("=================================================================\n")

for i, item in enumerate(maya_master_pack, start=1):
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
    print(f"  Diffusion done in {elapsed:.2f}s")
    
    save_path = out_dir / item["filename"]
    image.save(save_path, format="PNG")
    print(f"  Saved locally: {save_path.name}")
    
    artifact_path = artifacts_dir / item["filename"]
    shutil.copy2(save_path, artifact_path)
    print(f"  Copied to artifacts: {artifact_path.name}\n")

print("=================================================================")
print("  ALL 13 MASTER PERSONA IMAGES FOR MAYA BHUTIA GENERATED!")
print("=================================================================")
