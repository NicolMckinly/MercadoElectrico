"""
Archivo temporal de diagnostico.
Muestra todos los tipos de tecnologia unicos que existen, y una
muestra de los datos de Generacion por Recurso.
"""

from pydataxm import pydataxm
from datetime import datetime, timedelta

objetoAPI = pydataxm.ReadDB()

fecha_fin = datetime.now()
fecha_inicio = fecha_fin - timedelta(days=1)

listado = objetoAPI.request_data("ListadoRecursos", "Sistema", fecha_inicio, fecha_fin)

print("Tipos de tecnologia unicos (Values_Type):")
print(listado["Values_Type"].value_counts())
print("")

print("Consultando Generacion por Recurso (esto puede tardar un poco)...")
fecha_generacion = datetime.now() - timedelta(days=7)
generacion = objetoAPI.request_data("Gene", "Recurso", fecha_generacion, fecha_generacion)

print("")
print("Columnas de Generacion por Recurso:")
print(generacion.columns.tolist())
print("")
print("Cantidad de recursos/plantas en el resultado:", len(generacion))
print("")
print("Primeras 10 filas:")
print(generacion.head(10).to_string())
