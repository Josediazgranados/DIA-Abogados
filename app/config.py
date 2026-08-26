"""
Configuración centralizada vía variables de entorno.

Nota de diseño: `DATABASE_URL` por defecto apunta a un archivo SQLite local
para poder correr el proyecto sin instalar PostgreSQL. En producción basta
con exportar `DATABASE_URL=postgresql://usuario:clave@host/db` — el resto
del código (SQLAlchemy) no cambia. Ver README.md, sección
"De prototipo a producción".
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent

# Carga automática de un archivo .env en la raíz del proyecto (si existe) —
# así, para pruebas locales, basta con copiar .env.example a .env y poner
# ahí las credenciales, sin tener que exportar variables de entorno a mano
# en cada sesión de terminal. En Render (y otros hostings) esto no hace
# nada: las variables ya vienen inyectadas por la plataforma, y load_dotenv
# no sobreescribe las que ya existan en el entorno.
load_dotenv(BASE_DIR.parent / ".env")
STORAGE_DIR = BASE_DIR / "storage"

DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{(STORAGE_DIR / 'casos.db').as_posix()}")

NOTIFY_MOCK = os.environ.get("NOTIFY_MOCK", "true").lower() == "true"

# Envío del derecho de petición desde el correo del abogado (ver
# app/services/notify.py). Modo simulado por defecto, igual que NOTIFY_MOCK.
SMTP_ABOGADO_MOCK = os.environ.get("SMTP_ABOGADO_MOCK", "true").lower() == "true"

# Revisión manual de las primeras N derechos de petición de la campaña antes
# de abrir el envío automático para el resto (0 = desactivada). Ver
# app/services/peticion.py.
REVISION_MANUAL_PRIMERAS_N = int(os.environ.get("REVISION_MANUAL_PRIMERAS_N", "0"))

# --- Credenciales para envío REAL (solo se usan si NOTIFY_MOCK/SMTP_ABOGADO_MOCK
# están en "false"; si faltan, notify.py lanza un error claro en vez de fallar
# silenciosamente). Ver README.md, sección "Probar envíos reales". ---

# WhatsApp — Meta Cloud API (WhatsApp Business Platform)
META_WHATSAPP_TOKEN = os.environ.get("META_WHATSAPP_TOKEN", "")
META_PHONE_NUMBER_ID = os.environ.get("META_PHONE_NUMBER_ID", "")

# Correo — Gmail con contraseña de aplicación (smtp.gmail.com)
GMAIL_USER = os.environ.get("GMAIL_USER", "")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")

# Datos fijos de la campaña / caso (en producción vendrían de configuración
# por caso, ya que una misma plataforma puede correr varias acciones de
# grupo en paralelo).
CONFIG_CASO = {
    "descripcion_caso": os.environ.get(
        "DESCRIPCION_CASO",
        "Acción de grupo por los comparendos impuestos mediante fotodetección "
        "(fotocomparendos) declarados nulos por decisión del Ministerio de Transporte, "
        "y la consecuente devolución de lo pagado y demás perjuicios derivados",
    ),
    "apoderado_nombre": os.environ.get("APODERADO_NOMBRE", "Nombre del abogado apoderado"),
    "apoderado_tarjeta_profesional": os.environ.get("APODERADO_TP", "T.P. No. 000000"),
    "apoderado_email_rna": os.environ.get("APODERADO_EMAIL_RNA", "apoderado@firma.com"),
    "apoderado_documento": os.environ.get("APODERADO_DOCUMENTO", "0000000"),
    "clausula_honorarios": os.environ.get(
        "CLAUSULA_HONORARIOS",
        "Los honorarios del CONTRATISTA corresponden al treinta por ciento (30%) neto de las "
        "sumas que se lleguen a recuperar u obtener en favor de EL CLIENTE, sin costo inicial "
        "para EL CLIENTE. La totalidad de los dineros que se reconozcan, devuelvan o paguen con "
        "ocasión del presente proceso serán recibidos única y exclusivamente por EL CONTRATISTA, "
        "quien se obliga a distribuirlos dentro de los diez (10) días hábiles siguientes a su "
        "recepción efectiva, entregando a EL CLIENTE el setenta por ciento (70%) neto de lo "
        "recuperado y reteniendo para sí el treinta por ciento (30%) neto restante a título de "
        "honorarios. EL CONTRATISTA se obliga a notificar a EL CLIENTE, por los canales de "
        "contacto aquí registrados, tanto la recepción de dichos dineros como el comprobante de "
        "la transferencia correspondiente a EL CLIENTE.",
    ),
    "ciudad": os.environ.get("CIUDAD_CASO", "Bogotá D.C."),
}
