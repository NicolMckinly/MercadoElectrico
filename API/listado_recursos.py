"""
Modulo: listado_recursos.py
Ubicacion: API/listado_recursos.py

Descarga el listado de plantas/recursos de generacion con su tipo
de tecnologia (Hidraulica, Termica, Solar, Eolica, Cogenerador),
usando la API oficial de XM.

Este listado cambia muy poco de un dia a otro (solo cuando entra o
sale una planta del sistema), asi que no hace falta descargarlo
todos los dias. Basta con actualizarlo cada cierto tiempo (por
ejemplo, una vez por semana).
"""

import sys
import os
from datetime import datetime, timedelta
from pydataxm import pydataxm

CARPETA_PROYECTO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(CARPETA_PROYECTO, "BaseDatos"))

from base_datos import guardar_listado_recursos

# Normalizamos los distintos nombres de tecnologia que aparecen en
# los datos de XM, agrupandolos segun lo pedido en la especificacion:
# - Hidraulica (queda sola)
# - Termica (ya incluye carbon, gas y liquidos combinados, porque XM
#   no los separa en la columna Values_Type)
# - Solar y Eolica (combinadas en una sola categoria)
# - Autogeneracion, Cogeneracion y Generacion Distribuida (combinadas
#   en una sola categoria, sin importar la tecnologia base)
def _normalizar_tecnologia(valor_type, valor_rectype):
    valor_type = str(valor_type).strip().upper()
    valor_rectype = str(valor_rectype).strip().upper()

    if valor_rectype in ("AUTOGENERADOR", "GEN. DISTRIBUIDA") or valor_type == "COGENERADOR":
        return "Autogen. y Cogen. y Gen. Distribuida"
    elif valor_type in ("SOLAR", "EOLICA"):
        return "Solar y Eolica"
    elif valor_type == "HIDRAULICA":
        return "Hidraulica"
    elif valor_type == "TERMICA":
        return "Termica"
    else:
        return "Otras tecnologias"


def descargar_listado_recursos():
    """
    Descarga el listado completo de recursos/plantas con su tipo de
    tecnologia, y lo guarda en la base de datos.
    """
    objetoAPI = pydataxm.ReadDB()

    fecha_fin = datetime.now()
    fecha_inicio = fecha_fin - timedelta(days=1)

    print("Descargando listado de recursos...")
    listado = objetoAPI.request_data("ListadoRecursos", "Sistema", fecha_inicio, fecha_fin)

    listado["tecnologia"] = listado.apply(
        lambda fila: _normalizar_tecnologia(fila["Values_Type"], fila["Values_RecType"]),
        axis=1
    )

    tabla_final = listado[["Values_Code", "Values_Name", "tecnologia"]].copy()
    tabla_final.columns = ["codigo", "nombre", "tecnologia"]
    tabla_final = tabla_final.drop_duplicates(subset=["codigo"])

    guardar_listado_recursos(tabla_final)

    print("Listado de recursos guardado: " + str(len(tabla_final)) + " plantas.")

    print("")
    print("Resumen por tecnologia:")
    print(tabla_final["tecnologia"].value_counts())


if __name__ == "__main__":
    descargar_listado_recursos()
