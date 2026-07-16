"""
Modulo: generar_informe_ejecutivo.py
Ubicacion: Reportes/generar_informe_ejecutivo.py

Genera el Resumen Ejecutivo Quincenal en PDF (Modulo 6 de la
especificacion original), que junta en un solo documento: Precio de
Bolsa, Precio de Escasez, Embalses, Aportes, Generacion por Fuente,
Alertas y una conclusion automatica.

Todas las graficas de este informe muestran una ventana de 12 MESES
MOVILES (eje X mes a mes): desde ayer (dia n-1, ultimo dia con datos
publicados) hacia atras 365 dias. Esta ventana se recalcula
automaticamente cada vez que se genera el informe.

Diseno compacto en 2 PAGINAS: sin tarjeta KPI de "Alertas Activas"
(se quito, aunque la seccion de detalle de alertas se conserva mas
abajo si hay alguna), sin seccion de noticias, y con la Conclusion
ubicada antes de Alertas. Todo el texto del documento (incluyendo
titulos) usa tamano de fuente uniforme de 12pt. Margenes reducidos
(1.2cm en los 4 lados) para que las graficas quepan bien en 2
paginas.

Este informe se envia cada 15 dias (no diario ni semanal).

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
    SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak, KeepTogether
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

TAMANO_FUENTE_BASE = 12
ANCHO_TARJETA = 5.5 * cm

MARGEN = 1.2 * cm
ANCHO_CONTENIDO = 21.59 * cm - (MARGEN * 2)

MESES_EN_ESPANOL_LARGO = {
    1: "enero", 2: "febrero", 3: "marzo", 4: "abril",
    5: "mayo", 6: "junio", 7: "julio", 8: "agosto",
    9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre",
}


def _crear_tarjeta_kpi(titulo, valor, color_acento):
    estilo_titulo = ParagraphStyle(
        "TituloTarjetaE", fontSize=TAMANO_FUENTE_BASE, textColor=COLOR_TEXTO,
        alignment=TA_CENTER, spaceAfter=3, fontName="Helvetica-Bold", leading=14
    )
    estilo_valor = ParagraphStyle(
        "ValorTarjetaE", fontSize=TAMANO_FUENTE_BASE, textColor=color_acento,
        alignment=TA_CENTER, fontName="Helvetica-Bold"
    )

    franja_acento = Table([[""]], colWidths=[ANCHO_TARJETA], rowHeights=[0.2 * cm])
    franja_acento.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), color_acento)]))

    contenido = [[franja_acento], [Paragraph(titulo, estilo_titulo)], [Paragraph(valor, estilo_valor)]]

    tabla = Table(contenido, colWidths=[ANCHO_TARJETA], rowHeights=[0.2 * cm, 1.0 * cm, 0.9 * cm])
    tabla.setStyle(TableStyle([
        ("SPAN", (0, 0), (0, 0)),
        ("BACKGROUND", (0, 1), (-1, -1), COLOR_FONDO_TARJETA),
        ("BOX", (0, 0), (-1, -1), 0.75, COLOR_BORDE),
        ("TOPPADDING", (0, 1), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 4),
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
        topMargin=MARGEN, bottomMargin=MARGEN, leftMargin=MARGEN, rightMargin=MARGEN
    )

    estilos = getSampleStyleSheet()

    estilo_titulo_principal = ParagraphStyle(
        "TituloPrincipalE", parent=estilos["Title"], textColor=COLOR_TEXTO,
        fontSize=TAMANO_FUENTE_BASE, spaceAfter=3, fontName="Helvetica-Bold"
    )
    estilo_subtitulo = ParagraphStyle(
        "SubtituloE", parent=estilos["Normal"], textColor=COLOR_TEXTO,
        fontSize=TAMANO_FUENTE_BASE, spaceAfter=8, fontName="Helvetica"
    )
    estilo_seccion = ParagraphStyle(
        "SeccionE", parent=estilos["Heading2"], textColor=COLOR_TEXTO,
        fontSize=TAMANO_FUENTE_BASE, spaceBefore=6, spaceAfter=3, fontName="Helvetica-Bold"
    )
    estilo_cuerpo = ParagraphStyle(
        "CuerpoE", parent=estilos["Normal"], fontSize=TAMANO_FUENTE_BASE, leading=15,
        textColor=COLOR_TEXTO, fontName="Helvetica"
    )
    estilo_conclusion = ParagraphStyle(
        "ConclusionE", parent=estilos["Normal"], fontSize=TAMANO_FUENTE_BASE, leading=15,
        textColor=COLOR_TEXTO, fontName="Helvetica"
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

    fila_tarjetas = Table([[tarjeta_precio, tarjeta_escasez, tarjeta_embalses]], colWidths=[5.9 * cm] * 3)
    fila_tarjetas.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    elementos.append(fila_tarjetas)
    elementos.append(Spacer(1, 6))

    # ---------- Precio de Bolsa y Precio de Escasez ----------
    seccion_precio = [Paragraph("Precio de Bolsa y Precio de Escasez - Últimos 12 Meses", estilo_seccion)]
    if ruta_grafico_precio is not None and os.path.exists(ruta_grafico_precio):
        seccion_precio.append(Image(ruta_grafico_precio, width=ANCHO_CONTENIDO, height=ANCHO_CONTENIDO * (4.2 / 11)))
    elementos.append(KeepTogether(seccion_precio))

    elementos.append(Spacer(1, 4))

    # ---------- Embalses ----------
    seccion_embalses = [Paragraph("Embalses - Últimos 12 Meses", estilo_seccion)]
    if ruta_grafico_embalses is not None and os.path.exists(ruta_grafico_embalses):
        seccion_embalses.append(Image(ruta_grafico_embalses, width=ANCHO_CONTENIDO, height=ANCHO_CONTENIDO * (4.2 / 11)))
    elementos.append(KeepTogether(seccion_embalses))

    # ======================= PAGINA 2 =======================
    elementos.append(PageBreak())

    # ---------- Aportes Hidricos ----------
    seccion_aportes = [Paragraph("Aportes Hídricos - Últimos 12 Meses", estilo_seccion)]
    if ruta_grafico_aportes is not None and os.path.exists(ruta_grafico_aportes):
        seccion_aportes.append(Image(ruta_grafico_aportes, width=ANCHO_CONTENIDO, height=ANCHO_CONTENIDO * (4.2 / 11)))
    elementos.append(KeepTogether(seccion_aportes))

    elementos.append(Spacer(1, 4))

    # ---------- Generacion por Fuente ----------
    seccion_generacion = [Paragraph("Generación por Fuente - Últimos 12 Meses", estilo_seccion)]
    if ruta_grafico_generacion is not None and os.path.exists(ruta_grafico_generacion):
        seccion_generacion.append(Image(ruta_grafico_generacion, width=ANCHO_CONTENIDO, height=ANCHO_CONTENIDO * (4.2 / 11)))
    elementos.append(KeepTogether(seccion_generacion))

    elementos.append(Spacer(1, 6))

    # ---------- Conclusion (antes de Alertas) ----------
    seccion_conclusion = [Paragraph("Conclusión", estilo_seccion), Paragraph(resumen["conclusion"], estilo_conclusion)]
    elementos.append(KeepTogether(seccion_conclusion))

    # ---------- Alertas Activas (detalle, si hay) ----------
    if len(resumen["alertas"]) > 0:
        elementos.append(Spacer(1, 6))
        seccion_alertas = [Paragraph("Alertas Activas", estilo_seccion)]
        for alerta in resumen["alertas"]:
            seccion_alertas.append(Paragraph("- " + alerta["mensaje"], estilo_cuerpo))
        elementos.append(KeepTogether(seccion_alertas))

    documento.build(elementos)

    print("Resumen ejecutivo generado: " + ruta_pdf)
    return ruta_pdf


if __name__ == "__main__":
    generar_informe_ejecutivo()
