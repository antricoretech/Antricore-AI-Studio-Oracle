from fastapi.testclient import TestClient

from studio.app import app


def test_frontend_is_module_split_and_static_modules_are_served():
    with TestClient(app) as client:
        index = client.get('/')
        assert index.status_code == 200
        assert 'type="module"' in index.text
        assert 'href="/workspace"' in index.text
        for module in ('core.js', 'api.js', 'navigation.js', 'photostudio.js'):
            response = client.get('/static/modules/' + module)
            assert response.status_code == 200
            assert 'export ' in response.text
