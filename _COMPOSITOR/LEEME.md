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

Cada corrida guarda `_COMPOSITOR_SALIDAS/<nombre>_HN_vNNN.mp4` (render) y `_vNNN_norm.mp4` (entrega), con el número siguiente. **Nunca pisa un exportado.**

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
| Pan Left (Mister Horse) | `ConPanLeft`: 5 cuadros antes y 5 después del corte, deslizamiento con desenfoque horizontal y bordes en espejo. No toca los subtítulos. |
| Objeto máscara (sándwich) | `mascara_persona.py`: mate de RobustVideoMatting + halo y calado, como video con alfa encima de la pastilla. |
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

Las tres piezas salen del mismo plan (`pilotos/ads14/plan.json`, copiado de `plan_v2.json`; las diferencias están en su `_nota`) y comparten el mismo cuerpo de 6 bloques.

| Pieza | Duración | Sonoridad | Clicks (antes de verse) | Cortes entre tomas |
|---|---|---|---|---|
| `ADS14_H1_v002_norm.mp4` (Cinco cosas…) | 62,5 s · 1875 cuadros | −14,0 LUFS · −1,0 dBTP · L/R iguales | 2–5 cuadros | 7, todos ≥ 11 dB por debajo de la voz |
| `ADS14_H2_v001_norm.mp4` (Esto es lo que hace diferente…) | 61,1 s · 1832 cuadros | −14,0 LUFS · −1,0 dBTP · L/R iguales | 2–5 cuadros | 7, todos ≥ 11 dB por debajo de la voz |
| `ADS14_H3_v001_norm.mp4` (¿Sabés todo lo que un analizador…?) | 61,9 s · 1858 cuadros | −14,0 LUFS · −1,0 dBTP · L/R iguales | 2–5 cuadros | 7, todos ≥ 11 dB por debajo de la voz |

Las tres en H.264 BT.709, con la música ≥ 20 dB por debajo de la voz y nada fuera de la zona segura aproximada. El contenido de cada toma se comprobó con su transcripción contra el guion del plan (coincidencia 0,82–1,00). En B07, después de la frase, la presentadora dice "Dije cualquier cosa": el corte lo deja afuera, porque la voz termina en 12,65 s, el corte cae en 13,06 s y el comentario empieza en 13,84 s.

**Para revisar con Juli (decisiones creativas, no se tocaron):**

- El plan trae **7 u 8 gráficos por pieza**; la wiki dice **2 a 4** por video.
- **CORTE 3D** y **REPORTE POR QR** quedan encima de las letras del logo "velabody" de la pared, y **CINCO COSAS** también lo cruza. La wiki pide sombra leve o desenfoque cuando el fondo dificulta la lectura; hoy solo RECOMENDACIÓN la tiene (como en el piloto).
- **COMPARA / EL PROGRESO** (y = 345) cae sobre la pantalla oscura de la tablet: violeta sobre negro, que no se arregla con sombra. Habría que moverlo o cambiar el B-roll de ese tramo.

## Hallazgos que también afectan al flujo de Premiere

1. **`Mouse Click.mp3` arranca con 0,26 s de silencio.** El builder pone el click al inicio del gráfico, así que suena unos 8 cuadros tarde; en el aprobado, Juli lo compensó a mano. El compositor ya lo corrige (`click_silencio_inicial_s`).
2. **El violeta del aprobado sale exportado como ~`#6601B2`, no `#6F04BA`**, posiblemente por la gestión de color de Premiere. El compositor entrega `#6F04BA`.
3. `velabody.py` fallaba al imprimir las notas en consolas cp1252 ("→", "⚠"). Ya está corregido.
4. **Dos B-roll del bloque 7 se cruzan 8 cuadros**, porque `velabody.py` alarga cada inserto y adelanta el siguiente. En Premiere lo tapa `overwriteClip`; el compositor hace lo mismo y lo avisa.
5. El plan del ADS14 tomaba **C3835 de la carpeta del Video 7** (ruta absoluta en `E:`). Acá se bajó a la carpeta del ADS14.

## Diferencias pendientes frente al aprobado

- **Montserrat:** se usó la versión oficial (OFL). En la pastilla, las letras D, M, R y N del aprobado son 6–7 px más angostas, y el acento de la Ó está corrido. Se compensa con tracking para que la caja mida lo mismo. Hace falta la `.otf` de la clienta.
- **SFX del Pan Left** (`Transition Complex 14.wav`): no estaba entre los recursos, así que el piloto no lo tiene.
- **Zona segura:** se verificó con una zona aproximada; falta el PNG de la clienta.
- **Pan Left:** está medido y hecho a ojo cuadro a cuadro, sin comparación numérica (en el aprobado no hay dos cortes iguales para medir).
- **Halo del subtítulo de cámara:** ajustado visualmente.
- **Sándwich:** funciona (ver `stills/sandwich_cmp.png` en la caché), pero en el ADS14 la cabeza nunca llega a la pastilla, así que no se usa. El halo se comparó a ojo con el aprobado.
- **Descendentes en los títulos:** la máscara del MOGRT corta en la línea de base. En el compositor el borde baja con la entrada para no cortar la cola de la Q ("QUE", "QR"). En el aprobado no había letras con descendente para comparar.
- **Fondo cargado:** solo está hecha la "sombra"; el "desenfoque" de zona falla con un mensaje claro.
- **Arranque del hook:** `velabody.py` deja 0,5 s de casi silencio antes de "Esto". Es el comportamiento del builder y no se tocó.
- **Versión 1080x1080:** no está hecha. Según la wiki, se arma después de validar.

## Licencias

- **Remotion:** gratis para personas y empresas con fines de lucro de hasta 3 empleados; por encima de eso hace falta *Company License*.
- **RobustVideoMatting:** GPL-3.0. Se usa como herramienta local y no se redistribuye.
- **Montserrat:** OFL.
- **Gotham:** licencia de la clienta; nunca va a Git (el repo es público).

## Notas de Windows

- **Git:** D: no registra dueño, así que hay que usar `git -c safe.directory=D:/VELABODY ...`.
- **Python:** las herramientas corren con `-I`, que ignora `PYTHONIOENCODING`; cada script fuerza UTF-8.
