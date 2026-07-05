"""
Modulo: generar_informe_diario.py
Ubicacion: Reportes/generar_informe_diario.py

Genera el informe diario en PDF del Precio de Bolsa (Modulo 1, 6 y 8
de la especificacion del proyecto): pagina ejecutiva con indicadores,
comentario automatico, grafico mensual, grafico anual, tabla de
estadisticas, y tabla del IMAR del dia siguiente (crudo y ajustado,
con el periodo mas alto resaltado en verde y el mas bajo en amarillo).

Diseno: fuente Helvetica (la mas parecida disponible a Arial Nova
Cond, que no esta instalada en el equipo), tamano base 12, titulos en
negrita, todo el texto en color negro.

Este archivo NO descarga datos ni hace calculos. Su unica
responsabilidad es tomar los resultados de los otros modulos y
armar el documento PDF final.
"""

import sys
import os
from datetime import datetime

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

from estadisticas_precio import calcular_estadisticas, generar_comentario_automatico
from grafico_mensual import generar_grafico_mensual
from grafico_anual import generar_grafico_anual
from tabla_imar_siguiente_dia import obtener_tabla_imar_siguiente_dia
from base_datos import consultar_precio_escasez_mas_reciente

CARPETA_ACTUAL = os.path.dirname(os.path.abspath(__file__))

COLOR_TEXTO = colors.black
COLOR_FONDO_ENCABEZADO_TABLA = colors.HexColor("#333333")
COLOR_FONDO_TARJETA = colors.HexColor("#F2F2F2")
COLOR_BORDE = colors.HexColor("#CCCCCC")
COLOR_RESALTADO_ALTO = colors.HexColor("#B6D7A8")
COLOR_RESALTADO_BAJO = colors.HexColor("#FFE599")

TAMANO_FUENTE_BASE = 12


def _crear_tarjeta_kpi(titulo, valor):
    estilo_titulo = ParagraphStyle(
        "TituloTarjeta", fontSize=9, textColor=COLOR_TEXTO,
        alignment=TA_CENTER, spaceAfter=2, fontName="Helvetica-Bold"
    )
    estilo_valor = ParagraphStyle(
        "ValorTarjeta", fontSize=15, textColor=COLOR_TEXTO,
        alignment=TA_CENTER, fontName="Helvetica-Bold"
    )

    contenido = [
        [Paragraph(titulo, estilo_titulo)],
        [Paragraph(valor, estilo_valor)]
    ]

    tabla = Table(contenido, colWidths=[4.2 * cm])
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), COLOR_FONDO_TARJETA),
        ("BOX", (0, 0), (-1, -1), 0.5, COLOR_BORDE),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))

    return tabla


def generar_informe_diario():
    estadisticas = calcular_estadisticas()

    if estadisticas is None:
        print("No hay datos suficientes para generar el informe.")
        return None

    comentario = generar_comentario_automatico(estadisticas)
    ruta_grafico_mensual = generar_grafico_mensual()
    ruta_grafico_anual = generar_grafico_anual()
    tabla_imar = obtener_tabla_imar_siguiente_dia()
    _, valor_escasez = consultar_precio_escasez_mas_reciente()

    hoy = datetime.now()
    nombre_archivo = "Informe_Diario_PrecioBolsa_" + hoy.strftime("%Y_%m_%d") + ".pdf"
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
        "TituloPrincipal", parent=estilos["Title"],
        textColor=COLOR_TEXTO, fontSize=20, spaceAfter=4,
        fontName="Helvetica-Bold"
    )
    estilo_subtitulo = ParagraphStyle(
        "Subtitulo", parent=estilos["Normal"],
        textColor=COLOR_TEXTO, fontSize=TAMANO_FUENTE_BASE, spaceAfter=16,
        fontName="Helvetica"
    )
    estilo_seccion = ParagraphStyle(
        "Seccion", parent=estilos["Heading2"],
        textColor=COLOR_TEXTO, fontSize=14, spaceBefore=18, spaceAfter=8,
        fontName="Helvetica-Bold"
    )
    estilo_cuerpo = ParagraphStyle(
        "Cuerpo", parent=estilos["Normal"],
        fontSize=TAMANO_FUENTE_BASE, leading=16, textColor=COLOR_TEXTO,
        fontName="Helvetica"
    )
    estilo_nota = ParagraphStyle(
        "Nota", parent=estilos["Normal"],
        fontSize=9, leading=12, textColor=COLOR_TEXTO,
        fontName="Helvetica-Oblique"
    )

    elementos = []

    elementos.append(Paragraph("Informe Diario - Precio de Bolsa Nacional", estilo_titulo_principal))
    elementos.append(Paragraph(hoy.strftime("%d de %B de %Y"), estilo_subtitulo))

    tarjeta_precio = _crear_tarjeta_kpi(
        "Precio Bolsa Actual (" + estadisticas["fuente_dia_mas_reciente"] + ")",
        "{:.0f}".format(estadisticas["precio_dia_mas_reciente"]) + " $/kWh"
    )

    tarjeta_escasez = _crear_tarjeta_kpi(
        "Precio de Escasez",
        "{:.0f}".format(valor_escasez) + " $/kWh" if valor_escasez is not None else "N/D"
    )

    if estadisticas["variacion_diaria"] is not None:
        texto_variacion = "{:+.1f}%".format(estadisticas["variacion_diaria_porcentual"])
    else:
        texto_variacion = "N/D"

    tarjeta_variacion = _crear_tarjeta_kpi("Variacion Diaria", texto_variacion)

    tarjeta_promedio = _crear_tarjeta_kpi(
        "Promedio Mensual",
        "{:.0f}".format(estadisticas["promedio_mensual"]) + " $/kWh" if estadisticas["promedio_mensual"] is not None else "N/D"
    )

    fila_tarjetas = Table(
        [[tarjeta_precio, tarjeta_escasez, tarjeta_variacion, tarjeta_promedio]],
        colWidths=[4.4 * cm] * 4
    )
    fila_tarjetas.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    elementos.append(fila_tarjetas)
    elementos.append(Spacer(1, 18))

    elementos.append(Paragraph("Resumen del Comportamiento del Mercado", estilo_seccion))
    elementos.append(Paragraph(comentario, estilo_cuerpo))
    elementos.append(Spacer(1, 10))

    elementos.append(Paragraph("Evolucion del Precio - Mes Vigente", estilo_seccion))
    if ruta_grafico_mensual is not None and os.path.exists(ruta_grafico_mensual):
        elementos.append(Image(ruta_grafico_mensual, width=17 * cm, height=17 * cm * (5.5 / 11)))
    else:
        elementos.append(Paragraph("Grafico no disponible.", estilo_cuerpo))

    elementos.append(Spacer(1, 10))

    elementos.append(Paragraph("Estadisticas Detalladas", estilo_seccion))

    estilo_celda_indicador = ParagraphStyle(
        "CeldaIndicador", fontSize=TAMANO_FUENTE_BASE - 2, textColor=COLOR_TEXTO,
        fontName="Helvetica-Bold", leading=14
    )
    estilo_celda_valor = ParagraphStyle(
        "CeldaValor", fontSize=TAMANO_FUENTE_BASE - 2, textColor=COLOR_TEXTO,
        fontName="Helvetica", leading=14
    )
    estilo_celda_encabezado = ParagraphStyle(
        "CeldaEncabezado", fontSize=TAMANO_FUENTE_BASE - 2, textColor=colors.white,
        fontName="Helvetica-Bold", leading=14
    )

    def fila(indicador, valor):
        return [Paragraph(indicador, estilo_celda_indicador), Paragraph(valor, estilo_celda_valor)]

    datos_tabla_estadisticas = [
        [Paragraph("Indicador", estilo_celda_encabezado), Paragraph("Valor", estilo_celda_encabezado)],
        fila("Desviacion estandar", "{:.2f}".format(estadisticas["desviacion_estandar"])),
        fila("Volatilidad", "{:.2f}".format(estadisticas["volatilidad_porcentual"]) + "%"),
        fila("Promedio ultimos 5 dias", "{:.2f}".format(estadisticas["promedio_ultimos_5_dias"]) + " $/kWh"),
        fila("Promedio semanal", "{:.2f}".format(estadisticas["promedio_semanal"]) + " $/kWh"),
        fila("Tendencia", estadisticas["tendencia"]),
        fila("Pronostico proximo dia", "{:.2f}".format(estadisticas["pronostico_manana"]) + " $/kWh" if estadisticas["pronostico_manana"] is not None else "N/D"),
    ]

    tabla_estadisticas = Table(datos_tabla_estadisticas, colWidths=[8 * cm, 9 * cm], repeatRows=1)
    tabla_estadisticas.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), COLOR_FONDO_ENCABEZADO_TABLA),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, COLOR_FONDO_TARJETA]),
        ("GRID", (0, 0), (-1, -1), 0.5, COLOR_BORDE),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    elementos.append(tabla_estadisticas)

    elementos.append(PageBreak())
    elementos.append(Paragraph("IMAR del Dia Siguiente - Periodo a Periodo", estilo_seccion))

    if tabla_imar is not None:
        elementos.append(Paragraph(
            "Fecha: " + tabla_imar["fecha"] + "  |  Ajuste calculado con "
            + str(tabla_imar["dias_usados_para_el_ajuste"]) + " dia(s) de historial cruzado entre Precio de Bolsa real e IMAR.",
            estilo_nota
        ))
        elementos.append(Spacer(1, 8))

        estilo_celda_periodo = ParagraphStyle(
            "CeldaPeriodo", fontSize=9, textColor=COLOR_TEXTO,
            fontName="Helvetica-Bold", leading=12
        )
        estilo_celda_numero = ParagraphStyle(
            "CeldaNumero", fontSize=9, textColor=COLOR_TEXTO,
            fontName="Helvetica", leading=12, alignment=TA_CENTER
        )
        estilo_celda_encabezado_imar = ParagraphStyle(
            "CeldaEncabezadoImar", fontSize=9, textColor=colors.white,
            fontName="Helvetica-Bold", leading=12, alignment=TA_CENTER
        )

        datos_tabla_imar = [[
            Paragraph("Periodo", estilo_celda_encabezado_imar),
            Paragraph("IMAR", estilo_celda_encabezado_imar),
            Paragraph("IMAR Ajustado", estilo_celda_encabezado_imar)
        ]]

        for fila_imar in tabla_imar["filas"]:
            datos_tabla_imar.append([
                Paragraph(fila_imar["periodo"], estilo_celda_periodo),
                Paragraph("{:.1f}".format(fila_imar["imar_crudo"]), estilo_celda_numero),
                Paragraph("{:.1f}".format(fila_imar["imar_ajustado"]), estilo_celda_numero),
            ])

        valores_ajustados = [f["imar_ajustado"] for f in tabla_imar["filas"]]
        indice_del_maximo = valores_ajustados.index(max(valores_ajustados)) + 1
        indice_del_minimo = valores_ajustados.index(min(valores_ajustados)) + 1

        tabla_imar_pdf = Table(datos_tabla_imar, colWidths=[7 * cm, 4 * cm, 4 * cm], repeatRows=1)
        tabla_imar_pdf.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), COLOR_FONDO_ENCABEZADO_TABLA),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, COLOR_FONDO_TARJETA]),
            ("GRID", (0, 0), (-1, -1), 0.5, COLOR_BORDE),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BACKGROUND", (0, indice_del_maximo), (-1, indice_del_maximo), COLOR_RESALTADO_ALTO),
            ("BACKGROUND", (0, indice_del_minimo), (-1, indice_del_minimo), COLOR_RESALTADO_BAJO),
        ]))
        elementos.append(tabla_imar_pdf)
    else:
        elementos.append(Paragraph("El IMAR del dia siguiente aun no esta publicado por XM.", estilo_cuerpo))

    elementos.append(PageBreak())
    elementos.append(Paragraph("Tendencia Anual del Precio de Bolsa", estilo_seccion))
    if ruta_grafico_anual is not None and os.path.exists(ruta_grafico_anual):
        elementos.append(Image(ruta_grafico_anual, width=17 * cm, height=17 * cm * (5.5 / 11)))
    else:
        elementos.append(Paragraph("Grafico anual no disponible todavia.", estilo_cuerpo))

    documento.build(elementos)

    print("Informe generado: " + ruta_pdf)
    return ruta_pdf


if __name__ == "__main__":
    generar_informe_diario()
