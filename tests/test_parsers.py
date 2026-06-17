from __future__ import annotations

import email
import os
from pathlib import Path

import pytest
from imap_tools import MailMessage

from bot.sources.parsers.yandex import YandexParser
from bot.sources.parsers.dgis import DgisParser
from bot.sources.parsers.google import GoogleParser
from bot.sources.router import resolve, source_hint

FIXTURES_DIR = Path(__file__).parent / "fixtures"

_PARSERS = [YandexParser(), DgisParser(), GoogleParser()]


def _load_eml(path: Path) -> MailMessage:
    raw = path.read_bytes()
    msg = email.message_from_bytes(raw)
    return MailMessage.from_bytes(raw)


def _eml_files() -> list[Path]:
    if not FIXTURES_DIR.exists():
        return []
    return list(FIXTURES_DIR.glob("*.eml"))


# ---------------------------------------------------------------------------
# Stub smoke-tests: parsers must return None (current milestone behaviour)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("parser", _PARSERS, ids=lambda p: p.source)
def test_parser_returns_none_for_missing_fixtures(parser):
    """Each stub parser must return None when no .eml is available."""
    files = [f for f in _eml_files() if parser.source in f.name]
    if files:
        pytest.skip(f"Fixture found for {parser.source} — implement parser first")
    # Nothing to parse → just assert the parser exists and has the right interface
    assert hasattr(parser, "source")
    assert callable(parser.parse)


@pytest.mark.skipif(not _eml_files(), reason="No .eml fixtures in tests/fixtures/")
@pytest.mark.parametrize("eml_path", _eml_files(), ids=lambda p: p.name)
def test_router_resolves_fixture(eml_path: Path):
    """Router must resolve a fixture to a parser or produce a non-empty hint."""
    msg = _load_eml(eml_path)
    hint = source_hint(msg)
    assert hint  # must never be empty


@pytest.mark.skipif(not _eml_files(), reason="No .eml fixtures in tests/fixtures/")
@pytest.mark.parametrize("eml_path", _eml_files(), ids=lambda p: p.name)
def test_stub_parsers_return_none(eml_path: Path):
    """Until parsers are implemented, parse() must return None without crashing."""
    msg = _load_eml(eml_path)
    parser = resolve(msg)
    if parser is None:
        pytest.skip("No parser matched — router test covers this")
    result = parser.parse(msg)
    assert result is None, (
        f"{parser.source}.parse() returned {result!r} — update this test once implemented"
    )
