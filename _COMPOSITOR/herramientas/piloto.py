"""Arma una pieza de punta a punta sin Premiere y verifica el MP4 que sale.

    plan.json → velabody.py → armado.json → preparar_medios.py → adaptar_armado.py → Remotion
    → normalización de sonoridad (−14 LUFS, −1 dBTP) → verificación

Las salidas van a <raiz>/_COMPOSITOR_SALIDAS/<nombre>_vNNN.mp4 (render) y _vNNN_norm.mp4 (entrega), con el
número siguiente al último que exista: nunca se pisa un exportado. Junto al MP4 queda un informe JSON con
las mediciones del archivo final y una hoja de contactos.

Uso:
    python piloto.py <plan.json> [--nombre NOMBRE] [--props props.json]
"""
import argparse
import json
import pathlib
import re
import subprocess
import sys

AQUI = pathlib.Path(__file__).resolve().parent
COMPOSITOR = AQUI.parent
sys.path.insert(0, str(AQUI.parents[1] / "_HERRAMIENTAS"))
import velabody  # noqa: E402

PY = sys.executable
OBJ_LUFS, OBJ_TP = velabody.CONFIG["audio"]["voz_lufs"], velabody.CONFIG["audio"]["true_peak_db"]


def correr(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    print("›", " ".join(str(c) for c in cmd))
    return subprocess.run(cmd, check=True, **kw)


def siguiente_version(carpeta: pathlib.Path, nombre: str) -> pathlib.Path:
    usadas = [int(m.group(1)) for p in carpeta.glob(f"{nombre}_v*.mp4") if (m := re.search(r"_v(\d{3})", p.name))]
    return carpeta / f"{nombre}_v{max(usadas, default=0) + 1:03d}.mp4"


def loudnorm(entrada: pathlib.Path, salida: pathlib.Path) -> dict:
    filtro = f"loudnorm=I={OBJ_LUFS}:TP={OBJ_TP}:LRA=11"
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(entrada), "-vn", "-af", filtro + ":print_format=json", "-f", "null", "-"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    m = json.loads(r.stderr[r.stderr.rindex("{"):r.stderr.rindex("}") + 1])
    segunda = (f"{filtro}:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}"
               f":measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
    correr(["ffmpeg", "-v", "error", "-y", "-i", str(entrada), "-c:v", "copy", "-af", segunda + ",aresample=48000",
            "-c:a", "aac", "-b:a", "320k", "-movflags", "+faststart", str(salida)])
    return m


def medir(mp4: pathlib.Path) -> dict:
    p = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                                   "stream=codec_type,codec_name,width,height,r_frame_rate,pix_fmt,sample_rate,channels:format=duration",
                                   "-of", "json", str(mp4)], capture_output=True, check=True).stdout)
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(mp4), "-vn", "-af", "ebur128=peak=true", "-f", "null", "-"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace").stderr
    resumen = r[r.rindex("Summary:"):]
    lufs = float(re.search(r"I:\s+(-?[\d.]+) LUFS", resumen).group(1))
    tp = float(re.search(r"Peak:\s+(-?[\d.]+) dBFS", resumen).group(1))
    # balance izquierda/derecha (el Video 1 salió cargado a la izquierda)
    canales = []
    for c in ("FL", "FR"):
        s = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(mp4), "-vn", "-af", f"pan=mono|c0={c},astats=measure_overall=RMS_level",
                            "-f", "null", "-"], capture_output=True, text=True, encoding="utf-8", errors="replace").stderr
        canales.append(float(re.findall(r"RMS level dB:\s+(-?[\d.]+)", s)[-1]))
    return {"streams": p["streams"], "duracion_s": float(p["format"]["duration"]), "lufs_integrado": lufs,
            "true_peak_dbtp": tp, "rms_izq_db": canales[0], "rms_der_db": canales[1]}


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("--nombre")
    ap.add_argument("--props", help="props de Remotion ya armadas (por ejemplo, la prueba de sándwich)")
    a = ap.parse_args()
    plan_path = pathlib.Path(a.plan).resolve()
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    edicion = velabody.carpeta_plan(plan) / "_EDICION"
    armado = edicion / "armado.json"
    publico = velabody.RAIZ / "_COMPOSITOR_CACHE" / "publico"
    salidas = velabody.RAIZ / "_COMPOSITOR_SALIDAS"
    salidas.mkdir(exist_ok=True)

    correr([PY, "-I", str(AQUI.parents[1] / "_HERRAMIENTAS" / "velabody.py"), str(plan_path)], stdout=subprocess.DEVNULL)
    correr([PY, "-I", str(AQUI / "preparar_medios.py"), str(armado), str(publico)])
    correr([PY, "-I", str(AQUI / "adaptar_armado.py"), str(armado), str(publico)])
    tl = json.loads((publico / "timeline.json").read_text(encoding="utf-8"))

    nombre = a.nombre or re.sub(r"\W+", "_", plan.get("titulo") or plan["nombre"]).strip("_")
    render = siguiente_version(salidas, nombre)
    cmd = ["npx", "remotion", "render", "src/index.ts", "VelabodyPieza", str(render), "--log=error"]
    if a.props:
        cmd.append(f"--props={a.props}")
    correr(cmd, cwd=COMPOSITOR, shell=sys.platform == "win32")
    final = render.with_name(render.stem + "_norm.mp4")
    previa = loudnorm(render, final)
    informe = {"plan": str(plan_path), "armado": str(armado), "render": str(render), "entrega": str(final),
               "cuadros_timeline": tl["duracion"], "duracion_timeline_s": tl["duracion"] / tl["fps"],
               "antes_de_normalizar": {"lufs": float(previa["input_i"]), "true_peak": float(previa["input_tp"])},
               "entrega_medida": medir(final)}
    correr(["ffmpeg", "-v", "error", "-y", "-i", str(final), "-vf", "fps=2,scale=216:384,tile=12x2", "-frames:v", "1",
            str(final.with_suffix(".hoja.jpg"))])
    final.with_suffix(".informe.json").write_text(json.dumps(informe, ensure_ascii=False, indent=1), encoding="utf-8")
    m = informe["entrega_medida"]
    print(f"\nEntrega: {final}\n  {m['duracion_s']:.3f} s (timeline {informe['duracion_timeline_s']:.3f} s) · "
          f"{m['lufs_integrado']} LUFS · true peak {m['true_peak_dbtp']} dBTP · L {m['rms_izq_db']} / R {m['rms_der_db']} dB")


if __name__ == "__main__":
    main()
