"""
Archivo: main_ejecutivo.py
Ubicacion: raiz del proyecto (C:\\MercadoElectrico\\main_ejecutivo.py)

Revisa si HOY es el dia 15 del mes, o el ultimo dia del mes. Si es
asi (y no se ha enviado ya hoy), genera el Resumen Ejecutivo
completo en PDF y lo envia por correo. Cualquier otro dia, no hace
nada.

Este archivo se ejecuta automaticamente todos los dias (junto con
el resto del sistema), pero solo actua realmente esos dos dias
especificos de cada mes.
"""

import sys
import os
import calendar
from datetime import datetime

CARPETA_PROYECTO = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(CARPETA_PROYECTO, "BaseDatos"))
sys.path.append(os.path.join(CARPETA_PROYECTO, "Analisis"))
sys.path.append(os.path.join(CARPETA_PROYECTO, "Graficas"))
sys.path.append(os.path.join(CARPETA_PROYECTO, "Reportes"))
sys.path.append(os.path.join(CARPETA_PROYECTO, "Correos"))

NOMBRE_PROCESO = "resumen_ejecutivo"


def _hoy_es_dia_de_envio():
    """
    Retorna True si hoy es el dia 15 del mes, o el ultimo dia del mes.
    """
    hoy = datetime.now()
    ultimo_dia_del_mes = calendar.monthrange(hoy.year, hoy.month)[1]

    return hoy.day == 15 or hoy.day == ultimo_dia_del_mes


def ejecutar_resumen_ejecutivo():
    print("=" * 60)
    print("REVISANDO RESUMEN EJECUTIVO - " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 60)

    from base_datos import ya_se_envio_hoy, marcar_enviado_hoy

    if not _hoy_es_dia_de_envio():
        print("Hoy no es dia 15 ni el ultimo dia del mes. No se hace nada.")
        return

    if ya_se_envio_hoy(NOMBRE_PROCESO):
        print("El resumen ejecutivo ya fue enviado hoy. No se hace nada.")
        return

    print("Hoy corresponde enviar el Resumen Ejecutivo. Generando...")

    try:
        from generar_informe_ejecutivo import generar_informe_ejecutivo
        ruta_informe = generar_informe_ejecutivo()

        if ruta_informe is not None:
            from enviar_correo import enviar_informe_por_correo
            enviado = enviar_informe_por_correo(
                ruta_informe,
                "Resumen Ejecutivo Quincenal - Mercado Electrico",
                "Adjunto encontraras el resumen ejecutivo, con el estado completo del mercado electrico."
            )
            if enviado:
                marcar_enviado_hoy(NOMBRE_PROCESO)
        else:
            print("No se pudo generar el informe (datos insuficientes).")

    except Exception as error:
        print("ERROR generando/enviando el resumen ejecutivo: " + str(error))

    # Junto con el resumen ejecutivo, tambien enviamos el Informe
    # del Mercado de Gas.
    try:
        from generar_informe_gas import generar_informe_gas
        ruta_informe_gas = generar_informe_gas()

        if ruta_informe_gas is not None:
            from enviar_correo import enviar_informe_por_correo
            enviar_informe_por_correo(
                ruta_informe_gas,
                "Informe del Mercado de Gas Natural",
                "Adjunto encontraras el informe del mercado de gas natural, con las convocatorias detectadas de Ecopetrol."
            )
    except Exception as error:
        print("ERROR generando/enviando el informe de gas: " + str(error))

    print("=" * 60)
    print("PROCESO TERMINADO - " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 60)


if __name__ == "__main__":
    ejecutar_resumen_ejecutivo()
