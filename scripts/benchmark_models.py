import os
import sys
import time
import json
import torch
from pathlib import Path
from PIL import Image
from diffusers import StableDiffusionXLPipeline, DPMSolverMultistepScheduler

device = "mps" if torch.backends.mps.is_available() else "cpu"
dtype = torch.float16 if device == "mps" else torch.float32

out_dir = Path("generated/benchmark_australian_glamour")
out_dir.mkdir(parents=True, exist_ok=True)

# Master Prompt
master_prompt = (
    "masterpiece, 8k raw photo, photorealistic intimate editorial full body portrait of 22-year-old Australian glamour model Chloe, "
    "athletic hourglass figure, toned slender waist, defined collarbones, long toned legs, natural feminine curves, "
    "sun-kissed golden tan skin, radiant light blue eyes, sun-bleached beach blonde wavy hair falling past shoulders. "
    "Tasteful aesthetic nude, open body, completely bare without any outfit or clothing, "
    "standing gracefully on a luxury Byron Bay penthouse balcony overlooking the ocean at sunset, "
    "soft warm golden hour rim lighting catching her silhouette, authentic skin pores, delicate skin texture, "
    "35mm f/1.8 full body shot, photorealistic, perfect anatomy, five fingers on each hand"
)

master_neg = (
    "clothes, bra, panties, underwear, fabric, strap, dress, "
    "blurry, cartoon, 3d, render, deformed, distorted, bad anatomy, "
    "extra fingers, missing fingers, fused fingers, mutated hands, poorly drawn hands, "
    "bad eyes, crossed eyes, plastic skin, doll, oversaturated, harsh glare, specular blowout, "
    "child, teenager, minor, text, watermark, signature, cropped head, cropped feet"
)

# Pony prompt with specialized score tags
pony_prompt = (
    "score_9, score_8_up, score_7_up, source_photo, realistic, 1girl, solo, "
    "masterpiece, 8k raw photo, photorealistic intimate editorial full body portrait of 22-year-old Australian glamour model Chloe, "
    "athletic hourglass figure, toned slender waist, defined collarbones, long toned legs, natural feminine curves, "
    "sun-kissed golden tan skin, radiant light blue eyes, sun-bleached beach blonde wavy hair. "
    "Tasteful aesthetic nude, completely bare without any clothes, "
    "standing on a luxury Byron Bay penthouse balcony overlooking ocean at sunset, "
    "golden hour rim lighting, authentic skin texture, full body shot, perfect anatomy"
)

pony_neg = (
    "score_4, score_5, score_6, clothes, bra, panties, underwear, dress, "
    "blurry, cartoon, anime, 3d, render, deformed, bad anatomy, bad hands, mutated fingers, extra digits, cropped"
)

models = [
    {
        "id": "cyberrealistic-xl",
        "name": "CyberRealistic XL (v10)",
        "file": "models/cyberrealistic-xl/CyberRealisticXLPlay_V10.0_FP16.safetensors",
        "prompt": master_prompt,
        "negative_prompt": master_neg,
        "guidance": 5.0,
        "steps": 30,
        "seed": 888,
        "out_filename": "01_cyberrealistic_xl.png"
    },
    {
        "id": "juggernaut-xl-v10",
        "name": "Juggernaut XL (v10)",
        "file": "models/juggernaut-xl-v10/Juggernaut-X-RunDiffusion-NSFW.safetensors",
        "prompt": master_prompt,
        "negative_prompt": master_neg,
        "guidance": 5.0,
        "steps": 30,
        "seed": 888,
        "out_filename": "02_juggernaut_xl_v10.png"
    },
    {
        "id": "pony-diffusion-v6-xl",
        "name": "Pony Diffusion V6 XL",
        "file": "models/pony-diffusion-v6-xl/ponyDiffusionV6XL_v6StartWithThisOne.safetensors",
        "prompt": pony_prompt,
        "negative_prompt": pony_neg,
        "guidance": 7.0,
        "steps": 30,
        "seed": 888,
        "out_filename": "03_pony_diffusion_v6_xl.png"
    }
]

results = []

print("=================================================================")
print("  AUSTRALIAN GLAMOUR MODEL BENCHMARK — ALL INSTALLED MODELS")
print(f"  Device: {device} | Dtype: {dtype} | Resolution: 768x1152")
print("=================================================================\n")

for i, m in enumerate(models, 1):
    print(f"\n--- [{i}/3] BENCHMARKING: {m['name']} ---")
    if not os.path.exists(m['file']):
        print(f"Error: Model checkpoint not found at {m['file']}")
        continue
    
    # 1. Measure load time
    t_load_start = time.time()
    print(f"Loading weights from {m['file']}...")
    pipe = StableDiffusionXLPipeline.from_single_file(m['file'], torch_dtype=dtype).to(device)
    pipe.scheduler = DPMSolverMultistepScheduler.from_config(pipe.scheduler.config, use_karras_sigmas=True)
    load_time = time.time() - t_load_start
    print(f"Loaded in {load_time:.2f}s")
    
    # 2. Measure inference time
    out_path = out_dir / m['out_filename']
    print(f"Starting 30-step generation (Guidance: {m['guidance']}, Seed: {m['seed']})...")
    
    t_gen_start = time.time()
    generator = torch.Generator(device).manual_seed(m['seed'])
    
    image = pipe(
        prompt=m['prompt'],
        negative_prompt=m['negative_prompt'],
        width=768,
        height=1152,
        num_inference_steps=m['steps'],
        guidance_scale=m['guidance'],
        generator=generator
    ).images[0]
    
    gen_time = time.time() - t_gen_start
    sec_per_step = gen_time / m['steps']
    
    image.save(str(out_path))
    print(f"Generation completed in {gen_time:.2f}s ({sec_per_step:.2f}s/step)")
    print(f"Saved: {out_path}")
    
    results.append({
        "id": m['id'],
        "name": m['name'],
        "file": m['file'],
        "load_time_sec": round(load_time, 2),
        "gen_time_sec": round(gen_time, 2),
        "sec_per_step": round(sec_per_step, 2),
        "steps": m['steps'],
        "guidance": m['guidance'],
        "seed": m['seed'],
        "resolution": "768x1152",
        "output_image": str(out_path)
    })
    
    # Free memory between models
    del pipe
    if device == "mps":
        torch.mps.empty_cache()

# Save results JSON
results_json_path = out_dir / "benchmark_results.json"
with open(results_json_path, "w") as f:
    json.dump(results, f, indent=2)

print("\n=================================================================")
print("  BENCHMARK COMPLETED SUCCESSFULLY!")
print(f"  Summary saved to: {results_json_path}")
print("=================================================================")
