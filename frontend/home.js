// Menú móvil (hamburguesa) + resaltar el enlace de la sección visible.

const navLinks = document.getElementById("dia-nav-links");
const navToggle = document.getElementById("dia-nav-toggle");

navToggle.addEventListener("click", () => {
  navLinks.classList.toggle("abierto");
});

navLinks.querySelectorAll("a").forEach((a) => {
  a.addEventListener("click", () => navLinks.classList.remove("abierto"));
});

const secciones = ["inicio", "nosotros", "servicios", "contacto"]
  .map((id) => document.getElementById(id))
  .filter(Boolean);

function resaltarSeccionVisible() {
  const scrollY = window.scrollY + 120;
  let actual = secciones[0];
  for (const sec of secciones) {
    if (sec.offsetTop <= scrollY) actual = sec;
  }
  navLinks.querySelectorAll("a").forEach((a) => {
    a.classList.toggle("activo", a.getAttribute("href") === `#${actual.id}`);
  });
}

window.addEventListener("scroll", resaltarSeccionVisible);
resaltarSeccionVisible();

// ---------------------------------------------------------------------
// Panel "HABLEMOS": notificación tipo chat con un menú de temas. Según
// lo que la persona necesite, muestra el contacto que le puede ayudar.
// Reemplaza cada "(pendiente)" por el teléfono/correo real del área
// correspondiente cuando estén definidos.
// ---------------------------------------------------------------------

const CONTACTOS_POR_TEMA = [
  {
    id: "caso",
    pregunta: "Estado de mi acción de grupo / mi caso",
    telefono: "(pendiente)",
    correo: "(pendiente)",
  },
  {
    id: "firma",
    pregunta: "Firma de documentos y del poder",
    telefono: "(pendiente)",
    correo: "(pendiente)",
  },
  {
    id: "honorarios",
    pregunta: "Honorarios y pagos",
    telefono: "(pendiente)",
    correo: "(pendiente)",
  },
  {
    id: "otro",
    pregunta: "Otra consulta",
    telefono: "(pendiente)",
    correo: "(pendiente)",
  },
];

const panelHablemos = document.getElementById("panel-hablemos");
const panelHablemosBody = document.getElementById("panel-hablemos-body");
const btnHablemos = document.getElementById("btn-hablemos");
const cerrarHablemos = document.getElementById("cerrar-hablemos");

function renderMenuHablemos() {
  panelHablemosBody.innerHTML = `
    <p class="panel-hablemos-intro">Cuéntanos qué necesitas y te decimos con quién hablar:</p>
    ${CONTACTOS_POR_TEMA.map(
      (t) => `<button type="button" class="panel-hablemos-opcion" data-tema="${t.id}">${t.pregunta}</button>`
    ).join("")}
  `;
  panelHablemosBody.querySelectorAll(".panel-hablemos-opcion").forEach((boton) => {
    boton.addEventListener("click", () => renderContactoHablemos(boton.dataset.tema));
  });
}

function renderContactoHablemos(temaId) {
  const tema = CONTACTOS_POR_TEMA.find((t) => t.id === temaId);
  if (!tema) return;
  panelHablemosBody.innerHTML = `
    <button type="button" class="panel-hablemos-volver">← Ver otro tema</button>
    <div class="panel-hablemos-contacto">
      <p><strong>${tema.pregunta}</strong></p>
      <p>📞 Teléfono: <span class="pendiente">${tema.telefono}</span></p>
      <p>✉️ Correo: <span class="pendiente">${tema.correo}</span></p>
    </div>
  `;
  panelHablemosBody.querySelector(".panel-hablemos-volver").addEventListener("click", renderMenuHablemos);
}

btnHablemos.addEventListener("click", () => {
  renderMenuHablemos();
  panelHablemos.classList.add("abierto");
});

cerrarHablemos.addEventListener("click", () => {
  panelHablemos.classList.remove("abierto");
});
