from httpx import AsyncClient

from app.core.logging import CORRELATION_ID_HEADER


async def test_response_contains_correlation_id(client: AsyncClient) -> None:
    response = await client.get("/health")

    assert response.status_code == 200
    assert CORRELATION_ID_HEADER in response.headers
    assert len(response.headers[CORRELATION_ID_HEADER]) > 0


async def test_valid_uuid_correlation_id_is_propagated(client: AsyncClient) -> None:
    custom_id = "550e8400-e29b-41d4-a716-446655440000"
    response = await client.get("/health", headers={CORRELATION_ID_HEADER: custom_id})

    assert response.status_code == 200
    assert response.headers[CORRELATION_ID_HEADER] == custom_id


async def test_non_uuid_correlation_id_is_replaced(client: AsyncClient) -> None:
    response = await client.get("/health", headers={CORRELATION_ID_HEADER: "not-a-uuid"})

    assert response.status_code == 200
    # Non-UUID input is discarded and replaced with a fresh UUID
    assert response.headers[CORRELATION_ID_HEADER] != "not-a-uuid"
    assert len(response.headers[CORRELATION_ID_HEADER]) == 36  # UUID length


async def test_unique_correlation_id_per_request(client: AsyncClient) -> None:
    response_1 = await client.get("/health")
    response_2 = await client.get("/health")

    id_1 = response_1.headers[CORRELATION_ID_HEADER]
    id_2 = response_2.headers[CORRELATION_ID_HEADER]
    assert id_1 != id_2
