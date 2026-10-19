import os
import sys
import time
import shutil
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import torch
from diffusers import StableDiffusionXLPipeline, DPMSolverMultistepScheduler

out_dir = Path("generated/testing_pov_date")
out_dir.mkdir(parents=True, exist_ok=True)

artifacts_dir = Path("/Users/guddugiri/.gemini/antigravity-ide/brain/739e6f68-e605-4993-ba1b-f78ad891d4d4")

device = "mps" if torch.backends.mps.is_available() else "cpu"
dtype = torch.float16 if device == "mps" else torch.float32

model_file = "models/juggernaut-xl-v10/Juggernaut-X-RunDiffusion-NSFW.safetensors"

print("=================================================================")
print("  TESTING METHOD B: 'POV: YOU TOOK ME ON A DATE' SERIES")
print("  Theme: Glamorous One-Piece Outfits (No Nudity) · High Engagement")
print("  Creative Typography: Cinzel Bold + Playfair Display + Montserrat")
print("  Vector Icons: Drawn Location Pin & Diamond Badges (No Missing Glyphs)")
print("=================================================================\n")

print(f"Loading pipeline from {model_file}...")
pipe = StableDiffusionXLPipeline.from_single_file(model_file, torch_dtype=dtype).to(device)
pipe.scheduler = DPMSolverMultistepScheduler.from_config(pipe.scheduler.config, use_karras_sigmas=True)

# 3 Romantic POV Date Scenes with Glamorous One-Piece Outfits (NO NUDITY)
scenes_data = [
    {
        "id": "scene1",
        "title": "SCENE 01: SUNSET PROMENADE ARRIVAL",
        "badge_num": "01 / 03",
        "prompt": (
            "8k raw photo, waist-up portrait of 22yo German woman Elena Weber, "
            "wearing a glamorous backless emerald green silk one-piece cocktail dress, "
            "looking back over her shoulder holding hand with viewer with an alluring smile, "
            "seaside marina promenade in Amalfi at sunset, warm golden hour illumination, "
            "striking hazel-green eyes, soft natural lips, wavy blonde hair, 35mm photograph"
        ),
        "seed": 1101,
        "clean_filename": "pov_date_01_arrival_clean.png",
        "editorial_filename": "pov_date_01_arrival_editorial.png",
        "top_left_badge": "POV · YOU TOOK ME ON A DATE",
        "location": "AMALFI COAST · 19:15",
        "hook_title": "POV: YOU TOOK ME TO YOUR FAVORITE SPOT",
        "hook_sub": "\"I'm glad you reserved this table... what should we drink first? ✦\"",
        "cta_tag": "SLIDE 01 / 03  ──►  SWIPE",
    },
    {
        "id": "scene2",
        "title": "SCENE 02: CANDLELIT SEASIDE BISTRO",
        "badge_num": "02 / 03",
        "prompt": (
            "8k raw photo, waist-up portrait of 22yo German woman Elena Weber, "
            "wearing an elegant figure-hugging black velvet one-piece evening dress, "
            "sitting across romantic candlelit restaurant table, resting chin on hands looking directly into camera with soft sensual smile, "
            "crystal wine glasses on table, soft warm candlelight on collarbones, "
            "striking hazel-green eyes, detailed natural lips, wavy blonde hair, 85mm lens"
        ),
        "seed": 2202,
        "clean_filename": "pov_date_02_dinner_clean.png",
        "editorial_filename": "pov_date_02_dinner_editorial.png",
        "top_left_badge": "POV · DINNER BY CANDLELIGHT",
        "location": "SEASIDE BISTRO · 20:45",
        "hook_title": "POV: SITTING ACROSS FROM ME ALL EVENING",
        "hook_sub": "\"Tell me the truth... have you been looking at me or the view? ✦\"",
        "cta_tag": "SLIDE 02 / 03  ──►  SWIPE",
    },
    {
        "id": "scene3",
        "title": "SCENE 03: PRIVATE HARBOR BALCONY",
        "badge_num": "03 / 03",
        "prompt": (
            "8k raw photo, waist-up portrait of 22yo German woman Elena Weber, "
            "wearing a luxurious champagne gold satin one-piece slip dress, "
            "leaning against marble balcony railing overlooking twinkling Mediterranean harbor lights, "
            "holding champagne glass, playful teasing smirk, evening sea breeze in wavy blonde hair, "
            "striking hazel-green eyes, soft natural lips, 50mm photograph"
        ),
        "seed": 3303,
        "clean_filename": "pov_date_03_balcony_clean.png",
        "editorial_filename": "pov_date_03_balcony_editorial.png",
        "top_left_badge": "POV · AFTER DINNER DRINKS",
        "location": "TERRACE BALCONY · 22:30",
        "hook_title": "POV: THE NIGHT DOESN'T HAVE TO END YET",
        "hook_sub": "\"Do we stay for one more glass of champagne, or take a walk? ✦\"",
        "cta_tag": "SLIDE 03 / 03  ·  SAVE & SHARE",
    }
]

NEGATIVE_PROMPT = (
    "nude, bare, topless, exposed breasts, deformed, bad anatomy, bad hands, extra fingers, missing fingers, "
    "plastic skin, smooth doll skin, 3d render, cartoon, anime, illustration, "
    "blurry, bad eyes, lowres, watermark, text"
)

# Helper to draw clean vector location pin
def draw_vector_pin(draw, x, y, color):
    draw.ellipse((x, y, x + 12, y + 12), outline=color, width=2)
    draw.ellipse((x + 4, y + 4, x + 8, y + 8), fill=color)
    draw.polygon([(x + 2, y + 8), (x + 10, y + 8), (x + 6, y + 16)], fill=color)

# Enhanced Method B Overlay with Luxury Typography & Vector Badges
def apply_luxury_editorial_overlay(img_path: Path, out_path: Path, data: dict):
    img = Image.open(img_path).convert("RGBA")
    w, h = img.size
    
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    
    # Load Creative Luxury Fonts
    f_cinzel = "fonts/Cinzel-Bold.ttf"
    f_playfair = "fonts/PlayfairDisplay-Bold.ttf"
    f_montserrat = "fonts/Montserrat-SemiBold.ttf"
    
    font_badge = ImageFont.truetype(f_cinzel, 18)
    font_loc = ImageFont.truetype(f_montserrat, 17)
    font_hook_title = ImageFont.truetype(f_playfair, 28)
    font_hook_sub = ImageFont.truetype(f_montserrat, 21)
    font_cta = ImageFont.truetype(f_cinzel, 17)
    
    top_y = 35
    
    # 1. Left Pill: Category / POV Tag (Cinzel Bold)
    left_text = data["top_left_badge"]
    bbox_left = draw.textbbox((0, 0), left_text, font=font_badge)
    w_left = bbox_left[2] - bbox_left[0]
    box_left = (35, top_y, 35 + w_left + 36, top_y + 42)
    # Frosted dark charcoal pill with soft gold border
    draw.rounded_rectangle(box_left, radius=21, fill=(15, 20, 30, 225), outline=(212, 175, 55, 160), width=1)
    draw.text((35 + 18, top_y + 11), left_text, font=font_badge, fill=(255, 248, 220, 255))
    
    # 2. Right Pill: Location & Time (with drawn vector pin icon)
    loc_text = data["location"]
    bbox_loc = draw.textbbox((0, 0), loc_text, font=font_loc)
    w_loc = bbox_loc[2] - bbox_loc[0]
    box_right = (w - 35 - w_loc - 48, top_y, w - 35, top_y + 42)
    draw.rounded_rectangle(box_right, radius=21, fill=(15, 20, 30, 210), outline=(255, 255, 255, 80), width=1)
    
    # Draw vector pin icon
    pin_x = w - 35 - w_loc - 32
    draw_vector_pin(draw, pin_x, top_y + 13, (212, 175, 55, 240))
    # Location text
    draw.text((pin_x + 18, top_y + 11), loc_text, font=font_loc, fill=(241, 245, 249, 240))
    
    # 3. Bottom Romantic POV Engagement Card (Frosted Glass with Gold Accent)
    card_margin_bottom = 40
    card_h = 135
    card_y = h - card_margin_bottom - card_h
    card_box = (35, card_y, w - 35, card_y + card_h)
    
    # Luxury dark glass background with warm champagne gold border
    draw.rounded_rectangle(card_box, radius=16, fill=(10, 14, 22, 230), outline=(212, 175, 55, 180), width=2)
    
    # Golden top decorative hairline inside card
    draw.line([(55, card_y + 1), (w - 55, card_y + 1)], fill=(212, 175, 55, 100), width=1)
    
    # Hook Title (Playfair Display Luxury Serif)
    draw.text((55, card_y + 20), data["hook_title"], font=font_hook_title, fill=(254, 240, 138, 255))
    
    # Hook Subtext (Montserrat)
    draw.text((55, card_y + 65), data["hook_sub"], font=font_hook_sub, fill=(248, 250, 252, 250))
    
    # Bottom CTA Tag / Swipe Cue (Cinzel)
    cta_text = data["cta_tag"]
    bbox_cta = draw.textbbox((0, 0), cta_text, font=font_cta)
    w_cta = bbox_cta[2] - bbox_cta[0]
    draw.text((w - 55 - w_cta, card_y + 24), cta_text, font=font_cta, fill=(203, 213, 225, 230))
    
    # Composite layers
    final_img = Image.alpha_composite(img, overlay).convert("RGB")
    final_img.save(out_path, format="PNG", quality=98)
    print(f"  Applied Luxury Method B Overlay -> {out_path.name}")

# Generate each scene
for i, sc in enumerate(scenes_data):
    print(f"\n[{i+1}/3] Generating {sc['title']} (Seed: {sc['seed']})...")
    generator = torch.Generator(device).manual_seed(sc["seed"])
    t0 = time.time()
    
    image = pipe(
        prompt=sc["prompt"],
        negative_prompt=NEGATIVE_PROMPT,
        width=768,
        height=1152,
        num_inference_steps=28,
        guidance_scale=5.0,
        generator=generator
    ).images[0]
    
    print(f"  Diffusion complete in {time.time() - t0:.2f}s")
    
    clean_path = out_dir / sc["clean_filename"]
    image.save(clean_path, format="PNG")
    print(f"  Saved Clean Image -> {clean_path.name}")
    
    editorial_path = out_dir / sc["editorial_filename"]
    apply_luxury_editorial_overlay(clean_path, editorial_path, sc)
    
    shutil.copy2(clean_path, artifacts_dir / clean_path.name)
    shutil.copy2(editorial_path, artifacts_dir / editorial_path.name)

print("\n=================================================================")
print("  POV DATE SERIES GENERATION WITH LUXURY METHOD B FINISHED!")
print("=================================================================")
