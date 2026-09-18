"""
descargar_archivos.py

Entra a la pagina de Informes de limitacion de suministro de XM,
localiza los dos archivos que necesitamos (identificandolos por texto,
no por posicion, para que no se rompa si cambian el orden) y los
descarga haciendo clic real en el boton "Descargar" (la tabla de
archivos vive dentro de Shadow DOM, por eso hay que buscarla con
JavaScript en vez de con los metodos normales de Selenium).

NOTA para Nicol: si la pagina de XM tiene una falla pasajera (por
ejemplo, responde "Service unavailable"), el script ahora espera unos
segundos y vuelve a intentar cargarla, hasta 3 veces, antes de darse
por vencido. Si aun asi falla, el workflow de GitHub Actions guarda una
captura de pantalla y el HTML completo de la pagina como "artifacts"
para que los revisemos juntas.
"""

import os
import time
import glob
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    StaleElementReferenceException,
)

URL_INFORMES = "https://www.xm.com.co/administraci%C3%B3n-financiera/limitaci%C3%B3n-de-suministro/informes-limitaci%C3%B3n-de-suministro"

# Texto que identifica cada archivo dentro de la tabla (no hace falta
# que sea el nombre completo, basta con un fragmento unico).
ARCHIVOS_A_DESCARGAR = {
    "en_bolsa.xlsx": "Limitación de suministro en bolsa",
    "corte_usuarios.xlsx": "Limitación de suministro Res CREG 116",
}

UA_REALISTA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)

# Cuantas veces reintentar cargar la pagina si viene con una falla
# pasajera (por ejemplo "Service unavailable"), y cuanto esperar entre
# un intento y el siguiente.
INTENTOS_MAXIMOS_CARGA_PAGINA = 3
ESPERA_ENTRE_INTENTOS_SEGUNDOS = 20

# Textos que, si aparecen en el titulo de la pagina, indican que XM
# tuvo una falla momentanea (no un problema de nuestro codigo).
SENIALES_DE_FALLA_PASAJERA = [
    "service unavailable",
    "503",
    "502",
    "500",
    "error",
    "no disponible",
]

# Busca, recursivamente atravesando cualquier Shadow DOM, todos los
# elementos <a> o <button> cuyo texto contenga "descargar", y devuelve
# para cada uno el elemento y el texto completo de su fila (para poder
# identificar a que archivo corresponde).
JS_BUSCAR_BOTONES_DESCARGA = """
function buscarEnRaiz(raiz, resultados) {
    const candidatos = raiz.querySelectorAll('a, button');
    candidatos.forEach(el => {
        const texto = (el.textContent || "").trim().toLowerCase();
        if (texto.includes("descargar")) {
            let fila = el.closest('tr') || el.closest('[class*="row"]') || el.parentElement;
            const textoFila = fila ? fila.textContent.trim() : texto;
            resultados.push({elemento: el, textoFila: textoFila});
        }
    });

    const todos = raiz.querySelectorAll('*');
    todos.forEach(el => {
        if (el.shadowRoot) {
            buscarEnRaiz(el.shadowRoot, resultados);
        }
    });
}

const resultados = [];
buscarEnRaiz(document, resultados);
return resultados;
"""


def _crear_navegador(carpeta_descargas):
    opciones = Options()
    opciones.add_argument("--headless=new")
    opciones.add_argument("--no-sandbox")
    opciones.add_argument("--disable-dev-shm-usage")
    opciones.add_argument("--window-size=1600,1200")
    opciones.add_argument(f"--user-agent={UA_REALISTA}")
    # Intentar que la pagina no detecte que es un navegador automatizado
    opciones.add_argument("--disable-blink-features=AutomationControlled")
    opciones.add_experimental_option("excludeSwitches", ["enable-automation"])
    opciones.add_experimental_option("useAutomationExtension", False)

    carpeta_absoluta = os.path.abspath(carpeta_descargas)
    os.makedirs(carpeta_absoluta, exist_ok=True)
    opciones.add_experimental_option(
        "prefs",
        {
            "download.default_directory": carpeta_absoluta,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True,
        },
    )

    navegador = webdriver.Chrome(options=opciones)
    navegador.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"},
    )
    # En modo headless, Chrome necesita este comando explicito para
    # permitir descargas de archivos (si no, las bloquea en silencio).
    navegador.execute_cdp_cmd(
        "Page.setDownloadBehavior",
        {"behavior": "allow", "downloadPath": carpeta_absoluta},
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
        pass  # no salio el popup, seguimos normal


def _guardar_diagnostico(navegador, sufijo=""):
    """Guarda screenshot + HTML de la pagina tal como esta en ese momento, para depurar."""
    try:
        navegador.save_screenshot(f"error_diagnostico{sufijo}.png")
        with open(f"error_pagina{sufijo}.html", "w", encoding="utf-8") as f:
            f.write(navegador.page_source)
    except Exception:
        pass


def _titulo_indica_falla_pasajera(navegador):
    titulo = (navegador.title or "").strip().lower()
    return any(senial in titulo for senial in SENIALES_DE_FALLA_PASAJERA)


def _cargar_pagina_con_reintentos(navegador, intentos_maximos=INTENTOS_MAXIMOS_CARGA_PAGINA,
                                   espera_segundos=ESPERA_ENTRE_INTENTOS_SEGUNDOS):
    """
    Carga URL_INFORMES. Si el titulo de la pagina sugiere una falla
    pasajera del lado de XM (por ejemplo "Service unavailable"), espera
    y reintenta hasta intentos_maximos veces antes de continuar con lo
    que haya cargado en el ultimo intento.
    """
    for intento in range(1, intentos_maximos + 1):
        navegador.get(URL_INFORMES)
        time.sleep(3)  # deja tiempo a que arranque el JS de la pagina

        if not _titulo_indica_falla_pasajera(navegador):
            return  # cargo bien, seguimos con el flujo normal

        print(
            f"Intento {intento}/{intentos_maximos}: la pagina respondio con el "
            f"titulo '{navegador.title}', que parece una falla pasajera de XM."
        )
        if intento < intentos_maximos:
            print(f"Esperando {espera_segundos} segundos antes de reintentar...")
            time.sleep(espera_segundos)
        else:
            print("Se agotaron los reintentos de carga de pagina. Se continua "
                  "con lo que haya, para poder guardar diagnostico si falla la busqueda de botones.")


def _buscar_botones_descarga(navegador, tiempo_maximo=60, intervalo=2):
    """
    Va reintentando la busqueda (via JS, atravesando Shadow DOM) de los
    botones/enlaces 'Descargar' hasta encontrar al menos uno, o hasta
    agotar tiempo_maximo segundos.
    Devuelve la lista de {elemento, textoFila} que entrega el JS.
    """
    tiempo_transcurrido = 0
    while tiempo_transcurrido < tiempo_maximo:
        resultados = navegador.execute_script(JS_BUSCAR_BOTONES_DESCARGA)
        if resultados:
            return resultados
        time.sleep(intervalo)
        tiempo_transcurrido += intervalo

    _guardar_diagnostico(navegador)
    print(f"Titulo de la pagina cargada: {navegador.title}")
    print(f"URL actual: {navegador.current_url}")
    raise TimeoutException(
        f"No se encontro ningun boton 'Descargar' en {tiempo_maximo} segundos "
        f"(ni siquiera atravesando Shadow DOM)."
    )


def _esperar_archivo_descargado(carpeta, archivos_antes, tiempo_maximo=40):
    """
    Espera a que aparezca un archivo nuevo (completo, no .crdownload) en
    la carpeta de descargas que no estuviera antes del clic.
    Devuelve la ruta completa del archivo nuevo.
    """
    tiempo_transcurrido = 0
    intervalo = 1
    while tiempo_transcurrido < tiempo_maximo:
        archivos_ahora = set(glob.glob(os.path.join(carpeta, "*")))
        nuevos = archivos_ahora - archivos_antes
        nuevos_completos = [
            ruta for ruta in nuevos
            if not ruta.endswith(".crdownload") and not ruta.endswith(".tmp")
        ]
        if nuevos_completos:
            return nuevos_completos[0]
        time.sleep(intervalo)
        tiempo_transcurrido += intervalo

    raise TimeoutException(
        f"No se detecto ningun archivo nuevo descargado en {tiempo_maximo} segundos "
        f"en la carpeta {carpeta}."
    )


def descargar_archivos(carpeta_destino="."):
    """
    Descarga los dos archivos y los guarda en carpeta_destino con los
    nombres definidos en ARCHIVOS_A_DESCARGAR.
    Devuelve un diccionario {nombre_archivo: ruta_completa}.
    """
    carpeta_destino_absoluta = os.path.abspath(carpeta_destino)
    navegador = _crear_navegador(carpeta_destino_absoluta)
    rutas_guardadas = {}

    try:
        _cargar_pagina_con_reintentos(navegador)
        _cerrar_popup_si_aparece(navegador)

        botones = _buscar_botones_descarga(navegador)

        for nombre_archivo, fragmento_busqueda in ARCHIVOS_A_DESCARGAR.items():
            elemento_boton = None
            for entrada in botones:
                texto_fila = entrada.get("textoFila", "")
                if fragmento_busqueda.lower() in texto_fila.lower():
                    elemento_boton = entrada.get("elemento")
                    break

            if elemento_boton is None:
                _guardar_diagnostico(navegador, sufijo="_no_encontrado")
                print("Filas detectadas en la pagina:")
                for entrada in botones:
                    print(f"  - {entrada.get('textoFila', '')!r}")
                raise RuntimeError(
                    f"No se encontro el archivo que contiene '{fragmento_busqueda}' "
                    f"en la pagina. Se guardo error_diagnostico_no_encontrado.png/.html para revisar."
                )

            archivos_antes = set(glob.glob(os.path.join(carpeta_destino_absoluta, "*")))

            try:
                elemento_boton.click()
            except StaleElementReferenceException:
                # La pagina pudo haber vuelto a renderizar la fila; buscamos otra vez.
                botones = _buscar_botones_descarga(navegador)
                elemento_boton = None
                for entrada in botones:
                    texto_fila = entrada.get("textoFila", "")
                    if fragmento_busqueda.lower() in texto_fila.lower():
                        elemento_boton = entrada.get("elemento")
                        break
                if elemento_boton is None:
                    raise
                elemento_boton.click()

            ruta_descargada = _esperar_archivo_descargado(carpeta_destino_absoluta, archivos_antes)

            ruta_destino = os.path.join(carpeta_destino_absoluta, nombre_archivo)
            if os.path.abspath(ruta_descargada) != os.path.abspath(ruta_destino):
                if os.path.exists(ruta_destino):
                    os.remove(ruta_destino)
                os.rename(ruta_descargada, ruta_destino)

            rutas_guardadas[nombre_archivo] = ruta_destino

    finally:
        navegador.quit()

    return rutas_guardadas


if __name__ == "__main__":
    rutas = descargar_archivos()
    for nombre, ruta in rutas.items():
        print(f"Descargado: {nombre} -> {ruta}")
