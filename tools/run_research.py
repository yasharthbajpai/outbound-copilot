"""MCP tool: run the complete outbound research pipeline in one call."""
from __future__ import annotations

from core.pipeline import run_research
from models import CompanyInput
from tools._server import mcp


@mcp.tool()
def run_full_research(
    company_name: str,
    company_domain: str,
    linkedin_profile_text: str = "",
) -> str:
    """Run the complete outbound research pipeline in a single call.

    Executes all four steps — website fetch, signal extraction, LinkedIn
    summarisation (if profile text is provided), and outbound synthesis —
    and returns the full result as a single JSON object.

    Use this for one-shot results. Use the individual tools when you need
    to inspect or modify intermediate outputs.

    Args:
        company_name:          Target company name, e.g. "Stripe".
        company_domain:        Target company domain, e.g. "stripe.com".
        linkedin_profile_text: Optional manually pasted LinkedIn profile text.

    Returns:
        JSON with keys: input, website, signals, linkedin (null if skipped),
        outbound — mirroring the full ResearchResult schema.
    """
    company_input = CompanyInput(
        name=company_name,
        domain=company_domain,
        linkedin_profile_text=linkedin_profile_text or None,
    )
    result = run_research(company_input)
    return result.model_dump_json(indent=2)
