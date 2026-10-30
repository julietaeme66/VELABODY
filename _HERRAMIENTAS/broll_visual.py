"""Mirada rápida a un B-roll, para partir los planos largos (pedido del 30/10).

Un inserto que dura mucho (p. ej. 10 s de la pantalla con los análisis) se corta cada 3–4 s. El plano
siguiente sale del mismo archivo, pero no puede verse como un jump cut. Hay dos opciones:
  - "otra parte": un tramo del clip que muestre otra cosa (que se vea distinto del plano anterior);
  - "plano cerrado": el mismo momento, más cerca, centrado en lo que tiene detalle (la pantalla, el rostro).

Solo se leen los cuadros clave (uno cada ~0,5 s) en miniatura, y el resultado se guarda en caché por archivo.
"""
import pathlib
import re
import subprocess

import numpy as np

ANCHO, ALTO = 90, 160          # miniatura vertical (ffmpeg aplica la rotación de la cámara)
_cache: dict[str, tuple[np.ndarray, np.ndarray]] = {}


def miniaturas(ruta: str, carpeta_cache: pathlib.Path | None = None) -> tuple[np.ndarray, np.ndarray]:
    """(tiempos en s, cuadros RGB float [n, ALTO, ANCHO, 3]) de los cuadros clave del archivo."""
    if ruta in _cache:
        return _cache[ruta]
    archivo = carpeta_cache / (pathlib.Path(ruta).stem + "_claves.npz") if carpeta_cache else None
    if archivo and archivo.exists() and archivo.stat().st_mtime >= pathlib.Path(ruta).stat().st_mtime:
        d = np.load(archivo)
        _cache[ruta] = (d["t"], d["img"])
        return _cache[ruta]
    r = subprocess.run(["ffmpeg", "-v", "info", "-skip_frame", "nokey", "-i", ruta, "-vf",
                        f"scale={ANCHO}:{ALTO},showinfo,format=rgb24", "-fps_mode", "passthrough",
                        "-f", "rawvideo", "-"], capture_output=True, check=True)
    t = np.array([float(x) for x in re.findall(rb"pts_time:([0-9.]+)", r.stderr)])
    img = np.frombuffer(r.stdout, np.uint8).reshape(-1, ALTO, ANCHO, 3).astype(np.float32)
    n = min(len(t), len(img))
    _cache[ruta] = (t[:n], img[:n])
    if archivo:
        archivo.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(archivo, t=t[:n], img=img[:n].astype(np.uint8))
    return _cache[ruta]


def _firma(img: np.ndarray) -> np.ndarray:
    """Gris desenfocado y normalizado: compara la composición, no el ruido ni la exposición."""
    g = img.mean(-1)
    g = (g[0::2, 0::2] + g[1::2, 0::2] + g[0::2, 1::2] + g[1::2, 1::2]) / 4
    g = g - g.mean()
    return (g / (np.linalg.norm(g) + 1e-6)).ravel()


def distancia(a: np.ndarray, b: np.ndarray) -> float:
    """0 = la misma imagen; ~1 = otra cosa. Mezcla composición (correlación) y color medio."""
    comp = 1 - float(_firma(a) @ _firma(b))
    color = float(np.abs(a.mean((0, 1)) - b.mean((0, 1))).mean()) / 64
    return min(1.5, comp + color)


def _ventana(t: np.ndarray, t0: float, t1: float) -> np.ndarray:
    k = np.where((t >= t0) & (t <= t1))[0]
    return k if len(k) else np.array([int(np.argmin(np.abs(t - (t0 + t1) / 2)))])


def otra_parte(ruta: str, dur: float, largo: float, anterior: tuple[float, float], usados: list[tuple[float, float]],
               umbral: float, carpeta_cache: pathlib.Path | None = None) -> float | None:
    """Inicio de un tramo de `dur` s del clip que no se pisa con lo ya usado y que se ve distinto del plano
    `anterior` (cada cuadro del tramo, contra el más parecido del anterior). Entre los que pasan el umbral
    gana el más cercano en el tiempo (sigue mostrando lo mismo de lo que se habla), y se evitan los tramos
    con la cámara en movimiento brusco. None si no hay ninguno."""
    t, img = miniaturas(ruta, carpeta_cache)
    previos = img[_ventana(t, *anterior)]
    mejor = None
    for s in np.arange(0.0, max(0.0, largo - dur - 0.1) + 1e-6, 0.25):
        if any(s < u1 + 0.5 and s + dur > u0 - 0.5 for u0, u1 in usados):
            continue
        k = _ventana(t, s, s + dur)
        cerca = min(distancia(img[i], p) for i in k for p in previos)
        sacudida = max((distancia(img[i], img[j]) for i, j in zip(k, k[1:])), default=0.0)
        puntaje = -abs(s - anterior[0]) - 20 * max(0.0, sacudida - 0.4)
        if cerca >= umbral and (mejor is None or puntaje > mejor[0]):
            mejor = (puntaje, float(s))
    return mejor[1] if mejor else None


def foco_cercano(ruta: str, t0: float, t1: float, zoom: float, carpeta_cache: pathlib.Path | None = None) -> tuple[float, float]:
    """(foco_x, foco_y) para un plano `zoom` veces más cerca: la ventana con más detalle (bordes) en ese
    tramo, con preferencia por el centro. Queda dentro del cuadro (como lo limita encuadrar())."""
    t, img = miniaturas(ruta, carpeta_cache)
    g = img[_ventana(t, t0, t1)].mean(-1)
    gx, gy = np.abs(np.diff(g, axis=2))[:, :-1, :], np.abs(np.diff(g, axis=1))[:, :, :-1]
    energia = (gx + gy).mean(0)
    h, w = energia.shape
    vh, vw = int(round(h / zoom)), int(round(w / zoom))
    integral = energia.cumsum(0).cumsum(1)
    integral = np.pad(integral, ((1, 0), (1, 0)))
    mejor = (-1.0, 0.5, 0.5)
    for y in range(0, h - vh + 1):
        for x in range(0, w - vw + 1):
            suma = integral[y + vh, x + vw] - integral[y, x + vw] - integral[y + vh, x] + integral[y, x]
            cx, cy = (x + vw / 2) / w, (y + vh / 2) / h
            puntaje = suma * (1 - 0.6 * ((cx - 0.5) ** 2 + (cy - 0.5) ** 2))
            if puntaje > mejor[0]:
                mejor = (puntaje, cx, cy)
    return round(mejor[1], 3), round(mejor[2], 3)
