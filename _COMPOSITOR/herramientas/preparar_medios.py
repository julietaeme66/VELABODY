"""Prepara la carpeta pública que lee Remotion a partir de un armado.json de velabody.py.

- Proxies de cada toma: solo el tramo usado (±1 s), con la rotación aplicada (las cámaras graban
  3840x2160 con rotation=90), CFR 30 y H.264 4:2:0 de 8 bits (Chrome no decodifica el XAVC 4:2:2 de
  10 bits original), con el color de la capa Lumetri horneado.
- Color: un LUT 3D que combina el LUT Alexa v3 → Rec709 de Premiere con la exposición y el contraste
  calibrados (config_velabody.json › compositor.color; ver calibrar_color.py, misma fórmula).
- Voz: aparte del video, un WAV por toma y ganancia (la que calculó velabody.py para cada pieza), en mono
  centrada (el Video 1 salió cargado a la izquierda).
- Copia fuentes, click, música y SFX, y escribe medios.json (clip → proxy, inicio, tamaño original).

Los originales no se tocan. Lo ya generado con los mismos parámetros no se rehace.

Uso:
    python preparar_medios.py <armado.json> [<armado.json> ...] <carpeta_publica>
"""
import hashlib
import json
import pathlib
import shutil
import subprocess
import sys

import numpy as np

AQUI = pathlib.Path(__file__).resolve().parent
HERRAMIENTAS = AQUI.parents[1] / "_HERRAMIENTAS"
sys.path.insert(0, str(HERRAMIENTAS))
import velabody  # noqa: E402  (config fusionada con config_local.json y rutas de la compu)

CONFIG = velabody.CONFIG
COMP = CONFIG["compositor"]
FPS = CONFIG["secuencia"]["fps"]
MARGEN_S = 1.0


def leer_cube(ruta: pathlib.Path) -> tuple[int, np.ndarray, list[str]]:
    tam, filas, cabecera = None, [], []
    for linea in ruta.read_text(encoding="utf-8", errors="replace").splitlines():
        s = linea.strip()
        if not s or s.startswith("#"):
            continue
        if s.upper().startswith("LUT_3D_SIZE"):
            tam = int(s.split()[1])
            cabecera.append(s)
        elif s[0].isalpha():
            cabecera.append(s)
        else:
            filas.append([float(v) for v in s.split()[:3]])
    return tam, np.array(filas, np.float64), cabecera


def ajuste(v: np.ndarray, exposicion: float, contraste: float) -> np.ndarray:
    """Igual que calibrar_color.ajuste: exposición sobre la señal linealizada y curva S."""
    lin = np.clip(v, 0, 1) ** 2.4 * 2 ** exposicion
    y = np.clip(lin, 0, 1) ** (1 / 2.4)
    s = y * y * (3 - 2 * y)
    return np.clip(y + contraste * (s - y), 0, 1)


def lut_combinado(cache: pathlib.Path) -> pathlib.Path:
    c = COMP["color"]
    origen = pathlib.Path(CONFIG["recursos"].get("lut_lumetri") or velabody.RAIZ / "_RECURSOS" / c["lut"])
    destino = cache / f"lumetri_velabody_e{c['exposicion_pasos']}_c{c['contraste_s']}.cube"
    if not destino.exists():
        tam, filas, cabecera = leer_cube(origen)
        filas = ajuste(filas, c["exposicion_pasos"], c["contraste_s"])
        lineas = [f"# {origen.name} + exposición {c['exposicion_pasos']} pasos + contraste S {c['contraste_s']} (piloto VELABODY)"]
        lineas += cabecera + [f"{r:.6f} {g:.6f} {b:.6f}" for r, g, b in filas]
        destino.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    return destino


def silencio_inicial(ruta: pathlib.Path, umbral: float = 0.1) -> float:
    """Segundos hasta que el sonido supera el umbral (relativo a su pico)."""
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(ruta), "-ac", "1", "-ar", "48000", "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    x = np.abs(np.frombuffer(raw, np.float32))
    return round(float(np.argmax(x > umbral * x.max())) / 48000, 4)


def ruta_ffmpeg_filtro(p: pathlib.Path) -> str:
    return p.as_posix().replace(":", "\\:")


def al_dia(destino: pathlib.Path, params: dict) -> tuple[bool, pathlib.Path, str]:
    """¿Ya existe con los mismos parámetros? (así no se rehace un proxy entre corridas)."""
    firma = hashlib.sha1(json.dumps(params, sort_keys=True).encode()).hexdigest()[:12]
    marca = destino.with_suffix(destino.suffix + ".json")
    ok = destino.exists() and marca.exists() and json.loads(marca.read_text())["firma"] == firma
    return ok, marca, firma


def proxy(medio: dict, ini: float, fin: float, destino: pathlib.Path, lut: pathlib.Path) -> None:
    """Video sin audio (la voz va aparte, porque cada pieza puede llevar otra ganancia)."""
    pc = COMP["proxy"]
    params = {"version": 3, "ruta": medio["ruta"], "ini": ini, "fin": fin, "lut": lut.name, "proxy": pc}
    ok, marca, firma = al_dia(destino, params)
    if ok:
        return
    vf = (f"scale={pc['ancho']}:{pc['alto']}:flags=lanczos,fps={FPS},format=rgb48le,"
          f"lut3d='{ruta_ffmpeg_filtro(lut)}',scale=out_range=tv,format=yuv420p")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{ini:.3f}", "-to", f"{fin:.3f}", "-i", medio["ruta"], "-vf", vf,
                    "-c:v", "libx264", "-preset", "medium", "-crf", str(pc["crf"]), "-g", "15", "-bf", "0",
                    "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", "-color_range", "tv",
                    "-movflags", "+faststart", "-an", str(destino)], check=True)
    marca.write_text(json.dumps({"firma": firma, **params}, ensure_ascii=False, indent=1), encoding="utf-8")


def voz(medio: dict, ini: float, fin: float, destino: pathlib.Path, ganancia_db: float) -> None:
    """Voz del mismo tramo que el proxy, con la ganancia de velabody.py, en mono centrada."""
    params = {"version": 1, "ruta": medio["ruta"], "ini": ini, "fin": fin, "ganancia": ganancia_db}
    ok, marca, firma = al_dia(destino, params)
    if ok:
        return
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{ini:.3f}", "-to", f"{fin:.3f}", "-i", medio["ruta"], "-vn",
                    "-af", f"pan=mono|c0=0.5*c0+0.5*c1,volume={ganancia_db}dB,aformat=channel_layouts=stereo",
                    "-c:a", "pcm_s16le", "-ar", "48000", str(destino)], check=True)
    marca.write_text(json.dumps({"firma": firma, **params}, ensure_ascii=False, indent=1), encoding="utf-8")


def clave_voz(clip: str, ganancia_db: float) -> str:
    return f"{clip}|{ganancia_db:+.1f}"


def main(armados: list[pathlib.Path], publico: pathlib.Path) -> None:
    """Un solo juego de proxies para todas las piezas (por ejemplo H1, H2 y H3 de un anuncio)."""
    sys.stdout.reconfigure(encoding="utf-8")
    piezas = [json.loads(p.read_text(encoding="utf-8")) for p in armados]
    a = piezas[0]
    cache = velabody.RAIZ / "_COMPOSITOR_CACHE"
    (publico / "medios").mkdir(parents=True, exist_ok=True)
    (publico / "fuentes").mkdir(exist_ok=True)
    (publico / "audio").mkdir(exist_ok=True)
    lut = lut_combinado(cache)

    usos: dict[str, dict] = {}
    for pieza in piezas:
        for capa in ("aroll", "broll"):
            for x in pieza[capa]:
                u = usos.setdefault(x["clip"], {"ini": x["in"], "fin": x["out"], "ganancias": set(), "medio": pieza["medios"][x["clip"]]})
                u["ini"], u["fin"] = min(u["ini"], x["in"]), max(u["fin"], x["out"])
                if capa == "aroll":
                    u["ganancias"].add(x["ganancia_db"])
    manifiesto, voces = {}, {}
    for clip, u in usos.items():
        m = u["medio"]
        ini = max(0.0, round(u["ini"] - MARGEN_S, 3))
        fin = min(m["duracion"], round(u["fin"] + MARGEN_S, 3))
        nombre = pathlib.Path(clip).name
        print(f"proxy {clip} [{ini:.2f}–{fin:.2f}]" + (f" · voz {sorted(u['ganancias'])} dB" if u["ganancias"] else ""))
        proxy(m, ini, fin, publico / "medios" / f"{nombre}.mp4", lut)
        manifiesto[clip] = {"src": f"medios/{nombre}.mp4", "inicio": ini, "fin": fin, "ancho": m["ancho"], "alto": m["alto"]}
        for g in sorted(u["ganancias"]):
            destino = publico / "medios" / f"voz_{nombre}_{g:+.1f}dB.wav"
            voz(m, ini, fin, destino, g)
            voces[clave_voz(clip, g)] = {"src": f"medios/{destino.name}", "inicio": ini}

    fuentes_dir = velabody.RAIZ / "_RECURSOS" / "fuentes"
    for f in {COMP["titulo"]["fuente"], COMP["pastilla"]["fuente"], COMP["subtitulos"]["fondo"]["fuente"],
              COMP["subtitulos"]["camara"]["fuente"]}:
        origen = next((c / f for c in velabody.CARPETAS_FUENTES if (c / f).exists()), None)
        if not origen:
            raise FileNotFoundError(f"Falta la fuente {f} (buscada en {fuentes_dir})")
        shutil.copy2(origen, publico / "fuentes" / f)
    audio = {}
    click = pathlib.Path(a["recursos"]["click"])
    shutil.copy2(click, publico / "audio" / "click.mp3")
    audio["click"] = "audio/click.mp3"
    # Mouse Click.mp3 arranca con ~0,26 s de silencio: si se pone al inicio del gráfico (como hace el
    # builder) suena 8 cuadros tarde. En el aprobado el click se oye justo al entrar el gráfico.
    audio["click_silencio_inicial_s"] = silencio_inicial(click)
    if a.get("musica"):
        musica = pathlib.Path(a["musica"]["ruta"])
        shutil.copy2(musica, publico / "audio" / ("musica" + musica.suffix.lower()))
        audio["musica"] = "audio/musica" + musica.suffix.lower()
    sfx = pathlib.Path(CONFIG["estilo_v2"]["sfx_transicion"])
    if sfx.exists():
        shutil.copy2(sfx, publico / "audio" / ("sfx_transicion" + sfx.suffix.lower()))
        audio["sfx_transicion"] = "audio/sfx_transicion" + sfx.suffix.lower()
    else:
        print(f"⚠ Falta el SFX de transición ({sfx}): el Pan Left queda sin sonido")
    (publico / "medios.json").write_text(json.dumps({"medios": manifiesto, "voces": voces, "audio": audio, "lut": lut.name},
                                                    ensure_ascii=False, indent=1),
                                         encoding="utf-8")
    print(f"medios.json · {len(manifiesto)} proxies · {len(voces)} pistas de voz · LUT {lut.name}")


if __name__ == "__main__":
    main([pathlib.Path(x) for x in sys.argv[1:-1]], pathlib.Path(sys.argv[-1]))
