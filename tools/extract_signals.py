"""MCP tool: extract structured outbound signals from raw company text."""
from __future__ import annotations

from core.signals import extract_key_signals
from tools._server import mcp


@mcp.tool()
def extract_company_signals(company_text: str) -> str:
    """Extract structured outbound-research signals from raw company text.

    Sends the text to Claude and returns a JSON object with six signal
    categories. Returns empty arrays for any category not found in the text —
    never fabricates data.

    Args:
        company_text: Plain text scraped or summarised from a company website.
                      Pass the ``text`` field from research_company_website.

    Returns:
        JSON with keys: hiring_signals, funding_signals, product_focus,
        market_segment, ideal_customer_profile, notable_initiatives.
        Each value is a list of short, concrete phrases.
    """
    result = extract_key_signals(text=company_text)
    return result.model_dump_json(indent=2)
