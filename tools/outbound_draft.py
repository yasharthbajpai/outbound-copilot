"""MCP tool: synthesize a tailored outbound package from account research."""
from __future__ import annotations

from typing import Optional

from core.outbound import synthesize_outbound
from models import CompanyInput, CompanySignals, LinkedInSummary
from tools._server import mcp


@mcp.tool()
def synthesize_outbound_draft(
    company_name: str,
    company_domain: str,
    website_text: str,
    signals_json: str,
    linkedin_json: str = "",
) -> str:
    """Generate a tailored outbound package from account research.

    Combines website text, structured signals, and an optional contact summary
    to produce 1-2 value propositions, a personalized icebreaker, and a short
    email snippet. Pass the raw JSON strings returned by the earlier tools.

    Args:
        company_name:   Target company name, e.g. "Stripe".
        company_domain: Target company domain, e.g. "stripe.com".
        website_text:   The ``text`` field from research_company_website.
        signals_json:   Full JSON string returned by extract_company_signals.
        linkedin_json:  Optional JSON string returned by summarize_linkedin_profile.

    Returns:
        JSON with keys: value_propositions (list), icebreaker (str), email_snippet (str).
    """
    company_input = CompanyInput(name=company_name, domain=company_domain)

    try:
        signals = CompanySignals.model_validate_json(signals_json)
    except Exception:
        signals = CompanySignals()

    linkedin: Optional[LinkedInSummary] = None
    if linkedin_json and linkedin_json.strip():
        try:
            linkedin = LinkedInSummary.model_validate_json(linkedin_json)
        except Exception:
            linkedin = None

    result = synthesize_outbound(
        company_input=company_input,
        website_text=website_text,
        signals=signals,
        linkedin=linkedin,
    )
    return result.model_dump_json(indent=2)
