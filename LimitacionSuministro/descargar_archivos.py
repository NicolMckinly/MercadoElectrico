"""
descargar_archivos.py

Entra a la página de Informes de limitación de suministro de XM,
localiza los dos archivos que necesitamos (identificándolos por texto,
no por posición, para que no se rompa si cambian el orden) y los
descarga.

NOTA para Nicol: la tabla de archivos de esa página no es HTML normal,
es un componente Angular (explorador-archivos-component) que dibuja su
contenido dentro de un "Shadow DOM" — una especie de caja aparte dentro
de la página, invisible para las búsquedas normales de Selenium aunque
se vea perfecto en pantalla. Por eso usamos JavaScript para buscar
"atravesando" esas cajas en vez del buscador normal de Selenium.

Si algo falla, el workflow de GitHub Actions guarda una captura de
pantalla y el HTML completo de la página como "artifacts" para revisar.
"""

import os
import time
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

URL_INFORMES = "https://www.xm.com.co/administraci%C3%B3n-financiera/limitaci%C3%B3n-de-suministro/informes-limitaci%C3%B3n-de-suministro"

# Texto que identifica cada archivo dentro de la tabla (no hace falta
# que sea el nombre completo, basta con un fragmento único).
ARCHIVOS_A_DESCARGAR = {
    "en_bolsa.xlsx": "Limitación de suministro en bolsa",
    "corte_usuarios.xlsx": "Limitación de suministro Res CREG 116",
}

UA_REALISTA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)

# Script que recorre TODO el documento, incluyendo cualquier Shadow DOM
# anidado (sin importar cuántos niveles), buscando enlaces <a> cuyo
# texto contenga "descargar". Devuelve una lista de {href, texto_fila}.
JS_BUSCAR_ENLACES_DESCARGA = """
function buscar(raiz, resultados) {
    const anclas = raiz.querySelectorAll('a');
    anclas.forEach(a => {
        const texto = (a.textContent || '').trim().toLowerCase();
        if (texto.includes('descargar') && a.href) {
            let fila = a.closest('tr') || a.closest('[class*="row"]') || a.parentElement;
            resultados.push({
                href: a.href,
                texto_fila: fila ? fila.textContent.trim() : a.textContent.trim()
            });
        }
    });
    const todos = raiz.querySelectorAll('*');
    todos.forEach(el => {
        if (el.shadowRoot) {
            buscar(el.shadowRoot, resultados);
        }
    });
}
const resultados = [];
buscar(document, resultados);
return resultados;
"""


def _crear_navegador():
    opciones = Options()
    opciones.add_argument("--headless=new")
    opciones.add_argument("--no-sandbox")
    opciones.add_argument("--disable-dev-shm-usage")
    opciones.add_argument("--window-size=1600,1200")
    opciones.add_argument(f"--user-agent={UA_REALISTA}")
    opciones.add_argument("--disable-blink-features=AutomationControlled")
    opciones.add_experimental_option("excludeSwitches", ["enable-automation"])
    opciones.add_experimental_option("useAutomationExtension", False)

    navegador = webdriver.Chrome(options=opciones)
    navegador.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"},
    )
    return navegador


def _cerrar_popup_si_aparece(navegador):
    """Cierra el aviso 'Antes de continuar... navegador diferente' si sale."""
    try:
        boton = WebDriverWait(navegador, 5).until(
            EC.element_to_be_clickable((By.XPATH, "//*[self::button or self::a][contains(text(),'Entendido')]"))
        )
        boton.click()
        time.sleep(1)
    except (TimeoutException, NoSuchElementException):
        pass  # no salió el popup, seguimos normal


def _guardar_diagnostico(navegador, sufijo=""):
    """Guarda screenshot + HTML de la página tal como está en ese momento, para depurar."""
    try:
        navegador.save_screenshot(f"error_diagnostico{sufijo}.png")
        with open(f"error_pagina{sufijo}.html", "w", encoding="utf-8") as f:
            f.write(navegador.page_source)
    except Exception:
        pass


def _obtener_enlaces_descarga(navegador, tiempo_maximo=60, intervalo=2):
    """
    Va preguntándole a la página (con JavaScript) por los enlaces de
    "Descargar", atravesando cualquier Shadow DOM, hasta que aparezcan
    o se agote el tiempo máximo.

    Devuelve un diccionario {texto_visible_de_la_fila: url_descarga}.
    """
    tiempo_transcurrido = 0
    while tiempo_transcurrido < tiempo_maximo:
        resultados = navegador.execute_script(JS_BUSCAR_ENLACES_DESCARGA)
        if resultados:
            return {r["texto_fila"]: r["href"] for r in resultados}
        time.sleep(intervalo)
        tiempo_transcurrido += intervalo

    # No apareció nada en el tiempo máximo: guardamos diagnóstico.
    _guardar_diagnostico(navegador)
    print(f"Título de la página cargada: {navegador.title}")
    print(f"URL actual: {navegador.current_url}")
    raise TimeoutException(
        f"No se encontró ningún enlace 'Descargar' en {tiempo_maximo} segundos "
        f"(ni siquiera atravesando Shadow DOM)."
    )


def descargar_archivos(carpeta_destino="."):
    """
    Descarga los dos archivos y los guarda en carpeta_destino con los
    nombres definidos en ARCHIVOS_A_DESCARGAR.
    Devuelve un diccionario {nombre_archivo: ruta_completa}.
    """
    navegador = _crear_navegador()
    rutas_guardadas = {}

    try:
        navegador.get(URL_INFORMES)
        time.sleep(3)  # deja tiempo a que arranque el JS de la página
        _cerrar_popup_si_aparece(navegador)

        enlaces_por_fila = _obtener_enlaces_descarga(navegador)

        cookies = {c["name"]: c["value"] for c in navegador.get_cookies()}
        agente = navegador.execute_script("return navigator.userAgent;")

        for nombre_archivo, fragmento_busqueda in ARCHIVOS_A_DESCARGAR.items():
            url_encontrada = None
            for texto_fila, href in enlaces_por_fila.items():
                if fragmento_busqueda.lower() in texto_fila.lower():
                    url_encontrada = href
                    break

            if url_encontrada is None:
                _guardar_diagnostico(navegador, sufijo="_no_encontrado")
                print("Filas de archivo detectadas en la página:")
                for texto_fila in enlaces_por_fila:
                    print(f"  - {texto_fila!r}")
                raise RuntimeError(
                    f"No se encontró el archivo que contiene '{fragmento_busqueda}' "
                    f"en la página. Se guardó error_diagnostico_no_encontrado.png/.html para revisar."
                )

            ruta_destino = os.path.join(carpeta_destino, nombre_archivo)
            respuesta = requests.get(
                url_encontrada,
                cookies=cookies,
                headers={"User-Agent": agente},
                timeout=60,
            )
            respuesta.raise_for_status()
            with open(ruta_destino, "wb") as f:
                f.write(respuesta.content)

            rutas_guardadas[nombre_archivo] = ruta_destino

    finally:
        navegador.quit()

    return rutas_guardadas


if __name__ == "__main__":
    rutas = descargar_archivos()
    for nombre, ruta in rutas.items():
        print(f"Descargado: {nombre} -> {ruta}")
