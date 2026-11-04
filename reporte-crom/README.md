# Reporte mensual CROM / PAT

Programa que descarga de XM los **Valores CROM definitivos**, calcula CROM 1, CROM 2 y
Patrimonio transaccional de los agentes seguidos y envía el correo
**CROM/PAT (Mes-Mes Año)** el 1er o 2do día hábil de cada mes.

XM publica en el mes M la carpeta del mes M-1 (en noviembre se toma `10.Oct`).

## Carpetas y archivos

| Archivo | Qué es |
|---|---|
| `crom_reporte.py` | El programa: descarga de XM, cálculo, Excel y correo. |
| `../.github/workflows/reporte_crom_mensual.yml` | El "despertador" de GitHub Actions. |
| `respaldo_capital.png` | Imagen "Respaldo de capital" que va en el correo. |
| `firma.jpg` | Firma que va al final del correo. |
| `enviados.log` | Meses ya enviados (lo actualiza el robot; evita enviar dos veces). |
| `requirements.txt` | Las librerías que hay que instalar. |

## Cálculo
- **CROM 1 / CROM 2 (MWh)** = promedio de los 3 primeros meses publicados de (kWh-mes ÷ horas del mes) ÷ 1.000
- **Patrimonio (miles de millones COP)** = PAT ÷ 1.000.000.000

## Secrets que usa
| Secret | Qué es |
|---|---|
| `CORREO_REMITENTE` | La cuenta de Gmail que envía (ya existía). |
| `CORREO_CONTRASENA_CROM` | Contraseña de aplicación "CROM" de esa cuenta. |
| `CORREO_DESTINO_CROM` | Destinatarios "Para", separados por comas. |
| `CORREO_CC_CROM` | Destinatarios "CC", separados por comas (opcional). |
| `CORREO_RESPONDER_A_CROM` | A dónde llegan las respuestas (opcional). |

## Ejecutarlo a mano
Pestaña **Actions** → **Reporte mensual CROM-PAT** → **Run workflow**
(`prueba` = solo al Gmail remitente, `enviar` = destinatarios reales, `no` = solo Excel).
El Excel queda en la ejecución, sección **Artifacts** → `reporte-crom`.

## Cambiar agentes
En `crom_reporte.py`, lista `AGENTES` (nombre en el reporte, sigla en XM).
