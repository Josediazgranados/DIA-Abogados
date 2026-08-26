"""Catálogo público de las 37 secretarías de tránsito, para el desplegable
del formulario del paso 1b. Solo expone id + nombre (no el correo interno
de notificación, que es un dato operativo del backend)."""
from __future__ import annotations

from fastapi import APIRouter

from app import db

router = APIRouter(prefix="/api/catalogos", tags=["catalogos"])


@router.get("/secretarias-transito")
def catalogo_secretarias_transito():
    return [{"id": s["id"], "nombre": s["nombre"]} for s in db.listar_secretarias_transito()]
