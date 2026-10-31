# Flujo de trabajo

**Claude arma y exporta los videos con el compositor (`_COMPOSITOR`, Remotion), sin Premiere.** Primero exporta todo en baja para validar; recién cuando está validado, en alta para entregar. *(Decidido el 30/10, después del piloto del ADS14. Reemplaza "Claude no renderiza", del flujo con Premiere.)*

## Los 7 pasos

| Paso | Quién | Qué pasa |
|---|---|---|
| 1. Brief | Quien pide la tanda | Le pasa a Claude el brief en **PDF** (o .docx). |
| 2. Ingesta | Claude | `npm run brief -- "<brief.pdf>" [--videos 6,8]` lee las fichas y **baja de Drive todas las tomas** (Claude las baja siempre, sin pedirlas). Arma `Video N — …/` con `PRESENTADORA`, `B-ROLL`, `VOZ EN OFF` y `guion.md`, y guarda los lineamientos generales en `_MATERIAL_BRUTO/brief_lineamientos.md`. Después transcribe todo (`transcribir.py`) y comprueba que cada toma diga lo que pide la ficha. |
| 3. Plan y preguntas | Claude → quien pidió | Escribe `Video N — …/_EDICION/plan.json` para cada video (ver abajo) y manda **una sola ronda de preguntas para toda la tanda**: los gráficos que propone para cada pieza, tomas dudosas o faltantes, voz en off, palabras mal dichas y choques con el brief o la wiki. |
| 4. Export en baja | Claude | `npm run baja` arma y exporta **todas las piezas en baja** (540x960, ~6 MB cada una) y deja una tabla resumen en `_COMPOSITOR_SALIDAS/resumen_baja.md`. |
| 5. Feedback | Quien pidió | Pide los cambios. Si valen para todos los videos, Claude actualiza la wiki y anota la decisión en [07_decisiones](07_decisiones.md). Si son de un solo video, cambia su `plan.json`. |
| 6. Corrección en baja | Claude | Reexporta en baja **solo las piezas que cambian** (`--videos`, `--piezas`). Se repiten los pasos 5 y 6 hasta que esté validado. |
| 7. Entrega en alta | Claude | `npm run alta` exporta todo en 1080x1920 (−14 LUFS, −1 dBTP). En `_ENTREGAS/<código>/` deja cada pieza con el nombre del brief (`ADS12_Hook1.mp4`, `ORG7.mp4`) y su **portada sin texto** (`…_portada.png`). Después, `npm run limpiar` manda a la Papelera las versiones de prueba y deja la última en alta de cada pieza. |
| 8. 1080x1080 | Claude | Solo cuando la clienta valida y cierra el video. Todavía no está hecho en el compositor. |

Los comandos se corren desde `_COMPOSITOR`; el detalle está en `_COMPOSITOR/LEEME.md`.

## El plan de cada video (`plan.json`)

Lo escribe Claude a partir de la ficha del brief, con las reglas de esta wiki. El ejemplo es el del Video 8: `Video 8 — ADS14 · …/_EDICION/plan.json`. Lleva:

- `codigo`, `titulo` y `carpeta`, que es la carpeta de las tomas, relativa a la raíz.
- La música.
- `"corte": {"modo": "dinamico", …}` y `"ritmo": {…}`: el ritmo de [cortes y ritmo](01_estilo/cortes_y_ritmo.md).
- Los `hooks`, en los ADS: cada hook sale **completo**, hook más cuerpo. No se usa `solo_hook_desde`.
- Los `bloques`, cada uno con su clip, sus gráficos, su B-roll y su Pan Left.

**Gráficos:** se ponen los que marca el brief. Si no marca ninguno, Claude los propone para cada pieza en la ronda de preguntas, y se usan los que se validen.

## Qué controla Claude en cada pieza

Lo mide automáticamente sobre el MP4 exportado y lo informa en la tabla resumen:

- **Duración:** entre 45 y 60 s, como pide el brief.
- **Sonoridad:** −14 LUFS y −1 dBTP.
- **% a cámara:** el brief pide al menos la mitad. El ritmo validado en el ADS14 da ~20 %, así que se informa y no se fuerza.
- **El equipo en los primeros 5 s:** se informa cuándo aparece el primer B-roll o la pastilla.
- **Zona segura:** según el PNG de la clienta.
- **Clicks y color.**
- **Avisos del armado:** B-roll que se movió por sacudidas y palabras dudosas.

El resto de las reglas lo aplica el builder solo:
- sin jump cuts;
- el gráfico se corta con la toma;
- B-roll largo partido en planos de 3–4 s y sin movimientos bruscos;
- números en cifras en los gráficos;
- la pastilla entra una sola vez.

## Reglas de trabajo para Claude

- Antes de armar, leer [00_INICIO](00_INICIO.md) y las páginas de estilo.
- Probar siempre en **baja**. La alta se hace una sola vez, al final, con todo validado.
- **Nunca pisar un exportado:** cada render tiene su número de versión.
- **Git:** commits locales en la rama del compositor, sin push mientras no se pida. El repo figura como público, así que nunca se suben tomas, música, fuentes con licencia ni exportados.
- Hablar en castellano rioplatense.

## Alternativa: Premiere (flujo anterior)

Sigue funcionando para quien prefiera editar a mano.

1. `velabody.py` genera `armado_HookN.json` desde `_EDICION\plan_v2.json`.
2. El panel *VELABODY Builder* (o Claude con `panel_remoto.py`) clona la secuencia del Video 1 en la bandeja del video, con un build por llamada y `app.project.save()` después de cada uno.
3. El editor revisa y exporta con *Normalización de sonoridad* a −14 LUFS y −1 dBTP.
4. Para los hooks, Hook 1 va completo y desde el Hook 2 solo el hook (`"solo_hook_desde": 2`): el editor pega el cuerpo corregido.

Reglas de Premiere:
- Identificar la secuencia recién clonada por un **ID que no existía antes**, nunca por "la última de la lista" (ver [errores conocidos](04_ejemplos/a_evitar/errores_conocidos.md)).
- Esperar a que carguen los medios antes de construir.
- No tocar secuencias corregidas por el editor.

Reparto del brief de los Videos 6 a 16 en el flujo con Premiere: Juli, 6, 7, 8, 13 y 14 a 16; Fede, 9 a 12.
