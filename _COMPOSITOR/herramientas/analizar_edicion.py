"""Desarma un reel plano por plano para comparar su edición con la de un video aprobado.

Por cada plano (entre cortes) mide:
- tipo: presentadora (cara frontal grande) o B-roll;
- duración y cuándo arranca/termina la voz respecto del corte;
- zoom dentro del plano (escala del último cuadro respecto del primero, con puntos ORB) y salto de escala
  respecto del plano anterior cuando es la misma toma (punch-in / punch-out);
- subtítulo: con caja violeta o a cámara (texto blanco sin caja), y su altura;
- gráficos violeta visibles (caja, alto) en el medio del plano.

Escribe un JSON con el detalle y un resumen (ritmo, proporción de B-roll, zooms, gráficos) en Markdown.

Uso:
    python analizar_edicion.py <video.mp4> <salida_sin_extension> [--umbral-escena 0.2]
"""
import argparse
import json
import pathlib
import re
import subprocess
import sys

import cv2
import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from medir_referencia import bandas_violeta  # noqa: E402

FPS = 30
W, H = 540, 960      # análisis a media resolución


def cortes(video: str, umbral: float) -> list[float]:
    r = subprocess.run(["ffmpeg", "-v", "info", "-i", video, "-vf", f"select='gt(scene,{umbral})',showinfo", "-f", "null", "-"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace").stderr
    ts = [float(x) for x in re.findall(r"pts_time:([\d.]+)", r)]
    # los cortes con Pan Left disparan varios cuadros seguidos: se queda el primero de cada grupo
    limpios = []
    for t in ts:
        if not limpios or t - limpios[-1] > 0.25:
            limpios.append(t)
    return limpios


def cuadro(video: str, t: float, w=W, h=H) -> np.ndarray:
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.4f}", "-i", video, "-frames:v", "1", "-vf", f"scale={w}:{h}",
                          "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(h, w, 3)


sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "_HERRAMIENTAS"))
import velabody  # noqa: E402

# YuNet (opencv_zoo, MIT): detector de caras de OpenCV; el modelo va en <raiz>/_COMPOSITOR_CACHE/modelos
CARAS = cv2.FaceDetectorYN.create(str(velabody.RAIZ / "_COMPOSITOR_CACHE" / "modelos" / "face_detection_yunet_2023mar.onnx"),
                                  "", (W, H), 0.8)


def cara(img: np.ndarray):
    """Caja (x, y, ancho, alto) de la cara más grande, o None."""
    _, fs = CARAS.detect(cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
    if fs is None or not len(fs):
        return None
    f = max(fs, key=lambda f: f[2] * f[3])
    return [int(v) for v in f[:4]]


ORB = cv2.ORB_create(1500)


def escala_relativa(a: np.ndarray, b: np.ndarray) -> float | None:
    """Escala de b respecto de a (>1 = b más cerca). Ignora la franja de gráficos y subtítulos."""
    m = np.zeros(a.shape[:2], np.uint8)
    m[260:540] = 255                      # franja media: ni títulos (arriba) ni subtítulos (y≈590 a media res.)
    m[650:] = 255
    ka, da = ORB.detectAndCompute(cv2.cvtColor(a, cv2.COLOR_RGB2GRAY), m)
    kb, db = ORB.detectAndCompute(cv2.cvtColor(b, cv2.COLOR_RGB2GRAY), m)
    if da is None or db is None or len(ka) < 20 or len(kb) < 20:
        return None
    pares = sorted(cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True).match(da, db), key=lambda x: x.distance)[:300]
    if len(pares) < 20:
        return None
    pa = np.float32([ka[p.queryIdx].pt for p in pares])
    pb = np.float32([kb[p.trainIdx].pt for p in pares])
    M, inl = cv2.estimateAffinePartial2D(pa, pb, method=cv2.RANSAC, ransacReprojThreshold=4)
    if M is None or inl is None or inl.sum() < 15:
        return None
    return float(np.hypot(M[0, 0], M[1, 0]))


def hist(img: np.ndarray) -> np.ndarray:
    h = cv2.calcHist([cv2.cvtColor(img, cv2.COLOR_RGB2HSV)[200:960]], [0, 1], None, [30, 32], [0, 180, 0, 256])
    return cv2.normalize(h, h).flatten()


def voz(video: str) -> np.ndarray:
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", video, "-vn", "-ac", "1", "-ar", "16000", "-af", "highpass=f=120",
                          "-f", "s16le", "-"], capture_output=True, check=True).stdout
    x = np.frombuffer(raw, np.int16).astype(float) / 32768
    n = 160
    x = x[: len(x) // n * n].reshape(-1, n)
    return 20 * np.log10(np.sqrt((x ** 2).mean(1)) + 1e-9)     # dB cada 10 ms


def subtitulo(img_full: np.ndarray) -> dict | None:
    zona = img_full[1060:1300]
    caja = [b for b in bandas_violeta(zona, 40) if b["caja"][3] - b["caja"][1] > 60]
    if caja:
        x0, y0, x1, y1 = caja[0]["caja"]
        return {"estilo": "caja", "y_centro": 1060 + (y0 + y1) / 2, "ancho": x1 - x0}
    blanco = (zona.min(2) > 235)
    filas = np.nonzero(blanco.sum(1) > 6)[0]
    if len(filas):
        return {"estilo": "camara", "y_centro": 1060 + (filas[0] + filas[-1]) / 2}
    return None


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("salida")
    ap.add_argument("--umbral-escena", type=float, default=0.2)
    a = ap.parse_args()
    dur = float(json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", a.video],
                                          capture_output=True).stdout)["format"]["duration"])
    cs = cortes(a.video, a.umbral_escena)
    bordes = [0.0] + cs + [dur]
    env = voz(a.video)
    nivel = np.percentile(env, 95)
    habla = env > nivel - 25
    planos = []
    previo, ref_hist = None, None
    for k, (t0, t1) in enumerate(zip(bordes, bordes[1:])):
        if t1 - t0 < 0.15:
            continue
        ini, med, fin = cuadro(a.video, t0 + 0.12), cuadro(a.video, (t0 + t1) / 2), cuadro(a.video, max(t0 + 0.12, t1 - 0.12))
        full = cuadro(a.video, (t0 + t1) / 2, 1080, 1920)
        c = cara(med)
        # presentadora = cara + mismo fondo y vestuario que el primer plano (el hook siempre es a cámara). Solo con la
        # cara no alcanza: las caras de la pantalla del equipo, en el B-roll, también son frontales y grandes.
        # Es aproximado (una toma de la presentadora operando el equipo puede contar como "presentadora").
        if ref_hist is None:
            ref_hist = hist(med)
        parecido = cv2.compareHist(ref_hist, hist(med), cv2.HISTCMP_CORREL)
        tipo = "presentadora" if c is not None and parecido >= 0.6 else "broll"
        zoom = escala_relativa(ini, fin)
        salto = escala_relativa(previo, ini) if previo is not None and tipo == "presentadora" and planos and planos[-1]["tipo"] == "presentadora" else None
        i0, i1 = int(t0 * 100), int(t1 * 100)
        h = habla[i0:i1]
        voz_ini = (np.argmax(h) / 100) if h.any() else None
        voz_fin = ((len(h) - np.argmax(h[::-1])) / 100) if h.any() else None
        graf = [b["caja"] for b in bandas_violeta(full, 40) if b["caja"][1] < 1050]
        planos.append({"n": len(planos) + 1, "desde": round(t0, 2), "hasta": round(t1, 2), "dur": round(t1 - t0, 2), "tipo": tipo,
                       "cara_alto_px": int(c[3] * 2) if c is not None else None,
                       "zoom_en_plano": None if zoom is None else round(zoom, 3),
                       "zoom_por_s_pct": None if zoom is None else round((zoom - 1) * 100 / max(0.3, t1 - t0 - 0.24), 2),
                       "salto_vs_anterior": None if salto is None else round(salto, 3),
                       "voz_desde_corte_s": None if voz_ini is None else round(voz_ini, 2),
                       "silencio_al_final_s": None if voz_fin is None else round((t1 - t0) - voz_fin, 2),
                       "subtitulo": subtitulo(full), "graficos": graf})
        previo = fin
    pres = [p for p in planos if p["tipo"] == "presentadora"]
    brl = [p for p in planos if p["tipo"] == "broll"]
    zooms = [p["zoom_por_s_pct"] for p in planos if p["zoom_por_s_pct"] is not None]
    resumen = {
        "duracion_s": round(dur, 2), "planos": len(planos), "plano_medio_s": round(float(np.mean([p["dur"] for p in planos])), 2),
        "plano_mediana_s": round(float(np.median([p["dur"] for p in planos])), 2),
        "presentadora": {"planos": len(pres), "seg": round(sum(p["dur"] for p in pres), 1),
                         "dur_mediana_s": round(float(np.median([p["dur"] for p in pres])), 2) if pres else None},
        "broll": {"planos": len(brl), "seg": round(sum(p["dur"] for p in brl), 1),
                  "dur_mediana_s": round(float(np.median([p["dur"] for p in brl])), 2) if brl else None},
        "zoom_por_s_pct_mediana": round(float(np.median(zooms)), 2) if zooms else None,
        "saltos_de_escala": [p["salto_vs_anterior"] for p in planos if p["salto_vs_anterior"] and abs(p["salto_vs_anterior"] - 1) > 0.04],
        "silencio_en_cortes_mediana_s": round(float(np.median([p["voz_desde_corte_s"] for p in planos if p["voz_desde_corte_s"] is not None])), 2),
        "segundos_con_grafico": round(sum(p["dur"] for p in planos if p["graficos"]), 1),
    }
    out = pathlib.Path(a.salida)
    out.with_suffix(".json").write_text(json.dumps({"resumen": resumen, "planos": planos}, ensure_ascii=False, indent=1), encoding="utf-8")
    md = [f"# Edición de `{pathlib.Path(a.video).name}`", "", "```", json.dumps(resumen, ensure_ascii=False, indent=1), "```", "",
          "| # | desde–hasta | dur | tipo | zoom en plano (%/s) | salto de escala | voz desde el corte | silencio al final | subtítulo | gráficos (caja) |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for p in planos:
        sub = p["subtitulo"]
        md.append(f"| {p['n']} | {p['desde']}–{p['hasta']} | {p['dur']} | {p['tipo']} | {p['zoom_en_plano']} ({p['zoom_por_s_pct']}) | "
                  f"{p['salto_vs_anterior'] or ''} | {p['voz_desde_corte_s']} | {p['silencio_al_final_s']} | "
                  f"{(sub['estilo'] + ' y=' + str(int(sub['y_centro']))) if sub else ''} | {p['graficos']} |")
    out.with_suffix(".md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
