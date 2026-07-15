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

La descarga de Generacion por Fuente (y su grafico) se ejecuta
siempre, en cada corrida del workflow, sin importar si el informe
diario ya se envio hoy, para que la grafica este siempre actualizada.

El informe diario (que incluye el grafico y la tabla del IMAR) se
envia tambien a destinatarios adicionales (Andrea Quintero y Fabian
Barahona), ademas del correo principal configurado en el .env,
unicamente para este informe.

Todas las fechas se calculan usando ahora_colombia() (ver
BaseDatos/zona_horaria.py), en vez de datetime.now(), para que el
sistema siempre use la hora real de Colombia y no la del servidor
(que corre en UTC).

Este archivo es el que se ejecuta automaticamente todos los dias
mediante GitHub Actions (o el Programador de Tareas de Windows).
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

# Destinatarios adicionales que reciben UNICAMENTE el informe diario
# (que incluye el grafico y la tabla del IMAR), ademas del correo
# principal configurado en el .env.
CORREOS_ADICIONALES_IMAR = ["andrea.quintero@tmmorro.com", "fabian.barahona@tmmorro.com"]


def ejecutar_proceso_diario():
    hoy = ahora_colombia()

    print("=" * 60)
    print("REVISANDO CONDICIONES - " + hoy.strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 60)

    # ---------- Revisar y enviar alertas (Modulo 7) ----------
    print("\n--- Revisando alertas ---")
    try:
        from enviar_alertas import revisar_y_enviar_alertas
        revisar_y_enviar_alertas()
    except Exception as error:
        print("ERROR revisando alertas: " + str(error))

    # ---------- Revisar Resumen Ejecutivo Quincenal (Modulo 6) ----------
    print("\n--- Revisando Resumen Ejecutivo Quincenal ---")
    try:
        from main_ejecutivo import ejecutar_resumen_ejecutivo
        ejecutar_resumen_ejecutivo()
    except Exception as error:
        print("ERROR revisando el resumen ejecutivo: " + str(error))

    # ---------- Revisar convocatorias de gas natural de Ecopetrol ----------
    print("\n--- Revisando convocatorias de Ecopetrol ---")
    try:
        from enviar_alerta_ecopetrol import revisar_y_enviar_alerta_ecopetrol
        revisar_y_enviar_alerta_ecopetrol()
    except Exception as error:
        print("ERROR revisando convocatorias de Ecopetrol: " + str(error))

    # ---------- Generacion por Fuente (datos + grafico) ----------
    print("\n--- Descargando Generacion por Fuente ---")
    try:
        from generacion_por_fuente import descargar_generacion_rango

        fecha_fin_gen = hoy - timedelta(days=1)
        fecha_inicio_gen = fecha_fin_gen - timedelta(days=8)
        descargar_generacion_rango(fecha_inicio_gen, fecha_fin_gen)
    except Exception as error:
        print("ERROR en Generacion por Fuente: " + str(error))

    print("\n--- Generando grafico de Generacion por Fuente ---")
    try:
        from grafico_generacion import generar_grafico_generacion
        generar_grafico_generacion()
    except Exception as error:
        print("ERROR generando el grafico de Generacion por Fuente: " + str(error))

    from base_datos import ya_se_envio_hoy, marcar_enviado_hoy

    # Condicion 1: si el informe de hoy ya se envio, no hacemos nada mas.
    if ya_se_envio_hoy("diario"):
        print("El informe diario ya fue enviado hoy. No se hace nada.")
        return

    # Condicion 2: si el IMAR de mañana aun no esta publicado por XM,
    # esperamos (el sistema volvera a revisar en el siguiente ciclo).
    from imar import verificar_imar_de_manana_publicado

    if not verificar_imar_de_manana_publicado():
        print("El IMAR de mañana aun no ha sido publicado por XM. Se revisara de nuevo mas tarde.")
        return

    print("El IMAR de mañana ya esta publicado. Procediendo con el informe diario completo.")
    print("")

    print("=" * 60)
    print("INICIANDO PROCESO DIARIO - " + hoy.strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 60)

    # ---------- 1. Precio de Bolsa ----------
    print("\n--- PASO 1: Descargando Precio de Bolsa ---")
    try:
        from precio_bolsa import obtener_precio_bolsa
        from base_datos import guardar_precio_bolsa

        fecha_fin = hoy - timedelta(days=1)
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

        fecha_fin_imar = hoy + timedelta(days=1)
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
    # Este informe (con el grafico y la tabla del IMAR) se envia
    # tambien a los destinatarios adicionales de CORREOS_ADICIONALES_IMAR,
    # ademas del correo principal del .env.
    print("\n--- PASO 5: Enviando correo ---")
    try:
        if ruta_informe is not None:
            from enviar_correo import enviar_informe_por_correo
            enviado = enviar_informe_por_correo(
                ruta_informe,
                "Informe Diario - Precio de Bolsa Nacional",
                "Adjunto encontraras el informe diario del Precio de Bolsa Nacional, generado automaticamente.",
                destinatarios_extra=CORREOS_ADICIONALES_IMAR
            )
            if enviado:
                marcar_enviado_hoy("diario")
        else:
            print("No se genero el informe, asi que no se envia correo.")
    except Exception as error:
        print("ERROR enviando el correo: " + str(error))

    print("\n" + "=" * 60)
    print("PROCESO DIARIO TERMINADO - " + ahora_colombia().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 60)


if __name__ == "__main__":
    ejecutar_proceso_diario()
