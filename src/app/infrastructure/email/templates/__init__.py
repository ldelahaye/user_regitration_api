"""Email template loading — reads .txt files at startup and caches them."""

import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

_TEMPLATES_DIR = Path(__file__).parent


@dataclass(frozen=True)
class EmailTemplate:
    subject: str
    body: str


_cache: dict[str, EmailTemplate] = {}


def load_templates() -> None:
    """Load all activation_*.txt templates into memory."""
    _cache.clear()
    for path in _TEMPLATES_DIR.glob("activation_*.txt"):
        lang = path.stem.removeprefix("activation_")
        raw = path.read_text(encoding="utf-8")
        header, body = raw.split("---", maxsplit=1)
        subject = header.strip().removeprefix("subject:").strip()
        _cache[lang] = EmailTemplate(subject=subject, body=body.strip())
        logger.info("Loaded email template: %s (%s)", path.name, lang)


def render(code: str, validity_minutes: int, lang: str) -> tuple[str, str]:
    """Return (subject, body) for the given language."""
    template = _cache.get(lang)
    if template is None:
        msg = f"No email template found for lang '{lang}'"
        raise RuntimeError(msg)
    body = template.body.format(code=code, validity_minutes=validity_minutes)
    return template.subject, body
