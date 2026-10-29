# =====================================================================
# reporte_semanal_secundario.py  —  REPORTE SEMANAL DEL MERCADO SECUNDARIO
# ---------------------------------------------------------------------
# El mercado secundario es la REVENTA del gas. El BEC lo publica día por
# día, así que podemos mirarlo semana por semana.
#
# Este reporte cubre UNA semana completa (de lunes a domingo) y la compara:
#   - con la semana anterior;
#   - con el promedio de las 4 semanas previas.
# Además dibuja las últimas 12 semanas para ver la tendencia.
#
# Reutiliza muchas piezas de generar_reporte.py (leer el Excel, separar
# los puntos, calcular el precio ponderado, armar el HTML, enviar el
# correo). Aquí solo está lo que es propio del reporte semanal.
#
# Formas de ejecutarlo:
#   python reporte_semanal_secundario.py
#        -> la última semana completa (la que terminó el domingo pasado)
#   python reporte_semanal_secundario.py --semana 2026-10-21
#        -> la semana que contiene ese día (de lunes a domingo)
#   python reporte_semanal_secundario.py --enviar   -> además lo envía por Gmail
# =====================================================================

import argparse
import os
from datetime import date

import matplotlib.pyplot as plt
import pandas as pd

import config
import enviar_correo
from generar_reporte import (
    armar_html, cambio_pct, color_punto, contar_negociaciones, estilo_basico,
    figura_a_png, flecha, fmt_num, fmt_precio, grafica_dispersion_puntos, h2, h3,
    imagen, leer_carpeta, leer_estado_descarga, leer_excel_secundario, leyenda_abajo,
    lista, parrafo_gris, plural, png_a_texto, precio_ponderado, resumen_mensual,
    resumen_por_modalidad, separar_puntos, tabla_modalidad_html, texto_cambio,
    CELDA, TITULO_COL, MES_LARGO,
)

SEMANAS_HISTORIA = 12        # cuántas semanas mostrar en las gráficas
SEMANAS_PROMEDIO = 4         # contra cuántas semanas previas se compara


# =====================================================================
# Ayudantes para hablar de semanas
# =====================================================================

def semana_bonita(semana):
    """Period de una semana -> 'del 19 al 25 de octubre de 2026'."""
    ini, fin = semana.start_time, semana.end_time
    if ini.month == fin.month:
        return f"del {ini.day} al {fin.day} de {MES_LARGO[fin.month]} de {fin.year}"
    if ini.year == fin.year:
        return (f"del {ini.day} de {MES_LARGO[ini.month]} al {fin.day} de "
                f"{MES_LARGO[fin.month]} de {fin.year}")
    return (f"del {ini.day} de {MES_LARGO[ini.month]} de {ini.year} al {fin.day} de "
            f"{MES_LARGO[fin.month]} de {fin.year}")


def etiqueta_corta(semana):
    """Para las gráficas: '19-25\\noct'."""
    ini, fin = semana.start_time, semana.end_time
    return f"{ini.day}-{fin.day}\n{MES_LARGO[fin.month][:3]}"


def por_semanas(tabla):
    """Cambia la columna "mes" por la SEMANA de cada día.

    Truco: muchas funciones que ya tenemos agrupan por la columna "mes".
    Si en esa columna ponemos la semana (lunes a domingo), esas mismas
    funciones sirven para semanas sin cambiarlas.
    """
    copia = tabla.copy()
    copia["mes"] = copia["fecha"].dt.to_period("W-SUN")     # semanas que terminan en domingo
    return copia


# =====================================================================
# Gráficas semanales
# =====================================================================

def ejes_de_semanas(ax, semanas):
    ax.set_xticks(range(len(semanas)))
    ax.set_xticklabels([etiqueta_corta(s) for s in semanas], fontsize=8)


def grafica_precio_semanal(grupos, semanas):
    """Precio promedio ponderado de cada punto, semana a semana."""
    fig, ax = plt.subplots(figsize=(10, 3.8))
    for nombre, tabla in grupos.items():
        serie = resumen_mensual(tabla)["precio"].reindex(semanas)
        ax.plot(range(len(semanas)), serie.values, marker="o", linewidth=2, markersize=4,
                label=nombre, color=color_punto(nombre))
    ejes_de_semanas(ax, semanas)
    ax.set_ylabel("USD/MBTU")
    estilo_basico(ax)
    leyenda_abajo(ax)
    return figura_a_png(fig)


def grafica_cantidad_semanal(grupos, semanas):
    """Cantidad negociada en cada punto, semana a semana."""
    fig, ax = plt.subplots(figsize=(10, 3.8))
    ancho = 0.8 / max(len(grupos), 1)
    for i, (nombre, tabla) in enumerate(grupos.items()):
        serie = resumen_mensual(tabla)["cantidad"].reindex(semanas).fillna(0) / 1000
        posiciones = [x - 0.4 + ancho * (i + 0.5) for x in range(len(semanas))]
        ax.bar(posiciones, serie.values, width=ancho, label=nombre, color=color_punto(nombre))
    ax.bar(len(semanas) - 1, 0)                 # (para que el eje incluya la última semana)
    ejes_de_semanas(ax, semanas)
    ax.set_ylabel("Miles de MBTUD")
    estilo_basico(ax)
    leyenda_abajo(ax)
    return figura_a_png(fig)


def grafica_dias_de_la_semana(grupos, semana):
    """Los 7 días de la semana: precio ponderado de cada punto, día por día.

    La franja de color muestra el rango entre el precio mínimo y el máximo
    de ese día: si es ancha, ese día hubo precios muy distintos.
    """
    dias = pd.date_range(semana.start_time.normalize(), periods=7, freq="D")
    nombres_dia = ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"]
    fig, ax = plt.subplots(figsize=(10, 3.6))
    for nombre, tabla in grupos.items():
        del_semana = tabla[tabla["mes"] == semana]
        precios, minimos, maximos = [], [], []
        for dia in dias:
            d = del_semana[del_semana["fecha"].dt.normalize() == dia]
            precios.append(precio_ponderado(d) if len(d) else float("nan"))
            minimos.append(d["precio_min"].min() if len(d) else float("nan"))
            maximos.append(d["precio_max"].max() if len(d) else float("nan"))
        color = color_punto(nombre)
        ax.fill_between(range(7), minimos, maximos, color=color, alpha=0.15)
        ax.plot(range(7), precios, marker="o", linewidth=2, color=color, label=nombre)
    ax.set_xticks(range(7))
    ax.set_xticklabels([f"{n}\n{d.day}" for n, d in zip(nombres_dia, dias)], fontsize=8)
    ax.set_ylabel("USD/MBTU")
    estilo_basico(ax)
    leyenda_abajo(ax)
    return figura_a_png(fig)


# =====================================================================
# Análisis
# =====================================================================

def resumen_de_semana(tabla, semana):
    """Los números clave de un punto en una semana."""
    d = tabla[tabla["mes"] == semana]
    if not len(d):
        return None
    con_inter = d[d["intermediacion"].notna()]
    margen = ((con_inter["cantidad"] * con_inter["intermediacion"]).sum() / con_inter["cantidad"].sum()
              if con_inter["cantidad"].sum() > 0 else float("nan"))
    return {"cantidad": d["cantidad"].sum(), "precio": precio_ponderado(d),
            "negociaciones": contar_negociaciones(d),
            "minimo": d["precio_min"].min(), "maximo": d["precio_max"].max(),
            "margen": margen, "dias": d["fecha"].dt.normalize().nunique()}


def analizar_punto_semana(nombre, tabla, semana):
    """Frases y alertas de UN punto en la semana."""
    frases, alertas = [], []
    r = resumen_de_semana(tabla, semana)
    if r is None:
        return [f"No hubo negociaciones en la semana {semana_bonita(semana)}."], alertas

    frases.append(
        f"Se negociaron {fmt_num(r['cantidad'])} MBTUD en "
        f"{plural(r['negociaciones'], 'negociación', 'negociaciones')} "
        f"({plural(r['dias'], 'día', 'días')} con negocios), a un precio ponderado de "
        f"{fmt_precio(r['precio'])} USD/MBTU.")

    ant = resumen_de_semana(tabla, semana - 1)
    if ant:
        dp = cambio_pct(r["precio"], ant["precio"])
        precio_txt = (f"el precio {texto_cambio(dp)}" if dp is not None else
                      "el precio no se puede comparar (una de las dos semanas no tiene precio publicado)")
        frases.append(
            f"Frente a la semana anterior, la cantidad "
            f"{texto_cambio(cambio_pct(r['cantidad'], ant['cantidad']))} y {precio_txt}.")
    else:
        frases.append("La semana anterior no hubo negocios para comparar.")

    previas = [resumen_de_semana(tabla, semana - k) for k in range(1, SEMANAS_PROMEDIO + 1)]
    previas = [p for p in previas if p]
    if previas:
        prom_q = sum(p["cantidad"] for p in previas) / SEMANAS_PROMEDIO
        precios = [p["precio"] for p in previas if pd.notna(p["precio"])]
        prom_p = sum(precios) / len(precios) if precios else float("nan")
        pct_p = cambio_pct(r["precio"], prom_p)
        frases.append(
            f"Frente al promedio de las {SEMANAS_PROMEDIO} semanas previas "
            f"({fmt_precio(prom_p)} USD/MBTU), el precio {texto_cambio(pct_p)}.")
        if pct_p is not None and pct_p > config.ALERTA_PRECIO_PCT:
            alertas.append(f"{nombre}: el precio está {pct_p:.0f} % por encima del promedio "
                           f"de las {SEMANAS_PROMEDIO} semanas previas.")
        if prom_q and r["cantidad"] > config.ALERTA_CANTIDAD_VECES * prom_q:
            alertas.append(f"{nombre}: la cantidad negociada es "
                           f"{fmt_precio(r['cantidad'] / prom_q)[:-1]} veces el promedio semanal.")

    if pd.notna(r["minimo"]) or pd.notna(r["maximo"]):
        frases.append(f"Los precios fueron desde {fmt_precio(r['minimo'])} hasta "
                      f"{fmt_precio(r['maximo'])} USD/MBTU.")
    if pd.notna(r["margen"]):
        frases.append(f"Margen promedio de intermediación (lo que gana quien revende): "
                      f"{fmt_precio(r['margen'])} USD/MBTU.")
    mod = resumen_por_modalidad(tabla, semana)
    if len(mod):
        lider = mod.iloc[0]
        frases.append(f"Modalidad principal: «{lider['modalidad']}» "
                      f"({lider['participacion']:.0f} % del volumen).")
    return frases, alertas


def tabla_semana_html(grupos, semana):
    """Tabla resumen: una fila por punto, con flechas frente a la semana anterior."""
    filas = ""
    for nombre, tabla in grupos.items():
        punto = (f"<span style='display:inline-block;width:10px;height:10px;"
                 f"background:{color_punto(nombre)};margin-right:8px'></span>{nombre}")
        r = resumen_de_semana(tabla, semana)
        if r is None:
            filas += (f"<tr><td style='{CELDA}'>{punto}</td>"
                      f"<td style='{CELDA};color:#6B7280' colspan='4'>Sin negociaciones</td></tr>")
            continue
        ant = resumen_de_semana(tabla, semana - 1)
        dq = cambio_pct(r["cantidad"], ant["cantidad"]) if ant else None
        dp = cambio_pct(r["precio"], ant["precio"]) if ant else None
        filas += (f"<tr><td style='{CELDA}'>{punto}</td>"
                  f"<td style='{CELDA};text-align:right'>{fmt_num(r['cantidad'])}<br>"
                  f"<span style='font-size:12px'>{flecha(dq)}</span></td>"
                  f"<td style='{CELDA};text-align:right'>{fmt_precio(r['precio'])}<br>"
                  f"<span style='font-size:12px'>{flecha(dp)}</span></td>"
                  f"<td style='{CELDA};text-align:right'>{fmt_precio(r['minimo'])} – "
                  f"{fmt_precio(r['maximo'])}</td>"
                  f"<td style='{CELDA};text-align:right'>{r['negociaciones']}</td></tr>")
    encabezado = "".join(
        f"<th style='{TITULO_COL};text-align:{a}'>{t}</th>"
        for t, a in [("Punto", "left"), ("Cantidad (MBTUD)", "right"),
                     ("Precio (USD/MBTU)", "right"), ("Mín. – máx.", "right"),
                     ("Negociaciones", "right")])
    return (f"<table style='width:100%;border-collapse:collapse;font-size:14px'>"
            f"<tr>{encabezado}</tr>{filas}</table>"
            f"<p style='margin:6px 0 0;color:#6B7280;font-size:12px'>Las flechas comparan con "
            f"la semana anterior. ▲ rojo = subió, ▼ verde = bajó.</p>")


def frases_comparativas(grupos, semana):
    """Frases que comparan los puntos entre sí en la semana."""
    datos = {n: resumen_de_semana(t, semana) for n, t in grupos.items()}
    datos = {n: r for n, r in datos.items() if r}
    if not datos:
        return [f"Ningún punto tuvo negociaciones en la semana {semana_bonita(semana)}."]
    total = sum(r["cantidad"] for r in datos.values())
    mayor = max(datos, key=lambda n: datos[n]["cantidad"])
    frases = [f"Entre los puntos seguidos se negociaron {fmt_num(total)} MBTUD; "
              f"{mayor} concentró el {100 * datos[mayor]['cantidad'] / total:.0f} %."]
    con_precio = {n: r["precio"] for n, r in datos.items() if pd.notna(r["precio"])}
    if len(con_precio) >= 2:
        caro = max(con_precio, key=con_precio.get)
        barato = min(con_precio, key=con_precio.get)
        if con_precio[caro] - con_precio[barato] < 0.01:
            frases.append(f"{' y '.join(con_precio)} se negociaron al mismo precio.")
        else:
            frases.append(f"El más caro fue {caro} ({fmt_precio(con_precio[caro])} USD/MBTU) y el "
                          f"más barato {barato} ({fmt_precio(con_precio[barato])}).")
    return frases


# =====================================================================
# Programa principal
# =====================================================================

def leer_opciones():
    lector = argparse.ArgumentParser(description="Reporte semanal del mercado secundario")
    lector.add_argument("--semana", help="un día cualquiera de la semana a reportar (AAAA-MM-DD). "
                                         "Si no lo pones, usa la última semana completa.")
    lector.add_argument("--enviar", action="store_true", help="envía el reporte por Gmail")
    return lector.parse_args()


def main():
    opciones = leer_opciones()
    hoy = date.today()
    if opciones.semana:
        semana = pd.Period(opciones.semana, freq="W-SUN")
    else:
        semana = pd.Period(hoy, freq="W-SUN") - 1        # la semana pasada completa
    semanas = list(pd.period_range(end=semana, periods=SEMANAS_HISTORIA, freq="W-SUN"))
    print(f"Reporte semanal del secundario: semana {semana_bonita(semana)}")

    print("PASO 1: leyendo datos...")
    tabla, leidos = leer_carpeta(config.CARPETA_DATOS, config.PATRON_SECUNDARIO,
                                 lector=leer_excel_secundario)
    if tabla is None:
        raise SystemExit("No encontré el archivo del mercado secundario (datos/secundario.xlsx).")
    tabla = por_semanas(tabla)
    ultimo_dia = tabla["fecha"].max()
    print(f"   Archivos leídos: {', '.join(leidos)} (datos hasta {ultimo_dia:%d/%m/%Y})")

    avisos = []
    if leer_estado_descarga().get("secundario") == "fallo":
        avisos.append(f"No pude descargar datos nuevos del mercado secundario. Se usan los últimos "
                      f"datos guardados (llegan hasta el {ultimo_dia:%d/%m/%Y}). Revisa las fotos "
                      f"del robot en la pestaña Actions de GitHub.")
    if ultimo_dia < semana.end_time.normalize():
        avisos.append(f"Los datos del BEC llegan hasta el {ultimo_dia:%d/%m/%Y}, así que puede "
                      f"faltar información de los últimos días de la semana.")

    print("PASO 2: separando puntos y analizando...")
    grupos, encontrados, otros, _ = separar_puntos(tabla, avisar=False)
    grupos = {n: g for n, g in grupos.items() if len(g)}       # el GNL importado no está aquí
    secciones, alertas = [], []
    for nombre, filas in grupos.items():
        frases, alertas_punto = analizar_punto_semana(nombre, filas, semana)
        secciones.append((nombre, frases, resumen_por_modalidad(filas, semana)))
        alertas += alertas_punto
        print(f"   {nombre}: {len(filas[filas['mes'] == semana])} filas en la semana")

    print("PASO 3: dibujando gráficas...")
    imagenes = {
        "sem_precio": grafica_precio_semanal(grupos, semanas),
        "sem_cantidad": grafica_cantidad_semanal(grupos, semanas),
        "sem_dias": grafica_dias_de_la_semana(grupos, semana),
        "sem_dispersion": grafica_dispersion_puntos(grupos, semana),
    }

    def cuerpo(src):
        partes = [h2("Resumen de la semana", arriba=0),
                  lista(frases_comparativas(grupos, semana)),
                  f"<div style='margin-top:14px'>{tabla_semana_html(grupos, semana)}</div>",
                  h3("Día por día"),
                  parrafo_gris("Precio ponderado de cada día. La franja de color va del precio "
                               "mínimo al máximo de ese día."),
                  imagen(src("sem_dias"), "Día por día"),
                  h3("Precio de cada registro de la semana"),
                  parrafo_gris("Cada círculo es un día de negocios de una modalidad; el color es "
                               "la modalidad y el tamaño, la cantidad."),
                  imagen(src("sem_dispersion"), "Registros de la semana"),
                  h3(f"Tendencia: últimas {SEMANAS_HISTORIA} semanas"),
                  parrafo_gris("Precio ponderado de cada punto, semana a semana."),
                  imagen(src("sem_precio"), "Precio semanal"),
                  parrafo_gris("Cantidad negociada en cada punto, semana a semana."),
                  imagen(src("sem_cantidad"), "Cantidad semanal")]
        for nombre, frases, mod in secciones:
            partes += [h2(nombre), lista(frases)]
            if len(mod):
                partes.append(tabla_modalidad_html(mod))
        return "".join(partes)

    nombres = "".join(f"<li>{n}: {', '.join(c) if c else '<i>no se negocia en el secundario</i>'}</li>"
                      for n, c in encontrados.items())
    pie = (f"<p style='margin:0'>Nombres del BEC incluidos en cada punto:</p>"
           f"<ul style='margin:4px 0 0;padding-left:18px'>{nombres}</ul>"
           f"<p style='margin:4px 0 0'>Archivo leído: {', '.join(leidos)}, con datos hasta el "
           f"{ultimo_dia:%d/%m/%Y}.</p>")

    print("PASO 4: escribiendo el reporte...")
    titulo = f"Mercado secundario de gas: semana {semana_bonita(semana)}"
    piezas = dict(titulo=titulo,
                  subtitulo=(f"Reporte semanal · Mercado secundario (reventa) · "
                             f"{' · '.join(grupos)} · corte al {hoy:%d/%m/%Y}"),
                  avisos=avisos, alertas=alertas, pie=pie, prueba=False,
                  fuente=("Fuente: Gestor del Mercado de Gas Natural (BMC), información "
                          "transaccional del mercado secundario publicada en el BEC (datos "
                          "diarios). Precio calculado como promedio ponderado por cantidad. "
                          "ND = precio no disponible. Los registros que el BEC publique después "
                          "de la fecha de corte aparecerán en el reporte de la semana siguiente."))
    html = armar_html(**piezas, cuerpo=cuerpo(lambda n: png_a_texto(imagenes[n])))
    os.makedirs(config.CARPETA_SALIDA, exist_ok=True)
    ruta = os.path.join(config.CARPETA_SALIDA,
                        f"semanal_secundario_{semana.start_time:%Y-%m-%d}.html")
    with open(ruta, "w", encoding="utf-8") as archivo:
        archivo.write(html)
    print(f"   Reporte guardado en: {ruta}")

    if opciones.enviar:
        print("PASO 5: enviando el correo...")
        acceso = enviar_correo.datos_de_acceso()
        if acceso is None:
            print("   No encontré GMAIL_USUARIO, GMAIL_CLAVE_APP o CORREO_DESTINO.")
            raise SystemExit(1)
        usuario, clave, destino = acceso
        html_correo = armar_html(**piezas, cuerpo=cuerpo(lambda n: f"cid:{n}"))
        asunto = f"Mercado secundario de gas: semana {semana_bonita(semana)}"
        if avisos and "No pude descargar" in avisos[0]:
            asunto = "[DATOS SIN ACTUALIZAR] " + asunto
        if alertas:
            asunto += f" ({len(alertas)} alerta{'s' if len(alertas) > 1 else ''})"
        correo = enviar_correo.armar_correo(asunto, html_correo, imagenes, remitente=usuario,
                                            destino=destino, adjunto=ruta)
        enviar_correo.enviar(correo, usuario, clave)
        print(f"   Correo enviado a: {destino}")
    print("¡Listo!")


if __name__ == "__main__":
    main()
