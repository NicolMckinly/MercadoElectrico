"""
Modulo: backfill_generacion_anual.py
Ubicacion: API/backfill_generacion_anual.py
Se ejecuta UNA SOLA VEZ para intentar descargar la Generacion por
Fuente de los ULTIMOS 365 DIAS, y guardarla en la base de datos.
Reutiliza descargar_generacion_rango() que ya existe en
generacion_por_fuente.py.

NOTA IMPORTANTE: la fuente de estos datos es el IDO (Informe Diario
de Operacion) de XM, que es un sistema pensado principalmente para
publicaciones recientes. Es posible que el IDO NO tenga disponible
el historico completo de un año hacia atras; en ese caso, los dias
mas antiguos simplemente se omitiran (apareceran como "aun no
publicado" en el log), y la grafica de 12 meses seguira mostrando un
hueco en esas fechas hasta que no haya forma de completarlo por esta
via. Esto no es un error del script, es una limitacion de la fuente
de datos.
"""
import sys
import os
from datetime import timedelta
CARPETA_PROYECTO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(CARPETA_PROYECTO, "API"))
sys.path.append(os.path.join(CARPETA_PROYECTO, "BaseDatos"))
from generacion_por_fuente import descargar_generacion_rango
from base_datos import consultar_todo_generacion_por_fuente
from zona_horaria import ahora_colombia
def completar_historico_generacion_365_dias():
    """
    Intenta descargar y guardar la generacion por fuente de los
    ultimos 365 dias (desde ayer hacia atras). Los dias que el IDO
    no tenga disponibles se omiten automaticamente.
    """
    hoy = ahora_colombia().replace(tzinfo=None)
    fecha_fin = hoy - timedelta(days=1)
    fecha_inicio = fecha_fin - timedelta(days=365)

    print("Intentando descargar generacion por fuente desde " + fecha_inicio.strftime("%Y-%m-%d") + " hasta " + fecha_fin.strftime("%Y-%m-%d"))
    print("(el IDO puede no tener disponibles los dias mas antiguos; esos se omitiran)")
    print("")

    descargar_generacion_rango(fecha_inicio, fecha_fin)

    print("")
    historico_final = consultar_todo_generacion_por_fuente()
    dias_unicos = historico_final["fecha"].nunique() if len(historico_final) > 0 else 0
    print("Proceso terminado. Total de dias distintos en la base de datos ahora: " + str(dias_unicos))
if __name__ == "__main__":
    completar_historico_generacion_365_dias()
