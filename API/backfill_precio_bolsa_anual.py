"""
Modulo: backfill_precio_bolsa_anual.py
Ubicacion: API/backfill_precio_bolsa_anual.py

Este archivo se ejecuta UNA SOLA VEZ (o cada vez que se quiera
completar historico faltante) para descargar todo el Precio de
Bolsa real desde el 1 de enero del año en curso hasta hoy, y
guardarlo en la base de datos.

Esto es necesario porque el sistema empezo a funcionar a finales de
junio, asi que los meses anteriores (enero a mayo, y parte de junio)
todavia no estaban en la base de datos, aunque XM ya los tiene
publicados y cerrados desde hace tiempo.

Como se consulta dia por dia (usando la misma logica robusta de
precio_bolsa.py, con reintentos), este proceso puede tardar varios
minutos dependiendo de cuantos dias falten.
"""

import sys
import os
from datetime import datetime, timedelta

CARPETA_PROYECTO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(CARPETA_PROYECTO, "API"))
sys.path.append(os.path.join(CARPETA_PROYECTO, "BaseDatos"))

from precio_bolsa import obtener_precio_bolsa
from base_datos import guardar_precio_bolsa, consultar_todo_precio_bolsa


def completar_historico_desde_enero():
    """
    Descarga y guarda el Precio de Bolsa real desde el 1 de enero
    del año en curso hasta hace unos dias (dejando el mismo margen
    de seguridad que usa precio_bolsa.py para evitar dias aun no
    publicados).
    """
    hoy = datetime.now()
    primer_dia_del_anio = datetime(hoy.year, 1, 1)

    # Revisamos que fechas ya tenemos, para no re-descargar innecesariamente
    historico_actual = consultar_todo_precio_bolsa()
    fechas_ya_guardadas = set(historico_actual["fecha"]) if len(historico_actual) > 0 else set()

    fecha_limite = hoy - timedelta(days=1)

    print("Verificando historico desde " + primer_dia_del_anio.strftime("%Y-%m-%d") + " hasta " + fecha_limite.strftime("%Y-%m-%d"))
    print("Dias ya guardados actualmente: " + str(len(fechas_ya_guardadas)))
    print("")

    fecha_actual = primer_dia_del_anio
    total_descargados = 0

    while fecha_actual <= fecha_limite:
        fecha_texto = fecha_actual.strftime("%Y-%m-%d")

        if fecha_texto in fechas_ya_guardadas:
            fecha_actual = fecha_actual + timedelta(days=1)
            continue

        datos_del_dia = obtener_precio_bolsa(fecha_actual, fecha_actual)

        if len(datos_del_dia) > 0:
            guardar_precio_bolsa(datos_del_dia)
            total_descargados += 1

        fecha_actual = fecha_actual + timedelta(days=1)

    print("")
    print("Proceso terminado. Dias nuevos descargados y guardados: " + str(total_descargados))

    historico_final = consultar_todo_precio_bolsa()
    print("Total de dias en la base de datos ahora: " + str(len(historico_final)))


if __name__ == "__main__":
    completar_historico_desde_enero()
