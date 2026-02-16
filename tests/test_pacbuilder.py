"""Tests for pacbuilder."""

import textwrap
from pathlib import Path
from unittest.mock import patch

import pytest

from pacbuilder import (
    deduplicate,
    fetch_zscaler_preselected,
    parse_allow_list,
    render_pac,
    validate_pac,
)

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"


# --- parse_allow_list ---


def test_parse_allow_list_basic(tmp_path):
    f = tmp_path / "allow.txt"
    f.write_text("example.com\ntest.org\n")
    result = parse_allow_list(f)
    assert result == ["example.com", "test.org"]


def test_parse_allow_list_deduplicates_and_sorts(tmp_path):
    f = tmp_path / "allow.txt"
    f.write_text("zebra.com\nalpha.com\nzebra.com\n")
    result = parse_allow_list(f)
    assert result == ["alpha.com", "zebra.com"]


def test_parse_allow_list_skips_blanks_and_comments(tmp_path):
    f = tmp_path / "allow.txt"
    f.write_text("# comment\n\nexample.com\n   \n# another\ntest.org\n")
    result = parse_allow_list(f)
    assert result == ["example.com", "test.org"]


def test_parse_allow_list_lowercases(tmp_path):
    f = tmp_path / "allow.txt"
    f.write_text("Example.COM\n")
    result = parse_allow_list(f)
    assert result == ["example.com"]


def test_parse_allow_list_skips_invalid(tmp_path, capsys):
    f = tmp_path / "allow.txt"
    f.write_text("good.com\nhttps://bad.com\n-bad.com\ngood2.org\n")
    result = parse_allow_list(f)
    assert result == ["good.com", "good2.org"]
    captured = capsys.readouterr()
    assert "skipping invalid domain" in captured.err.lower()


def test_parse_allow_list_missing_file(tmp_path):
    with pytest.raises(SystemExit):
        parse_allow_list(tmp_path / "missing.txt")


def test_parse_allow_list_empty_file(tmp_path):
    f = tmp_path / "allow.txt"
    f.write_text("# only comments\n\n")
    with pytest.raises(SystemExit):
        parse_allow_list(f)


# --- deduplicate ---


def test_deduplicate_removes_matches():
    allow = ["a.com", "b.com", "c.com"]
    zscaler = {"b.com", "d.com"}
    kept, removed = deduplicate(allow, zscaler)
    assert kept == ["a.com", "c.com"]
    assert removed == ["b.com"]


def test_deduplicate_no_overlap():
    allow = ["a.com", "b.com"]
    zscaler = {"x.com", "y.com"}
    kept, removed = deduplicate(allow, zscaler)
    assert kept == ["a.com", "b.com"]
    assert removed == []


# --- fetch_zscaler_preselected ---


def test_fetch_zscaler_preselected_parses_response():
    body = "example.com\n*.wildcard.org\n# comment\n\nbad---.invalid\ntest.net\n"

    def mock_urlopen(req, timeout=None):
        from io import BytesIO
        from unittest.mock import MagicMock

        resp = MagicMock()
        resp.read.return_value = body.encode()
        resp.__enter__ = lambda s: s
        resp.__exit__ = lambda s, *a: None
        return resp

    with patch("pacbuilder.urllib.request.urlopen", side_effect=mock_urlopen):
        result = fetch_zscaler_preselected("http://fake")

    assert "example.com" in result
    assert "wildcard.org" in result
    assert "test.net" in result


def test_fetch_zscaler_preselected_handles_failure():
    with patch(
        "pacbuilder.urllib.request.urlopen",
        side_effect=OSError("connection failed"),
    ):
        result = fetch_zscaler_preselected("http://fake")
    assert result == set()


# --- render_pac ---


def test_render_pac_single_domain():
    pac = render_pac(["example.com"], TEMPLATE_DIR)
    assert 'FindProxyForURL' in pac
    assert '"example.com"' in pac
    assert "DIRECT" in pac
    assert "PROXY 127.0.0.1:1" in pac
    assert "Domain count: 1" in pac


def test_render_pac_multiple_domains():
    pac = render_pac(["a.com", "b.com", "c.com"], TEMPLATE_DIR)
    assert '"a.com",' in pac
    assert '"b.com",' in pac
    # last domain should not have trailing comma
    assert '"c.com"\n' in pac
    assert "Domain count: 3" in pac


def test_render_pac_no_domains():
    pac = render_pac([], TEMPLATE_DIR)
    assert "var allowed = [\n    ];" in pac


# --- validate_pac ---


def test_validate_pac_valid():
    pac = render_pac(["example.com"], TEMPLATE_DIR)
    assert validate_pac(pac) is True


def test_validate_pac_missing_function():
    assert validate_pac("var x = 1;") is False


def test_validate_pac_missing_direct():
    assert validate_pac("function FindProxyForURL() { return 'PROXY 1'; }") is False


def test_validate_pac_missing_proxy():
    assert validate_pac("function FindProxyForURL() { return 'DIRECT'; }") is False


# --- Integration: full render + validate ---


def test_generated_pac_is_valid_javascript():
    """The generated PAC file from the template should pass Node.js parsing."""
    domains = ["example.com", "test.org", "another.net"]
    pac = render_pac(domains, TEMPLATE_DIR)
    assert validate_pac(pac) is True
    # Verify all domains present and properly quoted
    for d in domains:
        assert f'"{d}"' in pac
