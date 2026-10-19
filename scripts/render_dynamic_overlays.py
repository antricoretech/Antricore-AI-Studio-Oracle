#!/usr/bin/env python3
"""
Dynamic Multi-Style Editorial Typography Engine for Method B
Demonstrates 3 completely unique, non-repetitive visual layouts:
- Style 1: Luxury Fashion Editorial / Vogue Masthead + Floating Circular Stamp
- Style 2: Cinematic Romantic Film Still with Viewfinder Timestamp + Movie Subtitle
- Style 3: Late-Night Asymmetric Frosted Glass Postcard with Handwritten Calligraphy Signature
"""
from pathlib import Path
import shutil
from PIL import Image, ImageDraw, ImageFont

clean_dir = Path("generated/testing_pov_date")
out_dir = Path("generated/testing_pov_date")
artifacts_dir = Path("/Users/guddugiri/.gemini/antigravity-ide/brain/739e6f68-e605-4993-ba1b-f78ad891d4d4")

# Load fonts
f_cinzel = "fonts/Cinzel-Bold.ttf"
f_playfair = "fonts/PlayfairDisplay-Bold.ttf"
f_montserrat = "fonts/Montserrat-SemiBold.ttf"
f_italiana = "fonts/Italiana-Regular.ttf"
f_greatvibes = "fonts/GreatVibes-Regular.ttf"

# Reusable Vector Drawing Helpers (100% Crisp, No Missing Glyph Boxes)
def draw_gold_star(draw, cx, cy, radius, color):
    pts = [
        (cx, cy - radius),
        (cx + radius * 0.35, cy - radius * 0.35),
        (cx + radius, cy),
        (cx + radius * 0.35, cy + radius * 0.35),
        (cx, cy + radius),
        (cx - radius * 0.35, cy + radius * 0.35),
        (cx - radius, cy),
        (cx - radius * 0.35, cy - radius * 0.35)
    ]
    draw.polygon(pts, fill=color)

def draw_vector_pin(draw, x, y, color):
    draw.ellipse((x, y, x + 12, y + 12), fill=color)
    draw.ellipse((x + 4, y + 4, x + 8, y + 8), fill=(10, 15, 25, 255))
    draw.polygon([(x + 2, y + 8), (x + 10, y + 8), (x + 6, y + 17)], fill=color)

def draw_vector_arrow(draw, x, y, length, color):
    draw.line([(x, y), (x + length, y)], fill=color, width=2)
    draw.polygon([(x + length - 4, y - 4), (x + length + 4, y), (x + length - 4, y + 4)], fill=color)

def draw_small_heart(draw, cx, cy, size, color):
    # Vector heart
    r = size // 2
    draw.ellipse((cx - r, cy - r, cx, cy), fill=color)
    draw.ellipse((cx, cy - r, cx + r, cy), fill=color)
    draw.polygon([(cx - r, cy - r // 2), (cx + r, cy - r // 2), (cx, cy + r)], fill=color)


# ==============================================================================
# STYLE 1 (Slide 1 - Arrival): VOGUE EDITORIAL MASTHEAD + CIRCULAR WAX STAMP
# ==============================================================================
def render_style_1_vogue(img_path: Path, out_path: Path):
    img = Image.open(img_path).convert("RGBA")
    w, h = img.size
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    font_masthead = ImageFont.truetype(f_cinzel, 24)
    font_subhead = ImageFont.truetype(f_montserrat, 13)
    font_stamp_title = ImageFont.truetype(f_cinzel, 13)
    font_stamp_bold = ImageFont.truetype(f_playfair, 16)
    font_script = ImageFont.truetype(f_greatvibes, 38)
    font_caption = ImageFont.truetype(f_montserrat, 18)
    font_swipe = ImageFont.truetype(f_cinzel, 14)

    # 1. Top Masthead Banner (Floating luxury bar with gold rules)
    top_bar_y = 35
    top_bar_h = 56
    draw.rounded_rectangle((35, top_bar_y, w - 35, top_bar_y + top_bar_h), radius=12, fill=(10, 14, 24, 215), outline=(212, 175, 55, 160), width=1)
    
    # Gold decorative hairlines
    draw.line([(55, top_bar_y + 12), (180, top_bar_y + 12)], fill=(212, 175, 55, 150), width=1)
    draw.line([(w - 180, top_bar_y + 12), (w - 55, top_bar_y + 12)], fill=(212, 175, 55, 150), width=1)
    draw_gold_star(draw, 195, top_bar_y + 12, 5, (254, 240, 138, 240))
    draw_gold_star(draw, w - 195, top_bar_y + 12, 5, (254, 240, 138, 240))

    # Centered Masthead Title
    m_title = "THE AMALFI ROMANCE · ISSUE I"
    bbox_m = draw.textbbox((0, 0), m_title, font=font_masthead)
    wm = bbox_m[2] - bbox_m[0]
    draw.text(((w - wm) // 2, top_bar_y + 8), m_title, font=font_masthead, fill=(255, 248, 220, 255))
    
    # Sub-location text
    sub_text = "POSITANO COAST · GOLDEN HOUR · 19:15"
    bbox_sub = draw.textbbox((0, 0), sub_text, font=font_subhead)
    ws = bbox_sub[2] - bbox_sub[0]
    draw.text(((w - ws) // 2, top_bar_y + 36), sub_text, font=font_subhead, fill=(203, 213, 225, 220))

    # 2. Floating Circular Luxury Wax Stamp on Top-Right (Asymmetric eye-catcher)
    stamp_cx, stamp_cy, stamp_r = w - 90, 155, 54
    draw.ellipse((stamp_cx - stamp_r, stamp_cy - stamp_r, stamp_cx + stamp_r, stamp_cy + stamp_r), 
                 fill=(12, 18, 30, 235), outline=(212, 175, 55, 220), width=2)
    # Inner ring
    draw.ellipse((stamp_cx - stamp_r + 5, stamp_cy - stamp_r + 5, stamp_cx + stamp_r - 5, stamp_cy + stamp_r - 5), 
                 outline=(254, 240, 138, 120), width=1)
    
    draw_gold_star(draw, stamp_cx, stamp_cy - 27, 5, (254, 240, 138, 255))
    
    t1 = "POV DATE"
    bb1 = draw.textbbox((0, 0), t1, font=font_stamp_title)
    w1 = bb1[2] - bb1[0]
    draw.text((stamp_cx - w1 // 2, stamp_cy - 14), t1, font=font_stamp_title, fill=(212, 175, 55, 255))
    
    t2 = "SLIDE 01"
    bb2 = draw.textbbox((0, 0), t2, font=font_stamp_bold)
    w2 = bb2[2] - bb2[0]
    draw.text((stamp_cx - w2 // 2, stamp_cy + 5), t2, font=font_stamp_bold, fill=(255, 255, 255, 255))
    draw_gold_star(draw, stamp_cx, stamp_cy + 30, 4, (254, 240, 138, 240))

    # 3. Bottom Minimalist Floating Glass Strip with Handwritten Script Accent
    bot_y = h - 145
    draw.rounded_rectangle((35, bot_y, w - 35, bot_y + 105), radius=16, fill=(8, 12, 20, 225), outline=(212, 175, 55, 170), width=1)
    
    # Cursive Calligraphy intro
    draw.text((55, bot_y + 12), "Elena whispered...", font=font_script, fill=(254, 240, 138, 255))
    
    # Caption
    caption = "\"I'm glad you reserved this table... what should we drink first?\""
    draw.text((55, bot_y + 58), caption, font=font_caption, fill=(255, 255, 255, 255), stroke_width=1, stroke_fill=(255, 255, 255, 255))

    # Bottom Right Swipe Pill
    swipe_x = w - 195
    swipe_y = bot_y + 18
    draw.rounded_rectangle((swipe_x, swipe_y, swipe_x + 135, swipe_y + 32), radius=16, fill=(30, 41, 59, 230), outline=(212, 175, 55, 150), width=1)
    draw.text((swipe_x + 18, swipe_y + 8), "SWIPE 01/03", font=font_swipe, fill=(254, 240, 138, 240))
    draw_vector_arrow(draw, swipe_x + 112, swipe_y + 16, 10, (254, 240, 138, 240))

    final_img = Image.alpha_composite(img, overlay).convert("RGB")
    final_img.save(out_path, format="PNG", quality=98)
    print("  -> Saved Style 1 (Vogue Editorial):", out_path.name)


# ==============================================================================
# STYLE 2 (Slide 2 - Dinner): CINEMATIC VIEWFINDER + FLOATING MOVIE SUBTITLE + POLL
# ==============================================================================
def render_style_2_cinematic(img_path: Path, out_path: Path):
    img = Image.open(img_path).convert("RGBA")
    w, h = img.size
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    font_rec = ImageFont.truetype(f_montserrat, 15)
    font_cam = ImageFont.truetype(f_cinzel, 14)
    font_quote = ImageFont.truetype(f_playfair, 27)
    font_signature = ImageFont.truetype(f_greatvibes, 32)
    font_poll_hdr = ImageFont.truetype(f_cinzel, 13)
    font_poll_btn = ImageFont.truetype(f_montserrat, 15)

    # 1. Top Cinema Viewfinder Status (Clean modern film look)
    top_y = 35
    # Left: Rec blinking dot + Timecode
    draw.rounded_rectangle((35, top_y, 250, top_y + 40), radius=20, fill=(12, 16, 26, 220), outline=(255, 255, 255, 70), width=1)
    # Red Record circle
    draw.ellipse((52, top_y + 14, 64, top_y + 26), fill=(239, 68, 68, 255))
    draw.text((74, top_y + 11), "REC  20:45:12", font=font_rec, fill=(241, 245, 249, 240))

    # Right: Location with gold pin
    draw.rounded_rectangle((w - 245, top_y, w - 35, top_y + 40), radius=20, fill=(12, 16, 26, 220), outline=(212, 175, 55, 160), width=1)
    draw_vector_pin(draw, w - 228, top_y + 11, (254, 240, 138, 255))
    draw.text((w - 208, top_y + 12), "SEASIDE BISTRO", font=font_cam, fill=(255, 248, 220, 240))

    # 2. Center-Bottom Floating Cinematic Subtitle (With translucent dark veil)
    sub_h = 175
    sub_y = h - 215
    # Floating glass pill
    draw.rounded_rectangle((35, sub_y, w - 35, sub_y + sub_h), radius=20, fill=(8, 12, 20, 230), outline=(212, 175, 55, 180), width=1)

    # Hairline header inside subtitle card
    draw.text((55, sub_y + 16), "ROMANTIC POV · CANDLELIGHT MOMENT", font=font_cam, fill=(212, 175, 55, 220))
    draw_gold_star(draw, w - 55, sub_y + 24, 6, (254, 240, 138, 240))

    # Romantic dialogue quote
    line1 = "\"Tell me the truth... have you been"
    line2 = "looking at me or the view?\""
    draw.text((55, sub_y + 42), line1, font=font_quote, fill=(255, 255, 255, 255))
    draw.text((55, sub_y + 76), line2, font=font_quote, fill=(254, 240, 138, 255))

    # Elena signature & small red heart
    draw.text((w - 180, sub_y + 74), "– Elena", font=font_signature, fill=(248, 250, 252, 240))
    draw_small_heart(draw, w - 90, sub_y + 92, 12, (239, 68, 68, 240))

    # 3. Interactive Poll Options on bottom of card (Drives engagement & comments!)
    poll_y = sub_y + 118
    # Option A: "Looking at You (89%)"
    draw.rounded_rectangle((55, poll_y, 380, poll_y + 42), radius=10, fill=(40, 50, 70, 240), outline=(212, 175, 55, 190), width=1)
    draw.text((70, poll_y + 12), "A. Looking at You", font=font_poll_btn, fill=(255, 255, 255, 255))
    draw.text((320, poll_y + 12), "89%", font=font_poll_btn, fill=(254, 240, 138, 255))

    # Option B: "The View (11%)"
    draw.rounded_rectangle((395, poll_y, w - 55, poll_y + 42), radius=10, fill=(25, 33, 48, 220), outline=(255, 255, 255, 90), width=1)
    draw.text((410, poll_y + 12), "B. The View", font=font_poll_btn, fill=(226, 232, 240, 255))
    draw.text((w - 105, poll_y + 12), "11%", font=font_poll_btn, fill=(203, 213, 225, 255))

    final_img = Image.alpha_composite(img, overlay).convert("RGB")
    final_img.save(out_path, format="PNG", quality=98)
    print("  -> Saved Style 2 (Cinematic Movie Still):", out_path.name)


# ==============================================================================
# STYLE 3 (Slide 3 - Balcony): ASYMMETRIC POSTCARD / ITALIAN COUTURE LUXURY NOTE
# ==============================================================================
def render_style_3_postcard(img_path: Path, out_path: Path):
    img = Image.open(img_path).convert("RGBA")
    w, h = img.size
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    font_italiana_hdr = ImageFont.truetype(f_italiana, 32)
    font_cinzel_tag = ImageFont.truetype(f_cinzel, 14)
    font_montserrat_body = ImageFont.truetype(f_montserrat, 20)
    font_handwriting = ImageFont.truetype(f_greatvibes, 44)
    font_cta = ImageFont.truetype(f_cinzel, 15)

    # 1. Top Asymmetric Tag on Right (Minimalist couture badge)
    top_y = 35
    tag_box = (w - 290, top_y, w - 35, top_y + 42)
    draw.rounded_rectangle(tag_box, radius=21, fill=(10, 15, 26, 220), outline=(212, 175, 55, 170), width=1)
    draw_gold_star(draw, w - 272, top_y + 21, 6, (254, 240, 138, 255))
    draw.text((w - 256, top_y + 11), "AFTER HOURS · 22:30", font=font_cinzel_tag, fill=(255, 248, 220, 240))

    # 2. Bottom Luxury Asymmetric Postcard Note (Clean, architectural lines)
    card_w = w - 70
    card_h = 195
    card_y = h - 235
    draw.rounded_rectangle((35, card_y, 35 + card_w, card_y + card_h), radius=18, fill=(8, 12, 22, 240), outline=(212, 175, 55, 200), width=2)

    # Gold corner brackets on card
    # Top-Left Bracket
    draw.line([(45, card_y + 10), (75, card_y + 10)], fill=(254, 240, 138, 220), width=2)
    draw.line([(45, card_y + 10), (45, card_y + 40)], fill=(254, 240, 138, 220), width=2)
    # Bottom-Right Bracket
    draw.line([(w - 75, card_y + card_h - 10), (w - 45, card_y + card_h - 10)], fill=(254, 240, 138, 220), width=2)
    draw.line([(w - 45, card_y + card_h - 40), (w - 45, card_y + card_h - 10)], fill=(254, 240, 138, 220), width=2)

    # Postcard Title in Italiana (High Couture Italian Typography)
    draw.text((65, card_y + 20), "The Night Doesn't Have To End Yet", font=font_italiana_hdr, fill=(254, 240, 138, 255))

    # Body dialogue (Crisp white with gold accent)
    b_line1 = "\"Do we stay for one more glass of champagne,"
    b_line2 = "or take a midnight walk along the harbor?\""
    draw.text((65, card_y + 64), b_line1, font=font_montserrat_body, fill=(255, 255, 255, 255), stroke_width=1, stroke_fill=(255, 255, 255, 255))
    draw.text((65, card_y + 92), b_line2, font=font_montserrat_body, fill=(255, 255, 255, 255), stroke_width=1, stroke_fill=(255, 255, 255, 255))

    # Handwritten personal signoff in Great Vibes
    draw.text((65, card_y + 130), "Yours tonight, Elena", font=font_handwriting, fill=(254, 240, 138, 255))

    # Action / Save & Share button on bottom right of the card
    btn_w = 210
    btn_h = 38
    btn_x = w - 55 - btn_w
    btn_y = card_y + 138
    draw.rounded_rectangle((btn_x, btn_y, btn_x + btn_w, btn_y + btn_h), radius=19, fill=(30, 41, 59, 230), outline=(212, 175, 55, 170), width=1)
    
    # Save icon / star
    draw_gold_star(draw, btn_x + 18, btn_y + 19, 5, (254, 240, 138, 255))
    draw.text((btn_x + 30, btn_y + 10), "SAVE THIS DATE IDEA", font=font_cta, fill=(254, 240, 138, 240))

    final_img = Image.alpha_composite(img, overlay).convert("RGB")
    final_img.save(out_path, format="PNG", quality=98)
    print("  -> Saved Style 3 (Couture Postcard):", out_path.name)


# ==============================================================================
# MAIN EXECUTION
# ==============================================================================
if __name__ == "__main__":
    print("\n=======================================================")
    print("  RENDERING 3 DISTINCT DYNAMIC EDITORIAL OVERLAYS")
    print("=======================================================\n")
    
    p1_clean = clean_dir / "pov_date_01_arrival_clean.png"
    p1_out = out_dir / "pov_date_01_arrival_editorial.png"
    render_style_1_vogue(p1_clean, p1_out)
    shutil.copy2(p1_out, artifacts_dir / p1_out.name)

    p2_clean = clean_dir / "pov_date_02_dinner_clean.png"
    p2_out = out_dir / "pov_date_02_dinner_editorial.png"
    render_style_2_cinematic(p2_clean, p2_out)
    shutil.copy2(p2_out, artifacts_dir / p2_out.name)

    p3_clean = clean_dir / "pov_date_03_balcony_clean.png"
    p3_out = out_dir / "pov_date_03_balcony_editorial.png"
    render_style_3_postcard(p3_clean, p3_out)
    shutil.copy2(p3_out, artifacts_dir / p3_out.name)

    print("\n  All 3 distinct styles generated and copied to artifacts!")
