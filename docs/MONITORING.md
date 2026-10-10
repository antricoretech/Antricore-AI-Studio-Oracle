# Cloud worker monitoring

Open **Monitoring** after starting the application or reconnecting to the GPU server. Click **Run checks** to inspect the current worker state without starting a render.

The tab checks:

- **Security** — authentication configuration and strict media validation mode.

- **API / database** — FastAPI control plane, SQLite response and database path.
- **Connections** — optional local ComfyUI API URL, response status, devices and checkpoint count.
- **Runtime** — CUDA/PyTorch visibility, FFmpeg, Kokoro dependencies, Wan2.2 checkout and its separate Python executable.
- **Model files** — each allowlisted model directory under `models/`, expected license label and hardware guidance.
- **Workflows** — verified imported ComfyUI graphs versus catalog-only recipes that still need setup.
- **Operations** — active/failed jobs and persistent disk free space.

`READY` means the check responded successfully. `CHECK` means the application is usable but an optional integration, dependency, model or workflow still needs attention. `ERROR` indicates a core check failed. A degraded result is expected on a fresh worker before model downloads, FFmpeg/Kokoro installation, Wan2.2 setup or ComfyUI startup.

The endpoint is read-only: `GET /api/monitor`. Monitoring does not download models, start GPU inference or send prompts to a hosted API. The dashboard refreshes the view when the tab is opened and every 30 seconds while it remains visible.
