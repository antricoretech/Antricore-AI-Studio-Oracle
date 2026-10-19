import os
import sys
import time
import torch
from pathlib import Path
from PIL import Image
from diffusers import StableDiffusionXLPipeline, DPMSolverMultistepScheduler

device = "mps" if torch.backends.mps.is_available() else "cpu"
dtype = torch.float16 if device == "mps" else torch.float32

out_dir = Path("generated/benchmark_punjabi_glamour/perfected")
out_dir.mkdir(parents=True, exist_ok=True)

# 73-token strictly un-truncated prompt targeting hairline, hands on hips, and curvy unclad figure
corrected_prompt = (
    "8k raw photo, photorealistic full body nude portrait of 23yo curvy Punjabi woman, "
    "voluptuous hourglass figure, soft waist, full hips, golden skin. "
    "Hands resting on hips, five fingers, clean natural hairline, smooth forehead, dark almond eyes. "
    "Unclad, bare skin, luxury bedroom, warm amber light, 35mm"
)

# 64-token strictly un-truncated negative prompt eliminating skin tethers, clothes, and hairline smudges
corrected_negative = (
    "clothes, bra, panties, underwear, bodysuit, swimsuit, dress, fabric, "
    "hands on groin, pulling skin, skin string, double hairline, forehead smudge, "
    "deformed hands, extra fingers, missing fingers, mutated knuckles, "
    "blurry, cartoon, 3d, bad anatomy, deformed"
)

models_to_fix = [
    {
        "id": "juggernaut-xl-v10",
        "name": "Juggernaut XL (v10) - Perfected",
        "file": "models/juggernaut-xl-v10/Juggernaut-X-RunDiffusion-NSFW.safetensors",
        "guidance": 5.0,
        "steps": 30,
        "seed": 999,
        "out_filename": "02_juggernaut_xl_v10_perfected.png"
    },
    {
        "id": "cyberrealistic-xl",
        "name": "CyberRealistic XL (v10) - Perfected",
        "file": "models/cyberrealistic-xl/CyberRealisticXLPlay_V10.0_FP16.safetensors",
        "guidance": 5.5,
        "steps": 30,
        "seed": 999,
        "out_filename": "01_cyberrealistic_xl_perfected.png"
    }
]

print("=================================================================")
print("  GENERATING DEFECT-FREE PUNJABI GLAMOUR IMAGES (ZERO TRUNCATION)")
print(f"  Device: {device} | Dtype: {dtype} | Resolution: 768x1152")
print("=================================================================\n")

for m in models_to_fix:
    print(f"\n--- GENERATING: {m['name']} ---")
    if not os.path.exists(m['file']):
        print(f"Error: Model checkpoint not found at {m['file']}")
        continue
    
    t0 = time.time()
    pipe = StableDiffusionXLPipeline.from_single_file(m['file'], torch_dtype=dtype).to(device)
    pipe.scheduler = DPMSolverMultistepScheduler.from_config(pipe.scheduler.config, use_karras_sigmas=True)
    
    out_path = out_dir / m['out_filename']
    generator = torch.Generator(device).manual_seed(m['seed'])
    
    image = pipe(
        prompt=corrected_prompt,
        negative_prompt=corrected_negative,
        width=768,
        height=1152,
        num_inference_steps=m['steps'],
        guidance_scale=m['guidance'],
        generator=generator
    ).images[0]
    
    image.save(str(out_path))
    print(f"Saved perfected output to: {out_path} ({time.time() - t0:.1f}s)")
    
    del pipe
    if device == "mps":
        torch.mps.empty_cache()

print("\nDone generating perfected images!")
