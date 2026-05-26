"""MCP tool layer for outbound-copilot.

Each module wraps one core/ function with an @mcp.tool() decorator.
Importing this package registers all five tools on the shared FastMCP
instance in tools._server.
"""
from tools._server import mcp  # noqa: F401 — shared instance
from tools.extract_signals import extract_company_signals  # noqa: F401
from tools.linkedin_profile import summarize_linkedin_profile  # noqa: F401
from tools.outbound_draft import synthesize_outbound_draft  # noqa: F401
from tools.research_website import research_company_website  # noqa: F401
from tools.run_research import run_full_research  # noqa: F401

__all__ = [
    "mcp",
    "research_company_website",
    "extract_company_signals",
    "summarize_linkedin_profile",
    "synthesize_outbound_draft",
    "run_full_research",
]
