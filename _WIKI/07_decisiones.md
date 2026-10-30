# Registro de decisiones

Lo más nuevo va arriba. Formato: **fecha · decisión** · por qué · fuente.

- **30/10/2026** · Segunda revisión del ADS14: **nunca un jump cut de la misma toma** (reemplaza los punch-ins y el B-roll partido de la revisión anterior); **el gráfico se corta con la toma**; **la cantidad de gráficos la decide el plan**; la Pan Left se toma de los keyframes del proyecto validado (`VELABODY_EDICION.prproj`); los renders de prueba van de a uno y en calidad media · pedido en la revisión del piloto.

- **30/10/2026** · Criterios de la revisión del ADS14 armado en Remotion (H1, H2 y H3):
  - **gráficos**: siempre dos palabras en dos líneas justificadas (nunca una sola ni dos en una línea); nunca tocan la cabeza; desenfoque detrás cuando caen sobre el cartel "velabody"; la pastilla sale por detrás de la cabeza (sándwich);
  - **ritmo**: sin silencios muertos; la presentadora a cámara 3 s o más o nada (si no, sigue el B-roll con la voz en off); nunca volver a cámara un segundo entre dos B-roll; B-roll en planos cortos; zooms y punch-ins como en el Video 1 FINAL; cola final de 1 s;
  - **subtítulos**: 2 o 3 palabras como máximo;
  - **Pan Left**: siempre la misma, medida en el Video 1 FINAL.

  Para todos los gráficos manda la [guía de gráficos](_guia/Guia_graficos_Velabody.pdf) ("la biblia"). En el builder, el ritmo se activa por plan (`"corte": {"modo": "dinamico"}` y `"ritmo"`); sin esas claves sigue igual que antes · pedido en la revisión del piloto.

- **30/10/2026** · **Piloto de compositor sin Premiere (Remotion)**, en la rama `piloto-remotion`: arma ADS14 Hook 2 + bloque 1 desde el mismo `armado.json`, con los gráficos medidos sobre el Video 1 FINAL. **El flujo oficial sigue siendo Premiere** y ninguna regla de estilo cambia. Hallazgo para el flujo actual: `Mouse Click.mp3` arranca con 0,26 s de silencio, así que el click del builder suena ~8 cuadros tarde. Ver `_COMPOSITOR/LEEME.md` · pedido del equipo.
- **30/10/2026** · El proyecto se sube a GitHub (repo privado `julietaeme66/VELABODY`) para trabajar de a varios. Va solo lo liviano: la wiki, las herramientas, y el guion y el plan de cada video. La guía de gráficos se copió a `_WIKI/_guia` para que Obsidian muestre sus imágenes · Juli.
- **30/10/2026** · **Builder 2.1**: aplica solo los nombres del brief y la bandeja por video, los cortes largos con cola final, los subtítulos de fondo de 18 caracteres, la voz pareja con la música 22 dB abajo y los títulos siempre justificados. Los −14 LUFS finales salen de la normalización del export · Juli pidió actualizarlo.
- **30/10/2026** · Los gráficos van **siempre en MAYÚSCULAS**. La guía de gráficos en PDF es el documento de referencia · Juli.
- **30/10/2026** · Reglas nuevas de Juli:
  - audio a −14 LUFS y −1 dBTP, con la música solo de fondo (reemplaza "voz a 0 dB");
  - se edita y entrega en 1080x1920, y la versión 1080x1080 se hace solo cuando el video está validado y cerrado;
  - subtítulos en `#6F04BA` siempre, con fondo sobre B-roll y sombreado a cámara; los de fondo con 18 caracteres como máximo y en línea única;
  - gráficos justificados, con un click cada uno y sombra o desenfoque si el fondo está cargado;
  - una bandeja por video con el nombre del brief y secuencias `…_H1`, `…_H2`, `…_H3`;
  - la misma capa de ajuste con Lumetri en todos los videos;
  - no cortar palabras (mejor largo que mal cortado) y dejar 1 o 2 s de la presentadora mirando a cámara al final.
- **30/10/2026** · Fuente de los subtítulos: a cámara **Gotham Book 49**; sobre B-roll con caja **Montserrat Medium 58** · confirmado en Premiere · Juli.
- **30/10/2026** · **Los ejemplos de referencia son los Videos 1 (FINAL), 2, 3 y 4.** Los ADS exportados (ADS12, ADS13 y ADSRF1) **no** son correctos y no se usan como ejemplo. De los ejemplos sale la regla de 2 a 4 gráficos por video · Juli.
- **30/10/2026** · Se crea esta wiki como única fuente de verdad del estilo y del flujo · había que unificar criterios entre Juli, Fede y Claude · Juli.
- **29/10/2026** · Al rehacer un video se borran las versiones anteriores (las secuencias y los archivos de `_EDICION`; los archivos van a la Papelera) · solo ocupaban lugar en el proyecto y en el SSD · Juli, Video 13.
- **29/10/2026** · Claude no renderiza para verificar salvo que se lo pidan · los renders colgaban Premiere y el editor revisa por su cuenta · Juli, Video 13.
- **29/10/2026** · En los ADS, Claude arma Hook 1 completo y desde el Hook 2 solo el hook · el editor corrige el cuerpo una vez y lo pega en los demás · Juli, Video 8.
- **28/10/2026** · **Estilo v2**: títulos Montserrat Medium paquetito con MOGRT 1080x1920, pastilla ExtraBold sin itálica, Pan Left con SFX y sin light leaks. La referencia pasa a ser el Video 1 FINAL más la guía de gráficos · validado con el Video 1 FINAL · grabaciones de pantalla de Juli.
- **27/10/2026** · Feedback de la dueña: unificar el audio, subtítulos como en el Video 1, transición más tranquila en lugar del light leak, productos en MAYÚSCULAS, una variante por línea y un solo violeta · Doc "Feedback primeros 5 videos".
- **25/10/2026** · El proyecto se muda de `C:\TRABAJO\VELABODY` a `E:\VELABODY` (SSD externo) · Juli.
- **25/10/2026** · Reparto: Juli edita 6, 7, 8 y 13 a 16; Fede edita 9 a 12 · tracker.
