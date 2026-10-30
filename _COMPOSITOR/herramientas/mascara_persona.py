"""Sándwich de capas sin Premiere: la pastilla queda detrás de la cabeza de la presentadora.

En Premiere era: V1 clip, V2 pastilla, V3 copia del clip con Opacidad › Objeto máscara (calado ~13,
expansión 0, un halo chico). Acá:
1. Se toma el tramo del proxy del A-roll que está debajo de la pastilla (con unos cuadros previos para
   que la red se estabilice).
2. RobustVideoMatting (ONNX, CPU) calcula el mate de la persona cuadro a cuadro.
3. El mate se expande un poco (halo) y se suaviza (calado), en px de la secuencia.
4. Se escribe la persona recortada como video con alfa (VP9) y una entrada "sandwich" que el
   compositor dibuja encima de la pastilla y debajo de los títulos, con el mismo encuadre del clip.

Modelo: rvm_mobilenetv3_fp32.onnx (github.com/PeterL1n/RobustVideoMatting, GPL-3.0; se usa como
herramienta local, no se redistribuye).

Uso:
    python mascara_persona.py <carpeta_publica> <timeline.json> <props_salida.json> [--pastilla N] [--cy Y]
      --pastilla N : índice de la pastilla entre los gráficos (por defecto, la primera)
      --cy Y       : prueba: mueve la pastilla a esa altura (para ver el efecto cuando la cabeza no la toca)
"""
import argparse
import json
import pathlib
import subprocess
import sys

import cv2
import numpy as np
import onnxruntime as ort

AQUI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parents[1] / "_HERRAMIENTAS"))
import velabody  # noqa: E402

SANDWICH = velabody.CONFIG["compositor"]["sandwich"]
CALENTAR = 15   # cuadros previos para estabilizar el estado recurrente de la red


def cuadros_proxy(ruta: pathlib.Path, desde: int, n: int, fps: int = 30):
    w, h = velabody.CONFIG["compositor"]["proxy"]["ancho"], velabody.CONFIG["compositor"]["proxy"]["alto"]
    proc = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", f"{desde / fps:.4f}", "-i", str(ruta), "-frames:v", str(n),
                             "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    while True:
        buf = proc.stdout.read(w * h * 3)
        if len(buf) < w * h * 3:
            break
        yield np.frombuffer(buf, np.uint8).reshape(h, w, 3)
    proc.wait()


def mates(frames, modelo: pathlib.Path, ratio: float = 0.2):
    ses = ort.InferenceSession(str(modelo), providers=["CPUExecutionProvider"])
    rec = [np.zeros([1, 1, 1, 1], np.float32)] * 4
    dr = np.array([ratio], np.float32)
    for f in frames:
        src = (f.astype(np.float32) / 255).transpose(2, 0, 1)[None]
        _, pha, *rec = ses.run(None, {"src": src, "r1i": rec[0], "r2i": rec[1], "r3i": rec[2], "r4i": rec[3],
                                      "downsample_ratio": dr})
        yield pha[0, 0]


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("publico")
    ap.add_argument("timeline")
    ap.add_argument("props")
    ap.add_argument("--pastilla", type=int, default=0)
    ap.add_argument("--cy", type=float)
    a = ap.parse_args()
    publico = pathlib.Path(a.publico)
    tl = json.loads(pathlib.Path(a.timeline).read_text(encoding="utf-8"))
    pastillas = [g for g in tl["graficos"] if g["tipo"] == "pastilla"]
    p = pastillas[a.pastilla]
    if a.cy is not None:
        p["cy"] = a.cy
    modelo = velabody.RAIZ / "_COMPOSITOR_CACHE" / "modelos" / "rvm_mobilenetv3_fp32.onnx"
    tl["sandwich"] = []
    for v in tl["videos"]:
        if v["capa"] != "aroll":
            continue
        ini, fin = max(v["desde"], p["desde"]), min(v["desde"] + v["dur"], p["hasta"])
        if ini >= fin:
            continue
        # px de la secuencia → px del proxy (el mate se procesa a la resolución del proxy)
        caja = v.get("caja") or v["kf"][0]
        escala = velabody.CONFIG["compositor"]["proxy"]["ancho"] / caja["w"]
        halo = max(1, round(SANDWICH["halo_px"] * escala))
        calado = SANDWICH["calado_px"] * escala
        trim_ini = v["trim"] + (ini - v["desde"])
        previo = min(CALENTAR, trim_ini)
        n = fin - ini
        proxy = publico / v["src"]
        destino = publico / "medios" / f"sandwich_{pathlib.Path(v['src']).stem}_{ini}_{fin}.webm"
        print(f"máscara {v['clip']} cuadros {ini}–{fin} (halo {halo}px, calado {calado:.1f}px a resolución de proxy)")
        enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgba",
                                "-s", f"{velabody.CONFIG['compositor']['proxy']['ancho']}x{velabody.CONFIG['compositor']['proxy']['alto']}",
                                "-r", "30", "-i", "-", "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-auto-alt-ref", "0",
                                "-b:v", "0", "-crf", "18", "-row-mt", "1", str(destino)], stdin=subprocess.PIPE)
        frames = list(cuadros_proxy(proxy, trim_ini - previo, previo + n))
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * halo + 1, 2 * halo + 1))
        for k, (f, m) in enumerate(zip(frames, mates(frames, modelo))):
            if k < previo:
                continue
            m = cv2.dilate(m, kernel)
            m = cv2.GaussianBlur(m, (0, 0), calado)
            alfa = (np.clip(m, 0, 1) * 255).astype(np.uint8)
            enc.stdin.write(np.dstack([f, alfa]).tobytes())
        enc.stdin.close()
        enc.wait()
        entrada = {"src": f"medios/{destino.name}", "desde": ini, "dur": n, "trim": 0}
        if v.get("kf"):
            entrada["kf"] = v["kf"]
        else:
            entrada["caja"] = v["caja"]
        tl["sandwich"].append(entrada)
    pathlib.Path(a.props).write_text(json.dumps({"timeline": tl}, ensure_ascii=False), encoding="utf-8")
    print(f"{a.props} · {len(tl['sandwich'])} tramos de sándwich")


if __name__ == "__main__":
    main()
