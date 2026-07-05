"""
Archivo temporal de diagnostico.
Muestra la respuesta cruda de Google News RSS, para saber por que
la busqueda no esta encontrando resultados.
"""

import requests

parametros = {
    "q": "precio de bolsa energia Colombia XM",
    "hl": "es-419",
    "gl": "CO",
    "ceid": "CO:es"
}

encabezados = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

respuesta = requests.get("https://news.google.com/rss/search", params=parametros, headers=encabezados, timeout=30)

print("URL final consultada:", respuesta.url)
print("Codigo de respuesta:", respuesta.status_code)
print("")
print("Primeros 3000 caracteres de la respuesta:")
print(respuesta.text[:3000])
