"""
Limpia la carpeta Reportes/ dejando solo el PDF mas reciente de cada tipo de informe.

Los nombres de archivo siguen el patron:
    <Tipo_De_Informe>_YYYY_MM_DD.pdf
Ejemplos:
    Informe_Diario_PrecioBolsa_2026_08_10.pdf
    Informe_Hidrologico_2026_08_05.pdf

El script agrupa los archivos por "tipo" (todo lo que va antes de la fecha),
y en cada grupo borra todos menos el de fecha mas reciente.
"""

import re
from pathlib import Path

CARPETA_REPORTES = Path("Reportes")

# Patron: captura el "tipo" (prefijo) y la fecha YYYY_MM_DD antes de .pdf
PATRON = re.compile(r"^(.*)_(\d{4}_\d{2}_\d{2})\.pdf$")


def limpiar_reportes_viejos(carpeta: Path = CARPETA_REPORTES) -> None:
    if not carpeta.exists():
        print(f"La carpeta {carpeta} no existe, no hay nada que limpiar.")
        return

    # Agrupa los archivos por tipo de informe
    grupos = {}
    for archivo in carpeta.glob("*.pdf"):
        match = PATRON.match(archivo.name)
        if not match:
            # Si un archivo no sigue el patron esperado, se deja intacto
            continue
        tipo, fecha = match.groups()
        grupos.setdefault(tipo, []).append((fecha, archivo))

    total_borrados = 0
    for tipo, archivos in grupos.items():
        # Ordena por fecha (como string funciona porque el formato es YYYY_MM_DD)
        archivos.sort(key=lambda x: x[0])
        mas_reciente = archivos[-1][1]
        for fecha, archivo in archivos[:-1]:
            print(f"Borrando informe viejo: {archivo.name}")
            archivo.unlink()
            total_borrados += 1
        print(f"Se conserva: {mas_reciente.name}")

    print(f"\nListo. Se borraron {total_borrados} PDF(s) viejo(s).")


if __name__ == "__main__":
    limpiar_reportes_viejos()
