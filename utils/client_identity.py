from __future__ import annotations

import secrets

from fastapi import Request, Response


CLIENT_ID_COOKIE_NAME = "basic_chat_client_id"
CLIENT_ID_COOKIE_MAX_AGE_SECONDS = 60 * 60 * 24 * 365


def resolve_client_id(request: Request) -> tuple[str, bool]:
    existing_client_id = request.cookies.get(CLIENT_ID_COOKIE_NAME)
    if existing_client_id and existing_client_id.strip():
        return existing_client_id, False

    return secrets.token_urlsafe(32), True


def set_client_id_cookie(response: Response, client_id: str) -> None:
    response.set_cookie(
        key=CLIENT_ID_COOKIE_NAME,
        value=client_id,
        max_age=CLIENT_ID_COOKIE_MAX_AGE_SECONDS,
        httponly=True,
        samesite="lax",
        path="/",
    )
