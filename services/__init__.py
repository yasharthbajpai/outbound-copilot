"""External-service adapters (Bedrock, HTTP, headless browser)."""
from .bedrock_client import BedrockClient, BedrockError

__all__ = ["BedrockClient", "BedrockError"]
