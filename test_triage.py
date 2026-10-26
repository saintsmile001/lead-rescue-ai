"""
test_triage.py - Automated test suite for deterministic triage rules and metrics.
Verifies all boundary conditions, status handling, and metric consistency.
"""

from datetime import datetime, timezone, timedelta
import pytest
from triage import triage_single_lead, triage_leads
from sample_data import get_sample_leads, get_base_reference_time

@pytest.fixture
def ref_time():
    return datetime(2026, 10, 26, 12, 0, 0, tzinfo=timezone.utc)

def test_quote_at_and_beyond_72_hours(ref_time):
    """Quotes at or beyond 72h must be High Priority and Needs Follow-up."""
    # Exactly 72 hours
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

    # 96 hours (4 days)
    lead_96h = {
        "id": "q-96",
        "name": "Marcus",
        "service": "Main Replacement",
        "status": "Quote Sent",
        "lastContactDate": (ref_time - timedelta(hours=96)).isoformat(),
        "notes": "Big quote"
    }
    res_96 = triage_single_lead(lead_96h, now=ref_time)
    assert res_96["urgency"] == "high"
    assert res_96["is_high_priority"] is True
    assert res_96["needs_followup"] is True
    assert res_96["elapsed_days"] == 4

def test_quote_between_48_and_72_hours(ref_time):
    """Quotes between 48h and 72h must be Medium Priority (Needs Follow-up, but not High Priority)."""
    lead_55h = {
        "id": "q-55",
        "name": "Jordan",
        "service": "Boiler Service",
        "status": "Quote Sent",
        "lastContactDate": (ref_time - timedelta(hours=55)).isoformat(),
        "notes": "Sent 55 hours ago"
    }
    res = triage_single_lead(lead_55h, now=ref_time)
    assert res["urgency"] == "medium"
    assert res["is_high_priority"] is False
    assert res["needs_followup"] is True
    assert "Quote pending" in res["reason"]

def test_recent_quote(ref_time):
    """Quotes under 48 hours do not need follow-up yet."""
    lead_recent = {
        "id": "q-rec",
        "name": "Dave",
        "service": "Sump Pump",
        "status": "Quote Sent",
        "lastContactDate": (ref_time - timedelta(hours=20)).isoformat(),
        "notes": "Sent yesterday"
    }
    res = triage_single_lead(lead_recent, now=ref_time)
    assert res["urgency"] == "none"
    assert res["is_high_priority"] is False
    assert res["needs_followup"] is False
    assert res["reason"] == "Recent quote sent"

def test_inquiry_at_and_beyond_48_hours(ref_time):
    """Inquiries at or beyond 48 hours must be Medium Priority (Needs Follow-up)."""
    # Exactly 48 hours
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

    # 72 hours (3 days)
    lead_72h = {
        "id": "inq-72",
        "name": "Sarah",
        "service": "Water Heater",
        "status": "New Inquiry",
        "lastContactDate": (ref_time - timedelta(hours=72)).isoformat(),
        "notes": "Inactive inquiry"
    }
    res_72 = triage_single_lead(lead_72h, now=ref_time)
    assert res_72["urgency"] == "medium"
    assert res_72["is_high_priority"] is False
    assert res_72["needs_followup"] is True

def test_recent_inquiry(ref_time):
    """Inquiries under 48 hours do not need follow-up."""
    lead_recent = {
        "id": "inq-rec",
        "name": "Elena",
        "service": "Faucet Repair",
        "status": "New Inquiry",
        "lastContactDate": (ref_time - timedelta(hours=5)).isoformat(),
        "notes": "Just came in"
    }
    res = triage_single_lead(lead_recent, now=ref_time)
    assert res["urgency"] == "none"
    assert res["is_high_priority"] is False
    assert res["needs_followup"] is False
    assert res["reason"] == "Recent inquiry"

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
        assert res["urgency"] == "none", f"Status {st} should have urgency none"
        assert res["is_high_priority"] is False
        assert res["needs_followup"] is False
        assert res["reason"] == expected_reason

def test_summary_metrics_subset_and_no_double_count(ref_time):
    """Verifies that High-Priority Leads is strictly an urgent subset of Leads Needing Follow-up."""
    test_leads = [
        # 1. High priority quote (>=72h) -> Needs Follow-up AND High Priority
        {"id": "1", "name": "A", "status": "Quote Sent", "lastContactDate": (ref_time - timedelta(days=4)).isoformat()},
        # 2. Medium priority quote (>=48h, <72h) -> Needs Follow-up only
        {"id": "2", "name": "B", "status": "Quote Sent", "lastContactDate": (ref_time - timedelta(hours=50)).isoformat()},
        # 3. Medium priority inquiry (>=48h) -> Needs Follow-up only
        {"id": "3", "name": "C", "status": "New Inquiry", "lastContactDate": (ref_time - timedelta(days=2)).isoformat()},
        # 4. Recent inquiry (<48h) -> None
        {"id": "4", "name": "D", "status": "New Inquiry", "lastContactDate": (ref_time - timedelta(hours=2)).isoformat()},
        # 5. Won lead -> None
        {"id": "5", "name": "E", "status": "Won", "lastContactDate": (ref_time - timedelta(days=10)).isoformat()}
    ]
    result = triage_leads(test_leads, now=ref_time)
    metrics = result["metrics"]

    # Needs follow-up should be exactly 3 (leads 1, 2, 3)
    assert metrics["needs_followup_count"] == 3
    # High priority should be exactly 1 (lead 1)
    assert metrics["high_priority_count"] == 1
    # High priority is strictly <= needs_followup
    assert metrics["high_priority_count"] <= metrics["needs_followup_count"]

def test_seeded_sample_leads(ref_time):
    """Verifies default seeded sample data produces expected demo state."""
    leads = get_sample_leads(ref_time)
    result = triage_leads(leads, now=ref_time)
    
    assert result["metrics"]["needs_followup_count"] == 2  # Marcus (High) + Sarah (Medium)
    assert result["metrics"]["high_priority_count"] == 1   # Marcus Vance
    
    marcus = next(l for l in result["leads"] if l["name"] == "Marcus Vance")
    assert marcus["urgency"] == "high"
    assert marcus["is_high_priority"] is True
    
    sarah = next(l for l in result["leads"] if l["name"] == "Sarah Jenkins")
    assert sarah["urgency"] == "medium"
    assert sarah["needs_followup"] is True
    
    tom = next(l for l in result["leads"] if l["name"] == "Tom Bradley")
    assert tom["status"] == "Won"
    assert tom["urgency"] == "none"
