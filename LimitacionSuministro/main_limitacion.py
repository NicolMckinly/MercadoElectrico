"""
enviar_teams.py

Arma dos Tarjetas Adaptables (una para "CON CORTE A USUARIOS" y otra
para "EN BOLSA") y las envía como dos mensajes separados al webhook de
Teams. Se dividen en dos mensajes porque una sola tarjeta con todos los
datos puede quedar demasiado pesada y Teams la rechaza con el error
"RequestEntityTooLarge".
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


def _construir_tarjeta_seccion(fecha_texto, titulo_seccion, datos, numero_parte, total_partes):
    """
    Construye UNA tarjeta con el reporte de una sola sección (por
    ejemplo, solo "CON CORTE A USUARIOS"), para mantener cada mensaje
    liviano.
    """
    columnas = [{"width": 1}, {"width": 2}, {"width": 5}]

    cuerpo = [
        {
            "type": "TextBlock",
            "text": f"Revisión PLS {fecha_texto} ({numero_parte}/{total_partes})",
            "weight": "Bolder",
            "size": "Medium",
            "wrap": True,
        },
        {
            "type": "TextBlock",
            "text": titulo_seccion,
            "weight": "Bolder",
            "size": "Small",
            "wrap": True,
            "spacing": "Small",
        },
        {
            "type": "Table",
            "columns": columnas,
            "rows": _construir_tabla_seccion("ÚLTIMOS INICIADOS", datos["iniciados"]),
            "firstRowAsHeaders": False,
            "spacing": "Small",
        },
        {
            "type": "Table",
            "columns": columnas,
            "rows": _construir_tabla_seccion("ÚLTIMOS CANCELADOS", datos["cancelados"]),
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


def construir_tarjetas(fecha_texto, datos_corte_usuarios, datos_en_bolsa):
    """
    Devuelve una LISTA de dos payloads (dos mensajes) en vez de uno
    solo, para no exceder el límite de tamaño de Teams.
    """
    return [
        _construir_tarjeta_seccion(
            fecha_texto, "LIMITACIÓN DE SUMINISTRO CON CORTE A USUARIOS", datos_corte_usuarios, 1, 2
        ),
        _construir_tarjeta_seccion(
            fecha_texto, "LIMITACIÓN DE SUMINISTRO EN BOLSA", datos_en_bolsa, 2, 2
        ),
    ]


def enviar_a_teams(payloads, url_webhook=None):
    """
    Envía uno o varios payloads (tarjetas) al webhook de Teams, uno por
    uno. Lanza error si alguno falla.
    """
    if url_webhook is None:
        url_webhook = os.environ["TEAMS_WEBHOOK_LIMITACION"]

    if isinstance(payloads, dict):
        payloads = [payloads]

    respuestas = []
    for payload in payloads:
        respuesta = requests.post(url_webhook, json=payload, timeout=30)
        respuesta.raise_for_status()
        respuestas.append(respuesta)

    return respuestas
