"""
Modulo: variables_hidrologicas.py
Ubicacion: API/variables_hidrologicas.py
Descarga las variables hidrologicas principales del Modulo 3 desde
la API oficial de XM: Embalses (Volumen Util), Aportes Hidricos,
Capacidad Util, y la comparacion de Aportes con la Media Historica.
Todas estas metricas son de tipo "DailyEntities" (un solo valor por
dia, no 24 horas como el precio de bolsa), asi que las descargamos
usando el mismo patron robusto: dia por dia, con reintentos.

La funcion variables_hidrologicas_de_ayer_estan_publicadas() y el
bloque __main__ usan ahora_colombia() (ver BaseDatos/zona_horaria.py)
en vez de datetime.now(), para que "ayer" siempre se calcule con la
hora real de Colombia y no con la hora UTC del servidor.
"""
import requests
import pandas as pd
import time
import sys
import os
from datetime import timedelta

CARPETA_PROYECTO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(CARPETA_PROYECTO, "BaseDatos"))

from base_datos import guardar_variable_hidrologica
from zona_horaria import ahora_colombia

URL_API_XM = "https://servapibi.xm.com.co/daily"
MAX_INTENTOS_POR_DIA = 3
SEGUNDOS_ENTRE_INTENTOS = 5

# Cada entrada define: el codigo de la metrica en XM, y el nombre de
# tabla donde la vamos a guardar en nuestra base de datos.
VARIABLES_A_DESCARGAR = {
    "embalses_porcentaje": "PorcVoluUtilDiar",
    "embalses_energia": "VoluUtilDiarEner",
    "aportes_porcentaje": "PorcApor",
    "aportes_energia": "AporEner",
    "aportes_media_historica": "AporEnerMediHist",
    "capacidad_util_energia": "CapaUtilDiarEner",
}


def _consultar_metrica_de_un_dia(metric_id, fecha):
    """
    Consulta el valor de una metrica diaria especifica de XM, para
    una fecha en particular, con reintentos automaticos.
    Retorna:
        El valor numerico, o None si no se pudo obtener.
    """
    fecha_texto = fecha.strftime("%Y-%m-%d")
    cuerpo_peticion = {
        "MetricId": metric_id,
        "StartDate": fecha_texto,
        "EndDate": fecha_texto,
        "Entity": "Sistema"
    }
    for intento in range(1, MAX_INTENTOS_POR_DIA + 1):
        try:
            respuesta = requests.post(URL_API_XM, json=cuerpo_peticion, timeout=30)
            if respuesta.status_code == 200:
                datos_json = respuesta.json()
                items = datos_json["Items"]
                if len(items) == 0:
                    return None
                return float(items[0]["DailyEntities"][0]["Value"])
            else:
                print("    intento " + str(intento) + " fallo con codigo " + str(respuesta.status_code))
        except Exception as error:
            print("    intento " + str(intento) + " fallo con error: " + str(error))
        time.sleep(SEGUNDOS_ENTRE_INTENTOS)
    return None


def variables_hidrologicas_de_ayer_estan_publicadas():
    """
    Verifica si los datos hidrologicos del dia de ayer (dia n-1,
    calculado con la hora real de Colombia) ya estan publicados en
    la API de XM, consultando una sola metrica representativa
    (Embalses % Volumen Util) en vez de las 6 completas, para que la
    verificacion sea rapida.
    Se usa antes de descargar todo el conjunto de variables y enviar
    el informe, para no enviar el reporte con el dia mas reciente
    todavia vacio.
    Retorna:
        True si el dato de ayer ya esta disponible, False si no.
    """
    ayer = ahora_colombia() - timedelta(days=1)
    valor = _consultar_metrica_de_un_dia("PorcVoluUtilDiar", ayer)
    return valor is not None


def descargar_variables_hidrologicas(fecha_inicio, fecha_fin):
    """
    Descarga todas las variables hidrologicas definidas en
    VARIABLES_A_DESCARGAR, para un rango de fechas, dia por dia,
    y las guarda en la base de datos.
    Parametros:
        fecha_inicio (datetime): fecha desde la cual consultar.
        fecha_fin (datetime): fecha hasta la cual consultar.
    """
    fecha_actual = fecha_inicio
    while fecha_actual <= fecha_fin:
        fecha_texto = fecha_actual.strftime("%Y-%m-%d")
        print("Consultando variables hidrologicas del " + fecha_texto + "...")
        valores_del_dia = {}
        for nombre_variable, metric_id in VARIABLES_A_DESCARGAR.items():
            valor = _consultar_metrica_de_un_dia(metric_id, fecha_actual)
            valores_del_dia[nombre_variable] = valor
            if valor is None:
                print("  " + nombre_variable + ": no disponible para esta fecha.")
        guardar_variable_hidrologica(fecha_texto, valores_del_dia)
        fecha_actual = fecha_actual + timedelta(days=1)


if __name__ == "__main__":
    fecha_fin = ahora_colombia() - timedelta(days=1)
    fecha_inicio = fecha_fin - timedelta(days=5)
    print("Descargando variables hidrologicas desde " + str(fecha_inicio.date()) + " hasta " + str(fecha_fin.date()))
    print("")
    descargar_variables_hidrologicas(fecha_inicio, fecha_fin)
    print("")
    print("Proceso terminado.")
