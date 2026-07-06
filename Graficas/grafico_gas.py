"""
Modulo: grafico_gas.py
Ubicacion: Graficas/grafico_gas.py

Genera el grafico de tendencia de las cantidades de gas natural
ofertadas (en MBTUD) por Ecopetrol en sus convocatorias detectadas,
a lo largo del tiempo.
"""

import sys
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from datetime import datetime

CARPETA_PROYECTO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(CARPETA_PROYECTO, "Analisis"))

from estadisticas_gas import obtener_historico_gas

CARPETA_ACTUAL = os.path.dirname(os.path.abspath(__file__))

COLOR_GAS = "#D9822B"


def generar_grafico_gas():
    """
    Genera el grafico de barras con las cantidades de gas ofertadas
    en cada convocatoria que tenga una cantidad numerica identificada.

    Retorna:
        La ruta del archivo generado, o None si no hay datos.
    """
    historico = obtener_historico_gas()

    if len(historico) == 0:
        print("No hay convocatorias registradas para graficar.")
        return None

    con_cantidad = historico[historico["cantidad_mbtud"].notna()].copy()

    if len(con_cantidad) == 0:
        print("Ninguna convocatoria tiene una cantidad numerica identificada todavia.")
        return None

    con_cantidad = con_cantidad.sort_values("fecha_deteccion")
    con_cantidad["fecha_dt"] = con_cantidad["fecha_deteccion"].apply(lambda f: datetime.strptime(f, "%Y-%m-%d"))

    figura, ejes = plt.subplots(figsize=(11, 5))

    ejes.bar(
        con_cantidad["fecha_dt"], con_cantidad["cantidad_mbtud"],
        color=COLOR_GAS, width=3
    )

    ejes.set_title("Cantidades de Gas Natural Ofertadas (MBTUD)", fontsize=13, fontweight="bold")
    ejes.set_ylabel("MBTUD")
    ejes.set_xlabel("Fecha de deteccion de la convocatoria")
    ejes.grid(True, linestyle="--", alpha=0.4, axis="y")

    figura.autofmt_xdate()
    figura.tight_layout()

    ruta = os.path.join(CARPETA_ACTUAL, "gas_cantidades_ofertadas.png")
    figura.savefig(ruta, dpi=150)
    plt.close(figura)

    print("Grafico de gas generado: " + ruta)
    return ruta


if __name__ == "__main__":
    generar_grafico_gas()
