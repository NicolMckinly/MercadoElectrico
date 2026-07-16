"""
Modulo: grafico_generacion.py
Ubicacion: Graficas/grafico_generacion.py
Genera el grafico de AREAS APILADAS de Generacion por Fuente, con
las categorias combinadas segun lo definido en listado_recursos.py:
- Hidraulica
- Termica (carbon + gas + liquidos combinados)
- Solar y Eolica (combinadas)
- Autogen. y Cogen. y Gen. Distribuida (combinadas)

Incluye tambien una version de los ULTIMOS 12 MESES MOVILES
(terminando ayer), usada en el Resumen Ejecutivo Quincenal.

Los graficos se guardan como imagenes .png dentro de esta misma carpeta.
"""
import sys
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
CARPETA_PROYECTO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(CARPETA_PROYECTO, "BaseDatos"))
from base_datos import consultar_todo_generacion_por_fuente
from zona_horaria import ahora_colombia
CARPETA_ACTUAL = os.path.dirname(os.path.abspath(__file__))
COLORES_TECNOLOGIA = {
    "Hidraulica": "#1F6F50",
    "Termica": "#B22222",
    "Solar y Eolica": "#D9822B",
    "Autogen. y Cogen. y Gen. Distribuida": "#8E44AD",
    "Otras tecnologias": "#95A5A6",
}
# Nombres de exhibicion para la leyenda del grafico (distintos a los
# nombres internos que se usan para guardar en la base de datos)
ETIQUETAS_MOSTRAR = {
    "Hidraulica": "Hidrica",
    "Termica": "Termica Carbon+Gas+Liquidos",
    "Solar y Eolica": "Solar+Eolica",
    "Autogen. y Cogen. y Gen. Distribuida": "Autog+Cog+Gdist",
    "Otras tecnologias": "Otras tecnologias",
}
# Orden fijo para que el apilado sea siempre consistente entre ejecuciones
ORDEN_TECNOLOGIAS = ["Hidraulica", "Termica", "Solar y Eolica", "Autogen. y Cogen. y Gen. Distribuida", "Otras tecnologias"]
def generar_grafico_generacion():
    """
    Genera el grafico de areas apiladas de Generacion por Fuente, de
    los ultimos dias disponibles.
    Retorna:
        La ruta del archivo generado, o None si no hay datos.
    """
    datos = consultar_todo_generacion_por_fuente()
    if len(datos) == 0:
        print("No hay datos de generacion por fuente disponibles todavia.")
        return None
    datos["fecha_dt"] = datos["fecha"].apply(lambda f: datetime.strptime(f, "%Y-%m-%d"))
    datos["valor_gwh"] = datos["valor_kwh"] / 1_000_000
    tabla_pivote = datos.pivot(index="fecha_dt", columns="tecnologia", values="valor_gwh")
    tabla_pivote = tabla_pivote.sort_index().fillna(0)
    tecnologias_presentes = [t for t in ORDEN_TECNOLOGIAS if t in tabla_pivote.columns]
    colores = [COLORES_TECNOLOGIA.get(t, "#CCCCCC") for t in tecnologias_presentes]
    etiquetas = [ETIQUETAS_MOSTRAR.get(t, t) for t in tecnologias_presentes]
    figura, ejes = plt.subplots(figsize=(11, 5.5))
    ejes.stackplot(
        tabla_pivote.index,
        [tabla_pivote[t] for t in tecnologias_presentes],
        labels=etiquetas,
        colors=colores,
        alpha=0.85
    )
    ejes.set_title("Generacion por fuente", fontsize=13, fontweight="bold")
    ejes.set_ylabel("GWh")
    ejes.set_xlabel("Fecha")
    ejes.xaxis.set_major_formatter(mdates.DateFormatter("%d-%b"))
    ejes.grid(True, linestyle="--", alpha=0.3)
    ejes.legend(loc="upper center", bbox_to_anchor=(0.5, -0.18), ncol=2, frameon=False)
    figura.tight_layout()
    ruta = os.path.join(CARPETA_ACTUAL, "generacion_por_fuente.png")
    figura.savefig(ruta, dpi=150)
    plt.close(figura)
    print("Grafico de generacion por fuente generado: " + ruta)
    return ruta


def generar_grafico_generacion_anual_ejecutivo():
    """
    Genera el grafico de Generacion por Fuente de los ULTIMOS 12
    MESES MOVILES (terminando ayer), para el Resumen Ejecutivo
    Quincenal. Version independiente de generar_grafico_generacion()
    (que usa todo el historico disponible para el informe de
    variables).

    Retorna:
        La ruta del archivo generado, o None si no hay datos.
    """
    hoy = ahora_colombia()
    fecha_fin = (hoy - timedelta(days=1)).replace(tzinfo=None)
    fecha_inicio_texto = (fecha_fin - timedelta(days=365)).strftime("%Y-%m-%d")
    fecha_fin_texto = fecha_fin.strftime("%Y-%m-%d")

    datos = consultar_todo_generacion_por_fuente()
    if len(datos) == 0:
        print("No hay datos de generacion por fuente disponibles todavia.")
        return None

    datos = datos[(datos["fecha"] >= fecha_inicio_texto) & (datos["fecha"] <= fecha_fin_texto)]
    if len(datos) == 0:
        print("No hay datos de generacion por fuente en el rango de los ultimos 12 meses.")
        return None

    datos["fecha_dt"] = datos["fecha"].apply(lambda f: datetime.strptime(f, "%Y-%m-%d"))
    datos["valor_gwh"] = datos["valor_kwh"] / 1_000_000
    tabla_pivote = datos.pivot(index="fecha_dt", columns="tecnologia", values="valor_gwh")
    tabla_pivote = tabla_pivote.sort_index().fillna(0)

    tecnologias_presentes = [t for t in ORDEN_TECNOLOGIAS if t in tabla_pivote.columns]
    colores = [COLORES_TECNOLOGIA.get(t, "#CCCCCC") for t in tecnologias_presentes]
    etiquetas = [ETIQUETAS_MOSTRAR.get(t, t) for t in tecnologias_presentes]

    figura, ejes = plt.subplots(figsize=(11, 5.5))
    ejes.stackplot(
        tabla_pivote.index,
        [tabla_pivote[t] for t in tecnologias_presentes],
        labels=etiquetas,
        colors=colores,
        alpha=0.85
    )
    ejes.set_title("Generacion por Fuente - Últimos 12 Meses", fontsize=13, fontweight="bold")
    ejes.set_ylabel("GWh")
    ejes.set_xlabel("Fecha")
    ejes.xaxis.set_major_formatter(mdates.DateFormatter("%b-%y"))
    ejes.xaxis.set_major_locator(mdates.MonthLocator())
    ejes.grid(True, linestyle="--", alpha=0.3)
    ejes.legend(loc="upper center", bbox_to_anchor=(0.5, -0.18), ncol=2, frameon=False)
    figura.tight_layout()

    ruta = os.path.join(CARPETA_ACTUAL, "generacion_por_fuente_anual_ejecutivo.png")
    figura.savefig(ruta, dpi=150)
    plt.close(figura)

    print("Grafico de generacion por fuente (12 meses moviles) generado: " + ruta)
    return ruta


if __name__ == "__main__":
    generar_grafico_generacion()
