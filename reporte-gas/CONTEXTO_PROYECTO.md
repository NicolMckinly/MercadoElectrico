# Contexto del proyecto: reporte mensual de contratos de gas natural

Este documento resume todo lo hecho hasta ahora, para continuar el trabajo
en otra conversación o con otra persona. Última actualización: 23/10/2026.

## Cómo trabajar conmigo (preferencias del usuario)

- Responder siempre en **español**. El usuario está en Colombia.
- **Explicar todo muy al detalle, como a un estudiante de 7.º grado**:
  con comparaciones sencillas, paso a paso, explicando qué hace cada
  archivo y cada parte importante del código, y cómo probarlo.
- El usuario tiene cuenta de **GitHub** y usará **GitHub Actions**.
- El correo de envío es **Gmail**, con una llave ya guardada en GitHub Secrets.

## Objetivo

Hacer seguimiento al mercado de gas natural de Colombia, por **punto de
entrega**: **Cusiana, Floreña y Cartagena (GNL importado)**. (Antes era por
región Orinoquía; el usuario decidió cambiarlo a puntos.) Un reporte que se genere solo y llegue por correo el
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

## Dónde vive el proyecto

Repositorio público **NicolMckinly/MercadoElectrico** (rama `master`), que ya
tiene otro sistema (API, Correos, BaseDatos, etc.). El proyecto de gas está en
la carpeta **`reporte-gas/`**. El despertador está en la raíz:
`.github/workflows/reporte_gas_mensual.yml`, con
`working-directory: reporte-gas`, una cajita `mes` en "Run workflow", y los
secretos del usuario: `CORREO_REMITENTE` → GMAIL_USUARIO,
`CORREO_CONTRASENA_APP` → GMAIL_CLAVE_APP, `CORREO_DESTINO` → CORREO_DESTINO.
Nunca subir archivos a la raíz del repositorio (pisaría el otro sistema).

## Estado actual del proyecto

| Etapa | Estado |
|---|---|
| 1. Reporte mensual con gráficas y análisis automático | Hecho |
| 2. Envío por Gmail | Hecho (probado con simulador; falta la prueba real) |
| 3. Despertador de GitHub Actions (último día hábil) | Hecho (falta subirlo y probarlo) |
| 4. Descarga automática de datos del BEC (robot Playwright) | Hecho (probado contra un tablero falso; falta la prueba real) |

## Estructura del proyecto

| Archivo | Qué hace |
|---|---|
| `generar_reporte.py` | Programa principal: lee el Excel, calcula, grafica, arma el HTML y (opcional) envía. |
| `config.py` | Panel de control: ruta del Excel, `PUNTOS_SEGUIMIENTO` (nombre en el reporte → palabras clave, sin importar tildes ni mayúsculas), umbrales de alerta, colores. |
| `calendario.py` | Calcula el último día hábil del mes con festivos de Colombia (librería `holidays`). |
| `descargar_bec.py` | Robot (Playwright, Chromium invisible, locale es-CO): abre `config.URL_BEC_SUMINISTRO`, busca el iframe cuyo src contiene "powerbi" y lo abre directo, clic en la pestaña "Puntos" (texto exacto), hover sobre "Tabla de resultados", botón «…» (prueba varios selectores: rol button "Más opciones/More options", `data-testid=visual-more-options-btn`, `.vcMenuBtn`, aria-label), "Exportar datos", botón "Exportar" y espera la descarga. Toma fotos numeradas en `capturas/`. Revisa el archivo (≥100 filas y que no sea solo "Nacional") antes de reemplazar `datos/puntos.xlsx`; si falla, conserva el anterior y sale con código 1. |
| `enviar_correo.py` | Envía por Gmail (SMTP SSL, smtp.gmail.com:465) con imágenes como CID y el HTML adjunto. |
| `.github/workflows/reporte_mensual.yml` | Corre los días 24–31 a las 22:00 UTC (5 p.m. Colombia, `TZ: America/Bogota`); el script decide si es el último día hábil. Tiene botón manual. |
| `requirements.txt` | pandas, openpyxl, matplotlib, holidays, playwright. |
| `pruebas/` | `crear_datos_prueba.py` genera `ficticio_<punto>.xlsx` (un archivo por punto) con datos INVENTADOS en formato BEC. `--prueba` los usa y el reporte muestra un aviso grande. |
| `datos/` | Carpeta con los Excel exportados del BEC (a mano por ahora). El programa lee y junta TODOS los .xlsx (`config.CARPETA_DATOS`). El tablero del BEC solo deja elegir un punto a la vez, así que se descargan 3 archivos: `cusiana.xlsx`, `florena.xlsx`, `cartagena.xlsx`. Si un archivo no trae la columna de punto, se usa su nombre. Archivos idénticos se leen una sola vez (huella MD5). |
| `salida/` | Reportes generados (ignorada por git). |

### Opciones del programa

- `python generar_reporte.py` → reporte del mes actual.
- `python generar_reporte.py --mes 2026-09` → un mes específico.
- `python generar_reporte.py --solo-ultimo-dia-habil` → solo trabaja el último día hábil.
- `python generar_reporte.py --enviar` → además envía por Gmail.
- `python generar_reporte.py --prueba` → usa los datos inventados de `pruebas/`.

### Secretos de GitHub que usa el workflow

`GMAIL_USUARIO`, `GMAIL_CLAVE_APP` (contraseña de aplicación de 16 letras,
requiere verificación en dos pasos) y `CORREO_DESTINO` (uno o varios,
separados por coma). Si el secreto del usuario tiene otro nombre, se cambia
solo el lado derecho en el YAML (`${{ secrets.NOMBRE }}`).

### Qué contiene el reporte

1. Aviso si el archivo solo trae "Nacional" o si no encontró algún punto.
2. Caja de alertas por punto (precio > 20 % sobre su promedio de 12 meses,
   o cantidad > 1,5 veces su promedio).
3. Comparación entre puntos: frases (participación, punto más caro y más
   barato, diferencia), tabla con flechas de cambio frente al mes anterior,
   gráfica de precio por punto, gráfica de cantidad por punto y gráfica de
   dispersión de cada negociación del mes (color = modalidad).
4. Una sección por punto: frases (cantidad, cambios contra el mes anterior,
   el año anterior y su promedio; modalidad principal; rango de precios),
   tabla por modalidad y gráfica de barras apiladas + línea de precio.
5. Al final: qué nombres del BEC cayeron en cada punto y qué otros puntos
   había en el archivo (para ajustar las palabras clave).
6. Si el archivo solo trae "Nacional", el reporte funciona igual con una
   sola sección "Nacional".

## Hallazgos sobre los nombres de los puntos en el BEC

- El BEC cambió los nombres en 2025: `CUSIANA` → `PLANTA CUSIANA`;
  `FLOREÑA` → `PLANTA FLOREÑA`; `Unidad Flotante de Almacenamiento y
  Regasificación (FSRU)` (nov-2024 a ago-2025) → `SPEC` (desde ago-2025).
  Las palabras clave unen ambos nombres para tener la historia completa.
- Palabras clave actuales: Cusiana `["cusiana"]`, Floreña `["florena"]`,
  Cartagena (GNL importado) `["spec", "fsru"]`.
- NO se usa "cartagena": el punto `CARTAGENA` del BEC existe desde 2015, con
  modalidades y precios variados (no es solo gas importado). También existe
  `CARTAGENA CONEXIÓN` (1 fila, 2019). Pendiente: preguntar al usuario si
  quiere seguir `CARTAGENA` como punto aparte.
- `SPEC_CGI` no aparece en los contratos (solo en información operativa).
- El gas importado (SPEC) se negocia más o menos cada 3 meses (ago-2025,
  nov-2025, feb-2026, may-2026, ago-2026), siempre "Firme al 95%". Por eso,
  si el mes anterior no tuvo negocios, el reporte compara con la última
  negociación. Floreña tiene volúmenes muy pequeños desde nov-2025.
- Otros puntos cercanos que el usuario podría querer después: `CUPIAGUA`,
  `PLANTA CUPIAGUA`, `Cupiagua Sur`, `PK8 CUPIAGUA`, `APIAY`.
- Otra fuente posible (información operativa): "Energía Inyectada" diaria por
  punto (Nacional vs Importado), en MBTUD. No trae precios ni modalidades.

## Pendientes (en orden sugerido)

1. ~~Prueba real del correo~~: hecha, funcionó.
2. ~~Datos por punto~~: hecho. Se usa la Tabla de resultados de la pestaña
   "Puntos" (Información Transaccional → Mercado Primario → Información de
   Suministro → pestaña "Puntos"), exportada SIN filtrar (1 archivo, ~100
   puntos, desde 2015); el programa filtra solo. Guardada como
   `datos/puntos.xlsx`.
3. **Mercado secundario**: agregar al reporte (sección aparte en el BEC).
4. **Robot de descarga (Etapa 4)**: construido. El workflow ahora: portero
   (último día hábil, o siempre si es manual) → instala Chromium → robot
   (`continue-on-error`) → si salió bien, commit de `datos/puntos.xlsx`
   (`permissions: contents: write`, `git pull --rebase` antes del push) →
   reporte con `DESCARGA_FALLIDA=1` si el robot falló (aviso en el reporte y
   asunto "[DATOS SIN ACTUALIZAR]") → sube fotos (`fotos-del-robot`) y
   reporte como artifacts. Botón manual con opción `solo_descargar`.
   FALTA: primera prueba contra el BEC real; si falla, revisar las fotos
   del artifact y ajustar selectores. Nota: la página "Cubos" del BEC no
   permite acceso automático (robots); la de Información Suministro sí.
5. **Histórico**: guardar una copia de los datos de cada mes para detectar
   registros tardíos y revisiones de meses anteriores.
