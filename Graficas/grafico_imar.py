"""
Modulo: grafico_imar.py
Ubicacion: Graficas/grafico_imar.py

Genera el grafico de LINEA del IMAR (Crudo y Ajustado) periodo a
periodo, para el dia siguiente. Se usa dentro del informe diario,
justo despues del grafico de tendencia anual y antes de la tabla
del IMAR, como complemento visual.

El titulo del grafico incluye la fecha del dia que se esta mostrando
(ej. "IMAR 09 Julio 2026"), traducida manualmente al espanol, porque
el servidor donde corre el sistema (GitHub Actions) no tiene
instalado el idioma espanol.

El eje Y siempre parte desde 0, para que todas las graficas del
informe compartan la misma base de referencia visual.

El grafico se guarda como imagen .png dentro de esta misma carpeta.
"""

import os
from datetime import datetime
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

CARPETA_ACTUAL = os.path.dirname(os.path.abspath(__file__))

COLOR_IMAR_CRUDO = "#7F9CC4"
COLOR_IMAR_AJUSTADO = "#1F4E79"

MESES_EN_ESPANOL_LARGO = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre",
}


def _formatear_titulo_con_fecha(fecha_texto):
    """
    Convierte una fecha en formato "YYYY-MM-DD" en el titulo del
    grafico, ej: "IMAR 09 Julio 2026".
    """
    fecha_dt = datetime.strptime(fecha_texto, "%Y-%m-%d")
    dia = fecha_dt.strftime("%d")
    mes = MESES_EN_ESPANOL_LARGO[fecha_dt.month]
    anio = fecha_dt.strftime("%Y")
    return "IMAR " + dia + " " + mes + " " + anio


def generar_grafico_imar_siguiente_dia(tabla_imar):
    """
    Genera el grafico de linea del IMAR Crudo vs Ajustado, periodo a
    periodo, a partir del diccionario ya calculado por
    obtener_tabla_imar_siguiente_dia() (en Analisis/tabla_imar_siguiente_dia.py).

    Parametros:
        tabla_imar (dict o None): debe tener la forma
            {"fecha": ..., "filas": [{"periodo": ..., "imar_crudo": ..., "imar_ajustado": ...}, ...]}
            Puede ser None si el IMAR de mañana aun no esta publicado.

    Retorna:
        La ruta del archivo generado, o None si no hay datos.
    """
    if tabla_imar is None or len(tabla_imar.get("filas", [])) == 0:
        print("No hay datos de IMAR disponibles para graficar todavia.")
        return None

    cantidad_periodos = len(tabla_imar["filas"])
    # Etiquetas cortas tipo P01, P02, ... P24, en vez de la hora completa.
    periodos = ["P" + str(indice + 1).zfill(2) for indice in range(cantidad_periodos)]

    valores_crudo = [f["imar_crudo"] for f in tabla_imar["filas"]]
    valores_ajustado = [f["imar_ajustado"] for f in tabla_imar["filas"]]

    posiciones = np.arange(len(periodos))

    figura, ejes = plt.subplots(figsize=(11, 6.5))

    ejes.plot(posiciones, valores_crudo, marker="o", markersize=4,
              linewidth=2, label="IMAR", color=COLOR_IMAR_CRUDO)
    ejes.plot(posiciones, valores_ajustado, marker="o", markersize=4,
              linewidth=2, label="IMAR Ajustado", color=COLOR_IMAR_AJUSTADO)

    titulo_grafico = _formatear_titulo_con_fecha(tabla_imar["fecha"])
    ejes.set_title(titulo_grafico, fontsize=14, fontweight="bold")
    ejes.set_ylabel("$/kWh")
    ejes.set_xlabel("Periodo")
    ejes.set_xticks(posiciones)
    ejes.set_xticklabels(periodos, rotation=0, fontsize=8)
    ejes.grid(True, linestyle="--", alpha=0.3)
    ejes.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=2, frameon=False)

    # El eje Y siempre parte desde 0, para compartir la misma base
    # visual con las demas graficas del informe.
    ejes.set_ylim(bottom=0)

    # Mas espacio abajo para que la leyenda no se encime con las
    # etiquetas del eje X.
    figura.subplots_adjust(bottom=0.18)

    ruta = os.path.join(CARPETA_ACTUAL, "imar_siguiente_dia.png")
    figura.savefig(ruta, dpi=150)
    plt.close(figura)

    print("Grafico de IMAR generado: " + ruta)
    return ruta


if __name__ == "__main__":
    # Prueba rapida con datos ficticios, para poder correr este
    # archivo solo y ver que el grafico se genera bien.
    tabla_prueba = {
        "fecha": "2026-07-09",
        "filas": [
            {"periodo": "00:00-01:00", "imar_crudo": 350.0, "imar_ajustado": 360.0},
            {"periodo": "01:00-02:00", "imar_crudo": 340.0, "imar_ajustado": 345.0},
            {"periodo": "02:00-03:00", "imar_crudo": 330.0, "imar_ajustado": 335.0},
        ]
    }
    generar_grafico_imar_siguiente_dia(tabla_prueba)
