"""
Modulo: grafico_comparacion_imar_bolsa.py
Ubicacion: Graficas/grafico_comparacion_imar_bolsa.py

Genera el grafico de linea comparando, dia a dia, el promedio del
IMAR (linea verde) contra el promedio del Precio de Bolsa real
(linea azul), para el mes vigente (desde el dia 1 hasta hoy), e
incluye tambien el Precio de Escasez vigente como linea de referencia
(roja, punteada).

A diferencia del grafico mensual (grafico_mensual.py), que combina
ambas fuentes en UNA sola linea (usando IMAR solo cuando falta el
precio real), este grafico muestra las DOS lineas por separado, para
poder ver visualmente que tan cerca estuvo el IMAR (pronostico) del
precio real que finalmente se dio ese dia.

El eje Y va siempre de 0 a 1300, para que todas las graficas del
informe compartan la misma base y escala de referencia visual.

El grafico se guarda como una imagen .png dentro de esta misma carpeta.
"""

import sys
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd

CARPETA_PROYECTO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(CARPETA_PROYECTO, "Analisis"))
sys.path.append(os.path.join(CARPETA_PROYECTO, "BaseDatos"))

from combinar_precio import COLUMNAS_HORA
from base_datos import consultar_todo_precio_bolsa, consultar_todo_imar, consultar_precio_escasez_mas_reciente
from zona_horaria import ahora_colombia

CARPETA_ACTUAL = os.path.dirname(os.path.abspath(__file__))

COLOR_IMAR_VERDE = "#1F8A4C"
COLOR_PRECIO_AZUL = "#1F4E79"
COLOR_ESCASEZ = "#B22222"

LIMITE_SUPERIOR_EJE_Y = 1300

MESES_EN_ESPANOL = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre",
}


def generar_grafico_comparacion_imar_bolsa():
    """
    Genera y guarda el grafico comparativo IMAR vs Precio de Bolsa
    real, del mes vigente (dia 1 hasta hoy, hora Colombia), con el
    Precio de Escasez vigente como linea de referencia.

    Retorna:
        La ruta del archivo de imagen generado, o None si no hay
        datos disponibles todavia para el mes.
    """
    hoy = ahora_colombia()
    primer_dia_del_mes = hoy.replace(day=1).strftime("%Y-%m-%d")
    fecha_hoy_texto = hoy.strftime("%Y-%m-%d")

    precio_bolsa = consultar_todo_precio_bolsa()
    imar = consultar_todo_imar()

    precio_bolsa_mes = precio_bolsa[
        (precio_bolsa["fecha"] >= primer_dia_del_mes) & (precio_bolsa["fecha"] <= fecha_hoy_texto)
    ].copy()
    imar_mes = imar[
        (imar["fecha"] >= primer_dia_del_mes) & (imar["fecha"] <= fecha_hoy_texto)
    ].copy()

    if len(precio_bolsa_mes) == 0 and len(imar_mes) == 0:
        print("No hay datos disponibles todavia para el grafico comparativo IMAR vs Precio de Bolsa.")
        return None

    precio_bolsa_mes["promedio_diario"] = precio_bolsa_mes[COLUMNAS_HORA].mean(axis=1)
    imar_mes["promedio_diario"] = imar_mes[COLUMNAS_HORA].mean(axis=1)

    precio_bolsa_mes["fecha_dt"] = pd.to_datetime(precio_bolsa_mes["fecha"])
    imar_mes["fecha_dt"] = pd.to_datetime(imar_mes["fecha"])

    precio_bolsa_mes = precio_bolsa_mes.sort_values("fecha_dt")
    imar_mes = imar_mes.sort_values("fecha_dt")

    nombre_mes = MESES_EN_ESPANOL[hoy.month] + " " + str(hoy.year)

    figura, ejes = plt.subplots(figsize=(11, 5.5))

    ejes.plot(
        imar_mes["fecha_dt"], imar_mes["promedio_diario"],
        "o-", color=COLOR_IMAR_VERDE, linewidth=2.5, markersize=6,
        label="IMAR"
    )
    ejes.plot(
        precio_bolsa_mes["fecha_dt"], precio_bolsa_mes["promedio_diario"],
        "o-", color=COLOR_PRECIO_AZUL, linewidth=2.5, markersize=6,
        label="Precio de Bolsa real"
    )

    _, valor_escasez = consultar_precio_escasez_mas_reciente()
    if valor_escasez is not None:
        ejes.axhline(
            y=valor_escasez,
            color=COLOR_ESCASEZ,
            linestyle=":",
            linewidth=2,
            label="Precio de Escasez"
        )

    ejes.set_title("IMAR vs Precio de Bolsa Real (" + nombre_mes + ")", fontsize=13, fontweight="bold")
    ejes.set_ylabel("Precio promedio diario ($/kWh)")
    ejes.set_xlabel("Dia del mes")

    ejes.xaxis.set_major_formatter(mdates.DateFormatter("%d"))
    ejes.xaxis.set_major_locator(mdates.DayLocator())

    ejes.set_ylim(0, LIMITE_SUPERIOR_EJE_Y)
    ejes.grid(True, linestyle="--", alpha=0.4)
    ejes.legend(loc="upper center", bbox_to_anchor=(0.5, -0.15), ncol=3, frameon=False)

    figura.tight_layout()

    nombre_archivo = "comparacion_imar_bolsa_" + hoy.strftime("%Y_%m") + ".png"
    ruta_completa = os.path.join(CARPETA_ACTUAL, nombre_archivo)

    figura.savefig(ruta_completa, dpi=150)
    plt.close(figura)

    print("Grafico de comparacion IMAR vs Precio de Bolsa generado: " + ruta_completa)
    return ruta_completa


if __name__ == "__main__":
    generar_grafico_comparacion_imar_bolsa()
