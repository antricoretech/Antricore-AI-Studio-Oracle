import os
import torch
from pathlib import Path
from PIL import Image
from diffusers import StableDiffusionXLPipeline, DPMSolverMultistepScheduler

device = "mps" if torch.backends.mps.is_available() else "cpu"
dtype = torch.float16 if device == "mps" else torch.float32

model_path = "models/cyberrealistic-xl/CyberRealisticXLPlay_V10.0_FP16.safetensors"
out_dir = Path("generated")
out_dir.mkdir(parents=True, exist_ok=True)

# Shared persona anchor for Riya
base_persona = (
    "masterpiece, 8k raw photo, photorealistic intimate editorial portrait of 23-year-old fictional Indian model Riya, "
    "slender toned body, defined collarbones, warm golden caramel skin, mesmerizing dark almond eyes, "
    "subtle beauty mark above lip, voluminous glossy dark wavy hair. "
    "Tasteful aesthetic nude, open body, completely bare without any clothing, "
    "authentic skin pores, natural skin texture, delicate collarbones, 85mm f/1.4 lens, natural lighting, "
    "perfect facial anatomy, five fingers on each hand"
)

riya_neg = (
    "clothes, bra, panties, underwear, fabric, strap, dress, "
    "blurry, cartoon, 3d, render, deformed, distorted, bad anatomy, "
    "extra fingers, missing fingers, fused fingers, mutated hands, poorly drawn hands, "
    "bad eyes, crossed eyes, plastic skin, doll, oversaturated, harsh glare, specular blowout, "
    "child, teenager, minor, text, watermark, signature"
)

poses = [
    {
        "name": "riya_glamour_nude_bed_recline.png",
        "seed": 441,
        "pose_prompt": (
            f"{base_persona}, reclining gracefully back on a plush luxury bed with white linen sheets, "
            "one arm bent behind head with fingers woven through long dark hair, "
            "other arm resting gently along slender waist, arched toned spine, alluring intimate gaze at camera, "
            "soft warm morning sunlight streaming across bed"
        )
    },
    {
        "name": "riya_glamour_nude_balcony_profile.png",
        "seed": 442,
        "pose_prompt": (
            f"{base_persona}, standing three-quarter side profile by floor-to-ceiling glass hotel balcony window, "
            "head turned over shoulder looking directly at camera with sultry smile, "
            "hands resting delicately against sheer glass, elegant arched back, slender waist and hip curve, "
            "golden hour sunset rim lighting illuminating smooth caramel skin"
        )
    },
    {
        "name": "riya_glamour_nude_seated_rug.png",
        "seed": 443,
        "pose_prompt": (
            f"{base_persona}, seated intimately on a plush cream wool rug, legs folded elegantly to the side, "
            "one hand resting softly on the floor, other hand gently touching slender neck and collarbone, "
            "leaning slightly forward with intense appealing gaze directly into camera lens, "
            "soft ambient resort suite lighting, moody shadows"
        )
    }
]

print(f"Loading CyberRealistic XL from {model_path} onto {device}...")
pipe = StableDiffusionXLPipeline.from_single_file(model_path, torch_dtype=dtype).to(device)
pipe.scheduler = DPMSolverMultistepScheduler.from_config(pipe.scheduler.config, use_karras_sigmas=True)

for i, p in enumerate(poses, 1):
    out_path = out_dir / p["name"]
    print(f"\n[{i}/3] Generating {p['name']} (Seed: {p['seed']})...")
    
    img = pipe(
        prompt=p["pose_prompt"],
        negative_prompt=riya_neg,
        width=768,
        height=1152,
        num_inference_steps=30,
        guidance_scale=5.0,
        generator=torch.Generator(device).manual_seed(p["seed"])
    ).images[0]
    
    img.save(str(out_path))
    print(f"Saved: {out_path}")

print("\nAll 3 images generated successfully!")
