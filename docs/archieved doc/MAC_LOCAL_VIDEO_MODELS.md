# Local Video Generation Models for MacBook Air M5 (16 GB)

**Reference date:** 20 October 2026  
**Hardware:** MacBook Air M5, 16 GB unified memory, 512 GB storage

This note records the research shortlist for locally running relatively low-filter/open-weight video-generation models on Apple Silicon. It is a reference only; no model, runtime, dependency, or workflow has been installed as part of creating this file.

## Important terminology

“Uncensored” is not a formal technical category. A local model generally does not have a hosted API moderation layer, but model weights, code, and outputs may still be governed by licenses, acceptable-use policies, copyright rules, privacy law, and consent requirements. No model should be assumed to generate literally every kind of content.

## Recommended shortlist

### 1. Wan2.1 1.3B through MLX — first choice

- Official repository: https://github.com/Wan-Video/Wan2.1
- Apple Silicon implementation: https://github.com/ml-explore/mlx-examples/tree/main/video/wan2.1
- Approximate popularity: 17k GitHub stars for the official repository
- Primary capability: text-to-video
- Mac feasibility: **best candidate**
- Reported memory: approximately 10 GB RAM for 480p/81 frames with cache disabled in the MLX implementation
- Expected constraints on 16 GB: short clips, modest resolution, slow generation, and no other memory-heavy applications running
- License note: the Wan2.1 repository includes an Apache 2.0 license; verify the exact model-weight terms before distribution

The MLX implementation is specifically designed for Apple Silicon. Image-to-video is more demanding than text-to-video and should be treated as a separate compatibility test.

### 2. LTX-2.3 quantized MLX — second choice

- Official repository: https://github.com/Lightricks/LTX-2
- Apple Silicon implementation: https://github.com/dgrauet/ltx-2-mlx
- Approximate popularity: 9.5k stars for the official LTX-2 repository
- Capabilities: text-to-video, image-to-video, and audio-to-video
- Mac feasibility: **possible with int4 quantization and low-RAM streaming**
- Reported model-pack size: approximately 12 GB for an int4 variant
- Expected constraints on 16 GB: short/low-resolution clips and substantially slower execution than a discrete GPU

This is more feature-rich than Wan2.1 but less certain on a 16 GB MacBook Air. The community implementation documents an int4 configuration and `--low-ram` mode for 16 GB Macs.

### 3. Wan2.1 VACE 1.3B through MLX-Gen — editing/reference option

- Implementation: https://github.com/lpalbou/mlx-gen
- Documentation: https://github.com/lpalbou/mlx-gen/blob/main/docs/wan-video.md
- Capabilities: video-to-video, reference-image injection, and masked editing
- Mac feasibility: **possible only with small diagnostic settings**
- Best use: modifying or guiding an existing video rather than general text-to-video
- Reported low-memory diagnostic: approximately 13.8 GiB RSS at 448×256 and 17 frames

This may fit the machine, but practical quality settings are likely to exceed the comfortable memory budget.

### 4. CogVideoX-2B — experimental only

- Repository: https://github.com/zai-org/CogVideo
- Capabilities: text-to-video and image-to-video
- Mac feasibility: **uncertain/experimental**
- Memory note: the project documents quantized low-memory inference, but published benchmarks are mainly NVIDIA-focused
- License note: the repository contains Apache 2.0 licensing information; verify model-specific terms

CogVideoX-2B should not be the first Mac implementation because Apple Silicon/MPS behavior is less clearly validated than the MLX Wan2.1 route.

## Models not suitable for this machine

| Model | Reason |
|---|---|
| Wan2.2 TI2V-5B | Apple-native implementations have been measured on much larger-memory Macs; not a practical 16 GB target. |
| Wan2.2 14B | Requires substantially more memory. |
| HunyuanVideo | Official requirements list approximately 45–60 GB GPU memory. |
| HunyuanVideo 1.5 | Official target is NVIDIA CUDA; minimum listed memory is 14 GB GPU memory with offloading. |
| LTX-2 full precision | Generally requires substantially more than 16 GB unified memory. |
| MiniMax H3 | Far beyond the available memory capacity. |

## Storage planning

512 GB is sufficient for one or two carefully selected model packages, the Python/MLX environments, and test outputs. It is not sufficient for collecting many large checkpoints, multiple full-precision variants, caches, and generated video archives without active cleanup.

## Recommended future test order

1. Wan2.1 1.3B through MLX, text-to-video only.
2. Wan2.1 with very short image-to-video tests.
3. LTX-2.3 int4 MLX if audio-video or richer image-to-video features are required.
4. Wan2.1 VACE 1.3B only for editing/reference workflows.
5. CogVideoX-2B only as an experimental comparison.

## Source links

- Apple MLX Wan2.1 memory and usage notes: https://github.com/ml-explore/mlx-examples/blob/main/video/wan2.1/README.md
- MLX-Video supported models: https://github.com/Blaizzy/mlx-video
- LTX-2.3 MLX low-RAM/int4 notes: https://github.com/dgrauet/ltx-2-mlx
- Wan2.1 VACE/MLX-Gen memory notes: https://github.com/lpalbou/mlx-gen/blob/main/docs/wan-video.md
- ComfyUI popularity reference: https://github.com/comfy-org/ComfyUI
- HunyuanVideo requirements: https://github.com/Tencent-Hunyuan/HunyuanVideo/blob/main/README.md
- HunyuanVideo 1.5 requirements and license: https://github.com/Tencent-Hunyuan/HunyuanVideo-1.5
