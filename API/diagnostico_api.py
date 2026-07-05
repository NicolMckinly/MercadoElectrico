"""
Archivo temporal de diagnóstico.
Hace una petición manual (sin pydataxm) para ver el mensaje
de error exacto que devuelve el servidor de XM.
"""

import requests
from datetime import datetime, timedelta

# Probamos con un rango de fechas reciente
fecha_fin = datetime.now() - timedelta(days=1)
fecha_inicio = fecha_fin - timedelta(days=2)

cuerpo_peticion = {
    "MetricId": "PrecBolsNaci",
    "StartDate": fecha_inicio.strftime("%Y-%m-%d"),
    "EndDate": fecha_fin.strftime("%Y-%m-%d"),
    "Entity": "Sistema"
}

print("Enviando petición con estas fechas:", cuerpo_peticion["StartDate"], "a", cuerpo_peticion["EndDate"])

respuesta = requests.post("https://servapibi.xm.com.co/hourly", json=cuerpo_peticion)

print("\nCódigo de respuesta HTTP:", respuesta.status_code)
print("\nTexto de la respuesta del servidor:")
print(respuesta.text)