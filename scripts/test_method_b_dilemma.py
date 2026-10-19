import os
import sys
import time
import shutil
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import torch
from diffusers import StableDiffusionXLPipeline, DPMSolverMultistepScheduler

out_dir = Path("generated/testing_dilemma")
out_dir.mkdir(parents=True, exist_ok=True)

artifacts_dir = Path("/Users/guddugiri/.gemini/antigravity-ide/brain/739e6f68-e605-4993-ba1b-f78ad891d4d4")

device = "mps" if torch.backends.mps.is_available() else "cpu"
dtype = torch.float16 if device == "mps" else torch.float32

model_file = "models/juggernaut-xl-v10/Juggernaut-X-RunDiffusion-NSFW.safetensors"

print(f"Loading pipeline from {model_file}...")
pipe = StableDiffusionXLPipeline.from_single_file(model_file, torch_dtype=dtype).to(device)
pipe.scheduler = DPMSolverMultistepScheduler.from_config(pipe.scheduler.config, use_karras_sigmas=True)

# Concise, high-impact prompts under 55 tokens to ensure full body framing & bikini visibility
options_data = [
    {
        "id": "option1",
        "title": "OPTION 01: LUXURY BLACK BIKINI",
        "badge_num": "01 / 03",
        "prompt": (
            "8k raw photo, waist-up portrait of 22yo German woman Elena Weber, "
            "wearing stylish luxury black bikini, standing by edge of infinity pool, "
            "striking hazel eyes, blonde wavy hair, athletic curvy 34D-24-35 physique, "
            "natural skin texture, authentic pores, sunny afternoon, 35mm lens"
        ),
        "seed": 444,
        "clean_filename": "dilemma_option1_black_clean.png",
        "editorial_filename": "dilemma_option1_black_editorial.png",
        "top_left_badge": "OPTION 01 / 03 · MINIMALIST BLACK",
        "hook_title": "HELP ME CHOOSE: 1, 2, or 3?",
        "hook_sub": "Option 1: Classic Black. Going to the pool soon... Vote below! 👇",
        "location": "📍 VILLA HORIZON · IBIZA",
    },
    {
        "id": "option2",
        "title": "OPTION 02: SCARLET RED BIKINI",
        "badge_num": "02 / 03",
        "prompt": (
            "8k raw photo, waist-up portrait of 22yo German woman Elena Weber, "
            "wearing vibrant scarlet red bikini, relaxing on luxury sun lounger terrace, "
            "striking hazel eyes, blonde wavy hair, athletic curvy 34D-24-35 physique, "
            "sun-kissed skin texture, authentic pores, warm golden sunlight, 35mm lens"
        ),
        "seed": 888,
        "clean_filename": "dilemma_option2_red_clean.png",
        "editorial_filename": "dilemma_option2_red_editorial.png",
        "top_left_badge": "OPTION 02 / 03 · SCARLET SUNSET",
        "hook_title": "HELP ME CHOOSE: 1, 2, or 3?",
        "hook_sub": "Option 2: Bold Red. Or is red the move today? Tell me below! 👇",
        "location": "📍 SUNSET DECK · IBIZA",
    },
    {
        "id": "option3",
        "title": "OPTION 03: SHEER WHITE CABANA",
        "badge_num": "03 / 03",
        "prompt": (
            "8k raw photo, waist-up portrait of 22yo German woman Elena Weber, "
            "wearing chic sheer white lace beach cover-up over white bikini, "
            "sitting in resort cabana daybed, striking hazel eyes, blonde wavy hair, "
            "athletic curvy 34D-24-35 physique, radiant playful smile, authentic skin, 35mm lens"
        ),
        "seed": 999,
        "clean_filename": "dilemma_option3_white_clean.png",
        "editorial_filename": "dilemma_option3_white_editorial.png",
        "top_left_badge": "OPTION 03 / 03 · WHITE RESORT",
        "hook_title": "HELP ME CHOOSE: 1, 2, or 3?",
        "hook_sub": "Option 3: Sheer White Lace. What's your favorite fit? 1, 2 or 3? 👇",
        "location": "📍 RESORT CABANA · IBIZA",
    }
]

NEGATIVE_PROMPT = (
    "nude, bare, topless, deformed, bad anatomy, bad hands, extra fingers, missing fingers, "
    "plastic skin, smooth doll skin, 3d render, cartoon, anime, illustration, "
    "blurry, bad eyes, lowres, watermark, text"
)

# Typography helper for Method B with exact text bounding boxes
def apply_method_b_overlay(img_path: Path, out_path: Path, data: dict):
    img = Image.open(img_path).convert("RGBA")
    w, h = img.size
    
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    
    font_bold_path = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
    font_reg_path = "/System/Library/Fonts/Supplemental/Arial.ttf"
    
    font_pill = ImageFont.truetype(font_bold_path, 20)
    font_loc = ImageFont.truetype(font_bold_path, 18)
    font_hook_title = ImageFont.truetype(font_bold_path, 26)
    font_hook_sub = ImageFont.truetype(font_reg_path, 20)
    font_swipe = ImageFont.truetype(font_bold_path, 18)
    
    top_y = 35
    
    # Left pill: Option badge (calculated with textbbox for pixel perfection)
    left_text = data["top_left_badge"]
    bbox_left = draw.textbbox((0, 0), left_text, font=font_pill)
    text_w_left = bbox_left[2] - bbox_left[0]
    pill_box_left = (35, top_y, 35 + text_w_left + 32, top_y + 40)
    draw.rounded_rectangle(pill_box_left, radius=20, fill=(15, 23, 42, 220), outline=(255, 255, 255, 80), width=1)
    draw.text((35 + 16, top_y + 9), left_text, font=font_pill, fill=(255, 255, 255, 250))
    
    # Right pill: Location stamp
    loc_text = data["location"]
    bbox_loc = draw.textbbox((0, 0), loc_text, font=font_loc)
    text_w_loc = bbox_loc[2] - bbox_loc[0]
    pill_box_right = (w - 35 - text_w_loc - 28, top_y, w - 35, top_y + 40)
    draw.rounded_rectangle(pill_box_right, radius=20, fill=(15, 23, 42, 200), outline=(255, 255, 255, 70), width=1)
    draw.text((w - 35 - text_w_loc - 14, top_y + 10), loc_text, font=font_loc, fill=(226, 232, 240, 240))
    
    # Bottom Engagement Sticker
    card_margin_bottom = 40
    card_h = 120
    card_y = h - card_margin_bottom - card_h
    card_box = (35, card_y, w - 35, card_y + card_h)
    
    draw.rounded_rectangle(card_box, radius=14, fill=(11, 15, 25, 220), outline=(56, 189, 248, 150), width=2)
    
    # Hook Title
    draw.text((55, card_y + 18), data["hook_title"], font=font_hook_title, fill=(56, 189, 248, 255))
    
    # Hook Subtext
    draw.text((55, card_y + 60), data["hook_sub"], font=font_hook_sub, fill=(241, 245, 249, 245))
    
    # Swipe Indicator
    swipe_text = f"{data['badge_num']}  ->  SWIPE"
    bbox_swipe = draw.textbbox((0, 0), swipe_text, font=font_swipe)
    swipe_w = bbox_swipe[2] - bbox_swipe[0]
    draw.text((w - 55 - swipe_w, card_y + 22), swipe_text, font=font_swipe, fill=(203, 213, 225, 220))
    
    final_img = Image.alpha_composite(img, overlay).convert("RGB")
    final_img.save(out_path, format="PNG", quality=98)
    print(f"  Applied Method B Overlay -> {out_path.name}")

# Generate each
for i, opt in enumerate(options_data):
    print(f"\n[{i+1}/3] Generating {opt['title']} (Seed: {opt['seed']})...")
    generator = torch.Generator(device).manual_seed(opt["seed"])
    t0 = time.time()
    
    image = pipe(
        prompt=opt["prompt"],
        negative_prompt=NEGATIVE_PROMPT,
        width=768,
        height=1152,
        num_inference_steps=28,
        guidance_scale=5.0,
        generator=generator
    ).images[0]
    
    print(f"  Diffusion complete in {time.time() - t0:.2f}s")
    
    clean_path = out_dir / opt["clean_filename"]
    image.save(clean_path, format="PNG")
    print(f"  Saved Clean Image -> {clean_path.name}")
    
    editorial_path = out_dir / opt["editorial_filename"]
    apply_method_b_overlay(clean_path, editorial_path, opt)
    
    shutil.copy2(clean_path, artifacts_dir / clean_path.name)
    shutil.copy2(editorial_path, artifacts_dir / editorial_path.name)

print("\n=================================================================")
print("  RE-RENDER COMPLETE: PERFECT WAIST-UP BIKINI FRAMING + METHOD B")
print("=================================================================")
