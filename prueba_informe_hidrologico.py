"""
Script TEMPORAL de prueba.
Regenera unicamente el PDF del informe hidrologico (sin descargar
datos nuevos, sin actualizar la senda, y sin enviar correo), para
poder revisar visualmente los ajustes recientes sin duplicar el
envio del dia.

Borrar este archivo cuando terminemos de probar.
"""
import sys
import os

CARPETA_PROYECTO = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(CARPETA_PROYECTO, "API"))
sys.path.append(os.path.join(CARPETA_PROYECTO, "BaseDatos"))
sys.path.append(os.path.join(CARPETA_PROYECTO, "Analisis"))
sys.path.append(os.path.join(CARPETA_PROYECTO, "Graficas"))
sys.path.append(os.path.join(CARPETA_PROYECTO, "Reportes"))

from generar_informe_hidrologico import generar_informe_hidrologico

if __name__ == "__main__":
    print("Regenerando PDF del informe hidrologico (solo prueba, sin correo)...")
    ruta = generar_informe_hidrologico()
    if ruta is not None:
        print("PDF de prueba generado: " + ruta)
    else:
        print("No se pudo generar el PDF (revisa si hay datos suficientes).")
