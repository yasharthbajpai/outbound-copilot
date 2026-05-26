"""Summarize a manually pasted LinkedIn-style profile.

This tool intentionally does NOT scrape LinkedIn. The user pastes profile
text from their own session and we structure it. That keeps us compliant
with LinkedIn's Terms of Service.
"""
from __future__ import annotations

from typing import Optional

from models import LinkedInSummary
from services import BedrockClient, BedrockError
from utils.json_parse import extract_json, sanitize_prompt_content
from utils.logging import get_logger

logger = get_logger(__name__)

_SYSTEM_PROMPT = (
    "You are an outbound sales research analyst. The user pastes raw text "
    "from a LinkedIn-style professional profile that they have manually "
    "copied. Your job is to summarize it into a structured JSON object. "
    "Reply with one JSON object only, no prose, no code fences. Use null "
    "for unknown string fields and empty arrays for unknown list fields. "
    "Never invent specifics that are not visible in the pasted text."
)

_USER_TEMPLATE = """\
Profile text follows between the <profile> tags. Produce JSON exactly
matching this schema:

{{
  "name": string | null,
  "current_role": string | null,
  "seniority_level": string | null,
  "responsibilities_summary": string | null,
  "relevant_topics": [string],
  "outbound_angle": string | null
}}

Guidelines:
- "seniority_level": one of IC, Senior IC, Manager, Director, VP, C-level,
  Founder, or null if unclear.
- "responsibilities_summary": 1-2 sentences in plain language.
- "relevant_topics": short phrases describing what they care about
  professionally (e.g. "data infrastructure", "go-to-market", "developer
  experience").
- "outbound_angle": one sentence suggesting how an outbound rep should
  approach them given the profile.

<profile>
{profile}
</profile>

Respond with only the JSON object.
"""


def get_linkedin_summary(
    raw_profile_text: str, client: Optional[BedrockClient] = None
) -> Optional[LinkedInSummary]:
    """Return a LinkedInSummary or None if no profile text was provided.

    No web scraping ever happens here — the input must be pasted by hand.
    """
    if not raw_profile_text or not raw_profile_text.strip():
        return None

    client = client or BedrockClient()
    prompt = _USER_TEMPLATE.format(profile=sanitize_prompt_content(raw_profile_text.strip()))

    try:
        raw = client.invoke(prompt=prompt, system=_SYSTEM_PROMPT)
    except BedrockError as exc:
        logger.warning("Bedrock call failed in get_linkedin_summary: %s", exc)
        return LinkedInSummary()

    parsed = extract_json(raw)
    if not isinstance(parsed, dict):
        logger.warning("Could not parse JSON from LinkedIn response: %s", raw[:200])
        return LinkedInSummary()

    try:
        return LinkedInSummary.model_validate(parsed)
    except Exception as exc:
        logger.warning("LinkedIn JSON failed validation: %s", exc)
        return LinkedInSummary()
