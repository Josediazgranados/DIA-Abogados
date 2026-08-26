"""
API del flujo de vinculación a la acción de grupo (firma de poder especial +
contrato de prestación de servicios) — versión FastAPI, migrada del
prototipo `firma-poderes` (Flask + SQLite) según la sección
"De prototipo a producción" de su README.

FLUJO DE 4 PASOS PARA EL PARTICIPANTE + REMISIÓN CERTIFICADA AUTOMÁTICA
------------------------------------------------------------------------
 1) Datos básicos       -> POST /api/participantes/<token>/datos
 1b) Datos del comparendo(s) -> POST /api/participantes/<token>/comparendos
                                 (uno o varios: número, fecha, placa, tipo de
                                 vehículo, titular y su documento; ver abajo)
 2) Foto cédula+selfie -> POST /api/participantes/<token>/identidad
 3) Revisar y aceptar  -> GET  /api/participantes/<token>/documentos
                           POST /api/participantes/<token>/aceptar   (envía OTP)
 4) Confirmar OTP       -> POST /api/participantes/<token>/verificar-otp  (firma sellada)

 5) Remisión certificada del documento firmado ("el pantallazo que pide el
    juzgado"), automatizada en cascada de UN clic — ver
    app/services/remision.py para el detalle de cada opción y por qué
    quedan en ese orden de prioridad.

Ver README.md para el detalle metodológico completo y los endpoints de la
cascada de remisión (paso 5).
"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app import db
from app.routers import admin, auditoria, catalogos, documentos, identidad, participantes, remision

FRONTEND_DIR = Path(__file__).parent.parent / "frontend"


def create_app() -> FastAPI:
    app = FastAPI(title="DIA Abogados — Firma de poderes")
    db.init_db()

    # Permisivo para desarrollo local: el frontend estático (abierto como
    # archivo o servido en otro puerto) necesita poder llamar a esta API
    # desde un origen distinto. Restringir a los dominios reales en producción.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(participantes.router)
    app.include_router(identidad.router)
    app.include_router(documentos.router)
    app.include_router(remision.router)
    app.include_router(auditoria.router)
    app.include_router(catalogos.router)
    app.include_router(admin.router)

    @app.get("/api/salud")
    def salud():
        return {"status": "ok"}

    # Sirve el frontend estático (index.html, firma.html, css, js, imágenes)
    # desde el mismo servicio y el mismo dominio que la API. Se monta AL
    # FINAL, después de las rutas /api/... y /webhooks/..., para que estas
    # sigan resolviendo primero; todo lo demás (incluida la raíz "/") lo
    # sirve StaticFiles directo desde la carpeta frontend/.
    if FRONTEND_DIR.is_dir():
        app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
