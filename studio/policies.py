"""Shared content and provenance policy constants.

Keeping these values in one module prevents the API, CLI and brief schemas
from slowly acquiring different safety/disclosure behaviour.
"""

AI_DISCLOSURE = "Fictional adult character. AI-generated synthetic media."
DESTINATION_POLICIES = frozenset({"local_only", "review_required", "eligible"})
DEFAULT_NEGATIVE_PROMPT = (
    "blurry, deformed, extra fingers, duplicate person, text, watermark, logo, "
    "child, teenager, minor, nudity, exposed genitals, explicit sexual activity, "
    "lingerie, real-person likeness"
)


def normalize_content_class(value: str | None) -> str:
    normalized = str(value or "identity").strip().lower().replace(" ", "_")
    return (normalized or "identity")[:80]


def normalize_destination_policy(value: str | None) -> str:
    normalized = str(value or "review_required").strip().lower()
    if normalized not in DESTINATION_POLICIES:
        raise ValueError("Destination policy must be local_only, review_required, or eligible")
    return normalized
