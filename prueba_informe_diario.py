"""
Script TEMPORAL de prueba.
Regenera unicamente el PDF del informe diario (sin descargar datos
nuevos y sin enviar correo), para poder revisar visualmente los
ajustes recientes del IMAR / PB Proyectado sin duplicar el envio
del dia.

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

from generar_informe_diario import generar_informe_diario

if __name__ == "__main__":
    print("Regenerando PDF del informe diario (solo prueba, sin correo)...")
    ruta = generar_informe_diario()
    if ruta is not None:
        print("PDF de prueba generado: " + ruta)
    else:
        print("No se pudo generar el PDF (revisa si hay datos suficientes).")
