"""Robust JSON extraction from LLM text output, plus prompt-safety helpers.

LLMs sometimes wrap JSON in code fences, prose, or both. `extract_json`
tolerates that and returns the first valid JSON object found, or None.

`sanitize_prompt_content` prevents prompt-injection via XML tag breakout:
any ``</`` sequence in user-supplied text is neutralised so it cannot
close the enclosing tag in the prompt template.
"""
from __future__ import annotations

import json
import re
from typing import Any, Optional

_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE)
# Matches any closing XML/HTML tag written into user-controlled content.
_CLOSING_TAG_RE = re.compile(r"</", re.IGNORECASE)


def sanitize_prompt_content(text: str) -> str:
    """Escape closing XML tags to prevent prompt-injection tag breakout.

    Replaces every ``</`` occurrence with ``<\u200c/`` (zero-width
    non-joiner inserted) so the sequence cannot terminate the enclosing
    ``<tag>…</tag>`` block in a prompt template, while remaining
    semantically transparent to the LLM.
    """
    if not text:
        return text
    return _CLOSING_TAG_RE.sub("<\u200c/", text)


def extract_json(text: str) -> Optional[Any]:
    """Return the first parseable JSON value in `text`, or None.

    Strategy:
      1. Try parsing the whole text as JSON.
      2. Try contents of any ```json ... ``` (or ``` ... ```) fenced block.
      3. Scan for the first balanced `{...}` or `[...]` and try that.
    """
    if not text:
        return None

    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    for match in _FENCE_RE.finditer(text):
        body = match.group(1).strip()
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            continue

    for opener, closer in (("{", "}"), ("[", "]")):
        start = text.find(opener)
        while start != -1:
            depth = 0
            in_str = False
            escape = False
            for i in range(start, len(text)):
                ch = text[i]
                if in_str:
                    if escape:
                        escape = False
                    elif ch == "\\":
                        escape = True
                    elif ch == '"':
                        in_str = False
                    continue
                if ch == '"':
                    in_str = True
                elif ch == opener:
                    depth += 1
                elif ch == closer:
                    depth -= 1
                    if depth == 0:
                        candidate = text[start : i + 1]
                        try:
                            return json.loads(candidate)
                        except json.JSONDecodeError:
                            break
            start = text.find(opener, start + 1)

    return None
