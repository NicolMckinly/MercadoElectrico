"""
Modulo: estadisticas_generacion.py
Ubicacion: Analisis/estadisticas_generacion.py

Calcula el promedio de Generacion por Fuente de los ultimos dias
disponibles, junto con su participacion porcentual, para armar la
tabla que pide la especificacion del proyecto (Modulo 4).
"""

import sys
import os

CARPETA_PROYECTO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(CARPETA_PROYECTO, "BaseDatos"))

from base_datos import consultar_todo_generacion_por_fuente

DIAS_PARA_EL_PROMEDIO = 5


def calcular_promedio_generacion_por_fuente():
    """
    Calcula el promedio diario de generacion de cada tecnologia,
    usando los ultimos dias disponibles en la base de datos, y su
    participacion porcentual sobre el total.

    Retorna:
        Una lista de diccionarios, uno por tecnologia, con las claves
        "tecnologia", "promedio_gwh" y "porcentaje". Ordenada de
        mayor a menor participacion. O None si no hay datos.
    """
    datos = consultar_todo_generacion_por_fuente()

    if len(datos) == 0:
        return None

    fechas_disponibles = sorted(datos["fecha"].unique(), reverse=True)
    fechas_a_usar = fechas_disponibles[:DIAS_PARA_EL_PROMEDIO]

    datos_recientes = datos[datos["fecha"].isin(fechas_a_usar)]

    promedios = datos_recientes.groupby("tecnologia")["valor_kwh"].mean().reset_index()
    promedios["valor_gwh"] = promedios["valor_kwh"] / 1_000_000

    total_gwh = promedios["valor_gwh"].sum()
    promedios["porcentaje"] = (promedios["valor_gwh"] / total_gwh) * 100

    promedios = promedios.sort_values("valor_gwh", ascending=False)

    resultado = []
    for _, fila in promedios.iterrows():
        resultado.append({
            "tecnologia": fila["tecnologia"],
            "promedio_gwh": fila["valor_gwh"],
            "porcentaje": fila["porcentaje"]
        })

    return resultado


if __name__ == "__main__":
    resultado = calcular_promedio_generacion_por_fuente()

    if resultado is not None:
        print("Promedio de Generacion por Fuente (ultimos dias disponibles):")
        print("")
        print("{:<20} {:>15} {:>12}".format("Tecnologia", "Promedio GWh", "Porcentaje"))
        for fila in resultado:
            print("{:<20} {:>15.2f} {:>11.1f}%".format(fila["tecnologia"], fila["promedio_gwh"], fila["porcentaje"]))
    else:
        print("No hay datos de generacion disponibles todavia.")
