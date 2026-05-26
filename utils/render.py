"""Terminal rendering for a ResearchResult.

Uses `rich` if available for nice panels and tables, but falls back to
plain prints so the CLI works without it.
"""
from __future__ import annotations

from models import ResearchResult


def _bullets(items):
    if not items:
        return "  (none)"
    return "\n".join(f"  - {item}" for item in items)


def render_plain(result: ResearchResult) -> str:
    s = result.signals
    parts = [
        "",
        "=" * 70,
        f" Company: {result.input.name}",
        f" Domain:  {result.input.domain}",
        f" Source:  {result.website.source} ({result.website.url or 'n/a'})",
        "=" * 70,
        "",
        "Hiring signals:",
        _bullets(s.hiring_signals),
        "",
        "Funding signals:",
        _bullets(s.funding_signals),
        "",
        "Product focus:",
        _bullets(s.product_focus),
        "",
        "Market segment:",
        _bullets(s.market_segment),
        "",
        "Ideal customer profile:",
        _bullets(s.ideal_customer_profile),
        "",
        "Notable initiatives:",
        _bullets(s.notable_initiatives),
        "",
    ]

    if result.linkedin:
        li = result.linkedin
        parts.extend(
            [
                "-" * 70,
                "LinkedIn summary:",
                f"  Name:        {li.name or '-'}",
                f"  Role:        {li.current_role or '-'}",
                f"  Seniority:   {li.seniority_level or '-'}",
                f"  Summary:     {li.responsibilities_summary or '-'}",
                "  Topics:",
                _bullets(li.relevant_topics),
                f"  Outbound angle: {li.outbound_angle or '-'}",
                "",
            ]
        )

    o = result.outbound
    parts.extend(
        [
            "-" * 70,
            "Outbound draft:",
            "",
            "Value propositions:",
            _bullets(o.value_propositions),
            "",
            "Icebreaker:",
            f"  {o.icebreaker or '(none)'}",
            "",
            "Email snippet:",
            "",
            o.email_snippet or "(none)",
            "",
            "=" * 70,
        ]
    )
    return "\n".join(parts)


def render(result: ResearchResult) -> None:
    """Print the result to stdout using rich if available, plain otherwise."""
    try:
        from rich.console import Console  # type: ignore
        from rich.panel import Panel  # type: ignore
        from rich.markdown import Markdown  # type: ignore

        console = Console()
        s = result.signals
        header = (
            f"[bold]{result.input.name}[/bold]  "
            f"({result.input.domain})\n"
            f"[dim]source: {result.website.source}  "
            f"url: {result.website.url or 'n/a'}[/dim]"
        )
        console.print(Panel.fit(header, title="outbound-copilot"))

        def section(title: str, items):
            console.print(f"[bold cyan]{title}[/bold cyan]")
            if not items:
                console.print("  (none)")
            else:
                for it in items:
                    console.print(f"  • {it}")
            console.print()

        section("Hiring signals", s.hiring_signals)
        section("Funding signals", s.funding_signals)
        section("Product focus", s.product_focus)
        section("Market segment", s.market_segment)
        section("Ideal customer profile", s.ideal_customer_profile)
        section("Notable initiatives", s.notable_initiatives)

        if result.linkedin:
            li = result.linkedin
            console.print(
                Panel(
                    f"[bold]{li.name or '-'}[/bold]  ·  {li.current_role or '-'}\n"
                    f"Seniority: {li.seniority_level or '-'}\n\n"
                    f"{li.responsibilities_summary or ''}\n\n"
                    f"[dim]Outbound angle:[/dim] {li.outbound_angle or '-'}",
                    title="Contact",
                )
            )
            section("Relevant topics", li.relevant_topics)

        o = result.outbound
        section("Value propositions", o.value_propositions)
        console.print(Panel(o.icebreaker or "(none)", title="Icebreaker"))
        console.print(Panel(o.email_snippet or "(none)", title="Email snippet"))
    except ImportError:
        print(render_plain(result))
