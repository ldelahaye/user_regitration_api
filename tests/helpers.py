"""Shared test helpers."""

import base64


def basic_auth_header(username: str, password: str) -> dict[str, str]:
    credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
    return {"Authorization": f"Basic {credentials}"}
