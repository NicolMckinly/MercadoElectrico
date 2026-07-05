"""
Archivo: main_hidrologico.py
Ubicacion: raiz del proyecto (C:\\MercadoElectrico\\main_hidrologico.py)

Este es el "script maestro" del informe hidrologico (Modulo 3).
Ejecuta, en orden, todos los pasos necesarios:

1. Descarga las variables hidrologicas (embalses, aportes, etc.)
2. Actualiza la Senda de Referencia (si XM publico una nueva).
3. Genera los graficos de embalses y aportes.
4. Genera el informe PDF hidrologico.
5. Envia el informe por correo.

Este archivo se ejecuta automaticamente solo los MARTES y JUEVES,
segun la especificacion original del proyecto (esto se controla
desde la programacion de GitHub Actions, no desde este archivo).
"""

import sys
import os
from datetime import datetime, timedelta

CARPETA_PROYECTO = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(CARPETA_PROYECTO, "API"))
sys.path.append(os.path.join(CARPETA_PROYECTO, "BaseDatos"))
sys.path.append(os.path.join(CARPETA_PROYECTO, "Analisis"))
sys.path.append(os.path.join(CARPETA_PROYECTO, "Graficas"))
sys.path.append(os.path.join(CARPETA_PROYECTO, "Reportes"))
sys.path.append(os.path.join(CARPETA_PROYECTO, "Correos"))


def ejecutar_proceso_hidrologico():
    print("=" * 60)
    print("INICIANDO PROCESO HIDROLOGICO - " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 60)

    # ---------- 1. Variables Hidrologicas ----------
    print("\n--- PASO 1: Descargando Variables Hidrologicas ---")
    try:
        from variables_hidrologicas import descargar_variables_hidrologicas

        fecha_fin = datetime.now() - timedelta(days=1)
        fecha_inicio = fecha_fin - timedelta(days=5)
        descargar_variables_hidrologicas(fecha_inicio, fecha_fin)
    except Exception as error:
        print("ERROR en Variables Hidrologicas: " + str(error))

    # ---------- 2. Senda de Referencia ----------
    print("\n--- PASO 2: Actualizando Senda de Referencia ---")
    try:
        from senda_referencia import obtener_y_guardar_senda_referencia
        obtener_y_guardar_senda_referencia()
    except Exception as error:
        print("ERROR en Senda de Referencia: " + str(error))

    # ---------- 3. Generar informe PDF (incluye los graficos) ----------
    print("\n--- PASO 3: Generando informe hidrologico PDF ---")
    ruta_informe = None
    try:
        from generar_informe_hidrologico import generar_informe_hidrologico
        ruta_informe = generar_informe_hidrologico()
    except Exception as error:
        print("ERROR generando el informe hidrologico: " + str(error))

    # ---------- 4. Enviar por correo ----------
    print("\n--- PASO 4: Enviando correo ---")
    try:
        if ruta_informe is not None:
            from enviar_correo import enviar_informe_por_correo
            enviar_informe_por_correo(
                ruta_informe,
                "Informe de Variables Hidrologicas",
                "Adjunto encontraras el informe de variables hidrologicas, generado automaticamente."
            )
        else:
            print("No se genero el informe, asi que no se envia correo.")
    except Exception as error:
        print("ERROR enviando el correo: " + str(error))

    print("\n" + "=" * 60)
    print("PROCESO HIDROLOGICO TERMINADO - " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 60)


if __name__ == "__main__":
    ejecutar_proceso_hidrologico()
