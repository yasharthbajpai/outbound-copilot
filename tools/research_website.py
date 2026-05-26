"""MCP tool: fetch and extract readable text from a company website."""
from __future__ import annotations

from core.website import get_company_website_content
from tools._server import mcp


@mcp.tool()
def research_company_website(domain: str, name: str = "") -> str:
    """Fetch and extract readable text from a company website.

    Tries plain HTTP (httpx → requests + trafilatura/BeautifulSoup), then
    Playwright headless Chromium for JS-rendered pages, then a Claude
    best-effort description as a last resort.

    Args:
        domain: Company website domain, e.g. "stripe.com" (https:// optional).
        name:   Optional company name — only used if all scraping stages fail
                and Claude has to describe the company from name+domain alone.

    Returns:
        JSON with keys: text, source, url, error.
        ``source`` is one of "http", "playwright", "llm_fallback", or "none".
    """
    result = get_company_website_content(domain=domain, name=name or None)
    return result.model_dump_json(indent=2)
