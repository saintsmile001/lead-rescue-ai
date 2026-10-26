"""
generator.py - Dual-mode follow-up message generator for Lead Rescue AI.
Combines Google Gemini AI generation with an authoritative, deterministic template fallback.
Guarantees natural, high-quality message generation even if API keys, network, or external services fail.
"""

import os
from dotenv import load_dotenv

load_dotenv()

FALLBACK_TEMPLATES = {
    "friendly": (
        "Hi {first_name}, hope you're having a great week! Just following up to see if you "
        "had any questions about the {service}. We're glad to walk through any details or "
        "schedule a visit whenever you're ready."
    ),
    "nudge": (
        "Hi {first_name}, checking in regarding your {service}. We're organizing our upcoming "
        "technician schedule and wanted to make sure you have a spot reserved if you still "
        "need this taken care of."
    ),
    "value": (
        "Hi {first_name}, following up on your {service} estimate. All our work includes "
        "transparent pricing and certified service backed by our full satisfaction guarantee. "
        "Let us know if you'd like to get started!"
    )
}

def get_first_name(full_name: str) -> str:
    """Extracts customer first name for natural, friendly outreach."""
    if not full_name:
        return "there"
    parts = full_name.strip().split()
    return parts[0] if parts else "there"

def generate_template_message(lead: dict, tone: str = "friendly") -> str:
    """
    Produces a natural, high-quality deterministic follow-up message using template interpolation.
    Operates 100% offline with zero external dependencies.
    """
    clean_tone = tone.lower().strip() if tone else "friendly"
    if clean_tone not in FALLBACK_TEMPLATES:
        clean_tone = "friendly"
    
    template = FALLBACK_TEMPLATES[clean_tone]
    
    first_name = get_first_name(lead.get("name", ""))
    service = (lead.get("service") or "service").strip()
    
    # If notes specify a price/quote, mention it subtly in value tone
    notes = (lead.get("notes") or "").strip()
    quote_snippet = ""
    if clean_tone == "value" and "$" in notes:
        for word in notes.split():
            if "$" in word:
                quote_snippet = f" for the {word.strip(',.')} estimate"
                break

    message = template.format(
        first_name=first_name,
        service=service
    )
    if quote_snippet and "estimate" in message:
        message = message.replace("on your {service} estimate", f"on your {service} estimate ({quote_snippet.strip()})")

    return message

def generate_ai_message(lead: dict, tone: str = "friendly", api_key: str | None = None, model_name: str | None = None) -> str:
    """
    Generates a personalized follow-up message using Google Gemini.
    Raises an exception if the API key is missing or the call fails.
    """
    key = api_key or os.environ.get("GEMINI_API_KEY")
    if not key or key.strip() == "" or key.startswith("your_"):
        raise ValueError("Valid GEMINI_API_KEY not configured")

    model = model_name or os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")

    # Initialize Google GenAI client
    from google import genai
    client = genai.Client(api_key=key)

    first_name = get_first_name(lead.get("name", ""))

    tone_descriptions = {
        "friendly": "warm, conversational, and helpful check-in asking if they have any questions or want to discuss details",
        "nudge": "courteous, direct check-in noting technician schedule availability and holding their service slot",
        "value": "reassuring, value-oriented reminder highlighting professional workmanship, warranty, and satisfaction guarantee"
    }
    tone_instruction = tone_descriptions.get(tone.lower(), tone_descriptions["friendly"])

    prompt = f"""You are a professional assistant for a local home services business (e.g., plumbing and HVAC).
Generate a concise, natural follow-up message (2 to 3 sentences maximum) suitable for sending directly to the customer via WhatsApp or SMS.
Rules:
- Address the customer by their first name only: "{first_name}" (e.g. "Hi {first_name},").
- Do NOT include full names, subject lines, placeholder brackets, quotation marks around the message, or formal email sign-offs.
- Do NOT invent prices, warranty terms, or services not provided in the context.
- Keep the wording natural, courteous, and directly relevant to their situation.

Customer Context:
- First Name: {first_name}
- Requested Service: {lead.get('service', 'Service')}
- Lead Status: {lead.get('status', 'Inquiry')}
- Inactive Duration: {lead.get('elapsed_days', 'a few')} days since last interaction
- Notes: {lead.get('notes', 'None')}

Tone Required: {tone_instruction}

Write the exact message text ready to send:"""

    response = client.models.generate_content(
        model=model,
        contents=prompt
    )
    
    text = (response.text or "").strip()
    if text.startswith('"') and text.endswith('"'):
        text = text[1:-1].strip()
    if not text:
        raise ValueError("Empty response returned by Gemini model")
    
    return text

def generate_followup_message(lead: dict, tone: str = "friendly") -> dict:
    """
    Authoritative dual-mode follow-up message generator.
    Attempts Gemini AI generation first.
    If unavailable or any error occurs, transparently falls back to deterministic templates.
    Always returns:
      {
        "message": str,
        "source": "ai" | "fallback",
        "error": None | str
      }
    """
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    model = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite").strip()
    
    if api_key and not api_key.startswith("your_"):
        try:
            ai_text = generate_ai_message(lead, tone=tone, api_key=api_key, model_name=model)
            return {
                "message": ai_text,
                "source": "ai",
                "error": None
            }
        except Exception as e:
            fallback_text = generate_template_message(lead, tone=tone)
            return {
                "message": fallback_text,
                "source": "fallback",
                "error": str(e)
            }
    
    fallback_text = generate_template_message(lead, tone=tone)
    return {
        "message": fallback_text,
        "source": "fallback",
        "error": None
    }
