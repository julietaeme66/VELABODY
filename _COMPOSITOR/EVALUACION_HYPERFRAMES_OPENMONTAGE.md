# HyperFrames y OpenMontage para VELABODY

Evaluación hecha después del piloto con Remotion (30/10/2026). No se instaló ninguno de los dos en el proyecto, y no se copió ninguna guía global suya a `CLAUDE.md`: las reglas de VELABODY siguen en la wiki.

## Lo que el piloto ya resolvió con Remotion

El reel VELABODY es material real cortado según un guion, con pocos gráficos muy pautados, subtítulos, una sola transición y un color fijo. Remotion lo resolvió sin código ajeno, porque:

- reutiliza `velabody.py` tal cual;
- los gráficos quedan dentro de ±2 px del aprobado;
- el color queda a ΔE ≈ 1,7;
- el audio sale a −14 LUFS.

La duda es **qué agrega cada herramienta encima de eso**, no si reemplaza a Remotion.

## HyperFrames (heygen-com/hyperframes, Apache-2.0)

**Qué es:** composiciones en HTML/CSS con animaciones GSAP "seekables", renderizadas a MP4 de forma determinista. Trae CLI, un estudio, un catálogo de bloques y skills para agentes.

**Qué aportaría acá:**
- **Prototipar animaciones nuevas** que la clienta pida (otra transición para los ADS "más juguetones", una entrada distinta para un dato o un número), con GSAP y catálogo de bloques, antes de pasarlas a un componente de Remotion.
- **Un formato que entiende alguien que no programa:** una animación en HTML/CSS se puede revisar y tocar más fácil que un componente React.

**Qué no aportaría:**
- No mejora lo que ya funciona. Los gráficos actuales son dos MOGRT medidos, y en Remotion ya coinciden.
- Tener **dos motores de render en producción** duplica el mantenimiento (fuentes, color, sincronización de audio) y el riesgo de que el mismo gráfico se vea distinto según quién lo renderice.

**Integración propuesta (acotada):** usarlo solo como banco de pruebas, en una carpeta fuera del repo, para diseñar animaciones candidatas. Lo que se apruebe se reescribe como componente de `_COMPOSITOR/src/componentes` y se mide contra un ejemplo aprobado, como se hizo con el título y la pastilla. HyperFrames no entra en la línea de producción.

## OpenMontage (calesthio/openmontage, **AGPL-3.0**)

**Qué es:** un sistema "agéntico" de producción con 12 pipelines (explicativos, documental con material de archivo, talking head, doblaje, demos…). Tiene skills de director por etapa, selección de proveedores de IA (imagen, video, voz y música), autorevisión con ffprobe, muestreo de cuadros y niveles de audio, y compositor Remotion o HyperFrames.

**Qué aportaría acá, en etapas posteriores al compositor:**
1. **Análisis de videos de referencia:** su flujo "partí de un video que te guste" (transcripción, ritmo, escenas y estilo) se parece a lo que hacemos para las fichas de `_WIKI/04_ejemplos`. Puede inspirar una herramienta que arme la ficha y su hoja de contactos sola.
2. **Autorevisión antes de mostrar:** la idea de verificar la entrega (ffprobe, cuadros, niveles, subtítulos, "lo prometido contra lo entregado") ya está en `verificar_entrega.py`. Su lista de chequeos sirve para completarla (por ejemplo, subtítulos fuera de la zona segura o huecos negros).
3. **Variantes de hooks y localización:** su pipeline de doblaje y subtítulos es una referencia por si VELABODY pide versiones en otro idioma.
4. **Registro de decisiones con aprobación humana** en cada punto creativo, que coincide con cómo trabajan Juli y Fede.

**Qué no conviene:**
- **Licencia AGPL-3.0:** si se copia su código a las herramientas de VELABODY o se ofrece como servicio, obliga a liberar el código derivado. Conviene usarlo **solo como herramienta externa** o tomar **ideas**, sin copiar código.
- Su fuerte es **generar** material (imágenes y video con IA, voz sintética, música de stock). VELABODY trabaja con material grabado y reglas estrictas de la clienta. Sus pipelines generativos no aplican y podrían meter elementos que la wiki no permite.
- Trae guías globales propias (`CLAUDE.md`, `AGENTS.md`, decenas de skills) que chocarían con la wiki como única fuente de verdad.

**Integración propuesta (acotada):** ninguna dependencia en el repo. Si más adelante se quiere probar, que sea en un clon aparte, para:
- el análisis de referencias, que alimenta fichas de la wiki revisadas por Juli;
- comparar su lista de autorevisión con `verificar_entrega.py` y sumar lo que falte, escrito de cero.

## Orden sugerido

1. Producir un ADS completo con Remotion (H1, H2 y H3 con el mismo cuerpo) y que Juli lo revise contra Premiere.
2. Completar los recursos que faltan: Montserrat `.otf` de la clienta, SFX del Pan Left y PNG de zona segura.
3. Recién después, si aparece un pedido de animación nueva, usar HyperFrames como banco de pruebas.
4. OpenMontage, solo como fuente de ideas para el análisis de referencias y la autorevisión.
