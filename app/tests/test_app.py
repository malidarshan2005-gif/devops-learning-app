import json
import pytest
import app as app_module
from app import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    data_file = str(tmp_path / "tasks.json")

    app.config["TESTING"] = True
    # Works if app.py reads the env var at request time
    monkeypatch.setenv("DATA_FILE", data_file)
    # Works if app.py captured it in a module-level constant at import time
    monkeypatch.setattr(app_module, "DATA_FILE", data_file, raising=False)

    with app.test_client() as c:
        yield c
    # tmp_path and monkeypatch clean up automatically


def create_task(client, title):
    res = client.post("/api/tasks", json={"title": title})
    assert res.status_code == 201
    return json.loads(res.data)


def test_health_check(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert json.loads(res.data)["status"] == "healthy"


def test_get_tasks_empty(client):
    res = client.get("/api/tasks")
    assert res.status_code == 200
    assert json.loads(res.data) == []


def test_create_task(client):
    data = create_task(client, "Learn Docker")
    assert data["title"] == "Learn Docker"
    assert data["done"] is False


def test_create_task_missing_title(client):
    res = client.post("/api/tasks", json={})
    assert res.status_code == 400


def test_update_task(client):
    task = create_task(client, "Learn CI/CD")
    res = client.put(f"/api/tasks/{task['id']}", json={"done": True})
    assert res.status_code == 200
    assert json.loads(res.data)["done"] is True


def test_delete_task(client):
    task = create_task(client, "Learn Kubernetes")
    res = client.delete(f"/api/tasks/{task['id']}")
    assert res.status_code == 200
    tasks = json.loads(client.get("/api/tasks").data)
    assert len(tasks) == 0
