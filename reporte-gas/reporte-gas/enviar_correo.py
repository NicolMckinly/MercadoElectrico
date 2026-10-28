# =====================================================================
# enviar_correo.py  —  EL "CARTERO" DEL ROBOT
# ---------------------------------------------------------------------
# Este archivo mete el reporte en un "sobre" (un correo) y lo entrega
# a Gmail para que lo envíe.
#
# ¿De dónde saca la clave? De las "variables de entorno". Son como
# notas adhesivas que el computador le pasa al programa sin escribirlas
# en el código. En GitHub, esas notas salen de la caja fuerte (Secrets).
# Así la clave NUNCA queda escrita en ningún archivo.
#
# Las tres notas que necesita:
#   GMAIL_USUARIO    -> la cuenta de Gmail que ENVÍA (ej. robot@gmail.com)
#   GMAIL_CLAVE_APP  -> la "contraseña de aplicación" de esa cuenta
#   CORREO_DESTINO   -> a quién le llega. Pueden ser varios, separados
#                       por comas: "yo@gmail.com, jefe@empresa.com"
# =====================================================================

import os
import smtplib                                   # el "idioma" que usan los servidores de correo
from email.message import EmailMessage           # para armar el sobre del correo


def datos_de_acceso():
    """Lee las tres notas (variables de entorno). Si falta alguna, devuelve None."""
    usuario = os.environ.get("GMAIL_USUARIO")
    clave = os.environ.get("GMAIL_CLAVE_APP")
    destino = os.environ.get("CORREO_DESTINO")
    if not (usuario and clave and destino):
        return None
    return usuario, clave, destino


def armar_correo(asunto, html, imagenes, remitente, destino, adjunto=None):
    """Arma el correo completo.

    Un correo con imágenes es como un sobre con varias hojas adentro:
      - una hoja de texto simple (para programas de correo muy viejos),
      - una hoja HTML (la bonita, con colores y tabla),
      - las imágenes, cada una con una "etiqueta" (cid) que el HTML usa
        para saber dónde ponerla: <img src="cid:grafica1">.
      - opcional: el reporte como archivo adjunto.
    """
    correo = EmailMessage()
    correo["Subject"] = asunto
    correo["From"] = remitente
    correo["To"] = destino

    correo.set_content("Tu programa de correo no muestra HTML. "
                       "Abre el archivo adjunto para ver el reporte.")
    correo.add_alternative(html, subtype="html")

    # Pegamos cada imagen a la hoja HTML con su etiqueta.
    hoja_html = correo.get_payload()[1]
    for etiqueta, contenido_png in imagenes.items():
        hoja_html.add_related(contenido_png, maintype="image", subtype="png",
                              cid=f"<{etiqueta}>")

    if adjunto:
        with open(adjunto, "rb") as archivo:
            correo.add_attachment(archivo.read(), maintype="text", subtype="html",
                                  filename=os.path.basename(adjunto))
    return correo


def enviar(correo, usuario, clave):
    """Entrega el sobre a Gmail.

    smtp.gmail.com es la "oficina de correos" de Gmail y 465 es la
    ventanilla segura (la conexión va cifrada, nadie puede leerla en el camino).
    """
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as oficina:
        oficina.login(usuario, clave)
        oficina.send_message(correo)
