"""
Modulo: monitor_ecopetrol.py
Ubicacion: API/monitor_ecopetrol.py

Monitorea la pagina publica de Ecopetrol donde se publican las
convocatorias de comercializacion de Gas Natural (Campos Mayores e
Importado, y Campos Aislados y Campos Menores), y envia un correo
cada vez que aparece una convocatoria NUEVA que el sistema no habia
visto antes, con los detalles tecnicos extraidos automaticamente
(fuente, cantidad en MBTUD, modalidad/tipo de contrato, plazo,
garantia).

Esta pagina es HTML normal (no requiere JavaScript), asi que se
puede leer directamente con "requests" mas un extractor de texto.
"""

import requests
import re
import sys
import os
import hashlib
from bs4 import BeautifulSoup

CARPETA_PROYECTO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(CARPETA_PROYECTO, "BaseDatos"))

from base_datos import consultar_convocatorias_vistas, guardar_convocatoria_vista

URL_PAGINA = (
    "https://www.ecopetrol.com.co/wps/portal/Home/multisitios/comercial/es/"
    "sondeosyofertas/ofertas-informacion-comercial/informacion-comercial-gn"
)

ENCABEZADOS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

# Palabras que marcan el inicio de una convocatoria nueva dentro del texto
PATRON_TITULO = re.compile(
    r"(OFRECIMIENTO DE GAS NATURAL[^\n]*|PROCESO DE COMERCIALIZACI[ÓO]N[^\n]*)",
    re.IGNORECASE
)

# Patrones para extraer cada detalle tecnico, cuando aparezca
PATRONES_DETALLE = {
    "fuente": re.compile(r"Fuente[s]?:\s*([^\n]+)", re.IGNORECASE),
    "cantidad": re.compile(r"Cantidad:\s*([^\n]+)", re.IGNORECASE),
    "modalidad": re.compile(r"Modalidad:\s*([^\n]+)", re.IGNORECASE),
    "plazo": re.compile(r"Plazo:\s*([^\n]+)", re.IGNORECASE),
    "garantia": re.compile(r"Garant[íi]a:\s*([^\n]+)", re.IGNORECASE),
    "fecha_publicacion": re.compile(r"Fecha de publicaci[óo]n:\s*([^\n]+)", re.IGNORECASE),
}


def _obtener_texto_de_la_pagina():
    """
    Descarga la pagina de Ecopetrol y extrae su texto plano (sin
    etiquetas HTML), usando BeautifulSoup.

    Retorna:
        El texto completo de la pagina, o None si hubo un error.
    """
    try:
        respuesta = requests.get(URL_PAGINA, headers=ENCABEZADOS, timeout=30)

        if respuesta.status_code != 200:
            print("Error al descargar la pagina de Ecopetrol: codigo " + str(respuesta.status_code))
            return None

        sopa = BeautifulSoup(respuesta.text, "html.parser")

        # Quitamos scripts y estilos, que no nos interesan
        for etiqueta in sopa(["script", "style"]):
            etiqueta.decompose()

        texto = sopa.get_text(separator="\n")
        return texto

    except Exception as error:
        print("Error al descargar la pagina de Ecopetrol: " + str(error))
        return None


def _extraer_convocatorias(texto_completo):
    """
    Divide el texto completo de la pagina en convocatorias
    individuales, y extrae los detalles tecnicos de cada una.

    Para evitar falsos positivos (frases sueltas dentro de parrafos
    largos que mencionan "proceso de comercializacion" de pasada,
    como avisos legales), solo se consideran como "titulo" las
    LINEAS COMPLETAS que empiezan con el patron y son razonablemente
    cortas (un titulo real, no un parrafo de varias oraciones).

    Retorna:
        Una lista de diccionarios, cada uno con "titulo" y los
        detalles tecnicos encontrados (los que no se encuentren
        quedan como "No especificado").
    """
    LARGO_MAXIMO_DE_UN_TITULO = 140

    lineas = texto_completo.split("\n")

    indices_de_titulos = []
    for indice, linea in enumerate(lineas):
        linea_limpia = linea.strip()

        if len(linea_limpia) == 0 or len(linea_limpia) > LARGO_MAXIMO_DE_UN_TITULO:
            continue

        if PATRON_TITULO.match(linea_limpia):
            indices_de_titulos.append(indice)

    convocatorias = []

    for posicion in range(len(indices_de_titulos)):
        indice_inicio = indices_de_titulos[posicion]
        indice_fin = indices_de_titulos[posicion + 1] if posicion + 1 < len(indices_de_titulos) else len(lineas)

        titulo = lineas[indice_inicio].strip()
        bloque = "\n".join(lineas[indice_inicio:indice_fin])

        detalles = {"titulo": titulo}

        for nombre_campo, patron in PATRONES_DETALLE.items():
            coincidencia = patron.search(bloque)
            detalles[nombre_campo] = coincidencia.group(1).strip() if coincidencia else "No especificado"

        convocatorias.append(detalles)

    return convocatorias


def _generar_identificador(convocatoria):
    """
    Genera un identificador unico y estable para una convocatoria,
    a partir de su titulo y fecha de publicacion, para poder
    detectar si ya la habiamos visto antes.
    """
    texto_base = convocatoria["titulo"] + "|" + convocatoria["fecha_publicacion"]
    return hashlib.md5(texto_base.encode("utf-8")).hexdigest()


def buscar_convocatorias_nuevas():
    """
    Revisa la pagina de Ecopetrol y retorna solo las convocatorias
    que NO se hayan visto antes (comparando contra la base de datos).

    Retorna:
        Una lista de diccionarios con las convocatorias nuevas.
    """
    texto = _obtener_texto_de_la_pagina()

    if texto is None:
        return []

    todas_las_convocatorias = _extraer_convocatorias(texto)
    identificadores_ya_vistos = consultar_convocatorias_vistas()

    nuevas = []

    for convocatoria in todas_las_convocatorias:
        identificador = _generar_identificador(convocatoria)

        if identificador not in identificadores_ya_vistos:
            convocatoria["identificador"] = identificador
            nuevas.append(convocatoria)
            guardar_convocatoria_vista(identificador, convocatoria["titulo"])

    return nuevas


if __name__ == "__main__":
    print("Revisando convocatorias de gas natural de Ecopetrol...")
    print("")

    nuevas = buscar_convocatorias_nuevas()

    if len(nuevas) == 0:
        print("No hay convocatorias nuevas.")
    else:
        print("Se encontraron " + str(len(nuevas)) + " convocatoria(s) nueva(s):")
        print("")
        for convocatoria in nuevas:
            print("- " + convocatoria["titulo"])
            print("  Fecha de publicacion: " + convocatoria["fecha_publicacion"])
            print("  Fuente: " + convocatoria["fuente"])
            print("  Cantidad: " + convocatoria["cantidad"])
            print("  Modalidad: " + convocatoria["modalidad"])
            print("  Plazo: " + convocatoria["plazo"])
            print("  Garantia: " + convocatoria["garantia"])
            print("")
