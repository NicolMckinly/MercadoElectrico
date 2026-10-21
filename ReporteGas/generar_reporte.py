# =====================================================================
# generar_reporte.py  —  LA "RECETA" DEL ROBOT
# ---------------------------------------------------------------------
# Este programa hace 4 cosas, en orden:
#   PASO 1. Leer los Excel del BEC y limpiarlos.
#   PASO 2. Calcular números importantes (totales, precios, cambios).
#   PASO 3. Dibujar gráficas.
#   PASO 4. Escribir el análisis y armar el reporte en HTML.
#
# Formas de ejecutarlo (en la terminal):
#   python generar_reporte.py                 -> reporte del mes actual
#   python generar_reporte.py --mes 2026-09   -> reporte de septiembre 2026
#   python generar_reporte.py --solo-ultimo-dia-habil
#        -> solo hace el reporte si hoy es el último día hábil del mes
#   python generar_reporte.py --enviar
#        -> además de guardarlo, lo envía por Gmail
#   (las opciones se pueden combinar; GitHub usa las dos últimas juntas)
# =====================================================================

import argparse                   # lee las opciones que escribes en la terminal (--mes, etc.)
import base64                     # convierte imágenes en texto para meterlas en el HTML
import io                         # permite guardar imágenes en memoria (sin crear archivos)
import os                         # sirve para manejar carpetas
from datetime import date         # para saber la fecha de hoy

import matplotlib
matplotlib.use("Agg")             # dibuja sin abrir ventanas (necesario en servidores)
import matplotlib.pyplot as plt   # la "caja de colores" para hacer gráficas
import pandas as pd               # la herramienta para trabajar tablas, como un Excel dentro de Python

import config                     # nuestro panel de control (config.py)
import enviar_correo              # nuestro cartero (enviar_correo.py)
from calendario import hoy_es_ultimo_dia_habil   # nuestro calendario (calendario.py)

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
# PASO 1. LEER Y LIMPIAR LOS DATOS
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


def filtrar_orinoquia(tabla):
    """Se queda solo con los puntos de entrega de la Orinoquía.

    Devuelve la tabla filtrada y un texto que explica qué se usó.
    Si el archivo solo trae "Nacional", devuelve todo y lo avisa.
    """
    puntos = tabla["punto"].astype(str).unique()
    if list(puntos) == ["Nacional"]:
        return tabla, ("Este archivo solo trae el total Nacional (sin detalle por "
                       "punto de entrega). Para ver la Orinoquía, exporta la "
                       "pestaña «Puntos» del BEC.")
    patron = "|".join(config.PUNTOS_ORINOQUIA)
    filtrada = tabla[tabla["punto"].astype(str).str.contains(patron, case=False)]
    encontrados = sorted(filtrada["punto"].unique())
    return filtrada, "Puntos de entrega incluidos: " + ", ".join(encontrados)


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
    """Una fila por mes: cantidad total y precio ponderado."""
    filas = []
    for mes, grupo in tabla.groupby("mes"):
        filas.append({"mes": mes,
                      "cantidad": grupo["cantidad"].sum(),
                      "precio": precio_ponderado(grupo)})
    return pd.DataFrame(filas).set_index("mes").sort_index()


def resumen_por_modalidad(tabla, mes):
    """Para un mes: cantidad, precio y participación (%) de cada modalidad."""
    del_mes = tabla[tabla["mes"] == mes]
    filas = []
    for modalidad, grupo in del_mes.groupby("modalidad"):
        filas.append({"modalidad": modalidad,
                      "cantidad": grupo["cantidad"].sum(),
                      "precio": precio_ponderado(grupo),
                      "negociaciones": len(grupo)})
    res = pd.DataFrame(filas).sort_values("cantidad", ascending=False)
    res["participacion"] = 100 * res["cantidad"] / res["cantidad"].sum()
    return res


# =====================================================================
# PASO 3. DIBUJAR LAS GRÁFICAS
# =====================================================================

def figura_a_png(fig):
    """Convierte una gráfica en una imagen PNG guardada en memoria.

    Después la usamos de dos formas:
      - en el ARCHIVO, convertida a texto (base64) dentro del HTML;
      - en el CORREO, pegada como imagen aparte (Gmail no muestra la otra forma).
    """
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


def etiqueta_mes(periodo):
    return f"{NOMBRE_MES[periodo.month]}\n{periodo.year}"


def grafica_cantidad_y_precio(tabla, meses):
    """Gráfica 1: barras apiladas por modalidad + línea de precio.

    Es la misma idea del tablero del BEC, pero solo con los últimos meses.
    """
    datos = tabla[tabla["mes"].isin(meses)]
    pivote = (datos.pivot_table(index="mes", columns="modalidad",
                                values="cantidad", aggfunc="sum")
              .reindex(meses).fillna(0))
    precios = resumen_mensual(datos)["precio"].reindex(meses)

    fig, ax = plt.subplots(figsize=(10, 4.6))
    x = range(len(meses))
    base = [0] * len(meses)
    for modalidad in pivote.columns:
        valores = (pivote[modalidad] / 1000).tolist()     # en miles para leer mejor
        ax.bar(x, valores, bottom=base, label=modalidad, width=0.7,
               color=config.COLORES_MODALIDAD.get(modalidad, "#999999"))
        base = [b + v for b, v in zip(base, valores)]
    # Resaltamos el mes del reporte con un borde para encontrarlo rápido.
    i = len(meses) - 1
    ax.bar(i, base[i], width=0.7, fill=False, edgecolor="#111827", linewidth=1.5)
    ax.set_ylabel("Cantidad (miles de MBTUD)")
    ax.set_xticks(list(x))
    ax.set_xticklabels([etiqueta_mes(m) for m in meses], fontsize=8)
    estilo_basico(ax)

    ax2 = ax.twinx()                 # segundo eje (a la derecha) para el precio
    ax2.plot(list(x), precios.tolist(), color="#111827", marker="o", linewidth=2,
             label="Precio ponderado")
    ax2.set_ylabel("USD/MBTU")
    ax2.set_ylim(bottom=0)
    ax2.spines["top"].set_visible(False)

    barras, nombres = ax.get_legend_handles_labels()
    linea, nombre_linea = ax2.get_legend_handles_labels()
    ax.legend(barras + linea, nombres + nombre_linea, fontsize=8, ncol=4,
              loc="upper center", bbox_to_anchor=(0.5, -0.16), frameon=False)
    return figura_a_png(fig)


def grafica_precio_por_modalidad(tabla, meses):
    """Gráfica 2: una línea de precio por cada modalidad importante."""
    datos = tabla[tabla["mes"].isin(meses)]
    fig, ax = plt.subplots(figsize=(10, 3.8))
    x_de_mes = {m: i for i, m in enumerate(meses)}
    # Solo modalidades con precio en al menos 3 meses (si no, la línea no dice nada).
    for modalidad, grupo in datos.groupby("modalidad"):
        serie = grupo.groupby("mes").apply(precio_ponderado, include_groups=False)
        if serie.notna().sum() < 3:
            continue
        # Rellenamos los meses sin negociaciones con "vacío" (NaN). Así la
        # línea se corta en esos meses en vez de inventar un camino recto.
        serie = serie.reindex(meses)
        color = config.COLORES_MODALIDAD.get(modalidad, "#999999")
        if modalidad == "Con Interrupciones":
            color = "#7A7F87"        # el gris claro casi no se ve en una línea
        if modalidad == "Opción de Compra":
            color = "#C9A800"        # el amarillo puro casi no se ve sobre blanco
        ax.plot([x_de_mes[m] for m in serie.index], serie.values, marker="o",
                linewidth=1.8, markersize=4, label=modalidad, color=color)
    ax.set_xticks(range(len(meses)))
    ax.set_xticklabels([etiqueta_mes(m) for m in meses], fontsize=8)
    ax.set_ylabel("USD/MBTU")
    estilo_basico(ax)
    ax.legend(fontsize=8, ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.18),
              frameon=False)
    return figura_a_png(fig)


def grafica_dispersion(tabla, mes):
    """Gráfica 3: cada punto es una negociación del mes.

    Sirve para ver si todos pagaron parecido o si hubo precios muy distintos.
    El tamaño del punto muestra la cantidad negociada.
    """
    datos = tabla[(tabla["mes"] == mes) & tabla["precio"].notna()]
    modalidades = list(datos.groupby("modalidad")["cantidad"].sum()
                       .sort_values(ascending=False).index)
    # La altura crece con el número de modalidades para que no quede apretada.
    fig, ax = plt.subplots(figsize=(10, 1.2 + 0.55 * len(modalidades)))
    for i, modalidad in enumerate(modalidades):
        g = datos[datos["modalidad"] == modalidad]
        color = config.COLORES_MODALIDAD.get(modalidad, "#999999")
        ax.scatter(g["precio"], [i] * len(g), s=20 + g["cantidad"] / 300,
                   color=color, alpha=0.75, edgecolor="#374151", linewidth=0.6)
    ax.set_yticks(range(len(modalidades)))
    ax.set_yticklabels(modalidades, fontsize=9)
    ax.set_xlabel("Precio (USD/MBTU)")
    ax.invert_yaxis()
    estilo_basico(ax)
    ax.grid(axis="x", color="#E3E6EA", linewidth=0.8)
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
    palabra = "subió" if pct > 0 else "bajó"
    return f"{palabra} {abs(pct):.0f} %".replace(".", ",")


def escribir_analisis(mensual, mod_mes, mes, tabla):
    """Escribe frases automáticas a partir de los números.

    Es como un profesor que mira las notas y escribe comentarios:
    "este mes subió el precio", "esta modalidad dominó", etc.
    """
    frases, alertas = [], []
    actual = mensual.loc[mes]
    hist = mensual.loc[mensual.index < mes].tail(config.MESES_HISTORIA)

    # 1. Lo principal: cuánto y a qué precio.
    frases.append(
        f"En {mes_bonito(mes)} se contrataron {fmt_num(actual['cantidad'])} MBTUD "
        f"a un precio ponderado de {fmt_precio(actual['precio'])} USD/MBTU.")

    # 2. Contra el mes anterior.
    if (mes - 1) in mensual.index:
        ant = mensual.loc[mes - 1]
        frases.append(
            f"Frente a {mes_bonito(mes - 1)}, la cantidad "
            f"{texto_cambio(cambio_pct(actual['cantidad'], ant['cantidad']))} y el precio "
            f"{texto_cambio(cambio_pct(actual['precio'], ant['precio']))}.")

    # 3. Contra el mismo mes del año pasado (mes - 12).
    #    Sirve porque algunos meses siempre se mueven distinto (temporadas).
    if (mes - 12) in mensual.index:
        hace_un_anio = mensual.loc[mes - 12]
        frases.append(
            f"Frente a {mes_bonito(mes - 12)} (un año atrás), la cantidad "
            f"{texto_cambio(cambio_pct(actual['cantidad'], hace_un_anio['cantidad']))} y el precio "
            f"{texto_cambio(cambio_pct(actual['precio'], hace_un_anio['precio']))}.")

    # 4. Contra el promedio de los meses previos (y alertas).
    if len(hist) > 0:
        prom_q, prom_p = hist["cantidad"].mean(), hist["precio"].mean()
        pct_p = cambio_pct(actual["precio"], prom_p)
        frases.append(
            f"El promedio de los {len(hist)} meses previos fue {fmt_num(prom_q)} MBTUD "
            f"y {fmt_precio(prom_p)} USD/MBTU; frente a eso, el precio de este mes "
            f"{texto_cambio(pct_p)}.")
        if pct_p is not None and pct_p > config.ALERTA_PRECIO_PCT:
            alertas.append(f"El precio está {pct_p:.0f} % por encima de su promedio reciente.")
        if actual["cantidad"] > config.ALERTA_CANTIDAD_VECES * prom_q:
            alertas.append(f"La cantidad contratada es {actual['cantidad'] / prom_q:.1f} veces "
                           f"el promedio reciente: hubo una contratación inusualmente grande.")

    # 5. Qué modalidad dominó y cuál fue la más cara / barata.
    lider = mod_mes.iloc[0]
    frases.append(
        f"La modalidad dominante fue «{lider['modalidad']}», con el "
        f"{lider['participacion']:.0f} % del volumen.")
    con_precio = mod_mes.dropna(subset=["precio"])
    if len(con_precio) > 1:
        cara = con_precio.loc[con_precio["precio"].idxmax()]
        barata = con_precio.loc[con_precio["precio"].idxmin()]
        frases.append(
            f"La más cara fue «{cara['modalidad']}» ({fmt_precio(cara['precio'])} USD/MBTU) "
            f"y la más barata «{barata['modalidad']}» ({fmt_precio(barata['precio'])} USD/MBTU).")

    # 6. Rango de precios y negociaciones sin precio.
    del_mes = tabla[tabla["mes"] == mes]
    sin_precio = int(del_mes["precio"].isna().sum())
    frases.append(
        f"Los precios individuales fueron desde {fmt_precio(del_mes['precio'].min())} "
        f"hasta {fmt_precio(del_mes['precio'].max())} USD/MBTU en {len(del_mes)} negociaciones"
        + (f" ({sin_precio} sin precio publicado)." if sin_precio else "."))
    return frases, alertas


def tabla_html(mod):
    """Convierte el resumen por modalidad en una tabla HTML."""
    filas = ""
    for _, r in mod.iterrows():
        color = config.COLORES_MODALIDAD.get(r["modalidad"], "#999999")
        filas += (
            "<tr>"
            f"<td style='padding:8px 10px;border-bottom:1px solid #E3E6EA'>"
            f"<span style='display:inline-block;width:10px;height:10px;background:{color};"
            f"border:1px solid #9CA3AF;margin-right:8px'></span>{r['modalidad']}</td>"
            f"<td style='padding:8px 10px;border-bottom:1px solid #E3E6EA;text-align:right'>{fmt_num(r['cantidad'])}</td>"
            f"<td style='padding:8px 10px;border-bottom:1px solid #E3E6EA;text-align:right'>{r['participacion']:.0f}%</td>"
            f"<td style='padding:8px 10px;border-bottom:1px solid #E3E6EA;text-align:right'>{fmt_precio(r['precio'])}</td>"
            f"<td style='padding:8px 10px;border-bottom:1px solid #E3E6EA;text-align:right'>{r['negociaciones']}</td>"
            "</tr>")
    encabezado = "".join(
        f"<th style='padding:8px 10px;text-align:{a};font-weight:600;color:#4B5563;"
        f"border-bottom:2px solid #1F3A68'>{t}</th>"
        for t, a in [("Modalidad", "left"), ("Cantidad (MBTUD)", "right"),
                     ("Participación", "right"), ("Precio (USD/MBTU)", "right"),
                     ("Negociaciones", "right")])
    return (f"<table style='width:100%;border-collapse:collapse;font-size:14px'>"
            f"<tr>{encabezado}</tr>{filas}</table>")


def armar_html(titulo, subtitulo, nota_fuente, frases, alertas, tabla_mod,
               img1, img2, img3, mes_ultimo):
    # img1, img2, img3 son la "dirección" de cada imagen: puede ser el
    # texto base64 (para el archivo) o "cid:grafica1" (para el correo).
    """Junta todo en una página HTML.

    Usamos estilos "en línea" (style='...') porque los programas de correo
    como Gmail ignoran casi todo lo demás. Así el reporte se verá bien
    cuando te llegue por email (Etapa 2).
    """
    mes_txt = mes_bonito(mes_ultimo)
    caja_alertas = ""
    if alertas:
        items = "".join(f"<li style='margin:4px 0'>{a}</li>" for a in alertas)
        caja_alertas = (
            "<div style='border-left:4px solid #C2410C;background:#FFF7ED;padding:12px 16px;"
            "margin:0 0 20px'><p style='margin:0 0 4px;font-weight:600;color:#9A3412'>"
            f"Para revisar</p><ul style='margin:0;padding-left:18px'>{items}</ul></div>")
    analisis = "".join(f"<li style='margin:6px 0'>{f}</li>" for f in frases)

    def bloque(titulo_g, explicacion, img):
        return (f"<h2 style='font-family:Georgia,serif;font-size:19px;color:#1F3A68;"
                f"margin:32px 0 4px'>{titulo_g}</h2>"
                f"<p style='margin:0 0 10px;color:#4B5563;font-size:14px'>{explicacion}</p>"
                f"<img src='{img}' style='width:100%;max-width:720px' "
                f"alt='{titulo_g}'>")

    return f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{titulo}</title></head>
<body style="margin:0;background:#F3F4F6;font-family:Arial,Helvetica,sans-serif;color:#1F2937">
<div style="max-width:760px;margin:0 auto;background:#FFFFFF;padding:28px 28px 36px">
  <div style="border-top:6px solid #1F3A68;padding-top:14px">
    <h1 style="font-family:Georgia,serif;font-size:26px;margin:0;color:#111827">{titulo}</h1>
    <p style="margin:6px 0 0;color:#4B5563;font-size:14px">{subtitulo}</p>
    <p style="margin:6px 0 22px;color:#6B7280;font-size:12px">{nota_fuente}</p>
  </div>
  {caja_alertas}
  <h2 style="font-family:Georgia,serif;font-size:19px;color:#1F3A68;margin:0 0 6px">Análisis</h2>
  <ul style="margin:0;padding-left:18px;font-size:15px;line-height:1.5">{analisis}</ul>

  <h2 style="font-family:Georgia,serif;font-size:19px;color:#1F3A68;margin:32px 0 8px">Detalle por modalidad, {mes_txt}</h2>
  {tabla_mod}

  {bloque("Cantidad contratada y precio", "Barras: cuánto gas se contrató cada mes, por tipo de contrato (eje izquierdo). Línea negra: precio promedio ponderado (eje derecho). La barra con borde negro es el mes de este reporte.", img1)}
  {bloque("Precio por modalidad", "Cómo se movió el precio de cada tipo de contrato. Solo aparecen las modalidades con precio en al menos 3 meses.", img2)}
  {bloque(f"Precios de cada negociación, {mes_txt}", "Cada círculo es una negociación; los más grandes movieron más gas. Si los círculos están lejos entre sí, hubo precios muy distintos para la misma modalidad.", img3)}

  <p style="margin:32px 0 0;color:#6B7280;font-size:12px;line-height:1.5">
  Fuente: Gestor del Mercado de Gas Natural (BMC), información transaccional publicada en el BEC.
  Precio calculado como promedio ponderado por cantidad; puede diferir levemente del publicado por el BEC.
  ND = precio no disponible. Los contratos que se registren en el BEC después de la fecha de corte aparecerán en el reporte del mes siguiente. Generado automáticamente el {date.today():%d/%m/%Y}.</p>
</div></body></html>"""


# =====================================================================
# EL PROGRAMA PRINCIPAL: aquí se ejecutan los pasos en orden
# =====================================================================

def leer_opciones():
    """Lee lo que escribiste en la terminal después de 'python generar_reporte.py'."""
    lector = argparse.ArgumentParser(description="Reporte mensual de contratos de gas")
    lector.add_argument("--mes", help="mes a reportar, en formato AAAA-MM (ej. 2026-09). "
                                      "Si no lo pones, usa el mes actual.")
    lector.add_argument("--solo-ultimo-dia-habil", action="store_true",
                        help="no hace nada si hoy no es el último día hábil del mes")
    lector.add_argument("--enviar", action="store_true",
                        help="envía el reporte por Gmail (necesita las claves en Secrets)")
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
    tabla = leer_excel_bec(config.ARCHIVO_TABLA)
    tabla, nota_puntos = filtrar_orinoquia(tabla)
    print(f"   {len(tabla)} filas leídas. {nota_puntos}")

    print("PASO 2: calculando...")
    mensual = resumen_mensual(tabla)
    if mes not in mensual.index:
        print(f"   No hay datos de {mes_bonito(mes)} en el archivo. Revisa la descarga.")
        raise SystemExit(1)           # marca la ejecución en rojo en GitHub para que te enteres
    mod_mes = resumen_por_modalidad(tabla, mes)
    # Los meses de las gráficas: el del reporte y los 12 anteriores.
    meses_graf = list(pd.period_range(end=mes, periods=config.MESES_HISTORIA + 1, freq="M"))

    print("PASO 3: dibujando gráficas...")
    imagenes = {
        "grafica1": grafica_cantidad_y_precio(tabla, meses_graf),
        "grafica2": grafica_precio_por_modalidad(tabla, meses_graf),
        "grafica3": grafica_dispersion(tabla, mes),
    }

    print("PASO 4: escribiendo el reporte...")
    frases, alertas = escribir_analisis(mensual, mod_mes, mes, tabla)
    titulo_mes = mes_bonito(mes)
    textos = dict(
        titulo=f"Contratos de gas natural: {titulo_mes}",
        subtitulo=f"Reporte mensual · {config.MERCADO} · datos del BEC con corte al {hoy:%d/%m/%Y}",
        nota_fuente=nota_puntos,
        frases=frases, alertas=alertas, tabla_mod=tabla_html(mod_mes), mes_ultimo=mes)

    # Versión ARCHIVO: imágenes dentro del HTML como texto.
    html_archivo = armar_html(**textos, **{f"img{i}": png_a_texto(imagenes[f"grafica{i}"])
                                           for i in (1, 2, 3)})
    os.makedirs(config.CARPETA_SALIDA, exist_ok=True)
    ruta = os.path.join(config.CARPETA_SALIDA, f"reporte_{mes}.html")
    with open(ruta, "w", encoding="utf-8") as archivo:
        archivo.write(html_archivo)
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
        # Versión CORREO: las imágenes van aparte, el HTML las llama por su etiqueta.
        html_correo = armar_html(**textos, img1="cid:grafica1", img2="cid:grafica2",
                                 img3="cid:grafica3")
        asunto = f"Reporte mensual de gas natural: {titulo_mes}"
        if alertas:
            asunto += f" ({len(alertas)} alerta{'s' if len(alertas) > 1 else ''})"
        correo = enviar_correo.armar_correo(asunto, html_correo, imagenes,
                                            remitente=usuario, destino=destino,
                                            adjunto=ruta)
        try:
            enviar_correo.enviar(correo, usuario, clave)
        except enviar_correo.smtplib.SMTPAuthenticationError:
            print("   Gmail rechazó el usuario o la clave. Revisa que GMAIL_USUARIO sea el "
                  "correo completo y que GMAIL_CLAVE_APP sea la contraseña de aplicación "
                  "de 16 letras (no tu contraseña normal), sin espacios.")
            raise SystemExit(1)
        print(f"   Correo enviado a: {destino}")

    print("¡Listo!")


# Esta línea significa: "si alguien ejecuta este archivo, corre main()".
if __name__ == "__main__":
    main()
