// En producción (Render, etc.) el frontend se sirve desde el MISMO servicio
// que la API, así que basta con usar rutas relativas ("" = mismo origen).
// Solo cuando abres el archivo directo con doble clic (file://, sin
// servidor) no hay "mismo origen" al que pedirle nada, así que en ese caso
// se usa localhost:8000 — cambia ese valor si tu API corre en otro puerto.
const API_BASE = location.protocol === "file:" ? "http://localhost:8000" : "";

const state = {
  token: null,
  participanteId: null,
  deviceOs: detectarDeviceOs(),
  mailtoRemision: null,
  pollTimer: null,
  secretarias: [], // catálogo de secretarías de tránsito: [{id, nombre}, ...]
};

function detectarDeviceOs() {
  const ua = navigator.userAgent || "";
  if (/android/i.test(ua)) return "android";
  if (/iphone|ipad|ipod/i.test(ua)) return "iOS";
  return "desktop";
}

// Carga el catálogo de las 37 secretarías de tránsito desde la API, para
// poblar el <select> de "organismo de tránsito" en cada fila de comparendo
// (paso 2). Solo se necesita id + nombre; el correo de notificación es un
// dato interno del backend, no se expone aquí.
async function cargarSecretarias() {
  try {
    state.secretarias = await llamar("/api/catalogos/secretarias-transito");
  } catch (err) {
    console.error("No se pudo cargar el catálogo de secretarías de tránsito:", err);
    return;
  }
  // Por si el usuario ya llegó al paso 2 antes de que esta petición terminara
  // (poco probable, pero posible en una red lenta): rellena los <select>
  // que hayan quedado vacíos.
  document.querySelectorAll(".c-secretaria").forEach((select) => {
    if (select.options.length <= 1) {
      select.innerHTML = opcionesSecretarias();
    }
  });
}
cargarSecretarias();

function opcionesSecretarias() {
  return (
    `<option value="">Selecciona uno...</option>` +
    state.secretarias.map((s) => `<option value="${s.id}">${s.nombre}</option>`).join("")
  );
}

// ---------------------------------------------------------------------
// Utilidades de UI
// ---------------------------------------------------------------------

function mostrarAlerta(mensaje, tipo = "error") {
  const el = document.getElementById("alerta");
  el.textContent = mensaje;
  el.className = `alerta ${tipo}`;
  el.scrollIntoView({ behavior: "smooth", block: "center" });
}

function ocultarAlerta() {
  const el = document.getElementById("alerta");
  el.className = "alerta oculto";
}

function irAPaso(numero) {
  document.querySelectorAll(".paso").forEach((sec) => sec.classList.add("oculto"));
  document.getElementById(`paso-${numero}`).classList.remove("oculto");
  document.querySelectorAll(".paso-indicador").forEach((ind) => {
    const n = Number(ind.dataset.paso);
    ind.classList.toggle("completo", n < numero);
    ind.classList.toggle("activo", n === numero);
  });
  ocultarAlerta();
  window.scrollTo({ top: 0, behavior: "smooth" });
}

async function llamar(path, opciones = {}) {
  const resp = await fetch(`${API_BASE}${path}`, {
    headers: opciones.body instanceof FormData ? undefined : { "Content-Type": "application/json" },
    ...opciones,
  });
  let data = null;
  try {
    data = await resp.json();
  } catch (_) {
    // respuesta sin cuerpo (poco común aquí)
  }
  if (!resp.ok) {
    const detalle = (data && (data.error || JSON.stringify(data.detail))) || `Error ${resp.status}`;
    const err = new Error(detalle);
    err.data = data;
    err.status = resp.status;
    throw err;
  }
  return data;
}

// ---------------------------------------------------------------------
// Paso 1: datos básicos
// ---------------------------------------------------------------------

document.getElementById("form-datos").addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = new FormData(e.target);
  const boton = e.target.querySelector("button");
  boton.disabled = true;
  try {
    const creado = await llamar("/api/participantes", {
      method: "POST",
      body: JSON.stringify({
        nombre_completo: form.get("nombre_completo"),
        numero_documento: form.get("numero_documento"),
        email: form.get("email"),
        celular: form.get("celular"),
        origen: "formulario_web",
      }),
    });
    state.token = creado.token;
    state.participanteId = creado.id;

    await llamar(`/api/participantes/${state.token}/datos`, {
      method: "POST",
      body: JSON.stringify({ device_os: state.deviceOs }),
    });

    irAPaso(2);
    if (document.querySelectorAll("#lista-comparendos .comparendo-item").length === 0) {
      agregarFilaComparendo();
    }
  } catch (err) {
    mostrarAlerta(`No se pudo guardar tus datos: ${err.message}`);
  } finally {
    boton.disabled = false;
  }
});

// ---------------------------------------------------------------------
// Paso 2: comparendo(s)
// ---------------------------------------------------------------------

function agregarFilaComparendo() {
  const contenedor = document.getElementById("lista-comparendos");
  const div = document.createElement("div");
  div.className = "comparendo-item";
  div.innerHTML = `
    <div class="fila">
      <label>Número de comparendo
        <input type="text" class="c-numero" required />
      </label>
      <label>Fecha
        <input type="date" class="c-fecha" />
      </label>
    </div>
    <div class="fila">
      <label>Placa
        <input type="text" class="c-placa" required />
      </label>
      <label>Tipo de vehículo
        <input type="text" class="c-tipo" placeholder="Automóvil, moto..." />
      </label>
    </div>
    <label>Organismo de tránsito que impuso el comparendo
      <select class="c-secretaria" required>${opcionesSecretarias()}</select>
    </label>
    <details>
      <summary class="ayuda" style="cursor:pointer">¿El vehículo es de otra persona/empresa?</summary>
      <div class="fila" style="margin-top:0.6rem">
        <label>Nombre del titular
          <input type="text" class="c-titular-nombre" placeholder="(si es distinto a ti)" />
        </label>
        <label>Documento del titular
          <input type="text" class="c-titular-doc" />
        </label>
      </div>
    </details>
    <button type="button" class="btn-quitar">✕ Quitar este comparendo</button>
  `;
  div.querySelector(".btn-quitar").addEventListener("click", () => {
    if (document.querySelectorAll("#lista-comparendos .comparendo-item").length > 1) {
      div.remove();
    } else {
      mostrarAlerta("Debes dejar al menos un comparendo.", "info");
    }
  });
  contenedor.appendChild(div);
}

document.getElementById("btn-agregar-comparendo").addEventListener("click", agregarFilaComparendo);

document.getElementById("btn-continuar-comparendos").addEventListener("click", async (e) => {
  const boton = e.target;
  const filas = document.querySelectorAll("#lista-comparendos .comparendo-item");
  const comparendos = Array.from(filas).map((fila) => ({
    numero_comparendo: fila.querySelector(".c-numero").value.trim(),
    fecha_comparendo: fila.querySelector(".c-fecha").value || null,
    placa: fila.querySelector(".c-placa").value.trim(),
    tipo_vehiculo: fila.querySelector(".c-tipo").value.trim() || null,
    secretaria_transito_id: Number(fila.querySelector(".c-secretaria").value) || null,
    titular_nombre: fila.querySelector(".c-titular-nombre").value.trim() || null,
    titular_documento: fila.querySelector(".c-titular-doc").value.trim() || null,
  }));

  if (comparendos.some((c) => !c.numero_comparendo || !c.placa || !c.secretaria_transito_id)) {
    mostrarAlerta("Cada comparendo necesita al menos número, placa y organismo de tránsito.");
    return;
  }

  boton.disabled = true;
  try {
    const resultado = await llamar(`/api/participantes/${state.token}/comparendos`, {
      method: "POST",
      body: JSON.stringify({ comparendos }),
    });
    if (resultado.errores && resultado.errores.length) {
      mostrarAlerta(`Algunos comparendos no se pudieron guardar (fila ${resultado.errores[0].indice + 1}: ${resultado.errores[0].error})`);
      return;
    }
    irAPaso(3);
  } catch (err) {
    mostrarAlerta(`No se pudieron guardar los comparendos: ${err.message}`);
  } finally {
    boton.disabled = false;
  }
});

// ---------------------------------------------------------------------
// Paso 3: identidad
// ---------------------------------------------------------------------

document.getElementById("form-identidad").addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = new FormData(e.target);
  const boton = e.target.querySelector("button");
  boton.disabled = true;
  try {
    const body = new FormData();
    body.append("foto_cedula", form.get("foto_cedula"));
    body.append("selfie", form.get("selfie"));
    const resultado = await llamar(`/api/participantes/${state.token}/identidad`, {
      method: "POST",
      body,
    });
    if (!resultado.ok) {
      mostrarAlerta("No pudimos verificar tu identidad automáticamente. Intenta con fotos más claras.");
      return;
    }
    await cargarDocumentosParaRevision();
    irAPaso(4);
  } catch (err) {
    mostrarAlerta(`No se pudo verificar tu identidad: ${err.message}`);
  } finally {
    boton.disabled = false;
  }
});

// ---------------------------------------------------------------------
// Paso 4: revisión y aceptación
// ---------------------------------------------------------------------

async function cargarDocumentosParaRevision() {
  await llamar(`/api/participantes/${state.token}/documentos`);
  const base = `${API_BASE}/api/participantes/${state.token}/documentos`;
  document.getElementById("link-poder").href = `${base}/poder_especial/pdf`;
  document.getElementById("link-contrato").href = `${base}/contrato_prestacion_servicios/pdf`;
}

document.getElementById("check-acepto").addEventListener("change", (e) => {
  document.getElementById("btn-aceptar").disabled = !e.target.checked;
});

document.getElementById("btn-aceptar").addEventListener("click", async (e) => {
  const boton = e.target;
  const canal = document.querySelector('input[name="canal"]:checked').value;
  boton.disabled = true;
  try {
    const resultado = await llamar(`/api/participantes/${state.token}/aceptar`, {
      method: "POST",
      body: JSON.stringify({ canal }),
    });
    document.getElementById("texto-otp-canal").textContent =
      resultado.canal === "whatsapp"
        ? "Te enviamos un código de 6 dígitos por WhatsApp."
        : "Te enviamos un código de 6 dígitos por correo.";
    mostrarAlerta(
      "Modo de prueba: el código no llega de verdad — revisa la consola donde corre el servidor (uvicorn), ahí aparece impreso.",
      "info"
    );
    irAPaso(5);
  } catch (err) {
    mostrarAlerta(`No se pudo enviar el código: ${err.message}`);
  } finally {
    boton.disabled = false;
  }
});

// ---------------------------------------------------------------------
// Paso 5: verificar OTP -> firma sellada
// ---------------------------------------------------------------------

document.getElementById("form-otp").addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = new FormData(e.target);
  const boton = e.target.querySelector("button");
  boton.disabled = true;
  try {
    const resultado = await llamar(`/api/participantes/${state.token}/verificar-otp`, {
      method: "POST",
      body: JSON.stringify({ codigo: form.get("codigo") }),
    });
    mostrarResultadoFirma(resultado);
    irAPaso(6);
    await actualizarEstadoRemision();
    iniciarPolling();
  } catch (err) {
    mostrarAlerta(`No se pudo confirmar el código: ${err.message}`);
  } finally {
    boton.disabled = false;
  }
});

const TEXTO_ESTADO_PETICION = {
  enviado: "✅ enviado a la secretaría",
  bloqueado_verificacion: "⏳ pendiente de verificación del correo por el equipo jurídico",
  en_revision_manual: "⏳ en revisión manual antes de enviarse",
  fallido: "⚠️ no se pudo enviar, se reintentará",
};

function mostrarResultadoFirma(resultado) {
  const base = `${API_BASE}/api/participantes/${state.token}/documentos`;
  const el = document.getElementById("resultado-firma");
  const derechos = resultado.derechos_peticion || [];
  const listaDerechos = derechos.length
    ? `<ul>${derechos
        .map((d) => `<li>Derecho de petición: ${TEXTO_ESTADO_PETICION[d.estado_envio] || d.estado_envio}</li>`)
        .join("")}</ul>`
    : "";
  el.innerHTML = `
    <p>Tus documentos quedaron firmados electrónicamente y sellados con hash SHA-256.</p>
    <a href="${base}/poder_especial/pdf" target="_blank" rel="noopener">📄 Descargar poder especial firmado</a>
    <a href="${base}/contrato_prestacion_servicios/pdf" target="_blank" rel="noopener">📄 Descargar contrato firmado</a>
    <p class="hash">Hash poder especial: ${resultado.documentos.poder_especial.hash}</p>
    <p class="hash">Hash contrato: ${resultado.documentos.contrato_prestacion_servicios.hash}</p>
    ${listaDerechos}
  `;
}

// ---------------------------------------------------------------------
// Paso 6: remisión certificada (cascada)
// ---------------------------------------------------------------------

function iniciarPolling() {
  if (state.pollTimer) clearInterval(state.pollTimer);
  state.pollTimer = setInterval(actualizarEstadoRemision, 4000);
}

function detenerPolling() {
  if (state.pollTimer) clearInterval(state.pollTimer);
  state.pollTimer = null;
}

async function actualizarEstadoRemision() {
  try {
    const estado = await llamar(`/api/participantes/${state.token}/remision/estado`);
    renderEstadoRemision(estado);
  } catch (err) {
    // silencioso: el polling no debe llenar la pantalla de errores
    console.error("Error consultando estado de remisión:", err);
  }
}

function renderEstadoRemision(estado) {
  const cajaEstado = document.getElementById("estado-remision");
  const acciones = document.getElementById("acciones-remision");

  if (estado.estado_participante === "remitido") {
    detenerPolling();
    cajaEstado.className = "estado-remision confirmado";
    cajaEstado.textContent = "✅ Remisión confirmada. Tu firma quedó registrada como remitida.";
    acciones.innerHTML = "";
    return;
  }
  if (estado.estado_participante === "remision_pendiente_manual") {
    detenerPolling();
    cajaEstado.className = "estado-remision manual";
    cajaEstado.textContent = "⚠️ No se pudo confirmar automáticamente. El equipo jurídico se pondrá en contacto contigo.";
    acciones.innerHTML = "";
    return;
  }

  const intentoActivo = [...estado.intentos].reverse().find((i) => i.estado === "enviado");
  cajaEstado.className = "estado-remision";

  if (!intentoActivo) {
    cajaEstado.textContent = "Esperando confirmación...";
    acciones.innerHTML = "";
    return;
  }

  if (intentoActivo.canal === "whatsapp_boton") {
    cajaEstado.textContent = "📲 Te enviamos tu poder firmado por WhatsApp con un botón para confirmar.";
    acciones.innerHTML = `
      <button id="btn-simular-whatsapp">Ya toqué el botón en WhatsApp (confirmar)</button>
      <button class="secundario" id="btn-usar-correo">No me llegó / prefiero usar correo</button>
    `;
    document.getElementById("btn-simular-whatsapp").addEventListener("click", (e) => confirmarWhatsapp(e.target));
    document.getElementById("btn-usar-correo").addEventListener("click", (e) => activarFallbackEmail(e.target));
  } else if (intentoActivo.canal === "email_confirmacion") {
    cajaEstado.textContent = "✉️ Te ofrecimos confirmar por correo.";
    const botones = [`<button id="btn-simular-email">Ya envié el correo de confirmación</button>`];
    if (state.mailtoRemision) {
      botones.unshift(`<a class="secundario" style="display:block;text-align:center;padding:0.7rem;border:1px solid var(--azul);border-radius:8px;color:var(--azul);text-decoration:none;" href="${state.mailtoRemision}">Abrir correo prellenado</a>`);
    }
    if (state.deviceOs === "android") {
      botones.push(`<button class="secundario" id="btn-plan-c">No pude enviar el correo, compartir por WhatsApp</button>`);
    }
    acciones.innerHTML = botones.join("");
    document.getElementById("btn-simular-email")?.addEventListener("click", (e) => confirmarEmail(e.target));
    document.getElementById("btn-plan-c")?.addEventListener("click", (e) => activarPlanC(e.target));
  } else if (intentoActivo.canal === "share_android") {
    cajaEstado.textContent = "📤 Comparte el PDF firmado por WhatsApp desde tu celular.";
    acciones.innerHTML = `<button id="btn-compartir">Compartir por WhatsApp</button>`;
    document.getElementById("btn-compartir").addEventListener("click", (e) => compartirPlanC(e.target));
  }
}

async function confirmarWhatsapp(boton) {
  boton.disabled = true;
  try {
    await llamar("/webhooks/whatsapp/boton", {
      method: "POST",
      body: JSON.stringify({ token: state.token }),
    });
    await actualizarEstadoRemision();
  } catch (err) {
    mostrarAlerta(`No se pudo confirmar: ${err.message}`);
  } finally {
    boton.disabled = false;
  }
}

async function activarFallbackEmail(boton) {
  boton.disabled = true;
  try {
    const resultado = await llamar(`/api/participantes/${state.token}/remision/fallback-email`, { method: "POST" });
    state.mailtoRemision = resultado.mailto;
    await actualizarEstadoRemision();
  } catch (err) {
    mostrarAlerta(`No se pudo activar el respaldo por correo: ${err.message}`);
  } finally {
    boton.disabled = false;
  }
}

async function confirmarEmail(boton) {
  boton.disabled = true;
  try {
    await llamar("/webhooks/email/inbound", {
      method: "POST",
      body: JSON.stringify({ token: state.token }),
    });
    await actualizarEstadoRemision();
  } catch (err) {
    mostrarAlerta(`No se pudo confirmar: ${err.message}`);
  } finally {
    boton.disabled = false;
  }
}

async function activarPlanC(boton) {
  boton.disabled = true;
  try {
    await llamar(`/api/participantes/${state.token}/remision/plan-c`, { method: "POST" });
    await actualizarEstadoRemision();
  } catch (err) {
    mostrarAlerta(`Plan C no disponible: ${err.message}`);
  } finally {
    boton.disabled = false;
  }
}

async function compartirPlanC(boton) {
  boton.disabled = true;
  let exito = false;
  try {
    const url = `${API_BASE}/api/participantes/${state.token}/documentos/poder_especial/pdf`;
    const resp = await fetch(url);
    const blob = await resp.blob();
    const archivo = new File([blob], "poder_especial_firmado.pdf", { type: "application/pdf" });

    if (navigator.canShare && navigator.canShare({ files: [archivo] })) {
      await navigator.share({ files: [archivo], title: "Poder especial firmado" });
      exito = true;
    } else {
      mostrarAlerta("Tu navegador no soporta compartir archivos nativamente.", "info");
    }
  } catch (err) {
    exito = false;
  } finally {
    try {
      await llamar(`/api/participantes/${state.token}/remision/plan-c/confirmar`, {
        method: "POST",
        body: JSON.stringify({ exito }),
      });
    } catch (_) {
      // ignorar
    }
    await actualizarEstadoRemision();
    boton.disabled = false;
  }
}
