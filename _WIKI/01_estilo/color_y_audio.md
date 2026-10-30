# Color, audio y formatos

## Color (Lumetri)

**Todos los videos llevan la misma corrección de color:** una **capa de ajuste** con *Color de Lumetri*, arriba de todo el video. No se corrige clip por clip; la excepción es el sándwich de capas.

| Parámetro | Valor |
|---|---|
| Input LUT | Alexa v3 → Rec709 |
| Exposición | 0,4 |
| Contraste | 65 |

- La capa viene incluida cuando se clona la secuencia del Video 1. Si se arma una secuencia a mano, hay que **copiar esa misma capa de ajuste**, no rehacer el Lumetri.
- En los tramos con sándwich de capas, la capa de ajuste se deshabilita y el mismo Lumetri se pega en las dos copias del clip. Ver [transiciones y movimiento](transiciones_y_movimiento.md).

## Audio

**Prioridad: la voz se tiene que escuchar perfecta.** La música va **baja, solo de fondo**, y nunca compite con la voz.

### Nivelación estándar para redes

| Medida | Objetivo |
|---|---|
| Loudness integrado de la mezcla final | **−14 LUFS** (lo que normalizan Instagram, TikTok y YouTube) |
| True peak máximo | **−1 dBTP**. Nunca 0 dB, porque al recomprimir en la plataforma satura. |
| Voz | Pareja de punta a punta y centrada, sin estar cargada a un canal. Es la que define los −14 LUFS. |
| Música | **20 a 25 dB por debajo de la voz** (≈ −34 a −39 LUFS). Es un colchón: si se nota, está alta. Fade de 2 s al final. |
| Click de títulos | Audible pero corto (−8 dB de ganancia del clip). |
| SFX de transición | −12 dB |

### Cómo se hace

1. **El builder** deja la voz pareja en todos los bloques y la música 22 dB por debajo. Si las tomas vienen muy bajas (pasa seguido: −34 LUFS en crudo), la voz queda pareja pero por debajo de −14, y lo avisa en `notas_revision`.
2. **En el export**, en *Exportar › Efectos › Normalización de sonoridad*: estándar ITU BS.1770-3, **sonoridad objetivo −14 LUFS** y **true peak −1 dBTP**. Esto lleva cada video exactamente a −14 y todos quedan parejos entre sí.
3. Si se edita el audio a mano: voz en *Sonido esencial › Diálogo* y música en *Sonido esencial › Música*, con ducking contra el diálogo.

> Esto reemplaza la regla vieja de "voz normalizada a 0 dB de pico" y "música a −23 dB de ganancia".

## Formatos de entrega

1. **Se edita y se entrega siempre en 1080x1920.**
2. **Recién cuando el video está validado y cerrado**, cada secuencia (con hook o sin hook) se pasa a **1080x1080**. La versión cuadrada no se arma antes ni en paralelo.

| Etapa | Tamaño | Nombre de la secuencia |
|---|---|---|
| Edición y entrega | 1080x1920 | `<nombre del video>_H1` (ver [nombres en Premiere](../08_brief_y_premiere.md)) |
| Después de validado | **1080x1080** | `<nombre del video>_H1_1x1` *(sufijo propuesto, a confirmar)* |

### Cómo adaptar a 1080x1080

El cuadrado es la franja central de la vertical (y entre ~420 y ~1500), así que **no alcanza con cambiar el tamaño de la secuencia**:

- **Reencuadrar** cada clip: la cara en el tercio superior y el equipo visible en el B-roll.
- **Reubicar los gráficos:** títulos (y≈380) y pastillas (y 350 a 440) quedan **afuera** del cuadrado y hay que bajarlos dentro del margen.
- **Subtítulos:** mantener la altura fija, pero dentro del cuadrado.
- Volver a chequear que nada tape el equipo ni la cara.
