"""
Modulo: grafico_hidrologia.py
Ubicacion: Graficas/grafico_hidrologia.py

Genera dos graficos para el Modulo 3 (Variables Hidrologicas):
1. Tendencia de Embalses (% de capacidad util) en los ultimos 30 dias
   disponibles.
2. Aportes Hidricos comparados contra la Media Historica, en los
   ultimos 30 dias disponibles.

Los graficos se guardan como imagenes .png dentro de esta misma carpeta.
"""

import sys
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime

CARPETA_PROYECTO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(CARPETA_PROYECTO, "BaseDatos"))

from base_datos import consultar_todo_variables_hidrologicas, consultar_todo_senda_referencia

CARPETA_ACTUAL = os.path.dirname(os.path.abspath(__file__))

COLOR_EMBALSES = "#1F6F50"      # verde, asociado al agua/embalses
COLOR_SENDA = "#B22222"         # rojo, para la senda de referencia
COLOR_APORTES = "#2E86C1"       # azul
COLOR_MEDIA_HISTORICA = "#95A5A6"  # gris, para la referencia
COLOR_PORCENTAJE = "#D9822B"    # naranja, para el eje secundario de %


def generar_grafico_embalses():
    """
    Genera el grafico de tendencia de Embalses (%) de los ultimos
    30 dias disponibles, junto con la Senda de Referencia vigente
    (Resolucion CREG 209 de 2020) en la misma grafica.

    Retorna:
        La ruta del archivo generado, o None si no hay datos.
    """
    datos = consultar_todo_variables_hidrologicas()

    if len(datos) == 0:
        print("No hay datos de embalses disponibles todavia.")
        return None

    datos = datos.sort_values("fecha").tail(30)
    datos["fecha_dt"] = datos["fecha"].apply(lambda f: datetime.strptime(f, "%Y-%m-%d"))
    datos["embalses_pct"] = datos["embalses_porcentaje"] * 100

    senda = consultar_todo_senda_referencia()

    figura, ejes = plt.subplots(figsize=(11, 5))

    ejes.plot(datos["fecha_dt"], datos["embalses_pct"], "o-", color=COLOR_EMBALSES, linewidth=2, markersize=4, label="Embalse SIN (%)")

    if len(senda) > 0:
        senda = senda.copy()
        senda["fecha_dt"] = senda["fecha"].apply(lambda f: datetime.strptime(f, "%Y-%m-%d"))
        senda["valor_pct"] = senda["valor"] * 100

        # Solo mostramos la senda en el mismo rango de fechas que el embalse real
        fecha_min_grafico = datos["fecha_dt"].min()
        fecha_max_grafico = datos["fecha_dt"].max()
        senda_visible = senda[(senda["fecha_dt"] >= fecha_min_grafico) & (senda["fecha_dt"] <= fecha_max_grafico)]

        if len(senda_visible) > 0:
            ejes.plot(senda_visible["fecha_dt"], senda_visible["valor_pct"], "--", color=COLOR_SENDA, linewidth=2, label="Senda de Referencia")

    ejes.set_title("Nivel de Embalse %", fontsize=13, fontweight="bold")
    ejes.set_ylabel("Capacidad util (%)")
    ejes.set_xlabel("Fecha")
    ejes.xaxis.set_major_formatter(mdates.DateFormatter("%d-%b"))
    ejes.grid(True, linestyle="--", alpha=0.4)
    ejes.legend(loc="upper center", bbox_to_anchor=(0.5, -0.15), ncol=2, frameon=False)

    figura.tight_layout()
    ruta = os.path.join(CARPETA_ACTUAL, "embalses_tendencia.png")
    figura.savefig(ruta, dpi=150)
    plt.close(figura)

    print("Grafico de embalses generado: " + ruta)
    return ruta


def generar_grafico_aportes():
    """
    Genera el grafico de Aportes Hidricos vs Media Historica, de los
    ultimos 30 dias disponibles.

    Retorna:
        La ruta del archivo generado, o None si no hay datos.
    """
    datos = consultar_todo_variables_hidrologicas()

    if len(datos) == 0:
        print("No hay datos de aportes disponibles todavia.")
        return None

    datos = datos.sort_values("fecha").tail(30)
    datos["fecha_dt"] = datos["fecha"].apply(lambda f: datetime.strptime(f, "%Y-%m-%d"))

    # Convertimos de kWh a GWh (dividiendo entre 1,000,000) para que
    # los numeros sean mas legibles en el grafico
    datos["aportes_gwh"] = datos["aportes_energia"] / 1_000_000
    datos["media_historica_gwh"] = datos["aportes_media_historica"] / 1_000_000
    datos["aportes_pct"] = datos["aportes_porcentaje"] * 100

    figura, ejes = plt.subplots(figsize=(11, 5))

    ejes.plot(datos["fecha_dt"], datos["aportes_gwh"], "o-", color=COLOR_APORTES, linewidth=2, markersize=4, label="Aportes SIN (GWh/dia)")
    ejes.plot(datos["fecha_dt"], datos["media_historica_gwh"], "--", color=COLOR_MEDIA_HISTORICA, linewidth=2, label="Media Historica (GWh/dia)")

    ejes.set_title("Aportes SIN", fontsize=13, fontweight="bold")
    ejes.set_ylabel("GWh/dia")
    ejes.set_xlabel("Fecha")
    ejes.xaxis.set_major_formatter(mdates.DateFormatter("%d-%b"))
    ejes.grid(True, linestyle="--", alpha=0.4)

    # Eje secundario para el porcentaje, ya que se mide en una escala distinta
    ejes_pct = ejes.twinx()
    ejes_pct.plot(datos["fecha_dt"], datos["aportes_pct"], "o:", color=COLOR_PORCENTAJE, linewidth=1.8, markersize=4, label="Aportes SIN (%)")
    ejes_pct.set_ylabel("Aportes SIN (%)")

    # Combinamos las leyendas de ambos ejes en una sola
    lineas_1, etiquetas_1 = ejes.get_legend_handles_labels()
    lineas_2, etiquetas_2 = ejes_pct.get_legend_handles_labels()
    ejes.legend(lineas_1 + lineas_2, etiquetas_1 + etiquetas_2, loc="upper center", bbox_to_anchor=(0.5, -0.15), ncol=3, frameon=False)

    figura.tight_layout()
    ruta = os.path.join(CARPETA_ACTUAL, "aportes_vs_media_historica.png")
    figura.savefig(ruta, dpi=150)
    plt.close(figura)

    print("Grafico de aportes generado: " + ruta)
    return ruta


if __name__ == "__main__":
    generar_grafico_embalses()
    generar_grafico_aportes()
