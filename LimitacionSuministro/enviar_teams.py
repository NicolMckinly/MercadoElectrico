"""
enviar_teams.py

Arma el reporte de limitación de suministro como una Tarjeta Adaptable
liviana (listas por sección en vez de una tabla con celdas, que pesa
mucho más en JSON) y la envía al webhook de Teams como UN solo
mensaje. Si aun así el reporte quedara demasiado pesado (calculado
ANTES de enviar, no después), se divide automáticamente en dos
mensajes más livianos en vez de fallar.
"""

import os
import json
import requests

# Límite conservador (bytes) para decidir si el mensaje único cabe.
# Teams suele rechazar tarjetas por encima de ~25 KB.
LIMITE_BYTES_MENSAJE_UNICO = 20000


def _texto_seccion(filas):
    """
    Convierte la lista de (actividad, nombre) en un solo bloque de
    texto tipo lista, mucho más liviano que una tabla con celdas.
    """
    if not filas:
        return "**NO HUBO**"
    return "\n\n".join(f"- **{actividad}** — {nombre}" for actividad, nombre in filas)


def _bloques_seccion(titulo_seccion, datos):
    """Bloques de una sección completa (título + iniciados + cancelados)."""
    return [
        {
            "type": "TextBlock",
            "text": titulo_seccion,
            "weight": "Bolder",
            "size": "Small",
            "wrap": True,
            "spacing": "Medium",
        },
        {
            "type": "TextBlock",
            "text": "ÚLTIMOS INICIADOS",
            "weight": "Bolder",
            "size": "Small",
            "wrap": True,
            "spacing": "Small",
        },
        {
            "type": "TextBlock",
            "text": _texto_seccion(datos["iniciados"]),
            "wrap": True,
            "size": "Small",
            "spacing": "Small",
        },
        {
            "type": "TextBlock",
            "text": "ÚLTIMOS CANCELADOS",
            "weight": "Bolder",
            "size": "Small",
            "wrap": True,
            "spacing": "Medium",
        },
        {
            "type": "TextBlock",
            "text": _texto_seccion(datos["cancelados"]),
            "wrap": True,
            "size": "Small",
            "spacing": "Small",
        },
    ]


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


def _construir_tarjeta_completa(fecha_texto, datos_corte_usuarios, datos_en_bolsa):
    cuerpo = [
        {
            "type": "TextBlock",
            "text": f"Revisión PLS {fecha_texto}",
            "weight": "Bolder",
            "size": "Medium",
            "wrap": True,
        },
    ]
    cuerpo += _bloques_seccion("LIMITACIÓN DE SUMINISTRO CON CORTE A USUARIOS", datos_corte_usuarios)
    cuerpo += _bloques_seccion("LIMITACIÓN DE SUMINISTRO EN BOLSA", datos_en_bolsa)
    return _envolver_en_mensaje(cuerpo)


def _construir_tarjetas_divididas(fecha_texto, datos_corte_usuarios, datos_en_bolsa):
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
        ]
        cuerpo += _bloques_seccion(titulo_seccion, datos)
        tarjetas.append(_envolver_en_mensaje(cuerpo))
    return tarjetas


def enviar_a_teams(fecha_texto, datos_corte_usuarios, datos_en_bolsa, url_webhook=None):
    """
    Construye el reporte y lo envía a Teams. Decide ANTES de enviar si
    cabe en un solo mensaje (según su tamaño real en bytes) o si hay
    que dividirlo en dos, para no depender de un error que llega
    demasiado tarde para reaccionar.
    """
    if url_webhook is None:
        url_webhook = os.environ["TEAMS_WEBHOOK_LIMITACION"]

    tarjeta_unica = _construir_tarjeta_completa(fecha_texto, datos_corte_usuarios, datos_en_bolsa)
    tamano_bytes = len(json.dumps(tarjeta_unica).encode("utf-8"))

    if tamano_bytes <= LIMITE_BYTES_MENSAJE_UNICO:
        payloads = [tarjeta_unica]
    else:
        print(
            f"El reporte pesa {tamano_bytes} bytes, por encima del límite seguro "
            f"({LIMITE_BYTES_MENSAJE_UNICO}). Se envía dividido en dos mensajes."
        )
        payloads = _construir_tarjetas_divididas(fecha_texto, datos_corte_usuarios, datos_en_bolsa)

    respuestas = []
    for payload in payloads:
        respuesta = requests.post(url_webhook, json=payload, timeout=30)
        respuesta.raise_for_status()
        respuestas.append(respuesta)

    return respuestas
