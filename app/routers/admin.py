"""
Panel operativo para el equipo jurídico: catálogo de secretarías (con
correo y nivel de confianza, a diferencia del catálogo público de
app/routers/catalogos.py) y el interruptor de pausa de envío automático
de derechos de petición.

NOTA DE SEGURIDAD: en producción estos endpoints deben protegerse con
autenticación de staff (no están pensados para exponerse tal cual al
público); aquí quedan abiertos por ser un prototipo de demostración.
"""
from __future__ import annotations

from fastapi import APIRouter

from app import db
from app.schemas import ActualizarCorreoSecretariaBody
from app.utils import error

router = APIRouter(prefix="/api/admin", tags=["admin"])

ESTADOS_DERECHO_PETICION = ["pendiente", "enviado", "fallido", "bloqueado_verificacion", "en_revision_manual"]


@router.get("/secretarias-transito")
def admin_listar_secretarias():
    return db.listar_secretarias_transito()


@router.put("/secretarias-transito/{secretaria_id}/correo")
def admin_actualizar_correo_secretaria(secretaria_id: int, body: ActualizarCorreoSecretariaBody):
    correo = (body.correo_notificacion or "").strip()
    if not correo:
        return error("correo_notificacion es obligatorio", 400)
    db.actualizar_correo_secretaria(secretaria_id, correo, requiere_verificacion_manual=False)
    return {"ok": True, "secretaria": db.obtener_secretaria_transito(secretaria_id)}


@router.post("/envio-peticiones/pausar")
def admin_pausar_envio_peticiones():
    db.set_config("envio_peticiones_pausado", "true")
    return {"ok": True, "envio_peticiones_pausado": True}


@router.post("/envio-peticiones/reanudar")
def admin_reanudar_envio_peticiones():
    db.set_config("envio_peticiones_pausado", "false")
    return {"ok": True, "envio_peticiones_pausado": False}


@router.get("/envio-peticiones/resumen")
def admin_resumen_envio_peticiones():
    return {
        "pausado": db.get_config("envio_peticiones_pausado", "false") == "true",
        "total": db.contar_derechos_peticion_total(),
        "por_estado": {e: db.contar_derechos_peticion_por_estado(e) for e in ESTADOS_DERECHO_PETICION},
    }
