"""
Modulo: enviar_correo.py
Ubicacion: Correos/enviar_correo.py

Envia el informe diario en PDF por correo electronico, usando Gmail
como remitente y las credenciales guardadas en el archivo .env
(nunca escritas directamente en el codigo, por seguridad).

Este archivo NO genera el PDF ni hace analisis. Su unica
responsabilidad es enviar archivos por correo.
"""

import smtplib
import ssl
import os
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
from dotenv import load_dotenv

CARPETA_PROYECTO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUTA_ENV = os.path.join(CARPETA_PROYECTO, ".env")

load_dotenv(RUTA_ENV)

SERVIDOR_SMTP_GMAIL = "smtp.gmail.com"
PUERTO_SMTP_GMAIL = 465


def enviar_informe_por_correo(ruta_archivo_pdf, asunto, cuerpo_mensaje):
    """
    Envia un archivo PDF por correo electronico.

    Parametros:
        ruta_archivo_pdf (str): ruta completa del archivo PDF a adjuntar.
        asunto (str): asunto del correo.
        cuerpo_mensaje (str): texto del cuerpo del correo.

    Retorna:
        True si el correo se envio correctamente, False si hubo un error.
    """
    correo_remitente = os.getenv("CORREO_REMITENTE")
    contrasena_app = os.getenv("CORREO_CONTRASENA_APP")
    correo_destino = os.getenv("CORREO_DESTINO")

    if not correo_remitente or not contrasena_app or not correo_destino:
        print("Error: faltan credenciales en el archivo .env (CORREO_REMITENTE, CORREO_CONTRASENA_APP o CORREO_DESTINO).")
        return False

    if not os.path.exists(ruta_archivo_pdf):
        print("Error: no se encontro el archivo a adjuntar: " + ruta_archivo_pdf)
        return False

    mensaje = MIMEMultipart()
    mensaje["From"] = correo_remitente
    mensaje["To"] = correo_destino
    mensaje["Subject"] = asunto

    mensaje.attach(MIMEText(cuerpo_mensaje, "plain"))

    with open(ruta_archivo_pdf, "rb") as archivo:
        adjunto = MIMEBase("application", "octet-stream")
        adjunto.set_payload(archivo.read())

    encoders.encode_base64(adjunto)
    nombre_archivo = os.path.basename(ruta_archivo_pdf)
    adjunto.add_header("Content-Disposition", "attachment; filename=" + nombre_archivo)
    mensaje.attach(adjunto)

    try:
        contexto_seguro = ssl.create_default_context()
        with smtplib.SMTP_SSL(SERVIDOR_SMTP_GMAIL, PUERTO_SMTP_GMAIL, context=contexto_seguro) as servidor:
            servidor.login(correo_remitente, contrasena_app)
            servidor.sendmail(correo_remitente, correo_destino, mensaje.as_string())

        print("Correo enviado exitosamente a " + correo_destino)
        return True

    except Exception as error:
        print("Error al enviar el correo: " + str(error))
        return False


if __name__ == "__main__":
    # Prueba: enviamos el informe diario mas reciente que exista
    # en la carpeta Reportes.
    carpeta_reportes = os.path.join(CARPETA_PROYECTO, "Reportes")
    archivos_pdf = [f for f in os.listdir(carpeta_reportes) if f.endswith(".pdf")]

    if len(archivos_pdf) == 0:
        print("No se encontro ningun informe PDF en la carpeta Reportes para hacer la prueba.")
    else:
        archivos_pdf.sort(reverse=True)
        archivo_mas_reciente = archivos_pdf[0]
        ruta_completa = os.path.join(carpeta_reportes, archivo_mas_reciente)

        print("Enviando informe de prueba: " + archivo_mas_reciente)

        enviar_informe_por_correo(
            ruta_completa,
            "Informe Diario - Precio de Bolsa Nacional (Prueba)",
            "Adjunto encontraras el informe diario del Precio de Bolsa Nacional.\n\nEste es un correo de prueba del sistema."
        )
