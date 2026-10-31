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
- Cuando un mismo clip se usa en varios videos, conviene recorrerlo y usar otras partes para variar (no en todos los casos). *(pedido del 30/10)*
- **Nunca un jump cut que muestre la misma toma.** No se corta y se vuelve a la misma toma (ni con otro encuadre ni saltando un pedazo), ni en la presentadora ni en el B-roll. Una imagen se puede quedar más de 3 s: el dinamismo no va por ahí. Si una pausa recortada dejaría un salto a la vista, se conserva la pausa; dos tramos seguidos del mismo B-roll van de corrido. *(pedido del 30/10)*
- **Zoom lento continuo** en los tramos a cámara (hacia adentro o hacia afuera, ~3 % por segundo), sin cortes.
- **B-roll sin movimientos bruscos (regla general).** De cada B-roll se usa la parte que mejor acompaña lo que se dice (la que elige el plan), no necesariamente la más quieta. Pero **nunca un tramo con un movimiento o un cambio de cámara brusco**: si lo tiene, se usa el tramo más cercano del mismo clip con la imagen estable durante los segundos que hacen falta. Si el clip se mueve en todo su largo, va lo menos brusco. *(pedido del 30/10)*
- **B-roll largo: se corta cada 3–4 s.** Si un inserto dura mucho (p. ej. 10 s de la pantalla con los análisis), se parte. El plano siguiente sale del mismo archivo, pero tiene que verse como **otro plano**: o bien **otra parte del clip que muestre otra cosa**, o bien **un plano más cerrado** del mismo momento (×1,5, sobre la pantalla o el rostro; p. ej. cuando habla de la luz ultravioleta). Se alternan, empezando por el plano cerrado (sigue mostrando de lo que se habla). Los cortes caen al empezar una palabra, y nunca a mitad de un gráfico ni encima de una transición. *(pedido del 30/10)*

## Final del video

**Se deja 1 segundo de la presentadora mirando a cámara** después de la última palabra, para que termine bien la oración y se la vea sonriendo. Con eso basta. *(Juli, 30/10/2026; ajustado el 30/10 en la revisión del ADS14: ~~1 o 2 segundos~~)*

- La toma sigue después de terminar de hablar, sin cortar en la última sílaba.
- Si el cierre no lo necesita, la cola puede no estar: el plan lo pide con `"corte": {"cola_final": 0}` y el video termina con la última palabra, sin cortarla. *(ADS14, 30/10: "podría terminar en el 0:57 y nos ahorramos 2 segundos")*
- La música sigue sonando y hace el fade en esos segundos finales.

## En el builder

Desde la versión 2.1 (30/10), el builder corta con márgenes de 0,15 s antes y 0,35 s después de la voz real (medida en la forma de onda, no solo con Whisper). Solo quita pausas de más de 0,8 s y suma una cola final de 1,5 s. Los márgenes viejos (0,08 / 0,18 / 0,45) eran los que se comían las colas. Ver [herramientas](../06_herramientas.md).

Para el ritmo de arriba, el plan activa `"corte": {"modo": "dinamico", ...}` y `"ritmo": {...}` (ver `Video 8 — ADS14 · Derma Scan las funciones de Derma Scan/_EDICION/plan.json`):

- **Recorte dinámico:** mide la voz de cada toma con un umbral relativo a esa voz, no al pico. En tomas muy bajas el umbral por pico queda pegado al ruido de sala y deja segundos muertos. Deja 0,06 s antes y 0,15 s después de la voz, y saca pausas de más de 0,3 s. Solo achica tramos, nunca los agranda.
- **B-roll sin movimientos bruscos:** `config_velabody.json › broll_estable.brusco_max` (30). `broll_visual.py` mide cuánto se corre la imagen cada 0,1 s (en px de un cuadro de 1080, multiplicado por el zoom del plano) y toma el pico que dura al menos 0,2 s, hasta el último cuadro del plano: un tirón justo antes del corte también cuenta: ~10 es un paneo lento, 50 un barrido rápido y 200 un cambio de plano. Vale para todos los planes, también para el armado de Premiere. Los planos del B-roll largo partido pasan el mismo control, y el plano cerrado se busca a menos de 3 s del momento original para que siga mostrando lo mismo.
- **B-roll largo:** `"broll_max_s"` (4), `"broll_plano_s"` (3,5), `"broll_cerrado_zoom"` (1,5) y `"broll_distinto"` (0,6). `broll_visual.py` lee los cuadros clave de cada clip y mide qué tan distinta se ve otra parte. Por debajo de ~0,45 es el mismo encuadre apenas movido, o sea, un jump cut. El plano cerrado usa `zoom`/`foco_x`/`foco_y` del B-roll, que Premiere ya entiende.
- **Control:** después del recorte, cada palabra del guion alineada por Whisper tiene que quedar adentro; si no, sale un aviso en `notas_revision`.
