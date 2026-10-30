# Flujo de trabajo

**Claude arma el editable y el editor lo revisa en Premiere.** Claude **no renderiza ni exporta**: alcanza con crear y guardar las secuencias (Juli, 30/10).

## Reparto

| Editor | Videos |
|---|---|
| Juli | 6 (ADS12), 7 (ADS13), 8 (ADS14), 13 (ADS4), 14 a 16 (ADS RF Cavi Pro 1–3) |
| Fede | 9 a 12 |

Antes de bajar o armar algo de un brief, hay que filtrar los videos del editor que lo pide (`preparar_brief.py --videos`).

## Pasos por video

1. **Brief:** llega el .docx semanal, siempre con la misma estructura (ver [brief y Premiere](08_brief_y_premiere.md)), con los links al material en Drive. El material se baja con rclone a `Video N — CÓDIGO · Título\` en las subcarpetas `PRESENTADORA`, `B-ROLL` y `VOZ EN OFF`, más el `guion.md`.
2. **Transcripción:** `transcribir.py` (Whisper large-v3 con GPU) da los tiempos por palabra. Si se corre sobre una subcarpeta, hay que pasar `--salida <video>\_EDICION\transcripciones`.
3. **Plan:** Claude escribe `_EDICION\plan_v2.json`. Tiene los hooks y los bloques del guion, y para cada uno el clip, los gráficos, los zooms, el B-roll y el Pan Left. Para el formato, ver el de Video 8.
4. **Armado:** con `velabody.py` se generan `armado_HookN.json`, los SRT y las notas.
5. **Construir en Premiere:** el panel *VELABODY Builder* (o Claude por `panel_remoto.py`) clona la secuencia del Video 1. Cada secuencia va en la bandeja del video y con el nombre del brief más `_H1`, `_H2`… (ver [brief y Premiere](08_brief_y_premiere.md)). Se hace **un build por llamada** y `app.project.save()` después de cada uno.
6. **Revisión:** el editor revisa en Premiere y le pasa los cambios a Claude en texto ("el título 2 que entre antes"). Claude regenera.
7. **Hooks:** Hook 1 se arma completo (hook + cuerpo). Desde el Hook 2 se arma **solo el hook**, y el editor pega el cuerpo ya corregido (`"solo_hook_desde": 2`).
8. **Export:** lo hace el editor en 1080x1920, a `E:\VELABODY\EXPORTADOS`, con *Normalización de sonoridad* a −14 LUFS y −1 dBTP.
9. **Versión 1080x1080:** solo cuando la clienta valida y cierra el video, cada secuencia se adapta a 1080x1080. Ver [formatos](01_estilo/color_y_audio.md#formatos-de-entrega).
10. **Limpieza:** cuando hay versión nueva, se borran las secuencias y los archivos de la versión anterior (los archivos van a la **Papelera**, no se borran del todo).

## Reglas de trabajo para Claude

- **Nunca** tomar "la última secuencia de la lista" como la recién clonada. Hay que identificarla por un **ID que no existía antes**. Ver [errores conocidos](04_ejemplos/a_evitar/errores_conocidos.md).
- Esperar a que Premiere termine de cargar los medios antes de construir.
- No tocar secuencias corregidas por el editor ni videos de otro editor.
- Hablar en castellano rioplatense.
