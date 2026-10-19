# Master Persona Engineering Specification & Ringfences (FROZEN)

This specification defines the frozen standards and execution logic for Master Persona creation within the AI Influencer Studio platform.

---

## 1. The 13-Image Master Persona Vault Architecture

Every Master Persona MUST generate the complete 13-image reference set across 4 distinct functional sections:

### Section 1: 4-Angle Spatial Turnaround Pack (Studio Neutral Reference)
*Shot in uniform studio lighting with a neutral grey cyclorama backdrop and a minimalist black ribbed sleeveless top:*
1. **Front Profile (0° Direct)**: Eye-level symmetrical reference, direct gaze, establishing baseline facial bone structure, eye spacing, nose bridge, lip contour, and bust/waist proportions.
2. **Left Side Profile (-90° True Profile)**: True 90-degree left side view showing jawline, ear placement, nasal bridge slope, and profile silhouette.
3. **Right Side Profile (+90° True Profile)**: True 90-degree right side view verifying facial symmetry, opposite ear, and hair volume.
4. **True Back Profile (180° Direct Rear View)**: 100% direct rear view shot directly from behind with **zero face visible**, capturing the back of the head, hairstyle silhouette, back of neck, shoulder blades, and waistline.

### Section 2: Hyper-Realistic Eyes & Lips Micro-Detailing Macro
5. **Macro Beauty Portrait (100mm f/2.8)**: Extreme close-up capturing:
   - Iris radial striations and natural catchlights.
   - Individual dark eyelashes and defined eyebrow hairs.
   - Natural lip micro-creases, defined cupid's bow, and hydration sheen.
   - Authentic epidermal micro-pores and subtle freckles/skin texture (zero plastic smoothing).

### Section 3: Standard Category Baselines (Core Influencer Niches)
6. **High Fashion & Glamour**: Tailored architectural blazer dress/cocktail gown in a luxury penthouse setting.
7. **Fitness & Athleisure**: High ponytail, ribbed sports top and leggings in an aesthetic Pilates/yoga studio.
8. **Casual Streetwear Lifestyle**: Candid outdoor European cafe/street setting with coffee cup and layered knitwear/trench coat.
9. **Resort & Beachwear (No Nudity)**: Designer one-piece swimsuit beside a luxury infinity pool with sunglasses.

### Section 4: Adult Intimate & Erotic Glamour Baselines (Uncensored)
10. **Artistic Boudoir Nude (Half-Body)**: Topless on luxury white silk bed sheets in soft morning light, showcasing natural breast curvature and facial sensuality.
11. **Artistic Boudoir Nude (Full-Body)**: Fine art reclining nude on velvet chaise lounge, capturing complete anatomical proportions (e.g., 36-24-30 figure).
12. **Erotic Glamour Corset (Half-Body)**: Sheer black lace corset bustier with deep plunge cleavage in candlelit bedroom.
13. **Erotic Glamour Lingerie (Full-Body)**: Standing in front of a luxury full-length mirror wearing sheer lace lingerie, garter belt, and stockings.

---

## 2. Prompt Engineering & CLIP 77-Token Ringfences

SDXL CLIP text encoders have a hard limit of 77 tokens. To prevent truncation of styling, outfits, or background elements:

* **Token Rule 1 (Positioning & Framing First)**: The shot framing (e.g. `direct front view at 0 degrees, standing medium portrait`), angle, and outfit MUST be placed in the **first 20 tokens**.
* **Token Rule 2 (Persona Core DNA Second)**: Ethnicity, age, facial features, and body proportions follow in tokens **21 to 50**.
* **Token Rule 3 (Budget Cap)**: Total prompt length MUST stay **under 65 tokens**.

### Frozen Prompt Structure:
```text
[8k raw photo] + [Camera Angle & Shot Type] + [Age & Persona Heritage] + [Facial & Hair DNA] + [Body Proportions & Outfit] + [Setting & Lighting] + [Lens Specification]
```

---

## 3. Strict 180° Rear Turnaround Ringfence

Diffusion models exhibit a heavy bias toward turning female subjects to face the camera. To enforce a **100% direct back view**:
* **Positive Prompt Requirement**: Must include `"view directly from behind at 180 degrees, full rear back view, facing completely away from camera towards back wall, showing back of head with hair cascading straight down center of upper back, showing back of neck, toned shoulder blades, waist from behind"`.
* **Negative Prompt Enforcement**: MUST explicitly ban all facial elements:
  ```text
  face, eyes, mouth, nose, lips, looking back, looking at camera, turned head, profile, side view, front view
  ```

---

## 4. Facial Identity Anchoring Strategy

To guarantee facial identity consistency across diverse categories without drift:
1. **Anchor Seed Formula**:
   - Establish a `MASTER_SEED` for the front profile (`01`), macro (`05`), fashion (`06`), boudoir half (`10`), and lingerie half (`12`).
   - Use deterministic offsets `MASTER_SEED + k` for turnarounds and full-body shots.
2. **Locked Biometric Tokens**: The exact descriptors for ethnicity, eye color/shape, nose structure, and lip geometry must be repeated verbatim across every prompt.
3. **Master Reference Vault**: The Front (`01`), Profiles (`02`, `03`), and Macro (`05`) serve as image conditioning inputs (via IP-Adapter / FaceID) for subsequent downstream image generation.

---

## 5. Method B Dynamic Editorial Typography Rules

When overlaying text or graphics for social media / story studio:
1. **Zero Text from Diffusion**: Diffusion models must always render clean, pristine 4K images with `"text, watermark, logo"` in the negative prompt.
2. **Dynamic Non-Repetitive Layouts**: Every slide/post must adopt a distinct archetype (*Vogue Masthead*, *Cinematic Viewfinder*, *Couture Postcard*, *Interactive Poll*).
3. **Curated Luxury Typography**:
   - Headers: *Italiana* or *Playfair Display Bold* (editorial Vogue serif).
   - Badges & Tags: *Cinzel Bold* (Roman luxury serif).
   - Accents / Signatures: *Great Vibes* (personal cursive calligraphy).
   - Subtitles / Body: *Montserrat SemiBold* (modern aesthetic sans).
4. **Vector-Drawn Symbols Only**: Never use unicode emojis (which produce `□` missing glyph errors). All stars, pins, recording dots, hearts, and arrows must be rendered as clean vector math.

---

## 6. Mandatory Outfit & Location Diversity Ringfence (Zero Template Recycling)

To ensure that each Master Persona feels like an authentic, independent individual with their own distinct world:

1. **Zero Outfit Recycling Across Personas**:
   - The wardrobe styling across all category baselines (Fashion, Fitness, Casual, Resort, Boudoir, Lingerie) **MUST NEVER be duplicated** between different personas.
   - If Persona A wears an ivory blazer dress, lavender gym bra, and emerald one-piece swimsuit, Persona B must feature completely different cuts, fabrics, silhouetting, and color palettes (e.g. backless midnight velvet gown, terracotta ribbed athleisure, metallic gold draped resort wear, etc.).
   - Wardrobes must organically reflect the persona's regional heritage, body proportions, personal aesthetic, and seasonal context.

2. **Zero Location & Environment Recycling Across Personas**:
   - Background environments, architectural spaces, and geographic settings **MUST be completely unique** for each persona.
   - If Persona A is set in Gangtok/Himalayan mountain terraces, Persona B must be placed in distinct world environments (e.g. Amalfi coast cliffside promenade, Parisian Haussmann apartment balcony, Tokyo minimalist glass loft, Tulum jungle resort, Scandinavian brutalist villa, etc.).
   - Ambient lighting temperatures, horizons, and interior design palettes must never be recycled.

3. **Adult & Intimate Setting Uniqueness**:
   - Intimate Boudoir and Lingerie baselines must vary their staging: silk canopy beds, vintage velvet chaises, candlelit marble hearths, Moroccan riad courtyards, minimalist Japanese soaking tubs, or luxury penthouse mirrors.
   - Lingerie cuts must rotate: corsetry, sheer silk chemises, lace underwire sets, vintage satin robes, structural harnesses, and bespoke embroidery.

