import logging

import requests
from django.conf import settings
from django.utils.dateparse import parse_datetime

logger = logging.getLogger(__name__)


# ─── Paleta de colores ────────────────────────────────────────────────────────
COLOR_PRIMARY   = "#1a73e8"   # Azul corporativo
COLOR_SUCCESS   = "#28a745"   # Verde (orden finalizada)
COLOR_DARK      = "#2c3e50"   # Encabezado oscuro
COLOR_LIGHT_BG  = "#f4f6f9"   # Fondo general
COLOR_CARD      = "#ffffff"   # Tarjeta blanca
COLOR_BORDER    = "#e0e6ed"   # Bordes suaves
COLOR_TEXT      = "#333333"
COLOR_MUTED     = "#6c757d"


# ─── Plantilla base HTML ──────────────────────────────────────────────────────
def _base_html(titulo: str, accent: str, contenido: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>{titulo}</title>
</head>
<body style="margin:0;padding:0;background-color:{COLOR_LIGHT_BG};font-family:'Segoe UI',Arial,sans-serif;">

  <!-- Wrapper -->
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
         style="background-color:{COLOR_LIGHT_BG};padding:30px 0;">
    <tr>
      <td align="center">

        <!-- Card principal -->
        <table role="presentation" width="600" cellpadding="0" cellspacing="0"
               style="max-width:600px;width:100%;background:{COLOR_CARD};
                      border-radius:10px;overflow:hidden;
                      box-shadow:0 4px 16px rgba(0,0,0,0.10);">

          <!-- Encabezado con banda de color -->
          <tr>
            <td style="background:{accent};padding:28px 36px;">
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td>
                    <p style="margin:0;font-size:22px;font-weight:700;color:#ffffff;
                               letter-spacing:0.5px;">🔧 CarServ Taller</p>
                    <p style="margin:4px 0 0;font-size:13px;color:rgba(255,255,255,0.80);">
                      Servicio automotriz de confianza
                    </p>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Cuerpo del mensaje -->
          <tr>
            <td style="padding:32px 36px;color:{COLOR_TEXT};font-size:15px;line-height:1.7;">
              {contenido}
            </td>
          </tr>

          <!-- Pie de página -->
          <tr>
            <td style="background:{COLOR_LIGHT_BG};padding:18px 36px;
                       border-top:1px solid {COLOR_BORDER};text-align:center;">
              <p style="margin:0;font-size:12px;color:{COLOR_MUTED};">
                Este es un mensaje automático, por favor no responda a este correo.<br/>
                © 2025 CarServ Taller · Todos los derechos reservados
              </p>
            </td>
          </tr>

        </table>
        <!-- /Card -->

      </td>
    </tr>
  </table>

</body>
</html>"""


# ─── Fila de detalle (clave / valor) ─────────────────────────────────────────
def _fila(icono: str, etiqueta: str, valor: str) -> str:
    return f"""
      <tr>
        <td style="padding:8px 12px;color:{COLOR_MUTED};font-size:13px;
                   white-space:nowrap;border-bottom:1px solid {COLOR_BORDER};">
          {icono} &nbsp;{etiqueta}
        </td>
        <td style="padding:8px 12px;font-size:14px;font-weight:600;
                   color:{COLOR_TEXT};border-bottom:1px solid {COLOR_BORDER};">
          {valor}
        </td>
      </tr>"""


# ─── Tabla de detalles del vehículo / orden ──────────────────────────────────
def _tabla_detalles(filas_html: str) -> str:
    return f"""
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
           style="border:1px solid {COLOR_BORDER};border-radius:8px;
                  overflow:hidden;margin:20px 0;font-family:'Segoe UI',Arial,sans-serif;">
      {filas_html}
    </table>"""


# ─── Botón de llamada a la acción ─────────────────────────────────────────────
def _boton(texto: str, href: str = "#", color: str = COLOR_PRIMARY) -> str:
    return f"""
    <div style="text-align:center;margin:24px 0;">
      <a href="{href}"
         style="display:inline-block;padding:12px 32px;background:{color};
                color:#ffffff;text-decoration:none;font-size:15px;font-weight:600;
                border-radius:6px;letter-spacing:0.3px;">
        {texto}
      </a>
    </div>"""


# ─── Alerta / badge de estado ────────────────────────────────────────────────
def _badge_estado(estado: str, color: str) -> str:
    return f"""
    <p style="display:inline-block;margin:0 0 18px;padding:4px 14px;
              background:{color}1a;border:1px solid {color};
              border-radius:20px;font-size:12px;font-weight:700;
              color:{color};letter-spacing:0.5px;">
      ● &nbsp;{estado.upper()}
    </p>"""


# ─── Mensaje de bienvenida / aviso ───────────────────────────────────────────
def _saludo(nombre: str, mensaje: str) -> str:
    return f"""
    <p style="margin:0 0 6px;font-size:16px;">Hola, <strong>{nombre}</strong> 👋</p>
    <p style="margin:0 0 20px;color:{COLOR_MUTED};font-size:14px;">{mensaje}</p>"""


# ═══════════════════════════════════════════════════════════════════════════════
# CUERPOS DE CADA EVENTO
# ═══════════════════════════════════════════════════════════════════════════════

def _formatear_fecha(fecha, formato: str, fallback: str = "–") -> str:
    if not fecha:
        return fallback

    if hasattr(fecha, 'strftime'):
        return fecha.strftime(formato)

    if isinstance(fecha, str):
        fecha_parseada = parse_datetime(fecha)
        if fecha_parseada:
            return fecha_parseada.strftime(formato)
        return fecha

    return str(fecha)


def _formatear_kilometraje(kilometraje, fallback: str = "–") -> str:
    if kilometraje in (None, '', False):
        return fallback

    try:
        numero = int(kilometraje)
    except (TypeError, ValueError):
        try:
            texto = str(kilometraje).strip().replace('.', '').replace(',', '')
            numero = int(texto)
        except (TypeError, ValueError):
            return str(kilometraje)

    return f"{numero:,} km"


def _html_creada_cliente(orden) -> str:
    cliente = orden.vehiculo.cliente
    vehiculo = orden.vehiculo
    fecha = _formatear_fecha(orden.fecha_ingreso, "%d/%m/%Y %H:%M")
    estimada = _formatear_fecha(orden.fecha_estimada_entrega, "%d/%m/%Y", "Por confirmar")
    km = _formatear_kilometraje(orden.kilometraje_ingreso)

    filas = (
        _fila("📋", "N° de orden",    f"OT-{orden.numero}") +
        _fila("🚗", "Vehículo",       f"{vehiculo.marca} {vehiculo.modelo} {vehiculo.anio}") +
        _fila("🔖", "Placa",          vehiculo.placa.upper()) +
        _fila("📅", "Fecha ingreso",  fecha) +
        _fila("🏁", "Entrega estimada", estimada) +
        _fila("⚙️", "Km al ingreso",  km) +
        _fila("🔍", "Problema reportado", orden.descripcion)
    )

    contenido = (
        _badge_estado("Recibido", COLOR_PRIMARY) +
        _saludo(
            f"{cliente.nombre} {cliente.apellido}",
            "Tu vehículo ha ingresado exitosamente a nuestro taller. "
            "A continuación te mostramos un resumen del ingreso:"
        ) +
        _tabla_detalles(filas) +
        f"""<p style="font-size:14px;color:{COLOR_MUTED};margin:16px 0 0;">
          Nuestro equipo técnico comenzará la revisión pronto.
          Te notificaremos cuando tu unidad esté lista para ser retirada. 🛠️
        </p>"""
    )

    return _base_html("Tu auto ingresó al taller", COLOR_PRIMARY, contenido)


def _html_creada_mecanico(orden) -> str:
    mecanico = orden.mecanico
    vehiculo = orden.vehiculo
    nombre_mec = mecanico.usuario.get_full_name() or mecanico.usuario.username
    fecha = _formatear_fecha(orden.fecha_ingreso, "%d/%m/%Y %H:%M")

    filas = (
        _fila("📋", "N° de orden",   f"OT-{orden.numero}") +
        _fila("🚗", "Vehículo",      f"{vehiculo.marca} {vehiculo.modelo} {vehiculo.anio}") +
        _fila("🔖", "Placa",         vehiculo.placa.upper()) +
        _fila("👤", "Cliente",       f"{vehiculo.cliente.nombre} {vehiculo.cliente.apellido}") +
        _fila("📅", "Fecha ingreso", fecha) +
        _fila("🔧", "Especialidad",  mecanico.get_especialidad_display()) +
        _fila("🔍", "Descripción",   orden.descripcion)
    )

    contenido = (
        _badge_estado("Nueva asignación", COLOR_PRIMARY) +
        _saludo(
            nombre_mec,
            "Se te ha asignado una nueva orden de trabajo. Revisa los detalles a continuación:"
        ) +
        _tabla_detalles(filas) +
        f"""<p style="font-size:14px;color:{COLOR_MUTED};margin:16px 0 0;">
          Ingresa al sistema para ver el historial completo, registrar la inspección inicial
          y actualizar el estado de la orden.
        </p>"""
    )

    return _base_html("Nueva orden asignada", COLOR_PRIMARY, contenido)


def _html_finalizada_cliente(orden) -> str:
    cliente = orden.vehiculo.cliente
    vehiculo = orden.vehiculo
    mano_obra = f"${orden.mano_obra:,.2f}"
    repuestos = f"${orden.total_repuestos:,.2f}"
    total = f"${orden.total:,.2f}"

    filas = (
        _fila("📋", "N° de orden",   f"OT-{orden.numero}") +
        _fila("🚗", "Vehículo",      f"{vehiculo.marca} {vehiculo.modelo} {vehiculo.anio}") +
        _fila("🔖", "Placa",         vehiculo.placa.upper()) +
        _fila("🔧", "Mano de obra",  mano_obra) +
        _fila("🪛",  "Repuestos",    repuestos) +
        _fila("💰", "TOTAL",         total)
    )

    contenido = (
        _badge_estado("Finalizada", COLOR_SUCCESS) +
        _saludo(
            f"{cliente.nombre} {cliente.apellido}",
            "¡Buenas noticias! Tu vehículo ya está listo. Aquí tienes el resumen de la orden:"
        ) +
        _tabla_detalles(filas) +
        f"""<p style="font-size:14px;color:{COLOR_MUTED};margin:16px 0;">
          Puedes pasar a retirar tu vehículo en nuestro horario de atención.
          Si tienes alguna consulta, comunícate con nosotros. 😊
        </p>"""
    )

    return _base_html("Tu orden ha finalizado", COLOR_SUCCESS, contenido)


def _html_finalizada_mecanico(orden) -> str:
    mecanico = orden.mecanico
    nombre_mec = mecanico.usuario.get_full_name() or mecanico.usuario.username
    vehiculo = orden.vehiculo

    filas = (
        _fila("📋", "N° de orden", f"OT-{orden.numero}") +
        _fila("🚗", "Vehículo",    f"{vehiculo.marca} {vehiculo.modelo}") +
        _fila("🔖", "Placa",       vehiculo.placa.upper()) +
        _fila("👤", "Cliente",     f"{vehiculo.cliente.nombre} {vehiculo.cliente.apellido}") +
        _fila("💰", "Total orden", f"${orden.total:,.2f}")
    )

    contenido = (
        _badge_estado("Completada", COLOR_SUCCESS) +
        _saludo(
            nombre_mec,
            "La orden de trabajo ha sido marcada como finalizada correctamente."
        ) +
        _tabla_detalles(filas) +
        f"""<p style="font-size:14px;color:{COLOR_MUTED};margin:16px 0;">
          Verifica que todos los trabajos y repuestos estén correctamente registrados
          en el sistema antes del cierre definitivo.
        </p>"""
    )

    return _base_html("Orden finalizada", COLOR_SUCCESS, contenido)


# ═══════════════════════════════════════════════════════════════════════════════
# FUNCIÓN PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════

def _enviar(
    asunto: str,
    texto_plano: str,
    html: str,
    destinatarios: list[str],
) -> None:
    """Envía un correo mediante la API HTTPS de Brevo."""

    destinatarios_limpios = [
        correo.strip()
        for correo in destinatarios
        if correo and correo.strip()
    ]

    if not destinatarios_limpios:
        logger.warning(
            "No se envió el correo '%s': no hay destinatarios válidos.",
            asunto,
        )
        return

    api_key = getattr(settings, "BREVO_API_KEY", "").strip()
    sender_email = getattr(settings, "BREVO_SENDER_EMAIL", "").strip()
    sender_name = getattr(
        settings,
        "BREVO_SENDER_NAME",
        "CarServ Taller",
    ).strip()

    if not api_key:
        raise RuntimeError(
            "No está configurada la variable BREVO_API_KEY."
        )

    if not sender_email:
        raise RuntimeError(
            "No está configurada la variable BREVO_SENDER_EMAIL."
        )

    payload = {
        "sender": {
            "name": sender_name,
            "email": sender_email,
        },
        "to": [
            {"email": correo}
            for correo in destinatarios_limpios
        ],
        "subject": asunto,
        "textContent": texto_plano,
        "htmlContent": html,
    }

    try:
        response = requests.post(
            "https://api.brevo.com/v3/smtp/email",
            headers={
                "accept": "application/json",
                "api-key": api_key,
                "content-type": "application/json",
            },
            json=payload,
            timeout=30,
        )

        response.raise_for_status()

        datos = response.json()

        logger.info(
            "Correo enviado correctamente: asunto=%s, "
            "destinatarios=%s, messageId=%s",
            asunto,
            destinatarios_limpios,
            datos.get("messageId", "sin messageId"),
        )

    except requests.HTTPError as exc:
        logger.error(
            "Brevo rechazó el correo '%s' para %s. "
            "HTTP %s. Respuesta: %s",
            asunto,
            destinatarios_limpios,
            response.status_code,
            response.text,
            exc_info=True,
        )
        raise

    except requests.RequestException as exc:
        logger.error(
            "No se pudo conectar con Brevo para enviar '%s' a %s: %s",
            asunto,
            destinatarios_limpios,
            exc,
            exc_info=True,
        )
        raise


def enviar_notificaciones_orden(orden, evento: str = 'creada') -> None:
    """Envía correos al cliente y al mecánico según el evento de la orden."""

    # ── Obtener emails ────────────────────────────────────────────────────────
    cliente_email = None
    if orden.vehiculo and orden.vehiculo.cliente:
        c = orden.vehiculo.cliente
        cliente_email = c.email or (
            c.usuario.email if getattr(c, 'usuario', None) else None
        )

    mecanico_email = None
    if orden.mecanico and getattr(orden.mecanico, 'usuario', None):
        mecanico_email = orden.mecanico.usuario.email

    # ── Evento: CREADA ────────────────────────────────────────────────────────
    if evento == 'creada':
        cliente = orden.vehiculo.cliente
        vehiculo = orden.vehiculo

        # --- Cliente ---
        texto_cliente = (
            f"Hola {cliente.nombre} {cliente.apellido},\n\n"
            f"Tu vehículo {vehiculo.marca} {vehiculo.modelo} ({vehiculo.placa}) "
            f"(OT-{orden.numero}) ha ingresado a nuestro taller.\n"
            "Pronto recibirás novedades sobre el estado de tu unidad.\n\n"
            "CarServ Taller"
        )
        _enviar(
            asunto="Tu auto acaba de ingresar a la mecánica",
            texto_plano=texto_cliente,
            html=_html_creada_cliente(orden),
            destinatarios=[cliente_email] if cliente_email else [],
        )

        # --- Mecánico ---
        if orden.mecanico:
            nombre_mec = orden.mecanico.usuario.get_full_name() or orden.mecanico.usuario.username
            texto_mec = (
                f"Hola {nombre_mec},\n\n"
                f"Se te ha asignado la orden OT-{orden.numero} para el vehículo "
                f"{vehiculo.marca} {vehiculo.modelo} ({vehiculo.placa}).\n"
                "Ingresa al sistema para ver los detalles.\n\n"
                "CarServ Taller"
            )
            _enviar(
                asunto=f"Nueva orden asignada – OT-{orden.numero}",
                texto_plano=texto_mec,
                html=_html_creada_mecanico(orden),
                destinatarios=[mecanico_email] if mecanico_email else [],
            )

    # ── Evento: FINALIZADA ────────────────────────────────────────────────────
    elif evento == 'finalizada':
        cliente = orden.vehiculo.cliente

        # --- Cliente ---
        texto_cliente = (
            f"Hola {cliente.nombre} {cliente.apellido},\n\n"
            f"Tu orden OT-{orden.numero} ha finalizado. "
            "Tu vehículo está listo para ser retirado.\n"
            f"Total: ${orden.total:,.2f}\n\n"
            "CarServ Taller"
        )
        _enviar(
            asunto=f"Tu orden ha finalizado – OT-{orden.numero}",
            texto_plano=texto_cliente,
            html=_html_finalizada_cliente(orden),
            destinatarios=[cliente_email] if cliente_email else [],
        )

        # --- Mecánico ---
        if orden.mecanico:
            nombre_mec = orden.mecanico.usuario.get_full_name() or orden.mecanico.usuario.username
            texto_mec = (
                f"Hola {nombre_mec},\n\n"
                f"La orden OT-{orden.numero} ha sido marcada como finalizada.\n"
                "Verifica que todo esté correctamente registrado en el sistema.\n\n"
                "CarServ Taller"
            )
            _enviar(
                asunto=f"Orden finalizada – OT-{orden.numero}",
                texto_plano=texto_mec,
                html=_html_finalizada_mecanico(orden),
                destinatarios=[mecanico_email] if mecanico_email else [],
            )
