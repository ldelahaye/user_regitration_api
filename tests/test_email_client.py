"""Unit tests for HttpEmailService — HTTP failure paths and EmailSendError mapping."""

from unittest.mock import patch

import httpx
import pytest

from app.core.exceptions import NotificationError
from app.infrastructure.email.client import HttpEmailService


@pytest.fixture
def email_service() -> HttpEmailService:
    return HttpEmailService(
        api_url="http://mail.test/api/send",
        api_key="test-key",
        from_email="noreply@test.local",
    )


async def test_send_activation_code_success(email_service: HttpEmailService) -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(200))
    email_service._client = httpx.AsyncClient(transport=transport)

    with patch("app.infrastructure.email.client.render", return_value=("Subject", "Body")):
        await email_service.send_activation_code("user@test.com", "1234", 1, "fr")


async def test_send_activation_code_http_error_raises_notification_error(email_service: HttpEmailService) -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(500))
    email_service._client = httpx.AsyncClient(transport=transport)

    with (
        patch("app.infrastructure.email.client.render", return_value=("Subject", "Body")),
        pytest.raises(NotificationError),
    ):
        await email_service.send_activation_code("user@test.com", "1234", 1, "fr")


async def test_send_activation_code_network_error_raises_notification_error(email_service: HttpEmailService) -> None:
    transport = httpx.MockTransport(lambda request: (_ for _ in ()).throw(httpx.ConnectError("refused")))
    email_service._client = httpx.AsyncClient(transport=transport)

    with (
        patch("app.infrastructure.email.client.render", return_value=("Subject", "Body")),
        pytest.raises(NotificationError),
    ):
        await email_service.send_activation_code("user@test.com", "1234", 1, "fr")


async def test_check_connectivity_logs_warning_on_failure(email_service: HttpEmailService) -> None:
    transport = httpx.MockTransport(lambda request: (_ for _ in ()).throw(httpx.ConnectError("refused")))
    email_service._client = httpx.AsyncClient(transport=transport)

    # Should not raise — only log a warning
    await email_service.check_connectivity()


async def test_close_closes_client(email_service: HttpEmailService) -> None:
    await email_service.close()
    assert email_service._client.is_closed
