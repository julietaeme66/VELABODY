"""Lista de palabras a resaltar en los subtítulos (el SRT no guarda colores: se pintan a mano en Premiere).

Uso:
    python resaltados.py <carpeta _EDICION>

Palabras clave: las de "resaltar" en plan.json si existe; si no, las de los títulos de cada pieza
más los nombres de equipo. Escribe palabras_resaltadas.md con el tiempo y la pista de cada subtítulo.
"""
import json
import pathlib
import re
import sys

EQUIPOS = ["Derma Scan", "Diode Laser 4D", "RF Cavi Pro", "Ice Technology", "SMART"]


def main(edicion: pathlib.Path) -> None:
    plan = json.loads((edicion / "plan.json").read_text(encoding="utf-8"))
    codigo = plan.get("codigo", plan.get("nombre", ""))
    armados = sorted(edicion.glob("armado*.json"))
    salida = [f"# {codigo} — palabras a resaltar en los subtítulos", "",
              "Pintarlas en violeta #6F04BA (o celeste #78CCD0) en la pista de subtítulos: doble clic en el subtítulo, "
              "seleccionar la palabra y cambiar el color.", ""]
    for arm in armados:
        a = json.loads(arm.read_text(encoding="utf-8"))
        claves = plan.get("resaltar") or (
            [" ".join(r["t"] for r in l) for t in a["titulos"] for l in t["lineas"]] + EQUIPOS)
        palabras = {w.lower().strip("¿?¡!.,") for c in claves for w in c.split() if len(w) > 2 or w.isupper()}
        filas = []
        for s in a["subs"]:
            res, marcada = s["texto"], False
            for w in sorted(palabras, key=len, reverse=True):
                nuevo = re.sub(rf"(?i)(?<![\w*])({re.escape(w)})(?![\w*])", r"**\1**", res)
                marcada |= nuevo != res
                res = nuevo
            if marcada:
                m, seg = divmod(int(s["i"]), 60)
                filas.append(f"| {m:02}:{seg:02} | {'B-roll' if s['tipo'] == 'broll' else 'a cámara'} | {res} |")
        salida += [f"## {a['nombre']}", "", "| Tiempo | Pista | Subtítulo |", "|---|---|---|", *filas, ""]
    destino = edicion / "palabras_resaltadas.md"
    destino.write_text("\n".join(salida), encoding="utf-8")
    print(f"{destino} · {len(armados)} piezas")


if __name__ == "__main__":
    main(pathlib.Path(sys.argv[1]))
