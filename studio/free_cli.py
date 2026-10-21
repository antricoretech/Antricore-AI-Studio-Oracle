"""Free local generation commands; no API keys, cloud GPU, tokens, or credits used.

Large model downloads require network access once. To run offline afterwards,
use --offline with pre-downloaded local weights. Video backends have separate
Python environments; see docs/LOCAL_FREE_SETUP.md.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from types import SimpleNamespace

from .policies import AI_DISCLOSURE, DEFAULT_NEGATIVE_PROMPT

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / 'config' / 'approved_models.json'
REGISTRY = json.loads(CONFIG.read_text(encoding='utf8'))
MODEL_ROOT = ROOT / 'models'
OUTPUT_ROOT = ROOT / 'generated'


def identity_prompt_from_brief(brief) -> str:
    """Turn the frozen persona capsule into a stable suffix for both stages."""
    from .brief import brief_dict

    def flatten(value, limit=900):
        if isinstance(value, dict):
            text = '; '.join(f'{key.replace("_", " ")}: {flatten(item, 240)}' for key, item in value.items() if item not in (None, '', [], {}))
        elif isinstance(value, list):
            text = ', '.join(flatten(item, 180) for item in value if item not in (None, '', [], {}))
        else:
            text = str(value)
        return text[:limit]

    persona = brief.persona
    parts = [
        f'Original fictional adult persona: {persona.name}, age {persona.age}.',
        'This is an original fictional adult character; do not depict a minor or imitate a real person.',
        'Use tasteful, non-explicit editorial glamour and fashion direction only.',
        f'Appearance: {persona.appearance}.',
        f'Character direction: {persona.description}.',
        f'Identity anchor: {flatten(persona.consistency_anchor, 1200)}.',
        f'Structured identity capsule: {flatten(brief_dict(persona.characteristics), 4200)}.',
    ]
    return ' '.join(part for part in parts if not part.endswith(': .'))[:6000]


def run_brief(args):
    """Run one validated JSON brief through the local pipeline."""
    from .brief import brief_dict, parse_brief_file

    brief = parse_brief_file(args.file)
    plan = brief_dict(brief)
    if args.dry_run:
        print(json.dumps(plan, indent=2))
        return
    if not brief.image.enabled or not brief.video.enabled:
        raise ValueError('The executable brief requires both image.enabled and video.enabled to be true')
    if brief.voice.enabled and not brief.voice.text.strip():
        raise ValueError('voice.enabled requires non-empty narration text')
    if brief.voice.enabled and not brief.assembly.enabled:
        raise ValueError('voice.enabled requires assembly.enabled so the narration can be muxed into the video')
    identity = identity_prompt_from_brief(brief)
    pipeline(SimpleNamespace(
        prompt=f'{identity} Master image direction: {brief.image.prompt}',
        video_prompt=f'{identity} Video motion direction: {brief.video.prompt}',
        narration=brief.voice.text if brief.voice.enabled else None,
        voice=brief.voice.voice,
        lang=brief.voice.lang,
        model=brief.image.model,
        reference=brief.image.reference_paths or None,
        width=brief.image.width,
        height=brief.image.height,
        seed=brief.image.seed,
        steps=brief.image.steps,
        guidance=brief.image.guidance,
        negative_prompt=brief.image.negative_prompt,
        cpu_offload=args.cpu_offload,
        offline=args.offline,
        mode=brief.video.model,
        size=brief.video.size,
        python=args.python,
        master=brief.image.output,
        video=brief.video.output,
        audio=brief.voice.output,
        output=brief.assembly.output,
        disclosure=brief.assembly.disclosure,
        dry_run=False,
    ))


def local_model(key: str) -> Path:
    if key not in REGISTRY:
        raise ValueError(f'Unapproved model: {key}')
    return MODEL_ROOT / key


def register_output(args):
    """Import an existing CLI output into the canonical Asset boundary."""

    from . import database as db
    from .assets import register_media_asset
    from .media import extension_for, validate_image_bytes, validate_media_signature
    from .settings import get_settings

    db.initialize()
    source = Path(args.file).expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(f'Output file not found: {source}')
    extension_for(args.kind, source.name)
    if source.stat().st_size > get_settings().asset_max_bytes:
        raise ValueError(f'Output exceeds the {get_settings().asset_max_bytes // (1024 * 1024)} MB asset limit')
    raw = source.read_bytes()
    if args.kind == 'image':
        validate_image_bytes(raw)
    else:
        validate_media_signature(raw, args.kind, strict=get_settings().strict_media_validation)

    persona = db.row('SELECT id FROM personas WHERE id=?', (args.persona_id,))
    if not persona:
        raise ValueError('CLI registration requires a canonical Persona')
    version = db.row(
        'SELECT id FROM persona_versions WHERE persona_id=? ORDER BY version_no DESC LIMIT 1',
        (args.persona_id,),
    )
    asset = register_media_asset(
        persona_id=args.persona_id,
        persona_version_id=version['id'] if version else None,
        job_id=None,
        kind=args.kind,
        prompt=args.prompt,
        raw=raw,
        disclosure=args.disclosure,
        rights_confirmed=args.rights_confirmed,
        original_filename=source.name,
        lineage={
            'execution_mode': 'free_cli_register',
            'source_filename': source.name,
            'source_kind': args.kind,
        },
    )
    result = {
        'id': asset['id'],
        'persona_id': asset['persona_id'],
        'persona_version_id': asset['persona_version_id'],
        'kind': asset['kind'],
        'review': asset['review'],
        'rights_confirmed': bool(asset['rights_confirmed']),
        'url': f"/api/assets/{asset['id']}/file",
    }
    print(json.dumps(result, indent=2))
    return result


def _maybe_register_cli_output(args, path: str | Path, kind: str, prompt: str, stage: str):
    """Opt-in bridge for direct CLI commands that produced a local file."""

    persona_id = getattr(args, 'persona_id', None)
    if not persona_id:
        return None
    return register_output(SimpleNamespace(
        persona_id=persona_id,
        file=str(path),
        kind=kind,
        prompt=prompt or f'Free CLI {stage} output',
        disclosure=getattr(args, 'disclosure', AI_DISCLOSURE),
        rights_confirmed=False,
    ))


def verify_image(path: str) -> Path:
    file = Path(path).expanduser().resolve()
    if not file.is_file() or file.suffix.lower() not in {'.png','.jpg','.jpeg','.webp'}:
        raise ValueError(f'Missing or unsupported image: {file}')
    return file


def image_call(args, torch, pipeline):
    kwargs={'prompt':args.prompt,'height':args.height,'width':args.width,
            'num_inference_steps':args.steps,'guidance_scale':args.guidance,
            'generator':torch.Generator('cpu').manual_seed(args.seed)}
    if getattr(args, 'negative_prompt', None) and 'negative_prompt' in __import__('inspect').signature(pipeline.__call__).parameters:
        kwargs['negative_prompt'] = args.negative_prompt
    if args.reference:
        from PIL import Image
        if args.model != 'flux2-klein-4b':
            raise ValueError('Reference-image conditioning in this CLI requires flux2-klein-4b')
        paths=[verify_image(p) for p in args.reference]
        kwargs['image']=[Image.open(p).convert('RGB') for p in paths]
    return pipeline(**kwargs).images[0]


def make_image(args):
    if args.model not in {'flux2-klein-4b','z-image-turbo','pony-diffusion-v6-xl','cyberrealistic-xl','juggernaut-xl-v10'}:
        raise ValueError('Image CLI supports FLUX.2 Klein 4B, Z-Image Turbo, Pony Diffusion V6 XL, CyberRealistic XL, and Juggernaut XL v10 only')
    import torch
    from diffusers import DiffusionPipeline, StableDiffusionXLPipeline
    if torch.cuda.is_available():
        device = 'cuda'
    elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
        device = 'mps'
    else:
        raise RuntimeError('Image generation requires a supported GPU (CUDA or Apple Silicon Metal/MPS).')
    local=local_model(args.model)
    if args.offline and not local.is_dir():
        raise RuntimeError(f'Weights absent: {local}. Download the model before using --offline.')
    source=str(local) if local.is_dir() and any(local.iterdir()) else REGISTRY[args.model]['hf']
    if args.offline: os.environ['HF_HUB_OFFLINE']='1'
    print(f'Loading {args.model} from {source}; may require substantial VRAM and disk space')
    dtype = torch.bfloat16 if device == 'cuda' else torch.float16
    if args.model in {'pony-diffusion-v6-xl', 'cyberrealistic-xl', 'juggernaut-xl-v10'}:
        safetensors_files = list(local.glob('*.safetensors')) if local.is_dir() else []
        if safetensors_files:
            pipe = StableDiffusionXLPipeline.from_single_file(str(safetensors_files[0]), torch_dtype=dtype, local_files_only=args.offline)
        else:
            raise RuntimeError(f"Weights absent in {local}. Run download command first.")
    else:
        pipe=DiffusionPipeline.from_pretrained(source, torch_dtype=dtype, local_files_only=args.offline)
    if args.cpu_offload and device == 'cuda':
        pipe.enable_model_cpu_offload()
    else:
        pipe.to(device)
    if args.model == 'z-image-turbo':
        args.guidance=0.0  # distilled model: no CFG recommended
        if args.steps == 4: args.steps=9
    elif args.model == 'pony-diffusion-v6-xl':
        if args.steps == 4: args.steps = 25
        if args.guidance == 1.0: args.guidance = 7.0
    elif args.model == 'cyberrealistic-xl':
        if args.steps == 4: args.steps = 28
        if args.guidance == 1.0: args.guidance = 5.0
    elif args.model == 'juggernaut-xl-v10':
        if args.steps == 4: args.steps = 30
        if args.guidance == 1.0: args.guidance = 5.0
    
    face_ref = getattr(args, 'face_ref', None)
    if face_ref:
        if args.model not in {'cyberrealistic-xl', 'pony-diffusion-v6-xl', 'juggernaut-xl-v10'}:
            raise ValueError('FaceID identity locking requires an SDXL model (cyberrealistic-xl, pony-diffusion-v6-xl, or juggernaut-xl-v10)')
        import cv2
        from PIL import Image
        import insightface
        from insightface.app import FaceAnalysis
        from insightface.utils import face_align
        from ip_adapter.ip_adapter_faceid import IPAdapterFaceIDPlusXL, IPAdapterFaceIDXL

        ref_path = verify_image(face_ref)
        print(f"Extracting facial identity embedding from {ref_path}...")
        face_app = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
        face_app.prepare(ctx_id=0, det_size=(640, 640))
        img_cv2 = cv2.imread(str(ref_path))
        faces = face_app.get(img_cv2)
        if not faces:
            raise ValueError(f"No face detected in reference image: {face_ref}")

        faceid_embeds = torch.from_numpy(faces[0].normed_embedding).unsqueeze(0)
        face_image = face_align.norm_crop(img_cv2, landmark=faces[0].kps, image_size=224)
        face_image_pil = Image.fromarray(cv2.cvtColor(face_image, cv2.COLOR_BGR2RGB))

        use_plus = getattr(args, 'faceid_plus', True)
        face_scale = getattr(args, 'faceid_scale', 0.75)

        if use_plus:
            lora_path = Path("models/ip-adapter-faceid/ip-adapter-faceid-plusv2_sdxl_lora.safetensors")
            if lora_path.exists():
                print(f"Loading FaceID-PlusV2 LoRA...")
                pipe.load_lora_weights(str(lora_path))
                pipe.fuse_lora()

            image_encoder_path = "laion/CLIP-ViT-H-14-laion2B-s32B-b79K"
            ip_ckpt = "models/ip-adapter-faceid/ip-adapter-faceid-plusv2_sdxl.bin"
            print("Activating IP-Adapter-FaceID-PlusV2 identity locking...")
            ip_model = IPAdapterFaceIDPlusXL(
                pipe,
                image_encoder_path=image_encoder_path,
                ip_ckpt=ip_ckpt,
                device=device,
                torch_dtype=dtype
            )
            images = ip_model.generate(
                face_image=face_image_pil,
                faceid_embeds=faceid_embeds,
                prompt=args.prompt,
                negative_prompt=getattr(args, 'negative_prompt', DEFAULT_NEGATIVE_PROMPT),
                scale=face_scale,
                s_scale=1.0,
                shortcut=True,
                num_samples=1,
                width=args.width,
                height=args.height,
                num_inference_steps=args.steps,
                guidance_scale=args.guidance,
                seed=args.seed
            )
            result = images[0]
        else:
            lora_path = Path("models/ip-adapter-faceid/ip-adapter-faceid_sdxl_lora.safetensors")
            if lora_path.exists():
                pipe.load_lora_weights(str(lora_path))
                pipe.fuse_lora()
            ip_ckpt = "models/ip-adapter-faceid/ip-adapter-faceid_sdxl.bin"
            print("Activating IP-Adapter-FaceID identity locking...")
            ip_model = IPAdapterFaceIDXL(
                pipe,
                ip_ckpt=ip_ckpt,
                device=device,
                torch_dtype=dtype
            )
            images = ip_model.generate(
                faceid_embeds=faceid_embeds,
                prompt=args.prompt,
                negative_prompt=getattr(args, 'negative_prompt', DEFAULT_NEGATIVE_PROMPT),
                scale=face_scale,
                num_samples=1,
                width=args.width,
                height=args.height,
                num_inference_steps=args.steps,
                guidance_scale=args.guidance,
                seed=args.seed
            )
            result = images[0]
    else:
        result=image_call(args,torch,pipe)
    output=Path(args.output).expanduser().resolve()
    output.parent.mkdir(parents=True,exist_ok=True)
    result.save(output)
    print(f'Saved {output}')
    _maybe_register_cli_output(args, output, 'image', args.prompt, 'image')


def download_model(args):
    if not args.yes:
        raise ValueError('Downloads may use tens of GB of disk and bandwidth. Pass --yes to confirm.')
    from huggingface_hub import snapshot_download
    repo=REGISTRY[args.model]['hf']
    local=local_model(args.model)
    local.mkdir(parents=True, exist_ok=True)
    print(f'Downloading public weights {repo} to {local} (no paid API required).')
    options={}
    if args.model in {'flux2-klein-4b','flux2-klein-base-4b','z-image-turbo'}:
        # These repos also publish alternate all-in-one checkpoint files. The CLI
        # uses Diffusers subfolders, not those extra copies of the same weights.
        options['allow_patterns']=['model_index.json','scheduler/**','text_encoder/**',
            'text_encoder_2/**','tokenizer/**','tokenizer_2/**','transformer/**',
            'vae/**','*.json']
    elif args.model in {'cyberrealistic-xl', 'juggernaut-xl-v10'}:
        options['allow_patterns']=['*.safetensors','*.md']
    elif args.model == 'pony-diffusion-v6-xl':
        options['allow_patterns']=['*.safetensors','*.json','*.md']
    elif args.model == 'svd-xt':
        options['allow_patterns']=['unet/config.json','unet/diffusion_pytorch_model.fp16.safetensors','vae/config.json','vae/diffusion_pytorch_model.fp16.safetensors','image_encoder/config.json','image_encoder/model.fp16.safetensors','scheduler/**','feature_extractor/**','model_index.json']
    elif args.model == 'wan21-t2v-1.3b':
        options['allow_patterns']=['transformer/**','vae/**','text_encoder/**','tokenizer/**','scheduler/**','model_index.json','*.json']
    snapshot_download(repo_id=repo, local_dir=str(local), **options)
    print('Downloaded. Check model card and dependency licenses before commercial use.')


def make_video_svd(args):
    """Image-to-Video generation using Stable Video Diffusion XT (unrestricted visual motion)."""
    import torch
    from diffusers import StableVideoDiffusionPipeline
    from diffusers.utils import export_to_video, load_image

    if torch.cuda.is_available():
        device = 'cuda'
    elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
        device = 'mps'
    else:
        raise RuntimeError('Video generation requires a supported GPU (CUDA or Apple Silicon Metal/MPS).')

    local = local_model('svd-xt')
    source = str(local) if local.is_dir() and any(local.iterdir()) else REGISTRY['svd-xt']['hf']
    dtype = torch.float16

    print(f'Loading SVD-XT from {source} on {device}...')
    try:
        pipe = StableVideoDiffusionPipeline.from_pretrained(source, torch_dtype=dtype, variant='fp16', local_files_only=getattr(args, 'offline', False))
    except Exception:
        pipe = StableVideoDiffusionPipeline.from_pretrained(source, torch_dtype=dtype, local_files_only=getattr(args, 'offline', False))
    pipe.to(device)

    if device == 'mps':
        class SafeMPSAttnProcessor:
            def __call__(self, attn, hidden_states, encoder_hidden_states=None, attention_mask=None, **kwargs):
                residual = hidden_states
                input_ndim = hidden_states.ndim
                if input_ndim == 4:
                    batch_size, channel, height, width = hidden_states.shape
                    hidden_states = hidden_states.view(batch_size, channel, height * width).transpose(1, 2)
                batch_size, sequence_length, _ = hidden_states.shape
                if encoder_hidden_states is None:
                    encoder_hidden_states = hidden_states
                query = attn.to_q(hidden_states)
                key = attn.to_k(encoder_hidden_states)
                value = attn.to_v(encoder_hidden_states)
                inner_dim = key.shape[-1]
                head_dim = inner_dim // attn.heads
                query = query.view(batch_size, -1, attn.heads, head_dim).transpose(1, 2)
                key = key.view(batch_size, -1, attn.heads, head_dim).transpose(1, 2)
                value = value.view(batch_size, -1, attn.heads, head_dim).transpose(1, 2)
                scale = 1.0 / (head_dim ** 0.5)
                scores = torch.matmul(query.float() * scale, key.float().transpose(-1, -2))
                probs = torch.softmax(scores, dim=-1).to(value.dtype)
                hidden_states = torch.matmul(probs, value)
                hidden_states = hidden_states.transpose(1, 2).reshape(batch_size, -1, attn.heads * head_dim)
                hidden_states = hidden_states.to(query.dtype)
                hidden_states = attn.to_out[0](hidden_states)
                hidden_states = attn.to_out[1](hidden_states)
                if input_ndim == 4:
                    hidden_states = hidden_states.transpose(-1, -2).reshape(batch_size, channel, height, width)
                if attn.residual_connection:
                    hidden_states = hidden_states + residual
                hidden_states = hidden_states / attn.rescale_output_factor
                return hidden_states

        pipe.unet.set_attn_processor(SafeMPSAttnProcessor())
        old_decode = pipe.decode_latents
        pipe.decode_latents = lambda latents, num_frames, decode_chunk_size=14: old_decode(latents.to(pipe.vae.dtype), num_frames, decode_chunk_size)

    if not args.reference:
        raise ValueError('SVD-XT requires a reference master image (--reference path/to/image.png)')
    ref_img = load_image(str(verify_image(args.reference)))

    width = getattr(args, 'width', 512 if device == 'mps' else 1024)
    height = getattr(args, 'height', 288 if device == 'mps' else 576)
    ref_img = ref_img.resize((width, height))

    motion_bucket = getattr(args, 'motion_bucket', 127)
    fps = getattr(args, 'fps', 8)
    steps = getattr(args, 'steps', 14 if device == 'mps' else 25)
    num_frames = getattr(args, 'num_frames', 14 if device == 'mps' else 25)
    seed = getattr(args, 'seed', 42)
    generator = torch.Generator(device='cpu').manual_seed(seed)

    print(f'Generating motion from reference image ({steps} steps, {num_frames} frames, {width}x{height}, motion_bucket={motion_bucket})...')
    frames = pipe(
        ref_img,
        height=height,
        width=width,
        num_frames=num_frames,
        decode_chunk_size=2,
        generator=generator,
        motion_bucket_id=motion_bucket,
        num_inference_steps=steps,
    ).frames[0]

    out = Path(args.output).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    export_to_video(frames, str(out), fps=fps)
    print(f'Saved SVD-XT video: {out}')
    return str(out)


def make_video_liveportrait(args):
    """Zero-distortion photorealistic face & glamour portrait animation using LivePortrait."""
    lp_dir = ROOT / 'LivePortrait'
    if not lp_dir.is_dir():
        raise FileNotFoundError(f"LivePortrait repository not found at {lp_dir}")

    source = verify_image(args.reference) if getattr(args, 'reference', None) else OUTPUT_ROOT / 'portrait.png'
    if not Path(source).is_file():
        raise FileNotFoundError(f"Source reference image not found: {source}")

    driving_arg = getattr(args, 'driving', None) or 'd0.mp4'
    driving_path = Path(driving_arg)
    if not driving_path.is_absolute():
        if (lp_dir / driving_path).exists():
            driving_path = lp_dir / driving_path
        elif (lp_dir / 'assets' / 'examples' / 'driving' / driving_path).exists():
            driving_path = lp_dir / 'assets' / 'examples' / 'driving' / driving_path
        elif (lp_dir / 'assets' / 'examples' / 'driving' / f'{driving_arg}.mp4').exists():
            driving_path = lp_dir / 'assets' / 'examples' / 'driving' / f'{driving_arg}.mp4'
        elif (lp_dir / 'assets' / 'examples' / 'driving' / f'{driving_arg}.pkl').exists():
            driving_path = lp_dir / 'assets' / 'examples' / 'driving' / f'{driving_arg}.pkl'
        else:
            driving_path = lp_dir / 'assets' / 'examples' / 'driving' / 'd0.mp4'

    out_file = Path(args.output).expanduser().resolve()
    out_dir = out_file.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    venv_bin = str(ROOT / '.venv' / 'bin')
    env["PATH"] = venv_bin + os.pathsep + env.get("PATH", "")
    env["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"

    cmd = [
        sys.executable,
        str(lp_dir / 'inference.py'),
        '-s', str(source),
        '-d', str(driving_path),
        '-o', str(out_dir),
    ]
    print(f"Running LivePortrait: source={Path(source).name}, motion={driving_path.name}...")
    subprocess.run(cmd, check=True, cwd=str(lp_dir), env=env)

    expected = out_dir / f"{Path(source).stem}--{driving_path.stem}.mp4"
    if expected.exists() and str(expected) != str(out_file):
        shutil.copy2(expected, out_file)
    print(f"Saved LivePortrait video: {out_file}")
    return str(out_file)



def make_video_wan21(args):
    """Text-to-Video generation using Wan 2.1 1.3B."""
    import torch
    from diffusers import WanPipeline
    from diffusers.utils import export_to_video

    if torch.cuda.is_available():
        device = 'cuda'
    elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
        device = 'mps'
    else:
        raise RuntimeError('Video generation requires a supported GPU (CUDA or Apple Silicon Metal/MPS).')

    local = local_model('wan21-t2v-1.3b')
    source = str(local) if local.is_dir() and any(local.iterdir()) else REGISTRY['wan21-t2v-1.3b']['hf']
    dtype = torch.bfloat16 if device == 'cuda' else torch.float16

    print(f'Loading Wan 2.1 1.3B from {source} on {device}...')
    pipe = WanPipeline.from_pretrained(source, torch_dtype=dtype, local_files_only=getattr(args, 'offline', False))
    pipe.to(device)

    prompt = args.prompt
    if not prompt:
        raise ValueError('Wan 2.1 requires a text prompt (--prompt "...")')
    negative_prompt = getattr(args, 'negative_prompt', 'Bright tones, overexposed, static, blurred details, subtitles, style, artwork, painting, picture, still, overall grayish, worst quality, low quality, JPEG artifacts')
    seed = getattr(args, 'seed', 42)
    generator = torch.Generator(device='cpu').manual_seed(seed)
    steps = getattr(args, 'steps', 30)

    print(f"Generating Wan 2.1 video: '{prompt[:60]}...'")
    output = pipe(
        prompt=prompt,
        negative_prompt=negative_prompt,
        height=480,
        width=832,
        num_frames=81,
        num_inference_steps=steps,
        generator=generator,
    ).frames[0]

    out = Path(args.output).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    export_to_video(output, str(out), fps=16)
    print(f'Saved Wan 2.1 video: {out}')
    return str(out)


def video_command(args):
    """Build official Wan2.2 CLI invocation. Uses its own python environment."""
    if args.mode != 'wan22-ti2v-5b':
        raise ValueError('Supported video backend: wan22-ti2v-5b')
    script=ROOT / 'external' / 'Wan22' / 'generate.py'
    weights=local_model(args.mode)
    if not script.is_file():
        raise FileNotFoundError('Clone Wan22 first with scripts/clone-github-repos.ps1 -Names Wan22')
    if not weights.is_dir() or not any(weights.iterdir()):
        raise FileNotFoundError('Download wan22-ti2v-5b weights first with download --model wan22-ti2v-5b --yes')
    exe=str(Path(args.python).expanduser().resolve()) if args.python else sys.executable
    out=Path(args.output).expanduser().resolve()
    out.parent.mkdir(parents=True,exist_ok=True)
    cmd=[exe,str(script),'--task','ti2v-5B','--size',args.size,
         '--ckpt_dir',str(weights),'--offload_model','True','--convert_model_dtype','--t5_cpu',
         '--prompt',args.prompt,'--save_file',str(out)]
    if args.reference: cmd.extend(['--image',str(verify_image(args.reference))])
    return cmd


def video(args):
    output_path = None
    if args.mode == 'liveportrait':
        output_path = make_video_liveportrait(args)
    elif args.mode == 'svd-xt':
        output_path = make_video_svd(args)
    elif args.mode == 'wan21-t2v-1.3b':
        output_path = make_video_wan21(args)
    elif args.mode == 'wan22-ti2v-5b':
        cmd=video_command(args)
        print('Running official Wan2.2 CLI with local weights, no Dashscope prompt extension.')
        if args.dry_run:
            print(json.dumps(cmd,indent=2))
        else:
            subprocess.run(cmd,check=True,cwd=ROOT/'external'/'Wan22')
            output_path = str(Path(args.output).resolve())
            print(f'Saved video: {output_path}')
    else:
        raise ValueError(f"Unknown video mode: {args.mode}")
    if output_path:
        _maybe_register_cli_output(args, output_path, 'video', getattr(args, 'prompt', ''), 'video')
    return output_path


def voice(args):
    import numpy as np
    import soundfile as sf
    from kokoro import KPipeline
    pipeline=KPipeline(lang_code=args.lang)
    parts=[]
    for _, _, audio in pipeline(args.text, voice=args.voice):
        parts.append(np.asarray(audio))
    if not parts: raise RuntimeError('Kokoro returned no audio')
    dest=Path(args.output).expanduser().resolve()
    dest.parent.mkdir(parents=True,exist_ok=True)
    sf.write(dest,np.concatenate(parts),24000)
    print(f'Saved WAV: {dest}')
    _maybe_register_cli_output(args, dest, 'audio', args.text, 'voice')
    return str(dest)


def mux(args):
    if not shutil.which('ffmpeg'):
        raise RuntimeError('FFmpeg not installed or not on PATH (free local tool)')
    video_file=Path(args.video).resolve()
    audio_file=Path(args.audio).resolve()
    if not video_file.is_file() or not audio_file.is_file():
        raise FileNotFoundError('Provide existing local video and audio files')
    output=Path(args.output).resolve();output.parent.mkdir(parents=True,exist_ok=True)
    cmd=['ffmpeg','-y','-i',str(video_file),'-i',str(audio_file),'-map','0:v:0','-map','1:a:0','-c:v','copy','-c:a','aac','-shortest',str(output)]
    subprocess.run(cmd,check=True)
    print(f'Saved {output}')
    _maybe_register_cli_output(args, output, 'video', getattr(args, 'prompt', 'Assembled video with narration'), 'mux')
    return str(output)


def pipeline(args):
    """Run the local image, video, optional voice and mux stages."""
    master = Path(args.master).expanduser().resolve()
    video_file = Path(args.video).expanduser().resolve()
    audio_file = Path(args.audio).expanduser().resolve()
    final_file = Path(args.output).expanduser().resolve()
    disclosure_file = final_file.with_suffix(final_file.suffix + '.disclosure.txt')
    video_prompt = args.video_prompt or args.prompt

    plan = {
        'image': {'model': args.model, 'output': str(master), 'prompt': args.prompt},
        'video': {'mode': args.mode, 'output': str(video_file), 'reference': str(master), 'prompt': video_prompt},
        'voice': {'enabled': bool(args.narration), 'output': str(audio_file)},
        'mux': {'enabled': bool(args.narration), 'output': str(final_file)},
        'inference': 'local-only',
    }
    if args.dry_run:
        print(json.dumps(plan, indent=2))
        return

    image_args = SimpleNamespace(
        model=args.model, prompt=args.prompt, reference=args.reference,
        width=args.width, height=args.height, seed=args.seed,
        steps=args.steps, guidance=args.guidance, cpu_offload=args.cpu_offload,
        offline=args.offline, output=str(master), negative_prompt=args.negative_prompt,
        persona_id=getattr(args, 'persona_id', None), disclosure=getattr(args, 'disclosure', AI_DISCLOSURE),
    )
    make_image(image_args)

    video_args = SimpleNamespace(
        mode=args.mode, python=args.python, output=str(video_file), size=args.size,
        prompt=video_prompt, reference=str(master), dry_run=False,
        persona_id=getattr(args, 'persona_id', None), disclosure=getattr(args, 'disclosure', AI_DISCLOSURE),
    )
    video(video_args)

    if args.narration:
        voice(SimpleNamespace(text=args.narration, voice=args.voice, lang=args.lang, output=str(audio_file),
                              persona_id=getattr(args, 'persona_id', None), disclosure=getattr(args, 'disclosure', AI_DISCLOSURE)))
        mux(SimpleNamespace(video=str(video_file), audio=str(audio_file), output=str(final_file),
                            persona_id=getattr(args, 'persona_id', None), disclosure=getattr(args, 'disclosure', AI_DISCLOSURE),
                            prompt=video_prompt))
    else:
        # Keep the advertised --output contract even when the optional audio
        # stage is skipped. This gives review/import one stable final path.
        if final_file != video_file:
            final_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(video_file, final_file)

    disclosure_file.parent.mkdir(parents=True, exist_ok=True)
    disclosure_file.write_text(
        getattr(args, 'disclosure', AI_DISCLOSURE) + '\n',
        encoding='utf8',
    )
    print(f'Local pipeline complete: {final_file}')
    print(f'Disclosure sidecar: {disclosure_file}')


def doctor():
    print('Open-source, self-hosted AI Influencer Studio diagnostic')
    print('Python:',sys.version.split()[0],'Platform:',sys.platform)
    print('Git:',shutil.which('git') or 'NOT INSTALLED')
    print('FFmpeg:',shutil.which('ffmpeg') or 'NOT INSTALLED')
    try:
        import torch
        print('PyTorch:',torch.__version__)
        if torch.cuda.is_available():
            props=torch.cuda.get_device_properties(0)
            print('CUDA:',props.name,'VRAM (GiB):',round(props.total_memory/(1024**3),1))
        elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            print('Apple Silicon GPU (Metal/MPS): ready')
        else: print('CUDA/Metal: unavailable; GPU render not ready')
    except ImportError: print('PyTorch: not installed in this environment')
    print('Approved models:')
    for key,item in REGISTRY.items():
        directory=local_model(key)
        print(' ',key,'-',item['license'],'-','downloaded' if directory.is_dir() and any(directory.iterdir()) else 'not downloaded')
    print('Model weights are NOT included with source code and require free downloads.')


def cli(argv=None):
    parser=argparse.ArgumentParser(description='Free local generation commands; no paid inference API')
    sub=parser.add_subparsers(dest='cmd',required=True)
    sub.add_parser('doctor')
    dl=sub.add_parser('download');dl.add_argument('--model',required=True,choices=REGISTRY.keys());dl.add_argument('--yes',action='store_true')
    im=sub.add_parser('image');im.add_argument('--model',choices=['flux2-klein-4b','z-image-turbo','pony-diffusion-v6-xl','cyberrealistic-xl','juggernaut-xl-v10'],default='flux2-klein-4b');im.add_argument('--prompt',required=True)
    im.add_argument('--negative-prompt',default=DEFAULT_NEGATIVE_PROMPT)
    im.add_argument('--reference',action='append',help='Repeat for each master reference (FLUX.2 only)')
    im.add_argument('--face-ref',help='Master face reference image for IP-Adapter FaceID consistency (SDXL)')
    im.add_argument('--faceid-scale',type=float,default=0.75,help='Face identity influence (0.1 to 1.0, default 0.75)')
    im.add_argument('--faceid-plus',action='store_true',default=True,help='Use FaceID-PlusV2 dual-embedding (default: True)')
    im.add_argument('--width',type=int,default=768);im.add_argument('--height',type=int,default=1152)
    im.add_argument('--seed',type=int,default=42);im.add_argument('--steps',type=int,default=4);im.add_argument('--guidance',type=float,default=1.0)
    im.add_argument('--cpu-offload',action='store_true');im.add_argument('--offline',action='store_true')
    im.add_argument('--persona-id', help='Optional canonical Persona ID; register the output after generation')
    im.add_argument('--output',default=str(OUTPUT_ROOT/'portrait.png'))
    vid=sub.add_parser('video')
    vid.add_argument('--mode',choices=['liveportrait','svd-xt','wan21-t2v-1.3b','wan22-ti2v-5b'],default='liveportrait')
    vid.add_argument('--prompt',default='',help='Text prompt (required for Wan; optional for SVD/LivePortrait)')
    vid.add_argument('--reference',help='Master reference image (required for SVD/LivePortrait; optional for Wan)')
    vid.add_argument('--driving',default='d0',help='LivePortrait driving motion (d0, d11, wink, shy, laugh, or path to mp4/pkl)')
    vid.add_argument('--motion-bucket',type=int,default=127,help='SVD motion bucket (1-255; higher=more motion)')
    vid.add_argument('--fps',type=int,default=25,help='Output video frame rate')
    vid.add_argument('--steps',type=int,default=25,help='Denoising inference steps')
    vid.add_argument('--seed',type=int,default=42)
    vid.add_argument('--offline',action='store_true')
    vid.add_argument('--size',choices=['1280*704','704*1280','1024*576','576*1024'],default='1024*576')
    vid.add_argument('--python',help='Python executable in the Wan2.2 separate venv')
    vid.add_argument('--persona-id', help='Optional canonical Persona ID; register the output after generation')
    vid.add_argument('--output',default=str(OUTPUT_ROOT/'glamour_motion.mp4'))
    vid.add_argument('--dry-run',action='store_true')
    vc=sub.add_parser('voice');vc.add_argument('--text',required=True);vc.add_argument('--voice',default='af_heart')
    vc.add_argument('--lang',default='a');vc.add_argument('--persona-id', help='Optional canonical Persona ID; register the output after generation');vc.add_argument('--output',default=str(OUTPUT_ROOT/'voice.wav'))
    mx=sub.add_parser('mux');mx.add_argument('--video',required=True);mx.add_argument('--audio',required=True);mx.add_argument('--output',default=str(OUTPUT_ROOT/'narrated_reel.mp4'))
    mx.add_argument('--persona-id', help='Optional canonical Persona ID; register the assembled output after muxing')
    rg=sub.add_parser('register', help='Register an existing local output in the canonical Asset store')
    rg.add_argument('--persona-id', required=True, help='Canonical Persona ID; legacy persona IDs are not accepted')
    rg.add_argument('--file', required=True, help='Existing local image, video, or audio output')
    rg.add_argument('--kind', choices=['image', 'video', 'audio'], required=True)
    rg.add_argument('--prompt', required=True, help='Prompt or creative direction used for the output')
    rg.add_argument('--disclosure', default=AI_DISCLOSURE)
    rg.add_argument('--rights-confirmed', action='store_true', help='Explicitly confirm rights for this imported output')
    pp=sub.add_parser('pipeline', help='Run local image, video, optional voice and mux stages')
    pp.add_argument('--prompt', required=True, help='Master-image prompt for the fictional adult character')
    pp.add_argument('--negative-prompt', default=DEFAULT_NEGATIVE_PROMPT)
    pp.add_argument('--video-prompt', help='Motion prompt; defaults to the image prompt')
    pp.add_argument('--narration', help='Optional narration text; omit to skip Kokoro and muxing')
    pp.add_argument('--voice', default='af_heart'); pp.add_argument('--lang', default='a')
    pp.add_argument('--model', choices=['cyberrealistic-xl', 'juggernaut-xl-v10', 'pony-diffusion-v6-xl', 'flux2-klein-4b', 'z-image-turbo'], default='cyberrealistic-xl')
    pp.add_argument('--reference', action='append', help='Optional existing references for master-image editing')
    pp.add_argument('--face-ref', help='Master face reference image for IP-Adapter FaceID consistency')
    pp.add_argument('--faceid-scale', type=float, default=0.75, help='Face identity influence (0.1 to 1.0, default 0.75)')
    pp.add_argument('--faceid-plus', action='store_true', default=True, help='Use FaceID-PlusV2 dual-embedding (default: True)')
    pp.add_argument('--width', type=int, default=768); pp.add_argument('--height', type=int, default=1152)
    pp.add_argument('--seed', type=int, default=42); pp.add_argument('--steps', type=int, default=28)
    pp.add_argument('--guidance', type=float, default=5.0); pp.add_argument('--cpu-offload', action='store_true')
    pp.add_argument('--offline', action='store_true')
    pp.add_argument('--mode', choices=['liveportrait', 'svd-xt', 'wan21-t2v-1.3b', 'wan22-ti2v-5b'], default='liveportrait')
    pp.add_argument('--driving', default='d0', help='LivePortrait driving motion (d0, d11, wink, shy, laugh, or path)')
    pp.add_argument('--size', choices=['1280*704', '704*1280', '1024*576'], default='1024*576')
    pp.add_argument('--python', help='Python executable in the separate Wan2.2 environment')
    pp.add_argument('--master', default=str(OUTPUT_ROOT/'master.png'))
    pp.add_argument('--video', default=str(OUTPUT_ROOT/'reel.mp4'))
    pp.add_argument('--audio', default=str(OUTPUT_ROOT/'narration.wav'))
    pp.add_argument('--output', default=str(OUTPUT_ROOT/'reel_with_voice.mp4'))
    pp.add_argument('--disclosure', default=AI_DISCLOSURE)
    pp.add_argument('--persona-id', help='Optional canonical Persona ID; register generated outputs after each stage')
    pp.add_argument('--dry-run', action='store_true')
    br = sub.add_parser('brief', help='Validate and run a ChatGPT-authored generation brief')
    br.add_argument('--file', required=True, help='Path to generation brief JSON')
    br.add_argument('--python', help='Python executable in the separate Wan2.2 environment')
    br.add_argument('--cpu-offload', action='store_true')
    br.add_argument('--offline', action='store_true')
    br.add_argument('--dry-run', action='store_true', help='Validate and print the normalized brief without rendering')
    args=parser.parse_args(argv)
    try:
        return {'doctor':doctor,'download':lambda:download_model(args),'image':lambda:make_image(args),
                'video':lambda:video(args),'voice':lambda:voice(args),'mux':lambda:mux(args),
                'register':lambda:register_output(args),'pipeline':lambda:pipeline(args),'brief':lambda:run_brief(args)}[args.cmd]()
    except (RuntimeError,ValueError,FileNotFoundError) as e:
        parser.exit(2,f'Error: {e}\n')

if __name__=='__main__': cli()
