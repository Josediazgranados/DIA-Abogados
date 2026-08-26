"""
Capa de persistencia — misma API funcional que el prototipo (app/db.py en
firma-poderes), pero implementada con SQLAlchemy en vez de `sqlite3` crudo.
Todas las funciones siguen devolviendo `dict` (no objetos ORM) para que
`services/remision.py` y los routers, que acceden a los campos como
`participante["id"]`, no necesiten cambios.

El motor (SQLite en desarrollo, PostgreSQL en producción) se decide por
`DATABASE_URL` — ver app/config.py.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta

from app.database import SessionLocal, init_db as _init_db
from app.models import (
    Comparendo, ConfigKV, DerechoPeticion, DocumentoFirmado, EventoAuditoria,
    OtpChallenge, Participante, Remision, SecretariaTransito,
)


def init_db() -> None:
    _init_db()
    seed_secretarias_transito()


def seed_secretarias_transito() -> None:
    """Siembra el catálogo de las 37 secretarías la primera vez que corre la
    aplicación. Si la tabla ya tiene filas, NO las sobrescribe — así,
    correcciones manuales hechas después de la siembra (ej. un correo que
    el equipo jurídico verificó y corrigió) sobreviven a reinicios."""
    from app.data.secretarias_transito import SECRETARIAS_TRANSITO
    with SessionLocal() as session:
        existe = session.query(SecretariaTransito).first()
        if existe:
            return
        for s in SECRETARIAS_TRANSITO:
            session.add(SecretariaTransito(
                id=s["id"], nombre=s["nombre"], correo_notificacion=s["correo_notificacion"],
                correo_alternativo=s["correo_alternativo"], confianza=s["confianza"],
                requiere_verificacion_manual=bool(s["requiere_verificacion_manual"]),
                fuente=s["fuente"], nota=s["nota"],
            ))
        session.commit()


def new_id() -> str:
    return str(uuid.uuid4())


def now() -> str:
    return datetime.utcnow().isoformat()


def _to_dict(obj) -> dict | None:
    if obj is None:
        return None
    return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}


# ---------------------------------------------------------------------------
# Participantes
# ---------------------------------------------------------------------------

def crear_participante(nombre=None, numero_documento=None, email=None, celular=None) -> dict:
    pid, token, ts = new_id(), new_id(), now()
    with SessionLocal() as session:
        session.add(Participante(
            id=pid, token=token, nombre_completo=nombre, numero_documento=numero_documento,
            email=email, celular=celular, estado="invitado", creado_en=ts, actualizado_en=ts,
        ))
        session.commit()
    return obtener_participante(pid)


def obtener_participante(participante_id: str) -> dict | None:
    with SessionLocal() as session:
        return _to_dict(session.get(Participante, participante_id))


def obtener_participante_por_token(token: str) -> dict | None:
    with SessionLocal() as session:
        row = session.query(Participante).filter(Participante.token == token).first()
        return _to_dict(row)


def actualizar_participante(participante_id: str, **campos) -> None:
    if not campos:
        return
    campos["actualizado_en"] = now()
    with SessionLocal() as session:
        session.query(Participante).filter(Participante.id == participante_id).update(campos)
        session.commit()


# ---------------------------------------------------------------------------
# Comparendos (fotomultas) asociados al participante
# ---------------------------------------------------------------------------

def agregar_comparendo(participante_id: str, numero_comparendo=None, fecha_comparendo=None,
                        placa=None, tipo_vehiculo=None, titular_nombre=None,
                        titular_documento=None, secretaria_transito_id=None) -> dict:
    cid = new_id()
    with SessionLocal() as session:
        session.add(Comparendo(
            id=cid, participante_id=participante_id, numero_comparendo=numero_comparendo,
            fecha_comparendo=fecha_comparendo, placa=(placa or "").upper() or None,
            tipo_vehiculo=tipo_vehiculo, titular_nombre=titular_nombre,
            titular_documento=titular_documento, secretaria_transito_id=secretaria_transito_id, creado_en=now(),
        ))
        session.commit()
        return _to_dict(session.get(Comparendo, cid))


def comparendos_de(participante_id: str) -> list[dict]:
    with SessionLocal() as session:
        rows = (
            session.query(Comparendo)
            .filter(Comparendo.participante_id == participante_id)
            .order_by(Comparendo.creado_en)
            .all()
        )
        return [_to_dict(r) for r in rows]


def eliminar_comparendo(comparendo_id: str, participante_id: str) -> bool:
    with SessionLocal() as session:
        cur = (
            session.query(Comparendo)
            .filter(Comparendo.id == comparendo_id, Comparendo.participante_id == participante_id)
            .delete()
        )
        session.commit()
        return cur > 0


# ---------------------------------------------------------------------------
# Documentos
# ---------------------------------------------------------------------------

def crear_documento(participante_id: str, tipo: str, contenido_render_path: str) -> dict:
    doc_id = new_id()
    with SessionLocal() as session:
        session.add(DocumentoFirmado(
            id=doc_id, participante_id=participante_id, tipo=tipo,
            contenido_render_path=contenido_render_path,
        ))
        session.commit()
        return _to_dict(session.get(DocumentoFirmado, doc_id))


def marcar_documento_firmado(doc_id: str, contenido_final_path: str, hash_sha256: str) -> None:
    with SessionLocal() as session:
        session.query(DocumentoFirmado).filter(DocumentoFirmado.id == doc_id).update({
            "contenido_final_path": contenido_final_path,
            "hash_sha256": hash_sha256,
            "firmado_en": now(),
        })
        session.commit()


def documentos_de(participante_id: str) -> list[dict]:
    with SessionLocal() as session:
        rows = session.query(DocumentoFirmado).filter(DocumentoFirmado.participante_id == participante_id).all()
        return [_to_dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Auditoría
# ---------------------------------------------------------------------------

def registrar_evento(participante_id: str, tipo_evento: str, canal: str | None = None, detalle: dict | None = None) -> None:
    with SessionLocal() as session:
        session.add(EventoAuditoria(
            id=new_id(), participante_id=participante_id, tipo_evento=tipo_evento,
            canal=canal, detalle=json.dumps(detalle or {}), timestamp=now(),
        ))
        session.commit()


def eventos_de(participante_id: str) -> list[dict]:
    with SessionLocal() as session:
        rows = (
            session.query(EventoAuditoria)
            .filter(EventoAuditoria.participante_id == participante_id)
            .order_by(EventoAuditoria.timestamp)
            .all()
        )
        return [_to_dict(r) for r in rows]


# ---------------------------------------------------------------------------
# OTP
# ---------------------------------------------------------------------------

def crear_otp(participante_id: str, canal: str, codigo_hash: str, minutos_expira: int = 10) -> str:
    otp_id = new_id()
    expira = (datetime.utcnow() + timedelta(minutes=minutos_expira)).isoformat()
    with SessionLocal() as session:
        session.add(OtpChallenge(
            id=otp_id, participante_id=participante_id, canal=canal,
            codigo_hash=codigo_hash, expira_en=expira, intentos=0,
        ))
        session.commit()
    return otp_id


def ultimo_otp_vigente(participante_id: str) -> dict | None:
    with SessionLocal() as session:
        row = (
            session.query(OtpChallenge)
            .filter(OtpChallenge.participante_id == participante_id, OtpChallenge.verificado.is_(None))
            .order_by(OtpChallenge.expira_en.desc())
            .first()
        )
        return _to_dict(row)


def incrementar_intentos_otp(otp_id: str) -> None:
    with SessionLocal() as session:
        otp = session.get(OtpChallenge, otp_id)
        if otp:
            otp.intentos = (otp.intentos or 0) + 1
            session.commit()


def marcar_otp_verificado(otp_id: str) -> None:
    with SessionLocal() as session:
        session.query(OtpChallenge).filter(OtpChallenge.id == otp_id).update({"verificado": now()})
        session.commit()


# ---------------------------------------------------------------------------
# Remisión certificada del documento firmado (cascada opción 1 -> 3 -> 2)
# ---------------------------------------------------------------------------

def crear_intento_remision(participante_id: str, orden: int, canal: str, proveedor_ref: str | None = None,
                            detalle: dict | None = None, nivel_evidencia: str = "certificada_proveedor") -> dict:
    rid = new_id()
    with SessionLocal() as session:
        session.add(Remision(
            id=rid, participante_id=participante_id, orden=orden, canal=canal, estado="enviado",
            proveedor_ref=proveedor_ref, detalle=json.dumps(detalle or {}), nivel_evidencia=nivel_evidencia,
            creado_en=now(),
        ))
        session.commit()
        return _to_dict(session.get(Remision, rid))


def actualizar_intento_remision(remision_id: str, estado: str, constancia_path: str | None = None,
                                 detalle_extra: dict | None = None) -> None:
    with SessionLocal() as session:
        remision = session.get(Remision, remision_id)
        if not remision:
            return
        detalle = json.loads(remision.detalle) if remision.detalle else {}
        if detalle_extra:
            detalle.update(detalle_extra)
        remision.estado = estado
        if constancia_path is not None:
            remision.constancia_path = constancia_path
        remision.detalle = json.dumps(detalle)
        if estado == "confirmado":
            remision.confirmado_en = now()
        session.commit()


def intentos_remision_de(participante_id: str) -> list[dict]:
    with SessionLocal() as session:
        rows = (
            session.query(Remision)
            .filter(Remision.participante_id == participante_id)
            .order_by(Remision.orden, Remision.creado_en)
            .all()
        )
        return [_to_dict(r) for r in rows]


def remision_confirmada_de(participante_id: str) -> dict | None:
    with SessionLocal() as session:
        row = (
            session.query(Remision)
            .filter(Remision.participante_id == participante_id, Remision.estado == "confirmado")
            .order_by(Remision.confirmado_en)
            .first()
        )
        return _to_dict(row)


# ---------------------------------------------------------------------------
# Catálogo de secretarías de tránsito
# ---------------------------------------------------------------------------

def listar_secretarias_transito() -> list[dict]:
    with SessionLocal() as session:
        rows = session.query(SecretariaTransito).order_by(SecretariaTransito.id).all()
        return [_to_dict(r) for r in rows]


def obtener_secretaria_transito(secretaria_id: int) -> dict | None:
    with SessionLocal() as session:
        return _to_dict(session.get(SecretariaTransito, secretaria_id))


def actualizar_correo_secretaria(secretaria_id: int, correo_notificacion: str,
                                  requiere_verificacion_manual: bool = False) -> None:
    """Para cuando el equipo jurídico verifica/corrige un correo del catálogo
    (ej. tras la llamada telefónica de confirmación) — así deja de bloquearse
    el envío automático para esa secretaría."""
    with SessionLocal() as session:
        session.query(SecretariaTransito).filter(SecretariaTransito.id == secretaria_id).update({
            "correo_notificacion": correo_notificacion,
            "requiere_verificacion_manual": requiere_verificacion_manual,
        })
        session.commit()


# ---------------------------------------------------------------------------
# Derechos de petición (uno por participante x secretaría involucrada)
# ---------------------------------------------------------------------------

def crear_derecho_peticion(participante_id: str, secretaria_transito_id: int, comparendo_ids: list[str],
                            email_destino: str | None, estado_envio: str = "pendiente") -> dict:
    did = new_id()
    with SessionLocal() as session:
        session.add(DerechoPeticion(
            id=did, participante_id=participante_id, secretaria_transito_id=secretaria_transito_id,
            comparendo_ids=json.dumps(comparendo_ids), email_destino=email_destino,
            estado_envio=estado_envio, creado_en=now(),
        ))
        session.commit()
        return _to_dict(session.get(DerechoPeticion, did))


def actualizar_derecho_peticion(derecho_id: str, **campos) -> None:
    if not campos:
        return
    with SessionLocal() as session:
        session.query(DerechoPeticion).filter(DerechoPeticion.id == derecho_id).update(campos)
        session.commit()


def derechos_peticion_de(participante_id: str) -> list[dict]:
    with SessionLocal() as session:
        rows = (
            session.query(DerechoPeticion)
            .filter(DerechoPeticion.participante_id == participante_id)
            .order_by(DerechoPeticion.creado_en)
            .all()
        )
        return [_to_dict(r) for r in rows]


def contar_derechos_peticion_por_estado(estado_envio: str) -> int:
    with SessionLocal() as session:
        return session.query(DerechoPeticion).filter(DerechoPeticion.estado_envio == estado_envio).count()


def contar_derechos_peticion_total() -> int:
    with SessionLocal() as session:
        return session.query(DerechoPeticion).count()


# ---------------------------------------------------------------------------
# Configuración operativa simple (circuit breaker / pausa manual)
# ---------------------------------------------------------------------------

def get_config(clave: str, default: str | None = None) -> str | None:
    with SessionLocal() as session:
        row = session.get(ConfigKV, clave)
        return row.valor if row else default


def set_config(clave: str, valor: str) -> None:
    with SessionLocal() as session:
        row = session.get(ConfigKV, clave)
        if row:
            row.valor = valor
        else:
            session.add(ConfigKV(clave=clave, valor=valor))
        session.commit()
