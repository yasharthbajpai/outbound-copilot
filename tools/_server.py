"""Shared FastMCP server instance.

All tool files import `mcp` from here so there is exactly one FastMCP
instance in the process. This avoids duplicate registrations and
circular imports.
"""
from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    "outbound-copilot",
    instructions=(
        "Tools for B2B outbound sales research powered by Claude on Amazon Bedrock. "
        "Call them in pipeline order:\n"
        "  1. research_company_website  — fetch and extract website text\n"
        "  2. extract_company_signals   — structured signals from that text\n"
        "  3. summarize_linkedin_profile (optional) — structure a pasted profile\n"
        "  4. synthesize_outbound_draft — value props, icebreaker, email snippet\n"
        "Or call run_full_research to execute all four steps in one shot."
    ),
)
