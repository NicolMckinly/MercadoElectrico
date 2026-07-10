"""
Modulo: grafico_mensual.py
Ubicacion: Graficas/grafico_mensual.py

Genera el grafico del Precio de Bolsa del mes vigente (desde el dia 1
del mes actual hasta hoy), usando la serie combinada de Precio de
Bolsa real e IMAR, para que nunca haya espacios vacios.

Los dias que vienen del Precio de Bolsa real se muestran con una
linea solida. Los dias que vienen del IMAR (porque el precio real
aun no ha sido publicado) se muestran con una linea punteada y en
un color distinto, para dejar claro que es un dato provisional.

Los nombres de los meses se traducen manualmente al espanol, porque
el servidor donde corre el sistema (GitHub Actions) no tiene
instalado el idioma espanol, y usar strftime("%B") directamente
mostraria el mes en ingles.

La fecha de "hoy" se calcula con ahora_colombia() (ver
BaseDatos/zona_horaria.py) en vez de datetime.now(), para que el
sistema siempre use la hora real de Colombia y no la hora UTC del
servidor (que va 5 horas adelante).

El eje Y siempre parte desde 0, y su limite superior es el mayor
valor entre 1300 y el Precio de Escasez (mas un pequeno margen), para
que la etiqueta del Precio de Escasez nunca quede cortada si en algun
mes ese valor supera los 1300.

El grafico se guarda como una imagen .png dentro de esta misma carpeta.
"""

import sys
import os
import matplotlib
matplotlib.use("Agg")  # Modo sin pantalla, para poder correr sin ventanas graficas
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta

CARPETA_PROYECTO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(CARPETA_PROYECTO, "Analisis"))
sys.path.append(os.path.join(CARPETA_PROYECTO, "BaseDatos"))

from combinar_precio import obtener_serie_combinada, COLUMNAS_HORA
from base_datos import consultar_precio_escasez_mas_reciente
from zona_horaria import ahora_colombia

CARPETA_ACTUAL = os.path.dirname(os.path.abspath(__file__))

# Colores corporativos (se pueden ajustar mas adelante en el Modulo 10 de diseno)
COLOR_PRECIO_REAL = "#1F4E79"   # azul oscuro
COLOR_IMAR = "#D9822B"          # naranja
COLOR_ESCASEZ = "#B22222"       # rojo ladrillo

LIMITE_SUPERIOR_MINIMO = 1300

MESES_EN_ESPANOL = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre",
}


def generar_grafico_mensual():
    """
    Genera y guarda el grafico del mes vigente.

    Retorna:
        La ruta del archivo de imagen generado.
    """
    hoy = ahora_colombia()
    primer_dia_del_mes = hoy.replace(day=1).strftime("%Y-%m-%d")
    # Incluimos tambien el dia de MANANA, ya que el IMAR normalmente
    # ya esta publicado con un dia de anticipacion.
    manana = (hoy + timedelta(days=1)).strftime("%Y-%m-%d")

    serie = obtener_serie_combinada(fecha_inicio=primer_dia_del_mes, fecha_fin=manana)

    if len(serie) == 0:
        print("No hay datos disponibles para el mes vigente todavia.")
        return None

    # Calculamos el promedio diario (promedio de las 24 horas de cada dia)
    serie["promedio_diario"] = serie[COLUMNAS_HORA].mean(axis=1)
    serie["fecha_dt"] = serie["fecha"].apply(lambda f: datetime.strptime(f, "%Y-%m-%d"))
    serie = serie.sort_values("fecha_dt")

    figura, ejes = plt.subplots(figsize=(11, 5.5))

    # Separamos los dias por fuente, para poder darles estilos distintos,
    # pero conectando visualmente la linea entre ambos tramos.
    dias_precio_real = serie[serie["fuente"] == "Precio Bolsa"]
    dias_imar = serie[serie["fuente"] == "IMAR"]

    ejes.plot(
        serie["fecha_dt"], serie["promedio_diario"],
        color="#CCCCCC", linewidth=1, zorder=1
    )

    ejes.plot(
        dias_precio_real["fecha_dt"], dias_precio_real["promedio_diario"],
        "o-", color=COLOR_PRECIO_REAL, linewidth=2.5, markersize=6,
        label="Precio de Bolsa (real)", zorder=2
    )

    ejes.plot(
        dias_imar["fecha_dt"], dias_imar["promedio_diario"],
        "o--", color=COLOR_IMAR, linewidth=2.5, markersize=6,
        label="IMAR", zorder=2
    )

    # Etiqueta de dato en cada punto, mostrando el precio promedio del dia
    for _, fila in serie.iterrows():
        color_etiqueta = COLOR_PRECIO_REAL if fila["fuente"] == "Precio Bolsa" else COLOR_IMAR
        ejes.annotate(
            "{:.0f}".format(fila["promedio_diario"]),
            xy=(fila["fecha_dt"], fila["promedio_diario"]),
            xytext=(0, 10),
            textcoords="offset points",
            ha="center",
            fontsize=8,
            color=color_etiqueta,
            fontweight="bold"
        )

    nombre_mes = MESES_EN_ESPANOL[hoy.month] + " " + str(hoy.year)

    # Linea horizontal de referencia con el Precio de Escasez vigente del mes
    fecha_escasez, valor_escasez = consultar_precio_escasez_mas_reciente()

    limite_superior = LIMITE_SUPERIOR_MINIMO
    if valor_escasez is not None and valor_escasez * 1.06 > limite_superior:
        limite_superior = valor_escasez * 1.06

    # El eje Y siempre parte desde 0, y llega hasta el mayor valor
    # entre 1300 y el Precio de Escasez (con margen), para compartir
    # la misma base visual con las demas graficas del informe.
    ejes.set_ylim(0, limite_superior)

    if valor_escasez is not None:
        ejes.axhline(
            y=valor_escasez,
            color=COLOR_ESCASEZ,
            linestyle=":",
            linewidth=2,
            label="Precio de Escasez"
        )

        # Etiqueta con el valor exacto, ubicada sobre el primer dia del grafico
        primer_fecha = serie["fecha_dt"].iloc[0]
        ejes.annotate(
            "{:.0f}".format(valor_escasez),
            xy=(primer_fecha, valor_escasez),
            xytext=(0, 6),
            textcoords="offset points",
            ha="left",
            fontsize=9,
            color=COLOR_ESCASEZ,
            fontweight="bold",
            clip_on=False
        )

    ejes.set_title("Precio de Bolsa Nacional - " + nombre_mes, fontsize=14, fontweight="bold")
    ejes.set_ylabel("Precio promedio diario ($/kWh)")
    ejes.set_xlabel("Dia del mes")

    ejes.xaxis.set_major_formatter(mdates.DateFormatter("%d"))
    ejes.xaxis.set_major_locator(mdates.DayLocator())

    ejes.grid(True, linestyle="--", alpha=0.4)
    ejes.legend(
        loc="upper center",
        bbox_to_anchor=(0.5, -0.15),
        ncol=2,
        frameon=False
    )

    figura.tight_layout()

    nombre_archivo = "precio_bolsa_" + hoy.strftime("%Y_%m") + ".png"
    ruta_completa = os.path.join(CARPETA_ACTUAL, nombre_archivo)

    figura.savefig(ruta_completa, dpi=150)
    plt.close(figura)

    print("Grafico generado: " + ruta_completa)
    return ruta_completa


if __name__ == "__main__":
    generar_grafico_mensual()
