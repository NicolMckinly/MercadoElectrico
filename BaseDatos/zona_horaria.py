"""
Modulo: zona_horaria.py
Ubicacion: BaseDatos/zona_horaria.py

El servidor donde corre este sistema (GitHub Actions) usa la hora
UTC, NO la hora de Colombia. Colombia esta 5 horas detras de UTC,
asi que usar datetime.now() directamente puede hacer que el sistema
"crea" que ya es el dia siguiente varias horas antes de que
realmente lo sea en Colombia (por ejemplo, a las 7:00 PM en Colombia,
en UTC ya es medianoche del dia siguiente).

Este modulo centraliza el calculo de "la hora actual en Colombia",
para que TODO el sistema use siempre el mismo criterio.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

ZONA_COLOMBIA = ZoneInfo("America/Bogota")


def ahora_colombia():
    """
    Retorna la fecha y hora actual, correctamente ajustada a la
    zona horaria de Colombia, sin importar en que zona horaria este
    corriendo el servidor.
    """
    return datetime.now(ZONA_COLOMBIA)
