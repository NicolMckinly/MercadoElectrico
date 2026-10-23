# =====================================================================
# config.py  —  EL "PANEL DE CONTROL" DEL PROYECTO
# ---------------------------------------------------------------------
# Aquí van los datos que tú puedes cambiar sin tocar el programa
# principal. Es como los ajustes de un celular: cambias una opción
# aquí y el programa se comporta distinto.
# =====================================================================

# --- 1. ¿Dónde están los archivos de datos? --------------------------
# Son los Excel que descargas del BEC con el botón "Exportar datos".
# Usamos la "Tabla de resultados", que trae cada negociación por separado.
ARCHIVO_TABLA = "datos/tabla_resultados.xlsx"

# --- 2. ¿Dónde se guarda el reporte terminado? -----------------------
CARPETA_SALIDA = "salida"

# --- 3. ¿Qué mercado estamos mirando? --------------------------------
# Solo es un nombre que aparece en el título del reporte.
MERCADO = "Mercado primario"

# --- 4. Puntos de entrega a los que les hacemos seguimiento ----------
# A la IZQUIERDA: el nombre que aparecerá en el reporte.
# A la DERECHA: palabras clave para encontrar ese punto en el Excel del BEC.
#   - No importan mayúsculas ni tildes ("Floreña" = "FLORENA").
#   - Basta con que el nombre del BEC CONTENGA una de las palabras.
#   - Pusimos varias opciones porque aún no conocemos el nombre exacto
#     que usa el BEC. El reporte te muestra al final qué nombres encontró,
#     para que ajustes esta lista si hace falta.
# Para agregar otro punto, copia una línea y cambia los textos.
PUNTOS_SEGUIMIENTO = {
    "Cusiana": ["cusiana"],
    "Floreña": ["florena"],
    "Cartagena (GNL importado)": ["cartagena", "spec", "regasific", "gnl"],
}

# Color de cada punto en las gráficas comparativas.
COLORES_PUNTO = {
    "Cusiana": "#1F3A68",
    "Floreña": "#C2410C",
    "Cartagena (GNL importado)": "#7C3AED",
    "Nacional": "#374151",
}

# --- 5. ¿Cuántos meses hacia atrás mostrar en las gráficas? ----------
MESES_HISTORIA = 12

# --- 6. Umbrales de alerta -------------------------------------------
# Si el precio del mes sube más de este porcentaje frente al promedio
# de los últimos meses, el reporte lo marca como alerta.
ALERTA_PRECIO_PCT = 20      # 20 %
# Si la cantidad contratada es más de este número de veces el promedio,
# también se marca como alerta.
ALERTA_CANTIDAD_VECES = 1.5

# --- 7. Colores de cada modalidad ------------------------------------
# Usamos los mismos colores del tablero del BEC para que se reconozcan.
COLORES_MODALIDAD = {
    "Con Interrupciones": "#C8C8C8",
    "Contingencia": "#00E5F0",
    "Firme": "#1F3A68",
    "Firme al 95%": "#4472C4",
    "Firmeza Condicionada": "#13A04A",
    "Opción de Compra": "#F2E600",
    "Otras": "#16C79A",
}
