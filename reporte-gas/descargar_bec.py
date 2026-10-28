# =====================================================================
# descargar_bec.py  —  EL ROBOT QUE VA POR LOS DATOS AL BEC
# ---------------------------------------------------------------------
# Hace exactamente lo mismo que tú haces a mano, pero solo, y para DOS
# tableros: el del mercado primario y el del mercado secundario.
#
# MERCADO PRIMARIO
#   1. Abre la página "Información de Suministro" (primario).
#   2. Encuentra el tablero de Power BI y trabaja dentro de él.
#   3. Hace clic en la pestaña "Puntos".
#   4. En la "Tabla de resultados": "…" → "Exportar datos" → "Exportar".
#   5. Revisa el archivo y lo guarda como datos/puntos.xlsx.
#
# MERCADO SECUNDARIO
#   Igual, pero en vez de la pestaña "Puntos" (no tiene), ESCRIBE EL RANGO
#   DE FECHAS, porque ese tablero viene configurado solo con un año.
#   Lo guarda como datos/secundario.xlsx.
#
# Si un mercado falla, el otro sigue. Al final deja una notita
# (estado_descarga.json) que dice cómo le fue con cada uno, para que el
# reporte avise si algún dato no se pudo actualizar.
#
# Usa "Playwright": una herramienta que maneja un navegador Chrome
# invisible (sin pantalla), como si un fantasma usara el mouse.
# En cada paso toma una FOTO en la carpeta capturas/.
#
# Uso:   python descargar_bec.py
# =====================================================================

import json
import os
import re
import shutil
import sys
from datetime import date
from urllib.parse import urljoin   # completa direcciones incompletas

from playwright.sync_api import sync_playwright

import config
from generar_reporte import leer_excel_bec, leer_excel_secundario

CARPETA_FOTOS = "capturas"
ARCHIVO_ESTADO = "estado_descarga.json"

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

    def __init__(self, pagina, prefijo):
        self.pagina = pagina
        self.prefijo = prefijo          # "primario" o "secundario"
        self.numero = 0
        os.makedirs(CARPETA_FOTOS, exist_ok=True)

    def tomar(self, nombre):
        self.numero += 1
        ruta = os.path.join(CARPETA_FOTOS, f"{self.prefijo}_{self.numero:02d}_{nombre}.png")
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


def rango_permitido(cajita):
    """Lee el rango de fechas que el tablero permite, si lo anuncia.

    El tablero del BEC dice, por ejemplo: "Intervalo de entrada disponible
    01/01/2024 a 28/10/2026". Si encontramos eso, devolvemos las dos fechas.
    """
    texto = cajita.get_attribute("aria-label") or ""
    fechas = re.findall(r"(\d{1,2})/(\d{1,2})/(\d{4})", texto)
    if len(fechas) >= 2:
        (d1, m1, a1), (d2, m2, a2) = fechas[-2], fechas[-1]
        return date(int(a1), int(m1), int(d1)), date(int(a2), int(m2), int(d2))
    return None


def poner_fechas(pagina, tablero, foto, desde, hasta):
    """Escribe el rango de fechas en las dos cajitas del tablero.

    Lecciones aprendidas en la primera prueba real:
      - Al presionar Enter se abre un CALENDARIO que tapa la otra cajita.
        Por eso cerramos el calendario con la tecla Escape.
      - No hacemos clic en las cajitas: escribimos directamente en ellas
        (así nada que esté encima nos estorba).
      - Respetamos el rango que el tablero permite.
    """
    patron_fecha = re.compile(r"^\d{1,2}/\d{1,2}/\d{4}$")
    cajitas = []
    for _ in range(30):                       # esperamos hasta ~30 s a que aparezcan
        # Primero buscamos las cajitas por su nombre interno de Power BI;
        # si no, cualquier cajita que tenga una fecha escrita.
        cajitas = [c for c in tablero.locator("input.date-slicer-input").all() if c.is_visible()]
        if len(cajitas) < 2:
            cajitas = [c for c in tablero.locator("input").all()
                       if c.is_visible() and patron_fecha.match((c.input_value() or "").strip())]
        if len(cajitas) >= 2:
            break
        pagina.wait_for_timeout(1_000)
    if len(cajitas) < 2:
        raise RuntimeError("No encontré las dos cajitas del rango de fechas.")

    # Ajustamos las fechas al rango que permite el tablero.
    permitido = rango_permitido(cajitas[1]) or rango_permitido(cajitas[0])
    if permitido:
        desde, hasta = max(desde, permitido[0]), min(hasta, permitido[1])
        print(f"   el tablero permite de {permitido[0]:%d/%m/%Y} a {permitido[1]:%d/%m/%Y}")

    for cajita, fecha in ((cajitas[0], desde), (cajitas[1], hasta)):
        cerrar_ventanitas(pagina, tablero)    # por si quedó un calendario abierto
        cajita.fill(f"{fecha:%d/%m/%Y}")      # escribe sin hacer clic
        cajita.press("Enter")
        pagina.wait_for_timeout(1_500)
        cerrar_ventanitas(pagina, tablero)    # cierra el calendario que se abre
    pagina.wait_for_timeout(6_000)            # tiempo para que el tablero se actualice
    print(f"   fechas pedidas: {desde:%d/%m/%Y} a {hasta:%d/%m/%Y} "
          f"(el tablero muestra: {cajitas[0].input_value()} a {cajitas[1].input_value()})")
    foto.tomar("fechas_puestas")


def cerrar_ventanitas(pagina, tablero):
    """Cierra cualquier ventanita emergente (como el calendario) que quedó abierta.

    Power BI deja un "vidrio" transparente encima de todo mientras una
    ventanita está abierta (se llama cdk-overlay-backdrop). No se ve, pero no
    deja tocar nada. Lo quitamos probando, en orden:
      1. hacer clic en el vidrio (como hacer clic "afuera" de un menú);
      2. presionar Escape;
      3. si sigue ahí, quitarlo a la fuerza (solo en el navegador del robot).
    """
    vidrio = tablero.locator(".cdk-overlay-backdrop")
    for intento in range(4):
        visibles = [v for v in vidrio.all() if v.is_visible()]
        if not visibles:
            return
        try:
            visibles[-1].click(timeout=3_000, force=True)
        except Exception:
            pass
        pagina.wait_for_timeout(700)
        pagina.keyboard.press("Escape")
        pagina.wait_for_timeout(700)
    # Último recurso: quitar el vidrio y las ventanitas a la fuerza.
    if any(v.is_visible() for v in vidrio.all()):
        print("   (quito a la fuerza una ventanita que no se quería cerrar)")
        vidrio.first.evaluate(
            "v => document.querySelectorAll('.cdk-overlay-backdrop, .cdk-overlay-pane')"
            ".forEach(e => e.remove())")
        pagina.wait_for_timeout(700)


def esconder_menu_del_bec(pagina):
    """Esconde el menú de arriba de la página del BEC.

    Ese menú se queda "flotando" y a veces tapa partes del tablero cuando
    el robot baja por la página. Lo escondemos solo en el navegador del
    robot; la página real no cambia.
    """
    try:
        pagina.add_style_tag(content="nav.navbar, .navbar__bar { display: none !important; }")
    except Exception:
        pass


def abrir_menu_de_la_tabla(pagina, tablero, foto):
    """Pasa el mouse sobre la Tabla de resultados y abre su menú "…"."""
    cerrar_ventanitas(pagina, tablero)       # que nada tape la tabla
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


def exportar(pagina, tablero, foto, ruta_temporal):
    """Hace clic en "Exportar datos" y luego en el botón "Exportar"."""
    tablero.get_by_text(TEXTO_EXPORTAR_DATOS).first.click(timeout=ESPERA_CORTA)
    pagina.wait_for_timeout(2_000)
    foto.tomar("ventana_exportar")

    # "expect_download" significa: "prepárate, va a llegar un archivo".
    with pagina.expect_download(timeout=ESPERA_LARGA) as descarga:
        tablero.get_by_role("button", name=TEXTO_BOTON_EXPORTAR).last.click(timeout=ESPERA_CORTA)
    descarga.value.save_as(ruta_temporal)
    print(f"   archivo descargado: {descarga.value.suggested_filename}")


def revisar_primario(ruta):
    """Comprueba que el archivo del PRIMARIO sea el correcto ANTES de usarlo.

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


def revisar_secundario(ruta):
    """Comprueba que el archivo del SECUNDARIO sea el correcto."""
    tabla = leer_excel_secundario(ruta)
    meses = tabla["mes"].nunique()
    if len(tabla) < 100:
        raise RuntimeError(f"El archivo tiene muy pocas filas ({len(tabla)}).")
    if meses < 6:
        raise RuntimeError(f"El archivo solo trae {meses} meses; parece que las fechas no se pusieron bien.")
    print(f"   archivo revisado: {len(tabla)} filas, {tabla['punto'].nunique()} puntos, "
          f"meses de {tabla['mes'].min()} a {tabla['mes'].max()}")


# Las "fichas" de cada mercado: qué página abrir, qué hacer y dónde guardar.
hoy = date.today()
MERCADOS = [
    {"nombre": "primario", "url": config.URL_BEC_SUMINISTRO,
     "pestana_puntos": True, "fechas": None,
     "destino": os.path.join(config.CARPETA_DATOS, "puntos.xlsx"),
     "revisar": revisar_primario},
    {"nombre": "secundario", "url": config.URL_BEC_SECUNDARIO,
     "pestana_puntos": False,
     # Desde el 1 de enero de hace dos años hasta hoy (suficiente para
     # comparar con el año anterior y dibujar 13 meses).
     "fechas": (date(hoy.year - 2, 1, 1), hoy),
     "destino": os.path.join(config.CARPETA_DATOS, "secundario.xlsx"),
     "revisar": revisar_secundario},
]


def descargar_mercado(navegador, ficha):
    """Hace todos los pasos para UN mercado. Devuelve True si salió bien."""
    nombre = ficha["nombre"]
    temporal = f"descarga_{nombre}.xlsx"
    print(f"\n=== MERCADO {nombre.upper()} ===")
    contexto = navegador.new_context(locale="es-CO", accept_downloads=True,
                                     viewport={"width": 1600, "height": 1000})
    pagina = contexto.new_page()
    foto = Foto(pagina, nombre)
    try:
        print("1. Abriendo la página del BEC...")
        pagina.goto(ficha["url"], timeout=ESPERA_LARGA)
        esconder_menu_del_bec(pagina)
        foto.tomar("pagina_bec")

        print("2. Buscando el tablero de Power BI...")
        tablero = abrir_tablero(pagina, foto)

        if ficha["pestana_puntos"]:
            print("3. Entrando a la pestaña Puntos...")
            ir_a_pestana_puntos(pagina, tablero, foto)
        if ficha["fechas"]:
            print("3. Escribiendo el rango de fechas...")
            poner_fechas(pagina, tablero, foto, *ficha["fechas"])

        print("4. Abriendo el menú de la tabla...")
        abrir_menu_de_la_tabla(pagina, tablero, foto)

        print("5. Exportando los datos...")
        exportar(pagina, tablero, foto, temporal)
    except Exception as error:
        foto.tomar("ERROR")
        print(f"EL ROBOT SE PERDIÓ en el mercado {nombre}: {error}")
        print("Revisa las fotos de la carpeta capturas/ para ver dónde.")
        return False
    finally:
        contexto.close()

    print("6. Revisando el archivo...")
    try:
        ficha["revisar"](temporal)
    except Exception as error:
        print(f"EL ARCHIVO NO SIRVE: {error} Conservo los datos anteriores.")
        return False
    os.makedirs(config.CARPETA_DATOS, exist_ok=True)
    shutil.move(temporal, ficha["destino"])
    print(f"¡Listo! Datos nuevos guardados en {ficha['destino']}")
    return True


def main():
    print("ROBOT: voy por los datos al BEC...")
    estado = {}
    with sync_playwright() as p:
        navegador = p.chromium.launch()
        for ficha in MERCADOS:
            salio_bien = descargar_mercado(navegador, ficha)
            estado[ficha["nombre"]] = "ok" if salio_bien else "fallo"
        navegador.close()

    # La notita para el reporte.
    with open(ARCHIVO_ESTADO, "w", encoding="utf-8") as archivo:
        json.dump(estado, archivo)
    print(f"\nRESUMEN: {estado}")
    if "fallo" in estado.values():
        sys.exit(1)        # avisa a GitHub que algo falló (el reporte sale igual)


if __name__ == "__main__":
    main()
