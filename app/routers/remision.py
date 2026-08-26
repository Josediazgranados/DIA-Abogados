"""
Paso 5 — cascada de remisión certificada del documento ya firmado (el
"pantallazo" del juzgado): opción 1 (WhatsApp) -> opción 3 (correo,
respaldo) -> opción 2 (Web Share Android, plan C). Ver
app/services/remision.py para el detalle de cada opción.
"""
from __future__ import annotations

import json

from fastapi import APIRouter, Request

from app import db
from app.config import CONFIG_CASO
from app.schemas import EmailWebhookBody, PlanCConfirmarBody, WhatsappWebhookBody
from app.services import remision
from app.utils import error, ip_cliente, respond

router = APIRouter(tags=["remision"])


def _ultimo_hash_poder(participante_id: str) -> str | None:
    for doc in db.documentos_de(participante_id):
        if doc["tipo"] == "poder_especial" and doc["hash_sha256"]:
            return doc["hash_sha256"]
    return None


# --- Opción 1: webhook real (o simulado) de WhatsApp Business API -----
@router.post("/webhooks/whatsapp/boton")
def webhook_whatsapp_boton(body: WhatsappWebhookBody):
    """
    En producción, Meta/Twilio llaman esta URL cuando la persona toca
    el botón. El payload real trae el número de origen (con el que se
    busca al participante); aquí, mientras no hay esa integración, se
    identifica por `token` explícito en el body para poder simular el
    evento fácilmente (ver demo.py).
    """
    p = db.obtener_participante_por_token(body.token)
    if not p:
        return error("token inválido", 404)

    intentos = [i for i in db.intentos_remision_de(p["id"]) if i["canal"] == "whatsapp_boton" and i["estado"] == "enviado"]
    if not intentos:
        return error("no hay un intento de remisión por WhatsApp pendiente", 400)
    intento = intentos[-1]

    payload_webhook = {
        "boton_texto": body.boton_texto,
        "timestamp": db.now(),
        "estado_entrega": "entregado",
        "estado_lectura": "leído",
    }
    ruta_constancia = remision.confirmar_whatsapp_boton(
        p, intento, payload_webhook, documento_hash=_ultimo_hash_poder(p["id"]),
    )
    db.actualizar_intento_remision(intento["id"], estado="confirmado", constancia_path=ruta_constancia,
                                    detalle_extra=payload_webhook)
    db.registrar_evento(p["id"], "remision_confirmada", canal="whatsapp_boton",
                         detalle={"constancia": ruta_constancia})
    db.actualizar_participante(p["id"], estado="remitido")
    return {"ok": True, "constancia": ruta_constancia}


# --- Opción 3: se dispara cuando la 1 falla/expira sin confirmación ---
@router.post("/api/participantes/{token}/remision/fallback-email")
def remision_fallback_email(token: str):
    p = db.obtener_participante_por_token(token)
    if not p:
        return error("token inválido", 404)

    # Marca como fallido/expirado el intento vigente de la opción 1.
    for i in db.intentos_remision_de(p["id"]):
        if i["canal"] == "whatsapp_boton" and i["estado"] == "enviado":
            db.actualizar_intento_remision(i["id"], estado="fallido")
            db.registrar_evento(p["id"], "remision_opcion1_fallida_o_expirada", canal="whatsapp_boton")

    intento = remision.fallback_email(p, CONFIG_CASO["apoderado_email_rna"])
    return {
        "ok": True, "opcion_activa": "email_confirmacion",
        "remision_id": intento["id"],
        "mailto": _mailto_o_none(intento),
    }


def _mailto_o_none(intento: dict) -> str | None:
    detalle = json.loads(intento["detalle"]) if intento.get("detalle") else {}
    return detalle.get("mailto")


# --- webhook real (o simulado) de correo entrante ----------------------
@router.post("/webhooks/email/inbound")
def webhook_email_inbound(body: EmailWebhookBody):
    p = db.obtener_participante_por_token(body.token)
    if not p:
        return error("token inválido", 404)

    intentos = [i for i in db.intentos_remision_de(p["id"]) if i["canal"] == "email_confirmacion" and i["estado"] == "enviado"]
    if not intentos:
        return error("no hay un intento de remisión por correo pendiente", 400)
    intento = intentos[-1]

    payload_webhook = {
        "from": body.from_ or p["email"],
        "to": CONFIG_CASO["apoderado_email_rna"],
        "subject": body.subject or f"Confirmo y remito mi firma — {p['nombre_completo']}",
        "message_id": body.message_id or f"<{db.new_id()}@mail>",
        "date": db.now(),
        "ip": body.ip or "N/A",
        "body": body.body or "Confirmo que remito firmado el poder especial.",
    }
    ruta_constancia = remision.confirmar_email_recibido(
        p, intento, payload_webhook, documento_hash=_ultimo_hash_poder(p["id"]),
    )
    db.actualizar_intento_remision(intento["id"], estado="confirmado", constancia_path=ruta_constancia,
                                    detalle_extra=payload_webhook)
    db.registrar_evento(p["id"], "remision_confirmada", canal="email_confirmacion",
                         detalle={"constancia": ruta_constancia})
    db.actualizar_participante(p["id"], estado="remitido")
    return {"ok": True, "constancia": ruta_constancia}


# --- Opción 2 (plan C): solo si el dispositivo es Android --------------
@router.post("/api/participantes/{token}/remision/plan-c")
def remision_plan_c(token: str):
    p = db.obtener_participante_por_token(token)
    if not p:
        return error("token inválido", 404)

    for i in db.intentos_remision_de(p["id"]):
        if i["canal"] == "email_confirmacion" and i["estado"] == "enviado":
            db.actualizar_intento_remision(i["id"], estado="fallido")
            db.registrar_evento(p["id"], "remision_opcion3_fallida_o_expirada", canal="email_confirmacion")

    intento = remision.fallback_share_android(p)
    if intento is None:
        # Las 3 opciones automatizadas quedaron agotadas (la 2 ni
        # siquiera estaba disponible): pasa a gestión manual del equipo
        # jurídico como último recurso.
        db.registrar_evento(p["id"], "remision_pendiente_manual", canal=None,
                             detalle={"motivo": "opción 2 no disponible (no es Android) y 1/3 ya fallaron"})
        db.actualizar_participante(p["id"], estado="remision_pendiente_manual")
        return respond({
            "ok": False,
            "error": "plan C no disponible: el dispositivo no es Android",
            "estado_final": "remision_pendiente_manual",
        }, 409)
    return {"ok": True, "opcion_activa": "share_android", "remision_id": intento["id"]}


@router.post("/api/participantes/{token}/remision/plan-c/confirmar")
def remision_plan_c_confirmar(token: str, body: PlanCConfirmarBody, request: Request):
    """El frontend llama a navigator.share({files:[pdf]}) y reporta aquí
    si el selector nativo se completó sin error (`exito`: true/false)."""
    p = db.obtener_participante_por_token(token)
    if not p:
        return error("token inválido", 404)

    intentos = [i for i in db.intentos_remision_de(p["id"]) if i["canal"] == "share_android" and i["estado"] == "enviado"]
    if not intentos:
        return error("no hay un intento de plan C pendiente", 400)
    intento = intentos[-1]

    metadata = {
        "user_agent": request.headers.get("User-Agent"),
        "timestamp": db.now(),
        "ip": ip_cliente(request),
    }
    estado, ruta_constancia = remision.registrar_resultado_share_android(
        p, intento, body.exito, metadata, documento_hash=_ultimo_hash_poder(p["id"]),
    )
    db.actualizar_intento_remision(intento["id"], estado=estado, constancia_path=ruta_constancia)

    if estado == "confirmado":
        db.registrar_evento(p["id"], "remision_confirmada", canal="share_android",
                             detalle={"constancia": ruta_constancia, "nivel_evidencia": "autorreportada"})
        db.actualizar_participante(p["id"], estado="remitido")
        return {"ok": True, "constancia": ruta_constancia, "nivel_evidencia": "autorreportada"}

    # Las tres opciones fallaron: queda para gestión manual del equipo jurídico.
    db.registrar_evento(p["id"], "remision_pendiente_manual", canal="share_android",
                         detalle={"motivo": "las 3 opciones automatizadas fallaron"})
    db.actualizar_participante(p["id"], estado="remision_pendiente_manual")
    return {"ok": False, "estado_final": "remision_pendiente_manual"}


@router.get("/api/participantes/{token}/remision/estado")
def remision_estado(token: str):
    p = db.obtener_participante_por_token(token)
    if not p:
        return error("token inválido", 404)
    return {
        "estado_participante": p["estado"],
        "intentos": db.intentos_remision_de(p["id"]),
        "confirmada": db.remision_confirmada_de(p["id"]),
    }
