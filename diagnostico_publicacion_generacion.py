"""
Archivo temporal de diagnostico.
Prueba la disponibilidad de datos de Generacion por Recurso en los
ultimos dias, para saber con cuanta anticipacion realmente hace
falta el margen de seguridad.
"""

import requests
from datetime import datetime, timedelta

for dias_atras in range(1, 8):
    fecha = datetime.now() - timedelta(days=dias_atras)
    fecha_texto = fecha.strftime("%Y-%m-%d")

    cuerpo_peticion = {
        "MetricId": "Gene",
        "StartDate": fecha_texto,
        "EndDate": fecha_texto,
        "Entity": "Recurso"
    }

    respuesta = requests.post("https://servapibi.xm.com.co/hourly", json=cuerpo_peticion, timeout=60)

    if respuesta.status_code == 200:
        datos_json = respuesta.json()
        cantidad_items = len(datos_json.get("Items", []))
        print(fecha_texto + " (hace " + str(dias_atras) + " dias): OK, " + str(cantidad_items) + " recursos encontrados")
    else:
        print(fecha_texto + " (hace " + str(dias_atras) + " dias): codigo " + str(respuesta.status_code))
