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
        assert 'CANONICAL_GENERATION_DRAFT_KEY' in app_js.text
        assert 'handoffSynthesizedPersonaToCanonicalFlow' in app_js.text
        assert 'handoffOrchestratorRequestToCanonicalFlow' in app_js.text
        assert "window.location.assign('/workspace#personas')" in app_js.text
        assert "#production" in app_js.text
        workspace_js = client.get('/static/workspace.js')
        assert workspace_js.status_code == 200
        assert 'preflightFingerprint' in workspace_js.text
        assert 'Generation inputs changed while preflight was running' in workspace_js.text
        assert 'readCanonicalPersonaDraft' in workspace_js.text
        assert 'readCanonicalGenerationDraft' in workspace_js.text
        assert 'Draft imported from legacy Orchestrator.' in workspace_js.text
        assert 'Draft imported from legacy Vault synthesis.' in workspace_js.text
        assert "['benchmarks', 'Identity Benchmarks'" in workspace_js.text
        assert 'identity-benchmark-create-form' in workspace_js.text
        assert 'recordIdentityBenchmarkResult' in workspace_js.text
        assert '/api/identity-conditioning/catalog' in workspace_js.text
        assert "['creator', 'Creator System'" in workspace_js.text
        assert 'creator-profile-form' in workspace_js.text
        assert 'Adult/glamour remains a content pillar inside the same Identity Core' in workspace_js.text
        assert "['content-briefs', 'Content Briefs'" in workspace_js.text
        assert 'content-brief-form' in workspace_js.text
        assert '/content-briefs' in workspace_js.text
        assert 'Edit draft' in workspace_js.text
        assert 'revision' in workspace_js.text
        assert 'Hand off to Production' in workspace_js.text
        assert 'content-artifact-create-form' in workspace_js.text
        assert '/content-artifacts/' in workspace_js.text
        assert 'deterministic template' in workspace_js.text
        assert 'Run quality check' in workspace_js.text
        assert '/quality' in workspace_js.text
        assert 'content-artifact-edit-form' in workspace_js.text
        assert 'Save artifact revision' in workspace_js.text
        assert 'content_artifacts' in workspace_js.text
        assert 'Refresh quality' in workspace_js.text
        assert 'name="reviewer"' in workspace_js.text
        assert 'name="reason"' in workspace_js.text
        assert 'assessAssetQuality' in workspace_js.text
        assert 'data-asset-assessment' in workspace_js.text
        assert 'Save assessment' in workspace_js.text
        assert 'recordAssetAssessment' in workspace_js.text
        assert 'Check publishing readiness' in workspace_js.text
        assert '/publishing-readiness' in workspace_js.text
        assert 'Check Instagram readiness' in workspace_js.text
        assert '/platform-readiness?platform=instagram' in workspace_js.text
        assert 'publishing-account-form' in workspace_js.text
        assert '/publishing-accounts' in workspace_js.text
        assert 'publishing-workflow-form' in workspace_js.text
        assert 'staging-readiness' in workspace_js.text
        assert 'Run staging preflight' in workspace_js.text
        assert 'publish-dry-run' in workspace_js.text
        assert 'Record dry-run' in workspace_js.text
        assert 'Publish to Instagram' in workspace_js.text
        assert 'confirm_external' in workspace_js.text
        assert 'Prepare public media URL' in workspace_js.text
        assert 'Verify account' in workspace_js.text
        assert 'local dry-run provider' in workspace_js.text.lower()
        for module in ('core.js', 'api.js', 'navigation.js', 'photostudio.js'):
            response = client.get('/static/modules/' + module)
            assert response.status_code == 200
            assert 'export ' in response.text
