# Guía: prueba real del correo desde GitHub

Piensa en GitHub como una **casa con una alarma programada**. Tu código son
los muebles, la carpeta `.github/workflows` es el reloj despertador, y los
*Secrets* son una caja fuerte donde guardas la llave del correo. Hoy vamos a:
1) meter los muebles en la casa, 2) revisar la caja fuerte y 3) oprimir el
botón del despertador a mano para ver si suena.

---

## Paso 1. Crear el repositorio (la "casa")

1. Entra a https://github.com y arriba a la derecha toca **+** → **New repository**.
2. Nombre: `reporte-gas`.
3. Marca **Private** (privado), para que nadie más vea los datos.
4. **No** marques "Add a README" (ya tenemos uno).
5. Toca **Create repository**.

> Si ya tienes un repositorio para esto, sáltate este paso y úsalo.

## Paso 2. Subir los archivos (meter los muebles)

⚠️ **La trampa más común:** la carpeta `.github` empieza con un punto, y
Windows la **esconde**. Si no se sube, el botón "Run workflow" nunca aparece.

**Forma fácil (arrastrando):**

1. Descomprime el zip en tu computador.
2. En el Explorador de Windows: pestaña **Vista** → marca **Elementos ocultos**.
   Ahora debes ver la carpeta `.github`.
3. En la página del repositorio toca **uploading an existing file**.
4. Arrastra **todo el contenido** de la carpeta `reporte-gas` (no la carpeta
   misma, sino lo que hay adentro), incluida `.github`.
5. Abajo toca **Commit changes**.

**Cómo comprobar que quedó bien:** en la página del repositorio debes ver la
carpeta `.github`. Si no aparece, haz esto: toca **Add file → Create new
file**, en el nombre escribe exactamente
`.github/workflows/reporte_mensual.yml` (al escribir `/` GitHub crea las
carpetas solo), pega adentro el contenido de ese archivo y toca
**Commit changes**.

## Paso 3. Revisar la caja fuerte (Secrets)

1. En el repositorio: **Settings** → menú izquierdo **Secrets and variables**
   → **Actions**.
2. Deben existir estos tres secretos (los secretos son **de cada
   repositorio**: si los guardaste en otro repositorio, hay que crearlos
   también aquí con **New repository secret**):

| Nombre | Qué va adentro | Ejemplo |
|---|---|---|
| `GMAIL_USUARIO` | El Gmail que envía, completo | `robot.tmm@gmail.com` |
| `GMAIL_CLAVE_APP` | La contraseña de aplicación de 16 letras, **sin espacios** | `abcdefghijklmnop` |
| `CORREO_DESTINO` | A quién le llega (varios, separados por coma) | `nicol@gmail.com` |

> GitHub nunca te deja **ver** un secreto guardado, solo reemplazarlo. Eso es
> normal: es una caja fuerte.
>
> Si tu llave ya existe con **otro nombre** (por ejemplo `GMAIL_PASSWORD`),
> no la crees de nuevo: abre `.github/workflows/reporte_mensual.yml` y cambia
> solo el lado derecho, así: `GMAIL_CLAVE_APP: ${{ secrets.GMAIL_PASSWORD }}`.

## Paso 4. Oprimir el botón (la prueba)

1. Pestaña **Actions** del repositorio. Si sale un aviso para habilitar los
   workflows, tócalo para aceptar.
2. A la izquierda toca **Reporte mensual de gas**.
3. A la derecha toca **Run workflow**. Aparece una cajita
   **"Mes a reportar"**: escribe `2026-09` (septiembre está completo;
   octubre todavía va por la mitad).
4. Toca el botón verde **Run workflow**. En unos segundos aparece una fila
   con un círculo amarillo girando. Espera 1 o 2 minutos.

## Paso 5. Ver el resultado

- ✅ **Círculo verde**: revisa tu correo (y la carpeta **Spam** la primera
  vez). Debe llegar *"Reporte mensual de gas natural: septiembre de 2026"*
  con las 3 gráficas y el reporte adjunto. Si llegó a Spam, márcalo como
  "No es spam" para que los próximos lleguen bien.
- Además, dentro de la ejecución, abajo en **Artifacts**, hay un archivo
  `reporte` con la copia del HTML.
- ❌ **Círculo rojo**: toca la ejecución → **generar** → abre el paso que
  tiene la ✗ y lee las últimas líneas. Usa esta tabla:

| Lo que dice | Qué significa | Cómo se arregla |
|---|---|---|
| `No encontré GMAIL_USUARIO, GMAIL_CLAVE_APP o CORREO_DESTINO` | Falta un secreto o tiene otro nombre | Paso 3 |
| `Gmail rechazó el usuario o la clave` | La clave no es la de aplicación, o tiene espacios | Crea una nueva en https://myaccount.google.com/apppasswords (requiere verificación en dos pasos) y reemplaza el secreto |
| `No hay datos de ... en el archivo` | El mes escrito no está en el Excel | Escribe otro mes, ej. `2026-09` |
| `No such file ... datos/tabla_resultados.xlsx` | No se subió la carpeta `datos` | Súbela (Paso 2) |
| No aparece el botón **Run workflow** | No se subió `.github` | Paso 2, "Cómo comprobar" |

## Paso 6. Después de la prueba

Cuéntame qué color salió (y, si fue rojo, copia las últimas líneas del
error). Con el verde, el despertador ya queda funcionando solo: el próximo
correo automático llegará el **viernes 30 de octubre de 2026** a las 5 p.m.
(último día hábil de octubre).
