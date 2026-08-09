"""Integration tests for FastAPI REST endpoints."""

import time
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_check():
    """Verify health check endpoint."""
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"


def test_create_project_and_trigger_run():
    """Test POST /projects, POST /projects/{id}/runs, GET /runs/{id}, GET /runs/{id}/artifacts."""
    # 1. Create project
    proj_res = client.post("/api/v1/projects", json={"name": "Calculator Project", "description": "CLI calculator"})
    assert proj_res.status_code == 201
    proj_data = proj_res.json()
    project_id = proj_data["id"]
    assert proj_data["name"] == "Calculator Project"

    # 2. Trigger run (returns 202 immediately with run_id)
    run_res = client.post(f"/api/v1/projects/{project_id}/runs", json={"task_description": "Build a add function"})
    assert run_res.status_code == 202
    run_data = run_res.json()
    run_id = run_data["run_id"]
    assert run_data["project_id"] == project_id

    # Wait briefly for background async execution
    time.sleep(0.5)

    # 3. Get run status
    status_res = client.get(f"/api/v1/runs/{run_id}")
    assert status_res.status_code == 200
    status_data = status_res.json()
    assert status_data["run_id"] == run_id
    assert status_data["status"] in ("PLANNING", "ARCHITECTING", "CODING", "REVIEWING", "TESTING", "DONE")

    # 4. Get run artifacts
    artifacts_res = client.get(f"/api/v1/runs/{run_id}/artifacts")
    assert artifacts_res.status_code == 200
    artifacts_data = artifacts_res.json()
    assert artifacts_data["run_id"] == run_id
    assert "artifacts" in artifacts_data
