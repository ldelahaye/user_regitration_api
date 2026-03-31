"""Email service implementations — HTTP API client and console mock.

The SMTP server is treated as a third-party service offering an HTTP API.
When APP_EMAIL_MOCK=true, activation codes are logged to the console instead.
"""

import logging

import httpx

from app.core.config import Settings
from app.core.exceptions import NotificationError
from app.domain.ports import EmailService
from app.infrastructure.email.templates import render

logger = logging.getLogger(__name__)


def create_email_service(settings: Settings) -> EmailService:
    """Build the appropriate email service based on configuration."""
    if settings.email_mock:
        logger.info("Email service: console mock (APP_EMAIL_MOCK=true)")
        return ConsoleEmailService()
    logger.info("Email service: HTTP API (%s)", settings.email_api_url)
    return HttpEmailService(
        api_url=settings.email_api_url,
        api_key=settings.email_api_key.get_secret_value(),
        from_email=settings.email_from,
    )


class HttpEmailService(EmailService):
    """Sends activation codes via a third-party SMTP HTTP API."""

    def __init__(self, api_url: str, api_key: str, from_email: str) -> None:
        self._api_url = api_url
        self._api_key = api_key
        self._from_email = from_email
        self._client = httpx.AsyncClient(timeout=10.0)

    async def check_connectivity(self) -> None:
        try:
            response = await self._client.head(self._api_url)
            logger.info("Email API reachable (%s, status %d)", self._api_url, response.status_code)
        except httpx.HTTPError:
            logger.warning("Email API unreachable (%s)", self._api_url)

    async def send_activation_code(self, email: str, code: str, validity_minutes: int, lang: str) -> None:
        subject, body = render(code, validity_minutes, lang)
        payload = {
            "from": self._from_email,
            "to": email,
            "subject": subject,
            "body": body,
        }
        headers = {"Authorization": f"Bearer {self._api_key}"}
        try:
            response = await self._client.post(self._api_url, json=payload, headers=headers)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            status_code = getattr(getattr(exc, "response", None), "status_code", "network error")
            logger.exception("Failed to send activation code (status=%s)", status_code)
            raise NotificationError from exc
        logger.info("Activation code sent to %s via email API (lang=%s)", email, lang)

    async def close(self) -> None:
        await self._client.aclose()
        logger.info("Email HTTP client closed")


class ConsoleEmailService(EmailService):
    """Logs activation codes to the console — used when APP_EMAIL_MOCK=true."""

    async def check_connectivity(self) -> None:
        logger.info("Console email service: connectivity check skipped (mock)")

    async def send_activation_code(self, email: str, code: str, validity_minutes: int, lang: str) -> None:
        render(code, validity_minutes, lang)  # validate template renders without error
        logger.info("[MOCK] activation code sent → %s (lang=%s, ttl=%d min)", email, lang, validity_minutes)

    async def close(self) -> None:
        logger.info("Console email service closed")
