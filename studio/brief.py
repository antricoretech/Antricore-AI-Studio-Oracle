"""Shared JSON contract for ChatGPT-authored local generation briefs.

The brief is intentionally model-specific only at the execution boundary. ChatGPT
can write the creative direction, while the dashboard and CLI validate the safety
and shape of the inputs before anything is queued.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class BriefModel(BaseModel):
    """Allow ChatGPT to add useful nested detail without losing it on import."""
    model_config = ConfigDict(extra="allow")


class FaceCharacteristics(BriefModel):
    face_shape: Any = ""
    skin_tone: Any = ""
    eyes: Any = ""
    hair: Any = ""
    distinguishing_features: Any = ""


class PhysiqueCharacteristics(BriefModel):
    height_and_build: Any = ""
    posture_and_movement: Any = ""
    age_cues: Any = ""


class StyleCharacteristics(BriefModel):
    wardrobe: Any = ""
    materials_and_palette: Any = ""
    accessories_and_grooming: Any = ""
    glamour_direction: Any = ""


class PersonalityCharacteristics(BriefModel):
    traits: Any = ""
    interests_and_values: Any = ""
    speech_style: Any = ""
    mannerisms: Any = ""


class WorldCharacteristics(BriefModel):
    cultural_context: Any = ""
    home_base: Any = ""
    recurring_locations: Any = ""
    content_pillars: Any = ""


class CameraCharacteristics(BriefModel):
    framing: Any = ""
    lens_and_depth: Any = ""
    lighting: Any = ""
    color_grade: Any = ""


class PersonaCharacteristics(BriefModel):
    consistency_anchor: Any = ""
    face: FaceCharacteristics = Field(default_factory=FaceCharacteristics)
    physique: PhysiqueCharacteristics = Field(default_factory=PhysiqueCharacteristics)
    style: StyleCharacteristics = Field(default_factory=StyleCharacteristics)
    personality: PersonalityCharacteristics = Field(default_factory=PersonalityCharacteristics)
    world: WorldCharacteristics = Field(default_factory=WorldCharacteristics)
    camera: CameraCharacteristics = Field(default_factory=CameraCharacteristics)


class PersonaBrief(BriefModel):
    name: str = Field(min_length=2, max_length=80)
    age: int = Field(ge=18, le=110)
    appearance: str = Field(min_length=8, max_length=1500)
    description: str = Field(min_length=8, max_length=1500)
    consistency_anchor: Any = ""
    characteristics: PersonaCharacteristics = Field(default_factory=PersonaCharacteristics)
    disclosure: Any = "Fictional AI-generated adult persona"


class PersonaImportBrief(BriefModel):
    schema_version: Literal["persona-1.0", "1.0"] = "persona-1.0"
    persona: PersonaBrief


class ImageBrief(BaseModel):
    enabled: bool = True
    model: Literal["flux2-klein-4b", "z-image-turbo"] = "flux2-klein-4b"
    prompt: str = Field(min_length=5, max_length=3000)
    negative_prompt: str = Field(
        default=(
            "blurry, deformed, extra fingers, duplicate person, watermark, typography, logo, "
            "child, teenager, minor, nudity, exposed genitals, explicit sexual activity, lingerie, real-person likeness"
        ),
        max_length=2000,
    )
    width: int = Field(default=768, ge=256, le=2048)
    height: int = Field(default=1152, ge=256, le=2048)
    seed: int = Field(default=42, ge=0, le=9223372036854775807)
    steps: int = Field(default=4, ge=1, le=100)
    guidance: float = Field(default=1.0, ge=0, le=30)
    reference_paths: list[str] = Field(default_factory=list, max_length=8)
    output: str = Field(default="generated/master.png", min_length=1, max_length=260)


class VideoBrief(BaseModel):
    enabled: bool = True
    model: Literal["wan22-ti2v-5b"] = "wan22-ti2v-5b"
    prompt: str = Field(min_length=5, max_length=3000)
    size: Literal["1280*704", "704*1280"] = "704*1280"
    output: str = Field(default="generated/reel.mp4", min_length=1, max_length=260)


class VoiceBrief(BaseModel):
    enabled: bool = False
    text: str = Field(default="", max_length=1200)
    voice: str = Field(default="af_heart", pattern=r"^(af_|am_|bf_|bm_)[a-z0-9_]+$")
    lang: str = Field(default="a", min_length=1, max_length=8)
    output: str = Field(default="generated/narration.wav", min_length=1, max_length=260)


class AssemblyBrief(BaseModel):
    enabled: bool = True
    output: str = Field(default="generated/reel_with_voice.mp4", min_length=1, max_length=260)
    disclosure: str = Field(
        default="Fictional adult character. AI-generated synthetic media.",
        min_length=20,
        max_length=300,
    )


class ReviewBrief(BaseModel):
    disclosure_required: bool = True
    checklist: list[str] = Field(default_factory=lambda: [
        "Confirm the character is fictional and an adult.",
        "Confirm reference inputs are owned or permission-cleared.",
        "Check identity continuity, anatomy, motion and audio timing.",
        "Keep the AI-generated disclosure attached to the export.",
    ], max_length=20)


class GenerationBrief(BaseModel):
    schema_version: Literal["1.0"] = "1.0"
    title: str = Field(min_length=2, max_length=120)
    persona: PersonaBrief
    image: ImageBrief
    video: VideoBrief
    voice: VoiceBrief = Field(default_factory=VoiceBrief)
    assembly: AssemblyBrief = Field(default_factory=AssemblyBrief)
    review: ReviewBrief = Field(default_factory=ReviewBrief)


def parse_brief_bytes(raw: bytes) -> GenerationBrief:
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Brief must be valid UTF-8 JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("Brief root must be a JSON object")
    try:
        if hasattr(GenerationBrief, "model_validate"):
            return GenerationBrief.model_validate(payload)
        return GenerationBrief.parse_obj(payload)
    except Exception as exc:
        raise ValueError(f"Brief validation failed: {exc}") from exc


def parse_brief_file(path: str | Path) -> GenerationBrief:
    file = Path(path).expanduser().resolve()
    if not file.is_file():
        raise FileNotFoundError(f"Brief file not found: {file}")
    return parse_brief_bytes(file.read_bytes())


def parse_persona_bytes(raw: bytes) -> PersonaImportBrief:
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Persona brief must be valid UTF-8 JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("Persona brief root must be a JSON object")
    # Accept either the recommended envelope or a persona object copied directly.
    if "persona" not in payload:
        payload = {"schema_version": "persona-1.0", "persona": payload}
    try:
        if hasattr(PersonaImportBrief, "model_validate"):
            return PersonaImportBrief.model_validate(payload)
        return PersonaImportBrief.parse_obj(payload)
    except Exception as exc:
        raise ValueError(f"Persona brief validation failed: {exc}") from exc


def brief_dict(brief: GenerationBrief) -> dict:
    """Return a Pydantic-version-independent JSON-ready dictionary."""
    if hasattr(brief, "model_dump"):
        return brief.model_dump()
    return brief.dict()
