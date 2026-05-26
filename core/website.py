"""Fetch and extract readable text from a company website.

Strategy, in order:
  1. Plain HTTP GET via httpx/requests, parsed with trafilatura (best
     readability extraction) and a BeautifulSoup fallback.
  2. Playwright headless browser for JS-rendered sites.
  3. As a last resort, ask Claude for a best-effort description from
     company name + domain alone.

Each stage is wrapped in try/except — the caller always gets a
`WebsiteFetchResult`, never an unhandled exception.
"""
from __future__ import annotations

import ipaddress
import socket
from typing import Optional, Tuple
from urllib.parse import urlparse

from config import get_settings
from models import WebsiteFetchResult
from services import BedrockClient, BedrockError
from utils.logging import get_logger

logger = get_logger(__name__)

# Private / link-local / loopback ranges that must never be fetched (SSRF guard).
_BLOCKED_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),      # loopback
    ipaddress.ip_network("::1/128"),           # IPv6 loopback
    ipaddress.ip_network("10.0.0.0/8"),        # RFC-1918
    ipaddress.ip_network("172.16.0.0/12"),     # RFC-1918
    ipaddress.ip_network("192.168.0.0/16"),    # RFC-1918
    ipaddress.ip_network("169.254.0.0/16"),    # link-local / AWS metadata
    ipaddress.ip_network("fd00::/8"),          # IPv6 unique-local
    ipaddress.ip_network("fe80::/10"),         # IPv6 link-local
    ipaddress.ip_network("0.0.0.0/8"),         # "this" network
    ipaddress.ip_network("100.64.0.0/10"),     # shared address space
]


def _is_safe_url(url: str) -> bool:
    """Return False if the URL resolves to a private/internal address."""
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname
        if not hostname:
            return False
        try:
            addr = ipaddress.ip_address(hostname)
            return not any(addr in net for net in _BLOCKED_NETWORKS)
        except ValueError:
            pass  # not an IP literal — resolve it
        try:
            infos = socket.getaddrinfo(hostname, None)
        except socket.gaierror:
            # DNS failed — the HTTP request will also fail naturally; no SSRF risk.
            return True
        for _, _, _, _, sockaddr in infos:
            raw_addr = sockaddr[0]
            try:
                addr = ipaddress.ip_address(raw_addr)
                if any(addr in net for net in _BLOCKED_NETWORKS):
                    logger.warning("SSRF guard: %s resolves to private IP %s", hostname, addr)
                    return False
            except ValueError:
                continue
        return True
    except Exception as exc:
        logger.warning("URL safety check failed for %s: %s", url, exc)
        return False


def _normalize_url(domain: str) -> str:
    domain = domain.strip()
    if domain.startswith("http://") or domain.startswith("https://"):
        return domain
    return f"https://{domain}"


def _clean_text(text: str) -> str:
    """Collapse whitespace and trim huge pages to something Claude can chew."""
    if not text:
        return ""
    lines = [ln.strip() for ln in text.splitlines()]
    nonempty = [ln for ln in lines if ln]
    joined = "\n".join(nonempty)
    return joined[:20_000]


def _http_fetch(url: str, timeout: int) -> Tuple[str, str]:
    """Return (html, final_url). Raises on failure."""
    try:
        import httpx  # type: ignore

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (compatible; outbound-copilot/0.1; +https://example.local)"
            )
        }
        with httpx.Client(
            timeout=timeout, follow_redirects=True, headers=headers
        ) as client:
            resp = client.get(url)
            resp.raise_for_status()
            return resp.text, str(resp.url)
    except ImportError:
        pass
    except Exception as exc:
        logger.info("httpx fetch failed for %s: %s", url, exc)

    import requests  # type: ignore

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (compatible; outbound-copilot/0.1; +https://example.local)"
        )
    }
    resp = requests.get(url, timeout=timeout, headers=headers, allow_redirects=True)
    resp.raise_for_status()
    return resp.text, resp.url


def _extract_from_html(html: str, url: str) -> str:
    """Run trafilatura first (better readability), fall back to BeautifulSoup."""
    if not html:
        return ""

    try:
        import trafilatura  # type: ignore

        extracted = trafilatura.extract(
            html,
            url=url,
            include_comments=False,
            include_tables=False,
            favor_recall=True,
        )
        if extracted:
            return _clean_text(extracted)
    except Exception as exc:
        logger.info("trafilatura failed: %s", exc)

    try:
        from bs4 import BeautifulSoup  # type: ignore

        soup = BeautifulSoup(html, "lxml") if _has_lxml() else BeautifulSoup(
            html, "html.parser"
        )
        for tag in soup(["script", "style", "noscript", "header", "footer", "nav"]):
            tag.decompose()
        text = soup.get_text(separator="\n")
        return _clean_text(text)
    except Exception as exc:
        logger.info("BeautifulSoup parse failed: %s", exc)
        return ""


def _has_lxml() -> bool:
    try:
        import lxml  # noqa: F401
        return True
    except ImportError:
        return False


def _playwright_fetch(url: str, timeout: int) -> Optional[str]:
    """Render `url` in headless Chromium and return extracted text."""
    try:
        from playwright.sync_api import sync_playwright  # type: ignore
    except ImportError:
        logger.info("Playwright not installed; skipping headless fallback")
        return None

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (compatible; outbound-copilot/0.1)"
                )
                page = context.new_page()
                page.goto(url, timeout=timeout * 1000, wait_until="domcontentloaded")
                try:
                    page.wait_for_load_state("networkidle", timeout=timeout * 1000)
                except Exception:
                    pass
                html = page.content()
            finally:
                browser.close()
        return _extract_from_html(html, url)
    except Exception as exc:
        logger.info("Playwright fetch failed for %s: %s", url, exc)
        return None


def _llm_best_effort(name: str, domain: str) -> str:
    """Ask Claude for a best-effort description when scraping is impossible."""
    try:
        client = BedrockClient()
    except Exception as exc:
        logger.warning("Could not initialize Bedrock for fallback: %s", exc)
        return ""

    system = (
        "You are a business research analyst. The user gives you a company "
        "name and domain. Reply with a concise factual description of what "
        "the company likely does, who it serves, and any obvious public "
        "signals. If you are uncertain, say so explicitly. Keep it under "
        "250 words. Do not invent specific funding amounts, headcounts, or "
        "executives."
    )
    prompt = (
        f"Company name: {name}\nCompany domain: {domain}\n\n"
        "Write the description now."
    )
    try:
        return client.invoke(prompt=prompt, system=system).strip()
    except BedrockError as exc:
        logger.warning("LLM fallback failed: %s", exc)
        return ""


def get_company_website_content(
    domain: str, name: Optional[str] = None
) -> WebsiteFetchResult:
    """Fetch and extract readable text describing the company.

    Args:
        domain: The company website domain (with or without scheme).
        name:   Optional company name — used only for the LLM fallback.
    """
    if not domain or not domain.strip():
        return WebsiteFetchResult(text="", source="none", error="Empty domain")

    settings = get_settings()
    url = _normalize_url(domain)

    if not _is_safe_url(url):
        logger.warning("Blocked fetch to private/internal URL: %s", url)
        return WebsiteFetchResult(
            text="",
            source="none",
            error=f"Domain '{domain}' resolves to a private or reserved address and was blocked",
        )

    last_error: Optional[str] = None
    text = ""
    final_url = url

    try:
        html, final_url = _http_fetch(url, settings.http_timeout_seconds)
        text = _extract_from_html(html, final_url)
    except Exception as exc:
        last_error = f"http fetch failed: {exc}"
        logger.info(last_error)

    if len(text) >= settings.min_website_text_chars:
        return WebsiteFetchResult(text=text, source="http", url=final_url)

    rendered = _playwright_fetch(url, settings.http_timeout_seconds)
    if rendered and len(rendered) >= settings.min_website_text_chars:
        return WebsiteFetchResult(text=rendered, source="playwright", url=url)
    if rendered and len(rendered) > len(text):
        text = rendered

    fallback = _llm_best_effort(name or domain, domain)
    if fallback:
        return WebsiteFetchResult(
            text=fallback,
            source="llm_fallback",
            url=url,
            error=last_error,
        )

    return WebsiteFetchResult(
        text=text,
        source="http" if text else "none",
        url=url,
        error=last_error or "All extraction stages produced insufficient text",
    )
