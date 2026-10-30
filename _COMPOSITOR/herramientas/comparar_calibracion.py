"""Compara, cuadro a cuadro, los gráficos violeta del aprobado con los de la composición Calibracion.

Mide los dos videos con medir_referencia.bandas_violeta en los tramos pedidos, empareja las bandas por
cercanía vertical y reporta la diferencia de sus cajas (x0, y0, x1, y1) en px. Escribe un JSON con el
detalle y un resumen por tramo (mediana y máximo del error), que es lo que va a la tabla de diferencias.

Uso:
    python comparar_calibracion.py <aprobado.mp4> <calibracion.mp4> <salida.json> nombre:desde:hasta [...]
"""
import json
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from medir_referencia import bandas_violeta, cuadros  # noqa: E402


def medir(video: str, desde: float, hasta: float) -> list[list[dict]]:
    return [bandas_violeta(img, 40) for _, img in cuadros(pathlib.Path(video), desde, hasta)]


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    aprobado, calib, salida = sys.argv[1], sys.argv[2], pathlib.Path(sys.argv[3])
    informe = {}
    for tramo in sys.argv[4:]:
        nombre, d, h = tramo.split(":")
        a, c = medir(aprobado, float(d), float(h)), medir(calib, float(d), float(h))
        filas, errores, presencia = [], [], 0
        for k, (ba, bc) in enumerate(zip(a, c)):
            if bool(ba) != bool(bc):
                presencia += 1
            for x in ba:
                if not bc:
                    continue
                y = min(bc, key=lambda b: abs((b["caja"][1] + b["caja"][3]) - (x["caja"][1] + x["caja"][3])))
                dif = [yy - xx for xx, yy in zip(x["caja"], y["caja"])]
                errores.append(max(abs(v) for v in dif))
                filas.append({"cuadro": round(float(d) * 30) + k, "aprobado": x["caja"], "nuestro": y["caja"], "dif": dif})
        e = np.array(errores) if errores else np.array([np.nan])
        informe[nombre] = {"tramo_s": [float(d), float(h)], "cuadros": len(a), "cuadros_con_presencia_distinta": presencia,
                           "error_px_mediana": float(np.nanmedian(e)), "error_px_p90": float(np.nanpercentile(e, 90)),
                           "error_px_max": float(np.nanmax(e)), "detalle": filas}
        print(f"{nombre:28s} {len(a):3d} cuadros · presencia distinta en {presencia:2d} · error px mediana "
              f"{np.nanmedian(e):5.1f} · p90 {np.nanpercentile(e, 90):5.1f} · máx {np.nanmax(e):5.1f}")
    salida.write_text(json.dumps(informe, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
