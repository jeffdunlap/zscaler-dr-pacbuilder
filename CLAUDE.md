# CLAUDE.md

## Project Overview

**zscaler-dr-pacbuilder** is a Python application that generates proxy auto-config (PAC) files for Zscaler ZIA Disaster Recovery mode. It reads a domain allow-list from a text file (`allow-list.txt`) and produces a properly formatted `proxy.pac` JavaScript file. Domains on the allow list get DIRECT internet access during DR mode; all other traffic is blocked via `PROXY 127.0.0.1:1`.

**License:** GNU AGPL v3

**Status:** Early stage — template files exist but Python implementation is not yet built.

## Repository Structure

```
.
├── CLAUDE.md          # This file — AI assistant guidance
├── LICENSE            # GNU AGPL v3
├── TODO.md            # Project description and task tracking
├── allow-list.txt     # Newline-delimited list of domains to allow
└── proxy.pac          # Template/output PAC file (JavaScript)
```

## Key Files

- **`allow-list.txt`** — One domain per line (e.g., `whatismyip.com`). These domains (and all subdomains) receive DIRECT access in the generated PAC file.
- **`proxy.pac`** — JavaScript PAC file implementing `FindProxyForURL()`. Currently a static template; will be generated programmatically.
- **`TODO.md`** — Doubles as README and task board. Contains project description and checklist of planned work.

## Development Status & Planned Work

From `TODO.md`, the following are planned:

1. **Python parser** — Read `allow-list.txt` and inject domains into a templated `proxy.pac` file
2. **Zscaler deduplication** — Check entries against the Zscaler pre-selected destinations list at `https://dll7xpq8c5ev0.cloudfront.net/drdb.txt` to avoid duplicates
3. **PAC validation** — Syntax-check the generated `proxy.pac` to confirm correctness

## Conventions

### PAC File Format
- The `FindProxyForURL(url, host)` function is the standard entry point
- Domain matching uses `dnsDomainIs()` for subdomain support
- Allowed domains return `"DIRECT"`; everything else returns `"PROXY 127.0.0.1:1"`
- Domain strings in the `allowed` array must be quoted (e.g., `"whatismyip.com"`)

### Allow List Format
- Plain text, one domain per line
- Apex domains only (subdomain matching is handled by the PAC logic)
- No protocol prefixes (no `https://`)

## Build & Test

No build system, dependency management, or test infrastructure exists yet. When Python implementation is added:

- Expect standard Python tooling (`requirements.txt` or `pyproject.toml`)
- Testing should validate PAC file syntax and correct domain matching behavior
- The generated PAC file should be valid JavaScript parseable by browsers

## Known Issues

- `proxy.pac:10` — Domain entries in the `allowed` array are unquoted (`whatismyip.com` should be `"whatismyip.com"`). This is a syntax error that will cause the PAC file to fail.

## AI Assistant Guidelines

- This is a small, early-stage project. Keep implementations simple and avoid over-engineering.
- The core output is a valid JavaScript PAC file — ensure any generated PAC files are syntactically correct.
- When implementing the Python tooling, prefer standard library where possible given the project's simplicity.
- Respect the GNU AGPL v3 license requirements when adding dependencies.
