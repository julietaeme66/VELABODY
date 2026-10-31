# Compositor VELABODY (Remotion)

Arma y exporta los reels **sin Premiere**, a partir de lo mismo que usaba el flujo anterior: el plan (`plan.json`), las transcripciones y `velabody.py`. El estilo sale de la wiki y de `_HERRAMIENTAS/config_velabody.json` (sección `compositor`, medida sobre el Video 1 FINAL).

> **Estado:** es el **flujo oficial** desde el 30/10, después del piloto del ADS14 (ver `_WIKI/03_flujo_de_trabajo.md`). Premiere queda como alternativa. El código está en la rama `piloto-remotion`, con commits locales y sin push.

## El flujo, con sus comandos

Se corren desde `_COMPOSITOR` y requieren Node 22+, Python 3.12+ y ffmpeg. Instalación, una sola vez:

```bash
npm install
python -m venv .venv
.venv/Scripts/python -m pip install -r herramientas/requirements.txt
```

| Paso | Comando | Qué deja |
|---|---|---|
| 2. Ingesta del brief | `npm run brief -- "<brief.pdf>" [--videos 6,8]` | `Video N — …/` con las tomas, `guion.md`, `_MATERIAL_BRUTO/brief.json` y `brief_lineamientos.md` |
| 2. Transcripción | `python ../_HERRAMIENTAS/transcribir.py <carpeta> --salida "<video>/_EDICION/transcripciones"` | Tiempos por palabra |
| 3. Plan | Claude escribe `Video N — …/_EDICION/plan.json` (ejemplo: el del Video 8) | — |
| 4. Todo en baja | `npm run baja -- [--videos 6,8] [--piezas H1]` | `_COMPOSITOR_SALIDAS/<código>_HN_baja_vNNN_norm.mp4` y `resumen_baja.md` |
| 6. Correcciones | `npm run baja -- --videos 8 --piezas H2` | Solo lo que cambia |
| 7. Entrega en alta | `npm run alta -- [--videos 6,8]` | `_ENTREGAS/<código>/<código>_HookN.mp4` y `_portada.png`, más `resumen_alta.md` |
| 7. Limpieza | `npm run limpiar -- --simular`, y después `npm run limpiar` | Deja la última versión en alta de cada pieza; el resto va a la Papelera |

Otros:

| Para qué | Comando |
|---|---|
| Volver a armar `_ENTREGAS` con lo último en alta, sin renderizar | `npm run entregar -- [--videos 8]` |
| Una pieza suelta o en calidad media (810x1440) | `npm run pieza -- "<plan.json>" --piezas H1 --calidad media` |
| Preview interactivo (Remotion Studio) | `npm run studio` |
| Verificar un MP4 exportado | `npm run verificar -- <video.mp4> <carpeta_publica> <informe.json> [timeline_H1.json]` |
| Pruebas (unittest de `herramientas/` + tipos) | `npm run pruebas` |

**Qué hace cada pieza** (`herramientas/piloto.py › producir()`, lo llama `lote.py`):

1. `velabody.py` arma `armado.json` o, en un anuncio, `armado_HookN.json`. Ahí se aplican las reglas: sin jump cuts, B-roll largo partido, B-roll sin sacudidas (`broll_visual.py`), números en cifras, la pastilla una sola vez.
2. `preparar_medios.py` arma los proxies, con el color horneado y la voz aparte.
3. `adaptar_armado.py` → `timeline_HN.json`: px y cuadros, gráficos que se cortan con la toma, títulos lejos de la cabeza, desenfoque detrás y pastilla detrás de la cabeza (`mascara_persona.py`).
4. Render de Remotion, en baja (540x960), media (810x1440) o alta (1080x1920).
5. Normalización a −14 LUFS, con 0,5 dB de margen sobre el true peak de −1 dBTP, porque el AAC lo sube unas décimas.
6. Informe:
   - las mediciones del archivo;
   - **lo que pide el brief**: duración de 45–60 s, % a cámara y cuándo aparece el equipo (primer B-roll o pastilla);
   - hoja de contactos, `verificar_entrega.py` (zona segura con el PNG de la clienta, clicks, color) y, en alta, la portada sin texto (prop `sinTextos`).

**Nunca se pisa un exportado:** cada corrida usa el número de versión siguiente. **Hooks:** cada hook sale completo (hook + cuerpo) del mismo plan; si el plan trae `solo_hook_desde` (flujo de Premiere), `piloto.py` frena y avisa.

## Dónde está cada cosa

| Qué | Dónde | ¿En Git? |
|---|---|---|
| Código del compositor | `_COMPOSITOR/src` (Remotion) y `_COMPOSITOR/herramientas` (Python) | Sí |
| Plan de cada video | `<raiz>/Video N — …/_EDICION/plan.json` | Sí |
| Inventarios del piloto | `_COMPOSITOR/pilotos/ads14/` y `pilotos/ads14_h2/` | Sí |
| Rutas de esta compu | `_HERRAMIENTAS/config_local.json` (ver `config_local.ejemplo.json`) | No |
| Tomas | `<raiz>/Video N — …/` (las del ADS14, en `<raiz>/_MEDIOS_PILOTO/ADS14/`) | No |
| Fuentes, música, click, SFX, LUT, zona segura y aprobado | `<raiz>/_RECURSOS/` | No |
| Caché (proxies, carpeta pública, cuadros clave y movimiento del B-roll) | `<raiz>/_COMPOSITOR_CACHE/` y `<video>/_EDICION/_claves/` | No |
| Renders, informes y resúmenes | `<raiz>/_COMPOSITOR_SALIDAS/` | No |
| Entregas | `<raiz>/_ENTREGAS/<código>/` | No |

`<raiz>` sale de `VELABODY_RAIZ` o de `config_local.json` (`"raiz"`). En esta compu es `D:\VELABODY`. Sin ninguno de los dos, las herramientas apuntan a `E:\VELABODY`, como antes.

## Cómo se traduce lo de Premiere

| En Premiere | En el compositor |
|---|---|
| `velabody.py` → `armado.json` | **Igual, sin cambios de lógica**: cortes con bordes por forma de onda, cola final, subtítulos de 18 caracteres, maquetación justificada, zooms, ganancias. |
| Panel CEP / `velabody.jsx` | `adaptar_armado.py` traduce el armado a cuadros y px (`timeline.json`) y valida lo que no sabe hacer. |
| Escala/Posición de Movimiento | Caja en px: ancho = ancho rotado × escala/100, centrada en `pos`. El B-roll replica `encuadrar()` del JSX. Los keyframes son lineales. |
| Capa de ajuste Lumetri (LUT Alexa v3 → Rec709, exposición 0,4, contraste 65) | Un LUT 3D combinado y horneado en los proxies (`preparar_medios.py`), calibrado contra el aprobado (`calibrar_color.py`). |
| MOGRT *Ease Position & Mask Y - Bottom* | `Titulo` (SVG): sube desde una máscara con borde en la línea de base; ease-out *quint*, 30 cuadros. |
| MOGRT *1-Line Fill Text Box - Up* | `Pastilla` (SVG): la caja crece desde abajo y el texto sube con el borde superior; ease-out cúbica, 19 cuadros. |
| Estilos de pista `VELABODY SUBS C FONDO` / `CAMARA` | `Subtitulos` quemados: caja `#6F04BA` con Montserrat Medium 58, o Gotham Book 49 con halo violeta. |
| Pan Left (Mister Horse) | `ConPanLeft`, con **los keyframes de las dos capas de ajuste de Mister Horse del proyecto validado** (`VELABODY_EDICION.prproj`, leídos con `leer_prproj.py`): Transformar mueve la imagen de −4 a +11 cuadros del corte (la que sale acelera hacia la izquierda, la que entra aparece 471 px a la derecha y frena), Espejo rellena el lado vacío y Desenfoque direccional a 90° llega a 96 px en el corte. Del cuadro +1 al +9, la tabla se corrigió con lo medido en el export aprobado, porque Premiere frena la imagen más tarde que la interpolación lineal de los keyframes. Los valores están en `config_velabody.json › compositor.pan_left`. Lleva el SFX `Transition Complex 14.wav` desde 0,1 s antes del corte. Se mide con `medir_transicion.py`. No toca los subtítulos. |
| Objeto máscara (sándwich) | `mascara_persona.py --detras`: mate de RobustVideoMatting + halo y calado, como video con alfa encima de la pastilla. El adaptador ubica cada pastilla sobre la presentadora para que el pelo le tape ~25 % del alto (sale "por detrás de la cabeza", como en el Video 1). |
| Desenfoque gaussiano con máscara de calado (fondo cargado) | `Desenfoques`: `backdrop-filter` solo en la zona del título, con borde elíptico suave; entra y sale con el gráfico. |
| Mover el título a mano si toca la cabeza | El adaptador mide el borde del pelo (máscara de persona) bajo cada título y lo sube; si no entra bajo la zona segura, achica el bloque entero. |
| Normalización de sonoridad del export | `loudnorm` de ffmpeg en dos pasadas (−14 LUFS, −1 dBTP). |
| B-roll en una pista con `overwriteClip` | Si dos insertos se cruzan, el que se puso después pisa la cola del anterior (igual que en Premiere). |
| Volumen de la voz en el clip | Pista de voz aparte (WAV por toma y ganancia), así cada hook puede llevar su nivel. |
| Bandeja y secuencias `_H1` | No aplica: cada pieza es un MP4 versionado (`ADS14_H1_vNNN`…). |

## Calibración contra el Video 1 FINAL

Las medidas están en `config_velabody.json › compositor` y se pueden repetir:

- `medir_referencia.py`: cajas violeta cuadro a cuadro.
- Composición `Calibracion`: los gráficos del Video 1 hechos con nuestros componentes en los mismos cuadros.
- `comparar_calibracion.py`: compara las dos mediciones.

| Elemento | Resultado |
|---|---|
| Pastilla DERMA SCAN (escala 92) quieta | ±2 px; caja de 872,5×166 contra 873×166 |
| Pastilla, entrada | Error mediano de 5 px; por momentos va un cuadro adelantada |
| Título DIAGNÓSTICO | Mayúsculas a la misma altura (366–449); ancho 851 contra 851; corrimiento de 2 px; entrada en los mismos cuadros |
| Subtítulo con caja | ±2 px; caja de 449,6 contra 450 |
| Subtítulo a cámara | Altura y tamaño coinciden; el halo se ajustó a ojo, sin medición numérica |
| Color (B-roll C3831, dos cuadros) | ΔE2000 medio de 1,71 y 1,74 (p95 3,7–3,8); con el LUT solo daba 3,65–3,80 |
| Cadena Remotion (render contra proxy) | ΔE2000 1,69, con un corrimiento medio ≤ 1/255: casi todo es compresión |

## Historia del ADS14 (el piloto, 30/10)

El ADS14 se armó completo (H1, H2 y H3, con el mismo cuerpo de 6 bloques) y se ajustó en varias revisiones. Cada criterio quedó en la wiki (`07_decisiones.md`) y lo aplica el builder:

1. **Primera versión:**
   - títulos de dos palabras en dos líneas justificadas, lejos de la cabeza y con desenfoque detrás;
   - la pastilla sale por detrás de la cabeza;
   - a cámara, 3 s o más, o nada;
   - subtítulos de 2 o 3 palabras.
2. **Sin jump cuts:** se reemplazaron los punch-ins y el B-roll partido por un zoom lento continuo. Desde esa revisión:
   - el gráfico se corta con la toma;
   - el Pan Left usa los keyframes del `.prproj` validado, con su SFX;
   - la cantidad de gráficos la marca el plan.
3. **B-roll largo** partido en 3–4 s: primero el plano cerrado y después otra parte del clip. La pastilla entra una sola vez, y el Pan Left se corrigió con lo medido en el export aprobado (≤ 12 px de diferencia).
4. **B-roll sin movimientos bruscos:** se mide el pico de movimiento que dura al menos 0,2 s, hasta el último cuadro del plano. Si el tramo que eligió el plan lo tiene, se usa el tramo estable más cercano. El reporte (C3835) se mueve en todo el clip, así que va lo menos brusco.
5. **Números en cifras** en los gráficos ("5 COSAS") y **sin cola final** en este video (`"cola_final": 0`).

**Entrega** (`_ENTREGAS/ADS14/`):

| Pieza | Render | Duración | Sonoridad | A cámara | Equipo |
|---|---|---|---|---|---|
| `ADS14_Hook1.mp4` | `ADS14_H1_v005_norm.mp4` | 57,1 s | −14,0 LUFS · −1,0 dBTP | 19 % | 2,4 s |
| `ADS14_Hook2.mp4` | `ADS14_H2_v006_norm.mp4` (el mismo render que v004, normalizado con margen de pico) | 55,4 s | −14,0 LUFS · −1,5 dBTP | 21 % | 0,5 s |
| `ADS14_Hook3.mp4` | `ADS14_H3_v004_norm.mp4` | 56,3 s | −14,0 LUFS · −1,0 dBTP | 22 % | 3,7 s |

Ningún gráfico queda fuera de la zona segura, y la cadena de color da ΔE2000 de 1,7 contra el proxy. Comparado con el Video 1 FINAL, el plano mediano de B-roll es más largo (2–4 s contra 0,95 s), porque no hay material para cortar más seguido sin repetir encuadre. El tiempo a cámara (~20 %) es menor que la mitad que sugiere el brief, porque se aplica la regla de "3 s o más, o nada".

Del piloto corto (Hook 2 + bloque 1, `pilotos/ads14_h2`) quedó medido: la voz centrada, la música ≥ 20 dB por debajo de la voz y los clicks 2–3 cuadros antes de que se vea el gráfico, como en el aprobado.

## Hallazgos que también afectan al flujo de Premiere

1. **`Mouse Click.mp3` arranca con 0,26 s de silencio.** El builder pone el click al inicio del gráfico, así que suena unos 8 cuadros tarde; en el aprobado, Juli lo compensó a mano. El compositor ya lo corrige (`click_silencio_inicial_s`).
2. **El violeta del aprobado sale exportado como ~`#6601B2`, no `#6F04BA`**, posiblemente por la gestión de color de Premiere. El compositor entrega `#6F04BA`.
3. `velabody.py` fallaba al imprimir las notas en consolas cp1252 ("→", "⚠"). Ya está corregido.
4. **Dos B-roll del bloque 7 se cruzan 8 cuadros**, porque `velabody.py` alarga cada inserto y adelanta el siguiente. En Premiere lo tapa `overwriteClip`; el compositor hace lo mismo y lo avisa.
5. El plan del ADS14 tomaba **C3835 de la carpeta del Video 7** (ruta absoluta en `E:`). Acá se bajó a la carpeta del ADS14.

## Diferencias pendientes frente al aprobado

- **Montserrat:** se usó la versión oficial (OFL). En la pastilla, las letras D, M, R y N del aprobado son 6–7 px más angostas, y el acento de la Ó está corrido. Se compensa con tracking para que la caja mida lo mismo. Hace falta la `.otf` de la clienta.
- **Pan Left:** los keyframes del `.prproj`, corregidos del cuadro +1 al +9 con lo medido en el export aprobado; quedan a ≤ 12 px por cuadro (`medir_transicion.py`).
- **Halo del subtítulo de cámara:** ajustado visualmente.
- **Sándwich:** el halo se comparó a ojo con el aprobado; no hay comparación numérica.
- **Descendentes en los títulos:** la máscara del MOGRT corta en la línea de base. En el compositor el borde baja con la entrada para no cortar la cola de la Q ("QUE", "QR"). En el aprobado no había letras con descendente para comparar.
- **Desenfoque de fondo:** se ajustó a ojo (22 px, elipse con borde suave); no hay un desenfoque del aprobado con el que comparar.
- **Versión 1080x1080:** no está hecha. Según la wiki, se arma cuando la clienta cierra el video.

## Licencias

- **Remotion:** gratis para personas y empresas con fines de lucro de hasta 3 empleados; por encima de eso hace falta *Company License*.
- **RobustVideoMatting:** GPL-3.0. Se usa como herramienta local y no se redistribuye.
- **Montserrat:** OFL.
- **Gotham:** licencia de la clienta; nunca va a Git (el repo es público).

## Notas de Windows

- **Git:** D: no registra dueño, así que hay que usar `git -c safe.directory=D:/VELABODY ...`.
- **Python:** las herramientas corren con `-I`, que ignora `PYTHONIOENCODING`; cada script fuerza UTF-8.
