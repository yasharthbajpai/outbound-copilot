"""Pydantic models that describe pipeline inputs and outputs.

Using pydantic gives us:
- JSON (de)serialization for terminal display and inter-tool transport
- Validation on values returned from the LLM
- Sensible defaults so partial results don't blow up the pipeline
"""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class CompanyInput(BaseModel):
    """User-provided seed data for one company research run."""
    name: str = Field(..., min_length=1, description="Company name")
    domain: str = Field(..., min_length=1, description="Primary website domain")
    linkedin_profile_text: Optional[str] = Field(
        default=None,
        description="Optional pasted LinkedIn-style profile text for a contact",
    )


class WebsiteFetchResult(BaseModel):
    """Output of the company website fetch step."""
    text: str = Field(default="", description="Plain text extracted from the site")
    source: str = Field(
        default="none",
        description="Which path produced the text: http, playwright, llm_fallback, or none",
    )
    url: Optional[str] = Field(default=None, description="Final URL used")
    error: Optional[str] = Field(default=None, description="Last error if any")


class CompanySignals(BaseModel):
    """Structured signals extracted from raw company text."""
    hiring_signals: List[str] = Field(default_factory=list)
    funding_signals: List[str] = Field(default_factory=list)
    product_focus: List[str] = Field(default_factory=list)
    market_segment: List[str] = Field(default_factory=list)
    ideal_customer_profile: List[str] = Field(default_factory=list)
    notable_initiatives: List[str] = Field(default_factory=list)


class LinkedInSummary(BaseModel):
    """Structured summary of a manually pasted LinkedIn profile."""
    name: Optional[str] = None
    current_role: Optional[str] = None
    seniority_level: Optional[str] = None
    responsibilities_summary: Optional[str] = None
    relevant_topics: List[str] = Field(default_factory=list)
    outbound_angle: Optional[str] = None


class OutboundDraft(BaseModel):
    """The final synthesized outbound artifact."""
    value_propositions: List[str] = Field(default_factory=list)
    icebreaker: str = ""
    email_snippet: str = ""


class ResearchResult(BaseModel):
    """Complete output of one research run, suitable for JSON dump."""
    input: CompanyInput
    website: WebsiteFetchResult
    signals: CompanySignals
    linkedin: Optional[LinkedInSummary] = None
    outbound: OutboundDraft
