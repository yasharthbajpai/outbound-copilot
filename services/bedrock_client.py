"""Amazon Bedrock client for Anthropic Claude models.

We use the native `bedrock-runtime` invoke_model API with the Anthropic
messages payload. boto3 reads AWS credentials from environment variables,
the shared credentials file, or an attached IAM role — exactly the order
the standard credential chain uses, which is what we want.
"""
from __future__ import annotations

import json
from typing import List, Optional

from config import Settings, get_settings
from utils.logging import get_logger

logger = get_logger(__name__)


class BedrockError(RuntimeError):
    """Raised for any failure invoking Bedrock."""


class BedrockClient:
    """Thin wrapper around bedrock-runtime invoke_model."""

    # API version expected by Anthropic models on Bedrock.
    ANTHROPIC_VERSION = "bedrock-2023-05-31"

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()
        self._client = None  # lazy

    def _ensure_client(self):
        if self._client is not None:
            return self._client
        try:
            import boto3  # type: ignore
        except ImportError as exc:
            raise BedrockError(
                "boto3 is not installed. Run `pip install -r requirements.txt`."
            ) from exc

        kwargs = {"region_name": self.settings.aws_region}
        if self.settings.aws_access_key_id and self.settings.aws_secret_access_key:
            kwargs["aws_access_key_id"] = self.settings.aws_access_key_id
            kwargs["aws_secret_access_key"] = self.settings.aws_secret_access_key
            if self.settings.aws_session_token:
                kwargs["aws_session_token"] = self.settings.aws_session_token

        try:
            self._client = boto3.client("bedrock-runtime", **kwargs)
        except Exception as exc:  # pragma: no cover - boto3 init rarely fails
            raise BedrockError(f"Failed to create Bedrock client: {exc}") from exc
        return self._client

    def invoke(
        self,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> str:
        """Run a single-turn Claude completion and return the text content."""
        client = self._ensure_client()

        messages: List[dict] = [{"role": "user", "content": prompt}]
        body = {
            "anthropic_version": self.ANTHROPIC_VERSION,
            "max_tokens": max_tokens or self.settings.max_tokens,
            "temperature": (
                temperature if temperature is not None else self.settings.temperature
            ),
            "messages": messages,
        }
        if system:
            body["system"] = system

        try:
            response = client.invoke_model(
                modelId=self.settings.bedrock_model_id,
                contentType="application/json",
                accept="application/json",
                body=json.dumps(body),
            )
        except Exception as exc:
            raise BedrockError(f"Bedrock invoke_model failed: {exc}") from exc

        try:
            payload = json.loads(response["body"].read())
        except Exception as exc:
            raise BedrockError(f"Could not decode Bedrock response: {exc}") from exc

        # Anthropic messages format: content is a list of {type, text} blocks.
        content = payload.get("content") or []
        chunks = [
            block.get("text", "")
            for block in content
            if isinstance(block, dict) and block.get("type") == "text"
        ]
        text = "".join(chunks).strip()
        if not text:
            raise BedrockError(f"Empty completion from Bedrock: {payload!r}")
        return text
