"""Run isolated, CPU-only image smoke tests without importing Studio code."""

from __future__ import annotations

import argparse
import json
import os
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CACHE = ROOT / "cache"
OUTPUTS = ROOT / "outputs"
RESULTS = ROOT / "results.json"

MODELS = {
    "small-sd": {
        "label": "Small Stable Diffusion v0",
        "repo": "OFA-Sys/small-stable-diffusion-v0",
        "pipeline": "diffusion",
        "steps": 10,
    },
    "sd-turbo": {
        "label": "SD-Turbo",
        "repo": "stabilityai/sd-turbo",
        "pipeline": "turbo",
        "steps": 1,
    },
    "tiny-sd": {
        "label": "Tiny-SD",
        "repo": "segmind/tiny-sd",
        "pipeline": "diffusion",
        "steps": 10,
    },
}

PROMPT = (
    "editorial glamour portrait of an original fictional adult woman aged 25, "
    "tasteful full-coverage fashion styling, confident natural pose, soft window light, "
    "realistic photography, clean modern background, non-explicit"
)
NEGATIVE_PROMPT = (
    "blurry, deformed, extra fingers, duplicate person, watermark, typography, logo, "
    "child, teenager, minor, nudity, exposed genitals, explicit sexual activity, lingerie, real-person likeness"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", choices=["all", *MODELS], default="all")
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--width", type=int, default=512)
    parser.add_argument("--height", type=int, default=512)
    parser.add_argument(
        "--prompt",
        default=PROMPT,
        help="Override the isolated smoke-test prompt (keep it non-explicit and fictional).",
    )
    parser.add_argument(
        "--negative-prompt",
        default=NEGATIVE_PROMPT,
        help="Negative prompt used by the model quality/safety pass.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.width % 8 or args.height % 8:
        raise SystemExit("Width and height must be multiples of 8.")

    CACHE.mkdir(parents=True, exist_ok=True)
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("HF_HOME", str(CACHE / "huggingface"))
    # Keep the isolated test harness on the regular Hub HTTP path. This makes
    # resumable downloads more predictable on this Windows workstation and
    # avoids coupling the test environment to the optional hf-xet client.
    os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
    if args.offline:
        os.environ["HF_HUB_OFFLINE"] = "1"

    import psutil
    import torch
    from diffusers import DiffusionPipeline

    # Deliberately force CPU. This is a local test harness, not a production
    # GPU path, and it must not alter or depend on Studio's CUDA environment.
    device = "cpu"
    torch.set_grad_enabled(False)
    process = psutil.Process()
    selected = list(MODELS) if args.model == "all" else [args.model]
    results: list[dict] = []

    for key in selected:
        spec = MODELS[key]
        started = time.perf_counter()
        record = {
            "model": key,
            "label": spec["label"],
            "repository": spec["repo"],
            "device": device,
            "width": args.width,
            "height": args.height,
            "steps": spec["steps"],
            "seed": args.seed,
            "prompt": args.prompt,
            "negative_prompt": args.negative_prompt,
            "status": "failed",
            "started_at": datetime.now(timezone.utc).isoformat(),
        }
        try:
            print(f"[{key}] loading {spec['repo']} on CPU ...", flush=True)
            dtype = torch.float32
            if spec["pipeline"] == "turbo":
                from diffusers import AutoPipelineForText2Image

                pipe = AutoPipelineForText2Image.from_pretrained(
                    spec["repo"],
                    torch_dtype=dtype,
                    variant="fp16",
                    use_safetensors=True,
                    cache_dir=str(CACHE / "huggingface"),
                    local_files_only=args.offline,
                )
            else:
                pipe = DiffusionPipeline.from_pretrained(
                    spec["repo"],
                    torch_dtype=dtype,
                    cache_dir=str(CACHE / "huggingface"),
                    local_files_only=args.offline,
                )
            pipe.to(device)
            generator = torch.Generator(device=device).manual_seed(args.seed)
            kwargs = {
                "prompt": args.prompt,
                "negative_prompt": args.negative_prompt,
                "height": args.height,
                "width": args.width,
                "num_inference_steps": spec["steps"],
                "generator": generator,
            }
            if key == "sd-turbo":
                kwargs["guidance_scale"] = 0.0
            result = pipe(**kwargs).images[0]
            image_path = OUTPUTS / f"{key}_{args.seed}.png"
            result.save(image_path)
            extrema = result.convert("RGB").getextrema()
            if all(channel[1] <= 2 for channel in extrema):
                record.update({
                    "status": "blocked_safety",
                    "output": str(image_path.relative_to(ROOT.parent)),
                })
                print(
                    f"[{key}] safety checker returned a blank placeholder: {image_path}",
                    file=sys.stderr,
                    flush=True,
                )
                del pipe
                continue
            record.update(
                {
                    "status": "passed",
                    "output": str(image_path.relative_to(ROOT.parent)),
                    "rss_mb": round(process.memory_info().rss / 1024 / 1024, 1),
                }
            )
            print(f"[{key}] saved {image_path}", flush=True)
            del pipe
        except Exception as exc:  # keep running the remaining isolated tests
            record["error"] = f"{type(exc).__name__}: {exc}"
            print(f"[{key}] FAILED: {record['error']}", file=sys.stderr, flush=True)
        finally:
            record["duration_seconds"] = round(time.perf_counter() - started, 2)
            results.append(record)

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "torch_cuda_available": bool(torch.cuda.is_available()),
        "forced_device": device,
        "prompt_policy": "fictional adult, fully clothed, non-explicit smoke test",
        "results": results,
    }
    # Keep a per-run report so an unsuccessful model download never erases a
    # previous successful smoke test. Preserve results.json for the all-model
    # invocation and write model-specific reports for single-model runs.
    report_path = RESULTS if args.model == "all" else ROOT / f"results_{args.model}.json"
    report_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    passed = sum(item["status"] == "passed" for item in results)
    print(f"Completed {passed}/{len(results)} tests. Report: {report_path}")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
