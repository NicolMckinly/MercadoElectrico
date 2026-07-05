"""
Modulo: estadisticas_precio.py
Ubicacion: Analisis/estadisticas_precio.py

Calcula las estadisticas del Precio de Bolsa que pide la especificacion
del proyecto: promedio, maximo, minimo, desviacion estandar, volatilidad,
tendencia, promedios moviles (5, 10, 20 dias), promedio semanal y mensual.

Tambien genera un pequeno pronostico de corto plazo basado en la
tendencia reciente, y un comentario automatico en lenguaje sencillo.

Este archivo NO descarga datos ni genera graficos. Solo hace calculos
a partir de la serie combinada (Precio de Bolsa real + IMAR).
"""

import sys
import os
import pandas as pd
from datetime import datetime

CARPETA_PROYECTO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(CARPETA_PROYECTO, "Analisis"))

from combinar_precio import obtener_serie_combinada, COLUMNAS_HORA


def calcular_estadisticas():
    """
    Calcula todas las estadisticas del Precio de Bolsa sobre el
    historico completo disponible en la base de datos.

    Retorna:
        Un diccionario con todas las estadisticas calculadas, o
        None si no hay suficientes datos todavia.
    """
    serie = obtener_serie_combinada()

    if len(serie) == 0:
        print("No hay datos suficientes para calcular estadisticas.")
        return None

    serie["promedio_diario"] = serie[COLUMNAS_HORA].mean(axis=1)
    serie["fecha_dt"] = serie["fecha"].apply(lambda f: datetime.strptime(f, "%Y-%m-%d"))
    serie = serie.sort_values("fecha_dt").reset_index(drop=True)

    resultado = {}

    # Dato del dia mas reciente y el dia anterior (para variacion diaria)
    resultado["fecha_mas_reciente"] = serie.iloc[-1]["fecha"]
    resultado["precio_dia_mas_reciente"] = serie.iloc[-1]["promedio_diario"]
    resultado["fuente_dia_mas_reciente"] = serie.iloc[-1]["fuente"]

    if len(serie) >= 2:
        precio_dia_anterior = serie.iloc[-2]["promedio_diario"]
        resultado["precio_dia_anterior"] = precio_dia_anterior
        resultado["variacion_diaria"] = resultado["precio_dia_mas_reciente"] - precio_dia_anterior
        resultado["variacion_diaria_porcentual"] = (resultado["variacion_diaria"] / precio_dia_anterior) * 100
    else:
        resultado["precio_dia_anterior"] = None
        resultado["variacion_diaria"] = None
        resultado["variacion_diaria_porcentual"] = None

    # Estadisticas generales sobre todo el historico disponible
    resultado["promedio_general"] = serie["promedio_diario"].mean()
    resultado["maximo"] = serie["promedio_diario"].max()
    resultado["fecha_del_maximo"] = serie.loc[serie["promedio_diario"].idxmax(), "fecha"]
    resultado["minimo"] = serie["promedio_diario"].min()
    resultado["fecha_del_minimo"] = serie.loc[serie["promedio_diario"].idxmin(), "fecha"]
    resultado["desviacion_estandar"] = serie["promedio_diario"].std()

    # La volatilidad se expresa como el porcentaje que representa la
    # desviacion estandar sobre el promedio (a mayor numero, mas
    # inestable ha sido el precio en el periodo analizado)
    if resultado["promedio_general"] > 0:
        resultado["volatilidad_porcentual"] = (resultado["desviacion_estandar"] / resultado["promedio_general"]) * 100
    else:
        resultado["volatilidad_porcentual"] = 0

    # Promedios moviles: promedio de los ultimos N dias disponibles
    resultado["promedio_ultimos_5_dias"] = _promedio_ultimos_n_dias(serie, 5)
    resultado["promedio_ultimos_10_dias"] = _promedio_ultimos_n_dias(serie, 10)
    resultado["promedio_ultimos_20_dias"] = _promedio_ultimos_n_dias(serie, 20)

    # Promedio semanal: promedio de los ultimos 7 dias
    resultado["promedio_semanal"] = _promedio_ultimos_n_dias(serie, 7)

    # Promedio mensual: promedio de los dias del mes en curso
    hoy = datetime.now()
    dias_del_mes_actual = serie[
        (serie["fecha_dt"].dt.year == hoy.year) & (serie["fecha_dt"].dt.month == hoy.month)
    ]
    if len(dias_del_mes_actual) > 0:
        resultado["promedio_mensual"] = dias_del_mes_actual["promedio_diario"].mean()
    else:
        resultado["promedio_mensual"] = None

    # Tendencia: comparamos el promedio de los ultimos 5 dias contra
    # el promedio de los 5 dias anteriores a esos, para saber si el
    # precio esta subiendo, bajando o estable
    resultado["tendencia"] = _calcular_tendencia(serie)

    # Pronostico sencillo de corto plazo: se calcula proyectando el
    # cambio promedio diario de los ultimos 5 dias, un dia hacia adelante.
    # Es un pronostico simple, no un modelo estadistico complejo.
    resultado["pronostico_manana"] = _calcular_pronostico_simple(serie)

    return resultado


def _promedio_ultimos_n_dias(serie, n):
    """Calcula el promedio de los ultimos n dias disponibles en la serie."""
    if len(serie) == 0:
        return None
    ultimos_n = serie.tail(n)
    return ultimos_n["promedio_diario"].mean()


def _calcular_tendencia(serie):
    """
    Determina si el precio esta en tendencia "al alza", "a la baja"
    o "estable", comparando los ultimos 5 dias contra los 5 dias
    anteriores a esos.
    """
    if len(serie) < 10:
        return "Datos insuficientes para determinar tendencia (se necesitan al menos 10 dias)"

    ultimos_5 = serie.tail(5)["promedio_diario"].mean()
    anteriores_5 = serie.tail(10).head(5)["promedio_diario"].mean()

    diferencia_porcentual = ((ultimos_5 - anteriores_5) / anteriores_5) * 100

    if diferencia_porcentual > 2:
        return "Al alza"
    elif diferencia_porcentual < -2:
        return "A la baja"
    else:
        return "Estable"


def _calcular_pronostico_simple(serie):
    """
    Calcula un pronostico simple para el dia siguiente, basado en el
    cambio promedio diario de los ultimos 5 dias, proyectado un dia
    hacia adelante desde el ultimo valor conocido.
    """
    if len(serie) < 5:
        return None

    ultimos_5 = serie.tail(5)["promedio_diario"].reset_index(drop=True)
    cambios_diarios = ultimos_5.diff().dropna()
    cambio_promedio = cambios_diarios.mean()

    ultimo_valor_conocido = serie.iloc[-1]["promedio_diario"]
    pronostico = ultimo_valor_conocido + cambio_promedio

    return pronostico


def generar_comentario_automatico(estadisticas):
    """
    Genera un pequeno texto en lenguaje sencillo describiendo el
    comportamiento reciente del precio, similar al ejemplo de la
    especificacion del proyecto.

    Parametros:
        estadisticas (dict): el resultado de calcular_estadisticas()

    Retorna:
        Un string con el comentario automatico.
    """
    if estadisticas["variacion_diaria"] is not None:
        if estadisticas["variacion_diaria"] > 0:
            direccion = "aumento"
        elif estadisticas["variacion_diaria"] < 0:
            direccion = "disminuyo"
        else:
            direccion = "se mantuvo igual"

        frase_variacion = "El precio de bolsa " + direccion + " respecto al dia anterior"
    else:
        frase_variacion = "Aun no hay suficiente historico para calcular la variacion diaria"

    precio_escasez_disponible = False
    try:
        sys.path.append(os.path.join(CARPETA_PROYECTO, "BaseDatos"))
        from base_datos import consultar_precio_escasez_mas_reciente
        _, valor_escasez = consultar_precio_escasez_mas_reciente()
        if valor_escasez is not None:
            precio_escasez_disponible = True
    except Exception:
        pass

    if precio_escasez_disponible:
        if estadisticas["precio_dia_mas_reciente"] < valor_escasez:
            frase_escasez = "y continua por debajo del precio de escasez"
        else:
            frase_escasez = "y ya supera el precio de escasez, lo cual amerita atencion"
    else:
        frase_escasez = ""

    comentario = frase_variacion + " " + frase_escasez + "."

    if "insuficientes" in estadisticas["tendencia"]:
        comentario += " Aun no hay suficiente historico acumulado para determinar la tendencia (se necesitan al menos 10 dias de datos)."
    else:
        comentario += " La tendencia reciente es: " + estadisticas["tendencia"] + "."

    if estadisticas["fuente_dia_mas_reciente"] == "IMAR":
        comentario += " Nota: el dato mas reciente corresponde al IMAR (Predespacho Ideal), ya que el precio real de bolsa de ese dia aun no ha sido publicado por XM."

    return comentario


if __name__ == "__main__":
    print("Calculando estadisticas del Precio de Bolsa...")
    print("")

    estadisticas = calcular_estadisticas()

    if estadisticas is not None:
        print("Fecha mas reciente: " + str(estadisticas["fecha_mas_reciente"]) + " (fuente: " + estadisticas["fuente_dia_mas_reciente"] + ")")
        print("Precio de ese dia: " + "{:.2f}".format(estadisticas["precio_dia_mas_reciente"]))

        if estadisticas["variacion_diaria"] is not None:
            print("Variacion diaria: " + "{:.2f}".format(estadisticas["variacion_diaria"]) + " (" + "{:.2f}".format(estadisticas["variacion_diaria_porcentual"]) + "%)")

        print("")
        print("Promedio general del historico: " + "{:.2f}".format(estadisticas["promedio_general"]))
        print("Maximo: " + "{:.2f}".format(estadisticas["maximo"]) + " (fecha: " + str(estadisticas["fecha_del_maximo"]) + ")")
        print("Minimo: " + "{:.2f}".format(estadisticas["minimo"]) + " (fecha: " + str(estadisticas["fecha_del_minimo"]) + ")")
        print("Desviacion estandar: " + "{:.2f}".format(estadisticas["desviacion_estandar"]))
        print("Volatilidad: " + "{:.2f}".format(estadisticas["volatilidad_porcentual"]) + "%")

        print("")
        print("Promedio ultimos 5 dias: " + "{:.2f}".format(estadisticas["promedio_ultimos_5_dias"]))
        if estadisticas["promedio_ultimos_10_dias"] is not None:
            print("Promedio ultimos 10 dias: " + "{:.2f}".format(estadisticas["promedio_ultimos_10_dias"]))
        if estadisticas["promedio_ultimos_20_dias"] is not None:
            print("Promedio ultimos 20 dias: " + "{:.2f}".format(estadisticas["promedio_ultimos_20_dias"]))
        print("Promedio semanal: " + "{:.2f}".format(estadisticas["promedio_semanal"]))
        if estadisticas["promedio_mensual"] is not None:
            print("Promedio mensual (mes en curso): " + "{:.2f}".format(estadisticas["promedio_mensual"]))

        print("")
        print("Tendencia: " + estadisticas["tendencia"])
        if estadisticas["pronostico_manana"] is not None:
            print("Pronostico simple para el proximo dia: " + "{:.2f}".format(estadisticas["pronostico_manana"]))

        print("")
        print("Comentario automatico:")
        print(generar_comentario_automatico(estadisticas))
