"""
Archivo de utilidad, uso unico.
Limpia la tabla generacion_por_fuente, porque cambiamos el esquema
de categorias (de tecnologias separadas a categorias combinadas) y
no queremos mezclar datos con nombres de categoria antiguos.
"""

import sys
import os

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "BaseDatos"))

from base_datos import obtener_conexion

conexion = obtener_conexion()
cursor = conexion.cursor()
cursor.execute("DELETE FROM generacion_por_fuente")
conexion.commit()
conexion.close()

print("Tabla generacion_por_fuente limpiada correctamente.")
