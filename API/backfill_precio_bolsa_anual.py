"""
Modulo: backfill_precio_bolsa_anual.py
Ubicacion: API/backfill_precio_bolsa_anual.py
Este archivo se ejecuta UNA SOLA VEZ (o cada vez que se quiera
completar historico faltante) para descargar todo el Precio de
Bolsa real de los ULTIMOS 365 DIAS (un año completo hacia atras
desde ayer), y guardarlo en la base de datos.

Esto es necesario para que las graficas de 12 meses moviles del
Resumen Ejecutivo Quincenal tengan datos desde el inicio del rango,
en vez de mostrar el eje X vacio en los meses anteriores a cuando
el sistema empezo a funcionar.

Como se consulta dia por dia (usando la misma logica robusta de
precio_bolsa.py, con reintentos), este proceso puede tardar varios
minutos. Ya trae logica para saltarse los dias que ya esten
guardados, asi que se puede volver a correr sin problema si se
interrumpe a la mitad.
"""
import sys
import os
from datetime import timedelta
CARPETA_PROYECTO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(CARPETA_PROYECTO, "API"))
sys.path.append(os.path.join(CARPETA_PROYECTO, "BaseDatos"))
from precio_bolsa import obtener_precio_bolsa
from base_datos import guardar_precio_bolsa, consultar_todo_precio_bolsa
from zona_horaria import ahora_colombia
def completar_historico_365_dias():
    """
    Descarga y guarda el Precio de Bolsa real de los ultimos 365
    dias (desde ayer hacia atras), saltandose los dias que ya
    esten guardados en la base de datos.
    """
    hoy = ahora_colombia().replace(tzinfo=None)
    fecha_limite = hoy - timedelta(days=1)
    fecha_inicio = fecha_limite - timedelta(days=365)

    historico_actual = consultar_todo_precio_bolsa()
    fechas_ya_guardadas = set(historico_actual["fecha"]) if len(historico_actual) > 0 else set()

    print("Verificando historico desde " + fecha_inicio.strftime("%Y-%m-%d") + " hasta " + fecha_limite.strftime("%Y-%m-%d"))
    print("Dias ya guardados actualmente: " + str(len(fechas_ya_guardadas)))
    print("")

    fecha_actual = fecha_inicio
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
    completar_historico_365_dias()
