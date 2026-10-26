"""
sample_data.py - Seeded plumbing & home-service leads for Lead Rescue AI.
Provides realistic sample leads with fixed reference dates for consistent demo presentation.
"""

from datetime import datetime, timezone, timedelta

def get_base_reference_time() -> datetime:
    """Standard fixed reference timestamp for demo consistency (2026-10-26T12:00:00Z)."""
    return datetime(2026, 10, 26, 12, 0, 0, tzinfo=timezone.utc)

def get_sample_leads(reference_time: datetime | None = None) -> list[dict]:
    """
    Returns realistic sample leads for home service / plumbing.
    Timestamps are anchored to reference_time (defaulting to get_base_reference_time()).
    """
    ref = reference_time or get_base_reference_time()
    
    return [
        {
            "id": "lead-1",
            "name": "Marcus Vance",
            "service": "Main Pipe Replacement",
            "status": "Quote Sent",
            "lastContactDate": (ref - timedelta(days=4)).isoformat(),  # 4 days ago -> High Priority
            "notes": "Sent $1,800 quote for main copper pipe replacement. Customer said they would discuss with partner, then went silent."
        },
        {
            "id": "lead-2",
            "name": "Sarah Jenkins",
            "service": "Tankless Water Heater Inspection",
            "status": "New Inquiry",
            "lastContactDate": (ref - timedelta(days=3)).isoformat(),  # 3 days (72h) ago -> Needs Follow-up
            "notes": "Customer asked about cost and timeline for tankless water heater upgrade. Responded with questions about existing setup; no reply for 3 days."
        },
        {
            "id": "lead-3",
            "name": "Dave Miller",
            "service": "Sump Pump Installation",
            "status": "Quote Sent",
            "lastContactDate": (ref - timedelta(days=1)).isoformat(),  # 1 day (24h) ago -> Recent, No Follow-up Needed
            "notes": "Sent estimate yesterday afternoon. Customer acknowledged receipt and is reviewing."
        },
        {
            "id": "lead-4",
            "name": "Elena Rostova",
            "service": "Kitchen Faucet & Drain Repair",
            "status": "New Inquiry",
            "lastContactDate": (ref - timedelta(hours=5)).isoformat(),  # 5 hours ago -> Recent, No Follow-up Needed
            "notes": "Enquired this morning about a leaking faucet and slow drain. Service tech assigned to reply."
        },
        {
            "id": "lead-5",
            "name": "Tom Bradley",
            "service": "Emergency Sewer Line Clearing",
            "status": "Won",
            "lastContactDate": (ref - timedelta(days=5)).isoformat(),  # Won -> No Follow-up Needed
            "notes": "Job completed successfully on Thursday, payment received and invoice settled. Closed won."
        }
    ]
