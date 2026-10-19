import os
import torch
from pathlib import Path
from PIL import Image
from diffusers import StableDiffusionXLPipeline, DPMSolverMultistepScheduler

device = "mps" if torch.backends.mps.is_available() else "cpu"
dtype = torch.float16 if device == "mps" else torch.float32

model_path = "models/cyberrealistic-xl/CyberRealisticXLPlay_V10.0_FP16.safetensors"

# Common prompt elements that define Riya's photorealistic persona
riya_prompt = (
    "masterpiece, 8k raw photo, photorealistic intimate editorial portrait of 23-year-old fictional Indian model Riya, "
    "slender toned body, defined collarbones, warm golden caramel skin, mesmerizing dark almond eyes, "
    "subtle beauty mark above lip, glossy dark wavy hair. "
    "Tasteful aesthetic nude, open body, completely bare without any clothing, covering breasts gracefully with forearm, "
    "natural soft morning light through bedroom sheer curtains, authentic skin pores, delicate collarbones, "
    "85mm f/1.4 lens, natural skin texture, perfectly formed hands, five fingers on each hand"
)

riya_neg = (
    "clothes, bra, panties, underwear, fabric, strap, dress, "
    "blurry, cartoon, 3d, render, deformed, distorted, bad anatomy, "
    "extra fingers, missing fingers, fused fingers, mutated hands, poorly drawn hands, "
    "bad eyes, crossed eyes, plastic skin, doll, oversaturated, harsh glare, specular blowout, "
    "child, teenager, minor, text, watermark, signature"
)

# Test A: Native CyberRealistic XL with Riya's exact persona anchor (Seed 440 - same as lace photo)
print("=== Generating A: Native CyberRealistic XL (Seed 440, Clean Persona Anchor) ===")
pipe_a = StableDiffusionXLPipeline.from_single_file(model_path, torch_dtype=dtype).to(device)
pipe_a.scheduler = DPMSolverMultistepScheduler.from_config(pipe_a.scheduler.config, use_karras_sigmas=True)

img_a = pipe_a(
    prompt=riya_prompt,
    negative_prompt=riya_neg,
    width=768,
    height=1152,
    num_inference_steps=30,
    guidance_scale=5.0,
    generator=torch.Generator(device).manual_seed(440)
).images[0]

img_a.save("generated/riya_clean_persona_anchor.png")
print("Saved generated/riya_clean_persona_anchor.png")

del pipe_a
torch.mps.empty_cache()

# Test B: Gentle IP-Adapter-FaceID-PlusV2 (scale=0.45, s_scale=0.25, NO double LoRA)
print("=== Generating B: Tuned IP-Adapter-FaceID-PlusV2 (Gentle scale 0.45, s_scale 0.25) ===")
import cv2
import insightface
from insightface.app import FaceAnalysis
from insightface.utils import face_align
from ip_adapter.ip_adapter_faceid import IPAdapterFaceIDPlusXL

face_app = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
face_app.prepare(ctx_id=0, det_size=(640, 640))
ref_img = cv2.imread("generated/riya_indian_glamour_closeup_lace.png")
faces = face_app.get(ref_img)
faceid_embeds = torch.from_numpy(faces[0].normed_embedding).unsqueeze(0)
face_image = face_align.norm_crop(ref_img, landmark=faces[0].kps, image_size=224)
face_image_pil = Image.fromarray(cv2.cvtColor(face_image, cv2.COLOR_BGR2RGB))

pipe_b = StableDiffusionXLPipeline.from_single_file(model_path, torch_dtype=dtype).to(device)
pipe_b.scheduler = DPMSolverMultistepScheduler.from_config(pipe_b.scheduler.config, use_karras_sigmas=True)

# Important: DO NOT fuse LoRA into UNet base! Pass bin directly to IPAdapterFaceIDPlusXL
ip_ckpt = "models/ip-adapter-faceid/ip-adapter-faceid-plusv2_sdxl.bin"
image_encoder = "laion/CLIP-ViT-H-14-laion2B-s32B-b79K"
ip_model = IPAdapterFaceIDPlusXL(pipe_b, image_encoder_path=image_encoder, ip_ckpt=ip_ckpt, device=device, torch_dtype=dtype)

img_b = ip_model.generate(
    face_image=face_image_pil,
    faceid_embeds=faceid_embeds,
    prompt=riya_prompt,
    negative_prompt=riya_neg,
    scale=0.45,
    s_scale=0.25,
    shortcut=True,
    width=768,
    height=1152,
    num_inference_steps=30,
    guidance_scale=5.0,
    seed=440
)[0]

img_b.save("generated/riya_faceid_tuned_gentle.png")
print("Saved generated/riya_faceid_tuned_gentle.png")
print("Both tests finished!")
