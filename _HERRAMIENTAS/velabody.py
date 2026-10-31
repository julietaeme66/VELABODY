"""Generador de armado VELABODY.

Toma un plan de corte (plan.json, lo escribe Claude a partir del guion) y las
transcripciones palabra por palabra, y produce en <carpeta_video>/_EDICION/:

  armado.json         línea de tiempo resuelta (lo lee el panel de Premiere)
  subs_camara.srt     subtítulos cuando ella habla a cámara
  subs_broll.srt      subtítulos cuando hay B-roll (estilo con fondo violeta)
  corte_fcp.xml       respaldo: el corte en XML de Final Cut (Archivo > Importar)
  notas_revision.md   decisiones y avisos para revisar

Uso:
    python velabody.py <plan.json>
"""
import difflib
import json
import math
import os
import pathlib
import re
import subprocess
import sys
import unicodedata
import urllib.parse
from xml.sax.saxutils import escape

AQUI = pathlib.Path(__file__).resolve().parent
CONFIG = json.loads((AQUI / "config_velabody.json").read_text(encoding="utf-8"))


def _fusionar(base: dict, extra: dict) -> None:
    for k, v in extra.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            _fusionar(base[k], v)
        else:
            base[k] = v


# config_local.json (no se versiona) pisa las rutas de cada compu: "raiz" del proyecto, "recursos.*" y
# "carpetas_fuentes". Sin ese archivo (ni VELABODY_RAIZ) todo sigue apuntando a E:\VELABODY
CONFIG_LOCAL = AQUI / "config_local.json"
if CONFIG_LOCAL.exists():
    _fusionar(CONFIG, json.loads(CONFIG_LOCAL.read_text(encoding="utf-8")))
RAIZ = pathlib.Path(os.environ.get("VELABODY_RAIZ") or CONFIG.get("raiz") or r"E:\VELABODY")
CARPETAS_FUENTES = [pathlib.Path(c) for c in CONFIG.get("carpetas_fuentes", [])] + [
    RAIZ / "_RECURSOS" / "fuentes", pathlib.Path(r"C:\Windows\Fonts"),
    pathlib.Path.home() / r"AppData\Local\Microsoft\Windows\Fonts"]


def carpeta_plan(plan: dict) -> pathlib.Path:
    """Carpeta del video: absoluta como siempre, o relativa a la raíz del proyecto (portable)."""
    c = pathlib.Path(plan["carpeta"])
    return c if c.is_absolute() else RAIZ / c


# ---------------------------------------------------------------- utilidades

def normalizar(palabra: str) -> str:
    s = unicodedata.normalize("NFKD", palabra.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9ñ]", "", s)


# en los gráficos los números van en cifras ("CINCO COSAS" → "5 COSAS"; pedido del 30/10, regla general);
# en los subtítulos siguen con letras. "Un", "uno" y "una" no se tocan: casi siempre son artículos
_UNIDADES = ["cero", "", "dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho", "nueve", "diez", "once", "doce",
             "trece", "catorce", "quince", "dieciseis", "diecisiete", "dieciocho", "diecinueve", "veinte"]
_DECENAS = {"treinta": 30, "cuarenta": 40, "cincuenta": 50, "sesenta": 60, "setenta": 70, "ochenta": 80, "noventa": 90}
NUMEROS = {**{w: n for n, w in enumerate(_UNIDADES) if w}, **_DECENAS, "cien": 100, "mil": 1000,
           **{"veinti" + w: 20 + n for n, w in enumerate(_UNIDADES) if 2 <= n <= 9}, "veintiuno": 21, "veintiun": 21}
_UNO = {"uno", "un", "una"}


def numeros_en_cifras(texto: str) -> str:
    """Los números escritos con letras pasan a cifras, también "treinta y cinco" → "35". Mantiene el resto."""
    palabras = texto.split()
    salida, k = [], 0
    while k < len(palabras):
        n = NUMEROS.get(normalizar(palabras[k]))
        u = normalizar(palabras[k + 2]) if k + 2 < len(palabras) else ""
        u = 1 if u in _UNO else NUMEROS.get(u, 0)
        if n in _DECENAS.values() and k + 2 < len(palabras) and normalizar(palabras[k + 1]) == "y" and 1 <= u <= 9:
            salida.append(str(n + u))
            k += 3
            continue
        salida.append(str(n) if n is not None else palabras[k])
        k += 1
    return " ".join(salida)


def similitud(a: str, b: str) -> float:
    if a == b:
        return 1.0
    return difflib.SequenceMatcher(None, a, b).ratio()


def aplicar_reemplazos(texto: str) -> str:
    """Convenciones de la marca (p. ej. 'laser' sin tilde)."""
    for a, b in CONFIG.get("reemplazos", {}).items():
        texto = re.sub(r"(?<!\w)" + re.escape(a) + r"(?!\w)", b, texto)
    return texto


def tokens(texto: str) -> list[str]:
    return [t for t in re.split(r"\s+", aplicar_reemplazos(texto).strip()) if normalizar(t)]


def srt_tiempo(seg: float) -> str:
    ms = int(round(seg * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def ffprobe(path: pathlib.Path) -> dict:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries",
         "stream=codec_type,width,height,r_frame_rate:stream_side_data=rotation:format=duration", "-of", "json", str(path)],
        capture_output=True, check=True).stdout
    d = json.loads(out)
    info = {"duracion": float(d["format"]["duration"]), "ancho": None, "alto": None, "fps": None, "audio": False}
    for s in d["streams"]:
        if s["codec_type"] == "video" and info["ancho"] is None:
            num, den = s["r_frame_rate"].split("/")
            ancho, alto = s["width"], s["height"]
            # cámara en vertical: el archivo dice 3840x2160 pero trae rotación de 90° (se ve 2160x3840)
            rot = next((abs(int(sd.get("rotation", 0))) for sd in s.get("side_data_list", []) if "rotation" in sd), 0)
            if rot % 180 == 90:
                ancho, alto = alto, ancho
            info.update(ancho=ancho, alto=alto, fps=float(num) / float(den))
        if s["codec_type"] == "audio":
            info["audio"] = True
    return info


def pico_db(path: pathlib.Path, ini: float, fin: float) -> float:
    r = subprocess.run(["ffmpeg", "-v", "info", "-ss", f"{ini:.3f}", "-to", f"{fin:.3f}", "-i", str(path),
                        "-vn", "-af", "volumedetect", "-f", "null", "-"], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    m = re.search(r"max_volume:\s*(-?[\d.]+) dB", r.stderr)
    return float(m.group(1)) if m else 0.0


def loudness(path: pathlib.Path, ini: float = 0.0, fin: float = 10 ** 6) -> tuple[float, float]:
    """Loudness integrado (LUFS) y true peak (dBTP) de un tramo, medidos con el loudnorm de ffmpeg."""
    r = subprocess.run(["ffmpeg", "-hide_banner", "-ss", f"{ini:.3f}", "-to", f"{fin:.3f}", "-i", str(path), "-vn",
                        "-af", "loudnorm=print_format=json", "-f", "null", "-"], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    ini_json = r.stderr.rindex("{")
    d = json.loads(r.stderr[ini_json:r.stderr.index("}", ini_json) + 1])
    return float(d["input_i"]), float(d["input_tp"])


VENTANA_ENV = 0.01
_envolventes: dict[str, list[float]] = {}


def envolvente(path: pathlib.Path) -> list[float]:
    """Nivel RMS en dB de la toma, en ventanas de 10 ms (se calcula una vez por toma)."""
    clave_env = str(path)
    if clave_env not in _envolventes:
        import numpy as np
        pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-vn", "-ac", "1", "-ar", "16000",
                              "-af", "highpass=f=80", "-f", "s16le", "-"], capture_output=True, check=True).stdout
        x = np.frombuffer(pcm, np.int16).astype(np.float64) / 32768
        n = int(16000 * VENTANA_ENV)
        x = x[: len(x) // n * n].reshape(-1, n)
        _envolventes[clave_env] = (20 * np.log10(np.sqrt((x ** 2).mean(1)) + 1e-9)).tolist()
    return _envolventes[clave_env]


def recorte_dinamico(tramos: list[list[float]], env: list[float], cc: dict,
                     conservar: list[tuple[float, float]] = ()) -> list[list[float]]:
    """Modo "dinamico" (plan › corte): achica cada tramo hasta donde de verdad hay voz y saca las pausas
    internas largas. El umbral es relativo a la voz de la toma (percentil 95 + umbral_db), no al pico: en
    tomas muy bajas el umbral por pico queda pegado al ruido de sala y deja segundos muertos. Las pausas que
    toquen algún intervalo de "conservar" no se cortan (el corte se vería como jump cut). Solo achica
    o parte tramos, nunca los agranda: no puede meter habla nueva. Deja voz_pad_inicio antes de la voz y
    voz_pad_fin después (para las colas: "s" finales, vocales que se arrastran). Los tramos de entrada
    salen de la búsqueda de siempre, con los márgenes generosos de la regla general: así un inicio que
    Whisper marcó tarde no queda afuera antes de llegar acá."""
    import numpy as np
    e = np.array(env)
    v = VENTANA_ENV
    todos = np.concatenate([e[int(a / v):int(b / v)] for a, b in tramos])
    if not len(todos):
        return tramos
    umbral = max(np.percentile(todos, 95) + cc.get("umbral_db", -30), np.percentile(todos, 10) + 6)
    min_voz = 3                                     # 30 ms seguidos sobre el umbral cuentan como voz
    # se parte de un solo tramo continuo: las pausas las decide este recorte (y "conservar"), no la búsqueda de antes
    tramos = [[min(a for a, _ in tramos), max(b for _, b in tramos)]]
    salida = []
    for a, b in tramos:
        i0, i1 = int(a / v), int(b / v)
        voz = e[i0:i1] >= umbral
        # corridas de voz (descarta chasquidos de menos de 30 ms)
        corridas, k = [], 0
        while k < len(voz):
            if voz[k]:
                j = k
                while j < len(voz) and voz[j]:
                    j += 1
                if j - k >= min_voz:
                    corridas.append([k, j])
                k = j
            else:
                k += 1
        if not corridas:
            salida.append([a, b])
            continue
        # se unen las corridas separadas por pausas cortas; las pausas largas se cortan
        unidas = [corridas[0]]
        for c in corridas[1:]:
            g0, g1 = (i0 + unidas[-1][1]) * v, (i0 + c[0]) * v
            if (c[0] - unidas[-1][1]) * v <= cc["voz_pausa_max"] or any(x0 - 0.3 <= g1 and x1 + 0.3 >= g0 for x0, x1 in conservar):
                unidas[-1][1] = c[1]
            else:
                unidas.append(c)
        for c0, c1 in unidas:
            ini = max(a, (i0 + c0) * v - cc["voz_pad_inicio"])
            fin = min(b, (i0 + c1) * v + cc["voz_pad_fin"])
            salida.append([round(ini, 4), round(fin, 4)])
    return salida


def borde_habla(sil: list[tuple[float, float]], t: float, final: bool, limite: float | None) -> float:
    """Lleva un borde de Whisper hasta donde la forma de onda dice que empieza/termina la voz.
    Whisper suele cerrar las palabras antes de su cola ("s" finales, vocales arrastradas): el corte
    se hace en el silencio real que sigue (o antes del que precede), sin pasar a la palabra vecina."""
    if final:
        a = next((sa for sa, sb in sil if sa >= t - 0.05), None)
        if a is not None and a - t < 0.6 and (limite is None or a <= limite):
            return max(t, a)
        return t
    b = next((sb for sa, sb in reversed(sil) if sb <= t + 0.05), None)
    if b is not None and t - b < 0.4 and (limite is None or b >= limite):
        return min(t, b)
    return t


def silencios(path: pathlib.Path) -> list[tuple[float, float]]:
    """Intervalos de silencio relativos al pico del clip (cacheados junto a la transcripción)."""
    pico = pico_db(path, 0, 10 ** 6)
    r = subprocess.run(["ffmpeg", "-v", "info", "-i", str(path), "-vn", "-af",
                        f"silencedetect=n={pico - 28:.1f}dB:d=0.25", "-f", "null", "-"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    ini = [float(x) for x in re.findall(r"silence_start: (-?[\d.]+)", r.stderr)]
    fin = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", r.stderr)]
    return list(zip(ini, fin + [10 ** 6] * (len(ini) - len(fin))))


def ajustar_palabras(palabras: list[dict], sil: list[tuple[float, float]]) -> None:
    """Whisper a veces estira una palabra sobre un silencio (p. ej. «tratamientos» de 48,9 a 53,7 s
    cuando en realidad se dice después de una pausa). La palabra se queda con el tramo de habla
    real más largo que haya dentro de su intervalo."""
    for w in palabras:
        tramos = [[w["i"], w["f"]]]
        for a, b in sil:
            nuevos = []
            for x, y in tramos:
                if b <= x or a >= y:
                    nuevos.append([x, y])
                    continue
                if a > x:
                    nuevos.append([x, a])
                if b < y:
                    nuevos.append([b, y])
            tramos = nuevos
        if tramos:
            w["i"], w["f"] = max(tramos, key=lambda r: r[1] - r[0])
        else:                                   # cayó entera en un silencio: tiempo desconocido
            w["f"] = w["i"]


def leak_con_alfa(origen: pathlib.Path) -> pathlib.Path:
    """Convierte un light leak (luz sobre negro) en ProRes 4444 con transparencia:
    alfa = canal más brillante y color des-premultiplicado. En modo Normal se ve
    como 'Trama' (Screen), así no hay que tocar el modo de fusión en Premiere."""
    destino = AQUI / "cache_leaks" / (origen.parent.name + " - " + origen.stem + " (alfa).mov")
    if not destino.exists():
        destino.parent.mkdir(exist_ok=True)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(origen), "-an", "-vf",
                        "format=rgba,geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':a='max(max(r(X,Y),g(X,Y)),b(X,Y))',"
                        "unpremultiply=inplace=1",
                        "-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le", str(destino)],
                       check=True)
    return destino


def render_pantalla_dividida(partes: list[dict], dur: float, carpeta: pathlib.Path, destino: pathlib.Path) -> None:
    """Pantalla dividida en franjas horizontales (una por insert), apiladas en 1080x1920.
    Se pre-renderiza en ProRes 422 HQ y entra a Premiere como un clip más de B-roll."""
    W, H = CONFIG["secuencia"]["ancho"], CONFIG["secuencia"]["alto"]
    n = len(partes)
    alto = H // n
    entradas, filtros = [], []
    for k, pt in enumerate(partes):
        ruta = pathlib.Path(pt["clip"])
        if not ruta.is_absolute():
            ruta = next(carpeta.glob(pt["clip"] + ".*"))
        entradas += ["-ss", f"{pt.get('in', 0):.3f}", "-t", f"{dur:.3f}", "-i", str(ruta)]
        foco_y = pt.get("foco_y", 0.5)
        filtros.append(f"[{k}:v]scale={W}:-2,crop={W}:{alto}:0:'max(0,min(ih-{alto},ih*{foco_y}-{alto}/2))',"
                       f"fps={CONFIG['secuencia']['fps']},setsar=1[p{k}]")
    filtros.append("".join(f"[p{k}]" for k in range(n)) + f"vstack=inputs={n},pad={W}:{H}:0:0[v]")
    subprocess.run(["ffmpeg", "-v", "error", "-y", *entradas, "-filter_complex", ";".join(filtros), "-map", "[v]",
                    "-an", "-t", f"{dur:.3f}", "-c:v", "prores_ks", "-profile:v", "3", str(destino)], check=True)


# ------------------------------------------------- alineación guion ↔ tomas

def alinear(guion: list[str], clip: list[dict]) -> tuple[float, list[int | None]]:
    """Alineación local (Smith-Waterman) del bloque del guion contra las palabras
    de una toma. Si hay varias tomas buenas, se queda con la ÚLTIMA.
    Devuelve (puntaje 0..1, índice de palabra del clip para cada palabra del guion)."""
    g = [normalizar(w) for w in guion]
    c = [normalizar(w["w"]) for w in clip]
    n, m = len(g), len(c)
    umbral = CONFIG["corte"]["similitud_palabra"]
    H = [[0.0] * (m + 1) for _ in range(n + 1)]
    T = [[0] * (m + 1) for _ in range(n + 1)]  # 1 diag, 2 arriba (salta guion), 3 izq (salta clip)
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            sim = similitud(g[i - 1], c[j - 1])
            diag = H[i - 1][j - 1] + (2.0 if sim >= umbral else -1.0)
            arriba = H[i - 1][j] - 1.0
            izq = H[i][j - 1] - 0.6
            doble = H[i - 2][j - 1] + 4.0 if i > 1 and similitud(g[i - 2] + g[i - 1], c[j - 1]) >= umbral else -1e9
            mejor = max(0.0, diag, arriba, izq, doble)
            H[i][j] = mejor
            T[i][j] = 0 if mejor == 0 else (1 if mejor == diag else (4 if mejor == doble else (2 if mejor == arriba else 3)))
    maximo = max(max(f) for f in H)
    if maximo <= 0:
        return 0.0, [None] * n
    # la última toma con puntaje cercano al máximo
    fin_i, fin_j = max(((i, j) for i in range(n + 1) for j in range(m + 1) if H[i][j] >= 0.92 * maximo),
                       key=lambda p: (p[1], H[p[0]][p[1]]))
    mapa: list[int | None] = [None] * n
    i, j = fin_i, fin_j
    while i > 0 and j > 0 and H[i][j] > 0:
        t = T[i][j]
        if t == 1:
            if similitud(g[i - 1], c[j - 1]) >= umbral:
                mapa[i - 1] = j - 1
            i, j = i - 1, j - 1
        elif t == 4:
            mapa[i - 1] = mapa[i - 2] = j - 1
            i, j = i - 2, j - 1
        elif t == 2:
            i -= 1
        else:
            j -= 1
    puntaje = sum(1 for x in mapa if x is not None) / n
    return puntaje, mapa


def palabras_clip(transcripcion: dict) -> list[dict]:
    return [w for s in transcripcion["segmentos"] for w in s["palabras"]]


# ----------------------------------------------------------------- títulos

def _fuente(nombre: str):
    from PIL import ImageFont
    for carpeta in CARPETAS_FUENTES:
        p = carpeta / nombre
        if p.exists():
            return ImageFont.truetype(str(p), 100)
    raise FileNotFoundError(f"No encuentro la fuente {nombre}")


def maquetar_titulo(lineas: list[list[dict]], y_primera: float | None = None) -> dict:
    """Arma el 'paquetito' como en los ejemplos de la marca (ANÁLISIS [facial], DIODE / [laser] 4D):
    la primera línea define el ancho; las demás se justifican a ese ancho sin superar su tamaño.
    La pastilla lleva texto más chico (pastilla_rel) y su alto ≈ las mayúsculas de la palabra clave.
    Devuelve, por pieza, el centro visual en px de la secuencia; el panel convierte a coordenadas del MOGRT."""
    cfg = CONFIG["titulos"]
    ancho_sec = CONFIG["secuencia"]["ancho"]
    pad_h, pad_v = cfg["pastilla_padding"]          # en em del texto de la pastilla
    rel = cfg["pastilla_rel"]
    gap = cfg["separacion_runs_em"]
    cap = cfg["alto_mayusculas_em"]

    def medir(linea):
        """Ancho natural de la línea a tamaño 100 (la pastilla a 100*rel, con su padding)."""
        total, partes = 0.0, []
        for k, run in enumerate(linea):
            estilo = cfg["fuentes"][run["estilo"]]
            texto = aplicar_reemplazos(run["t"])
            texto = texto.upper() if estilo["mayus"] else texto
            f = _fuente(estilo["archivo"])
            x0, _, x1, _ = f.getbbox(texto)
            w = x1 - x0
            if run["estilo"] == "pastilla":
                w = w * rel + 2 * pad_h * 100 * rel
            partes.append((texto, w, estilo, run["estilo"]))
            total += w + (gap * 100 if k else 0)
        return total, partes

    medidas = [medir(l) for l in lineas]
    t0 = min(cfg["tamano_max"], 100 * cfg["ancho_max"] / medidas[0][0])
    ancho = medidas[0][0] * t0 / 100
    x_izq = (ancho_sec - ancho) / 2
    y0 = y_primera or cfg["y_primera_linea"]   # la altura se puede pisar por video o por título
    y_centro = y0
    piezas = []
    for n, ((natural, partes), linea) in enumerate(zip(medidas, lineas)):
        tam = t0 if n == 0 else min(t0, 100 * ancho / natural)
        esc = tam / 100
        ancho_linea = natural * esc
        x = x_izq + (ancho - ancho_linea) / 2       # justificada (o centrada si no llega)
        hay_pastilla = any(e == "pastilla" for *_, e in partes)
        alto_linea = max(cap * tam, (cap + 2 * pad_v) * tam * rel if hay_pastilla else 0)
        if n:
            y_centro += alto_linea / 2
        for k, (texto, w, estilo, nombre) in enumerate(partes):
            if k:
                x += gap * tam
            ancho_run = w * esc
            tam_run = tam * rel if nombre == "pastilla" else tam
            pieza = {"texto": texto, "estilo": nombre, "fuente": estilo["ps"], "italica": estilo["italica"],
                     "tamano": round(tam_run, 1), "x": round(x + ancho_run / 2, 1), "y": round(y_centro, 1),
                     "ancho": round(ancho_run, 1), "alto_mayus": round(cap * tam_run, 1)}
            if nombre == "pastilla":
                pieza["padding"] = [round(pad_h * tam_run, 1), round(pad_v * tam_run, 1)]
                # el MOGRT "1-Line Fill Text Box" suma 14 px propios a cada padding: se descuentan
                base = cfg["pastilla_padding_base_px"]
                pieza["padding_mogrt"] = [round(max(0.0, v - base), 1) for v in pieza["padding"]]
            piezas.append(pieza)
            x += ancho_run
        y_centro += alto_linea / 2 + cfg["interlineado"] * tam
    alto_total = y_centro - cfg["interlineado"] * t0 - (y0 - cap * t0 / 2)
    y_top = y0 - cap * t0 / 2
    return {"piezas": piezas, "caja": [round(x_izq, 1), round(y_top, 1), round(ancho, 1), round(alto_total, 1)]}


def maquetar_titulo_v2(lineas: list[str], y_top: float | None = None) -> list[dict]:
    """Estilo v2 (Video 1 cerrado, guía 28/10): MOGRT 'Ease Position & Mask Y - Bottom' 1080x1920,
    Montserrat Medium en mayúsculas, tamaño de fuente 100 fijo; el tamaño se da con la Escala de
    Movimiento. La primera línea toca los dos bordes de la guía (o el tope de escala) y las demás se
    escalan al mismo ancho, cada una en su capa. Medido en el export del Video 1: ancho real ≈ 0,965 ×
    tinta de PIL; mayúsculas arriba en pos_y − 0,135·escala y línea de base en pos_y + 0,565·escala."""
    cfg = CONFIG["titulos_v2"]
    f = _fuente(cfg["fuente"])
    anchos = []
    for texto in lineas:
        x0, _, x1, _ = f.getbbox(aplicar_reemplazos(texto).upper())
        anchos.append((x1 - x0) * cfg["factor_ancho"])
    # margen justificado siempre (Juli 30/10, como "ANÁLISIS / FACIAL" del Video 2): todas las líneas
    # miden lo mismo; la más larga toca los dos bordes de la guía salvo que una línea corta tuviera que
    # pasar el tope de escala, y entonces el bloque entero se angosta
    tope_esc = cfg["escala_max"] if len(lineas) == 1 else cfg["escala_linea_max"]
    ancho = min(cfg["ancho_guia"], min(w * tope_esc / 100 for w in anchos))
    tope = y_top or cfg["y_mayusculas"]
    capas = []
    for n, (texto, w) in enumerate(zip(lineas, anchos)):
        esc = 100 * ancho / w
        pos_y = tope + cfg["arriba_rel"] * esc
        capas.append({"texto": aplicar_reemplazos(texto).upper(), "escala": round(esc, 1),
                      "pos": [cfg["x"], round(pos_y, 1)]})
        tope = pos_y + cfg["base_rel"] * esc + cfg["separacion"]
    return capas


def aplicar_zooms(aroll: list[dict], zooms: list[dict], medio, caras: dict, fps: int) -> list[dict]:
    """Parte los cortes de A-roll en los bordes de cada zoom y les pone escala/posición en px.
    "lento": zoom in con dos keyframes lineales (de → a); "punch": plano más cerrado fijo, para tapar
    un salto de corte. El zoom se hace hacia la cara ("caras": clip → [x, y] normalizados), que queda
    en el mismo lugar de pantalla (en el punch se acerca un poco al centro), sin dejar bordes."""
    W, H = CONFIG["secuencia"]["ancho"], CONFIG["secuencia"]["alto"]
    cuadro = lambda v: round(round(v * fps) / fps, 4)
    cortes = sorted({cuadro(v) for z in zooms for v in (z["t"], z["fin"])})
    partes = []
    for a in aroll:
        ini, fin = a["t"], a["t"] + a["out"] - a["in"]
        bordes = [ini] + [c for c in cortes if ini + 0.2 < c < fin - 0.2] + [fin]
        for b0, b1 in zip(bordes, bordes[1:]):
            partes.append({**a, "t": round(b0, 4), "in": round(a["in"] + b0 - ini, 4), "out": round(a["in"] + b1 - ini, 4)})
    for p in partes:
        if p.get("solo_audio"):                  # voz en off: no hay imagen que encuadrar
            continue
        m = medio(p["clip"])
        base = max(W / m["ancho"], H / m["alto"]) * 100
        fx, fy = caras.get(p["clip"], [0.5, 0.45])
        p_ini, p_fin = p["t"], p["t"] + p["out"] - p["in"]
        z = next((z for z in zooms if z["t"] - 0.01 <= (p_ini + p_fin) / 2 <= z["fin"] + 0.01), None)

        def encuadre(zz, acercar=0.0):
            sx = W * fx + (W / 2 - W * fx) * acercar
            sy = H * fy
            px = sx - (fx - 0.5) * W * zz
            py = sy - (fy - 0.5) * H * zz
            mx, my = (zz - 1) * W / 2, (zz - 1) * H / 2
            return [round(min(W / 2 + mx, max(W / 2 - mx, px)), 1), round(min(H / 2 + my, max(H / 2 - my, py)), 1)]

        if not z:
            p["escala"], p["pos"] = round(base, 2), [W / 2, H / 2]
        elif z["tipo"] == "punch":
            p["escala"], p["pos"] = round(base * z["z"], 2), encuadre(z["z"], 0.5)
        else:
            # lento: el zoom avanza a lo largo de todo el tramo del zoom aunque esté partido en varios cortes
            dz = lambda tt: z.get("de", 1.0) + (z["a"] - z.get("de", 1.0)) * (tt - z["t"]) / max(0.01, z["fin"] - z["t"])
            p["escala"], p["pos"] = round(base * dz(p_ini), 2), encuadre(dz(p_ini))
            p["kf"] = [{"t": round(p_ini, 4), "escala": round(base * dz(p_ini), 2), "pos": encuadre(dz(p_ini))},
                       {"t": round(p_fin, 4), "escala": round(base * dz(p_fin), 2), "pos": encuadre(dz(p_fin))}]
    return partes


def ritmo_automatico(rt: dict, aroll: list[dict], broll: list[dict], palabras: list[dict], zooms: list[dict],
                     duracion: float, medio, fps: int, notas: list[str]) -> list[dict]:
    """Ritmo de edición del Video 1 FINAL (plan › "ritmo"), medido plano a plano en el aprobado:
    1. Sin planos de la presentadora pegados a un B-roll que duren menos de min_plano_s o en los que diga
       una sola palabra o nada (p. ej. "Primero" y enseguida el insert, o quedarse callada antes de la
       transición): el B-roll se estira para cubrirlos y la voz sigue en off. El arranque del hook y la
       cola final a cámara del último bloque no se tocan.
    2. Nunca un jump cut dentro de la misma toma: B-roll seguido de la misma toma va de corrido, cada
       tramo a cámara es un solo plano con zoom lento continuo (reemplaza los zooms del plan), y los cortes
       de pausa que quedarían a la vista se devuelven para conservar esa pausa al volver a armar.
    Devuelve (zooms, saltos_visibles)."""
    cuadro = lambda v: round(round(v * fps) / fps, 4)
    min_plano = rt.get("min_plano_s", 1.2)
    fin_de = lambda x: x["t"] + x["out"] - x["in"]
    # un tramo a cámara pegado a un B-roll sobra si es corto o si la presentadora no dice más de una palabra
    # (o nada: queda en silencio antes de la transición)
    palabras_en = lambda a0, a1: sum(1 for p in palabras if a0 <= (p["i"] + p["f"]) / 2 <= a1)
    sobra = lambda a0, a1, minimo=min_plano: 0 < a1 - a0 and (a1 - a0 < minimo or palabras_en(a0, a1) <= 1)
    # volver a cámara entre dos inserts es lo más brusco: ahí se pide un plano más largo para quedarse
    entre_broll = rt.get("min_plano_entre_broll_s", 2.0)
    def cubrir(x: dict, t0: float, t1: float) -> None:
        """El B-roll x pasa a ocupar [t0, t1] de la línea de tiempo. Mantiene su material alineado y, si al
        archivo no le alcanza hacia atrás o hacia adelante, corre la ventana (así no queda un pedacito a cámara)."""
        dur = cuadro(t1 - t0)
        largo = medio(x["clip"])["duracion"]
        ini = min(max(0.0, x["in"] - (x["t"] - t0)), max(0.0, largo - dur))
        if ini + dur > largo:
            notas.append(f"- ⚠️ Ritmo: {x['clip']} dura menos que el tramo a cubrir ({dur:.2f} s).")
            dur = largo - ini
        x["t"], x["in"], x["out"] = cuadro(t0), round(ini, 3), round(ini + dur, 3)

    bloques = sorted({a["bloque"] for a in aroll})
    for nb in bloques:
        b0 = min(a["t"] for a in aroll if a["bloque"] == nb)
        b1 = max(fin_de(a) for a in aroll if a["bloque"] == nb)
        bs = sorted((b for b in broll if b["bloque"] == nb), key=lambda b: b["t"])
        if not bs:
            continue
        # el hook abre siempre con la presentadora (y el primer gráfico en el primer segundo)
        if nb != bloques[0] and sobra(b0, bs[0]["t"]):
            notas.append(f"- Ritmo: el B-roll {bs[0]['clip']} arranca {bs[0]['t'] - b0:.2f} s antes (cubre el inicio del bloque {nb}).")
            cubrir(bs[0], b0, fin_de(bs[0]))
        for x, y in zip(bs, bs[1:]):
            if sobra(fin_de(x), y["t"], entre_broll):
                notas.append(f"- Ritmo: se unen {x['clip']} y {y['clip']} (quedaban {y['t'] - fin_de(x):.2f} s a cámara en el medio).")
                cubrir(x, x["t"], y["t"])
        if nb != bloques[-1] and sobra(fin_de(bs[-1]), b1):
            notas.append(f"- Ritmo: el B-roll {bs[-1]['clip']} sigue {b1 - fin_de(bs[-1]):.2f} s más (cubre el final del bloque {nb}).")
            cubrir(bs[-1], bs[-1]["t"], b1)

    # nunca un jump cut dentro de la misma toma (pedido del 30/10): dos B-roll seguidos de la misma toma
    # se unen en un solo plano continuo (el segundo sigue desde donde termina el primero)
    unidos = []
    for b in sorted(broll, key=lambda b: b["t"]):
        a = unidos[-1] if unidos else None
        if a and a["clip"] == b["clip"] and abs(b["t"] - fin_de(a)) < 1.5 / fps:
            extra = b["out"] - b["in"]
            if a["out"] + extra <= medio(a["clip"])["duracion"]:
                a["out"] = round(a["out"] + extra, 3)
                notas.append(f"- Ritmo: {b['clip']} sigue de corrido (sin jump cut entre dos tramos de la misma toma).")
                continue
        unidos.append(b)
    broll[:] = unidos

    # tramos a cámara: lo que no tapa ningún B-roll. Cada uno es un solo plano con un zoom lento continuo
    # (hacia adentro y hacia afuera, alternando entre tramos): el dinamismo no va por cortar la misma toma
    tapados = sorted((b["t"], fin_de(b)) for b in broll)
    tramos, cursor = [], 0.0
    for a0, a1 in tapados + [(duracion, duracion)]:
        if a0 - cursor > 0.05:
            tramos.append((cursor, a0))
        cursor = max(cursor, a1)
    vel, zmax = rt.get("zoom_lento_por_s", 0.03), rt.get("zoom_max", 1.12)
    nuevos = []
    for k, (p0, p1) in enumerate(tramos):
        z = min(zmax, 1.0 + vel * (p1 - p0))
        de, a = (1.0, z) if k % 2 == 0 else (z, 1.0)
        nuevos.append({"tipo": "lento", "de": round(de, 3), "a": round(a, 3), "t": cuadro(p0), "fin": cuadro(p1), "auto": True})

    # jump cuts que quedarían a la vista: dos tramos seguidos de la misma toma con un salto en el medio (una
    # pausa recortada) y sin un B-roll que tape ese corte. Se devuelven para volver a armar conservando esa pausa
    saltos = []
    ar = sorted((a for a in aroll if not a.get("solo_audio")), key=lambda a: a["t"])
    for x, y in zip(ar, ar[1:]):
        if x["clip"] != y["clip"] or abs(y["in"] - x["out"]) < 0.02:
            continue
        tapado = any(b["t"] - 0.5 / fps <= y["t"] <= fin_de(b) + 0.5 / fps for b in broll)
        if not tapado:
            saltos.append((x["clip"], round(x["out"], 3), round(y["in"], 3)))
    return nuevos, saltos


def broll_sin_sacudidas(broll: list[dict], medio, notas: list[str], carpeta_cache: pathlib.Path,
                        plano: float | None = None) -> None:
    """Regla general (30/10): de cada B-roll se usa la parte que eligió el plan por el guion, pero nunca un
    tramo con movimientos o cambios de cámara bruscos. Si lo tiene, el B-roll se corre al tramo más cercano
    del mismo clip sin sacudidas, mejor sin pisar lo que ya muestra otro B-roll de ese clip (si no hay otra
    forma, se repite antes que sacudirse). Con plano (el B-roll largo se parte después), se busca primero
    un arranque con los dos primeros planos quietos (el segundo es el plano cerrado que sigue de corrido) y,
    si no hay, con el primero; los demás los controla partir_broll_largo plano por plano."""
    sys.path.insert(0, str(AQUI))     # con python -I la carpeta del script no está en sys.path
    import broll_visual
    maximo = CONFIG["broll_estable"]["brusco_max"]
    for b in sorted(broll, key=lambda b: b["t"]):
        if "pantalla_dividida" in pathlib.Path(b["clip"]).name:
            continue
        m = medio(b["clip"])
        dur = b["out"] - b["in"]
        usados = [(x["in"], x["out"]) for x in broll if x is not b and x["clip"] == b["clip"]]
        umbral = maximo / (b.get("zoom") or 1.0)
        miras = sorted({min(dur, 2 * plano), min(dur, plano)}, reverse=True) if plano else [dur]
        nuevo, mira = None, miras[-1]
        for mira_k in miras:
            for us in (usados, []):
                s = broll_visual.parte_sin_sacudidas(m["ruta"], b["in"], mira_k, m["duracion"] - (dur - mira_k), umbral,
                                                     us, carpeta_cache)
                if broll_visual.brusco(m["ruta"], s, s + mira_k, carpeta_cache) < umbral:
                    nuevo, mira = s, mira_k
                    break
            if nuevo is not None:
                break
        if nuevo is None:      # ningún tramo quieto: el menos brusco
            nuevo = broll_visual.parte_sin_sacudidas(m["ruta"], b["in"], mira, m["duracion"] - (dur - mira), umbral,
                                                     usados, carpeta_cache)
        antes = broll_visual.brusco(m["ruta"], b["in"], b["in"] + mira, carpeta_cache)
        if nuevo != b["in"]:
            despues = broll_visual.brusco(m["ruta"], nuevo, nuevo + mira, carpeta_cache)
            aviso = "" if despues < umbral else " ⚠️ el clip no tiene un tramo quieto de ese largo: queda el menos brusco"
            notas.append(f"- B-roll {b['clip']} en {b['t']:.2f} s: el tramo {b['in']:.1f} s tiene un movimiento brusco "
                         f"({antes:.0f}); pasa a {nuevo:.1f} s ({despues:.0f}).{aviso}")
            b["in"], b["out"] = round(nuevo, 3), round(nuevo + dur, 3)


def partir_broll_largo(rt: dict, broll: list[dict], palabras: list[dict], graficos: list[dict], transiciones: list[dict],
                       medio, fps: int, notas: list[str], carpeta_cache: pathlib.Path) -> None:
    """B-roll largo (pedido del 30/10): un inserto de más de broll_max_s se corta en planos de ~broll_plano_s.
    Cada plano nuevo sale del mismo archivo sin ser un jump cut: o bien otra parte del clip que se ve
    distinta (broll_visual.otra_parte), o bien el mismo momento en un plano más cerrado (broll_cerrado_zoom,
    centrado en lo que tiene detalle). Se alternan, empezando por el plano cerrado (sigue mostrando lo
    mismo de lo que se habla, p. ej. el 3D bajo el título "CORTE 3D"). Los cortes caen al empezar
    una palabra, nunca a mitad de un gráfico ni encima de una transición. Ningún plano nuevo puede tener
    movimientos de cámara bruscos (broll_estable; el plano cerrado los agranda por su zoom)."""
    sys.path.insert(0, str(AQUI))     # con python -I la carpeta del script no está en sys.path
    import broll_visual
    brusco_max = CONFIG["broll_estable"]["brusco_max"]
    quieto = lambda ruta, t0, t1, zoom=1.0: broll_visual.brusco(ruta, t0, t1, carpeta_cache) * zoom < brusco_max
    maximo, plano = rt["broll_max_s"], rt.get("broll_plano_s", 3.5)
    radio_cerrado = rt.get("broll_cerrado_radio_s", 3.0)    # el plano cerrado sigue mostrando lo mismo
    zoom_cerrado, umbral = rt.get("broll_cerrado_zoom", 1.5), rt.get("broll_distinto", 0.6)
    minimo = rt.get("broll_plano_min_s", 2.0)
    cuadro = lambda v: round(round(v * fps) / fps, 4)
    ocupado = [(g["t"], g["fin"]) for g in graficos] + [(x["t"] - 0.5, x["t"] + 0.5) for x in transiciones]
    candidatos = sorted({cuadro(p["i"]) for p in palabras} | {cuadro(g["fin"]) for g in graficos})
    candidatos = [c for c in candidatos if not any(a < c < b for a, b in ocupado)]
    usados: dict[str, list[tuple[float, float]]] = {}
    for b in broll:
        usados.setdefault(b["clip"], []).append((b["in"], b["out"]))

    nuevos = []
    for b in sorted(broll, key=lambda b: b["t"]):
        dur = b["out"] - b["in"]
        n = max(1, round(dur / plano))
        if dur <= maximo or n < 2:
            nuevos.append(b)
            continue
        cortes, t0 = [], b["t"]
        for k in range(1, n):
            ideal = b["t"] + k * dur / n
            validos = [c for c in candidatos if c - t0 >= minimo and b["t"] + dur - c >= minimo * (n - k)]
            if validos:
                t0 = min(validos, key=lambda c: abs(c - ideal))
                cortes.append(t0)
        if not cortes:
            notas.append(f"- ⚠️ B-roll {b['clip']} de {dur:.1f} s: no encuentro dónde cortarlo (gráficos o transiciones encima).")
            nuevos.append(b)
            continue
        ruta, largo = medio(b["clip"])["ruta"], medio(b["clip"])["duracion"]
        bordes = [b["t"], *cortes, b["t"] + dur]
        prev = {**b, "out": round(b["in"] + bordes[1] - bordes[0], 3)}
        piezas = [prev]
        for k in range(1, len(bordes) - 1):
            d = round(bordes[k + 1] - bordes[k], 3)
            otra = broll_visual.otra_parte(ruta, d, largo, (prev["in"], prev["out"]), usados[b["clip"]], umbral, carpeta_cache,
                                           brusco_max / (b.get("zoom") or 1.0))
            sigue = prev["out"] if prev["out"] + d <= largo - 0.05 else None
            # plano cerrado: el mismo momento más cerca; si lo que sigue se mueve, el arranque quieto más cercano
            # (el cambio de escala ya lo hace otro plano). Sin pisar otros B-roll de este clip
            cerrado = None
            if prev.get("zoom", 1.0) < zoom_cerrado and sigue is not None:
                otros = [u for u in usados[b["clip"]] if u != (b["in"], b["out"])] + [(x["in"], x["out"]) for x in piezas]
                cerrado = broll_visual.parte_sin_sacudidas(ruta, sigue, d, largo, brusco_max / zoom_cerrado, otros,
                                                           carpeta_cache, radio=radio_cerrado)
                if not quieto(ruta, cerrado, cerrado + d, zoom_cerrado):
                    cerrado = None
            quiere_otra = k % 2 == 0 or cerrado is None
            if otra is not None and quiere_otra:
                pieza = {**b, "in": round(otra, 3), "out": round(otra + d, 3)}
                como = f"otra parte del clip ({otra:.1f} s)"
            elif cerrado is not None:
                fx, fy = broll_visual.foco_cercano(ruta, cerrado, cerrado + d, zoom_cerrado, carpeta_cache)
                pieza = {**b, "in": round(cerrado, 3), "out": round(cerrado + d, 3), "zoom": zoom_cerrado, "foco_x": fx, "foco_y": fy}
                como = f"plano más cerrado (×{zoom_cerrado}, foco {fx:.2f}/{fy:.2f}" + ("" if cerrado == sigue else f", desde {cerrado:.1f} s") + ")"
            elif (sigue is not None and prev.get("zoom", 1.0) != b.get("zoom", 1.0)
                  and quieto(ruta, sigue, sigue + d, b.get("zoom") or 1.0)):
                pieza = {**b, "in": round(sigue, 3), "out": round(sigue + d, 3)}
                como = "vuelve al plano abierto"
            else:
                # el clip no tiene nada quieto: gana lo menos brusco entre otra parte distinta, un plano cerrado en
                # cualquier momento del clip (el cambio de escala ya lo hace otro plano) y seguir de corrido
                z_b, z_prev = b.get("zoom") or 1.0, prev.get("zoom") or 1.0
                opciones = []
                otra = broll_visual.otra_parte(ruta, d, largo, (prev["in"], prev["out"]), usados[b["clip"]], umbral,
                                               carpeta_cache, brusco_max / z_b, menos_brusco=True)
                if otra is not None:
                    opciones.append((broll_visual.brusco(ruta, otra, otra + d, carpeta_cache) * z_b, "otra", otra))
                if z_prev < zoom_cerrado:
                    otros = [u for u in usados[b["clip"]] if u != (b["in"], b["out"])] + [(x["in"], x["out"]) for x in piezas]
                    c = broll_visual.parte_sin_sacudidas(ruta, sigue if sigue is not None else prev["in"], d, largo,
                                                         brusco_max / zoom_cerrado, otros, carpeta_cache)
                    if not any(c < u1 and c + d > u0 for u0, u1 in otros):
                        opciones.append((broll_visual.brusco(ruta, c, c + d, carpeta_cache) * zoom_cerrado, "cerrado", c))
                if sigue is not None:
                    opciones.append((broll_visual.brusco(ruta, prev["in"], prev["out"] + d, carpeta_cache) * z_prev, "corrido", None))
                # a igual sacudida, mejor no cortar
                valor, tipo, s = min(opciones, key=lambda o: (o[0], o[1] != "corrido")) if opciones else (0, "corrido", None)
                if tipo == "corrido":
                    prev["out"] = round(prev["out"] + d, 3)       # no hay cómo variar sin sacudirse más: el plano anterior sigue
                    notas.append(f"- ⚠️ B-roll {b['clip']}: no encuentro otra parte distinta ni un plano cerrado; sigue de corrido.")
                    continue
                if tipo == "otra":
                    pieza = {**b, "in": round(s, 3), "out": round(s + d, 3)}
                    como = f"otra parte del clip ({s:.1f} s)"
                else:
                    fx, fy = broll_visual.foco_cercano(ruta, s, s + d, zoom_cerrado, carpeta_cache)
                    pieza = {**b, "in": round(s, 3), "out": round(s + d, 3), "zoom": zoom_cerrado, "foco_x": fx, "foco_y": fy}
                    como = f"plano más cerrado (×{zoom_cerrado}, foco {fx:.2f}/{fy:.2f}, desde {s:.1f} s)"
                como += f" ⚠️ lo menos brusco ({valor:.0f}): el clip se mueve en todo su largo"
            pieza["t"] = cuadro(bordes[k])
            usados[b["clip"]].append((pieza["in"], pieza["out"]))
            piezas.append(pieza)
            prev = pieza
            notas.append(f"- Ritmo: {b['clip']} se corta en {bordes[k]:.2f} s → {como}.")
        nuevos.extend(piezas)
    broll[:] = nuevos


# ------------------------------------------------------------------ armado

def titulo_video(plan: dict) -> str:
    """Nombre del video tal cual el brief ("Video 6 — ADS12 · Derma Scan: por qué incorporar Derma
    Scan"): es la bandeja de Premiere y la base del nombre de cada secuencia. La carpeta del disco es
    el mismo nombre sin ":" (no válido en Windows), así que se busca en el brief por esa carpeta."""
    if plan.get("titulo"):
        return plan["titulo"]
    carpeta = carpeta_plan(plan).name
    for brief in (RAIZ / "_MATERIAL_BRUTO" / "brief.json", AQUI / "brief" / "brief.json"):
        if brief.exists():
            for v in json.loads(brief.read_text(encoding="utf-8")):
                if re.sub(r'[:<>"/\\|?*]', "", v["titulo"]).strip() == carpeta:
                    return v["titulo"]
    return carpeta


def armar(plan_path: pathlib.Path) -> None:
    """Orgánicos: una pieza. Anuncios (plan con "hooks"): una pieza por hook = hook + bloques comunes.
    Secuencias: "<título del brief>_H1", "_H2"… en los anuncios; el título solo en los orgánicos."""
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    plan["bandeja"] = titulo_video(plan)
    if plan.get("hooks"):
        for k, hook in enumerate(plan["hooks"], 1):
            if hook.get("pendiente"):          # hook sin material: se saltea sin cambiar la numeración
                print(f"⚠ Hook {k} pendiente: {hook.get('texto', '')}")
                continue
            # estilo v2: desde el hook N ("solo_hook_desde") la secuencia lleva solo el hook;
            # el body lo corrige Juli en el Hook 1 y lo pega en las demás
            solo = plan.get("solo_hook_desde") and k >= plan["solo_hook_desde"]
            pieza = {**plan, "bloques": [hook] + ([] if solo else plan["bloques"]), "nombre": f"{plan['bandeja']}_H{k}",
                     "solo_hook": bool(solo)}
            armar_sin_saltos(pieza, f"_Hook{k}")
    else:
        armar_sin_saltos({**plan, "nombre": plan["bandeja"]}, "")


def armar_sin_saltos(pieza: dict, sufijo: str, vueltas: int = 5) -> None:
    """Arma la pieza y, si quedó algún jump cut a la vista (pausa recortada dentro de la misma toma, sin B-roll
    que la tape), la vuelve a armar conservando esa pausa. Al conservarla se corre todo lo que sigue, así que
    puede aparecer otro: se repite hasta que no quede ninguno."""
    conservar: dict[str, list] = {}
    for _ in range(vueltas):
        saltos = armar_pieza(pieza, sufijo, conservar)
        if not saltos:
            return
        for clip, fin, ini in saltos:
            conservar.setdefault(clip, []).append((min(fin, ini), max(fin, ini)))
        print(f"↺ {pieza['nombre']}: se conservan {len(saltos)} pausa(s) para no dejar jump cuts a la vista")
    print(f"⚠ {pieza['nombre']}: quedan jump cuts después de {vueltas} vueltas")


def armar_pieza(plan: dict, sufijo: str, conservar: dict | None = None) -> list:
    """Arma una pieza. "conservar" (toma → [(fin, inicio)] en segundos de la toma) son pausas que no se
    recortan porque el corte quedaría a la vista como jump cut. Devuelve los jump cuts que todavía se ven."""
    conservar = conservar or {}
    saltos: list = []
    carpeta = carpeta_plan(plan)
    salida = carpeta / "_EDICION"
    salida.mkdir(exist_ok=True)
    trans_dir = salida / "transcripciones"
    fps = CONFIG["secuencia"]["fps"]
    # el plan puede ajustar el corte (p. ej. {"modo": "dinamico", "pausa_max": 0.3}); si no, la regla general
    cc = {**CONFIG["corte"], **plan.get("corte", {})}
    notas = [f"# Notas de revisión — {plan['nombre']}", ""]
    if plan.get("corte"):
        notas.append(f"- Corte con ajustes propios del plan: {plan['corte']}")

    medios: dict[str, dict] = {}

    def medio(nombre: str) -> dict:
        if nombre not in medios:
            p = pathlib.Path(nombre)
            if not p.is_absolute():
                p = next(carpeta.glob(nombre + ".*"), carpeta / nombre)
            medios[nombre] = {"ruta": str(p), **ffprobe(p)}
        return medios[nombre]

    # transcripción por clip; si el bloque pide "desde_seg" (tomas repetidas pegadas) se usa la
    # transcripción hecha desde ese segundo (transcribir.py --desde) y solo las palabras posteriores
    def clave(c, desde):
        return f"{c}@{desde:g}" if desde else c

    trans, sil_por_clip = {}, {}
    for b in plan["bloques"]:
        if b.get("voz_en_off"):
            b["clip"] = b["voz_en_off"]
    usos = {(b.get("clip"), b.get("desde_seg", 0)) for b in plan["bloques"] if b.get("clip")}
    usos |= {(c, 0) for c in plan["aroll"]}
    for c, desde in usos:
        nombre = pathlib.Path(c).name
        variante = trans_dir / f"{nombre}.desde{desde:g}.words.json"
        archivo = variante if desde and variante.exists() else trans_dir / f"{nombre}.words.json"
        tr = json.loads(archivo.read_text(encoding="utf-8"))
        if desde:
            for seg in tr["segmentos"]:
                seg["palabras"] = [w for w in seg["palabras"] if w["i"] >= desde - 0.3]
        if c not in sil_por_clip:
            sil_por_clip[c] = silencios(pathlib.Path(medio(c)["ruta"]))
        ajustar_palabras(palabras_clip(tr), sil_por_clip[c])
        trans[clave(c, desde)] = tr

    t = 0.0  # cursor en la línea de tiempo
    aroll, broll, titulos, leaks, palabras_tl = [], [], [], [], []
    graficos, zooms, transiciones = [], [], []
    for nb, bloque in enumerate(plan["bloques"], 1):
        guion = tokens(bloque["texto"])
        candidatos = [bloque["clip"]] if bloque.get("clip") else plan["aroll"]
        desde = bloque.get("desde_seg", 0) if bloque.get("clip") else 0
        mejor = max(((alinear(guion, palabras_clip(trans[clave(c, desde)])), c) for c in candidatos), key=lambda x: x[0][0])
        (puntaje, mapa), clip = mejor
        pal = palabras_clip(trans[clave(clip, desde)])
        idx = sorted({k for k in mapa if k is not None})
        if not idx:
            notas.append(f"- ⚠️ Bloque {nb}: no encontré la frase en ninguna toma: «{bloque['texto']}»")
            continue
        if puntaje < 0.85:
            notas.append(f"- ⚠️ Bloque {nb}: la mejor toma ({clip}) coincide solo {puntaje:.0%} con el guion.")
        # palabras de la toma que sobran respecto del guion (dentro del rango usado)
        usadas = set(idx)
        extra = [pal[k]["w"] for k in range(idx[0], idx[-1] + 1) if k not in usadas]
        if extra:
            notas.append(f"- Bloque {nb} ({clip}): la toma dice además «{' '.join(extra)}» (quedó adentro; recortar a mano si molesta).")
        # sub-cortes: se eliminan SOLO los silencios reales largos dentro de la toma
        # (no se confía en los huecos entre palabras de Whisper: así nunca se pierde habla).
        # Juli 30/10: nunca cortar palabras; mejor un corte largo que uno que se coma la cola
        dur_clip = medio(clip)["duracion"]
        sil = sil_por_clip[clip]
        previa = pal[idx[0] - 1]["f"] if idx[0] > 0 else None
        siguiente = pal[idx[-1] + 1]["i"] if idx[-1] + 1 < len(pal) else None
        ini_toma = max(0.0, borde_habla(sil, pal[idx[0]]["i"], False, previa) - cc["pad_inicio"])
        fin_toma = min(dur_clip, borde_habla(sil, pal[idx[-1]]["f"], True, siguiente) + cc["pad_fin"])
        tramos = [[ini_toma, fin_toma]]
        for sa, sb in sil:
            corte_a, corte_b = sa + cc["pad_fin"], sb - cc["pad_inicio"]
            if sb - sa <= cc["pausa_max"] or corte_b - corte_a < 0.15:
                continue
            x, y = tramos[-1]
            if x < corte_a and corte_b < y:
                tramos[-1] = [x, corte_a]
                tramos.append([corte_b, y])
        if cc.get("modo") == "dinamico":
            tramos = recorte_dinamico(tramos, envolvente(pathlib.Path(medio(clip)["ruta"])), cc, conservar.get(clip, []))
            # control: ninguna palabra del guion puede dejar voz afuera. Se mira la energía dentro del intervalo
            # de Whisper (que a veces estira una palabra sobre el silencio) con un umbral 10 dB más bajo que el
            # del recorte, para que una sílaba suave tampoco pase
            import numpy as np
            env = np.array(envolvente(pathlib.Path(medio(clip)["ruta"])))
            usados = np.concatenate([env[int(a / VENTANA_ENV):int(b / VENTANA_ENV)] for a, b in tramos])
            umbral = max(np.percentile(usados, 95) + cc.get("umbral_db", -30) - 10, np.percentile(usados, 10) + 6)
            for ci in mapa:
                if ci is None:
                    continue
                k0, k1 = int(pal[ci]["i"] / VENTANA_ENV), int(pal[ci]["f"] / VENTANA_ENV)
                fuera = [k for k in range(k0, k1) if env[k] >= umbral
                         and not any(a <= k * VENTANA_ENV <= b for a, b in tramos)]
                if len(fuera) >= 5:
                    notas.append(f"- ⚠️ Bloque {nb}: la palabra «{pal[ci]['w']}» deja {len(fuera) * 10} ms de voz fuera del corte "
                                 f"dinámico ({fuera[0] * VENTANA_ENV:.2f} s de {clip}).")
        # tramos sin ninguna palabra del guion (respiraciones, ruidos) se descartan
        medios_palabras = [(pal[ci]["i"] + pal[ci]["f"]) / 2 for ci in mapa
                           if ci is not None and pal[ci]["f"] - pal[ci]["i"] >= 0.04]
        tramos = [tr for tr in tramos if any(tr[0] <= m <= tr[1] for m in medios_palabras)] or tramos
        t_bloque = t
        for ini, fin in tramos:
            # duración en cuadros enteros: así los cortes quedan pegados sin cuadros negros
            fin = ini + max(1, round((fin - ini) * fps)) / fps
            aroll.append({"clip": clip, "in": round(ini, 4), "out": round(fin, 4), "t": round(t, 4), "bloque": nb,
                          "foco_x": bloque.get("encuadre", {}).get("foco_x", plan.get("encuadre", {}).get(clip, 0.5)),
                          "foco_y": bloque.get("encuadre", {}).get("foco_y", 0.5),
                          "zoom": bloque.get("encuadre", {}).get("zoom", 1.0),
                          "solo_audio": bool(bloque.get("voz_en_off"))})
            for gi, ci in enumerate(mapa):
                if ci is None:
                    continue
                i0, f0 = pal[ci]["i"], pal[ci]["f"]
                if f0 - i0 < 0.04:                       # sin tiempo fiable: se interpola después
                    continue
                mismos = [k for k, x in enumerate(mapa) if x == ci]
                if len(mismos) > 1:
                    paso = (f0 - i0) / len(mismos)
                    i0, f0 = i0 + paso * mismos.index(gi), i0 + paso * (mismos.index(gi) + 1)
                medio_w = (i0 + f0) / 2
                if ini <= medio_w <= fin:
                    palabras_tl.append({"g": gi, "w": guion[gi], "i": t + max(i0, ini) - ini,
                                        "f": t + min(f0, fin) - ini, "bloque": nb})
            t += fin - ini
        t += bloque.get("pausa_despues", 0.0)
        # palabras del guion sin tiempo (whisper no las reconoció): se interpolan
        bl = sorted([p for p in palabras_tl if p["bloque"] == nb], key=lambda p: p["g"])
        conocidas = {p["g"]: p for p in bl}
        for gi, w in enumerate(guion):
            if gi not in conocidas:
                prev = max((p for p in bl if p["g"] < gi), key=lambda p: p["g"], default=None)
                nxt = min((p for p in bl if p["g"] > gi), key=lambda p: p["g"], default=None)
                i0 = prev["f"] if prev else t_bloque
                f0 = nxt["i"] if nxt else t
                palabras_tl.append({"g": gi, "w": w, "i": i0, "f": max(i0 + 0.05, f0), "bloque": nb})
        palabras_tl.sort(key=lambda p: (p["bloque"], p["g"]))

        def tiempo_de(frase: str, desde_fin=False) -> float:
            objetivo = [normalizar(x) for x in tokens(frase)]
            bp = [p for p in palabras_tl if p["bloque"] == nb]
            for k in range(len(bp) - len(objetivo) + 1):
                if all(similitud(normalizar(bp[k + q]["w"]), objetivo[q]) >= 0.8 for q in range(len(objetivo))):
                    return bp[k + len(objetivo) - 1]["f"] if desde_fin else bp[k]["i"]
            raise ValueError(f"Bloque {nb}: no encuentro «{frase}» en el texto del bloque")

        for br in bloque.get("broll", []):
            ini = tiempo_de(br["desde"]) - 0.1 if br.get("desde") else t_bloque
            if br.get("hasta"):
                fin = tiempo_de(br["hasta"], desde_fin=True) + 0.15
            elif br.get("dur"):
                fin = ini + br["dur"]
            else:
                fin = t
            fin = min(fin, t)
            if br.get("pantalla_dividida"):
                destino = salida / f"pantalla_dividida_B{nb:02}{sufijo}.mov"
                render_pantalla_dividida(br["pantalla_dividida"], round(fin - ini + 2.0, 2), carpeta, destino)
                br = {**br, "clip": str(destino), "in": 0.0}
            m = medio(br["clip"])
            src_in = br.get("in", 0.0)
            if src_in + (fin - ini) > m["duracion"]:
                notas.append(f"- ⚠️ B-roll {br['clip']}: no alcanza el largo, lo recorto.")
                fin = ini + m["duracion"] - src_in
            ini = round(ini * fps) / fps
            fin = ini + max(1, round((fin - ini) * fps)) / fps
            broll.append({"clip": br["clip"], "in": round(src_in, 3), "out": round(src_in + fin - ini, 3),
                          "t": round(ini, 4), "foco_x": br.get("foco_x", 0.5), "foco_y": br.get("foco_y", 0.5), "zoom": br.get("zoom", 1.0),
                          "bloque": nb})
        if bloque.get("voz_en_off"):
            # sin presentadora en cámara: los inserts se estiran para cubrir todo el bloque, sin huecos
            del_bloque = sorted((b for b in broll if b["bloque"] == nb), key=lambda b: b["t"])
            for k, b in enumerate(del_bloque):
                cuadro = lambda v: round(round(v * fps) / fps, 6)   # bordes exactos en la grilla de cuadros
                ini_b = cuadro(t_bloque if k == 0 else b["t"])
                fin_b = cuadro(del_bloque[k + 1]["t"] if k + 1 < len(del_bloque) else t)
                src_dur = medio(b["clip"])["duracion"]
                b["in"] = round(max(0.0, min(b["in"], src_dur - (fin_b - ini_b))), 3)
                if b["in"] + (fin_b - ini_b) > src_dur:
                    notas.append(f"- ⚠️ Bloque {nb}: {b['clip']} es más corto que el tramo a cubrir.")
                b["t"], b["out"] = ini_b, round(b["in"] + fin_b - ini_b, 6)
            if not del_bloque:
                notas.append(f"- ⚠️ Bloque {nb}: es voz en off y no tiene inserts (quedaría negro).")
        for ti in bloque.get("titulos", []):
            ini = tiempo_de(ti["en"]) if ti.get("en") else t_bloque
            dur = ti.get("dur", CONFIG["titulos"]["duracion"])
            y_t = ti.get("y", plan.get("titulos_y"))
            titulos.append({"t": round(ini, 3), "dur": dur, "lineas": ti["lineas"], **maquetar_titulo(ti["lineas"], y_t)})
        # ---- estilo v2: títulos por línea, pastilla, zooms y transición Pan Left
        def tramo(g):
            ini = tiempo_de(g["en"]) if g.get("en") else t_bloque
            if g.get("hasta") == "fin":
                fin = t
            elif g.get("hasta"):
                fin = tiempo_de(g["hasta"], desde_fin=True) + 0.15
            else:
                fin = ini + g.get("dur", CONFIG["titulos_v2"]["duracion"])
            return round(round(ini * fps) / fps, 4), round(round(min(fin, t) * fps) / fps, 4)

        for g in bloque.get("graficos", []):
            ini, fin = tramo(g)
            # fondo cargado (wiki › títulos): "sombra" o "desenfoque"; el panel de Premiere lo ignora
            extra = {"fondo_cargado": g["fondo_cargado"]} if g.get("fondo_cargado") else {}
            if g.get("pastilla"):
                cp = CONFIG["pastilla_v2"]
                # la pastilla entra y sale una sola vez y se mantiene (pedido del 30/10): si el plan la repite
                # enseguida con el mismo texto (p. ej. la reutilizada del cierre), sigue la primera
                prev = next((x for x in reversed(graficos) if x["tipo"] == "pastilla"), None)
                if prev and prev["texto"] == numeros_en_cifras(g["pastilla"]).upper() and ini - prev["fin"] <= 1.0:
                    notas.append(f"- Pastilla {prev['texto']}: la del plan en {ini:.2f} s sigue la anterior (entra una sola vez).")
                    prev["fin"] = max(prev["fin"], fin)
                    continue
                graficos.append({"tipo": "pastilla", "t": ini, "fin": fin, "texto": numeros_en_cifras(g["pastilla"]).upper(),
                                 "escala": g.get("escala", cp["escala"]), "pos": g.get("pos", cp["pos"]), "bloque": nb, **extra})
                continue
            # un gráfico va siempre en dos líneas justificadas (paquetito): ni una línea de varias palabras ni
            # una palabra sola (pedidos del 30/10: "ANALIZADOR / FACIAL", "PROTECTOR / SOLAR", "REPORTE / POR QR")
            lineas = [numeros_en_cifras(x) for x in g["lineas"]]
            if len(lineas) == 1 and len(lineas[0].split()) >= 2:
                lineas = lineas[0].split(maxsplit=1)
            elif len(lineas) == 1:
                notas.append(f"- ⚠️ Gráfico «{lineas[0]}» de una sola palabra: siempre van dos, en dos líneas (agregar la segunda en el plan).")
            for n, capa in enumerate(maquetar_titulo_v2(lineas, g.get("y"))):
                graficos.append({"tipo": "titulo", "t": round(ini + n * CONFIG["titulos_v2"]["escalon"], 4), "fin": fin,
                                 **capa, "bloque": nb, **extra})
        for z in bloque.get("zooms", []):
            ini, fin = tramo({**z, "hasta": z.get("hasta", "fin")})
            zooms.append({**z, "t": ini, "fin": fin})
        if bloque.get("pan_left") and nb > 1:
            transiciones.append({"t": round(t_bloque, 4), "tipo": "Pan Left"})
        if bloque.get("light_leak_al_final") and nb < len(plan["bloques"]):
            leaks.append({"t": round(t - CONFIG["light_leak"]["duracion"] / 2, 3), "archivo": bloque["light_leak_al_final"]})

    # cola final (Juli 30/10): 1-2 s de la presentadora mirando a cámara para no cerrar de golpe.
    # Sale de la misma toma, hasta que vuelve a hablar o se termina el archivo. Las piezas "solo hook"
    # no llevan: ahí se pega el body a mano
    if not plan.get("solo_hook") and aroll:
        ult = aroll[-1]
        if ult["solo_audio"]:
            notas.append("- ⚠️ El video termina en voz en off: sin cola a cámara.")
        else:
            habla = next((sb for sa, sb in sil_por_clip[ult["clip"]] if sa <= ult["out"] < sb), ult["out"])
            disponible = min(habla - 0.1, medio(ult["clip"])["duracion"]) - ult["out"]
            cola = round(max(0.0, min(cc["cola_final"], disponible)) * fps) / fps
            if cola < cc["cola_minima"]:
                notas.append(f"- ⚠️ La toma final ({ult['clip']}) solo tiene {cola:.1f} s a cámara después de la última palabra.")
            ult["out"] = round(ult["out"] + cola, 4)
            t = max(t, ult["t"] + ult["out"] - ult["in"])

    duracion = t
    if plan.get("solo_hook") and plan["bloques"][0].get("pan_left_al_final", True):
        transiciones.append({"t": round(t, 4), "tipo": "Pan Left"})   # corte hook → body pegado a mano
    if plan.get("ritmo"):
        zooms, saltos = ritmo_automatico(plan["ritmo"], aroll, broll, palabras_tl, zooms, duracion, medio, fps, notas)
    partir = (plan.get("ritmo") or {}).get("broll_max_s")
    if CONFIG.get("broll_estable") and broll:
        broll_sin_sacudidas(broll, medio, notas, salida / "_claves",
                            plan["ritmo"].get("broll_plano_s", 3.5) if partir else None)
    if partir:
        partir_broll_largo(plan["ritmo"], broll, palabras_tl, graficos, transiciones, medio, fps, notas, salida / "_claves")
    aroll = aplicar_zooms(aroll, zooms, medio, plan.get("caras", {}), fps)

    # ---- subtítulos: bloques de 2-3 palabras, una sola línea
    cs = CONFIG["subtitulos"]
    # nombres de equipos/marcas que no se cortan entre dos subtítulos ("Derma Scan")
    ordenadas = sorted(palabras_tl, key=lambda p: p["i"])
    unidas: list[dict] = []
    k = 0
    while k < len(ordenadas):
        for termino in cs.get("no_separar", []):
            partes = [normalizar(x) for x in termino.split()]
            grupo = ordenadas[k:k + len(partes)]
            if len(grupo) == len(partes) and [normalizar(x["w"]) for x in grupo] == partes:
                unidas.append({**grupo[0], "w": " ".join(x["w"] for x in grupo), "f": grupo[-1]["f"]})
                k += len(partes)
                break
        else:
            unidas.append(ordenadas[k])
            k += 1
    # sobre B-roll van con fondo (máx. 18 caracteres, Juli 30/10); a cámara, con sombreado. Un
    # subtítulo nunca mezcla los dos: cambia de estilo en el corte
    for p in unidas:
        medio_p = (p["i"] + p["f"]) / 2
        p["fondo"] = any(b["t"] <= medio_p <= b["t"] + (b["out"] - b["in"]) for b in broll)
    limite = lambda fondo: cs["caracteres_max_fondo"] if fondo else cs["caracteres_max"]
    chunks: list[list[dict]] = []
    for p in unidas:
        cur = chunks[-1] if chunks else None
        texto_cur = " ".join(x["w"] for x in cur) if cur else ""
        corta = cur is None or len(cur) >= cs["palabras_max"] or len(texto_cur) + 1 + len(p["w"]) > limite(cur[0]["fondo"]) \
            or p["fondo"] != cur[-1]["fondo"] or p["bloque"] != cur[-1]["bloque"] or re.search(r"[.,;:?!]$", cur[-1]["w"]) \
            or p["i"] - cur[-1]["f"] > 0.5
        if corta:
            chunks.append([p])
        else:
            cur.append(p)
    # sin palabras sueltas: un bloque de una sola palabra se une al siguiente (o al anterior)
    # mientras siga entrando en una línea (los de fondo nunca pasan el máximo) y sin pasar de 2 o 3
    # palabras (guía de gráficos: "una sola línea de 2 o 3 palabras"; "Derma Scan" cuenta como una)
    tope = lambda fondo: cs["caracteres_max_fondo"] if fondo else cs["caracteres_max"] + 8
    largo = lambda ch: len(" ".join(x["w"] for x in ch))
    entra = lambda ch: largo(ch) <= tope(ch[0]["fondo"]) and len(ch) <= cs["palabras_max"]
    k = 0
    while k < len(chunks):
        ch = chunks[k]
        if len(ch) == 1 and len(chunks) > 1:
            sig = chunks[k + 1] if k + 1 < len(chunks) else None
            ant = chunks[k - 1] if k > 0 else None
            if sig and sig[0]["bloque"] == ch[0]["bloque"] and sig[0]["fondo"] == ch[0]["fondo"] \
                    and entra(ch + sig) and not re.search(r"[.?!]$", ch[-1]["w"]):
                chunks[k + 1] = ch + sig
                del chunks[k]
                continue
            if ant and ant[-1]["bloque"] == ch[0]["bloque"] and ant[-1]["fondo"] == ch[0]["fondo"] \
                    and entra(ant + ch):
                ant.extend(ch)
                del chunks[k]
                continue
        k += 1
    subs = []
    for k, ch in enumerate(chunks):
        ini, fin = ch[0]["i"], ch[-1]["f"]
        if k + 1 < len(chunks) and chunks[k + 1][0]["i"] - fin < cs["unir_huecos_menores_a"]:
            fin = chunks[k + 1][0]["i"]
        fin = max(fin, ini + cs["duracion_min"])
        texto = " ".join(x["w"] for x in ch).rstrip(".,;:")
        subs.append({"i": round(ini, 3), "f": round(fin, 3), "texto": texto, "tipo": "broll" if ch[0]["fondo"] else "camara"})
        if ch[0]["fondo"] and len(texto) > cs["caracteres_max_fondo"]:
            notas.append(f"- ⚠️ Subtítulo con fondo de {len(texto)} caracteres (máx. {cs['caracteres_max_fondo']}): «{texto}»")

    for tipo in ("camara", "broll"):
        lineas = []
        for n, s in enumerate((s for s in subs if s["tipo"] == tipo), 1):
            lineas += [str(n), f"{srt_tiempo(s['i'])} --> {srt_tiempo(s['f'])}", s["texto"], ""]
        (salida / f"subs_{tipo}{sufijo}.srt").write_text("\n".join(lineas), encoding="utf-8")

    # ---- audio (Juli 30/10): voz pareja apuntando a -14 LUFS y música de colchón por debajo.
    # Todos los bloques van al MISMO nivel; si las tomas vienen tan bajas que el Volumen de Premiere
    # (+15 dB como máximo) no llega a -14, el nivel común es el que alcanza el bloque más bajo y los
    # -14 LUFS / -1 dBTP finales los da la normalización de sonoridad del export
    ca = CONFIG["audio"]
    energia, segs = {}, {}
    for a in aroll:
        lufs, _ = loudness(pathlib.Path(medio(a["clip"])["ruta"]), a["in"], a["out"])
        d, b = a["out"] - a["in"], a["bloque"]
        if math.isfinite(lufs):
            energia[b] = energia.get(b, 0.0) + d * 10 ** (lufs / 10)
            segs[b] = segs.get(b, 0.0) + d
    lufs_bloque = {b: 10 * math.log10(energia[b] / segs[b]) for b in segs}
    voz_lufs = min([ca["voz_lufs"]] + [l + ca["voz_ganancia_max_db"] for l in lufs_bloque.values()])
    for a in aroll:
        lufs = lufs_bloque.get(a["bloque"], voz_lufs)
        a["lufs"] = round(lufs, 1)
        a["ganancia_db"] = round(voz_lufs - lufs, 1)
    if voz_lufs < ca["voz_lufs"] - 0.5:
        notas.append(f"- Voz pareja a {voz_lufs:.1f} LUFS (las tomas vienen bajas): exportar con normalización "
                     f"de sonoridad a {ca['voz_lufs']} LUFS y {ca['true_peak_db']} dBTP.")

    leak_dir = pathlib.Path(CONFIG["recursos"]["carpeta_light_leaks"])
    for lk in leaks:
        lk["ruta"] = str(leak_con_alfa(leak_dir / lk["archivo"]))
        lk["sfx"] = str(leak_dir / "Sound FX" / plan.get("sfx_light", "CINEMATIC LIGHT SOUND FX - 01.mp3"))
        medios[lk["ruta"]] = {"ruta": lk["ruta"], **ffprobe(pathlib.Path(lk["ruta"]))}

    musica, musica_db = plan.get("musica"), None
    if musica and not pathlib.Path(musica).is_absolute():
        musica = str(RAIZ / musica)
    if musica:
        medios[musica] = {"ruta": musica, **ffprobe(pathlib.Path(musica))}
        # la música queda "musica_bajo_voz_db" por debajo de la voz: solo de fondo
        musica_db = round(min(15.0, voz_lufs - ca["musica_bajo_voz_db"] - loudness(pathlib.Path(musica))[0]), 1)

    armado = {
        "nombre": plan["nombre"],
        "bandeja": plan.get("bandeja", plan["nombre"]),
        "secuencia": CONFIG["secuencia"],
        "duracion": round(duracion, 3),
        "medios": medios,
        "aroll": aroll,
        "broll": broll,
        "titulos": titulos,
        "graficos": graficos,
        "transiciones": transiciones,
        "estilo_v2": CONFIG["estilo_v2"] if plan.get("estilo") == "v2" else None,
        "solo_hook": plan.get("solo_hook", False),
        "light_leaks": leaks,
        "musica": {"ruta": musica, "db": musica_db} if musica else None,
        "audio": ca,
        "recursos": CONFIG["recursos"],
        "violeta": CONFIG["violeta"],
        "mogrt_comp": CONFIG["titulos"]["mogrt_comp"],
        "subtitulos": {"camara": str(salida / f"subs_camara{sufijo}.srt"), "broll": str(salida / f"subs_broll{sufijo}.srt")},
        "subs": subs,
    }
    (salida / f"armado{sufijo}.json").write_text(json.dumps(armado, ensure_ascii=False, indent=1), encoding="utf-8")
    (salida / f"corte_fcp{sufijo}.xml").write_text(fcp_xml(armado), encoding="utf-8")

    notas += ["", f"Duración: {duracion:.1f} s · {len(aroll)} cortes de A-roll · {len(broll)} B-roll · "
              f"{len(titulos)} títulos · {len(leaks)} light leaks · {len(subs)} subtítulos", ""]
    notas.append("## Corte")
    for a in aroll:
        notas.append(f"- {a['t']:6.2f}s  {a['clip']} [{a['in']:.2f}–{a['out']:.2f}]  {a['lufs']:.1f} LUFS → ganancia {a['ganancia_db']:+.1f} dB")
    if musica:
        notas.append(f"- Música {pathlib.Path(musica).name}: {musica_db:+.1f} dB ({ca['musica_bajo_voz_db']} dB por debajo de la voz)")
    for b in broll:
        notas.append(f"- {b['t']:6.2f}s  B-roll {b['clip']} [{b['in']:.2f}–{b['out']:.2f}]")
    notas.append("\n## Títulos")
    for ti in titulos:
        notas.append(f"- {ti['t']:6.2f}s  " + " / ".join(" ".join(r['t'] for r in l) for l in ti["lineas"]))
    for g in graficos:
        notas.append(f"- {g['t']:6.2f}–{g['fin']:.2f}s  {g['tipo']}: {g['texto']}  (escala {g['escala']}, posición {g['pos'][0]:.0f} / {g['pos'][1]:.0f})")
    if transiciones:
        notas.append("\n## Transiciones")
        notas += [f"- {tr['t']:6.2f}s  {tr['tipo']}" for tr in transiciones]
    zoom_txt = [f"- {a['t']:6.2f}s  {a['clip']}  escala {a['escala']}" + (f" → {a['kf'][1]['escala']} (keyframes)" if a.get("kf") else "")
                for a in aroll if a.get("kf") or a.get("escala", 0) > 51]
    if zoom_txt:
        notas.append("\n## Zooms")
        notas += zoom_txt
    (salida / f"notas_revision{sufijo}.md").write_text("\n".join(notas) + "\n", encoding="utf-8")
    print("\n".join(notas))
    return saltos


# --------------------------------------------------------- XML de respaldo

def fcp_xml(a: dict) -> str:
    """Corte en xmeml v4 (Premiere: Archivo > Importar). Incluye A-roll, B-roll,
    light leaks, clicks, SFX y música, y marcadores con el texto de los títulos."""
    fps = a["secuencia"]["fps"]
    W, H = a["secuencia"]["ancho"], a["secuencia"]["alto"]
    fr = lambda s: int(round(s * fps))
    ids = {}

    def file_el(ruta: str) -> str:
        m = a["medios"][ruta] if ruta in a["medios"] else next(v for v in a["medios"].values() if v["ruta"] == ruta)
        if ruta in ids:
            return f'<file id="{ids[ruta]}"/>'
        ids[ruta] = f"file-{len(ids) + 1}"
        url = "file://localhost/" + urllib.parse.quote(m["ruta"].replace("\\", "/"))
        media = ""
        if m["ancho"]:
            media += (f"<video><samplecharacteristics><width>{m['ancho']}</width><height>{m['alto']}</height>"
                      f"</samplecharacteristics></video>")
        if m["audio"]:
            media += "<audio><channelcount>2</channelcount></audio>"
        src_fps = round(m["fps"] or fps)
        return (f'<file id="{ids[ruta]}"><name>{escape(pathlib.Path(m["ruta"]).name)}</name>'
                f"<pathurl>{escape(url)}</pathurl><rate><timebase>{src_fps}</timebase><ntsc>FALSE</ntsc></rate>"
                f"<duration>{int(m['duracion'] * src_fps)}</duration><media>{media}</media></file>")

    def escala(ruta: str, zoom=1.0) -> float:
        m = next(v for v in a["medios"].values() if v["ruta"] == ruta)
        return round(100 * max(W / m["ancho"], H / m["alto"]) * zoom, 2)

    n = [0]

    def clip(ruta, t, i, o, video=True, db=None, extra=""):
        n[0] += 1
        filtros = ""
        if video:
            filtros += (f"<filter><effect><name>Basic Motion</name><effectid>basic</effectid><effectcategory>motion</effectcategory>"
                        f"<effecttype>motion</effecttype><mediatype>video</mediatype><parameter><parameterid>scale</parameterid>"
                        f"<name>Scale</name><value>{escala(ruta)}</value></parameter></effect></filter>")
        if db is not None:
            filtros += (f"<filter><effect><name>Audio Levels</name><effectid>audiolevels</effectid><effectcategory>audiolevels</effectcategory>"
                        f"<effecttype>audiolevels</effecttype><mediatype>audio</mediatype><parameter><parameterid>level</parameterid>"
                        f"<name>Level</name><value>{10 ** (db / 20):.5f}</value></parameter></effect></filter>")
        return (f'<clipitem id="clip-{n[0]}"><name>{escape(pathlib.Path(ruta).name)}</name><enabled>TRUE</enabled>'
                f"<rate><timebase>{fps}</timebase><ntsc>FALSE</ntsc></rate><start>{fr(t)}</start><end>{fr(t) + fr(o - i)}</end>"
                f"<in>{fr(i)}</in><out>{fr(i) + fr(o - i)}</out>{file_el(ruta)}{extra}{filtros}</clipitem>")

    ruta_de = lambda c: a["medios"][c]["ruta"]
    v1 = "".join(clip(ruta_de(x["clip"]), x["t"], x["in"], x["out"]) for x in a["aroll"] if not x.get("solo_audio"))
    v2 = "".join(clip(ruta_de(x["clip"]), x["t"], x["in"], x["out"]) for x in a["broll"])
    v4 = "".join(clip(x["ruta"], x["t"], 0, a["medios"][x["ruta"]]["duracion"],
                      ) for x in a["light_leaks"])
    a1 = "".join(clip(ruta_de(x["clip"]), x["t"], x["in"], x["out"], video=False, db=x["ganancia_db"]) for x in a["aroll"])
    click = a["recursos"]["click"]
    a["medios"].setdefault(click, {"ruta": click, **ffprobe(pathlib.Path(click))})
    a2 = "".join(clip(click, x["t"], 0, a["medios"][click]["duracion"], video=False, db=a["audio"]["click_db"]) for x in a["titulos"])
    a3 = ""
    for x in a["light_leaks"]:
        a["medios"].setdefault(x["sfx"], {"ruta": x["sfx"], **ffprobe(pathlib.Path(x["sfx"]))})
        a3 += clip(x["sfx"], max(0, x["t"] - 0.2), 0, min(2.0, a["medios"][x["sfx"]]["duracion"]), video=False, db=a["audio"]["sfx_light_db"])
    a4 = clip(a["musica"]["ruta"], 0, 0, min(a["duracion"], a["medios"][a["musica"]["ruta"]]["duracion"]),
              video=False, db=a["musica"]["db"]) if a.get("musica") else ""
    marcadores = "".join(
        f"<marker><name>TÍTULO</name><comment>{escape(' / '.join(' '.join(r['t'] for r in l) for l in x['lineas']))}</comment>"
        f"<in>{fr(x['t'])}</in><out>-1</out></marker>" for x in a["titulos"])
    pista = lambda xml: f"<track>{xml}</track>"
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE xmeml>\n<xmeml version="4"><sequence id="seq-1">'
            f"<name>{escape(a['nombre'])} (XML)</name><duration>{fr(a['duracion'])}</duration>"
            f"<rate><timebase>{fps}</timebase><ntsc>FALSE</ntsc></rate>{marcadores}<media>"
            f"<video><format><samplecharacteristics><rate><timebase>{fps}</timebase><ntsc>FALSE</ntsc></rate>"
            f"<width>{W}</width><height>{H}</height><pixelaspectratio>square</pixelaspectratio></samplecharacteristics></format>"
            f"{pista(v1)}{pista(v2)}{pista('')}{pista(v4)}</video>"
            f"<audio>{pista(a1)}{pista(a2)}{pista(a3)}{pista(a4)}</audio></media></sequence></xmeml>\n")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")   # las notas llevan "→" y "⚠": sin esto falla en consolas cp1252
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    armar(pathlib.Path(sys.argv[1]))
