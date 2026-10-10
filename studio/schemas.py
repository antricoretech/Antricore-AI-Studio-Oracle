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
