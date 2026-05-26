"""MCP-inspired tool layer.

Each tool is a single-purpose callable with a clear input/output contract.
They are orchestrated by the pipeline in `tools.pipeline`.
"""
from .company_website import get_company_website_content
from .key_signals import extract_key_signals
from .linkedin_summary import get_linkedin_summary
from .outbound_synthesis import synthesize_outbound
from .pipeline import run_research

__all__ = [
    "get_company_website_content",
    "extract_key_signals",
    "get_linkedin_summary",
    "synthesize_outbound",
    "run_research",
]
