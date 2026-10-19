#!/usr/bin/env python3
"""
Render Luxury Editorial Typography & Vector Graphic Overlays for Method B Testing
No diffusion inference required - instantly overlays on top of pristine clean images.
"""
from pathlib import Path
import shutil
from PIL import Image, ImageDraw, ImageFont

clean_dir = Path("generated/testing_pov_date")
out_dir = Path("generated/testing_pov_date")
artifacts_dir = Path("/Users/guddugiri/.gemini/antigravity-ide/brain/739e6f68-e605-4993-ba1b-f78ad891d4d4")

scenes_data = [
    {
        "clean_filename": "pov_date_01_arrival_clean.png",
        "editorial_filename": "pov_date_01_arrival_editorial.png",
        "category_badge": "POV · DATE NIGHT",
        "location": "AMALFI COAST · 19:15",
        "slide_index": "01 / 03",
        "hook_title": "POV: You Took Me To Your Favorite Spot",
        "hook_dialogue": "\"I'm glad you reserved this table... what should we order first?\"",
        "action_label": "SWIPE TO DINE",
    },
    {
        "clean_filename": "pov_date_02_dinner_clean.png",
        "editorial_filename": "pov_date_02_dinner_editorial.png",
        "category_badge": "POV · DINNER FOR TWO",
        "location": "SEASIDE BISTRO · 20:45",
        "slide_index": "02 / 03",
        "hook_title": "POV: Sitting Across From Me All Evening",
        "hook_dialogue": "\"Tell me the truth... have you been looking at me or the view?\"",
        "action_label": "SWIPE TO TERRACE",
    },
    {
        "clean_filename": "pov_date_03_balcony_clean.png",
        "editorial_filename": "pov_date_03_balcony_editorial.png",
        "category_badge": "POV · AFTER DINNER",
        "location": "TERRACE BALCONY · 22:30",
        "slide_index": "03 / 03",
        "hook_title": "POV: The Night Doesn't Have To End Yet",
        "hook_dialogue": "\"Do we stay for one more glass of champagne, or take a midnight walk?\"",
        "action_label": "SAVE & SHARE",
    }
]

# Helper to draw a crisp vector location pin
def draw_vector_pin(draw, x, y, color):
    # Circle head
    draw.ellipse((x, y, x + 14, y + 14), fill=color)
    # Inner dark dot
    draw.ellipse((x + 4, y + 4, x + 10, y + 10), fill=(15, 20, 30, 255))
    # Pointy bottom
    draw.polygon([(x + 2, y + 9), (x + 12, y + 9), (x + 7, y + 19)], fill=color)

# Helper to draw a gold 4-point diamond star sparkle
def draw_gold_star(draw, cx, cy, radius, color):
    # Vertical and horizontal points
    points = [
        (cx, cy - radius),
        (cx + radius * 0.35, cy - radius * 0.35),
        (cx + radius, cy),
        (cx + radius * 0.35, cy + radius * 0.35),
        (cx, cy + radius),
        (cx - radius * 0.35, cy + radius * 0.35),
        (cx - radius, cy),
        (cx - radius * 0.35, cy - radius * 0.35)
    ]
    draw.polygon(points, fill=color)

# Helper to draw a small right arrow
def draw_vector_arrow(draw, x, y, length, color):
    draw.line([(x, y), (x + length, y)], fill=color, width=2)
    draw.polygon([(x + length - 4, y - 4), (x + length + 4, y), (x + length - 4, y + 4)], fill=color)

def apply_editorial_overlay(clean_img_path: Path, out_path: Path, data: dict):
    img = Image.open(clean_img_path).convert("RGBA")
    w, h = img.size
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # Fonts
    f_cinzel = "fonts/Cinzel-Bold.ttf"
    f_playfair = "fonts/PlayfairDisplay-Bold.ttf"
    f_montserrat = "fonts/Montserrat-SemiBold.ttf"

    font_badge = ImageFont.truetype(f_cinzel, 18)
    font_loc = ImageFont.truetype(f_montserrat, 16)
    font_slide = ImageFont.truetype(f_cinzel, 15)
    font_hook_title = ImageFont.truetype(f_playfair, 30)
    font_hook_dialogue = ImageFont.truetype(f_montserrat, 19)
    font_action = ImageFont.truetype(f_cinzel, 15)

    # -------------------------------------------------------------
    # TOP HEADER NAVIGATION (Pills)
    # -------------------------------------------------------------
    top_y = 35

    # 1. Top-Left Pill: Series Badge
    badge_text = data["category_badge"]
    bbox_b = draw.textbbox((0, 0), badge_text, font=font_badge)
    w_b = bbox_b[2] - bbox_b[0]
    box_b = (35, top_y, 35 + w_b + 40, top_y + 44)
    # Dark luxury glass pill with gold metallic border
    draw.rounded_rectangle(box_b, radius=22, fill=(10, 14, 22, 225), outline=(212, 175, 55, 180), width=1)
    # Gold star icon inside left of pill
    draw_gold_star(draw, 35 + 18, top_y + 22, 7, (254, 240, 138, 255))
    draw.text((35 + 32, top_y + 12), badge_text, font=font_badge, fill=(255, 248, 220, 255))

    # 2. Top-Right Pill: Location & Time with Vector Pin
    loc_text = data["location"]
    bbox_loc = draw.textbbox((0, 0), loc_text, font=font_loc)
    w_loc = bbox_loc[2] - bbox_loc[0]
    box_loc = (w - 35 - w_loc - 50, top_y, w - 35, top_y + 44)
    draw.rounded_rectangle(box_loc, radius=22, fill=(10, 14, 22, 215), outline=(255, 255, 255, 75), width=1)
    
    pin_x = w - 35 - w_loc - 34
    draw_vector_pin(draw, pin_x, top_y + 12, (254, 240, 138, 240))
    draw.text((pin_x + 22, top_y + 12), loc_text, font=font_loc, fill=(241, 245, 249, 240))

    # -------------------------------------------------------------
    # BOTTOM LUXURY EDITORIAL CARD (Frosted Glass & Gold Trim)
    # -------------------------------------------------------------
    card_h = 175
    card_margin_b = 35
    card_y = h - card_margin_b - card_h
    card_box = (35, card_y, w - 35, card_y + card_h)

    # Base luxury container: Deep black obsidian glass with double border
    draw.rounded_rectangle(card_box, radius=18, fill=(8, 12, 20, 235), outline=(212, 175, 55, 190), width=2)

    # Inner decorative hairline
    draw.line([(55, card_y + 1), (w - 55, card_y + 1)], fill=(254, 240, 138, 90), width=1)

    # Row 1: Slide Pill & Interactive Action Cue
    slide_text = f"SLIDE {data['slide_index']}"
    bbox_s = draw.textbbox((0, 0), slide_text, font=font_slide)
    w_s = bbox_s[2] - bbox_s[0]
    s_pill_box = (55, card_y + 18, 55 + w_s + 20, card_y + 44)
    draw.rounded_rectangle(s_pill_box, radius=13, fill=(30, 41, 59, 220), outline=(212, 175, 55, 140), width=1)
    draw.text((65, card_y + 23), slide_text, font=font_slide, fill=(254, 240, 138, 240))

    # Right action label with vector arrow
    action_text = data["action_label"]
    bbox_act = draw.textbbox((0, 0), action_text, font=font_action)
    w_act = bbox_act[2] - bbox_act[0]
    act_x = w - 55 - w_act - 24
    draw.text((act_x, card_y + 24), action_text, font=font_action, fill=(203, 213, 225, 220))
    draw_vector_arrow(draw, w - 62, card_y + 31, 14, (254, 240, 138, 240))

    # Row 2: Hook Title (Playfair Display Luxury Vogue Serif)
    draw.text((55, card_y + 58), data["hook_title"], font=font_hook_title, fill=(255, 255, 255, 255))

    # Row 3: Dialogue / Caption (Montserrat) with Gold Diamond Accents
    dial_text = data["hook_dialogue"]
    draw_gold_star(draw, 64, card_y + 128, 6, (212, 175, 55, 240))
    draw.text((78, card_y + 118), dial_text, font=font_hook_dialogue, fill=(226, 232, 240, 245))

    # Subtle bottom accent bar
    draw.rounded_rectangle((w // 2 - 30, card_y + card_h - 10, w // 2 + 30, card_y + card_h - 6), radius=2, fill=(212, 175, 55, 160))

    # Composite layers
    final_img = Image.alpha_composite(img, overlay).convert("RGB")
    final_img.save(out_path, format="PNG", quality=98)
    print(f"Successfully generated: {out_path.name}")

# Run overlay for all 3 scenes
for sc in scenes_data:
    clean_p = clean_dir / sc["clean_filename"]
    editorial_p = out_dir / sc["editorial_filename"]
    apply_editorial_overlay(clean_p, editorial_p, sc)
    
    # Copy to artifacts directory
    shutil.copy2(clean_p, artifacts_dir / clean_p.name)
    shutil.copy2(editorial_p, artifacts_dir / editorial_p.name)
    print(f"Copied to artifacts: {clean_p.name} and {editorial_p.name}")

print("\n--- ALL 3 POV DATE EDITORIAL OVERLAYS COMPLETED IN UNDER 1 SECOND! ---")
