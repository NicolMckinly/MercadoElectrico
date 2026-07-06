"""
Modulo: enviar_alerta_ecopetrol.py
Ubicacion: Correos/enviar_alerta_ecopetrol.py

Revisa si hay convocatorias nuevas de gas natural publicadas por
Ecopetrol, y si las hay, envia un correo con todos los detalles
tecnicos extraidos de cada una.
"""

import sys
import os

CARPETA_PROYECTO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(CARPETA_PROYECTO, "API"))
sys.path.append(os.path.join(CARPETA_PROYECTO, "Correos"))

from monitor_ecopetrol import buscar_convocatorias_nuevas
from enviar_correo import enviar_informe_por_correo


def _construir_cuerpo_del_correo(convocatorias):
    """
    Arma el texto del correo con el detalle de cada convocatoria nueva.
    """
    partes = ["Se detectaron " + str(len(convocatorias)) + " nueva(s) convocatoria(s) de gas natural en Ecopetrol:\n"]

    for convocatoria in convocatorias:
        partes.append("=" * 60)
        partes.append(convocatoria["titulo"])
        partes.append("-" * 60)
        partes.append("Fecha de publicacion: " + convocatoria["fecha_publicacion"])
        partes.append("Fuente: " + convocatoria["fuente"])
        partes.append("Cantidad: " + convocatoria["cantidad"])
        partes.append("Modalidad / Tipo de contrato: " + convocatoria["modalidad"])
        partes.append("Plazo: " + convocatoria["plazo"])
        partes.append("Garantia: " + convocatoria["garantia"])
        partes.append("")

    partes.append("Para ver el detalle completo y los anexos, consulta la pagina oficial de Ecopetrol:")
    partes.append(
        "https://www.ecopetrol.com.co/wps/portal/Home/multisitios/comercial/es/"
        "sondeosyofertas/ofertas-informacion-comercial/informacion-comercial-gn"
    )

    return "\n".join(partes)


def revisar_y_enviar_alerta_ecopetrol():
    """
    Revisa si hay convocatorias nuevas y, si las hay, envia el correo
    de notificacion correspondiente.

    Retorna:
        La cantidad de convocatorias nuevas encontradas.
    """
    nuevas = buscar_convocatorias_nuevas()

    if len(nuevas) == 0:
        print("No hay convocatorias nuevas de Ecopetrol.")
        return 0

    print("Se encontraron " + str(len(nuevas)) + " convocatoria(s) nueva(s). Enviando correo...")

    cuerpo = _construir_cuerpo_del_correo(nuevas)

    carpeta_reportes = os.path.join(CARPETA_PROYECTO, "Reportes")
    archivos_pdf = [f for f in os.listdir(carpeta_reportes) if f.endswith(".pdf")]

    if len(archivos_pdf) > 0:
        archivos_pdf.sort(reverse=True)
        ruta_adjunto = os.path.join(carpeta_reportes, archivos_pdf[0])
        enviar_informe_por_correo(ruta_adjunto, "Nueva(s) convocatoria(s) de Gas Natural - Ecopetrol", cuerpo)
    else:
        print("No hay ningun PDF disponible para adjuntar; no se pudo enviar (el sistema de correo requiere un adjunto).")

    return len(nuevas)


if __name__ == "__main__":
    revisar_y_enviar_alerta_ecopetrol()
