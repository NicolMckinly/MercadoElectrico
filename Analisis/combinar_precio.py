"""
Modulo: combinar_precio.py
Ubicacion: Analisis/combinar_precio.py

Este archivo combina el Precio de Bolsa real con el IMAR, para
producir una sola serie de datos sin espacios vacios:

- Si existe el Precio de Bolsa real de un dia, se usa ese valor.
- Si no existe (XM aun no lo ha publicado), se usa el IMAR de ese
  mismo dia en su lugar.

Ademas, se marca claramente con que fuente se completo cada dia,
para que los reportes y graficas puedan indicarlo (por ejemplo,
mostrando el dato del IMAR con un estilo visual distinto).

Este archivo NO descarga nada de internet. Solo lee lo que ya esta
guardado en la base de datos y lo combina.
"""

import sys
import os
import pandas as pd

CARPETA_PROYECTO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(CARPETA_PROYECTO, "BaseDatos"))

from base_datos import consultar_todo_precio_bolsa, consultar_todo_imar

COLUMNAS_HORA = [
    "hora_01", "hora_02", "hora_03", "hora_04", "hora_05", "hora_06",
    "hora_07", "hora_08", "hora_09", "hora_10", "hora_11", "hora_12",
    "hora_13", "hora_14", "hora_15", "hora_16", "hora_17", "hora_18",
    "hora_19", "hora_20", "hora_21", "hora_22", "hora_23", "hora_24"
]


def obtener_serie_combinada(fecha_inicio=None, fecha_fin=None):
    """
    Combina el Precio de Bolsa real y el IMAR en una sola serie diaria,
    sin espacios vacios.

    Parametros:
        fecha_inicio (str, opcional): fecha minima a incluir, formato "YYYY-MM-DD".
        fecha_fin (str, opcional): fecha maxima a incluir, formato "YYYY-MM-DD".
                                     Si no se indica, se incluye todo el historico.

    Retorna:
        Un DataFrame con las columnas: fecha, hora_01...hora_24, fuente.
        La columna "fuente" dice "Precio Bolsa" o "IMAR" segun de donde
        vino el dato de ese dia.
    """
    precio_bolsa = consultar_todo_precio_bolsa()
    imar = consultar_todo_imar()

    precio_bolsa["fuente"] = "Precio Bolsa"
    imar["fuente"] = "IMAR"

    # Unimos las fechas de ambas tablas, sin repetir
    todas_las_fechas = sorted(set(precio_bolsa["fecha"]).union(set(imar["fecha"])))

    if fecha_inicio is not None:
        todas_las_fechas = [f for f in todas_las_fechas if f >= fecha_inicio]

    if fecha_fin is not None:
        todas_las_fechas = [f for f in todas_las_fechas if f <= fecha_fin]

    precio_bolsa_indexado = precio_bolsa.set_index("fecha")
    imar_indexado = imar.set_index("fecha")

    filas_combinadas = []

    for fecha in todas_las_fechas:
        if fecha in precio_bolsa_indexado.index:
            # Prioridad 1: usamos el precio real si existe
            fila = precio_bolsa_indexado.loc[fecha]
            nueva_fila = {"fecha": fecha, "fuente": "Precio Bolsa"}
            for columna in COLUMNAS_HORA:
                nueva_fila[columna] = fila[columna]
            filas_combinadas.append(nueva_fila)

        elif fecha in imar_indexado.index:
            # Prioridad 2: si no hay precio real, usamos el IMAR
            fila = imar_indexado.loc[fecha]
            nueva_fila = {"fecha": fecha, "fuente": "IMAR"}
            for columna in COLUMNAS_HORA:
                nueva_fila[columna] = fila[columna]
            filas_combinadas.append(nueva_fila)

    resultado = pd.DataFrame(filas_combinadas)
    return resultado


if __name__ == "__main__":
    print("Combinando Precio de Bolsa e IMAR...")
    print("")

    serie = obtener_serie_combinada()

    print(serie[["fecha", "hora_01", "hora_12", "hora_24", "fuente"]].to_string())

    print("")
    print("Total de dias en la serie combinada: " + str(len(serie)))

    dias_con_precio_real = len(serie[serie["fuente"] == "Precio Bolsa"])
    dias_con_imar = len(serie[serie["fuente"] == "IMAR"])

    print("  Dias con Precio de Bolsa real: " + str(dias_con_precio_real))
    print("  Dias completados con IMAR: " + str(dias_con_imar))
