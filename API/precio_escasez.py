"""
Modulo: precio_escasez.py
Ubicacion: API/precio_escasez.py

Descarga el Precio Marginal de Escasez desde la API oficial de XM.

Este valor se actualiza una vez al mes (aunque XM lo publica todos
los dias, su valor se mantiene igual durante todo el mes vigente).

Las unidades que entrega XM para esta metrica ya vienen en COP/kWh,
por lo que NO es necesario dividir entre 1000 (a diferencia del IMAR).

Este archivo tiene tres funciones principales:
- obtener_precio_escasez_reciente(): trae el valor vigente actual.
- backfill_historico_anual_escasez(): completa el historico mes a mes
  desde enero del año en curso hasta hoy, para poder graficar como
  ha variado el Precio de Escasez a lo largo del año.
- backfill_ultimos_12_meses_escasez(): completa el historico de los
  ultimos 12 meses (contando hacia atras desde el mes actual, incluso
  si eso cruza al año anterior). Se usa una sola vez para llenar el
  hueco de los meses anteriores a cuando el sistema empezo a correr.
"""

import requests
import sys
import os
from datetime import datetime, timedelta

CARPETA_PROYECTO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(CARPETA_PROYECTO, "BaseDatos"))

from base_datos import guardar_precio_escasez, consultar_precio_escasez_mas_reciente

URL_API_XM = "https://servapibi.xm.com.co/daily"


def _consultar_escasez_de_un_dia(fecha):
    """
    Consulta el valor de Precio de Escasez vigente para una fecha
    especifica (funcion interna de uso general).

    Retorna:
        Una tupla (fecha_texto, valor) o (None, None) si no hay dato.
    """
    cuerpo_peticion = {
        "MetricId": "PrecEscaMarg",
        "StartDate": fecha.strftime("%Y-%m-%d"),
        "EndDate": fecha.strftime("%Y-%m-%d"),
        "Entity": "Sistema"
    }

    try:
        respuesta = requests.post(URL_API_XM, json=cuerpo_peticion, timeout=30)

        if respuesta.status_code == 200:
            datos_json = respuesta.json()
            items = datos_json["Items"]

            if len(items) == 0:
                return None, None

            item = items[0]
            fecha_texto = item["Date"]
            valor = float(item["DailyEntities"][0]["Value"])
            return fecha_texto, valor

        else:
            return None, None

    except Exception:
        return None, None


def obtener_precio_escasez_reciente():
    """
    Consulta el Precio Marginal de Escasez de los ultimos dias y
    devuelve el valor mas reciente disponible (que corresponde al
    valor vigente del mes actual).

    Retorna:
        Una tupla (fecha_texto, valor) o (None, None) si no se
        pudo obtener ningun dato.
    """
    fecha_fin = datetime.now()
    fecha_inicio = fecha_fin - timedelta(days=10)

    cuerpo_peticion = {
        "MetricId": "PrecEscaMarg",
        "StartDate": fecha_inicio.strftime("%Y-%m-%d"),
        "EndDate": fecha_fin.strftime("%Y-%m-%d"),
        "Entity": "Sistema"
    }

    try:
        respuesta = requests.post(URL_API_XM, json=cuerpo_peticion, timeout=30)

        if respuesta.status_code == 200:
            datos_json = respuesta.json()
            items = datos_json["Items"]

            if len(items) == 0:
                print("No hay datos de Precio de Escasez disponibles.")
                return None, None

            ultimo_item = items[-1]
            fecha_texto = ultimo_item["Date"]
            valor = float(ultimo_item["DailyEntities"][0]["Value"])

            return fecha_texto, valor

        else:
            print("Error al consultar Precio de Escasez, codigo: " + str(respuesta.status_code))
            return None, None

    except Exception as error:
        print("Error al consultar Precio de Escasez: " + str(error))
        return None, None


def backfill_historico_anual_escasez():
    """
    Completa el historico de Precio de Escasez mes a mes, desde enero
    del año en curso hasta el mes actual, guardando en la base de
    datos el valor vigente del primer dia de cada mes. Esto permite
    graficar como ha variado el Precio de Escasez a lo largo del año.

    Como este valor no cambia dentro de un mismo mes, basta con
    consultar un solo dia por mes (usamos el dia 5, para evitar
    cualquier problema de publicacion de los primeros dias del mes).
    """
    hoy = datetime.now()
    anio_actual = hoy.year
    mes_actual = hoy.month

    print("Completando historico anual de Precio de Escasez...")

    for numero_mes in range(1, mes_actual + 1):
        fecha_de_consulta = datetime(anio_actual, numero_mes, 5)

        if fecha_de_consulta > hoy:
            continue

        fecha_texto, valor = _consultar_escasez_de_un_dia(fecha_de_consulta)

        if valor is not None:
            guardar_precio_escasez(fecha_texto, valor)
            print("  Mes " + str(numero_mes).zfill(2) + ": " + "{:.2f}".format(valor) + " COP/kWh")
        else:
            print("  Mes " + str(numero_mes).zfill(2) + ": no disponible.")


def backfill_ultimos_12_meses_escasez():
    """
    Completa el historico de Precio de Escasez para los ultimos 12
    meses, contando hacia atras desde el mes actual (incluso si eso
    cruza al año anterior). Guarda en la base de datos el valor
    vigente del dia 5 de cada uno de esos meses.

    Se usa UNA SOLA VEZ para llenar el hueco de los meses anteriores
    a cuando el sistema empezo a correr, de modo que la grafica de
    12 meses del Resumen Ejecutivo quede completa.
    """
    hoy = datetime.now()

    print("Completando historico de los ultimos 12 meses de Precio de Escasez...")

    for meses_atras in range(11, -1, -1):
        mes_objetivo = hoy.month - meses_atras
        anio_objetivo = hoy.year

        while mes_objetivo <= 0:
            mes_objetivo += 12
            anio_objetivo -= 1

        fecha_de_consulta = datetime(anio_objetivo, mes_objetivo, 5)

        if fecha_de_consulta > hoy:
            continue

        fecha_texto, valor = _consultar_escasez_de_un_dia(fecha_de_consulta)

        etiqueta = str(anio_objetivo) + "-" + str(mes_objetivo).zfill(2)

        if valor is not None:
            guardar_precio_escasez(fecha_texto, valor)
            print("  " + etiqueta + ": " + "{:.2f}".format(valor) + " COP/kWh")
        else:
            print("  " + etiqueta + ": no disponible.")


if __name__ == "__main__":
    print("Consultando Precio Marginal de Escasez vigente...")
    fecha, valor = obtener_precio_escasez_reciente()

    if valor is not None:
        print("Fecha del dato: " + fecha)
        print("Precio de Escasez vigente: " + str(valor) + " COP/kWh")

        print("")
        print("Guardando en la base de datos...")
        guardar_precio_escasez(fecha, valor)
    else:
        print("No se pudo obtener el Precio de Escasez vigente.")

    print("")
    backfill_historico_anual_escasez()

    print("")
    fecha_guardada, valor_guardado = consultar_precio_escasez_mas_reciente()
    print("Valor mas reciente en la base de datos: " + str(valor_guardado) + " COP/kWh (fecha: " + str(fecha_guardada) + ")")
