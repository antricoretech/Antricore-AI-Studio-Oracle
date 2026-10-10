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
    if args.model not in {'flux2-klein-4b','z-image-turbo'}:
        raise ValueError('Image CLI supports FLUX.2 Klein 4B and Z-Image Turbo only')
    import torch
    from diffusers import DiffusionPipeline
    if not torch.cuda.is_available():
        raise RuntimeError('Image generation requires a supported GPU for this preset. Use doctor to check.')
    local=local_model(args.model)
    if args.offline and not local.is_dir():
        raise RuntimeError(f'Weights absent: {local}. Download the model before using --offline.')
    source=str(local) if local.is_dir() and any(local.iterdir()) else REGISTRY[args.model]['hf']
    if args.offline: os.environ['HF_HUB_OFFLINE']='1'
    print(f'Loading {args.model} from {source}; may require substantial VRAM and disk space')
    pipe=DiffusionPipeline.from_pretrained(source, torch_dtype=torch.bfloat16, local_files_only=args.offline)
    if args.cpu_offload:
        pipe.enable_model_cpu_offload()
    else:
        pipe.to('cuda')
    if args.model == 'z-image-turbo':
        args.guidance=0.0  # distilled model: no CFG recommended
        if args.steps == 4: args.steps=9
    result=image_call(args,torch,pipe)
    output=Path(args.output).expanduser().resolve()
    output.parent.mkdir(parents=True,exist_ok=True)
    result.save(output)
    print(f'Saved {output}')


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
    snapshot_download(repo_id=repo, local_dir=str(local), **options)
    print('Downloaded. Check model card and dependency licenses before commercial use.')


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
    cmd=video_command(args)
    print('Running official Wan2.2 CLI with local weights, no Dashscope prompt extension.')
    if args.dry_run:
        print(json.dumps(cmd,indent=2))
    else:
        subprocess.run(cmd,check=True,cwd=ROOT/'external'/'Wan22')
        print(f'Saved video: {Path(args.output).resolve()}')


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
    )
    make_image(image_args)

    video_args = SimpleNamespace(
        mode=args.mode, python=args.python, output=str(video_file), size=args.size,
        prompt=video_prompt, reference=str(master), dry_run=False,
    )
    video(video_args)

    if args.narration:
        voice(SimpleNamespace(text=args.narration, voice=args.voice, lang=args.lang, output=str(audio_file)))
        mux(SimpleNamespace(video=str(video_file), audio=str(audio_file), output=str(final_file)))
    else:
        # Keep the advertised --output contract even when the optional audio
        # stage is skipped. This gives review/import one stable final path.
        if final_file != video_file:
            final_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(video_file, final_file)

    disclosure_file.parent.mkdir(parents=True, exist_ok=True)
    disclosure_file.write_text(
        getattr(args, 'disclosure', 'Fictional adult character. AI-generated synthetic media.') + '\n',
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
        else: print('CUDA: unavailable; FLUX/Wan GPU render not ready')
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
    im=sub.add_parser('image');im.add_argument('--model',choices=['flux2-klein-4b','z-image-turbo'],default='flux2-klein-4b');im.add_argument('--prompt',required=True)
    im.add_argument('--negative-prompt',default='blurry, deformed, extra fingers, duplicate person, watermark, typography, logo, child, teenager, minor, nudity, exposed genitals, explicit sexual activity, lingerie, real-person likeness')
    im.add_argument('--reference',action='append',help='Repeat for each master reference (FLUX.2 only)')
    im.add_argument('--width',type=int,default=768);im.add_argument('--height',type=int,default=1152)
    im.add_argument('--seed',type=int,default=42);im.add_argument('--steps',type=int,default=4);im.add_argument('--guidance',type=float,default=1.0)
    im.add_argument('--cpu-offload',action='store_true');im.add_argument('--offline',action='store_true')
    im.add_argument('--output',default=str(OUTPUT_ROOT/'portrait.png'))
    vid=sub.add_parser('video');vid.add_argument('--mode',choices=['wan22-ti2v-5b'],default='wan22-ti2v-5b')
    vid.add_argument('--prompt',required=True);vid.add_argument('--reference');vid.add_argument('--size',choices=['1280*704','704*1280'],default='704*1280')
    vid.add_argument('--python',help='Python executable in the Wan2.2 separate venv');vid.add_argument('--output',default=str(OUTPUT_ROOT/'reel.mp4'))
    vid.add_argument('--dry-run',action='store_true')
    vc=sub.add_parser('voice');vc.add_argument('--text',required=True);vc.add_argument('--voice',default='af_heart')
    vc.add_argument('--lang',default='a');vc.add_argument('--output',default=str(OUTPUT_ROOT/'voice.wav'))
    mx=sub.add_parser('mux');mx.add_argument('--video',required=True);mx.add_argument('--audio',required=True);mx.add_argument('--output',default=str(OUTPUT_ROOT/'narrated_reel.mp4'))
    pp=sub.add_parser('pipeline', help='Run local image, video, optional voice and mux stages')
    pp.add_argument('--prompt', required=True, help='Master-image prompt for the fictional adult character')
    pp.add_argument('--negative-prompt', default='blurry, deformed, extra fingers, duplicate person, watermark, typography, logo, child, teenager, minor, nudity, exposed genitals, explicit sexual activity, lingerie, real-person likeness')
    pp.add_argument('--video-prompt', help='Motion prompt; defaults to the image prompt')
    pp.add_argument('--narration', help='Optional narration text; omit to skip Kokoro and muxing')
    pp.add_argument('--voice', default='af_heart'); pp.add_argument('--lang', default='a')
    pp.add_argument('--model', choices=['flux2-klein-4b', 'z-image-turbo'], default='flux2-klein-4b')
    pp.add_argument('--reference', action='append', help='Optional existing references for master-image editing')
    pp.add_argument('--width', type=int, default=768); pp.add_argument('--height', type=int, default=1152)
    pp.add_argument('--seed', type=int, default=42); pp.add_argument('--steps', type=int, default=4)
    pp.add_argument('--guidance', type=float, default=1.0); pp.add_argument('--cpu-offload', action='store_true')
    pp.add_argument('--offline', action='store_true')
    pp.add_argument('--mode', choices=['wan22-ti2v-5b'], default='wan22-ti2v-5b')
    pp.add_argument('--size', choices=['1280*704', '704*1280'], default='704*1280')
    pp.add_argument('--python', help='Python executable in the separate Wan2.2 environment')
    pp.add_argument('--master', default=str(OUTPUT_ROOT/'master.png'))
    pp.add_argument('--video', default=str(OUTPUT_ROOT/'reel.mp4'))
    pp.add_argument('--audio', default=str(OUTPUT_ROOT/'narration.wav'))
    pp.add_argument('--output', default=str(OUTPUT_ROOT/'reel_with_voice.mp4'))
    pp.add_argument('--disclosure', default='Fictional adult character. AI-generated synthetic media.')
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
                'pipeline':lambda:pipeline(args),'brief':lambda:run_brief(args)}[args.cmd]()
    except (RuntimeError,ValueError,FileNotFoundError) as e:
        parser.exit(2,f'Error: {e}\n')

if __name__=='__main__': cli()
