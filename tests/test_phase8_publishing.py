import studio.database as db
from studio import app as app_module
from studio import publishing_providers as provider_module
from studio.secrets import InMemorySecretStore


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


def test_configured_meta_provider_generates_pkce_plan_without_network(client, monkeypatch):
    monkeypatch.setenv('STUDIO_ENABLE_INSTAGRAM_PROVIDER', '1')
    monkeypatch.setenv('STUDIO_INSTAGRAM_CLIENT_ID', 'test-client-id')
    monkeypatch.setenv('STUDIO_INSTAGRAM_CLIENT_SECRET_REF', 'keyring/meta/client-secret')
    monkeypatch.setenv('STUDIO_INSTAGRAM_REDIRECT_URI', 'http://127.0.0.1:8123/oauth/callback')
    persona = _persona(client)
    account = client.post(f"/api/personas/{persona['id']}/publishing-accounts", json={
        'platform': 'instagram', 'account_label': 'Configured Meta account', 'account_type': 'creator',
    }).json()
    providers = client.get('/api/publishing/providers').json()['providers']
    meta = next(item for item in providers if item['id'] == 'meta_instagram')
    assert meta['execution_status'] == 'configured'
    assert meta['supports_oauth'] is True
    response = client.post(f"/api/publishing-accounts/{account['id']}/authorization-plan", json={
        'provider': 'meta_instagram', 'auth_mode': 'instagram_login',
        'redirect_uri': 'http://127.0.0.1:8123/oauth/callback',
    })
    assert response.status_code == 200
    data = response.json()
    assert data['status'] == 'planned'
    assert data['state_issued'] is True
    assert data['authorization_url'].startswith('https://www.instagram.com/oauth/authorize?')
    assert 'code_challenge_method=S256' in data['authorization_url']
    assert data['scopes'] == ['instagram_business_basic', 'instagram_business_content_publish']
    assert 'client_secret' not in data['authorization_url']
    sessions = client.get(f"/api/publishing-accounts/{account['id']}/authorization-sessions").json()
    assert sessions[0]['auth_mode'] == 'instagram_login'
    assert sessions[0]['scopes'] == data['scopes']


def test_oauth_callback_consumes_state_once_without_token_exchange(client, monkeypatch):
    monkeypatch.setenv('STUDIO_ENABLE_INSTAGRAM_PROVIDER', '1')
    monkeypatch.setenv('STUDIO_INSTAGRAM_CLIENT_ID', 'test-client-id')
    monkeypatch.setenv('STUDIO_INSTAGRAM_CLIENT_SECRET_REF', 'keyring/meta/client-secret')
    monkeypatch.setenv('STUDIO_INSTAGRAM_REDIRECT_URI', 'http://127.0.0.1:8123/oauth/callback')
    persona = _persona(client)
    account = client.post(f"/api/personas/{persona['id']}/publishing-accounts", json={
        'platform': 'instagram', 'account_label': 'Callback account', 'account_type': 'creator',
    }).json()
    plan = client.post(f"/api/publishing-accounts/{account['id']}/authorization-plan", json={
        'provider': 'meta_instagram', 'redirect_uri': 'http://127.0.0.1:8123/oauth/callback',
    }).json()
    callback = client.get('/oauth/callback', params={
        'provider': 'meta_instagram', 'state': plan['state'], 'code': 'one-time-code',
    })
    assert callback.status_code == 200
    data = callback.json()
    assert data['status'] == 'callback_received'
    assert data['token_exchange'] == 'disabled'
    assert data['authorization_code_stored'] is False
    assert 'one-time-code' not in callback.text
    replay = client.get('/api/publishing/oauth/callback', params={
        'provider': 'meta_instagram', 'state': plan['state'], 'code': 'one-time-code',
    })
    assert replay.status_code == 409
    sessions = client.get(f"/api/publishing-accounts/{account['id']}/authorization-sessions").json()
    assert sessions[0]['status'] == 'callback_received'
    assert sessions[0]['consumed_at']


def test_oauth_callback_rejects_invalid_state_and_provider_mismatch(client, monkeypatch):
    monkeypatch.setenv('STUDIO_ENABLE_INSTAGRAM_PROVIDER', '1')
    monkeypatch.setenv('STUDIO_INSTAGRAM_CLIENT_ID', 'test-client-id')
    monkeypatch.setenv('STUDIO_INSTAGRAM_CLIENT_SECRET_REF', 'keyring/meta/client-secret')
    monkeypatch.setenv('STUDIO_INSTAGRAM_REDIRECT_URI', 'http://127.0.0.1:8123/oauth/callback')
    persona = _persona(client)
    account = client.post(f"/api/personas/{persona['id']}/publishing-accounts", json={
        'platform': 'instagram', 'account_label': 'State account', 'account_type': 'creator',
    }).json()
    plan = client.post(f"/api/publishing-accounts/{account['id']}/authorization-plan", json={
        'provider': 'meta_instagram', 'redirect_uri': 'http://127.0.0.1:8123/oauth/callback',
    }).json()
    invalid = client.get('/api/publishing/oauth/callback', params={'state': 'wrong-state', 'code': 'code'})
    assert invalid.status_code == 400
    mismatch = client.get('/api/publishing/oauth/callback', params={
        'provider': 'local_dry_run', 'state': plan['state'], 'code': 'code',
    })
    assert mismatch.status_code == 400


def test_oauth_callback_records_denial_and_expires_sessions(client, monkeypatch):
    monkeypatch.setenv('STUDIO_ENABLE_INSTAGRAM_PROVIDER', '1')
    monkeypatch.setenv('STUDIO_INSTAGRAM_CLIENT_ID', 'test-client-id')
    monkeypatch.setenv('STUDIO_INSTAGRAM_CLIENT_SECRET_REF', 'keyring/meta/client-secret')
    monkeypatch.setenv('STUDIO_INSTAGRAM_REDIRECT_URI', 'http://127.0.0.1:8123/oauth/callback')
    persona = _persona(client)
    account = client.post(f"/api/personas/{persona['id']}/publishing-accounts", json={
        'platform': 'instagram', 'account_label': 'Denial account', 'account_type': 'creator',
    }).json()
    denied_plan = client.post(f"/api/publishing-accounts/{account['id']}/authorization-plan", json={
        'provider': 'meta_instagram', 'redirect_uri': 'http://127.0.0.1:8123/oauth/callback',
    }).json()
    denied = client.get('/oauth/callback', params={
        'state': denied_plan['state'], 'error': 'access_denied',
        'error_description': 'contains private details',
    })
    assert denied.status_code == 200
    assert denied.json()['status'] == 'denied'
    assert denied.json()['session']['error'] == 'access_denied'
    assert 'private' not in denied.text

    expired_plan = client.post(f"/api/publishing-accounts/{account['id']}/authorization-plan", json={
        'provider': 'meta_instagram', 'redirect_uri': 'http://127.0.0.1:8123/oauth/callback',
    }).json()
    db.write("UPDATE publishing_auth_sessions SET expires_at=? WHERE id=?", (
        '2000-01-01T00:00:00+00:00', expired_plan['session']['id'],
    ))
    expired = client.get('/oauth/callback', params={'state': expired_plan['state'], 'code': 'code'})
    assert expired.status_code == 400
    sessions = client.get(f"/api/publishing-accounts/{account['id']}/authorization-sessions").json()
    assert any(item['id'] == expired_plan['session']['id'] and item['status'] == 'expired' for item in sessions)


def test_configured_token_exchange_and_refresh_use_keychain_only(client, monkeypatch):
    monkeypatch.setenv('STUDIO_ENABLE_INSTAGRAM_PROVIDER', '1')
    monkeypatch.setenv('STUDIO_ENABLE_INSTAGRAM_TOKEN_EXCHANGE', '1')
    monkeypatch.setenv('STUDIO_INSTAGRAM_CLIENT_ID', 'test-client-id')
    monkeypatch.setenv('STUDIO_INSTAGRAM_CLIENT_SECRET_REF', 'keyring/meta/client-secret')
    monkeypatch.setenv('STUDIO_INSTAGRAM_REDIRECT_URI', 'http://127.0.0.1:8123/oauth/callback')
    store = InMemorySecretStore()
    store.put('keyring/meta/client-secret', 'client-secret')
    monkeypatch.setattr(app_module, 'get_store', lambda: store)
    monkeypatch.setattr(provider_module, 'get_store', lambda: store)
    provider = provider_module.get('meta_instagram')
    monkeypatch.setattr(provider, '_post_form', lambda _url, _form: {
        'access_token': 'access-token-value', 'refresh_token': 'refresh-token-value',
        'expires_in': 3600, 'token_type': 'bearer', 'scope': 'instagram_business_basic',
    })
    persona = _persona(client)
    account = client.post(f"/api/personas/{persona['id']}/publishing-accounts", json={
        'platform': 'instagram', 'account_label': 'Token account', 'account_type': 'creator',
    }).json()
    plan = client.post(f"/api/publishing-accounts/{account['id']}/authorization-plan", json={
        'provider': 'meta_instagram', 'redirect_uri': 'http://127.0.0.1:8123/oauth/callback',
    }).json()
    assert plan['secret_storage'] == 'os_keyring_verifier'
    assert plan['code_verifier'] is None
    callback = client.get('/oauth/callback', params={
        'state': plan['state'], 'code': 'authorization-code',
    })
    assert callback.status_code == 200
    assert callback.json()['status'] == 'authorized'
    assert callback.json()['token_stored'] is True
    assert 'access-token-value' not in callback.text
    assert store.get(f"publishing/account/{account['id']}/tokens")
    monkeypatch.setattr(provider, '_post_form', lambda _url, _form: {
        'access_token': 'refreshed-access-token', 'expires_in': 3600,
        'token_type': 'bearer', 'scope': 'instagram_business_basic',
    })
    refreshed = client.post(f"/api/publishing-accounts/{account['id']}/token-refresh")
    assert refreshed.status_code == 200
    assert refreshed.json()['token_refresh'] == 'completed'
    assert 'refresh-token-value' not in refreshed.text
    assert 'refresh-token-value' in store.get(f"publishing/account/{account['id']}/tokens")


def test_account_verification_and_public_media_complete_readiness_contract(client, monkeypatch):
    from io import BytesIO
    from PIL import Image

    monkeypatch.setenv('STUDIO_ENABLE_INSTAGRAM_PROVIDER', '1')
    monkeypatch.setenv('STUDIO_ENABLE_INSTAGRAM_TOKEN_EXCHANGE', '1')
    monkeypatch.setenv('STUDIO_ENABLE_INSTAGRAM_ACCOUNT_VERIFICATION', '1')
    monkeypatch.setenv('STUDIO_ENABLE_PUBLIC_MEDIA_DELIVERY', '1')
    monkeypatch.setenv('STUDIO_PUBLIC_MEDIA_BASE_URL', 'https://media.example.test')
    monkeypatch.setenv('STUDIO_INSTAGRAM_CLIENT_ID', 'test-client-id')
    monkeypatch.setenv('STUDIO_INSTAGRAM_CLIENT_SECRET_REF', 'keyring/meta/client-secret')
    monkeypatch.setenv('STUDIO_INSTAGRAM_REDIRECT_URI', 'http://127.0.0.1:8123/oauth/callback')
    store = InMemorySecretStore()
    store.put('keyring/meta/client-secret', 'client-secret')
    monkeypatch.setattr(app_module, 'get_store', lambda: store)
    monkeypatch.setattr(provider_module, 'get_store', lambda: store)
    provider = provider_module.get('meta_instagram')
    monkeypatch.setattr(provider, '_post_form', lambda _url, _form: {
        'access_token': 'access-token-value', 'refresh_token': 'refresh-token-value',
        'expires_in': 3600, 'token_type': 'bearer',
        'scope': 'instagram_business_basic,instagram_business_content_publish',
    })
    monkeypatch.setattr(provider, '_get_json', lambda _url, _query: {
        'id': 'instagram-external-123', 'username': 'verified_creator', 'account_type': 'creator',
    })
    persona = _persona(client)
    account = client.post(f"/api/personas/{persona['id']}/publishing-accounts", json={
        'platform': 'instagram', 'account_label': 'Verified account', 'account_type': 'creator',
    }).json()
    plan = client.post(f"/api/publishing-accounts/{account['id']}/authorization-plan", json={
        'provider': 'meta_instagram', 'redirect_uri': 'http://127.0.0.1:8123/oauth/callback',
    }).json()
    assert client.get('/oauth/callback', params={'state': plan['state'], 'code': 'authorization-code'}).status_code == 200
    verified = client.post(f"/api/publishing-accounts/{account['id']}/verify")
    assert verified.status_code == 200
    assert verified.json()['status'] == 'verified'
    assert verified.json()['account']['external_account_id'] == 'instagram-external-123'
    assert 'access-token-value' not in verified.text

    assert client.post(f"/api/personas/{persona['id']}/freeze").status_code == 200
    buffer = BytesIO()
    Image.new('RGB', (32, 32), 'ivory').save(buffer, format='PNG')
    imported = client.post('/api/assets/import', data={
        'persona_id': persona['id'], 'kind': 'image', 'prompt': 'Public media image',
        'content_class': 'adult_glamour', 'destination_policy': 'eligible',
        'disclosure': 'Fictional adult character. AI-generated synthetic media.', 'rights_confirmed': 'true',
    }, files={'file': ('public-media.png', buffer.getvalue(), 'image/png')})
    aid = imported.json()['id']
    assert client.post(f'/api/assets/{aid}/assessment', json={
        'identity_score': 0.95, 'anatomy_score': 0.9, 'hands_score': 0.9,
        'facial_drift_score': 0.95, 'evaluator': 'qa_operator',
    }).status_code == 200
    assert client.patch(f'/api/assets/{aid}/review', json={'review': 'approved', 'reason': 'Ready for delivery'}).status_code == 200
    public_media = client.post(f'/api/assets/{aid}/public-media')
    assert public_media.status_code == 200
    assert public_media.json()['media']['url'] == f'https://media.example.test/api/assets/{aid}/file'
    readiness = client.get(f'/api/assets/{aid}/platform-readiness?platform=instagram&format=feed_image&account_id={account["id"]}')
    assert readiness.status_code == 200
    assert readiness.json()['platform_readiness']['ready'] is True


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
