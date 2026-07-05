"""
Modulo: senda_referencia.py
Ubicacion: API/senda_referencia.py

Descarga la Senda de Referencia del Embalse, publicada por XM segun
la Resolucion CREG 209 de 2020. Este archivo se actualiza aproximada-
mente cada 6 meses (una vez por temporada: Verano o Invierno), asi
que este script prueba varios nombres posibles (año actual y
anterior, ambas temporadas) hasta encontrar el archivo vigente que
cubra la fecha de hoy, sin que nadie tenga que descargarlo a mano.

La fuente es un archivo Excel publicado en el sitio publico de XM
(no esta disponible en la API oficial ni en SIMEM), asi que aqui se
usa "web scraping" del archivo publico, igual que con el IMAR.
"""

import requests
import pandas as pd
import sys
import os
import io
from datetime import datetime

CARPETA_PROYECTO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(CARPETA_PROYECTO, "BaseDatos"))

from base_datos import guardar_senda_referencia

URL_BASE = "https://api-portalxm.xm.com.co/administracion-archivos/ficheros/mostrar-url"
NOMBRE_CONTENEDOR = "storageportalxm"
NOMBRE_HOJA = "Senda_Embalse"


def _intentar_descargar_archivo(anio, temporada):
    """
    Intenta descargar el archivo de la senda de referencia para un
    año y temporada especificos.

    Retorna:
        El contenido del archivo (bytes) si existe, o None si no.
    """
    nombre_archivo = "Supuestos_Resultados_SendaReferencia_" + temporada + "_" + str(anio) + ".xlsx"
    ruta_archivo = "M:/InformacionAgentes/Usuarios/Publico/PlaneacionOperacion/Senda de Referencia/" + str(anio) + "/" + nombre_archivo

    parametros = {
        "ruta": ruta_archivo,
        "nombreBlobContainer": NOMBRE_CONTENEDOR
    }

    try:
        respuesta = requests.get(URL_BASE, params=parametros, timeout=30)

        if respuesta.status_code == 200 and len(respuesta.content) > 10000:
            return respuesta.content
        else:
            return None

    except Exception:
        return None


def _extraer_tabla_senda(contenido_excel):
    """
    Extrae la tabla de Fecha y Embalse SIN Diario [%] desde el
    contenido de un archivo Excel de senda de referencia.

    Retorna:
        Un DataFrame con columnas "fecha" (texto YYYY-MM-DD) y
        "valor" (fraccion decimal, ej. 0.6214 para 62.14%).
    """
    df = pd.read_excel(
        io.BytesIO(contenido_excel),
        sheet_name=NOMBRE_HOJA,
        header=8,
        usecols=[1, 2]
    )

    df.columns = ["fecha_dt", "valor"]
    df = df.dropna()
    df["fecha"] = df["fecha_dt"].apply(lambda f: f.strftime("%Y-%m-%d"))

    return df[["fecha", "valor"]]


def obtener_y_guardar_senda_referencia():
    """
    Busca automaticamente el archivo de senda de referencia vigente
    (probando año actual y anterior, temporadas Invierno y Verano),
    y guarda en la base de datos el que efectivamente cubra la fecha
    de hoy. Si ninguno cubre exactamente hoy, usa el que tenga los
    datos mas recientes disponibles.

    Retorna:
        True si se encontro y guardo un archivo, False si no.
    """
    hoy_texto = datetime.now().strftime("%Y-%m-%d")

    candidatos_probados = []

    for anio in [datetime.now().year, datetime.now().year - 1]:
        for temporada in ["Invierno", "Verano"]:
            print("Probando: " + temporada + " " + str(anio) + "...")
            contenido = _intentar_descargar_archivo(anio, temporada)

            if contenido is not None:
                try:
                    tabla = _extraer_tabla_senda(contenido)
                    fecha_min = tabla["fecha"].min()
                    fecha_max = tabla["fecha"].max()
                    print("  Encontrado. Cubre desde " + fecha_min + " hasta " + fecha_max)

                    candidatos_probados.append({
                        "anio": anio,
                        "temporada": temporada,
                        "tabla": tabla,
                        "fecha_min": fecha_min,
                        "fecha_max": fecha_max
                    })
                except Exception as error:
                    print("  Se encontro el archivo pero no se pudo leer: " + str(error))

    if len(candidatos_probados) == 0:
        print("No se encontro ningun archivo de senda de referencia.")
        return False

    # Preferimos el archivo cuyo rango de fechas SI cubra el dia de hoy
    candidato_vigente = None
    for candidato in candidatos_probados:
        if candidato["fecha_min"] <= hoy_texto <= candidato["fecha_max"]:
            candidato_vigente = candidato
            break

    # Si ninguno cubre exactamente hoy, usamos el que tenga la fecha mas reciente
    if candidato_vigente is None:
        candidato_vigente = max(candidatos_probados, key=lambda c: c["fecha_max"])
        print("Ningun archivo cubre exactamente hoy. Usando el mas reciente: " + candidato_vigente["temporada"] + " " + str(candidato_vigente["anio"]))
    else:
        print("Archivo vigente encontrado: " + candidato_vigente["temporada"] + " " + str(candidato_vigente["anio"]))

    guardar_senda_referencia(candidato_vigente["tabla"])
    return True


if __name__ == "__main__":
    obtener_y_guardar_senda_referencia()
