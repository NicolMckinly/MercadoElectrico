# =====================================================================
# generar_reporte.py  —  LA "RECETA" DEL ROBOT
# ---------------------------------------------------------------------
# Este programa hace 5 cosas, en orden:
#   PASO 1. Leer el Excel del BEC y separar los puntos de entrega.
#   PASO 2. Calcular números importantes de cada punto.
#   PASO 3. Dibujar gráficas (comparativas y de cada punto).
#   PASO 4. Escribir el análisis y armar el reporte en HTML.
#   PASO 5. (Opcional) Enviarlo por Gmail.
#
# Formas de ejecutarlo (en la terminal):
#   python generar_reporte.py                 -> reporte del mes actual
#   python generar_reporte.py --mes 2026-09   -> reporte de septiembre 2026
#   python generar_reporte.py --solo-ultimo-dia-habil
#        -> solo hace el reporte si hoy es el último día hábil del mes
#   python generar_reporte.py --enviar        -> además lo envía por Gmail
#   python generar_reporte.py --prueba        -> usa datos INVENTADOS de la
#        carpeta pruebas/ para ver cómo queda el reporte
#   (las opciones se pueden combinar)
# =====================================================================

import argparse                   # lee las opciones que escribes en la terminal (--mes, etc.)
import base64                     # convierte imágenes en texto para meterlas en el HTML
import io                         # permite guardar imágenes en memoria (sin crear archivos)
import os                         # sirve para manejar carpetas
import unicodedata                # sirve para quitar tildes (Floreña -> Florena)
from datetime import date         # para saber la fecha de hoy

import matplotlib
matplotlib.use("Agg")             # dibuja sin abrir ventanas (necesario en servidores)
import matplotlib.pyplot as plt   # la "caja de colores" para hacer gráficas
import pandas as pd               # la herramienta para trabajar tablas, como un Excel dentro de Python

import config                     # nuestro panel de control (config.py)
import enviar_correo              # nuestro cartero (enviar_correo.py)
from calendario import hoy_es_ultimo_dia_habil   # nuestro calendario (calendario.py)

ARCHIVO_PRUEBA = "pruebas/datos_ficticios_puntos.xlsx"

# El BEC escribe los meses abreviados en español. Esta tabla le enseña
# al programa qué número tiene cada mes.
MESES = {"Ene": 1, "Feb": 2, "Mar": 3, "Abr": 4, "May": 5, "Jun": 6,
         "Jul": 7, "Ago": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dic": 12}
NOMBRE_MES = {v: k for k, v in MESES.items()}   # al revés: 10 -> "Oct"
MES_LARGO = {1: "enero", 2: "febrero", 3: "marzo", 4: "abril", 5: "mayo",
             6: "junio", 7: "julio", 8: "agosto", 9: "septiembre",
             10: "octubre", 11: "noviembre", 12: "diciembre"}


def mes_bonito(periodo):
    """Period(2026-09) -> 'septiembre de 2026'."""
    return f"{MES_LARGO[periodo.month]} de {periodo.year}"


# =====================================================================
# PASO 1. LEER LOS DATOS Y SEPARAR LOS PUNTOS
# =====================================================================

def leer_excel_bec(ruta):
    """Lee un Excel exportado del BEC y devuelve una tabla limpia.

    Los Excel del BEC traen "basura" arriba y abajo (filas que dicen
    "Filtros aplicados", "Total", filas vacías). Esta función busca
    dónde empieza la tabla de verdad y se queda solo con los datos.
    """
    crudo = pd.read_excel(ruta, header=None)

    # Buscamos la fila que contiene la palabra "Año-mes": ahí están los títulos.
    fila_titulos = None
    for i, fila in crudo.iterrows():
        if any(str(celda).startswith("Año-mes") for celda in fila):
            fila_titulos = i
            break
    if fila_titulos is None:
        raise ValueError(f"No encontré la columna 'Año-mes' en {ruta}")

    tabla = crudo.iloc[fila_titulos + 1:].copy()
    tabla.columns = [str(c) for c in crudo.iloc[fila_titulos]]

    # Les ponemos nombres cortos y fijos a las columnas, buscando palabras
    # clave. Así no importa si el BEC escribe "Pto_entrega" o "Punto de entrega".
    nombres = {}
    for col in tabla.columns:
        if col.startswith("Año-mes"):
            nombres[col] = "mes_texto"
        elif "unto" in col or "Pto" in col:
            nombres[col] = "punto"
        elif "Modalidad" in col:
            nombres[col] = "modalidad"
        elif "Cantidad" in col:
            nombres[col] = "cantidad"
        elif "Precio" in col:
            nombres[col] = "precio"
    tabla = tabla.rename(columns=nombres)[list(nombres.values())]

    # Quitamos filas que no son datos: las que no tienen modalidad.
    tabla = tabla[tabla["modalidad"].notna()]

    # Convertimos "2026 Oct" en una fecha de verdad (un "periodo" mensual).
    def a_periodo(texto):
        anio, mes = str(texto).split()
        return pd.Period(year=int(anio), month=MESES[mes], freq="M")
    tabla["mes"] = tabla["mes_texto"].apply(a_periodo)

    # Los números: la cantidad es un número entero. El precio a veces
    # viene con coma ("17,00") o como "ND" (No Disponible). Cambiamos la
    # coma por punto y lo que no sea número queda vacío (NaN).
    tabla["cantidad"] = pd.to_numeric(tabla["cantidad"])
    tabla["precio"] = pd.to_numeric(
        tabla["precio"].astype(str).str.replace(",", "."), errors="coerce")

    return tabla[["mes", "punto", "modalidad", "cantidad", "precio"]]


def sin_tildes(texto):
    """'Floreña' -> 'florena'. Quita tildes y pasa a minúsculas.

    Así no importa si el BEC escribe FLOREÑA, Florena o floreña.
    """
    normal = unicodedata.normalize("NFKD", str(texto))
    return "".join(c for c in normal if not unicodedata.combining(c)).lower()


def separar_puntos(tabla):
    """Reparte las filas del Excel en "cajas", una por punto de seguimiento.

    Devuelve:
      - grupos: diccionario {nombre del punto: sus filas}
      - encontrados: {nombre del punto: nombres del BEC que cayeron en esa caja}
      - otros: nombres de puntos del BEC que NO estamos siguiendo
      - aviso: texto si algo no salió como se esperaba (o None)
    """
    puntos_bec = sorted(tabla["punto"].astype(str).unique())

    # Caso especial: el archivo solo trae el total Nacional.
    if puntos_bec == ["Nacional"]:
        aviso = ("Este archivo solo trae el total Nacional, sin detalle por punto de "
                 "entrega. Exporta la tabla de la pestaña «Puntos» del BEC para ver "
                 "Cusiana, Floreña y Cartagena por separado.")
        return {"Nacional": tabla}, {"Nacional": ["Nacional"]}, [], aviso

    grupos, encontrados, usados = {}, {}, set()
    for nombre, palabras in config.PUNTOS_SEGUIMIENTO.items():
        # ¿Qué nombres del BEC contienen alguna de las palabras clave?
        coinciden = [p for p in puntos_bec
                     if any(sin_tildes(clave) in sin_tildes(p) for clave in palabras)]
        encontrados[nombre] = coinciden
        usados.update(coinciden)
        grupos[nombre] = tabla[tabla["punto"].astype(str).isin(coinciden)]

    otros = [p for p in puntos_bec if p not in usados]
    sin_datos = [n for n, c in encontrados.items() if not c]
    aviso = None
    if sin_datos:
        aviso = ("No encontré en el archivo estos puntos: " + ", ".join(sin_datos) +
                 ". Revisa las palabras clave en config.py comparándolas con la "
                 "lista de puntos del final del reporte.")
    return grupos, encontrados, otros, aviso


# =====================================================================
# PASO 2. CALCULAR LOS NÚMEROS IMPORTANTES
# =====================================================================

def precio_ponderado(grupo):
    """Promedio ponderado: los contratos grandes pesan más que los pequeños.

    Ejemplo: si compras 10 unidades a $10 y 1 unidad a $20, el promedio
    simple sería $15, pero el ponderado es (10×10 + 1×20) / 11 = $10,9,
    que refleja mejor lo que pasó. Las filas sin precio ("ND") no cuentan.
    """
    con_precio = grupo[grupo["precio"].notna()]
    if con_precio["cantidad"].sum() == 0:
        return float("nan")
    return (con_precio["cantidad"] * con_precio["precio"]).sum() / con_precio["cantidad"].sum()


def resumen_mensual(tabla):
    """Una fila por mes: cantidad total, precio ponderado y número de negociaciones."""
    filas = [{"mes": mes, "cantidad": g["cantidad"].sum(),
              "precio": precio_ponderado(g), "negociaciones": len(g)}
             for mes, g in tabla.groupby("mes")]
    if not filas:
        return pd.DataFrame(columns=["cantidad", "precio", "negociaciones"])
    return pd.DataFrame(filas).set_index("mes").sort_index()


def resumen_por_modalidad(tabla, mes):
    """Para un mes: cantidad, precio y participación (%) de cada modalidad."""
    del_mes = tabla[tabla["mes"] == mes]
    filas = [{"modalidad": mod, "cantidad": g["cantidad"].sum(),
              "precio": precio_ponderado(g), "negociaciones": len(g)}
             for mod, g in del_mes.groupby("modalidad")]
    if not filas:
        return pd.DataFrame(columns=["modalidad", "cantidad", "precio",
                                     "negociaciones", "participacion"])
    res = pd.DataFrame(filas).sort_values("cantidad", ascending=False)
    res["participacion"] = 100 * res["cantidad"] / res["cantidad"].sum()
    return res


# =====================================================================
# PASO 3. DIBUJAR LAS GRÁFICAS
# =====================================================================

def figura_a_png(fig):
    """Convierte una gráfica en una imagen PNG guardada en memoria."""
    memoria = io.BytesIO()
    fig.savefig(memoria, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    return memoria.getvalue()


def png_a_texto(png):
    """Convierte la imagen en texto para meterla dentro de un archivo HTML."""
    return "data:image/png;base64," + base64.b64encode(png).decode("ascii")


def estilo_basico(ax):
    """Quita bordes innecesarios para que la gráfica se lea limpia."""
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    ax.grid(axis="y", color="#E3E6EA", linewidth=0.8)
    ax.set_axisbelow(True)


def ejes_de_meses(ax, meses):
    ax.set_xticks(range(len(meses)))
    ax.set_xticklabels([f"{NOMBRE_MES[m.month]}\n{m.year}" for m in meses], fontsize=8)


def leyenda_abajo(ax, ncol=4, manejadores=None, nombres=None):
    if manejadores is None:
        manejadores, nombres = ax.get_legend_handles_labels()
    ax.legend(manejadores, nombres, fontsize=8, ncol=ncol, loc="upper center",
              bbox_to_anchor=(0.5, -0.18), frameon=False)


def color_punto(nombre):
    return config.COLORES_PUNTO.get(nombre, "#6B7280")


def grafica_precio_por_punto(grupos, meses):
    """Comparativa 1: una línea de precio por cada punto.

    Aquí se ve de inmediato si el gas importado (Cartagena) está más caro
    que el nacional (Cusiana, Floreña) y si la diferencia crece o se achica.
    """
    fig, ax = plt.subplots(figsize=(10, 3.8))
    for nombre, tabla in grupos.items():
        serie = resumen_mensual(tabla)["precio"].reindex(meses)   # meses vacíos = NaN
        ax.plot(range(len(meses)), serie.values, marker="o", linewidth=2,
                markersize=4, label=nombre, color=color_punto(nombre))
    ejes_de_meses(ax, meses)
    ax.set_ylabel("USD/MBTU")
    estilo_basico(ax)
    leyenda_abajo(ax)
    return figura_a_png(fig)


def grafica_cantidad_por_punto(grupos, meses):
    """Comparativa 2: barras lado a lado con la cantidad de cada punto."""
    fig, ax = plt.subplots(figsize=(10, 3.8))
    n = len(grupos)
    ancho = 0.8 / n
    for i, (nombre, tabla) in enumerate(grupos.items()):
        serie = resumen_mensual(tabla)["cantidad"].reindex(meses).fillna(0) / 1000
        posiciones = [x - 0.4 + ancho * (i + 0.5) for x in range(len(meses))]
        ax.bar(posiciones, serie.values, width=ancho, label=nombre,
               color=color_punto(nombre))
    ejes_de_meses(ax, meses)
    ax.set_ylabel("Miles de MBTUD")
    estilo_basico(ax)
    leyenda_abajo(ax)
    return figura_a_png(fig)


def grafica_dispersion_puntos(grupos, mes):
    """Comparativa 3: cada círculo es una negociación del mes.

    Una fila por punto. El color dice la modalidad y el tamaño, la cantidad.
    """
    nombres = list(grupos.keys())
    fig, ax = plt.subplots(figsize=(10, 1.4 + 0.7 * len(nombres)))
    vistas = set()
    for i, nombre in enumerate(nombres):
        datos = grupos[nombre]
        datos = datos[(datos["mes"] == mes) & datos["precio"].notna()]
        for modalidad, g in datos.groupby("modalidad"):
            etiqueta = modalidad if modalidad not in vistas else None
            vistas.add(modalidad)
            ax.scatter(g["precio"], [i] * len(g), s=25 + g["cantidad"] / 300,
                       color=config.COLORES_MODALIDAD.get(modalidad, "#999999"),
                       alpha=0.8, edgecolor="#374151", linewidth=0.6, label=etiqueta)
    ax.set_yticks(range(len(nombres)))
    ax.set_yticklabels(nombres, fontsize=9)
    ax.set_ylim(len(nombres) - 0.5, -0.5)
    ax.set_xlabel("Precio (USD/MBTU)")
    estilo_basico(ax)
    ax.grid(axis="x", color="#E3E6EA", linewidth=0.8)
    if vistas:
        ax.legend(fontsize=8, ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.28),
                  frameon=False, markerscale=0.7)
    return figura_a_png(fig)


def grafica_modalidades(tabla, meses):
    """Gráfica de un punto: barras apiladas por modalidad + línea de precio.

    Es la misma idea del tablero del BEC, pero solo para ese punto.
    """
    datos = tabla[tabla["mes"].isin(meses)]
    pivote = (datos.pivot_table(index="mes", columns="modalidad",
                                values="cantidad", aggfunc="sum")
              .reindex(meses).fillna(0))
    precios = resumen_mensual(datos)["precio"].reindex(meses)

    fig, ax = plt.subplots(figsize=(10, 3.8))
    x = list(range(len(meses)))
    base = [0] * len(meses)
    for modalidad in pivote.columns:
        valores = (pivote[modalidad] / 1000).tolist()     # en miles para leer mejor
        ax.bar(x, valores, bottom=base, label=modalidad, width=0.7,
               color=config.COLORES_MODALIDAD.get(modalidad, "#999999"))
        base = [b + v for b, v in zip(base, valores)]
    # Resaltamos el mes del reporte con un borde para encontrarlo rápido.
    ax.bar(x[-1], base[-1], width=0.7, fill=False, edgecolor="#111827", linewidth=1.5)
    ax.set_ylabel("Miles de MBTUD")
    ejes_de_meses(ax, meses)
    estilo_basico(ax)

    ax2 = ax.twinx()                 # segundo eje (a la derecha) para el precio
    ax2.plot(x, precios.tolist(), color="#111827", marker="o", linewidth=2,
             label="Precio ponderado")
    ax2.set_ylabel("USD/MBTU")
    ax2.set_ylim(bottom=0)
    ax2.spines["top"].set_visible(False)

    barras, nombres = ax.get_legend_handles_labels()
    linea, nombre_linea = ax2.get_legend_handles_labels()
    leyenda_abajo(ax, manejadores=barras + linea, nombres=nombres + nombre_linea)
    return figura_a_png(fig)


# =====================================================================
# PASO 4. ESCRIBIR EL ANÁLISIS Y ARMAR EL REPORTE
# =====================================================================

def fmt_num(n):
    """1234567 -> '1.234.567' (formato colombiano)."""
    return f"{n:,.0f}".replace(",", ".")


def fmt_precio(p):
    return "ND" if pd.isna(p) else f"{p:,.2f}".replace(".", ",")


def cambio_pct(nuevo, viejo):
    if pd.isna(nuevo) or pd.isna(viejo) or viejo == 0:
        return None
    return 100 * (nuevo - viejo) / viejo


def texto_cambio(pct):
    if pct is None:
        return "sin dato para comparar"
    if abs(pct) < 0.5:
        return "se mantuvo igual"
    palabra = "subió" if pct > 0 else "bajó"
    return f"{palabra} {abs(pct):.0f} %"


def flecha(pct):
    """Una flechita para la tabla: ▲ 12 %, ▼ 5 % o —."""
    if pct is None:
        return "<span style='color:#9CA3AF'>—</span>"
    if abs(pct) < 0.5:
        return "<span style='color:#6B7280'>= 0 %</span>"
    simbolo, color = ("▲", "#B91C1C") if pct > 0 else ("▼", "#047857")
    return f"<span style='color:{color}'>{simbolo} {abs(pct):.0f} %</span>"


def analizar_punto(nombre, tabla, mes):
    """Escribe las frases de UN punto y detecta sus alertas.

    Es como un profesor que mira las notas de un estudiante y escribe
    comentarios: "este mes subió el precio", "esta modalidad dominó", etc.
    """
    frases, alertas = [], []
    mensual = resumen_mensual(tabla)
    if mes not in mensual.index:
        return [f"No hubo negociaciones registradas en {mes_bonito(mes)}."], alertas

    actual = mensual.loc[mes]
    hist = mensual.loc[mensual.index < mes].tail(config.MESES_HISTORIA)

    frases.append(
        f"Se contrataron {fmt_num(actual['cantidad'])} MBTUD en "
        f"{int(actual['negociaciones'])} negociaciones, a un precio ponderado de "
        f"{fmt_precio(actual['precio'])} USD/MBTU.")

    if (mes - 1) in mensual.index:
        ant = mensual.loc[mes - 1]
        frases.append(
            f"Frente a {mes_bonito(mes - 1)}, la cantidad "
            f"{texto_cambio(cambio_pct(actual['cantidad'], ant['cantidad']))} y el precio "
            f"{texto_cambio(cambio_pct(actual['precio'], ant['precio']))}.")
    else:
        frases.append(f"En {mes_bonito(mes - 1)} no hubo negociaciones para comparar.")

    if (mes - 12) in mensual.index:
        hace_un_anio = mensual.loc[mes - 12]
        frases.append(
            f"Frente a {mes_bonito(mes - 12)} (un año atrás), el precio "
            f"{texto_cambio(cambio_pct(actual['precio'], hace_un_anio['precio']))}.")

    if len(hist) > 0:
        prom_q, prom_p = hist["cantidad"].mean(), hist["precio"].mean()
        pct_p = cambio_pct(actual["precio"], prom_p)
        frases.append(
            f"Frente a su promedio reciente ({fmt_precio(prom_p)} USD/MBTU en los meses "
            f"con negocios), el precio {texto_cambio(pct_p)}.")
        if pct_p is not None and pct_p > config.ALERTA_PRECIO_PCT:
            alertas.append(f"{nombre}: el precio está {pct_p:.0f} % por encima de su promedio reciente.")
        if actual["cantidad"] > config.ALERTA_CANTIDAD_VECES * prom_q:
            alertas.append(f"{nombre}: la cantidad contratada es {fmt_precio(actual['cantidad'] / prom_q)[:-1]} "
                           f"veces su promedio reciente.")

    mod = resumen_por_modalidad(tabla, mes)
    lider = mod.iloc[0]
    frases.append(f"Modalidad principal: «{lider['modalidad']}» "
                  f"({lider['participacion']:.0f} % del volumen).")

    del_mes = tabla[tabla["mes"] == mes]
    if del_mes["precio"].notna().sum() > 1:
        frases.append(f"Los precios fueron desde {fmt_precio(del_mes['precio'].min())} hasta "
                      f"{fmt_precio(del_mes['precio'].max())} USD/MBTU.")
    sin_precio = int(del_mes["precio"].isna().sum())
    if sin_precio:
        frases.append(f"{sin_precio} negociación(es) sin precio publicado (ND).")
    return frases, alertas


def analisis_comparativo(grupos, mes):
    """Frases que comparan los puntos entre sí."""
    if len(grupos) < 2:
        return []
    datos = {n: resumen_mensual(t) for n, t in grupos.items()}
    del_mes = {n: d.loc[mes] for n, d in datos.items() if mes in d.index}
    frases = []
    if not del_mes:
        return [f"Ningún punto registró negociaciones en {mes_bonito(mes)}."]

    total = sum(r["cantidad"] for r in del_mes.values())
    mayor = max(del_mes, key=lambda n: del_mes[n]["cantidad"])
    frases.append(
        f"Entre los puntos seguidos se contrataron {fmt_num(total)} MBTUD; "
        f"{mayor} concentró el {100 * del_mes[mayor]['cantidad'] / total:.0f} %.")

    con_precio = {n: r["precio"] for n, r in del_mes.items() if pd.notna(r["precio"])}
    if len(con_precio) >= 2:
        caro = max(con_precio, key=con_precio.get)
        barato = min(con_precio, key=con_precio.get)
        diferencia = con_precio[caro] - con_precio[barato]
        frases.append(
            f"El punto más caro fue {caro}, con {fmt_precio(con_precio[caro])} USD/MBTU; el más "
            f"barato, {barato}, con {fmt_precio(con_precio[barato])}. La diferencia es de "
            f"{fmt_precio(diferencia)} USD/MBTU ({100 * diferencia / con_precio[barato]:.0f} % más caro).")

    sin_negocios = [n for n in grupos if n not in del_mes]
    if sin_negocios:
        frases.append("Sin negociaciones este mes: " + ", ".join(sin_negocios) + ".")
    return frases


# --- Piezas de HTML -------------------------------------------------
# Usamos estilos "en línea" (style='...') porque Gmail ignora casi todo lo demás.

CELDA = "padding:8px 10px;border-bottom:1px solid #E3E6EA"
TITULO_COL = "padding:8px 10px;font-weight:600;color:#4B5563;border-bottom:2px solid #1F3A68"


def h2(texto, arriba=32):
    return (f"<h2 style='font-family:Georgia,serif;font-size:20px;color:#1F3A68;"
            f"margin:{arriba}px 0 6px'>{texto}</h2>")


def h3(texto):
    return (f"<h3 style='font-family:Georgia,serif;font-size:16px;color:#111827;"
            f"margin:22px 0 4px'>{texto}</h3>")


def parrafo_gris(texto):
    return f"<p style='margin:0 0 10px;color:#4B5563;font-size:14px'>{texto}</p>"


def lista(frases):
    items = "".join(f"<li style='margin:5px 0'>{f}</li>" for f in frases)
    return f"<ul style='margin:0;padding-left:18px;font-size:15px;line-height:1.5'>{items}</ul>"


def imagen(src, alt):
    return f"<img src='{src}' alt='{alt}' style='width:100%;max-width:720px;margin-top:6px'>"


def tabla_comparativa_html(grupos, mes):
    """Tabla resumen: una fila por punto, con flechas de cambio."""
    filas = ""
    for nombre, tabla in grupos.items():
        mensual = resumen_mensual(tabla)
        punto = (f"<span style='display:inline-block;width:10px;height:10px;"
                 f"background:{color_punto(nombre)};margin-right:8px'></span>{nombre}")
        if mes not in mensual.index:
            filas += (f"<tr><td style='{CELDA}'>{punto}</td>"
                      f"<td style='{CELDA};color:#6B7280' colspan='5'>Sin negociaciones</td></tr>")
            continue
        r = mensual.loc[mes]
        ant = mensual.loc[mes - 1] if (mes - 1) in mensual.index else None
        dq = cambio_pct(r["cantidad"], ant["cantidad"]) if ant is not None else None
        dp = cambio_pct(r["precio"], ant["precio"]) if ant is not None else None
        lider = resumen_por_modalidad(tabla, mes).iloc[0]["modalidad"]
        filas += (f"<tr><td style='{CELDA}'>{punto}</td>"
                  f"<td style='{CELDA};text-align:right'>{fmt_num(r['cantidad'])}<br>"
                  f"<span style='font-size:12px'>{flecha(dq)}</span></td>"
                  f"<td style='{CELDA};text-align:right'>{fmt_precio(r['precio'])}<br>"
                  f"<span style='font-size:12px'>{flecha(dp)}</span></td>"
                  f"<td style='{CELDA}'>{lider}</td>"
                  f"<td style='{CELDA};text-align:right'>{int(r['negociaciones'])}</td></tr>")
    encabezado = "".join(
        f"<th style='{TITULO_COL};text-align:{a}'>{t}</th>"
        for t, a in [("Punto", "left"), ("Cantidad (MBTUD)", "right"),
                     ("Precio (USD/MBTU)", "right"), ("Modalidad principal", "left"),
                     ("Negociaciones", "right")])
    return (f"<table style='width:100%;border-collapse:collapse;font-size:14px'>"
            f"<tr>{encabezado}</tr>{filas}</table>"
            f"<p style='margin:6px 0 0;color:#6B7280;font-size:12px'>Las flechas comparan con "
            f"el mes anterior. ▲ rojo = subió, ▼ verde = bajó.</p>")


def tabla_modalidad_html(mod):
    """Tabla de un punto: una fila por modalidad."""
    filas = ""
    for _, r in mod.iterrows():
        color = config.COLORES_MODALIDAD.get(r["modalidad"], "#999999")
        filas += (
            f"<tr><td style='{CELDA}'><span style='display:inline-block;width:10px;height:10px;"
            f"background:{color};border:1px solid #9CA3AF;margin-right:8px'></span>{r['modalidad']}</td>"
            f"<td style='{CELDA};text-align:right'>{fmt_num(r['cantidad'])}</td>"
            f"<td style='{CELDA};text-align:right'>{r['participacion']:.0f}%</td>"
            f"<td style='{CELDA};text-align:right'>{fmt_precio(r['precio'])}</td>"
            f"<td style='{CELDA};text-align:right'>{r['negociaciones']}</td></tr>")
    encabezado = "".join(
        f"<th style='{TITULO_COL};text-align:{a}'>{t}</th>"
        for t, a in [("Modalidad", "left"), ("MBTUD", "right"), ("Part.", "right"),
                     ("USD/MBTU", "right"), ("Negoc.", "right")])
    return (f"<table style='width:100%;border-collapse:collapse;font-size:14px;margin-top:8px'>"
            f"<tr>{encabezado}</tr>{filas}</table>")


def armar_html(*, titulo, subtitulo, aviso, alertas, comparativo, tabla_comp,
               secciones, encontrados, otros, src, prueba):
    """Junta todas las piezas en una página HTML.

    src es una función que dice dónde está cada imagen: dentro del HTML
    (para el archivo) o pegada aparte con una etiqueta (para el correo).
    """
    partes = []
    if prueba:
        partes.append(
            "<div style='background:#FEF3C7;border:2px dashed #B45309;padding:12px 16px;"
            "margin:0 0 18px;font-weight:600;color:#92400E'>DATOS DE PRUEBA INVENTADOS. "
            "Este reporte solo sirve para ver cómo se ve; sus números no son reales.</div>")
    if aviso:
        partes.append(
            f"<div style='border-left:4px solid #6B7280;background:#F3F4F6;padding:10px 14px;"
            f"margin:0 0 18px;font-size:14px'>{aviso}</div>")
    if alertas:
        partes.append(
            "<div style='border-left:4px solid #C2410C;background:#FFF7ED;padding:12px 16px;"
            "margin:0 0 18px'><p style='margin:0 0 4px;font-weight:600;color:#9A3412'>"
            f"Para revisar</p>{lista(alertas)}</div>")

    if len(secciones) > 1:
        partes.append(h2("Comparación entre puntos", arriba=0))
        partes.append(lista(comparativo))
        partes.append(f"<div style='margin-top:14px'>{tabla_comp}</div>")
        partes.append(h3("Precio por punto"))
        partes.append(parrafo_gris("Precio promedio ponderado de cada punto, mes a mes. "
                                   "Si una línea se corta, ese mes no hubo negociaciones."))
        partes.append(imagen(src("comp_precio"), "Precio por punto"))
        partes.append(h3("Cantidad por punto"))
        partes.append(parrafo_gris("Cuánto gas se contrató en cada punto, mes a mes."))
        partes.append(imagen(src("comp_cantidad"), "Cantidad por punto"))
        partes.append(h3("Precio de cada negociación del mes"))
        partes.append(parrafo_gris("Cada círculo es una negociación; el color es la modalidad "
                                   "y el tamaño, la cantidad."))
        partes.append(imagen(src("comp_dispersion"), "Negociaciones del mes"))

    for i, (nombre, frases, mod) in enumerate(secciones):
        partes.append(h2(nombre))
        partes.append(lista(frases))
        if len(mod):
            partes.append(tabla_modalidad_html(mod))
        partes.append(imagen(src(f"punto_{i}"), f"Modalidades en {nombre}"))
        partes.append(parrafo_gris("Barras: cantidad por modalidad (eje izquierdo). "
                                   "Línea: precio ponderado (eje derecho). "
                                   "Borde negro: mes del reporte."))

    nombres_bec = "".join(
        f"<li>{n}: {', '.join(c) if c else '<i>no encontrado</i>'}</li>"
        for n, c in encontrados.items())
    otros_txt = (f"<p style='margin:4px 0 0'>Otros puntos en el archivo que no seguimos: "
                 f"{', '.join(otros)}.</p>" if otros else "")

    return f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{titulo}</title></head>
<body style="margin:0;background:#F3F4F6;font-family:Arial,Helvetica,sans-serif;color:#1F2937">
<div style="max-width:760px;margin:0 auto;background:#FFFFFF;padding:28px 28px 36px">
  <div style="border-top:6px solid #1F3A68;padding-top:14px;margin-bottom:22px">
    <h1 style="font-family:Georgia,serif;font-size:26px;margin:0;color:#111827">{titulo}</h1>
    <p style="margin:6px 0 0;color:#4B5563;font-size:14px">{subtitulo}</p>
  </div>
  {''.join(partes)}
  <div style="margin:36px 0 0;color:#6B7280;font-size:12px;line-height:1.5">
  <p style="margin:0">Nombres del BEC incluidos en cada punto:</p>
  <ul style="margin:4px 0 0;padding-left:18px">{nombres_bec}</ul>{otros_txt}
  <p style="margin:10px 0 0">Fuente: Gestor del Mercado de Gas Natural (BMC), información
  transaccional publicada en el BEC. Precio calculado como promedio ponderado por cantidad;
  puede diferir levemente del publicado por el BEC. ND = precio no disponible. Los contratos
  registrados después de la fecha de corte aparecerán en el reporte del mes siguiente.
  Generado automáticamente el {date.today():%d/%m/%Y}.</p></div>
</div></body></html>"""


# =====================================================================
# EL PROGRAMA PRINCIPAL: aquí se ejecutan los pasos en orden
# =====================================================================

def leer_opciones():
    """Lee lo que escribiste en la terminal después de 'python generar_reporte.py'."""
    lector = argparse.ArgumentParser(description="Reporte mensual de contratos de gas")
    lector.add_argument("--mes", help="mes a reportar, formato AAAA-MM (ej. 2026-09). "
                                      "Si no lo pones, usa el mes actual.")
    lector.add_argument("--solo-ultimo-dia-habil", action="store_true",
                        help="no hace nada si hoy no es el último día hábil del mes")
    lector.add_argument("--enviar", action="store_true",
                        help="envía el reporte por Gmail (necesita las claves en Secrets)")
    lector.add_argument("--prueba", action="store_true",
                        help="usa los datos INVENTADOS de la carpeta pruebas/")
    return lector.parse_args()


def main():
    opciones = leer_opciones()
    hoy = date.today()

    # El "portero": si nos pidieron trabajar solo el último día hábil y hoy
    # no lo es, el programa se despide sin hacer nada.
    if opciones.solo_ultimo_dia_habil and not hoy_es_ultimo_dia_habil(hoy):
        print(f"Hoy ({hoy:%d/%m/%Y}) no es el último día hábil del mes. No hago nada.")
        return

    mes = pd.Period(opciones.mes, freq="M") if opciones.mes else pd.Period(hoy, freq="M")
    print(f"Reporte de {mes_bonito(mes)}")

    print("PASO 1: leyendo datos...")
    archivo = ARCHIVO_PRUEBA if opciones.prueba else config.ARCHIVO_TABLA
    tabla = leer_excel_bec(archivo)
    grupos, encontrados, otros, aviso = separar_puntos(tabla)
    for nombre, filas in grupos.items():
        print(f"   {nombre}: {len(filas)} filas ({', '.join(encontrados[nombre]) or 'no encontrado'})")
    if aviso:
        print(f"   AVISO: {aviso}")

    print("PASO 2: calculando...")
    meses_graf = list(pd.period_range(end=mes, periods=config.MESES_HISTORIA + 1, freq="M"))
    secciones, alertas = [], []
    for nombre, filas in grupos.items():
        frases, alertas_punto = analizar_punto(nombre, filas, mes)
        secciones.append((nombre, frases, resumen_por_modalidad(filas, mes)))
        alertas += alertas_punto

    print("PASO 3: dibujando gráficas...")
    imagenes = {}
    if len(grupos) > 1:
        imagenes["comp_precio"] = grafica_precio_por_punto(grupos, meses_graf)
        imagenes["comp_cantidad"] = grafica_cantidad_por_punto(grupos, meses_graf)
        imagenes["comp_dispersion"] = grafica_dispersion_puntos(grupos, mes)
    for i, filas in enumerate(grupos.values()):
        imagenes[f"punto_{i}"] = grafica_modalidades(filas, meses_graf)

    print("PASO 4: escribiendo el reporte...")
    titulo_mes = mes_bonito(mes)
    piezas = dict(
        titulo=f"Contratos de gas natural: {titulo_mes}",
        subtitulo=(f"Reporte mensual · {config.MERCADO} · "
                   f"{' · '.join(grupos.keys())} · corte al {hoy:%d/%m/%Y}"),
        aviso=aviso, alertas=alertas,
        comparativo=analisis_comparativo(grupos, mes),
        tabla_comp=tabla_comparativa_html(grupos, mes),
        secciones=secciones, encontrados=encontrados, otros=otros,
        prueba=opciones.prueba)

    # Versión ARCHIVO: las imágenes van dentro del HTML como texto.
    html_archivo = armar_html(**piezas, src=lambda nombre: png_a_texto(imagenes[nombre]))
    os.makedirs(config.CARPETA_SALIDA, exist_ok=True)
    sufijo = "_PRUEBA" if opciones.prueba else ""
    ruta = os.path.join(config.CARPETA_SALIDA, f"reporte_{mes}{sufijo}.html")
    with open(ruta, "w", encoding="utf-8") as archivo_html:
        archivo_html.write(html_archivo)
    print(f"   Reporte guardado en: {ruta}")

    # PASO 5 (opcional): enviar por correo.
    if opciones.enviar:
        print("PASO 5: enviando el correo...")
        acceso = enviar_correo.datos_de_acceso()
        if acceso is None:
            print("   No encontré GMAIL_USUARIO, GMAIL_CLAVE_APP o CORREO_DESTINO. "
                  "No envié el correo.")
            raise SystemExit(1)       # avisa a GitHub que algo falló (te llega un aviso)
        usuario, clave, destino = acceso
        # Versión CORREO: imágenes aparte; el HTML las llama por su etiqueta.
        html_correo = armar_html(**piezas, src=lambda nombre: f"cid:{nombre}")
        asunto = f"Reporte mensual de gas natural: {titulo_mes}"
        if opciones.prueba:
            asunto = "[PRUEBA] " + asunto
        if alertas:
            asunto += f" ({len(alertas)} alerta{'s' if len(alertas) > 1 else ''})"
        correo = enviar_correo.armar_correo(asunto, html_correo, imagenes,
                                            remitente=usuario, destino=destino,
                                            adjunto=ruta)
        enviar_correo.enviar(correo, usuario, clave)
        print(f"   Correo enviado a: {destino}")

    print("¡Listo!")


# Esta línea significa: "si alguien ejecuta este archivo, corre main()".
if __name__ == "__main__":
    main()
