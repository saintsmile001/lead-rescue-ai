"""
triage.py - Authoritative deterministic triage and metrics engine for Lead Rescue AI.
Evaluates lead urgency, reasons, and summary metrics.
Supports an explicit reference time (`now`) to ensure 100% deterministic test and demo evaluation.
"""

from datetime import datetime, timezone
import math

def parse_iso_datetime(dt_input: str | datetime) -> datetime:
    """Parses an ISO format string or normalizes a datetime to timezone-aware UTC."""
    if isinstance(dt_input, datetime):
        if dt_input.tzinfo is None:
            return dt_input.replace(tzinfo=timezone.utc)
        return dt_input.astimezone(timezone.utc)
    
    # Handle ISO string formats (e.g., ending with 'Z' or offset)
    clean_str = dt_input.replace("Z", "+00:00")
    dt = datetime.fromisoformat(clean_str)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)

def triage_single_lead(lead: dict, now: datetime | None = None) -> dict:
    """
    Evaluates a single lead against deterministic urgency rules.
    Returns an enriched copy of the lead with:
      - urgency: 'high' | 'medium' | 'none'
      - is_high_priority: bool
      - needs_followup: bool
      - reason: str
      - elapsed_days: int
      - elapsed_hours: float
    """
    ref_time = now if now is not None else datetime.now(timezone.utc)
    if ref_time.tzinfo is None:
        ref_time = ref_time.replace(tzinfo=timezone.utc)
    else:
        ref_time = ref_time.astimezone(timezone.utc)

    status = (lead.get("status") or "New Inquiry").strip()
    last_contact_raw = lead.get("lastContactDate")
    
    if last_contact_raw:
        try:
            last_contact = parse_iso_datetime(last_contact_raw)
            elapsed_seconds = max(0.0, (ref_time - last_contact).total_seconds())
        except Exception:
            elapsed_seconds = 0.0
    else:
        elapsed_seconds = 0.0

    elapsed_hours = elapsed_seconds / 3600.0
    elapsed_days = int(math.floor(elapsed_hours / 24.0))

    urgency = "none"
    is_high_priority = False
    needs_followup = False
    reason = "Status up to date"

    # Closed or already contacted states -> never need follow-up
    if status == "Won":
        urgency = "none"
        is_high_priority = False
        needs_followup = False
        reason = "Service booked / won"
    elif status == "Lost":
        urgency = "none"
        is_high_priority = False
        needs_followup = False
        reason = "Marked as lost"
    elif status == "Followed Up":
        urgency = "none"
        is_high_priority = False
        needs_followup = False
        reason = "Followed up recently"
    
    # Actionable states
    elif status == "Quote Sent":
        if elapsed_hours >= 72.0:  # >= 3 days -> High Priority
            urgency = "high"
            is_high_priority = True
            needs_followup = True
            days_str = f"{elapsed_days} days" if elapsed_days > 1 else "3 days"
            reason = f"Quote unanswered for {days_str}"
        elif elapsed_hours >= 48.0:  # >= 2 days and < 3 days -> Needs Follow-up (Standard)
            urgency = "medium"
            is_high_priority = False
            needs_followup = True
            reason = f"Quote pending for {elapsed_days} days"
        else:  # < 48 hours -> Recent
            urgency = "none"
            is_high_priority = False
            needs_followup = False
            reason = "Recent quote sent"
            
    elif status == "New Inquiry":
        if elapsed_hours >= 48.0:  # >= 48 hours -> Needs Follow-up (Standard)
            urgency = "medium"
            is_high_priority = False
            needs_followup = True
            days_str = f"{elapsed_days} days" if elapsed_days > 1 else "48 hours"
            reason = f"Inquiry inactive for {days_str}"
        else:  # < 48 hours -> Recent
            urgency = "none"
            is_high_priority = False
            needs_followup = False
            reason = "Recent inquiry"

    enriched = dict(lead)
    enriched.update({
        "urgency": urgency,
        "is_high_priority": is_high_priority,
        "needs_followup": needs_followup,
        "reason": reason,
        "elapsed_days": elapsed_days,
        "elapsed_hours": round(elapsed_hours, 1)
    })
    return enriched

def triage_leads(leads: list[dict], now: datetime | None = None) -> dict:
    """
    Evaluates a collection of leads and computes consistent summary metrics.
    Guarantees:
      - high_priority_count <= needs_followup_count (High-Priority is an exact subset).
      - No double counting of leads.
    """
    enriched_leads = [triage_single_lead(l, now=now) for l in leads]

    high_priority_count = sum(1 for l in enriched_leads if l["is_high_priority"])
    needs_followup_count = sum(1 for l in enriched_leads if l["needs_followup"])

    return {
        "leads": enriched_leads,
        "metrics": {
            "needs_followup_count": needs_followup_count,
            "high_priority_count": high_priority_count,
            "total_leads": len(enriched_leads)
        }
    }
