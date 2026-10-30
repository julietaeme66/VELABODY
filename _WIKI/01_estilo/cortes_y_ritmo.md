# Cortes y ritmo

## Cortes de audio y video

**Nunca se corta una palabra a la mitad.** Es preferible que un corte quede **largo** a que quede mal cortado: alargarlo después obliga a mover toda la secuencia, y eso es mucho más engorroso que recortar un poco. *(Juli, 30/10/2026)*

- Los cortes tienen que ser **normales**, sin recortes agresivos de pausas.
- Cada corte deja que **la última palabra termine de sonar entera**, con su cola: las "s" finales, las vocales que se arrastran y la respiración natural.
- Se corta en las **pausas reales** del habla, nunca adentro de una palabra.
- Si hay dudas sobre dónde termina una palabra, se deja **más margen, no menos**.
- Los tiempos de Whisper no son exactos: a veces cortan la palabra antes de que termine o la estiran sobre una pausa. Hay que chequear contra la forma de onda (con `silencedetect`) antes de confiar en ellos.

## Ritmo (pedido del 30/10, revisión del ADS14)

- **Sin silencios muertos.** Las pausas largas dentro de una toma y entre bloques se recortan; la voz arranca casi en el corte, como en el Video 1 FINAL. Sigue valiendo no cortar palabras.
- **A cámara, 3 segundos o más, o nada.** Si la presentadora va a aparecer solo un momento antes o después de un B-roll ("Primero" y enseguida el insert, o callada antes de la transición), no se la muestra: el B-roll se estira y la voz sigue en off. Entre dos B-roll nunca se vuelve a cámara por un segundo. El hook abre siempre a cámara.
- **B-roll en planos cortos** (hasta ~2,5 s; en el Video 1 FINAL ninguno pasa de 2,2 s). Si un insert tiene que cubrir más, se parte en planos de ~2 s de distintos momentos de la toma.
- **Zooms como en el Video 1 FINAL:** los tramos a cámara se parten en planos de ~2 s, alternando encuadre normal y punch-in (×1,25–1,4), con un zoom lento hacia adentro o hacia afuera en cada uno (±4–9 % por segundo).

## Final del video

**Se deja 1 segundo de la presentadora mirando a cámara** después de la última palabra, para que termine bien la oración y se la vea sonriendo. Con eso basta. *(Juli, 30/10/2026; ajustado el 30/10 en la revisión del ADS14: ~~1 o 2 segundos~~)*

- La toma sigue después de terminar de hablar, sin cortar en la última sílaba.
- La música sigue sonando y hace el fade en esos segundos finales.

## En el builder

Desde la versión 2.1 (30/10), el builder corta con márgenes de 0,15 s antes y 0,35 s después de la voz real (medida en la forma de onda, no solo con Whisper). Solo quita pausas de más de 0,8 s y suma una cola final de 1,5 s. Los márgenes viejos (0,08 / 0,18 / 0,45) eran los que se comían las colas. Ver [herramientas](../06_herramientas.md).

Para el ritmo de arriba, el plan activa `"corte": {"modo": "dinamico", ...}` y `"ritmo": {...}` (ver `_COMPOSITOR/pilotos/ads14/plan.json`):

- **Recorte dinámico:** mide la voz de cada toma con un umbral relativo a esa voz, no al pico. En tomas muy bajas el umbral por pico queda pegado al ruido de sala y deja segundos muertos. Deja 0,06 s antes y 0,15 s después de la voz, y saca pausas de más de 0,3 s. Solo achica tramos, nunca los agranda.
- **Control:** después del recorte, cada palabra del guion alineada por Whisper tiene que quedar adentro; si no, sale un aviso en `notas_revision`.
