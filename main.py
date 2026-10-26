"""
main.py - FastAPI server for Lead Rescue AI.
Coordinates API routes, serves static frontend assets, and keeps GEMINI_API_KEY secure.
"""

import os
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from triage import triage_leads, parse_iso_datetime
from sample_data import get_sample_leads, get_base_reference_time
from generator import generate_followup_message

load_dotenv()

app = FastAPI(
    title="Lead Rescue AI",
    description="Service Lead Recovery Copilot - Deterministic triage & AI follow-up generator",
    version="1.0.0"
)

# Enable CORS for local development safety
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request / Response Schemas
class TriageRequest(BaseModel):
    leads: list[dict]
    reference_time: str | None = None

class GenerateRequest(BaseModel):
    lead: dict
    tone: str = "friendly"

# Static directory setup
STATIC_DIR = Path(__file__).parent / "static"
if not STATIC_DIR.exists():
    STATIC_DIR.mkdir(parents=True, exist_ok=True)

# Mount static files at /static
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/")
async def serve_index():
    """Serves the main single-page dashboard."""
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {"message": "Lead Rescue AI is running. Visit /static/index.html"}

@app.get("/api/health")
async def health_check():
    """Returns system status, configured model, and whether Gemini key is present."""
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    is_configured = bool(api_key and not api_key.startswith("your_"))
    model = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite").strip()
    return {
        "status": "ok",
        "gemini_configured": is_configured,
        "model": model,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@app.get("/api/leads")
async def get_default_leads():
    """
    Returns the initial 5 seeded sample leads, triaged by the canonical engine.
    Uses get_base_reference_time() so demo metrics and reasons remain consistent.
    """
    ref_time = get_base_reference_time()
    raw_leads = get_sample_leads(ref_time)
    triaged = triage_leads(raw_leads, now=ref_time)
    return triaged

@app.post("/api/triage")
async def triage_leads_endpoint(req: TriageRequest):
    """
    Authoritative triage endpoint for any collection of leads.
    Allows frontend to pass added or modified leads and receive consistent metrics.
    """
    ref = None
    if req.reference_time:
        try:
            ref = parse_iso_datetime(req.reference_time)
        except Exception:
            ref = None
    
    # If not specified, default to base reference time for consistency with seeded demo
    if ref is None:
        ref = get_base_reference_time()

    return triage_leads(req.leads, now=ref)

@app.post("/api/generate")
async def generate_message_endpoint(req: GenerateRequest):
    """
    Generates a personalized revival message for a lead using Gemini AI
    with automatic deterministic template fallback.
    """
    try:
        result = generate_followup_message(req.lead, tone=req.tone)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
