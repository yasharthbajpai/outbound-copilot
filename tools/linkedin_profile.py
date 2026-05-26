"""MCP tool: structure a manually pasted LinkedIn profile."""
from __future__ import annotations

import json

from core.linkedin import get_linkedin_summary
from tools._server import mcp


@mcp.tool()
def summarize_linkedin_profile(profile_text: str) -> str:
    """Structure a manually pasted LinkedIn profile into outbound-relevant fields.

    Accepts text the user has manually copied from a LinkedIn profile they are
    authorised to view. Never scrapes LinkedIn — automated scraping violates
    LinkedIn's Terms of Service.

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
