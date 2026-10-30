"""Adaptador armado.json (velabody.py) → timeline.json (compositor Remotion).

El armado describe la pieza con las convenciones de Premiere; acá se traducen a cuadros y píxeles:

- Tiempos: segundos → cuadros a 30 fps. Cada clip va de round(t·fps) a round((t + out − in)·fps), así
  los tramos contiguos no dejan huecos por redondeo.
- A-roll: "escala" es el % de Movimiento de Premiere sobre el cuadro original ya rotado (2160x3840; la
  escala base de cobertura es 50) y "pos" es dónde queda el centro del clip, en px de la secuencia. La
  caja resultante mide ancho·escala/100 × alto·escala/100 centrada en pos. Los keyframes ("kf") son
  lineales, igual que los que pone el builder.
- B-roll: el armado trae foco_x/foco_y/zoom; se replica encuadrar() de velabody.jsx (cobertura × zoom,
  centrado en el foco y sin dejar bordes).
- Títulos: escala del MOGRT = tamaño de fuente en px (fuente a 100 en el MOGRT); la línea de base queda
  en pos_y + base_rel·escala (medido en el export del Video 1, config titulos_v2).
- Pastilla: escala y pos de Movimiento; la geometría de caja y texto sale de config › compositor.pastilla.
- Subtítulos: cuadros de entrada/salida y estilo (fondo sobre B-roll, cámara a cámara).
- Transiciones Pan Left, clicks (uno por capa de gráfico), música con su fade y voz ya horneada en el proxy.

Valida y falla con un mensaje claro ante lo que el compositor no sabe hacer (light leaks del estilo v1,
campos desconocidos, tramos fuera de la duración de los proxies o capas de video superpuestas).

Uso:
    python adaptar_armado.py <armado.json> <carpeta_publica> [timeline_X.json]   (por defecto, timeline.json)
"""
import json
import pathlib
import sys

from PIL import ImageFont

AQUI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parents[1] / "_HERRAMIENTAS"))
import velabody  # noqa: E402  (config fusionada y carpetas de fuentes de esta compu)

CONFIG = velabody.CONFIG


def ancho_tinta(fuente: str, px: float, texto: str, tracking_em: float) -> float:
    """Ancho visible del texto (tinta, sin márgenes laterales), con el tracking del compositor."""
    f = ImageFont.truetype(str(next(c / fuente for c in velabody.CARPETAS_FUENTES if (c / fuente).exists())), 400)
    x0, _, x1, _ = f.getbbox(texto)
    return (x1 - x0) * px / 400 + tracking_em * px * (len(texto) - 1)

# en el A-roll v2 manda escala/pos (fijarMovimiento en velabody.jsx); foco_x/foco_y/zoom quedan del v1 y se ignoran
CAMPOS_AROLL = {"clip", "in", "out", "t", "bloque", "solo_audio", "escala", "pos", "kf", "lufs", "ganancia_db", "pausa",
                "foco_x", "foco_y", "zoom"}
CAMPOS_BROLL = {"clip", "in", "out", "t", "foco_x", "foco_y", "zoom", "bloque"}
CAMPOS_GRAFICO = {"tipo", "t", "fin", "texto", "escala", "pos", "bloque", "fondo_cargado"}


class ArmadoNoSoportado(ValueError):
    pass


def cuadro(seg: float, fps: int) -> int:
    return int(round(seg * fps))


def tramo(x: dict, fps: int) -> tuple[int, int]:
    return cuadro(x["t"], fps), cuadro(x["t"] + x["out"] - x["in"], fps)


def caja_premiere(ancho: float, alto: float, escala: float, pos: list[float]) -> dict:
    w, h = ancho * escala / 100, alto * escala / 100
    return {"x": round(pos[0] - w / 2, 3), "y": round(pos[1] - h / 2, 3), "w": round(w, 3), "h": round(h, 3)}


def caja_encuadrar(medio: dict, W: int, H: int, foco_x=0.5, zoom=1.0, foco_y=0.5) -> dict:
    """Mismo cálculo que encuadrar() en velabody.jsx."""
    esc = max(W / medio["ancho"], H / medio["alto"]) * (zoom or 1)
    w, h = medio["ancho"] * esc, medio["alto"] * esc
    cx = W / 2 + (0.5 - foco_x) * w
    cx = max(W / 2 - (w - W) / 2, min(W / 2 + (w - W) / 2, cx))
    cy = H / 2 + (0.5 - foco_y) * h
    cy = max(H / 2 - (h - H) / 2, min(H / 2 + (h - H) / 2, cy))
    return {"x": round(cx - w / 2, 3), "y": round(cy - h / 2, 3), "w": round(w, 3), "h": round(h, 3)}


def desconocidos(x: dict, permitidos: set, que: str) -> None:
    extra = set(x) - permitidos
    if extra:
        raise ArmadoNoSoportado(f"{que}: campos que el compositor no sabe interpretar: {sorted(extra)}")


def adaptar(a: dict, medios: dict) -> dict:
    fps, W, H = a["secuencia"]["fps"], a["secuencia"]["ancho"], a["secuencia"]["alto"]
    if fps != 30 or (W, H) != (1080, 1920):
        raise ArmadoNoSoportado(f"Secuencia {W}x{H} a {fps} fps: el piloto solo arma 1080x1920 a 30 fps")
    if a.get("light_leaks"):
        raise ArmadoNoSoportado("El armado trae light leaks (estilo v1): la wiki los reemplazó por Pan Left")
    if a.get("titulos"):
        raise ArmadoNoSoportado("El armado trae títulos del estilo v1 ('titulos'); usar 'graficos' (plan con estilo v2)")
    if not a.get("estilo_v2"):
        raise ArmadoNoSoportado("El plan no es estilo v2")
    total = cuadro(a["duracion"], fps)
    tv = CONFIG["titulos_v2"]
    comp = CONFIG["compositor"]

    def fuente_de(x: dict, que: str) -> dict:
        m = medios["medios"].get(x["clip"])
        if not m:
            raise ArmadoNoSoportado(f"{que}: no hay proxy para {x['clip']} (correr preparar_medios.py)")
        if x["in"] < m["inicio"] - 1e-3 or x["out"] > m["fin"] + 1e-3:
            raise ArmadoNoSoportado(f"{que}: {x['clip']} [{x['in']}–{x['out']}] queda fuera del proxy [{m['inicio']}–{m['fin']}]")
        return m

    videos, voces = [], []
    for k, x in enumerate(a["aroll"]):
        desconocidos(x, CAMPOS_AROLL, f"A-roll {k}")
        m = fuente_de(x, f"A-roll {k}")
        desde, hasta = tramo(x, fps)
        trim = cuadro(x["in"] - m["inicio"], fps)
        if not x.get("solo_audio"):
            v = {"capa": "aroll", "clip": x["clip"], "src": m["src"], "desde": desde, "dur": hasta - desde, "trim": trim}
            if x.get("kf"):
                v["kf"] = [{"cuadro": cuadro(kf["t"], fps), **caja_premiere(m["ancho"], m["alto"], kf["escala"], kf["pos"])}
                           for kf in x["kf"]]
            else:
                v["caja"] = caja_premiere(m["ancho"], m["alto"], x["escala"], x["pos"])
            videos.append(v)
        # la voz va en su propia pista (WAV del mismo tramo que el proxy, con la ganancia de esta pieza)
        vz = medios["voces"].get(f"{x['clip']}|{x['ganancia_db']:+.1f}")
        if not vz:
            raise ArmadoNoSoportado(f"A-roll {k}: falta la voz de {x['clip']} a {x['ganancia_db']:+.1f} dB (correr preparar_medios.py)")
        voces.append({"src": vz["src"], "desde": desde, "dur": hasta - desde, "trim": cuadro(x["in"] - vz["inicio"], fps)})
    for k, x in enumerate(a["broll"]):
        desconocidos(x, CAMPOS_BROLL, f"B-roll {k}")
        m = fuente_de(x, f"B-roll {k}")
        desde, hasta = tramo(x, fps)
        videos.append({"capa": "broll", "clip": x["clip"], "src": m["src"], "desde": desde, "dur": hasta - desde,
                       "trim": cuadro(x["in"] - m["inicio"], fps),
                       "caja": caja_encuadrar(m, W, H, x.get("foco_x", 0.5), x.get("zoom", 1.0), x.get("foco_y", 0.5))})
    # B-roll: en Premiere va todo en una pista con overwriteClip, así que un inserto pisa la cola del que
    # se puso antes (velabody.py alarga cada uno 0,15 s y adelanta el siguiente 0,1 s). Se replica eso.
    brolls = [v for v in videos if v["capa"] == "broll"]
    ajustes = []
    for k, v in enumerate(brolls):
        for w in brolls[k + 1:]:
            if v["desde"] < w["desde"] < v["desde"] + v["dur"]:
                ajustes.append(f"{v['clip']} pierde {v['desde'] + v['dur'] - w['desde']} cuadros (lo pisa {w['clip']})")
                v["dur"] = w["desde"] - v["desde"]
    # A-roll: una sola capa continua, sin superposiciones
    tramos = sorted((v["desde"], v["desde"] + v["dur"], v["clip"]) for v in videos if v["capa"] == "aroll")
    for (a0, a1, c0), (b0, b1, c1) in zip(tramos, tramos[1:]):
        if b0 < a1:
            raise ArmadoNoSoportado(f"aroll: {c0} y {c1} se superponen (cuadros {b0}–{a1})")
    for t in ajustes:
        print(f"  B-roll: {t}")
    for v in videos:
        if v["desde"] + v["dur"] > total + 1:
            raise ArmadoNoSoportado(f"{v['clip']} termina después del final de la pieza")

    graficos = []
    for k, g in enumerate(a["graficos"]):
        desconocidos(g, CAMPOS_GRAFICO, f"Gráfico {k}")
        desde, hasta = cuadro(g["t"], fps), cuadro(g["fin"], fps)
        if g["tipo"] == "titulo":
            graficos.append({"tipo": "titulo", "texto": g["texto"], "desde": desde, "hasta": hasta,
                             "fontPx": g["escala"], "x": g["pos"][0],
                             "base": round(g["pos"][1] + tv["base_rel"] * g["escala"], 2)})
        elif g["tipo"] == "pastilla":
            cp = comp["pastilla"]
            alto = cp["alto_caja_por_escala"] * g["escala"]
            px = cp["fuente_px_por_escala"] * g["escala"]
            ancho = ancho_tinta(cp["fuente"], px, g["texto"], cp["tracking_em"]) + 2 * cp["margen_x_por_alto_caja"] * alto
            graficos.append({"tipo": "pastilla", "texto": g["texto"], "desde": desde, "hasta": hasta, "escala": g["escala"],
                             "cx": g["pos"][0], "cy": g["pos"][1], "fontPx": round(px, 2), "w": round(ancho, 2), "h": round(alto, 2)})
        else:
            raise ArmadoNoSoportado(f"Gráfico {k}: tipo {g['tipo']!r} desconocido")
        if g.get("fondo_cargado"):
            if g["fondo_cargado"] != "sombra":
                raise ArmadoNoSoportado(f"Gráfico {k}: fondo_cargado {g['fondo_cargado']!r} todavía no está hecho (solo 'sombra')")
            graficos[-1]["sombra"] = True

    cs = comp["subtitulos"]
    subtitulos = []
    for s in a["subs"]:
        estilo = "fondo" if s["tipo"] == "broll" else "camara"
        e = cs[estilo]
        sub = {"texto": s["texto"], "desde": cuadro(s["i"], fps), "hasta": cuadro(s["f"], fps), "estilo": estilo}
        if estilo == "fondo":
            sub["w"] = round(ancho_tinta(e["fuente"], e["px"], s["texto"], e["tracking_em"]) + 2 * e["margen_x"], 2)
        subtitulos.append(sub)
    transiciones = []
    for tr in a.get("transiciones", []):
        if tr["tipo"] != "Pan Left":
            raise ArmadoNoSoportado(f"Transición {tr['tipo']!r} desconocida")
        transiciones.append({"tipo": "panLeft", "cuadro": cuadro(tr["t"], fps)})

    db = lambda v: round(10 ** (v / 20), 5)
    audio = []
    silencio = cuadro(medios["audio"].get("click_silencio_inicial_s", 0), fps)
    for g in graficos:      # el click suena al arrancar la entrada del gráfico (se saltea el silencio del mp3)
        audio.append({"src": medios["audio"]["click"], "desde": g["desde"], "trim": silencio, "volumen": db(a["audio"]["click_db"])})
    if medios["audio"].get("sfx_transicion"):
        e2 = a["estilo_v2"]
        for tr in transiciones:
            audio.append({"src": medios["audio"]["sfx_transicion"], "desde": max(0, tr["cuadro"] - cuadro(e2["sfx_adelanto"], fps)),
                          "volumen": db(e2["sfx_transicion_db"])})
    if a.get("musica"):
        fade = 0 if a.get("solo_hook") else cuadro(a["estilo_v2"]["musica_fade"], fps)
        audio.append({"src": medios["audio"]["musica"], "desde": 0, "dur": total, "volumen": db(a["musica"]["db"]),
                      "fadeFinal": fade})
    return {"version": 1, "nombre": a["nombre"], "fps": fps, "ancho": W, "alto": H, "duracion": total,
            "videos": videos, "voces": voces, "graficos": graficos, "subtitulos": subtitulos,
            "transiciones": transiciones, "audio": audio, "sandwich": []}


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    armado, publico = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
    nombre = sys.argv[3] if len(sys.argv) > 3 else "timeline.json"     # una por pieza: timeline_H1.json…
    medios = json.loads((publico / "medios.json").read_text(encoding="utf-8"))
    tl = adaptar(json.loads(armado.read_text(encoding="utf-8")), medios)
    (publico / nombre).write_text(json.dumps(tl, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{nombre} · {tl['duracion']} cuadros · {len(tl['videos'])} videos · {len(tl['graficos'])} gráficos · "
          f"{len(tl['subtitulos'])} subtítulos · {len(tl['transiciones'])} transiciones · {len(tl['sandwich'])} sándwich")


if __name__ == "__main__":
    main()
