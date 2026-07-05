"""
Archivo temporal de diagnostico.
Busca listados de recursos/plantas que incluyan su tipo de tecnologia.
"""

from pydataxm import pydataxm

objetoAPI = pydataxm.ReadDB()
catalogo = objetoAPI.get_collections()

resultado = catalogo[catalogo['Type'] == 'ListsEntities']
print(resultado[['MetricId', 'MetricName', 'Entity']].to_string())
