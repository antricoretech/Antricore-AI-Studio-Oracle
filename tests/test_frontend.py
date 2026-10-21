from fastapi.testclient import TestClient

from studio.app import app


def test_frontend_is_module_split_and_static_modules_are_served():
    with TestClient(app) as client:
        index = client.get('/')
        assert index.status_code == 200
        assert 'type="module"' in index.text
        assert 'href="/workspace"' in index.text
        assert 'data-canonical-workspace-link' in index.text
        for target in ('personas', 'production', 'content-packs', 'assets', 'overview'):
            assert f'data-canonical-target="{target}"' in index.text
        app_js = client.get('/static/app.js')
        assert app_js.status_code == 200
        assert 'syncCanonicalSurfaceLinks' in app_js.text
        assert 'CANONICAL_PERSONA_DRAFT_KEY' in app_js.text
        assert 'handoffSynthesizedPersonaToCanonicalFlow' in app_js.text
        assert "window.location.assign('/workspace#personas')" in app_js.text
        workspace_js = client.get('/static/workspace.js')
        assert workspace_js.status_code == 200
        assert 'preflightFingerprint' in workspace_js.text
        assert 'Generation inputs changed while preflight was running' in workspace_js.text
        assert 'readCanonicalPersonaDraft' in workspace_js.text
        assert 'Draft imported from legacy Vault synthesis.' in workspace_js.text
        for module in ('core.js', 'api.js', 'navigation.js', 'photostudio.js'):
            response = client.get('/static/modules/' + module)
            assert response.status_code == 200
            assert 'export ' in response.text
