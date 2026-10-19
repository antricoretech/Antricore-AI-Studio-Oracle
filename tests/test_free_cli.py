from pathlib import Path
from types import SimpleNamespace
import pytest
from studio import free_cli as fc

def test_registry_only_freely_available_models():
    assert fc.REGISTRY
    assert all(r['license'] in {'Apache-2.0', 'Fair AI Public License 1.0-SD', 'CreativeML OpenRAIL++-M', 'Stability AI Community License'} for r in fc.REGISTRY.values())
    assert 'flux2-klein-9b' not in fc.REGISTRY
    assert 'inswapper_128' not in fc.REGISTRY

def test_requires_explicit_large_download_confirmation():
    with pytest.raises(ValueError,match='--yes'):
        fc.download_model(SimpleNamespace(model='flux2-klein-4b',yes=False))

def test_reference_requires_supported_model():
    args=SimpleNamespace(model='z-image-turbo',prompt='abc',height=512,width=512,steps=4,guidance=1.0,seed=9,reference=['anything.png'])
    with pytest.raises(ValueError,match='requires flux2-klein-4b'):
        fc.image_call(args,SimpleNamespace(Generator=lambda device:SimpleNamespace(manual_seed=lambda seed:None)),lambda **_:None)

def test_video_command_clones_required(tmp_path,monkeypatch):
    monkeypatch.setattr(fc,'ROOT',tmp_path)
    args=SimpleNamespace(mode='wan22-ti2v-5b',python=None,output=str(tmp_path/'out.mp4'),size='704*1280',prompt='hello',reference=None)
    with pytest.raises(FileNotFoundError,match='Clone Wan22'):
        fc.video_command(args)

def test_output_and_approved_catalog():
    assert fc.local_model('wan22-ti2v-5b').name=='wan22-ti2v-5b'
    with pytest.raises(ValueError,match='Unapproved'):
        fc.local_model('flux1-dev')

def test_pipeline_dry_run_is_local_only(tmp_path, capsys):
    args = SimpleNamespace(
        model='flux2-klein-4b', prompt='fictional adult character', video_prompt='gentle motion',
        narration=None, voice='af_heart', lang='a', reference=None, width=768, height=1152,
        seed=42, steps=4, guidance=1.0, cpu_offload=True, offline=True,
        mode='wan22-ti2v-5b', size='704*1280', python=None,
        master=str(tmp_path/'master.png'), video=str(tmp_path/'reel.mp4'),
        audio=str(tmp_path/'voice.wav'), output=str(tmp_path/'final.mp4'), dry_run=True,
    )
    fc.pipeline(args)
    output = capsys.readouterr().out
    assert 'local-only' in output
    assert 'fictional adult character' in output

def test_generation_brief_dry_run(tmp_path, capsys):
    args = SimpleNamespace(file=str(Path('config/generation_brief.example.json')), dry_run=True,
                           cpu_offload=False, offline=True, python=None)
    fc.run_brief(args)
    output = capsys.readouterr().out
    assert 'Mira Vale' in output
    assert 'wan22-ti2v-5b' in output


def test_generation_brief_identity_capsule_is_shared_with_both_render_stages():
    from studio.brief import parse_brief_file
    brief = parse_brief_file('config/generation_brief.example.json')
    identity = fc.identity_prompt_from_brief(brief)
    assert 'Mira Vale' in identity
    assert 'hazel' in identity.lower()
    assert 'consistency' in identity.lower() or 'same facial geometry' in identity.lower()
