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

IDENTITY_CONDITIONING_METHOD_CATALOG = {
    "text_only": {
        "label": "Text-only baseline",
        "category": "baseline",
        "requires": ["base_image_model"],
        "execution_status": "deferred_final_gate",
    },
    "ip_adapter_faceid": {
        "label": "IP-Adapter FaceID",
        "category": "zero_shot_adapter",
        "requires": ["base_image_model", "face_embedding_runtime", "adapter_weights"],
        "execution_status": "deferred_final_gate",
    },
    "instantid": {
        "label": "InstantID",
        "category": "zero_shot_adapter",
        "requires": ["base_image_model", "face_embedding_runtime", "adapter_weights"],
        "execution_status": "deferred_final_gate",
    },
    "pulid": {
        "label": "PuLID",
        "category": "zero_shot_adapter",
        "requires": ["base_image_model", "face_embedding_runtime", "adapter_weights"],
        "execution_status": "deferred_final_gate",
    },
    "lora": {
        "label": "Persona LoRA",
        "category": "personalized_adapter",
        "requires": ["base_image_model", "training_or_adapter_weights"],
        "execution_status": "deferred_final_gate",
    },
}

SCORE_WEIGHTS = {
    "identity_score": 0.45,
    "prompt_adherence": 0.20,
    "anatomy_score": 0.20,
    "style_consistency": 0.15,
}

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


def method_catalog() -> list[dict]:
    return [
        {"id": method, **dict(IDENTITY_CONDITIONING_METHOD_CATALOG[method])}
        for method in IDENTITY_CONDITIONING_METHODS
    ]


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


def summarize_cases(cases: list[dict]) -> list[dict]:
    """Return deterministic method comparisons without selecting a winner."""

    grouped: dict[str, list[dict]] = {}
    for case in cases:
        grouped.setdefault(case["method"], []).append(case)
    summaries = []
    for method, method_cases in grouped.items():
        completed = [case for case in method_cases if case.get("status") == "completed"]
        metric_values = [case.get("metrics") or {} for case in completed]
        score_rows = []
        for metrics in metric_values:
            available = {name: float(metrics[name]) for name in SCORE_WEIGHTS if name in metrics}
            weight_total = sum(SCORE_WEIGHTS[name] for name in available)
            if weight_total:
                score_rows.append(sum(value * SCORE_WEIGHTS[name] for name, value in available.items()) / weight_total)
        def mean_metric(name: str):
            values = [float(metrics[name]) for metrics in metric_values if name in metrics]
            return round(sum(values) / len(values), 4) if values else None
        memory_values = [float(metrics["peak_memory_mb"]) for metrics in metric_values if "peak_memory_mb" in metrics]
        summaries.append({
            "method": method,
            "label": IDENTITY_CONDITIONING_METHOD_CATALOG.get(method, {}).get("label", method),
            "total_cases": len(method_cases),
            "completed_cases": len(completed),
            "failed_cases": sum(case.get("status") == "failed" for case in method_cases),
            "blocked_cases": sum(case.get("status") == "blocked" for case in method_cases),
            "coverage": round(len(completed) / len(method_cases), 4) if method_cases else 0.0,
            "mean_score": round(sum(score_rows) / len(score_rows), 4) if score_rows else None,
            "mean_identity_score": mean_metric("identity_score"),
            "mean_prompt_adherence": mean_metric("prompt_adherence"),
            "mean_anatomy_score": mean_metric("anatomy_score"),
            "mean_style_consistency": mean_metric("style_consistency"),
            "mean_latency_ms": mean_metric("latency_ms"),
            "peak_memory_mb": max(memory_values) if memory_values else None,
            "eligible_for_selection": len(completed) == len(method_cases) and bool(score_rows),
            "selection_status": "eligible_for_review" if len(completed) == len(method_cases) and bool(score_rows) else "incomplete",
        })
    return sorted(summaries, key=lambda item: (item["eligible_for_selection"], item["mean_score"] or -1), reverse=True)
