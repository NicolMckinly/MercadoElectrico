"""
Modulo: enviar_pdd_cero.py
Ubicacion: raiz del repositorio (junto a main_diario.py)

PLANEACION DESPACHO DIARIO (PDD) EN CERO - A PEDIDO

Mientras la planta no tenga gas (por lo menos hasta el 31 de diciembre
de 2026), el PDD de cada dia es siempre igual: 0 kWh en las 24 horas y
"Fuera de linea". Lo unico que cambia es:
    1) la fecha (el dia de manana)
    2) el IMAR de cada periodo (lo publica XM el dia anterior)

Este script:
    - Descarga el IMAR de manana del sitio publico de XM (igual que
      API/imar.py, fila "Costo Marginal", convertido a $/kWh).
    - Arma el cuadro del PDD igualito al del Excel.
    - Lo envia desde Gmail a tu correo corporativo, con un archivo
      adjunto "PDD_....eml" que es el BORRADOR listo: al abrirlo en
      Outlook aparece un correo nuevo con destinatarios, copias,
      asunto y cuadro ya puestos. Solo le das "Enviar" y sale desde
      tu correo corporativo.

No corre solo: se ejecuta desde GitHub con el boton "Run workflow"
(archivo .github/workflows/pdd_cero.yml).

Uso manual:
    python enviar_pdd_cero.py                      -> PDD de manana
    python enviar_pdd_cero.py --fecha 2026-11-14   -> PDD de esa fecha
    python enviar_pdd_cero.py --correo otro@tmmorro.com
"""

import os
import sys
import time
import ssl
import smtplib
import argparse
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage

import requests
from dotenv import load_dotenv

CARPETA_PROYECTO = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(CARPETA_PROYECTO, ".env"))

# ---------------------------------------------------------------------
# CONFIGURACION (lo que se puede cambiar facilmente)
# ---------------------------------------------------------------------

# A quien le llega el correo desde Gmail (tu correo corporativo).
CORREO_PARA_MI = "nicol.leyton@tmmorro.com"

# Destinatarios del borrador que vas a enviar desde Outlook.
PARA = [
    "erik.albarracin@tmmorro.com",
    "edinsson.alarcon@tmmorro.com",
]
CON_COPIA = [
    "albeiro.rengifo@tmmorro.com",
    "fabian.barahona@tmmorro.com",
    "andrea.quintero@tmmorro.com",
]

NOTA_SIN_GAS = ("Para la ejecución del PDD del día de mañana, no se programa la "
                "operación de la planta ya que no se cuenta con el suministro de "
                "gas para generar.")

# Fuente del IMAR (la misma que usa API/imar.py)
URL_XM = "https://api-portalxm.xm.com.co/administracion-archivos/ficheros/mostrar-url"
CONTENEDOR_XM = "storageportalxm"

DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]

ZONA_COLOMBIA = timezone(timedelta(hours=-5))


# ---------------------------------------------------------------------
# 1) TRAER EL IMAR DE XM
# ---------------------------------------------------------------------

def descargar_imar(fecha):
    """
    Devuelve una lista con los 24 valores del IMAR ($/kWh) de la fecha,
    o None si XM todavia no lo ha publicado.
    """
    ruta = ("M:/InformacionAgentes/Usuarios/Publico/PredespachoIdeal/"
            + fecha.strftime("%Y-%m") + "/iMAR" + fecha.strftime("%m%d") + ".txt")
    parametros = {"ruta": ruta, "nombreBlobContainer": CONTENEDOR_XM}

    for intento in range(1, 4):
        try:
            respuesta = requests.get(URL_XM, params=parametros, timeout=30)
            if respuesta.status_code == 200 and "Costo Marginal" in respuesta.text:
                return leer_costo_marginal(respuesta.text)
            if respuesta.status_code == 404:
                return None
            print("Intento " + str(intento) + ": XM respondio codigo " + str(respuesta.status_code))
        except Exception as error:
            print("Intento " + str(intento) + ": error " + str(error))
        time.sleep(5)
    return None


def leer_costo_marginal(texto):
    """Toma la fila "Costo Marginal" y la pasa de $/MWh a $/kWh."""
    for linea in texto.strip().splitlines():
        if linea.startswith('"Costo Marginal"'):
            partes = linea.split(",")[1:25]
            return [float(p.strip()) / 1000 for p in partes]
    return None


# ---------------------------------------------------------------------
# 2) ARMAR EL CUADRO (HTML, como el del Excel)
# ---------------------------------------------------------------------

def fecha_larga(fecha):
    """Ej: viernes, 13 de noviembre de 2026"""
    return (DIAS[fecha.weekday()] + ", " + str(fecha.day) + " de "
            + MESES[fecha.month - 1] + " de " + str(fecha.year))


def numero(valor):
    """Un decimal, como en el Excel: 1075.6"""
    return "{:.1f}".format(valor)


def armar_cuadro_html(fecha, imar):
    borde = "border:1px solid #000;"
    celda = borde + "padding:2px 8px;font-family:Arial;font-size:10pt;text-align:center;"
    gris = "background:#F2F2F2;"

    filas = ""
    for periodo in range(1, 25):
        filas += (
            "<tr>"
            "<td style='" + celda + "font-weight:bold;'>" + str(periodo) + "</td>"
            "<td style='" + celda + "'>" + numero(imar[periodo - 1]) + "</td>"
            "<td style='" + celda + gris + "'>0</td>"
            "<td style='" + celda + "'>Fuera de línea</td>"
            "</tr>"
        )

    promedio = sum(imar) / len(imar)

    return (
        "<table style='border-collapse:collapse;" + borde + "'>"
        "<tr><td colspan='4' style='" + celda + "font-weight:bold;'>Planeación Despacho Diario</td></tr>"
        "<tr><td style='" + celda + "font-weight:bold;'>Fecha</td>"
        "<td colspan='3' style='" + celda + "font-weight:bold;'>"
        + fecha_larga(fecha) + "</td></tr>"
        "<tr>"
        "<td style='" + celda + "'>Período</td>"
        "<td style='" + celda + "'>IMAR - $/kWh</td>"
        "<td style='" + celda + "'>Energía a generar<br>con la planta - TMM<br>kWh</td>"
        "<td style='" + celda + "'>CONFIGURACIÓN SUGERIDA</td>"
        "</tr>"
        + filas +
        "<tr>"
        "<td style='" + celda + "font-weight:bold;'>TOTAL</td>"
        "<td style='" + celda + "font-style:italic;'>" + numero(promedio) + "</td>"
        "<td style='" + celda + gris + "font-style:italic;'>0</td>"
        "<td style='" + celda + "'></td>"
        "</tr>"
        "<tr><td colspan='4' style='" + borde + "padding:8px;font-family:Arial;font-size:10pt;'>"
        + NOTA_SIN_GAS + "</td></tr>"
        "</table>"
    )


def asunto_del_correo(fecha):
    """Ej: Planeación Despacho Diario Noviembre 13/2026"""
    return ("Planeación Despacho Diario " + MESES[fecha.month - 1].capitalize()
            + " " + str(fecha.day).zfill(2) + "/" + str(fecha.year))


def cuerpo_borrador_html(fecha, cuadro):
    return (
        "<div style='font-family:Arial;font-size:11pt;'>"
        "<p>Buen día,</p>"
        "<p>Comparto la Planeación del Despacho Diario (PDD sugerido) para el "
        + fecha_larga(fecha) + ".</p>"
        + cuadro +
        "<p>Saludos,</p>"
        "</div>"
    )


# ---------------------------------------------------------------------
# 3) CREAR EL BORRADOR .eml (se abre en Outlook listo para enviar)
# ---------------------------------------------------------------------

def crear_borrador_eml(fecha, cuadro):
    borrador = EmailMessage()
    borrador["To"] = ", ".join(PARA)
    borrador["Cc"] = ", ".join(CON_COPIA)
    borrador["Subject"] = asunto_del_correo(fecha)
    # Esta linea hace que Outlook lo abra como correo NUEVO (para enviar),
    # no como un correo ya recibido.
    borrador["X-Unsent"] = "1"
    borrador.set_content("Abre este correo en Outlook para ver el cuadro.")
    borrador.add_alternative(cuerpo_borrador_html(fecha, cuadro), subtype="html")

    nombre = "PDD_" + fecha.strftime("%y%m%d") + ".eml"
    ruta = os.path.join(CARPETA_PROYECTO, nombre)
    with open(ruta, "wb") as archivo:
        archivo.write(bytes(borrador))
    return ruta


# ---------------------------------------------------------------------
# 4) ENVIAR DESDE GMAIL A TU CORREO CORPORATIVO
# ---------------------------------------------------------------------

def enviar_gmail(destino, asunto, html, ruta_adjunto=None):
    remitente = os.getenv("CORREO_REMITENTE")
    contrasena = os.getenv("CORREO_CONTRASENA_APP")
    if not remitente or not contrasena:
        print("Error: faltan CORREO_REMITENTE o CORREO_CONTRASENA_APP.")
        return False

    mensaje = EmailMessage()
    mensaje["From"] = remitente
    mensaje["To"] = destino
    mensaje["Subject"] = asunto
    mensaje.set_content("Abre este correo en Outlook para ver el cuadro.")
    mensaje.add_alternative(html, subtype="html")

    if ruta_adjunto:
        with open(ruta_adjunto, "rb") as archivo:
            mensaje.add_attachment(archivo.read(), maintype="application",
                                   subtype="octet-stream",
                                   filename=os.path.basename(ruta_adjunto))

    try:
        contexto = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=contexto) as servidor:
            servidor.login(remitente, contrasena)
            servidor.send_message(mensaje)
        print("Correo enviado a " + destino)
        return True
    except Exception as error:
        print("Error al enviar el correo: " + str(error))
        return False


# ---------------------------------------------------------------------
# PROGRAMA PRINCIPAL
# ---------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fecha", default="", help="AAAA-MM-DD (vacio = manana)")
    parser.add_argument("--correo", default="", help="correo que recibe (vacio = el tuyo)")
    args = parser.parse_args()

    if args.fecha.strip():
        fecha = datetime.strptime(args.fecha.strip(), "%Y-%m-%d").date()
    else:
        fecha = (datetime.now(ZONA_COLOMBIA) + timedelta(days=1)).date()

    destino = args.correo.strip() or CORREO_PARA_MI
    print("PDD en cero para: " + fecha_larga(fecha))

    imar = descargar_imar(fecha)

    if imar is None or len(imar) != 24:
        print("XM todavia no ha publicado el IMAR de esa fecha.")
        enviar_gmail(
            destino,
            "PDD en cero: IMAR del " + fecha.strftime("%d/%m/%Y") + " aún NO publicado",
            "<p>XM todavía no ha publicado el IMAR para el <b>" + fecha_larga(fecha)
            + "</b>.</p><p>Vuelve a darle <b>Run workflow</b> en un rato.</p>",
        )
        sys.exit(1)

    cuadro = armar_cuadro_html(fecha, imar)
    ruta_eml = crear_borrador_eml(fecha, cuadro)

    instrucciones = (
        "<div style='font-family:Arial;font-size:11pt;'>"
        "<p style='background:#E8F0FE;padding:8px;'>"
        "<b>Para enviarlo desde tu correo corporativo:</b> abre el adjunto <b>"
        + os.path.basename(ruta_eml) + "</b> → se abre un correo nuevo con "
        "destinatarios, copias, asunto y cuadro listos → dale <b>Enviar</b>.</p>"
        "<p><b>Asunto:</b> " + asunto_del_correo(fecha) + "<br>"
        "<b>Para:</b> " + ", ".join(PARA) + "<br>"
        "<b>CC:</b> " + ", ".join(CON_COPIA) + "</p>"
        "<p>Vista previa:</p>"
        + cuadro +
        "</div>"
    )

    ok = enviar_gmail(destino, "[Listo para enviar] " + asunto_del_correo(fecha),
                      instrucciones, ruta_eml)
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
