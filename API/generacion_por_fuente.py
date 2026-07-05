"""
Modulo: generacion_por_fuente.py
Ubicacion: API/generacion_por_fuente.py

Descarga la Generacion por Fuente usando la API del IDO (Informe
Diario de Operacion) de XM, que publica los datos ya clasificados
por categoria (Hidraulica, Termica, Solar, Eolica, Autogeneracion,
Cogenerador, Distribuida), con muy poco rezago (normalmente
publicado a las 6:00 AM del dia siguiente).

Esta fuente reemplaza el metodo anterior (que combinaba la
Generacion por Recurso de la API oficial con un listado de plantas
clasificadas manualmente), porque es mas simple, mas rapida, y mas
actualizada.

Las categorias del IDO se agrupan asi, segun la especificacion del
proyecto:
- Hidraulica: Generacion Hidraulica + Generacion Menores Hidraulica
- Termica: Generacion Termica + Generacion Menores Termica
- Solar y Eolica: Generacion Solar + Menores Solar + Menores Eolica
- Autogen. y Cogen. y Gen. Distribuida: Autogeneracion + Cogenerador
  + Generacion Distribuida
"""

import requests
import time
import sys
import os
import urllib3
from datetime import datetime, timedelta

# El servidor del IDO de XM tiene un problema de configuracion en su
# certificado de seguridad (le falta un certificado intermedio en la
# cadena de confianza). Los navegadores lo toleran, pero Python lo
# rechaza correctamente por ser mas estricto. Como aqui solo LEEMOS
# informacion publica (no enviamos credenciales ni datos sensibles),
# desactivamos la verificacion SSL unicamente para esta conexion
# especifica, y silenciamos la advertencia relacionada.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

CARPETA_PROYECTO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(CARPETA_PROYECTO, "BaseDatos"))

from base_datos import guardar_generacion_por_fuente

URL_IDO = "https://ido.xm.com.co/ArchivoIdo/ObtenerArchivosPorDia"
ENCABEZADOS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}
MAX_INTENTOS = 3
SEGUNDOS_ENTRE_INTENTOS = 5


def _clasificar_categoria(nombre_grupo):
    """
    Clasifica el nombre de un grupo del IDO (que puede venir con
    codigos HTML como "&oacute;" en vez de tildes) en una de las
    4 categorias combinadas que pide la especificacion.
    """
    nombre = nombre_grupo.lower()

    if "distribuida" in nombre:
        return "Autogen. y Cogen. y Gen. Distribuida"
    elif "cogenerador" in nombre:
        return "Autogen. y Cogen. y Gen. Distribuida"
    elif "autogeneraci" in nombre:
        return "Autogen. y Cogen. y Gen. Distribuida"
    elif "hidr" in nombre:
        return "Hidraulica"
    elif "rmica" in nombre:
        return "Termica"
    elif "solar" in nombre:
        return "Solar y Eolica"
    elif "lica" in nombre:
        # Ultimo recurso: atrapa "Eolica" (que llega con tilde codificada)
        return "Solar y Eolica"
    else:
        return "Otras tecnologias"


def obtener_generacion_de_un_dia(fecha):
    """
    Descarga la generacion por fuente de un dia especifico desde el
    IDO, y la agrupa en las 4 categorias combinadas.

    Parametros:
        fecha (datetime): el dia a consultar (el IDO publica el
                           informe DEL dia anterior a la fecha actual,
                           pero la fecha aqui es la fecha del reporte,
                           no la fecha de publicacion).

    Retorna:
        Un diccionario {categoria: total_gwh}, o None si no esta
        publicado o no se pudo obtener.
    """
    fecha_texto = fecha.strftime("%Y-%m-%d")

    parametros = {
        "fecha": fecha_texto,
        "carpeta": "Ido_Generacion",
        "archivo": "generacion"
    }

    for intento in range(1, MAX_INTENTOS + 1):
        try:
            respuesta = requests.get(URL_IDO, params=parametros, headers=ENCABEZADOS, timeout=30, verify=False)

            if respuesta.status_code == 200:
                datos = respuesta.json()

                if not datos.get("ok") or "payload" not in datos:
                    print("  " + fecha_texto + ": aun no publicado por el IDO, se omite.")
                    return None

                grupos = datos["payload"]["items"]

                totales_por_categoria = {}

                for grupo in grupos:
                    nombre_grupo = grupo["elemento"][0]["nombre"]
                    valor_real_gwh = grupo["subtotales"]["subtotal1"]

                    categoria = _clasificar_categoria(nombre_grupo)

                    if categoria not in totales_por_categoria:
                        totales_por_categoria[categoria] = 0
                    totales_por_categoria[categoria] += valor_real_gwh

                return totales_por_categoria

            else:
                print("  " + fecha_texto + ": intento " + str(intento) + " fallo con codigo " + str(respuesta.status_code))

        except Exception as error:
            print("  " + fecha_texto + ": intento " + str(intento) + " fallo con error: " + str(error))

        time.sleep(SEGUNDOS_ENTRE_INTENTOS)

    print("  " + fecha_texto + ": no se pudo obtener la generacion despues de varios intentos.")
    return None


def descargar_y_guardar_generacion(fecha):
    """
    Descarga la generacion por fuente de un dia especifico y la
    guarda en la base de datos (convirtiendo de GWh a kWh, para
    mantener consistencia con el resto del sistema).
    """
    print("Consultando generacion por fuente (IDO) del " + fecha.strftime("%Y-%m-%d") + "...")
    totales_gwh = obtener_generacion_de_un_dia(fecha)

    if totales_gwh is not None:
        totales_kwh = {categoria: valor * 1_000_000 for categoria, valor in totales_gwh.items()}
        guardar_generacion_por_fuente(fecha.strftime("%Y-%m-%d"), totales_kwh)

    return totales_gwh


def descargar_generacion_rango(fecha_inicio, fecha_fin):
    """
    Descarga la generacion por fuente para un rango de fechas, dia
    por dia, y la guarda en la base de datos.
    """
    fecha_actual = fecha_inicio

    while fecha_actual <= fecha_fin:
        descargar_y_guardar_generacion(fecha_actual)
        fecha_actual = fecha_actual + timedelta(days=1)


if __name__ == "__main__":
    # El IDO publica con muy poco rezago (normalmente el dia
    # siguiente a las 6:00 AM), asi que usamos un margen de solo 1 dia.
    fecha_fin = datetime.now() - timedelta(days=1)
    fecha_inicio = fecha_fin - timedelta(days=9)

    print("Descargando generacion por fuente (IDO) desde " + str(fecha_inicio.date()) + " hasta " + str(fecha_fin.date()))
    print("")

    descargar_generacion_rango(fecha_inicio, fecha_fin)

    print("")
    print("Proceso terminado.")
