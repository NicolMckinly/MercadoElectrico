"""
Modulo: backfill_variables_hidrologicas_anual.py
Ubicacion: API/backfill_variables_hidrologicas_anual.py
Se ejecuta UNA SOLA VEZ para descargar Embalses y Aportes de los
ULTIMOS 365 DIAS, y guardarlos en la base de datos. Reutiliza la
funcion descargar_variables_hidrologicas() que ya existe en
variables_hidrologicas.py (la misma que usa el proceso diario, pero
aqui con un rango de un año en vez de solo unos pocos dias).

Este proceso es mas lento que el de Precio de Bolsa, porque cada dia
requiere descargar 6 metricas distintas de XM. Puede tardar bastante
para 365 dias; si se interrumpe, se puede volver a correr sin
problema (los datos ya guardados simplemente se actualizan).
"""
import sys
import os
from datetime import timedelta
CARPETA_PROYECTO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(CARPETA_PROYECTO, "API"))
sys.path.append(os.path.join(CARPETA_PROYECTO, "BaseDatos"))
from variables_hidrologicas import descargar_variables_hidrologicas
from base_datos import consultar_todo_variables_hidrologicas
from zona_horaria import ahora_colombia
def completar_historico_hidrologico_365_dias():
    """
    Descarga y guarda las variables hidrologicas de los ultimos 365
    dias (desde ayer hacia atras).
    """
    hoy = ahora_colombia().replace(tzinfo=None)
    fecha_fin = hoy - timedelta(days=1)
    fecha_inicio = fecha_fin - timedelta(days=365)

    print("Descargando variables hidrologicas desde " + fecha_inicio.strftime("%Y-%m-%d") + " hasta " + fecha_fin.strftime("%Y-%m-%d"))
    print("Esto puede tardar varios minutos...")
    print("")

    descargar_variables_hidrologicas(fecha_inicio, fecha_fin)

    print("")
    historico_final = consultar_todo_variables_hidrologicas()
    print("Proceso terminado. Total de dias en la base de datos ahora: " + str(len(historico_final)))
if __name__ == "__main__":
    completar_historico_hidrologico_365_dias()
