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

Este archivo se ejecuta automaticamente los MARTES y JUEVES, entre
las 8:00 AM y las 12:00 PM hora Colombia (revisando cada 15 minutos
gracias al cron externo). Apenas XM publica los datos del dia
anterior, se genera y envia el informe UNA SOLA VEZ ese dia; si XM
aun no ha publicado, se vuelve a intentar en la siguiente revision.

Este informe se envia tambien a destinatarios adicionales (Andrea
Quintero y Fabian Barahona), ademas del correo principal configurado
en el .env.

Usa ahora_colombia() (ver BaseDatos/zona_horaria.py) en vez de
datetime.now(), para que el sistema siempre use la hora real de
Colombia y no la hora UTC del servidor (que va 5 horas adelante).
"""
import sys
import os
from datetime import timedelta

CARPETA_PROYECTO = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(CARPETA_PROYECTO, "API"))
sys.path.append(os.path.join(CARPETA_PROYECTO, "BaseDatos"))
sys.path.append(os.path.join(CARPETA_PROYECTO, "Analisis"))
sys.path.append(os.path.join(CARPETA_PROYECTO, "Graficas"))
sys.path.append(os.path.join(CARPETA_PROYECTO, "Reportes"))
sys.path.append(os.path.join(CARPETA_PROYECTO, "Correos"))

from zona_horaria import ahora_colombia

# Destinatarios adicionales que reciben UNICAMENTE el informe
# hidrologico, ademas del correo principal configurado en el .env.
CORREOS_ADICIONALES_HIDROLOGICO = ["andrea.quintero@tmmorro.com", "fabian.barahona@tmmorro.com"]


def ejecutar_proceso_hidrologico():
    hoy = ahora_colombia()

    print("=" * 60)
    print("REVISANDO CONDICIONES HIDROLOGICO - " + hoy.strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 60)

    from base_datos import ya_se_envio_hoy, marcar_enviado_hoy

    # Condicion 1: si el informe hidrologico de hoy ya se envio, no
    # hacemos nada mas (para no duplicar el correo).
    if ya_se_envio_hoy("hidrologico"):
        print("El informe hidrologico ya fue enviado hoy. No se hace nada.")
        return

    # Condicion 2: si los datos hidrologicos de ayer aun no estan
    # publicados por XM, esperamos (se volvera a revisar en la
    # siguiente corrida del cron, hasta las 12:00 PM).
    from variables_hidrologicas import variables_hidrologicas_de_ayer_estan_publicadas

    if not variables_hidrologicas_de_ayer_estan_publicadas():
        print("Los datos hidrologicos de ayer aun no estan publicados por XM. Se revisara de nuevo mas tarde.")
        return

    print("Los datos hidrologicos de ayer ya estan publicados. Procediendo con el informe completo.")
    print("")

    print("=" * 60)
    print("INICIANDO PROCESO HIDROLOGICO - " + hoy.strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 60)
    # ---------- 1. Variables Hidrologicas ----------
    print("\n--- PASO 1: Descargando Variables Hidrologicas ---")
    try:
        from variables_hidrologicas import descargar_variables_hidrologicas
        fecha_fin = hoy - timedelta(days=1)
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
            enviado = enviar_informe_por_correo(
                ruta_informe,
                "Informe de Variables Hidrologicas",
                "Adjunto encontraras el informe de variables hidrologicas, generado automaticamente.",
                destinatarios_extra=CORREOS_ADICIONALES_HIDROLOGICO
            )
            if enviado:
                marcar_enviado_hoy("hidrologico")
        else:
            print("No se genero el informe, asi que no se envia correo.")
    except Exception as error:
        print("ERROR enviando el correo: " + str(error))
    print("\n" + "=" * 60)
    print("PROCESO HIDROLOGICO TERMINADO - " + ahora_colombia().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 60)


if __name__ == "__main__":
    ejecutar_proceso_hidrologico()
