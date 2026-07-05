"""
Archivo temporal de diagnostico.
Hace una peticion manual al endpoint /daily de XM para ver la
estructura exacta de la respuesta del Precio Marginal de Escasez.
"""

import requests
from datetime import datetime, timedelta

fecha_fin = datetime.now()
fecha_inicio = fecha_fin - timedelta(days=10)

cuerpo_peticion = {
    "MetricId": "PrecEscaMarg",
    "StartDate": fecha_inicio.strftime("%Y-%m-%d"),
    "EndDate": fecha_fin.strftime("%Y-%m-%d"),
    "Entity": "Sistema"
}

print("Enviando peticion con estas fechas:", cuerpo_peticion["StartDate"], "a", cuerpo_peticion["EndDate"])

respuesta = requests.post("https://servapibi.xm.com.co/daily", json=cuerpo_peticion)

print("")
print("Codigo de respuesta HTTP:", respuesta.status_code)
print("")
print("Texto de la respuesta del servidor:")
print(respuesta.text)
