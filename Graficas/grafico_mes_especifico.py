"""
Modulo: grafico_mes_especifico.py
Ubicacion: Graficas/grafico_mes_especifico.py

Genera el grafico del Precio de Bolsa de un mes ESPECIFICO (por
ejemplo, septiembre de 2026), no del mes vigente como hace
grafico_mensual.py. Sirve para revisar meses ya cerrados.

Tiene el mismo estilo del grafico mensual del sistema: Precio de
Bolsa real (TX1) en linea solida azul, IMAR en linea punteada naranja
para los dias que aun no tienen precio real, y la linea del Precio de
Escasez vigente ese mes.

Este archivo NO descarga nada: solo lee la base de datos local. No
borra ningun otro grafico, y su nombre de salida
(precio_bolsa_mes_AAAA_MM.png) no coincide con el patron que limpia
grafico_mensual.py.

Tambien incluye generar_grafico_comparativo(), que pone varios meses
lado a lado (lineas superpuestas por dia del mes, y barras con el
promedio de cada mes frente a su Precio de Escasez).

Para pedir graficos de cualquier mes o meses y recibirlos por correo,
usar main_graficos_a_pedido.py (raiz del proyecto).

Uso directo:
    python Graficas/grafico_mes_especifico.py 2026 9
"""

import sys
import os
import calendar
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd

CARPETA_PROYECTO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(CARPETA_PROYECTO, "Analisis"))
sys.path.append(os.path.join(CARPETA_PROYECTO, "BaseDatos"))

from combinar_precio import obtener_serie_combinada, COLUMNAS_HORA
from base_datos import consultar_todo_precio_escasez
from zona_horaria import ahora_colombia

CARPETA_ACTUAL = os.path.dirname(os.path.abspath(__file__))

COLOR_PRECIO_REAL = "#1F4E79"
COLOR_IMAR = "#D9822B"
COLOR_ESCASEZ = "#B22222"

LIMITE_SUPERIOR_MINIMO = 1300

MESES_EN_ESPANOL = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre",
}


def _rango_del_mes(anio, mes):
    ultimo_dia = calendar.monthrange(anio, mes)[1]
    return "%04d-%02d-01" % (anio, mes), "%04d-%02d-%02d" % (anio, mes, ultimo_dia)


def _es_mes_en_curso(anio, mes):
    hoy = ahora_colombia()
    return (anio, mes) == (hoy.year, hoy.month)


def generar_grafico_mes(anio, mes, carpeta_salida=None):
    """
    Genera el grafico del mes indicado, con el mismo estilo del grafico
    mensual del sistema (grafico_mensual.py): Precio de Bolsa real (TX1)
    en linea solida, IMAR en linea punteada naranja para los dias aun
    sin precio real, y el Precio de Escasez vigente ese mes.

    Retorna:
        La ruta de la imagen generada, o None si no hay datos de ese mes.
    """
    inicio, fin = _rango_del_mes(anio, mes)
    serie = obtener_serie_combinada(fecha_inicio=inicio, fecha_fin=fin)

    if len(serie) == 0:
        print("No hay datos de Precio de Bolsa para " + MESES_EN_ESPANOL[mes] + " " + str(anio) + ".")
        return None

    serie["promedio_diario"] = serie[COLUMNAS_HORA].mean(axis=1)
    serie["fecha_dt"] = pd.to_datetime(serie["fecha"])
    serie = serie.sort_values("fecha_dt")

    # Precio de Escasez vigente en ese mes (el ultimo valor guardado del mes)
    escasez = consultar_todo_precio_escasez()
    escasez_mes = escasez[(escasez["fecha"] >= inicio) & (escasez["fecha"] <= fin)]
    valor_escasez = escasez_mes["valor"].iloc[-1] if len(escasez_mes) > 0 else None

    figura, ejes = plt.subplots(figsize=(11, 5.5))

    # Linea gris de fondo que une ambos tramos (real e IMAR)
    ejes.plot(serie["fecha_dt"], serie["promedio_diario"], color="#CCCCCC", linewidth=1, zorder=1)

    dias_real = serie[serie["fuente"] == "Precio Bolsa"]
    dias_imar = serie[serie["fuente"] == "IMAR"]

    ejes.plot(
        dias_real["fecha_dt"], dias_real["promedio_diario"], "o-",
        color=COLOR_PRECIO_REAL, linewidth=2.5, markersize=6,
        label="Precio de Bolsa (real)", zorder=2
    )
    # El IMAR solo aparece (y en la leyenda) si el mes tiene dias sin precio real
    if len(dias_imar) > 0:
        ejes.plot(
            dias_imar["fecha_dt"], dias_imar["promedio_diario"], "o--",
            color=COLOR_IMAR, linewidth=2.5, markersize=6,
            label="IMAR", zorder=2
        )

    for _, fila in serie.iterrows():
        color = COLOR_PRECIO_REAL if fila["fuente"] == "Precio Bolsa" else COLOR_IMAR
        ejes.annotate(
            "{:.0f}".format(fila["promedio_diario"]),
            xy=(fila["fecha_dt"], fila["promedio_diario"]),
            xytext=(0, 10), textcoords="offset points",
            ha="center", fontsize=8, color=color, fontweight="bold"
        )

    limite_superior = LIMITE_SUPERIOR_MINIMO
    if valor_escasez is not None and valor_escasez * 1.06 > limite_superior:
        limite_superior = valor_escasez * 1.06
    ejes.set_ylim(0, limite_superior)

    if valor_escasez is not None:
        ejes.axhline(
            y=valor_escasez, color=COLOR_ESCASEZ, linestyle=":", linewidth=2,
            label="Precio de Escasez"
        )
        ejes.annotate(
            "{:.0f}".format(valor_escasez),
            xy=(serie["fecha_dt"].iloc[0], valor_escasez),
            xytext=(0, 6), textcoords="offset points",
            ha="left", fontsize=9, color=COLOR_ESCASEZ, fontweight="bold", clip_on=False
        )

    ejes.set_title(
        "Precio de Bolsa Nacional - " + MESES_EN_ESPANOL[mes] + " " + str(anio)
        + (" (mes en curso)" if _es_mes_en_curso(anio, mes) else ""),
        fontsize=14, fontweight="bold"
    )
    ejes.set_ylabel("Precio promedio diario ($/kWh)")
    ejes.set_xlabel("Dia del mes")

    # Solo los dias del mes (sin el dia anterior ni el siguiente en el eje)
    ejes.set_xlim(
        pd.Timestamp(inicio) - pd.Timedelta(hours=18),
        pd.Timestamp(fin) + pd.Timedelta(hours=18)
    )
    ejes.xaxis.set_major_formatter(mdates.DateFormatter("%d"))
    ejes.xaxis.set_major_locator(mdates.DayLocator())

    ejes.grid(True, linestyle="--", alpha=0.4)
    ejes.legend(loc="upper center", bbox_to_anchor=(0.5, -0.15), ncol=3, frameon=False)

    figura.tight_layout()

    nombre_archivo = "precio_bolsa_mes_%04d_%02d.png" % (anio, mes)
    ruta = os.path.join(carpeta_salida or CARPETA_ACTUAL, nombre_archivo)
    figura.savefig(ruta, dpi=150)
    plt.close(figura)

    print("Grafico generado: " + ruta)
    return ruta

COLORES_COMPARATIVO = ["#1F4E79", "#D9822B", "#2E8B57", "#8E44AD", "#C0392B", "#7F8C8D"]
MAXIMO_MESES_SUPERPUESTOS = 6


def generar_grafico_comparativo(meses, carpeta_salida=None):
    """
    Compara varios meses en un solo grafico.

    Parametros:
        meses: lista de tuplas (anio, mes), en el orden deseado.

    Retorna:
        La ruta de la imagen generada, o None si ningun mes tiene datos.
    """
    datos = []
    for anio, mes in meses:
        inicio, fin = _rango_del_mes(anio, mes)
        serie = obtener_serie_combinada(fecha_inicio=inicio, fecha_fin=fin)
        if len(serie) == 0:
            continue
        serie["promedio_diario"] = serie[COLUMNAS_HORA].mean(axis=1)
        serie["dia"] = serie["fecha"].str[8:10].astype(int)
        serie = serie.sort_values("dia")

        escasez = consultar_todo_precio_escasez()
        escasez_mes = escasez[(escasez["fecha"] >= inicio) & (escasez["fecha"] <= fin)]
        valor_escasez = escasez_mes["valor"].iloc[-1] if len(escasez_mes) > 0 else None

        en_curso = _es_mes_en_curso(anio, mes)
        datos.append({
            "etiqueta": MESES_EN_ESPANOL[mes][:3] + " " + str(anio) + ("\n(en curso)" if en_curso else ""),
            "nombre": MESES_EN_ESPANOL[mes] + " " + str(anio) + (" (en curso)" if en_curso else ""),
            "serie": serie,
            "promedio": serie["promedio_diario"].mean(),
            "escasez": valor_escasez,
            "tiene_imar": (serie["fuente"] == "IMAR").any(),
        })

    if len(datos) == 0:
        print("Ninguno de los meses pedidos tiene datos.")
        return None

    superponer = len(datos) <= MAXIMO_MESES_SUPERPUESTOS
    if superponer:
        figura, (ejes, ejes_barras) = plt.subplots(
            2, 1, figsize=(12, 8.5), gridspec_kw={"height_ratios": [1.6, 1]}
        )
    else:
        figura, ejes_barras = plt.subplots(figsize=(12, 5.5))

    # ---------- Lineas superpuestas por dia del mes ----------
    if superponer:
        for i, d in enumerate(datos):
            color = COLORES_COMPARATIVO[i % len(COLORES_COMPARATIVO)]
            etiqueta = d["nombre"] + " (prom. {:.0f})".format(d["promedio"])
            if d["tiene_imar"]:
                etiqueta += " *"
            ejes.plot(
                d["serie"]["dia"], d["serie"]["promedio_diario"], "o-",
                color=color, linewidth=2, markersize=3.5, label=etiqueta
            )
        ejes.set_xlim(0.5, 31.5)
        ejes.set_xticks(range(1, 32))
        ejes.set_ylim(0, max(LIMITE_SUPERIOR_MINIMO, max(d["serie"]["promedio_diario"].max() for d in datos) * 1.1))
        ejes.set_xlabel("Dia del mes")
        ejes.set_ylabel("Promedio diario ($/kWh)")
        ejes.set_title("Precio de Bolsa Nacional - Comparacion por dia del mes", fontsize=13, fontweight="bold")
        ejes.grid(True, linestyle="--", alpha=0.4)
        ejes.legend(loc="upper left", fontsize=8.5, frameon=True, framealpha=0.9)

    # ---------- Barras: promedio de cada mes vs Precio de Escasez ----------
    posiciones = list(range(len(datos)))
    promedios = [d["promedio"] for d in datos]
    barras = ejes_barras.bar(posiciones, promedios, width=0.6, color=COLOR_PRECIO_REAL, label="Promedio del mes")
    for barra, valor in zip(barras, promedios):
        ejes_barras.annotate(
            "{:.0f}".format(valor), xy=(barra.get_x() + barra.get_width() / 2, valor),
            xytext=(0, 4), textcoords="offset points", ha="center", fontsize=8.5, fontweight="bold"
        )

    posiciones_escasez = [p for p, d in zip(posiciones, datos) if d["escasez"] is not None]
    valores_escasez = [d["escasez"] for d in datos if d["escasez"] is not None]
    if len(valores_escasez) > 0:
        ejes_barras.scatter(
            posiciones_escasez, valores_escasez, marker="_", s=900,
            linewidths=2.5, color=COLOR_ESCASEZ, label="Precio de Escasez", zorder=3
        )

    tope = max(promedios + valores_escasez) * 1.15
    ejes_barras.set_ylim(0, tope)
    ejes_barras.set_xticks(posiciones)
    ejes_barras.set_xticklabels([d["etiqueta"] for d in datos], rotation=45 if len(datos) > 8 else 0, ha="center")
    ejes_barras.set_ylabel("$/kWh")
    ejes_barras.set_title("Promedio mensual del Precio de Bolsa", fontsize=11, fontweight="bold", loc="left")
    ejes_barras.grid(True, axis="y", linestyle="--", alpha=0.4)
    ejes_barras.legend(loc="upper left", fontsize=8.5, frameon=True, framealpha=0.9)

    nota = "Fuente: XM. Datos de la base local del sistema."
    if any(d["tiene_imar"] for d in datos):
        nota += "  * Incluye dias con IMAR (precio real aun no publicado)."
    figura.text(0.01, 0.005, nota, fontsize=7, color="#777777")
    figura.tight_layout(rect=(0, 0.015, 1, 1))

    primero, ultimo = meses[0], meses[-1]
    nombre_archivo = "precio_bolsa_comparativo_%04d_%02d_a_%04d_%02d.png" % (primero + ultimo)
    ruta = os.path.join(carpeta_salida or CARPETA_ACTUAL, nombre_archivo)
    figura.savefig(ruta, dpi=150)
    plt.close(figura)

    print("Grafico comparativo generado: " + ruta)
    return ruta


if __name__ == "__main__":
    if len(sys.argv) == 3:
        generar_grafico_mes(int(sys.argv[1]), int(sys.argv[2]))
    else:
        print("Uso: python Graficas/grafico_mes_especifico.py AAAA MM   (ej. 2026 9)")
