from studio.application_surface import route_allowed


def test_canonical_surface_exposes_workspace_and_canonical_api_only():
    assert route_allowed("canonical", "/")
    assert route_allowed("canonical", "/workspace")
    assert route_allowed("canonical", "/api/personas")
    assert route_allowed("canonical", "/api/jobs")
    assert not route_allowed("canonical", "/api/v2/personas")
    assert not route_allowed("canonical", "/api/orchestrator/generate")
    assert not route_allowed("canonical", "/generated/legacy.png")


def test_legacy_surface_exposes_legacy_shell_and_legacy_api_only():
    assert route_allowed("legacy", "/")
    assert route_allowed("legacy", "/api/v2/personas")
    assert route_allowed("legacy", "/api/orchestrator/generate")
    assert route_allowed("legacy", "/generated/master_persona_maya/maya.png")
    assert not route_allowed("legacy", "/workspace")
    assert not route_allowed("legacy", "/api/personas")
    assert not route_allowed("legacy", "/api/jobs")


def test_combined_surface_preserves_backwards_compatibility():
    assert route_allowed("combined", "/")
    assert route_allowed("combined", "/workspace")
    assert route_allowed("combined", "/api/v2/personas")
