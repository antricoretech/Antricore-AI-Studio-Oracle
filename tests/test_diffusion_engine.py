import pytest


def test_diffusion_engine_rejects_registered_model_without_runtime_support():
    import studio.diffusion_engine as diffusion_engine

    with pytest.raises(diffusion_engine.ModelConfigurationError, match='not supported'):
        diffusion_engine.get_pipeline('flux2-klein-4b')


def test_diffusion_engine_does_not_scan_alternate_checkpoints(monkeypatch, tmp_path):
    import studio.diffusion_engine as diffusion_engine

    alternate = tmp_path / 'models' / 'some-other-model'
    alternate.mkdir(parents=True)
    (alternate / 'unrelated.safetensors').write_bytes(b'not a checkpoint')
    monkeypatch.setattr(diffusion_engine, 'ROOT_DIR', tmp_path)

    with pytest.raises(FileNotFoundError, match='juggernaut-xl-v10'):
        diffusion_engine.get_pipeline('juggernaut-xl-v10')
