import os
import time
import secrets
import threading
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

ROOT_DIR = Path(__file__).resolve().parent.parent
RENDERS_DIR = ROOT_DIR / "generated" / "renders"
RENDERS_DIR.mkdir(parents=True, exist_ok=True)

# Aspect ratio map for SDXL
ASPECT_DIMENSIONS: Dict[str, Tuple[int, int]] = {
    "9:16": (704, 1280),
    "4:5": (832, 1024),
    "1:1": (1024, 1024),
    "16:9": (1280, 720),
    "2:3": (768, 1152),
}

UNIVERSAL_NEGATIVE = (
    "deformed, bad anatomy, bad hands, extra fingers, missing fingers, mutated, "
    "fake plastic skin, doll skin, 3d render, cartoon, anime, illustration, blurry, "
    "bad eyes, crossed eyes, oversaturated, low quality, artifacts, watermark, text"
)

_lock = threading.Lock()
_current_pipe = None
_current_model_id = None

def get_pipeline(model_id: str = "juggernaut-xl-v10"):
    global _current_pipe, _current_model_id
    with _lock:
        if _current_pipe is not None and _current_model_id == model_id:
            return _current_pipe

        import torch
        from diffusers import StableDiffusionXLPipeline, DPMSolverMultistepScheduler

        device = "mps" if (hasattr(torch.backends, "mps") and torch.backends.mps.is_available()) else ("cuda" if torch.cuda.is_available() else "cpu")
        dtype = torch.float16 if device in ("mps", "cuda") else torch.float32

        if model_id == "cyberrealistic-xl":
            model_path = ROOT_DIR / "models/cyberrealistic-xl/CyberRealisticXLPlay_V10.0_FP16.safetensors"
        else:
            model_path = ROOT_DIR / "models/juggernaut-xl-v10/Juggernaut-X-RunDiffusion-NSFW.safetensors"

        if not model_path.exists():
            # Check alternative in models
            alternatives = list((ROOT_DIR / "models").glob("*/*.safetensors"))
            if alternatives:
                model_path = alternatives[0]
            else:
                raise FileNotFoundError(f"Model file not found: {model_path}")

        print(f"[Diffusion Engine] Loading {model_id} from {model_path} onto {device} ({dtype})...")
        pipe = StableDiffusionXLPipeline.from_single_file(
            str(model_path),
            torch_dtype=dtype,
            local_files_only=True
        ).to(device)

        pipe.scheduler = DPMSolverMultistepScheduler.from_config(
            pipe.scheduler.config,
            use_karras_sigmas=True
        )

        _current_pipe = pipe
        _current_model_id = model_id
        print(f"[Diffusion Engine] Model {model_id} ready on {device}!")
        return _current_pipe

def generate_render(
    prompt: str,
    negative_prompt: Optional[str] = None,
    aspect_ratio: str = "1:1",
    model_id: str = "juggernaut-xl-v10",
    persona_id: str = "maya_bhutia",
    persona_name: str = "Creator",
    seed: Optional[int] = None,
    steps: int = 20,
    guidance_scale: float = 5.0,
    register_asset: bool = True,
) -> Dict[str, Any]:
    """
    Executes real neural diffusion inference on Apple MPS using Juggernaut XL v10 / CyberRealistic XL.
    Saves the generated PNG to generated/renders/ and registers in SQLite assets table.
    """
    import torch

    device = "mps" if (hasattr(torch.backends, "mps") and torch.backends.mps.is_available()) else ("cuda" if torch.cuda.is_available() else "cpu")
    width, height = ASPECT_DIMENSIONS.get(aspect_ratio, (1024, 1024))

    actual_seed = seed if (seed is not None and seed > 0) else secrets.randbelow(999999)
    generator = torch.Generator(device).manual_seed(actual_seed)

    neg = negative_prompt.strip() if (negative_prompt and negative_prompt.strip()) else UNIVERSAL_NEGATIVE

    t0 = time.time()
    pipe = get_pipeline(model_id)

    print(f"[Diffusion Engine] Generating {width}x{height} render for {persona_name} (Seed: {actual_seed}, Steps: {steps})...")
    with _lock:
        image = pipe(
            prompt=prompt,
            negative_prompt=neg,
            width=width,
            height=height,
            num_inference_steps=steps,
            guidance_scale=guidance_scale,
            generator=generator
        ).images[0]

    elapsed = round(time.time() - t0, 2)

    timestamp = int(time.time())
    filename = f"render_{persona_id}_{timestamp}_{actual_seed}.png"
    out_path = RENDERS_DIR / filename
    image.save(out_path, format="PNG")

    rel_url = f"/generated/renders/{filename}"
    print(f"[Diffusion Engine] Saved render in {elapsed}s to {rel_url}")

    # The canonical API route registers bytes through studio.assets so it can
    # attach Job lineage, hashes, quality metadata, and the configured output
    # store. Keep the legacy registration path for vault compatibility until
    # that background workflow is migrated separately.
    if register_asset:
        try:
            from . import database as db
            aid = f"render-{timestamp}-{actual_seed}"
            version = db.row(
                "SELECT id FROM persona_versions WHERE persona_id=? ORDER BY version_no DESC LIMIT 1",
                (persona_id,),
            )
            db.write(
                "INSERT INTO assets (id, persona_id, persona_version_id, filename, kind, prompt, review, rights_confirmed, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (aid, persona_id, version["id"] if version else None, filename, "image", prompt, "pending", 1, time.strftime("%Y-%m-%d %H:%M:%S"))
            )
        except Exception as db_err:
            print(f"[Diffusion Engine] Database write notice: {db_err}")

    return {
        "status": "completed",
        "image_url": rel_url,
        "aspect_ratio": aspect_ratio,
        "width": width,
        "height": height,
        "seed": actual_seed,
        "elapsed_seconds": elapsed,
        "model": model_id,
        "persona_id": persona_id,
        "persona_name": persona_name,
        "filename": filename
    }
