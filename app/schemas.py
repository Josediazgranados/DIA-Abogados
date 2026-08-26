"""Schemas Pydantic de request/response, uno por endpoint del flujo."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ParticipanteCreate(BaseModel):
    nombre_completo: Optional[str] = None
    numero_documento: Optional[str] = None
    email: Optional[str] = None
    celular: Optional[str] = None
    origen: Optional[str] = "manual"


class DatosUpdate(BaseModel):
    nombre_completo: Optional[str] = None
    numero_documento: Optional[str] = None
    email: Optional[str] = None
    celular: Optional[str] = None
    device_os: Optional[str] = None


class ComparendoItem(BaseModel):
    numero_comparendo: Optional[str] = None
    fecha_comparendo: Optional[str] = None
    placa: Optional[str] = None
    tipo_vehiculo: Optional[str] = None
    secretaria_transito_id: Optional[int] = None
    titular_nombre: Optional[str] = None
    titular_documento: Optional[str] = None


class ComparendoBody(ComparendoItem):
    """Acepta un solo comparendo (campos a nivel raíz) o una lista bajo
    `comparendos`, igual que el prototipo, para que el mismo formulario
    sirva si la persona tiene uno o varios."""

    comparendos: Optional[list[ComparendoItem]] = None


class AceptarBody(BaseModel):
    canal: Optional[str] = "whatsapp"


class VerificarOtpBody(BaseModel):
    codigo: str = ""


class WhatsappWebhookBody(BaseModel):
    token: str
    boton_texto: Optional[str] = "Confirmo y remito mi firma"


class EmailWebhookBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    token: str
    from_: Optional[str] = Field(None, alias="from")
    subject: Optional[str] = None
    message_id: Optional[str] = None
    ip: Optional[str] = None
    body: Optional[str] = None


class PlanCConfirmarBody(BaseModel):
    exito: bool = False


class ActualizarCorreoSecretariaBody(BaseModel):
    correo_notificacion: str
