"""
Archivo temporal de verificacion.
Muestra el contenido guardado de variables hidrologicas.
"""

import sys
import os

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "BaseDatos"))

from base_datos import consultar_todo_variables_hidrologicas

datos = consultar_todo_variables_hidrologicas()
print(datos.to_string())
