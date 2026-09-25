"""
enviar_teams.py

Arma la Tarjeta Adaptable con el formato de tabla Status/Actividad/
Nombre y la envía como UN solo mensaje al webhook de Teams. Si Teams
la rechaza por ser demasiado pesada (error 413 / RequestEntityTooLarge,
lo cual puede pasar en una semana con muchos registros), el script
reintenta automáticamente dividiéndola en dos mensajes más livianos
(uno por sección) en vez de fallar por completo.
"""

import os
import requests

COLUMNAS = [{"width": 1}, {"width": 2}, {"width": 5}]


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


def _envolver_en_mensaje(cuerpo):
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


def construir_tarjeta(fecha_texto, datos_corte_usuarios, datos_en_bolsa):
    """Construye el reporte COMPLETO como un solo mensaje (formato normal)."""
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
            "columns": COLUMNAS,
            "rows": _construir_tabla_seccion("ÚLTIMOS INICIADOS", datos_corte_usuarios["iniciados"]),
            "firstRowAsHeaders": False,
            "spacing": "Small",
        },
        {
            "type": "Table",
            "columns": COLUMNAS,
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
            "columns": COLUMNAS,
            "rows": _construir_tabla_seccion("ÚLTIMOS INICIADOS", datos_en_bolsa["iniciados"]),
            "firstRowAsHeaders": False,
            "spacing": "Small",
        },
        {
            "type": "Table",
            "columns": COLUMNAS,
            "rows": _construir_tabla_seccion("ÚLTIMOS CANCELADOS", datos_en_bolsa["cancelados"]),
            "firstRowAsHeaders": False,
            "spacing": "None",
        },
    ]
    return _envolver_en_mensaje(cuerpo)


def construir_tarjetas_divididas(fecha_texto, datos_corte_usuarios, datos_en_bolsa):
    """
    Construye el mismo reporte pero como DOS mensajes separados (uno
    por sección). Se usa solo como respaldo si el mensaje único queda
    demasiado pesado para Teams.
    """
    partes = [
        ("LIMITACIÓN DE SUMINISTRO CON CORTE A USUARIOS", datos_corte_usuarios),
        ("LIMITACIÓN DE SUMINISTRO EN BOLSA", datos_en_bolsa),
    ]
    tarjetas = []
    for numero, (titulo_seccion, datos) in enumerate(partes, start=1):
        cuerpo = [
            {
                "type": "TextBlock",
                "text": f"Revisión PLS {fecha_texto} ({numero}/2)",
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
                "columns": COLUMNAS,
                "rows": _construir_tabla_seccion("ÚLTIMOS INICIADOS", datos["iniciados"]),
                "firstRowAsHeaders": False,
                "spacing": "Small",
            },
            {
                "type": "Table",
                "columns": COLUMNAS,
                "rows": _construir_tabla_seccion("ÚLTIMOS CANCELADOS", datos["cancelados"]),
                "firstRowAsHeaders": False,
                "spacing": "None",
            },
        ]
        tarjetas.append(_envolver_en_mensaje(cuerpo))
    return tarjetas


def _es_error_de_tamano(error):
    respuesta = getattr(error, "response", None)
    return respuesta is not None and respuesta.status_code in (413,)


def enviar_a_teams(payload_principal, payloads_respaldo=None, url_webhook=None):
    """
    Intenta enviar el reporte como UN solo mensaje (payload_principal).
    Si Teams lo rechaza por ser demasiado pesado (413), y se pasó
    payloads_respaldo, envía esos en su lugar (varios mensajes más
    livianos). Si no hay respaldo, o el error no es de tamaño, se
    lanza el error normalmente.
    """
    if url_webhook is None:
        url_webhook = os.environ["TEAMS_WEBHOOK_LIMITACION"]

    try:
        respuesta = requests.post(url_webhook, json=payload_principal, timeout=30)
        respuesta.raise_for_status()
        return [respuesta]
    except requests.exceptions.HTTPError as error:
        if not _es_error_de_tamano(error) or not payloads_respaldo:
            raise

        print(
            "El mensaje único quedó demasiado pesado para Teams (error 413). "
            "Se reenvía dividido en varios mensajes más livianos..."
        )
        respuestas = []
        for payload in payloads_respaldo:
            respuesta = requests.post(url_webhook, json=payload, timeout=30)
            respuesta.raise_for_status()
            respuestas.append(respuesta)
        return respuestas
