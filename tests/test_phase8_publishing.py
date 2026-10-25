def _persona(client):
    return client.post('/api/personas', json={
        'name': 'Publishing Persona', 'age': 30,
        'appearance': 'long brown hair and hazel eyes',
        'description': 'fictional adult creator for publishing account tests',
    }).json()


def test_publishing_account_binding_is_local_and_unverified(client):
    persona = _persona(client)
    response = client.post(f"/api/personas/{persona['id']}/publishing-accounts", json={
        'platform': 'instagram', 'account_label': 'Main creator account',
        'account_type': 'creator', 'handle': '@publishing_persona',
        'external_account_id': 'local-placeholder',
    })
    assert response.status_code == 201
    account = response.json()
    assert account['status'] == 'unverified'
    assert 'token' not in account
    assert client.get(f"/api/personas/{persona['id']}/publishing-accounts").json()[0]['id'] == account['id']


def test_publishing_provider_catalog_is_dry_run_only(client):
    response = client.get('/api/publishing/providers')
    assert response.status_code == 200
    data = response.json()
    assert data['external_calls'] is False
    provider = data['providers'][0]
    assert provider['id'] == 'local_dry_run'
    assert provider['supports_oauth'] is False
    assert provider['supports_publish'] is False
    assert data['providers'][1]['id'] == 'meta_instagram'
    assert data['providers'][1]['execution_status'] == 'disabled'


def test_publishing_security_exposes_capability_only(client):
    response = client.get('/api/publishing/security')
    assert response.status_code == 200
    data = response.json()
    assert data['external_calls'] is False
    assert data['database_secret_values'] is False
    assert data['token_reference_policy'] == 'opaque_reference_only'
    assert 'secret' not in str(data).lower() or 'secret_storage' in data


def test_in_memory_secret_store_is_only_a_test_contract():
    from studio.secrets import InMemorySecretStore

    store = InMemorySecretStore()
    store.put('test/provider/token', 'token-value')
    assert store.get('test/provider/token') == 'token-value'
    store.delete('test/provider/token')
    assert store.get('test/provider/token') is None


def test_authorization_plan_is_persisted_without_oauth_or_secrets(client):
    persona = _persona(client)
    account = client.post(f"/api/personas/{persona['id']}/publishing-accounts", json={
        'platform': 'instagram', 'account_label': 'Authorization plan account', 'account_type': 'creator',
    }).json()
    response = client.post(f"/api/publishing-accounts/{account['id']}/authorization-plan", json={
        'redirect_uri': 'http://127.0.0.1:8123/oauth/callback',
        'scopes': ['future.publish', 'future.publish'],
    })
    assert response.status_code == 200
    data = response.json()
    assert data['status'] == 'blocked'
    assert data['authorization_url'] is None
    assert data['state_issued'] is False
    assert data['secret_storage'] == 'hashes_only'
    assert data['external_calls'] is False
    assert 'state_hash' not in data['session']
    assert 'verifier_hash' not in data['session']
    sessions = client.get(f"/api/publishing-accounts/{account['id']}/authorization-sessions")
    assert sessions.status_code == 200
    assert sessions.json()[0]['scopes'] == ['future.publish']


def test_authorization_plan_rejects_non_absolute_redirect_uri(client):
    persona = _persona(client)
    account = client.post(f"/api/personas/{persona['id']}/publishing-accounts", json={
        'platform': 'instagram', 'account_label': 'Invalid redirect account', 'account_type': 'business',
    }).json()
    response = client.post(f"/api/publishing-accounts/{account['id']}/authorization-plan", json={
        'redirect_uri': '/oauth/callback',
    })
    assert response.status_code == 400


def test_publishing_account_rejects_unsupported_instagram_account_type(client):
    persona = _persona(client)
    response = client.post(f"/api/personas/{persona['id']}/publishing-accounts", json={
        'platform': 'instagram', 'account_label': 'Invalid account', 'account_type': 'personal',
    })
    assert response.status_code == 400


def test_publish_dry_run_is_idempotent_and_has_no_external_side_effect(client):
    from io import BytesIO
    from PIL import Image

    persona = _persona(client)
    account = client.post(f"/api/personas/{persona['id']}/publishing-accounts", json={
        'platform': 'instagram', 'account_label': 'Dry run account', 'account_type': 'professional',
    }).json()
    assert client.post(f"/api/personas/{persona['id']}/freeze").status_code == 200
    buffer = BytesIO()
    Image.new('RGB', (32, 32), 'ivory').save(buffer, format='PNG')
    imported = client.post('/api/assets/import', data={
        'persona_id': persona['id'], 'kind': 'image', 'prompt': 'Dry run image',
        'content_class': 'adult_glamour', 'destination_policy': 'eligible',
        'disclosure': 'Fictional adult character. AI-generated synthetic media.', 'rights_confirmed': 'true',
    }, files={'file': ('dry-run.png', buffer.getvalue(), 'image/png')})
    aid = imported.json()['id']
    result = client.post(f'/api/assets/{aid}/publish-dry-run', json={
        'account_id': account['id'], 'idempotency_key': 'phase8-dry-run-001',
    })
    assert result.status_code == 200
    assert result.json()['attempt']['dry_run'] is True
    assert result.json()['attempt']['status'] == 'blocked'
    assert result.json()['attempt']['response']['external_calls'] is False
    assert result.json()['attempt']['response']['provider'] == 'local_dry_run'
    replay = client.post(f'/api/assets/{aid}/publish-dry-run', json={
        'account_id': account['id'], 'idempotency_key': 'phase8-dry-run-001',
    })
    assert replay.status_code == 200
    assert replay.json()['replayed'] is True
    assert replay.json()['attempt']['id'] == result.json()['attempt']['id']


def test_publish_dry_run_rejects_unknown_provider(client):
    from io import BytesIO
    from PIL import Image

    persona = _persona(client)
    account = client.post(f"/api/personas/{persona['id']}/publishing-accounts", json={
        'platform': 'instagram', 'account_label': 'Provider test account', 'account_type': 'creator',
    }).json()
    buffer = BytesIO()
    Image.new('RGB', (16, 16), 'white').save(buffer, format='PNG')
    imported = client.post('/api/assets/import', data={
        'persona_id': persona['id'], 'kind': 'image', 'prompt': 'Provider test image',
        'content_class': 'identity', 'destination_policy': 'eligible',
        'disclosure': 'Fictional adult character. AI-generated synthetic media.', 'rights_confirmed': 'true',
    }, files={'file': ('provider.png', buffer.getvalue(), 'image/png')})
    response = client.post(f"/api/assets/{imported.json()['id']}/publish-dry-run", json={
        'provider': 'real_instagram', 'account_id': account['id'], 'idempotency_key': 'phase8-provider-001',
    })
    assert response.status_code == 400
