"""
Archivo temporal de diagnostico.
Muestra el contenido completo de la hoja Senda_Embalse, para ubicar
exactamente en que fila empiezan los datos de Fecha y Embalse SIN.
"""

import pandas as pd

df = pd.read_excel("senda_referencia_prueba.xlsx", sheet_name="Senda_Embalse", header=None, nrows=20)
print(df.to_string())
