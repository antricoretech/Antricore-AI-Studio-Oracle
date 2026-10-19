import os
import cv2
import torch
from PIL import Image
from diffusers import StableDiffusionXLPipeline, DPMSolverMultistepScheduler
from insightface.app import FaceAnalysis
from insightface.utils import face_align
from ip_adapter.ip_adapter_faceid import IPAdapterFaceIDPlusXL, IPAdapterFaceIDXL

device = "mps" if torch.backends.mps.is_available() else "cpu"
dtype = torch.float16 if device == "mps" else torch.float32

ref_path = "generated/riya_indian_glamour_closeup_lace.png"
print(f"Extracting face from {ref_path}...")
app = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
app.prepare(ctx_id=0, det_size=(640, 640))
img_cv2 = cv2.imread(ref_path)
faces = app.get(img_cv2)
faceid_embeds = torch.from_numpy(faces[0].normed_embedding).unsqueeze(0)
face_image = face_align.norm_crop(img_cv2, landmark=faces[0].kps, image_size=224)
face_image_pil = Image.fromarray(cv2.cvtColor(face_image, cv2.COLOR_BGR2RGB))

# Base model
model_path = "models/cyberrealistic-xl/CyberRealisticXLPlay_V10.0_FP16.safetensors"

prompt = "masterpiece, 8k uhd, photorealistic RAW candid photo of 21yo Indian woman Riya, natural face, warm skin texture, tasteful intimate portrait, covering private parts with hands, soft resort bedroom morning light, delicate collarbones, cinematic lighting, realistic eyes, natural lips"
negative_prompt = "ugly, deformed, disfigured, bad eyes, bad hands, plastic, fake skin, 3d render, cartoon, doll, harsh specular, watermark, text, signature, overexposed, oversaturated"

# Test 1: Pure FaceID XL (No CLIP image encoder, no double LoRA, clean 512-dim face ID injection)
print("--- TEST 1: Pure FaceID XL (scale=0.6, no double LoRA) ---")
pipe1 = StableDiffusionXLPipeline.from_single_file(model_path, torch_dtype=dtype).to(device)
pipe1.scheduler = DPMSolverMultistepScheduler.from_config(pipe1.scheduler.config, use_karras_sigmas=True)

ip_ckpt_pure = "models/ip-adapter-faceid/ip-adapter-faceid_sdxl.bin"
ip_model1 = IPAdapterFaceIDXL(pipe1, ip_ckpt=ip_ckpt_pure, device=device, torch_dtype=dtype)

img1 = ip_model1.generate(
    faceid_embeds=faceid_embeds,
    prompt=prompt,
    negative_prompt=negative_prompt,
    scale=0.6,
    width=768,
    height=1152,
    num_inference_steps=28,
    guidance_scale=5.0,
    seed=108
)[0]
img1.save("generated/riya_pure_faceid_test.png")
print("Saved generated/riya_pure_faceid_test.png")

del ip_model1
del pipe1
torch.mps.empty_cache()

# Test 2: FaceID Plus V2 with tuned scales (scale=0.55, s_scale=0.4, NO double LoRA)
print("--- TEST 2: FaceID Plus V2 (scale=0.55, s_scale=0.4, no double LoRA) ---")
pipe2 = StableDiffusionXLPipeline.from_single_file(model_path, torch_dtype=dtype).to(device)
pipe2.scheduler = DPMSolverMultistepScheduler.from_config(pipe2.scheduler.config, use_karras_sigmas=True)

ip_ckpt_plus = "models/ip-adapter-faceid/ip-adapter-faceid-plusv2_sdxl.bin"
image_encoder = "laion/CLIP-ViT-H-14-laion2B-s32B-b79K"
ip_model2 = IPAdapterFaceIDPlusXL(pipe2, image_encoder_path=image_encoder, ip_ckpt=ip_ckpt_plus, device=device, torch_dtype=dtype)

img2 = ip_model2.generate(
    face_image=face_image_pil,
    faceid_embeds=faceid_embeds,
    prompt=prompt,
    negative_prompt=negative_prompt,
    scale=0.55,
    s_scale=0.4,
    shortcut=True,
    width=768,
    height=1152,
    num_inference_steps=28,
    guidance_scale=5.0,
    seed=108
)[0]
img2.save("generated/riya_plusv2_tuned_test.png")
print("Saved generated/riya_plusv2_tuned_test.png")
print("Diagnosis complete!")
