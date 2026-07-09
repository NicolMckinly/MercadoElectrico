"""
Modulo: tabla_imar_siguiente_dia.py
Ubicacion: Analisis/tabla_imar_siguiente_dia.py

Genera la tabla del IMAR periodo a periodo (24 horas) para el dia
siguiente, incluyendo una version "ajustada" que corrige el IMAR
crudo usando la desviacion promedio observada entre el Precio de
Bolsa real y el IMAR en los ultimos dias donde ambos datos existan
para la misma fecha.

El ajuste se calcula HORA POR HORA (no un solo numero para todo el
dia), usando los ultimos 3 dias disponibles donde ya exista tanto
el precio real como el IMAR para esa misma fecha. Esto sirve para
identificar en que horas del dia el IMAR tiende a desviarse mas del
precio real.

"Mañana" se calcula con ahora_colombia() (ver BaseDatos/zona_horaria.py)
en vez de datetime.now(), para que siempre se use la hora real de
Colombia y no la hora UTC del servidor (que va 5 horas adelante).

Este archivo NO descarga datos ni genera el PDF. Solo hace el calculo
y entrega los resultados listos para usar.
"""

import sys
import os
from datetime import timedelta

CARPETA_PROYECTO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(CARPETA_PROYECTO, "BaseDatos"))

from base_datos import consultar_todo_precio_bolsa, consultar_todo_imar
from zona_horaria import ahora_colombia

COLUMNAS_HORA = [
    "hora_01", "hora_02", "hora_03", "hora_04", "hora_05", "hora_06",
    "hora_07", "hora_08", "hora_09", "hora_10", "hora_11", "hora_12",
    "hora_13", "hora_14", "hora_15", "hora_16", "hora_17", "hora_18",
    "hora_19", "hora_20", "hora_21", "hora_22", "hora_23", "hora_24"
]

CANTIDAD_DIAS_PARA_EL_AJUSTE = 3


def calcular_factores_de_ajuste_por_hora():
    """
    Calcula, para cada una de las 24 horas, el factor promedio de
    ajuste entre el Precio de Bolsa real y el IMAR, usando los
    ultimos N dias donde ambos datos existan para la misma fecha.

    El factor es multiplicativo: factor = precio_real / imar_crudo,
    promediado sobre los dias disponibles. Un factor de 1.05, por
    ejemplo, significa que en promedio el precio real termino siendo
    un 5% mas alto que lo que el IMAR habia anticipado en esa hora.

    Retorna:
        Un diccionario {nombre_columna_hora: factor}, o None si no
        hay suficientes dias con ambos datos disponibles.
    """
    precio_bolsa = consultar_todo_precio_bolsa()
    imar = consultar_todo_imar()

    fechas_con_ambos_datos = sorted(
        set(precio_bolsa["fecha"]).intersection(set(imar["fecha"])),
        reverse=True
    )

    if len(fechas_con_ambos_datos) == 0:
        print("Aun no hay ningun dia con Precio de Bolsa real e IMAR para la misma fecha. No se puede calcular el ajuste todavia.")
        return None

    fechas_a_usar = fechas_con_ambos_datos[:CANTIDAD_DIAS_PARA_EL_AJUSTE]

    precio_bolsa_indexado = precio_bolsa.set_index("fecha")
    imar_indexado = imar.set_index("fecha")

    factores = {}

    for columna in COLUMNAS_HORA:
        razones_de_esta_hora = []

        for fecha in fechas_a_usar:
            valor_real = precio_bolsa_indexado.loc[fecha, columna]
            valor_imar = imar_indexado.loc[fecha, columna]

            if valor_imar != 0:
                razones_de_esta_hora.append(valor_real / valor_imar)

        if len(razones_de_esta_hora) > 0:
            factores[columna] = sum(razones_de_esta_hora) / len(razones_de_esta_hora)
        else:
            factores[columna] = 1.0

    return factores


def obtener_tabla_imar_siguiente_dia():
    """
    Arma la tabla del IMAR del dia siguiente, periodo a periodo,
    con su version ajustada.

    Retorna:
        Un diccionario con:
        - "fecha": la fecha del dia que se esta mostrando
        - "filas": una lista de 24 diccionarios, uno por periodo,
          con "periodo", "imar_crudo", "imar_ajustado"
        - "dias_usados_para_el_ajuste": cuantos dias se usaron para
          calcular el ajuste (para ser transparentes sobre la
          confiabilidad del calculo)
        O None si no hay datos de IMAR disponibles para el dia siguiente.
    """
    imar = consultar_todo_imar()

    if len(imar) == 0:
        print("No hay datos de IMAR disponibles todavia.")
        return None

    manana = (ahora_colombia() + timedelta(days=1)).strftime("%Y-%m-%d")

    imar_indexado = imar.set_index("fecha")

    if manana not in imar_indexado.index:
        print("Aun no esta publicado el IMAR de manana (" + manana + ").")
        return None

    factores = calcular_factores_de_ajuste_por_hora()

    filas = []
    for numero_hora in range(24):
        columna = COLUMNAS_HORA[numero_hora]
        valor_crudo = imar_indexado.loc[manana, columna]

        if factores is not None:
            valor_ajustado = valor_crudo * factores[columna]
        else:
            valor_ajustado = valor_crudo

        hora_inicio = str(numero_hora).zfill(2) + ":00"
        hora_fin = str(numero_hora).zfill(2) + ":59"

        filas.append({
            "periodo": "P" + str(numero_hora + 1).zfill(2) + ": " + hora_inicio + "-" + hora_fin,
            "imar_crudo": valor_crudo,
            "imar_ajustado": valor_ajustado
        })

    precio_bolsa = consultar_todo_precio_bolsa()
    dias_usados = len(set(precio_bolsa["fecha"]).intersection(set(imar["fecha"])))
    dias_usados = min(dias_usados, CANTIDAD_DIAS_PARA_EL_AJUSTE)

    return {
        "fecha": manana,
        "filas": filas,
        "dias_usados_para_el_ajuste": dias_usados
    }


if __name__ == "__main__":
    resultado = obtener_tabla_imar_siguiente_dia()

    if resultado is not None:
        print("IMAR para el dia: " + resultado["fecha"])
        print("Ajuste calculado con " + str(resultado["dias_usados_para_el_ajuste"]) + " dia(s) de historial cruzado.")
        print("")
        print("{:<20} {:>15} {:>15}".format("Periodo", "IMAR crudo", "IMAR ajustado"))

        for fila in resultado["filas"]:
            print("{:<20} {:>15.2f} {:>15.2f}".format(fila["periodo"], fila["imar_crudo"], fila["imar_ajustado"]))
