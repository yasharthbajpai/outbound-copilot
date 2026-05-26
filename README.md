# outbound-copilot

An MCP-inspired terminal agent for outbound sales research. Give it a
company name and domain (and optionally a pasted LinkedIn profile for a
contact) and it produces structured signals plus a tailored outbound
draft — value props, an icebreaker, and an email snippet — using Claude
on Amazon Bedrock.

## Why this design

Each capability is a single-purpose **tool** with a typed input/output
contract, in the spirit of MCP. A thin **pipeline** orchestrates them.
This makes each step easy to test, swap, or expose over a real MCP
server later.

```
config/    Env-driven settings
services/  Bedrock client (boto3, Anthropic messages API)
tools/     get_company_website_content, extract_key_signals,
           get_linkedin_summary, synthesize_outbound, pipeline
models/    Pydantic schemas for every step's I/O
utils/     JSON extraction, logging, terminal rendering
tests/     Import/structure/validation tests (no AWS needed)
main.py    CLI entrypoint
```

## Setup

```bash
python -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Install the headless browser (optional but recommended)

Playwright is used to fall back to a real browser for JS-rendered sites.
Install the bundled Chromium with:

```bash
python -m playwright install chromium
```

If you skip this step the app still works — Playwright fetches are
quietly skipped and the pipeline falls back to the LLM best-effort
description.

### Configure environment

```bash
cp .env.example .env
# then edit .env and set at minimum:
#   BEDROCK_MODEL_ID   (e.g. anthropic.claude-3-5-sonnet-20241022-v2:0)
#   AWS_REGION         (e.g. us-east-1)
# AWS credentials follow the standard chain — env vars, ~/.aws/credentials,
# IAM role, or SSO all work.
```

| Variable | Required | Purpose |
|---|---|---|
| `BEDROCK_MODEL_ID` | **yes** | Full Bedrock model id, no default |
| `AWS_REGION` | yes (defaults to `us-east-1`) | Region with model access |
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` / `AWS_SESSION_TOKEN` | optional | If unset, default credential chain is used |
| `BEDROCK_MAX_TOKENS` | optional (1500) | Per-call token cap |
| `BEDROCK_TEMPERATURE` | optional (0.2) | Sampling temperature |
| `HTTP_TIMEOUT_SECONDS` | optional (15) | Web fetch timeout |
| `MIN_WEBSITE_TEXT_CHARS` | optional (400) | Below this we fall back to Playwright / LLM |

## Run the CLI

Interactive (prompts for each field):

```bash
python main.py
```

Non-interactive:

```bash
python main.py --name "Acme" --domain "acme.com" --skip-linkedin
python main.py --name "Acme" --domain "acme.com" --linkedin-file ./jane.txt --json
```

Flags:

- `--name`, `--domain`: skip the corresponding prompts
- `--linkedin-file PATH`: read profile text from a file instead of pasting
- `--skip-linkedin`: do not include any profile in the run
- `--json`: print the full `ResearchResult` as JSON

## MCP Server

`mcp_server.py` exposes the four research steps — plus a full-pipeline
convenience tool — as real [MCP](https://modelcontextprotocol.io) tools
that any MCP client (Claude Desktop, Cursor, etc.) can call directly.

### Tools exposed

| Tool | Description |
|------|-------------|
| `research_company_website` | Fetch + extract website text (HTTP → Playwright → LLM fallback) |
| `extract_company_signals` | Claude extracts hiring, funding, ICP, product focus, etc. |
| `summarize_linkedin_profile` | Structure a manually pasted LinkedIn profile |
| `synthesize_outbound_draft` | Generate value props, icebreaker, email snippet |
| `run_full_research` | One-shot: all four steps in a single call |

### Claude Desktop config

Add this block to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "outbound-copilot": {
      "command": "/path/to/outbound-copilot/.venv/bin/python",
      "args": ["/path/to/outbound-copilot/mcp_server.py"],
      "env": {
        "BEDROCK_MODEL_ID": "us.anthropic.claude-sonnet-4-6",
        "AWS_REGION": "us-east-1",
        "AWS_ACCESS_KEY_ID": "...",
        "AWS_SECRET_ACCESS_KEY": "..."
      }
    }
  }
}
```

### Cursor MCP config

Add to `.cursor/mcp.json` in your project (or `~/.cursor/mcp.json` globally):

```json
{
  "mcpServers": {
    "outbound-copilot": {
      "command": "/path/to/outbound-copilot/.venv/bin/python",
      "args": ["/path/to/outbound-copilot/mcp_server.py"]
    }
  }
}
```

### HTTP mode (network-accessible)

```bash
python mcp_server.py --http            # listens on 0.0.0.0:8000
python mcp_server.py --http --port 9000
```

## Pipeline

1. **`research_company_website(domain)`** — tries `httpx`/`requests` +
   `trafilatura`/BeautifulSoup, then Playwright headless Chromium, then
   a Claude-on-Bedrock best-effort description from name+domain.
2. **`extract_company_signals(text)`** — Claude returns structured JSON:
   `hiring_signals`, `funding_signals`, `product_focus`,
   `market_segment`, `ideal_customer_profile`, `notable_initiatives`.
3. **`summarize_linkedin_profile(raw_profile_text)`** — Claude structures
   pasted profile text into `name`, `current_role`, `seniority_level`,
   `responsibilities_summary`, `relevant_topics`, `outbound_angle`.
4. **`synthesize_outbound_draft(...)`** — Claude combines the above into
   1-2 value propositions, an icebreaker, and an email snippet.

Every step degrades gracefully: if any LLM call fails, the rest of the
pipeline still runs with empty results for the failed stage.

## Tests

```bash
python -m unittest discover -s tests -v
```

These tests do not require AWS credentials — they exercise imports,
config validation, model serialization, and the JSON extractor.

## LinkedIn compliance note

This project **does not scrape LinkedIn**. The LinkedIn step accepts
only text that the user has manually copied from a profile they are
authorized to view. Automated scraping of LinkedIn violates LinkedIn's
User Agreement and may also run afoul of the CFAA / similar laws in
some jurisdictions. If you want a richer contact step, prefer
LinkedIn's official APIs (Sales Navigator, Marketing Developer
Platform) or a licensed data provider.

## Output

Two representations of every run:

- **Terminal**: human-readable, formatted with `rich` if available.
- **JSON**: full pydantic dump via `--json`, matching the
  `ResearchResult` schema in `models/schemas.py`. Suitable for piping
  into another tool, storing in a CRM, or exposing over an MCP server.
