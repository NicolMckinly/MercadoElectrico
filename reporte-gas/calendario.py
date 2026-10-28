# =====================================================================
# calendario.py  —  ¿HOY ES EL ÚLTIMO DÍA HÁBIL DEL MES?
# ---------------------------------------------------------------------
# Un "día hábil" es un día de trabajo: de lunes a viernes y que no sea
# festivo. El último día hábil del mes NO siempre es el día 30 o 31:
#   - Si el mes termina en sábado o domingo, es el viernes anterior.
#   - Si ese viernes es festivo, es el jueves, y así sucesivamente.
#
# Para saber los festivos de Colombia usamos la librería "holidays",
# que ya trae la lista de cada año (incluidos los que se pasan a lunes).
# =====================================================================

import calendar
from datetime import date, timedelta

import holidays


def es_dia_habil(dia):
    """True si el día es de lunes a viernes y no es festivo en Colombia."""
    festivos = holidays.Colombia(years=dia.year)
    # weekday(): lunes = 0, martes = 1, ... sábado = 5, domingo = 6
    return dia.weekday() < 5 and dia not in festivos


def ultimo_dia_habil(anio, mes):
    """Busca el último día hábil de un mes.

    Empieza en el último día del mes y va retrocediendo un día a la vez
    hasta encontrar uno hábil. Es como buscar, desde el final del
    calendario hacia atrás, el primer día que no esté pintado de rojo.
    """
    ultimo_dia_numero = calendar.monthrange(anio, mes)[1]   # 28, 29, 30 o 31
    dia = date(anio, mes, ultimo_dia_numero)
    while not es_dia_habil(dia):
        dia = dia - timedelta(days=1)
    return dia


def hoy_es_ultimo_dia_habil(hoy=None):
    """True si hoy (o la fecha que le pasemos) es el último día hábil del mes."""
    hoy = hoy or date.today()
    return hoy == ultimo_dia_habil(hoy.year, hoy.month)


# Si ejecutas este archivo solo (python calendario.py), te muestra
# el último día hábil de cada mes del año. Sirve para comprobar que
# el cálculo está bien.
if __name__ == "__main__":
    anio = date.today().year
    nombres = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
               "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
    dias = ["lunes", "martes", "miércoles", "jueves", "viernes"]
    print(f"Últimos días hábiles de {anio}:")
    for mes in range(1, 13):
        d = ultimo_dia_habil(anio, mes)
        print(f"  {nombres[mes - 1]:>10}: {dias[d.weekday()]} {d:%d/%m/%Y}")
