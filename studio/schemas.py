"""HTTP request schemas kept separate from route and orchestration code."""

from __future__ import annotations

import secrets

from pydantic import BaseModel, Field

from .brief import PersonaCharacteristics
from .policies import DEFAULT_NEGATIVE_PROMPT


class PersonaIn(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    age: int = Field(ge=18, le=110)
    description: str = Field(min_length=8, max_length=1500)
    appearance: str = Field(min_length=8, max_length=1500)
    disclosure: str = Field(default="Fictional AI-generated adult persona", min_length=10, max_length=250)
    characteristics: PersonaCharacteristics = Field(default_factory=PersonaCharacteristics)


class JobIn(BaseModel):
    persona_id: str
    workflow_id: str = "sdxl_basic_api"
    prompt: str = Field(min_length=5, max_length=3000)
    video_prompt: str | None = Field(default=None, max_length=3000)
    negative_prompt: str = Field(default=DEFAULT_NEGATIVE_PROMPT)
    checkpoint: str = Field(default="", max_length=260)
    reference_id: str | None = None
    source_asset_id: str | None = None
    audio_asset_id: str | None = None
    width: int = Field(default=768, ge=256, le=2048)
    height: int = Field(default=1152, ge=256, le=2048)
    seed: int = Field(default_factory=lambda: secrets.randbelow(2147483647), ge=0, le=9223372036854775807)
    rights_confirmed: bool = False


class ReviewIn(BaseModel):
    review: str


class ReferencePackReviewIn(BaseModel):
    review: str
    rights_confirmed: bool | None = None


class ReferencePackCanonicalIn(BaseModel):
    selected: bool = True
    item_ids: list[str] = Field(default_factory=list, max_length=100)


class ReferencePackAssetLinkIn(BaseModel):
    asset_id: str = Field(min_length=1, max_length=128)


class VoiceIn(BaseModel):
    persona_id: str
    text: str = Field(min_length=2, max_length=1200)
    voice: str = Field(default="af_heart", pattern=r"^(af_|am_|bf_|bm_)[a-z0-9_]+$")


class LinkIn(BaseModel):
    label: str = Field(min_length=2, max_length=100)
    destination: str = Field(min_length=10, max_length=1500)


class SeriesEpisodeIn(BaseModel):
    title: str = Field(min_length=2, max_length=120)
    prompt: str = Field(min_length=5, max_length=3000)
    video_prompt: str = Field(min_length=5, max_length=3000)


class SeriesIn(BaseModel):
    persona_id: str
    title: str = Field(min_length=2, max_length=120)
    description: str = Field(min_length=8, max_length=1200)
    shared_prompt: str = Field(min_length=8, max_length=3000)
    episodes: list[SeriesEpisodeIn] = Field(min_length=1, max_length=30)


class SeriesQueueIn(BaseModel):
    workflow_id: str
    checkpoint: str = Field(default="", max_length=260)
    reference_id: str | None = None
    source_asset_id: str | None = None
    audio_asset_id: str | None = None
    width: int = Field(default=704, ge=256, le=2048)
    height: int = Field(default=1280, ge=256, le=2048)
    seed: int | None = Field(default=None, ge=0, le=9223372036854775807)
    rights_confirmed: bool = False


class PhotoStudioPromptIn(BaseModel):
    persona_id: str
    location: str = ""
    costume: str = ""
    expression: str = ""
    angle: str = ""
    custom_direction: str = ""
    model_id: str = "cyberrealistic-xl"


class PhotoStudioGenerateIn(BaseModel):
    persona_id: str
    prompt: str = Field(min_length=5, max_length=3000)
    negative_prompt: str = Field(default="")
    model: str = "cyberrealistic-xl"
    width: int = Field(default=768, ge=256, le=2048)
    height: int = Field(default=1152, ge=256, le=2048)
    steps: int = Field(default=28, ge=10, le=50)
    guidance: float = Field(default=5.0, ge=1.0, le=20.0)
    seed: int | None = None
    rights_confirmed: bool = True


class OrchestratorCompilePersonaIn(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    age: int = Field(default=23, ge=18, le=110)
    country: str = Field(default="Germany")
    region: str = Field(default="Bavaria")
    facial_identity: str = Field(default="")
    body_type: str = Field(default="curvy athletic hourglass")
    measurements: str = Field(default="34D-24-35")
    height: str = Field(default="5'8\"")
    skin_tone: str = Field(default="fair golden with subtle freckles")
    breast_shape: str = Field(default="natural teardrop, realistic gravity")
    content_mode: str = Field(default="adult")
    aspect_ratio: str = Field(default="2:3")
    quality: str = Field(default="4K")


class OrchestratorCreatePersonaIn(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    age: int = Field(default=23, ge=18, le=110)
    country: str = Field(default="Germany")
    region: str = Field(default="Bavaria")
    facial_identity: str = Field(default="")
    body_physics: dict = Field(default_factory=dict)
    content_mode: str = Field(default="adult")
    master_prompt: str = Field(min_length=10, max_length=4000)
    negative_prompt: str = Field(default="")
    aspect_ratio: str = Field(default="2:3")
    quality: str = Field(default="4K")


class OrchestratorRenderAnchorIn(BaseModel):
    persona_id: str
    prompt: str = Field(min_length=10, max_length=4000)
    negative_prompt: str = Field(default="")
    model: str = Field(default="cyberrealistic-xl")
    aspect_ratio: str = Field(default="2:3")
    quality: str = Field(default="4K")
    seed: int | None = None


class OrchestratorLockAnchorIn(BaseModel):
    persona_id: str
    asset_id: str


class OrchestratorSynthesizeScenesIn(BaseModel):
    persona_id: str
    narrative: str = Field(min_length=5, max_length=2000)
    category: str = Field(default="adult_intimate")
    batch_count: int = Field(default=3, ge=1, le=8)
    aspect_ratio: str = Field(default="2:3")
    quality: str = Field(default="4K")
    model_override: str | None = None


class OrchestratorSceneItem(BaseModel):
    title: str = ""
    location: str = ""
    costume: str = ""
    expression: str = ""
    shot: str = ""
    prompt: str
    negative_prompt: str = ""


class OrchestratorBatchGenerateIn(BaseModel):
    persona_id: str
    scenes: list[OrchestratorSceneItem]
    model: str = "cyberrealistic-xl"
    aspect_ratio: str = "2:3"
    quality: str = "4K"
    steps: int = Field(default=30, ge=15, le=50)
    guidance: float = Field(default=5.0, ge=1.0, le=15.0)
    rights_confirmed: bool = True

