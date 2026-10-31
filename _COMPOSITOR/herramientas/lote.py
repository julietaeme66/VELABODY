"""Produce y entrega una tanda de videos (el flujo de la wiki › 03_flujo_de_trabajo):

    python lote.py --calidad baja [--videos 6,8] [--piezas H1]    # todas las piezas, para validar
    python lote.py --calidad alta [--videos 6,8]                  # la entrega: alta + _ENTREGAS
    python lote.py --solo-entregar [--videos 8]                   # empaqueta lo último en alta, sin renderizar

Los planes son <raiz>/Video N — …/_EDICION/plan.json (o los que se pasen con --planes). Cada pieza sale de
piloto.producir(); al final queda una tabla resumen (_COMPOSITOR_SALIDAS/resumen_<calidad>.md) con lo que pide
el brief: duración, sonoridad, % a cámara, cuándo aparece el equipo y los avisos de las notas del armado.

Entrega (calidad alta): <raiz>/_ENTREGAS/<código>/ con el nombre que pide el brief (ADS12_Hook1.mp4, ORG7.mp4)
y la portada sin texto de cada pieza (.png).
"""
import argparse
import datetime
import json
import pathlib
import re
import shutil
import sys

AQUI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import piloto  # noqa: E402
from piloto import velabody  # noqa: E402

SALIDAS = velabody.RAIZ / "_COMPOSITOR_SALIDAS"
ENTREGAS = velabody.RAIZ / "_ENTREGAS"


def planes(videos: set[int] | None, explicitos: list[str] | None) -> list[pathlib.Path]:
    if explicitos:
        return [pathlib.Path(p).resolve() for p in explicitos]
    encontrados = []
    for p in sorted(velabody.RAIZ.glob("Video */_EDICION/plan.json")):
        n = int(re.match(r"Video (\d+)", p.parents[1].name).group(1))
        if videos is None or n in videos:
            encontrados.append(p)
    return sorted(encontrados, key=lambda p: int(re.match(r"Video (\d+)", p.parents[1].name).group(1)))


def avisos(armado: str) -> list[str]:
    """Las líneas con ⚠️ de las notas del armado (B-roll que se movió, clip que se mueve entero, palabras…)."""
    notas = pathlib.Path(armado).with_name(pathlib.Path(armado).name.replace("armado", "notas_revision").replace(".json", ".md"))
    if not notas.exists():
        return []
    return [l.strip("- ").strip() for l in notas.read_text(encoding="utf-8").splitlines() if "⚠" in l]


def ultimas_altas(codigo: str) -> dict[str, dict]:
    """Por pieza, el informe de la última versión en alta (<código>[_HN]_vNNN_norm.informe.json, sin _baja/_media)."""
    ultimas: dict[str, tuple[int, dict]] = {}
    for f in SALIDAS.glob(f"{codigo}*_v*_norm.informe.json"):
        m = re.fullmatch(re.escape(codigo) + r"(?:_(H\d+))?_v(\d{3})_norm\.informe\.json", f.name)
        if not m:
            continue
        pieza, v = m.group(1) or "", int(m.group(2))
        if v > ultimas.get(pieza, (0, None))[0]:
            ultimas[pieza] = (v, json.loads(f.read_text(encoding="utf-8")))
    return {p: i for p, (_, i) in ultimas.items()}


def entregar(codigo: str) -> list[pathlib.Path]:
    """Copia la última versión en alta de cada pieza a _ENTREGAS/<código>/ con el nombre del brief, con su portada."""
    destino = ENTREGAS / codigo
    destino.mkdir(parents=True, exist_ok=True)
    hechos = []
    for pieza, inf in sorted(ultimas_altas(codigo).items()):
        nombre = f"{codigo}_Hook{pieza[1:]}" if pieza else codigo
        mp4 = pathlib.Path(inf["entrega"])
        shutil.copy2(mp4, destino / f"{nombre}.mp4")
        portada = mp4.with_suffix(".portada.png")
        if portada.exists():
            shutil.copy2(portada, destino / f"{nombre}_portada.png")
        hechos.append(destino / f"{nombre}.mp4")
    return hechos


def tabla(informes: list[dict]) -> str:
    filas = ["| Pieza | Duración | LUFS / TP | A cámara | Equipo (1.er B-roll o pastilla) | Avisos | Archivo |",
             "|---|---|---|---|---|---|---|"]
    for i in informes:
        m, b = i["entrega_medida"], i["contra_brief"]
        dur = f"{m['duracion_s']:.1f} s" + ("" if b["duracion_en_rango"] else " ⚠ fuera de 45–60 s")
        equipo = "—" if b["equipo_primer_b_roll_o_pastilla_s"] is None else \
            f"{b['equipo_primer_b_roll_o_pastilla_s']:.1f} s" + ("" if b["equipo_en_5s"] else " ⚠")
        av = "<br>".join(avisos(i["armado"])) or "—"
        if not i.get("verificacion_ok", True):
            av = "⚠ la verificación falló<br>" + av
        filas.append(f"| {i['codigo']} {i['pieza']} | {dur} | {m['lufs_integrado']} / {m['true_peak_dbtp']} | {b['a_camara_pct']} % | "
                     f"{equipo} | {av} | `{pathlib.Path(i['entrega']).name}` |")
    return "\n".join(filas)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--calidad", choices=list(piloto.CALIDADES), default="baja")
    ap.add_argument("--videos", help="números de video del brief, por ejemplo 6,8")
    ap.add_argument("--piezas", help="solo estas piezas, por ejemplo H1")
    ap.add_argument("--planes", nargs="+", help="planes puntuales en lugar de buscar Video */_EDICION/plan.json")
    ap.add_argument("--solo-entregar", action="store_true", help="no renderiza: empaqueta lo último en alta")
    a = ap.parse_args()
    videos = {int(x) for x in a.videos.split(",")} if a.videos else None
    lista = planes(videos, a.planes)
    if not lista:
        sys.exit("No hay planes: se buscan en <raiz>/Video N — …/_EDICION/plan.json (o pasalos con --planes).")

    informes = []
    for plan in lista:
        codigo = piloto.nombre_base(json.loads(plan.read_text(encoding="utf-8")))
        if a.solo_entregar:
            informes += list(ultimas_altas(codigo).values())
        else:
            print(f"\n=== {codigo} ({plan}) · calidad {a.calidad}", flush=True)
            informes += piloto.producir(plan, a.calidad, a.piezas)
        if a.solo_entregar or a.calidad == "alta":
            for f in entregar(codigo):
                print(f"Entrega: {f}")

    calidad = "alta" if a.solo_entregar else a.calidad
    md = f"# Resumen · calidad {calidad} · {datetime.datetime.now():%Y-%m-%d %H:%M}\n\n" + tabla(informes) + "\n"
    (SALIDAS / f"resumen_{calidad}.md").write_text(md, encoding="utf-8")
    print("\n" + md)


if __name__ == "__main__":
    main()
