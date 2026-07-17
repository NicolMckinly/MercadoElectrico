"""
Modulo: grafico_precio_anual_ejecutivo.py
Ubicacion: Reportes/grafico_precio_anual_ejecutivo.py

Genera el grafico de Precio de Bolsa (diario + promedio mensual) y
Precio de Escasez para el Resumen Ejecutivo Quincenal, usando una
ventana de 12 MESES MOVILES: desde ayer (dia n-1, que es el ultimo
dia con datos publicados) hacia atras 365 dias.

Esta ventana se recalcula cada vez que se genera el informe, asi que
"corre" solo dia a dia y mes a mes, sin necesidad de ajustar nada
manualmente.

Es una version independiente de grafico_anual.py (que usa el año
calendario para el informe diario) y no lo modifica ni lo reemplaza.

El grafico se guarda como una imagen .png dentro de esta misma carpeta.
"""

import sys
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import FuncFormatter
from datetime import datetime, timedelta

CARPETA_PROYECTO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(CARPETA_PROYECTO, "Analisis"))
sys.path.append(os.path.join(CARPETA_PROYECTO, "BaseDatos"))

from combinar_precio import obtener_serie_combinada, COLUMNAS_HORA
from base_datos import consultar_todo_precio_escasez
from zona_horaria import ahora_colombia

CARPETA_ACTUAL = os.path.dirname(os.path.abspath(__file__))

COLOR_DIARIO = "#8FB8DE"
COLOR_MENSUAL = "#1F4E79"
COLOR_ESCASEZ = "#B22222"

LIMITE_SUPERIOR_MINIMO = 1300

MESES_ABREVIADOS_ESPANOL = {
    1: "Ene", 2: "Feb", 3: "Mar", 4: "Abr", 5: "May", 6: "Jun",
    7: "Jul", 8: "Ago", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dic",
}


def _formatear_mes_en_espanol(valor_x, posicion=None):
    fecha = mdates.num2date(valor_x)
    return MESES_ABREVIADOS_ESPANOL[fecha.month]


def _valor_escasez_vigente_en(historico_escasez, fecha_referencia):
    """
    Determina cual era el Precio de Escasez vigente en una fecha
    especifica, buscando el valor guardado mas reciente que sea
    anterior o igual a esa fecha.
    """
    if len(historico_escasez) == 0:
        return None

    historico_escasez = historico_escasez.copy()
    historico_escasez["fecha_dt"] = historico_escasez["fecha"].apply(lambda f: datetime.strptime(f, "%Y-%m-%d"))

    candidatos = historico_escasez[historico_escasez["fecha_dt"] <= fecha_referencia]

    if len(candidatos) == 0:
        return None

    return candidatos.sort_values("fecha_dt").iloc[-1]["valor"]


def generar_grafico_precio_anual_ejecutivo():
    """
    Genera el grafico de Precio de Bolsa vs Precio de Escasez de los
    ultimos 12 meses moviles (terminando ayer), para el Resumen
    Ejecutivo Quincenal.

    Retorna:
        La ruta del archivo generado, o None si no hay datos.
    """
    hoy = ahora_colombia()
    fecha_fin = (hoy - timedelta(days=1)).replace(tzinfo=None)
    fecha_inicio = fecha_fin - timedelta(days=365)

    serie = obtener_serie_combinada(
        fecha_inicio=fecha_inicio.strftime("%Y-%m-%d"),
        fecha_fin=fecha_fin.strftime("%Y-%m-%d")
    )

    if len(serie) == 0:
        print("No hay datos disponibles para el grafico de precio (ultimos 12 meses).")
        return None

    serie["promedio_diario"] = serie[COLUMNAS_HORA].mean(axis=1)
    serie["fecha_dt"] = serie["fecha"].apply(lambda f: datetime.strptime(f, "%Y-%m-%d"))
    serie = serie.sort_values("fecha_dt")

    serie["anio_mes"] = serie["fecha_dt"].apply(lambda f: (f.year, f.month))
    promedios_mensuales = serie.groupby("anio_mes")["promedio_diario"].mean().reset_index()
    promedios_mensuales = promedios_mensuales.sort_values("anio_mes")

    historico_escasez = consultar_todo_precio_escasez()

    fechas_mensuales = []
    valores_mensuales = []
    valores_escasez = []

    for _, fila in promedios_mensuales.iterrows():
        anio, mes = fila["anio_mes"]
        dias_del_mes_en_serie = serie[(serie["fecha_dt"].dt.year == anio) & (serie["fecha_dt"].dt.month == mes)]
        fecha_representativa = dias_del_mes_en_serie["fecha_dt"].median()
        fechas_mensuales.append(fecha_representativa)
        valores_mensuales.append(fila["promedio_diario"])
        valores_escasez.append(_valor_escasez_vigente_en(historico_escasez, fecha_representativa))

    figura, ejes = plt.subplots(figsize=(11, 5.5))

    ejes.plot(serie["fecha_dt"], serie["promedio_diario"], color=COLOR_DIARIO, linewidth=1, alpha=0.8, label="Precio de Bolsa (promedio diario)")
    ejes.plot(fechas_mensuales, valores_mensuales, "o-", color=COLOR_MENSUAL, linewidth=2.5, markersize=7, label="Precio de Bolsa (promedio mensual)")

    for fecha_x, valor in zip(fechas_mensuales, valores_mensuales):
        ejes.annotate("{:.0f}".format(valor), xy=(fecha_x, valor), xytext=(0, -14), textcoords="offset points",
                       ha="center", fontsize=8, color=COLOR_MENSUAL, fontweight="bold")

    if any(v is not None for v in valores_escasez):
        ejes.plot(fechas_mensuales, valores_escasez, "o:", color=COLOR_ESCASEZ, linewidth=2, markersize=6, label="Precio de Escasez")
        for fecha_x, valor in zip(fechas_mensuales, valores_escasez):
            if valor is not None:
                ejes.annotate("{:.0f}".format(valor), xy=(fecha_x, valor), xytext=(0, 8), textcoords="offset points",
                               ha="center", fontsize=8, color=COLOR_ESCASEZ, fontweight="bold")

    ejes.set_title("Precio de Bolsa vs Precio de Escasez", fontsize=13, fontweight="bold")
    ejes.set_ylabel("Precio ($/kWh)")
    ejes.set_xlabel("Mes")
    ejes.xaxis.set_major_formatter(FuncFormatter(_formatear_mes_en_espanol))
    ejes.xaxis.set_major_locator(mdates.MonthLocator())
    ejes.grid(True, linestyle="--", alpha=0.4)
    ejes.legend(loc="upper center", bbox_to_anchor=(0.5, -0.15), ncol=3, frameon=False)

    valores_validos_escasez = [v for v in valores_escasez if v is not None]
    limite_superior = LIMITE_SUPERIOR_MINIMO
    if len(valores_validos_escasez) > 0:
        limite_superior = max(LIMITE_SUPERIOR_MINIMO, max(valores_validos_escasez) * 1.08, serie["promedio_diario"].max() * 1.08)
    ejes.set_ylim(0, limite_superior)

    figura.tight_layout()
    ruta = os.path.join(CARPETA_ACTUAL, "precio_bolsa_anual_ejecutivo.png")
    figura.savefig(ruta, dpi=150)
    plt.close(figura)

    print("Grafico de precio (12 meses moviles) generado: " + ruta)
    return ruta


if __name__ == "__main__":
    generar_grafico_precio_anual_ejecutivo()
