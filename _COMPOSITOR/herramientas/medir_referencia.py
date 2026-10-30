"""Mide, cuadro a cuadro, dónde están los gráficos violeta (#6F04BA) en un video exportado.

Sirve para calibrar el compositor contra el video aprobado: por cada cuadro del tramo pedido
devuelve las bandas horizontales con violeta (título, pastilla, caja de subtítulo) y su caja
(x0, y0, x1, y1) en px de 1080x1920. No interpreta nada: solo mide.

Uso:
    python medir_referencia.py <video.mp4> <desde_s> <hasta_s> [--salida medidas.json] [--tol 40]
"""
import argparse
import json
import pathlib
import subprocess

import numpy as np

VIOLETA_RGB = (0x6F, 0x04, 0xBA)


def cuadros(video: pathlib.Path, desde: float, hasta: float, w=1080, h=1920):
    """Cuadros RGB exactos del tramo (sin escalar), decodificados con ffmpeg."""
    proc = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", f"{desde:.3f}", "-to", f"{hasta:.3f}", "-i", str(video),
                             "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE,
                            stderr=subprocess.DEVNULL)
    n = 0
    try:
        while True:
            buf = proc.stdout.read(w * h * 3)
            if len(buf) < w * h * 3:
                break
            yield n, np.frombuffer(buf, np.uint8).reshape(h, w, 3)
            n += 1
    finally:            # si quien lee corta antes, se cierra ffmpeg sin errores de tubería
        proc.stdout.close()
        proc.kill()
        proc.wait()


def bandas_violeta(img: np.ndarray, tol: int, min_px: int = 3, min_alto: int = 4) -> list[dict]:
    r, g, b = (img[..., i].astype(int) for i in range(3))
    m = (abs(r - VIOLETA_RGB[0]) < tol) & (abs(g - VIOLETA_RGB[1]) < tol) & (abs(b - VIOLETA_RGB[2]) < tol)
    filas = np.nonzero(m.sum(1) > min_px)[0]
    grupos: list[list[int]] = []
    for y in filas:
        if grupos and y - grupos[-1][1] <= 3:
            grupos[-1][1] = int(y)
        else:
            grupos.append([int(y), int(y)])
    salida = []
    for y0, y1 in grupos:
        if y1 - y0 < min_alto:
            continue
        xs = np.nonzero(m[y0:y1 + 1].any(0))[0]
        salida.append({"caja": [int(xs.min()), y0, int(xs.max()), y1], "px": int(m[y0:y1 + 1].sum())})
    return salida


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("desde", type=float)
    ap.add_argument("hasta", type=float)
    ap.add_argument("--salida")
    ap.add_argument("--tol", type=int, default=40)
    ap.add_argument("--fps", type=float, default=30.0)
    a = ap.parse_args()
    medidas = [{"cuadro": round(a.desde * a.fps) + n, "t": round(a.desde + n / a.fps, 3), "bandas": bandas_violeta(img, a.tol)}
               for n, img in cuadros(pathlib.Path(a.video), a.desde, a.hasta)]
    if a.salida:
        pathlib.Path(a.salida).write_text(json.dumps(medidas, indent=1), encoding="utf-8")
    for m in medidas:
        print(f"{m['cuadro']:4d} {m['t']:6.3f}  " + "  ".join(f"{b['caja']}" for b in m["bandas"]))


if __name__ == "__main__":
    main()
