"""
Modulo: generar_informe_hidrologico.py
Ubicacion: Reportes/generar_informe_hidrologico.py

Genera el informe de Variables Hidrologicas en PDF (Modulo 3 de la
especificacion del proyecto): resumen ejecutivo con los indicadores
principales, comentario automatico, y los graficos de embalses y
aportes hidricos.

Este informe se envia unicamente los MARTES y JUEVES, segun la
especificacion original del proyecto.

Diseno: mismo estilo que el informe diario (Helvetica, tamano 12,
titulos en negrita, todo en negro), con tarjetas KPI de tamano
uniforme y un acento de color en la parte superior de cada una.
"""

import sys
import os
from datetime import datetime

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER

CARPETA_PROYECTO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(CARPETA_PROYECTO, "Analisis"))
sys.path.append(os.path.join(CARPETA_PROYECTO, "Graficas"))

from estadisticas_hidrologia import calcular_estadisticas_hidrologia, generar_comentario_hidrologia
from grafico_hidrologia import generar_grafico_embalses, generar_grafico_aportes
from grafico_generacion import generar_grafico_generacion

sys.path.append(os.path.join(CARPETA_PROYECTO, "API"))
from noticias import recopilar_noticias
from base_datos import consultar_noticias_recientes

CARPETA_ACTUAL = os.path.dirname(os.path.abspath(__file__))

COLOR_TEXTO = colors.black
COLOR_FONDO_ENCABEZADO_TABLA = colors.HexColor("#333333")
COLOR_FONDO_TARJETA = colors.HexColor("#F7F7F7")
COLOR_BORDE = colors.HexColor("#DDDDDD")

COLOR_ACENTO_EMBALSES = colors.HexColor("#1F6F50")
COLOR_ACENTO_VARIACION = colors.HexColor("#1F4E79")
COLOR_ACENTO_APORTES = colors.HexColor("#D9822B")

TAMANO_FUENTE_BASE = 12
ANCHO_TARJETA = 5.4 * cm


def _crear_tarjeta_kpi(titulo, valor, color_acento):
    """
    Crea una tarjeta KPI con tamano y tipografia uniformes, y una
    franja de color en la parte superior a modo de acento visual.
    """
    estilo_titulo = ParagraphStyle(
        "TituloTarjetaH", fontSize=10, textColor=COLOR_TEXTO,
        alignment=TA_CENTER, spaceAfter=4, fontName="Helvetica-Bold",
        leading=13
    )
    estilo_valor = ParagraphStyle(
        "ValorTarjetaH", fontSize=18, textColor=color_acento,
        alignment=TA_CENTER, fontName="Helvetica-Bold"
    )

    franja_acento = Table([[""]], colWidths=[ANCHO_TARJETA], rowHeights=[0.25 * cm])
    franja_acento.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), color_acento),
    ]))

    contenido = [
        [franja_acento],
        [Paragraph(titulo, estilo_titulo)],
        [Paragraph(valor, estilo_valor)]
    ]

    tabla = Table(contenido, colWidths=[ANCHO_TARJETA], rowHeights=[0.25 * cm, 1.3 * cm, 1.4 * cm])
    tabla.setStyle(TableStyle([
        ("SPAN", (0, 0), (0, 0)),
        ("BACKGROUND", (0, 1), (-1, -1), COLOR_FONDO_TARJETA),
        ("BOX", (0, 0), (-1, -1), 0.75, COLOR_BORDE),
        ("TOPPADDING", (0, 1), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))

    return tabla


def generar_informe_hidrologico():
    """
    Genera el informe de Variables Hidrologicas en PDF.

    Retorna:
        La ruta del archivo PDF generado, o None si no hay datos suficientes.
    """
    estadisticas = calcular_estadisticas_hidrologia()

    if estadisticas is None:
        print("No hay datos hidrologicos suficientes para generar el informe.")
        return None

    comentario = generar_comentario_hidrologia(estadisticas)
    ruta_grafico_embalses = generar_grafico_embalses()
    ruta_grafico_aportes = generar_grafico_aportes()
    ruta_grafico_generacion = generar_grafico_generacion()

    hoy = datetime.now()
    nombre_archivo = "Informe_Hidrologico_" + hoy.strftime("%Y_%m_%d") + ".pdf"
    ruta_pdf = os.path.join(CARPETA_ACTUAL, nombre_archivo)

    documento = SimpleDocTemplate(
        ruta_pdf,
        pagesize=letter,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm
    )

    estilos = getSampleStyleSheet()

    estilo_titulo_principal = ParagraphStyle(
        "TituloPrincipalH", parent=estilos["Title"],
        textColor=COLOR_TEXTO, fontSize=20, spaceAfter=4,
        fontName="Helvetica-Bold"
    )
    estilo_subtitulo = ParagraphStyle(
        "SubtituloH", parent=estilos["Normal"],
        textColor=COLOR_TEXTO, fontSize=TAMANO_FUENTE_BASE, spaceAfter=16,
        fontName="Helvetica"
    )
    estilo_seccion = ParagraphStyle(
        "SeccionH", parent=estilos["Heading2"],
        textColor=COLOR_TEXTO, fontSize=14, spaceBefore=18, spaceAfter=8,
        fontName="Helvetica-Bold"
    )
    estilo_cuerpo = ParagraphStyle(
        "CuerpoH", parent=estilos["Normal"],
        fontSize=TAMANO_FUENTE_BASE, leading=16, textColor=COLOR_TEXTO,
        fontName="Helvetica"
    )

    elementos = []

    elementos.append(Paragraph("Informe de Variables Hidrologicas", estilo_titulo_principal))
    elementos.append(Paragraph(hoy.strftime("%d de %B de %Y"), estilo_subtitulo))

    tarjeta_embalses = _crear_tarjeta_kpi(
        "Embalses",
        "{:.1f}".format(estadisticas["embalses_porcentaje_actual"] * 100) + "%",
        COLOR_ACENTO_EMBALSES
    )

    if estadisticas["embalses_variacion_diaria_puntos"] is not None:
        texto_variacion = "{:+.2f}".format(estadisticas["embalses_variacion_diaria_puntos"] * 100) + " pp"
    else:
        texto_variacion = "N/D"
    tarjeta_variacion_embalses = _crear_tarjeta_kpi("Variacion Diaria Embalses", texto_variacion, COLOR_ACENTO_VARIACION)

    tarjeta_aportes = _crear_tarjeta_kpi(
        "Aportes SIN",
        "{:.1f}".format(estadisticas["aportes_porcentaje_actual"] * 100) + "%",
        COLOR_ACENTO_APORTES
    )

    fila_tarjetas = Table(
        [[tarjeta_embalses, tarjeta_variacion_embalses, tarjeta_aportes]],
        colWidths=[5.7 * cm] * 3
    )
    fila_tarjetas.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    elementos.append(fila_tarjetas)
    elementos.append(Spacer(1, 18))

    elementos.append(Paragraph("Resumen del Comportamiento Hidrologico", estilo_seccion))
    elementos.append(Paragraph(comentario, estilo_cuerpo))
    elementos.append(Spacer(1, 10))

    elementos.append(Paragraph("Tendencia de Embalses", estilo_seccion))
    if ruta_grafico_embalses is not None and os.path.exists(ruta_grafico_embalses):
        elementos.append(Image(ruta_grafico_embalses, width=17 * cm, height=17 * cm * (5 / 11)))
    else:
        elementos.append(Paragraph("Grafico no disponible.", estilo_cuerpo))

    elementos.append(Spacer(1, 10))

    elementos.append(Paragraph("Aportes Hidricos SIN vs Media Historica", estilo_seccion))
    if ruta_grafico_aportes is not None and os.path.exists(ruta_grafico_aportes):
        elementos.append(Image(ruta_grafico_aportes, width=17 * cm, height=17 * cm * (5 / 11)))
    else:
        elementos.append(Paragraph("Grafico no disponible.", estilo_cuerpo))

    elementos.append(Spacer(1, 10))

    elementos.append(Paragraph("Generacion por Fuente", estilo_seccion))
    if ruta_grafico_generacion is not None and os.path.exists(ruta_grafico_generacion):
        elementos.append(Image(ruta_grafico_generacion, width=17 * cm, height=17 * cm * (5.5 / 11)))
    else:
        elementos.append(Paragraph("Grafico no disponible.", estilo_cuerpo))

    # ---------- Noticias (Modulo 5) ----------
    elementos.append(Spacer(1, 10))
    elementos.append(Paragraph("Noticias Relacionadas (ultimos 7 dias)", estilo_seccion))

    recopilar_noticias()
    noticias = consultar_noticias_recientes(dias=7)

    estilo_nota_noticias = ParagraphStyle(
        "NotaNoticias", parent=estilos["Normal"],
        fontSize=9, leading=12, textColor=COLOR_TEXTO,
        fontName="Helvetica-Oblique", spaceAfter=8
    )
    estilo_item_noticia = ParagraphStyle(
        "ItemNoticia", parent=estilos["Normal"],
        fontSize=10, leading=14, textColor=COLOR_TEXTO,
        fontName="Helvetica", spaceAfter=6
    )

    elementos.append(Paragraph(
        "Los siguientes son titulares recientes recopilados automaticamente de fuentes publicas, "
        "sin ninguna interpretacion generada por el sistema. Para el analisis completo de cada "
        "noticia, consulte el enlace original.",
        estilo_nota_noticias
    ))

    if len(noticias) == 0:
        elementos.append(Paragraph("No se encontraron noticias recientes relacionadas.", estilo_cuerpo))
    else:
        for _, noticia in noticias.head(10).iterrows():
            texto_item = (
                "<b>[" + noticia["fecha_publicacion"] + "]</b> "
                + noticia["titulo"] + " (" + noticia["fuente"] + ") - "
                + "<link href='" + noticia["enlace"] + "' color='blue'>Ver noticia</link>"
            )
            elementos.append(Paragraph(texto_item, estilo_item_noticia))

    documento.build(elementos)

    print("Informe hidrologico generado: " + ruta_pdf)
    return ruta_pdf


if __name__ == "__main__":
    generar_informe_hidrologico()
