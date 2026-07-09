"""
Modulo: generar_informe_diario.py
Ubicacion: Reportes/generar_informe_diario.py

Genera el informe diario en PDF del Precio de Bolsa (Modulo 1, 6 y 8
de la especificacion del proyecto): pagina ejecutiva con indicadores,
comentario automatico, grafico mensual, grafico anual, grafico del
IMAR del dia siguiente periodo a periodo, tabla de estadisticas, y
tabla del IMAR del dia siguiente (crudo, ajustado, Costo WCO GasTY y
Costo GE Gas TY, con fila de promedio al final, y el periodo mas alto
resaltado en verde y el mas bajo en amarillo).

Los valores de Costo WCO GasTY y Costo GE Gas TY son ESTATICOS por
ahora (se definen como constantes mas abajo, COSTO_WCO_GASTY y
COSTO_GE_GASTY) y se pueden actualizar manualmente editando esos dos
numeros cuando corresponda.

El logo de la empresa se dibuja en la esquina superior derecha de
TODAS las paginas del documento, en tamano pequeno tipo membrete.

La fecha del titulo se muestra en espanol (usando el diccionario
MESES_EN_ESPANOL_LARGO), porque el servidor donde corre el sistema
(GitHub Actions) no tiene instalado el idioma espanol, y usar
strftime("%B") directamente mostraria el mes en ingles.

La fecha se calcula con ahora_colombia() (ver BaseDatos/zona_horaria.py)
en vez de datetime.now(), para que el nombre del archivo y la fecha
mostrada en el titulo siempre correspondan a la hora real de Colombia
y no a la hora UTC del servidor (que va 5 horas adelante).

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
from grafico_imar import generar_grafico_imar_siguiente_dia
from tabla_imar_siguiente_dia import obtener_tabla_imar_siguiente_dia
from base_datos import
