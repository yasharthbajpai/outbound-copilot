"""Terminal entrypoint for outbound-copilot.

Run with:
    python main.py
"""
from __future__ import annotations

import argparse
import json
import sys

from config import ConfigError, get_settings
from models import CompanyInput
from tools import run_research
from utils.logging import get_logger
from utils.render import render, render_plain

logger = get_logger("outbound_copilot.cli")


def _prompt(label: str, allow_empty: bool = False) -> str:
    """Prompt the user, retrying when input is required but empty."""
    while True:
        try:
            value = input(f"{label}: ").strip()
        except EOFError:
            value = ""
        if value or allow_empty:
            return value
        print("  This field is required.")


def _prompt_multiline(label: str) -> str:
    """Read multiline input until a line containing only 'END' (or EOF)."""
    print(f"{label}")
    print("  (Paste profile text. Finish with a line containing only 'END',")
    print("   or press Ctrl-D / Ctrl-Z then Enter. Leave empty to skip.)")
    lines = []
    try:
        while True:
            line = input()
            if line.strip() == "END":
                break
            lines.append(line)
    except EOFError:
        pass
    return "\n".join(lines).strip()


def _collect_input(args: argparse.Namespace) -> CompanyInput:
    name = args.name or _prompt("Company name")
    domain = args.domain or _prompt("Company domain (e.g. acme.com)")
    if args.skip_linkedin:
        profile = ""
    elif args.linkedin_file:
        with open(args.linkedin_file, "r", encoding="utf-8") as fh:
            profile = fh.read().strip()
    else:
        profile = _prompt_multiline(
            "Optional LinkedIn-style profile text for a contact at this company:"
        )
    return CompanyInput(
        name=name,
        domain=domain,
        linkedin_profile_text=profile or None,
    )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="outbound-copilot",
        description=(
            "Research a company and produce a tailored outbound draft using "
            "Claude on Amazon Bedrock."
        ),
    )
    parser.add_argument("--name", help="Company name (skip prompt)")
    parser.add_argument("--domain", help="Company domain (skip prompt)")
    parser.add_argument(
        "--linkedin-file",
        help="Path to a text file with pasted LinkedIn profile text",
    )
    parser.add_argument(
        "--skip-linkedin",
        action="store_true",
        help="Do not prompt for or include LinkedIn profile text",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the full result as JSON instead of a formatted view",
    )
    args = parser.parse_args(argv)

    try:
        get_settings()  # validates required env vars early
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2

    try:
        company_input = _collect_input(args)
    except (KeyboardInterrupt, EOFError):
        print("\nAborted.", file=sys.stderr)
        return 130

    try:
        result = run_research(company_input)
    except Exception as exc:  # pragma: no cover - last-resort safety net
        logger.exception("Research pipeline crashed: %s", exc)
        print(f"Fatal error: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(result.model_dump_json(indent=2))
    else:
        try:
            render(result)
        except Exception:
            print(render_plain(result))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
