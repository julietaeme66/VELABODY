"""Arma una pieza de punta a punta sin Premiere y verifica el MP4 que sale. En los anuncios, una pieza
completa por hook (hook + cuerpo): <nombre>_H1, _H2…

    plan.json → velabody.py → armado.json → preparar_medios.py → adaptar_armado.py → Remotion
    → normalización de sonoridad (−14 LUFS, −1 dBTP) → verificación

Las salidas van a <raiz>/_COMPOSITOR_SALIDAS/<nombre>[_calidad]_vNNN.mp4 (render) y _vNNN_norm.mp4 (entrega),
con el número siguiente al último que exista: nunca se pisa un exportado. Junto al MP4 quedan un informe JSON
(mediciones del archivo final y del armado: duración contra el brief, % a cámara, cuándo aparece el equipo),
una hoja de contactos y, en calidad alta, la portada sin texto (.portada.png).

Calidades: baja (540x960, para validar), media (810x1440) y alta (1080x1920, la entrega).

Uso:
    python piloto.py <plan.json> [--nombre NOMBRE] [--piezas H1,H3] [--calidad alta|media|baja] [--props props.json]
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
CALIDADES = {"alta": [],
             "media": ["--scale=0.75", "--image-format=jpeg", "--jpeg-quality=85", "--crf=23"],
             "baja": ["--scale=0.5", "--image-format=jpeg", "--jpeg-quality=75", "--crf=28"]}
DURACION_BRIEF_S = (45, 60)      # "Duración: entre 45 segundos y 1 minuto, aprox." (brief de los Videos 6 a 16)


def correr(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    print("›", " ".join(str(c) for c in cmd))
    return subprocess.run(cmd, check=True, **kw)


def siguiente_version(carpeta: pathlib.Path, nombre: str) -> pathlib.Path:
    usadas = [int(m.group(1)) for p in carpeta.glob(f"{nombre}_v*.mp4") if (m := re.search(r"_v(\d{3})", p.name))]
    return carpeta / f"{nombre}_v{max(usadas, default=0) + 1:03d}.mp4"


def loudnorm(entrada: pathlib.Path, salida: pathlib.Path) -> dict:
    # el AAC de la entrega sube el pico unas décimas (el ADS14 H2 dio −0,9 dBTP con objetivo −1): margen de 0,5 dB
    filtro = f"loudnorm=I={OBJ_LUFS}:TP={OBJ_TP - 0.5}:LRA=11"
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


def tramos_a_camara(tl: dict) -> list[tuple[int, int]]:
    """Cuadros [desde, hasta) en que se ve a la presentadora (A-roll que no tapa ningún B-roll)."""
    tapado = [0] * tl["duracion"]
    for v in tl["videos"]:
        if v["capa"] == "broll":
            for f in range(max(0, v["desde"]), min(tl["duracion"], v["desde"] + v["dur"])):
                tapado[f] = 1
    visible = [0] * tl["duracion"]
    for v in tl["videos"]:
        if v["capa"] == "aroll":
            for f in range(max(0, v["desde"]), min(tl["duracion"], v["desde"] + v["dur"])):
                visible[f] = 1 - tapado[f]
    tramos, ini = [], None
    for f, x in enumerate(visible + [0]):
        if x and ini is None:
            ini = f
        elif not x and ini is not None:
            tramos.append((ini, f))
            ini = None
    return tramos


def armado_contra_brief(tl: dict) -> dict:
    """Lo que el brief pide de cada pieza, medido en el timeline: duración (45 a 60 s), presentadora a cámara
    (pide al menos la mitad) y el equipo en los primeros 5 s (primer B-roll o pastilla; a cámara la
    presentadora suele estar junto al equipo, eso se mira en la hoja de contactos)."""
    fps, tramos = tl["fps"], tramos_a_camara(tl)
    dur = tl["duracion"] / fps
    apariciones = [v["desde"] for v in tl["videos"] if v["capa"] == "broll"] + \
                  [g["desde"] for g in tl["graficos"] if g["tipo"] == "pastilla"]
    equipo = min(apariciones) / fps if apariciones else None
    return {"duracion_s": round(dur, 2), "duracion_en_rango": DURACION_BRIEF_S[0] <= dur <= DURACION_BRIEF_S[1] + 0.5,
            "a_camara_pct": round(100 * sum(b - a for a, b in tramos) / tl["duracion"]),
            "equipo_primer_b_roll_o_pastilla_s": None if equipo is None else round(equipo, 2),
            "equipo_en_5s": equipo is not None and equipo <= 5}


def portada(props: str, tl: dict, destino: pathlib.Path) -> None:
    """Un cuadro sin texto (el brief pide una portada por video): el medio del tramo a cámara más largo."""
    tramos = tramos_a_camara(tl) or [(0, tl["duracion"])]
    a, b = max(tramos, key=lambda t: t[1] - t[0])
    con_props = json.loads(pathlib.Path(props).read_text(encoding="utf-8"))
    sin = pathlib.Path(props).with_name(pathlib.Path(props).stem + "_portada.json")
    sin.write_text(json.dumps({**con_props, "sinTextos": True}, ensure_ascii=False), encoding="utf-8")
    correr(["npx", "remotion", "still", "src/index.ts", "VelabodyPieza", str(destino), "--log=error", f"--props={sin}",
            f"--frame={(a + b) // 2}"], cwd=COMPOSITOR, shell=sys.platform == "win32")


def piezas_de(plan: dict, edicion: pathlib.Path) -> list[tuple[str, pathlib.Path]]:
    """Orgánico: una pieza (armado.json). Anuncio: una por hook (armado_HookN.json → sufijo _HN)."""
    if not plan.get("hooks"):
        return [("", edicion / "armado.json")]
    return [(f"_H{k}", edicion / f"armado_Hook{k}.json") for k, h in enumerate(plan["hooks"], 1) if not h.get("pendiente")]


def nombre_base(plan: dict) -> str:
    """El código del brief (ADS14, ORG7, ADS RF Cavi Pro 1 → ADS_RF_Cavi_Pro_1)."""
    return re.sub(r"\W+", "_", plan.get("codigo") or plan.get("nombre") or plan.get("titulo")).strip("_")


def producir(plan_path: pathlib.Path, calidad: str = "alta", piezas_pedidas: str | None = None,
             nombre: str | None = None, props_fijas: str | None = None) -> list[dict]:
    """Arma, renderiza, normaliza y verifica las piezas de un plan. Devuelve el informe de cada una."""
    plan_path = pathlib.Path(plan_path).resolve()
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    if plan.get("solo_hook_desde"):
        sys.exit("El plan tiene solo_hook_desde (flujo de Premiere: el cuerpo se pega a mano). Para el compositor, "
                 "cada hook se arma completo: sacá esa clave del plan.")
    edicion = velabody.carpeta_plan(plan) / "_EDICION"
    publico = velabody.RAIZ / "_COMPOSITOR_CACHE" / "publico"
    salidas = velabody.RAIZ / "_COMPOSITOR_SALIDAS"
    salidas.mkdir(exist_ok=True)

    correr([PY, "-I", str(AQUI.parents[1] / "_HERRAMIENTAS" / "velabody.py"), str(plan_path)], stdout=subprocess.DEVNULL)
    piezas = piezas_de(plan, edicion)
    if piezas_pedidas:
        pedidas = {f"_{x.strip()}" for x in piezas_pedidas.split(",")}
        piezas = [p for p in piezas if p[0] in pedidas]
    correr([PY, "-I", str(AQUI / "preparar_medios.py"), *[str(x) for _, x in piezas], str(publico)])
    base = nombre or nombre_base(plan)
    informes = []
    for sufijo, armado in piezas:
        nombre_tl = f"timeline{sufijo or ''}.json"
        correr([PY, "-I", str(AQUI / "adaptar_armado.py"), str(armado), str(publico), nombre_tl])
        tl = json.loads((publico / nombre_tl).read_text(encoding="utf-8"))
        if any(g.get("detras") for g in tl["graficos"]):     # sándwich: pastilla detrás de la cabeza
            correr([PY, "-I", str(AQUI / "mascara_persona.py"), str(publico), str(publico / nombre_tl), str(publico / nombre_tl), "--detras"])
            tl = json.loads((publico / nombre_tl).read_text(encoding="utf-8"))
        props = props_fijas
        if not props:
            props = str(velabody.RAIZ / "_COMPOSITOR_CACHE" / f"props{sufijo}.json")
            pathlib.Path(props).write_text(json.dumps({"timeline": tl}, ensure_ascii=False), encoding="utf-8")
        render = siguiente_version(salidas, base + sufijo + ("" if calidad == "alta" else "_" + calidad))
        correr(["npx", "remotion", "render", "src/index.ts", "VelabodyPieza", str(render), "--log=error", f"--props={props}",
                *CALIDADES[calidad]], cwd=COMPOSITOR, shell=sys.platform == "win32")
        final = render.with_name(render.stem + "_norm.mp4")
        previa = loudnorm(render, final)
        informe = {"plan": str(plan_path), "codigo": base, "pieza": sufijo.strip("_"), "calidad": calidad,
                   "armado": str(armado), "render": str(render), "entrega": str(final),
                   "cuadros_timeline": tl["duracion"], "duracion_timeline_s": tl["duracion"] / tl["fps"],
                   "contra_brief": armado_contra_brief(tl),
                   "antes_de_normalizar": {"lufs": float(previa["input_i"]), "true_peak": float(previa["input_tp"])},
                   "entrega_medida": medir(final)}
        fps_hoja = 24 / informe["duracion_timeline_s"]
        correr(["ffmpeg", "-v", "error", "-y", "-i", str(final), "-vf", f"fps={fps_hoja:.4f},scale=216:384,tile=12x2", "-frames:v", "1",
                str(final.with_suffix(".hoja.jpg"))])
        if calidad == "alta":
            portada(props, tl, final.with_suffix(".portada.png"))
        final.with_suffix(".informe.json").write_text(json.dumps(informe, ensure_ascii=False, indent=1), encoding="utf-8")
        # una falla de la verificación se informa pero no frena las piezas que faltan
        verif = subprocess.run([PY, "-I", str(AQUI / "verificar_entrega.py"), str(final), str(publico),
                                str(final.with_suffix(".verificacion.json")), nombre_tl], stdout=subprocess.DEVNULL)
        informe["verificacion_ok"] = verif.returncode == 0
        final.with_suffix(".informe.json").write_text(json.dumps(informe, ensure_ascii=False, indent=1), encoding="utf-8")
        informes.append(informe)
    return informes


def linea(i: dict) -> str:
    m, b = i["entrega_medida"], i["contra_brief"]
    return (f"{pathlib.Path(i['entrega']).name}: {m['duracion_s']:.2f} s (timeline {i['duracion_timeline_s']:.2f} s) · "
            f"{m['lufs_integrado']} LUFS · TP {m['true_peak_dbtp']} dBTP · L {m['rms_izq_db']:.2f} / R {m['rms_der_db']:.2f} dB · "
            f"a cámara {b['a_camara_pct']} %" + ("" if i["verificacion_ok"] else " · ⚠ la verificación falló"))


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("--nombre")
    ap.add_argument("--piezas", help="solo estas piezas, por ejemplo H1,H3")
    ap.add_argument("--props", help="props de Remotion ya armadas (por ejemplo, la prueba de sándwich)")
    ap.add_argument("--calidad", choices=list(CALIDADES), default="alta",
                    help="baja: 540x960, para validar; media: 810x1440; alta: 1080x1920, la entrega")
    a = ap.parse_args()
    informes = producir(a.plan, a.calidad, a.piezas, a.nombre, a.props)
    print(f"\nEntregas en {velabody.RAIZ / '_COMPOSITOR_SALIDAS'}:")
    for i in informes:
        print("  " + linea(i))


if __name__ == "__main__":
    main()
