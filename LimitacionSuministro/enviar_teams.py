"""
enviar_teams.py

Arma una Tarjeta Adaptable (Adaptive Card) con el formato de tabla
Status / Actividad / Nombre que usas actualmente, y la envía por POST
al webhook de Teams (el que se crea con la app "Flujos de trabajo").
"""

import os
import requests


def _fila_tabla(status, actividad, nombre, es_encabezado=False, es_titulo_status=False):
    """Crea una fila de la tabla Adaptive Card con 3 columnas (letra pequeña)."""
    peso = "Bolder" if (es_encabezado or es_titulo_status) else "Default"
    return {
        "type": "TableRow",
        "cells": [
            {
                "type": "TableCell",
                "items": [{"type": "TextBlock", "text": status, "wrap": True, "weight": peso, "size": "Small"}],
            },
            {
                "type": "TableCell",
                "items": [{"type": "TextBlock", "text": actividad, "wrap": True, "weight": peso, "size": "Small"}],
            },
            {
                "type": "TableCell",
                "items": [{"type": "TextBlock", "text": nombre, "wrap": True, "weight": peso, "size": "Small"}],
            },
        ],
    }


def _construir_tabla_seccion(titulo_status, filas):
    """
    Construye las filas de una sección (ÚLTIMOS INICIADOS o ÚLTIMOS
    CANCELADOS): encabezado Status/Actividad/Nombre + los datos, o
    "NO HUBO" si la lista viene vacía.
    """
    tabla = [_fila_tabla("Status", "Actividad", "Nombre", es_encabezado=True)]

    if not filas:
        tabla.append(_fila_tabla(titulo_status, "", "NO HUBO", es_titulo_status=True))
        return tabla

    primera = True
    for actividad, nombre in filas:
        status_mostrado = titulo_status if primera else ""
        tabla.append(_fila_tabla(status_mostrado, actividad, nombre, es_titulo_status=primera))
        primera = False

    return tabla


def construir_tarjeta(fecha_texto, datos_corte_usuarios, datos_en_bolsa):
    """
    fecha_texto: texto tipo "27 de agosto de 2026" para el encabezado.
    datos_corte_usuarios / datos_en_bolsa: dicts con "iniciados" y
        "cancelados" (listas de tuplas (actividad, empresa)).
    """
    columnas = [{"width": 1}, {"width": 1.3}, {"width": 3}]

    cuerpo = [
        {
            "type": "TextBlock",
            "text": f"Revisión PLS {fecha_texto}",
            "weight": "Bolder",
            "size": "Medium",
            "wrap": True,
        },
        {
            "type": "TextBlock",
            "text": "LIMITACIÓN DE SUMINISTRO CON CORTE A USUARIOS",
            "weight": "Bolder",
            "size": "Small",
            "wrap": True,
            "spacing": "Small",
        },
        {
            "type": "Table",
            "columns": columnas,
            "rows": _construir_tabla_seccion("ÚLTIMOS INICIADOS", datos_corte_usuarios["iniciados"]),
            "firstRowAsHeaders": False,
            "spacing": "Small",
        },
        {
            "type": "Table",
            "columns": columnas,
            "rows": _construir_tabla_seccion("ÚLTIMOS CANCELADOS", datos_corte_usuarios["cancelados"]),
            "firstRowAsHeaders": False,
            "spacing": "None",
        },
        {
            "type": "TextBlock",
            "text": "LIMITACIÓN DE SUMINISTRO EN BOLSA",
            "weight": "Bolder",
            "size": "Small",
            "wrap": True,
            "spacing": "Medium",
        },
        {
            "type": "Table",
            "columns": columnas,
            "rows": _construir_tabla_seccion("ÚLTIMOS INICIADOS", datos_en_bolsa["iniciados"]),
            "firstRowAsHeaders": False,
            "spacing": "Small",
        },
        {
            "type": "Table",
            "columns": columnas,
            "rows": _construir_tabla_seccion("ÚLTIMOS CANCELADOS", datos_en_bolsa["cancelados"]),
            "firstRowAsHeaders": False,
            "spacing": "None",
        },
    ]

    tarjeta = {
        "type": "AdaptiveCard",
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "version": "1.5",
        "body": cuerpo,
        "msteams": {"width": "Full"},
    }

    return {
        "type": "message",
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": tarjeta,
            }
        ],
    }


def enviar_a_teams(payload, url_webhook=None):
    """Envía el payload (tarjeta) al webhook de Teams. Lanza error si falla."""
    if url_webhook is None:
        url_webhook = os.environ["TEAMS_WEBHOOK_LIMITACION"]

    respuesta = requests.post(url_webhook, json=payload, timeout=30)
    respuesta.raise_for_status()
    return respuesta
