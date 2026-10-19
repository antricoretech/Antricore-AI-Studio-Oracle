#!/usr/bin/env python3
"""
Complete Master Persona Profile Generator: Mehar Sahu
Persona: 21yo Mumbai college girl, fair, beautiful, charming model look, 40-36-30 figure, tight large bust.
Generates:
1. 4-Angle Spatial Turnaround Pack (Front 0°, Left -90°, Right +90°, True Back 180°)
2. Hyper-Realistic Macro: Eyes, Lips & Authentic Skin Texture (100mm f/2.8)
3. 4 Standard Category Baselines (Fashion, Fitness, Casual, Resort)
4. 4 Adult Intimate Baselines (Artistic Boudoir Half & Full, Erotic Lingerie Half & Full)
Total: 13 Master Profile Reference Images strictly adhering to MASTER_PERSONA_ENGINEERING_SPEC.md.
"""
import os
import sys
import time
import shutil
from pathlib import Path
from PIL import Image
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

# Master Seed Anchor for Mehar Sahu to lock facial and anatomical identity
MASTER_SEED = 9142

# Universal Negative Prompt (Compliant with Spec)
UNIVERSAL_NEGATIVE = (
    "deformed, bad anatomy, distorted face, crossed eyes, bad hands, extra fingers, missing fingers, "
    "fake plastic skin, doll skin, 3d render, cartoon, anime, illustration, blurry, low quality, "
    "saggy, bad breasts, watermark, text, signature"
)

# 180° Direct Rear Turnaround Strict Negative Ringfence (Ban all facial tokens)
REAR_TURNAROUND_NEGATIVE = (
    "face, eyes, mouth, nose, lips, looking back, looking at camera, turned head, profile, side view, front view, "
    "deformed, bad anatomy, bad hands, blurry, watermark"
)

# Core DNA strings
DNA = "21yo Indian woman Mehar Sahu from Mumbai, fair radiant skin, dark brown almond eyes, plump lips, silky dark wavy hair"
FIGURE_CLOTHED = "voluptuous 40 36 30 figure, very tight large full 40E bust, 36-inch waist, 30-inch hips"
FIGURE_NUDE = "nude natural voluptuous 40 36 30 figure, very tight firm large 40E breasts, 36-inch waist, 30-inch hips"

# 13 Master Persona Image Specifications
mehar_master_pack = [
    # --------------------------------------------------------------------------
    # 1. 4-ANGLE SPATIAL TURNAROUND PACK (Studio Neutral)
    # --------------------------------------------------------------------------
    {
        "id": "mehar_01_turnaround_front",
        "title": "Turnaround [01/04] Front Profile (0° Direct)",
        "prompt": (
            f"8k raw photo, direct front view at 0 degrees, standing medium portrait of {DNA}, "
            f"wearing black ribbed sleeveless crop top, showing very tight large 40E bust and 36-inch waist, "
            f"neutral studio lighting, light grey cyclorama background, 50mm lens"
        ),
        "negative": UNIVERSAL_NEGATIVE,
        "seed": MASTER_SEED,
        "filename": "mehar_01_turnaround_front.png"
    },
    {
        "id": "mehar_02_turnaround_left",
        "title": "Turnaround [02/04] Left Side Profile (-90° True Profile)",
        "prompt": (
            f"8k raw photo, true 90-degree left profile view, side angle portrait of {DNA}, "
            f"showing left jawline, ear, straight nose profile, lips contour, silky dark hair down back, "
            f"wearing black ribbed sleeveless top, side profile projection of tight large 40E bust and waist, studio grey background, 50mm lens"
        ),
        "negative": UNIVERSAL_NEGATIVE,
        "seed": MASTER_SEED + 1,
        "filename": "mehar_02_turnaround_left.png"
    },
    {
        "id": "mehar_03_turnaround_right",
        "title": "Turnaround [03/04] Right Side Profile (+90° True Profile)",
        "prompt": (
            f"8k raw photo, true 90-degree right profile view, side angle portrait of {DNA}, "
            f"showing right jawline, cheekbone, ear, silky hair, wearing black ribbed sleeveless top, "
            f"side profile projection of large firm 40E bust and 36 waist, studio grey background, 50mm lens"
        ),
        "negative": UNIVERSAL_NEGATIVE,
        "seed": MASTER_SEED + 2,
        "filename": "mehar_03_turnaround_right.png"
    },
    {
        "id": "mehar_04_turnaround_back",
        "title": "Turnaround [04/04] True Back Profile (180° Direct Rear View)",
        "prompt": (
            "8k raw photo, view directly from behind at 180 degrees, complete rear back view of 21yo woman Mehar Sahu, "
            "facing completely away from camera towards back wall, showing back of head with dark wavy hair cascading past upper back, "
            "wearing black ribbed top, back of neck, toned shoulder blades, waist from behind, studio grey background, 50mm lens"
        ),
        "negative": REAR_TURNAROUND_NEGATIVE,
        "seed": MASTER_SEED + 3,
        "filename": "mehar_04_turnaround_back.png"
    },

    # --------------------------------------------------------------------------
    # 2. HYPER-REALISTIC EYES & LIPS MICRO-DETAILING MACRO (100mm f/2.8)
    # --------------------------------------------------------------------------
    {
        "id": "mehar_05_micro_eyes_lips",
        "title": "Micro-Detailing [05/13] Eyes & Lips Macro Close-Up",
        "prompt": (
            f"8k raw extreme macro beauty close-up portrait of {DNA}, "
            f"focusing closely on eyes and lips, striking dark brown almond eyes, dense natural eyelashes, "
            f"plump full lips with defined cupid's bow and natural hydration sheen, fair skin micro-pores, 100mm macro lens"
        ),
        "negative": UNIVERSAL_NEGATIVE,
        "seed": MASTER_SEED,
        "filename": "mehar_05_micro_eyes_lips.png"
    },

    # --------------------------------------------------------------------------
    # 3. STANDARD CATEGORY BASELINES (Mandatory Diversity Ringfence: Mumbai)
    # --------------------------------------------------------------------------
    {
        "id": "mehar_06_baseline_fashion",
        "title": "Baseline [06/13] High Fashion & Glamour",
        "prompt": (
            f"8k raw photo, waist-up fashion editorial portrait of {DNA}, "
            f"wearing tailored midnight navy silk blazer dress with deep plunge showing tight large 40E cleavage, gold necklace, "
            f"standing on luxury Marine Drive Mumbai penthouse balcony overlooking the sea, 85mm portrait lens"
        ),
        "negative": UNIVERSAL_NEGATIVE,
        "seed": MASTER_SEED,
        "filename": "mehar_06_baseline_fashion.png"
    },
    {
        "id": "mehar_07_baseline_fitness",
        "title": "Baseline [07/13] Fitness & Athleisure",
        "prompt": (
            f"8k raw photo, waist-up portrait of {DNA}, hair in high sleek ponytail, "
            f"wearing crimson red ribbed sports bra and high-waist gym tights, accentuating firm tight large 40E bust and 36-inch waist, "
            f"modern sunlit Mumbai Pilates glass studio with wooden floor, 50mm lens"
        ),
        "negative": UNIVERSAL_NEGATIVE,
        "seed": MASTER_SEED + 4,
        "filename": "mehar_07_baseline_fitness.png"
    },
    {
        "id": "mehar_08_baseline_casual",
        "title": "Baseline [08/13] Casual Streetwear Lifestyle",
        "prompt": (
            f"8k raw candid street photo, waist-up portrait of {DNA}, "
            f"sitting at outdoor Bandra Mumbai seaside cafe wooden table holding iced matcha latte, "
            f"wearing cropped off-shoulder cream knit top over fitted camisole highlighting tight full bust, charming warm smile, 35mm street photo"
        ),
        "negative": UNIVERSAL_NEGATIVE,
        "seed": MASTER_SEED + 5,
        "filename": "mehar_08_baseline_casual.png"
    },
    {
        "id": "mehar_09_baseline_resort",
        "title": "Baseline [09/13] Resort & Swimwear (No Nudity)",
        "prompt": (
            f"8k raw photo, waist-up portrait of {DNA}, "
            f"wearing metallic bronze one-piece designer swimsuit with waist cut-out, showcasing tight large 40E bust, no nudity, "
            f"sitting on private luxury yacht deck sailing near Mumbai harbor at golden hour, sunglasses on head, 50mm lens"
        ),
        "negative": UNIVERSAL_NEGATIVE,
        "seed": MASTER_SEED + 6,
        "filename": "mehar_09_baseline_resort.png"
    },

    # --------------------------------------------------------------------------
    # 4. ADULT INTIMATE & EROTIC GLAMOUR BASELINES (UNCENSORED)
    # --------------------------------------------------------------------------
    {
        "id": "mehar_10_boudoir_half",
        "title": "Adult Boudoir [10/13] Artistic Nude / Intimate (Half-Body)",
        "prompt": (
            f"8k raw photo, intimate boudoir half-body portrait of {DNA}, "
            f"sitting on luxury bed with white silk sheets, topless, bare breasts, very tight large round 40E breasts, "
            f"soft warm morning sunlight on fair skin, looking seductively into camera, dark wavy hair over shoulder, 85mm lens"
        ),
        "negative": UNIVERSAL_NEGATIVE,
        "seed": MASTER_SEED,
        "filename": "mehar_10_boudoir_half.png"
    },
    {
        "id": "mehar_11_boudoir_full",
        "title": "Adult Boudoir [11/13] Artistic Nude / Intimate (Full-Body)",
        "prompt": (
            f"8k raw photo, full-body artistic nude photography of {DNA}, "
            f"reclining on plush emerald velvet chaise lounge, completely nude, {FIGURE_NUDE}, "
            f"smooth fair glowing skin, dark hair draped across lounge, soft dramatic studio directional lighting, 50mm lens"
        ),
        "negative": UNIVERSAL_NEGATIVE,
        "seed": MASTER_SEED + 7,
        "filename": "mehar_11_boudoir_full.png"
    },
    {
        "id": "mehar_12_lingerie_half",
        "title": "Erotic Glamour [12/13] Sheer Lace Lingerie (Half-Body)",
        "prompt": (
            f"8k raw photo, half-body erotic glamour portrait of {DNA}, "
            f"wearing sheer deep ruby red lace corset bustier, deep plunge showcasing very tight large 40E bust cleavage, "
            f"sultry alluring gaze, fair skin, candlelight luxury bedroom background, 85mm lens"
        ),
        "negative": UNIVERSAL_NEGATIVE,
        "seed": MASTER_SEED,
        "filename": "mehar_12_lingerie_half.png"
    },
    {
        "id": "mehar_13_lingerie_full",
        "title": "Erotic Glamour [13/13] Luxury Lingerie & Stockings (Full-Body)",
        "prompt": (
            f"8k raw photo, full-body luxury lingerie portrait of {DNA}, "
            f"standing in front of full-length luxury hotel mirror, wearing sheer black lace lingerie set with matching garter belt and stockings, "
            f"highlighting voluptuous 40 36 30 figure and tight large 40E bust, high-heels, opulent Mumbai hotel suite, 50mm lens"
        ),
        "negative": UNIVERSAL_NEGATIVE,
        "seed": MASTER_SEED + 8,
        "filename": "mehar_13_lingerie_full.png"
    }
]

total = len(mehar_master_pack)
print(f"\n=================================================================")
print(f"  STARTING GENERATION OF ALL {total} MASTER PERSONA IMAGES")
print(f"  Persona: Mehar Sahu (21yo, Mumbai College Girl, 40-36-30 Figure)")
print(f"  Model: Juggernaut XL v10 NSFW (MPS Hardware Accelerated)")
print("=================================================================\n")

for i, item in enumerate(mehar_master_pack, start=1):
    print(f"[{i}/{total}] Generating: {item['title']} (Seed: {item['seed']})...")
    generator = torch.Generator(device).manual_seed(item["seed"])
    t0 = time.time()
    
    image = pipe(
        prompt=item["prompt"],
        negative_prompt=item.get("negative", UNIVERSAL_NEGATIVE),
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
print("  ALL 13 MASTER PERSONA IMAGES FOR MEHAR SAHU GENERATED!")
print("=================================================================")
