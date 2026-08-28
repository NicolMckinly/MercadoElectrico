"""
main_limitacion.py

Orquesta el proceso completo de los jueves:
  1. Descarga los 2 Excel de XM.
  2. Los procesa (filtra últimos 8 días, deduplica).
  3. Arma la tarjeta y la envía al canal de Teams.
"""

from datetime import datetime

from descargar_archivos import descargar_archivos
from procesar_limitacion import procesar_archivo
from enviar_teams import construir_tarjeta, enviar_a_teams

MESES_ES = {
    1: "enero", 2: "febrero", 3: "marzo", 4: "abril", 5: "mayo", 6: "junio",
    7: "julio", 8: "agosto", 9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre",
}


def _fecha_en_espanol(fecha):
    return f"{fecha.day} de {MESES_ES[fecha.month]} de {fecha.year}"


def main():
    print("1/3 Descargando archivos de XM...")
    rutas = descargar_archivos(carpeta_destino=".")

    print("2/3 Procesando archivos...")
    datos_corte_usuarios = procesar_archivo(rutas["corte_usuarios.xlsx"])
    datos_en_bolsa = procesar_archivo(rutas["en_bolsa.xlsx"])

    print("3/3 Enviando a Teams...")
    hoy = datetime.now().date()
    payload = construir_tarjeta(_fecha_en_espanol(hoy), datos_corte_usuarios, datos_en_bolsa)
    enviar_a_teams(payload)

    print("Listo. Mensaje enviado al canal de Teams.")


if __name__ == "__main__":
    main()
