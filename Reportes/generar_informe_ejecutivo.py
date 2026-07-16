"""
Modulo: generar_informe_ejecutivo.py
Ubicacion: Reportes/generar_informe_ejecutivo.py

Genera el Resumen Ejecutivo Quincenal en PDF (Modulo 6 de la
especificacion original), que junta en un solo documento: Precio de
Bolsa, Precio de Escasez, Embalses, Aportes, Generacion por Fuente,
Noticias y Alertas, terminando con una conclusion automatica.

Todas las graficas de este informe muestran una ventana de 12 MESES
MOVILES: desde ayer (dia n-1, ultimo dia con datos publicados) hacia
atras 365 dias. Esta ventana se recalcula automaticamente cada vez
que se genera el informe, asi que avanza sola dia a dia y mes a mes,
sin necesidad de ajustar nada manualmente.

Este informe se envia cada 15 dias (no diario ni semanal), segun lo
pedido por el usuario.

La fecha se calcula con ahora_colombia() (ver BaseDatos/zona_horaria.py)
en vez de datetime.now(), para que el nombre del archivo y la fecha
mostrada en el titulo siempre correspondan a la hora real de Colombia.
"""

import sys
import os

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER

CARPETA_PROYECTO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(CARPETA_PROYECTO, "Analisis"))
sys.path.append(os.path.join(CARPETA_PROYECTO, "Graficas"))
sys.path.append(os.path.join(CARPETA_PROYECTO, "BaseDatos"))

from resumen_ejecutivo import generar_resumen_ejecutivo
from grafico_precio_anual_ejecutivo import generar_grafico_precio_anual_ejecutivo
from grafico_hidrologia import generar_grafico_embalses_anual_ejecutivo, generar_grafico_aportes_anual_ejecutivo
from grafico_generacion import generar_grafico_generacion_anual_ejecutivo
from zona_horaria import ahora_colombia

CARPETA_ACTUAL = os.path.dirname(os.path.abspath(__file__))

COLOR_TEXTO = colors.black
COLOR_FONDO_TARJETA = colors.HexColor("#F7F7F7")
COLOR_BORDE = colors.HexColor("#DDDDDD")

COLOR_ACENTO_PRECIO = colors.HexColor("#1F4E79")
COLOR_ACENTO_ESCASEZ = colors.HexColor("#B22222")
COLOR_ACENTO_EMBALSES = colors.HexColor("#1F6F50")
COLOR_ACENTO_ALERTAS = colors.HexColor("#D9822B")

ANCHO_TARJETA = 4.3 * cm

MESES_EN_ESPANOL_LARGO = {
    1: "enero", 2: "febrero", 3: "marzo", 4: "abril",
    5: "mayo", 6: "junio", 7: "julio", 8: "agosto",
    9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre",
}


def _crear_tarjeta_kpi(titulo, valor, color_acento):
    estilo_titulo = ParagraphStyle(
        "TituloTarjetaE", fontSize=9, textColor=COLOR_TEXTO,
        alignment=TA_CENTER, spaceAfter=4, fontName="Helvetica-Bold", leading=12
    )
    estilo_valor = ParagraphStyle(
        "ValorTarjetaE", fontSize=14, textColor=color_acento,
        alignment=TA_CENTER, fontName="Helvetica-Bold"
    )

    franja_acento = Table([[""]], colWidths=[ANCHO_TARJETA], rowHeights=[0.22 * cm])
    franja_acento.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), color_acento)]))

    contenido = [[franja_acento], [Paragraph(titulo, estilo_titulo)], [Paragraph(valor, estilo_valor)]]

    tabla = Table(contenido, colWidths=[ANCHO_TARJETA], rowHeights=[0.22 * cm, 1.2 * cm, 1.1 * cm])
    tabla.setStyle(TableStyle([
        ("SPAN", (0, 0), (0, 0)),
        ("BACKGROUND", (0, 1), (-1, -1), COLOR_FONDO_TARJETA),
        ("BOX", (0, 0), (-1, -1), 0.75, COLOR_BORDE),
        ("TOPPADDING", (0, 1), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return tabla


def generar_informe_ejecutivo():
    """
    Genera el Resumen Ejecutivo Quincenal en PDF.

    Retorna:
        La ruta del archivo PDF generado, o None si no hay datos suficientes.
    """
    resumen = generar_resumen_ejecutivo()

    if resumen is None:
        print("No hay datos suficientes para generar el resumen ejecutivo.")
        return None

    ruta_grafico_precio = generar_grafico_precio_anual_ejecutivo()
    ruta_grafico_embalses = generar_grafico_embalses_anual_ejecutivo()
    ruta_grafico_aportes = generar_grafico_aportes_anual_ejecutivo()
    ruta_grafico_generacion = generar_grafico_generacion_anual_ejecutivo()

    hoy = ahora_colombia()
    nombre_archivo = "Resumen_Ejecutivo_" + hoy.strftime("%Y_%m_%d") + ".pdf"
    ruta_pdf = os.path.join(CARPETA_ACTUAL, nombre_archivo)

    documento = SimpleDocTemplate(
        ruta_pdf, pagesize=letter,
        topMargin=1.5 * cm, bottomMargin=1.5 * cm, leftMargin=1.5 * cm, rightMargin=1.5 * cm
    )

    estilos = getSampleStyleSheet()

    estilo_titulo_principal = ParagraphStyle(
        "TituloPrincipalE", parent=estilos["Title"], textColor=COLOR_TEXTO,
        fontSize=20, spaceAfter=4, fontName="Helvetica-Bold"
    )
    estilo_subtitulo = ParagraphStyle(
        "SubtituloE", parent=estilos["Normal"], textColor=COLOR_TEXTO,
        fontSize=12, spaceAfter=16, fontName="Helvetica"
    )
    estilo_seccion = ParagraphStyle(
        "SeccionE", parent=estilos["Heading2"], textColor=COLOR_TEXTO,
        fontSize=14, spaceBefore=18, spaceAfter=8, fontName="Helvetica-Bold"
    )
    estilo_cuerpo = ParagraphStyle(
        "CuerpoE", parent=estilos["Normal"], fontSize=12, leading=16,
        textColor=COLOR_TEXTO, fontName="Helvetica"
    )
    estilo_conclusion = ParagraphStyle(
        "ConclusionE", parent=estilos["Normal"], fontSize=12, leading=17,
        textColor=COLOR_TEXTO, fontName="Helvetica"
    )
    estilo_item = ParagraphStyle(
        "ItemE", parent=estilos["Normal"], fontSize=10, leading=14,
        textColor=COLOR_TEXTO, fontName="Helvetica", spaceAfter=6
    )

    elementos = []

    elementos.append(Paragraph("Resumen Ejecutivo Quincenal", estilo_titulo_principal))
    fecha_en_espanol = hoy.strftime("%d") + " de " + MESES_EN_ESPANOL_LARGO[hoy.month] + " de " + str(hoy.year)
    elementos.append(Paragraph("Mercado Eléctrico Colombiano - " + fecha_en_espanol, estilo_subtitulo))

    ep = resumen["estadisticas_precio"]
    eh = resumen["estadisticas_hidro"]

    tarjeta_precio = _crear_tarjeta_kpi("Precio Bolsa Actual", "{:.0f}".format(ep["precio_dia_mas_reciente"]) + " $/kWh", COLOR_ACENTO_PRECIO)
    tarjeta_escasez = _crear_tarjeta_kpi(
        "Precio de Escasez",
        "{:.0f}".format(resumen["valor_escasez"]) + " $/kWh" if resumen["valor_escasez"] is not None else "N/D",
        COLOR_ACENTO_ESCASEZ
    )
    tarjeta_embalses = _crear_tarjeta_kpi(
        "Embalses",
        "{:.1f}".format(eh["embalses_porcentaje_actual"] * 100) + "%" if eh is not None else "N/D",
        COLOR_ACENTO_EMBALSES
    )
    tarjeta_alertas = _crear_tarjeta_kpi("Alertas Activas", str(len(resumen["alertas"])), COLOR_ACENTO_ALERTAS)

    fila_tarjetas = Table([[tarjeta_precio, tarjeta_escasez, tarjeta_embalses, tarjeta_alertas]], colWidths=[4.4 * cm] * 4)
    fila_tarjetas.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    elementos.append(fila_tarjetas)
    elementos.append(Spacer(1, 16))

    elementos.append(Paragraph("Precio de Bolsa y Precio de Escasez - Últimos 12 Meses", estilo_seccion))
    if ruta_grafico_precio is not None and os.path.exists(ruta_grafico_precio):
        elementos.append(Image(ruta_grafico_precio, width=17 * cm, height=17 * cm * (5.5 / 11)))

    elementos.append(PageBreak())

    elementos.append(Paragraph("Embalses - Últimos 12 Meses", estilo_seccion))
    if ruta_grafico_embalses is not None and os.path.exists(ruta_grafico_embalses):
        elementos.append(Image(ruta_grafico_embalses, width=17 * cm, height=17 * cm * (5 / 11)))

    elementos.append(Spacer(1, 10))
    elementos.append(Paragraph("Aportes Hídricos - Últimos 12 Meses", estilo_seccion))
    if ruta_grafico_aportes is not None and os.path.exists(ruta_grafico_aportes):
        elementos.append(Image(ruta_grafico_aportes, width=17 * cm, height=17 * cm * (5 / 11)))

    elementos.append(PageBreak())

    elementos.append(Paragraph("Generación por Fuente - Últimos 12 Meses", estilo_seccion))
    if ruta_grafico_generacion is not None and os.path.exists(ruta_grafico_generacion):
        elementos.append(Image(ruta_grafico_generacion, width=17 * cm, height=17 * cm * (5.5 / 11)))

    if len(resumen["noticias"]) > 0:
        elementos.append(Spacer(1, 10))
        elementos.append(Paragraph("Noticias Relacionadas (últimos 15 días)", estilo_seccion))

        for _, noticia in resumen["noticias"].head(8).iterrows():
            texto_item = (
                "<b>[" + noticia["fecha_publicacion"] + "]</b> " + noticia["titulo"]
                + " (" + noticia["fuente"] + ") - "
                + "<link href='" + noticia["enlace"] + "' color='blue'>Ver noticia</link>"
            )
            elementos.append(Paragraph(texto_item, estilo_item))

    if len(resumen["alertas"]) > 0:
        elementos.append(Spacer(1, 10))
        elementos.append(Paragraph("Alertas Activas", estilo_seccion))

        for alerta in resumen["alertas"]:
            elementos.append(Paragraph("- " + alerta["mensaje"], estilo_cuerpo))

    elementos.append(Spacer(1, 14))
    elementos.append(Paragraph("Conclusión", estilo_seccion))
    elementos.append(Paragraph(resumen["conclusion"], estilo_conclusion))

    documento.build(elementos)

    print("Resumen ejecutivo generado: " + ruta_pdf)
    return ruta_pdf


if __name__ == "__main__":
    generar_informe_ejecutivo()
