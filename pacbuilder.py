#!/usr/bin/env python3
"""
zscaler-dr-pacbuilder - Generate proxy.pac files for Zscaler ZIA DR mode.

Reads domains from allow-list.txt, optionally deduplicates against Zscaler's
pre-selected destinations list, renders a Jinja2 template, and validates
the output PAC file.
"""

import argparse
import re
import subprocess
import sys
import urllib.request
import urllib.error
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

ZSCALER_DRDB_URL = "https://dll7xpq8c5ev0.cloudfront.net/drdb.txt"
DOMAIN_RE = re.compile(
    r"^(?!-)[A-Za-z0-9-]{1,63}(?<!-)(\.[A-Za-z0-9-]{1,63})*\.[A-Za-z]{2,}$"
)
INVALID_CHARS_RE = re.compile(r"""[\"',;:!@#$%^&*()+=\[\]{}<>|\\~` \t]""")


def _check_invalid_chars(line: str) -> str | None:
    """Return a description of invalid characters found in a line, or None if clean."""
    found = set(INVALID_CHARS_RE.findall(line))
    if not found:
        return None
    char_descriptions = []
    for ch in sorted(found):
        if ch == '"':
            char_descriptions.append('double quote (")')
        elif ch == "'":
            char_descriptions.append("single quote (')")
        elif ch == ",":
            char_descriptions.append("comma (,)")
        elif ch == " ":
            char_descriptions.append("space")
        elif ch == "\t":
            char_descriptions.append("tab")
        else:
            char_descriptions.append(f"'{ch}'")
    return ", ".join(char_descriptions)


def parse_allow_list(path: Path) -> list[str]:
    """Read allow-list.txt and return a sorted list of unique, valid domains."""
    if not path.is_file():
        print(f"Error: allow list not found: {path}", file=sys.stderr)
        sys.exit(1)

    domains: list[str] = []
    with open(path) as f:
        for lineno, raw_line in enumerate(f, start=1):
            line = raw_line.strip().lower()
            if not line or line.startswith("#"):
                continue
            bad_chars = _check_invalid_chars(line)
            if bad_chars:
                print(
                    f"Warning: skipping line {lineno} — contains invalid characters "
                    f"({bad_chars}): {raw_line.rstrip()}",
                    file=sys.stderr,
                )
                continue
            if not DOMAIN_RE.match(line):
                print(
                    f"Warning: skipping invalid domain on line {lineno}: {raw_line.rstrip()}",
                    file=sys.stderr,
                )
                continue
            domains.append(line)

    unique = sorted(set(domains))
    if not unique:
        print("Error: allow list contains no valid domains", file=sys.stderr)
        sys.exit(1)

    return unique


def fetch_zscaler_preselected(url: str = ZSCALER_DRDB_URL) -> set[str]:
    """Fetch Zscaler's pre-selected destinations list and return as a set of domains."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "zscaler-dr-pacbuilder"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            text = resp.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, OSError) as exc:
        print(
            f"Warning: could not fetch Zscaler pre-selected destinations: {exc}",
            file=sys.stderr,
        )
        return set()

    domains: set[str] = set()
    for line in text.splitlines():
        line = line.strip().lower()
        if not line or line.startswith("#"):
            continue
        # drdb.txt may contain wildcards like *.example.com — extract the apex
        if line.startswith("*."):
            line = line[2:]
        if DOMAIN_RE.match(line):
            domains.add(line)

    return domains


def deduplicate(
    allow_list: list[str], zscaler_domains: set[str]
) -> tuple[list[str], list[str]]:
    """Remove domains already in Zscaler's pre-selected list.

    Returns (kept, removed) domain lists.
    """
    kept: list[str] = []
    removed: list[str] = []
    for domain in allow_list:
        if domain in zscaler_domains:
            removed.append(domain)
        else:
            kept.append(domain)
    return kept, removed


def render_pac(domains: list[str], template_dir: Path) -> str:
    """Render proxy.pac from the Jinja2 template with the given domain list."""
    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        keep_trailing_newline=True,
    )
    template = env.get_template("proxy.pac.j2")
    return template.render(domains=domains)


def validate_pac(pac_content: str) -> bool:
    """Validate PAC file syntax using node if available, else basic checks."""
    # Basic structural checks
    if "function FindProxyForURL" not in pac_content:
        print("Validation error: missing FindProxyForURL function", file=sys.stderr)
        return False

    if '"DIRECT"' not in pac_content and "'DIRECT'" not in pac_content:
        print("Validation error: no DIRECT return found", file=sys.stderr)
        return False

    if '"PROXY' not in pac_content and "'PROXY" not in pac_content:
        print("Validation error: no PROXY return found", file=sys.stderr)
        return False

    # Try Node.js syntax check if available
    try:
        result = subprocess.run(
            ["node", "--check", "-e", pac_content],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            # node --check -e doesn't work for syntax checking a string;
            # instead parse it as a script
            result = subprocess.run(
                ["node", "-e", f"new Function({pac_content!r})"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0:
                print(
                    f"Validation error (node): {result.stderr.strip()}",
                    file=sys.stderr,
                )
                return False
        print("PAC file passed Node.js syntax validation", file=sys.stderr)
    except FileNotFoundError:
        print(
            "Note: node not found, skipping JavaScript syntax validation",
            file=sys.stderr,
        )
    except subprocess.TimeoutExpired:
        print("Warning: node validation timed out", file=sys.stderr)

    return True


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate proxy.pac for Zscaler ZIA Disaster Recovery mode."
    )
    parser.add_argument(
        "--allow-list",
        default="allow-list.txt",
        help="Path to the domain allow list (default: allow-list.txt)",
    )
    parser.add_argument(
        "--output",
        default="proxy.pac",
        help="Output path for the generated PAC file (default: proxy.pac)",
    )
    parser.add_argument(
        "--template-dir",
        default=None,
        help="Directory containing proxy.pac.j2 (default: templates/ next to this script)",
    )
    parser.add_argument(
        "--skip-dedup",
        action="store_true",
        help="Skip deduplication against Zscaler pre-selected destinations",
    )
    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Skip PAC file syntax validation",
    )
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    allow_list_path = Path(args.allow_list)
    output_path = Path(args.output)
    template_dir = Path(args.template_dir) if args.template_dir else script_dir / "templates"

    # 1. Parse allow list
    domains = parse_allow_list(allow_list_path)
    print(f"Loaded {len(domains)} domain(s) from {allow_list_path}", file=sys.stderr)

    # 2. Deduplicate against Zscaler pre-selected destinations
    if not args.skip_dedup:
        zscaler_domains = fetch_zscaler_preselected()
        if zscaler_domains:
            domains, removed = deduplicate(domains, zscaler_domains)
            if removed:
                print(
                    f"Removed {len(removed)} domain(s) already in Zscaler pre-selected list: "
                    + ", ".join(removed),
                    file=sys.stderr,
                )
            if not domains:
                print(
                    "Error: all domains were removed by deduplication — "
                    "nothing to add to PAC file",
                    file=sys.stderr,
                )
                sys.exit(1)

    # 3. Render PAC file
    pac_content = render_pac(domains, template_dir)

    # 4. Validate
    if not args.skip_validation:
        if not validate_pac(pac_content):
            print("Error: PAC file validation failed", file=sys.stderr)
            sys.exit(1)

    # 5. Write output
    output_path.write_text(pac_content)
    print(f"Generated {output_path} with {len(domains)} domain(s)", file=sys.stderr)


if __name__ == "__main__":
    main()
