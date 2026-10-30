"""Calibra el equivalente del Lumetri de VELABODY (LUT Alexa v3 → Rec709, exposición 0,4, contraste 65)
contra el video aprobado, usando un cuadro de una toma que aparece en los dos.

1. Busca el cuadro exacto de la fuente que coincide con el cuadro del aprobado (correlación de bordes,
   que no depende del color).
2. Pasa la fuente por el LUT con ffmpeg y ajusta, sobre los píxeles alineados, una exposición (en pasos,
   sobre la señal lineal aproximada) y un contraste (curva S alrededor del gris medio).
3. Informa el ΔE2000 medio y el percentil 95 antes y después, y escribe los parámetros en JSON.

No declara equivalencia: deja el error medido para que se lea.

Uso:
    python calibrar_color.py <fuente> <seg_fuente> <aprobado> <seg_aprobado> <lut.cube> <salida.json>
    python calibrar_color.py ... <salida.json> --verificar <exposicion> <contraste>
"""
import json
import pathlib
import subprocess
import sys

import cv2
import numpy as np

W, H = 1080, 1920


def cuadro(video: str, t: float, vf: str = "") -> np.ndarray:
    """Un cuadro RGB float 0..1 de 1080x1920 (la fuente vertical se rota sola al decodificar)."""
    filtros = f"scale={W}:{H}:flags=lanczos,format=rgb48le" + (f",{vf}" if vf else "")
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.4f}", "-i", video, "-frames:v", "1", "-vf", filtros,
                          "-f", "rawvideo", "-pix_fmt", "rgb48le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint16).reshape(H, W, 3).astype(np.float32) / 65535


def bordes(img: np.ndarray) -> np.ndarray:
    g = cv2.cvtColor((img * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32)
    g = cv2.resize(g, (270, 480), interpolation=cv2.INTER_AREA)
    m = np.hypot(cv2.Sobel(g, cv2.CV_32F, 1, 0), cv2.Sobel(g, cv2.CV_32F, 0, 1))
    return (m - m.mean()) / (m.std() + 1e-6)


def delta_e(a: np.ndarray, b: np.ndarray, mascara: np.ndarray) -> tuple[float, float]:
    la = cv2.cvtColor(a.astype(np.float32), cv2.COLOR_RGB2Lab)[mascara]
    lb = cv2.cvtColor(b.astype(np.float32), cv2.COLOR_RGB2Lab)[mascara]
    d = ciede2000(la, lb)
    return float(d.mean()), float(np.percentile(d, 95))


def ciede2000(lab1: np.ndarray, lab2: np.ndarray) -> np.ndarray:
    L1, a1, b1 = lab1.T
    L2, a2, b2 = lab2.T
    C1, C2 = np.hypot(a1, b1), np.hypot(a2, b2)
    Cm = (C1 + C2) / 2
    G = 0.5 * (1 - np.sqrt(Cm ** 7 / (Cm ** 7 + 25 ** 7)))
    a1p, a2p = a1 * (1 + G), a2 * (1 + G)
    C1p, C2p = np.hypot(a1p, b1), np.hypot(a2p, b2)
    h1p, h2p = np.degrees(np.arctan2(b1, a1p)) % 360, np.degrees(np.arctan2(b2, a2p)) % 360
    dLp, dCp = L2 - L1, C2p - C1p
    dh = h2p - h1p
    dh = np.where(dh > 180, dh - 360, np.where(dh < -180, dh + 360, dh))
    dh = np.where(C1p * C2p == 0, 0, dh)
    dHp = 2 * np.sqrt(C1p * C2p) * np.sin(np.radians(dh) / 2)
    Lm, Cmp = (L1 + L2) / 2, (C1p + C2p) / 2
    hs = h1p + h2p
    hm = np.where(C1p * C2p == 0, hs, np.where(abs(h1p - h2p) <= 180, hs / 2, np.where(hs < 360, (hs + 360) / 2, (hs - 360) / 2)))
    T = 1 - 0.17 * np.cos(np.radians(hm - 30)) + 0.24 * np.cos(np.radians(2 * hm)) + 0.32 * np.cos(np.radians(3 * hm + 6)) \
        - 0.20 * np.cos(np.radians(4 * hm - 63))
    dth = 30 * np.exp(-((hm - 275) / 25) ** 2)
    Rc = 2 * np.sqrt(Cmp ** 7 / (Cmp ** 7 + 25 ** 7))
    Sl = 1 + 0.015 * (Lm - 50) ** 2 / np.sqrt(20 + (Lm - 50) ** 2)
    Sc, Sh = 1 + 0.045 * Cmp, 1 + 0.015 * Cmp * T
    Rt = -np.sin(np.radians(2 * dth)) * Rc
    return np.sqrt((dLp / Sl) ** 2 + (dCp / Sc) ** 2 + (dHp / Sh) ** 2 + Rt * (dCp / Sc) * (dHp / Sh))


def ajuste(img: np.ndarray, exposicion: float, contraste: float) -> np.ndarray:
    """Exposición en pasos sobre la señal linealizada (gamma 2,4) y contraste como curva S
    (mezcla con una smoothstep alrededor de 0,5). Mismo modelo que preparar_medios.py."""
    lin = np.clip(img, 0, 1) ** 2.4 * 2 ** exposicion
    y = np.clip(lin, 0, 1) ** (1 / 2.4)
    s = y * y * (3 - 2 * y)
    return np.clip(y + contraste * (s - y), 0, 1)


def main() -> None:
    fuente, t_f, aprobado, t_a, lut, salida = sys.argv[1], float(sys.argv[2]), sys.argv[3], float(sys.argv[4]), sys.argv[5], sys.argv[6]
    ref = cuadro(aprobado, t_a)
    # cuadro exacto: barrido fino alrededor del segundo dado
    candidatos = [t_f + k * 0.02 for k in range(-10, 11)]
    br = bordes(ref)
    puntajes = [(float((bordes(cuadro(fuente, t)) * br).mean()), t) for t in candidatos]
    corr, t_ok = max(puntajes)
    lut_s = str(pathlib.Path(lut).as_posix()).replace(":", "\\:")
    con_lut = cuadro(fuente, t_ok, f"lut3d='{lut_s}'")
    # se excluyen los gráficos del aprobado (subtítulos, títulos: violeta o blanco puro) y los bordes
    r, g, b = (ref[..., i] for i in range(3))
    grafico = ((abs(r - 0x6F / 255) < 0.2) & (g < 0.25) & (abs(b - 0xBA / 255) < 0.2)) | (ref.min(2) > 0.97)
    grafico = cv2.dilate(grafico.astype(np.uint8), np.ones((31, 31), np.uint8)).astype(bool)
    mascara = ~grafico
    mascara[:40], mascara[-40:], mascara[:, :40], mascara[:, -40:] = False, False, False, False
    antes = delta_e(con_lut, ref, mascara)
    if len(sys.argv) > 8:      # --verificar <exposicion> <contraste>: mide parámetros ya ajustados, sin buscar
        mejor = (None, float(sys.argv[8]), float(sys.argv[9]))
    else:
        mejor = None
        for e in np.arange(-0.2, 1.21, 0.05):
            for c in np.arange(0.0, 1.01, 0.05):
                d = delta_e(ajuste(con_lut, e, c), ref, mascara)[0]
                if mejor is None or d < mejor[0]:
                    mejor = (d, round(float(e), 2), round(float(c), 2))
    despues = delta_e(ajuste(con_lut, mejor[1], mejor[2]), ref, mascara)
    res = {"fuente": fuente, "segundo_fuente": round(t_ok, 3), "correlacion_bordes": round(corr, 3),
           "aprobado": aprobado, "segundo_aprobado": t_a, "lut": lut,
           "exposicion_pasos": mejor[1], "contraste_s": mejor[2],
           "dE2000_solo_lut": {"medio": round(antes[0], 2), "p95": round(antes[1], 2)},
           "dE2000_ajustado": {"medio": round(despues[0], 2), "p95": round(despues[1], 2)},
           "pixeles_comparados": int(mascara.sum())}
    pathlib.Path(salida).write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(res, indent=1, ensure_ascii=False))
    comp = np.hstack([con_lut, ajuste(con_lut, mejor[1], mejor[2]), ref])
    cv2.imwrite(str(pathlib.Path(salida).with_suffix(".png")), cv2.cvtColor((cv2.resize(comp, (1080, 640)) * 255).astype(np.uint8), cv2.COLOR_RGB2BGR))


if __name__ == "__main__":
    main()
