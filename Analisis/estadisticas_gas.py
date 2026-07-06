"""
Modulo: estadisticas_gas.py
Ubicacion: Analisis/estadisticas_gas.py

Procesa el historico de convocatorias de Ecopetrol detectadas, para
extraer la cantidad numerica de gas ofertada (en MBTUD) de cada una
(cuando sea posible identificarla en el texto), y armar los datos
para el grafico de tendencia y la tabla de contratos vigentes.
"""

import sys
import os
import re

CARPETA_PROYECTO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(CARPETA_PROYECTO, "BaseDatos"))

from base_datos import consultar_todas_convocatorias

# Busca un numero (con decimales opcionales) seguido de "MBTUD" o
# variantes de mayusculas/espacios, en el texto de la cantidad.
PATRON_CANTIDAD_NUMERICA = re.compile(r"([\d.,]+)\s*M\s*B\s*T\s*U\s*D", re.IGNORECASE)


def _extraer_cantidad_numerica(texto_cantidad):
    """
    Intenta extraer el valor numerico de MBTUD desde el texto libre
    de la cantidad (por ejemplo, "70Mbtud" o "279 MBTUD").

    Retorna:
        Un numero float, o None si no se pudo identificar.
    """
    if texto_cantidad is None or texto_cantidad == "No especificado":
        return None

    coincidencia = PATRON_CANTIDAD_NUMERICA.search(texto_cantidad)
    if coincidencia is None:
        return None

    texto_numero = coincidencia.group(1).replace(".", "").replace(",", ".")

    try:
        return float(texto_numero)
    except ValueError:
        return None


def obtener_historico_gas():
    """
    Trae el historico completo de convocatorias, agregando la
    cantidad numerica extraida cuando sea posible.

    Retorna:
        Un DataFrame con una columna adicional "cantidad_mbtud".
    """
    convocatorias = consultar_todas_convocatorias()

    if len(convocatorias) == 0:
        return convocatorias

    convocatorias = convocatorias.copy()
    convocatorias["cantidad_mbtud"] = convocatorias["cantidad"].apply(_extraer_cantidad_numerica)

    return convocatorias


if __name__ == "__main__":
    historico = obtener_historico_gas()

    if len(historico) == 0:
        print("No hay convocatorias registradas todavia.")
    else:
        print("Total de convocatorias registradas: " + str(len(historico)))
        print("")
        con_cantidad = historico[historico["cantidad_mbtud"].notna()]
        print("Convocatorias con cantidad numerica identificada: " + str(len(con_cantidad)))
        print("")
        print(historico[["titulo", "fecha_deteccion", "cantidad", "cantidad_mbtud", "modalidad"]].to_string())
