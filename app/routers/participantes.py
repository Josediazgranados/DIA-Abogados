"""
Paso 0 (alta), paso 1 (datos básicos) y paso 1b (comparendo(s) que la
persona quiere incluir en la acción de grupo).
"""
from __future__ import annotations

from fastapi import APIRouter, Request

from app import db
from app.schemas import ComparendoBody, DatosUpdate, ParticipanteCreate
from app.utils import error, ip_cliente, respond

router = APIRouter(prefix="/api/participantes", tags=["participantes"])


@router.post("", status_code=201)
def crear_participante(body: ParticipanteCreate):
    p = db.crear_participante(
        nombre=body.nombre_completo,
        numero_documento=body.numero_documento,
        email=body.email,
        celular=body.celular,
    )
    db.registrar_evento(p["id"], "invitacion_creada", detalle={"origen": body.origen})
    return {"token": p["token"], "id": p["id"]}


@router.get("/{token}")
def obtener_participante(token: str):
    p = db.obtener_participante_por_token(token)
    if not p:
        return error("token inválido", 404)
    return p


@router.post("/{token}/datos")
def guardar_datos(token: str, body: DatosUpdate, request: Request):
    p = db.obtener_participante_por_token(token)
    if not p:
        return error("token inválido", 404)

    # device_os lo detecta el frontend (ej. por userAgentData o sniffing
    # del user-agent) y define si el "plan C" (opción 2, Web Share API)
    # estará disponible más adelante para esta persona — ver paso 5.
    db.actualizar_participante(
        p["id"],
        nombre_completo=body.nombre_completo if body.nombre_completo is not None else p["nombre_completo"],
        numero_documento=body.numero_documento if body.numero_documento is not None else p["numero_documento"],
        email=body.email if body.email is not None else p["email"],
        celular=body.celular if body.celular is not None else p["celular"],
        device_os=body.device_os if body.device_os is not None else p["device_os"],
        estado="datos_capturados",
    )
    db.registrar_evento(p["id"], "datos_capturados", detalle={"ip": ip_cliente(request)})
    return {"ok": True}


@router.post("/{token}/comparendos", status_code=201)
def agregar_comparendos(token: str, body: ComparendoBody, request: Request):
    p = db.obtener_participante_por_token(token)
    if not p:
        return error("token inválido", 404)

    items = body.comparendos if body.comparendos is not None else [body]
    ids_validos = {s["id"] for s in db.listar_secretarias_transito()}

    creados, errores = [], []
    for i, item in enumerate(items):
        numero = (item.numero_comparendo or "").strip()
        placa = (item.placa or "").strip()
        if not numero or not placa:
            errores.append({"indice": i, "error": "numero_comparendo y placa son obligatorios"})
            continue
        if item.secretaria_transito_id not in ids_validos:
            errores.append({"indice": i, "error": "secretaria_transito_id es obligatorio y debe "
                                                    "ser una de las 37 secretarías del catálogo "
                                                    "(ver GET /api/catalogos/secretarias-transito)"})
            continue
        comparendo = db.agregar_comparendo(
            p["id"],
            numero_comparendo=numero,
            fecha_comparendo=item.fecha_comparendo,
            placa=placa,
            tipo_vehiculo=item.tipo_vehiculo,
            secretaria_transito_id=item.secretaria_transito_id,
            titular_nombre=item.titular_nombre or p["nombre_completo"],
            titular_documento=item.titular_documento or p["numero_documento"],
        )
        creados.append(comparendo)
        db.registrar_evento(
            p["id"], "comparendo_registrado",
            detalle={"numero_comparendo": numero, "placa": placa,
                     "secretaria_transito_id": item.secretaria_transito_id, "ip": ip_cliente(request)},
        )

    status = 201 if creados else 400
    return respond({"creados": creados, "errores": errores}, status)


@router.get("/{token}/comparendos")
def listar_comparendos(token: str):
    p = db.obtener_participante_por_token(token)
    if not p:
        return error("token inválido", 404)
    return db.comparendos_de(p["id"])


@router.delete("/{token}/comparendos/{comparendo_id}")
def borrar_comparendo(token: str, comparendo_id: str):
    p = db.obtener_participante_por_token(token)
    if not p:
        return error("token inválido", 404)
    borrado = db.eliminar_comparendo(comparendo_id, p["id"])
    if not borrado:
        return error("comparendo no encontrado", 404)
    db.registrar_evento(p["id"], "comparendo_eliminado", detalle={"comparendo_id": comparendo_id})
    return {"ok": True}
