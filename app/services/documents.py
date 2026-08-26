"""
Generación de documentos (poder especial y contrato de prestación de
servicios) a partir de plantillas, y su materialización en PDF.

Diseño de integridad documental:
  1. Se renderiza el documento "para revisión" con los datos del
     participante (sin constancia de firma) -> esto es lo que la persona
     lee antes de aceptar.
  2. Al aceptar y verificar el OTP, se calcula un hash SHA-256 del texto
     exacto que la persona aceptó + metadatos del evento de firma
     (timestamp, canal, id de evento de auditoría) y se regenera el PDF
     agregando la "Constancia de firma electrónica" con ese hash.
  3. El hash queda registrado en la base de datos (tabla
     documentos_firmados) y en el evento de auditoría correspondiente,
     de modo que cualquier alteración posterior del documento es
     detectable (cumple el criterio de integridad del art. 7, Ley 527/1999).
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from xml.sax.saxutils import escape as _xml_escape

from jinja2 import Environment, FileSystemLoader, select_autoescape
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
STORAGE_DIR = Path(__file__).parent.parent / "storage"

_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(disabled_extensions=("txt",)),
    trim_blocks=True,
    lstrip_blocks=True,
)

PLANTILLAS = {
    "poder_especial": "poder_especial.txt",
    "contrato_prestacion_servicios": "contrato_prestacion_servicios.txt",
    "derecho_peticion": "derecho_peticion.txt",
}


def renderizar_texto(tipo: str, contexto: dict) -> str:
    plantilla = _env.get_template(PLANTILLAS[tipo])
    return plantilla.render(**contexto)


def calcular_hash(texto: str) -> str:
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def texto_a_pdf(texto: str, ruta_salida: Path) -> Path:
    """
    NOTA — bug real encontrado y corregido: reportlab's Paragraph interpreta
    el texto como un subconjunto de XML/HTML (por eso podemos insertar
    '<br/>' para los saltos de línea). Si el contenido dinámico de un
    documento contiene '<', '>' o '&' -por ejemplo un Message-ID de correo
    con formato '<abc123@dominio.com>', que es el formato estándar
    (RFC 5322)- reportlab lo interpreta como una etiqueta XML inválida y el
    texto desaparece SILENCIOSAMENTE del PDF (sin lanzar error), lo que
    produciría derechos de petición con la constancia de envío incompleta
    sin que nadie lo notara. Por eso aquí se escapa el texto ANTES de
    insertar las etiquetas '<br/>' reales.
    """
    ruta_salida.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(ruta_salida), pagesize=letter,
        leftMargin=2.5 * cm, rightMargin=2.5 * cm,
        topMargin=2 * cm, bottomMargin=2 * cm,
    )
    styles = getSampleStyleSheet()
    story = []
    for parrafo in texto.split("\n\n"):
        limpio = _xml_escape(parrafo).replace("\n", "<br/>")
        story.append(Paragraph(limpio, styles["Normal"]))
        story.append(Spacer(1, 0.4 * cm))
    doc.build(story)
    return ruta_salida


def generar_documento_para_revision(tipo: str, participante_id: str, contexto: dict) -> dict:
    """Genera el PDF que la persona revisa ANTES de firmar (sin constancia)."""
    contexto_revision = {
        **contexto,
        "hash_documento": "PENDIENTE — se calculará al momento de la firma",
        "fecha_firma": "PENDIENTE",
        "canal_verificacion": "PENDIENTE",
        "id_evento_firma": "PENDIENTE",
    }
    texto = renderizar_texto(tipo, contexto_revision)
    ruta = STORAGE_DIR / participante_id / f"{tipo}_borrador.pdf"
    texto_a_pdf(texto, ruta)
    return {"texto_base": texto, "ruta_pdf": str(ruta)}


def sellar_documento_firmado(
    tipo: str,
    participante_id: str,
    contexto: dict,
    fecha_firma_iso: str,
    canal_verificacion: str,
    id_evento_firma: str,
) -> dict:
    """
    Recalcula el documento con los datos definitivos + constancia de firma,
    genera el hash sobre el CONTENIDO SUSTANCIAL (sin la constancia, para
    evitar dependencia circular) y produce el PDF final firmado.
    """
    # 1) Contenido sustancial que la persona efectivamente aceptó.
    contexto_sustancial = {
        **contexto,
        "hash_documento": "",
        "fecha_firma": fecha_firma_iso,
        "canal_verificacion": canal_verificacion,
        "id_evento_firma": id_evento_firma,
    }
    texto_sustancial = renderizar_texto(tipo, contexto_sustancial)
    hash_doc = calcular_hash(texto_sustancial)

    # 2) Documento final, con el hash ya calculado incluido en la constancia.
    contexto_final = {**contexto_sustancial, "hash_documento": hash_doc}
    texto_final = renderizar_texto(tipo, contexto_final)

    ruta = STORAGE_DIR / participante_id / f"{tipo}_firmado.pdf"
    texto_a_pdf(texto_final, ruta)

    return {"hash_sha256": hash_doc, "ruta_pdf": str(ruta), "texto_final": texto_final}


# ---------------------------------------------------------------------------
# Derecho de petición: un documento aparte (no es "firmado" por el
# participante, sino "enviado" por el apoderado), por eso usa su propia
# constancia (hash + fecha de envío + destinatario) en vez de la de firma.
# Una misma persona puede generar VARIOS derechos de petición (uno por cada
# secretaría de tránsito involucrada en sus comparendos), por lo que aquí
# `nombre_archivo` sí debe ser único por secretaría (a diferencia del poder
# y el contrato, que son uno solo por participante).
# ---------------------------------------------------------------------------

def generar_derecho_peticion_borrador(participante_id: str, nombre_archivo: str, contexto: dict) -> dict:
    contexto_borrador = {
        **contexto,
        "hash_documento": "PENDIENTE — se calculará al momento del envío",
        "fecha_envio": "PENDIENTE",
        "proveedor_ref": "PENDIENTE",
    }
    texto = renderizar_texto("derecho_peticion", contexto_borrador)
    ruta = STORAGE_DIR / participante_id / f"{nombre_archivo}_borrador.pdf"
    texto_a_pdf(texto, ruta)
    return {"texto_base": texto, "ruta_pdf": str(ruta)}


def sellar_derecho_peticion_enviado(participante_id: str, nombre_archivo: str, contexto: dict,
                                     fecha_envio_iso: str, proveedor_ref: str) -> dict:
    contexto_sustancial = {**contexto, "hash_documento": "", "fecha_envio": fecha_envio_iso,
                            "proveedor_ref": proveedor_ref}
    texto_sustancial = renderizar_texto("derecho_peticion", contexto_sustancial)
    hash_doc = calcular_hash(texto_sustancial)

    contexto_final = {**contexto_sustancial, "hash_documento": hash_doc}
    texto_final = renderizar_texto("derecho_peticion", contexto_final)

    ruta = STORAGE_DIR / participante_id / f"{nombre_archivo}_enviado.pdf"
    texto_a_pdf(texto_final, ruta)
    return {"hash_sha256": hash_doc, "ruta_pdf": str(ruta), "texto_final": texto_final}
