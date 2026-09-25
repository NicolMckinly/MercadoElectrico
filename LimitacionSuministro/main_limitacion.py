"""
main_limitacion.py

Orquesta el proceso completo: descarga los archivos de XM, los
procesa y envía el reporte a Teams (normalmente como un solo mensaje;
solo se divide en dos si de verdad no cabe).
"""

import datetime

from descargar_archivos import descargar_archivos
from procesar_limitacion import procesar_archivo
from enviar_teams import enviar_a_teams

MESES_ES = {
    1: "enero", 2: "febrero", 3: "marzo", 4: "abril",
    5: "mayo", 6: "junio", 7: "julio", 8: "agosto",
    9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre",
}


def _fecha_en_espanol(fecha):
    return f"{fecha.day} de {MESES_ES[fecha.month]} de {fecha.year}"


def main():
    print("1/3 Descargando archivos de XM...")
    rutas = descargar_archivos(carpeta_destino=".")

    print("2/3 Procesando archivos...")
    datos_corte_usuarios = procesar_archivo(rutas["corte_usuarios.xlsx"])
    datos_en_bolsa = procesar_archivo(rutas["en_bolsa.xlsx"])

    fecha_texto = _fecha_en_espanol(datetime.date.today())

    print("3/3 Enviando reporte a Teams...")
    enviar_a_teams(fecha_texto, datos_corte_usuarios, datos_en_bolsa)

    print("Listo.")


if __name__ == "__main__":
    main()
