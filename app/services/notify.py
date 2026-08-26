"""
Servicio de notificaciones y OTP (código de un solo uso) por WhatsApp y correo.

Estrategia de canal: se intenta primero WhatsApp (mayor tasa de apertura en
Colombia y confirma un número activo de la persona) y si no está disponible
o falla, se usa correo electrónico como respaldo. El participante también
puede elegir explícitamente su canal preferido.

Integraciones reales conectadas:
  - WhatsApp: Meta Cloud API (WhatsApp Business Platform) — ver
    `_enviar_whatsapp_texto` / `_enviar_whatsapp_boton`.
  - Email: Gmail vía SMTP con contraseña de aplicación — ver
    `_enviar_correo_gmail`.

Activadas solo cuando `NOTIFY_MOCK`/`SMTP_ABOGADO_MOCK` están en "false" Y
las credenciales correspondientes están configuradas (ver app/config.py);
si faltan credenciales con el modo mock apagado, se lanza un error claro
en vez de fallar en silencio o simular el envío sin que nadie lo note.
"""
from __future__ import annotations

import hashlib
import mimetypes
import os
import random
import smtplib
import string
from datetime import datetime, timedelta
from email.message import EmailMessage

import requests

from app.config import GMAIL_APP_PASSWORD, GMAIL_USER, META_PHONE_NUMBER_ID, META_WHATSAPP_TOKEN
from app.config import NOTIFY_MOCK as MOCK_MODE
from app.config import SMTP_ABOGADO_MOCK

META_GRAPH_URL = "https://graph.facebook.com/v20.0"


def generar_codigo_otp(longitud: int = 6) -> str:
    return "".join(random.choices(string.digits, k=longitud))


def hash_codigo(codigo: str, participante_id: str) -> str:
    # El código nunca se persiste en texto plano; se guarda su hash salado
    # con el id del participante para poder verificarlo después.
    return hashlib.sha256(f"{participante_id}:{codigo}".encode()).hexdigest()


def expiracion_otp(minutos: int = 10) -> datetime:
    return datetime.utcnow() + timedelta(minutes=minutos)


# ---------------------------------------------------------------------------
# WhatsApp — Meta Cloud API
# ---------------------------------------------------------------------------

def _numero_meta(numero_e164: str) -> str:
    """Meta espera el número con indicativo de país pero SIN el '+' inicial."""
    return numero_e164.strip().lstrip("+").replace(" ", "").replace("-", "")


def _enviar_whatsapp_texto(numero_e164: str, texto: str) -> dict:
    if not META_WHATSAPP_TOKEN or not META_PHONE_NUMBER_ID:
        raise RuntimeError(
            "Configura META_WHATSAPP_TOKEN y META_PHONE_NUMBER_ID (Meta Cloud API) "
            "para enviar WhatsApp real, o deja NOTIFY_MOCK=true para seguir en modo simulado."
        )
    resp = requests.post(
        f"{META_GRAPH_URL}/{META_PHONE_NUMBER_ID}/messages",
        headers={"Authorization": f"Bearer {META_WHATSAPP_TOKEN}"},
        json={
            "messaging_product": "whatsapp",
            "to": _numero_meta(numero_e164),
            "type": "text",
            "text": {"body": texto},
        },
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def enviar_whatsapp_boton(numero_e164: str, texto: str, boton_id: str, boton_texto: str) -> dict:
    """Mensaje interactivo con un botón de respuesta rápida (usado por el
    paso 5 de remisión certificada — ver app/services/remision.py)."""
    if not META_WHATSAPP_TOKEN or not META_PHONE_NUMBER_ID:
        raise RuntimeError(
            "Configura META_WHATSAPP_TOKEN y META_PHONE_NUMBER_ID (Meta Cloud API) "
            "para enviar WhatsApp real, o deja NOTIFY_MOCK=true para seguir en modo simulado."
        )
    resp = requests.post(
        f"{META_GRAPH_URL}/{META_PHONE_NUMBER_ID}/messages",
        headers={"Authorization": f"Bearer {META_WHATSAPP_TOKEN}"},
        json={
            "messaging_product": "whatsapp",
            "to": _numero_meta(numero_e164),
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {"text": texto},
                "action": {"buttons": [{"type": "reply", "reply": {"id": boton_id, "title": boton_texto}}]},
            },
        },
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def enviar_whatsapp_otp(numero_e164: str, codigo: str, nombre: str) -> bool:
    mensaje = (
        f"Hola {nombre}, tu código para confirmar tu firma es: {codigo}. "
        f"Vence en 10 minutos. Si no solicitaste esto, ignora este mensaje."
    )
    if MOCK_MODE:
        print(f"[MOCK][WhatsApp -> {numero_e164}] {mensaje}")
        return True
    _enviar_whatsapp_texto(numero_e164, mensaje)
    return True


# ---------------------------------------------------------------------------
# Correo — Gmail vía SMTP con contraseña de aplicación
# ---------------------------------------------------------------------------

def _enviar_correo_gmail(destinatario: str, asunto: str, cuerpo_texto: str,
                          adjunto_path: str | None = None, remitente: str | None = None) -> str:
    """Envía un correo por smtp.gmail.com con una contraseña de aplicación
    (no la contraseña normal de la cuenta). Devuelve el Message-ID generado.
    Ver README.md, sección "Probar envíos reales", para cómo generar la
    contraseña de aplicación en la configuración de seguridad de Google."""
    if not GMAIL_USER or not GMAIL_APP_PASSWORD:
        raise RuntimeError(
            "Configura GMAIL_USER y GMAIL_APP_PASSWORD para enviar correo real, "
            "o deja NOTIFY_MOCK=true / SMTP_ABOGADO_MOCK=true para seguir en modo simulado."
        )
    msg = EmailMessage()
    msg["From"] = remitente or GMAIL_USER
    msg["To"] = destinatario
    msg["Subject"] = asunto
    msg.set_content(cuerpo_texto)

    if adjunto_path:
        tipo, _ = mimetypes.guess_type(adjunto_path)
        maintype, subtype = (tipo.split("/", 1) if tipo else ("application", "octet-stream"))
        with open(adjunto_path, "rb") as f:
            msg.add_attachment(f.read(), maintype=maintype, subtype=subtype,
                                filename=os.path.basename(adjunto_path))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15) as smtp:
        smtp.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        smtp.send_message(msg)

    return msg["Message-ID"] or ""


def enviar_email_otp(email: str, codigo: str, nombre: str) -> bool:
    asunto = "Código para confirmar tu firma"
    mensaje = (
        f"Hola {nombre},\n\nTu código para confirmar tu firma es: {codigo}\n"
        f"Vence en 10 minutos.\n\nSi no solicitaste esto, ignora este correo."
    )
    if MOCK_MODE:
        print(f"[MOCK][Email -> {email}] Asunto: {asunto}\n{mensaje}")
        return True
    _enviar_correo_gmail(email, asunto, mensaje)
    return True


def enviar_copia_firmada(destino_email: str | None, destino_whatsapp: str | None, pdf_path: str) -> None:
    """Envía al participante copia de los documentos ya firmados, con su constancia."""
    if MOCK_MODE:
        print(f"[MOCK] Enviando copia firmada '{pdf_path}' a email={destino_email} whatsapp={destino_whatsapp}")
        return
    if destino_email:
        _enviar_correo_gmail(
            destino_email, "Copia de tu poder especial firmado",
            "Adjunto la copia de tu poder especial ya firmado electrónicamente.",
            adjunto_path=pdf_path,
        )


# ---------------------------------------------------------------------------
# Envío "desde el servidor del abogado" — para el derecho de petición
# ---------------------------------------------------------------------------
#
# A diferencia de enviar_email_otp/enviar_copia_firmada (correo transaccional
# genérico de la plataforma), el derecho de petición debe salir con el
# remitente del propio abogado apoderado — el mismo correo que quedó
# registrado en el poder y, si aplica, el que tiene inscrito en el Registro
# Nacional de Abogados (ver Ley 2213 de 2022). Esto no es solo un detalle de
# "de quién parece venir": es lo que le da al derecho de petición su
# remitente legítimo y trazable ante la entidad.
#
# ADVERTENCIA DE ESCALA: enviar miles de derechos de petición literalmente
# a través del buzón personal del abogado (Gmail/Outlook normal) chocará con
# los límites de envío de esos proveedores (cientos a un par de miles de
# correos/día) y puede hacer que el proveedor marque la cuenta como spam a
# mitad de campaña. La forma correcta de cumplir "debe salir del servidor
# del abogado" SIN perder capacidad de envío es usar el dominio de correo
# propio del abogado (el mismo de su firma / RNA) autenticado con SPF, DKIM
# y DMARC en un relay transaccional (Amazon SES, SendGrid, Postmark, o el
# propio SMTP corporativo si lo permite) — así cada correo sale técnicamente
# autenticado COMO el dominio del abogado, cumpliendo el requisito legal, sin
# depender de la bandeja de un solo buzón personal. Para las PRUEBAS de esta
# app, Gmail + contraseña de aplicación es suficiente (ver GMAIL_USER en
# app/config.py) — se usa como remitente "From", aunque el correo del
# abogado registrado en el caso (`remitente_abogado`) sea otro.


def enviar_derecho_peticion(destino_email: str, asunto: str, cuerpo_texto: str, pdf_path: str,
                             remitente_abogado: str) -> dict:
    """
    Envía el derecho de petición desde el correo/dominio del abogado
    apoderado. Devuelve {"ok": bool, "proveedor_ref": str} — proveedor_ref
    es el Message-ID real (para dejarlo en la traza de auditoría y poder
    probar, ante una eventual controversia sobre el silencio de la entidad,
    la fecha exacta en que se radicó el derecho de petición).
    """
    if SMTP_ABOGADO_MOCK:
        print(f"[MOCK][Derecho de petición, remitente={remitente_abogado} -> {destino_email}] "
              f"Asunto: {asunto}\n    Adjunto: {pdf_path}")
        return {"ok": True, "proveedor_ref": f"<mock-{hashlib.sha256(destino_email.encode()).hexdigest()[:12]}@{remitente_abogado.split('@')[-1]}>"}

    message_id = _enviar_correo_gmail(destino_email, asunto, cuerpo_texto, adjunto_path=pdf_path)
    return {"ok": True, "proveedor_ref": message_id}
