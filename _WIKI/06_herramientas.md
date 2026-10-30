# Herramientas

Todo está en `E:\VELABODY\_HERRAMIENTAS\`. Hay más detalle en `LEEME.md` dentro de esa carpeta.

| Archivo | Qué hace |
|---|---|
| `preparar_brief.py` | Baja el material del brief (rclone) filtrando por video (`--videos`). |
| `transcribir.py` | Transcripción con tiempos por palabra (faster-whisper large-v3, GPU). Acepta `--desde` y `--salida`. |
| `velabody.py` | Toma `plan_v2.json` (con `"estilo": "v2"`) y genera `armado_HookN.json`, SRTs, XML y notas. |
| `preview.py` | Arma un preview liviano del corte sin pasar por Premiere. |
| `palabras_corte.py`, `resaltados.py` | Ayudas para elegir cortes y textos destacados. |
| `config_velabody.json` | Medidas, niveles, rutas y reemplazos. Tiene que coincidir con esta wiki. |
| `premiere_panel\com.velabody.builder\` | Panel CEP *VELABODY Builder* (el JSX es `velabody.jsx`, función `construirV2`). |
| `panel_remoto.py` | Le permite a Claude manejar Premiere por el puerto de depuración `localhost:8088`. |

## Builder 2.1 (30/10/2026): reglas que ya aplica solo

- [x] **Nombres:** crea la bandeja del video con el nombre del brief (lo busca en `_MATERIAL_BRUTO\brief.json` por la carpeta, o lo toma de `"titulo"` en el plan) y nombra las secuencias `<título>_H1`, `_H2`… Los ORG llevan el título solo. Si ya existe una secuencia con ese nombre, lo avisa en el log. Los archivos de `_EDICION` siguen llamándose `armado_Hook1.json`, etc.
- [x] **Cortes:** `pad_inicio 0.15`, `pad_fin 0.35` y `pausa_max 0.8`. Además, cada borde se lleva hasta donde la forma de onda dice que termina la voz (Whisper suele cerrar antes), sin pasar a la palabra vecina. Suma una **cola final** de 1,5 s a cámara (`cola_final`) y avisa en las notas si la toma tiene menos de 1 s.
- [x] **Subtítulos:** los de fondo tienen 18 caracteres como máximo (`caracteres_max_fondo`). Un subtítulo nunca mezcla B-roll y cámara: cambia de estilo en el corte.
- [x] **Audio:** deja todos los bloques de voz al **mismo nivel**, apuntando a −14 LUFS. Si las tomas vienen bajas y el Volumen de Premiere (+15 dB como máximo) no alcanza, iguala al nivel posible y lo avisa en las notas. La música queda **22 dB por debajo de la voz real**. Los −14 LUFS y −1 dBTP finales salen del export (ver [color, audio y formatos](01_estilo/color_y_audio.md)).
- [x] **Títulos:** siempre justificados. Todas las líneas tienen el mismo ancho, y una línea corta puede escalar hasta 200 (`escala_linea_max`). Todo en MAYÚSCULAS.
- [ ] **Pendiente:** las pistas de subtítulos se crean sin estilo, así que hay que aplicar a mano los estilos de pista `VELABODY SUBS C FONDO` / `VELABODY SUBS CAMARA`. Tampoco crea la versión 1080x1080 (se hace a mano cuando el video está cerrado).

**Probado** el 30/10 en seco con el plan del Video 8 (sin Premiere): cortes 0,2–0,5 s más largos, cola final de 1,4 s y ningún subtítulo con fondo de más de 18 caracteres. **No se probó todavía dentro de Premiere.**

## Avisos técnicos

- **No renderizar** para verificar: alcanza con crear y guardar las secuencias (Juli, 29 y 30/10).
- **Panel instalado vs. repo:** la copia de `%APPDATA%\Adobe\CEP\extensions\com.velabody.builder` puede quedar vieja. Cada vez que cambia `velabody.jsx`, hay que copiarlo también ahí. Si cambia `VB_VERSION`, se sube `VERSION` en los dos `index.html`.
- **Construir directo:** `$.evalFile(".../velabody.jsx"); vb_construir(armadoPath, '{"titulos":true,"subs":true,"factor":1}')` y después `app.project.save()`.
- **CEP evalScript se come las barras invertidas:** las rutas se arman con `String.fromCharCode(92)`.
- **Render con AME** (solo si lo piden): `app.encoder.encodeSequence` con rutas con barra invertida. Con barras normales tira "Unknown error".
- `importSequences` puede dejar colgado ExtendScript hasta que se reinicia Premiere.
- Si Whisper estira una palabra sobre una pausa, hay que re-transcribir con `--desde` y chequear con `silencedetect` antes de cortar.
