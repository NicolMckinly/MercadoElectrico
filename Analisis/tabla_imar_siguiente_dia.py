"""
Modulo: tabla_imar_siguiente_dia.py
Ubicacion: Analisis/tabla_imar_siguiente_dia.py

Genera la tabla del IMAR periodo a periodo (24 horas) para el dia
siguiente, junto con el "Precio de Bolsa Proyectado", que se calcula
asi, HORA POR HORA:

    PB_proyectado = promedio( promedio_ultimos_3_dias(Precio de
    Bolsa real) , promedio_ultimos_3_dias(IMAR) )

Es decir: se promedian los ultimos 3 dias DISPONIBLES de Precio de
Bolsa real (sin importar que fecha sea), se promedian por separado
los ultimos 3 dias DISPONIBLES de IMAR (tambien sin importar la
fecha, y sin incluir el IMAR crudo de "mañana" que se esta
proyectando), y luego se promedian esos dos resultados entre si.
Como cada promedio usa "los ultimos disponibles" en el momento de
la corrida, el calculo se va corriendo solo, dia a dia, a medida
que ambas variables se actualizan.

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

CANTIDAD_DIAS_PARA_EL_PROMEDIO = 3


def calcular_pb_proyectado_por_hora(fecha_manana):
    """
    Calcula, para cada una de las 24 horas, el Precio de Bolsa
    Proyectado: el promedio entre (a) el promedio de los ultimos 3
    dias DISPONIBLES de Precio de Bolsa real, y (b) el promedio de
    los ultimos 3 dias DISPONIBLES de IMAR (sin contar el IMAR crudo
    del dia que se esta proyectando). Cada variable usa sus propios
    ultimos dias disponibles, sin necesidad de que coincidan en
    fecha entre si.

    Retorna:
        Un diccionario {nombre_columna_hora: valor_proyectado}, o
        None si no hay suficientes datos todavia.
    """
    precio_bolsa = consultar_todo_precio_bolsa()
    imar = consultar_todo_imar()

    if len(precio_bolsa) == 0 or len(imar) == 0:
        print("Aun no hay suficiente historico de Precio de Bolsa y/o IMAR para calcular la proyeccion.")
        return None

    # Ultimos 3 dias disponibles de Precio de Bolsa real (los mas recientes)
    precio_bolsa_ultimos_3 = precio_bolsa.sort_values("fecha", ascending=False).head(CANTIDAD_DIAS_PARA_EL_PROMEDIO)

    # Ultimos 3 dias disponibles de IMAR, SIN incluir el IMAR crudo del
    # dia que se esta proyectando (fecha_manana), para no usar el dato
    # que justamente estamos tratando de proyectar.
    imar_historico = imar[imar["fecha"] < fecha_manana]
    imar_ultimos_3 = imar_historico.sort_values("fecha", ascending=False).head(CANTIDAD_DIAS_PARA_EL_PROMEDIO)

    if len(precio_bolsa_ultimos_3) == 0 or len(imar_ultimos_3) == 0:
        print("Aun no hay suficiente historico para calcular la proyeccion.")
        return None

    pb_proyectado = {}

    for columna in COLUMNAS_HORA:
        promedio_precio_bolsa = precio_bolsa_ultimos_3[columna].mean()
        promedio_imar = imar_ultimos_3[columna].mean()
        pb_proyectado[columna] = (promedio_precio_bolsa + promedio_imar) / 2

    return pb_proyectado


def obtener_tabla_imar_siguiente_dia():
    """
    Arma la tabla del IMAR del dia siguiente, periodo a periodo,
    junto con el Precio de Bolsa Proyectado.

    Retorna:
        Un diccionario con:
        - "fecha": la fecha del dia que se esta mostrando
        - "filas": una lista de 24 diccionarios, uno por periodo,
          con "periodo", "imar_crudo", "pb_proyectado"
        - "dias_usados_para_el_promedio": cuantos dias se usaron
          como base del promedio (para ser transparentes sobre la
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

    pb_proyectado_por_hora = calcular_pb_proyectado_por_hora(manana)

    filas = []
    for numero_hora in range(24):
        columna = COLUMNAS_HORA[numero_hora]
        valor_crudo = imar_indexado.loc[manana, columna]

        if pb_proyectado_por_hora is not None:
            valor_proyectado = pb_proyectado_por_hora[columna]
        else:
            valor_proyectado = valor_crudo

        hora_inicio = str(numero_hora).zfill(2) + ":00"
        hora_fin = str(numero_hora).zfill(2) + ":59"

        filas.append({
            "periodo": "P" + str(numero_hora + 1).zfill(2) + ": " + hora_inicio + "-" + hora_fin,
            "imar_crudo": valor_crudo,
            "pb_proyectado": valor_proyectado
        })

    dias_usados = min(len(consultar_todo_precio_bolsa()), CANTIDAD_DIAS_PARA_EL_PROMEDIO)

    return {
        "fecha": manana,
        "filas": filas,
        "dias_usados_para_el_promedio": dias_usados
    }


if __name__ == "__main__":
    resultado = obtener_tabla_imar_siguiente_dia()

    if resultado is not None:
        print("IMAR para el dia: " + resultado["fecha"])
        print("Proyeccion calculada con hasta " + str(resultado["dias_usados_para_el_promedio"]) + " dia(s) de historial de cada variable.")
        print("")
        print("{:<20} {:>15} {:>18}".format("Periodo", "IMAR", "PB Proyectado"))

        for fila in resultado["filas"]:
            print("{:<20} {:>15.2f} {:>18.2f}".format(fila["periodo"], fila["imar_crudo"], fila["pb_proyectado"]))
