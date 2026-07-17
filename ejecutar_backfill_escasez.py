"""
Script de UN SOLO USO para llenar el hueco de Precio de Escasez.

Como usarlo:
1. Guardalo en la raiz de tu proyecto MercadoElectrico (al mismo
   nivel que la carpeta API/).
2. Abre una terminal en esa carpeta.
3. Ejecuta: python ejecutar_backfill_escasez.py
4. Cuando termine, borra este archivo (ya cumplio su proposito).
"""

import sys
import os

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "API"))

from precio_escasez import backfill_ultimos_12_meses_escasez

if __name__ == "__main__":
    backfill_ultimos_12_meses_escasez()
    print("")
    print("Listo. Revisa tu base de datos o vuelve a generar el Resumen")
    print("Ejecutivo para confirmar que la grafica de 12 meses ya no")
    print("tiene el hueco.")
