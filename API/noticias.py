"""
Modulo: noticias.py
Ubicacion: API/noticias.py

Recopila titulares y enlaces de noticias recientes (ultimos 7 dias)
relacionadas con el mercado electrico colombiano, usando el buscador
de noticias de Google (a traves de su formato RSS publico y gratuito,
sin necesidad de ninguna llave de acceso).

IMPORTANTE: este modulo NO usa inteligencia artificial ni genera
ninguna interpretacion de las noticias. Solo recopila titulares y
enlaces reales, para que la persona que lea el informe pueda
revisarlos por su cuenta. Esto evita cualquier costo de uso de APIs
de pago, y tambien evita copiar el contenido de las noticias
(solo se muestra el titulo, que es informacion publica, y el enlace
a la fuente original).
"""

import requests
import xml.etree.ElementTree as ET
import sys
import os
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime

CARPETA_PROYECTO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(CARPETA_PROYECTO, "BaseDatos"))

from base_datos import guardar_noticias, consultar_noticias_recientes

URL_BASE_GOOGLE_NEWS = "https://news.google.com/rss/search"

# Busquedas relacionadas con los temas que pide la especificacion:
# precio de bolsa, embalses, aportes, generacion termica, regulacion.
BUSQUEDAS = [
    "precio de bolsa energia Colombia XM",
    "embalses hidrologia Colombia energia",
    "generacion termica Colombia energia",
    "CREG regulacion energia Colombia",
    "UPME energia Colombia",
]

DIAS_HACIA_ATRAS = 7
ENCABEZADOS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}


def _buscar_noticias_de_una_consulta(consulta):
    """
    Busca noticias recientes para una consulta especifica, usando
    el RSS de busqueda de Google News.

    Retorna:
        Una lista de diccionarios con "titulo", "enlace", "fecha",
        y "fuente".
    """
    parametros = {
        "q": consulta,
        "hl": "es-419",
        "gl": "CO",
        "ceid": "CO:es"
    }

    resultados = []

    try:
        respuesta = requests.get(URL_BASE_GOOGLE_NEWS, params=parametros, headers=ENCABEZADOS, timeout=30)

        if respuesta.status_code != 200:
            print("  Error consultando '" + consulta + "': codigo " + str(respuesta.status_code))
            return resultados

        raiz = ET.fromstring(respuesta.content)

        fecha_limite = datetime.now(tz=None).astimezone() - timedelta(days=DIAS_HACIA_ATRAS)

        for item in raiz.findall(".//item"):
            titulo = item.findtext("title", default="")
            enlace = item.findtext("link", default="")
            fecha_texto = item.findtext("pubDate", default="")
            fuente_elemento = item.find("source")
            fuente = fuente_elemento.text if fuente_elemento is not None else "Desconocida"

            try:
                fecha_publicacion = parsedate_to_datetime(fecha_texto)
            except Exception:
                continue

            if fecha_publicacion >= fecha_limite:
                resultados.append({
                    "titulo": titulo,
                    "enlace": enlace,
                    "fecha": fecha_publicacion.strftime("%Y-%m-%d"),
                    "fuente": fuente
                })

    except Exception as error:
        print("  Error consultando '" + consulta + "': " + str(error))

    return resultados


def recopilar_noticias():
    """
    Recopila noticias de todas las busquedas definidas, elimina
    duplicados (una misma noticia puede aparecer en varias
    busquedas), y las guarda en la base de datos.

    Retorna:
        La lista final de noticias recopiladas.
    """
    todas_las_noticias = []
    enlaces_ya_vistos = set()

    for consulta in BUSQUEDAS:
        print("Buscando: " + consulta + "...")
        resultados = _buscar_noticias_de_una_consulta(consulta)

        for noticia in resultados:
            if noticia["enlace"] not in enlaces_ya_vistos:
                enlaces_ya_vistos.add(noticia["enlace"])
                todas_las_noticias.append(noticia)

    print("")
    print("Total de noticias unicas encontradas: " + str(len(todas_las_noticias)))

    guardar_noticias(todas_las_noticias)

    return todas_las_noticias


if __name__ == "__main__":
    noticias = recopilar_noticias()

    print("")
    for noticia in noticias:
        print("- [" + noticia["fecha"] + "] " + noticia["titulo"] + " (" + noticia["fuente"] + ")")
        print("  " + noticia["enlace"])
