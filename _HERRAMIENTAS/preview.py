"""Preview rápido del corte (sin títulos ni subtítulos) para revisar ritmo y B-roll
sin abrir Premiere. Lee _EDICION/armado.json y escribe _EDICION/preview_corte.mp4 (540x960).

Uso:
    python preview.py <armado.json>
"""
import json
import pathlib
import subprocess
import sys


def main(ruta: pathlib.Path) -> None:
    a = json.loads(ruta.read_text(encoding="utf-8"))
    W, H, fps = 540, 960, a["secuencia"]["fps"]
    entradas, filtros, n = [], [], 0

    def recorte(medio, x_):
        esc = max(W / medio["ancho"], H / medio["alto"]) * x_.get("zoom", 1.0)
        w = round(medio["ancho"] * esc / 2) * 2
        h = round(medio["alto"] * esc / 2) * 2
        x = min(max(0, int(x_.get("foco_x", 0.5) * w - W / 2)), w - W)
        y = min(max(0, int(x_.get("foco_y", 0.5) * h - H / 2)), h - H)
        return f"scale={w}:{h},crop={W}:{H}:{x}:{y}"

    capas = []
    for x in a["aroll"] + a["broll"]:
        m = a["medios"][x["clip"]]
        if x.get("solo_audio"):
            entradas += ["-ss", f"{x['in']:.3f}", "-t", f"{x['out'] - x['in']:.3f}", "-i", m["ruta"]]
            capas.append((n, x))
            n += 1
            continue
        entradas += ["-ss", f"{x['in']:.3f}", "-t", f"{x['out'] - x['in']:.3f}", "-i", m["ruta"]]
        filtros.append(f"[{n}:v]{recorte(m, x)},fps={fps},tpad=stop_mode=clone:stop_duration=0.2,setpts=PTS-STARTPTS+{x['t']:.3f}/TB[v{n}]")
        capas.append((n, x))
        n += 1
    filtros.append(f"color=black:s={W}x{H}:r={fps}:d={a['duracion']:.3f}[base]")
    prev = "base"
    for k, (i, x) in enumerate(capas):
        if x.get("solo_audio"):
            filtros.append(f"[{prev}]null[o{k}]")
            prev = f"o{k}"
            continue
        fin = x["t"] + x["out"] - x["in"] + 0.5 / fps     # medio cuadro de tolerancia: sin huecos por redondeo
        filtros.append(f"[{prev}][v{i}]overlay=enable='between(t,{x['t']:.4f},{fin:.4f})':eof_action=pass[o{k}]")
        prev = f"o{k}"
    # audio: voz de A-roll en su lugar
    voces = []
    for i, x in capas:
        if x in a["aroll"]:
            filtros.append(f"[{i}:a]volume={x['ganancia_db']}dB,adelay={int(x['t'] * 1000)}:all=1[a{i}]")
            voces.append(f"[a{i}]")
    filtros.append("".join(voces) + f"amix=inputs={len(voces)}:normalize=0[voz]")
    if a.get("musica"):
        entradas += ["-i", a["musica"]["ruta"]]
        filtros.append(f"[{n}:a]volume={a['musica']['db']}dB[mus];[voz][mus]amix=inputs=2:normalize=0:duration=first[aout]")
    else:
        filtros.append("[voz]anull[aout]")
    salida = ruta.parent / "preview_corte.mp4"
    cmd = ["ffmpeg", "-v", "error", "-y", *entradas, "-filter_complex", ";".join(filtros),
           "-map", f"[{prev}]", "-map", "[aout]", "-t", f"{a['duracion']:.3f}",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "26", "-c:a", "aac", "-b:a", "128k", str(salida)]
    subprocess.run(cmd, check=True)
    print(f"Preview: {salida}")


if __name__ == "__main__":
    main(pathlib.Path(sys.argv[1]))
