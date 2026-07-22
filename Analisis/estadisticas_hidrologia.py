"""
Modulo: estadisticas_hidrologia.py
Ubicacion: Analisis/estadisticas_hidrologia.py

Calcula las comparaciones que pide la especificacion del proyecto
para el Modulo 3 (Variables Hidrologicas): variacion diaria, semanal,
mensual, y comparacion con el mismo periodo del año anterior.

Tambien calcula la diferencia entre el Embalse SIN% actual y la
Senda de Referencia vigente para esa misma fecha (Resolucion CREG
209 de 2020), y genera un comentario automatico en lenguaje sencillo
para cada variable principal (embalses y aportes).

Este archivo NO descarga datos ni genera graficos. Solo hace calculos
a partir de lo que ya este guardado en la base de datos.
"""

import sys
import os
import pandas as pd
from datetime import datetime, timedelta

CARPETA_PROYECTO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(CARPETA_PROYECTO, "BaseDatos"))

from base_datos import consultar_todo_variables_hidrologicas, consultar_todo_senda_referencia


def _valor_en_fecha(datos, fecha_texto, columna):
    """
    Busca el valor de una columna especifica en una fecha exacta.
    Retorna None si esa fecha no existe en la base de datos.
    """
    fila = datos[datos["fecha"] == fecha_texto]
    if len(fila) == 0:
        return None
    return fila.iloc[0][columna]


def _variacion(valor_actual, valor_anterior):
    """
    Calcula la variacion absoluta y porcentual entre dos valores.
    Retorna (None, None) si no se puede calcular.
    """
    if valor_actual is None or valor_anterior is None or valor_anterior == 0:
        return None, None

    variacion_absoluta = valor_actual - valor_anterior
    variacion_porcentual = (variacion_absoluta / valor_anterior) * 100
    return variacion_absoluta, variacion_porcentual


def _valor_senda_vigente_en(senda, fecha_referencia_texto):
    """
    Busca el valor de la Senda de Referencia vigente para una fecha
    especifica. Si no hay un dato exacto para ese dia, usa el valor
    guardado mas reciente que sea anterior o igual a esa fecha.

    Retorna:
        El valor de la senda (fraccion decimal, ej. 0.62 para 62%),
        o None si no hay ningun dato disponible.
    """
    if len(senda) == 0:
        return None

    senda = senda.copy()
    fecha_referencia_dt = datetime.strptime(fecha_referencia_texto, "%Y-%m-%d")
    senda["fecha_dt"] = senda["fecha"].apply(lambda f: datetime.strptime(f, "%Y-%m-%d"))

    candidatos = senda[senda["fecha_dt"] <= fecha_referencia_dt]

    if len(candidatos) == 0:
        return None

    return candidatos.sort_values("fecha_dt").iloc[-1]["valor"]


def calcular_estadisticas_hidrologia():
    """
    Calcula el estado actual y las comparaciones de las variables
    hidrologicas principales (embalses y aportes).

    Retorna:
        Un diccionario con toda la informacion calculada, o None si
        no hay datos suficientes todavia.
    """
    datos = consultar_todo_variables_hidrologicas()

    if len(datos) == 0:
        print("No hay datos hidrologicos suficientes todavia.")
        return None

    datos = datos.sort_values("fecha").reset_index(drop=True)
    datos["fecha_dt"] = datos["fecha"].apply(lambda f: datetime.strptime(f, "%Y-%m-%d"))

    fila_mas_reciente = datos.iloc[-1]
    fecha_mas_reciente_dt = fila_mas_reciente["fecha_dt"]
    fecha_mas_reciente_texto = fila_mas_reciente["fecha"]

    resultado = {"fecha": fecha_mas_reciente_texto}

    # ---------- Embalses ----------
    resultado["embalses_porcentaje_actual"] = fila_mas_reciente["embalses_porcentaje"]
    resultado["embalses_energia_actual"] = fila_mas_reciente["embalses_energia"]

    fecha_ayer = (fecha_mas_reciente_dt - timedelta(days=1)).strftime("%Y-%m-%d")
    fecha_semana_pasada = (fecha_mas_reciente_dt - timedelta(days=7)).strftime("%Y-%m-%d")
    fecha_mes_pasado = (fecha_mas_reciente_dt - timedelta(days=30)).strftime("%Y-%m-%d")
    fecha_anio_pasado = fecha_mas_reciente_dt.replace(year=fecha_mas_reciente_dt.year - 1).strftime("%Y-%m-%d")

    valor_embalses_ayer = _valor_en_fecha(datos, fecha_ayer, "embalses_porcentaje")
    valor_embalses_semana_pasada = _valor_en_fecha(datos, fecha_semana_pasada, "embalses_porcentaje")
    valor_embalses_mes_pasado = _valor_en_fecha(datos, fecha_mes_pasado, "embalses_porcentaje")
    valor_embalses_anio_pasado = _valor_en_fecha(datos, fecha_anio_pasado, "embalses_porcentaje")

    resultado["embalses_variacion_diaria_puntos"], _ = _variacion(
        resultado["embalses_porcentaje_actual"], valor_embalses_ayer
    )
    resultado["embalses_variacion_semanal_puntos"], _ = _variacion(
        resultado["embalses_porcentaje_actual"], valor_embalses_semana_pasada
    )
    resultado["embalses_variacion_mensual_puntos"], _ = _variacion(
        resultado["embalses_porcentaje_actual"], valor_embalses_mes_pasado
    )
    resultado["embalses_variacion_anual_puntos"], _ = _variacion(
        resultado["embalses_porcentaje_actual"], valor_embalses_anio_pasado
    )

    # ---------- Senda de Referencia (Resolucion CREG 209 de 2020) ----------
    senda = consultar_todo_senda_referencia()
    resultado["senda_referencia_actual"] = _valor_senda_vigente_en(senda, fecha_mas_reciente_texto)

    if resultado["senda_referencia_actual"] is not None:
        resultado["embalses_diferencia_vs_senda_puntos"] = (
            resultado["embalses_porcentaje_actual"] - resultado["senda_referencia_actual"]
        )
    else:
        resultado["embalses_diferencia_vs_senda_puntos"] = None

    # ---------- Aportes ----------
    resultado["aportes_porcentaje_actual"] = fila_mas_reciente["aportes_porcentaje"]
    resultado["aportes_energia_actual"] = fila_mas_reciente["aportes_energia"]
    resultado["aportes_media_historica_actual"] = fila_mas_reciente["aportes_media_historica"]

    if resultado["aportes_media_historica_actual"] not in (None, 0):
        resultado["aportes_porcentaje_vs_media_historica"] = (
            resultado["aportes_energia_actual"] / resultado["aportes_media_historica_actual"]
        ) * 100
    else:
        resultado["aportes_porcentaje_vs_media_historica"] = None

    valor_aportes_ayer = _valor_en_fecha(datos, fecha_ayer, "aportes_porcentaje")
    resultado["aportes_variacion_diaria_puntos"], _ = _variacion(
        resultado["aportes_porcentaje_actual"], valor_aportes_ayer
    )

    # ---------- Tendencia de los ultimos 30 dias (embalses) ----------
    ultimos_30 = datos.tail(30)
    if len(ultimos_30) >= 2:
        cambio_30_dias = ultimos_30.iloc[-1]["embalses_porcentaje"] - ultimos_30.iloc[0]["embalses_porcentaje"]
        if cambio_30_dias > 0.01:
            resultado["tendencia_embalses_30_dias"] = "Al alza"
        elif cambio_30_dias < -0.01:
            resultado["tendencia_embalses_30_dias"] = "A la baja"
        else:
            resultado["tendencia_embalses_30_dias"] = "Estable"
    else:
        resultado["tendencia_embalses_30_dias"] = "Datos insuficientes (se necesitan al menos 2 dias en los ultimos 30)"

    return resultado


def generar_comentario_hidrologia(estadisticas):
    """
    Genera un comentario automatico en lenguaje sencillo sobre el
    estado de los embalses y los aportes, similar al ejemplo de la
    especificacion del proyecto.

    Parametros:
        estadisticas (dict): resultado de calcular_estadisticas_hidrologia()

    Retorna:
        Un string con el comentario.
    """
    partes = []

    # Comentario de embalses
    if estadisticas["embalses_variacion_diaria_puntos"] is not None:
        puntos = estadisticas["embalses_variacion_diaria_puntos"] * 100
        if puntos > 0:
            direccion = "aumentaron " + "{:.2f}".format(abs(puntos)) + " puntos porcentuales"
        elif puntos < 0:
            direccion = "disminuyeron " + "{:.2f}".format(abs(puntos)) + " puntos porcentuales"
        else:
            direccion = "se mantuvieron estables"

        partes.append("Los embalses " + direccion + " respecto al dia anterior, ubicandose en " + "{:.2f}".format(estadisticas["embalses_porcentaje_actual"] * 100) + "% de su capacidad util.")
    else:
        partes.append("Los embalses se encuentran en " + "{:.2f}".format(estadisticas["embalses_porcentaje_actual"] * 100) + "% de su capacidad util.")

    # Comentario de Embalse SIN% vs Senda de Referencia
    if estadisticas["embalses_diferencia_vs_senda_puntos"] is not None:
        diferencia_puntos = estadisticas["embalses_diferencia_vs_senda_puntos"] * 100
        senda_pct = estadisticas["senda_referencia_actual"] * 100

        if diferencia_puntos > 0.01:
            posicion = "por encima de la Senda de Referencia en " + "{:.2f}".format(abs(diferencia_puntos)) + " puntos porcentuales"
        elif diferencia_puntos < -0.01:
            posicion = "por debajo de la Senda de Referencia en " + "{:.2f}".format(abs(diferencia_puntos)) + " puntos porcentuales"
        else:
            posicion = "practicamente igual a la Senda de Referencia"

        partes.append("El nivel de Embalse SIN se encuentra " + posicion + " (la Senda de Referencia vigente hoy es de " + "{:.2f}".format(senda_pct) + "%).")

    # Comentario de aportes vs media historica
    if estadisticas["aportes_porcentaje_vs_media_historica"] is not None:
        porcentaje_vs_media = estadisticas["aportes_porcentaje_vs_media_historica"]
        if porcentaje_vs_media >= 100:
            partes.append("Los aportes hidricos estan " + "{:.1f}".format(porcentaje_vs_media) + "% de la media historica, es decir, por encima de lo normal para esta epoca.")
        else:
            partes.append("Los aportes hidricos estan " + "{:.1f}".format(porcentaje_vs_media) + "% de la media historica, es decir, por debajo de lo normal para esta epoca.")

    # Tendencia
    if "insuficientes" not in estadisticas["tendencia_embalses_30_dias"]:
        partes.append("La tendencia de los embalses en los ultimos 30 dias es: " + estadisticas["tendencia_embalses_30_dias"] + ".")
    else:
        partes.append("Aun no hay suficiente historico para determinar la tendencia de 30 dias de los embalses.")

    return " ".join(partes)


if __name__ == "__main__":
    print("Calculando estadisticas hidrologicas...")
    print("")

    estadisticas = calcular_estadisticas_hidrologia()

    if estadisticas is not None:
        print("Fecha mas reciente: " + estadisticas["fecha"])
        print("")
        print("EMBALSES")
        print("  Actual: " + "{:.2f}".format(estadisticas["embalses_porcentaje_actual"] * 100) + "%")
        if estadisticas["embalses_variacion_diaria_puntos"] is not None:
            print("  Variacion diaria: " + "{:+.2f}".format(estadisticas["embalses_variacion_diaria_puntos"] * 100) + " puntos porcentuales")
        if estadisticas["embalses_variacion_semanal_puntos"] is not None:
            print("  Variacion semanal: " + "{:+.2f}".format(estadisticas["embalses_variacion_semanal_puntos"] * 100) + " puntos porcentuales")
        if estadisticas["embalses_variacion_mensual_puntos"] is not None:
            print("  Variacion mensual: " + "{:+.2f}".format(estadisticas["embalses_variacion_mensual_puntos"] * 100) + " puntos porcentuales")
        if estadisticas["embalses_variacion_anual_puntos"] is not None:
            print("  Variacion vs mismo periodo año anterior: " + "{:+.2f}".format(estadisticas["embalses_variacion_anual_puntos"] * 100) + " puntos porcentuales")
        print("  Tendencia 30 dias: " + estadisticas["tendencia_embalses_30_dias"])
        if estadisticas["senda_referencia_actual"] is not None:
            print("  Senda de Referencia vigente: " + "{:.2f}".format(estadisticas["senda_referencia_actual"] * 100) + "%")
            print("  Diferencia vs Senda de Referencia: " + "{:+.2f}".format(estadisticas["embalses_diferencia_vs_senda_puntos"] * 100) + " puntos porcentuales")

        print("")
        print("APORTES")
        print("  Actual: " + "{:.2f}".format(estadisticas["aportes_porcentaje_actual"] * 100) + "%")
        if estadisticas["aportes_porcentaje_vs_media_historica"] is not None:
            print("  Vs media historica: " + "{:.1f}".format(estadisticas["aportes_porcentaje_vs_media_historica"]) + "%")

        print("")
        print("Comentario automatico:")
        print(generar_comentario_hidrologia(estadisticas))
