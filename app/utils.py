from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse


def error(detail: str, status_code: int) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"error": detail})


def respond(content, status_code: int = 200) -> JSONResponse:
    return JSONResponse(status_code=status_code, content=content)


def ip_cliente(request: Request) -> str:
    return request.headers.get("X-Forwarded-For") or (request.client.host if request.client else "desconocida")
