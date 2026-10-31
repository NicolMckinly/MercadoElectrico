"""
Archivo: main_graficos_a_pedido.py
Ubicacion: raiz del proyecto

Genera, CUANDO SE PIDA, los graficos del Precio de Bolsa de los meses
que se indiquen y los envia por correo como imagenes (.png).
No corre solo: se ejecuta a mano (o con el boton "Run workflow" de
GitHub, ver .github/workflows/graficos_a_pedido.yml).

Como indicar los meses (formato AAAA-MM):
    Un mes ............... 2026-09
    Varios meses ......... 2026-07, 2026-09, 2025-09
    Un rango ............. 2026-07 a 2026-09   (tambien 2026-07:2026-09)
    Mezclado ............. 2026-01 a 2026-03, 2025-09

Que llega en el correo (imagenes adjuntas):
    - Una imagen por mes (TX1 + IMAR + Precio de Escasez).
    - Si se piden 2 o mas meses SEGUIDOS, ademas una imagen con todo el
      periodo en una sola linea de tiempo (mismo estilo).
    - Si son meses sueltos (ej. 2025-09 y 2026-09), una comparativa.

Uso desde la terminal:
    python main_graficos_a_pedido.py "2026-09"
    python main_graficos_a_pedido.py "2026-07 a 2026-09"
    python main_graficos_a_pedido.py "2026-09" --sin-correo
    python main_graficos_a_pedido.py "2026-09" --correo otra.persona@empresa.com
"""

import sys
import os
import re
import shutil
import argparse


CARPETA_PROYECTO = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(CARPETA_PROYECTO, "BaseDatos"))
sys.path.append(os.path.join(CARPETA_PROYECTO, "Analisis"))
sys.path.append(os.path.join(CARPETA_PROYECTO, "Graficas"))
sys.path.append(os.path.join(CARPETA_PROYECTO, "Correos"))

from grafico_mes_especifico import (
    generar_grafico_mes, generar_grafico_comparativo, generar_grafico_periodo,
    _meses_son_seguidos, MESES_EN_ESPANOL
)
from zona_horaria import ahora_colombia

# Carpeta de trabajo: se vacia en cada ejecucion y esta en .gitignore,
# para que estos archivos nunca se acumulen ni se suban a GitHub.
CARPETA_SALIDA = os.path.join(CARPETA_PROYECTO, "GraficosAPedido")

MAXIMO_MESES = 24


def interpretar_meses(texto):
    """
    Convierte el texto pedido (ej. "2026-07 a 2026-09, 2025-09") en una
    lista ordenada y sin repetidos de tuplas (anio, mes).

    Lanza ValueError con un mensaje claro si algo no se entiende.
    """
    meses = set()
    partes = [p.strip() for p in re.split(r"[,;\n]+", texto) if p.strip()]
    if len(partes) == 0:
        raise ValueError("No se indico ningun mes. Ejemplo: 2026-09")

    for parte in partes:
        extremos = re.split(r"\s*(?::|\ba\b|\bal\b|\bhasta\b)\s*", parte)
        extremos = [e for e in extremos if e]
        if len(extremos) == 1:
            meses.add(_leer_mes(extremos[0]))
        elif len(extremos) == 2:
            desde, hasta = _leer_mes(extremos[0]), _leer_mes(extremos[1])
            if desde > hasta:
                desde, hasta = hasta, desde
            anio, mes = desde
            while (anio, mes) <= hasta:
                meses.add((anio, mes))
                anio, mes = (anio, mes + 1) if mes < 12 else (anio + 1, 1)
        else:
            raise ValueError("No entendi '" + parte + "'. Ejemplo de rango: 2026-07 a 2026-09")

    hoy = ahora_colombia()
    futuros = [m for m in meses if m > (hoy.year, hoy.month)]
    if futuros:
        raise ValueError("Se pidieron meses que aun no han llegado: "
                         + ", ".join("%04d-%02d" % m for m in sorted(futuros)))

    if len(meses) > MAXIMO_MESES:
        raise ValueError("Se pidieron " + str(len(meses)) + " meses; el maximo es " + str(MAXIMO_MESES) + ".")

    return sorted(meses)


def _leer_mes(texto):
    coincidencia = re.fullmatch(r"(\d{4})[-/](\d{1,2})", texto.strip())
    if not coincidencia:
        raise ValueError("No entendi '" + texto + "'. Usa el formato AAAA-MM, por ejemplo 2026-09")
    anio, mes = int(coincidencia.group(1)), int(coincidencia.group(2))
    if not 1 <= mes <= 12:
        raise ValueError("El mes de '" + texto + "' no existe.")
    return anio, mes


def _nombre_mes(anio_mes):
    return MESES_EN_ESPANOL[anio_mes[1]] + " " + str(anio_mes[0])


def _descripcion_periodo(meses):
    if len(meses) == 1:
        return _nombre_mes(meses[0])
    return _nombre_mes(meses[0]) + " a " + _nombre_mes(meses[-1]) + " (" + str(len(meses)) + " meses)"


def generar_y_enviar(texto_meses, enviar=True, correo_extra=None):
    """
    Genera los graficos pedidos (imagenes .png) y, si enviar=True, los
    envia por correo como adjuntos.

    Retorna:
        La lista de imagenes generadas, o None si ningun mes tenia datos.
    """
    meses = interpretar_meses(texto_meses)
    print("Meses pedidos: " + ", ".join("%04d-%02d" % m for m in meses))

    if os.path.isdir(CARPETA_SALIDA):
        shutil.rmtree(CARPETA_SALIDA)
    os.makedirs(CARPETA_SALIDA)

    imagenes = []
    meses_con_datos = []
    meses_sin_datos = []

    for anio, mes in meses:
        ruta = generar_grafico_mes(anio, mes, carpeta_salida=CARPETA_SALIDA)
        if ruta is None:
            meses_sin_datos.append((anio, mes))
        else:
            meses_con_datos.append((anio, mes))
            imagenes.append(ruta)

    if len(meses_con_datos) == 0:
        print("Ninguno de los meses pedidos tiene datos en la base. No se envia nada.")
        return None

    # Si son varios meses: seguidos -> una sola linea de tiempo;
    # no seguidos (ej. sep 2025 y sep 2026) -> comparativo superpuesto.
    if len(meses_con_datos) > 1:
        if _meses_son_seguidos(meses_con_datos):
            ruta_conjunta = generar_grafico_periodo(meses_con_datos, carpeta_salida=CARPETA_SALIDA)
        else:
            ruta_conjunta = generar_grafico_comparativo(meses_con_datos, carpeta_salida=CARPETA_SALIDA)
        if ruta_conjunta is not None:
            imagenes.insert(0, ruta_conjunta)

    if not enviar:
        return imagenes

    cuerpo = [
        "Adjunto encontrara los graficos del Precio de Bolsa Nacional solicitados.",
        "",
        "Meses incluidos: " + ", ".join(_nombre_mes(m) for m in meses_con_datos) + ".",
    ]
    if len(meses_con_datos) > 1:
        if _meses_son_seguidos(meses_con_datos):
            cuerpo.append("La primera imagen muestra todo el periodo seguido; luego viene cada mes por separado.")
        else:
            cuerpo.append("La primera imagen compara los meses; luego viene cada mes por separado.")
    if meses_sin_datos:
        cuerpo.append("")
        cuerpo.append("Sin datos en el sistema (no incluidos): "
                      + ", ".join(_nombre_mes(m) for m in meses_sin_datos) + ".")

    from enviar_correo import enviar_informe_por_correo
    enviado = enviar_informe_por_correo(
        None,
        "Graficos Precio de Bolsa - " + _descripcion_periodo(meses_con_datos),
        "\n".join(cuerpo),
        destinatarios_extra=[correo_extra] if correo_extra else None,
        archivos_adicionales=imagenes
    )
    if not enviado:
        raise RuntimeError("Las imagenes se generaron, pero el correo no se pudo enviar (revisar credenciales).")
    return imagenes


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Graficos del Precio de Bolsa a pedido.")
    parser.add_argument("meses", help='Ej: "2026-09" o "2026-07 a 2026-09" o "2026-07, 2025-09"')
    parser.add_argument("--sin-correo", action="store_true", help="Solo genera las imagenes, no las envia.")
    parser.add_argument("--correo", default="", help="Correo adicional que tambien lo recibe.")
    argumentos = parser.parse_args()

    try:
        resultado = generar_y_enviar(
            argumentos.meses,
            enviar=not argumentos.sin_correo,
            correo_extra=argumentos.correo.strip() or None
        )
    except (ValueError, RuntimeError) as error:
        print("ERROR: " + str(error))
        sys.exit(1)

    if resultado is None:
        sys.exit(1)
