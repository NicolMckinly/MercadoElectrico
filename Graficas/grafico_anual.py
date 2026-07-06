"""
Modulo: grafico_anual.py
Ubicacion: Graficas/grafico_anual.py

Genera el grafico de tendencia anual del Precio de Bolsa, mostrando
DOS lineas:
1. El precio promedio DIARIO (linea fina, para ver la tendencia real
   dia a dia a lo largo del año).
2. El precio promedio MENSUAL (linea gruesa con marcadores, para
   resumir la tendencia general de cada mes).

Tambien muestra el Precio de Escasez que estuvo vigente en cada mes
especifico (ya que este valor cambia mes a mes), con su etiqueta de
dato correspondiente.

Este grafico se actualiza automaticamente cada vez que se ejecuta,
tomando todo lo que exista en la base de datos hasta ese momento
(no hay que hacer nada especial para "actualizarlo").

El grafico se guarda como una imagen .png dentro de esta misma carpeta.
"""

import sys
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime

CARPETA_PROYECTO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(CARPETA_PROYECTO, "Analisis"))
sys.path.append(os.path.join(CARPETA_PROYECTO, "BaseDatos"))

from combinar_precio import obtener_serie_combinada, COLUMNAS_HORA
from base_datos import consultar_todo_precio_escasez

CARPETA_ACTUAL = os.path.dirname(os.path.abspath(__file__))

COLOR_DIARIO = "#8FB8DE"       # azul claro, para la linea de fondo dia a dia
COLOR_MENSUAL = "#1F4E79"      # azul oscuro, para el resumen mensual
COLOR_ESCASEZ = "#B22222"      # rojo, para el Precio de Escasez


def _valor_escasez_vigente_en_el_mes(historico_escasez, anio, mes):
    """
    Determina cual era el Precio de Escasez vigente en un mes
    especifico, buscando el valor guardado mas reciente que sea
    anterior o igual al final de ese mes.
    """
    if len(historico_escasez) == 0:
        return None

    historico_escasez = historico_escasez.copy()
    historico_escasez["fecha_dt"] = historico_escasez["fecha"].apply(lambda f: datetime.strptime(f, "%Y-%m-%d"))

    if mes == 12:
        fin_del_mes = datetime(anio + 1, 1, 1)
    else:
        fin_del_mes = datetime(anio, mes + 1, 1)

    candidatos = historico_escasez[historico_escasez["fecha_dt"] < fin_del_mes]

    if len(candidatos) == 0:
        return None

    return candidatos.sort_values("fecha_dt").iloc[-1]["valor"]


def _fecha_del_medio_del_mes(anio, mes, ultima_fecha_disponible):
    """
    Calcula una fecha representativa (el punto medio) para ubicar el
    marcador mensual en el eje X, sin salirse del rango de datos
    disponible si el mes actual esta incompleto.
    """
    inicio_mes = datetime(anio, mes, 1)
    if mes == 12:
        fin_mes = datetime(anio + 1, 1, 1)
    else:
        fin_mes = datetime(anio, mes + 1, 1)

    fin_real = min(fin_mes, ultima_fecha_disponible)
    return inicio_mes + (fin_real - inicio_mes) / 2


def generar_grafico_anual():
    """
    Genera y guarda el grafico de tendencia anual (diaria + mensual).

    Retorna:
        La ruta del archivo de imagen generado, o None si no hay
        datos disponibles.
    """
    hoy = datetime.now()
    primer_dia_del_anio = hoy.replace(month=1, day=1).strftime("%Y-%m-%d")
    fecha_de_hoy = hoy.strftime("%Y-%m-%d")

    serie = obtener_serie_combinada(fecha_inicio=primer_dia_del_anio, fecha_fin=fecha_de_hoy)

    if len(serie) == 0:
        print("No hay datos disponibles para el grafico anual todavia.")
        return None

    serie["promedio_diario"] = serie[COLUMNAS_HORA].mean(axis=1)
    serie["fecha_dt"] = serie["fecha"].apply(lambda f: datetime.strptime(f, "%Y-%m-%d"))
    serie = serie.sort_values("fecha_dt")

    serie["anio_mes"] = serie["fecha_dt"].apply(lambda f: (f.year, f.month))
    promedios_mensuales = serie.groupby("anio_mes")["promedio_diario"].mean().reset_index()
    promedios_mensuales = promedios_mensuales.sort_values("anio_mes")

    ultima_fecha_disponible = serie["fecha_dt"].max()

    historico_escasez = consultar_todo_precio_escasez()

    fechas_mensuales = []
    valores_mensuales = []
    valores_escasez = []

    for _, fila in promedios_mensuales.iterrows():
        anio, mes = fila["anio_mes"]
        fechas_mensuales.append(_fecha_del_medio_del_mes(anio, mes, ultima_fecha_disponible))
        valores_mensuales.append(fila["promedio_diario"])
        valores_escasez.append(_valor_escasez_vigente_en_el_mes(historico_escasez, anio, mes))

    figura, ejes = plt.subplots(figsize=(11, 5.5))

    # Linea 1: precio promedio DIARIO (fina, de fondo, para ver la tendencia real)
    ejes.plot(
        serie["fecha_dt"], serie["promedio_diario"],
        color=COLOR_DIARIO, linewidth=1, alpha=0.8,
        label="Precio de Bolsa (promedio diario)"
    )

    # Linea 2: precio promedio MENSUAL (gruesa, con marcadores, resumen del mes)
    ejes.plot(
        fechas_mensuales, valores_mensuales,
        "o-", color=COLOR_MENSUAL, linewidth=2.5, markersize=7,
        label="Precio de Bolsa (promedio mensual)"
    )

    # Etiqueta de dato para cada punto del promedio mensual
    for fecha_x, valor in zip(fechas_mensuales, valores_mensuales):
        ejes.annotate(
            "{:.0f}".format(valor),
            xy=(fecha_x, valor),
            xytext=(0, -14),
            textcoords="offset points",
            ha="center",
            fontsize=8,
            color=COLOR_MENSUAL,
            fontweight="bold"
        )

    # Linea 3: Precio de Escasez vigente en cada mes, con etiqueta de dato
    if any(v is not None for v in valores_escasez):
        ejes.plot(
            fechas_mensuales, valores_escasez,
            "o:", color=COLOR_ESCASEZ, linewidth=2, markersize=6,
            label="Precio de Escasez vigente ese mes"
        )

        for fecha_x, valor in zip(fechas_mensuales, valores_escasez):
            if valor is not None:
                ejes.annotate(
                    "{:.0f}".format(valor),
                    xy=(fecha_x, valor),
                    xytext=(0, 8),
                    textcoords="offset points",
                    ha="center",
                    fontsize=8,
                    color=COLOR_ESCASEZ,
                    fontweight="bold"
                )

    nombre_anio = hoy.strftime("%Y")
    ejes.set_ylabel("Precio ($/kWh)")
    ejes.set_xlabel("Mes")

    ejes.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
    ejes.xaxis.set_major_locator(mdates.MonthLocator())

    ejes.grid(True, linestyle="--", alpha=0.4)
    ejes.legend(loc="upper center", bbox_to_anchor=(0.5, -0.15), ncol=2, frameon=False)

    valores_validos_escasez = [v for v in valores_escasez if v is not None]
    if len(valores_validos_escasez) > 0:
        techo = max(max(valores_validos_escasez), serie["promedio_diario"].max()) * 1.08
        piso = min(serie["promedio_diario"].min(), min(valores_validos_escasez)) * 0.95
        ejes.set_ylim(piso, techo)

    figura.tight_layout()

    nombre_archivo = "precio_bolsa_anual_" + nombre_anio + ".png"
    ruta_completa = os.path.join(CARPETA_ACTUAL, nombre_archivo)

    figura.savefig(ruta_completa, dpi=150)
    plt.close(figura)

    print("Grafico anual generado: " + ruta_completa)
    return ruta_completa


if __name__ == "__main__":
    generar_grafico_anual()
