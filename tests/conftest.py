import pytest
from fastapi.testclient import TestClient

import studio.database as db
from studio.app import app


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DATA", tmp_path)
    monkeypatch.setattr(db, "DB", tmp_path / "test.db")
    monkeypatch.setattr(db, "UPLOADS", tmp_path / "references")
    monkeypatch.setattr(db, "OUTPUTS", tmp_path / "outputs")
    monkeypatch.setattr(db, "WORKFLOWS", tmp_path / "workflows")
    with TestClient(app) as test_client:
        yield test_client
