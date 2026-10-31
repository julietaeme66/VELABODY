# Wiki Velabody

Reels verticales para la marca **Velabody** (1080x1920, 30 fps). Desde el 30/10 los arma y exporta **Claude con el compositor** (`_COMPOSITOR`, Remotion): brief → todo en baja → feedback → todo en alta. Ver [flujo de trabajo](03_flujo_de_trabajo.md). Premiere queda como alternativa. Esta wiki es la **única fuente de verdad**: si algo de acá choca con una memoria, un PDF viejo o un plan anterior, manda la wiki.

> **Para Claude:** leé esta página entera antes de editar cualquier video. Después abrí las páginas de la sección que vayas a tocar. Si te corrigen algo que vale para todos los videos, actualizá la página que corresponde y anotalo en [07_decisiones](07_decisiones.md).

## Reglas de oro (lo mínimo para no equivocarse)

1. **Referencia de estilo:** los **Videos 1 (FINAL), 2, 3 y 4** y la guía de gráficos del 28/10. Ver [ejemplos buenos](04_ejemplos/README.md). Los ADS exportados hasta ahora **no** son referencia.
2. **Gráficos:** los que marca el brief. Si no marca ninguno, Claude los propone para cada video y se usan los validados. El primero va en el primer segundo y el producto, en pastilla, que **entra una sola vez**. Los **números van en cifras** ("5 COSAS").
3. **Un solo violeta:** `#6F04BA`. Se usa para títulos, pastilla y caja de subtítulos.
4. **Gráficos:** siempre en **MAYÚSCULAS** y con margen justificado (paquetito) y cada uno entra con un click. Si el fondo está cargado, se usa una sombra paralela leve o se desenfoca la zona del gráfico. → [titulos](01_estilo/titulos.md)
5. **Nombres de producto** siempre en MAYÚSCULAS, en un solo bloque y con una sola variante: **DERMA SCAN**, **DIODE LASER 4D**, **RF CAVI PRO**. "Laser" va **sin tilde**.
6. **Subtítulos:** con **B-roll** van con fondo (Montserrat Medium 58, máximo 18 caracteres); **a cámara** van con sombreado (Gotham Book 49). Siempre en `#6F04BA`, en una sola línea y a altura fija. → [subtitulos](01_estilo/subtitulos.md)
7. **Transiciones:** Mister Horse *Pan Left*, solo 2 o 3 por video, con SFX. **Sin light leaks.** → [transiciones](01_estilo/transiciones_y_movimiento.md)
8. **Audio y color:** la voz tiene que sonar perfecta y la música queda de fondo. Mezcla a **−14 LUFS** con true peak de −1 dBTP. Todos los videos llevan la misma capa de ajuste con Lumetri. → [color, audio y formatos](01_estilo/color_y_audio.md)
9. **Cortes:** **nunca** se corta una palabra a la mitad; es mejor un corte largo que uno mal hecho. **Nunca un jump cut de la misma toma.** El gráfico se corta con la toma. A cámara, 3 s o más, o nada. El B-roll largo se parte en planos de 3–4 s y **nunca tiene movimientos de cámara bruscos**. Al final queda **1 s** de la presentadora mirando a cámara, o nada si el plan lo pide. → [cortes y ritmo](01_estilo/cortes_y_ritmo.md)
10. **Todo dentro de la zona segura de IG**, con el mismo margen a los dos lados.
11. **Formato:** se edita y se entrega en **1080x1920**. Solo cuando el video está validado y cerrado, cada secuencia se pasa a **1080x1080**.
12. **Nombres de entrega:** el código del video más el hook (`ADS12_Hook1.mp4`, `ORG7.mp4`), cada uno con su portada sin texto. → [brief](08_brief_y_premiere.md)
13. **Se prueba en baja y se entrega en alta:** primero todas las piezas en baja para validar, y la alta una sola vez, con todo validado. → [flujo de trabajo](03_flujo_de_trabajo.md)

## Documento de referencia

[**Guía de gráficos Velabody (PDF)**](_guia/Guia_graficos_Velabody.pdf): explica paso a paso cada gráfico (paquetito, pastilla, sándwich de capas, máscara y rastreador), con fotogramas. Las medidas también están resumidas en [titulos](01_estilo/titulos.md).

## Secciones

| Página | Qué tiene |
|---|---|
| [01_estilo/titulos](01_estilo/titulos.md) | Títulos paquetito y pastilla de destacado, con medidas exactas. |
| [01_estilo/subtitulos](01_estilo/subtitulos.md) | Subtítulos a cámara y sobre B-roll. |
| [01_estilo/transiciones_y_movimiento](01_estilo/transiciones_y_movimiento.md) | Pan Left, zooms, punch-ins y sándwich de capas. |
| [01_estilo/cortes_y_ritmo](01_estilo/cortes_y_ritmo.md) | No cortar palabras, ritmo sin jump cuts, B-roll sin sacudidas y cola final. |
| [01_estilo/color_y_audio](01_estilo/color_y_audio.md) | Lumetri, nivelación de audio para redes y paso a 1080x1080. |
| [02_reglas_cliente](02_reglas_cliente.md) | Todo lo que pidió la clienta, con fecha y fuente. |
| [03_flujo_de_trabajo](03_flujo_de_trabajo.md) | Del brief a la entrega con el compositor: los 7 pasos y quién hace qué. |
| [04_ejemplos](04_ejemplos/README.md) | Ediciones aprobadas (fichas con fotogramas) y errores para no repetir. |
| [05_recursos](05_recursos.md) | Dónde está cada MOGRT, sonido, música, LUT y guía. |
| [06_herramientas](06_herramientas.md) | Compositor, scripts y panel de Premiere, y cómo los usa Claude. |
| [08_brief_y_premiere](08_brief_y_premiere.md) | Cómo viene el brief semanal y cómo se nombran bandejas y secuencias. |
| [07_decisiones](07_decisiones.md) | Registro de cambios de criterio: fecha, qué se decidió y por qué. |

## Cómo se mantiene

- **Ejemplo nuevo:** copiá [la plantilla](_plantillas/ficha_ejemplo.md) en `04_ejemplos/buenos/`, o pedíselo a Claude ("ADS13_Hook1 es buen ejemplo porque…"). Claude arma la ficha y saca los fotogramas.
- **Regla nueva o cambiada:** se edita la página que corresponde y se suma una línea en [07_decisiones](07_decisiones.md). No hay que dejar dos versiones de la misma regla.
- **Para leerla cómoda:** en Obsidian, *Open folder as vault* → `E:\VELABODY\_WIKI` (o la carpeta `_WIKI` de tu copia del repo).
- **GitHub:** la wiki, las herramientas y los planes están en el repo [julietaeme66/VELABODY](https://github.com/julietaeme66/VELABODY). Hoy figura como **público**: nunca subir tomas, música, fuentes con licencia ni exportados. El compositor está en la rama `piloto-remotion`, con commits locales y sin push mientras no se pida. Los videos, la música y el `.prproj` no están en el repo: van por Drive.
