"""
Modulo: generar_informe_gas.py
Ubicacion: Reportes/generar_informe_gas.py

Genera el Informe del Mercado de Gas en PDF, con la tabla de
convocatorias/contratos detectados y el grafico de tendencia de
cantidades ofertadas (MBTUD).

Este informe se genera y envia especificamente cuando se detecta una
convocatoria NUEVA de Ecopetrol (ver Correos/enviar_alerta_ecopetrol.py),
no junto con el Resumen Ejecutivo Quincenal.

Usa ahora_colombia() (ver BaseDatos/zona_horaria.py) en vez de
datetime.now(), para que la fecha del nombre del archivo y del
subtitulo siempre correspondan a la hora real de Colombia.
"""

import sys
import os

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

CARPETA_PROYECTO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(CARPETA_PROYECTO, "Analisis"))
sys.path.append(os.path.join(CARPETA_PROYECTO, "Graficas"))
sys.path.append(os.path.join(CARPETA_PROYECTO, "BaseDatos"))

from estadisticas_gas import obtener_historico_gas
from grafico_gas import generar_grafico_gas
from zona_horaria import ahora_colombia

CARPETA_ACTUAL = os.path.dirname(os.path.abspath(__file__))

COLOR_TEXTO = colors.black
COLOR_FONDO_ENCABEZADO_TABLA = colors.HexColor("#333333")
COLOR_FONDO_TARJETA = colors.HexColor("#F7F7F7")
COLOR_BORDE = colors.HexColor("#DDDDDD")

MESES_EN_ESPANOL_LARGO = {
    1: "enero", 2: "febrero", 3: "marzo", 4: "abril",
    5: "mayo", 6: "junio", 7: "julio", 8: "agosto",
    9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre",
}


def generar_informe_gas():
    """
    Genera el Informe del Mercado de Gas en PDF.

    Retorna:
        La ruta del archivo PDF generado, o None si no hay datos.
    """
    historico = obtener_historico_gas()

    hoy = ahora_colombia()
    nombre_archivo = "Informe_Mercado_Gas_" + hoy.strftime("%Y_%m_%d") + ".pdf"
    ruta_pdf = os.path.join(CARPETA_ACTUAL, nombre_archivo)

    documento = SimpleDocTemplate(
        ruta_pdf, pagesize=letter,
        topMargin=1.5 * cm, bottomMargin=1.5 * cm, leftMargin=1.5 * cm, rightMargin=1.5 * cm
    )

    estilos = getSampleStyleSheet()

    estilo_titulo_principal = ParagraphStyle(
        "TituloPrincipalG", parent=estilos["Title"], textColor=COLOR_TEXTO,
        fontSize=20, spaceAfter=4, fontName="Helvetica-Bold"
    )
    estilo_subtitulo = ParagraphStyle(
        "SubtituloG", parent=estilos["Normal"], textColor=COLOR_TEXTO,
        fontSize=12, spaceAfter=16, fontName="Helvetica"
    )
    estilo_seccion = ParagraphStyle(
        "SeccionG", parent=estilos["Heading2"], textColor=COLOR_TEXTO,
        fontSize=14, spaceBefore=18, spaceAfter=8, fontName="Helvetica-Bold"
    )
    estilo_cuerpo = ParagraphStyle(
        "CuerpoG", parent=estilos["Normal"], fontSize=12, leading=16,
        textColor=COLOR_TEXTO, fontName="Helvetica"
    )
    estilo_celda = ParagraphStyle(
        "CeldaG", fontSize=8.5, textColor=COLOR_TEXTO, fontName="Helvetica", leading=11
    )
    estilo_celda_encabezado = ParagraphStyle(
        "CeldaEncabezadoG", fontSize=8.5, textColor=colors.white, fontName="Helvetica-Bold", leading=11
    )

    elementos = []

    elementos.append(Paragraph("Informe del Mercado de Gas Natural", estilo_titulo_principal))

    fecha_en_espanol = hoy.strftime("%d") + " de " + MESES_EN_ESPANOL_LARGO[hoy.month] + " de " + str(hoy.year)
    elementos.append(Paragraph("Convocatorias de Ecopetrol - " + fecha_en_espanol, estilo_subtitulo))

    elementos.append(Paragraph("Tendencia de Cantidades Ofertadas", estilo_seccion))
    ruta_grafico = generar_grafico_gas()
    if ruta_grafico is not None and os.path.exists(ruta_grafico):
        elementos.append(Image(ruta_grafico, width=17 * cm, height=17 * cm * (5 / 11)))
    else:
        elementos.append(Paragraph(
            "Aun no hay suficientes convocatorias con cantidad numerica identificada para graficar una tendencia.",
            estilo_cuerpo
        ))

    elementos.append(Spacer(1, 14))
    elementos.append(Paragraph("Convocatorias y Contratos Detectados", estilo_seccion))

    if len(historico) == 0:
        elementos.append(Paragraph("Aun no se ha detectado ninguna convocatoria.", estilo_cuerpo))
    else:
        datos_tabla = [[
            Paragraph("Convocatoria", estilo_celda_encabezado),
            Paragraph("Fuente", estilo_celda_encabezado),
            Paragraph("Cantidad", estilo_celda_encabezado),
            Paragraph("Modalidad", estilo_celda_encabezado),
            Paragraph("Plazo", estilo_celda_encabezado),
        ]]

        for _, fila in historico.iterrows():
            datos_tabla.append([
                Paragraph(fila["titulo"], estilo_celda),
                Paragraph(fila["fuente"], estilo_celda),
                Paragraph(fila["cantidad"], estilo_celda),
                Paragraph(fila["modalidad"], estilo_celda),
                Paragraph(fila["plazo"], estilo_celda),
            ])

        tabla = Table(datos_tabla, colWidths=[4.5 * cm, 3.5 * cm, 3 * cm, 3.5 * cm, 2.5 * cm], repeatRows=1)
        tabla.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), COLOR_FONDO_ENCABEZADO_TABLA),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, COLOR_FONDO_TARJETA]),
            ("GRID", (0, 0), (-1, -1), 0.5, COLOR_BORDE),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        elementos.append(tabla)

    elementos.append(Spacer(1, 10))
    elementos.append(Paragraph(
        "Nota: esta informacion se extrae automaticamente de las publicaciones de Ecopetrol. "
        "Los precios del mercado (BMC/iGas-D) y la disponibilidad declarada por campo (PTDVF) "
        "de Floreña, Cupiagua y Cusiana se incorporaran en una proxima version de este informe.",
        ParagraphStyle("NotaG", parent=estilos["Normal"], fontSize=9, textColor=COLOR_TEXTO, fontName="Helvetica-Oblique")
    ))

    documento.build(elementos)

    print("Informe de mercado de gas generado: " + ruta_pdf)
    return ruta_pdf


if __name__ == "__main__":
    generar_informe_gas()
