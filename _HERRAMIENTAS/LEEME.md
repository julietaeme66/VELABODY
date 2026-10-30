# VELABODY: flujo de edición con Claude

Claude arma el editable y vos lo revisás. Esta carpeta tiene las herramientas.

| Archivo | Para qué sirve |
|---|---|
| `transcribir.py` | Transcribe los clips con tiempos por palabra (Whisper large-v3 con GPU). |
| `velabody.py` | Toma `plan.json` y produce `armado.json`, dos SRT, un XML de respaldo y las notas. |
| `preview.py` | Arma un preview liviano del corte (`preview_corte.mp4`) para revisarlo sin Premiere. |
| `config_velabody.json` | Reglas de estilo: dB, tamaños, rutas a MOGRT, click, light leaks, etc. |
| `premiere_panel/` | Panel **VELABODY Builder** para Premiere (CEP + ExtendScript). |
| `instalar_panel.bat` | Instala el panel. Se corre una sola vez. |
| `panel_remoto.py` | Permite que Claude pruebe el panel desde afuera (depuración en localhost:8088). |

## Preparación (una sola vez)

1. **Instalar el panel:** doble clic en `instalar_panel.bat` y reiniciar Premiere. El panel se abre desde *Ventana > Extensiones > VELABODY Builder*.
2. **Secuencia plantilla con Lumetri (recomendado):** creá una secuencia vacía 1080x1920 a 30 fps llamada **`_PLANTILLA_9x16`**. En su pista **V3**, poné una *Capa de ajuste* larga (por ejemplo 3 minutos) con el Lumetri de la guía: Input LUT Alexa v3 → Rec709, Exposición 0,4 y Contraste 65. El panel duplica esa secuencia y recorta la capa al largo del video. En Premiere los efectos viven en el clip de la línea de tiempo, no en el ítem del proyecto, así que esta es la forma de que el Lumetri venga incluido.
3. **Estilos de subtítulo:** guardá dos *Estilos de pista*: **`VELABODY SUBS C FONDO`** (ya existe) y **`VELABODY SUBS CAMARA`** (texto blanco con brillo violeta). Los dos van a la altura fija que pidió la clienta y siempre en una sola línea.
4. Si no existe la plantilla, el panel crea la secuencia solo, pero sin Lumetri.

## Por cada video

1. Me pasás el link de Drive con el material y el guion. Si el Doc no es público, compartilo con acceso de lectura o pegámelo.
2. Yo lo bajo, transcribo y escribo `_EDICION/plan.json`, que es el guion convertido en bloques con el B-roll, los títulos y los light leaks. Después corro `velabody.py` y `preview.py`.
3. Vos mirás `preview_corte.mp4` y `notas_revision.md`. Si el corte está OK:
4. Abrís tu proyecto en Premiere y, en el panel, hacés **Elegir armado.json** y después **Construir secuencia**.
5. Aplicás los dos estilos de pista a las dos pistas de subtítulos, que son dos clics.
6. Revisás y me pasás los cambios en texto ("el título 2 que entre antes", "otro B-roll en el seg 12"). Yo regenero y se arma una secuencia nueva.

## Qué arma el panel

| Pista | Contenido |
|---|---|
| V1 / A1 | A-roll cortado (pausas eliminadas), encuadrado 9:16 y con la voz normalizada a pico 0 dB. |
| V2 | B-roll encuadrado, sin audio. |
| V3 | Capa de ajuste con Lumetri (viene de la plantilla `_PLANTILLA_9x16`). |
| V4 / A3 | Light leak de la carpeta de transiciones, convertido a .mov con transparencia (se ve como Trama, en modo Normal), más el SFX "cinematic light". Solo 1 o 2 por video. |
| V5+ / A2 | Títulos (MOGRT Mister Horse *Position & Mask Ease In [Bottom]*; la pastilla violeta es *1-Line Fill Text Box*) y el click en cada título. |
| A4 | Música a −23 dB (la guía dice −20, pero la clienta pidió "apenas más baja"). |
| Arriba de todo | Guía de zona segura, desactivada. |
| Subtítulos | Dos pistas: `subs_camara` (ella a cámara) y `subs_broll` (sobre B-roll, con fondo). |

**Diagnóstico de clips seleccionados:** seleccionás clips en la línea de tiempo, tocás el botón y se guarda `diagnostico_premiere.txt` con todos sus parámetros. Me sirve para calibrar si algo no queda bien (por ejemplo, el tamaño de los títulos).

## Reglas de la clienta incorporadas

- Subtítulos siempre en **una línea**: hasta 3 palabras o 20 caracteres, a altura fija.
- Light leak con moderación: no en todas las transiciones.
- Títulos como "paquetito": la primera palabra define el ancho, todo va justificado y en 3 líneas como máximo. Fuente Montserrat en violeta #6F04BA, con la palabra secundaria en pastilla (ExtraBold itálica).
- En los videos de depilación se escribe **laser sin tilde**.
- Export: 1080x1920, H.264.
