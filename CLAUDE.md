# CLAUDE.md

## Project Overview

**zscaler-dr-pacbuilder** is a Python application that generates proxy auto-config (PAC) files for Zscaler ZIA Disaster Recovery mode. It reads a domain allow-list from a text file (`allow-list.txt`), optionally deduplicates against Zscaler's pre-selected destinations, renders a Jinja2 template, validates the output, and writes a `proxy.pac` file. Domains on the allow list get DIRECT internet access during DR mode; all other traffic is blocked via `PROXY 127.0.0.1:1`.

**License:** GNU AGPL v3

## Repository Structure

```
.
├── CLAUDE.md              # This file — AI assistant guidance
├── LICENSE                # GNU AGPL v3
├── TODO.md                # Project description and task tracking
├── allow-list.txt         # Newline-delimited list of domains to allow
├── pacbuilder.py          # Main application — parses, deduplicates, renders, validates
├── proxy.pac              # Generated output PAC file (do not edit manually)
├── requirements.txt       # Python dependencies (jinja2)
├── templates/
│   └── proxy.pac.j2       # Jinja2 template for PAC file generation
└── tests/
    └── test_pacbuilder.py  # pytest test suite (19 tests)
```

## Key Files

- **`pacbuilder.py`** — Main entry point. Reads `allow-list.txt`, deduplicates against Zscaler's drdb.txt, renders the Jinja2 template, validates the PAC output, and writes `proxy.pac`.
- **`templates/proxy.pac.j2`** — Jinja2 template for the PAC file. Receives a `domains` list variable.
- **`allow-list.txt`** — One domain per line. Supports comments (`#`) and blank lines. Apex domains only.
- **`proxy.pac`** — Generated output. Do not edit manually; re-run `pacbuilder.py` instead.

## Usage

```bash
# Install dependencies
pip install -r requirements.txt

# Generate proxy.pac (with Zscaler deduplication)
python3 pacbuilder.py

# Skip deduplication (if Zscaler URL is unreachable)
python3 pacbuilder.py --skip-dedup

# Skip PAC validation
python3 pacbuilder.py --skip-validation

# Custom paths
python3 pacbuilder.py --allow-list my-domains.txt --output out/proxy.pac
```

## Running Tests

```bash
pip install pytest
python3 -m pytest tests/ -v
```

All 19 tests cover: allow-list parsing, domain validation, deduplication, template rendering, and PAC syntax validation.

## Conventions

### PAC File Format
- The `FindProxyForURL(url, host)` function is the standard entry point
- Domain matching uses `dnsDomainIs()` for subdomain support
- Allowed domains return `"DIRECT"`; everything else returns `"PROXY 127.0.0.1:1"`
- Domain strings in the `allowed` array must be quoted (e.g., `"whatismyip.com"`)
- The generated PAC includes a domain count comment for quick verification

### Allow List Format
- Plain text, one domain per line
- Lines starting with `#` are comments
- Blank lines are ignored
- Apex domains only (subdomain matching is handled by the PAC logic)
- No protocol prefixes (no `https://`)
- Invalid domains are warned and skipped

### Zscaler Deduplication
- Fetches `https://dll7xpq8c5ev0.cloudfront.net/drdb.txt` to get Zscaler's pre-selected destinations
- Domains already in Zscaler's list are removed from the custom PAC to avoid redundancy
- Handles `*.domain.com` wildcard entries by extracting the apex domain
- Gracefully degrades if the URL is unreachable (warns and continues)

### PAC Validation
- Checks for required `FindProxyForURL` function, `DIRECT` and `PROXY` returns
- Uses Node.js (`node -e`) for JavaScript syntax validation when available
- Falls back to structural checks if Node.js is not installed

## AI Assistant Guidelines

- `proxy.pac` is a generated file — always modify the template (`templates/proxy.pac.j2`) or `pacbuilder.py` instead
- Run `python3 -m pytest tests/ -v` after any changes to verify correctness
- Keep implementations simple; prefer Python standard library where possible
- The only external dependency is `jinja2`
- Respect the GNU AGPL v3 license requirements when adding dependencies
