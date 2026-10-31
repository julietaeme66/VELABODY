# Proyecto Velabody

Reels verticales para Velabody. Desde el 30/10 los arma y exporta Claude con el compositor (`_COMPOSITOR`, Remotion), sin Premiere; Premiere queda como alternativa. Antes de editar, armar o responder sobre estilo, **leé `_WIKI/00_INICIO.md`** y las páginas de la sección que vayas a tocar.

- **Flujo** (`_WIKI/03_flujo_de_trabajo.md`):
  1. Llega el brief en PDF.
  2. Claude baja todas las tomas de Drive por su cuenta (`npm run brief`) y transcribe.
  3. Escribe un `plan.json` por video y hace **una sola ronda de preguntas**: entre ellas, los gráficos que propone si el brief no los marca.
  4. Exporta **todas las piezas en baja** (`npm run baja`).
  5. Recibe el feedback.
  6. Corrige en baja solo lo que cambia.
  7. Con todo validado, exporta **en alta** a `_ENTREGAS/<código>/` (`npm run alta`), con los nombres del brief y una portada sin texto, y limpia los renders de prueba (`npm run limpiar`).
- La wiki (`_WIKI/`) es la única fuente de verdad sobre estilo, reglas de la clienta, flujo, recursos y ejemplos. Si algo de tus memorias choca con la wiki, manda la wiki.
- Cuando corrijan un criterio que vale para todos los videos, actualizá la página que corresponde de la wiki y agregá una línea en `_WIKI/07_decisiones.md`. No dejes dos versiones de la misma regla. Si es de un solo video, va en su `plan.json`.
- **Git:** commits locales en la rama `piloto-remotion` y sin push salvo que lo pidan. El repo figura como público, así que nunca se suben tomas, música, fuentes con licencia ni exportados. En D: hay que usar `git -c safe.directory=D:/VELABODY`.
- Si te piden sumar un ejemplo, seguí `_WIKI/04_ejemplos/README.md`.
- Hablá en castellano rioplatense.
