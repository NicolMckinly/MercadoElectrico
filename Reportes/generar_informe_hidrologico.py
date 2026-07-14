"""
Modulo: generar_informe_hidrologico.py
Ubicacion: Reportes/generar_informe_hidrologico.py

Genera el informe de Variables Hidrologicas en PDF (Modulo 3 de la
especificacion del proyecto): resumen ejecutivo con los indicadores
principales, comentario automatico, los graficos de embalses y
aportes, el grafico de Generacion por Fuente, el grafico de
Evolucion del Precio de Bolsa (mes vigente, despues de Generacion
por Fuente), y las noticias relacionadas.

Este informe se envia unicamente los MARTES y JUEVES, segun la
especificacion original del proyecto.

Todo el texto del documento usa tamano de fuente uniforme de 12pt,
incluyendo titulos y encabezados de seccion. Margenes reducidos
(1.2cm en los 4 lados) y tarjetas KPI mas angostas, para que la
Tendencia de Embalses y los Aportes Hidricos quepan en la misma
pagina que el resumen ejecutivo.

La fecha se calcula con ahora_colombia() (ver BaseDatos/zona_horaria.py)
en vez de datetime.now(), para que el nombre del archivo y la fecha
mostrada en el titulo siempre correspondan a la hora real de Colombia.

Todos los textos visibles del PDF llevan tildes y ortografia
correcta en espanol.
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

from estadisticas_hidrologia import calcular_estadisticas_hidrologia, generar_comentario_hidrologia
from grafico_hidrologia import generar_grafico_embalses, generar_grafico_aportes
from grafico_generacion import generar_grafico_generacion
from grafico_mensual import generar_grafico_mensual
from zona_horaria import ahora_colombia

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
ANCHO_TARJETA = 4.2 * cm

MARGEN = 1.2 * cm
ANCHO_CONTENIDO = 21.59 * cm - (MARGEN * 2)

MESES_EN_ESPANOL_LARGO = {
    1: "enero", 2: "febrero", 3: "marzo", 4: "abril",
    5: "mayo", 6: "junio", 7: "julio", 8: "agosto",
    9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre",
}


def _crear_tarjeta_kpi(titulo, valor, color_acento):
    """
    Crea una tarjeta KPI compacta (fuente uniforme de 12pt), con una
    franja de color en la parte superior a modo de acento visual.
    """
    estilo_titulo = ParagraphStyle(
        "TituloTarjetaH", fontSize=TAMANO_FUENTE_BASE, textColor=COLOR_TEXTO,
        alignment=TA_CENTER, spaceAfter=3, fontName="Helvetica-Bold",
        leading=14
    )
    estilo_valor = ParagraphStyle(
        "ValorTarjetaH", fontSize=TAMANO_FUENTE_BASE, textColor=color_acento,
        alignment=TA_CENTER, fontName="Helvetica-Bold"
    )

    franja_acento = Table([[""]], colWidths=[ANCHO_TARJETA], rowHeights=[0.2 * cm])
    franja_acento.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), color_acento),
    ]))

    contenido = [
        [franja_acento],
        [Paragraph(titulo, estilo_titulo)],
        [Paragraph(valor, estilo_valor)]
    ]

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
    ruta_grafico_precio_mensual = generar_grafico_mensual()

    hoy = ahora_colombia()
    nombre_archivo = "Informe_Hidrologico_" + hoy.strftime("%Y_%m_%d") + ".pdf"
    ruta_pdf = os.path.join(CARPETA_ACTUAL, nombre_archivo)

    documento = SimpleDocTemplate(
        ruta_pdf,
        pagesize=letter,
        topMargin=MARGEN,
        bottomMargin=MARGEN,
        leftMargin=MARGEN,
        rightMargin=MARGEN
    )

    estilos = getSampleStyleSheet()

    estilo_titulo_principal = ParagraphStyle(
        "TituloPrincipalH", parent=estilos["Title"],
        textColor=COLOR_TEXTO, fontSize=TAMANO_FUENTE_BASE, spaceAfter=3,
        fontName="Helvetica-Bold"
    )
    estilo_subtitulo = ParagraphStyle(
        "SubtituloH", parent=estilos["Normal"],
        textColor=COLOR_TEXTO, fontSize=TAMANO_FUENTE_BASE, spaceAfter=8,
        fontName="Helvetica"
    )
    estilo_seccion = ParagraphStyle(
        "SeccionH", parent=estilos["Heading2"],
        textColor=COLOR_TEXTO, fontSize=TAMANO_FUENTE_BASE, spaceBefore=8, spaceAfter=4,
        fontName="Helvetica-Bold"
    )
    estilo_cuerpo = ParagraphStyle(
        "CuerpoH", parent=estilos["Normal"],
        fontSize=TAMANO_FUENTE_BASE, leading=15, textColor=COLOR_TEXTO,
        fontName="Helvetica"
    )

    elementos = []

    elementos.append(Paragraph("Informe de Variables Hidrológicas", estilo_titulo_principal))

    fecha_en_espanol = hoy.strftime("%d") + " de " + MESES_EN_ESPANOL_LARGO[hoy.month] + " de " + str(hoy.year)
    elementos.append(Paragraph(fecha_en_espanol, estilo_subtitulo))

    tarjeta_embalses = _crear_tarjeta_kpi(
        "Embalses",
        "{:.1f}".format(estadisticas["embalses_porcentaje_actual"] * 100) + "%",
        COLOR_ACENTO_EMBALSES
    )

    if estadisticas["embalses_variacion_diaria_puntos"] is not None:
        texto_variacion = "{:+.2f}".format(estadisticas["embalses_variacion_diaria_puntos"] * 100) + " pp"
    else:
        texto_variacion = "N/D"
    tarjeta_variacion_embalses = _crear_tarjeta_kpi("Variación Diaria Embalses", texto_variacion, COLOR_ACENTO_VARIACION)

    tarjeta_aportes = _crear_tarjeta_kpi(
        "Aportes SIN",
        "{:.1f}".format(estadisticas["aportes_porcentaje_actual"] * 100) + "%",
        COLOR_ACENTO_APORTES
    )

    fila_tarjetas = Table(
        [[tarjeta_embalses, tarjeta_variacion_embalses, tarjeta_aportes]],
        colWidths=[4.4 * cm] * 3
    )
    fila_tarjetas.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    elementos.append(fila_tarjetas)
    elementos.append(Spacer(1, 8))

    elementos.append(Paragraph("Resumen del Comportamiento Hidrológico", estilo_seccion))
    elementos.append(Paragraph(comentario, estilo_cuerpo))
    elementos.append(Spacer(1, 4))

    # ---------- Tendencia de Embalses ----------
    seccion_embalses = [Paragraph("Tendencia de Embalses", estilo_seccion)]
    if ruta_grafico_embalses is not None and os.path.exists(ruta_grafico_embalses):
        seccion_embalses.append(Image(ruta_grafico_embalses, width=ANCHO_CONTENIDO, height=ANCHO_CONTENIDO * (4.2 / 11)))
    else:
        seccion_embalses.append(Paragraph("Gráfico no disponible.", estilo_cuerpo))
    elementos.append(KeepTogether(seccion_embalses))

    elementos.append(Spacer(1, 4))

    # ---------- Aportes Hidricos SIN vs Media Historica ----------
    seccion_aportes = [Paragraph("Aportes Hídricos SIN vs Media Histórica", estilo_seccion)]
    if ruta_grafico_aportes is not None and os.path.exists(ruta_grafico_aportes):
        seccion_aportes.append(Image(ruta_grafico_aportes, width=ANCHO_CONTENIDO, height=ANCHO_CONTENIDO * (4.2 / 11)))
    else:
        seccion_aportes.append(Paragraph("Gráfico no disponible.", estilo_cuerpo))
    elementos.append(KeepTogether(seccion_aportes))

    # ======================= PAGINA 2 =======================
    elementos.append(PageBreak())

    # ---------- Generacion por Fuente ----------
    seccion_generacion = [Paragraph("Generación por Fuente", estilo_seccion)]
    if ruta_grafico_generacion is not None and os.path.exists(ruta_grafico_generacion):
        seccion_generacion.append(Image(ruta_grafico_generacion, width=ANCHO_CONTENIDO, height=ANCHO_CONTENIDO * (4.6 / 11)))
    else:
        seccion_generacion.append(Paragraph("Gráfico no disponible.", estilo_cuerpo))
    elementos.append(KeepTogether(seccion_generacion))

    elementos.append(Spacer(1, 4))

    # ---------- Evolucion del Precio - Mes Vigente ----------
    seccion_precio = [Paragraph("Evolución del Precio - Mes Vigente", estilo_seccion)]
    if ruta_grafico_precio_mensual is not None and os.path.exists(ruta_grafico_precio_mensual):
        seccion_precio.append(Image(ruta_grafico_precio_mensual, width=ANCHO_CONTENIDO, height=ANCHO_CONTENIDO * (4.2 / 11)))
    else:
        seccion_precio.append(Paragraph("Gráfico no disponible.", estilo_cuerpo))
    elementos.append(KeepTogether(seccion_precio))

    # ---------- Noticias (Modulo 5) ----------
    elementos.append(Spacer(1, 6))
    elementos.append(Paragraph("Noticias Relacionadas (últimos 7 días)", estilo_seccion))

    recopilar_noticias()
    noticias = consultar_noticias_recientes(dias=7)

estilo_item_noticia = ParagraphStyle(
        "ItemNoticia", parent=estilos["Normal"],
        fontSize=TAMANO_FUENTE_BASE, leading=15, textColor=COLOR_TEXTO,
        fontName="Helvetica", spaceAfter=5
    )

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

    print("Informe hidrológico generado: " + ruta_pdf)
    return ruta_pdf


if __name__ == "__main__":
    generar_informe_hidrologico()
