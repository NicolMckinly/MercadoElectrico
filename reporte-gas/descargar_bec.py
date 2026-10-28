# =====================================================================
# descargar_bec.py  —  EL ROBOT QUE VA POR LOS DATOS AL BEC
# ---------------------------------------------------------------------
# Hace exactamente lo mismo que tú haces a mano, pero solo:
#   1. Abre la página "Información de Suministro" del BEC.
#   2. Encuentra el tablero de Power BI que está "pegado" en la página
#      y trabaja dentro de él (o lo abre aparte si hace falta).
#   3. Hace clic en la pestaña "Puntos".
#   4. Pasa el mouse sobre la "Tabla de resultados", hace clic en "…"
#      y luego en "Exportar datos".
#   5. Revisa que el archivo descargado esté bien y lo guarda como
#      datos/puntos.xlsx (reemplazando el anterior).
#
# Usa "Playwright": una herramienta que maneja un navegador Chrome
# invisible (sin pantalla), como si un fantasma usara el mouse.
#
# En cada paso toma una FOTO (captura de pantalla) en la carpeta capturas/.
# Si algo sale mal, esas fotos muestran dónde se perdió el robot.
#
# Uso:   python descargar_bec.py
# =====================================================================

import os
import re
import shutil
import sys
from urllib.parse import urljoin   # completa direcciones incompletas

from playwright.sync_api import sync_playwright

import config
from generar_reporte import leer_excel_bec

CARPETA_FOTOS = "capturas"
ARCHIVO_DESTINO = os.path.join(config.CARPETA_DATOS, "puntos.xlsx")
ARCHIVO_TEMPORAL = "descarga_temporal.xlsx"

# Tiempos de espera, en milisegundos (1000 = 1 segundo). Power BI es lento
# para cargar, así que le damos bastante paciencia.
ESPERA_LARGA = 120_000
ESPERA_CORTA = 15_000

# Textos que busca el robot. Usamos "expresiones regulares" (re.compile):
# son como un molde que acepta varias formas de escribir lo mismo. Así
# funciona aunque Power BI salga en español o en inglés.
TEXTO_MAS_OPCIONES = re.compile(r"más opciones|more options", re.IGNORECASE)
TEXTO_EXPORTAR_DATOS = re.compile(r"exportar datos|export data", re.IGNORECASE)
TEXTO_BOTON_EXPORTAR = re.compile(r"^\s*(exportar|export)\s*$", re.IGNORECASE)


class Foto:
    """Lleva la cuenta de las fotos: 01_..., 02_..., 03_..."""

    def __init__(self, pagina):
        self.pagina = pagina
        self.numero = 0
        os.makedirs(CARPETA_FOTOS, exist_ok=True)

    def tomar(self, nombre):
        self.numero += 1
        ruta = os.path.join(CARPETA_FOTOS, f"{self.numero:02d}_{nombre}.png")
        try:
            self.pagina.screenshot(path=ruta, full_page=True)
            print(f"   foto: {ruta}")
        except Exception as error:          # si la foto falla, no detenemos al robot
            print(f"   (no pude tomar la foto {nombre}: {error})")


def encontrar_tablero(pagina):
    """Busca el tablero de Power BI dentro de la página del BEC.

    El tablero no está escrito en la página: está "pegado" con un marco
    (un <iframe>), como una foto pegada en un cuaderno. Devolvemos dos cosas:
      - el marco, para trabajar DENTRO de la página del BEC (plan A);
      - su dirección, por si toca abrir el tablero aparte (plan B).
    """
    pagina.wait_for_selector("iframe", timeout=ESPERA_LARGA)
    for marco in pagina.locator("iframe").all():
        direccion = marco.get_attribute("src") or ""
        if "powerbi" in direccion.lower():
            marco.scroll_into_view_if_needed()
            # Si la dirección viene incompleta ("/reporte..."), la completamos
            # con la de la página, como poner la ciudad a una dirección.
            return marco, urljoin(pagina.url, direccion)
    raise RuntimeError("No encontré el tablero de Power BI en la página.")


def esperar_tabla(tablero, espera):
    """Espera a que aparezca el título "Tabla de resultados" en el tablero."""
    tablero.get_by_text("Tabla de resultados", exact=True).last.wait_for(timeout=espera)


def abrir_tablero(pagina, foto):
    """Deja el tablero listo para trabajar. Tiene un plan A y un plan B.

    Plan A: trabajar DENTRO de la página del BEC. Algunos tableros solo
    funcionan ahí, porque la página les da la "llave" para abrirse (como un
    control remoto que solo sirve con su televisor).
    Plan B: si el plan A no funciona, abrir el tablero aparte, en su
    propia pestaña.

    Devuelve "tablero": el lugar donde el robot buscará botones y textos.
    """
    marco, direccion = encontrar_tablero(pagina)
    tablero = marco.content_frame          # "mirar dentro del marco"
    try:
        print("   plan A: trabajar dentro de la página del BEC...")
        esperar_tabla(tablero, ESPERA_LARGA)
        foto.tomar("tablero_dentro_de_la_pagina")
        return tablero
    except Exception:
        foto.tomar("plan_A_no_funciono")
        print("   el plan A no funcionó; plan B: abrir el tablero aparte...")
    pagina.goto(direccion, timeout=ESPERA_LARGA)
    esperar_tabla(pagina, ESPERA_LARGA)
    foto.tomar("tablero_aparte")
    return pagina


def ir_a_pestana_puntos(pagina, tablero, foto):
    """Hace clic en la pestaña "Puntos" (abajo del tablero)."""
    pestana = tablero.get_by_text("Puntos", exact=True).last
    pestana.click(timeout=ESPERA_LARGA)
    # Esperamos a que la tabla muestre nombres de puntos reales (no "Nacional").
    pagina.wait_for_timeout(8_000)
    foto.tomar("pestana_puntos")


def abrir_menu_de_la_tabla(pagina, tablero, foto):
    """Pasa el mouse sobre la Tabla de resultados y abre su menú "…"."""
    titulo = tablero.get_by_text("Tabla de resultados", exact=True).last
    titulo.wait_for(timeout=ESPERA_LARGA)
    titulo.hover()                       # al pasar el mouse aparecen los botones
    pagina.wait_for_timeout(1_500)
    foto.tomar("mouse_sobre_tabla")

    # El botón "…" puede encontrarse de varias formas. Las probamos en
    # orden, como buscar unas llaves: primero en el bolsillo, luego en la
    # mesa, luego en el cajón. Usamos la primera que aparezca en pantalla.
    candidatos = [
        tablero.get_by_role("button", name=TEXTO_MAS_OPCIONES),     # por su nombre
        tablero.locator("[data-testid='visual-more-options-btn']"),  # nombres internos
        tablero.locator(".vcMenuBtn"),                               # de Power BI
        tablero.locator("button[aria-label*='opciones' i], button[aria-label*='options' i]"),
    ]
    for boton in candidatos:
        visibles = [b for b in boton.all() if b.is_visible()]
        if visibles:
            visibles[-1].click(timeout=ESPERA_CORTA)    # el último = el de la tabla
            break
    else:
        raise RuntimeError("No encontré el botón «…» (Más opciones) de la tabla.")
    pagina.wait_for_timeout(1_000)
    foto.tomar("menu_abierto")


def exportar(pagina, tablero, foto):
    """Hace clic en "Exportar datos" y luego en el botón "Exportar"."""
    tablero.get_by_text(TEXTO_EXPORTAR_DATOS).first.click(timeout=ESPERA_CORTA)
    pagina.wait_for_timeout(2_000)
    foto.tomar("ventana_exportar")

    # "expect_download" significa: "prepárate, va a llegar un archivo".
    with pagina.expect_download(timeout=ESPERA_LARGA) as descarga:
        tablero.get_by_role("button", name=TEXTO_BOTON_EXPORTAR).last.click(timeout=ESPERA_CORTA)
    descarga.value.save_as(ARCHIVO_TEMPORAL)
    print(f"   archivo descargado: {descarga.value.suggested_filename}")


def revisar_archivo(ruta):
    """Comprueba que el archivo descargado sea el correcto ANTES de usarlo.

    Es como revisar que te dieron el pedido correcto antes de irte de la
    tienda: si algo no cuadra, no reemplazamos los datos buenos que ya
    teníamos.
    """
    tabla = leer_excel_bec(ruta)
    puntos = set(tabla["punto"].astype(str))
    if len(tabla) < 100:
        raise RuntimeError(f"El archivo tiene muy pocas filas ({len(tabla)}).")
    if puntos == {"Nacional"}:
        raise RuntimeError("El archivo es de la pestaña Nacional, no de Puntos.")
    print(f"   archivo revisado: {len(tabla)} filas, {len(puntos)} puntos, "
          f"meses de {tabla['mes'].min()} a {tabla['mes'].max()}")


def main():
    print("ROBOT: voy por los datos al BEC...")
    with sync_playwright() as p:
        navegador = p.chromium.launch()
        contexto = navegador.new_context(locale="es-CO", accept_downloads=True,
                                         viewport={"width": 1600, "height": 1000})
        pagina = contexto.new_page()
        foto = Foto(pagina)
        try:
            print("1. Abriendo la página del BEC...")
            pagina.goto(config.URL_BEC_SUMINISTRO, timeout=ESPERA_LARGA)
            foto.tomar("pagina_bec")

            print("2. Buscando el tablero de Power BI...")
            tablero = abrir_tablero(pagina, foto)

            print("3. Entrando a la pestaña Puntos...")
            ir_a_pestana_puntos(pagina, tablero, foto)

            print("4. Abriendo el menú de la tabla...")
            abrir_menu_de_la_tabla(pagina, tablero, foto)

            print("5. Exportando los datos...")
            exportar(pagina, tablero, foto)
        except Exception as error:
            foto.tomar("ERROR")
            print(f"\nEL ROBOT SE PERDIÓ: {error}")
            print("Revisa las fotos de la carpeta capturas/ para ver dónde.")
            sys.exit(1)        # avisa a GitHub que este paso falló
        finally:
            navegador.close()

    print("6. Revisando el archivo...")
    try:
        revisar_archivo(ARCHIVO_TEMPORAL)
    except Exception as error:
        print(f"\nEL ARCHIVO NO SIRVE: {error} Conservo los datos anteriores.")
        sys.exit(1)

    os.makedirs(config.CARPETA_DATOS, exist_ok=True)
    shutil.move(ARCHIVO_TEMPORAL, ARCHIVO_DESTINO)
    print(f"¡Listo! Datos nuevos guardados en {ARCHIVO_DESTINO}")


if __name__ == "__main__":
    main()
