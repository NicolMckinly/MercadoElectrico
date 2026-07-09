"""
Modulo: precio_bolsa.py
Ubicacion: API/precio_bolsa.py
Este archivo se encarga de conectarse a la API oficial de XM
y descargar el Precio de Bolsa Nacional para un rango de fechas.
Ademas, cuando se ejecuta directamente, guarda automaticamente
los datos descargados en la base de datos del proyecto.
NOTA TECNICA: en vez de usar el metodo request_data() de la libreria
pydataxm (que pide varios dias en paralelo y falla por completo si
uno solo de esos dias tiene un problema temporal), hacemos las
peticiones nosotros mismos, un dia a la vez, con reintentos
automaticos. Esto es mas robusto para un sistema que debe ejecutarse
solo, todos los dias, sin que nadie este mirando si algo fallo.

El bloque __main__ (ejecucion manual) usa ahora_colombia() en vez
de datetime.now(), para que "hoy" siempre se calcule con la hora
real de Colombia y no con la hora UTC del servidor.
"""
import requests
import pandas as pd
import time
import sys
import os
from datetime import timedelta
# Le decimos a Python donde encontrar el modulo de base de datos,
# que vive en una carpeta distinta (BaseDatos).
CARPETA_PROYECTO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(CARPETA_PROYECTO, "BaseDatos"))
from base_datos import guardar_precio_bolsa, consultar_todo_precio_bolsa
from zona_horaria import ahora_colombia
URL_API_XM = "https://servapibi.xm.com.co/hourly"
MAX_INTENTOS_POR_DIA = 3
SEGUNDOS_ENTRE_INTENTOS = 5
def obtener_precio_bolsa_de_un_dia(fecha):
    """
    Descarga el Precio de Bolsa Nacional de un solo dia especifico.
    Reintenta varias veces si el servidor responde con error.
    """
    fecha_texto = fecha.strftime("%Y-%m-%d")
    cuerpo_peticion = {
        "MetricId": "PrecBolsNaci",
        "StartDate": fecha_texto,
        "EndDate": fecha_texto,
        "Entity": "Sistema"
    }
    for intento in range(1, MAX_INTENTOS_POR_DIA + 1):
        try:
            respuesta = requests.post(URL_API_XM, json=cuerpo_peticion, timeout=30)
            if respuesta.status_code == 200:
                datos_json = respuesta.json()
                if len(datos_json["Items"]) == 0:
                    print("  " + fecha_texto + ": aun no publicado por XM, se omite.")
                    return None
                valores_por_hora = datos_json["Items"][0]["HourlyEntities"][0]["Values"]
                valores_por_hora["Date"] = fecha_texto
                return valores_por_hora
            else:
                print("  " + fecha_texto + ": intento " + str(intento) + " fallo con codigo " + str(respuesta.status_code))
        except Exception as error:
            print("  " + fecha_texto + ": intento " + str(intento) + " fallo con error: " + str(error))
        time.sleep(SEGUNDOS_ENTRE_INTENTOS)
    print("  " + fecha_texto + ": no se pudo obtener el dato despues de varios intentos.")
    return None
def obtener_precio_bolsa(fecha_inicio, fecha_fin):
    """
    Descarga el Precio de Bolsa Nacional entre dos fechas, dia por dia.
    """
    lista_de_dias = []
    fecha_actual = fecha_inicio
    while fecha_actual <= fecha_fin:
        print("Consultando " + fecha_actual.strftime("%Y-%m-%d") + "...")
        datos_del_dia = obtener_precio_bolsa_de_un_dia(fecha_actual)
        if datos_del_dia is not None:
            lista_de_dias.append(datos_del_dia)
        fecha_actual = fecha_actual + timedelta(days=1)
    df = pd.DataFrame(lista_de_dias)
    return df
if __name__ == "__main__":
    fecha_fin = ahora_colombia() - timedelta(days=1)
    fecha_inicio = fecha_fin - timedelta(days=5)
    print("Consultando Precio de Bolsa desde " + str(fecha_inicio.date()) + " hasta " + str(fecha_fin.date()))
    print("")
    datos = obtener_precio_bolsa(fecha_inicio, fecha_fin)
    print("")
    print("Datos descargados de XM:")
    print(datos)
    print("")
    print("Guardando en la base de datos...")
    guardar_precio_bolsa(datos)
    print("")
    print("Historico completo en la base de datos:")
    historico = consultar_todo_precio_bolsa()
    print(historico)
    print("")
    print("Total de dias en el historico: " + str(len(historico)))
