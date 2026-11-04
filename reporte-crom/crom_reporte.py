"""
Automatización reporte CROM / PAT (XM - Valores CROM definitivos) – versión nube (GitHub Actions)
================================================================================================

Qué hace:
  1. Descarga de la página de XM los 2 archivos del mes publicado
     (ResultadosCROMDefinitivo_<Mes><Año>.xlsx y PatrimonioCROM_<MM><Año>.xlsx).
  2. Calcula para cada agente:
       CROM 1 / CROM 2 (MWh) = promedio, desde el mes publicado hasta diciembre de ese año, de
                               (kWh-mes / horas del mes) / 1000
       Patrimonio (miles de millones COP) = PAT / 1.000.000.000
  3. Genera el Excel de soporte (hoja "Resumen" con fórmulas trazables).
  4. Envía el correo "CROM/PAT (Oct-Dic 2026)" desde la cuenta de Gmail configurada.

Calendario:
  XM publica en el mes M la carpeta del mes M-1 (en noviembre se publica "10.Oct").
  El correo se envía el 1er o 2do día hábil de cada mes (festivos de Colombia).
  Con --auto solo actúa en esos dos días; si el día 1 no está publicado, reintenta el día 2.
  No envía dos veces el mismo mes (registro en enviados.log).

Credenciales y destinatarios (Secrets de GitHub, nunca dentro del código).
En el workflow se conectan así:
  CORREO_USUARIO       <- secrets.CORREO_REMITENTE
  CORREO_CLAVE         <- secrets.CORREO_CONTRASENA_CROM
  CORREO_DESTINO_CROM  <- secrets.CORREO_DESTINO_CROM
  CORREO_CC_CROM       <- secrets.CORREO_CC_CROM
Detalle por método:
  Envío por Gmail (SMTP):        CORREO_USUARIO (la cuenta @gmail.com),
                                 CORREO_CLAVE (contraseña de aplicación de 16 letras)
  Envío por Microsoft Graph:     CORREO_USUARIO, GRAPH_TENANT_ID, GRAPH_CLIENT_ID, GRAPH_CLIENT_SECRET
"""

import argparse
import base64
import json
import smtplib
import urllib.parse
import urllib.request
from email.mime.application import MIMEApplication
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import calendar
import datetime as dt
import os
import sys
from decimal import ROUND_HALF_UP, Decimal

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

# ---------------------------------------------------------------------------
# CONFIGURACIÓN
# ---------------------------------------------------------------------------
# (Nombre que aparece en el reporte, Sigla en los archivos de XM)
AGENTES = [
    ("BIA ENERGY", "BIA"),
    ("DUCK ENERGY", "DUC"),
    ("ENEL COLOMBIA", "END"),
    ("GESTION ENERGETICA", "HIM"),
    ("GRUPO ENERGÉTICO", "GRE"),
    ("NITRO ENERGY COLOMBIA", "NTC"),
    ("QI ENERGY", "QIE"),
    ("SANTA FE ENERGY", "SFE"),
    ("TERMO MECHERO MORRO", "TMM"),
    ("VATIA", "GNC"),
]

# Destinatarios: se leen de los Secrets de GitHub (el repositorio es público,
# así los correos de las personas no quedan visibles en el código).
#   CORREO_DESTINO_CROM -> "Para", separados por comas
#   CORREO_CC_CROM      -> "CC", separados por comas (opcional)
def _lista(nombre):
    return [x.strip() for x in os.environ.get(nombre, "").replace(";", ",").split(",") if x.strip()]


CORREO_PARA = _lista("CORREO_DESTINO_CROM")
CORREO_CC = _lista("CORREO_CC_CROM")
ADJUNTAR_EXCEL = False          # True para adjuntar el Excel de soporte al correo
METODO_ENVIO = "smtp"           # "smtp" (Gmail u otro servidor SMTP) o "graph" (Microsoft 365)
SMTP_SERVIDOR = "smtp.gmail.com"
SMTP_PUERTO = 587
RESPONDER_A = os.environ.get("CORREO_RESPONDER_A_CROM", "").strip()  # opcional: a dónde llegan las respuestas
DIAS_HABILES_ENVIO = (1, 2)     # 1er y 2do día hábil del mes

_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGEN_RESPALDO = os.path.join(_DIR, "respaldo_capital.png")
IMAGEN_FIRMA = os.path.join(_DIR, "firma.jpg")

# Periodo del cálculo y del asunto: desde el mes publicado hasta DICIEMBRE de ese
# mismo año (Oct -> Oct-Dic = 3 meses; Ago -> Ago-Dic = 5; Ene -> Ene-Dic = 12).
def meses_hasta_diciembre(fecha_inicio):
    return 13 - fecha_inicio.month

MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio",
         "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
ABREV = ["Ene", "Feb", "Mar", "Abr", "May", "Jun",
         "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]

URL_XM = ("https://www.xm.com.co/administraci%C3%B3n-financiera/"
          "gesti%C3%B3n-de-riesgo-del-mercado/valores-crom-definitivos")

TEXTO_CROM1 = ("Indica la capacidad para comprar energía en el mercado spot donde el riesgo se "
               "calcula como la compra de energía cuando el precio de bolsa es igual al precio de "
               "escasez, para este cálculo solo se consideran las compras y ventas en contratos, "
               "la demanda de usuarios no regulados y la generación propia del agente.")
TEXTO_CROM2 = ("Indica la capacidad para vender energía en el mercado spot donde el riesgo se "
               "calcula como la venta de energía cuando el precio de bolsa es igual al CERE + FAZNI "
               "(precio mínimo del mercado spot), para este cálculo solo se consideran las compras "
               "y ventas en contratos, la demanda de usuarios no regulados y la demanda regulada.")


# ---------------------------------------------------------------------------
# CALENDARIO
# ---------------------------------------------------------------------------
def mes_anterior(fecha):
    return (fecha.year - 1, 12) if fecha.month == 1 else (fecha.year, fecha.month - 1)


def dia_habil_del_mes(fecha):
    """Devuelve qué día hábil del mes es 'fecha' (1, 2, ...) o None si no es hábil."""
    try:
        import holidays
        festivos = holidays.Colombia(years=fecha.year)
    except ImportError:
        print("AVISO: falta 'holidays' (pip install holidays); solo se excluyen fines de semana.")
        festivos = {}
    n = 0
    for d in range(1, fecha.day + 1):
        f = dt.date(fecha.year, fecha.month, d)
        if f.weekday() < 5 and f not in festivos:
            n += 1
            if f == fecha:
                return n
    return None


def ya_enviado(carpeta, anio, mes):
    log = os.path.join(carpeta, "enviados.log")
    if not os.path.exists(log):
        return False
    with open(log, encoding="utf-8") as f:
        return f"{anio}-{mes:02d}" in f.read().split()


def registrar_envio(carpeta, anio, mes):
    with open(os.path.join(carpeta, "enviados.log"), "a", encoding="utf-8") as f:
        f.write(f"{anio}-{mes:02d}\n")


# ---------------------------------------------------------------------------
# DESCARGA DESDE XM
# ---------------------------------------------------------------------------
def nombres_archivos(anio, mes):
    return (f"ResultadosCROMDefinitivo_{MESES[mes - 1]}{anio}.xlsx",
            f"PatrimonioCROM_{mes:02d}{anio}.xlsx")


def _frame_explorador(page):
    """El explorador de archivos de XM se carga por JavaScript y puede estar
    dentro de un iframe: se busca el frame que tenga el buscador."""
    for _ in range(60):
        for fr in page.frames:
            try:
                if fr.get_by_placeholder("Buscar archivo por nombre").count() > 0:
                    return fr
            except Exception:
                pass
        page.wait_for_timeout(1000)
    raise RuntimeError("No se encontró el explorador de archivos en la página de XM")


def _abrir_carpeta(page, fr, patron, descripcion):
    """Abre la carpeta cuyo nombre cumple el patrón (clic y, si no entra, doble clic)."""
    import re
    item = fr.get_by_text(re.compile(patron)).first
    item.wait_for(timeout=30000)
    texto_antes = fr.locator("body").inner_text()
    item.click()
    page.wait_for_timeout(2500)
    if fr.locator("body").inner_text() == texto_antes:
        item.dblclick()
        page.wait_for_timeout(2500)
    print(f"  Carpeta abierta: {descripcion}")


def descargar_xm(anio, mes, carpeta, visible=False):
    """Entra a la página de XM, abre <año> -> <mes> y descarga los 2 archivos."""
    import re
    from playwright.sync_api import sync_playwright

    os.makedirs(carpeta, exist_ok=True)
    prefijos = ["ResultadosCROMDefinitivo", "PatrimonioCROM"]
    print(f"Abriendo {URL_XM}")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not visible)
        page = browser.new_page(accept_downloads=True)
        page.goto(URL_XM, wait_until="domcontentloaded", timeout=90000)
        fr = _frame_explorador(page)

        # 1) Año   (carpetas: 2026, 2025, ...)
        _abrir_carpeta(page, fr, rf"^\s*{anio}\s*$", str(anio))
        # 2) Mes   (carpetas: '10.Oct', '03. Mar', ... -> se busca por el número)
        _abrir_carpeta(page, fr, rf"^\s*0?{mes}\.\s*[A-Za-z]", f"mes {mes:02d}")

        # 3) Archivos
        for pref in prefijos:
            nombre = fr.get_by_text(re.compile(rf"^\s*{pref}", re.I)).first
            nombre.wait_for(timeout=30000)
            fila = nombre.locator(
                "xpath=ancestor::*[.//*[normalize-space(text())='Descargar']][1]")
            boton = fila.get_by_text("Descargar", exact=True).first
            with page.expect_download(timeout=120000) as dl:
                boton.click()
            d = dl.value
            destino = os.path.join(carpeta, d.suggested_filename)
            d.save_as(destino)
            print(f"  Descargado: {destino}")
        browser.close()


def buscar_archivo(carpeta, tipo, anio, mes):
    """Busca el archivo del mes sin depender del nombre exacto."""
    for f in sorted(os.listdir(carpeta)):
        fl = f.lower()
        if not fl.endswith((".xlsx", ".xls")):
            continue
        if tipo == "resultados" and fl.startswith("resultadoscromdefinitivo") \
                and f"{MESES[mes - 1].lower()}{anio}" in fl:
            return os.path.join(carpeta, f)
        if tipo == "patrimonio" and fl.startswith("patrimoniocrom") \
                and f"{mes:02d}{anio}" in fl:
            return os.path.join(carpeta, f)
    esperado = nombres_archivos(anio, mes)[0 if tipo == "resultados" else 1]
    raise FileNotFoundError(f"No se encontró '{esperado}' en {carpeta}. "
                            "Use --descargar o copie el archivo en esa carpeta.")


def leer_hoja(ws):
    return [list(r) for r in ws.iter_rows(values_only=True)]


def fila_por_sigla(filas, col_sigla, fila_inicio):
    idx = {}
    for i, f in enumerate(filas[fila_inicio - 1:], start=fila_inicio):
        if len(f) > col_sigla and f[col_sigla]:
            idx[str(f[col_sigla]).strip().upper()] = i
    return idx


# ---------------------------------------------------------------------------
# CÁLCULO
# ---------------------------------------------------------------------------
def _a_fecha(v):
    """Convierte lo que venga en la celda de fecha (fecha, número de Excel o texto) a fecha."""
    if isinstance(v, dt.datetime):
        return v
    if isinstance(v, dt.date):
        return dt.datetime(v.year, v.month, v.day)
    if isinstance(v, (int, float)) and 20000 < v < 80000:
        return dt.datetime(1899, 12, 30) + dt.timedelta(days=float(v))
    if isinstance(v, str):
        t = v.lower()
        for i, m in enumerate(MESES):
            if m.lower() in t:
                import re
                a = re.search(r"(19|20)\d{2}", t)
                if a:
                    return dt.datetime(int(a.group()), i + 1, 1)
    return None


def fechas_columnas(filas, anio, mes):
    """Fecha de cada columna de meses (desde la E). Se busca en la fila 3; si XM la
    dejó como fórmula sin valor, se lee el encabezado de la fila 6
    ('Octubre de 2026(KWhm)'); y si tampoco, se cuenta desde el mes pedido."""
    n = max(len(filas[2]), len(filas[5])) - 4
    out = []
    for i in range(n):
        c = 4 + i
        f = None
        for fila in (filas[2], filas[5]):
            if c < len(fila):
                f = _a_fecha(fila[c])
                if f:
                    break
        if f is None:
            y, m = anio + (mes - 1 + i) // 12, (mes - 1 + i) % 12 + 1
            f = dt.datetime(y, m, 1)
        out.append(f)
    return out


def calcular(anio, mes, carpeta):
    ruta_res = buscar_archivo(carpeta, "resultados", anio, mes)
    ruta_pat = buscar_archivo(carpeta, "patrimonio", anio, mes)
    print(f"Usando:\n  {ruta_res}\n  {ruta_pat}")

    wb_res = openpyxl.load_workbook(ruta_res, data_only=True)
    wb_pat = openpyxl.load_workbook(ruta_pat, data_only=True)
    crom = {h: leer_hoja(wb_res[h]) for h in ("CROM 1", "CROM 2")}
    pat = leer_hoja(wb_pat["PAT"])

    fechas_todas = fechas_columnas(crom["CROM 1"], anio, mes)
    n_meses = meses_hasta_diciembre(fechas_todas[0])
    fechas = fechas_todas[:n_meses]
    print(f"Periodo del cálculo: {periodo_texto(fechas)} ({n_meses} meses)")
    if (fechas[0].year, fechas[0].month) != (anio, mes):
        print(f"ADVERTENCIA: el archivo inicia en {fechas[0]:%m/%Y}, no en {mes:02d}/{anio}")
    horas = [calendar.monthrange(f.year, f.month)[1] * 24 for f in fechas]

    idx = {"CROM 1": fila_por_sigla(crom["CROM 1"], 2, 7),
           "CROM 2": fila_por_sigla(crom["CROM 2"], 2, 7),
           "PAT": fila_por_sigla(pat, 2, 4)}

    filas, faltantes = [], []
    for nombre, sigla in AGENTES:
        s = sigla.upper()
        fila = {"nombre": nombre, "sigla": s, "ref": {}}
        for hoja in ("CROM 1", "CROM 2"):
            if s in idx[hoja]:
                r = idx[hoja][s]
                crudos = [crom[hoja][r - 1][4 + i] for i in range(n_meses)]
                if any(not isinstance(v, (int, float)) for v in crudos):
                    raise ValueError(f"{nombre} ({sigla}) en {hoja}: valores vacíos o no numéricos "
                                     f"{crudos}. Revisar el archivo de XM.")
                vals = crudos
                fila[hoja] = sum(v / h for v, h in zip(vals, horas)) / len(vals) / 1000
                fila["ref"][hoja] = r
            else:
                fila[hoja] = None
                faltantes.append(f"{nombre} ({sigla}) en {hoja}")
        if s in idx["PAT"]:
            r = idx["PAT"][s]
            fila["PAT"] = (pat[r - 1][4] or 0) / 1e9
            fila["ref"]["PAT"] = r
        else:
            fila["PAT"] = None
            faltantes.append(f"{nombre} ({sigla}) en PAT")
        filas.append(fila)

    if faltantes:
        print("ADVERTENCIA – no se encontraron:\n  " + "\n  ".join(faltantes))
    return {"anio": anio, "mes": mes, "fechas": fechas, "fechas_todas": fechas_todas,
            "n_meses": n_meses,
            "filas": filas,
            "faltantes": faltantes, "crom": crom, "pat": pat,
            "ruta_res": ruta_res, "ruta_pat": ruta_pat}


def periodo_texto(fechas):
    """'Oct-Dic 2026', 'Ene-Dic 2027' o 'Dic 2026' si es un solo mes."""
    a, b = fechas[0], fechas[-1]
    if a == b:
        return f"{ABREV[a.month - 1]} {a.year}"
    if a.year == b.year:
        return f"{ABREV[a.month - 1]}-{ABREV[b.month - 1]} {a.year}"
    return f"{ABREV[a.month - 1]} {a.year}-{ABREV[b.month - 1]} {b.year}"


# ---------------------------------------------------------------------------
# EXCEL DE SOPORTE
# ---------------------------------------------------------------------------
def generar_excel(datos, salida):
    anio, mes = datos["anio"], datos["mes"]
    out = openpyxl.Workbook()
    resumen = out.active
    resumen.title = "Resumen"

    for nombre, filas in (("CROM 1", datos["crom"]["CROM 1"]),
                          ("CROM 2", datos["crom"]["CROM 2"]), ("PAT", datos["pat"])):
        ws = out.create_sheet(nombre)
        for r, fila in enumerate(filas, start=1):
            for c, v in enumerate(fila, start=1):
                if v is not None:
                    ws.cell(r, c, v)
        if nombre.startswith("CROM"):
            for i, d in enumerate(datos["fechas_todas"]):
                c = 5 + i
                ws.cell(3, c, d).number_format = "mmm-yyyy"
                ws.cell(4, c, calendar.monthrange(d.year, d.month)[1])
            ws.cell(4, 4, "Días del mes")

    negrita = Font(name="Arial", bold=True, size=10)
    normal = Font(name="Arial", size=10)
    gris = PatternFill("solid", start_color="D9D9D9")
    fino = Side(style="thin")
    borde = Border(left=fino, right=fino, top=fino, bottom=fino)
    centro = Alignment(horizontal="center", vertical="center", wrap_text=True)

    resumen["C2"] = f"CROM/PAT ({periodo_texto(datos['fechas'])})"
    resumen["C2"].font = Font(name="Arial", bold=True, size=12)
    resumen.merge_cells("C5:C6")
    resumen.merge_cells("D5:E5")
    resumen.merge_cells("F5:F6")
    resumen["C5"] = "Agente"
    resumen["D5"] = "Energía (MWh)"
    resumen["D6"] = "CROM 1 \nMWh"
    resumen["E6"] = "CROM 2 \nMWh"
    resumen["F5"] = "Patrimonio transaccional\nMiles de millones COP"
    for row in resumen["C5:F6"]:
        for cell in row:
            cell.font, cell.alignment, cell.border, cell.fill = negrita, centro, borde, gris
    resumen.row_dimensions[6].height = 30

    cols = [get_column_letter(5 + i) for i in range(datos["n_meses"])]

    def formula_crom(hoja, fila):
        partes = ",".join(f"'{hoja}'!{c}{fila}/('{hoja}'!{c}$4*24)" for c in cols)
        return f"=AVERAGE({partes})/1000"

    r = 7
    for f in datos["filas"]:
        resumen.cell(r, 3, f["nombre"])
        for col, hoja in ((4, "CROM 1"), (5, "CROM 2")):
            ref = f["ref"].get(hoja)
            resumen.cell(r, col, formula_crom(hoja, ref) if ref else "N/D")
        ref = f["ref"].get("PAT")
        resumen.cell(r, 6, f"='PAT'!E{ref}/1000000000" if ref else "N/D")
        for c in range(3, 7):
            resumen.cell(r, c).font = normal
            resumen.cell(r, c).border = borde
        for c in (4, 5):
            resumen.cell(r, c).number_format = "0"
            resumen.cell(r, c).alignment = Alignment(horizontal="center")
        resumen.cell(r, 6).number_format = '_-"$"\\ * #,##0_-;\\-"$"\\ * #,##0_-;_-"$"\\ * "-"??_-;_-@_-'
        r += 1

    nota = Font(name="Arial", size=8, italic=True)
    resumen.cell(r + 1, 3, f"Fuente: XM – Valores CROM definitivos, {MESES[mes - 1]} {anio} "
                 f"({os.path.basename(datos['ruta_res'])}, "
                 f"{os.path.basename(datos['ruta_pat'])}).").font = nota
    resumen.cell(r + 2, 3, f"CROM: promedio {periodo_texto(datos['fechas'])} "
                 f"({datos['n_meses']} meses) de "
                 "(kWh-mes ÷ horas del mes) ÷ 1.000. Patrimonio: PAT ÷ 10^9.").font = nota
    for col, w in (("A", 3), ("B", 3), ("C", 28), ("D", 14), ("E", 14), ("F", 26)):
        resumen.column_dimensions[col].width = w
    resumen.sheet_view.showGridLines = False
    out.save(salida)
    print(f"Excel generado: {salida}")
    return salida


# ---------------------------------------------------------------------------
# CORREO
# ---------------------------------------------------------------------------
def redondear(x):
    return int(Decimal(str(x)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def html_correo(datos, src_imagen, src_firma=""):
    f_txt = "font-family:Arial,sans-serif;font-size:11pt;color:#000;"
    f_tab = "font-family:'Arial Narrow',Arial,sans-serif;font-size:11pt;"
    f_head = "font-family:Calibri,Arial,sans-serif;font-size:11pt;font-weight:bold;"
    pt = "1px dotted #000"
    sol = "1px solid #000"

    filas = []
    for f in datos["filas"]:
        c1 = "N/D" if f["CROM 1"] is None else str(redondear(f["CROM 1"]))
        c2 = "N/D" if f["CROM 2"] is None else str(redondear(f["CROM 2"]))
        pt_val = "N/D" if f["PAT"] is None else f"{redondear(f['PAT']):,}"
        filas.append(
            f'<tr style="{f_tab}">'
            f'<td style="border-right:{pt};border-bottom:{pt};padding:1px 4px;">{f["nombre"]}</td>'
            f'<td style="border-right:{pt};border-bottom:{pt};text-align:center;">{c1}</td>'
            f'<td style="border-right:{sol};border-bottom:{pt};text-align:center;">{c2}</td>'
            f'<td style="border-bottom:{pt};padding:1px 4px;">'
            f'<table width="100%" cellspacing="0" cellpadding="0" style="{f_tab}"><tr>'
            f'<td style="text-align:left;">$</td><td style="text-align:right;">{pt_val}</td>'
            f'</tr></table></td></tr>')

    tabla = f"""
<table cellspacing="0" cellpadding="0" style="border:2px solid #000;border-collapse:collapse;width:640px;">
  <tr style="{f_head}">
    <td rowspan="2" style="border-right:{pt};border-bottom:{sol};text-align:center;width:240px;">Agente</td>
    <td colspan="2" style="border-right:{sol};border-bottom:{pt};text-align:center;">Energía (MWh)</td>
    <td rowspan="2" style="border-bottom:{sol};text-align:center;width:230px;">Patrimonio transaccional<br>Miles de millones COP</td>
  </tr>
  <tr style="{f_head}">
    <td style="border-right:{pt};border-bottom:{sol};text-align:center;width:85px;">CROM 1<br>MWh</td>
    <td style="border-right:{sol};border-bottom:{sol};text-align:center;width:85px;">CROM 2<br>MWh</td>
  </tr>
  {''.join(filas)}
</table>"""

    img = (f'<p><img src="{src_imagen}" width="620" alt="Respaldo de capital para realizar '
           f'transacciones en bolsa"></p>') if src_imagen else ""

    firma = (f'<p><img src="{src_firma}" width="520" alt="Nicol Leyton – Analista Comercial"></p>'
             if src_firma else "")

    return f"""<div style="{f_txt}">
<p>Estimados,</p>
<p>A continuación, presento la información correspondiente al CROM 1, CROM 2 y el Patrimonio Transaccional.</p>
{tabla}
<p><b>CROM 1:</b> {TEXTO_CROM1}</p>
<p><b>CROM 2:</b> {TEXTO_CROM2}</p>
{img}
<p>Cordialmente,</p>
{firma}
</div>"""


def _data_uri(ruta, tipo):
    if not os.path.exists(ruta):
        return ""
    with open(ruta, "rb") as f:
        return f"data:{tipo};base64," + base64.b64encode(f.read()).decode()


def vista_previa(datos, asunto, ruta):
    cab = (f'<p style="font-family:Arial;font-size:10pt;color:#555;">'
           f'<b>Asunto:</b> {asunto}</p><hr>')
    cuerpo = html_correo(datos, _data_uri(IMAGEN_RESPALDO, "image/png"),
                         _data_uri(IMAGEN_FIRMA, "image/jpeg"))
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(f"<html><head><meta charset='utf-8'></head><body>{cab}{cuerpo}</body></html>")
    print(f"Vista previa del correo: {ruta}")


def _imagenes():
    """[(ruta, content-id, subtipo)] de las imágenes que existan."""
    return [(r, cid, sub) for r, cid, sub in
            ((IMAGEN_RESPALDO, "respaldo_capital", "png"), (IMAGEN_FIRMA, "firma", "jpeg"))
            if os.path.exists(r)]


def _env(nombre):
    v = os.environ.get(nombre, "").strip()
    if not v:
        raise RuntimeError(f"Falta la credencial '{nombre}' (configúrela en GitHub > Settings > "
                           "Secrets and variables > Actions)")
    return v


def enviar_correo(datos, asunto, para, cc, adjunto=None):
    remitente = _env("CORREO_USUARIO")
    imgs = _imagenes()
    src = {cid: f"cid:{cid}" for _, cid, _ in imgs}
    html = (f"<html><body>"
            f"{html_correo(datos, src.get('respaldo_capital', ''), src.get('firma', ''))}"
            f"</body></html>")

    if METODO_ENVIO == "graph":
        _enviar_graph(remitente, asunto, html, para, cc, imgs, adjunto)
    else:
        _enviar_smtp(remitente, asunto, html, para, cc, imgs, adjunto)
    print(f"Correo enviado: {asunto}  ->  {', '.join(para + cc)}")


def _enviar_smtp(remitente, asunto, html, para, cc, imgs, adjunto):
    msg = MIMEMultipart("mixed")
    msg["Subject"], msg["From"], msg["To"] = asunto, remitente, ", ".join(para)
    if cc:
        msg["Cc"] = ", ".join(cc)
    if RESPONDER_A:
        msg["Reply-To"] = RESPONDER_A
    rel = MIMEMultipart("related")
    rel.attach(MIMEText(html, "html", "utf-8"))
    for ruta, cid, sub in imgs:
        with open(ruta, "rb") as f:
            im = MIMEImage(f.read(), _subtype=sub)
        im.add_header("Content-ID", f"<{cid}>")
        im.add_header("Content-Disposition", "inline", filename=os.path.basename(ruta))
        rel.attach(im)
    msg.attach(rel)
    if adjunto:
        with open(adjunto, "rb") as f:
            part = MIMEApplication(f.read(), Name=os.path.basename(adjunto))
        part["Content-Disposition"] = f'attachment; filename="{os.path.basename(adjunto)}"'
        msg.attach(part)
    with smtplib.SMTP(SMTP_SERVIDOR, SMTP_PUERTO, timeout=60) as s:
        s.starttls()
        s.login(remitente, _env("CORREO_CLAVE"))
        s.sendmail(remitente, para + cc, msg.as_string())


def _enviar_graph(remitente, asunto, html, para, cc, imgs, adjunto):
    token_url = f"https://login.microsoftonline.com/{_env('GRAPH_TENANT_ID')}/oauth2/v2.0/token"
    data = urllib.parse.urlencode({
        "client_id": _env("GRAPH_CLIENT_ID"), "client_secret": _env("GRAPH_CLIENT_SECRET"),
        "scope": "https://graph.microsoft.com/.default", "grant_type": "client_credentials",
    }).encode()
    token = json.load(urllib.request.urlopen(token_url, data, timeout=60))["access_token"]

    adjuntos = []
    for ruta, cid, sub in imgs:
        with open(ruta, "rb") as f:
            adjuntos.append({"@odata.type": "#microsoft.graph.fileAttachment",
                             "name": os.path.basename(ruta), "contentType": f"image/{sub}",
                             "contentId": cid, "isInline": True,
                             "contentBytes": base64.b64encode(f.read()).decode()})
    if adjunto:
        with open(adjunto, "rb") as f:
            adjuntos.append({"@odata.type": "#microsoft.graph.fileAttachment",
                             "name": os.path.basename(adjunto),
                             "contentBytes": base64.b64encode(f.read()).decode()})
    cuerpo = {"message": {
        "subject": asunto, "body": {"contentType": "HTML", "content": html},
        "toRecipients": [{"emailAddress": {"address": a}} for a in para],
        "ccRecipients": [{"emailAddress": {"address": a}} for a in cc],
        "attachments": adjuntos}, "saveToSentItems": True}
    req = urllib.request.Request(
        f"https://graph.microsoft.com/v1.0/users/{remitente}/sendMail",
        data=json.dumps(cuerpo).encode(), method="POST",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    urllib.request.urlopen(req, timeout=60)


# ---------------------------------------------------------------------------
# FLUJO
# ---------------------------------------------------------------------------
def procesar(anio, mes, carpeta, bajar, visible, modo_correo):
    """modo_correo: 'enviar' (destinatarios reales), 'prueba' (solo al remitente), 'no'."""
    os.makedirs(carpeta, exist_ok=True)
    descargas = os.path.join(carpeta, "descargas")
    if bajar:
        descargar_xm(anio, mes, descargas, visible)
    datos = calcular(anio, mes, descargas if os.path.isdir(descargas) else carpeta)
    asunto = f"CROM/PAT ({periodo_texto(datos['fechas'])})"

    salida = os.path.join(carpeta, "salida")
    os.makedirs(salida, exist_ok=True)
    base = os.path.join(salida, f"Reporte_CROM_{MESES[mes - 1]}{anio}")
    excel = generar_excel(datos, base + ".xlsx")
    vista_previa(datos, asunto, base + "_correo.html")
    adj = excel if ADJUNTAR_EXCEL else None

    if modo_correo == "enviar" and datos["faltantes"]:
        print("Hay agentes sin datos: se envía como PRUEBA (solo al remitente) para revisión.")
        modo_correo = "prueba"
    if modo_correo == "enviar":
        if not CORREO_PARA:
            raise RuntimeError("Falta el Secret CORREO_DESTINO_CROM (a quién se envía el correo)")
        enviar_correo(datos, asunto, CORREO_PARA, CORREO_CC, adj)
    elif modo_correo == "prueba":
        enviar_correo(datos, "[PRUEBA] " + asunto, [_env("CORREO_USUARIO")], [], adj)
    return modo_correo


def modo_auto(carpeta, visible):
    hoy = dt.date.today()
    n = dia_habil_del_mes(hoy)
    if n not in DIAS_HABILES_ENVIO:
        print(f"{hoy}: no es 1er ni 2do día hábil (día hábil = {n}). No se hace nada.")
        return
    anio, mes = mes_anterior(hoy)  # XM publica el mes M-1
    if ya_enviado(carpeta, anio, mes):
        print(f"El reporte de {MESES[mes - 1]} {anio} ya fue enviado. No se hace nada.")
        return
    print(f"{hoy}: día hábil {n}. Procesando publicación de {MESES[mes - 1]} {anio}.")
    try:
        modo = procesar(anio, mes, carpeta, True, visible, "enviar")
    except Exception as e:
        siguiente = "Se reintentará el próximo día hábil." if n < max(DIAS_HABILES_ENVIO) \
            else "Era el último día programado: revisar manualmente."
        print(f"ERROR: {e}\n{siguiente}")
        sys.exit(1)
    if modo == "enviar":
        registrar_envio(carpeta, anio, mes)


def main():
    p = argparse.ArgumentParser(description="Reporte y correo CROM/PAT")
    p.add_argument("--auto", action="store_true",
                   help="Modo programado: actúa solo el 1er/2do día hábil, mes M-1, y envía")
    p.add_argument("--anio", type=int)
    p.add_argument("--mes", type=int)
    p.add_argument("--carpeta", default=".", help="Carpeta de trabajo")
    p.add_argument("--descargar", action="store_true", help="Descargar archivos de XM")
    p.add_argument("--visible", action="store_true", help="Mostrar el navegador al descargar")
    p.add_argument("--correo", choices=["enviar", "prueba", "no"], default="no",
                   help="enviar = destinatarios reales; prueba = solo al remitente; no = no enviar")
    a = p.parse_args()

    if a.auto:
        modo_auto(a.carpeta, a.visible)
        return
    if not a.anio or not a.mes:
        a.anio, a.mes = mes_anterior(dt.date.today())
    if not 1 <= a.mes <= 12:
        sys.exit("El mes debe estar entre 1 y 12")
    modo = procesar(a.anio, a.mes, a.carpeta, a.descargar, a.visible, a.correo)
    if modo == "enviar":
        registrar_envio(a.carpeta, a.anio, a.mes)


if __name__ == "__main__":
    main()
