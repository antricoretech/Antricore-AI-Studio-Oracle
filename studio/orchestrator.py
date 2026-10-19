import os
import json
import time
import secrets
import shutil
import asyncio
from pathlib import Path
from types import SimpleNamespace
from typing import Dict, Any, List, Tuple
from PIL import Image, ImageFilter

import torch

from . import database as db
from .provenance import media_metadata, quality_report, sha256_bytes
from .policies import AI_DISCLOSURE, DEFAULT_NEGATIVE_PROMPT

ASPECT_RATIOS: Dict[str, Tuple[int, int]] = {
    "2:3": (768, 1152),       # Classic Portrait DSLR
    "9:16": (704, 1280),      # Story / Reels Vertical
    "1:1": (1024, 1024),      # Square Feed / Avatar
    "4:5": (864, 1080),       # Instagram Portrait
    "16:9": (1280, 720),      # Cinematic Landscape
    "3:4": (832, 1104),       # Editorial Portrait
}

QUALITY_PRESETS: Dict[str, Dict[str, Any]] = {
    "1080p": {"scale": 1.0, "label": "1080p Full HD", "suffix": "clean raw photo, 35mm photograph"},
    "2K": {"scale": 1.5, "label": "2K QHD (1.5x Upscale)", "suffix": "crisp details, 4k uhd, sharp focus, natural skin texture"},
    "4K": {"scale": 2.0, "label": "4K Ultra HD (2x Upscale)", "suffix": "masterpiece, 8k uhd, hyperdetailed skin pores, film grain, photorealistic"},
    "8K": {"scale": 4.0, "label": "8K Master Studio (4x Upscale)", "suffix": "award-winning photograph, 8k resolution, extreme micro-texture, Hasselblad H6D-100c, studio lighting"},
}

MODEL_ROUTING: Dict[str, Dict[str, str]] = {
    "adult_intimate": {
        "model_id": "cyberrealistic-xl",
        "checkpoint": "models/cyberrealistic-xl/CyberRealisticXLPlay_V10.0_FP16.safetensors",
        "reason": "Unsurpassed natural human anatomy, realistic curves/breasts, uncensored adult skin micro-textures.",
    },
    "erotic_glamour": {
        "model_id": "cyberrealistic-xl",
        "checkpoint": "models/cyberrealistic-xl/CyberRealisticXLPlay_V10.0_FP16.safetensors",
        "reason": "Optimal balance of sensual erotic glamour, boudoir mood lighting, and authentic skin pores.",
    },
    "bikini_beach": {
        "model_id": "juggernaut-xl-v10",
        "checkpoint": "models/juggernaut-xl-v10/Juggernaut-X-RunDiffusion-NSFW.safetensors",
        "reason": "Top-tier outdoor sunlight, swimwear details, vibrant skies, and realistic wet skin reflections.",
    },
    "glamour_lifestyle": {
        "model_id": "juggernaut-xl-v10",
        "checkpoint": "models/juggernaut-xl-v10/Juggernaut-X-RunDiffusion-NSFW.safetensors",
        "reason": "Exceptional lighting, luxury lifestyle environments, rooftop terraces, and natural skin realism.",
    },
    "fashion_editorial": {
        "model_id": "cyberrealistic-xl",
        "checkpoint": "models/cyberrealistic-xl/CyberRealisticXLPlay_V10.0_FP16.safetensors",
        "reason": "High-fashion couture aesthetics, intricate fabric textures, and studio lighting precision.",
    },
    "casual_street": {
        "model_id": "juggernaut-xl-v10",
        "checkpoint": "models/juggernaut-xl-v10/Juggernaut-X-RunDiffusion-NSFW.safetensors",
        "reason": "Authentic candid camera look, depth of field, and natural city backdrops.",
    },
    "fitness_athletic": {
        "model_id": "cyberrealistic-xl",
        "checkpoint": "models/cyberrealistic-xl/CyberRealisticXLPlay_V10.0_FP16.safetensors",
        "reason": "Accurate muscle definition, toned midriff/abs, and dynamic gym/workout lighting.",
    },
}

CATEGORIES = [
    {"id": "adult_intimate", "label": "Artistic Nude / Intimate Boudoir (Adult)", "adult": True},
    {"id": "erotic_glamour", "label": "Erotic Glamour / Lingerie / Sheer (Adult)", "adult": True},
    {"id": "bikini_beach", "label": "Bikini & Beach / Poolside (Glamour)", "adult": False},
    {"id": "glamour_lifestyle", "label": "Luxury Glamour & Nightlife", "adult": False},
    {"id": "fashion_editorial", "label": "High-Fashion & Editorial Runway", "adult": False},
    {"id": "casual_street", "label": "Casual Streetwear & City Candid", "adult": False},
    {"id": "fitness_athletic", "label": "Fitness & Athletic Body", "adult": False},
]

def get_orchestrator_presets() -> Dict[str, Any]:
    return {
        "categories": CATEGORIES,
        "aspect_ratios": [
            {"id": k, "label": f"{k} ({w}×{h})", "width": w, "height": h}
            for k, (w, h) in ASPECT_RATIOS.items()
        ],
        "quality_levels": [
            {"id": k, "label": v["label"], "scale": v["scale"]}
            for k, v in QUALITY_PRESETS.items()
        ],
        "models": [
            {"id": "cyberrealistic-xl", "label": "CyberRealistic XL v5.0 (Adult & Skin Realism)"},
            {"id": "juggernaut-xl-v10", "label": "Juggernaut XL v10 (Glamour & Outdoor Lighting)"},
            {"id": "pony-diffusion-v6-xl", "label": "Pony Diffusion V6 XL (Uncensored Poses)"},
            {"id": "flux-1-dev-gguf", "label": "FLUX.1-Dev GGUF (Detailed Prompt Adherence)"},
        ]
    }

def route_model_for_request(category_id: str, is_adult: bool = False) -> Dict[str, str]:
    if is_adult or "adult" in category_id or "erotic" in category_id:
        return MODEL_ROUTING.get("adult_intimate")
    return MODEL_ROUTING.get(category_id, MODEL_ROUTING["glamour_lifestyle"])

def compile_persona_master_prompt(dna: Dict[str, Any]) -> Dict[str, Any]:
    name = dna.get("name", "Fictional Model")
    age = dna.get("age", 23)
    country = dna.get("country", "Germany")
    region = dna.get("region", "Bavaria")
    facial = dna.get("facial_identity", "striking hazel eyes, soft jawline, delicate straight nose, natural full lips, dirty blonde wavy hair")
    
    body = dna.get("body_physics", {})
    body_type = body.get("body_type", "curvy athletic hourglass")
    measurements = body.get("measurements", "34D-24-35")
    height = body.get("height", "5'8\"")
    skin_tone = body.get("skin_tone", "fair with golden undertones and subtle freckles")
    breast_shape = body.get("breast_shape", "natural teardrop, realistic gravity")
    
    is_adult = dna.get("content_mode") == "adult" or dna.get("is_adult", False)
    category_id = dna.get("category_id", "erotic_glamour" if is_adult else "glamour_lifestyle")
    routed = route_model_for_request(category_id, is_adult=is_adult)
    
    quality_key = dna.get("quality", "4K")
    quality_suffix = QUALITY_PRESETS.get(quality_key, QUALITY_PRESETS["4K"])["suffix"]
    
    positive_parts = [
        f"RAW photo, ultra-photorealistic studio portrait of a {age}-year-old {region} {country} woman named {name}",
        f"{facial}",
        f"{body_type} physique, {measurements} measurements, {height} height, {skin_tone}, {breast_shape}",
        "authentic human skin micro-texture, visible skin pores, natural imperfections, subtle subsurface scattering",
        "wearing a minimal stylish nude-tone silk bodysuit, neutral minimalist luxury studio background",
        "Hasselblad H6D-100c, 85mm f/1.4 lens, soft directional beauty lighting, shallow depth of field",
        f"{quality_suffix}"
    ]
    positive_prompt = ", ".join(positive_parts)
    
    if is_adult:
        negative_prompt = (
            "deformed, bad anatomy, bad hands, extra fingers, missing fingers, mutated knuckles, "
            "plastic skin, smooth doll skin, 3d render, cartoon, anime, illustration, "
            "oversaturated, blurry, bad eyes, asymmetric eyes, lowres, watermark, text"
        )
    else:
        negative_prompt = (
            "nude, bare, topless, deformed, bad anatomy, bad hands, extra fingers, missing fingers, "
            "plastic skin, doll, 3d render, cartoon, anime, illustration, blurry, lowres, watermark"
        )
        
    return {
        "persona_name": name,
        "positive_prompt": positive_prompt,
        "negative_prompt": negative_prompt,
        "token_estimate": len(positive_prompt.split()),
        "recommended_model": routed["model_id"],
        "routing_reason": routed["reason"],
    }

def synthesize_scene_variations(
    persona_dna: Dict[str, Any],
    narrative: str,
    category_id: str,
    batch_count: int = 3,
    aspect_ratio: str = "2:3",
    quality: str = "4K"
) -> Dict[str, Any]:
    name = persona_dna.get("name", "Model")
    country = persona_dna.get("country", "")
    region = persona_dna.get("region", "")
    age = persona_dna.get("age", 23)
    facial = persona_dna.get("facial_identity", "")
    body = persona_dna.get("body_physics", {})
    body_desc = f"{body.get('body_type', 'curvy athletic')}, {body.get('measurements', '34D-24-35')}, {body.get('skin_tone', 'natural skin')}"
    
    is_adult = "adult" in category_id or "erotic" in category_id or persona_dna.get("content_mode") == "adult"
    routed = route_model_for_request(category_id, is_adult=is_adult)
    quality_suffix = QUALITY_PRESETS.get(quality, QUALITY_PRESETS["4K"])["suffix"]
    
    # Procedural diversity palettes based on narrative and category
    scene_templates = [
        {
            "tag": "Scene 1 · Establishing Mood & Tease",
            "loc": "luxury modern high-rise penthouse, floor-to-ceiling glass windows overlooking morning city skyline, golden dawn light",
            "costume": "sheer translucent white silk robe open at front, delicate lace trim, sensual draped fabric" if is_adult else "chic luxury black silk loungewear, open collar",
            "expression": "leaning playfully against glass, looking over shoulder, mischievous teasing smirk",
            "shot": "waist-up medium portrait, 50mm f/1.4 lens, warm morning rim lighting"
        },
        {
            "tag": "Scene 2 · Intimate & Sensual Detail",
            "loc": "Italian marble bathroom, freestanding soaking tub with soft foam bubbles and steamy ambient light",
            "costume": "artistic bare skin with glistening water droplets on shoulders and collarbone, wet hair clinging softly" if is_adult else "minimalist designer two-piece swimwear, damp skin",
            "expression": "resting arms on tub edge, head tilted, relaxed sultry gaze directly at camera",
            "shot": "medium close-up beauty shot, 85mm f/1.8 lens, soft diffused water reflections"
        },
        {
            "tag": "Scene 3 · Unfiltered Intimacy & Curves",
            "loc": "sun-drenched king-size bed with crumpled champagne silk bedsheets, sheer billowing curtains",
            "costume": "bare midriff and sculpted curves exposed, sheer micro-lace lingerie" if is_adult else "oversized cashmere sweater slipped off one shoulder, bare legs",
            "expression": "propped on elbows, laughing playfully, radiant spontaneous expression",
            "shot": "wide 35mm environmental shot, shallow depth of field, authentic film grain"
        },
        {
            "tag": "Scene 4 · Sunset Terrace & Allure",
            "loc": "private rooftop plunge pool terrace, twilight city horizon with bokeh streetlights",
            "costume": "striking metallic bikini, wet golden skin, subtle tan lines" if is_adult else "designer evening cocktail slip dress",
            "expression": "confident alluring gaze, holding champagne flute, gentle breeze blowing hair",
            "shot": "low angle 70mm portrait, cinematic bokeh background, twilight blue-hour illumination"
        },
        {
            "tag": "Scene 5 · Boudoir Vanity Mirror",
            "loc": "vintage European dressing suite, ornate gilded mirror, warm candlelight and soft shadows",
            "costume": "silk slip dress gently unclasped, delicate curves and back profile" if is_adult else "silk robe with feather trim",
            "expression": "catching eye in mirror reflection with a knowing smile, biting lower lip playfully",
            "shot": "artistic reflection shot, 50mm f/1.2 lens, moody chiaroscuro lighting"
        }
    ]
    
    scenes = []
    actual_count = min(max(1, batch_count), len(scene_templates))
    
    for i in range(actual_count):
        tmpl = scene_templates[i]
        
        pos_parts = [
            f"RAW candid photograph of 23yo {region} {country} woman {name}",
            f"{facial}",
            f"{body_desc}",
            f"narrative context: {narrative}",
            f"setting: {tmpl['loc']}",
            f"wardrobe: {tmpl['costume']}",
            f"expression: {tmpl['expression']}",
            f"camera: {tmpl['shot']}",
            "authentic skin micro-pores, natural goosebumps, subsurface scattering, realistic anatomy",
            f"{quality_suffix}"
        ]
        pos_prompt = ", ".join(pos_parts)
        
        if is_adult:
            neg_prompt = (
                "deformed, bad anatomy, bad hands, extra fingers, missing fingers, mutated knuckles, "
                "plastic smooth skin, porcelain doll, 3d render, cartoon, anime, illustration, "
                "oversaturated, blurry, bad eyes, lowres, watermark, text"
            )
        else:
            neg_prompt = (
                "nude, bare, topless, deformed, bad anatomy, bad hands, extra fingers, missing fingers, "
                "plastic skin, doll, 3d render, cartoon, anime, illustration, blurry, lowres, watermark"
            )
            
        scenes.append({
            "index": i + 1,
            "title": tmpl["tag"],
            "location": tmpl["loc"],
            "costume": tmpl["costume"],
            "expression": tmpl["expression"],
            "shot": tmpl["shot"],
            "prompt": pos_prompt,
            "negative_prompt": neg_prompt,
            "token_count": len(pos_prompt.split()),
        })
        
    width, height = ASPECT_RATIOS.get(aspect_ratio, (768, 1152))
    
    return {
        "persona_name": name,
        "narrative": narrative,
        "category_id": category_id,
        "model_id": routed["model_id"],
        "routing_reason": routed["reason"],
        "aspect_ratio": aspect_ratio,
        "width": width,
        "height": height,
        "quality": quality,
        "scenes": scenes,
    }

def upscale_image_quality(img: Image.Image, quality_key: str) -> Image.Image:
    scale = QUALITY_PRESETS.get(quality_key, {}).get("scale", 1.0)
    if scale <= 1.0:
        return img
    
    new_w = int(img.width * scale)
    new_h = int(img.height * scale)
    
    # High-fidelity Lanczos resampling
    upscaled = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    
    # Subtle unsharp mask to accentuate skin pores and eye highlights without halo artifacts
    sharpened = upscaled.filter(ImageFilter.UnsharpMask(radius=1.2, percent=85, threshold=3))
    return sharpened

def generate_orchestrator_image(
    prompt: str,
    negative_prompt: str,
    model_id: str,
    width: int,
    height: int,
    seed: int,
    quality: str = "1080p",
    steps: int = 30,
    guidance: float = 5.0
) -> Path:
    from .free_cli import make_image
    
    aid = secrets.token_hex(8)
    dest_path = db.OUTPUTS / f"orchestrator_{aid}.png"
    
    args = SimpleNamespace(
        prompt=prompt,
        negative_prompt=negative_prompt,
        model=model_id,
        width=width,
        height=height,
        steps=steps,
        guidance=guidance,
        seed=seed,
        output=str(dest_path),
        reference=None,
        cpu_offload=False,
        offline=True,
    )
    
    # Run diffusion on MPS
    make_image(args)
    
    if not dest_path.is_file():
        raise RuntimeError("Image generation failed to produce output file")
        
    # Apply post-generation quality upscale if 2K, 4K, or 8K requested
    if quality in ("2K", "4K", "8K"):
        raw_img = Image.open(dest_path).convert("RGB")
        upscaled_img = upscale_image_quality(raw_img, quality)
        upscaled_img.save(dest_path, format="PNG", quality=98)
        
    return dest_path
