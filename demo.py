"""
Demostración end-to-end del algoritmo de vinculación a la acción de grupo
por fotocomparendos declarados nulos por el Ministerio de Transporte,
incluyendo el paso 1b (datos del/los comparendo(s): número, fecha, placa,
tipo de vehículo, titular, su documento y la secretaría de tránsito que lo
impuso), el paso 5 (cascada de remisión certificada) y el derecho de
petición automático que se genera y envía por cada secretaría involucrada:

    Opción 1 -> botón interactivo de WhatsApp Business API
    Opción 3 -> confirmación por correo (mailto prellenado), si la 1 falla
    Opción 2 -> Web Share API hacia WhatsApp, solo si el dispositivo es
                Android y las dos anteriores fallaron ("plan C")
    Si las tres fallan -> queda pendiente de gestión manual

Se corren 4 escenarios para mostrar cada rama de la cascada Y del derecho
de petición:
    A) WhatsApp confirma de inmediato (camino feliz). Secretaría de
       confianza alta -> derecho de petición sale enviado solo.
    B) WhatsApp no se confirma -> cae a correo -> correo confirma. Dos
       comparendos de la MISMA secretaría -> se agrupan en un solo
       derecho de petición.
    C) WhatsApp y correo no se confirman, dispositivo Android -> plan C
       confirma. Secretaría sin correo confiable -> derecho de petición
       queda bloqueado para verificación manual.
    D) WhatsApp y correo no se confirman, dispositivo NO es Android
       -> ninguna opción automatizada disponible -> queda pendiente
       manual. Secretaría distinta, también bloqueada por otro motivo.

Uso:
    python demo.py
"""
import io
import shutil
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image

from app.main import create_app

STORAGE_DIR = Path(__file__).parent / "app" / "storage"


def _imagen_dummy() -> io.BytesIO:
    img = Image.new("RGB", (400, 300), color=(230, 230, 230))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)
    return buf


def firmar_participante(client, nombre, documento, email, celular, device_os, comparendos):
    """Corre los pasos 1, 1b, 2, 3 y 4 (datos, comparendo(s), identidad,
    revisión, OTP) y deja el documento firmado. Devuelve el token y el
    resultado de verificar-otp."""
    from app import db
    from app.services import notify

    r = client.post("/api/participantes", json={
        "nombre_completo": nombre, "numero_documento": documento,
        "email": email, "celular": celular, "origen": "carga_masiva_csv",
    })
    token = r.json()["token"]

    client.post(f"/api/participantes/{token}/datos", json={"device_os": device_os})

    # Paso 1b: uno o varios comparendos que la persona quiere incluir.
    r = client.post(f"/api/participantes/{token}/comparendos", json={"comparendos": comparendos})
    print(f"    [Paso 1b] {len(r.json()['creados'])} comparendo(s) registrado(s) para {nombre.split()[0]}")

    client.post(
        f"/api/participantes/{token}/identidad",
        files={
            "foto_cedula": ("cedula.jpg", _imagen_dummy(), "image/jpeg"),
            "selfie": ("selfie.jpg", _imagen_dummy(), "image/jpeg"),
        },
    )

    client.get(f"/api/participantes/{token}/documentos")
    client.post(f"/api/participantes/{token}/aceptar", json={"canal": "whatsapp"})

    p = db.obtener_participante_por_token(token)
    otp = db.ultimo_otp_vigente(p["id"])
    codigo_demo = notify.generar_codigo_otp()
    db.crear_otp(p["id"], "whatsapp", notify.hash_codigo(codigo_demo, p["id"]))

    r = client.post(f"/api/participantes/{token}/verificar-otp", json={"codigo": codigo_demo})
    return token, r.json()


def main():
    if STORAGE_DIR.exists():
        shutil.rmtree(STORAGE_DIR)
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)

    app = create_app()
    client = TestClient(app)

    print("=" * 78)
    print("DEMO: firma del poder + remisión certificada + derecho de petición")
    print("=" * 78)

    # ----------------------------------------------------------------
    # Escenario A: la persona firma y confirma la opción 1 (WhatsApp).
    # ----------------------------------------------------------------
    print("\n--- Escenario A: confirmación inmediata por WhatsApp (opción 1) ---")
    token_a, res_a = firmar_participante(
        client, "María Fernanda Restrepo Gómez", "1020304050",
        "maria.restrepo@example.com", "+573001234567", device_os="iOS",
        # secretaria_transito_id=5 -> Secretaría Distrital de Movilidad de
        # Bogotá, correo de notificación judicial de confianza "alta" en el
        # catálogo -> el derecho de petición debería salir enviado solo.
        comparendos=[{
            "numero_comparendo": "11001000000012345", "fecha_comparendo": "2025-03-14",
            "placa": "ABC123", "tipo_vehiculo": "Automóvil", "secretaria_transito_id": 5,
        }],
    )
    print(f"[Paso 4] Firma sellada. Cascada iniciada -> {res_a['remision']}")
    print(f"[Paso 4 / Derecho de petición] {res_a['derechos_peticion']}")

    r = client.post("/webhooks/whatsapp/boton", json={"token": token_a})
    print(f"[Paso 5 / Opción 1] Webhook de WhatsApp confirma el botón -> {r.json()}")

    # ----------------------------------------------------------------
    # Escenario B: WhatsApp no se confirma -> cae a correo -> confirma.
    # ----------------------------------------------------------------
    print("\n--- Escenario B: WhatsApp expira -> respaldo por correo (opción 3) ---")
    token_b, res_b = firmar_participante(
        client, "Carlos Andrés Pineda Ruiz", "80112233",
        "carlos.pineda@example.com", "+573007654321", device_os="iOS",
        # Los 2 comparendos son de la MISMA secretaría (id=6, Barranquilla,
        # confianza alta) -> deben agruparse en UN solo derecho de petición
        # que liste ambos, no en dos peticiones separadas.
        comparendos=[
            {"numero_comparendo": "11001000000067890", "fecha_comparendo": "2024-11-02",
             "placa": "XYZ987", "tipo_vehiculo": "Motocicleta", "secretaria_transito_id": 6},
            {"numero_comparendo": "11001000000067891", "fecha_comparendo": "2025-01-20",
             "placa": "XYZ987", "tipo_vehiculo": "Motocicleta", "secretaria_transito_id": 6},
        ],
    )
    print(f"[Paso 4] Firma sellada. Cascada iniciada -> {res_b['remision']}")
    print(f"[Paso 4 / Derecho de petición] {res_b['derechos_peticion']} (debe ser 1 solo, agrupando los 2 comparendos)")

    r = client.post(f"/api/participantes/{token_b}/remision/fallback-email")
    print(f"[Paso 5 / Opción 3] Opción 1 marcada como expirada; se ofrece 'Responder para "
          f"confirmar' por correo -> mailto generado: {r.json()['mailto'][:60]}...")

    r = client.post("/webhooks/email/inbound", json={"token": token_b})
    print(f"[Paso 5 / Opción 3] Webhook de correo entrante confirma -> {r.json()}")

    # ----------------------------------------------------------------
    # Escenario C: WhatsApp y correo fallan; dispositivo Android -> plan C.
    # ----------------------------------------------------------------
    print("\n--- Escenario C: WhatsApp y correo fallan, Android -> plan C (opción 2) ---")
    token_c, res_c = firmar_participante(
        client, "Laura Juliana Torres Méndez", "1098765432",
        "laura.torres@example.com", "+573009998877", device_os="android",
        # Aquí la titular del vehículo es distinta de quien firma (ej. carro
        # de la empresa familiar) — el formulario permite esa diferencia.
        # secretaria_transito_id=7 -> Instituto de Corozal, catalogado como
        # "no_encontrado" (solo se halló un correo de Hotmail de fuente no
        # oficial) -> el derecho de petición debe quedar BLOQUEADO para
        # verificación manual, no enviarse solo a un correo no confiable.
        comparendos=[{
            "numero_comparendo": "11001000000054321", "fecha_comparendo": "2025-05-09",
            "placa": "LMT456", "tipo_vehiculo": "Camioneta", "secretaria_transito_id": 7,
            "titular_nombre": "Transportes Torres S.A.S.", "titular_documento": "NIT 900123456-1",
        }],
    )
    print(f"[Paso 4] Firma sellada. Cascada iniciada -> {res_c['remision']}")
    print(f"[Paso 4 / Derecho de petición] {res_c['derechos_peticion']} (debe quedar bloqueado_verificacion)")

    client.post(f"/api/participantes/{token_c}/remision/fallback-email")  # opción 1 -> fallida
    r = client.post(f"/api/participantes/{token_c}/remision/plan-c")       # opción 3 -> fallida, ofrece plan C
    print(f"[Paso 5 / Opción 2] Opciones 1 y 3 falladas; se ofrece plan C -> {r.json()}")

    r = client.post(f"/api/participantes/{token_c}/remision/plan-c/confirmar", json={"exito": True})
    print(f"[Paso 5 / Opción 2] navigator.share() reporta éxito -> {r.json()}")

    # ----------------------------------------------------------------
    # Escenario D: WhatsApp y correo fallan; dispositivo NO Android
    # -> ninguna opción automatizada disponible -> pendiente manual.
    # ----------------------------------------------------------------
    print("\n--- Escenario D: WhatsApp y correo fallan, iPhone -> sin plan C -> manual ---")
    token_d, res_d = firmar_participante(
        client, "Jorge Iván Salazar Cuervo", "79456123",
        "jorge.salazar@example.com", "+573001112233", device_os="iOS",
        # secretaria_transito_id=20 -> Movilidad de Cundinamarca, catalogada
        # como "no_encontrado" (solo reciben por formulario web) -> también
        # debe quedar bloqueado, por un motivo distinto al del escenario C.
        comparendos=[{
            "numero_comparendo": "11001000000099999", "fecha_comparendo": "2024-08-30",
            "placa": "JSC321", "tipo_vehiculo": "Automóvil", "secretaria_transito_id": 20,
        }],
    )
    print(f"[Paso 4] Firma sellada. Cascada iniciada -> {res_d['remision']}")
    print(f"[Paso 4 / Derecho de petición] {res_d['derechos_peticion']} (debe quedar bloqueado_verificacion)")

    client.post(f"/api/participantes/{token_d}/remision/fallback-email")  # opción 1 -> fallida
    r = client.post(f"/api/participantes/{token_d}/remision/plan-c")       # opción 3 -> fallida; plan C no disponible
    print(f"[Paso 5] Ninguna opción automatizada disponible (iPhone) -> {r.json()}")

    # ----------------------------------------------------------------
    # Resumen final de los 4 escenarios
    # ----------------------------------------------------------------
    from app import db
    print("\n" + "=" * 78)
    print("Resumen final de los 4 escenarios (estado del participante + intentos):")
    for nombre_escenario, token in [("A", token_a), ("B", token_b), ("C", token_c), ("D", token_d)]:
        p = db.obtener_participante_por_token(token)
        intentos = db.intentos_remision_de(p["id"])
        print(f"\n  Escenario {nombre_escenario} — {p['nombre_completo']}")
        print(f"    Estado final: {p['estado']}")
        for i in intentos:
            constancia = f" | constancia: {Path(i['constancia_path']).name}" if i["constancia_path"] else ""
            print(f"    - orden {i['orden']} | {i['canal']:<18} | {i['estado']:<10} "
                  f"| evidencia: {i['nivel_evidencia']}{constancia}")
        for dp in db.derechos_peticion_de(p["id"]):
            secretaria = db.obtener_secretaria_transito(dp["secretaria_transito_id"])
            print(f"    - derecho de petición -> {secretaria['nombre']}: {dp['estado_envio']}"
                  f" (correo: {dp['email_destino'] or 'NO VERIFICADO'})")
    print("=" * 78)

    print("\nResumen operativo de la campaña (lo que vería el equipo jurídico en el panel):")
    for estado in ("pendiente", "enviado", "fallido", "bloqueado_verificacion", "en_revision_manual"):
        print(f"    {estado}: {db.contar_derechos_peticion_por_estado(estado)}")
    print(f"    total: {db.contar_derechos_peticion_total()}")
    print("=" * 78)


if __name__ == "__main__":
    main()
