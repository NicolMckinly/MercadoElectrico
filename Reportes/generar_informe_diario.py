"""
Modulo: generar_informe_diario.py
Ubicacion: Reportes/generar_informe_diario.py

Genera el informe diario en PDF del Precio de Bolsa (Modulo 1, 6 y 8
de la especificacion del proyecto).

Estructura del documento:
PAGINA 1: Titulo, tarjetas KPI, Resumen del Comportamiento del
    Mercado, tabla de Estadisticas Detalladas, y grafico de
    Tendencia Anual del Precio de Bolsa.
PAGINA 2: Grafico IMAR vs Precio de Bolsa Real (mes vigente) y
    grafico del IMAR del dia siguiente periodo a periodo.
PAGINA 3: Tabla del IMAR del dia siguiente, periodo a periodo (con
    Costo WCO GasTY y Costo GE Gas TY, y fila de promedio). La
    columna que antes decia "IMAR Ajustado" ahora se llama
    "PB Proyectado TMM".

NOTA: el grafico de "Evolucion del Precio - Mes Vigente" (antes en
la pagina 1) se movio al Informe de Variables Hidrologicas
(Reportes/generar_informe_hidrologico.py), para que este informe
diario quepa completo en 3 paginas.

Margenes: izquierdo, derecho e inferior mas angostos (1.0cm) para
ganar espacio de contenido util en cada pagina. El margen superior
es de 2.0cm, para dejar sitio al logo de la empresa, que se dibuja
en la esquina superior derecha.

Todos los textos visibles del PDF llevan tildes y ortografia
correcta en espanol.

Los valores de Costo WCO GasTY y Costo GE Gas TY son ESTATICOS por
ahora (se definen como constantes mas abajo, COSTO_WCO_GASTY y
COSTO_GE_GASTY) y se pueden actualizar manualmente editando esos dos
numeros cuando corresponda.

La fecha se calcula con ahora_colombia() (ver BaseDatos/zona_horaria.py)
en vez de datetime.now(), para que el nombre del archivo y la fecha
mostrada en el titulo siempre correspondan a la hora real de Colombia.

Este archivo NO descarga datos ni hace calculos de mercado. Su unica
responsabilidad es tomar los resultados de los otros modulos y armar
el documento PDF final.
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

from estadisticas_precio import calcular_estadisticas, generar_comentario_automatico
from grafico_anual import generar_grafico_anual
from grafico_imar import generar_grafico_imar_siguiente_dia
from grafico_comparacion_imar_bolsa import generar_grafico_comparacion_imar_bolsa
from tabla_imar_siguiente_dia import obtener_tabla_imar_siguiente_dia
from base_datos import consultar_precio_escasez_mas_reciente
from zona_horaria import ahora_colombia

CARPETA_ACTUAL = os.path.dirname(os.path.abspath(__file__))
RUTA_LOGO = os.path.join(CARPETA_ACTUAL, "logo_termomorro.png")

COLOR_TEXTO = colors.black
COLOR_FONDO_ENCABEZADO_TABLA = colors.HexColor("#333333")
COLOR_FONDO_TARJETA = colors.HexColor("#F7F7F7")
COLOR_BORDE = colors.HexColor("#DDDDDD")
COLOR_RESALTADO_ALTO = colors.HexColor("#B6D7A8")
COLOR_RESALTADO_BAJO = colors.HexColor("#FFE599")

COLOR_ACENTO_PRECIO = colors.HexColor("#1F4E79")
COLOR_ACENTO_ESCASEZ = colors.HexColor("#B22222")
COLOR_ACENTO_VARIACION = colors.HexColor("#1F6F50")
COLOR_ACENTO_PROMEDIO = colors.HexColor("#D9822B")

TAMANO_FUENTE_BASE = 12
ANCHO_TARJETA = 4.3 * cm

MARGEN_SUPERIOR = 2.0 * cm
MARGEN_INFERIOR = 1.0 * cm
MARGEN_IZQUIERDO = 1.0 * cm
MARGEN_DERECHO = 1.0 * cm

ANCHO_CONTENIDO = 21.59 * cm - MARGEN_IZQUIERDO - MARGEN_DERECHO

PROPORCION_LOGO = 545 / 1645  # alto / ancho
ANCHO_LOGO = 2.2 * cm
ALTO_LOGO = ANCHO_LOGO * PROPORCION_LOGO

COSTO_WCO_GASTY = 447.2
COSTO_GE_GASTY = 497.9

MESES_EN_ESPANOL_LARGO = {
    1: "enero", 2: "febrero", 3: "marzo", 4: "abril",
    5: "mayo", 6: "junio", 7: "julio", 8: "agosto",
    9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre",
}


def _dibujar_logo_en_pagina(canvas_obj, doc):
    """
    Dibuja el logo de la empresa, pequeno tipo membrete, en la esquina
    superior derecha de la pagina.
    """
    if not os.path.exists(RUTA_LOGO):
        return

    ancho_pagina, alto_pagina = doc.pagesize
    x = ancho_pagina - doc.rightMargin - ANCHO_LOGO
    y = alto_pagina - 1.0 * cm - ALTO_LOGO

    canvas_obj.drawImage(
        RUTA_LOGO, x, y,
        width=ANCHO_LOGO, height=ALTO_LOGO,
        preserveAspectRatio=True, mask="auto"
    )


def _crear_tarjeta_kpi(titulo, valor, color_acento):
    """
    Crea una tarjeta KPI compacta, con tamano y tipografia uniformes.
    """
    estilo_titulo = ParagraphStyle(
        "TituloTarjeta", fontSize=8.5, textColor=COLOR_TEXTO,
        alignment=TA_CENTER, spaceAfter=2, fontName="Helvetica-Bold",
        leading=10
    )
    estilo_valor = ParagraphStyle(
        "ValorTarjeta", fontSize=12, textColor=color_acento,
        alignment=TA_CENTER, fontName="Helvetica-Bold"
    )

    franja_acento = Table([[""]], colWidths=[ANCHO_TARJETA], rowHeights=[0.15 * cm])
    franja_acento.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), color_acento),
    ]))

    contenido = [
        [franja_acento],
        [Paragraph(titulo, estilo_titulo)],
        [Paragraph(valor, estilo_valor)]
    ]

    tabla = Table(contenido, colWidths=[ANCHO_TARJETA], rowHeights=[0.15 * cm, 0.85 * cm, 0.7 * cm])
    tabla.setStyle(TableStyle([
        ("SPAN", (0, 0), (0, 0)),
        ("BACKGROUND", (0, 1), (-1, -1), COLOR_FONDO_TARJETA),
        ("BOX", (0, 0), (-1, -1), 0.75, COLOR_BORDE),
        ("TOPPADDING", (0, 1), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 3),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))

    return tabla


def generar_informe_diario():
    estadisticas = calcular_estadisticas()

    if estadisticas is None:
        print("No hay datos suficientes para generar el informe.")
        return None

    comentario = generar_comentario_automatico(estadisticas)
    ruta_grafico_anual = generar_grafico_anual()
    ruta_grafico_comparacion = generar_grafico_comparacion_imar_bolsa()
    tabla_imar = obtener_tabla_imar_siguiente_dia()
    ruta_grafico_imar = generar_grafico_imar_siguiente_dia(tabla_imar)
    _, valor_escasez = consultar_precio_escasez_mas_reciente()

    hoy = ahora_colombia()
    nombre_archivo = "Informe_Diario_PrecioBolsa_" + hoy.strftime("%Y_%m_%d") + ".pdf"
    ruta_pdf = os.path.join(CARPETA_ACTUAL, nombre_archivo)

    documento = SimpleDocTemplate(
        ruta_pdf,
        pagesize=letter,
        topMargin=MARGEN_SUPERIOR,
        bottomMargin=MARGEN_INFERIOR,
        leftMargin=MARGEN_IZQUIERDO,
        rightMargin=MARGEN_DERECHO
    )

    estilos = getSampleStyleSheet()

    estilo_titulo_principal = ParagraphStyle(
        "TituloPrincipal", parent=estilos["Title"],
        textColor=COLOR_TEXTO, fontSize=16, spaceAfter=2,
        fontName="Helvetica-Bold"
    )
    estilo_subtitulo = ParagraphStyle(
        "Subtitulo", parent=estilos["Normal"],
        textColor=COLOR_TEXTO, fontSize=TAMANO_FUENTE_BASE, spaceAfter=8,
        fontName="Helvetica"
    )
    estilo_seccion = ParagraphStyle(
        "Seccion", parent=estilos["Heading2"],
        textColor=COLOR_TEXTO, fontSize=12, spaceBefore=8, spaceAfter=3,
        fontName="Helvetica-Bold"
    )
    estilo_cuerpo = ParagraphStyle(
        "Cuerpo", parent=estilos["Normal"],
        fontSize=TAMANO_FUENTE_BASE, leading=15, textColor=COLOR_TEXTO,
        fontName="Helvetica"
    )
    estilo_nota = ParagraphStyle(
        "Nota", parent=estilos["Normal"],
        fontSize=9, leading=12, textColor=COLOR_TEXTO,
        fontName="Helvetica-Oblique"
    )

    elementos = []

    # ======================= PAGINA 1 =======================

    elementos.append(Paragraph("Informe Diario - Precio de Bolsa Nacional", estilo_titulo_principal))

    fecha_en_espanol = hoy.strftime("%d") + " de " + MESES_EN_ESPANOL_LARGO[hoy.month] + " de " + str(hoy.year)
    elementos.append(Paragraph(fecha_en_espanol, estilo_subtitulo))

    tarjeta_precio = _crear_tarjeta_kpi(
        "Precio Bolsa Actual (" + estadisticas["fuente_dia_mas_reciente"] + ")",
        "{:.0f}".format(estadisticas["precio_dia_mas_reciente"]) + " $/kWh",
        COLOR_ACENTO_PRECIO
    )

    tarjeta_escasez = _crear_tarjeta_kpi(
        "Precio de Escasez",
        "{:.0f}".format(valor_escasez) + " $/kWh" if valor_escasez is not None else "N/D",
        COLOR_ACENTO_ESCASEZ
    )

    if estadisticas["variacion_diaria"] is not None:
        texto_variacion = "{:+.1f}%".format(estadisticas["variacion_diaria_porcentual"])
    else:
        texto_variacion = "N/D"

    tarjeta_variacion = _crear_tarjeta_kpi("Variación Diaria", texto_variacion, COLOR_ACENTO_VARIACION)

    tarjeta_promedio = _crear_tarjeta_kpi(
        "Promedio Mensual",
        "{:.0f}".format(estadisticas["promedio_mensual"]) + " $/kWh" if estadisticas["promedio_mensual"] is not None else "N/D",
        COLOR_ACENTO_PROMEDIO
    )

    fila_tarjetas = Table(
        [[tarjeta_precio, tarjeta_escasez, tarjeta_variacion, tarjeta_promedio]],
        colWidths=[4.4 * cm] * 4
    )
    fila_tarjetas.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    elementos.append(fila_tarjetas)
    elementos.append(Spacer(1, 8))

    elementos.append(Paragraph("Resumen del Comportamiento del Mercado", estilo_seccion))
    elementos.append(Paragraph(comentario, estilo_cuerpo))
    elementos.append(Spacer(1, 4))

    # ---------- Tabla de Estadisticas Detalladas (version compacta) ----------
    seccion_estadisticas = []
    seccion_estadisticas.append(Paragraph("Estadísticas Detalladas", estilo_seccion))

    estilo_celda_indicador = ParagraphStyle(
        "CeldaIndicador", fontSize=9, textColor=COLOR_TEXTO,
        fontName="Helvetica-Bold", leading=11
    )
    estilo_celda_valor = ParagraphStyle(
        "CeldaValor", fontSize=9, textColor=COLOR_TEXTO,
        fontName="Helvetica", leading=11
    )
    estilo_celda_encabezado = ParagraphStyle(
        "CeldaEncabezado", fontSize=9, textColor=colors.white,
        fontName="Helvetica-Bold", leading=11
    )

    def fila(indicador, valor):
        return [Paragraph(indicador, estilo_celda_indicador), Paragraph(valor, estilo_celda_valor)]

    datos_tabla_estadisticas = [
        [Paragraph("Indicador", estilo_celda_encabezado), Paragraph("Valor", estilo_celda_encabezado)],
        fila("Desviación estándar", "{:.2f}".format(estadisticas["desviacion_estandar"])),
        fila("Volatilidad", "{:.2f}".format(estadisticas["volatilidad_porcentual"]) + "%"),
        fila("Promedio últimos 5 días", "{:.2f}".format(estadisticas["promedio_ultimos_5_dias"]) + " $/kWh"),
        fila("Promedio semanal", "{:.2f}".format(estadisticas["promedio_semanal"]) + " $/kWh"),
        fila("Tendencia", estadisticas["tendencia"]),
        fila("Pronóstico próximo día", "{:.2f}".format(estadisticas["pronostico_manana"]) + " $/kWh" if estadisticas["pronostico_manana"] is not None else "N/D"),
    ]

    tabla_estadisticas = Table(datos_tabla_estadisticas, colWidths=[ANCHO_CONTENIDO * 0.47, ANCHO_CONTENIDO * 0.53], repeatRows=1)
    tabla_estadisticas.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), COLOR_FONDO_ENCABEZADO_TABLA),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, COLOR_FONDO_TARJETA]),
        ("GRID", (0, 0), (-1, -1), 0.5, COLOR_BORDE),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    seccion_estadisticas.append(tabla_estadisticas)

    elementos.append(KeepTogether(seccion_estadisticas))

    elementos.append(Spacer(1, 4))

    # ---------- Grafico Tendencia Anual del Precio de Bolsa (misma pagina que las estadisticas) ----------
    seccion_anual = [Paragraph("Tendencia Anual del Precio de Bolsa", estilo_seccion)]
    if ruta_grafico_anual is not None and os.path.exists(ruta_grafico_anual):
        seccion_anual.append(Image(ruta_grafico_anual, width=ANCHO_CONTENIDO, height=ANCHO_CONTENIDO * (4.2 / 11)))
    else:
        seccion_anual.append(Paragraph("Gráfico anual no disponible todavía.", estilo_cuerpo))
    elementos.append(KeepTogether(seccion_anual))

    # ======================= PAGINA 2 =======================
    elementos.append(PageBreak())

    # ---------- Grafico IMAR vs Precio de Bolsa Real - Mes Vigente ----------
    seccion_comparacion = [Paragraph("IMAR vs Precio de Bolsa Real - Mes Vigente", estilo_seccion)]
    if ruta_grafico_comparacion is not None and os.path.exists(ruta_grafico_comparacion):
        seccion_comparacion.append(Image(ruta_grafico_comparacion, width=ANCHO_CONTENIDO, height=ANCHO_CONTENIDO * (4.6 / 11)))
    else:
        seccion_comparacion.append(Paragraph("Gráfico no disponible todavía.", estilo_cuerpo))
    elementos.append(KeepTogether(seccion_comparacion))

    elementos.append(Spacer(1, 6))

    # ---------- Grafico del IMAR del Dia Siguiente ----------
    seccion_imar = [Paragraph("IMAR del Día Siguiente", estilo_seccion)]
    if ruta_grafico_imar is not None and os.path.exists(ruta_grafico_imar):
        seccion_imar.append(Image(ruta_grafico_imar, width=ANCHO_CONTENIDO, height=ANCHO_CONTENIDO * (5.4 / 11)))
    else:
        seccion_imar.append(Paragraph("El IMAR del día siguiente aún no está publicado, no hay gráfico disponible.", estilo_cuerpo))
    elementos.append(KeepTogether(seccion_imar))

    # ======================= PAGINA 3 =======================
    elementos.append(PageBreak())
    elementos.append(Paragraph("IMAR del Día Siguiente - Período a Período", estilo_seccion))

    if tabla_imar is not None:
        elementos.append(Paragraph(
            "Fecha: " + tabla_imar["fecha"] + "  |  Ajuste calculado con "
            + str(tabla_imar["dias_usados_para_el_ajuste"]) + " día(s) de historial cruzado entre Precio de Bolsa real e IMAR.",
            estilo_nota
        ))
        elementos.append(Spacer(1, 6))

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
        estilo_celda_promedio_texto = ParagraphStyle(
            "CeldaPromedioTexto", fontSize=9, textColor=colors.white,
            fontName="Helvetica-Bold", leading=12
        )
        estilo_celda_promedio_numero = ParagraphStyle(
            "CeldaPromedioNumero", fontSize=9, textColor=colors.white,
            fontName="Helvetica-Bold", leading=12, alignment=TA_CENTER
        )

        datos_tabla_imar = [[
            Paragraph("Período", estilo_celda_encabezado_imar),
            Paragraph("IMAR", estilo_celda_encabezado_imar),
            Paragraph("PB Proyectado TMM", estilo_celda_encabezado_imar),
            Paragraph("Costo WCO GasTY", estilo_celda_encabezado_imar),
            Paragraph("Costo GE Gas TY", estilo_celda_encabezado_imar)
        ]]

        for fila_imar in tabla_imar["filas"]:
            datos_tabla_imar.append([
                Paragraph(fila_imar["periodo"], estilo_celda_periodo),
                Paragraph("{:.1f}".format(fila_imar["imar_crudo"]), estilo_celda_numero),
                Paragraph("{:.1f}".format(fila_imar["imar_ajustado"]), estilo_celda_numero),
                Paragraph("{:.1f}".format(COSTO_WCO_GASTY), estilo_celda_numero),
                Paragraph("{:.1f}".format(COSTO_GE_GASTY), estilo_celda_numero),
            ])

        valores_crudos = [f["imar_crudo"] for f in tabla_imar["filas"]]
        valores_ajustados = [f["imar_ajustado"] for f in tabla_imar["filas"]]
        indice_del_maximo = valores_ajustados.index(max(valores_ajustados)) + 1
        indice_del_minimo = valores_ajustados.index(min(valores_ajustados)) + 1

        promedio_crudo = sum(valores_crudos) / len(valores_crudos)
        promedio_ajustado = sum(valores_ajustados) / len(valores_ajustados)

        indice_fila_promedio = len(datos_tabla_imar)
        datos_tabla_imar.append([
            Paragraph("PROMEDIO", estilo_celda_promedio_texto),
            Paragraph("{:.1f}".format(promedio_crudo), estilo_celda_promedio_numero),
            Paragraph("{:.1f}".format(promedio_ajustado), estilo_celda_promedio_numero),
            Paragraph("{:.1f}".format(COSTO_WCO_GASTY), estilo_celda_promedio_numero),
            Paragraph("{:.1f}".format(COSTO_GE_GASTY), estilo_celda_promedio_numero),
        ])

        tabla_imar_pdf = Table(
            datos_tabla_imar,
            colWidths=[ANCHO_CONTENIDO * 0.24, ANCHO_CONTENIDO * 0.19, ANCHO_CONTENIDO * 0.19, ANCHO_CONTENIDO * 0.19, ANCHO_CONTENIDO * 0.19],
            repeatRows=1
        )
        tabla_imar_pdf.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), COLOR_FONDO_ENCABEZADO_TABLA),
            ("ROWBACKGROUNDS", (0, 1), (-1, indice_fila_promedio - 1), [colors.white, COLOR_FONDO_TARJETA]),
            ("GRID", (0, 0), (-1, -1), 0.5, COLOR_BORDE),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BACKGROUND", (0, indice_del_maximo), (-1, indice_del_maximo), COLOR_RESALTADO_ALTO),
            ("BACKGROUND", (0, indice_del_minimo), (-1, indice_del_minimo), COLOR_RESALTADO_BAJO),
            ("BACKGROUND", (0, indice_fila_promedio), (-1, indice_fila_promedio), COLOR_FONDO_ENCABEZADO_TABLA),
        ]))
        elementos.append(tabla_imar_pdf)
    else:
        elementos.append(Paragraph("El IMAR del día siguiente aún no está publicado por XM.", estilo_cuerpo))

    documento.build(
        elementos,
        onFirstPage=_dibujar_logo_en_pagina,
        onLaterPages=_dibujar_logo_en_pagina
    )

    print("Informe generado: " + ruta_pdf)
    return ruta_pdf


if __name__ == "__main__":
    generar_informe_diario()
