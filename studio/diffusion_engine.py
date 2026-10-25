import os
import time
import secrets
import threading
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

ROOT_DIR = Path(__file__).resolve().parent.parent
GENERATED_ROOT = Path(os.getenv("STUDIO_GENERATED_DIR") or (ROOT_DIR / "generated")).resolve()
RENDERS_DIR = GENERATED_ROOT / "renders"
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


class ModelConfigurationError(RuntimeError):
    """Raised when a requested model cannot be served by this runtime."""


# This module is deliberately narrow: it is the legacy SDXL single-file
# renderer, not a universal adapter for every model in approved_models.json.
# Keeping the mapping explicit prevents a missing checkpoint from silently
# selecting an unrelated file from the models directory.
SUPPORTED_SINGLE_FILE_MODELS: Dict[str, Path] = {
    "juggernaut-xl-v10": Path(
        "models/juggernaut-xl-v10/Juggernaut-X-RunDiffusion-NSFW.safetensors"
    ),
    "cyberrealistic-xl": Path(
        "models/cyberrealistic-xl/CyberRealisticXLPlay_V10.0_FP16.safetensors"
    ),
}

def get_pipeline(model_id: str = "juggernaut-xl-v10"):
    global _current_pipe, _current_model_id
    with _lock:
        if _current_pipe is not None and _current_model_id == model_id:
            return _current_pipe

        model_relative_path = SUPPORTED_SINGLE_FILE_MODELS.get(model_id)
        if model_relative_path is None:
            from .model_registry import get

            if get(model_id) is None:
                raise ModelConfigurationError(
                    f"Model '{model_id}' is not in the approved registry"
                )
            raise ModelConfigurationError(
                f"Model '{model_id}' is registered but not supported by the "
                "legacy SDXL single-file runtime"
            )

        from .model_registry import match

        compatible, reason = match(
            model_id,
            task="image.text_to_image",
            backend="direct-cli",
        )
        if not compatible:
            raise ModelConfigurationError(reason)

        model_path = ROOT_DIR / model_relative_path
        if not model_path.is_file():
            raise FileNotFoundError(
                f"Model file not found for '{model_id}': {model_path}. "
                "Install the approved checkpoint before running generation."
            )

        import torch
        from diffusers import StableDiffusionXLPipeline, DPMSolverMultistepScheduler

        device = "mps" if (hasattr(torch.backends, "mps") and torch.backends.mps.is_available()) else ("cuda" if torch.cuda.is_available() else "cpu")
        dtype = torch.float16 if device in ("mps", "cuda") else torch.float32

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


def _register_render_asset(*, persona_id: str, persona_name: str, prompt: str,
                           raw: bytes, original_filename: str, model_id: str,
                           seed: int, aspect_ratio: str, width: int, height: int) -> dict:
    """Register a standalone render through the canonical media boundary."""

    from . import database as db
    from .assets import register_media_asset

    persona = db.row("SELECT id FROM personas WHERE id=?", (persona_id,))
    if not persona:
        raise ValueError("Standalone diffusion registration requires a canonical Persona")
    version = db.row(
        "SELECT id FROM persona_versions WHERE persona_id=? ORDER BY version_no DESC LIMIT 1",
        (persona_id,),
    )
    return register_media_asset(
        persona_id=persona_id,
        persona_version_id=version["id"] if version else None,
        job_id=None,
        kind="image",
        prompt=prompt,
        raw=raw,
        rights_confirmed=False,
        original_filename=original_filename,
        lineage={
            "execution_mode": "standalone_diffusion",
            "model": model_id,
            "persona_name": persona_name,
            "seed": seed,
            "aspect_ratio": aspect_ratio,
            "width": width,
            "height": height,
        },
    )


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
    # Validate routing before importing the heavyweight runtime. This gives a
    # deterministic configuration error for unsupported/uninstalled models.
    pipe = get_pipeline(model_id)
    import torch

    device = "mps" if (hasattr(torch.backends, "mps") and torch.backends.mps.is_available()) else ("cuda" if torch.cuda.is_available() else "cpu")
    width, height = ASPECT_DIMENSIONS.get(aspect_ratio, (1024, 1024))

    actual_seed = seed if (seed is not None and seed > 0) else secrets.randbelow(999999)
    generator = torch.Generator(device).manual_seed(actual_seed)

    neg = negative_prompt.strip() if (negative_prompt and negative_prompt.strip()) else UNIVERSAL_NEGATIVE

    t0 = time.time()
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

    asset = None
    if register_asset:
        try:
            asset = _register_render_asset(
                persona_id=persona_id,
                persona_name=persona_name,
                prompt=prompt,
                raw=out_path.read_bytes(),
                original_filename=filename,
                model_id=model_id,
                seed=actual_seed,
                aspect_ratio=aspect_ratio,
                width=width,
                height=height,
            )
            print(f"[Diffusion Engine] Registered canonical pending asset {asset['id']}")
        except Exception as db_err:
            print(f"[Diffusion Engine] Canonical asset registration notice: {db_err}")

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
        "filename": filename,
        "asset_id": asset["id"] if asset else None,
        "asset_url": f"/api/assets/{asset['id']}/file" if asset else None,
    }
