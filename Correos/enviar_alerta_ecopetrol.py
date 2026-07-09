"""
Modulo: enviar_alerta_ecopetrol.py
Ubicacion: Correos/enviar_alerta_ecopetrol.py
Revisa si hay convocatorias nuevas de gas natural publicadas por
Ecopetrol, y si las hay, envia un correo de NOTIFICACION RAPIDA
(solo texto, sin ningun PDF adjunto) con los detalles que el
sistema logra extraer automaticamente de cada convocatoria.

Este correo es independiente del Informe del Mercado de Gas
(Reportes/generar_informe_gas.py) y del Resumen Ejecutivo Quincenal:
avisa UNICAMENTE cuando Ecopetrol publica algo nuevo, sin graficos
ni tendencias, para que sea una alerta rapida de "revisa esto".
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
    Arma el texto del correo con el detalle de cada convocatoria
    nueva, usando unicamente los campos que el sistema logra
    extraer automaticamente de la pagina de Ecopetrol (Fuente,
    Cantidad, Modalidad, Plazo, Garantia, Fecha de publicacion).
    """
    partes = ["Hey, salio " + str(len(convocatorias)) + " nueva(s) convocatoria(s) de gas natural en Ecopetrol. Ve a revisar:\n"]
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
    Revisa si hay convocatorias nuevas y, si las hay, envia el
    correo de notificacion rapida (sin adjunto) correspondiente.
    Retorna:
        La cantidad de convocatorias nuevas encontradas.
    """
    nuevas = buscar_convocatorias_nuevas()
    if len(nuevas) == 0:
        print("No hay convocatorias nuevas de Ecopetrol.")
        return 0
    print("Se encontraron " + str(len(nuevas)) + " convocatoria(s) nueva(s). Enviando alerta...")
    cuerpo = _construir_cuerpo_del_correo(nuevas)
    enviar_informe_por_correo(
        None,
        "Nueva(s) convocatoria(s) de Gas Natural - Ecopetrol",
        cuerpo
    )
    return len(nuevas)
if __name__ == "__main__":
    revisar_y_enviar_alerta_ecopetrol()
