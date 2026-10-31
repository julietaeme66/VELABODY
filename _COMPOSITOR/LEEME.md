# Compositor VELABODY (Remotion) — piloto

Arma un reel **sin Premiere**, a partir de lo mismo que ya usa el flujo actual: el plan (`plan*.json`), las transcripciones y `velabody.py`. El estilo sale de la wiki y de `_HERRAMIENTAS/config_velabody.json` (sección `compositor`, medida sobre el Video 1 FINAL).

> **Estado:** piloto, en la rama `piloto-remotion`. **El flujo oficial sigue siendo Premiere.** Nada de esto cambia una regla de la wiki.

## Comandos

Se corren desde `_COMPOSITOR` y requieren Node 22+, Python 3.12+ y ffmpeg.

```bash
npm install
python -m venv .venv
.venv/Scripts/python -m pip install -r herramientas/requirements.txt
```

| Para qué | Comando |
|---|---|
| Armar, renderizar, normalizar y verificar el ADS14 completo (H1, H2 y H3) | `npm run ads14` |
| Solo algunos hooks | `npm run ads14 -- --piezas H2` |
| Una prueba rápida para revisar (810x1440, cuadros JPEG) | `npm run ads14 -- --piezas H1 --calidad media` |
| Para validar el armado (540x960, la más rápida) | `npm run ads14 -- --piezas H1 --calidad baja` |
| El piloto corto (Hook 2 + bloque 1) | `npm run piloto` |
| Abrir el preview interactivo (Remotion Studio) | `npm run studio` |
| Renderizar a mano lo que haya en `timeline.json` | `npx remotion render src/index.ts VelabodyPieza <salida.mp4>` |
| Verificar un MP4 exportado | `npm run verificar -- <video.mp4> <carpeta_publica> <informe.json> [timeline_H1.json]` |
| Pruebas del adaptador y chequeo de tipos | `npm run pruebas` |

`herramientas/piloto.py` hace todo el recorrido, en este orden:

1. `velabody.py`: arma `armado.json` o, en un anuncio, `armado_HookN.json`.
2. `preparar_medios.py`: un solo juego de proxies para todas las piezas.
3. Por cada pieza, `adaptar_armado.py` → `timeline_HN.json`.
4. Render de Remotion.
5. Normalización a −14 LUFS y −1 dBTP.
6. Informe, hoja de contactos y `verificar_entrega.py`.

Cada corrida guarda `_COMPOSITOR_SALIDAS/<nombre>_HN_vNNN.mp4` (render) y `_vNNN_norm.mp4` (entrega), con el número siguiente; en calidad media, `<nombre>_HN_media_vNNN`. **Nunca pisa un exportado.** Las pruebas se renderizan de a una pieza y en calidad media.

**Hooks:** en Premiere, `solo_hook_desde` armaba el cuerpo una vez y se pegaba a mano en los demás hooks. Acá cada hook sale completo (hook + cuerpo) del mismo plan, así que esa clave no va. Si el plan la trae, `piloto.py` frena y avisa.

## Dónde está cada cosa

| Qué | Dónde | ¿En Git? |
|---|---|---|
| Código del compositor | `_COMPOSITOR/src` (Remotion) y `_COMPOSITOR/herramientas` (Python) | Sí |
| Planes e inventarios | `_COMPOSITOR/pilotos/ads14/` (ADS14 completo) y `pilotos/ads14_h2/` (piloto corto) | Sí |
| Rutas de esta compu | `_HERRAMIENTAS/config_local.json` (ver `config_local.ejemplo.json`) | No |
| Tomas del ADS14 (las 15) | `<raiz>/_MEDIOS_PILOTO/ADS14/` | No |
| Fuentes, música, click, LUT y aprobado | `<raiz>/_RECURSOS/` | No |
| Caché (proxies, carpeta pública, mediciones) | `<raiz>/_COMPOSITOR_CACHE/` | No |
| MP4 exportados e informes | `<raiz>/_COMPOSITOR_SALIDAS/` | No |

`<raiz>` sale de `VELABODY_RAIZ` o de `config_local.json` (`"raiz"`). Sin ninguno de los dos, las herramientas siguen apuntando a `E:\VELABODY`, como antes.

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

## Verificación del piloto (`ADS14_H2_piloto_v003_norm.mp4`)

| Qué | Resultado |
|---|---|
| Formato | H.264 yuv420p BT.709 en rango TV, 1080x1920, 30 fps, 358 cuadros (= timeline), AAC 48 kHz |
| Sonoridad | −14,0 LUFS; true peak −1,0 dBTP |
| Voz centrada | L −17,56 / R −17,56 dB |
| Música | ≥ 20 dB por debajo de la voz (−34,7 dB contra −14,5 dB, antes de la primera palabra) |
| Corte hook → bloque | −34 / −37 dB alrededor del corte contra −14,5 dB de voz: no corta palabras |
| Clicks | Suenan en el cuadro de inicio de cada gráfico, 2–3 cuadros antes de que se vea (como en el aprobado) |
| Zona segura | Ningún gráfico afuera (zona aproximada: falta el PNG oficial) |

## ADS14 completo: H1, H2 y H3

Las tres piezas salen del mismo plan (`pilotos/ads14/plan.json`, copiado de `plan_v2.json`; las diferencias están en su `_nota`) y comparten el mismo cuerpo de 6 bloques. Esta versión aplica los criterios de la revisión del 30/10, que quedaron en la wiki (`07_decisiones.md`):

- **Títulos:** siempre dos palabras en dos líneas justificadas, nunca tocando la cabeza, con desenfoque detrás. **Si se corta la toma, el gráfico se corta en el mismo cuadro**, sin fundido (`cortar_graficos_con_la_toma`).
- **Cantidad de gráficos:** la del plan, aunque la wiki recomiende 2 a 4.
- **Pastilla:** sale por detrás de la cabeza y **entra una sola vez**: si el plan la repite enseguida con el mismo texto, sigue la primera.
- **B-roll sin movimientos bruscos (regla general):** de cada B-roll va la parte que eligió el plan por el guion, salvo que tenga un movimiento o un cambio de cámara brusco; en ese caso se usa el tramo estable más cercano del mismo clip (`broll_sin_sacudidas` en `velabody.py`, umbral en `config_velabody.json › broll_estable`). Vale también para el armado de Premiere.
- **B-roll largo:** se corta cada 3–4 s (`partir_broll_largo` en `velabody.py`, con `broll_visual.py`). El plano siguiente sale del mismo archivo: primero el mismo momento en un plano ×1,5 más cerrado, centrado en lo que tiene detalle, y después otra parte del clip que se vea distinta. Los cortes caen al empezar una palabra y nunca a mitad de un gráfico. Usa `zoom`/`foco` del B-roll, igual que el panel de Premiere.
- **Ritmo:** sin silencios; a cámara 3 s o más o nada; cola final de 1 s.
- **Nunca un jump cut de la misma toma.** Si dos tramos seguidos de la misma toma quedarían a la vista, `velabody.py` vuelve a armar la pieza conservando la pausa entre ellos (`armar_sin_saltos`), y dos insertos seguidos del mismo clip se unen en un solo plano. La imagen puede quedarse más de 3 s; se mueve con un zoom lento continuo (entra o sale), nunca con un salto de escala.
- **Pan Left:** los keyframes del proyecto validado, con su SFX.
- **Subtítulos:** de 2 o 3 palabras.

| Pieza | Duración | Sonoridad | Tramos a cámara | Avisos de palabras cortadas |
|---|---|---|---|---|
| `ADS14_H1_v004_norm.mp4` (Cinco cosas…) | 58,1 s · 1742 cuadros | −14,0 LUFS · −1,0 dBTP · L/R iguales | hook, 3,7 s en el bloque 4, cierre | ninguno |
| `ADS14_H2_v003_norm.mp4` (Esto es lo que hace diferente…) | 56,3 s · 1689 cuadros | −14,0 LUFS · −1,0 dBTP · L/R iguales | hook, 3,7 s en el bloque 4, cierre | ninguno |
| `ADS14_H3_v003_norm.mp4` (¿Sabés todo lo que un analizador…?) | 57,2 s · 1717 cuadros | −14,0 LUFS · −1,0 dBTP · L/R iguales | hook, 3,7 s en el bloque 4, cierre | ninguno |

Las versiones anteriores quedan en `_COMPOSITOR_SALIDAS` (no se pisan). El contenido de cada toma se comprobó con su transcripción contra el guion del plan (coincidencia 0,82–1,00). En B07, el "Dije cualquier cosa" de la presentadora queda afuera del corte.

**Comparación con el aprobado** (`analizar_edicion.py`, en `_COMPOSITOR_CACHE/analisis/`):

| | Video 1 FINAL | ADS14 H1 v004 |
|---|---|---|
| Plano mediano | 1,33 s | 2,30 s |
| Plano mediano de B-roll | 0,95 s | 2,17 s |
| Tiempo a cámara | 54 % | 21 % (regla de 3 s) |
| Silencio en los cortes | 0,0 s | 0,0 s |

**Para revisar (decisiones creativas):**

- Los insertos siguen siendo más largos que en el aprobado (mediana de 0,95 s allá, 2–4 s acá): no hay material para cortar más seguido sin repetir el mismo encuadre.
- En H3, ANALIZADOR / FACIAL sube 48 px para no tocar la cabeza.
- La pastilla reutilizada del cierre queda más abajo que la guía (545/350), porque se ubica detrás de la cabeza.

### Segunda revisión: `ADS14_H1_media_v001_norm.mp4`

Prueba de una sola pieza en calidad media (810x1440), como se pidió. 58,1 s, 1742 cuadros, −14,0 LUFS, −1,0 dBTP, L/R iguales.

| Qué | Resultado |
|---|---|
| Jump cuts de la misma toma | Ninguno a la vista. A cámara quedan el hook (2,4 s), el bloque 4 (3,7 s) y el cierre (5,9 s), cada uno con un zoom lento continuo. |
| B-roll | Ningún inserto pegado a otro del mismo clip. |
| Gráficos y cortes | Los 6 títulos que llegaban a un corte terminan en ese cuadro (CINCO COSAS 71, RECOMENDACIÓN 253, PROTECTOR 1038, REPORTE 1471…). COMPARA / EL PROGRESO y CORTE / 3D se apagan dentro de su propio plano. |
| Pan Left (`medir_transicion.py`, toma que entra, en px a 1080) | Corte 1292: 500, 316, 164, 84, 44, 28, 16. Aprobado (corte 45): 496, 316, 200, 116, 72, 44, 24. La que sale: −8, −36, −88 contra −12, −40, −92. |
| SFX de la transición | Sí, en los 3 cortes. |
| Zona segura (PNG de la clienta) | Ningún gráfico afuera. |
| Color de la cadena | ΔE2000 1,56. |

### Tercera revisión: `ADS14_H1_media_v003_norm.mp4`

El H1 de la segunda revisión quedó aprobado como camino. Sobre esa versión:

| Qué | Resultado |
|---|---|
| B-roll largo | C3831 (6,5 s) pasa a un primer plano del rostro en la tablet; C3829 (9,5 s), al 3D más cerca (debajo de CORTE / 3D) y después a otra parte del clip; C3835 (6 s), a un plano más cerrado del reporte. Ningún plano de B-roll pasa de 4 s. |
| Pastilla DERMA SCAN | Una sola entrada, de 1573 a 1712, con un solo click. |
| Pan Left (corte 1292 contra el aprobado) | La toma que sale: −12, −40, −92 contra −12, −40, −92. La que entra: 500, 328, 192, 108, 64, 40, 24, 16 contra 496, 316, 200, 116, 72, 44, 24, 16 (≤ 12 px). |
| Sonoridad, zona segura y color | −14,0 LUFS, −1,0 dBTP; ningún gráfico afuera; ΔE2000 1,56. |

### H1 v004: `ADS14_H1_media_v004_norm.mp4`

Sobre la v003, solo cambia el B-roll con movimientos bruscos. La medida es cuánto se corre la imagen cada 0,1 s, en px a 1080 y multiplicado por el zoom: ~10 es un paneo lento, 50 un barrido y 200 un cambio de plano.

| Plano | v003 | v004 |
|---|---|---|
| C3829, plano general (27,8 s) | 143: la cámara pasa a otra escena | 35: otra parte quieta del clip |
| C3835, reporte (43 s y 46 s) | 132 y 300 | 54 y 81: el clip es un paneo en mano en todo su largo y solo tiene ~1,5 s quietos seguidos, así que va lo menos brusco |
| C3829, 3D (21–28 s) | 8 y 47 a ×1,5 | 8 y 20: arranca 0,7 s antes, donde la tablet está quieta |
| C3829 (hook) y C3838 | 50 y 51 | 30 y 31–45 |

El resto queda igual que en la v003: −14,0 LUFS, −1,0 dBTP, ningún gráfico fuera de la zona segura y ΔE2000 1,55.

### Versión para validar del H1: `ADS14_H1_baja_v001_norm.mp4` (540x960)

En la v004, el plano de C3829 que termina a los 30,9 s tenía un tirón de cámara en sus últimos 0,2 s. La medida anterior (percentil 95 de todo el plano) no lo detectaba. Ahora se mide **el pico que dura al menos 0,2 s, hasta el último cuadro del plano**, con umbral 30.

- Todos los planos del H1 quedan en 25 o menos, corridos como mucho 1,5 s respecto de lo que eligió el plan.
- La excepción es el reporte (C3835: 36, y 73 en el plano cerrado). Es un paneo en mano y no tiene 3 s quietos seguidos en ninguna parte.
- El plano de los 30,9 s ahora termina quieto.
- −14,0 LUFS, −1,0 dBTP; ningún gráfico fuera de la zona segura.

### Entrega: H1 en calidad final, H2 y H3 para validar

Con el H1 validado en baja, se sumaron dos cambios:
- **Los números van en cifras en los gráficos** ("5 COSAS / QUE NO SABÍAS"), y con letras en los subtítulos.
- **El ADS14 cierra sin cola** (`"cola_final": 0` en el plan): termina con la última palabra, a los ~57 s.

| Pieza | Archivo | Duración | Sonoridad |
|---|---|---|---|
| H1, calidad final (1080x1920) | `ADS14_H1_v005_norm.mp4` | 57,1 s | −14,0 LUFS · −1,0 dBTP |
| H2, baja (540x960) | `ADS14_H2_baja_v001_norm.mp4` | 55,4 s | −14,0 LUFS · −0,9 dBTP |
| H3, baja (540x960) | `ADS14_H3_baja_v001_norm.mp4` | 56,3 s | −14,0 LUFS · −1,0 dBTP |

En las tres, ningún gráfico queda fuera de la zona segura. El true peak de −0,9 del H2 en baja queda 0,1 dB por encima del objetivo; se vuelve a medir en el render final del H2.

## Hallazgos que también afectan al flujo de Premiere

1. **`Mouse Click.mp3` arranca con 0,26 s de silencio.** El builder pone el click al inicio del gráfico, así que suena unos 8 cuadros tarde; en el aprobado, Juli lo compensó a mano. El compositor ya lo corrige (`click_silencio_inicial_s`).
2. **El violeta del aprobado sale exportado como ~`#6601B2`, no `#6F04BA`**, posiblemente por la gestión de color de Premiere. El compositor entrega `#6F04BA`.
3. `velabody.py` fallaba al imprimir las notas en consolas cp1252 ("→", "⚠"). Ya está corregido.
4. **Dos B-roll del bloque 7 se cruzan 8 cuadros**, porque `velabody.py` alarga cada inserto y adelanta el siguiente. En Premiere lo tapa `overwriteClip`; el compositor hace lo mismo y lo avisa.
5. El plan del ADS14 tomaba **C3835 de la carpeta del Video 7** (ruta absoluta en `E:`). Acá se bajó a la carpeta del ADS14.

## Diferencias pendientes frente al aprobado

- **Montserrat:** se usó la versión oficial (OFL). En la pastilla, las letras D, M, R y N del aprobado son 6–7 px más angostas, y el acento de la Ó está corrido. Se compensa con tracking para que la caja mida lo mismo. Hace falta la `.otf` de la clienta.
- **Pan Left:** los valores son los keyframes del `.prproj`. El efecto de Mister Horse interpola entre ellos con su propia curva, y el compositor, linealmente cuadro a cuadro. La diferencia queda medida con `medir_transicion.py` (ver la verificación de abajo).
- **Halo del subtítulo de cámara:** ajustado visualmente.
- **Sándwich:** el halo se comparó a ojo con el aprobado; no hay comparación numérica.
- **Descendentes en los títulos:** la máscara del MOGRT corta en la línea de base. En el compositor el borde baja con la entrada para no cortar la cola de la Q ("QUE", "QR"). En el aprobado no había letras con descendente para comparar.
- **Desenfoque de fondo:** se ajustó a ojo (22 px, elipse con borde suave); no hay un desenfoque del aprobado con el que comparar.
- **Versión 1080x1080:** no está hecha. Según la wiki, se arma después de validar.

## Licencias

- **Remotion:** gratis para personas y empresas con fines de lucro de hasta 3 empleados; por encima de eso hace falta *Company License*.
- **RobustVideoMatting:** GPL-3.0. Se usa como herramienta local y no se redistribuye.
- **Montserrat:** OFL.
- **Gotham:** licencia de la clienta; nunca va a Git (el repo es público).

## Notas de Windows

- **Git:** D: no registra dueño, así que hay que usar `git -c safe.directory=D:/VELABODY ...`.
- **Python:** las herramientas corren con `-I`, que ignora `PYTHONIOENCODING`; cada script fuerza UTF-8.
