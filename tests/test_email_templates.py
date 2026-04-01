"""Unit tests for email template loading and rendering."""

import pytest

from app.infrastructure.email.templates import load_templates, render


@pytest.fixture(autouse=True)
def _loaded_templates() -> None:
    load_templates()


def test_load_templates_loads_all_languages() -> None:
    for lang in ("fr", "en", "de", "es", "it"):
        subject, body = render("1234", 5, lang)
        assert subject
        assert body


def test_render_injects_code_and_validity() -> None:
    _subject, body = render("5678", 10, "en")

    assert "5678" in body
    assert "10" in body


def test_render_raises_for_unknown_lang() -> None:
    with pytest.raises(RuntimeError, match="No email template found for lang"):
        render("1234", 5, "zz")
