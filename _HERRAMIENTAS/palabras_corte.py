"""Muestra las palabras de cada corte de A-roll de un armado con su tiempo en la línea de tiempo.
Uso: python palabras_corte.py <armado.json>"""
import glob, json, pathlib, sys

armado = pathlib.Path(sys.argv[1])
a = json.loads(armado.read_text(encoding="utf-8"))
trans = armado.parent / "transcripciones"
for x in a["aroll"]:
    nombre = x["clip"].split("/")[-1]
    cands = sorted(trans.glob(f"{nombre}.desde*.words.json")) or [trans / f"{nombre}.words.json"]
    d = json.loads(cands[0].read_text(encoding="utf-8"))
    out, prev = [], None
    for s in d["segmentos"]:
        for w in s["palabras"]:
            if w["i"] < x["in"] - 0.05 or w["f"] > x["out"] + 0.1:
                continue
            if prev is not None and w["i"] - prev > 0.3:
                out.append(f"[{w['i'] - prev:.2f}]")
            out.append(f"{w['w']}@{x['t'] + w['i'] - x['in']:.2f}")
            prev = w["f"]
    print(f"\n## {nombre} t={x['t']:.2f} in={x['in']:.2f} out={x['out']:.2f}\n" + " ".join(out))
