"""Synthesize the final outbound artifact from company + (optional) contact context."""
from __future__ import annotations

import json
from typing import Optional

from models import CompanyInput, CompanySignals, LinkedInSummary, OutboundDraft
from services import BedrockClient, BedrockError
from utils.json_parse import extract_json, sanitize_prompt_content
from utils.logging import get_logger

logger = get_logger(__name__)

_SYSTEM_PROMPT = (
    "You are a senior outbound sales strategist. You receive structured "
    "research on a target account and, optionally, a contact at that "
    "account. Generate a tight outbound package: 1-2 tailored value "
    "propositions, a personalized icebreaker, and a short email snippet. "
    "Reply with one JSON object only, no prose, no code fences. Keep tone "
    "specific, concrete, and non-cheesy. Do not invent facts that are not "
    "supported by the provided research."
)

_USER_TEMPLATE = """\
Research bundle:

<company_input>
{company_input}
</company_input>

<company_website_text>
{website_text}
</company_website_text>

<company_signals>
{signals}
</company_signals>

<linkedin_summary>
{linkedin}
</linkedin_summary>

Produce JSON matching exactly:

{{
  "value_propositions": [string],   // 1 or 2 entries, each under 35 words
  "icebreaker":         string,     // 1-2 sentences, references something specific
  "email_snippet":      string      // 4-7 sentences, no subject line, signed "[Your name]"
}}

Tone rules:
- Be specific. Reference the signals or profile facts you actually used.
- No empty flattery, no "I came across your company".
- If LinkedIn summary is empty, write to the account generically but still concretely.
- Do not promise outcomes you cannot back up.

Respond with only the JSON object.
"""


def synthesize_outbound(
    company_input: CompanyInput,
    website_text: str,
    signals: CompanySignals,
    linkedin: Optional[LinkedInSummary],
    client: Optional[BedrockClient] = None,
) -> OutboundDraft:
    """Generate the final OutboundDraft. Returns an empty draft on failure."""
    client = client or BedrockClient()

    prompt = _USER_TEMPLATE.format(
        company_input=company_input.model_dump_json(indent=2),
        website_text=sanitize_prompt_content((website_text or "")[:6000]),
        signals=signals.model_dump_json(indent=2),
        linkedin=(
            linkedin.model_dump_json(indent=2)
            if linkedin
            else json.dumps({"note": "No LinkedIn profile provided"}, indent=2)
        ),
    )

    try:
        raw = client.invoke(prompt=prompt, system=_SYSTEM_PROMPT)
    except BedrockError as exc:
        logger.warning("Bedrock call failed in synthesize_outbound: %s", exc)
        return OutboundDraft()

    parsed = extract_json(raw)
    if not isinstance(parsed, dict):
        logger.warning(
            "Could not parse JSON from outbound response: %s", raw[:200]
        )
        return OutboundDraft()

    try:
        return OutboundDraft.model_validate(parsed)
    except Exception as exc:
        logger.warning("Outbound JSON failed validation: %s", exc)
        return OutboundDraft()
