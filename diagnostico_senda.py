"""
Archivo temporal de diagnostico.
Prueba la descarga del archivo Excel de la Senda de Referencia,
usando el mismo patron de URL que descubrimos para el IMAR.
"""

import requests

URL_BASE = "https://api-portalxm.xm.com.co/administracion-archivos/ficheros/mostrar-url"

ruta_archivo = "M:/InformacionAgentes/Usuarios/Publico/PlaneacionOperacion/Senda de Referencia/2026/Supuestos_Resultados_SendaReferencia_Invierno_2026.xlsx"

parametros = {
    "ruta": ruta_archivo,
    "nombreBlobContainer": "storageportalxm"
}

respuesta = requests.get(URL_BASE, params=parametros, timeout=30)

print("Codigo de respuesta:", respuesta.status_code)
print("Tipo de contenido:", respuesta.headers.get("Content-Type"))
print("Tamano de la respuesta (bytes):", len(respuesta.content))

# Si parece ser un archivo Excel valido, lo guardamos para revisarlo
if respuesta.status_code == 200 and len(respuesta.content) > 1000:
    with open("senda_referencia_prueba.xlsx", "wb") as archivo:
        archivo.write(respuesta.content)
    print("Archivo guardado como senda_referencia_prueba.xlsx en la carpeta actual.")
else:
    print("Primeros 500 caracteres de la respuesta (por si es un mensaje de error):")
    print(respuesta.text[:500])
