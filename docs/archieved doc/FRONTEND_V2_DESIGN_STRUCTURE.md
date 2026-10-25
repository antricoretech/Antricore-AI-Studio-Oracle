# AI Influencer Studio V2: Frontend Architecture & Design Specification

> **Definitive Architectural Blueprint**: This document details the complete structure, UI design system, tab-by-tab components, and user workflows for **Frontend V2** of the AI Influencer Studio.

---

## 1. Executive Design System: "Obsidian Luxury & Champagne Gold"

The V2 UI is engineered with an ultra-premium aesthetic tailored to luxury digital influencer management:

* **Color Palette**:
  * **Deep Obsidian Canvas**: `#0B0F17` (App Background), `#0E1420` (Surface Cards).
  * **Frosted Glassmorphism**: `rgba(15, 23, 42, 0.75)` with `backdrop-filter: blur(16px)` and subtle hairline borders `rgba(212, 175, 55, 0.18)`.
  * **Metallic Accent**: Champagne Gold (`#D4AF37` / `#FEF08A`) for active states, badges, and primary buttons.
  * **Status & Mode Glows**:
    * 🟣 Royal Purple (`#A855F7`): Personal Lifestyle & Organic Blogging Mode.
    * 🟡 Champagne Gold (`#EAB308`): Commercial Niche & Brand Campaign Mode.
    * 🟢 Emerald Green (`#10B981`): Hardware Ready / Inference Idle.
    * 🔴 Crimson (`#EF4444`): Active Inference / Live Recording Indicator.
* **Typography System**:
  * **Primary Display & Titles**: *Cinzel* (Roman luxury serif) + *Italiana* (haute couture).
  * **Editorial Story Hooks**: *Playfair Display Bold* (editorial Vogue serif) + *Great Vibes* (handwritten signature calligraphy).
  * **UI Controls & Data Tables**: *Montserrat* / *Inter* (modern high-legibility sans-serif).
* **Iconography & Graphics**:
  * 100% native SVG and vector-drawn elements. Zero reliance on unicode emoji glyphs to prevent broken rendering (`□`).

---

## 2. Global Navigation & Header Shell

The top bar persists globally across all 5 functional tabs:

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────────┐
│  👑 AI INFLUENCER STUDIO V2   │  Active Persona: [ Maya Bhutia (Sikkim) ▼ ]  │  MPS GPU: 68% VRAM   │
├──────────────┬──────────────────┬─────────────────┬─────────────────────┬────────────────────────────┤
│ 1. GENERATE  │ 2. MASTER VAULT  │ 3. STORY STUDIO │  4. MEDIA GALLERY   │   5. SYSTEM & MONITORING   │
└──────────────┴──────────────────┴─────────────────┴─────────────────────┴────────────────────────────┘
```

* **Left**: App Logo, Version Badge (`V2.0 PRO`), and Workspace Status.
* **Center**: **Global Active Persona Switcher** (Dropdown to switch between *Maya Bhutia*, *Elena Weber*, *Riya Sen*, or trigger *+ Create New Master Persona*).
* **Right**: Real-time Hardware Telemetry Pill (MPS / CUDA VRAM usage, inference status, active task indicator).
* **Primary Navigation Tabs**:
  1. `1. MASTER VAULT` (Persona DNA Creation & 13-Image Identity Vault)
  2. `2. GENERATE` (Text-to-Image, Img2Img & Photoshoot Orchestrator)
  3. `3. STORY STUDIO` (Single/Carousel Creator, Persona Feed & Content Calendar)
  4. `4. MEDIA GALLERY` (Persona-Centric Asset Explorer & Metadata Inspector)
  5. `5. SYSTEM & MONITORING` (Hardware Telemetry, Model Health & Queue Manager)

---

## 3. Tab-by-Tab Functional Breakdown

### TAB 1: MASTER PERSONA CREATION & IDENTITY VAULT
* **Core Purpose**: Establish permanent, biometric identity anchors for any persona narrative.
* **Layout Structure**: 2 Sub-Views toggled via inner navigation pill:
  * `[ ◈ Master Vault Inspector (Nordic Glass) ]` · `[ ✦ Generate Master Persona (DNA Synthesizer) ]`
* **Key Components**:
  1. **Narrative-to-DNA Synthesizer**:
     * Input simple narrative (*e.g., "24yo from Sikkim, fair, 36-24-30 figure"*) or ingest complex JSON specifications (*e.g. `Veyra nolin.json`*) $\rightarrow$ generates full physical spec:
       * Facial landmarks, epicanthic fold, iris pigment, lips cupid's bow, skin pore texture.
       * 36-24-30 anatomical figure metrics (natural 36D bust projection, 24" waist, 30" hips).
  2. **The 13-Image Master Vault Generator**:
     * One-click generation of the frozen 13-image vault:
       * **Pack 1 (4-Angle Turnaround)**: Front ($0^\circ$), Left ($-90^\circ$), Right ($+90^\circ$), True Back ($180^\circ$ direct rear with zero face).
       * **Pack 2 (Micro-Detailing)**: 100mm f/2.8 macro of eyes, lips, and natural skin pores.
       * **Pack 3 (Standard Baselines)**: High Fashion, Fitness/Athleisure, Casual Streetwear, Resort Swimwear.
       * **Pack 4 (Adult Intimate Baselines)**: Boudoir Nude Half-Body, Boudoir Nude Full-Body, Lingerie Corset Half-Body, Lingerie & Stockings Full-Body.
  3. **Mandatory Outfit & Location Diversity Enforcement**:
     * Automatically ensures wardrobe styling and geographic backdrops are 100% unique across all personas (zero template recycling).
  4. **Master Vault Inspector**:
     * 3D carousel and grid view of the 13 reference images with lock status and seed provenance.

---

### TAB 2: GENERATE & PHOTOSHOOT ORCHESTRATOR
* **Core Purpose**: Rapid generation for both text-to-image and image-to-image with zero prompt restrictions (100% uncensored).
* **Layout Structure**: Dual-pane layout (38% Controls on Left / 62% Live 4K Canvas on Right).
* **Key Components**:
  1. **Dual Generation Modes**:
     * *Text-to-Image*: Unrestricted prompt box with syntax highlighting.
     * *Image-to-Image*: Drag-and-drop reference image canvas with Denoising Strength slider ($0.10$–$0.95$).
  2. **Model Selection**:
     * Auto-Recommendation badge (suggests best-fit model based on prompt: e.g. Juggernaut XL v10 for photorealism/intimacy).
     * Manual model override dropdown (SDXL, Juggernaut, Flux, SVD).
  3. **Photoshoot Scene Orchestrator**:
     * **Framing & Angle**: Extreme Close-up, Waist-up, Full-body, Low-angle, Overhead.
     * **Lens & DOF**: 35mm street, 50mm natural eye, 85mm portrait, 100mm f/2.8 macro.
     * **Lighting Environment**: Golden hour sunset, 3-point studio, Candlelight intimate, Cyberpunk neon, Diffuse cloudy mountain.
  4. **One-Click Scene Generator**:
     * Narrative input $\rightarrow$ AI suggests the **Top 3 Diverse Scene Variations** with one-click adoption.
  5. **Aspect Ratio Presets**: 9:16 (Stories/Reels), 4:5 (Feed Portrait), 1:1 (Square), 16:9 (Landscape).
  6. **Interactive Canvas**: High-res preview, zoom/pan controls, and side-by-side comparison slider.

---

### TAB 3: STORY & DIGITAL BLOG STUDIO (VIRAL CONTENT ENGINE)
* **Core Purpose**: End-to-end viral content generation, scheduling, and management for influencers.
* **Layout Structure**: 3 Sub-Views toggled via inner navigation pill:
  * `[ Studio Creator ]` · `[ Persona Feed & Archive ]` · `[ Posting Calendar ]`

#### Sub-View 1: Studio Creator Workspace
1. **Format Selector**:
   * **Single Image Post** (High-impact standalone hook/quote/photo).
   * **Multi-Slide Carousel** (2 to 10 slides for story blogging and swipe engagement).
2. **Intent & Mode Selector (The Critical Split)**:
   * **🌟 Mode A: Personal Lifestyle & Organic Blog**:
     * *Sub-Themes*: Day in My Life, POV Romance / Date, Travel Diary, Late-Night Thoughts / Confessions, GRWM, Life Q&A.
     * *Inputs*: Mood / Daily Narrative.
   * **💼 Mode B: Commercial Niche & Brand Campaign**:
     * *Market Niches*: Fashion, Cosmetics/Skincare, Food & Dining, Wellness/Medicine, Tech/IT, E-Commerce, Adult Boudoir/Glamour.
     * *Inputs*: Brand Name, Product Tag, Promo Code (`MAYA20`), Campaign Objective (Launch, Review, Promo, Unboxing).
3. **AI Viral Pre-Generation Suite**:
   * **Top 3 High-Converting Hooks**: Category-tailored hooks generated dynamically.
   * **Micro-Blog Story Captions**: Conversational story copy matching persona tone and commercial goals.
   * **Tiered Hashtag Mix**: Viral mega-tags, niche community tags, and persona tags.
   * **Visual Scene & Prop Recommendations**: Optimal lighting and props tailored to the chosen mode/niche.
4. **Method B Editorial Overlay Engine**:
   * Clean diffusion render (zero text distortion) + sub-second (<0.2s) graphic overlay.
   * **Dynamic Multi-Style Selector**: Vogue Masthead, Cinematic Viewfinder (`REC` dot + Subtitle), Couture Postcard, Interactive Poll pill (`89% vs 11%`).
   * Pure vector icons (zero broken glyphs).
5. **Publish & Schedule Action**: One-click export or schedule directly to the Content Calendar.

#### Sub-View 2: Persona Feed & Content Archive
* **Persona Filter**: Displays all generated single posts and carousels for the active persona.
* **Format & Mode Filters**: Filter by `Single`, `Carousel`, `Personal Blog (🟣)`, `Commercial Campaign (🟡)`, `Draft`, `Scheduled`.
* **Content Cards**: Interactive cards showing thumbnail, slide count, hook title, niche badge, and quick actions (*Edit Overlay, Download, Reschedule*).

#### Sub-View 3: Persona Posting Calendar
* **Visual Monthly & Weekly Grid Planner**:
  * Chronological view of scheduled and published posts for the active persona.
  * **Color-Coded Badges**: 🟣 Purple for Personal Lifestyle vs. 🟡 Gold for Commercial Campaign.
  * **70/30 Content Balance Tracker**: Live health gauge showing the ratio of organic lifestyle to sponsored posts to prevent audience burnout and maximize engagement.
  * Drag-and-drop date rescheduling with peak engagement time slot recommendations (18:00–21:00).

---

### TAB 4: MEDIA GALLERY & ASSET HUB
* **Core Purpose**: Comprehensive asset management, metadata inspection, and export hub.
* **Key Components**:
  1. **Multi-Faceted Filter Sidebar**:
     * Filter by Persona, Category, Series, Format (Single/Carousel), Aspect Ratio (9:16, 4:5, 1:1), and NSFW status.
  2. **High-Res Media Grid**: Infinite scroll with masonry card layouts and quick action overlays.
  3. **Deep Metadata Inspector Modal**:
     * High-res image viewer with interactive Clean vs Editorial overlay comparison slider.
     * Full generation parameters: Prompt, Negative Prompt, Seed, Model, Sampler, CFG, Inference Steps, Aspect Ratio, Generation Date.
     * Quick Actions: *One-Click Download (PNG/WebP)*, *Send to Img2Img*, *Use as Facial Anchor*, *Send to Story Studio*.

---

### TAB 5: SYSTEM MONITORING & HARDWARE TELEMETRY
* **Core Purpose**: Real-time performance monitoring, model health, and task orchestration.
* **Key Components**:
  1. **Hardware Telemetry Gauges**:
     * Live Apple Silicon MPS / CUDA GPU VRAM load and temperature.
     * System RAM and CPU core utilization graphs.
  2. **Integrated Models Status Registry**:
     * Health check indicators and loaded status for Juggernaut XL, SDXL, Flux, FaceID, and SVD.
     * VRAM cache purge button.
  3. **Active Task Queue & Inspector**:
     * Step-by-step progress bar with live step counter ($14/28$ steps), elapsed time, and ETA.
     * Real-time console log stream.
     * One-click task cancellation control.

---

## 4. Technology & Implementation Stack

* **Frontend Architecture**: Single Page Application (SPA) with modern modular JavaScript (ES Modules) and pure Vanilla CSS.
  * No heavy frontend dependencies. Maximum control over glassmorphism and performance.
  * Sub-second transitions and dynamic DOM rendering.
* **Backend Integration**: FastAPI / Python backend connected directly to:
  * `studio/master_persona_engine.py` (Master Persona 13-Image Vault Generator).
  * `scripts/render_dynamic_overlays.py` (Method B Dynamic Typography Engine).
  * Stable Diffusion XL / Juggernaut XL pipeline running locally on Apple Silicon MPS.
  * SQLite / JSON metadata storage for personas, calendar events, and gallery assets.
