"""
Modulo: grafico_imar.py
Ubicacion: Graficas/grafico_imar.py

Genera el grafico de LINEA del IMAR (Crudo y Ajustado) periodo a
periodo, para el dia siguiente. Se usa dentro del informe diario,
justo despues del grafico de tendencia anual y antes de la tabla
del IMAR, como complemento visual.

El grafico se guarda como imagen .png dentro de esta misma carpeta.
"""

import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

CARPETA_ACTUAL = os.path.dirname(os.path.abspath(__file__))

COLOR_IMAR_CRUDO = "#7F9CC4"
COLOR_IMAR_AJUSTADO = "#1F4E79"


def generar_grafico_imar_siguiente_dia(tabla_imar):
    """
    Genera el grafico de linea del IMAR Crudo vs Ajustado, periodo a
    periodo, a partir del diccionario ya calculado por
    obtener_tabla_imar_siguiente_dia() (en Reportes/tabla_imar_siguiente_dia.py).

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

    periodos = [f["periodo"] for f in tabla_imar["filas"]]
    valores_crudo = [f["imar_crudo"] for f in tabla_imar["filas"]]
    valores_ajustado = [f["imar_ajustado"] for f in tabla_imar["filas"]]

    posiciones = np.arange(len(periodos))

    figura, ejes = plt.subplots(figsize=(11, 5.5))

    ejes.plot(posiciones, valores_crudo, marker="o", markersize=4,
              linewidth=2, label="IMAR Crudo", color=COLOR_IMAR_CRUDO)
    ejes.plot(posiciones, valores_ajustado, marker="o", markersize=4,
              linewidth=2, label="IMAR Ajustado", color=COLOR_IMAR_AJUSTADO)

    ejes.set_title("IMAR del dia siguiente - Periodo a periodo", fontsize=13, fontweight="bold")
    ejes.set_ylabel("$/kWh")
    ejes.set_xlabel("Periodo")
    ejes.set_xticks(posiciones)
    ejes.set_xticklabels(periodos, rotation=90, fontsize=8)
    ejes.grid(True, linestyle="--", alpha=0.3)
    ejes.legend(loc="upper center", bbox_to_anchor=(0.5, -0.28), ncol=2, frameon=False)

    figura.tight_layout()

    ruta = os.path.join(CARPETA_ACTUAL, "imar_siguiente_dia.png")
    figura.savefig(ruta, dpi=150)
    plt.close(figura)

    print("Grafico de IMAR generado: " + ruta)
    return ruta


if __name__ == "__main__":
    # Prueba rapida con datos ficticios, para poder correr este
    # archivo solo y ver que el grafico se genera bien.
    tabla_prueba = {
        "fecha": "2026-07-08",
        "filas": [
            {"periodo": "00:00-01:00", "imar_crudo": 350.0, "imar_ajustado": 360.0},
            {"periodo": "01:00-02:00", "imar_crudo": 340.0, "imar_ajustado": 345.0},
            {"periodo": "02:00-03:00", "imar_crudo": 330.0, "imar_ajustado": 335.0},
        ]
    }
    generar_grafico_imar_siguiente_dia(tabla_prueba)
