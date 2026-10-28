# Reporte mensual de contratos de gas natural

Programa que lee los datos del Gestor del Mercado de Gas Natural (BEC) y
genera un reporte con análisis y gráficas el último día hábil de cada mes,
en los mercados primario y secundario,
con seguimiento a los puntos de entrega **Cusiana, Floreña y Cartagena (GNL importado)**.

## Carpetas y archivos

| Archivo | Qué es |
|---|---|
| `generar_reporte.py` | El programa principal (la "receta"). |
| `calendario.py` | Calcula el último día hábil del mes (con festivos de Colombia). |
| `.github/workflows/reporte_mensual.yml` | El "despertador" de GitHub Actions. |
| `descargar_bec.py` | El robot que descarga los datos del BEC solo. |
| `enviar_correo.py` | El cartero: envía el reporte por Gmail. |
| `config.py` | El panel de control: rutas, puntos de la Orinoquía, alertas, colores. |
| `requirements.txt` | Las librerías que hay que instalar. |
| `pruebas/` | Datos INVENTADOS para probar el reporte por puntos (`crear_datos_prueba.py`). |
| `datos/` | Aquí van los Excel exportados del BEC. |
| `salida/` | Aquí aparece el reporte terminado (`reporte_AAAA-MM-DD.html`). |

## Cómo usarlo en tu computador

1. Instala Python (https://www.python.org/downloads/). En Windows, marca la casilla **"Add Python to PATH"**.
2. Abre una terminal dentro de esta carpeta.
3. Instala las librerías (solo la primera vez):
   `pip install -r requirements.txt`
4. Pon el Excel del BEC en `datos/` con el nombre `tabla_resultados.xlsx`.
5. Ejecuta uno de estos comandos:
   - `python generar_reporte.py` → reporte del mes actual.
   - `python generar_reporte.py --mes 2026-09` → reporte de un mes específico.
   - `python generar_reporte.py --solo-ultimo-dia-habil` → solo trabaja si hoy es el último día hábil.
   - `python generar_reporte.py --enviar` → además lo envía por Gmail (necesita las claves).
   - `python generar_reporte.py --prueba --mes 2026-09` → reporte con datos inventados (para probar).
   - `python calendario.py` → muestra los últimos días hábiles del año.
6. Abre el archivo que aparece en `salida/` con tu navegador.

## Etapas del proyecto

- [x] Etapa 1: reporte mensual con gráficas y análisis automático.
- [x] Etapa 2: envío por Gmail (claves en GitHub Secrets: `GMAIL_USUARIO`, `GMAIL_CLAVE_APP`, `CORREO_DESTINO`).
- [x] Etapa 3 (preparada): despertador el último día hábil de cada mes (GitHub Actions).
- [x] Etapa 4: descarga automática de los datos del BEC (`descargar_bec.py`).
