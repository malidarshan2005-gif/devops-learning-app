import pytest
import json
import os
import tempfile
from app.app import app


@pytest.fixture
def client():
    # Use a temp file so tests don't touch real data
    tmp = tempfile.mktemp(suffix=".json")
    app.config["TESTING"] = True
    os.environ["DATA_FILE"] = tmp
    with app.test_client() as c:
        yield c
    if os.path.exists(tmp):
        os.remove(tmp)


def test_health_check(client):
    res = client.get("/health")
    assert res.status_code == 200
    data = json.loads(res.data)
    assert data["status"] == "healthy"


def test_get_tasks_empty(client):
    res = client.get("/api/tasks")
    assert res.status_code == 200
    assert json.loads(res.data) == []


def test_create_task(client):
    res = client.post("/api/tasks", json={"title": "Learn Docker"})
    assert res.status_code == 201
    data = json.loads(res.data)
    assert data["title"] == "Learn Docker"
    assert data["done"] is False


def test_create_task_missing_title(client):
    res = client.post("/api/tasks", json={})
    assert res.status_code == 400


def test_update_task(client):
    client.post("/api/tasks", json={"title": "Learn CI/CD"})
    res = client.put("/api/tasks/1", json={"done": True})
    assert res.status_code == 200
    assert json.loads(res.data)["done"] is True


def test_delete_task(client):
    client.post("/api/tasks", json={"title": "Learn Kubernetes"})
    res = client.delete("/api/tasks/1")
    assert res.status_code == 200
    tasks = json.loads(client.get("/api/tasks").data)
    assert len(tasks) == 0
