# Contexto del proyecto: reporte mensual de contratos de gas natural

Este documento resume todo lo hecho hasta ahora, para continuar el trabajo
en otra conversación o con otra persona. Última actualización: 21/10/2026.

## Cómo trabajar conmigo (preferencias del usuario)

- Responder siempre en **español**. El usuario está en Colombia.
- **Explicar todo muy al detalle, como a un estudiante de 7.º grado**:
  con comparaciones sencillas, paso a paso, explicando qué hace cada
  archivo y cada parte importante del código, y cómo probarlo.
- El usuario tiene cuenta de **GitHub** y usará **GitHub Actions**.
- El correo de envío es **Gmail**, con una llave ya guardada en GitHub Secrets.

## Objetivo

Hacer seguimiento al mercado de gas natural de Colombia, con énfasis en la
**Orinoquía**. Un reporte que se genere solo y llegue por correo el
**último día hábil de cada mes**, con gráficas y un análisis breve sobre:
cantidades contratadas, precios, modalidades de contrato, mercado primario y
secundario, puntos de entrega y campo de origen.

## Fuente de los datos

- **BEC** (Boletín Electrónico Central) del **Gestor del Mercado de Gas
  Natural**, función que ejerce la Bolsa Mercantil de Colombia (BMC).
  Página del mercado primario:
  https://www.bmcbec.com.co/informaci%C3%B3n-transaccional/mercado-primario/informaci%C3%B3n-suministro
- Los datos salen del **registro obligatorio de contratos**: vendedores y
  compradores declaran sus contratos ante el Gestor. Norma vigente:
  **Resolución CREG 102 015 de 2025** (derogó la CREG 186 de 2020; eliminó
  las modalidades C1 y C2).
- El tablero es **Power BI**. Pestañas "Nacional" y "Puntos". Tiene una
  "Tabla de resultados" que se exporta con "…" → "Exportar datos".
- Unidades: cantidad en **MBTUD**; precio en **USD/MBTU**.

### Limitaciones importantes de los datos

- El Gestor **no publica negociaciones individuales con nombres**: no se
  puede saber, con datos públicos, quién compró a quién. Los vendedores se
  pueden inferir por campo; los compradores en general no.
  Opción: preguntar a la BMC por servicios de información
  (gestordegas@bolsamercantil.com.co).
- Con la norma de 2025, las ofertas de negociación directa del mercado
  primario deben publicarse en la web del vendedor y anunciarse vía el
  Gestor (fuente posible para saber quién ofrece y de qué campo).
- Las cantidades del archivo exportado **coinciden exactamente** con el
  tablero. Los **precios difieren unos centavos**: el BEC probablemente
  pondera también por duración del contrato, dato que no viene en el
  archivo. Nuestro precio es ponderado solo por cantidad.
- "ND" = precio no disponible.

## Estado actual del proyecto

| Etapa | Estado |
|---|---|
| 1. Reporte mensual con gráficas y análisis automático | Hecho |
| 2. Envío por Gmail | Hecho (probado con simulador; falta la prueba real) |
| 3. Despertador de GitHub Actions (último día hábil) | Hecho (falta subirlo y probarlo) |
| 4. Descarga automática de datos del BEC | Pendiente |

## Estructura del proyecto

| Archivo | Qué hace |
|---|---|
| `generar_reporte.py` | Programa principal: lee el Excel, calcula, grafica, arma el HTML y (opcional) envía. |
| `config.py` | Panel de control: ruta del Excel, puntos de la Orinoquía, umbrales de alerta, colores. |
| `calendario.py` | Calcula el último día hábil del mes con festivos de Colombia (librería `holidays`). |
| `enviar_correo.py` | Envía por Gmail (SMTP SSL, smtp.gmail.com:465) con imágenes como CID y el HTML adjunto. |
| `.github/workflows/reporte_mensual.yml` | Corre los días 24–31 a las 22:00 UTC (5 p.m. Colombia, `TZ: America/Bogota`); el script decide si es el último día hábil. Tiene botón manual con cajita "Mes a reportar" (AAAA-MM; vacío = mes actual). |
| `requirements.txt` | pandas, openpyxl, matplotlib, holidays. |
| `datos/tabla_resultados.xlsx` | Excel exportado del BEC (por ahora se actualiza a mano). |
| `salida/` | Reportes generados (ignorada por git). |

### Opciones del programa

- `python generar_reporte.py` → reporte del mes actual.
- `python generar_reporte.py --mes 2026-09` → un mes específico.
- `python generar_reporte.py --solo-ultimo-dia-habil` → solo trabaja el último día hábil.
- `python generar_reporte.py --enviar` → además envía por Gmail.

### Secretos de GitHub que usa el workflow

`GMAIL_USUARIO`, `GMAIL_CLAVE_APP` (contraseña de aplicación de 16 letras,
requiere verificación en dos pasos) y `CORREO_DESTINO` (uno o varios,
separados por coma). Si el secreto del usuario tiene otro nombre, se cambia
solo el lado derecho en el YAML (`${{ secrets.NOMBRE }}`).

### Qué contiene el reporte

1. Caja de alertas (precio > 20 % sobre el promedio de 12 meses, o cantidad > 1,5 veces el promedio).
2. Análisis en frases: totales del mes, comparación contra el mes anterior,
   contra el mismo mes del año pasado y contra el promedio de 12 meses;
   modalidad dominante, la más cara y la más barata; rango de precios.
3. Tabla por modalidad (cantidad, participación, precio, negociaciones).
4. Gráficas: barras apiladas por modalidad + línea de precio (13 meses);
   precio por modalidad (las líneas se cortan en meses sin datos);
   dispersión de precios de cada negociación del mes.

## Pendientes (en orden sugerido)

1. **Prueba real del correo**: subir el proyecto a GitHub (incluida la
   carpeta oculta `.github`), revisar los secretos y usar "Run workflow"
   (escribir `2026-09` en la cajita del mes). Guía paso a paso en
   `GUIA_PRUEBA_GITHUB.md`. Preparado el 21/10/2026: botón con selector de
   mes, error (rojo en GitHub) si no hay datos del mes, y mensaje claro si
   Gmail rechaza la clave. Falta que el usuario la ejecute.
2. **Datos de la Orinoquía**: el Excel actual solo trae "Nacional". Falta
   exportar la tabla de la pestaña **"Puntos"** (primario y secundario) y
   confirmar los nombres exactos de los puntos. Lista provisional en
   `config.py`: Cusiana, Cupiagua, Floreña, Pauto, Apiay.
3. **Mercado secundario**: agregar al reporte (sección aparte en el BEC).
4. **Robot de descarga (Etapa 4)**: plan acordado = Playwright con navegador
   invisible que entra al BEC, abre "Puntos", hace "…" → "Exportar datos" y
   guarda el Excel. Debe tomar capturas de pantalla de cada paso y, si
   falla, enviar un correo de aviso. Plan B: consultar directamente el
   servicio de Power BI (no oficial). En paralelo: pedir a la BMC un enlace
   fijo de descarga.
   Nota: el entorno de Claude no tiene acceso de red a bmcbec.com.co, así
   que el robot debe probarlo el usuario en su computador.
5. **Histórico**: guardar una copia de los datos de cada mes para detectar
   registros tardíos y revisiones de meses anteriores.

## Ubicación en GitHub (21/10/2026)

El proyecto vive dentro del repositorio **MercadoElectrico** (público), en la
carpeta `ReporteGas/`. El workflow está en
`.github/workflows/reporte_gas_mensual.yml` (en la raíz del repositorio, porque
GitHub solo lee workflows ahí) y usa `working-directory: ReporteGas`. Usa los
secretos de Gmail del mismo repositorio.
