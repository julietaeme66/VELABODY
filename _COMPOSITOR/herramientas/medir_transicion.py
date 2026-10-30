"""Mide una transición cuadro a cuadro: desplazamiento horizontal y nitidez alrededor del corte.

Compara el perfil horizontal de cada cuadro (franja media, sin gráficos ni subtítulos) contra un cuadro
quieto de la toma que sale (8 cuadros antes) y otro de la que entra (9 después). Así se midió el Pan Left
del Video 1 FINAL (config › compositor.pan_left) y así se verifica el nuestro.

Uso:
    python medir_transicion.py <video.mp4> <cuadro_del_corte> [--fps 30]
"""
import argparse
import subprocess
import sys

import numpy as np


def cuadros(video: str, c0: int, n: int, fps: float) -> np.ndarray:
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{c0 / fps:.4f}", "-i", video, "-frames:v", str(n),
                          "-vf", "scale=270:480,format=gray", "-f", "rawvideo", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, 480, 270).astype(float)


def perfil(f: np.ndarray) -> np.ndarray:
    p = f[150:420].mean(0)
    return p - p.mean()


def desplazamiento(a: np.ndarray, b: np.ndarray, maximo: int = 135) -> tuple[float, int]:
    mejor = (-2.0, 0)
    for s in range(-maximo, maximo + 1):
        x, y = (a[s:], b[:len(b) - s]) if s >= 0 else (a[:s], b[-s:])
        c = float((x * y).sum() / np.sqrt((x * x).sum() * (y * y).sum() + 1e-9))
        mejor = max(mejor, (c, s))
    return mejor


def medir(video: str, corte: int, fps: float = 30) -> list[dict]:
    f = cuadros(video, corte - 8, 18, fps)
    sale, entra = perfil(f[0]), perfil(f[-1])
    filas = []
    for k, img in enumerate(f):
        co, so = desplazamiento(perfil(img), sale)
        ci, si = desplazamiento(perfil(img), entra)
        filas.append({"rel": k - 8, "nitidez": round(float(np.abs(np.diff(img[150:420], axis=1)).mean()), 2),
                      "vs_sale_px": so * 4, "corr_sale": round(co, 2), "vs_entra_px": si * 4, "corr_entra": round(ci, 2)})
    return filas


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("corte", type=int)
    ap.add_argument("--fps", type=float, default=30)
    a = ap.parse_args()
    for r in medir(a.video, a.corte, a.fps):
        print(f"{r['rel']:+3d}  nitidez {r['nitidez']:5.2f}  vs saliente {r['vs_sale_px']:+5d} px (corr {r['corr_sale']:.2f})"
              f"  vs entrante {r['vs_entra_px']:+5d} px (corr {r['corr_entra']:.2f})")


if __name__ == "__main__":
    main()
