# =====================================================================
# crear_datos_prueba.py  —  FÁBRICA DE DATOS INVENTADOS
# ---------------------------------------------------------------------
# Crea un Excel con el MISMO formato que exporta el BEC, pero con números
# INVENTADOS al azar. Sirve para probar el reporte por puntos mientras no
# tengamos el archivo real de la pestaña "Puntos".
#
# ¡OJO! Estos números NO son reales. Nunca los uses para tomar decisiones.
#
# Uso (desde la carpeta principal del proyecto):
#   python pruebas/crear_datos_prueba.py
#   python generar_reporte.py --prueba --mes 2026-09
# =====================================================================

import random

import pandas as pd

random.seed(7)     # "semilla": hace que el azar salga igual cada vez

MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]

# Para cada punto inventado: (precio típico, modalidades posibles)
PUNTOS = {
    "CUSIANA": (9.5, ["Con Interrupciones", "Firme al 95%", "Firmeza Condicionada"]),
    "FLOREÑA": (10.0, ["Con Interrupciones", "Firme al 95%"]),
    "SPEC - CARTAGENA": (16.0, ["Firme al 95%", "Contingencia", "Opción de Compra"]),
    "BALLENA": (8.0, ["Con Interrupciones"]),     # punto que NO seguimos
}

filas = []
for anio in (2024, 2025, 2026):
    for numero_mes, mes in enumerate(MESES, start=1):
        if anio == 2026 and numero_mes > 10:
            break
        for punto, (precio_base, modalidades) in PUNTOS.items():
            if random.random() < 0.15:          # algunos meses sin negocios
                continue
            for _ in range(random.randint(1, 4)):
                precio = precio_base * random.uniform(0.8, 1.25)
                filas.append([f"{anio} {mes}", punto, random.choice(modalidades),
                              random.randint(2, 60) * 1000,
                              "ND" if random.random() < 0.05 else f"{precio:.2f}".replace(".", ",")])

# Armamos la hoja igual que el BEC: dos filas de "basura" arriba y los títulos.
encabezado = ["Año-mes*", "Punto de entrega", "Modalidad", "Cantidad (MBTUD)",
              "Precio Promedio Ponderado (USD/MBTU)"]
hoja = [["Filtros aplicados: DATOS INVENTADOS PARA PRUEBAS", "", "", "", ""],
        ["", "", "", "", ""], encabezado] + filas
pd.DataFrame(hoja).to_excel("pruebas/datos_ficticios_puntos.xlsx", header=False, index=False)
print(f"Creadas {len(filas)} filas inventadas en pruebas/datos_ficticios_puntos.xlsx")
