"""
test_server.py - Integration tests for FastAPI endpoints in main.py.
Verifies health, default leads, triage endpoint, message generation, and static index delivery.
"""

import pytest
from fastapi.testclient import TestClient
from main import app
from sample_data import get_base_reference_time

@pytest.fixture
def client():
    return TestClient(app)

def test_health_endpoint(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert "gemini_configured" in data
    assert "model" in data
    assert "timestamp" in data

def test_get_default_leads(client):
    res = client.get("/api/leads")
    assert res.status_code == 200
    data = res.json()
    assert "leads" in data
    assert "metrics" in data
    assert len(data["leads"]) == 5
    assert data["metrics"]["needs_followup_count"] == 2
    assert data["metrics"]["high_priority_count"] == 1
    assert data["metrics"]["high_priority_count"] <= data["metrics"]["needs_followup_count"]

def test_post_triage_custom_leads(client):
    ref_time = get_base_reference_time().isoformat()
    custom_leads = [
        {
            "id": "c1",
            "name": "Bob",
            "service": "Drain Cleaning",
            "status": "Quote Sent",
            "lastContactDate": "2026-10-22T10:00:00Z"  # 4 days ago -> High Priority
        },
        {
            "id": "c2",
            "name": "Alice",
            "service": "Water Filter",
            "status": "New Inquiry",
            "lastContactDate": "2026-10-26T10:00:00Z"  # 2 hours ago -> Recent
        }
    ]
    res = client.post("/api/triage", json={"leads": custom_leads, "reference_time": ref_time})
    assert res.status_code == 200
    data = res.json()
    assert len(data["leads"]) == 2
    assert data["metrics"]["needs_followup_count"] == 1
    assert data["metrics"]["high_priority_count"] == 1
    assert data["leads"][0]["urgency"] == "high"
    assert data["leads"][1]["urgency"] == "none"

def test_post_generate_endpoint(client):
    lead = {
        "name": "Marcus Vance",
        "service": "Pipe Replacement",
        "status": "Quote Sent",
        "notes": "Sent $1,800 quote",
        "elapsed_days": 4
    }
    res = client.post("/api/generate", json={"lead": lead, "tone": "friendly"})
    assert res.status_code == 200
    data = res.json()
    assert "message" in data
    assert len(data["message"]) > 20
    assert data["source"] in ["ai", "fallback"]
    assert "Marcus" in data["message"]

def test_serve_index(client):
    res = client.get("/")
    assert res.status_code == 200
    assert "Lead Rescue AI" in res.text
    assert "metric-needs-followup" in res.text
    assert "metric-high-priority" in res.text
    assert "leads-container" in res.text
    assert "detail-panel-content" in res.text

def test_static_css_delivery(client):
    res = client.get("/static/style.css")
    assert res.status_code == 200
    assert "--color-primary" in res.text
    assert ".dashboard-grid" in res.text

def test_static_js_delivery(client):
    res = client.get("/static/app.js")
    assert res.status_code == 200
    assert "initApp" in res.text
    assert "reTriageLeads" in res.text
    assert "handleGenerateMessage" in res.text
