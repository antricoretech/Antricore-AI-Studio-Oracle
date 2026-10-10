# Isolated local image-test environment

This directory is intentionally separate from the production Studio code. It
does not import `studio.free_cli`, modify production configuration, or change
the dashboard. It tests whether small text-to-image checkpoints can run on the
local Windows workstation using CPU inference.

## Models tested

- `OFA-Sys/small-stable-diffusion-v0` — compact CPU-oriented baseline.
- `stabilityai/sd-turbo` — one-step distilled Diffusers baseline.
- `segmind/tiny-sd` — compact distilled 512px baseline.

Model files are downloaded into `local_test/cache/` and generated files are
written to `local_test/outputs/`. They are not production assets. The prompts
are safe, fully clothed, fictional-adult fashion prompts for pipeline testing.

## Setup (PowerShell)

```powershell
cd "D:\Project\AI Influencer Studio"
py -3.12 -m venv local_test\.venv
local_test\.venv\Scripts\python.exe -m pip install --upgrade pip
local_test\.venv\Scripts\python.exe -m pip install -r local_test\requirements.txt
```

## Run all CPU image tests

```powershell
local_test\.venv\Scripts\python.exe local_test\run_image_tests.py
```

The command writes:

- one PNG and JSON sidecar per model under `local_test/outputs/`;
- `local_test/results.json` containing duration, status, device and errors;
- a non-destructive summary to the terminal.

Use `--model small-sd`, `--model sd-turbo` or `--model tiny-sd` to run one
model. Use `--offline` after all required weights are cached. The first run
can be slow and requires internet access for model downloads.

For an isolated scene variation, pass a custom prompt. Keep the subject
explicitly fictional and adult, and keep the scene non-explicit:

```powershell
local_test\.venv\Scripts\python.exe local_test\run_image_tests.py `
  --model small-sd --seed 77 `
  --prompt "editorial lifestyle portrait of an original fictional adult woman aged 25, wearing full-coverage athletic swimwear with a long-sleeve rash guard and swim leggings, beside a sunny pool, realistic non-explicit fashion photography"
```

## Interpretation

This is a CPU smoke test, not a production-quality benchmark. The local AMD
integrated GPU is not used by this harness. The generated images must remain
pending manual review and must not be published without the project's AI
disclosure and rights checks.
