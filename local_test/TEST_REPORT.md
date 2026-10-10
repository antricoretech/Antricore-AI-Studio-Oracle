# Local CPU image smoke-test report

**Date:** 10 October 2026  
**Environment:** Windows 10, Python 3.12.10, isolated `local_test/.venv`  
**Device:** CPU-only PyTorch (`torch.cuda.is_available() == false`)  
**Prompt policy:** original fictional adult, fully clothed, non-explicit fashion portrait

## Results

### Small Stable Diffusion v0 — passed

- Repository: `OFA-Sys/small-stable-diffusion-v0`
- Resolution: 512 × 512
- Steps: 10
- Seed: 42
- Output: `outputs/small-sd_42.png`
- Report: `results_small-sd.json`
- End-to-end duration including model download: approximately 671 seconds.
- Peak recorded process RSS: approximately 4.3 GB.
- CPU generation after loading: approximately 3 minutes 12 seconds.

The image is valid and suitable for testing the output/import/review pipeline.
It shows visible face/eye artifacts and should not be used as a production
persona master.

### Swimwear scene variation — safety-checker fallback

- Command: `run_image_tests.py --model small-sd --seed 77 --prompt ...`
- The diffusion pipeline completed in approximately 5 minutes and wrote
  `outputs/small-sd_77.png`.
- The checkpoint's built-in safety checker classified the result as unsafe and
  returned a black placeholder image. This is a model safety-checker result,
  not an application crash. The placeholder must not be treated as a usable
  asset; the successful `small-sd_42.png` remains the valid smoke-test output.

### SD-Turbo — blocked before inference

- Repository: `stabilityai/sd-turbo`
- Report: `results_sd-turbo.json`
- The Hugging Face download stalled while fetching the remaining weight files.
- The full `sd_turbo.safetensors` file is approximately 5.2 GB; the smaller
  fp16 component path was also not fully cached during this run.

No image was generated. This is a model-download/network limitation, not an
application-code failure.

### Tiny-SD — blocked before inference

- Repository: `segmind/tiny-sd`
- Report: `results_tiny-sd.json`
- The Hugging Face download stalled before the VAE and UNet weights were
  completely cached.

No image was generated. The cached partial files should be retried only when a
stable model-download connection is available.

### Tiny-SD retry — download interrupted

- A second retry was started with a shorter swimwear test prompt (seed 90).
- The download resumed and created additional partial weight blobs, but the
  run was interrupted before the pipeline could load, so no image was produced.
- No production files were changed and no incomplete checkpoint was treated as
  usable.

## Interpretation

The local machine can run a compact diffusion model on CPU, but the result is
slow and visibly less reliable than the cloud GPU path. The successful test
proves that the isolated environment can create a PNG and can be connected to
the dashboard import/review flow later. It does not justify changing the
production CUDA model registry.

The isolated environment deliberately does not import `studio.free_cli`, does
not change `studio/`, and does not alter production requirements. Model cache,
outputs and reports remain inside `local_test/`.

The harness now accepts `--prompt` and `--negative-prompt`, carries the safety
terms into each test report, and labels an all-black safety-checker placeholder
as `blocked_safety` instead of counting it as a successful render.

## Next retry options

1. Retry SD-Turbo with a stable connection and the fp16 component variant.
2. Retry Tiny-SD with a stable connection.
3. Evaluate an ONNX/DirectML SD1.5 path separately; the 2 GB integrated Radeon
   may still be too small for reliable GPU execution.
4. Keep Small Stable Diffusion as the local CPU smoke-test fallback.
