"""Core business logic for outbound-copilot.

Each module is a single-purpose, framework-free function with a typed
input/output contract. They are consumed by the tools/ MCP layer and
directly by main.py when running in CLI mode.
"""
from .linkedin import get_linkedin_summary
from .outbound import synthesize_outbound
from .pipeline import run_research
from .signals import extract_key_signals
from .website import get_company_website_content

__all__ = [
    "get_company_website_content",
    "extract_key_signals",
    "get_linkedin_summary",
    "synthesize_outbound",
    "run_research",
]
