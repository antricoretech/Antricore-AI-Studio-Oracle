from io import BytesIO

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
    assert client.get(r.json()['url']).status_code == 200
    w = client.get('/api/workflows').json()
    assert isinstance(w, list)
    job = {"persona_id":pid,"workflow_id":"nonexistent_imported_workflow","prompt":"By a sunny café terrace",
           "checkpoint":"sdxl_base.safetensors", "reference_id":r.json()['id']}
    assert client.post('/api/jobs',json=job).status_code == 400
    assert client.get('/api/summary').json()['personas'] == 1


def test_link_redirect_and_review_validation(client):
    assert client.post('/api/links', json={"label": "Test", "destination": "http://example.com/"}).status_code == 400
    r = client.post('/api/links', json={"label": "Landing", "destination": "https://example.com/landing"})
    assert r.status_code == 201
    code = r.json()['code']
    assert client.get('/go/'+code,follow_redirects=False).status_code == 302
    assert client.get('/api/links').json()[0]['clicks'] == 1
    assert client.patch('/api/assets/fake/review',json={"review":"approved"}).status_code == 404


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
    assets = client.get('/api/assets').json()
    assert len(assets) == 1
    assert 'AI-generated' in assets[0]['disclosure']
    assert client.get('/api/assets/'+assets[0]['id']+'/file').content == png
    assert client.patch('/api/assets/'+assets[0]['id']+'/review',json={'review':'approved'}).status_code == 200
    assert client.get('/api/summary').json()['approved'] == 1


def test_phase3_preflight_and_job_lineage(client):
    import json
    import studio.database as test_db

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
        'disclosure': 'Fictional adult character. AI-generated synthetic media.', 'rights_confirmed': 'true'
    }, files={'file': ('episode.mp4', b'fake mp4 bytes', 'video/mp4')})
    assert imported.status_code == 201
    aid = imported.json()['id']
    manifest = client.get('/api/assets/' + aid + '/manifest')
    assert manifest.status_code == 200
    assert manifest.json()['schema_version'] == 'asset-manifest-1.0'
    assert manifest.json()['asset']['sha256']
    assert client.get('/api/assets/' + aid + '/package').status_code == 409
    approved = client.patch('/api/assets/' + aid + '/review', json={'review': 'approved'})
    assert approved.status_code == 200
    package = client.get('/api/assets/' + aid + '/package')
    assert package.status_code == 200
    with zipfile.ZipFile(io.BytesIO(package.content)) as archive:
        assert {'manifest.json', 'AI-DISCLOSURE.txt'} <= set(archive.namelist())
