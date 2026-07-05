"""
Archivo temporal de diagnostico.
Prueba una peticion manual (sin pydataxm) para traer la Generacion
por Recurso de un solo dia, y ver la estructura de la respuesta.
"""

import requests
from datetime import datetime, timedelta

fecha = datetime.now() - timedelta(days=7)
fecha_texto = fecha.strftime("%Y-%m-%d")

cuerpo_peticion = {
    "MetricId": "Gene",
    "StartDate": fecha_texto,
    "EndDate": fecha_texto,
    "Entity": "Recurso"
}

print("Consultando Generacion por Recurso del " + fecha_texto + "...")
respuesta = requests.post("https://servapibi.xm.com.co/hourly", json=cuerpo_peticion, timeout=60)

print("Codigo de respuesta:", respuesta.status_code)

if respuesta.status_code == 200:
    datos_json = respuesta.json()
    items = datos_json["Items"]
    print("Cantidad de dias en la respuesta:", len(items))

    if len(items) > 0:
        entidades = items[0]["HourlyEntities"]
        print("Cantidad de recursos/plantas en ese dia:", len(entidades))
        print("")
        print("Ejemplo del primer recurso:")
        print(entidades[0])
else:
    print("Primeros 500 caracteres de la respuesta:")
    print(respuesta.text[:500])
