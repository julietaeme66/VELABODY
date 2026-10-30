# Errores conocidos

## De estilo (los marcó la clienta)

| Error | Corrección | Fuente |
|---|---|---|
| Subtítulos en dos líneas o a mitad de cuadro, tapando el equipo | Una línea a altura fija | Tracker |
| Light leak en cada corte | Pan Left 2 o 3 veces por video, sin light leaks | Feedback 27/10 |
| Nombre de producto con dos pesos de fuente o en minúsculas | MAYÚSCULAS, un bloque, una variante | Feedback 27/10 |
| Dos variantes de fuente en la misma línea | Separar en dos líneas | Feedback 27/10 |
| Dos tonos de violeta | Solo `#6F04BA` | Feedback 27/10 |
| Audio desparejo entre videos (Video 1 más fuerte y cargado a la izquierda) | Voz centrada y normalizada igual en todos | Feedback 27/10 |
| "láser" con tilde | "laser" | Tracker |
| Cortes abruptos que se comen el final de las palabras | Cortes normales; si hay dudas, largos | Juli 30/10 |
| El video termina en la última sílaba | Dejar 1 o 2 s de la presentadora mirando a cámara | Juli 30/10 |

## De proceso (le pasaron a Claude)

| Qué pasó | Regla | Fecha |
|---|---|---|
| Se tomó `app.project.sequences[último]` como el clon recién hecho y se pisó `ADS12_Hook3`, que ya estaba terminado (se recuperó desde el `.prproj` guardado). | Identificar el clon por un **ID nuevo** y chequear el nombre antes de tocarlo. | 29/10 |
| Un build sin guardar se perdió cuando Premiere reabrió el save anterior. | `app.project.save()` después de **cada** build. | 29/10 |
| El panel instalado tenía el JSX viejo y armó una secuencia v1 sin Lumetri. | Sincronizar el JSX con la carpeta de CEP y subir la `VERSION`. | 29/10 |
| Un render de verificación colgó ExtendScript (AME no estaba abierto). | No renderizar salvo que lo pidan. | 29/10 |
| Se cerró el diálogo "importando archivos" de Premiere y se rompió el build. | Esperar a que termine de cargar los medios. | 29/10 |
