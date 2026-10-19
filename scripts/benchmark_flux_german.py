import os
import sys
import time
import torch
from pathlib import Path
from PIL import Image
from diffusers import FluxPipeline, FluxTransformer2DModel, GGUFQuantizationConfig

out_dir = Path("generated/german_girl_glamour")
out_dir.mkdir(parents=True, exist_ok=True)

# 72-token prompt targeting German glamour with uncensored anatomy
prompt = (
    "8k raw photo, photorealistic full body nude portrait of 22yo German woman, "
    "athletic toned curves, slender waist, firm bust, fair skin with light freckles. "
    "Hands resting on hips, five fingers, radiant blue eyes, blonde hair, clean natural hairline. "
    "Unclad, bare skin, luxury penthouse, soft window light, 35mm"
)

gguf_transformer_path = "models/flux-1-dev-gguf/flux1-dev-Q4_K_S.gguf"
local_config_path = "models/flux-1-dev-gguf"
lora_path = "models/flux-lora/scg-anatomy-female-v2.safetensors"
out_path = out_dir / "german_girl_flux_dev_gguf.png"

print("=================================================================")
print("  FLUX.1 [dev] GGUF Q4 + NSFW LoRA BENCHMARK (GERMAN GLAMOUR)")
print("  Device: Apple Silicon MPS | Memory: CPU Offloaded | Steps: 20")
print("=================================================================\n")

t0 = time.time()
print(f"Loading Quantized Q4 FLUX.1 [dev] Transformer from {gguf_transformer_path}...")
transformer = FluxTransformer2DModel.from_single_file(
    gguf_transformer_path,
    config=local_config_path,
    quantization_config=GGUFQuantizationConfig(compute_dtype=torch.bfloat16),
    torch_dtype=torch.bfloat16
)
print(f"Loaded transformer in {time.time() - t0:.2f}s")

print("Assembling FluxPipeline...")
t_pipe = time.time()
pipe = FluxPipeline.from_pretrained(
    "Niansuh/FLUX.1-schnell",
    transformer=transformer,
    torch_dtype=torch.bfloat16
)
print(f"Pipeline assembled in {time.time() - t_pipe:.2f}s")

print("Enabling dynamic model CPU offload for 16GB memory safety...")
pipe.enable_model_cpu_offload()

if os.path.exists(lora_path):
    print(f"Loading SCG Anatomy NSFW LoRA from {lora_path}...")
    pipe.load_lora_weights(lora_path)
    print("NSFW LoRA loaded successfully!")
else:
    print(f"Warning: LoRA not found at {lora_path}, proceeding without LoRA.")

print("\nStarting FLUX generation (20 steps, guidance 3.5, 768x1152, seed 777)...")
t_gen = time.time()
generator = torch.Generator().manual_seed(777)

image = pipe(
    prompt=prompt,
    width=768,
    height=1152,
    num_inference_steps=20,
    guidance_scale=3.5,
    generator=generator
).images[0]

gen_time = time.time() - t_gen
image.save(str(out_path))

print(f"\nFLUX Generation completed in {gen_time:.2f}s ({gen_time/20:.2f}s/step)")
print(f"Saved FLUX render to: {out_path}")
print("=================================================================")
