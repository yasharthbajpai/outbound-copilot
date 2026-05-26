"""MCP server exposing outbound-copilot's research tools.

The four pipeline steps are each a standalone MCP tool so an LLM agent
(Claude Desktop, Cursor, etc.) can call them individually or in sequence.
A fifth convenience tool runs the full pipeline in one shot.

Run modes
---------
stdio (default) — for Claude Desktop / Cursor MCP config:
    python mcp_server.py

Streamable HTTP — for network-accessible deployments:
    python mcp_server.py --http          # listens on 0.0.0.0:8000
    python mcp_server.py --http --port 9000
"""
from __future__ import annotations

import json
import sys
from typing import Optional

from mcp.server.fastmcp import FastMCP

from config import ConfigError, get_settings
from models import CompanyInput, CompanySignals, LinkedInSummary
from tools import (
    extract_key_signals,
    get_company_website_content,
    get_linkedin_summary,
    run_research,
    synthesize_outbound,
)

# ---------------------------------------------------------------------------
# Server instance
# ---------------------------------------------------------------------------

mcp = FastMCP(
    "outbound-copilot",
    instructions=(
        "A set of tools for B2B outbound sales research. "
        "Call them in pipeline order:\n"
        "  1. research_company_website  — fetch & extract website text\n"
        "  2. extract_company_signals   — structured signals from that text\n"
        "  3. summarize_linkedin_profile (optional) — structure a pasted profile\n"
        "  4. synthesize_outbound_draft — value props, icebreaker, email snippet\n"
        "Or use run_full_research to execute all four steps in one call."
    ),
)


# ---------------------------------------------------------------------------
# Tool 1 — website fetch
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Tool 2 — signal extraction
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Tool 3 — LinkedIn profile summary
# ---------------------------------------------------------------------------

@mcp.tool()
def summarize_linkedin_profile(profile_text: str) -> str:
    """Structure a manually pasted LinkedIn profile into outbound-relevant fields.

    This tool intentionally does NOT scrape LinkedIn. The caller must supply
    text that was manually copied from a profile the user is authorised to view.
    Automated scraping of LinkedIn violates their Terms of Service.

    Args:
        profile_text: Raw text pasted from a LinkedIn profile page.

    Returns:
        JSON with keys: name, current_role, seniority_level,
        responsibilities_summary, relevant_topics, outbound_angle.
        String fields are null when not found; list fields are empty arrays.
    """
    result = get_linkedin_summary(raw_profile_text=profile_text)
    if result is None:
        return json.dumps({"error": "Empty profile text — nothing to summarise."})
    return result.model_dump_json(indent=2)


# ---------------------------------------------------------------------------
# Tool 4 — outbound synthesis
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Tool 5 — full pipeline (convenience)
# ---------------------------------------------------------------------------

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

    Use this when you want one-shot results. Use the individual tools when
    you need to inspect or modify intermediate outputs.

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


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    try:
        get_settings()
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        sys.exit(2)

    use_http = "--http" in sys.argv
    port = 8000
    for arg in sys.argv:
        if arg.startswith("--port="):
            port = int(arg.split("=", 1)[1])
        elif arg == "--port":
            idx = sys.argv.index("--port")
            if idx + 1 < len(sys.argv):
                port = int(sys.argv[idx + 1])

    if use_http:
        print(f"Starting outbound-copilot MCP server on http://0.0.0.0:{port}", file=sys.stderr)
        mcp.run(transport="streamable-http", host="0.0.0.0", port=port)
    else:
        mcp.run()  # stdio — default for Claude Desktop / Cursor
