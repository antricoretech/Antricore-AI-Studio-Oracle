import os
import sys
import time
import subprocess
import shutil
import torch
from pathlib import Path
from PIL import Image
from diffusers import StableVideoDiffusionPipeline
from diffusers.utils import export_to_video

out_dir = Path("generated/german_girl_glamour/video")
out_dir.mkdir(parents=True, exist_ok=True)

input_image_path = "generated/german_girl_glamour/german_girl_black_bikini_dance.png"
if not os.path.exists(input_image_path):
    input_image_path = "generated/german_girl_glamour/german_girl_black_bikini.png"

print("=================================================================")
print("  APPROACH 2: SVD-XT MULTI-CLIP CHAINING (FULL-BODY DANCING)")
print("  Target: 7.5 - 8.0s cinematic dancing & teasing video in black bikini")
print("  Device: Apple Silicon MPS | Architecture: SVD-XT + MCI Interpolation")
print("=================================================================\n")

print(f"Loading master dance image from: {input_image_path}")
image = Image.open(input_image_path).convert("RGB")
# Target dimensions: 384x576 (maintaining exact 2:3 aspect ratio, divisible by 64 for latent stability)
target_w, target_h = 384, 576
image_resized = image.resize((target_w, target_h), Image.LANCZOS)
print(f"Resized image for SVD inference: {image_resized.size}")

print("Loading StableVideoDiffusionPipeline from models/svd-xt onto MPS...")
t0 = time.time()
pipe = StableVideoDiffusionPipeline.from_pretrained(
    "models/svd-xt",
    torch_dtype=torch.float16,
    variant="fp16"
).to("mps")
pipe.enable_attention_slicing()
print(f"Loaded SVD-XT pipeline in {time.time() - t0:.2f}s")

# CLIP 1: Initial full-body teasing & dancing motion (0s - 4s)
# High motion bucket (140) triggers full-body hip swaying, shoulder movement, and hair flow
print("\n--- Generating Clip 1 (14 frames, 20 steps, motion bucket 140, seed 42) ---")
t_clip1 = time.time()
generator1 = torch.manual_seed(42)
frames_clip1 = pipe(
    image_resized,
    width=target_w,
    height=target_h,
    num_inference_steps=20,
    num_frames=14,
    decode_chunk_size=2,
    generator=generator1,
    motion_bucket_id=140,
    noise_aug_strength=0.06
).frames[0]
print(f"Clip 1 completed in {time.time() - t_clip1:.2f}s ({len(frames_clip1)} frames)")

# Save keyframe from clip 1
frames_clip1[0].save(out_dir / "clip1_start.png")
frames_clip1[-1].save(out_dir / "clip1_end.png")

# CLIP 2: Continued dancing motion chained from the final frame of Clip 1 (4s - 8s)
# Shifted motion bucket (160) for dynamic teasing motion progression
print("\n--- Generating Clip 2 (14 frames, 20 steps, motion bucket 160, seed 123) ---")
t_clip2 = time.time()
last_frame_clip1 = frames_clip1[-1]
generator2 = torch.manual_seed(123)
frames_clip2 = pipe(
    last_frame_clip1,
    width=target_w,
    height=target_h,
    num_inference_steps=20,
    num_frames=14,
    decode_chunk_size=2,
    generator=generator2,
    motion_bucket_id=160,
    noise_aug_strength=0.07
).frames[0]
print(f"Clip 2 completed in {time.time() - t_clip2:.2f}s ({len(frames_clip2)} frames)")

frames_clip2[-1].save(out_dir / "clip2_end.png")

# Combine Clip 1 and Clip 2 (skipping duplicate boundary frame)
chained_frames = frames_clip1 + frames_clip2[1:]
raw_out_path = str(out_dir / "svd_dance_chained_raw.mp4")

# 27 frames at 3.5 fps = 7.71 seconds
export_to_video(chained_frames, raw_out_path, fps=3.5)
total_raw_duration = len(chained_frames) / 3.5
print(f"\nSaved raw chained dance video ({len(chained_frames)} frames @ 3.5fps = {total_raw_duration:.2f}s) to: {raw_out_path}")

# Run FFmpeg Motion-Compensated Interpolation (MCI) to 30 FPS + Lanczos upscale to 768x1152
final_video_path = str(out_dir / "german_girl_black_bikini_dance_svd_7.8s.mp4")
ffmpeg_bin = "/Users/guddugiri/Developer/AI-Influencer-Studio/.venv/bin/ffmpeg"
if not os.path.exists(ffmpeg_bin):
    ffmpeg_bin = "ffmpeg"

print(f"\nInterpolating to fluid 30 FPS and upscaling to 768x1152 using {ffmpeg_bin}...")
cmd = [
    ffmpeg_bin, "-y",
    "-i", raw_out_path,
    "-vf", "minterpolate=fps=30:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1,scale=768:1152:flags=lanczos",
    "-c:v", "libx264",
    "-crf", "18",
    "-pix_fmt", "yuv420p",
    final_video_path
]

res = subprocess.run(cmd, capture_output=True, text=True)
if res.returncode == 0:
    print(f"SUCCESS! Final cinematic video generated: {final_video_path}")
    print(f"File size: {os.path.getsize(final_video_path) / (1024*1024):.2f} MB")
else:
    print(f"FFmpeg interpolation warning: {res.stderr[-300:]}")
    # Fallback to standard high-quality scale and fps if mci timed out
    fallback_cmd = [
        ffmpeg_bin, "-y",
        "-i", raw_out_path,
        "-vf", "scale=768:1152:flags=lanczos,fps=30",
        "-c:v", "libx264",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        final_video_path
    ]
    subprocess.run(fallback_cmd, check=True)
    print(f"Generated final video via fallback filter: {final_video_path}")

print("=================================================================")
print("  MULTI-CLIP SVD FULL-BODY DANCE GENERATION FINISHED")
print("=================================================================")
