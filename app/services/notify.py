"""
Servicio de notificaciones y OTP (código de un solo uso) por WhatsApp y correo.

Estrategia de canal: se intenta primero WhatsApp (mayor tasa de apertura en
Colombia y confirma un número activo de la persona) y si no está disponible
o falla, se usa correo electrónico como respaldo. El participante también
puede elegir explícitamente su canal preferido.

Integraciones reales pendientes (requieren credenciales que aún no existen):
  - WhatsApp: Twilio WhatsApp Business API, o Meta Cloud API directamente.
  - Email: SendGrid, Amazon SES o SMTP corporativo.

Mientras tanto, este módulo imprime el mensaje en consola en vez de
enviarlo (modo MOCK, activado por defecto vía `NOTIFY_MOCK`).
"""
from __future__ import annotations

import hashlib
import random
import string
from datetime import datetime, timedelta

from app.config import NOTIFY_MOCK as MOCK_MODE
from app.config import SMTP_ABOGADO_MOCK


def generar_codigo_otp(longitud: int = 6) -> str:
    return "".join(random.choices(string.digits, k=longitud))


def hash_codigo(codigo: str, participante_id: str) -> str:
    # El código nunca se persiste en texto plano; se guarda su hash salado
    # con el id del participante para poder verificarlo después.
    return hashlib.sha256(f"{participante_id}:{codigo}".encode()).hexdigest()


def expiracion_otp(minutos: int = 10) -> datetime:
    return datetime.utcnow() + timedelta(minutes=minutos)


def enviar_whatsapp_otp(numero_e164: str, codigo: str, nombre: str) -> bool:
    mensaje = (
        f"Hola {nombre}, tu código para confirmar tu firma es: {codigo}. "
        f"Vence en 10 minutos. Si no solicitaste esto, ignora este mensaje."
    )
    if MOCK_MODE:
        print(f"[MOCK][WhatsApp -> {numero_e164}] {mensaje}")
        return True
    # --- Integración real (ejemplo con Twilio) ---
    # from twilio.rest import Client
    # client = Client(os.environ["TWILIO_SID"], os.environ["TWILIO_AUTH_TOKEN"])
    # client.messages.create(
    #     from_=f"whatsapp:{os.environ['TWILIO_WHATSAPP_FROM']}",
    #     to=f"whatsapp:{numero_e164}",
    #     body=mensaje,
    # )
    raise NotImplementedError("Configurar proveedor real de WhatsApp Business API")


def enviar_email_otp(email: str, codigo: str, nombre: str) -> bool:
    asunto = "Código para confirmar tu firma"
    mensaje = (
        f"Hola {nombre},\n\nTu código para confirmar tu firma es: {codigo}\n"
        f"Vence en 10 minutos.\n\nSi no solicitaste esto, ignora este correo."
    )
    if MOCK_MODE:
        print(f"[MOCK][Email -> {email}] Asunto: {asunto}\n{mensaje}")
        return True
    # --- Integración real (ejemplo con SendGrid) ---
    # import sendgrid
    # from sendgrid.helpers.mail import Mail
    # sg = sendgrid.SendGridAPIClient(os.environ["SENDGRID_API_KEY"])
    # mail = Mail(from_email=os.environ["EMAIL_FROM"], to_emails=email,
    #              subject=asunto, plain_text_content=mensaje)
    # sg.send(mail)
    raise NotImplementedError("Configurar proveedor real de correo (SendGrid/SES/SMTP)")


def enviar_copia_firmada(destino_email: str | None, destino_whatsapp: str | None, pdf_path: str) -> None:
    """Envía al participante copia de los documentos ya firmados, con su constancia."""
    if MOCK_MODE:
        print(f"[MOCK] Enviando copia firmada '{pdf_path}' a email={destino_email} whatsapp={destino_whatsapp}")
        return
    raise NotImplementedError("Configurar envío real de copia firmada")


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
# depender de la bandeja de un solo buzón personal.


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

    # --- Integración real ---
    # Opción A (SMTP directo del dominio del abogado, para volumen bajo/medio):
    #   import smtplib
    #   from email.message import EmailMessage
    #   msg = EmailMessage()
    #   msg["From"] = remitente_abogado
    #   msg["To"] = destino_email
    #   msg["Subject"] = asunto
    #   msg.set_content(cuerpo_texto)
    #   with open(pdf_path, "rb") as f:
    #       msg.add_attachment(f.read(), maintype="application", subtype="pdf",
    #                          filename=os.path.basename(pdf_path))
    #   with smtplib.SMTP_SSL(os.environ["SMTP_ABOGADO_HOST"], int(os.environ["SMTP_ABOGADO_PORT"])) as s:
    #       s.login(os.environ["SMTP_ABOGADO_USER"], os.environ["SMTP_ABOGADO_PASS"])
    #       s.send_message(msg)
    #
    # Opción B (relay transaccional autenticado con el dominio del abogado,
    # recomendado para volumen alto — ver advertencia arriba): Amazon SES /
    # SendGrid / Postmark configurado con verificación de dominio (SPF+DKIM)
    # del propio dominio de correo del abogado, remitente = remitente_abogado.
    raise NotImplementedError("Configurar el servidor/relay de correo del abogado apoderado")
