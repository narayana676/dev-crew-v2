"""Integration tests for Auth, Idempotency, and Rate Limiting."""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_idempotency_key_deduplication():
    """Verify duplicate requests with X-Idempotency-Key return cached response."""
    key = "unique-idempotency-key-123"
    payload = {"task_description": "Build a parser with idempotency"}

    # First request
    res1 = client.post("/api/v1/projects/default/runs", json=payload, headers={"X-Idempotency-Key": key})
    assert res1.status_code == 202
    data1 = res1.json()

    # Second request with same idempotency key
    res2 = client.post("/api/v1/projects/default/runs", json=payload, headers={"X-Idempotency-Key": key})
    assert res2.status_code == 202
    data2 = res2.json()

    # Must return exact same run_id without duplicate execution
    assert data1["run_id"] == data2["run_id"]


def test_rate_limiting_headers():
    """Verify rate limit headers on response."""
    res = client.get("/health")
    assert res.status_code == 200

    # API endpoints include rate limit headers
    proj_res = client.get("/api/v1/runs/non-existent")
    assert "X-RateLimit-Limit" in proj_res.headers
    assert "X-RateLimit-Remaining" in proj_res.headers
