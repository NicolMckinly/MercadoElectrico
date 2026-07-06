"""
Modulo: resumen_ejecutivo.py
Ubicacion: Analisis/resumen_ejecutivo.py

Reune toda la informacion de los ultimos 15 dias para el Resumen
Ejecutivo (Modulo 6 de la especificacion original): Precio de Bolsa,
Precio de Escasez, Embalses, Aportes, Generacion por Fuente,
Noticias, Alertas, y una conclusion automatica que combina todo.

Este archivo NO descarga datos ni genera el PDF. Solo combina lo que
ya calculan los demas modulos de analisis.
"""

import sys
import os

CARPETA_PROYECTO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(CARPETA_PROYECTO, "BaseDatos"))
sys.path.append(os.path.join(CARPETA_PROYECTO, "Analisis"))

from base_datos import (
    consultar_precio_escasez_mas_reciente,
    consultar_noticias_recientes,
    consultar_generacion_por_fuente_de_un_dia,
    consultar_fecha_mas_reciente_generacion,
)
from estadisticas_precio import calcular_estadisticas
from estadisticas_hidrologia import calcular_estadisticas_hidrologia
from alertas import generar_todas_las_alertas


def generar_conclusion_automatica(estadisticas_precio, estadisticas_hidro, alertas):
    """
    Genera una conclusion en lenguaje sencillo que combina el estado
    del precio, los embalses/aportes, y si hay alertas activas.
    """
    partes = []

    if estadisticas_precio is not None:
        partes.append(
            "El Precio de Bolsa se ubica en " + "{:.0f}".format(estadisticas_precio["precio_dia_mas_reciente"])
            + " $/kWh, con una tendencia " + estadisticas_precio["tendencia"].lower() + " en el periodo reciente."
        )

    if estadisticas_hidro is not None:
        partes.append(
            "Los embalses se encuentran en " + "{:.1f}".format(estadisticas_hidro["embalses_porcentaje_actual"] * 100)
            + "% de su capacidad util, con tendencia " + estadisticas_hidro["tendencia_embalses_30_dias"].lower() + "."
        )

    if len(alertas) == 0:
        partes.append("No hay alertas activas en este momento; el mercado opera dentro de condiciones normales.")
    else:
        partes.append(
            "Se identificaron " + str(len(alertas)) + " alerta(s) activa(s) que ameritan atencion "
            + "(ver seccion de Alertas para el detalle)."
        )

    return " ".join(partes)


def generar_resumen_ejecutivo():
    """
    Genera el diccionario completo con toda la informacion del
    resumen ejecutivo quincenal.

    Retorna:
        Un diccionario con todas las secciones, o None si no hay
        datos suficientes para al menos el precio de bolsa.
    """
    estadisticas_precio = calcular_estadisticas()

    if estadisticas_precio is None:
        return None

    estadisticas_hidro = calcular_estadisticas_hidrologia()

    _, valor_escasez = consultar_precio_escasez_mas_reciente()

    fecha_generacion = consultar_fecha_mas_reciente_generacion()
    generacion_reciente = None
    if fecha_generacion is not None:
        generacion_reciente = consultar_generacion_por_fuente_de_un_dia(fecha_generacion)

    noticias = consultar_noticias_recientes(dias=15)

    alertas = generar_todas_las_alertas()

    conclusion = generar_conclusion_automatica(estadisticas_precio, estadisticas_hidro, alertas)

    return {
        "estadisticas_precio": estadisticas_precio,
        "valor_escasez": valor_escasez,
        "estadisticas_hidro": estadisticas_hidro,
        "fecha_generacion": fecha_generacion,
        "generacion_reciente": generacion_reciente,
        "noticias": noticias,
        "alertas": alertas,
        "conclusion": conclusion,
    }


if __name__ == "__main__":
    resumen = generar_resumen_ejecutivo()

    if resumen is None:
        print("No hay datos suficientes para generar el resumen ejecutivo.")
    else:
        print("Precio de Bolsa actual: " + "{:.0f}".format(resumen["estadisticas_precio"]["precio_dia_mas_reciente"]) + " $/kWh")
        if resumen["valor_escasez"] is not None:
            print("Precio de Escasez: " + "{:.0f}".format(resumen["valor_escasez"]) + " $/kWh")
        if resumen["estadisticas_hidro"] is not None:
            print("Embalses: " + "{:.1f}".format(resumen["estadisticas_hidro"]["embalses_porcentaje_actual"] * 100) + "%")
        print("Noticias recientes encontradas: " + str(len(resumen["noticias"])))
        print("Alertas activas: " + str(len(resumen["alertas"])))
        print("")
        print("Conclusion automatica:")
        print(resumen["conclusion"])
