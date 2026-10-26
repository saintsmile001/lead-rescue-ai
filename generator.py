"""
generator.py - Dual-mode follow-up message generator for Lead Rescue AI.
Combines Google Gemini AI generation with an authoritative, deterministic template fallback.
Guarantees message generation even if API keys, network, or external services fail.
"""

import os
from dotenv import load_dotenv

load_dotenv()

FALLBACK_TEMPLATES = {
    "friendly": (
        "Hi {name}, hope you're having a great week! Just following up regarding your "
        "{service} inquiry. We would love to help get this sorted for you—please let us know "
        "if you have any questions or if you'd like to pick a convenient time!"
    ),
    "nudge": (
        "Hi {name}, checking in on the {service} we discussed. Our service schedule for "
        "the coming days is filling up, so I wanted to touch base and ensure you have a "
        "time reserved if you still need this taken care of."
    ),
    "value": (
        "Hi {name}, following up on your {service} estimate. Just a quick reminder that all our "
        "work comes with our full satisfaction guarantee, transparent pricing, and certified "
        "technicians. We'd be glad to answer any questions whenever you're ready!"
    )
}

def generate_template_message(lead: dict, tone: str = "friendly") -> str:
    """
    Produces a high-quality deterministic follow-up message using template interpolation.
    Operates 100% offline with zero external dependencies.
    """
    clean_tone = tone.lower().strip() if tone else "friendly"
    if clean_tone not in FALLBACK_TEMPLATES:
        clean_tone = "friendly"
    
    template = FALLBACK_TEMPLATES[clean_tone]
    
    name = (lead.get("name") or "there").strip()
    service = (lead.get("service") or "service").strip()
    
    # If notes specify a price/quote, mention it subtly if value tone
    notes = (lead.get("notes") or "").strip()
    quote_snippet = ""
    if clean_tone == "value" and "$" in notes:
        # extract rough dollar mention if present
        for word in notes.split():
            if "$" in word:
                quote_snippet = f" regarding the {word.strip(',.')} estimate"
                break

    message = template.format(
        name=name,
        service=service
    )
    if quote_snippet and quote_snippet not in message:
        message = message.replace(f"on your {service} estimate", f"on your {service} estimate{quote_snippet}")

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

    tone_descriptions = {
        "friendly": "warm, polite, and conversational check-in asking if they have any questions",
        "nudge": "courteous gentle nudge noting schedule availability or holding their slot",
        "value": "reassuring, value-focused reminder highlighting quality, warranty, and peace of mind"
    }
    tone_instruction = tone_descriptions.get(tone.lower(), tone_descriptions["friendly"])

    prompt = f"""You are a professional, helpful assistant for a local home services business (e.g., plumbing and HVAC).
Generate a concise, natural follow-up message (2 to 3 sentences maximum) suitable for sending directly to the customer via WhatsApp or SMS.
Do NOT include a subject line, placeholder brackets, quotation marks around the message, or formal email sign-offs.

Customer Context:
- Customer Name: {lead.get('name', 'Valued Customer')}
- Requested Service: {lead.get('service', 'Service')}
- Current Lead Status: {lead.get('status', 'Inquiry')}
- Inactive Duration: {lead.get('elapsed_days', 'a few')} days since last contact
- Conversation Notes: {lead.get('notes', 'None')}

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
    # 1. Attempt AI generation if key is present
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
            # Fall back safely
            fallback_text = generate_template_message(lead, tone=tone)
            return {
                "message": fallback_text,
                "source": "fallback",
                "error": str(e)
            }
    
    # 2. Key is absent -> deterministic template fallback
    fallback_text = generate_template_message(lead, tone=tone)
    return {
        "message": fallback_text,
        "source": "fallback",
        "error": None
    }
