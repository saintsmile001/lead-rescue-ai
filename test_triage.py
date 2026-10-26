"""
test_triage.py - Automated test suite for deterministic triage rules and metrics.
Verifies all boundary conditions (exact 72h, 48h, 71.9h, 72.1h, 47.9h, 48.1h),
status handling, metric subset consistency, and generator output.
"""

from datetime import datetime, timezone, timedelta
import pytest
from triage import triage_single_lead, triage_leads
from sample_data import get_sample_leads, get_base_reference_time
from generator import generate_template_message, generate_followup_message, get_first_name

@pytest.fixture
def ref_time():
    return datetime(2026, 10, 26, 12, 0, 0, tzinfo=timezone.utc)

def test_quote_exact_and_sub_boundary_72_hours(ref_time):
    """Verifies quote status behavior at 71.9h, exactly 72h, and 72.1h."""
    # 71.9 hours -> Medium Priority (Needs Follow-up, NOT High Priority)
    lead_below_72 = {
        "id": "q-below-72",
        "name": "Jordan",
        "service": "Boiler Service",
        "status": "Quote Sent",
        "lastContactDate": (ref_time - timedelta(hours=71.9)).isoformat(),
        "notes": "Sent 71.9 hours ago"
    }
    res_below = triage_single_lead(lead_below_72, now=ref_time)
    assert res_below["urgency"] == "medium"
    assert res_below["is_high_priority"] is False
    assert res_below["needs_followup"] is True
    assert "Quote pending" in res_below["reason"]

    # Exactly 72.0 hours -> High Priority
    lead_72h = {
        "id": "q-72",
        "name": "Alex",
        "service": "Pipe Repair",
        "status": "Quote Sent",
        "lastContactDate": (ref_time - timedelta(hours=72)).isoformat(),
        "notes": "Quote sent"
    }
    res_72 = triage_single_lead(lead_72h, now=ref_time)
    assert res_72["urgency"] == "high"
    assert res_72["is_high_priority"] is True
    assert res_72["needs_followup"] is True
    assert "Quote unanswered" in res_72["reason"]

    # 72.1 hours -> High Priority
    lead_above_72 = {
        "id": "q-above-72",
        "name": "Marcus",
        "service": "Main Replacement",
        "status": "Quote Sent",
        "lastContactDate": (ref_time - timedelta(hours=72.1)).isoformat(),
        "notes": "Big quote"
    }
    res_above = triage_single_lead(lead_above_72, now=ref_time)
    assert res_above["urgency"] == "high"
    assert res_above["is_high_priority"] is True
    assert res_above["needs_followup"] is True

def test_inquiry_exact_and_sub_boundary_48_hours(ref_time):
    """Verifies inquiry status behavior at 47.9h, exactly 48h, and 48.1h."""
    # 47.9 hours -> Recent inquiry (<48h), no follow-up needed
    lead_below_48 = {
        "id": "inq-below-48",
        "name": "Chris",
        "service": "Drain Inspection",
        "status": "New Inquiry",
        "lastContactDate": (ref_time - timedelta(hours=47.9)).isoformat(),
        "notes": "Inquiry 47.9h ago"
    }
    res_below = triage_single_lead(lead_below_48, now=ref_time)
    assert res_below["urgency"] == "none"
    assert res_below["is_high_priority"] is False
    assert res_below["needs_followup"] is False
    assert res_below["reason"] == "Recent inquiry"

    # Exactly 48.0 hours -> Medium Priority (Needs Follow-up)
    lead_48h = {
        "id": "inq-48",
        "name": "Taylor",
        "service": "Drain Cleaning",
        "status": "New Inquiry",
        "lastContactDate": (ref_time - timedelta(hours=48)).isoformat(),
        "notes": "Initial message"
    }
    res_48 = triage_single_lead(lead_48h, now=ref_time)
    assert res_48["urgency"] == "medium"
    assert res_48["is_high_priority"] is False
    assert res_48["needs_followup"] is True
    assert "Inquiry inactive" in res_48["reason"]

    # 48.1 hours -> Medium Priority
    lead_above_48 = {
        "id": "inq-above-48",
        "name": "Sarah",
        "service": "Water Heater",
        "status": "New Inquiry",
        "lastContactDate": (ref_time - timedelta(hours=48.1)).isoformat(),
        "notes": "Inactive inquiry"
    }
    res_above = triage_single_lead(lead_above_48, now=ref_time)
    assert res_above["urgency"] == "medium"
    assert res_above["is_high_priority"] is False
    assert res_above["needs_followup"] is True

def test_recent_leads_no_followup(ref_time):
    """Recent leads (<48h) never require follow-up."""
    recent_quote = {
        "id": "q-rec",
        "name": "Dave",
        "service": "Sump Pump",
        "status": "Quote Sent",
        "lastContactDate": (ref_time - timedelta(hours=24)).isoformat()
    }
    res_q = triage_single_lead(recent_quote, now=ref_time)
    assert res_q["urgency"] == "none"
    assert res_q["needs_followup"] is False

    recent_inq = {
        "id": "inq-rec",
        "name": "Elena",
        "service": "Faucet Repair",
        "status": "New Inquiry",
        "lastContactDate": (ref_time - timedelta(hours=5)).isoformat()
    }
    res_i = triage_single_lead(recent_inq, now=ref_time)
    assert res_i["urgency"] == "none"
    assert res_i["needs_followup"] is False

def test_closed_and_followed_up_statuses(ref_time):
    """Won, Lost, and Followed Up leads never trigger follow-up, regardless of age."""
    for st, expected_reason in [
        ("Won", "Service booked / won"),
        ("Lost", "Marked as lost"),
        ("Followed Up", "Followed up recently")
    ]:
        lead = {
            "id": f"closed-{st}",
            "name": f"Customer {st}",
            "service": "Any Service",
            "status": st,
            "lastContactDate": (ref_time - timedelta(days=20)).isoformat(),
            "notes": "Old record"
        }
        res = triage_single_lead(lead, now=ref_time)
        assert res["urgency"] == "none"
        assert res["is_high_priority"] is False
        assert res["needs_followup"] is False
        assert res["reason"] == expected_reason

def test_summary_metrics_subset_and_no_double_count(ref_time):
    """Verifies that High-Priority Leads is strictly an urgent subset of Leads Needing Follow-up."""
    test_leads = [
        {"id": "1", "name": "A", "status": "Quote Sent", "lastContactDate": (ref_time - timedelta(days=4)).isoformat()},
        {"id": "2", "name": "B", "status": "Quote Sent", "lastContactDate": (ref_time - timedelta(hours=50)).isoformat()},
        {"id": "3", "name": "C", "status": "New Inquiry", "lastContactDate": (ref_time - timedelta(days=2)).isoformat()},
        {"id": "4", "name": "D", "status": "New Inquiry", "lastContactDate": (ref_time - timedelta(hours=2)).isoformat()},
        {"id": "5", "name": "E", "status": "Won", "lastContactDate": (ref_time - timedelta(days=10)).isoformat()}
    ]
    result = triage_leads(test_leads, now=ref_time)
    metrics = result["metrics"]

    assert metrics["needs_followup_count"] == 3
    assert metrics["high_priority_count"] == 1
    assert metrics["high_priority_count"] <= metrics["needs_followup_count"]

def test_first_name_helper():
    assert get_first_name("Marcus Vance") == "Marcus"
    assert get_first_name("Sarah") == "Sarah"
    assert get_first_name("") == "there"
    assert get_first_name(None) == "there"

def test_deterministic_template_fallback_all_tones():
    """Verifies natural message generation using first name for all 3 tones."""
    lead = {
        "name": "Marcus Vance",
        "service": "Main Pipe Replacement",
        "status": "Quote Sent",
        "notes": "Sent $1,800 quote"
    }
    
    # 1. Friendly Check-in
    msg_friendly = generate_template_message(lead, tone="friendly")
    assert "Hi Marcus," in msg_friendly
    assert "Marcus Vance" not in msg_friendly  # Should use first name only
    assert "Main Pipe Replacement" in msg_friendly
    assert "schedule a visit" in msg_friendly

    # 2. Gentle Nudge
    msg_nudge = generate_template_message(lead, tone="nudge")
    assert "Hi Marcus," in msg_nudge
    assert "technician schedule" in msg_nudge

    # 3. Value-Focused
    msg_value = generate_template_message(lead, tone="value")
    assert "Hi Marcus," in msg_value
    assert "satisfaction guarantee" in msg_value

def test_generator_graceful_fallback_without_key(monkeypatch):
    """Verifies that generator always succeeds with source='fallback' if GEMINI_API_KEY is unset."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    
    lead = {
        "name": "Sarah Jenkins",
        "service": "Tankless Water Heater",
        "status": "New Inquiry"
    }
    res = generate_followup_message(lead, tone="friendly")
    assert res["source"] == "fallback"
    assert "Hi Sarah," in res["message"]
    assert "Tankless Water Heater" in res["message"]
    assert res["error"] is None

def test_generator_graceful_fallback_on_api_error(monkeypatch):
    """Verifies that even if an invalid key triggers an API error, fallback succeeds seamlessly."""
    monkeypatch.setenv("GEMINI_API_KEY", "invalid_test_key_12345")
    
    lead = {
        "name": "Dave Miller",
        "service": "Sump Pump",
        "status": "Quote Sent"
    }
    res = generate_followup_message(lead, tone="nudge")
    assert res["source"] == "fallback"
    assert "Hi Dave," in res["message"]
    assert res["error"] is not None
