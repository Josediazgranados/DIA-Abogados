# DIA Abogados — Firma de poder especial y contrato para acción de grupo (fotocomparendos)

Implementación del algoritmo del prototipo de referencia
(`../firma-poderes`), migrada a la arquitectura que su propio README
recomendaba para producción: **FastAPI** en vez de Flask, y **SQLAlchemy**
en vez de `sqlite3` crudo (con PostgreSQL como motor de producción, con
solo cambiar `DATABASE_URL`).

Implementa el mismo flujo end-to-end: datos básicos → **datos del/los
comparendo(s)** (número, fecha, placa, tipo de vehículo, titular, su
documento y la **secretaría de tránsito** que lo impuso, elegida de un
catálogo de 37 organismos) → foto de cédula + selfie → revisión y
aceptación → confirmación por código (OTP) enviado por WhatsApp o correo.
Al confirmar, el poder especial y el contrato de prestación de servicios
quedan firmados electrónicamente, sellados con un hash SHA-256 y con una
traza de auditoría completa — y, en el mismo instante:

- **Paso 5: remisión certificada**, automatizada en cascada de un clic
  (WhatsApp → correo → Web Share Android → pendiente manual). Ver
  `app/services/remision.py` para el detalle de cada opción.
- **Derecho de petición automático**: se genera y se intenta enviar, desde
  el correo del abogado apoderado, un derecho de petición a cada
  secretaría de tránsito involucrada en los comparendos del participante.
  Ver la sección [Derecho de petición automático](#derecho-de-petición-automático) más abajo.

## Requisitos

Python 3.10+. Usa SQLite por defecto (sin necesidad de instalar
PostgreSQL/Docker) ni credenciales de terceros — WhatsApp/correo funcionan
en modo simulado (ver `NOTIFY_MOCK` abajo).

```bash
pip install -r requirements.txt
```

Copiar `.env.example` a `.env` y ajustar los datos del caso/apoderado si se
desea (todos tienen valores por defecto para poder correr sin configurar
nada).

## Ejecutar la demostración end-to-end (sin servidor)

```bash
python demo.py
```

Corre el flujo completo (pasos 1 a 5) para **4 escenarios** que muestran
cada rama de la cascada de remisión: (A) WhatsApp confirma de inmediato,
(B) WhatsApp expira y confirma por correo, (C) WhatsApp y correo fallan
pero el dispositivo es Android y confirma por plan C, y (D) WhatsApp y
correo fallan y el dispositivo no es Android, por lo que el caso queda
pendiente de gestión manual. Deja los PDF y las constancias de remisión
generadas en `app/storage/<id_participante>/`.

## Levantar la API

```bash
uvicorn app.main:app --reload --port 8000
```

Documentación interactiva autogenerada (Swagger UI) en
`http://localhost:8000/docs`.

Endpoints principales (mismas rutas que el prototipo — ver `app/routers/`):

| Paso | Método y ruta |
|---|---|
| 0. Alta / invitación | `POST /api/participantes` |
| 1. Datos básicos | `POST /api/participantes/<token>/datos` |
| 1b. Datos del/los comparendo(s) | `POST /api/participantes/<token>/comparendos` (uno o una lista) |
| 1b. Ver / quitar comparendos | `GET` y `DELETE /api/participantes/<token>/comparendos/<id>` |
| 2. Foto cédula + selfie | `POST /api/participantes/<token>/identidad` (multipart) |
| 3a. Generar documentos | `GET  /api/participantes/<token>/documentos` |
| 3b. Aceptar → envía OTP | `POST /api/participantes/<token>/aceptar` |
| 4. Confirmar OTP → firma (dispara opción 1 automáticamente) | `POST /api/participantes/<token>/verificar-otp` |
| 5-Op.1. Webhook confirmación WhatsApp | `POST /webhooks/whatsapp/boton` |
| 5-Op.3. Activar respaldo por correo | `POST /api/participantes/<token>/remision/fallback-email` |
| 5-Op.3. Webhook confirmación correo | `POST /webhooks/email/inbound` |
| 5-Op.2. Activar plan C (solo Android) | `POST /api/participantes/<token>/remision/plan-c` |
| 5-Op.2. Confirmar resultado de navigator.share() | `POST /api/participantes/<token>/remision/plan-c/confirmar` |
| 5. Estado de la remisión | `GET  /api/participantes/<token>/remision/estado` |
| Catálogo de secretarías de tránsito | `GET  /api/catalogos/secretarias-transito` |
| Estado del/los derecho(s) de petición | `GET  /api/participantes/<token>/derechos-peticion` |
| Auditoría | `GET  /api/participantes/<token>/auditoria` |

Panel operativo para el equipo jurídico (**sin autenticación — prototipo
de demostración, proteger antes de producción**):

| Función | Método y ruta |
|---|---|
| Catálogo completo (con correo y confianza) | `GET  /api/admin/secretarias-transito` |
| Corregir el correo de una secretaría | `PUT  /api/admin/secretarias-transito/<id>/correo` |
| Pausar / reanudar el envío automático | `POST /api/admin/envio-peticiones/pausar` \| `/reanudar` |
| Resumen de la campaña (conteos por estado) | `GET  /api/admin/envio-peticiones/resumen` |

## Desplegar en Render (para compartir un link con otras personas)

El frontend (`index.html`, `firma.html`, css, js, imágenes) se sirve desde
el **mismo** servicio FastAPI (ver `app/main.py`, al final de `create_app()`):
la API queda en `/api/...` y todo lo demás (incluida la raíz `/`) lo sirve
directo desde la carpeta `frontend/`. Esto significa que solo hay **un
servicio que desplegar y un solo link que compartir** — no hay que
configurar CORS entre dos sitios distintos ni levantar nada por separado.

Ya incluye [render.yaml](render.yaml), un *Blueprint* de Render con el
servicio web + una base de datos PostgreSQL gratuita (necesaria porque el
disco de un Web Service en Render **no es persistente**: sin Postgres, los
participantes y documentos firmados desaparecerían cada vez que el
servicio se reinicia o se vuelve a desplegar).

**Pasos:**

1. Sube este proyecto a un repositorio de GitHub (puede ser privado).
2. En [render.com](https://render.com), crea una cuenta gratuita (o inicia
   sesión) y conecta tu cuenta de GitHub.
3. `New +` → `Blueprint` → selecciona el repositorio. Render lee
   `render.yaml` solo y te muestra el servicio web + la base de datos que
   va a crear — confirma.
4. Espera a que termine el primer despliegue (unos minutos). Render te da
   una URL pública, algo como `https://dia-abogados.onrender.com` — **ese
   es el link que compartes**; cualquiera que lo abra ve la página de
   inicio y puede completar el formulario, sin tocar ni ver el código.
5. (Opcional) En la pestaña "Environment" del servicio, ajusta las
   variables `APODERADO_NOMBRE`, `APODERADO_TP`, `APODERADO_EMAIL_RNA`,
   `APODERADO_DOCUMENTO`, `CIUDAD_CASO` con los datos reales de la firma —
   ya vienen con valores de ejemplo en `render.yaml`.

**Nota sobre el plan gratuito de Render:** el servicio "se duerme" tras
~15 minutos sin uso y tarda unos 30-50 segundos en "despertar" con la
primera visita — normal en el plan free, no es un error. La base de datos
Postgres gratuita expira a los 90 días (Render avisa antes); para un uso
más permanente, cambiar a un plan pago en cualquier momento sin tocar
código.

## Estructura

```
app/
  main.py                 # FastAPI app factory (create_app), monta los routers
  config.py                # Settings: CONFIG_CASO, NOTIFY_MOCK, SMTP_ABOGADO_MOCK, DATABASE_URL
  database.py               # engine/session de SQLAlchemy
  models.py                  # modelos ORM (mismo esquema que el prototipo)
  db.py                       # capa de persistencia (misma API que el prototipo)
  schemas.py                   # request/response Pydantic
  data/
    secretarias_transito.py    # catálogo semilla de las 37 secretarías (correo + confianza)
  routers/
    participantes.py           # pasos 0, 1, 1b
    identidad.py                # paso 2
    documentos.py                 # pasos 3a, 3b, 4 (+ derechos de petición)
    remision.py                    # paso 5 (cascada + webhooks)
    auditoria.py
    catalogos.py                     # catálogo público de secretarías de tránsito
    admin.py                          # panel operativo (secretarías, pausa, resumen)
  services/
    identity.py               # verificación de identidad (cédula+selfie) — mock
    notify.py                  # envío de OTP por WhatsApp/correo, y del derecho de petición — mock
    documents.py                 # render de plantillas + PDF + hash
    remision.py                    # cascada de remisión certificada (opción 1 -> 3 -> 2)
    peticion.py                      # derecho de petición automático + salvaguardas
  templates/
    poder_especial.txt
    contrato_prestacion_servicios.txt
    derecho_peticion.txt
  storage/                        # archivos generados (git-ignorado)
demo.py                            # corre el flujo completo sin necesidad de UI
frontend/                            # sitio estático (home + formulario), servido por FastAPI en producción
requirements.txt
render.yaml                            # Blueprint de despliegue en Render (ver sección "Desplegar en Render")
.env.example
```

## Derecho de petición automático

Antes de la eventual demanda, el sistema genera y **envía automáticamente
un derecho de petición** a cada secretaría de tránsito involucrada en los
comparendos del participante — en el mismo momento en que se sella la
firma (paso 4), desde el correo del abogado apoderado.

**Catálogo de las 37 secretarías** (`app/data/secretarias_transito.py`,
sembrado una sola vez en la tabla `secretarias_transito`): trae, para cada
una, el correo de notificación investigado, un correo alternativo, y un
nivel de confianza (`alta` / `media` / `baja` / `no_encontrado`). De las
37, alrededor de 10 quedan marcadas `requiere_verificacion_manual` porque
no se pudo confirmar el correo con certeza — los correos de entidades
públicas municipales cambian con cada administración, así que este
catálogo es un punto de partida, no una fuente de verdad definitiva.

**Salvaguardas** (`app/services/peticion.py`), para no enviar a ciegas:

1. **Bloqueo por correo no verificado**: si la secretaría destinataria
   está marcada `requiere_verificacion_manual`, el envío NO sale solo; el
   documento se genera pero queda en `bloqueado_verificacion` hasta que
   alguien del equipo jurídico confirme el correo (por teléfono o en el
   sitio oficial) y lo corrija vía `PUT /api/admin/secretarias-transito/<id>/correo`.
2. **Circuit breaker manual**: `POST /api/admin/envio-peticiones/pausar`
   detiene todo envío automático de un clic (útil si algo se ve mal a
   mitad de campaña); `/reanudar` lo reactiva.
3. **Revisión manual de las primeras N**: variable de entorno
   `REVISION_MANUAL_PRIMERAS_N` (0 = desactivada) — si está activa, los
   primeros N derechos de petición de la campaña quedan en
   `en_revision_manual` para que un paralegal los revise antes de abrir
   el envío automático al resto.

**Advertencia de escala** (ver comentario en `app/services/notify.py`):
enviar miles de derechos de petición por el buzón personal del abogado
(Gmail/Outlook normal) choca con los límites de envío de esos proveedores
y puede marcar la cuenta como spam a mitad de campaña. La forma correcta
de que el correo "salga del abogado" sin perder capacidad de envío es
autenticar el dominio propio del abogado (SPF + DKIM + DMARC) en un relay
transaccional (Amazon SES, SendGrid, Postmark), no depender de un solo
buzón personal.

## Próximos pasos (integraciones reales — requieren credenciales)

Igual que en el prototipo de referencia, lo siguiente queda pendiente
porque depende de credenciales/infraestructura que aún no existen:

1. **Verificación de identidad real**: reemplazar `MockIdentityProvider`
   (`app/services/identity.py`) por Truora, MetaMap o validación directa
   contra la Registraduría Nacional.
2. **WhatsApp y correo real**: reemplazar los stubs en
   `app/services/notify.py` y `app/services/remision.py` por Twilio
   WhatsApp Business API (o Meta Cloud API) y SendGrid/SES. Las funciones
   ya están aisladas detrás de una interfaz para que el resto del sistema
   no cambie — solo hay que quitar el `if MOCK_MODE` y completar el bloque
   comentado de cada función.
3. **Colas asíncronas**: mover la verificación de identidad y el envío de
   notificaciones a tareas en segundo plano (Celery + Redis o similar),
   para no bloquear la respuesta HTTP y poder absorber picos de miles de
   invitaciones simultáneas.
4. **Base de datos de producción**: exportar
   `DATABASE_URL=postgresql://...` (requiere `psycopg2-binary` o
   `asyncpg`) — el código no necesita cambios, ya usa SQLAlchemy.
5. **Almacenamiento**: fotos y PDFs a un bucket S3-compatible cifrado en
   reposo, con políticas de retención acordes a la Ley 1581 de 2012.
6. **Carga masiva e invitaciones**: un job que toma el listado de posibles
   afectados (CSV del abogado) y crea un `participante` + token único por
   persona, y despacha el enlace por WhatsApp Business API en lote.
7. **Panel de seguimiento**: vista para el equipo jurídico con el estado de
   cada participante (invitado / en proceso / firmado / remitido /
   pendiente manual) y exportación de los poderes firmados en lote para
   anexar a la demanda.
8. **Remisión certificada real**: conectar `/webhooks/whatsapp/boton` al
   webhook real de Meta Cloud API / Twilio (mensajes interactivos con
   botón), y `/webhooks/email/inbound` a un servicio de correo entrante
   (SendGrid Inbound Parse o Amazon SES + S3). Agregar un job programado
   que dispare automáticamente el fallback a la opción 3 cuando la opción
   1 no se confirme dentro de una ventana de espera (ej. 15 minutos), y a
   la opción 2 cuando la 3 tampoco se confirme.

Ver el documento de metodología adjunto (referenciado en el README del
prototipo) para el marco legal, el análisis de riesgos y el plan de
implementación por fases.
