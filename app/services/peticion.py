"""
Generación y envío automático del derecho de petición previo a la demanda,
uno por cada secretaría de tránsito involucrada en los comparendos que la
persona registró (paso 1b).

Disparo: se llama justo después de que el participante firma el poder y el
contrato y pasa la validación de OTP (mismo punto donde ya se dispara la
cascada de remisión certificada, ver app/services/remision.py) — así se
cumple el requisito de que el envío salga "automáticamente a la aceptación
del usuario con su firma de contrato, poder, validación de factores de
autenticación".

Salvaguardas incluidas:

  1. Bloqueo por baja confianza del correo: si la secretaría destinataria
     está marcada `requiere_verificacion_manual` en el catálogo (ver
     app/data/secretarias_transito.py), el envío NO sale solo; el derecho
     de petición se genera pero queda en estado `bloqueado_verificacion`
     para que alguien del equipo jurídico confirme el correo y lo libere.

  2. Circuit breaker manual: `db.get_config("envio_peticiones_pausado")`
     — si está en "true", ningún envío automático sale (para poder pausar
     toda la campaña de un solo interruptor si algo se ve mal).

  3. Revisión manual de las primeras N: configurable con la variable de
     entorno REVISION_MANUAL_PRIMERAS_N (por defecto 0 = desactivada). Si
     está activa, los primeros N derechos de petición de la campaña se
     generan pero NO se envían solos — quedan en `en_revision_manual` para
     que un paralegal los revise antes de que se abra el envío automático
     para el resto. Es una forma barata de detectar un error de plantilla
     o de datos antes de que afecte a miles de envíos.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from app import db
from app.config import REVISION_MANUAL_PRIMERAS_N
from app.services import documents, notify


def _agrupar_comparendos_por_secretaria(comparendos: list[dict]) -> dict[int, list[dict]]:
    grupos = defaultdict(list)
    for c in comparendos:
        if c.get("secretaria_transito_id"):
            grupos[c["secretaria_transito_id"]].append(c)
    return grupos


def generar_y_enviar_derechos_peticion(participante: dict, config_caso: dict) -> list[dict]:
    """
    Punto de entrada. Agrupa los comparendos del participante por secretaría,
    genera un derecho de petición por grupo, y lo envía (o lo deja
    retenido, según las salvaguardas) desde el correo del abogado apoderado.
    Devuelve la lista de registros de derechos_peticion creados.
    """
    comparendos = db.comparendos_de(participante["id"])
    grupos = _agrupar_comparendos_por_secretaria(comparendos)

    if not grupos:
        db.registrar_evento(participante["id"], "derechos_peticion_omitidos",
                             detalle={"motivo": "ningún comparendo tiene secretaría de tránsito asignada"})
        return []

    resultados = []
    for secretaria_id, sus_comparendos in grupos.items():
        resultados.append(
            _procesar_una_secretaria(participante, config_caso, secretaria_id, sus_comparendos)
        )
    return resultados


def _procesar_una_secretaria(participante: dict, config_caso: dict, secretaria_id: int,
                              comparendos_grupo: list[dict]) -> dict:
    secretaria = db.obtener_secretaria_transito(secretaria_id)
    nombre_archivo = f"derecho_peticion_sec{secretaria_id}"

    contexto = {
        **config_caso,
        **participante,
        "fecha": datetime.utcnow().date().isoformat(),
        "comparendos": comparendos_grupo,
        "secretaria_nombre": secretaria["nombre"] if secretaria else f"Secretaría #{secretaria_id} (no catalogada)",
        "secretaria_correo": (secretaria or {}).get("correo_notificacion") or "[correo pendiente de verificación]",
    }

    # 1) Se genera siempre el documento (para que el equipo pueda revisarlo
    #    aunque el envío quede retenido por alguna salvaguarda).
    borrador = documents.generar_derecho_peticion_borrador(participante["id"], nombre_archivo, contexto)

    email_destino = (secretaria or {}).get("correo_notificacion")
    derecho = db.crear_derecho_peticion(
        participante["id"], secretaria_id,
        comparendo_ids=[c["id"] for c in comparendos_grupo],
        email_destino=email_destino,
    )

    # 2) Salvaguarda 1: secretaría marcada como de baja confianza / sin
    #    correo verificado -> se bloquea el envío automático.
    if not secretaria or secretaria.get("requiere_verificacion_manual") or not email_destino:
        db.actualizar_derecho_peticion(derecho["id"], estado_envio="bloqueado_verificacion")
        db.registrar_evento(
            participante["id"], "derecho_peticion_bloqueado_verificacion", canal="email",
            detalle={"secretaria_id": secretaria_id, "secretaria_nombre": contexto["secretaria_nombre"],
                     "motivo": "correo no verificado en el catálogo — requiere confirmación manual"},
        )
        return {**derecho, "estado_envio": "bloqueado_verificacion"}

    # 3) Salvaguarda 2: circuit breaker manual (pausa de toda la campaña).
    if db.get_config("envio_peticiones_pausado", "false") == "true":
        db.actualizar_derecho_peticion(derecho["id"], estado_envio="en_revision_manual")
        db.registrar_evento(participante["id"], "derecho_peticion_pausado_circuit_breaker",
                             detalle={"secretaria_id": secretaria_id})
        return {**derecho, "estado_envio": "en_revision_manual"}

    # 4) Salvaguarda 3: revisión manual de las primeras N de la campaña.
    if REVISION_MANUAL_PRIMERAS_N and db.contar_derechos_peticion_total() <= REVISION_MANUAL_PRIMERAS_N:
        db.actualizar_derecho_peticion(derecho["id"], estado_envio="en_revision_manual")
        db.registrar_evento(participante["id"], "derecho_peticion_en_revision_manual_inicial",
                             detalle={"secretaria_id": secretaria_id,
                                      "motivo": f"dentro de las primeras {REVISION_MANUAL_PRIMERAS_N} de la campaña"})
        return {**derecho, "estado_envio": "en_revision_manual"}

    # 5) Todo despejado: se envía automáticamente desde el correo del abogado.
    return _enviar(participante, config_caso, derecho, contexto, nombre_archivo, email_destino, borrador["ruta_pdf"])


def _enviar(participante: dict, config_caso: dict, derecho: dict, contexto: dict,
            nombre_archivo: str, email_destino: str, ruta_pdf_borrador: str) -> dict:
    asunto = f"Derecho de petición — nulidad comparendo(s) SAST — {participante['nombre_completo']}"
    envio = notify.enviar_derecho_peticion(
        destino_email=email_destino, asunto=asunto,
        cuerpo_texto=f"Se adjunta derecho de petición a nombre de {participante['nombre_completo']}.",
        pdf_path=ruta_pdf_borrador,
        remitente_abogado=config_caso["apoderado_email_rna"],
    )

    if not envio.get("ok"):
        db.actualizar_derecho_peticion(derecho["id"], estado_envio="fallido")
        db.registrar_evento(participante["id"], "derecho_peticion_envio_fallido",
                             detalle={"secretaria_id": derecho["secretaria_transito_id"]})
        return {**derecho, "estado_envio": "fallido"}

    sello = documents.sellar_derecho_peticion_enviado(
        participante["id"], nombre_archivo, contexto,
        fecha_envio_iso=db.now(), proveedor_ref=envio["proveedor_ref"],
    )
    db.actualizar_derecho_peticion(
        derecho["id"], estado_envio="enviado", proveedor_ref=envio["proveedor_ref"],
        pdf_path=sello["ruta_pdf"], hash_sha256=sello["hash_sha256"], enviado_en=db.now(),
    )
    db.registrar_evento(
        participante["id"], "derecho_peticion_enviado", canal="email",
        detalle={"secretaria_id": derecho["secretaria_transito_id"], "destino": email_destino,
                 "proveedor_ref": envio["proveedor_ref"], "hash": sello["hash_sha256"]},
    )
    return {**derecho, "estado_envio": "enviado", "pdf_path": sello["ruta_pdf"], "hash_sha256": sello["hash_sha256"]}
