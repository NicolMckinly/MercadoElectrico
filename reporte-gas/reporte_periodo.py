# =====================================================================
# reporte_periodo.py  —  INFORME DE UN PERIODO EN LÍNEA DE TIEMPO
# ---------------------------------------------------------------------
# Toma varios meses seguidos (por ejemplo septiembre y octubre) y los
# pone "pegados" en una sola línea de tiempo, para ver cómo evolucionó
# todo de un mes al otro.
#
#   - Mercado secundario: día por día y semana a semana (el BEC lo
#     publica diario).
#   - Mercado primario: cada negociación de cada mes (el BEC lo publica
#     por mes, no por día).
#   - Comparación mes contra mes y primario contra secundario.
#
# Reutiliza las piezas de generar_reporte.py y reporte_semanal_secundario.py.
#
# Uso:
#   python reporte_periodo.py --desde 2026-09 --hasta 2026-10
#   python reporte_periodo.py --desde 2026-09 --hasta 2026-10 --enviar
# =====================================================================

import argparse
import os
from datetime import date

import matplotlib.pyplot as plt
import pandas as pd

import config
import enviar_correo
from generar_reporte import (
    CELDA, MES_LARGO, NOMBRE_MES, TITULO_COL, armar_html, cambio_pct, color_punto,
    contar_negociaciones, estilo_basico, figura_a_png, flecha, fmt_num, fmt_precio, h1_mercado,
    h2, h3, imagen, leer_carpeta, leer_excel_bec, leer_excel_secundario, leyenda_abajo, lista,
    parrafo_gris, png_a_texto, precio_ponderado, separar_puntos, texto_cambio,
)
from reporte_semanal_secundario import etiqueta_corta, semana_bonita


def nombre_periodo(meses):
    """[sep 2026, oct 2026] -> 'septiembre y octubre de 2026'."""
    nombres = [MES_LARGO[m.month] for m in meses]
    anios = {m.year for m in meses}
    if len(anios) == 1:
        texto = nombres[0] if len(nombres) == 1 else ", ".join(nombres[:-1]) + " y " + nombres[-1]
        return f"{texto} de {meses[0].year}"
    return " y ".join(f"{MES_LARGO[m.month]} de {m.year}" for m in meses)


def resumen_mes(tabla, mes):
    """Cantidad, precio, negociaciones, mín., máx. y margen de un punto en un mes."""
    d = tabla[tabla["mes"] == mes]
    if not len(d):
        return None
    r = {"cantidad": d["cantidad"].sum(), "precio": precio_ponderado(d),
         "negociaciones": contar_negociaciones(d)}
    if "precio_min" in d.columns:
        r["minimo"], r["maximo"] = d["precio_min"].min(), d["precio_max"].max()
        con = d[d["intermediacion"].notna()]
        r["margen"] = ((con["cantidad"] * con["intermediacion"]).sum() / con["cantidad"].sum()
                       if con["cantidad"].sum() > 0 else float("nan"))
    return r


# =====================================================================
# Gráficas en línea de tiempo
# =====================================================================

def marcar_meses(ax, dias, meses):
    """Pone una línea vertical donde empieza cada mes y su nombre arriba."""
    for i, mes in enumerate(meses):
        inicio = mes.start_time.normalize()
        x = (inicio - dias[0]).days
        if i > 0:
            ax.axvline(x - 0.5, color="#111827", linewidth=1.2, linestyle=":")
        fin = min(mes.end_time.normalize(), dias[-1])
        centro = (x + (fin - dias[0]).days) / 2
        ax.text(centro, 1.02, MES_LARGO[mes.month].capitalize(), transform=ax.get_xaxis_transform(),
                ha="center", va="bottom", fontsize=10, color="#1F3A68", fontweight="bold")
        if i % 2 == 1:                                   # sombreamos un mes sí y otro no
            ax.axvspan(x - 0.5, (fin - dias[0]).days + 0.5, color="#F3F4F6", zorder=0)


def ejes_de_dias(ax, dias):
    """Etiquetas del eje: un número cada 3 días para que se lea bien."""
    posiciones = [i for i, d in enumerate(dias) if d.day % 3 == 1]
    ax.set_xticks(posiciones)
    ax.set_xticklabels([str(dias[i].day) for i in posiciones], fontsize=8)
    ax.set_xlim(-0.5, len(dias) - 0.5)


def grafica_precio_diario(grupos, dias, meses):
    """Precio ponderado de cada día, para cada punto, a lo largo de todo el periodo."""
    fig, ax = plt.subplots(figsize=(10, 4))
    for nombre, tabla in grupos.items():
        diario = tabla.groupby(tabla["fecha"].dt.normalize()).apply(precio_ponderado,
                                                                     include_groups=False)
        serie = diario.reindex(dias)
        ax.plot(range(len(dias)), serie.values, marker="o", markersize=3, linewidth=1.4,
                label=nombre, color=color_punto(nombre))
    marcar_meses(ax, dias, meses)
    ejes_de_dias(ax, dias)
    ax.set_ylabel("USD/MBTU")
    estilo_basico(ax)
    leyenda_abajo(ax)
    return figura_a_png(fig)


def grafica_cantidad_diaria(grupos, dias, meses):
    """Cantidad negociada cada día (barras apiladas por punto)."""
    fig, ax = plt.subplots(figsize=(10, 3.6))
    base = [0.0] * len(dias)
    for nombre, tabla in grupos.items():
        diario = tabla.groupby(tabla["fecha"].dt.normalize())["cantidad"].sum()
        valores = (diario.reindex(dias).fillna(0) / 1000).tolist()
        ax.bar(range(len(dias)), valores, bottom=base, width=0.8, label=nombre,
               color=color_punto(nombre))
        base = [b + v for b, v in zip(base, valores)]
    marcar_meses(ax, dias, meses)
    ejes_de_dias(ax, dias)
    ax.set_ylabel("Miles de MBTUD")
    estilo_basico(ax)
    leyenda_abajo(ax)
    return figura_a_png(fig)


def grafica_precio_semanal(grupos, semanas):
    """Precio ponderado semana a semana (suaviza los saltos de día a día)."""
    fig, ax = plt.subplots(figsize=(10, 3.6))
    for nombre, tabla in grupos.items():
        sem = tabla.copy()
        sem["semana"] = sem["fecha"].dt.to_period("W-SUN")
        serie = sem.groupby("semana").apply(precio_ponderado, include_groups=False).reindex(semanas)
        ax.plot(range(len(semanas)), serie.values, marker="o", linewidth=2, markersize=5,
                label=nombre, color=color_punto(nombre))
    ax.set_xticks(range(len(semanas)))
    ax.set_xticklabels([etiqueta_corta(s) for s in semanas], fontsize=8)
    ax.set_ylabel("USD/MBTU")
    estilo_basico(ax)
    leyenda_abajo(ax)
    return figura_a_png(fig)


# =====================================================================
# Tablas y frases
# =====================================================================

def tabla_meses_html(grupos, meses, mercado):
    """Una fila por punto: cada mes del periodo y el cambio del primero al último."""
    encabezado = [("Punto", "left")]
    for m in meses:
        encabezado.append((f"{MES_LARGO[m.month].capitalize()}<br>precio · cantidad", "right"))
    encabezado.append(("Cambio de precio", "right"))
    filas = ""
    for nombre, tabla in grupos.items():
        punto = (f"<span style='display:inline-block;width:10px;height:10px;"
                 f"background:{color_punto(nombre)};margin-right:8px'></span>{nombre}")
        celdas = ""
        datos = [resumen_mes(tabla, m) for m in meses]
        for r in datos:
            celdas += (f"<td style='{CELDA};text-align:right'>"
                       + (f"{fmt_precio(r['precio'])}<br><span style='font-size:12px;color:#6B7280'>"
                          f"{fmt_num(r['cantidad'])} MBTUD</span>" if r else
                          "<span style='color:#9CA3AF'>sin negocios</span>") + "</td>")
        cambio = (cambio_pct(datos[-1]["precio"], datos[0]["precio"])
                  if datos[0] and datos[-1] else None)
        filas += (f"<tr><td style='{CELDA}'>{punto}</td>{celdas}"
                  f"<td style='{CELDA};text-align:right'>{flecha(cambio)}</td></tr>")
    th = "".join(f"<th style='{TITULO_COL};text-align:{a}'>{t}</th>" for t, a in encabezado)
    return (f"<table style='width:100%;border-collapse:collapse;font-size:14px;margin-top:8px'>"
            f"<tr>{th}</tr>{filas}</table>"
            f"<p style='margin:6px 0 0;color:#6B7280;font-size:12px'>{mercado}. Precios en "
            f"USD/MBTU. El cambio compara el primer mes con el último.</p>")


def tabla_semanas_html(grupos, semanas, dias):
    """Semana a semana: precio y cantidad de cada punto.

    La primera y la última semana se recortan al periodo (por ejemplo, si
    el periodo empieza un martes, la primera semana va de martes a domingo).
    """
    th = f"<th style='{TITULO_COL};text-align:left'>Semana</th>" + "".join(
        f"<th style='{TITULO_COL};text-align:right'>{n}</th>" for n in grupos)
    filas = ""
    for s in semanas:
        celdas = ""
        for tabla in grupos.values():
            d = tabla[tabla["fecha"].dt.to_period("W-SUN") == s]
            celdas += (f"<td style='{CELDA};text-align:right'>"
                       + (f"{fmt_precio(precio_ponderado(d))}<br><span style='font-size:12px;"
                          f"color:#6B7280'>{fmt_num(d['cantidad'].sum())}</span>" if len(d) else
                          "<span style='color:#9CA3AF'>—</span>") + "</td>")
        ini = max(s.start_time.normalize(), dias[0])
        fin = min(s.end_time.normalize(), dias[-1])
        filas += (f"<tr><td style='{CELDA}'>{ini.day} {NOMBRE_MES[ini.month]} – "
                  f"{fin.day} {NOMBRE_MES[fin.month]}</td>{celdas}</tr>")
    return (f"<table style='width:100%;border-collapse:collapse;font-size:13px;margin-top:8px'>"
            f"<tr>{th}</tr>{filas}</table>"
            f"<p style='margin:6px 0 0;color:#6B7280;font-size:12px'>Arriba: precio ponderado "
            f"(USD/MBTU). Abajo: cantidad (MBTUD).</p>")


def frases_secundario(nombre, tabla, meses):
    """Lo más importante de un punto en el secundario durante el periodo."""
    datos = [resumen_mes(tabla, m) for m in meses]
    frases = []
    if datos[0] and datos[-1]:
        primero, ultimo = MES_LARGO[meses[0].month], MES_LARGO[meses[-1].month]
        frases.append(
            f"De {primero} a {ultimo}, el precio pasó de {fmt_precio(datos[0]['precio'])} a "
            f"{fmt_precio(datos[-1]['precio'])} USD/MBTU ({texto_cambio(cambio_pct(datos[-1]['precio'], datos[0]['precio']))}) "
            f"y la cantidad de {fmt_num(datos[0]['cantidad'])} a {fmt_num(datos[-1]['cantidad'])} MBTUD "
            f"({texto_cambio(cambio_pct(datos[-1]['cantidad'], datos[0]['cantidad']))}).")
        if pd.notna(datos[0].get("margen")) and pd.notna(datos[-1].get("margen")):
            frases.append(f"El margen de intermediación pasó de {fmt_precio(datos[0]['margen'])} a "
                          f"{fmt_precio(datos[-1]['margen'])} USD/MBTU.")
    diario = tabla.groupby(tabla["fecha"].dt.normalize()).apply(
        lambda d: pd.Series({"precio": precio_ponderado(d), "cantidad": d["cantidad"].sum(),
                             "maximo": d["precio_max"].max()}), include_groups=False)
    if len(diario):
        caro = diario["precio"].idxmax() if diario["precio"].notna().any() else None
        lleno = diario["cantidad"].idxmax()
        if caro is not None:
            frases.append(f"El día más caro fue el {caro.day} de {MES_LARGO[caro.month]} "
                          f"({fmt_precio(diario.loc[caro, 'precio'])} USD/MBTU en promedio).")
        frases.append(f"El día de más volumen fue el {lleno.day} de {MES_LARGO[lleno.month]} "
                      f"({fmt_num(diario.loc[lleno, 'cantidad'])} MBTUD).")
        if diario["maximo"].notna().any():
            tope = diario["maximo"].idxmax()
            frases.append(f"El precio más alto pagado fue {fmt_precio(diario.loc[tope, 'maximo'])} "
                          f"USD/MBTU, el {tope.day} de {MES_LARGO[tope.month]}.")
    return frases or ["Sin negociaciones en el periodo."]


def tabla_negociaciones_primario(grupos, meses):
    """Cada negociación del primario en el periodo (el BEC no da el día, solo el mes)."""
    filas = ""
    for mes in meses:
        for nombre, tabla in grupos.items():
            for _, r in tabla[tabla["mes"] == mes].sort_values("cantidad", ascending=False).iterrows():
                filas += (f"<tr><td style='{CELDA}'>{MES_LARGO[mes.month].capitalize()}</td>"
                          f"<td style='{CELDA}'><span style='display:inline-block;width:10px;"
                          f"height:10px;background:{color_punto(nombre)};margin-right:8px'></span>"
                          f"{nombre}</td><td style='{CELDA}'>{r['modalidad']}</td>"
                          f"<td style='{CELDA};text-align:right'>{fmt_num(r['cantidad'])}</td>"
                          f"<td style='{CELDA};text-align:right'>{fmt_precio(r['precio'])}</td></tr>")
    if not filas:
        return parrafo_gris("No hubo negociaciones en el primario en estos puntos.")
    th = "".join(f"<th style='{TITULO_COL};text-align:{a}'>{t}</th>" for t, a in
                 [("Mes", "left"), ("Punto", "left"), ("Modalidad", "left"),
                  ("MBTUD", "right"), ("USD/MBTU", "right")])
    return (f"<table style='width:100%;border-collapse:collapse;font-size:14px;margin-top:8px'>"
            f"<tr>{th}</tr>{filas}</table>")


def tabla_cruce_html(gp, gs, meses):
    """Primario vs. secundario, mes por mes."""
    nombres = list(gp) + [n for n in gs if n not in gp]
    th = f"<th style='{TITULO_COL};text-align:left'>Punto</th>"
    for m in meses:
        mm = MES_LARGO[m.month].capitalize()
        th += (f"<th style='{TITULO_COL};text-align:right'>{mm}<br>primario</th>"
               f"<th style='{TITULO_COL};text-align:right'>{mm}<br>secundario</th>")
    filas = ""
    for nombre in nombres:
        celdas = ""
        for m in meses:
            for g in (gp, gs):
                r = resumen_mes(g[nombre], m) if nombre in g else None
                celdas += (f"<td style='{CELDA};text-align:right'>"
                           + (fmt_precio(r["precio"]) if r else "<span style='color:#9CA3AF'>—</span>")
                           + "</td>")
        filas += f"<tr><td style='{CELDA}'>{nombre}</td>{celdas}</tr>"
    return (f"<table style='width:100%;border-collapse:collapse;font-size:13px;margin-top:8px'>"
            f"<tr>{th}</tr>{filas}</table>"
            f"<p style='margin:6px 0 0;color:#6B7280;font-size:12px'>Precio ponderado en USD/MBTU. "
            f"— = sin negocios ese mes o el punto no existe en ese mercado.</p>")


# =====================================================================
# Programa principal
# =====================================================================

def main():
    lector = argparse.ArgumentParser(description="Informe de un periodo en línea de tiempo")
    lector.add_argument("--desde", required=True, help="primer mes (AAAA-MM), ej. 2026-09")
    lector.add_argument("--hasta", required=True, help="último mes (AAAA-MM), ej. 2026-10")
    lector.add_argument("--enviar", action="store_true", help="envía el informe por Gmail")
    opciones = lector.parse_args()
    hoy = date.today()
    meses = list(pd.period_range(opciones.desde, opciones.hasta, freq="M"))
    periodo = nombre_periodo(meses)
    print(f"Informe de {periodo}")

    tabla_p, leidos_p = leer_carpeta(config.CARPETA_DATOS, config.PATRON_PRIMARIO, lector=leer_excel_bec)
    tabla_s, leidos_s = leer_carpeta(config.CARPETA_DATOS, config.PATRON_SECUNDARIO,
                                     lector=leer_excel_secundario)
    ultimo_dia = tabla_s["fecha"].max()
    fin = min(meses[-1].end_time.normalize(), ultimo_dia.normalize())
    dias = list(pd.date_range(meses[0].start_time.normalize(), fin, freq="D"))
    semanas = list(pd.period_range(dias[0], dias[-1], freq="W-SUN"))

    # Solo las filas del periodo.
    tabla_p = tabla_p[tabla_p["mes"].isin(meses)]
    tabla_s = tabla_s[(tabla_s["fecha"] >= dias[0]) & (tabla_s["fecha"] <= dias[-1] + pd.Timedelta(days=1))]
    gp, enc_p, _, _ = separar_puntos(tabla_p, avisar=False)
    gs, enc_s, _, _ = separar_puntos(tabla_s, avisar=False)
    gp = {n: g for n, g in gp.items() if len(g)}
    gs = {n: g for n, g in gs.items() if len(g)}

    imagenes = {"per_precio_diario": grafica_precio_diario(gs, dias, meses),
                "per_cantidad_diaria": grafica_cantidad_diaria(gs, dias, meses),
                "per_precio_semanal": grafica_precio_semanal(gs, semanas)}

    avisos = []
    if ultimo_dia.normalize() < meses[-1].end_time.normalize():
        avisos.append(f"Los datos del mercado secundario llegan hasta el {ultimo_dia.day} de "
                      f"{MES_LARGO[ultimo_dia.month]} de {ultimo_dia.year}; los días siguientes "
                      f"aún no están publicados en el BEC.")

    def cuerpo(src):
        partes = [h1_mercado("Mes contra mes"),
                  parrafo_gris("Cómo cambió cada punto de un mes al otro, en los dos mercados."),
                  h3("Mercado secundario (reventa)"), tabla_meses_html(gs, meses, "Mercado secundario"),
                  h3("Mercado primario (primera venta)"), tabla_meses_html(gp, meses, "Mercado primario"),
                  h3("Primario vs. secundario, mes por mes"), tabla_cruce_html(gp, gs, meses),
                  h1_mercado("Mercado secundario: línea de tiempo"),
                  parrafo_gris(f"Los {len(dias)} días del periodo, uno detrás del otro. La línea "
                               f"punteada marca el cambio de mes."),
                  h3("Precio de cada día"), imagen(src("per_precio_diario"), "Precio diario"),
                  h3("Cantidad negociada cada día"), imagen(src("per_cantidad_diaria"), "Cantidad diaria"),
                  h3("Semana a semana"),
                  parrafo_gris("El precio semanal suaviza los saltos de un día a otro."),
                  imagen(src("per_precio_semanal"), "Precio semanal"),
                  tabla_semanas_html(gs, semanas, dias)]
        for nombre, tabla in gs.items():
            partes += [h2(nombre), lista(frases_secundario(nombre, tabla, meses))]
        partes += [h1_mercado("Mercado primario: negociaciones del periodo"),
                   parrafo_gris("El BEC publica el primario por mes (sin el día), así que aquí "
                                "aparece cada negociación con su mes."),
                   tabla_negociaciones_primario(gp, meses)]
        return "".join(partes)

    pie = (f"<p style='margin:0'>Archivos leídos: {', '.join(leidos_p + leidos_s)}. Secundario con "
           f"datos hasta el {ultimo_dia:%d/%m/%Y}.</p>")
    piezas = dict(titulo=f"Gas natural: {periodo}",
                  subtitulo=(f"Informe del periodo · Mercados primario y secundario · "
                             f"{' · '.join(config.PUNTOS_SEGUIMIENTO)} · corte al {hoy:%d/%m/%Y}"),
                  avisos=avisos, alertas=[], pie=pie, prueba=False,
                  fuente=("Fuente: Gestor del Mercado de Gas Natural (BMC), información "
                          "transaccional publicada en el BEC. Precio calculado como promedio "
                          "ponderado por cantidad. ND = precio no disponible."))
    html = armar_html(**piezas, cuerpo=cuerpo(lambda n: png_a_texto(imagenes[n])))
    os.makedirs(config.CARPETA_SALIDA, exist_ok=True)
    ruta = os.path.join(config.CARPETA_SALIDA, f"periodo_{meses[0]}_a_{meses[-1]}.html")
    with open(ruta, "w", encoding="utf-8") as archivo:
        archivo.write(html)
    print(f"Informe guardado en: {ruta}")

    if opciones.enviar:
        acceso = enviar_correo.datos_de_acceso()
        if acceso is None:
            raise SystemExit("No encontré GMAIL_USUARIO, GMAIL_CLAVE_APP o CORREO_DESTINO.")
        usuario, clave, destino = acceso
        correo = enviar_correo.armar_correo(f"Gas natural: {periodo}",
                                            armar_html(**piezas, cuerpo=cuerpo(lambda n: f"cid:{n}")),
                                            imagenes, remitente=usuario, destino=destino,
                                            adjunto=ruta)
        enviar_correo.enviar(correo, usuario, clave)
        print(f"Correo enviado a: {destino}")


if __name__ == "__main__":
    main()
