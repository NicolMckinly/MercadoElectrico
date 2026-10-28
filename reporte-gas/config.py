# =====================================================================
# config.py  —  EL "PANEL DE CONTROL" DEL PROYECTO
# ---------------------------------------------------------------------
# Aquí van los datos que tú puedes cambiar sin tocar el programa
# principal. Es como los ajustes de un celular: cambias una opción
# aquí y el programa se comporta distinto.
# =====================================================================

# --- 1. ¿Dónde están los archivos de datos? --------------------------
# Es la CARPETA donde guardas los Excel que descargas del BEC con el
# botón "Exportar datos" de la "Tabla de resultados".
# El programa lee TODOS los .xlsx que haya en esta carpeta y los junta.
# Así puedes descargar un archivo por punto (cusiana.xlsx, florena.xlsx,
# cartagena.xlsx) o uno solo con todos: funciona igual.
# Consejo: ponle a cada archivo el nombre del punto. Si algún Excel no
# trae la columna "Punto de entrega", el programa usa el nombre del
# archivo para saber de qué punto es.
CARPETA_DATOS = "datos"

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
    # El BEC cambió los nombres en 2025: "CUSIANA" pasó a "PLANTA CUSIANA".
    # La palabra "cusiana" atrapa los dos, así la historia queda completa.
    "Cusiana": ["cusiana"],
    # Igual aquí: "FLOREÑA" (hasta 2025) y "PLANTA FLOREÑA" (desde 2025).
    "Floreña": ["florena"],
    # El gas importado entra por la terminal de regasificación de Cartagena.
    # El BEC la llamó "Unidad Flotante de Almacenamiento y Regasificación
    # (FSRU)" hasta agosto de 2025 y "SPEC" desde entonces.
    # OJO: NO usamos la palabra "cartagena", porque el punto "CARTAGENA" del
    # BEC es otro (existe desde 2015 y mezcla gas que no es solo importado).
    "Cartagena (GNL importado)": ["spec", "fsru"],
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
