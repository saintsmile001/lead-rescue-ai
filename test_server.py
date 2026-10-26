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

def test_lifecycle_add_lead_and_reset(client):
    """Simulates adding a new lead, re-triaging through backend, and resetting."""
    # 1. Start with seeded leads
    seeded_res = client.get("/api/leads")
    assert seeded_res.status_code == 200
    initial_leads = seeded_res.json()["leads"]
    assert len(initial_leads) == 5
    assert seeded_res.json()["metrics"]["needs_followup_count"] == 2
    assert seeded_res.json()["metrics"]["high_priority_count"] == 1

    # 2. Add an urgent new lead (Quote Sent 5 days ago)
    new_lead = {
        "id": "new-test-1",
        "name": "David Clark",
        "service": "Emergency Boiler Repair",
        "status": "Quote Sent",
        "lastContactDate": "2026-10-21T10:00:00Z",  # 5 days ago -> High Priority
        "notes": "Sent $3,200 quote"
    }
    updated_list = [new_lead] + initial_leads

    # 3. Post to /api/triage
    triage_res = client.post("/api/triage", json={"leads": updated_list})
    assert triage_res.status_code == 200
    triage_data = triage_res.json()
    assert len(triage_data["leads"]) == 6
    # Metric counts should increment: needs_followup -> 3, high_priority -> 2
    assert triage_data["metrics"]["needs_followup_count"] == 3
    assert triage_data["metrics"]["high_priority_count"] == 2
    assert triage_data["leads"][0]["urgency"] == "high"

    # 4. Generate message for newly added lead
    gen_res = client.post("/api/generate", json={"lead": triage_data["leads"][0], "tone": "friendly"})
    assert gen_res.status_code == 200
    assert "David" in gen_res.json()["message"]

    # 5. Reset to default seeded data
    reset_res = client.get("/api/leads")
    assert reset_res.status_code == 200
    assert len(reset_res.json()["leads"]) == 5
    assert reset_res.json()["metrics"]["needs_followup_count"] == 2
    assert reset_res.json()["metrics"]["high_priority_count"] == 1
