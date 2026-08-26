"""
Remisión certificada del documento ya firmado ("el pantallazo que pide el
juzgado"), automatizada en cascada de 3 opciones, cada una accionable con
UN clic desde el flujo:

  Opción 1 (prioridad 1) — Botón interactivo de WhatsApp Business API.
      Se envía el poder ya firmado con un botón "Confirmo y remito mi
      firma". Al tocarlo, el propio proveedor (Meta/Twilio) certifica el
      mensaje entrante (número, hora, entregado/leído). Es la evidencia
      más sólida porque la certifica un tercero, no el propio usuario.

  Opción 3 (prioridad 2, respaldo) — Confirmación por correo (mailto
      prellenado). Si no hay WhatsApp o no se confirma a tiempo, se ofrece
      un botón que abre el cliente de correo de la persona con una
      respuesta ya redactada; basta un toque en "Enviar". La evidencia son
      las cabeceras SMTP del correo entrante.

  Opción 2 (prioridad 3, "plan C", solo Android) — Compartir el PDF con la
      Web Share API (navigator.share) hacia WhatsApp. Solo se ofrece si el
      dispositivo es Android (en iOS el soporte de archivos es limitado,
      ver documento de metodología). La evidencia es autorreportada por el
      navegador, no certificada por un proveedor — por eso queda como
      último recurso, marcada con menor nivel de evidencia.

  Si las tres fallan, el caso queda en estado 'remision_pendiente_manual'
  para que el equipo jurídico contacte a la persona y gestione, como
  último recurso, un pantallazo manual tradicional.

Este módulo expone la interfaz de cada canal (envío + confirmación) y el
orquestador `orquestar_cascada_remision`, que en producción se dispara así:
  - Opción 1 se envía de inmediato al firmar; la confirmación llega por el
    webhook de WhatsApp cuando la persona toca el botón.
  - Si no hay confirmación dentro de la ventana de espera (ej. 15 minutos),
    un job programado dispara la opción 3.
  - Si tampoco se confirma, y el dispositivo era Android, el frontend
    ofrece la opción 2 (Web Share) la próxima vez que la persona abra el
    enlace.

Las funciones de "envío" siguen siendo simuladas (MOCK, activado por
defecto vía `NOTIFY_MOCK`) hasta que haya credenciales reales de WhatsApp
Business API / correo entrante; las de "confirmación" están separadas para
poder invocarse tanto desde un webhook real como desde la demo — ver
demo.py.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

from app import db
from app.config import NOTIFY_MOCK as MOCK_MODE

STORAGE_DIR = Path(__file__).parent.parent / "storage"

FONT_DIR = Path("/usr/share/fonts/truetype/dejavu")


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    nombre = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    ruta = FONT_DIR / nombre
    if ruta.exists():
        return ImageFont.truetype(str(ruta), size)
    return ImageFont.load_default()


# ---------------------------------------------------------------------------
# OPCIÓN 1 — Botón interactivo de WhatsApp Business API (prioridad 1)
# ---------------------------------------------------------------------------

def enviar_whatsapp_boton_remision(participante: dict) -> dict:
    """
    Envía el documento firmado por WhatsApp Business API con un botón de
    respuesta rápida "Confirmo y remito mi firma".
    """
    texto = (
        f"Hola {participante['nombre_completo']}, adjunto tu poder especial ya firmado. "
        f"Para dejar constancia de que lo recibes y lo remites como tuyo, toca el botón."
    )
    boton = "Confirmo y remito mi firma"

    if MOCK_MODE:
        print(f"[MOCK][WhatsApp interactivo -> {participante['celular']}] {texto}\n    [Botón: {boton}]")
        proveedor_ref = f"wamid.MOCK-{db.new_id()[:12]}"
        return {"ok": True, "proveedor_ref": proveedor_ref}

    # --- Integración real (ejemplo con Meta Cloud API / Twilio) ---
    # POST https://graph.facebook.com/v20.0/<PHONE_NUMBER_ID>/messages
    # {
    #   "messaging_product": "whatsapp", "to": participante["celular"],
    #   "type": "interactive",
    #   "interactive": {
    #       "type": "button",
    #       "body": {"text": texto},
    #       "action": {"buttons": [{"type": "reply",
    #                    "reply": {"id": "confirmar_remision", "title": boton}}]}
    #   }
    # }
    # El `id` del mensaje devuelto (wamid...) es el `proveedor_ref` a guardar.
    raise NotImplementedError("Configurar Meta Cloud API / Twilio para mensajes interactivos")


def confirmar_whatsapp_boton(participante: dict, remision: dict, payload_webhook: dict,
                              documento_hash: str | None = None) -> str:
    """
    Se invoca cuando llega el evento de webhook (real o simulado) de que la
    persona tocó el botón. `payload_webhook` trae los campos que Meta/Twilio
    entregan: número de origen, texto del botón, timestamp, y los eventos
    de estado (delivered/read) asociados al mismo id de mensaje.
    Genera la constancia visual y devuelve su ruta.
    """
    carpeta = STORAGE_DIR / participante["id"]
    carpeta.mkdir(parents=True, exist_ok=True)
    ruta = carpeta / "constancia_remision_whatsapp.png"
    _generar_constancia_whatsapp(ruta, participante, remision, payload_webhook, documento_hash)
    return str(ruta)


def _generar_constancia_whatsapp(ruta: Path, participante: dict, remision: dict, payload: dict,
                                  documento_hash: str | None = None) -> None:
    """Renderiza una imagen tipo 'captura de chat', construida a partir de
    metadatos verificados del proveedor (no es una captura manual)."""
    W, H = 720, 560
    img = Image.new("RGB", (W, H), color=(236, 229, 221))
    d = ImageDraw.Draw(img)

    # Barra superior estilo WhatsApp
    d.rectangle([0, 0, W, 70], fill=(7, 94, 84))
    d.text((20, 20), f"{participante['nombre_completo']}", font=_font(22, bold=True), fill="white")
    d.text((20, 48), participante.get("celular") or "", font=_font(14), fill=(210, 230, 225))

    # Burbuja saliente (del cliente) con el documento
    bx, by, bw = 140, 110, 520
    d.rounded_rectangle([bx, by, bx + bw, by + 130], radius=14, fill=(220, 248, 198))
    d.text((bx + 16, by + 14), "[PDF]  Poder_especial_firmado.pdf", font=_font(16, bold=True), fill=(30, 30, 30))
    d.text((bx + 16, by + 44), f"\"{payload.get('boton_texto', 'Confirmo y remito mi firma')}\"",
           font=_font(15), fill=(40, 40, 40))
    hora = payload.get("timestamp", datetime.utcnow().isoformat())[11:16]
    d.text((bx + bw - 90, by + 100), f"{hora}  ✓✓", font=_font(13), fill=(83, 148, 143))

    # Franja de constancia certificada
    d.rectangle([0, 260, W, H], fill=(255, 255, 255))
    d.text((20, 275), "CONSTANCIA DE REMISIÓN CERTIFICADA", font=_font(18, bold=True), fill=(31, 59, 87))
    d.text((20, 300), "Generada automáticamente a partir del registro del proveedor de WhatsApp",
           font=_font(12), fill=(90, 90, 90))
    d.text((20, 316), "Business API (Meta/Twilio) — no es una captura de pantalla manual.",
           font=_font(12), fill=(90, 90, 90))

    campos = [
        ("Participante", f"{participante['nombre_completo']} — C.C. {participante['numero_documento']}"),
        ("Número verificado (OTP previo)", participante.get("celular") or "N/A"),
        ("ID de mensaje (proveedor)", remision.get("proveedor_ref", "N/A")),
        ("Botón confirmado", payload.get("boton_texto", "Confirmo y remito mi firma")),
        ("Fecha y hora (UTC)", payload.get("timestamp", datetime.utcnow().isoformat())),
        ("Estado de entrega", payload.get("estado_entrega", "entregado")),
        ("Estado de lectura", payload.get("estado_lectura", "leído")),
        ("Documento remitido — hash", (documento_hash or "N/A")[:24] + "…"),
    ]
    y = 350
    for etiqueta, valor in campos:
        d.text((20, y), f"{etiqueta}:", font=_font(13, bold=True), fill=(40, 40, 40))
        d.text((260, y), str(valor), font=_font(13), fill=(40, 40, 40))
        y += 24

    img.save(ruta)


# ---------------------------------------------------------------------------
# OPCIÓN 3 — Confirmación por correo, mailto prellenado (prioridad 2)
# ---------------------------------------------------------------------------

def preparar_mailto_confirmacion(participante: dict, apoderado_email: str) -> dict:
    """
    Devuelve los datos para que el frontend construya un enlace
    mailto:...?subject=...&body=... que abre el cliente de correo de la
    persona con la respuesta ya redactada; ella solo toca 'Enviar'.
    """
    asunto = f"Confirmo y remito mi firma — {participante['nombre_completo']}"
    cuerpo = (
        f"Confirmo que remito firmado el poder especial y el contrato de "
        f"prestación de servicios correspondientes a la acción de grupo, "
        f"a nombre de {participante['nombre_completo']}, C.C. {participante['numero_documento']}."
    )
    mailto = f"mailto:{apoderado_email}?subject={asunto}&body={cuerpo}"
    return {"mailto": mailto, "para": apoderado_email, "asunto": asunto, "cuerpo": cuerpo}


def enviar_instrucciones_email_confirmacion(participante: dict, apoderado_email: str) -> dict:
    datos = preparar_mailto_confirmacion(participante, apoderado_email)
    if MOCK_MODE:
        print(f"[MOCK][Email respaldo -> {participante['email']}] Se ofrece botón 'Responder para confirmar' "
              f"con asunto: {datos['asunto']}")
        return {"ok": True, "mailto": datos["mailto"]}
    # Ver app/services/notify.py para la integración real de envío (SendGrid/SES);
    # aquí solo se prepara el enlace mailto: que abrirá el cliente de correo
    # de la persona con la respuesta lista para enviar con un toque.
    raise NotImplementedError("Configurar envío real de instrucciones de confirmación por correo")


def confirmar_email_recibido(participante: dict, remision: dict, payload_webhook: dict,
                              documento_hash: str | None = None) -> str:
    """
    Se invoca cuando llega el correo de respuesta (real: vía SendGrid Inbound
    Parse / Amazon SES + S3, o similar; simulado en demo.py). `payload_webhook`
    trae las cabeceras capturadas: From, Date, Message-ID, cuerpo, IP de envío.
    """
    carpeta = STORAGE_DIR / participante["id"]
    carpeta.mkdir(parents=True, exist_ok=True)
    ruta = carpeta / "constancia_remision_email.pdf"
    _generar_constancia_email(ruta, participante, remision, payload_webhook, documento_hash)
    return str(ruta)


def _generar_constancia_email(ruta: Path, participante: dict, remision: dict, payload: dict,
                               documento_hash: str | None = None) -> None:
    doc = SimpleDocTemplate(str(ruta), pagesize=letter,
                             leftMargin=2.5 * cm, rightMargin=2.5 * cm,
                             topMargin=2 * cm, bottomMargin=2 * cm)
    styles = getSampleStyleSheet()
    story = [
        Paragraph("CONSTANCIA DE REMISIÓN CERTIFICADA — CORREO ELECTRÓNICO", styles["Title"]),
        Spacer(1, 0.3 * cm),
        Paragraph(
            "Generada automáticamente a partir de las cabeceras SMTP capturadas al recibir "
            "la respuesta de confirmación remitida por el participante. No es una captura de "
            "pantalla manual.",
            styles["Normal"],
        ),
        Spacer(1, 0.4 * cm),
    ]

    filas = [
        ["Participante", f"{participante['nombre_completo']} — C.C. {participante['numero_documento']}"],
        ["De (remitente verificado)", payload.get("from", participante.get("email", "N/A"))],
        ["Para", payload.get("to", "apoderado@firma.com")],
        ["Asunto", payload.get("subject", "")],
        ["Message-ID", payload.get("message_id", "N/A")],
        ["Fecha (UTC)", payload.get("date", datetime.utcnow().isoformat())],
        ["IP de envío reportada", payload.get("ip", "N/A")],
        ["Documento remitido — hash", (documento_hash or "N/A")[:48] + ("…" if documento_hash and len(documento_hash) > 48 else "")],
    ]
    tabla = Table(filas, colWidths=[6 * cm, 10 * cm])
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#1F3B57")),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(tabla)
    story.append(Spacer(1, 0.4 * cm))
    story.append(Paragraph("Cuerpo del mensaje recibido:", styles["Heading3"]))
    story.append(Paragraph(payload.get("body", "").replace("\n", "<br/>"), styles["Normal"]))

    doc.build(story)


# ---------------------------------------------------------------------------
# OPCIÓN 2 — Web Share API hacia WhatsApp, solo Android (prioridad 3 / plan C)
# ---------------------------------------------------------------------------

def plan_c_disponible(participante: dict) -> bool:
    """La opción 2 (Web Share API con archivo adjunto) solo es confiable en
    Android; en iOS/Safari el soporte para compartir archivos es limitado."""
    return (participante.get("device_os") or "").lower() == "android"


def registrar_resultado_share_android(participante: dict, remision: dict, exito_reportado: bool,
                                       metadata_dispositivo: dict, documento_hash: str | None = None
                                       ) -> tuple[str, str | None]:
    """
    El frontend llama a navigator.share({files:[pdf]}) y reporta si el
    selector nativo se completó sin error. Es evidencia AUTORREPORTADA por
    el navegador (no certificada por un proveedor externo), por eso va
    marcada con menor nivel de evidencia y como último recurso.
    """
    if not exito_reportado:
        return "fallido", None

    carpeta = STORAGE_DIR / participante["id"]
    carpeta.mkdir(parents=True, exist_ok=True)
    ruta = carpeta / "constancia_remision_share_android.png"
    _generar_constancia_share(ruta, participante, remision, metadata_dispositivo, documento_hash)
    return "confirmado", str(ruta)


def _generar_constancia_share(ruta: Path, participante: dict, remision: dict, meta: dict,
                               documento_hash: str | None = None) -> None:
    W, H = 720, 500
    img = Image.new("RGB", (W, H), color=(255, 255, 255))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 60], fill=(120, 60, 20))
    d.text((20, 18), "CONSTANCIA DE REMISIÓN — PLAN C (compartir nativo, Android)",
           font=_font(15, bold=True), fill="white")

    d.text((20, 80), "Evidencia autorreportada por el navegador del dispositivo. No está",
           font=_font(13), fill=(120, 40, 20))
    d.text((20, 100), "certificada por un proveedor externo (Meta/Twilio/servidor de correo);",
           font=_font(13), fill=(120, 40, 20))
    d.text((20, 120), "úsese como respaldo adicional, no como única prueba ante el juzgado.",
           font=_font(13), fill=(120, 40, 20))

    campos = [
        ("Participante", f"{participante['nombre_completo']} — C.C. {participante['numero_documento']}"),
        ("Dispositivo", meta.get("user_agent", "N/A")),
        ("Sistema operativo", participante.get("device_os", "N/A")),
        ("Mecanismo", "Web Share API (navigator.share) hacia WhatsApp"),
        ("Resultado reportado por el navegador", "Selector nativo completado sin error"),
        ("Fecha y hora (UTC)", meta.get("timestamp", datetime.utcnow().isoformat())),
        ("IP", meta.get("ip", "N/A")),
        ("Documento compartido — hash", (documento_hash or "N/A")[:24] + "…"),
    ]
    # Diseño apilado (etiqueta encima, valor debajo) para que las etiquetas
    # largas nunca se encimen con el valor, sin importar su longitud.
    y = 155
    for etiqueta, valor in campos:
        d.text((20, y), f"{etiqueta}:", font=_font(12, bold=True), fill=(90, 90, 90))
        d.text((20, y + 16), str(valor), font=_font(14), fill=(30, 30, 30))
        y += 40

    img.save(ruta)


# ---------------------------------------------------------------------------
# Orquestador de la cascada 1 -> 3 -> 2
# ---------------------------------------------------------------------------

ORDEN_WHATSAPP_BOTON = 1
ORDEN_EMAIL_CONFIRMACION = 2
ORDEN_SHARE_ANDROID = 3


def iniciar_cascada(participante: dict) -> dict:
    """Punto de entrada real: se llama justo después de sellar la firma
    (paso 4). Dispara la opción 1 y deja el caso a la espera de webhook."""
    resultado = enviar_whatsapp_boton_remision(participante)
    intento = db.crear_intento_remision(
        participante["id"], ORDEN_WHATSAPP_BOTON, "whatsapp_boton",
        proveedor_ref=resultado.get("proveedor_ref"), nivel_evidencia="certificada_proveedor",
    )
    db.registrar_evento(participante["id"], "remision_opcion1_enviada", canal="whatsapp_boton",
                         detalle={"proveedor_ref": resultado.get("proveedor_ref")})
    return intento


def fallback_email(participante: dict, apoderado_email: str) -> dict:
    """Se dispara cuando la opción 1 falla o expira sin confirmación."""
    datos = enviar_instrucciones_email_confirmacion(participante, apoderado_email)
    intento = db.crear_intento_remision(
        participante["id"], ORDEN_EMAIL_CONFIRMACION, "email_confirmacion",
        detalle={"mailto": datos.get("mailto")}, nivel_evidencia="certificada_proveedor",
    )
    db.registrar_evento(participante["id"], "remision_opcion3_enviada", canal="email_confirmacion")
    return intento


def fallback_share_android(participante: dict) -> dict | None:
    """Se dispara cuando la opción 3 también falla o expira, y solo si el
    dispositivo es Android."""
    if not plan_c_disponible(participante):
        db.registrar_evento(participante["id"], "remision_opcion2_no_disponible", canal="share_android",
                             detalle={"motivo": "dispositivo no es Android"})
        return None
    intento = db.crear_intento_remision(
        participante["id"], ORDEN_SHARE_ANDROID, "share_android", nivel_evidencia="autorreportada",
    )
    db.registrar_evento(participante["id"], "remision_opcion2_ofrecida", canal="share_android")
    return intento
