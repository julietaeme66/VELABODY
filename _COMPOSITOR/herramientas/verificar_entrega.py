"""Verifica un MP4 del compositor contra su timeline.json (lo que se mide es el archivo exportado).

- Gráficos: primer cuadro con violeta visible en la zona de cada gráfico.
- Clicks: dónde arranca cada click en el audio final (filtro adaptado con el propio Mouse Click.mp3)
  y su distancia, en cuadros, al primer cuadro visible del gráfico.
- Cortes de A-roll entre tomas distintas: nivel del audio final alrededor del corte comparado con la voz
  (un corte en mitad de una palabra deja energía alta justo en el corte).
- Música: nivel en el arranque, antes de la primera palabra, frente al nivel de la voz.
- Color de la cadena Remotion: ΔE2000 entre un cuadro del render y el mismo cuadro del proxy.
- Márgenes: caja de cada gráfico y subtítulo contra la zona segura de IG (aprox.; sin el PNG oficial).

Uso:
    python verificar_entrega.py <video.mp4> <carpeta_publica> <salida.json> [timeline_X.json]
"""
import json
import pathlib
import subprocess
import sys

import cv2
import numpy as np

AQUI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
from calibrar_color import ciede2000  # noqa: E402
from medir_referencia import bandas_violeta, cuadros  # noqa: E402

SR = 48000
# zona segura de Reels aproximada (sin el PNG de la clienta): 250 px arriba, 420 abajo, 60 a los costados
ZONA = {"x0": 60, "x1": 1020, "y0": 250, "y1": 1500}


def audio(path: pathlib.Path, pasaaltos: bool = False) -> np.ndarray:
    """Mono a 48 kHz. Con pasaaltos (5 kHz) queda casi solo el click: la voz y la música casi no llegan ahí."""
    af = ["-af", "highpass=f=5000,highpass=f=5000"] if pasaaltos else []
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-vn", "-ac", "1", "-ar", str(SR), *af, "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32)


def rms_db(x: np.ndarray) -> float:
    return float(20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-9))


def lab(rgb: np.ndarray) -> np.ndarray:
    return cv2.cvtColor((rgb / 255).astype(np.float32), cv2.COLOR_RGB2Lab).reshape(-1, 3)


def cuadro_rgb(path: pathlib.Path, t: float, w=1080, h=1920) -> np.ndarray:
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.4f}", "-i", str(path), "-frames:v", "1", "-vf", f"scale={w}:{h}",
                          "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(h, w, 3).astype(np.float32)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    video, publico, salida = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]), pathlib.Path(sys.argv[3])
    tl = json.loads((publico / (sys.argv[4] if len(sys.argv) > 4 else "timeline.json")).read_text(encoding="utf-8"))
    fps = tl["fps"]
    inf: dict = {"video": str(video)}

    # gráficos: primer cuadro visible
    visibles = []
    for g in tl["graficos"]:
        y_ref = g["cy"] if g["tipo"] == "pastilla" else g["base"] - 0.35 * g["fontPx"]
        primero = None
        for k, img in cuadros(video, g["desde"] / fps, (g["desde"] + 12) / fps):
            if any(b["caja"][1] - 30 <= y_ref <= b["caja"][3] + 30 for b in bandas_violeta(img, 40)):
                primero = g["desde"] + k
                break
        visibles.append(primero)

    # clicks
    a = audio(video)
    a_hp = audio(video, pasaaltos=True)
    click = audio(publico / "audio" / "click.mp3", pasaaltos=True)
    arranque = int(np.argmax(np.abs(click) > 0.2 * np.abs(click).max()))   # el mp3 trae silencio al principio
    click = click[arranque: arranque + int(0.03 * SR)]
    inf["click_silencio_inicial_s"] = round(arranque / SR, 3)
    filas = []
    for g, vis in zip(tl["graficos"], visibles):
        c0 = max(0, int((g["desde"] / fps - 0.3) * SR))
        tramo = a_hp[c0: c0 + int(0.6 * SR)]
        corr = np.correlate(tramo, click, mode="valid") / (np.linalg.norm(click) * (np.sqrt(np.convolve(tramo ** 2, np.ones(len(click)), "valid")) + 1e-9))
        t_click = (c0 + int(np.nanargmax(corr))) / SR
        filas.append({"grafico": g["texto"], "cuadro_inicio": g["desde"], "primer_cuadro_visible": vis,
                      "click_s": round(t_click, 3), "click_cuadro": round(t_click * fps, 2), "correlacion": round(float(np.nanmax(corr)), 3),
                      "click_menos_visible_cuadros": None if vis is None else round(t_click * fps - vis, 2)})
    inf["graficos_y_clicks"] = filas

    # cortes entre tomas distintas
    voz = [v for v in tl["videos"] if v["capa"] == "aroll"]
    nivel_voz = rms_db(a[int(voz[0]["desde"] / fps * SR): int((voz[-1]["desde"] + voz[-1]["dur"]) / fps * SR)])
    cortes = []
    for v0, v1 in zip(voz, voz[1:]):
        if v0["clip"] == v1["clip"] and v0["trim"] + v0["dur"] == v1["trim"]:
            continue      # misma toma, continua (solo se partió por el zoom)
        c = v1["desde"] / fps
        cortes.append({"cuadro": v1["desde"], "de": v0["clip"], "a": v1["clip"],
                       "rms_60ms_antes_db": round(rms_db(a[int((c - 0.06) * SR): int(c * SR)]), 1),
                       "rms_60ms_despues_db": round(rms_db(a[int(c * SR): int((c + 0.06) * SR)]), 1),
                       "voz_media_db": round(nivel_voz, 1)})
    inf["cortes"] = cortes

    # música sola al arranque (antes de la primera palabra) frente a la voz
    primera = min(s["desde"] for s in tl["subtitulos"]) / fps
    inf["musica_vs_voz"] = {"rms_antes_primera_palabra_db": round(rms_db(a[: int(max(0.1, primera - 0.15) * SR)]), 1),
                            "rms_voz_media_db": round(nivel_voz, 1),
                            "nota": "el tramo inicial incluye el ruido de sala de la toma, así que es un techo para la música"}

    # color de la cadena: render vs proxy, en el medio del primer B-roll
    b = next(v for v in tl["videos"] if v["capa"] == "broll")
    f = b["desde"] + b["dur"] // 2
    render = cuadro_rgb(video, (f + 0.5) / fps)
    mascara = np.ones((1920, 1080), bool)
    mascara[1080:1300] = False      # fuera la franja de subtítulos
    # se prueba el cuadro del proxy esperado y sus vecinos (la toma se mueve: un cuadro de más pesa mucho)
    mejores = []
    for dk in (-1, 0, 1):
        proxy = cuadro_rgb(publico / b["src"], (b["trim"] + f - b["desde"] + dk + 0.5) / fps)
        d = ciede2000(lab(render)[mascara.ravel()], lab(proxy)[mascara.ravel()])
        mejores.append((float(d.mean()), float(np.percentile(d, 95)), dk))
    m, p95, dk = min(mejores)
    inf["color_cadena_remotion"] = {"cuadro": f, "desfase_cuadros": dk, "dE2000_medio": round(m, 2), "dE2000_p95": round(p95, 2),
                                    "por_desfase": [{"desfase": x[2], "dE2000_medio": round(x[0], 2)} for x in mejores]}

    # márgenes
    fuera = []
    for g in tl["graficos"]:
        if g["tipo"] == "pastilla":
            caja = [g["cx"] - g["w"] / 2, g["cy"] - g["h"] / 2, g["cx"] + g["w"] / 2, g["cy"] + g["h"] / 2]
        else:
            caja = [g["x"] - 426, g["base"] - 0.7 * g["fontPx"], g["x"] + 426, g["base"]]
        if caja[0] < ZONA["x0"] or caja[2] > ZONA["x1"] or caja[1] < ZONA["y0"] or caja[3] > ZONA["y1"]:
            fuera.append({"grafico": g["texto"], "caja": caja})
    inf["zona_segura_aprox"] = {"zona": ZONA, "fuera": fuera}

    salida.write_text(json.dumps(inf, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(inf, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
