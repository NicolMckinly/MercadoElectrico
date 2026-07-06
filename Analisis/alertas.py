"""
Modulo: alertas.py
Ubicacion: Analisis/alertas.py

Genera alertas automaticas cuando ocurren eventos importantes en el
mercado electrico, segun la especificacion del proyecto (Modulo 7):

1. Precio de Bolsa supera el Precio de Escasez.
2. Embalses por debajo de un umbral configurable.
3. Aportes muy inferiores a la media historica.
4. Variaciones importantes del precio de bolsa (mas de un porcentaje
   configurable en un solo dia).

Este archivo NO descarga datos ni envia nada. Solo revisa lo que ya
esta guardado en la base de datos y devuelve una lista de alertas
en texto, listas para incluir en cualquier informe o correo.
"""

import sys
import os

CARPETA_PROYECTO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(CARPETA_PROYECTO, "BaseDatos"))
sys.path.append(os.path.join(CARPETA_PROYECTO, "Analisis"))
sys.path.append(os.path.join(CARPETA_PROYECTO, "Graficas"))

from base_datos import consultar_precio_escasez_mas_reciente
from estadisticas_precio import calcular_estadisticas, generar_comentario_automatico
from estadisticas_hidrologia import calcular_estadisticas_hidrologia, generar_comentario_hidrologia
from grafico_mensual import generar_grafico_mensual
from grafico_hidrologia import generar_grafico_embalses

# ---------- Umbrales configurables ----------
# Se pueden ajustar estos valores segun el criterio del negocio.

UMBRAL_EMBALSES_BAJO = 0.30            # 30% de capacidad util
UMBRAL_VARIACION_DIARIA_PORCENTUAL = 15.0  # % de cambio en un solo dia


def generar_alertas_precio():
    """
    Revisa las condiciones de alerta relacionadas con el Precio de
    Bolsa: comparacion con el Precio de Escasez, y variaciones
    diarias importantes.

    Retorna:
        Una lista de diccionarios con "tipo", "mensaje",
        "explicacion" y "ruta_grafico". Lista vacia si no hay
        ninguna alerta activa.
    """
    alertas = []

    estadisticas = calcular_estadisticas()
    if estadisticas is None:
        return alertas

    _, valor_escasez = consultar_precio_escasez_mas_reciente()
    explicacion = generar_comentario_automatico(estadisticas)
    ruta_grafico = generar_grafico_mensual()

    # Alerta 1: Precio de Bolsa supera el Precio de Escasez
    if valor_escasez is not None and estadisticas["precio_dia_mas_reciente"] > valor_escasez:
        alertas.append({
            "tipo": "alerta_escasez",
            "mensaje": (
                "El Precio de Bolsa (" + "{:.0f}".format(estadisticas["precio_dia_mas_reciente"])
                + " $/kWh) supero el Precio de Escasez (" + "{:.0f}".format(valor_escasez) + " $/kWh)."
            ),
            "explicacion": explicacion,
            "ruta_grafico": ruta_grafico
        })

    # Alerta 2: variacion diaria importante (en cualquier direccion)
    if estadisticas["variacion_diaria_porcentual"] is not None:
        variacion_absoluta = abs(estadisticas["variacion_diaria_porcentual"])
        if variacion_absoluta >= UMBRAL_VARIACION_DIARIA_PORCENTUAL:
            direccion = "aumento" if estadisticas["variacion_diaria_porcentual"] > 0 else "disminuyo"
            alertas.append({
                "tipo": "alerta_variacion",
                "mensaje": (
                    "El Precio de Bolsa " + direccion + " " + "{:.1f}".format(variacion_absoluta)
                    + "% respecto al dia anterior, una variacion considerada importante (umbral: "
                    + "{:.0f}".format(UMBRAL_VARIACION_DIARIA_PORCENTUAL) + "%)."
                ),
                "explicacion": explicacion,
                "ruta_grafico": ruta_grafico
            })

    return alertas


def generar_alertas_hidrologia():
    """
    Revisa la condicion de alerta relacionada con embalses.

    Retorna:
        Una lista de diccionarios con "tipo", "mensaje",
        "explicacion" y "ruta_grafico". Lista vacia si no hay
        ninguna alerta activa.
    """
    alertas = []

    estadisticas = calcular_estadisticas_hidrologia()
    if estadisticas is None:
        return alertas

    # Alerta: Embalses por debajo del umbral configurado
    if estadisticas["embalses_porcentaje_actual"] < UMBRAL_EMBALSES_BAJO:
        alertas.append({
            "tipo": "alerta_embalses",
            "mensaje": (
                "Los embalses estan en " + "{:.1f}".format(estadisticas["embalses_porcentaje_actual"] * 100)
                + "%, por debajo del umbral de alerta configurado ("
                + "{:.0f}".format(UMBRAL_EMBALSES_BAJO * 100) + "%)."
            ),
            "explicacion": generar_comentario_hidrologia(estadisticas),
            "ruta_grafico": generar_grafico_embalses()
        })

    return alertas


def generar_todas_las_alertas():
    """
    Combina todas las alertas del sistema (precio e hidrologia) en
    una sola lista.

    Retorna:
        Una lista de diccionarios con todas las alertas activas.
    """
    return generar_alertas_precio() + generar_alertas_hidrologia()


if __name__ == "__main__":
    print("Revisando condiciones de alerta...")
    print("")

    todas = generar_todas_las_alertas()

    if len(todas) == 0:
        print("No hay alertas activas en este momento.")
    else:
        print("Se encontraron " + str(len(todas)) + " alerta(s):")
        print("")
        for alerta in todas:
            print("[" + alerta["tipo"] + "] " + alerta["mensaje"])
            print("  Explicacion: " + alerta["explicacion"])
            print("  Grafico: " + str(alerta["ruta_grafico"]))
            print("")
