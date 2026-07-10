"""
Modulo: generar_informe_diario.py
Ubicacion: Reportes/generar_informe_diario.py

Genera el informe diario en PDF del Precio de Bolsa (Modulo 1, 6 y 8
de la especificacion del proyecto).

Estructura del documento (3 paginas):
PAGINA 1: Titulo, tarjetas KPI, Resumen del Comportamiento del
    Mercado, grafico de Evolucion del Precio (mes vigente), y tabla
    de Estadisticas Detalladas.
PAGINA 2: Grafico IMAR vs Precio de Bolsa Real (mes vigente), grafico
    de Tendencia Anual del Precio de Bolsa, y grafico del IMAR del
    dia siguiente periodo a periodo. Los tres graficos se muestran
    en tamano reducido para que quepan juntos en la misma pagina.
PAGINA 3: Tabla del IMAR del dia siguiente, periodo a periodo (con
    Costo WCO GasTY y Costo GE Gas TY, y fila de promedio).

Margenes: izquierdo, derecho e inferior mas angostos (1.0cm) para
ganar espacio de contenido util en cada pagina. El margen superior
se mantiene mas amplio (2.6cm) para dejar sitio al logo de la
empresa, que se dibuja en la esquina superior derecha.

Todos los textos visibles del PDF (titulos, encabezados de tabla,
notas, etc.) llevan tildes y ortografia correcta en espanol.

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
from grafico_mensual import generar_grafico_mensual
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

# Margenes de la pagina. Izquierdo/derecho/inferior mas angostos para
# ganar espacio de contenido; superior mas amplio para dejar sitio al logo.
MARGEN_SUPERIOR = 2.6 * cm
MARGEN_INFERIOR = 1.0 * cm
MARGEN_IZQUIERDO = 1.0 * cm
MARGEN_DERECHO = 1.0 * cm

# Ancho de pagina carta (letter) es 21.59cm. Restando los margenes
# izquierdo y derecho, el ancho util de contenido queda en:
ANCHO_CONTENIDO = 21.59 * cm - MARGEN_IZQUIERDO - MARGEN_DERECHO

# Proporcion real del archivo del logo (ancho x alto en pixeles),
# para dibujarlo siempre con las proporciones correctas y que no se
# vea deformado.
PROPORCION_LOGO = 545 / 1645  # alto / ancho
ANCHO_LOGO = 2.2 * cm
ALTO_LOGO = ANCHO_LOGO * PROPORCION_LOGO

# Valores ESTATICOS de las columnas "Costo WCO GasTY" y "Costo GE Gas
# TY" en la tabla del IMAR. Se actualizan manualmente cambiando estos
# dos numeros cuando corresponda.
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
    superior derecha de la pagina. Se usa como callback "onPage" de
    SimpleDocTemplate, asi que ReportLab lo llama automaticamente en
    CADA pagina del PDF (primera y siguientes).
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
    Crea una tarjeta KPI compacta, con tamano y tipografia uniformes
    (cerca de 12pt), y una franja de color delgada en la parte
    superior a modo de acento visual.
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

    contenido =
