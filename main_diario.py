"""
Archivo: main_diario.py
Ubicacion: raiz del proyecto (C:\\MercadoElectrico\\main_diario.py)

Este es el "script maestro" del informe diario (Modulo 1). Ejecuta,
en orden, todos los pasos necesarios para que el sistema funcione
de principio a fin sin intervencion manual:

1. Descarga el Precio de Bolsa mas reciente y lo guarda.
2. Descarga el IMAR mas reciente (incluyendo el de mañana) y lo guarda.
3. Descarga el Precio de Escasez vigente y lo guarda.
4. Genera el grafico mensual y el grafico anual.
5. Genera el informe PDF completo.
6. Envia el informe por correo.

Este archivo es el que se ejecuta automaticamente todos los dias
mediante GitHub Actions (o el Programador de Tareas de Windows).
"""

import sys
import os
from datetime import datetime

CARPETA_PROYECTO = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(CARPETA_PROYECTO, "API"))
sys.path.append(os.path.join(CARPETA_PROYECTO, "BaseDatos"))
sys.path.append(os.path.join(CARPETA_PROYECTO, "Analisis"))
sys.path.append(os.path.join(CARPETA_PROYECTO, "Graficas"))
sys.path.append(os.path.join(CARPETA_PROYECTO, "Reportes"))
sys.path.append(os.path.join(CARPETA_PROYECTO, "Correos"))


def ejecutar_proceso_diario():
    print("=" * 60)
    print("INICIANDO PROCESO DIARIO - " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 60)

    # ---------- 1. Precio de Bolsa ----------
    print("\n--- PASO 1: Descargando Precio de Bolsa ---")
    try:
        from precio_bolsa import obtener_precio_bolsa
        from base_datos import guardar_precio_bolsa
        from datetime import timedelta

        fecha_fin = datetime.now() - timedelta(days=1)
        fecha_inicio = fecha_fin - timedelta(days=5)
        datos_bolsa = obtener_precio_bolsa(fecha_inicio, fecha_fin)
        guardar_precio_bolsa(datos_bolsa)
    except Exception as error:
        print("ERROR en Precio de Bolsa: " + str(error))

    # ---------- 2. IMAR ----------
    print("\n--- PASO 2: Descargando IMAR ---")
    try:
        from imar import obtener_imar
        from base_datos import guardar_imar
        from datetime import timedelta

        fecha_fin_imar = datetime.now() + timedelta(days=1)
        fecha_inicio_imar = fecha_fin_imar - timedelta(days=6)
        datos_imar = obtener_imar(fecha_inicio_imar, fecha_fin_imar)
        guardar_imar(datos_imar)
    except Exception as error:
        print("ERROR en IMAR: " + str(error))

    # ---------- 3. Precio de Escasez ----------
    print("\n--- PASO 3: Descargando Precio de Escasez ---")
    try:
        from precio_escasez import obtener_precio_escasez_reciente
        from base_datos import guardar_precio_escasez

        fecha_escasez, valor_escasez = obtener_precio_escasez_reciente()
        if valor_escasez is not None:
            guardar_precio_escasez(fecha_escasez, valor_escasez)
    except Exception as error:
        print("ERROR en Precio de Escasez: " + str(error))

    # ---------- 4. Generar informe PDF (incluye los graficos) ----------
    print("\n--- PASO 4: Generando informe PDF ---")
    ruta_informe = None
    try:
        from generar_informe_diario import generar_informe_diario
        ruta_informe = generar_informe_diario()
    except Exception as error:
        print("ERROR generando el informe: " + str(error))

    # ---------- 5. Enviar por correo ----------
    print("\n--- PASO 5: Enviando correo ---")
    try:
        if ruta_informe is not None:
            from enviar_correo import enviar_informe_por_correo
            enviar_informe_por_correo(
                ruta_informe,
                "Informe Diario - Precio de Bolsa Nacional",
                "Adjunto encontraras el informe diario del Precio de Bolsa Nacional, generado automaticamente."
            )
        else:
            print("No se genero el informe, asi que no se envia correo.")
    except Exception as error:
        print("ERROR enviando el correo: " + str(error))

    print("\n" + "=" * 60)
    print("PROCESO DIARIO TERMINADO - " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 60)


if __name__ == "__main__":
    ejecutar_proceso_diario()
