# Generation brief workflow

Use one JSON brief as the hand-off between ChatGPT, the dashboard and the local CLI. The brief describes a fictional adult character, the master image, the Wan2.2 motion prompt, optional Kokoro narration, FFmpeg output and the review gate.

## 1. Ask ChatGPT for the brief

Paste the following instruction into ChatGPT, then replace the values in the `INPUTS` block:

```text
You are a production planner for a local, self-hosted AI media pipeline.
Return ONLY valid UTF-8 JSON matching config/generation_brief.example.json and schema_version "1.0". Do not add Markdown fences or commentary.

Create a fictional adult fashion, glamour or lifestyle character. The character must be 18 or older, original and clearly disclosed as AI-generated. Bold glamour, sensual editorial styling, swimwear and lingerie-inspired fashion are allowed when the subject is clearly an adult and the context is non-explicit. Never use a real person's name, face, body, voice, private data or copyrighted reference without documented permission. Do not describe minors, explicit sexual acts, impersonation, or deceptive real-person content.

Allowed image models: flux2-klein-4b, z-image-turbo.
Allowed video model: wan22-ti2v-5b.
Allowed sizes: 1280*704 or 704*1280.
Use concise, production-ready prompts. Keep the same identity anchor in both image and video prompts. Include a useful negative prompt. Set voice.enabled=false unless narration text is supplied.

INPUTS:
- Character name: [name]
- Adult age: [18+ age]
- Face anchor: [face shape, skin tone, eyes, hair and one fictional distinguishing feature]
- Physique and movement: [adult proportions, posture, walk and age cues]
- Style system: [wardrobe, fabrics, palette, accessories, grooming and glamour direction]
- Personality: [traits, interests, values, speech style and mannerisms]
- World: [cultural context, home base, recurring locations and content pillars]
- Camera language: [framing, lens/depth, lighting and color grade]
- Location and scene: [where]
- Action and camera movement: [what happens in the video]
- Narration: [optional text, or NONE]
- Aspect ratio: [vertical or landscape]
- Seed: [number or choose one]

The output must contain: schema_version, title, persona, image, video, voice, assembly and review. `persona.characteristics` must contain `face`, `physique`, `style`, `personality`, `world` and `camera` sections. Keep the same identity anchor in both image and video prompts.
```

An example is available at [config/generation_brief.example.json](../config/generation_brief.example.json).

## 2. Create a persona directly in Persona Library

The **Persona Library** has its own **Copy persona prompt** and **Import persona JSON** controls. Use the persona prompt when you want ChatGPT to create only the reusable identity capsule first. Save the response as JSON, upload it there, and the app will validate and add the persona immediately. The file shape is:

```json
{
  "schema_version": "persona-1.0",
  "persona": {
    "name": "Mira Vale",
    "age": 25,
    "appearance": "...",
    "description": "...",
    "consistency_anchor": "...",
    "characteristics": {
      "face": {}, "physique": {}, "style": {},
      "personality": {}, "world": {}, "camera": {}
    }
  }
}
```

You can also upload a direct persona object without the envelope; the server wraps and validates it. A complete starter file is available at [config/persona_brief.example.json](../config/persona_brief.example.json). References are still uploaded separately so rights confirmation is explicit.

## 3. Load it in the dashboard

Open **Create → Generation brief**. The **ChatGPT handoff** card shows the required uniqueness inputs and includes a **Copy ChatGPT prompt** button. Choose the JSON file, then select **Load brief**. The dashboard validates the file and stages the persona, image prompt, motion prompt, canvas, seed and narration fields. Review the staged values, save the persona, select an appropriate workflow, confirm rights/disclosure, then queue the job. The import does not start a GPU job automatically.

The validation endpoint is `POST /api/briefs/validate` and accepts one JSON file up to 1 MB.

## 4. Run the same file from the local CLI

Validate without rendering:

```powershell
.\.venv\Scripts\python.exe -m studio.free_cli brief --file config\generation_brief.example.json --dry-run
```

Execute after model weights, the Wan2.2 checkout, FFmpeg and the separate Wan Python environment are installed:

```powershell
.\.venv\Scripts\python.exe -m studio.free_cli brief --file path\to\brief.json --python path\to\wan-venv\Scripts\python.exe
```

The CLI still writes a disclosure sidecar next to the final output. Generation remains local; the JSON brief does not call a hosted API or consume API credits.

## Required review

The brief is a production plan, not proof that a model or asset is commercially licensed. Verify each model card, dependency, reference image, voice pack and destination platform before publication. Manually inspect identity continuity, anatomy, motion, audio timing and the visible AI disclosure.
