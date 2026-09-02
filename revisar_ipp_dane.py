"""
Revisa si el DANE ya publico el boletin del IPP (Indice de Precios del
Productor) provisional del mes en curso, y si es la primera vez que se
detecta, envia un correo de notificacion.

Logica:
- El DANE publica cada mes el IPP del mes ANTERIOR (con rezago de unos
  dias). Por ejemplo, a comienzos de septiembre se publica el IPP de agosto.
- El DANE ha usado distintos patrones de nombre de archivo a lo largo de
  los anios, y a veces agrega una subcarpeta por mes. Por eso este script
  prueba varias URLs candidatas y usa la primera que responda.
- Se guarda en Estado/estado_ipp.json cual fue el ultimo mes ya notificado,
  para no enviar el correo mas de una vez por mes.
"""

import json
import smtplib
from email.mime.text import MIMEText
from pathlib import Path
from zoneinfo import ZoneInfo
import datetime
import os

import requests
from dotenv import load_dotenv

load_dotenv()

ARCHIVO_ESTADO = Path("Estado/estado_ipp.json")

MESES_ABREV = {
    1: "ene", 2: "feb", 3: "mar", 4: "abr", 5: "may", 6: "jun",
    7: "jul", 8: "ago", 9: "sep", 10: "oct", 11: "nov", 12: "dic",
}

NOMBRES_MESES = {
    1: "enero", 2: "febrero", 3: "marzo", 4: "abril", 5: "mayo", 6: "junio",
    7: "julio", 8: "agosto", 9: "septiembre", 10: "octubre",
    11: "noviembre", 12: "diciembre",
}


def mes_objetivo() -> tuple[int, int]:
    """Devuelve (anio, mes) del IPP que deberia estar saliendo ahora
    (el mes inmediatamente anterior al mes actual, hora Colombia)."""
    hoy = datetime.datetime.now(ZoneInfo("America/Bogota")).date()
    primer_dia_mes_actual = hoy.replace(day=1)
    ultimo_dia_mes_anterior = primer_dia_mes_actual - datetime.timedelta(days=1)
    return ultimo_dia_mes_anterior.year, ultimo_dia_mes_anterior.month


def urls_candidatas(anio: int, mes: int) -> list[str]:
    """Genera varias URLs posibles, porque el DANE ha cambiado el patron
    de nombres de archivo con el tiempo. Se prueban de la mas reciente
    conocida a la mas antigua."""
    abrev = MESES_ABREV[mes]
    aa = str(anio)[-2:]
    mes_anio = f"{abrev}{anio}"  # ej: ago2026

    return [
        # Patron 2026 (con subcarpeta por mes, visto en IPC)
        f"https://www.dane.gov.co/files/operaciones/IPP/{mes_anio}/bol-IPP-{mes_anio}.pdf",
        # Patron 2023-2025 (sin subcarpeta)
        f"https://www.dane.gov.co/files/operaciones/IPP/bol-IPP-{mes_anio}.pdf",
        # Patron antiguo 2021-2022
        f"https://www.dane.gov.co/files/investigaciones/boletines/ipp/bol_ipp_{abrev}{aa}.pdf",
    ]


def cargar_estado() -> dict:
    if ARCHIVO_ESTADO.exists():
        return json.loads(ARCHIVO_ESTADO.read_text(encoding="utf-8"))
    return {"ultimo_mes_notificado": None}


def guardar_estado(estado: dict) -> None:
    ARCHIVO_ESTADO.parent.mkdir(parents=True, exist_ok=True)
    ARCHIVO_ESTADO.write_text(json.dumps(estado, ensure_ascii=False, indent=2), encoding="utf-8")


def url_publicada(url: str) -> bool:
    try:
        resp = requests.head(url, timeout=15, allow_redirects=True)
        if resp.status_code == 200:
            return True
        # Algunos servidores no responden bien a HEAD, se intenta con GET
        resp = requests.get(url, timeout=15, stream=True)
        return resp.status_code == 200
    except requests.RequestException:
        return False


def buscar_boletin_publicado(anio: int, mes: int) -> str | None:
    for url in urls_candidatas(anio, mes):
        print(f"Revisando: {url}")
        if url_publicada(url):
            return url
    return None


def enviar_correo(anio: int, mes: int, url: str) -> None:
    remitente = os.getenv("CORREO_REMITENTE")
    contrasena = os.getenv("CORREO_CONTRASENA_APP")
    destino = "nicol.leyton@tmmorro.com"

    nombre_mes = NOMBRES_MESES[mes]
    asunto = f"DANE publico el IPP provisional de {nombre_mes} {anio}"
    cuerpo = (
        f"El DANE ya publico el boletin del Indice de Precios del Productor (IPP) "
        f"provisional de {nombre_mes} de {anio}.\n\n"
        f"Puedes descargarlo aqui:\n{url}\n"
    )

    mensaje = MIMEText(cuerpo, "plain", "utf-8")
    mensaje["Subject"] = asunto
    mensaje["From"] = remitente
    mensaje["To"] = destino

    with smtplib.SMTP("smtp.gmail.com", 587) as servidor:
        servidor.starttls()
        servidor.login(remitente, contrasena)
        servidor.sendmail(remitente, [destino], mensaje.as_string())


def main() -> None:
    anio, mes = mes_objetivo()
    clave_mes = f"{anio}-{mes:02d}"
    estado = cargar_estado()

    if estado.get("ultimo_mes_notificado") == clave_mes:
        print(f"El IPP de {clave_mes} ya fue notificado antes. No se hace nada.")
        return

    url_encontrada = buscar_boletin_publicado(anio, mes)

    if url_encontrada:
        print(f"¡Boletin encontrado en {url_encontrada}! Enviando correo...")
        enviar_correo(anio, mes, url_encontrada)
        estado["ultimo_mes_notificado"] = clave_mes
        guardar_estado(estado)
        print("Correo enviado y estado actualizado.")
    else:
        print(f"El IPP de {clave_mes} todavia no ha sido publicado (o cambio de URL otra vez).")


if __name__ == "__main__":
    main()
