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
DGIS_FIXTURE = FIXTURES_DIR / "dgis_review_1.eml"
DGIS_NEGATIVE_FIXTURE = FIXTURES_DIR / "dgis_review_negative_1.eml"
YANDEX_FIXTURE = FIXTURES_DIR / "yandex_review_1.eml"
YANDEX_DIGEST_3 = FIXTURES_DIR / "yandex_digest_3.eml"
YANDEX_DIGEST_5 = FIXTURES_DIR / "yandex_digest_5.eml"

# Parsers that are still stubs (no fixture, parse() returns empty list)
_STUB_PARSERS = [GoogleParser()]

# All parsers — used for router / smoke tests
_ALL_PARSERS = [YandexParser(), DgisParser(), GoogleParser()]


def _load_eml(path: Path) -> MailMessage:
    raw = path.read_bytes()
    return MailMessage.from_bytes(raw)


def _eml_files() -> list[Path]:
    if not FIXTURES_DIR.exists():
        return []
    return list(FIXTURES_DIR.glob("*.eml"))


# ---------------------------------------------------------------------------
# Stub smoke-tests: parsers without fixtures must expose the right interface
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("parser", _STUB_PARSERS, ids=lambda p: p.source)
def test_parser_returns_empty_for_missing_fixtures(parser):
    """Stub parsers must expose the right interface and return [] without crashing."""
    files = [f for f in _eml_files() if parser.source in f.name]
    if files:
        pytest.skip(f"Fixture found for {parser.source} — implement parser first")
    assert hasattr(parser, "source")
    assert callable(parser.parse)
    assert callable(parser.is_review)


@pytest.mark.skipif(not _eml_files(), reason="No .eml fixtures in tests/fixtures/")
@pytest.mark.parametrize("eml_path", _eml_files(), ids=lambda p: p.name)
def test_router_resolves_fixture(eml_path: Path):
    """Router must resolve a fixture to a parser or produce a non-empty hint."""
    msg = _load_eml(eml_path)
    hint = source_hint(msg)
    assert hint  # must never be empty


@pytest.mark.skipif(not _eml_files(), reason="No .eml fixtures in tests/fixtures/")
@pytest.mark.parametrize("eml_path", _eml_files(), ids=lambda p: p.name)
def test_stub_parsers_return_empty(eml_path: Path):
    """Until parsers are implemented, parse() must return [] without crashing."""
    msg = _load_eml(eml_path)
    parser = resolve(msg)
    if parser is None:
        pytest.skip("No parser matched — router test covers this")
    result = parser.parse(msg)
    if result:
        pytest.skip(f"{parser.source} parser is now implemented — see dedicated test")
    assert result == []


# ---------------------------------------------------------------------------
# 2GIS review fixture
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not DGIS_FIXTURE.exists(), reason="dgis_review_1.eml not found")
def test_dgis_review_1():
    msg = _load_eml(DGIS_FIXTURE)
    parser = DgisParser()

    assert parser.is_review(msg) is True

    reviews = parser.parse(msg)
    assert len(reviews) == 1
    review = reviews[0]
    assert review.source == "dgis"
    assert review.author
    assert review.text.startswith("В восторге")
    assert "притяжения Французская" in review.text
    assert review.url and "account.2gis.com" in review.url
    assert review.rating == 5


@pytest.mark.skipif(not DGIS_NEGATIVE_FIXTURE.exists(), reason="dgis_review_negative_1.eml not found")
def test_dgis_review_negative():
    msg = _load_eml(DGIS_NEGATIVE_FIXTURE)
    parser = DgisParser()

    assert parser.is_review(msg) is True

    reviews = parser.parse(msg)
    assert len(reviews) == 1
    review = reviews[0]
    assert review.source == "dgis"
    assert review.rating == 1


# ---------------------------------------------------------------------------
# Yandex single-review fixture
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not YANDEX_FIXTURE.exists(), reason="yandex_review_1.eml not found")
def test_yandex_review_1():
    msg = _load_eml(YANDEX_FIXTURE)
    parser = YandexParser()

    assert parser.is_review(msg) is True

    reviews = parser.parse(msg)
    assert len(reviews) == 1
    review = reviews[0]
    assert review.source == "yandex"
    assert review.author is None
    assert review.rating == 5
    assert review.text.startswith("Приятное во всех аспектах")
    assert review.url and "supersender.yandex.net" in review.url


# ---------------------------------------------------------------------------
# Yandex digest fixtures
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not YANDEX_DIGEST_5.exists(), reason="yandex_digest_5.eml not found")
def test_yandex_digest_5():
    msg = _load_eml(YANDEX_DIGEST_5)
    parser = YandexParser()

    assert parser.is_review(msg) is True

    reviews = parser.parse(msg)
    assert len(reviews) == 5
    assert [r.rating for r in reviews] == [5, 5, 5, 3, 5]
    assert reviews[3].text.startswith("По еде очень плохо")


@pytest.mark.skipif(not YANDEX_DIGEST_3.exists(), reason="yandex_digest_3.eml not found")
def test_yandex_digest_3():
    msg = _load_eml(YANDEX_DIGEST_3)
    parser = YandexParser()

    assert parser.is_review(msg) is True

    reviews = parser.parse(msg)
    assert len(reviews) == 3


# ---------------------------------------------------------------------------
# dedup_key regression
# ---------------------------------------------------------------------------

def test_dedup_key_none_safe():
    """dedup_key must not raise when author and text are None (Yandex case)."""
    from bot.models import Review
    r = Review(source="yandex", author=None, date="", text=None)
    key = r.dedup_key
    assert isinstance(key, str) and len(key) > 0
