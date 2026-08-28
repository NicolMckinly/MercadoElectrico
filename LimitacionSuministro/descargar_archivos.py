"""
descargar_archivos.py

Entra a la página de Informes de limitación de suministro de XM y
descarga los dos archivos que necesitamos.

NOTA para Nicol - lo que descubrimos entre las dos:
1) La tabla de archivos es un componente Angular (explorador-archivos-
   component) que dibuja su contenido dentro de "Shadow DOM" — invisible
   para las búsquedas normales de Selenium aunque se vea perfecto en
   pantalla. Por eso buscamos con JavaScript, atravesando esas cajas.
2) El botón "Descargar" no tiene una URL fija que se pueda copiar: arma
   y dispara la descarga por JavaScript al hacer clic (como cuando tú lo
   haces a mano). Por eso, en vez de tratar de adivinar la URL, hacemos
   clic de verdad en el botón y dejamos que Chrome descargue el archivo
   a una carpeta, exactamente como si lo hicieras tú.

Si algo falla, el workflow de GitHub Actions guarda una captura de
pantalla y el HTML completo de la página como "artifacts" para revisar.
"""

import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException

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
# anidado, buscando elementos clicables (<a> o <button>) cuyo texto
# contenga "descargar". Devuelve una lista de {elemento, texto_fila}.
# Selenium convierte automáticamente los nodos DOM devueltos en objetos
# WebElement que luego podemos usar para hacer .click().
JS_BUSCAR_BOTONES_DESCARGA = """
function buscar(raiz, resultados) {
    const candidatos = raiz.querySelectorAll('a, button');
    candidatos.forEach(el => {
        const texto = (el.textContent || '').trim().toLowerCase();
        if (texto.includes('descargar')) {
            let fila = el.closest('tr') || el.closest('[class*="row"]') || el.parentElement;
            resultados.push({
                elemento: el,
                texto_fila: fila ? fila.textContent.trim() : texto
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


def _crear_navegador(carpeta_descargas):
    opciones = Options()
    opciones.add_argument("--headless=new")
    opciones.add_argument("--no-sandbox")
    opciones.add_argument("--disable-dev-shm-usage")
    opciones.add_argument("--window-size=1600,1200")
    opciones.add_argument(f"--user-agent={UA_REALISTA}")
    opciones.add_argument("--disable-blink-features=AutomationControlled")
    opciones.add_experimental_option("excludeSwitches", ["enable-automation"])
    opciones.add_experimental_option("useAutomationExtension", False)
    opciones.add_experimental_option("prefs", {
        "download.default_directory": os.path.abspath(carpeta_descargas),
        "download.prompt_for_download": False,
        "safebrowsing.enabled": True,
    })

    navegador = webdriver.Chrome(options=opciones)
    navegador.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"},
    )
    # En modo headless hay que habilitar explícitamente el permiso de descarga.
    navegador.execute_cdp_cmd("Page.setDownloadBehavior", {
        "behavior": "allow",
        "downloadPath": os.path.abspath(carpeta_descargas),
    })
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
    """Guarda screenshot + HTML de la página tal como está, para depurar."""
    try:
        navegador.save_screenshot(f"error_diagnostico{sufijo}.png")
        with open(f"error_pagina{sufijo}.html", "w", encoding="utf-8") as f:
            f.write(navegador.page_source)
    except Exception:
        pass


def _buscar_botones_descarga(navegador, tiempo_maximo=60, intervalo=2):
    """
    Pregunta repetidamente (con JavaScript) por los botones de
    "Descargar", atravesando Shadow DOM, hasta que aparezcan.
    Devuelve una lista de {"elemento": WebElement, "texto_fila": str}.
    """
    tiempo_transcurrido = 0
    while tiempo_transcurrido < tiempo_maximo:
        resultados = navegador.execute_script(JS_BUSCAR_BOTONES_DESCARGA)
        if resultados:
            return resultados
        time.sleep(intervalo)
        tiempo_transcurrido += intervalo

    _guardar_diagnostico(navegador)
    print(f"Título de la página cargada: {navegador.title}")
    print(f"URL actual: {navegador.current_url}")
    raise TimeoutException(
        f"No se encontró ningún botón 'Descargar' en {tiempo_maximo} segundos "
        f"(ni siquiera atravesando Shadow DOM)."
    )


def _esperar_archivo_descargado(carpeta, archivos_antes, tiempo_maximo=40):
    """
    Espera a que aparezca un archivo NUEVO (que no estuviera antes del
    clic) y que ya haya terminado de descargarse (Chrome usa la
    extensión .crdownload mientras está en progreso).
    Devuelve el nombre del archivo nuevo, o None si se agotó el tiempo.
    """
    tiempo_transcurrido = 0
    while tiempo_transcurrido < tiempo_maximo:
        archivos_ahora = set(os.listdir(carpeta))
        nuevos = archivos_ahora - archivos_antes
        completos = [f for f in nuevos if not f.endswith(".crdownload") and not f.endswith(".tmp")]
        if completos:
            return completos[0]
        time.sleep(1)
        tiempo_transcurrido += 1
    return None


def descargar_archivos(carpeta_destino="."):
    """
    Descarga los dos archivos haciendo clic real en los botones de la
    página, y los deja en carpeta_destino con los nombres definidos en
    ARCHIVOS_A_DESCARGAR.
    Devuelve un diccionario {nombre_archivo: ruta_completa}.
    """
    os.makedirs(carpeta_destino, exist_ok=True)
    navegador = _crear_navegador(carpeta_destino)
    rutas_guardadas = {}

    try:
        navegador.get(URL_INFORMES)
        time.sleep(3)
        _cerrar_popup_si_aparece(navegador)

        for nombre_archivo, fragmento_busqueda in ARCHIVOS_A_DESCARGAR.items():
            # Volvemos a buscar los botones cada vez (por si la página
            # se re-renderizó después del clic anterior y las
            # referencias viejas ya no sirven).
            botones = _buscar_botones_descarga(navegador)

            candidato = None
            for item in botones:
                if fragmento_busqueda.lower() in item["texto_fila"].lower():
                    candidato = item["elemento"]
                    break

            if candidato is None:
                _guardar_diagnostico(navegador, sufijo="_no_encontrado")
                print("Filas detectadas en la página:")
                for item in botones:
                    print(f"  - {item['texto_fila']!r}")
                raise RuntimeError(
                    f"No se encontró el botón de descarga para '{fragmento_busqueda}'. "
                    f"Se guardó error_diagnostico_no_encontrado.png/.html para revisar."
                )

            archivos_antes = set(os.listdir(carpeta_destino))

            try:
                candidato.click()
            except StaleElementReferenceException:
                # La página cambió justo antes del clic: reintentamos una vez.
                botones = _buscar_botones_descarga(navegador)
                candidato = next(
                    (item["elemento"] for item in botones
                     if fragmento_busqueda.lower() in item["texto_fila"].lower()),
                    None,
                )
                if candidato is None:
                    raise RuntimeError(f"No se pudo re-encontrar el botón para '{fragmento_busqueda}'.")
                candidato.click()

            nombre_descargado = _esperar_archivo_descargado(carpeta_destino, archivos_antes)
            if nombre_descargado is None:
                _guardar_diagnostico(navegador, sufijo="_sin_descarga")
                raise RuntimeError(
                    f"Se hizo clic en 'Descargar' para '{fragmento_busqueda}' pero no apareció "
                    f"ningún archivo nuevo en {carpeta_destino} después de 40 segundos."
                )

            ruta_final = os.path.join(carpeta_destino, nombre_archivo)
            os.replace(os.path.join(carpeta_destino, nombre_descargado), ruta_final)
            rutas_guardadas[nombre_archivo] = ruta_final

    finally:
        navegador.quit()

    return rutas_guardadas


if __name__ == "__main__":
    rutas = descargar_archivos()
    for nombre, ruta in rutas.items():
        print(f"Descargado: {nombre} -> {ruta}")
