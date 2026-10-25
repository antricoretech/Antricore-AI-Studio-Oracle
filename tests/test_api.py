from io import BytesIO
import json

import pytest
from fastapi.testclient import TestClient
from PIL import Image

import studio.database as db
from studio.app import app


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DATA", tmp_path)
    monkeypatch.setattr(db, "DB", tmp_path / "test.db")
    monkeypatch.setattr(db, "UPLOADS", tmp_path / "references")
    monkeypatch.setattr(db, "OUTPUTS", tmp_path / "outputs")
    monkeypatch.setattr(db, "WORKFLOWS", tmp_path / "workflows")
    with TestClient(app) as c:
        yield c


def test_persona_reference_and_gates(client):
    assert client.post('/api/personas', json={"name": "Underage", "age": 16,
        "description": "fictional influencer", "appearance": "dark brown hair"}).status_code == 422
    p = client.post('/api/personas', json={"name": "Mira Vale", "age": 27,
        "description": "fictional travel creator", "appearance": "brown eyes and curled hair",
        "characteristics": {"face": {"eyes": "hazel almond eyes"}, "style": {"wardrobe": "linen layers"}}})
    assert p.status_code == 201
    assert p.json()['characteristics']['face']['eyes'] == 'hazel almond eyes'
    pid = p.json()['id']
    assert len(client.get('/api/personas').json()) == 1
    image = Image.new('RGB', (80, 80), 'beige')
    bio = BytesIO()
    image.save(bio, format='PNG')
    assert client.post(f'/api/personas/{pid}/references', files={"file": ("a.png",bio.getvalue(),"image/png")}).status_code == 400
    r = client.post(f'/api/personas/{pid}/references',
        files={"file": ("a.png",bio.getvalue(),"image/png")}, data={"rights_confirmed":"true", "label":"master"})
    assert r.status_code == 201
    ref = client.get(f'/api/personas/{pid}/references').json()[0]
    assert ref['persona_version_id'] == p.json()['current_version']['id']
    assert ref['role'] == 'identity_anchor'
    assert ref['review'] == 'pending'
    assert client.get(r.json()['url']).status_code == 200
    w = client.get('/api/workflows').json()
    assert isinstance(w, list)
    job = {"persona_id":pid,"workflow_id":"nonexistent_imported_workflow","prompt":"By a sunny café terrace",
           "checkpoint":"sdxl_base.safetensors", "reference_id":r.json()['id']}
    assert client.post('/api/jobs',json=job).status_code == 400
    assert client.get('/api/summary').json()['personas'] == 1


def test_content_pack_workspace_page_is_served(client):
    response = client.get('/content-packs')
    assert response.status_code == 200
    assert 'ContentPack workspace' in response.text
    assert '/static/content_packs.js' in response.text
    assert client.get('/static/content_packs.js').status_code == 200
    assert client.get('/static/content_packs.css').status_code == 200
    api_module = client.get('/static/modules/api.js')
    assert api_module.status_code == 200
    assert 'export class ApiError' in api_module.text
    assert 'AbortError' in api_module.text


def test_canonical_workspace_page_is_served(client):
    response = client.get('/workspace')
    assert response.status_code == 200
    assert 'Canonical Workspace' in response.text
    assert 'type="module"' in response.text
    assert '/static/workspace.js' in response.text
    workspace_js = client.get('/static/workspace.js')
    assert workspace_js.status_code == 200
    assert 'persona-create-form' in workspace_js.text
    assert 'data-freeze-persona' in workspace_js.text
    assert 'data-reference-pack-review' in workspace_js.text
    assert 'data-reference-canonical' in workspace_js.text
    assert 'data-reference-item-asset' in workspace_js.text
    assert 'data-asset-review' in workspace_js.text
    assert 'Export package' in workspace_js.text
    assert 'data-job-action' in workspace_js.text
    assert '/api/jobs/' in workspace_js.text
    assert 'Generation readiness' in workspace_js.text
    assert 'generation-form' in workspace_js.text
    assert '/api/preflight?' in workspace_js.text
    assert 'Queue generation' in workspace_js.text
    assert '/api/personas/' in workspace_js.text
    assert 'data-lineage-state' in workspace_js.text
    assert 'Stale lineage warning' in workspace_js.text
    assert 'Reference linkage' in workspace_js.text
    assert 'assetReferenceLinks' in workspace_js.text
    assert 'aria-busy' in response.text
    assert 'skip-link' in response.text
    assert client.get('/static/workspace.css').status_code == 200


def test_persona_version_is_persisted_frozen_and_attached_to_series(client):
    persona = client.post('/api/personas', json={
        'name': 'Nora Vale', 'age': 28,
        'appearance': 'dark hair and hazel eyes',
        'description': 'fictional adult lifestyle creator'
    }).json()
    version = persona['current_version']
    assert version['version_no'] == 1
    assert version['state'] == 'draft'
    assert version['snapshot']['name'] == 'Nora Vale'

    versions = client.get(f"/api/personas/{persona['id']}/versions")
    assert versions.status_code == 200
    assert versions.json()[0]['id'] == version['id']

    frozen = client.post(f"/api/personas/{persona['id']}/freeze")
    assert frozen.status_code == 200
    assert frozen.json()['identity_locked'] == 1
    assert frozen.json()['frozen_version']['state'] == 'frozen'

    series = client.post('/api/series', json={
        'persona_id': persona['id'],
        'title': 'Nora weekly series',
        'description': 'A repeatable creator content series',
        'shared_prompt': 'Keep the frozen identity and editorial tone consistent',
        'episodes': [{
            'title': 'Cafe morning',
            'prompt': 'A quiet cafe portrait',
            'video_prompt': 'Slow natural head turn'
        }]
    })
    assert series.status_code == 201
    assert series.json()['persona_version_id'] == version['id']


def test_v2_json_is_compatibility_import_export_and_not_live_storage(client, tmp_path, monkeypatch):
    import studio.api_v2 as api_v2
    monkeypatch.setattr(api_v2, 'PERSONAS_FILE', tmp_path / 'personas_v2.json')
    personas = client.get('/api/v2/personas')
    assert personas.status_code == 200
    assert len(personas.json()['personas']) >= 3
    assert all(item.get('canonical_version_id') for item in personas.json()['personas'])

    packs = client.get('/api/v2/personas/maya_bhutia/reference-packs')
    assert packs.status_code == 200
    pack_by_type = {item['pack_type']: item for item in packs.json()['packs']}
    assert pack_by_type['adult_glamour']['content_class'] == 'adult_glamour'
    assert pack_by_type['adult_glamour']['identity_authority'] == 'identity_and_style'
    assert pack_by_type['adult_glamour']['review'] == 'pending'
    assert pack_by_type['adult_glamour']['canonical_eligible'] == 1
    assert pack_by_type['adult_glamour']['items'][0]['role'] == 'adult_glamour_identity_anchor'

    exported = client.get('/api/v2/personas/export')
    assert exported.status_code == 200
    assert exported.json()['schema_version'] == 'persona-v2-export-1'
    assert len(exported.json()['personas']) >= 3

    imported = client.post('/api/v2/personas/import', json={'personas': [{
        'id': 'compatibility_test_persona',
        'name': 'Compatibility Test',
        'age': 30,
        'tagline': 'A fictional adult compatibility persona',
        'origin': 'Local test fixture',
        'biometrics': {'eyes': 'hazel eyes', 'hair': 'dark hair'},
        'adult_baselines': [],
        'category_baselines': [],
        'turnaround_pack': [],
    }]})
    assert imported.status_code == 200
    assert 'compatibility_test_persona' in imported.json()['imported']
    assert any(item['id'] == 'compatibility_test_persona' for item in client.get('/api/personas').json())

    archived = client.delete('/api/v2/personas/maya_bhutia')
    assert archived.status_code == 200
    archived_packs = client.get('/api/v2/personas/archived').json()['archived_personas'][0]['reference_packs']
    assert any(item['pack_type'] == 'adult_glamour' for item in archived_packs)
    restored = client.post('/api/v2/personas/maya_bhutia/restore')
    assert restored.status_code == 200
    restored_packs = client.get('/api/v2/personas/maya_bhutia/reference-packs').json()['packs']
    assert any(item['pack_type'] == 'adult_glamour' for item in restored_packs)
    restored_version = next(item for item in client.get('/api/personas').json() if item['id'] == 'maya_bhutia')['current_version']['id']
    assert all(item['persona_version_id'] == restored_version for item in restored_packs)
    assert len({item['pack_type'] for item in restored_packs}) == len(restored_packs)


def test_reference_pack_review_linkage_and_canonical_selection(client, tmp_path, monkeypatch):
    import studio.api_v2 as api_v2

    monkeypatch.setattr(api_v2, 'PERSONAS_FILE', tmp_path / 'personas_v2.json')
    packs_response = client.get('/api/v2/personas/maya_bhutia/reference-packs')
    assert packs_response.status_code == 200
    pack = next(item for item in packs_response.json()['packs'] if item['pack_type'] == 'adult_glamour')
    item = pack['items'][0]

    image = Image.new('RGB', (64, 64), 'plum')
    bio = BytesIO()
    image.save(bio, format='PNG')
    imported = client.post('/api/assets/import', data={
        'persona_id': 'maya_bhutia', 'kind': 'image', 'prompt': 'Reviewed adult glamour identity anchor',
        'disclosure': 'Fictional adult character. AI-generated synthetic media.', 'rights_confirmed': 'true'
    }, files={'file': ('anchor.png', bio.getvalue(), 'image/png')})
    assert imported.status_code == 201
    asset_id = imported.json()['id']

    assert client.patch(f"/api/v2/personas/maya_bhutia/reference-packs/{pack['id']}/canonical",
                        json={'selected': True, 'item_ids': [item['id']]}).status_code == 409
    assert client.patch(f'/api/assets/{asset_id}/review', json={'review': 'approved'}).status_code == 200
    linked = client.post(
        f"/api/v2/personas/maya_bhutia/reference-packs/{pack['id']}/items/{item['id']}/asset",
        json={'asset_id': asset_id},
    )
    assert linked.status_code == 200
    for pack_item in pack['items']:
        reviewed_item = client.patch(
            f"/api/v2/personas/maya_bhutia/reference-packs/{pack['id']}/items/{pack_item['id']}/review",
            json={'review': 'approved', 'rights_confirmed': True},
        )
        assert reviewed_item.status_code == 200
    reviewed_pack = client.patch(
        f"/api/v2/personas/maya_bhutia/reference-packs/{pack['id']}/review",
        json={'review': 'approved'},
    )
    assert reviewed_pack.status_code == 200
    selected = client.patch(
        f"/api/v2/personas/maya_bhutia/reference-packs/{pack['id']}/canonical",
        json={'selected': True, 'item_ids': [item['id']]},
    )
    assert selected.status_code == 200
    selected_pack = selected.json()['pack']
    assert selected_pack['canonical_selected'] == 1
    selected_item = next(entry for entry in selected_pack['items'] if entry['id'] == item['id'])
    assert selected_item['asset_id'] == asset_id
    assert selected_item['canonical_selected'] == 1
    assert selected_item['asset_persona_version_id'] == selected_pack['persona_version_id']

    rejected = client.patch(f'/api/assets/{asset_id}/review', json={'review': 'rejected'})
    assert rejected.status_code == 200
    invalidated = client.get(f"/api/v2/personas/maya_bhutia/reference-packs/{pack['id']}")
    assert invalidated.status_code == 200
    assert invalidated.json()['pack']['canonical_selected'] == 0
    assert invalidated.json()['pack']['items'][0]['canonical_selected'] == 0


def test_content_pack_persists_style_and_resolves_canonical_identity(client, tmp_path, monkeypatch):
    import studio.api_v2 as api_v2

    monkeypatch.setattr(api_v2, 'PERSONAS_FILE', tmp_path / 'personas_v2.json')
    packs = client.get('/api/v2/personas/maya_bhutia/reference-packs').json()['packs']
    source_pack = next(item for item in packs if item['pack_type'] == 'adult_glamour')
    source_item = source_pack['items'][0]

    image = Image.new('RGB', (64, 64), 'gold')
    bio = BytesIO()
    image.save(bio, format='PNG')
    imported = client.post('/api/assets/import', data={
        'persona_id': 'maya_bhutia', 'kind': 'image', 'prompt': 'ContentPack canonical adult style anchor',
        'disclosure': 'Fictional adult character. AI-generated synthetic media.', 'rights_confirmed': 'true'
    }, files={'file': ('content-pack-anchor.png', bio.getvalue(), 'image/png')})
    assert imported.status_code == 201
    asset_id = imported.json()['id']
    assert client.patch(f'/api/assets/{asset_id}/review', json={'review': 'approved'}).status_code == 200
    assert client.post(
        f"/api/personas/maya_bhutia/reference-packs/{source_pack['id']}/items/{source_item['id']}/asset",
        json={'asset_id': asset_id},
    ).status_code == 200
    for item in source_pack['items']:
        assert client.patch(
            f"/api/personas/maya_bhutia/reference-packs/{source_pack['id']}/items/{item['id']}/review",
            json={'review': 'approved', 'rights_confirmed': True},
        ).status_code == 200
    assert client.patch(
        f"/api/personas/maya_bhutia/reference-packs/{source_pack['id']}/review",
        json={'review': 'approved'},
    ).status_code == 200
    assert client.patch(
        f"/api/personas/maya_bhutia/reference-packs/{source_pack['id']}/canonical",
        json={'selected': True, 'item_ids': [source_item['id']]},
    ).status_code == 200

    created = client.post('/api/personas/maya_bhutia/content-packs', json={
        'reference_pack_id': source_pack['id'],
        'pack_type': 'adult_glamour_creator',
        'name': 'Adult Glamour Creator Style',
        'content_class': 'adult_glamour',
        'identity_authority': 'style',
        'identity_core': False,
        'style': {'tone': 'editorial, intimate, confident', 'wardrobe': ['lingerie', 'silk'], 'formats': ['reel', 'photo']},
        'metadata': {'audience': 'adult subscribers'},
        'reference_item_ids': [source_item['id']],
    })
    assert created.status_code == 201
    content_pack = created.json()
    assert content_pack['identity_core'] == 1
    assert content_pack['identity_authority'] == 'identity_and_style'
    assert client.get(f"/api/personas/maya_bhutia/content-packs/{content_pack['id']}/resolve").status_code == 409

    approved = client.patch(
        f"/api/personas/maya_bhutia/content-packs/{content_pack['id']}/review",
        json={'review': 'approved'},
    )
    assert approved.status_code == 200
    resolved = client.get(f"/api/personas/maya_bhutia/content-packs/{content_pack['id']}/resolve")
    assert resolved.status_code == 200
    resolved_pack = resolved.json()
    assert resolved_pack['content_class'] == 'adult_glamour'
    assert resolved_pack['identity_core'] is True
    assert resolved_pack['identity_authority'] == 'identity_and_style'
    assert resolved_pack['style']['tone'].startswith('editorial')
    assert resolved_pack['anchors'][0]['asset_id'] == asset_id

    lingerie = client.post('/api/personas/maya_bhutia/content-packs', json={
        'reference_pack_id': source_pack['id'],
        'pack_type': 'lingerie_creator',
        'name': 'Lingerie Creator Style',
        'content_class': 'lingerie',
        'identity_authority': 'style',
        'identity_core': False,
        'style': {'tone': 'editorial lingerie campaign'},
        'reference_item_ids': [source_item['id']],
    })
    assert lingerie.status_code == 201
    assert lingerie.json()['identity_core'] == 1
    assert lingerie.json()['identity_authority'] == 'identity_and_style'

    rejected = client.patch(f'/api/assets/{asset_id}/review', json={'review': 'rejected'})
    assert rejected.status_code == 200
    assert client.get(f"/api/personas/maya_bhutia/content-packs/{content_pack['id']}/resolve").status_code == 409


def test_identity_benchmark_binds_frozen_version_and_adult_glamour_anchor(client, tmp_path, monkeypatch):
    import studio.api_v2 as api_v2

    catalog = client.get('/api/identity-conditioning/catalog')
    assert catalog.status_code == 200
    assert catalog.json()['execution_status'] == 'deferred_final_gate'
    assert {method['id'] for method in catalog.json()['methods']} == {
        'text_only', 'ip_adapter_faceid', 'instantid', 'pulid', 'lora'
    }
    assert any(item['content_class'] == 'adult_glamour' for item in catalog.json()['scenarios'])

    monkeypatch.setattr(api_v2, 'PERSONAS_FILE', tmp_path / 'personas_v2.json')
    packs = client.get('/api/v2/personas/maya_bhutia/reference-packs').json()['packs']
    source_pack = next(item for item in packs if item['pack_type'] == 'adult_glamour')
    source_item = source_pack['items'][0]
    image = Image.new('RGB', (64, 64), 'plum')
    bio = BytesIO()
    image.save(bio, format='PNG')
    imported = client.post('/api/assets/import', data={
        'persona_id': 'maya_bhutia', 'kind': 'image', 'prompt': 'Identity benchmark adult glamour anchor',
        'disclosure': 'Fictional adult character. AI-generated synthetic media.', 'rights_confirmed': 'true'
    }, files={'file': ('benchmark-anchor.png', bio.getvalue(), 'image/png')})
    assert imported.status_code == 201
    asset_id = imported.json()['id']
    assert client.patch(f'/api/assets/{asset_id}/review', json={'review': 'approved'}).status_code == 200
    assert client.post(
        f"/api/v2/personas/maya_bhutia/reference-packs/{source_pack['id']}/items/{source_item['id']}/asset",
        json={'asset_id': asset_id},
    ).status_code == 200
    for item in source_pack['items']:
        assert client.patch(
            f"/api/v2/personas/maya_bhutia/reference-packs/{source_pack['id']}/items/{item['id']}/review",
            json={'review': 'approved', 'rights_confirmed': True},
        ).status_code == 200
    assert client.patch(
        f"/api/v2/personas/maya_bhutia/reference-packs/{source_pack['id']}/review",
        json={'review': 'approved'},
    ).status_code == 200
    assert client.patch(
        f"/api/v2/personas/maya_bhutia/reference-packs/{source_pack['id']}/canonical",
        json={'selected': True, 'item_ids': [source_item['id']]},
    ).status_code == 200
    assert client.post('/api/personas/maya_bhutia/freeze').status_code == 200

    created = client.post('/api/personas/maya_bhutia/identity-benchmarks', json={
        'base_model_id': 'pending-final-gate',
        'methods': ['text_only', 'ip_adapter_faceid'],
        'scenario_ids': ['neutral_portrait', 'adult_glamour_editorial'],
    })
    assert created.status_code == 201
    benchmark = created.json()
    assert benchmark['status'] == 'planned'
    assert benchmark['anchor_content_class'] == 'adult_glamour'
    assert benchmark['persona_version_id'] == source_pack['persona_version_id']
    assert len(benchmark['cases']) == 4
    assert {case['method'] for case in benchmark['cases']} == {'text_only', 'ip_adapter_faceid'}

    first_case = benchmark['cases'][0]
    invalid = client.post(
        f"/api/personas/maya_bhutia/identity-benchmarks/{benchmark['id']}/cases/{first_case['id']}/result",
        json={'status': 'completed', 'metrics': {'identity_score': 1.1}},
    )
    assert invalid.status_code == 409
    recorded = client.post(
        f"/api/personas/maya_bhutia/identity-benchmarks/{benchmark['id']}/cases/{first_case['id']}/result",
        json={'status': 'completed', 'metrics': {
            'identity_score': 0.91, 'prompt_adherence': 0.82, 'anatomy_score': 0.88,
            'latency_ms': 1200,
        }},
    )
    assert recorded.status_code == 200
    assert recorded.json()['status'] == 'in_progress'
    assert next(case for case in recorded.json()['cases'] if case['id'] == first_case['id'])['status'] == 'completed'
    text_summary = next(item for item in recorded.json()['summary'] if item['method'] == 'text_only')
    assert text_summary['completed_cases'] == 1
    assert text_summary['coverage'] == 0.5
    assert text_summary['eligible_for_selection'] is False


def test_creator_profile_binds_persona_version_and_keeps_adult_pillar_in_identity_core(client):
    persona = client.post('/api/personas', json={
        'name': 'Creator Profile Test', 'age': 28,
        'description': 'A fictional adult creator with a defined editorial voice.',
        'appearance': 'Dark hair, warm skin, natural editorial features.',
    }).json()
    pid = persona['id']
    empty = client.get(f'/api/personas/{pid}/creator-profile')
    assert empty.status_code == 200
    assert empty.json()['profile'] is None
    saved = client.put(f'/api/personas/{pid}/creator-profile', json={
        'personality': {'traits': 'Confident and witty', 'speech_style': 'Warm and direct'},
        'audience': {'primary': 'Adults interested in fashion and lifestyle'},
        'brand': {'positioning': 'Luxury fashion with relatable storytelling'},
        'voice': {'tone': 'Smart and warm'},
        'disclosure': 'Fictional adult creator. AI-generated synthetic media.',
        'content_pillars': [
            {'name': 'Fashion', 'content_classes': ['fashion'], 'identity_authority': 'style'},
            {'name': 'Adult Glamour', 'content_classes': ['adult_glamour'], 'identity_authority': 'style'},
        ],
    })
    assert saved.status_code == 200
    body = saved.json()
    assert body['version_state'] == 'draft'
    assert body['profile']['persona_version_id'] == body['persona_version_id']
    glamour = next(item for item in body['profile']['content_pillars'] if item['name'] == 'Adult Glamour')
    assert glamour['identity_core'] is True
    assert glamour['identity_authority'] == 'identity_and_style'
    assert client.post(f'/api/personas/{pid}/freeze').status_code == 200
    frozen = client.put(f'/api/personas/{pid}/creator-profile', json={
        'disclosure': 'Fictional adult creator. AI-generated synthetic media.',
        'content_pillars': [],
    })
    assert frozen.status_code == 409


def test_content_brief_requires_creator_system_and_frozen_version_for_production_handoff(client):
    persona = client.post('/api/personas', json={
        'name': 'Brief Test', 'age': 30,
        'description': 'A fictional adult creator for reusable content planning.',
        'appearance': 'Dark hair, warm skin, consistent editorial identity.',
    }).json()
    pid = persona['id']
    payload = {
        'title': 'Adult glamour evening editorial',
        'format': 'reel',
        'content_class': 'adult_glamour',
        'pillar_key': 'adult_glamour',
        'audience_goal': 'Inspire confident adult self-expression.',
        'emotional_objective': 'Make the audience feel confident and seen.',
        'visual_direction': 'Editorial evening light with canonical identity anchors and tasteful styling.',
        'motion_direction': 'Slow controlled movement and natural adult gestures.',
        'caption_direction': 'Confident hook, reflective close, and visible AI disclosure.',
        'disclosure': 'Fictional adult creator. AI-generated synthetic media.',
    }
    missing_profile = client.post(f'/api/personas/{pid}/content-briefs', json=payload)
    assert missing_profile.status_code == 409
    profile = client.put(f'/api/personas/{pid}/creator-profile', json={
        'disclosure': 'Fictional adult creator. AI-generated synthetic media.',
        'content_pillars': [{
            'name': 'Adult Glamour', 'content_classes': ['adult_glamour'],
            'identity_authority': 'style',
        }],
    })
    assert profile.status_code == 200
    created = client.post(f'/api/personas/{pid}/content-briefs', json=payload)
    assert created.status_code == 201
    brief = created.json()
    assert brief['status'] == 'draft'
    assert brief['content_class'] == 'adult_glamour'
    revised_payload = {**payload, 'title': 'Adult glamour evening editorial revision', 'emotional_objective': 'Make the audience feel confident, seen, and engaged.'}
    revised = client.put(f"/api/personas/{pid}/content-briefs/{brief['id']}", json=revised_payload)
    assert revised.status_code == 200
    assert revised.json()['title'].endswith('revision')
    assert revised.json()['revision'] == 2
    brief = revised.json()
    blocked = client.patch(f"/api/personas/{pid}/content-briefs/{brief['id']}/approve")
    assert blocked.status_code == 409
    assert client.post(f'/api/personas/{pid}/freeze').status_code == 200
    approved = client.patch(f"/api/personas/{pid}/content-briefs/{brief['id']}/approve")
    assert approved.status_code == 200
    assert approved.json()['status'] == 'approved'
    resolved = client.get(f"/api/personas/{pid}/content-briefs/{brief['id']}/resolve")
    assert resolved.status_code == 200
    handoff = resolved.json()
    assert handoff['production_handoff']['format'] == 'reel'
    assert handoff['content_pillar']['identity_core'] is True
    assert handoff['content_pillar']['identity_authority'] == 'identity_and_style'
    assert handoff['creator_profile']['id'] == profile.json()['profile']['id']
    caption = client.post(f"/api/personas/{pid}/content-briefs/{brief['id']}/artifacts", json={
        'artifact_type': 'caption',
    })
    assert caption.status_code == 201
    artifact = caption.json()
    assert artifact['status'] == 'draft'
    assert artifact['source'] == 'deterministic_template'
    assert artifact['quality_status'] == 'needs_review'
    assert any(check['key'] == 'operator_review' and check['status'] == 'warning' for check in artifact['quality']['checks'])
    assert 'Disclosure:' in artifact['content']
    template_quality = client.post(f"/api/personas/{pid}/content-artifacts/{artifact['id']}/quality")
    assert template_quality.status_code == 200
    assert template_quality.json()['quality_status'] == 'needs_review'
    edited_artifact = client.put(f"/api/personas/{pid}/content-artifacts/{artifact['id']}", json={
        'artifact_type': 'caption',
        'content': 'A reviewed caption draft. Fictional adult creator. AI-generated synthetic media.',
    })
    assert edited_artifact.status_code == 200
    assert edited_artifact.json()['revision'] == 2
    assert edited_artifact.json()['source'] == 'operator'
    assert edited_artifact.json()['quality_status'] == 'passed'
    approved_artifact = client.patch(f"/api/personas/{pid}/content-artifacts/{artifact['id']}/review", json={'review': 'approved'})
    assert approved_artifact.status_code == 200
    assert approved_artifact.json()['quality_status'] == 'passed'
    handoff_with_artifact = client.get(f"/api/personas/{pid}/content-briefs/{brief['id']}/resolve")
    assert handoff_with_artifact.status_code == 200
    assert handoff_with_artifact.json()['content_artifacts'][0]['id'] == artifact['id']
    assert handoff_with_artifact.json()['content_artifacts'][0]['artifact_type'] == 'caption'
    resolved_artifact = client.get(f"/api/personas/{pid}/content-artifacts/{artifact['id']}/resolve")
    assert resolved_artifact.status_code == 200
    assert resolved_artifact.json()['content_brief_id'] == brief['id']
    assert resolved_artifact.json()['persona_version_id'] == handoff['persona_version_id']
    assert resolved_artifact.json()['quality']['status'] == 'passed'
    duplicate_artifact = client.post(f"/api/personas/{pid}/content-briefs/{brief['id']}/artifacts", json={'artifact_type': 'caption'})
    assert duplicate_artifact.status_code == 409
    immutable = client.put(f"/api/personas/{pid}/content-briefs/{brief['id']}", json=revised_payload)
    assert immutable.status_code == 409
    assert client.get(f'/api/personas/{pid}/content-briefs').json()[0]['id'] == brief['id']


def test_link_redirect_and_review_validation(client):
    assert client.post('/api/links', json={"label": "Test", "destination": "http://example.com/"}).status_code == 400
    r = client.post('/api/links', json={"label": "Landing", "destination": "https://example.com/landing"})
    assert r.status_code == 201
    code = r.json()['code']
    assert client.get('/go/'+code,follow_redirects=False).status_code == 302
    assert client.get('/api/links').json()[0]['clicks'] == 1
    assert client.patch('/api/assets/fake/review',json={"review":"approved"}).status_code == 404


def test_request_and_correlation_ids_are_returned_and_bounded(client):
    response = client.get('/api/summary', headers={
        'X-Request-ID': 'req-123',
        'X-Correlation-ID': 'corr-456',
    })
    assert response.status_code == 200
    assert response.headers['X-Request-ID'] == 'req-123'
    assert response.headers['X-Correlation-ID'] == 'corr-456'

    generated = client.get('/api/summary')
    assert generated.headers['X-Request-ID']
    assert generated.headers['X-Correlation-ID']
    assert len(generated.headers['X-Request-ID']) == 32
    assert len(generated.headers['X-Correlation-ID']) == 32

    invalid = client.get('/api/summary', headers={'X-Request-ID': 'bad value'})
    assert invalid.status_code == 200
    assert invalid.headers['X-Request-ID'] != 'bad value'
    assert invalid.headers['X-Correlation-ID'] != 'bad value'


def test_photo_studio_generation_starts_in_pending_review(client, monkeypatch):
    import studio.free_cli as free_cli

    persona = client.post('/api/personas', json={
        'name': 'Asha Vale', 'age': 29,
        'appearance': 'dark hair and brown eyes',
        'description': 'fictional adult fashion creator'
    }).json()

    def fake_make_image(args):
        Image.new('RGB', (32, 32), 'beige').save(args.output, format='PNG')

    monkeypatch.setattr(free_cli, 'make_image', fake_make_image)
    request = {
        'persona_id': persona['id'],
        'prompt': 'Editorial portrait in a studio',
        'rights_confirmed': True,
    }
    response = client.post('/api/photo-studio/generate', json=request, headers={'Idempotency-Key': 'photo-studio-repeat-1'})
    assert response.status_code == 201
    asset = next(item for item in client.get('/api/assets').json() if item['id'] == response.json()['id'])
    assert asset['review'] == 'pending'
    assert asset['filename'].startswith('asset_')
    assert (db.OUTPUTS / asset['filename']).is_file()
    repeated = client.post('/api/photo-studio/generate', json=request, headers={'Idempotency-Key': 'photo-studio-repeat-1'})
    assert repeated.status_code == 201
    assert repeated.json()['id'] == response.json()['id']
    jobs = [job for job in client.get('/api/jobs').json() if job['id'] == response.json()['job_id']]
    assert jobs and jobs[0]['status'] == 'completed'
    assert jobs[0]['result']['id'] == response.json()['id']


def test_legacy_photoshoot_render_uses_canonical_job_and_asset(client, monkeypatch, tmp_path):
    import studio.diffusion_engine as diffusion_engine

    persona = client.post('/api/personas', json={
        'name': 'Legacy Bridge', 'age': 30,
        'appearance': 'dark hair and green eyes',
        'description': 'fictional adult editorial creator'
    }).json()
    render_dir = tmp_path / 'renders'
    render_dir.mkdir()
    monkeypatch.setattr(diffusion_engine, 'RENDERS_DIR', render_dir)

    def fake_generate_render(**kwargs):
        assert kwargs['register_asset'] is False
        filename = 'render_legacy_bridge.png'
        Image.new('RGB', (24, 24), 'plum').save(render_dir / filename, format='PNG')
        return {
            'status': 'completed', 'image_url': f'/generated/renders/{filename}',
            'aspect_ratio': kwargs['aspect_ratio'], 'width': 24, 'height': 24,
            'seed': 42, 'elapsed_seconds': 0.01, 'model': kwargs['model_id'],
            'persona_id': kwargs['persona_id'], 'persona_name': kwargs['persona_name'],
            'filename': filename,
        }

    monkeypatch.setattr(diffusion_engine, 'generate_render', fake_generate_render)
    request = {
        'persona_id': persona['id'],
        'prompt': 'Editorial portrait in a studio',
        'negative_prompt': 'blurry',
        'aspect_ratio': '1:1',
        'model': 'juggernaut-xl-v10',
    }
    response = client.post('/api/v2/orchestrator/generate', json=request, headers={'Idempotency-Key': 'legacy-render-repeat-1'})
    assert response.status_code == 200
    result = response.json()
    assert result['job_id']
    assert result['asset_id'] == result['id']
    assert result['image_url'].startswith('/api/assets/')
    assert client.get(result['image_url']).status_code == 200

    asset = next(item for item in client.get('/api/assets').json() if item['id'] == result['asset_id'])
    assert asset['job_id'] == result['job_id']
    assert asset['review'] == 'pending'
    jobs = [job for job in client.get('/api/jobs').json() if job['id'] == result['job_id']]
    assert jobs and jobs[0]['status'] == 'completed'
    assert jobs[0]['result']['asset_id'] == result['asset_id']

    repeated = client.post('/api/v2/orchestrator/generate', json=request, headers={'Idempotency-Key': 'legacy-render-repeat-1'})
    assert repeated.status_code == 200
    assert repeated.json()['asset_id'] == result['asset_id']
    assert len([item for item in client.get('/api/assets').json() if item['id'] == result['asset_id']]) == 1


def test_legacy_photoshoot_render_failure_marks_job_failed_without_static_asset(client, monkeypatch):
    import studio.diffusion_engine as diffusion_engine

    persona = client.post('/api/personas', json={
        'name': 'Generation Failure', 'age': 30,
        'appearance': 'dark hair and hazel eyes',
        'description': 'fictional adult editorial creator'
    }).json()

    def failed_generate_render(**kwargs):
        raise RuntimeError('approved checkpoint is unavailable')

    monkeypatch.setattr(diffusion_engine, 'generate_render', failed_generate_render)
    response = client.post('/api/v2/orchestrator/generate', json={
        'persona_id': persona['id'],
        'prompt': 'Editorial portrait in a studio',
        'model': 'juggernaut-xl-v10',
    }, headers={'Idempotency-Key': 'legacy-render-failure-1'})

    assert response.status_code == 503
    assert 'approved checkpoint is unavailable' in response.json()['detail']
    jobs = [job for job in client.get('/api/jobs').json() if job['id']]
    assert len(jobs) == 1
    assert jobs[0]['status'] == 'failed'
    assert 'approved checkpoint is unavailable' in jobs[0]['error']
    assert not any(item.get('job_id') == jobs[0]['id'] for item in client.get('/api/assets').json())


def test_legacy_vault_worker_registers_each_pack_under_parent_job(client, monkeypatch, tmp_path):
    import studio.api_v2 as api_v2
    import studio.diffusion_engine as diffusion_engine

    persona = client.post('/api/personas', json={
        'name': 'Vault Bridge', 'age': 31,
        'appearance': 'wavy dark hair and hazel eyes',
        'description': 'fictional adult glamour creator'
    }).json()
    render_dir = tmp_path / 'renders'
    render_dir.mkdir()
    monkeypatch.setattr(api_v2, 'ROOT', tmp_path)
    monkeypatch.setattr(api_v2, 'JOBS_CACHE_FILE', tmp_path / 'vault-jobs.json')
    monkeypatch.setattr(diffusion_engine, 'RENDERS_DIR', render_dir)
    calls = []

    def fake_generate_render(**kwargs):
        assert kwargs['register_asset'] is False
        index = len(calls) + 1
        calls.append(index)
        filename = f'render_vault_{index}.png'
        Image.new('RGB', (24, 24), 'beige').save(render_dir / filename, format='PNG')
        return {'filename': filename}

    monkeypatch.setattr(diffusion_engine, 'generate_render', fake_generate_render)
    job_id = 'vault_test_parent_job'
    specs = [{'filename': f'pack_{index:02d}.png', 'label': f'Pack {index}', 'prompt': f'Pack prompt {index}'} for index in range(1, 14)]
    api_v2._vault_jobs[job_id] = {
        'job_id': job_id, 'persona_id': persona['id'], 'persona_name': persona['name'],
        'status': 'starting', 'current_index': 1, 'total_packs': 13,
        'current_pack_name': 'Starting', 'completed_packs': [], 'percent': 0,
        'start_time': 0, 'start_time_str': '00:00:00', 'elapsed_seconds': 0,
        'elapsed_str': '0s', 'remaining_seconds': 0, 'remaining_str': '0s',
        'asset_ids': [], 'error': None,
    }
    try:
        api_v2._run_vault_generation_background(job_id, persona['id'], specs)
    finally:
        api_v2._vault_jobs.pop(job_id, None)

    assets = [item for item in client.get('/api/assets').json() if item['job_id'] == job_id]
    assert len(assets) == 13
    assert all(item['review'] == 'pending' for item in assets)
    assert all(json.loads(item['metadata_json'])['lineage']['execution_mode'] == 'legacy_master_vault' for item in assets)
    job = next(item for item in client.get('/api/jobs').json() if item['id'] == job_id)
    assert job['status'] == 'completed'
    assert len(job['result']['asset_ids']) == 13
    assert len(calls) == 13


def test_legacy_vault_worker_honors_canonical_cancel_state(client, monkeypatch, tmp_path):
    import studio.api_v2 as api_v2
    import studio.database as test_db
    import studio.diffusion_engine as diffusion_engine

    persona = client.post('/api/personas', json={
        'name': 'Cancelled Vault', 'age': 31,
        'appearance': 'wavy dark hair and hazel eyes',
        'description': 'fictional adult glamour creator'
    }).json()
    monkeypatch.setattr(api_v2, 'ROOT', tmp_path)
    monkeypatch.setattr(api_v2, 'JOBS_CACHE_FILE', tmp_path / 'vault-jobs.json')
    calls = []

    def should_not_render(**kwargs):
        calls.append(kwargs)
        raise AssertionError('cancelled Vault job must not start another render')

    monkeypatch.setattr(diffusion_engine, 'generate_render', should_not_render)
    job_id = 'vault_cancelled_parent_job'
    specs = [{'filename': 'pack_01.png', 'label': 'Pack 1', 'prompt': 'Pack prompt 1'}]
    api_v2._vault_jobs[job_id] = {
        'job_id': job_id, 'persona_id': persona['id'], 'persona_name': persona['name'],
        'status': 'starting', 'current_index': 1, 'total_packs': 1,
        'current_pack_name': 'Starting', 'completed_packs': [], 'percent': 0,
        'start_time': 0, 'start_time_str': '00:00:00', 'elapsed_seconds': 0,
        'elapsed_str': '0s', 'remaining_seconds': 0, 'remaining_str': '0s',
        'asset_ids': [], 'error': None,
    }
    api_v2._ensure_vault_job_record(job_id, persona['id'], specs)
    test_db.write("UPDATE jobs SET status='cancelled', cancel_requested=1 WHERE id=?", (job_id,))
    try:
        api_v2._run_vault_generation_background(job_id, persona['id'], specs)
    finally:
        api_v2._vault_jobs.pop(job_id, None)

    job = next(item for item in client.get('/api/jobs').json() if item['id'] == job_id)
    assert job['status'] == 'cancelled'
    assert job['result']['error'] == 'Cancelled by operator'
    assert calls == []


def test_import_local_pipeline_output_requires_disclosure_and_starts_pending_review(client):
    persona = client.post('/api/personas', json={
        'name': 'Tala Reed', 'age': 31,
        'appearance': 'dark bob haircut and hazel eyes',
        'description': 'fictional adult lifestyle creator'
    }).json()
    payload = b'fake mp4 bytes'
    denied = client.post('/api/assets/import', data={
        'persona_id': persona['id'], 'kind': 'video', 'prompt': 'Wan2.2 episode output',
        'disclosure': 'Fictional adult character. AI-generated synthetic media.'
    }, files={'file': ('episode.mp4', payload, 'video/mp4')})
    assert denied.status_code == 400
    imported = client.post('/api/assets/import', data={
        'persona_id': persona['id'], 'kind': 'video', 'prompt': 'Wan2.2 episode output',
        'disclosure': 'Fictional adult character. AI-generated synthetic media.', 'rights_confirmed': 'true'
    }, files={'file': ('episode.mp4', payload, 'video/mp4')})
    assert imported.status_code == 201
    asset = client.get('/api/assets').json()[0]
    assert asset['review'] == 'pending'
    assert 'AI-generated' in asset['disclosure']
    assert client.get(imported.json()['url']).content == payload
    assert asset['filename'].startswith('asset_')
    assert (db.OUTPUTS / asset['filename']).is_file()
    (db.OUTPUTS / asset['filename']).unlink()
    assert client.get(imported.json()['url']).status_code == 404


def test_monitor_reports_control_plane_runtime_models_and_storage(client):
    response = client.get('/api/monitor')
    assert response.status_code == 200
    payload = response.json()
    assert payload['overall']['status'] in {'ready', 'degraded', 'error'}
    assert payload['api']['status'] == 'ready'
    assert payload['database']['status'] == 'ready'
    assert 'storage' in payload and 'free_gb' in payload['storage']
    assert isinstance(payload['connections'], list)
    assert isinstance(payload['runtime'], list)
    assert isinstance(payload['models'], list)
    assert 'ready_count' in payload['workflows']
    assert 'active' in payload['queue']


def test_phase6_model_registry_and_capability_preflight(client, monkeypatch):
    import shutil
    import studio.preflight as resource_checks
    monkeypatch.setattr(resource_checks.shutil, 'disk_usage', lambda path: shutil._ntuple_diskusage(500 * 1024 ** 3, 450 * 1024 ** 3, 50 * 1024 ** 3))
    models = client.get('/api/models')
    assert models.status_code == 200
    flux = next(item for item in models.json() if item['id'] == 'flux2-klein-4b')
    assert 'image.text_to_image' in flux['capabilities']
    assert flux['revision_pinned'] is False
    response = client.get('/api/preflight?workflow_id=flux2_klein_txt2img&width=769&height=1152')
    assert response.status_code == 200
    checks = {item['id']: item for item in response.json()['checks']}
    assert checks['model_capability']['status'] == 'ready'
    assert checks['canvas']['status'] == 'error'
    engines = client.get('/api/engines').json()
    assert {item['id'] for item in engines} >= {'direct-cli', 'comfyui'}
    readiness = client.get('/api/readiness?profile=local')
    assert readiness.status_code == 200
    assert readiness.json()['profile'] == 'local'
    assert readiness.json()['status'] in {'ready', 'warning', 'blocked'}
    cloud_readiness = client.get('/api/readiness?profile=cloud')
    assert cloud_readiness.status_code == 200
    assert cloud_readiness.json()['status'] == 'blocked'
    assert any(item['code'] == 'auth' for item in cloud_readiness.json()['blockers'])


def test_phase4_resource_preflight_and_queue_gate(client, monkeypatch):
    import json
    import shutil
    import studio.app as backend
    import studio.preflight as resource_checks

    monkeypatch.setattr(resource_checks, '_memory_snapshot', lambda: (16 * 1024 ** 3, 12 * 1024 ** 3))
    monkeypatch.setattr(resource_checks.shutil, 'disk_usage', lambda path: shutil._ntuple_diskusage(500 * 1024 ** 3, 450 * 1024 ** 3, 50 * 1024 ** 3))
    ready = resource_checks.resource_preflight('image_resource_test', 768, 1152)
    assert {item['id'] for item in ready} == {'resource_disk', 'resource_memory'}
    assert all(item['status'] == 'ready' for item in ready)

    monkeypatch.setattr(resource_checks.shutil, 'disk_usage', lambda path: shutil._ntuple_diskusage(20 * 1024 ** 3, 19 * 1024 ** 3, 1 * 1024 ** 3))
    low_disk = resource_checks.resource_preflight('image_resource_test', 768, 1152)
    assert next(item for item in low_disk if item['id'] == 'resource_disk')['status'] == 'error'

    persona = client.post('/api/personas', json={
        'name': 'Resource Gate', 'age': 29,
        'appearance': 'short dark hair and brown eyes',
        'description': 'fictional adult editorial creator'
    }).json()
    workflow = resource_checks.db.WORKFLOWS / 'resource_gate.json'
    workflow.write_text(json.dumps({'1': {'class_type': 'SaveImage', 'inputs': {}}}))
    monkeypatch.setattr(backend, 'resource_preflight', lambda **kwargs: [{'id': 'resource_memory', 'status': 'error', 'detail': 'Synthetic low-memory condition'}])
    response = client.post('/api/jobs', json={
        'persona_id': persona['id'], 'workflow_id': 'resource_gate',
        'prompt': 'A resource-gated portrait', 'rights_confirmed': True
    })
    assert response.status_code == 409
    assert 'Resource preflight failed' in response.json()['detail']


def test_workflow_upload_requires_api_json(client):
    bad = client.post('/api/workflows',data={"label":"bad"},files={"file":("workflow.json", b'{"nodes":[]}',"application/json")})
    assert bad.status_code == 400
    good = client.post('/api/workflows',data={"label":"wan-video"},files={"file":(
        "workflow.json", b'{"5":{"class_type":"SaveImage","inputs":{"images":["1",0]}}}',"application/json")})
    assert good.status_code == 201
    assert any(w['id']==good.json()['id'] for w in client.get('/api/workflows').json())


def test_generation_brief_validation(client):
    brief = {
        "schema_version": "1.0", "title": "Mira cafe reel",
        "persona": {"name": "Mira Vale", "age": 25, "appearance": "brown hair and hazel eyes",
                     "description": "fictional adult lifestyle creator", "consistency_anchor": "same face and hair"},
        "image": {"prompt": "Editorial portrait of the fictional adult character"},
        "video": {"prompt": "The same fictional adult character smiles and turns slowly"}
    }
    response = client.post('/api/briefs/validate', files={
        'file': ('brief.json', __import__('json').dumps(brief).encode(), 'application/json')
    })
    assert response.status_code == 200
    assert response.json()['persona']['name'] == 'Mira Vale'
    bad = client.post('/api/briefs/validate', files={'file': ('bad.json', b'{"title":', 'application/json')})
    assert bad.status_code == 400


def test_persona_json_import_creates_library_entry(client):
    import json
    payload = {
        "schema_version": "persona-1.0",
        "persona": {
            "name": "Nila Stone", "age": 29,
            "appearance": "short copper hair and grey eyes",
            "description": "fictional adult street-style creator",
            "consistency_anchor": {"identity_id": "NILA_001", "immutable_traits": ["copper crop", "grey eyes"]},
            "disclosure": {"public_disclosure": "Fictional AI-generated adult persona"},
            "characteristics": {"face": {"hair": "short copper crop", "eyes": {"color": "grey", "shape": "almond"}},
                                 "style": {"wardrobe": "structured denim"}, "world": {"recurring_locations": [{"name": "North Pier"}]}}
        }
    }
    response = client.post('/api/personas/import', files={
        'file': ('persona.json', json.dumps(payload).encode(), 'application/json')
    })
    assert response.status_code == 201
    assert response.json()['name'] == 'Nila Stone'
    assert response.json()['characteristics']['style']['wardrobe'] == 'structured denim'
    assert response.json()['characteristics']['face']['eyes']['color'] == 'grey'


def test_persona_freeze_and_series_plan(client):
    persona = client.post('/api/personas', json={
        'name': 'Ari Sol', 'age': 28,
        'appearance': 'short copper hair and grey eyes',
        'description': 'fictional adult fashion storyteller'
    }).json()
    pid = persona['id']
    assert persona['identity_locked'] == 0

    blocked = client.post('/api/series', json={
        'persona_id': pid, 'title': 'Harbor Notes',
        'description': 'A compact coastal fashion diary.',
        'shared_prompt': 'Keep Ari Sol canonical: copper crop, grey eyes, mineral palette, documentary editorial camera.',
        'episodes': [{'title': 'Arrival', 'prompt': 'At the harbor in a tailored coat.', 'video_prompt': 'Slow walk and a gentle camera push-in.'}]
    })
    assert blocked.status_code == 409

    frozen = client.post(f'/api/personas/{pid}/freeze')
    assert frozen.status_code == 200
    assert frozen.json()['identity_locked'] == 1
    assert frozen.json()['identity_version'] == 1
    image = Image.new('RGB', (24, 24), 'beige')
    bio = BytesIO()
    image.save(bio, format='PNG')
    assert client.post(f'/api/personas/{pid}/references', files={'file': ('late.png', bio.getvalue(), 'image/png')}, data={'rights_confirmed': 'true'}).status_code == 409

    series = client.post('/api/series', json={
        'persona_id': pid, 'title': 'Harbor Notes',
        'description': 'A compact coastal fashion diary.',
        'shared_prompt': 'Keep Ari Sol canonical: copper crop, grey eyes, mineral palette, documentary editorial camera.',
        'episodes': [
            {'title': 'Arrival', 'prompt': 'At the harbor in a tailored coat.', 'video_prompt': 'Slow walk and a gentle camera push-in.'},
            {'title': 'Textile room', 'prompt': 'Studying folded fabrics in a studio.', 'video_prompt': 'Close hand movement and a soft rack focus.'}
        ]
    })
    assert series.status_code == 201
    payload = series.json()
    assert payload['identity_locked'] == 1
    assert payload['identity_version'] == 1
    assert len(payload['episodes']) == 2
    assert payload['episodes'][0]['episode_no'] == 1
    assert 'Keep Ari Sol canonical' in payload['episodes'][1]['prompt']
    listed = client.get('/api/series').json()
    assert listed[0]['id'] == payload['id']


def test_series_queue_prefers_latest_approved_master_asset(client, monkeypatch):
    import asyncio
    import studio.app as backend
    persona = client.post('/api/personas', json={
        'name': 'Nora Pike', 'age': 30,
        'appearance': 'black hair and brown eyes',
        'description': 'fictional adult travel creator'
    }).json()
    pid = persona['id']
    client.post(f'/api/personas/{pid}/freeze')
    series = client.post('/api/series', json={
        'persona_id': pid, 'title': 'Coastal Notes', 'description': 'A coastal travel series.',
        'shared_prompt': 'Keep Nora Pike consistent in every shot.',
        'episodes': [{'title': 'Arrival', 'prompt': 'At a bright harbor.', 'video_prompt': 'Slow walk toward camera.'}]
    }).json()
    episode = series['episodes'][0]
    import studio.database as test_db
    asset_id = backend.uid()
    test_db.write('INSERT INTO assets (id,persona_id,job_id,filename,kind,prompt,review,rights_confirmed,disclosure,created_at) VALUES (?,?,?,?,?,?,?,?,?,?)',
                   (asset_id, pid, None, 'master.png', 'image', 'approved master', 'approved', 1, 'Fictional adult character. AI-generated synthetic media.', backend.now()))
    captured = {}

    async def fake_create_job(payload):
        captured['payload'] = payload
        test_db.write('INSERT INTO jobs (id,persona_id,workflow_id,type,prompt,status,created_at) VALUES (?,?,?,?,?,?,?)',
                      ('series-job-1', payload.persona_id, payload.workflow_id, 'video', payload.prompt, 'queued', backend.now()))
        return {'id': 'series-job-1', 'status': 'queued'}

    monkeypatch.setattr(backend, 'create_job', fake_create_job)
    response = asyncio.run(backend.queue_series_episode(series['id'], episode['id'], backend.SeriesQueueIn(workflow_id='wan22_video', rights_confirmed=True)))
    assert response['status'] == 'queued'
    assert captured['payload'].source_asset_id == asset_id


def test_complete_generation_lifecycle_with_mocked_comfy(client, monkeypatch):
    import asyncio
    import json
    import httpx
    import studio.app as backend
    from studio.comfy import ComfyClient

    p = client.post('/api/personas', json={"name":"Mira","age":25,
        "appearance":"wavy brown hair, brown eyes","description":"urban lifestyle creator"}).json()
    image = Image.new('RGB', (32, 32), '#56789a')
    bio = BytesIO()
    image.save(bio, format='PNG')
    png = bio.getvalue()

    def route(request):
        if request.url.path == '/prompt':
            sent = json.loads(request.content)
            assert sent['prompt']['1']['inputs']['ckpt_name'] == 'mock.safetensors'
            return httpx.Response(200, json={'prompt_id':'render123'})
        if request.url.path == '/history/render123':
            return httpx.Response(200, json={'render123':{'status':{'completed':True},
              'outputs':{'7':{'images':[{'filename':'result.png','type':'output','subfolder':''}]}}}})
        if request.url.path == '/view':
            return httpx.Response(200, content=png)
        return httpx.Response(404, json={})

    def factory():
        return ComfyClient(transport=httpx.MockTransport(route))
    monkeypatch.setattr(backend, 'ComfyClient', factory)
    import studio.database as db
    # A mocked ComfyUI graph used ONLY by tests, not provided as a generation preset.
    (db.WORKFLOWS / 'mock_comfy_workflow.json').write_text(json.dumps({
      '1':{'class_type':'MockCheckpoint','inputs':{'ckpt_name':'{{CHECKPOINT}}'}},
      '2':{'class_type':'MockText','inputs':{'text':'{{PROMPT}}'}},
      '7':{'class_type':'SaveImage','inputs':{'images':['1',0]}}
    }))
    job_payload = backend.JobIn(persona_id=p['id'], workflow_id='mock_comfy_workflow',
        prompt='Candid portrait with soft daylight', checkpoint='mock.safetensors', rights_confirmed=True)
    import studio.database as db
    jid = backend.uid()
    db.write('INSERT INTO jobs (id,persona_id,workflow_id,type,prompt,status,created_at) VALUES (?,?,?,?,?,?,?)',
        (jid,p['id'],'mock_comfy_workflow','image','portrait','queued',backend.now()))
    asyncio.run(backend.execute_job(jid,job_payload,p))
    job = client.get('/api/jobs').json()[0]
    assert job['status'] == 'completed'
    assert job['progress_stage'] == 'completed'
    assert job['progress_percent'] == 100
    assert job['progress']['children'][0]['state'] == 'completed'
    assets = client.get('/api/assets').json()
    assert len(assets) == 1
    assert 'AI-generated' in assets[0]['disclosure']
    assert client.get('/api/assets/'+assets[0]['id']+'/file').content == png
    assert client.patch('/api/assets/'+assets[0]['id']+'/review',json={'review':'approved'}).status_code == 200
    assert client.get('/api/summary').json()['approved'] == 1


def test_phase3_preflight_and_job_lineage(client, monkeypatch):
    import json
    import shutil
    import studio.database as test_db
    import studio.preflight as resource_checks

    monkeypatch.setattr(resource_checks.shutil, 'disk_usage', lambda path: shutil._ntuple_diskusage(500 * 1024 ** 3, 450 * 1024 ** 3, 50 * 1024 ** 3))
    monkeypatch.setattr(resource_checks, '_memory_snapshot', lambda: (16 * 1024 ** 3, 12 * 1024 ** 3))

    persona = client.post('/api/personas', json={
        'name': 'Phase Three', 'age': 29,
        'appearance': 'short dark hair and hazel eyes',
        'description': 'fictional adult editorial creator'
    }).json()
    workflow = test_db.WORKFLOWS / 'phase3_image.json'
    workflow.write_text(json.dumps({'1': {'class_type': 'SaveImage', 'inputs': {'images': ['1', 0]}}}))
    response = client.get('/api/preflight?workflow_id=phase3_image')
    assert response.status_code == 200
    assert response.json()['overall'] in {'ready', 'degraded'}
    queued = client.post('/api/jobs', json={
        'persona_id': persona['id'], 'workflow_id': 'phase3_image',
        'prompt': 'A carefully lit editorial portrait', 'rights_confirmed': True
    })
    assert queued.status_code == 202
    jobs = client.get('/api/jobs').json()
    assert jobs[0]['lineage']['persona_id'] == persona['id']
    assert jobs[0]['lineage']['workflow_id'] == 'phase3_image'
    assert jobs[0]['attempt'] == 1


def test_generation_job_rejects_server_side_workflow_preflight_error(client, monkeypatch):
    import json
    import studio.app as backend
    import studio.database as test_db

    persona = client.post('/api/personas', json={
        'name': 'Server Gate', 'age': 29,
        'appearance': 'short dark hair and brown eyes',
        'description': 'fictional adult editorial creator'
    }).json()
    workflow = test_db.WORKFLOWS / 'phase10_gate.json'
    workflow.write_text(json.dumps({'1': {'class_type': 'SaveImage', 'inputs': {}}}))
    monkeypatch.setattr(backend, 'resource_preflight', lambda **kwargs: [
        {'id': 'resource_disk', 'status': 'ready', 'detail': 'Synthetic resource readiness'}
    ])
    monkeypatch.setattr(backend, 'workflow_preflight', lambda *args, **kwargs: [
        {'id': 'model_capability', 'status': 'error', 'detail': 'Synthetic workflow preflight failure'}
    ])

    response = client.post('/api/jobs', json={
        'persona_id': persona['id'], 'workflow_id': 'phase10_gate',
        'prompt': 'A server-gated editorial portrait', 'rights_confirmed': True
    })

    assert response.status_code == 409
    assert 'Synthetic workflow preflight failure' in response.json()['detail']
    assert client.get('/api/jobs').json() == []


def test_phase4_durable_dispatcher_picks_up_persisted_queue_row(client, monkeypatch):
    import asyncio
    import studio.app as backend
    import studio.database as test_db

    persona = client.post('/api/personas', json={
        'name': 'Dispatcher Persona', 'age': 29,
        'appearance': 'short dark hair and hazel eyes',
        'description': 'fictional adult editorial creator'
    }).json()
    payload = backend.JobIn(
        persona_id=persona['id'], workflow_id='dispatcher_test',
        prompt='A queued dispatcher test', rights_confirmed=True
    )
    job_id = backend.uid()
    backend.JobRepository.create(
        job_id=job_id, persona_id=persona['id'], workflow_id=payload.workflow_id,
        kind='image', prompt=payload.prompt, request_json=payload.model_dump_json(),
        lineage_json=json.dumps({'workflow_id': payload.workflow_id}), created_at=backend.now()
    )
    calls = []

    async def fake_execute(job_id_arg, payload_arg, person_arg):
        calls.append((job_id_arg, payload_arg.workflow_id, person_arg['id']))
        test_db.write(
            "UPDATE jobs SET status='completed', result_json=?, finished_at=?, updated_at=? WHERE id=?",
            (json.dumps({'job_id': job_id_arg, 'dispatcher': True}), backend.now(), backend.now(), job_id_arg),
        )

    monkeypatch.setattr(backend, 'execute_job', fake_execute)
    backend._job_task(job_id, payload, persona)

    async def wait_for_dispatch():
        for _ in range(50):
            if test_db.row("SELECT status FROM jobs WHERE id=?", (job_id,))['status'] == 'completed':
                return
            await asyncio.sleep(0.01)
        raise AssertionError('durable dispatcher did not execute the persisted queue row')

    asyncio.run(wait_for_dispatch())
    assert calls == [(job_id, 'dispatcher_test', persona['id'])]
    assert client.get('/api/jobs').json()[0]['result']['dispatcher'] is True


def test_phase4_restart_preserves_durable_queued_row(client):
    import studio.app as backend
    import studio.database as test_db

    persona = client.post('/api/personas', json={
        'name': 'Restart Queue Persona', 'age': 30,
        'appearance': 'dark hair and hazel eyes',
        'description': 'fictional adult editorial creator'
    }).json()
    job_id = backend.uid()
    backend.JobRepository.create(
        job_id=job_id, persona_id=persona['id'], workflow_id='restart_queue_test',
        kind='image', prompt='A queued restart test', request_json='{}',
        lineage_json='{}', created_at=backend.now(),
    )
    test_db.write("UPDATE jobs SET status='queued', next_retry_at=? WHERE id=?", ('2999-01-01T00:00:00+00:00', job_id))
    test_db.initialize()
    row = test_db.row("SELECT status,next_retry_at,worker_id,lease_expires_at FROM jobs WHERE id=?", (job_id,))
    assert row['status'] == 'queued'
    assert row['next_retry_at'] == '2999-01-01T00:00:00+00:00'
    assert row['worker_id'] is None
    assert row['lease_expires_at'] is None


def test_phase4_shutdown_reconciles_only_active_managed_jobs(client):
    import studio.app as backend
    import studio.database as test_db

    persona = client.post('/api/personas', json={
        'name': 'Shutdown Persona', 'age': 30,
        'appearance': 'dark hair and hazel eyes',
        'description': 'fictional adult editorial creator'
    }).json()
    active_job_id = backend.uid()
    queued_job_id = backend.uid()
    for job_id, status in ((active_job_id, 'running'), (queued_job_id, 'queued')):
        backend.JobRepository.create(
            job_id=job_id, persona_id=persona['id'], workflow_id='shutdown_test',
            kind='image', prompt='A shutdown recovery test', request_json='{}',
            lineage_json='{}', created_at=backend.now(),
        )
        test_db.write("UPDATE jobs SET status=? WHERE id=?", (status, job_id))

    assert backend._mark_shutdown_jobs_interrupted([active_job_id, queued_job_id]) == 1
    active = test_db.row("SELECT status,error FROM jobs WHERE id=?", (active_job_id,))
    queued = test_db.row("SELECT status,error FROM jobs WHERE id=?", (queued_job_id,))
    assert active['status'] == 'interrupted'
    assert 'Studio stopped' in active['error']
    assert queued['status'] == 'queued'
    assert queued['error'] is None


def test_phase4_standalone_diffusion_registration_uses_canonical_asset_store(client):
    from io import BytesIO
    import studio.app as backend
    import studio.database as test_db
    import studio.diffusion_engine as diffusion_engine
    from PIL import Image

    persona = client.post('/api/personas', json={
        'name': 'Diffusion Boundary Persona', 'age': 31,
        'appearance': 'dark hair and green eyes',
        'description': 'fictional adult editorial creator'
    }).json()
    image = Image.new('RGB', (24, 24), '#456789')
    buffer = BytesIO()
    image.save(buffer, format='PNG')

    asset = diffusion_engine._register_render_asset(
        persona_id=persona['id'], persona_name=persona['name'],
        prompt='A canonical diffusion boundary test', raw=buffer.getvalue(),
        original_filename='legacy_render.png', model_id='test-model', seed=42,
        aspect_ratio='1:1', width=24, height=24,
    )
    assert asset['review'] == 'pending'
    assert asset['rights_confirmed'] == 0
    assert asset['persona_version_id'] == persona['current_version']['id']
    assert test_db.OUTPUTS.joinpath(asset['filename']).is_file()
    assert backend.app.url_path_for('asset_file', aid=asset['id']) == f"/api/assets/{asset['id']}/file"


def test_phase4_free_cli_registers_output_with_persona_version(client, tmp_path, capsys):
    from types import SimpleNamespace
    import studio.free_cli as free_cli
    import studio.database as test_db
    from PIL import Image

    persona = client.post('/api/personas', json={
        'name': 'CLI Boundary Persona', 'age': 32,
        'appearance': 'dark hair and brown eyes',
        'description': 'fictional adult editorial creator'
    }).json()
    output = tmp_path / 'cli-output.png'
    Image.new('RGB', (24, 24), '#789abc').save(output, format='PNG')

    asset = free_cli.register_output(SimpleNamespace(
        persona_id=persona['id'], file=str(output), kind='image',
        prompt='A free CLI registration test', disclosure='Fictional adult character. AI-generated synthetic media.',
        rights_confirmed=False,
    ))
    assert asset['persona_version_id'] == persona['current_version']['id']
    assert asset['review'] == 'pending'
    assert asset['rights_confirmed'] is False
    assert test_db.OUTPUTS.joinpath(test_db.row('SELECT filename FROM assets WHERE id=?', (asset['id'],))['filename']).is_file()
    assert asset['url'] == f"/api/assets/{asset['id']}/file"
    assert asset['id'] in capsys.readouterr().out


def test_phase4_job_lease_recovery_and_retry_backoff(client, monkeypatch):
    import datetime
    import studio.app as backend
    import studio.database as test_db

    persona = client.post('/api/personas', json={
        'name': 'Lease Persona', 'age': 31,
        'appearance': 'long dark hair and brown eyes',
        'description': 'fictional adult editorial creator'
    }).json()
    payload = backend.JobIn(
        persona_id=persona['id'], workflow_id='lease_test',
        prompt='A lease recovery test', rights_confirmed=True
    )
    expired_job_id = backend.uid()
    test_db.write(
        "INSERT INTO jobs (id,persona_id,workflow_id,type,prompt,status,created_at,worker_id,heartbeat_at,lease_expires_at) "
        "VALUES (?,?,?,?,?,?,?,?,?,?)",
        (expired_job_id, persona['id'], payload.workflow_id, 'image', payload.prompt, 'running', backend.now(),
         'stale-worker', backend.now(), '2000-01-01T00:00:00+00:00'),
    )

    # The supervisor performs this same recovery before dispatching queued work.
    backend._recover_expired_jobs()
    recovered = test_db.row("SELECT status,worker_id,heartbeat_at,lease_expires_at,error FROM jobs WHERE id=?", (expired_job_id,))
    assert recovered['status'] == 'interrupted'
    assert recovered['worker_id'] is None
    assert recovered['heartbeat_at'] is None
    assert recovered['lease_expires_at'] is None
    assert 'lease expired' in recovered['error']

    retry_job_id = backend.uid()
    backend.JobRepository.create(
        job_id=retry_job_id, persona_id=persona['id'], workflow_id=payload.workflow_id,
        kind='image', prompt=payload.prompt, request_json=payload.model_dump_json(),
        lineage_json='{}', created_at=backend.now(),
    )
    test_db.write("UPDATE jobs SET status='failed', error=? WHERE id=?", ('Synthetic failure', retry_job_id))
    response = client.post(f'/api/jobs/{retry_job_id}/retry')
    assert response.status_code == 202
    body = response.json()
    assert body['attempt'] == 2
    assert body['retry_after_seconds'] == 5
    assert datetime.datetime.fromisoformat(body['next_retry_at']) > datetime.datetime.now(datetime.timezone.utc)
    queued = test_db.row("SELECT status,next_retry_at,worker_id,heartbeat_at,lease_expires_at FROM jobs WHERE id=?", (retry_job_id,))
    assert queued['status'] == 'queued'
    assert queued['next_retry_at'] == body['next_retry_at']
    assert queued['worker_id'] is None
    assert queued['heartbeat_at'] is None
    assert queued['lease_expires_at'] is None


def test_phase4_reconciles_completed_comfy_prompt_without_duplicate_assets(client, monkeypatch):
    import asyncio
    import httpx
    import studio.app as backend
    import studio.database as test_db
    from studio.comfy import ComfyClient

    persona = client.post('/api/personas', json={
        'name': 'Recovery Persona', 'age': 28,
        'appearance': 'short dark hair and hazel eyes',
        'description': 'fictional adult editorial creator'
    }).json()
    payload = backend.JobIn(
        persona_id=persona['id'], workflow_id='recovery_test',
        prompt='A recovered editorial portrait', rights_confirmed=True
    )
    job_id = backend.uid()
    backend.JobRepository.create(
        job_id=job_id, persona_id=persona['id'], workflow_id=payload.workflow_id,
        kind='image', prompt=payload.prompt, request_json=payload.model_dump_json(),
        lineage_json='{}', created_at=backend.now(),
    )
    test_db.write(
        "UPDATE jobs SET status='interrupted', comfy_prompt_id=?, error=? WHERE id=?",
        ('reconcile123', 'App restarted during job; retry from Studio', job_id),
    )
    image = Image.new('RGB', (24, 24), '#345678')
    bio = BytesIO()
    image.save(bio, format='PNG')
    png = bio.getvalue()

    def route(request):
        if request.url.path == '/history/reconcile123':
            return httpx.Response(200, json={'reconcile123': {
                'status': {'completed': True, 'status_str': 'success'},
                'outputs': {'7': {'images': [{'filename': 'recovered.png', 'type': 'output', 'subfolder': ''}]}}
            }})
        if request.url.path == '/view':
            return httpx.Response(200, content=png)
        return httpx.Response(404, json={})

    monkeypatch.setattr(backend, 'ComfyClient', lambda: ComfyClient(transport=httpx.MockTransport(route)))
    asyncio.run(backend._reconcile_interrupted_prompts())
    completed = test_db.row("SELECT status,result_json,error FROM jobs WHERE id=?", (job_id,))
    result = json.loads(completed['result_json'])
    assert completed['status'] == 'completed'
    assert result['reconciled'] is True
    assert len(result['asset_ids']) == 1
    assert test_db.row("SELECT COUNT(*) AS count FROM assets WHERE job_id=?", (job_id,))['count'] == 1

    # A second reconciliation pass is a no-op because the canonical Job is complete.
    asyncio.run(backend._reconcile_interrupted_prompts())
    assert test_db.row("SELECT COUNT(*) AS count FROM assets WHERE job_id=?", (job_id,))['count'] == 1


def test_phase5_asset_manifest_and_approved_export_package(client):
    import io
    import zipfile

    persona = client.post('/api/personas', json={
        'name': 'Export Ready', 'age': 32,
        'appearance': 'short black hair and green eyes',
        'description': 'fictional adult fashion creator'
    }).json()
    imported = client.post('/api/assets/import', data={
        'persona_id': persona['id'], 'kind': 'video', 'prompt': 'Imported reviewed episode output',
        'disclosure': 'Fictional adult character. AI-generated synthetic media.', 'rights_confirmed': 'true',
        'content_class': 'adult glamour', 'destination_policy': 'review_required'
    }, files={'file': ('episode.mp4', b'fake mp4 bytes', 'video/mp4')})
    assert imported.status_code == 201
    aid = imported.json()['id']
    manifest = client.get('/api/assets/' + aid + '/manifest')
    assert manifest.status_code == 200
    assert manifest.json()['schema_version'] == 'asset-manifest-1.0'
    assert manifest.json()['asset']['sha256']
    quality = client.post('/api/assets/' + aid + '/quality')
    assert quality.status_code == 200
    assert any(check['id'] == 'rights' and check['status'] == 'ready' for check in quality.json()['quality']['checks'])
    assert any(check['id'] == 'container' and check['status'] == 'warning' for check in quality.json()['quality']['checks'])
    assert any(check['id'] == 'content_class' and check['status'] == 'ready' for check in quality.json()['quality']['checks'])
    assert any(check['id'] == 'destination_policy' and check['status'] == 'warning' for check in quality.json()['quality']['checks'])
    stored_before_review = next(item for item in client.get('/api/assets').json() if item['id'] == aid)
    assert stored_before_review['content_class'] == 'adult_glamour'
    assert stored_before_review['destination_policy'] == 'review_required'
    assert client.get('/api/assets/' + aid + '/package').status_code == 409
    approved = client.patch('/api/assets/' + aid + '/review', json={
        'review': 'approved', 'reviewer': 'qa_operator',
        'reason': 'Integrity, disclosure, rights, and provenance review passed.',
    })
    assert approved.status_code == 200
    assert approved.json()['reviewer'] == 'qa_operator'
    assert approved.json()['review_reason'].startswith('Integrity')
    stored = next(item for item in client.get('/api/assets').json() if item['id'] == aid)
    assert stored['reviewed_at']
    assert stored['reviewer'] == 'qa_operator'
    assert stored['review_reason'].startswith('Integrity')
    package = client.get('/api/assets/' + aid + '/package')
    assert package.status_code == 200
    with zipfile.ZipFile(io.BytesIO(package.content)) as archive:
        assert {'manifest.json', 'AI-DISCLOSURE.txt'} <= set(archive.namelist())
        exported_manifest = json.loads(archive.read('manifest.json'))
        assert exported_manifest['asset']['content_class'] == 'adult_glamour'
        assert exported_manifest['asset']['destination_policy'] == 'review_required'


def test_phase7_strict_media_quality_blocks_unverified_container(client, monkeypatch):
    from studio.assets import register_media_asset

    persona = client.post('/api/personas', json={
        'name': 'Strict Media', 'age': 30,
        'appearance': 'short dark hair and brown eyes',
        'description': 'fictional adult creator for media validation'
    }).json()
    monkeypatch.setenv('STUDIO_STRICT_MEDIA', '1')
    asset = register_media_asset(
        persona_id=persona['id'], persona_version_id=None, job_id=None,
        kind='video', prompt='Strict media fixture', raw=b'not a video container',
        disclosure='Fictional adult character. AI-generated synthetic media.',
        rights_confirmed=True, original_filename='strict.mp4',
        lineage={'source': 'test'},
    )
    quality = client.post(f"/api/assets/{asset['id']}/quality")
    assert quality.status_code == 200
    assert quality.json()['quality']['status'] == 'error'
    assert any(check['id'] == 'container' and check['status'] == 'error' for check in quality.json()['quality']['checks'])
    approval = client.patch(f"/api/assets/{asset['id']}/review", json={'review': 'approved'})
    assert approval.status_code == 409
    assert 'integrity' in approval.json()['detail'].lower()


def test_phase7_operator_quality_assessment_persists_and_requires_rereview(client):
    from studio.assets import register_media_asset

    persona = client.post('/api/personas', json={
        'name': 'Assessment Review', 'age': 29,
        'appearance': 'long dark hair and hazel eyes',
        'description': 'fictional adult glamour creator for review assessment'
    }).json()
    image = Image.new('RGB', (32, 32), 'beige')
    buffer = BytesIO()
    image.save(buffer, format='PNG')
    asset = register_media_asset(
        persona_id=persona['id'], persona_version_id=None, job_id=None,
        kind='image', prompt='Quality assessment fixture', raw=buffer.getvalue(),
        disclosure='Fictional adult character. AI-generated synthetic media.',
        rights_confirmed=True, original_filename='assessment.png',
        content_class='adult_glamour', destination_policy='review_required',
        lineage={'source': 'test'},
    )
    passing = client.post(f"/api/assets/{asset['id']}/assessment", json={
        'identity_score': 0.92, 'anatomy_score': 0.88, 'hands_score': 0.84,
        'facial_drift_score': 0.91, 'evaluator': 'qa_operator', 'notes': 'All visible anatomy and identity checks passed.'
    })
    assert passing.status_code == 200
    assert passing.json()['quality']['status'] == 'warning'
    assert any(check['id'] == 'identity_similarity' and check['status'] == 'ready' for check in passing.json()['quality']['checks'])
    approved = client.patch(f"/api/assets/{asset['id']}/review", json={'review': 'approved', 'reason': 'Assessment passed'})
    assert approved.status_code == 200

    failing = client.post(f"/api/assets/{asset['id']}/assessment", json={
        'identity_score': 0.42, 'anatomy_score': 0.88, 'hands_score': 0.84,
        'facial_drift_score': 0.91, 'evaluator': 'qa_operator', 'notes': 'Identity drift detected.'
    })
    assert failing.status_code == 200
    assert failing.json()['review'] == 'pending'
    assert failing.json()['quality']['status'] == 'error'
    assert any(check['id'] == 'identity_similarity' and check['status'] == 'error' for check in failing.json()['quality']['checks'])
    blocked = client.patch(f"/api/assets/{asset['id']}/review", json={'review': 'approved'})
    assert blocked.status_code == 409


def test_phase7_publishing_readiness_requires_frozen_identity_policy_and_quality(client):
    persona = client.post('/api/personas', json={
        'name': 'Publishing Gate', 'age': 31,
        'appearance': 'wavy brown hair and green eyes',
        'description': 'fictional adult glamour creator for readiness checks'
    }).json()
    frozen = client.post(f"/api/personas/{persona['id']}/freeze")
    assert frozen.status_code == 200
    image = Image.new('RGB', (32, 32), 'ivory')
    buffer = BytesIO()
    image.save(buffer, format='PNG')
    imported = client.post('/api/assets/import', data={
        'persona_id': persona['id'], 'kind': 'image', 'prompt': 'Publishing readiness image',
        'content_class': 'adult_glamour', 'destination_policy': 'eligible',
        'disclosure': 'Fictional adult character. AI-generated synthetic media.', 'rights_confirmed': 'true',
    }, files={'file': ('readiness.png', buffer.getvalue(), 'image/png')})
    assert imported.status_code == 201
    aid = imported.json()['id']
    before = client.get(f'/api/assets/{aid}/publishing-readiness')
    assert before.status_code == 200
    assert before.json()['status'] == 'blocked'
    assessment = client.post(f'/api/assets/{aid}/assessment', json={
        'identity_score': 0.95, 'anatomy_score': 0.9, 'hands_score': 0.9,
        'facial_drift_score': 0.95, 'evaluator': 'qa_operator',
    })
    assert assessment.status_code == 200
    approved = client.patch(f'/api/assets/{aid}/review', json={'review': 'approved', 'reason': 'Publishing readiness gate passed'})
    assert approved.status_code == 200
    ready = client.get(f'/api/assets/{aid}/publishing-readiness')
    assert ready.status_code == 200
    assert ready.json()['ready'] is True
    assert ready.json()['status'] == 'ready'


def test_photo_studio_presets(client):
    res = client.get('/api/photo-studio/presets')
    assert res.status_code == 200
    data = res.json()
    assert 'locations' in data
    assert 'costumes' in data
    assert 'expressions' in data
    assert 'angles' in data
    assert 'aspect_ratios' in data
    assert len(data['locations']) >= 4
    assert len(data['costumes']) >= 4


def test_photo_studio_compile_prompt(client):
    persona = client.post('/api/personas', json={
        'name': 'Lena Hartmann', 'age': 27,
        'appearance': 'hazel-green eyes with amber flecks, tiny crescent freckle below left eye, wavy dark chestnut hair, defined cheekbones',
        'description': 'fictional German creator'
    }).json()

    res = client.post('/api/photo-studio/compile-prompt', json={
        'persona_id': persona['id'],
        'location': 'Amalfi beach',
        'costume': 'black string bikini',
        'expression': 'confident editorial gaze',
        'angle': 'full body editorial shot',
    })
    assert res.status_code == 200
    data = res.json()
    assert 'Lena Hartmann' in data['prompt']
    assert '27yo woman' in data['prompt']
    assert 'black string bikini' in data['prompt']
    assert 'Amalfi beach' in data['prompt']
    assert 'crescent freckle' in data['prompt']
    assert 'anime' in data['negative_prompt']
    assert 'cartoon' in data['negative_prompt']
    assert data['token_estimate'] > 10

