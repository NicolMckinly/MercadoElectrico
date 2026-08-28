"""
descargar_archivos.py

Entra a la página de Informes de limitación de suministro de XM,
localiza los dos archivos que necesitamos (identificándolos por texto,
no por posición, para que no se rompa si cambian el orden) y los
descarga.

NOTA para Nicol: esta es la parte que con más probabilidad necesite un
ajuste fino la primera vez que la corramos, porque la tabla de archivos
se carga con JavaScript y no puedo probarla en vivo desde aquí. Si falla,
el workflow de GitHub Actions guarda una captura de pantalla (screenshot)
como "artifact" para que la revisemos juntas y ajustemos el selector.
"""

import os
import time
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

URL_INFORMES = "https://www.xm.com.co/administraci%C3%B3n-financiera/limitaci%C3%B3n-de-suministro/informes-limitaci%C3%B3n-de-suministro"

# Texto que identifica cada archivo dentro de la tabla (no hace falta
# que sea el nombre completo, basta con un fragmento único).
ARCHIVOS_A_DESCARGAR = {
    "en_bolsa.xlsx": "Limitación de suministro en bolsa",
    "corte_usuarios.xlsx": "Limitación de suministro Res CREG 116",
}


def _crear_navegador():
    opciones = Options()
    opciones.add_argument("--headless=new")
    opciones.add_argument("--no-sandbox")
    opciones.add_argument("--disable-dev-shm-usage")
    opciones.add_argument("--window-size=1600,1200")
    return webdriver.Chrome(options=opciones)


def _obtener_enlaces_descarga(navegador):
    """
    Devuelve un diccionario {texto_visible_de_la_fila: url_descarga}
    buscando cada enlace de texto "Descargar" y mirando el texto de su
    fila para identificar a qué archivo corresponde.
    """
    espera = WebDriverWait(navegador, 30)
    espera.until(EC.presence_of_element_located((By.PARTIAL_LINK_TEXT, "Descargar")))
    # Pequeña pausa extra: a veces la tabla sigue poblándose después del
    # primer enlace visible.
    time.sleep(2)

    enlaces = navegador.find_elements(By.PARTIAL_LINK_TEXT, "Descargar")

    resultado = {}
    for enlace in enlaces:
        href = enlace.get_attribute("href")
        if not href:
            continue

        texto_fila = ""
        # Intentamos varias formas de encontrar el contenedor de la fila,
        # porque no sabemos de antemano si es una tabla <tr> o divs.
        for xpath_ancestro in ["./ancestor::tr[1]", "./ancestor::div[contains(@class,'row')][1]",
                                "./ancestor::div[1]/.."]:
            try:
                fila = enlace.find_element(By.XPATH, xpath_ancestro)
                texto_fila = fila.text
                if texto_fila.strip():
                    break
            except Exception:
                continue

        resultado[texto_fila] = href

    return resultado


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
        enlaces_por_fila = _obtener_enlaces_descarga(navegador)

        # Cookies de la sesión del navegador, por si el archivo requiere
        # la misma sesión para descargarse (normalmente no hace falta,
        # pero así queda más robusto).
        cookies = {c["name"]: c["value"] for c in navegador.get_cookies()}
        agente = navegador.execute_script("return navigator.userAgent;")

        for nombre_archivo, fragmento_busqueda in ARCHIVOS_A_DESCARGAR.items():
            url_encontrada = None
            for texto_fila, href in enlaces_por_fila.items():
                if fragmento_busqueda.lower() in texto_fila.lower():
                    url_encontrada = href
                    break

            if url_encontrada is None:
                # Guardamos una captura de pantalla para poder diagnosticar
                # por qué no se encontró el archivo.
                navegador.save_screenshot("error_no_encontrado.png")
                raise RuntimeError(
                    f"No se encontró el archivo que contiene '{fragmento_busqueda}' "
                    f"en la página. Se guardó error_no_encontrado.png para revisar."
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
