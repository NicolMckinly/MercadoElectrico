"""
Modulo: grafico_hidrologia.py
Ubicacion: Graficas/grafico_hidrologia.py

Genera los graficos para el Modulo 3 (Variables Hidrologicas):
1. Nivel de Embalse (%) en los ultimos 30 dias disponibles, mostrado
   como area apilada en azul claro, junto con la Senda de Referencia
   (linea punteada azul oscuro). Usado en el informe de variables.
2. Caudal (Aportes Hidricos, en GWh/dia) mostrado como area apilada
   en verde claro, comparado contra la Media Historica (linea
   punteada gris) y el porcentaje de Aportes SIN (linea punteada en
   el eje secundario, verde oscuro). Usado en el informe de variables.
3. Version de Embalses de los ULTIMOS 12 MESES MOVILES (terminando
   ayer), usada en el Resumen Ejecutivo Quincenal.
4. Version de Aportes de los ULTIMOS 12 MESES MOVILES (terminando
   ayer), usada en el Resumen Ejecutivo Quincenal.

Todos los graficos tienen su eje Y siempre partiendo desde 0.

Los graficos se guardan como imagenes .png dentro de esta misma carpeta.
"""

import sys
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta

CARPETA_PROYECTO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(CARPETA_PROYECTO, "BaseDatos"))

from base_datos import consultar_todo_variables_hidrologicas, consultar_todo_senda_referencia
from zona_horaria import ahora_colombia

CARPETA_ACTUAL = os.path.dirname(os.path.abspath(__file__))

COLOR_EMBALSES = "#7FB3D5"      # azul claro, para el area de Nivel de Embalse
COLOR_SENDA = "#1F4E79"         # azul oscuro, para la senda de referencia
COLOR_APORTES = "#7DCEA0"       # verde claro, para el area de Caudal
COLOR_MEDIA_HISTORICA = "#95A5A6"  # gris, para la referencia
COLOR_PORCENTAJE = "#1F6F50"    # verde oscuro, para el eje secundario de %


def generar_grafico_embalses():
    """
    Genera el grafico de Nivel de Embalse (%) de los ultimos 30 dias
    disponibles, como area apilada, junto con la Senda de Referencia
    vigente (Resolucion CREG 209 de 2020) como linea punteada.

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

    ejes.stackplot(datos["fecha_dt"], datos["embalses_pct"], colors=[COLOR_EMBALSES], alpha=0.85, labels=["Embalse SIN (%)"])

    if len(senda) > 0:
        senda = senda.copy()
        senda["fecha_dt"] = senda["fecha"].apply(lambda f: datetime.strptime(f, "%Y-%m-%d"))
        senda["valor_pct"] = senda["valor"] * 100

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
    ejes.set_ylim(bottom=0)
    ejes.legend(loc="upper center", bbox_to_anchor=(0.5, -0.15), ncol=2, frameon=False)

    figura.tight_layout()
    ruta = os.path.join(CARPETA_ACTUAL, "embalses_tendencia.png")
    figura.savefig(ruta, dpi=150)
    plt.close(figura)

    print("Grafico de embalses generado: " + ruta)
    return ruta


def generar_grafico_aportes():
    """
    Genera el grafico de Caudal (Aportes Hidricos, GWh/dia) como
    area apilada, comparado contra la Media Historica (linea
    punteada gris) y el porcentaje de Aportes SIN (linea punteada
    en el eje secundario).

    Retorna:
        La ruta del archivo generado, o None si no hay datos.
    """
    datos = consultar_todo_variables_hidrologicas()

    if len(datos) == 0:
        print("No hay datos de aportes disponibles todavia.")
        return None

    datos = datos.sort_values("fecha").tail(30)
    datos["fecha_dt"] = datos["fecha"].apply(lambda f: datetime.strptime(f, "%Y-%m-%d"))

    datos["aportes_gwh"] = datos["aportes_energia"] / 1_000_000
    datos["media_historica_gwh"] = datos["aportes_media_historica"] / 1_000_000
    datos["aportes_pct"] = datos["aportes_porcentaje"] * 100

    figura, ejes = plt.subplots(figsize=(11, 5))

    ejes.stackplot(datos["fecha_dt"], datos["aportes_gwh"], colors=[COLOR_APORTES], alpha=0.85, labels=["Caudal GWh/día"])
    ejes.plot(datos["fecha_dt"], datos["media_historica_gwh"], "--", color=COLOR_MEDIA_HISTORICA, linewidth=2, label="Media Historica (GWh/dia)")

    ejes.set_title("Aportes SIN", fontsize=13, fontweight="bold")
    ejes.set_ylabel("GWh/dia")
    ejes.set_xlabel("Fecha")
    ejes.xaxis.set_major_formatter(mdates.DateFormatter("%d-%b"))
    ejes.grid(True, linestyle="--", alpha=0.4)
    ejes.set_ylim(bottom=0)

    ejes_pct = ejes.twinx()
    ejes_pct.plot(datos["fecha_dt"], datos["aportes_pct"], "o:", color=COLOR_PORCENTAJE, linewidth=1.8, markersize=4, label="Aportes SIN (%)")
    ejes_pct.set_ylabel("Aportes SIN (%)")
    ejes_pct.set_ylim(bottom=0)

    lineas_1, etiquetas_1 = ejes.get_legend_handles_labels()
    lineas_2, etiquetas_2 = ejes_pct.get_legend_handles_labels()
    ejes.legend(lineas_1 + lineas_2, etiquetas_1 + etiquetas_2, loc="upper center", bbox_to_anchor=(0.5, -0.15), ncol=3, frameon=False)

    figura.tight_layout()
    ruta = os.path.join(CARPETA_ACTUAL, "aportes_vs_media_historica.png")
    figura.savefig(ruta, dpi=150)
    plt.close(figura)

    print("Grafico de aportes generado: " + ruta)
    return ruta


def generar_grafico_embalses_anual_ejecutivo():
    """
    Genera el grafico de Nivel de Embalse (%) de los ULTIMOS 12 MESES
    MOVILES (terminando ayer), para el Resumen Ejecutivo Quincenal.
    Version independiente de generar_grafico_embalses() (que usa
    los ultimos 30 dias para el informe de variables).

    Retorna:
        La ruta del archivo generado, o None si no hay datos.
    """
    hoy = ahora_colombia()
    fecha_fin = (hoy - timedelta(days=1)).replace(tzinfo=None)
    fecha_inicio_texto = (fecha_fin - timedelta(days=365)).strftime("%Y-%m-%d")
    fecha_fin_texto = fecha_fin.strftime("%Y-%m-%d")

    datos = consultar_todo_variables_hidrologicas()

    if len(datos) == 0:
        print("No hay datos de embalses disponibles todavia.")
        return None

    datos = datos[(datos["fecha"] >= fecha_inicio_texto) & (datos["fecha"] <= fecha_fin_texto)]
    if len(datos) == 0:
        print("No hay datos de embalses en el rango de los ultimos 12 meses.")
        return None

    datos = datos.sort_values("fecha")
    datos["fecha_dt"] = datos["fecha"].apply(lambda f: datetime.strptime(f, "%Y-%m-%d"))
    datos["embalses_pct"] = datos["embalses_porcentaje"] * 100

    senda = consultar_todo_senda_referencia()

    figura, ejes = plt.subplots(figsize=(11, 5))

    ejes.stackplot(datos["fecha_dt"], datos["embalses_pct"], colors=[COLOR_EMBALSES], alpha=0.85, labels=["Embalse SIN (%)"])

    if len(senda) > 0:
        senda = senda.copy()
        senda["fecha_dt"] = senda["fecha"].apply(lambda f: datetime.strptime(f, "%Y-%m-%d"))
        senda["valor_pct"] = senda["valor"] * 100
        senda_visible = senda[(senda["fecha_dt"] >= datos["fecha_dt"].min()) & (senda["fecha_dt"] <= datos["fecha_dt"].max())]
        if len(senda_visible) > 0:
            ejes.plot(senda_visible["fecha_dt"], senda_visible["valor_pct"], "--", color=COLOR_SENDA, linewidth=2, label="Senda de Referencia")

    ejes.set_title("Nivel de Embalse % - Últimos 12 Meses", fontsize=13, fontweight="bold")
    ejes.set_ylabel("Capacidad util (%)")
    ejes.set_xlabel("Fecha")
    ejes.xaxis.set_major_formatter(mdates.DateFormatter("%b-%y"))
    ejes.xaxis.set_major_locator(mdates.MonthLocator())
    ejes.grid(True, linestyle="--", alpha=0.4)
    ejes.set_ylim(bottom=0)
    ejes.legend(loc="upper center", bbox_to_anchor=(0.5, -0.15), ncol=2, frameon=False)

    figura.tight_layout()
    ruta = os.path.join(CARPETA_ACTUAL, "embalses_tendencia_anual_ejecutivo.png")
    figura.savefig(ruta, dpi=150)
    plt.close(figura)

    print("Grafico de embalses (12 meses moviles) generado: " + ruta)
    return ruta


def generar_grafico_aportes_anual_ejecutivo():
    """
    Genera el grafico de Caudal (Aportes Hidricos) de los ULTIMOS 12
    MESES MOVILES (terminando ayer), para el Resumen Ejecutivo
    Quincenal. Version independiente de generar_grafico_aportes()
    (que usa los ultimos 30 dias para el informe de variables).

    Retorna:
        La ruta del archivo generado, o None si no hay datos.
    """
    hoy = ahora_colombia()
    fecha_fin = (hoy - timedelta(days=1)).replace(tzinfo=None)
    fecha_inicio_texto = (fecha_fin - timedelta(days=365)).strftime("%Y-%m-%d")
    fecha_fin_texto = fecha_fin.strftime("%Y-%m-%d")

    datos = consultar_todo_variables_hidrologicas()

    if len(datos) == 0:
        print("No hay datos de aportes disponibles todavia.")
        return None

    datos = datos[(datos["fecha"] >= fecha_inicio_texto) & (datos["fecha"] <= fecha_fin_texto)]
    if len(datos) == 0:
        print("No hay datos de aportes en el rango de los ultimos 12 meses.")
        return None

    datos = datos.sort_values("fecha")
    datos["fecha_dt"] = datos["fecha"].apply(lambda f: datetime.strptime(f, "%Y-%m-%d"))

    datos["aportes_gwh"] = datos["aportes_energia"] / 1_000_000
    datos["media_historica_gwh"] = datos["aportes_media_historica"] / 1_000_000
    datos["aportes_pct"] = datos["aportes_porcentaje"] * 100

    figura, ejes = plt.subplots(figsize=(11, 5))

    ejes.stackplot(datos["fecha_dt"], datos["aportes_gwh"], colors=[COLOR_APORTES], alpha=0.85, labels=["Caudal GWh/día"])
    ejes.plot(datos["fecha_dt"], datos["media_historica_gwh"], "--", color=COLOR_MEDIA_HISTORICA, linewidth=2, label="Media Historica (GWh/dia)")

    ejes.set_title("Aportes SIN - Últimos 12 Meses", fontsize=13, fontweight="bold")
    ejes.set_ylabel("GWh/dia")
    ejes.set_xlabel("Fecha")
    ejes.xaxis.set_major_formatter(mdates.DateFormatter("%b-%y"))
    ejes.xaxis.set_major_locator(mdates.MonthLocator())
    ejes.grid(True, linestyle="--", alpha=0.4)
    ejes.set_ylim(bottom=0)

    ejes_pct = ejes.twinx()
    ejes_pct.plot(datos["fecha_dt"], datos["aportes_pct"], "o:", color=COLOR_PORCENTAJE, linewidth=1.8, markersize=3, label="Aportes SIN (%)")
    ejes_pct.set_ylabel("Aportes SIN (%)")
    ejes_pct.set_ylim(bottom=0)

    lineas_1, etiquetas_1 = ejes.get_legend_handles_labels()
    lineas_2, etiquetas_2 = ejes_pct.get_legend_handles_labels()
    ejes.legend(lineas_1 + lineas_2, etiquetas_1 + etiquetas_2, loc="upper center", bbox_to_anchor=(0.5, -0.15), ncol=3, frameon=False)

    figura.tight_layout()
    ruta = os.path.join(CARPETA_ACTUAL, "aportes_vs_media_historica_anual_ejecutivo.png")
    figura.savefig(ruta, dpi=150)
    plt.close(figura)

    print("Grafico de aportes (12 meses moviles) generado: " + ruta)
    return ruta


if __name__ == "__main__":
    generar_grafico_embalses()
    generar_grafico_aportes()
