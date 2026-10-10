"""Shared content and provenance policy constants.

Keeping these values in one module prevents the API, CLI and brief schemas
from slowly acquiring different safety/disclosure behaviour.
"""

AI_DISCLOSURE = "Fictional adult character. AI-generated synthetic media."
DEFAULT_NEGATIVE_PROMPT = (
    "blurry, deformed, extra fingers, duplicate person, text, watermark, logo, "
    "child, teenager, minor, nudity, exposed genitals, explicit sexual activity, "
    "lingerie, real-person likeness"
)
