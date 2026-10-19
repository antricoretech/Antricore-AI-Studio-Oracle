import os
import sys
import cv2
import torch
from pathlib import Path
from PIL import Image

import insightface
from insightface.app import FaceAnalysis
from insightface.utils import face_align
from diffusers import StableDiffusionXLPipeline, DPMSolverMultistepScheduler
from ip_adapter.ip_adapter_faceid import IPAdapterFaceIDPlusXL

device = "mps" if torch.backends.mps.is_available() else "cpu"
dtype = torch.float16 if device == "mps" else torch.float32

print(f"Device: {device}, Dtype: {dtype}")

# 1. Face Extraction
ref_path = "generated/riya_indian_glamour_closeup_lace.png"
print(f"Extracting face embedding from {ref_path}...")
app = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
app.prepare(ctx_id=0, det_size=(640, 640))

img_cv2 = cv2.imread(ref_path)
faces = app.get(img_cv2)
if not faces:
    raise ValueError("No face detected!")

faceid_embeds = torch.from_numpy(faces[0].normed_embedding).unsqueeze(0)
face_image = face_align.norm_crop(img_cv2, landmark=faces[0].kps, image_size=224)
face_image_pil = Image.fromarray(cv2.cvtColor(face_image, cv2.COLOR_BGR2RGB))

# 2. Load CyberRealistic XL Base Pipeline
model_path = "models/cyberrealistic-xl/cyberrealisticXL_v22.safetensors"
if not os.path.exists(model_path):
    # Try finding any safetensors in models/cyberrealistic-xl
    files = list(Path("models/cyberrealistic-xl").glob("*.safetensors"))
    if not files:
        raise FileNotFoundError("CyberRealistic XL checkpoint not found")
    model_path = str(files[0])

print(f"Loading pipeline from {model_path}...")
pipe = StableDiffusionXLPipeline.from_single_file(
    model_path,
    torch_dtype=dtype,
    use_safetensors=True
).to(device)

pipe.scheduler = DPMSolverMultistepScheduler.from_config(pipe.scheduler.config, use_karras_sigmas=True)

# 3. Load IP-Adapter FaceID PlusV2 LoRA
lora_path = "models/ip-adapter-faceid/ip-adapter-faceid-plusv2_sdxl_lora.safetensors"
if os.path.exists(lora_path):
    print(f"Loading and fusing LoRA from {lora_path}...")
    pipe.load_lora_weights(lora_path)
    pipe.fuse_lora()

# 4. Initialize IPAdapterFaceIDPlusXL
image_encoder_path = "laion/CLIP-ViT-H-14-laion2B-s32B-b79K"
ip_ckpt = "models/ip-adapter-faceid/ip-adapter-faceid-plusv2_sdxl.bin"

print("Initializing IPAdapterFaceIDPlusXL...")
ip_model = IPAdapterFaceIDPlusXL(
    pipe,
    image_encoder_path=image_encoder_path,
    ip_ckpt=ip_ckpt,
    device=device,
    torch_dtype=dtype
)

# 5. Quick 5-step test run
prompt = "stunning portrait of 21yo Indian woman Riya, elegant emerald evening gown, soft warm studio lighting, 8k uhd, photorealistic"
negative_prompt = "ugly, deformed, low quality, bad anatomy, bad hands, blurry, cartoon"

print("Running test generation (5 steps)...")
images = ip_model.generate(
    face_image=face_image_pil,
    faceid_embeds=faceid_embeds,
    prompt=prompt,
    negative_prompt=negative_prompt,
    scale=0.75,
    s_scale=1.0,
    shortcut=True,
    num_samples=1,
    width=768,
    height=1024,
    num_inference_steps=5,
    guidance_scale=5.0,
    seed=42
)

out_file = "generated/test_faceid_riya.png"
images[0].save(out_file)
print(f"Test generation successful! Saved to {out_file}")
