"""
Catálogo semilla de los 37 organismos de tránsito que operaron el SAST
(fotodetección) según el listado suministrado por el socio (Sanciones_SAST1.pdf,
fuente Ministerio de Transporte / Supertransporte), con el correo de
notificación/PQRSD más confiable que se pudo verificar para cada uno
mediante investigación web dirigida (agosto de 2026).

*** ADVERTENCIA IMPORTANTE — LEER ANTES DE USAR EN PRODUCCIÓN ***
Este catálogo es un PUNTO DE PARTIDA, no una fuente de verdad definitiva.
De las 37 entidades, ~10 quedaron con confianza "baja" o sin correo
verificado (ver `requiere_verificacion_manual=True`). Para esas, el
orquestador de envío (`app/services/peticion.py`) BLOQUEA el envío
automático y dejar el derecho de petición en estado
`bloqueado_verificacion` hasta que alguien del equipo jurídico confirme
el correo (por teléfono o en el sitio oficial) y lo actualice aquí o en
la tabla `secretarias_transito` de la base de datos (se siembra desde
este archivo solo si la tabla está vacía; después de la siembra, edítese
en la base de datos para no perder los cambios cada vez que se reinicie
el servicio).

Los correos electrónicos de entidades públicas municipales cambian con
frecuencia (cada nueva administración, cada 4 años; la próxima empieza en
enero de 2028) — se recomienda una revisión periódica de este catálogo,
no solo al lanzar la plataforma.
"""

# confianza: "alta" | "media" | "baja" | "no_encontrado"
SECRETARIAS_TRANSITO = [
    {"id": 1, "nombre": "Secretaría de Movilidad de Medellín",
     "correo_notificacion": "atencion.ciudadana@medellin.gov.co",
     "correo_alternativo": "notimedellin.oralidad@medellin.gov.co",
     "confianza": "media", "requiere_verificacion_manual": False,
     "fuente": "https://www.medellin.gov.co/es/secretaria-de-movilidad/conectate-con-la-secretaria/",
     "nota": "Correo compartido de Atención Ciudadana del Distrito, no exclusivo de Movilidad."},

    {"id": 2, "nombre": "División de Tránsito y Transporte de La Dorada",
     "correo_notificacion": "tyt@ladorada-caldas.gov.co",
     "correo_alternativo": None,
     "confianza": "media", "requiere_verificacion_manual": True,
     "fuente": "Directorio FCM 2021 (no confirmado en el sitio oficial, portal no accesible por scraping)",
     "nota": "Verificar telefónicamente antes de usar."},

    {"id": 3, "nombre": "Inspección Municipal de Tránsito de Villavicencio",
     "correo_notificacion": "movilidad@villavicencio.gov.co",
     "correo_alternativo": "correspondencia@villavicencio.gov.co",
     "confianza": "alta", "requiere_verificacion_manual": False,
     "fuente": "https://villavicencio.gov.co/alcaldia/directorio-institucional/",
     "nota": ""},

    {"id": 4, "nombre": "Secretaría de Movilidad de Santiago de Cali",
     "correo_notificacion": "secretario.transito@cali.gov.co",
     "correo_alternativo": None,
     "confianza": "media", "requiere_verificacion_manual": False,
     "fuente": "https://www.cali.gov.co/directorio/21/secretaria-de-movilidad/",
     "nota": "No se confirmó si existe un buzón judicial separado."},

    {"id": 5, "nombre": "Secretaría Distrital de Movilidad de Bogotá",
     "correo_notificacion": "judicial@movilidadbogota.gov.co",
     "correo_alternativo": "radicacionentidades@movilidadbogota.gov.co",
     "confianza": "alta", "requiere_verificacion_manual": False,
     "fuente": "https://www.movilidadbogota.gov.co/preguntas-frecuentes/cuales-son-los-medios-habilitados-por-la-secretaria-de-movilidad-para-radicar",
     "nota": ""},

    {"id": 6, "nombre": "Secretaría Distrital de Tránsito y Seguridad Vial de Barranquilla",
     "correo_notificacion": "notijudiciales@barranquilla.gov.co",
     "correo_alternativo": "atencionalciudadano@barranquilla.gov.co",
     "confianza": "alta", "requiere_verificacion_manual": False,
     "fuente": "https://barranquilla.gov.co/transito",
     "nota": ""},

    {"id": 7, "nombre": "Instituto Municipal de Tránsito y Transporte de Corozal",
     "correo_notificacion": None,
     "correo_alternativo": "transitodecorozalsucre@hotmail.com",
     "confianza": "no_encontrado", "requiere_verificacion_manual": True,
     "fuente": "Directorio FCM 2021 (sitio oficial con bucle de redirección, no verificado)",
     "nota": "Único dato disponible es un correo de Hotmail; verificar por PQRSD web o teléfono."},

    {"id": 8, "nombre": "Departamento Administrativo de Transporte y Tránsito de Villa del Rosario",
     "correo_notificacion": "datrans@datransvilladelrosario.gov.co",
     "correo_alternativo": None,
     "confianza": "alta", "requiere_verificacion_manual": False,
     "fuente": "https://www.datransvilladelrosario.gov.co/correo-electronico-para-notificaciones-judiciales/",
     "nota": ""},

    {"id": 9, "nombre": "Secretaría de Movilidad de Itagüí",
     "correo_notificacion": "contactenos@itagui.gov.co",
     "correo_alternativo": "notificaciones@itagui.gov.co",
     "confianza": "media", "requiere_verificacion_manual": False,
     "fuente": "https://itagui.gov.co/transparencia/dependencia/15",
     "nota": "Correo institucional general, no exclusivo de Movilidad."},

    {"id": 10, "nombre": "Secretaría de Movilidad y Tránsito de Sabaneta",
     "correo_notificacion": "secre.transito@sabaneta.gov.co",
     "correo_alternativo": "notificacionesjudiciales@sabaneta.gov.co",
     "confianza": "media", "requiere_verificacion_manual": True,
     "fuente": "Directorio EAPSA 2024 (no confirmado en sabaneta.gov.co)",
     "nota": "Verificar telefónicamente antes de usar."},

    {"id": 11, "nombre": "Oficina de Tránsito y Transporte Departamental del Magdalena",
     "correo_notificacion": None,
     "correo_alternativo": None,
     "confianza": "no_encontrado", "requiere_verificacion_manual": True,
     "fuente": "https://transitodelmagdalena.com/ (solo teléfonos publicados)",
     "nota": "No se encontró correo oficial; usar el formulario web o gestionar por teléfono."},

    {"id": 12, "nombre": "Secretaría de Movilidad de Bello",
     "correo_notificacion": "contactenos@bello.gov.co",
     "correo_alternativo": "notificacionesjudici@bello.gov.co",
     "confianza": "media", "requiere_verificacion_manual": False,
     "fuente": "https://www.supertransporte.gov.co/documentos/2022/Octubre/Atencionciudadano_10/20225350481421.pdf",
     "nota": "Correo institucional general de la Alcaldía, registrado ante Supertransporte para esta secretaría."},

    {"id": 13, "nombre": "Secretaría Municipal de Tránsito y Transporte de Galapa",
     "correo_notificacion": "juridicatransito@galapa-atlantico.gov.co",
     "correo_alternativo": "transito@galapa-atlantico.gov.co",
     "confianza": "alta", "requiere_verificacion_manual": False,
     "fuente": "https://www.galapa-atlantico.gov.co/secretariaTransito/Paginas/inicio.aspx",
     "nota": ""},

    {"id": 14, "nombre": "Instituto de Tránsito del Atlántico",
     "correo_notificacion": "juridica2@transitodelatlantico.gov.co",
     "correo_alternativo": None,
     "confianza": "alta", "requiere_verificacion_manual": False,
     "fuente": "https://transitodelatlantico.gov.co/contacto/",
     "nota": "Etiquetado oficialmente como correo de notificaciones judiciales."},

    {"id": 15, "nombre": "Secretaría Municipal de Tránsito y Transporte de Puerto Colombia",
     "correo_notificacion": "transito@puertocolombia-atlantico.gov.co",
     "correo_alternativo": "notificacionesjudiciales@puertocolombia-atlantico.gov.co",
     "confianza": "alta", "requiere_verificacion_manual": False,
     "fuente": "https://www.puertocolombia-atlantico.gov.co/transito/",
     "nota": ""},

    {"id": 16, "nombre": "Secretaría Municipal de Transporte y Tránsito de Arjona",
     "correo_notificacion": "pqr@transitoarjona.com",
     "correo_alternativo": None,
     "confianza": "alta", "requiere_verificacion_manual": False,
     "fuente": "https://transitoarjona.com/peticiones-quejas-y-reclamos/",
     "nota": "Usar 'Nueva PQR' como asunto, según indicación de la propia entidad."},

    {"id": 17, "nombre": "Secretaría de Tránsito y Transporte Municipal de Turbaco",
     "correo_notificacion": "info@transitoturbaco.gov.co",
     "correo_alternativo": "notificacionesjudiciales@turbaco-bolivar.gov.co",
     "confianza": "media", "requiere_verificacion_manual": False,
     "fuente": "https://transitoturbaco.gov.co/notificaciones",
     "nota": ""},

    {"id": 18, "nombre": "Instituto Municipal de Tránsito y Transporte de Soledad",
     "correo_notificacion": "tramitescomercial@transitosoledad.gov.co",
     "correo_alternativo": None,
     "confianza": "baja", "requiere_verificacion_manual": True,
     "fuente": "Protocolo de atención al público, transitosoledad.gov.co",
     "nota": "Orientado a trámites comerciales, no confirmado como canal de PQRSD/notificaciones."},

    {"id": 19, "nombre": "Secretaría de Tránsito y Transporte de la Alcaldía de San José de Cúcuta",
     "correo_notificacion": "secretaria.transito@cucuta.gov.co",
     "correo_alternativo": "notificaciones_judiciales@cucuta.gov.co",
     "confianza": "alta", "requiere_verificacion_manual": False,
     "fuente": "https://cucuta.gov.co/wp-content/uploads/2024/11/DIRECTORIO-INSTITUCIONAL-ALCALDIA-1.pdf",
     "nota": ""},

    {"id": 20, "nombre": "Secretaría de Movilidad de Cundinamarca",
     "correo_notificacion": None,
     "correo_alternativo": None,
     "confianza": "no_encontrado", "requiere_verificacion_manual": True,
     "fuente": "https://www.cundinamarca.gov.co/dependencias/secmovilidad/servicios-al-ciudadano/pqrsdf",
     "nota": "Solo reciben por formulario web PQRSDF departamental, no correo publicado."},

    {"id": 21, "nombre": "Organismo de Tránsito Municipal de Palermo",
     "correo_notificacion": None,
     "correo_alternativo": "contactenos@palermo-huila.gov.co",
     "confianza": "no_encontrado", "requiere_verificacion_manual": True,
     "fuente": "https://www.palermo-huila.gov.co/Ciudadanos/Paginas/PQRD-Identificacion.aspx",
     "nota": "El único correo de tránsito hallado es de Hotmail y de fuente no oficial; usar el de la Alcaldía con precaución (no es específico de tránsito)."},

    {"id": 22, "nombre": "Instituto Municipal de Tránsito y Transporte de Fundación (INTRASFUN)",
     "correo_notificacion": "atencionalciudadano@intrasfun.gov.co",
     "correo_alternativo": None,
     "confianza": "alta", "requiere_verificacion_manual": False,
     "fuente": "http://www.intrasfun.gov.co/",
     "nota": ""},

    {"id": 23, "nombre": "Instituto de Tránsito y Transporte del Municipio de Los Patios",
     "correo_notificacion": "direccion@transitolospatios.gov.co",
     "correo_alternativo": None,
     "confianza": "media", "requiere_verificacion_manual": False,
     "fuente": "Citado en fallos de tutela de la Rama Judicial",
     "nota": ""},

    {"id": 24, "nombre": "Secretaría de Movilidad y Transporte de Cartago",
     "correo_notificacion": "transito@cartago.gov.co",
     "correo_alternativo": None,
     "confianza": "alta", "requiere_verificacion_manual": False,
     "fuente": "https://www.cartago.gov.co/secretaria/secretaria-de-movilidad-y-transporte",
     "nota": ""},

    {"id": 25, "nombre": "Secretaría de Tránsito y Transporte de Yumbo",
     "correo_notificacion": "stransito@yumbo.gov.co",
     "correo_alternativo": "judicial@yumbo.gov.co",
     "confianza": "alta", "requiere_verificacion_manual": False,
     "fuente": "https://www.yumbo.gov.co/publicaciones/130/secretaria-de-movilidad/",
     "nota": ""},

    {"id": 26, "nombre": "Secretaría de Tránsito, Transporte y Movilidad del Municipio de Yotoco",
     "correo_notificacion": "secretariadetransito@yotocovalle.gov.co",
     "correo_alternativo": "contactenos@yotoco-valle.gov.co",
     "confianza": "baja", "requiere_verificacion_manual": True,
     "fuente": "Directorio Gobernación del Valle del Cauca",
     "nota": "El dominio del correo difiere del dominio oficial vigente del municipio; verificar."},

    {"id": 27, "nombre": "Instituto de Tránsito y Transporte Municipal de Ciénaga",
     "correo_notificacion": "intracienaga@cienaga-magdalena.gov.co",
     "correo_alternativo": None,
     "confianza": "baja", "requiere_verificacion_manual": True,
     "fuente": "Directorio FCM 2021",
     "nota": "No verificado en sitio oficial; el directorio también lista un correo Hotmail alterno."},

    {"id": 28, "nombre": "Inspección de Tránsito y Transporte de Barrancabermeja",
     "correo_notificacion": "cguzman@transitobarrancabermeja.gov.co",
     "correo_alternativo": "contactenos@barrancabermeja.gov.co",
     "confianza": "media", "requiere_verificacion_manual": True,
     "fuente": "https://www.barrancabermeja.gov.co/publicaciones/140/inspeccion-de-transito-y-transporte-de-barrancabermeja-ittb/",
     "nota": "Correo de un funcionario específico (cambia con el titular del cargo), no un buzón institucional."},

    {"id": 29, "nombre": "Secretaría de Movilidad Multimodal y Sostenible de Santa Marta",
     "correo_notificacion": "notificacionesjudiciales@santamarta.gov.co",
     "correo_alternativo": "atencionalciudadano@santamarta.gov.co",
     "confianza": "media", "requiere_verificacion_manual": False,
     "fuente": "https://www.santamarta.gov.co/pqrsd",
     "nota": "Correo genérico de notificaciones judiciales del Distrito, no exclusivo de Movilidad."},

    {"id": 30, "nombre": "Secretaría de Tránsito y Transporte Municipal de Popayán",
     "correo_notificacion": "notificacionesjudiciales@popayan.gov.co",
     "correo_alternativo": "secretariatransito@popayan.gov.co",
     "confianza": "alta", "requiere_verificacion_manual": False,
     "fuente": "https://www.popayan.gov.co/Ciudadanos/Paginas/Correo-electronico-para-notificaciones-judiciales.aspx",
     "nota": ""},

    {"id": 31, "nombre": "Instituto Municipal de Tránsito y Transporte de Aguachica",
     "correo_notificacion": "direcciondetransito@aguachica-cesar.gov.co",
     "correo_alternativo": None,
     "confianza": "media", "requiere_verificacion_manual": True,
     "fuente": "Informe PQRS 2016 del Instituto + directorio FCM 2021",
     "nota": "Fuente principal data de 2016; confirmar vigencia telefónicamente."},

    {"id": 32, "nombre": "Secretaría Municipal de Transporte y Tránsito de Montería",
     "correo_notificacion": "ajuridico@monteria.gov.co",
     "correo_alternativo": "atencionalciudadano@monteria.gov.co",
     "confianza": "media", "requiere_verificacion_manual": False,
     "fuente": "https://www.monteria.gov.co/publicaciones/52/notificaciones-judiciales/",
     "nota": "Correo jurídico general de la Alcaldía, no exclusivo de Tránsito."},

    {"id": 33, "nombre": "Secretaría de Transporte y Tránsito del Municipio de Planeta Rica",
     "correo_notificacion": None,
     "correo_alternativo": None,
     "confianza": "no_encontrado", "requiere_verificacion_manual": True,
     "fuente": "Directorio FCM 2021 (no confirmado en sitio oficial)",
     "nota": "Verificar telefónicamente (tel. 7768790 según directorio) antes de usar."},

    {"id": 34, "nombre": "Secretaría de Tránsito y Transporte de Palmira",
     "correo_notificacion": "notificaciones.judiciales@palmira.gov.co",
     "correo_alternativo": "atencionalciudadano@palmira.gov.co",
     "confianza": "alta", "requiere_verificacion_manual": False,
     "fuente": "https://www.palmira.gov.co/tramitespalmira/",
     "nota": ""},

    {"id": 35, "nombre": "Secretaría de Tránsito y Transporte Municipal de Santander de Quilichao",
     "correo_notificacion": None,
     "correo_alternativo": "ventanillaunica@santanderdequilichao-cauca.gov.co",
     "confianza": "no_encontrado", "requiere_verificacion_manual": True,
     "fuente": "Directorio Gobernación del Cauca",
     "nota": "Página oficial de notificaciones judiciales bloqueada para verificación automatizada; acceder manualmente."},

    {"id": 36, "nombre": "Secretaría de Movilidad y Transporte del Valle del Cauca",
     "correo_notificacion": "njudiciales@valledelcauca.gov.co",
     "correo_alternativo": "contactenos@valledelcauca.gov.co",
     "confianza": "alta", "requiere_verificacion_manual": False,
     "fuente": "https://www.valledelcauca.gov.co/documentos/10756/secretaria-de-movilidad-y-transporte/",
     "nota": ""},

    {"id": 37, "nombre": "Secretaría de Transporte y Movilidad de Zipaquirá",
     "correo_notificacion": "notificacionesjudiciales@transitozipaquira.com",
     "correo_alternativo": "derechosdepeticion@transitozipaquira.com",
     "confianza": "media", "requiere_verificacion_manual": False,
     "fuente": "https://transitozipaquira.com/WordPress/index.php/contactenos/",
     "nota": "Dominio del operador vinculado (Tránsito Zipaquirá S.E.M.), no se confirmó correo en el dominio .gov.co directo."},
]
