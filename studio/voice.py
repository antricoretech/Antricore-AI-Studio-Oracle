"""Optional Kokoro TTS adapter. Not installed in the base requirements."""
from pathlib import Path

def synthesize(text: str, voice: str, destination: Path):
    try:
        import numpy as np
        import soundfile as sf
        from kokoro import KPipeline
    except ImportError as exc:
        raise RuntimeError("Voice not installed. Run: pip install -r requirements-voice.txt and install eSpeak NG as required.") from exc
    lang = "b" if voice.startswith("b") else "a"
    pipeline = KPipeline(lang_code=lang)
    chunks = [audio for _graphemes, _phonemes, audio in pipeline(text, voice=voice, speed=1)]
    if not chunks:
        raise RuntimeError("Kokoro returned no audio")
    sf.write(str(destination), np.concatenate(chunks), 24000)
