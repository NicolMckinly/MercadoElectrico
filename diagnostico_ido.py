"""
Archivo temporal de diagnostico.
Prueba la API del IDO (Informe Diario de Operacion) directamente,
para ver la estructura de la respuesta.
"""

import requests

url = "https://ido.xm.com.co/ArchivoIdo/ObtenerArchivosPorDia"
parametros = {
    "fecha": "2026-07-04",
    "carpeta": "Ido_Generacion",
    "archivo": "generacion"
}

# Algunos sitios revisan el "User-Agent" (que identifica que la
# peticion viene de un navegador). Se lo agregamos por si acaso.
encabezados = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

respuesta = requests.get(url, params=parametros, headers=encabezados, timeout=30)

print("Codigo de respuesta:", respuesta.status_code)
print("Tipo de contenido:", respuesta.headers.get("Content-Type"))
print("")
print("Primeros 2000 caracteres de la respuesta:")
print(respuesta.text[:2000])
