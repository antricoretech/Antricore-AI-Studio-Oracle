from io import BytesIO

from PIL import Image


def _ready_asset(client):
    persona = client.post('/api/personas', json={
        'name': 'Platform Policy', 'age': 30,
        'appearance': 'long brown hair and hazel eyes',
        'description': 'fictional adult glamour creator for platform policy tests',
    }).json()
    assert client.post(f"/api/personas/{persona['id']}/freeze").status_code == 200
    buffer = BytesIO()
    Image.new('RGB', (32, 32), 'ivory').save(buffer, format='PNG')
    imported = client.post('/api/assets/import', data={
        'persona_id': persona['id'], 'kind': 'image', 'prompt': 'Platform policy image',
        'content_class': 'adult_glamour', 'destination_policy': 'eligible',
        'disclosure': 'Fictional adult character. AI-generated synthetic media.', 'rights_confirmed': 'true',
    }, files={'file': ('platform-policy.png', buffer.getvalue(), 'image/png')})
    assert imported.status_code == 201
    aid = imported.json()['id']
    assert client.post(f'/api/assets/{aid}/assessment', json={
        'identity_score': 0.95, 'anatomy_score': 0.9, 'hands_score': 0.9,
        'facial_drift_score': 0.95, 'evaluator': 'qa_operator',
    }).status_code == 200
    assert client.patch(f'/api/assets/{aid}/review', json={'review': 'approved', 'reason': 'Policy fixture passed'}).status_code == 200
    return aid


def test_platform_policy_catalog_is_local_only(client):
    response = client.get('/api/publishing/policies')
    assert response.status_code == 200
    data = response.json()
    assert data['external_calls'] is False
    assert data['policies']['instagram']['execution_status'] == 'deferred_phase_8'
    assert data['policies']['instagram']['formats']['feed_image']['kind'] == 'image'


def test_instagram_platform_readiness_reports_deferred_blockers(client):
    aid = _ready_asset(client)
    response = client.get(f'/api/assets/{aid}/platform-readiness?platform=instagram&format=feed_image')
    assert response.status_code == 200
    data = response.json()
    assert data['platform_readiness']['ready'] is False
    assert data['platform_readiness']['status'] == 'blocked'
    check_status = {check['id']: check['status'] for check in data['platform_readiness']['checks']}
    assert check_status['asset_readiness'] == 'ready'
    assert check_status['destination_policy'] == 'ready'
    assert check_status['platform_account_binding'] == 'blocked'
    assert check_status['public_media_url'] == 'blocked'


def test_platform_readiness_rejects_unknown_contract(client):
    aid = _ready_asset(client)
    response = client.get(f'/api/assets/{aid}/platform-readiness?platform=unknown')
    assert response.status_code == 400
