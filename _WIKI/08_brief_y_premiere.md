# Brief semanal y organización en Premiere

## Cómo viene el brief

Cada semana llega un brief en **PDF** o en **.docx**, siempre con la misma estructura. `preparar_brief.py` lee cualquiera de los dos y lo vuelca en `_MATERIAL_BRUTO\brief.json`. Del PDF también guarda los lineamientos generales (duración, B-roll, nombres de archivo, portada) en `_MATERIAL_BRUTO\brief_lineamientos.md`.

Por cada video trae:

1. **Un párrafo título** con este formato: `Video N — CÓDIGO · Equipo: tema`.
   Ejemplo: `Video 6 — ADS12 · Derma Scan: por qué incorporar Derma Scan`.
   - Los **ADS** traen hooks. Los **ORG** no traen hooks.
2. **Una tabla** con una fila por bloque y 5 columnas:

| Columna | Qué tiene | Ejemplo |
|---|---|---|
| Bloque | `Hook 1`, `Hook 2`, `Hook 3` (solo en ADS) y después `2`, `3`, `4`… | `Hook 1` |
| Inserts sugeridos | `A cámara` o `Insert`, con el link de Drive del B-roll | `Insert` |
| Texto | Lo que dice la presentadora en ese bloque | "Derma Scan es un analizador facial…" |
| Clip | El link de Drive de la toma a cámara | `Clip` |
| Indicación | Qué pieza es y desde qué segundo usar la toma | `Pieza 1 · Desde el seg 25` |

3. A veces trae **extras** debajo de la tabla: más inserts o fotos con una indicación de uso. Por ejemplo, "Fotos de las fases del vello, para sumar en chico…".

Con `--videos` se elige qué videos del brief bajar y armar. Ver [flujo de trabajo](03_flujo_de_trabajo.md).

## Nombres de entrega (compositor)

Como pide el brief, cada archivo lleva **el código del video** y, en los anuncios, **el número de hook**:

| Caso | Archivo en `_ENTREGAS/<código>/` |
|---|---|
| ADS con hooks | `ADS12_Hook1.mp4`, `ADS12_Hook2.mp4`, `ADS12_Hook3.mp4` |
| ORG sin hooks | `ORG7.mp4` |
| Portada (un cuadro sin texto, con la presentadora a cámara) | `ADS12_Hook1_portada.png`, … |

Si el código tiene espacios (`ADS RF Cavi Pro 1`), van con guion bajo: `ADS_RF_Cavi_Pro_1_Hook1.mp4`.

## Nombres en Premiere

### Una carpeta (bandeja) por video

Cada video tiene en el proyecto una **bandeja con el nombre exacto del brief**, con los dos puntos incluidos:

```
Video 6 — ADS12 · Derma Scan: por qué incorporar Derma Scan
```

Adentro van sus secuencias, sus SRT y su material.

> En Windows, las **carpetas del disco** no admiten ":", así que en `E:\VELABODY` el nombre va sin los dos puntos (`Video 6 — ADS12 · Derma Scan por qué incorporar Derma Scan`). En **Premiere** sí se usa el nombre completo.

### Secuencias

Las secuencias llevan el **mismo nombre que el video** más el sufijo del hook:

| Caso | Nombre de la secuencia |
|---|---|
| ADS con hooks | `Video 6 — ADS12 · Derma Scan: por qué incorporar Derma Scan_H1`, `…_H2`, `…_H3` |
| ORG sin hooks | `Video 9 — ORG7 · Diode Laser 4D: parámetros automáticos con el sistema SMART` (sin sufijo) |
| Versión 1080x1080, cuando el video ya está cerrado | El mismo nombre más `_1x1` *(a confirmar)* |

> **Reemplaza** los nombres viejos `ADS12_Hook1`, `ADS14_Hook1 · v2`, etc. El builder todavía usa el formato viejo y hay que actualizarlo.
