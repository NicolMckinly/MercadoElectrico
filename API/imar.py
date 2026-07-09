"""
Modulo: imar.py
Ubicacion: API/imar.py

Este archivo descarga el IMAR (Predespacho Ideal) directamente desde
el sitio publico de XM. A diferencia del Precio de Bolsa, el IMAR
NO esta disponible en la API oficial de XM (pydataxm), asi que aqui
si usamos "web scraping" (descargar el archivo publico directamente),
tal como estaba previsto en la especificacion del proyecto.

Cada archivo diario de XM trae tres filas: "Costo Marginal", "Delta"
y "MPO". Segun la especificacion del proyecto, solo usamos la fila
"Costo Marginal".

Los valores que publica XM vienen en pesos por MWh. Los convertimos
a pesos por kWh dividiendo entre 1000, para que queden en la misma
escala que el Precio de Bolsa.

Ademas, cuando se ejecuta directamente, guarda automaticamente
los datos descargados en la base de datos del proyecto.

NOTA: el IMAR es un pronostico (Predespacho Ideal) que XM publica
con un dia de anticipacion. Por eso, a diferencia del Precio de
Bolsa real, el IMAR del dia de hoy normalmente ya esta disponible.

La funcion verificar_imar_de_manana_publicado() usa ahora_colombia()
(ver BaseDatos/zona_horaria.py) en vez de datetime.now(), para que
"mañana" siempre se calcule con la hora real de Colombia y no con la
hora UTC del servidor (que va 5 horas adelante).
"""

import requests
import pandas as pd
import time
import sys
import os
from datetime import datetime, timedelta

CARPETA_PROYECTO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(CARPETA_PROYECTO, "BaseDatos"))

from base_datos import guardar_imar, consultar_todo_imar
from zona_horaria import ahora_colombia

URL_BASE = "https://api-portalxm.xm.com.co/administracion-archivos/ficheros/mostrar-url"
NOMBRE_CONTENEDOR = "storageportalxm"
MAX_INTENTOS_POR_DIA = 3
SEGUNDOS_ENTRE_INTENTOS = 5


def obtener_imar_de_un_dia(fecha):
    """
    Descarga el IMAR (Costo Marginal) de un solo dia especifico.
    """
    anio_mes = fecha.strftime("%Y-%m")
    mes_dia = fecha.strftime("%m%d")
    fecha_texto = fecha.strftime("%Y-%m-%d")

    nombre_archivo = "iMAR" + mes_dia + ".txt"
    ruta_archivo = "M:/InformacionAgentes/Usuarios/Publico/PredespachoIdeal/" + anio_mes + "/" + nombre_archivo

    parametros = {
        "ruta": ruta_archivo,
        "nombreBlobContainer": NOMBRE_CONTENEDOR
    }

    for intento in range(1, MAX_INTENTOS_POR_DIA + 1):
        try:
            respuesta = requests.get(URL_BASE, params=parametros, timeout=30)

            if respuesta.status_code == 200 and "Costo Marginal" in respuesta.text:
                return interpretar_archivo_imar(respuesta.text, fecha_texto)

            elif respuesta.status_code == 404:
                print("  " + fecha_texto + ": IMAR aun no publicado por XM, se omite.")
                return None

            else:
                print("  " + fecha_texto + ": intento " + str(intento) + " fallo con codigo " + str(respuesta.status_code))

        except Exception as error:
            print("  " + fecha_texto + ": intento " + str(intento) + " fallo con error: " + str(error))

        time.sleep(SEGUNDOS_ENTRE_INTENTOS)

    print("  " + fecha_texto + ": no se pudo obtener el IMAR despues de varios intentos.")
    return None


def interpretar_archivo_imar(texto_archivo, fecha_texto):
    """
    Convierte el texto crudo del archivo de XM en un diccionario con
    las 24 horas del dia, usando unicamente la fila "Costo Marginal",
    ya convertida de $/MWh a $/kWh.
    """
    lineas = texto_archivo.strip().split("\n")

    linea_costo_marginal = None
    for linea in lineas:
        if linea.startswith('"Costo Marginal"'):
            linea_costo_marginal = linea
            break

    if linea_costo_marginal is None:
        return None

    partes = linea_costo_marginal.split(",")
    valores_texto = partes[1:]

    resultado = {"Date": fecha_texto}

    for numero_hora in range(24):
        valor_en_pesos_mwh = float(valores_texto[numero_hora].strip())
        valor_en_pesos_kwh = valor_en_pesos_mwh / 1000
        nombre_columna = "Hour" + str(numero_hora + 1).zfill(2)
        resultado[nombre_columna] = valor_en_pesos_kwh

    return resultado


def obtener_imar(fecha_inicio, fecha_fin):
    """
    Descarga el IMAR entre dos fechas, dia por dia.
    """
    lista_de_dias = []
    fecha_actual = fecha_inicio

    while fecha_actual <= fecha_fin:
        print("Consultando IMAR " + fecha_actual.strftime("%Y-%m-%d") + "...")
        datos_del_dia = obtener_imar_de_un_dia(fecha_actual)

        if datos_del_dia is not None:
            lista_de_dias.append(datos_del_dia)

        fecha_actual = fecha_actual + timedelta(days=1)

    df = pd.DataFrame(lista_de_dias)
    return df


def verificar_imar_de_manana_publicado():
    """
    Verifica rapidamente (con una sola peticion) si el IMAR de
    mañana ya esta publicado por XM, sin descargar ni guardar nada.
    Esto es lo que usa el Modulo 2 (monitor permanente) para saber
    cuando ya es momento de generar y enviar el informe diario.

    "Mañana" se calcula con la hora real de Colombia (ahora_colombia()),
    no con la hora UTC del servidor.

    Retorna:
        True si ya esta publicado, False si no.
    """
    manana = ahora_colombia() + timedelta(days=1)
    resultado = obtener_imar_de_un_dia(manana)
    return resultado is not None


if __name__ == "__main__":

    # El IMAR se publica con un dia de anticipacion, asi que siempre
    # intentamos traer tambien el dia de MANANA (no solo hasta hoy).
    fecha_fin = ahora_colombia() + timedelta(days=1)
    fecha_inicio = fecha_fin - timedelta(days=6)

    print("Consultando IMAR desde " + str(fecha_inicio.date()) + " hasta " + str(fecha_fin.date()))
    print("")

    datos = obtener_imar(fecha_inicio, fecha_fin)

    print("")
    print("Datos de IMAR descargados de XM:")
    print(datos)

    print("")
    print("Guardando en la base de datos...")
    guardar_imar(datos)

    print("")
    print("Historico completo de IMAR en la base de datos:")
    historico = consultar_todo_imar()
    print(historico)
    print("")
    print("Total de dias en el historico de IMAR: " + str(len(historico)))
