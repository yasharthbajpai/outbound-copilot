"""Extract structured outbound-research signals from raw company text."""
from __future__ import annotations

from typing import Optional

from models import CompanySignals
from services import BedrockClient, BedrockError
from utils.json_parse import extract_json, sanitize_prompt_content
from utils.logging import get_logger

logger = get_logger(__name__)

_SYSTEM_PROMPT = (
    "You are an outbound sales research analyst. You receive raw text "
    "scraped or summarized from a company's public web presence. Your job "
    "is to extract concrete signals useful for outbound outreach. "
    "Always reply with a single JSON object, no prose, no code fences. "
    "Use empty arrays when a signal is not present in the text — never "
    "fabricate details."
)

_USER_TEMPLATE = """\
Company text follows between the <text> tags. Extract signals and reply
with JSON matching exactly this schema:

{{
  "hiring_signals": [string],
  "funding_signals": [string],
  "product_focus": [string],
  "market_segment": [string],
  "ideal_customer_profile": [string],
  "notable_initiatives": [string]
}}

Guidelines:
- "hiring_signals": roles being hired, team expansion, location moves.
- "funding_signals": rounds, investors, revenue milestones if explicitly stated.
- "product_focus": primary products/services in plain language.
- "market_segment": vertical(s), company-size band, geography.
- "ideal_customer_profile": who they appear to sell to.
- "notable_initiatives": launches, partnerships, GTM moves, strategy shifts.

Each list item should be a short, concrete phrase (under 20 words).

<text>
{text}
</text>

Respond with only the JSON object.
"""


def extract_key_signals(
    text: str, client: Optional[BedrockClient] = None
) -> CompanySignals:
    """Run Claude on `text` and return a validated `CompanySignals`.

    On any failure we return an empty `CompanySignals` rather than raising,
    so the rest of the pipeline can still run.
    """
    if not text or not text.strip():
        return CompanySignals()

    client = client or BedrockClient()
    prompt = _USER_TEMPLATE.format(text=sanitize_prompt_content(text.strip()))

    try:
        raw = client.invoke(prompt=prompt, system=_SYSTEM_PROMPT)
    except BedrockError as exc:
        logger.warning("Bedrock call failed in extract_key_signals: %s", exc)
        return CompanySignals()

    parsed = extract_json(raw)
    if not isinstance(parsed, dict):
        logger.warning("Could not parse JSON from signals response: %s", raw[:200])
        return CompanySignals()

    try:
        return CompanySignals.model_validate(parsed)
    except Exception as exc:
        logger.warning("Signals JSON failed validation: %s", exc)
        # Salvage what we can field-by-field.
        salvaged = {
            key: value
            for key, value in parsed.items()
            if key in CompanySignals.model_fields and isinstance(value, list)
        }
        try:
            return CompanySignals.model_validate(salvaged)
        except Exception:
            return CompanySignals()
