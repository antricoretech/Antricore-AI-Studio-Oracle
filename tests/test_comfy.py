import asyncio
import json
from pathlib import Path

import httpx
import pytest

from studio.comfy import ComfyClient, output_files, render_graph, validate_graph

ROOT = Path(__file__).resolve().parents[1]


def test_default_workflows_are_valid_api():
    for p in (ROOT / "workflows").glob("*.json"):
        graph = json.loads(p.read_text())
        assert validate_graph(graph)
        assert all("inputs" in node for node in graph.values())


def test_typed_template_substitution():
    graph = {
      '1':{'class_type':'MockCheckpoint','inputs':{'name':'{{CHECKPOINT}}'}},
      '2':{'class_type':'MockImage','inputs':{'image':'{{REFERENCE_IMAGE}}'}},
      '3':{'class_type':'MockEmptyLatent','inputs':{'width':'{{WIDTH}}','height':'{{HEIGHT}}'}},
      '7':{'class_type':'MockSampler','inputs':{'seed':'{{SEED}}','text':'{{PROMPT}}'}}
    }
    output = render_graph(graph, {'CHECKPOINT':'mock.safetensors','PROMPT':'Adult fictional character',
        'REFERENCE_IMAGE':'master.png','WIDTH':768,'HEIGHT':1152,'SEED':1234})
    assert output['3']['inputs']['width'] == 768
    assert isinstance(output['7']['inputs']['seed'], int)
    assert output['2']['inputs']['image'] == 'master.png'
    assert graph['2']['inputs']['image'] == '{{REFERENCE_IMAGE}}'


def test_reject_canvas_export():
    with pytest.raises(ValueError, match="API"):
        validate_graph({"nodes": [{"type": "SaveImage"}]})


def test_output_files_handles_multiple_save_nodes():
    assert len(output_files({"7": {"images": [{"filename": "x.png", "type": "output"}]},
                             "8": {"gifs": [{"filename": "y.mp4", "type": "output"}]}})) == 2


@pytest.mark.asyncio
async def test_mock_comfy_api_flow():
    def handle(request):
        if request.url.path == "/system_stats":
            return httpx.Response(200, json={"devices": []})
        if request.url.path == "/upload/image":
            return httpx.Response(200, json={"name": "uploaded_ref.png"})
        if request.url.path == "/prompt":
            body = json.loads(request.content)
            assert body["prompt"]["2"]["inputs"]["text"] == "A cinematic photo"
            return httpx.Response(200, json={"prompt_id": "mockid"})
        if request.url.path == "/history/mockid":
            return httpx.Response(200, json={"mockid": {"status": {"completed": True},
                "outputs": {"7": {"images": [{"filename": "out.png", "subfolder": "", "type": "output"}]}}}})
        if request.url.path == "/view":
            return httpx.Response(200, content=b"image-bytes")
        return httpx.Response(404)
    async with ComfyClient(transport=httpx.MockTransport(handle)) as client:
        assert "devices" in await client.health()
        assert await client.upload_reference(b"something", "master.png") == "uploaded_ref.png"
        graph = {"2": {"class_type": "CLIPTextEncode", "inputs": {"text": "A cinematic photo"}}}
        prompt_id = await client.submit(graph)
        outputs = await client.wait(prompt_id)
        files = output_files(outputs)
        assert files[0]["filename"] == "out.png"
        assert await client.download(files[0]) == b"image-bytes"


@pytest.mark.asyncio
async def test_comfy_interrupt_and_cooperative_wait_cancellation():
    calls = []

    def handle(request):
        calls.append(request.url.path)
        if request.url.path == "/interrupt":
            return httpx.Response(200, json={})
        if request.url.path == "/history/cancel-me":
            return httpx.Response(200, json={"cancel-me": {"status": {}}})
        return httpx.Response(404)

    async with ComfyClient(transport=httpx.MockTransport(handle)) as client:
        await client.interrupt()
        with pytest.raises(asyncio.CancelledError):
            await client.wait("cancel-me", cancel_check=lambda: True)

    assert "/interrupt" in calls
    assert "/history/cancel-me" not in calls
