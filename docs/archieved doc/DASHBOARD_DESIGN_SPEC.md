# AI Influencer Studio — Master Dashboard Design Specification

> **Reference Document**: Complete architecture, section taxonomy, metrics, and UI blueprint for the AI Influencer Studio Command Center.

---

## 1. Core Philosophy & Design Goals

The AI Influencer Studio Dashboard is designed to unite two core disciplines into a single high-efficiency cockpit:
1. **MLOps & Hardware Infrastructure**: Real-time tracking of GPU VRAM, local model weights, ComfyUI/Diffusers inference queues, and disk capacity.
2. **Virtual Talent & Content Operations**: Biometric facial consistency tracking, turnaround anchor management, multi-modal production (photos, video reels, Kokoro voiceover), episodic series planning, and legal AI disclosure compliance.

---

## 2. Information Architecture & Priority Hierarchy

| Priority Level | Section | Core Purpose & Metric Focus |
|---|---|---|
| **Tier 1 (Instant Glance)** | Top Bar & Hardware Telemetry | VRAM, GPU temp, compute backend ping, active persona anchor, disk room |
| **Tier 1 (Execution)** | Live Generation Queue & Engine | Step-by-step render progress, step latents, cancel/pause controls |
| **Tier 2 (Decision Making)** | Media Review & Approval Gate | Side-by-side comparison with 0° master anchor, 1-click Approve/Discard |
| **Tier 2 (Identity Integrity)** | Persona Biometric Matrix | 13-pack turnaround completion, FaceID embedding lock, likeness score |
| **Tier 3 (Production)** | Multi-Modal Pipeline Tracker | Photoshoot diversity, Wan2.2 video clips, Kokoro speech, muxed reels |
| **Tier 3 (Planning)** | Campaign & Content Calendar | Episode pipeline Kanban, brand sponsorship codes, story arcs |
| **Tier 4 (Operations)** | System Weights & Compliance | Local model inventory, C2PA sidecar status, synthetic media logs |

---

## 3. Deep Dive: The 8 Core Dashboard Sections

### Section 1: Executive Top Bar & Live Telemetry Ticker (Persistent)
*Always visible at the top of the viewport.*

* **Hardware Metrics**:
  * Active Acceleration Engine: `NVIDIA CUDA (RTX 4090)` or `Apple MPS`
  * Live VRAM Meter: Used / Total (e.g. `14.2 GB / 24.0 GB · 59%`)
  * GPU Temperature & Fan Speed / Power Draw (e.g. `62°C · 280W`)
* **Service Health**:
  * ComfyUI Backend Ping (`Online · 127.0.0.1:8188` / `Offline`)
  * Diffusers Local Engine Status (`Ready`)
  * Kokoro Speech Engine (`Loaded`)
* **Active Persona Anchor Pill**:
  * Circular avatar thumbnail
  * Persona Name (`Maya Bhutia`)
  * Quick-switch dropdown to swap active influencer context across all tabs
* **Storage Alert Gauge**:
  * Remaining drive capacity for `.safetensors` and media output (`e.g. 248 GB free on D:\`)

---

### Section 2: Persona Identity & Biometric Anchor Matrix
*Ensures absolute facial and anatomical consistency across all generative outputs.*

* **Key Data Points & Visuals**:
  * **Canonical 4-Angle Turnaround Grid**:
    * 0° Direct Eye-Level Front Portrait (Canonical biometric master)
    * -90° Left Side Profile
    * +90° Right Side Profile
    * 180° Rear Silhouette & Hair Cascade
  * **Biometric Lock Indicator**:
    * InsightFace `buffalo_l` 512-dimensional normalized embedding status (`LOCKED`)
    * IP-Adapter FaceID PlusV2 cross-attention weight status
  * **Demographic & Anatomical DNA Spec**:
    * Age, Ethnicity, Region (`23 · Germany · Bavaria`)
    * Body Physics (`curvy athletic hourglass · 34D-24-35 · 5'8"`)
    * Epidermal & Micro-Texture Spec (`fair golden · natural teardrop gravity · subtle freckles`)
  * **Turnaround Pack Completion Score**:
    * Progress tracker for all 13 Frozen Vault Reference Packs (01 Front, 02 Left, 03 Right, 04 Back, 05 Macro Lips/Eyes, 06 High Fashion, 07 Athleisure, 08 Street, 09 Resort, 10-13 Boudoir/Lingerie baselines).
* **Actionable Controls**:
  * `+ New Persona DNA` modal launcher
  * `Lock Output as Anchor` quick-action button
  * `Export Identity Vault (.zip)`

---

### Section 3: Live Generation Queue & Engine Room
*Tracks what the neural pipeline is rendering right now.*

* **Key Data Points & Visuals**:
  * **Active Render Card**:
    * Model Checkpoint: `CyberRealistic XL Play v10.0` or `Juggernaut XL v10` or `Wan2.2 TI2V-5B`
    * Step Counter & Progress Bar: e.g. `Step 22/30 (73%) · DPM-Solver++ 2M Karras`
    * Dynamic Latent Preview: Real-time step-by-step canvas rendering
    * Parameters Badge: Denoising `0.65`, CFG `5.0`, Seed `847291039`, Resolution `768×1152 (2:3)`
  * **Pending Queue Stream**:
    * List of waiting tasks with estimated time to completion (ETC)
    * Job Type Badges: `[PHOTO]`, `[VIDEO 720p]`, `[VOICE TTS]`
  * **Error & OOM Warning Center**:
    * Clear diagnostic tips if CUDA out-of-memory or model load failures happen
* **Actionable Controls**:
  * `Pause / Resume Queue`
  * `Cancel Current Job`
  * `Reorder / Prioritize Jobs`

---

### Section 4: Studio Output Feed & Curation Approval Gate
*A fast review deck to approve, iterate, or discard newly generated media.*

* **Key Data Points & Visuals**:
  * **Recent Generations Stream**:
    * High-res media cards for newly arrived outputs
    * Metadata inspector: full prompt, negative prompt, seed, engine, timestamp
  * **Side-by-Side Reference Comparison**:
    * Split-screen view placing the newly generated image next to the 0° canonical front anchor to verify likeness, bone structure, and eye color
  * **Curation Status Indicators**:
    * `Pending Review` (Yellow)
    * `Approved Master` (Green)
    * `Rejected Artifacts` (Red)
* **Actionable Controls**:
  * `Approve & Publish to Gallery` (Keyboard shortcut: `A`)
  * `Discard / Delete` (Keyboard shortcut: `D`)
  * `Re-roll with Same Seed & Prompt Variation`
  * `2x / 4x High-Resolution Upscale`

---

### Section 5: Multi-Modal Pipeline Tracker (Photo · Video · Voice)
*Manages the synthesis stages required for full social media reels and stories.*

* **Sub-Modules**:
  1. **Photo Studio**:
     * Prompt builder status (Location, Costume, Lighting, Angle, Expression)
     * Batch generation synthesis tracker
  2. **Video Engine (Wan2.2 TI2V-5B & SVD-XT)**:
     * Motion strength, frame count (25-81 frames), 720p/480p rendering status
  3. **Voice Studio (Kokoro TTS)**:
     * Voice persona mapping (`af_heart`, `am_adam`), audio length, transcript preview
  4. **FFmpeg Muxer**:
     * Final compositing station combining Video + Audio + Subtitles + Disclosure watermarks into publication-ready `.mp4` files
* **Actionable Controls**:
  * `Play Combined Reel Preview`
  * `Regenerate Audio Narration Only`

---

### Section 6: Campaign & Content Calendar Board
*Organizes storytelling arcs, episodes, and commercial deliverables.*

* **Key Data Points & Visuals**:
  * **Episodic Series Kanban**:
    * Columns: `1. Brief / Concept` → `2. Rendering Queue` → `3. Review & Approval` → `4. Ready to Post`
  * **Brand Sponsorship & Commerce Tracker**:
    * Sponsor Brand Name (e.g. *Radiance Botanicals*)
    * Campaign Tagging & Promo Code (e.g. `MAYA20` for 20% discount)
    * Product placement requirements
  * **Episode Counter**: e.g. "Milan Fashion Week: Episode 2 of 4 ready"
* **Actionable Controls**:
  * `Queue Entire Series Batch`
  * `Copy Caption & Disclosure to Clipboard`

---

### Section 7: System Infrastructure & Model Weights Inventory
*Monitors the local machine's storage and downloaded AI checkpoints.*

* **Key Data Points & Visuals**:
  * **Installed Weights Matrix**:
    * Primary SDXL Models: Juggernaut XL v10, CyberRealistic XL (`Ready · 6.6 GB`)
    * Adapter Weights: IP-Adapter FaceID PlusV2 (`Ready`)
    * Video Checkpoints: Wan2.2 TI2V-5B (`Ready · 14.0 GB`)
    * Speech Engine: Kokoro v0.19 (`Ready · 300 MB`)
  * **Disk Consumption Breakdown**:
    * `models/` directory footprint
    * `generated/` media folder size
    * Temporary latent and cache files
* **Actionable Controls**:
  * `1-Click Model Download (free_cli download)`
  * `Purge Temporary Latents & Cache`
  * `Run System Doctor Diagnostic`

---

### Section 8: Provenance, Legal Compliance & AI Disclosure
*Guarantees zero copyright infringement and 100% regulatory compliance.*

* **Key Data Points & Visuals**:
  * **Synthetic Media Disclosure**:
    * Mandatory tag status: `Fictional AI-generated adult persona` (Verified 100%)
  * **C2PA / Provenance Manifest**:
    * Verification that `.json` sidecar manifest and SHA-256 cryptographic hashes exist for every generated asset
  * **Likeness Ringfence Protection**:
    * Biometric uniqueness verification ensuring no collision with real-world celebrity identities
* **Actionable Controls**:
  * `Export Disclosure Package`
  * `Audit Provenance Manifest`

---

## 4. UI Wireframe Layout Blueprint

```
+----------------------------------------------------------------------------------------------------+
| [LOGO] AI INFLUENCER STUDIO | ACTIVE: [Maya Bhutia v] | VRAM: 14.2GB/24GB | COMFY: ONLINE | DISK: 248GB   |
+----------------------------------------------------------------------------------------------------+
| [ 1. OVERVIEW / COCKPIT ] [ 2. MASTER VAULT ] [ 3. GENERATE ] [ 4. STORY ] [ 5. GALLERY ] [ 6. SYSTEM ]|
+----------------------------------------------------------------------------------------------------+
| LEFT COLUMN (35%): BIOMETRICS & PROVENANCE     | RIGHT COLUMN (65%): ACTIVE OPERATIONS & QUEUE     |
|                                                |                                                   |
| +-- BIOMETRIC ANCHOR MATRIX -----------------+ | +-- LIVE RENDER STATUS & LATENT PREVIEW ---------+ |
| | [ 0° Front ] [ -90° Left ] [ +90° Right ]  | | | [ Model: CyberRealistic XL | Step 22/30 (73%) ] | |
| | [ 180° Back ] [ Macro ]    [ High Fashion ]| | | [ === LATENT REAL-TIME DECODE CANVAS === ]     | |
| |                                            | | | Resolution: 768x1152 | Seed: 847291039          | |
| | Identity: InsightFace Buffalo_L Locked     | | | [ Pause ] [ Cancel ] [ High-Res Fix ]          | |
| | Likeness Confidence: 98.4%                 | | +-----------------------------------------------+ |
| +--------------------------------------------+ |                                                   |
|                                                | +-- ACTIVE QUEUE & PIPELINE STREAM --------------+ |
| +-- CAMPAIGN & SERIES KANBAN ----------------+ | | 1. [PHOTO] Luxury Café Lifestyle · Running      | |
| | Series: "Autumn in Bavaria" (Ep 3/5)       | | | 2. [VIDEO] Slow Walk Turn (Wan2.2) · Queued     | |
| | Brand: Radiance Botanicals (Code: MAYA20)  | | | 3. [VOICE] 15s Story Narration · Queued         | |
| +--------------------------------------------+ | +-----------------------------------------------+ |
|                                                |                                                   |
| +-- COMPLIANCE & WATERMARK ------------------+ | +-- APPROVAL GATE (RECENT OUTPUTS) --------------+ |
| | [✓] 100% Synthetic AI Disclosure Sidecar   | | | [ New Image ] vs [ Master 0° Reference ]       | |
| | [✓] SHA-256 Manifest Encrypted             | | | [ Approve (A) ]   [ Discard (D) ]   [ Re-roll ]| |
| +--------------------------------------------+ | +-----------------------------------------------+ |
+----------------------------------------------------------------------------------------------------+
```

---

## 5. Implementation Path

1. **Step 1: Frontend HTML/CSS Mockup**: Add an `Overview / Cockpit` tab in [index.html](file:///d:/Project/AI%20Influencer%20Studio/static/index.html) and [styles.css](file:///d:/Project/AI%20Influencer%20Studio/static/styles.css).
2. **Step 2: Backend Aggregation Endpoint**: Create a `/api/dashboard/overview` endpoint in [studio/app.py](file:///d:/Project/AI%20Influencer%20Studio/studio/app.py) that aggregates:
   - Active persona details & turnaround thumbnails
   - Hardware telemetry (VRAM, memory, GPU)
   - Job queue counts (running, queued, completed)
   - Recent generation outputs for instant approval
   - System weights inventory status
3. **Step 3: Auto-Refresh WebSocket or Polling**: Keep the telemetry ticker and queue status updated in real-time.

