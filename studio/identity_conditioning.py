"""Model-independent contracts for identity-conditioning benchmarks.

The benchmark plan is intentionally separate from model execution. It can be
created and reviewed before the final Mac model gate, while later adapters can
record measured outputs without changing the PersonaVersion or anchor contract.
"""

from __future__ import annotations


IDENTITY_CONDITIONING_METHODS = (
    "text_only",
    "ip_adapter_faceid",
    "instantid",
    "pulid",
    "lora",
)

BENCHMARK_SCENARIOS = (
    {
        "id": "neutral_portrait",
        "label": "Neutral portrait",
        "content_class": "identity",
        "prompt": "A neutral studio portrait with soft even light and a natural expression.",
    },
    {
        "id": "three_quarter_profile",
        "label": "Three-quarter profile",
        "content_class": "identity",
        "prompt": "A three-quarter profile portrait with consistent facial proportions and natural skin detail.",
    },
    {
        "id": "full_body_lifestyle",
        "label": "Full-body lifestyle",
        "content_class": "lifestyle",
        "prompt": "A full-body lifestyle photograph in a believable everyday environment with stable body proportions.",
    },
    {
        "id": "fashion_editorial",
        "label": "Fashion editorial",
        "content_class": "fashion",
        "prompt": "A polished fashion editorial image with the same facial identity, hair, and signature styling.",
    },
    {
        "id": "adult_glamour_editorial",
        "label": "Adult/glamour editorial",
        "content_class": "adult_glamour",
        "prompt": "An adult glamour editorial image with consistent facial identity, realistic anatomy, and intentional styling.",
    },
)

METRIC_LIMITS = {
    "identity_score": (0.0, 1.0),
    "prompt_adherence": (0.0, 1.0),
    "anatomy_score": (0.0, 1.0),
    "style_consistency": (0.0, 1.0),
    "latency_ms": (0.0, None),
    "peak_memory_mb": (0.0, None),
    "disk_mb": (0.0, None),
}

BENCHMARK_STATUSES = frozenset({"planned", "in_progress", "completed", "blocked"})
CASE_STATUSES = frozenset({"planned", "running", "completed", "blocked", "failed"})


def scenario_catalog() -> list[dict]:
    """Return a copy so callers cannot mutate the canonical catalog."""

    return [dict(item) for item in BENCHMARK_SCENARIOS]


def normalize_selection(methods: list[str] | None, scenario_ids: list[str] | None) -> tuple[list[str], list[dict]]:
    selected_methods = list(dict.fromkeys(methods or IDENTITY_CONDITIONING_METHODS))
    unknown_methods = [method for method in selected_methods if method not in IDENTITY_CONDITIONING_METHODS]
    if unknown_methods:
        raise ValueError(f"Unsupported identity-conditioning method(s): {', '.join(unknown_methods)}")
    catalog = {item["id"]: item for item in BENCHMARK_SCENARIOS}
    selected_ids = list(dict.fromkeys(scenario_ids or catalog))
    unknown_scenarios = [scenario_id for scenario_id in selected_ids if scenario_id not in catalog]
    if unknown_scenarios:
        raise ValueError(f"Unsupported benchmark scenario(s): {', '.join(unknown_scenarios)}")
    if not selected_methods or not selected_ids:
        raise ValueError("A benchmark requires at least one method and one scenario")
    return selected_methods, [dict(catalog[scenario_id]) for scenario_id in selected_ids]


def validate_metrics(metrics: dict | None) -> dict:
    normalized = dict(metrics or {})
    unknown = sorted(set(normalized) - set(METRIC_LIMITS))
    if unknown:
        raise ValueError(f"Unsupported benchmark metric(s): {', '.join(unknown)}")
    for name, value in normalized.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"Benchmark metric '{name}' must be numeric")
        lower, upper = METRIC_LIMITS[name]
        if value < lower or (upper is not None and value > upper):
            bound = f"between {lower} and {upper}" if upper is not None else f"at least {lower}"
            raise ValueError(f"Benchmark metric '{name}' must be {bound}")
        normalized[name] = float(value)
    return normalized


def validate_completed_metrics(metrics: dict) -> None:
    required = {"identity_score", "prompt_adherence", "anatomy_score"}
    missing = sorted(required - set(metrics))
    if missing:
        raise ValueError(f"Completed benchmark results require: {', '.join(missing)}")
