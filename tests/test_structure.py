"""Import and structural tests that do not require AWS credentials.

We set a fake BEDROCK_MODEL_ID before importing anything, so settings
validation doesn't blow up.
"""
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

os.environ.setdefault("BEDROCK_MODEL_ID", "test.anthropic.claude-test-v1:0")
os.environ.setdefault("AWS_REGION", "us-east-1")


class StructureTests(unittest.TestCase):
    def test_top_level_modules_importable(self):
        import config  # noqa: F401
        import models  # noqa: F401
        import services  # noqa: F401
        import tools  # noqa: F401
        import utils  # noqa: F401

    def test_settings_load(self):
        from config import get_settings

        settings = get_settings()
        self.assertEqual(
            settings.bedrock_model_id, "test.anthropic.claude-test-v1:0"
        )
        self.assertTrue(settings.aws_region)
        self.assertGreater(settings.max_tokens, 0)
        self.assertGreaterEqual(settings.temperature, 0.0)

    def test_models_roundtrip(self):
        from models import (
            CompanyInput,
            CompanySignals,
            LinkedInSummary,
            OutboundDraft,
            ResearchResult,
            WebsiteFetchResult,
        )

        company = CompanyInput(name="Acme", domain="acme.com")
        signals = CompanySignals(
            hiring_signals=["Hiring 5 SDEs"],
            funding_signals=[],
            product_focus=["Widget platform"],
            market_segment=["SMB"],
            ideal_customer_profile=["Ops teams"],
            notable_initiatives=[],
        )
        result = ResearchResult(
            input=company,
            website=WebsiteFetchResult(
                text="Acme makes widgets.", source="http", url="https://acme.com"
            ),
            signals=signals,
            linkedin=LinkedInSummary(name="Jane", current_role="VP Eng"),
            outbound=OutboundDraft(
                value_propositions=["Faster widgets"],
                icebreaker="Saw the new widget launch.",
                email_snippet="Hi Jane,\n...",
            ),
        )
        as_json = result.model_dump_json()
        self.assertIn("Acme", as_json)
        # Re-validate from the serialized form.
        rebuilt = ResearchResult.model_validate_json(as_json)
        self.assertEqual(rebuilt.input.name, "Acme")
        self.assertEqual(rebuilt.signals.hiring_signals, ["Hiring 5 SDEs"])

    def test_extract_json_handles_fenced_and_plain(self):
        from utils.json_parse import extract_json

        self.assertEqual(extract_json('{"a": 1}'), {"a": 1})
        self.assertEqual(
            extract_json('Here you go:\n```json\n{"a": 2}\n```'), {"a": 2}
        )
        self.assertEqual(
            extract_json('prose ```{"a": 3, "b": [1,2]}``` more prose'),
            {"a": 3, "b": [1, 2]},
        )
        self.assertEqual(
            extract_json('garbage {"a": 4} trailing'), {"a": 4}
        )
        self.assertIsNone(extract_json("no json here"))
        self.assertIsNone(extract_json(""))

    def test_extract_key_signals_empty_text_short_circuits(self):
        from tools.key_signals import extract_key_signals

        # No Bedrock call should happen for empty text.
        result = extract_key_signals("")
        self.assertEqual(result.hiring_signals, [])
        self.assertEqual(result.funding_signals, [])

    def test_get_linkedin_summary_none_for_empty(self):
        from tools.linkedin_summary import get_linkedin_summary

        self.assertIsNone(get_linkedin_summary(""))
        self.assertIsNone(get_linkedin_summary("   "))

    def test_get_company_website_handles_empty_domain(self):
        from tools.company_website import get_company_website_content

        result = get_company_website_content("")
        self.assertEqual(result.source, "none")
        self.assertEqual(result.text, "")

    def test_main_module_importable(self):
        import importlib

        module = importlib.import_module("main")
        self.assertTrue(hasattr(module, "main"))


class ConfigErrorTests(unittest.TestCase):
    def test_missing_model_id_raises(self):
        from unittest.mock import patch

        from config.settings import ConfigError, get_settings

        get_settings.cache_clear()
        saved = os.environ.pop("BEDROCK_MODEL_ID", None)
        try:
            # Prevent load_dotenv from re-injecting BEDROCK_MODEL_ID from
            # the real .env file, which would make this test a false pass.
            with patch("config.settings._load_dotenv_if_present"):
                with self.assertRaises(ConfigError):
                    get_settings()
        finally:
            if saved is not None:
                os.environ["BEDROCK_MODEL_ID"] = saved
            get_settings.cache_clear()


if __name__ == "__main__":
    unittest.main()
