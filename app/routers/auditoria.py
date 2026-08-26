"""Trazabilidad (para el equipo legal / auditoría)."""
from __future__ import annotations

from fastapi import APIRouter

from app import db
from app.utils import error

router = APIRouter(prefix="/api/participantes", tags=["auditoria"])


@router.get("/{token}/auditoria")
def auditoria(token: str):
    p = db.obtener_participante_por_token(token)
    if not p:
        return error("token inválido", 404)
    return db.eventos_de(p["id"])
