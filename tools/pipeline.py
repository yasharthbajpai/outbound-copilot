"""End-to-end research pipeline orchestrator."""
from __future__ import annotations

from typing import Optional

from models import CompanyInput, ResearchResult
from services import BedrockClient
from utils.logging import get_logger

from .company_website import get_company_website_content
from .key_signals import extract_key_signals
from .linkedin_summary import get_linkedin_summary
from .outbound_synthesis import synthesize_outbound

logger = get_logger(__name__)


def run_research(
    company_input: CompanyInput,
    client: Optional[BedrockClient] = None,
) -> ResearchResult:
    """Run all four stages and return a single `ResearchResult`."""
    client = client or BedrockClient()

    logger.info("Fetching website content for %s", company_input.domain)
    website = get_company_website_content(
        domain=company_input.domain, name=company_input.name
    )

    logger.info("Extracting key signals (text source: %s)", website.source)
    signals = extract_key_signals(website.text, client=client)

    linkedin = None
    if company_input.linkedin_profile_text:
        logger.info("Summarizing pasted LinkedIn profile")
        linkedin = get_linkedin_summary(
            company_input.linkedin_profile_text, client=client
        )

    logger.info("Synthesizing outbound draft")
    outbound = synthesize_outbound(
        company_input=company_input,
        website_text=website.text,
        signals=signals,
        linkedin=linkedin,
        client=client,
    )

    return ResearchResult(
        input=company_input,
        website=website,
        signals=signals,
        linkedin=linkedin,
        outbound=outbound,
    )
