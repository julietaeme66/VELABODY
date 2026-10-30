# Cortes y ritmo

## Cortes de audio y video

**Nunca se corta una palabra a la mitad.** Es preferible que un corte quede **largo** a que quede mal cortado: alargarlo después obliga a mover toda la secuencia, y eso es mucho más engorroso que recortar un poco. *(Juli, 30/10/2026)*

- Los cortes tienen que ser **normales**, sin recortes agresivos de pausas.
- Cada corte deja que **la última palabra termine de sonar entera**, con su cola: las "s" finales, las vocales que se arrastran y la respiración natural.
- Se corta en las **pausas reales** del habla, nunca adentro de una palabra.
- Si hay dudas sobre dónde termina una palabra, se deja **más margen, no menos**.
- Los tiempos de Whisper no son exactos: a veces cortan la palabra antes de que termine o la estiran sobre una pausa. Hay que chequear contra la forma de onda (con `silencedetect`) antes de confiar en ellos.

## Final del video

**Se dejan 1 o 2 segundos de la presentadora mirando a cámara** después de la última palabra, para que el video no cierre de golpe. *(Juli, 30/10/2026)*

- La toma sigue después de terminar de hablar, sin cortar en la última sílaba.
- La música sigue sonando y hace el fade en esos segundos finales.

## En el builder

Desde la versión 2.1 (30/10), el builder corta con márgenes de 0,15 s antes y 0,35 s después de la voz real (medida en la forma de onda, no solo con Whisper). Solo quita pausas de más de 0,8 s y suma una cola final de 1,5 s. Los márgenes viejos (0,08 / 0,18 / 0,45) eran los que se comían las colas. Ver [herramientas](../06_herramientas.md).
