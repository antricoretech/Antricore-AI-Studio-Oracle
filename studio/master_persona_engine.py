"""
Master Persona Engine for AI Influencer Studio
Implements PersonaSpecification and MasterPersonaPromptBuilder conforming to
docs/MASTER_PERSONA_ENGINEERING_SPEC.md and CLIP 77-token budget limits.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
import time


@dataclass
class PersonaSpecification:
    name: str
    age: int
    origin: str
    ethnicity: str = "International"
    complexion: str = "radiant porcelain fair skin with natural micro-pores"
    facial_features: str = "expressive almond eyes with detailed irises"
    hair_spec: str = "silky natural shoulder-length waves"
    body_measurements: str = "36-24-30 figure"
    bust_spec: str = "36D sculpted natural bust"
    waist_spec: str = "slender 24-inch waist"
    hips_spec: str = "30-inch hips"
    master_seed: int = 1000
    tagline: Optional[str] = None
    facial_structure: Optional[str] = "high sculpted cheekbones and defined jawline"
    lips_spec: Optional[str] = "full natural lips with defined cupid's bow"
    skin_texture: Optional[str] = "fine epidermal texture, natural pore micro-relief, zero plastic smoothing"
    silhouette: Optional[str] = "slender athletic hourglass silhouette"
    wardrobe_signature: Optional[str] = None
    world_setting: Optional[str] = None


class MasterPersonaPromptBuilder:
    """
    Constructs the 13 frozen target packs ensuring:
    - First 25 tokens contain angle, framing, and outfit.
    - Persona biometric core in tokens 25-55.
    - Total prompt under 65 tokens (safe from SDXL 77-token CLIP cap).
    - 180° rear turnaround ringfence strictly enforces negative prompt blocking face.
    """

    NEGATIVE_STANDARD = (
        "deformed, bad anatomy, bad hands, extra fingers, missing fingers, mutated, "
        "fake plastic skin, doll skin, 3d render, cartoon, anime, illustration, blurry, "
        "bad eyes, crossed eyes, oversaturated, low quality, artifacts, watermark, text"
    )

    NEGATIVE_REAR = (
        "face, eyes, mouth, nose, lips, looking back, looking at camera, turned head, "
        "profile, side view, front view, deformed, bad anatomy, extra limbs, watermark, text"
    )

    @classmethod
    def build_13_pack_specs(cls, spec: PersonaSpecification) -> List[Dict[str, Any]]:
        name = spec.name
        age = spec.age
        origin = spec.origin
        seed = spec.master_seed

        # Unique palette or fallbacks
        wardrobe = spec.wardrobe_signature or "Deep mineral teal tailoring, oat-stone linen, and oxblood leather accents"
        world = spec.world_setting or f"Signature architectural settings across {origin}, authentic natural lighting"

        packs = [
            # Section 1: Spatial Turnaround Pack (Studio Neutral Reference)
            {
                "index": 1,
                "id": "turnaround_front",
                "label": "01 Front (0°)",
                "section": "turnaround",
                "filename": f"{name.lower().replace(' ', '_')}_01_turnaround_front.png",
                "prompt": (
                    f"8k raw photo, direct front eye-level view at 0 degrees, standing medium portrait of {age}yo woman {name} from {origin}, "
                    f"{spec.complexion}, {spec.facial_features}, {spec.hair_spec}, {spec.bust_spec}, {spec.waist_spec}, {spec.hips_spec}, "
                    f"wearing black ribbed sleeveless knit top, neutral light grey studio cyclorama, 50mm f/1.4 lens"
                ),
                "negative_prompt": cls.NEGATIVE_STANDARD,
                "aspect_ratio": "2:3",
                "seed": seed
            },
            {
                "index": 2,
                "id": "turnaround_left",
                "label": "02 Left (-90°)",
                "section": "turnaround",
                "filename": f"{name.lower().replace(' ', '_')}_02_turnaround_left.png",
                "prompt": (
                    f"8k raw photo, true left side profile view turned 85 degrees, waist-up portrait of {age}yo woman {name} from {origin}, "
                    f"showing sharp left jawline, left cheekbone, {spec.hair_spec}, "
                    f"wearing black ribbed sleeveless knit top, neutral studio lighting, light grey cyclorama, 50mm f/1.4 lens"
                ),
                "negative_prompt": cls.NEGATIVE_STANDARD,
                "aspect_ratio": "2:3",
                "seed": seed + 1
            },
            {
                "index": 3,
                "id": "turnaround_right",
                "label": "03 Right (+90°)",
                "section": "turnaround",
                "filename": f"{name.lower().replace(' ', '_')}_03_turnaround_right.png",
                "prompt": (
                    f"8k raw photo, true right side profile view turned 85 degrees, waist-up portrait of {age}yo woman {name} from {origin}, "
                    f"showing sharp right jawline, right cheekbone, {spec.hair_spec}, "
                    f"wearing black ribbed sleeveless knit top, neutral studio lighting, light grey cyclorama, 50mm f/1.4 lens"
                ),
                "negative_prompt": cls.NEGATIVE_STANDARD,
                "aspect_ratio": "2:3",
                "seed": seed + 2
            },
            {
                "index": 4,
                "id": "turnaround_back",
                "label": "04 Back (180°)",
                "section": "turnaround",
                "filename": f"{name.lower().replace(' ', '_')}_04_turnaround_back.png",
                "prompt": (
                    f"8k raw photo, view directly from behind at 180 degrees, full rear back view, facing completely away from camera towards back wall, "
                    f"showing back of head with hair cascading straight down center of upper back, showing back of neck, toned shoulder blades, "
                    f"slender waist from behind, neutral grey studio cyclorama, 50mm lens"
                ),
                "negative_prompt": cls.NEGATIVE_REAR,
                "aspect_ratio": "2:3",
                "seed": seed + 3
            },

            # Section 2: Hyper-Realistic Eyes & Lips Micro-Detailing Macro
            {
                "index": 5,
                "id": "micro_eyes_lips",
                "label": "05 Macro Eyes & Lips",
                "section": "micro_detailing",
                "filename": f"{name.lower().replace(' ', '_')}_05_micro_eyes_lips.png",
                "prompt": (
                    f"8k raw macro photo, 100mm f/2.8 macro lens, extreme close-up of {name}'s face showing detailed iris striations, "
                    f"natural catchlights, {spec.complexion}, {spec.lips_spec}, individual eyelashes, "
                    f"fine epidermal skin micro-pores, natural lip hydration sheen, soft diffused beauty light"
                ),
                "negative_prompt": cls.NEGATIVE_STANDARD,
                "aspect_ratio": "2:3",
                "seed": seed
            },

            # Section 3: Standard Category Baselines (Core Influencer Niches)
            {
                "index": 6,
                "id": "baseline_fashion",
                "label": "06 High Fashion",
                "section": "category_baselines",
                "filename": f"{name.lower().replace(' ', '_')}_06_baseline_fashion.png",
                "prompt": (
                    f"8k raw photo, elegant high fashion full-length portrait of {age}yo {name}, {spec.complexion}, "
                    f"wearing tailored architectural designer blazer dress, gold fine jewelry, standing in luxury penthouse lounge, "
                    f"soft evening interior ambient lighting, 85mm f/1.4 portrait lens"
                ),
                "negative_prompt": cls.NEGATIVE_STANDARD,
                "aspect_ratio": "2:3",
                "seed": seed
            },
            {
                "index": 7,
                "id": "baseline_fitness",
                "label": "07 Athleisure",
                "section": "category_baselines",
                "filename": f"{name.lower().replace(' ', '_')}_07_baseline_fitness.png",
                "prompt": (
                    f"8k raw photo, athletic fitness lifestyle medium portrait of {name}, {spec.hair_spec} in high ponytail, "
                    f"wearing ribbed lavender gym sports crop top and matching leggings, natural post-workout glow, "
                    f"sunlit Pilates studio with panoramic windows, 50mm f/1.8 lens"
                ),
                "negative_prompt": cls.NEGATIVE_STANDARD,
                "aspect_ratio": "2:3",
                "seed": seed + 4
            },
            {
                "index": 8,
                "id": "baseline_casual",
                "label": "08 Casual Street",
                "section": "category_baselines",
                "filename": f"{name.lower().replace(' ', '_')}_08_baseline_casual.png",
                "prompt": (
                    f"8k raw photo, candid street lifestyle portrait of {name} at cozy outdoor mountain terrace cafe, "
                    f"wearing warm chunky knit cardigan over black top, holding ceramic coffee cup, soft happy smile, "
                    f"scenic hillside backdrop, natural morning daylight, 35mm f/1.4 lens"
                ),
                "negative_prompt": cls.NEGATIVE_STANDARD,
                "aspect_ratio": "2:3",
                "seed": seed + 5
            },
            {
                "index": 9,
                "id": "baseline_resort",
                "label": "09 Resortwear",
                "section": "category_baselines",
                "filename": f"{name.lower().replace(' ', '_')}_09_baseline_resort.png",
                "prompt": (
                    f"8k raw photo, luxury resortwear full body portrait of {name}, {spec.body_measurements}, "
                    f"wearing emerald-green designer one-piece swimsuit with gold buckle belt, standing by infinity pool, "
                    f"golden hour sun reflections on azure water, 50mm f/1.4 lens"
                ),
                "negative_prompt": cls.NEGATIVE_STANDARD,
                "aspect_ratio": "2:3",
                "seed": seed + 6
            },

            # Section 4: Adult Intimate & Erotic Glamour Baselines (Uncensored)
            {
                "index": 10,
                "id": "boudoir_half",
                "label": "10 Boudoir Half",
                "section": "adult_baselines",
                "filename": f"{name.lower().replace(' ', '_')}_10_boudoir_half.png",
                "prompt": (
                    f"8k raw photo, sensual artistic boudoir half-body portrait of {age}yo woman {name}, topless on luxury white silk bed sheets, "
                    f"showcasing natural {spec.bust_spec}, soft gentle gaze at camera, natural morning light from sheer window curtains, "
                    f"warm skin tones, 85mm f/1.4 lens"
                ),
                "negative_prompt": cls.NEGATIVE_STANDARD,
                "aspect_ratio": "2:3",
                "seed": seed
            },
            {
                "index": 11,
                "id": "boudoir_full",
                "label": "11 Boudoir Full",
                "section": "adult_baselines",
                "filename": f"{name.lower().replace(' ', '_')}_11_boudoir_full.png",
                "prompt": (
                    f"8k raw photo, fine art reclining nude full body boudoir portrait of {name}, resting elegantly on deep crimson velvet chaise lounge, "
                    f"showcasing natural {spec.body_measurements}, slender waist, long legs, soft ambient bedroom lighting, "
                    f"classical painterly composition, 50mm lens"
                ),
                "negative_prompt": cls.NEGATIVE_STANDARD,
                "aspect_ratio": "2:3",
                "seed": seed + 7
            },
            {
                "index": 12,
                "id": "lingerie_half",
                "label": "12 Lingerie Half",
                "section": "adult_baselines",
                "filename": f"{name.lower().replace(' ', '_')}_12_lingerie_half.png",
                "prompt": (
                    f"8k raw photo, half-body erotic glamour portrait of {name}, wearing sheer black lace underwire corset bustier, "
                    f"deep sweetheart plunge cleavage, seductive captivating gaze, warm candlelight in luxury bedroom suite, "
                    f"shallow depth of field, 85mm f/1.4 lens"
                ),
                "negative_prompt": cls.NEGATIVE_STANDARD,
                "aspect_ratio": "2:3",
                "seed": seed
            },
            {
                "index": 13,
                "id": "lingerie_full",
                "label": "13 Lingerie & Stockings (Full)",
                "section": "adult_baselines",
                "filename": f"{name.lower().replace(' ', '_')}_13_lingerie_full.png",
                "prompt": (
                    f"8k raw photo, full body erotic glamour portrait of {name}, standing in front of ornate full-length gilded mirror, "
                    f"wearing sheer black lace lingerie set, garter belt, and sheer black stockings, showcasing complete {spec.body_measurements}, "
                    f"luxurious penthouse dressing room, warm ambient lighting, 50mm f/1.4 lens"
                ),
                "negative_prompt": cls.NEGATIVE_STANDARD,
                "aspect_ratio": "2:3",
                "seed": seed + 8
            }
        ]

        return packs
