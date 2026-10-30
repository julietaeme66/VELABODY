# Reglas de la clienta

Todo lo que pidió Velabody, con fecha y fuente. Si una regla cambia, se tacha la vieja (~~así~~), se agrega la nueva y se anota en [07_decisiones](07_decisiones.md).

## Fuentes

- **Tracker** (Google Sheet `1vUGW6HX…`): asignación de videos y feedback por video. Editores: Juli y Fede.
- **"Feedback primeros 5 videos"** (Google Doc `1eRZsxvhZJs4ljB8Rj1AhjC5rA1xL4j0HFlk_vbBEH0g`, se puede leer con el conector de Drive exportándolo a PDF).
- Los **guiones** son Google Docs privados: hay que pegarlos o compartirlos. En cada carpeta de video hay un `guion.md`.

## Reglas vigentes

### Subtítulos
- Con **B-roll** en pantalla van **con fondo**; con la presentadora **a cámara**, con **sombreado leve**. Los dos en `#6F04BA`, **siempre**. *(Juli, 30/10)*
- Los de fondo tienen **18 caracteres como máximo** y van en **línea única**. *(Juli, 30/10)*
- Siempre en **una línea**, a **altura fija**, sin cortar el cuadro a la mitad y sin tapar el equipo. *(tracker, oct.)*
- Todos los videos con subtítulos **igual que el Video 1**. *(feedback 27/10)*

### Gráficos
- **Siempre en MAYÚSCULAS.** *(Juli, 30/10)*
- **Siempre con margen justificado**, como en los ejemplos. *(Juli, 30/10)*
- **Cada gráfico entra con un click.** *(Juli, 30/10)*
- Si el fondo está cargado (cartelería), se usa una **sombra paralela leve** o se **desenfoca un poco la zona** del gráfico, de forma orgánica. *(Juli, 30/10)*

### Títulos
- Nombres de producto (**DIODE LASER 4D, DERMA SCAN, RF CAVI PRO**) siempre en **MAYÚSCULAS**, en un solo bloque y con una variante. *(feedback 27/10)*
- **Una sola variante de fuente por línea.** Si hacen falta dos, se separa en líneas (DEPILACIÓN / LASER). *(feedback 27/10)*
- **Un solo tono de violeta** (`#6F04BA`). *(feedback 27/10)*
- "laser" **sin tilde**. *(tracker)*

### Transiciones
- ~~Light leaks con moderación~~ → **reemplazar el light leak por algo más tranquilo**: sutil en los ORG y más juguetón en los ADS, a partir del video 4. *(feedback 27/10)* → Hoy usamos **Pan Left**.

### Cortes
- **No cortar palabras.** Hacer cortes normales y, si hay dudas, dejarlos largos: es preferible a cortarlos mal. *(Juli, 30/10)*
- Al final, **1 o 2 s de la presentadora mirando a cámara**, para que no cierre de golpe. *(Juli, 30/10)*

### Audio
- **La voz se escucha perfecta y la música queda solo de fondo**, con la nivelación estándar de redes: −14 LUFS y −1 dBTP. *(Juli, 30/10)*
- ~~Música apenas más baja que −20 dB. Voz normalizada a 0 dB.~~ *(tracker, reemplazado el 30/10)*
- **Unificar el audio** entre videos (el Video 1 estaba más fuerte y cargado a la izquierda). *(feedback 27/10)*

### Color
- **Todos los videos llevan la misma corrección**: una capa de ajuste con Color de Lumetri. *(Juli, 30/10)*
- Lumetri: LUT Alexa v3 → Rec709, exposición 0,4 y contraste 65. *(guía de la clienta)*

### Entregas (videos ADS)
- Cada ADS lleva **varios hooks** (Hook 1, 2, 3…) con el mismo cuerpo. Se exportan a `E:\VELABODY\EXPORTADOS`.
- Se entrega en **1080x1920** (H.264). Una vez **validado y cerrado**, cada secuencia, con hook o sin hook, se pasa a **1080x1080**. *(Juli, 30/10)*
- En Premiere: **una bandeja por video** con el nombre del brief, y las secuencias con ese nombre más `_H1`, `_H2` o `_H3`. *(Juli, 30/10)*
