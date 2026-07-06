"""
Modulo: enviar_alertas.py
Ubicacion: Correos/enviar_alertas.py

Revisa las alertas activas del sistema (Modulo 7) y, para cada una
que no se haya enviado todavia el dia de hoy, envia un correo
independiente con: el mensaje de la alerta, una explicacion basada
en los datos (usando los comentarios automaticos que ya genera el
sistema), y la grafica correspondiente adjunta.

Cada tipo de alerta se envia como maximo UNA vez por dia, aunque el
sistema la siga detectando en revisiones posteriores (por ejemplo,
si el monitor corre cada 10 minutos), para no saturar el correo.
"""

import sys
import os

CARPETA_PROYECTO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(CARPETA_PROYECTO, "BaseDatos"))
sys.path.append(os.path.join(CARPETA_PROYECTO, "Analisis"))
sys.path.append(os.path.join(CARPETA_PROYECTO, "Correos"))

from base_datos import ya_se_envio_hoy, marcar_enviado_hoy
from alertas import generar_todas_las_alertas
from enviar_correo import enviar_informe_por_correo

TITULOS_POR_TIPO = {
    "alerta_escasez": "ALERTA: Precio de Bolsa supero el Precio de Escasez",
    "alerta_variacion": "ALERTA: Variacion importante en el Precio de Bolsa",
    "alerta_embalses": "ALERTA: Embalses por debajo del umbral configurado",
}


def revisar_y_enviar_alertas():
    """
    Revisa todas las alertas activas y envia un correo por cada una
    que no se haya enviado hoy todavia.

    Retorna:
        La cantidad de alertas nuevas que se enviaron.
    """
    alertas = generar_todas_las_alertas()

    if len(alertas) == 0:
        print("No hay alertas activas en este momento.")
        return 0

    alertas_enviadas = 0

    for alerta in alertas:
        if ya_se_envio_hoy(alerta["tipo"]):
            print("La alerta '" + alerta["tipo"] + "' ya se envio hoy. Se omite.")
            continue

        titulo = TITULOS_POR_TIPO.get(alerta["tipo"], "ALERTA del Sistema de Mercado Electrico")

        cuerpo_mensaje = (
            alerta["mensaje"] + "\n\n"
            + "Explicacion basada en los datos actuales:\n"
            + alerta["explicacion"] + "\n\n"
            + "Este es un correo de alerta automatico. Para mas detalle, "
            + "consulta el informe diario o hidrologico correspondiente."
        )

        if alerta["ruta_grafico"] is not None and os.path.exists(alerta["ruta_grafico"]):
            enviado = enviar_informe_por_correo(alerta["ruta_grafico"], titulo, cuerpo_mensaje)
        else:
            print("No hay grafico disponible para adjuntar en esta alerta; no se envia (revisar manualmente).")
            enviado = False

        if enviado:
            marcar_enviado_hoy(alerta["tipo"])
            alertas_enviadas += 1

    return alertas_enviadas


if __name__ == "__main__":
    print("Revisando y enviando alertas...")
    print("")

    cantidad = revisar_y_enviar_alertas()

    print("")
    print("Total de alertas nuevas enviadas: " + str(cantidad))
