"""Lee el brief de edición (.docx con tablas por video y links de Drive), baja el material
y arma una carpeta por video con lo que le corresponde.

Uso:
    python preparar_brief.py <brief.docx> [--videos 6,7,8] [--solo-carpetas]

--videos: solo los videos indicados (los demás los edita otra persona)

Estructura que crea en E:\\VELABODY:
    _MATERIAL_BRUTO\\                      cada archivo de Drive, una sola vez
    Video N — CODIGO · Equipo tema\\
        PRESENTADORA\\  B02_Clip_C3868.MP4  (tomas a cámara, con el bloque al que van)
        B-ROLL\\        B03_Insert1_C3901.MP4
        VOZ EN OFF\\    B02_Audio1_xxx.mp3
        FOTOS\\
        guion.md        la ficha del video (bloques, texto de referencia, indicaciones)
En NTFS los archivos de cada video son enlaces duros a _MATERIAL_BRUTO (no ocupan espacio extra).
En exFAT (disco E) se copian a cada carpeta y después se borran de _MATERIAL_BRUTO.
"""
import concurrent.futures as cf
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys

import docx
from docx.oxml.ns import qn

RAIZ = pathlib.Path(r"E:\VELABODY")
BRUTO = RAIZ / "_MATERIAL_BRUTO"
URL = "https://drive.usercontent.google.com/download?id={}&export=download&confirm=t"


def texto(el) -> str:
    return "".join(x.text or "" for x in el.iter(qn("w:t"))).strip()


def leer_brief(ruta: pathlib.Path) -> list[dict]:
    d = docx.Document(str(ruta))
    rels = {k: r.target_ref for k, r in d.part.rels.items() if "hyperlink" in r.reltype}

    def links(el):
        out = []
        for h in el.iter(qn("w:hyperlink")):
            destino = rels.get(h.get(qn("r:id")), "")
            m = re.search(r"/d/([^/]+)", destino)
            if m:
                out.append({"texto": texto(h), "id": m.group(1)})
        return out

    videos, actual = [], None
    for el in d.element.body.iterchildren():
        if el.tag == qn("w:p"):
            t = texto(el)
            m = re.match(r"Video (\d+) — (.+)", t)
            if m:
                actual = {"video": int(m.group(1)), "titulo": t, "bloques": [], "extras": []}
                videos.append(actual)
            elif actual and links(el):
                actual["extras"].append({"texto": t, "links": links(el)})
        elif el.tag == qn("w:tbl") and actual:
            for fila in list(el.iter(qn("w:tr")))[1:]:
                c = list(fila.iter(qn("w:tc")))
                if len(c) >= 5:
                    actual["bloques"].append({
                        "bloque": texto(c[0]), "inserts_sug": texto(c[1]), "texto": texto(c[2]),
                        "clip": texto(c[3]), "indicacion": texto(c[4]),
                        "links_insert": links(c[1]), "links_clip": links(c[3])})
    return videos


def nombre_carpeta(titulo: str) -> str:
    # "Video 6 — ADS12 · Derma Scan: por qué incorporar Derma Scan" -> sin ":" (no válido en Windows)
    return re.sub(r'[:<>"/\\|?*]', "", titulo).strip()


def info_drive(i: str) -> dict:
    h = subprocess.run(["curl", "-sIL", "-m", "60", URL.format(i)], capture_output=True, text=True, errors="replace").stdout
    n = re.findall(r'filename="([^"]+)"', h)
    s = re.findall(r"(?i)content-length:\s*(\d+)", h)
    return {"nombre": n[-1] if n else None, "bytes": int(s[-1]) if s else None}


REMOTO = "gdrive:"   # remoto de rclone con la cuenta de Google del editor


def bajar(i: str, destino: pathlib.Path, total: int) -> str:
    """Descarga autenticada con rclone (la descarga anónima de Drive se queda sin cuota
    enseguida con archivos 4K: 'Google Drive - Quota exceeded')."""
    if destino.exists() and destino.stat().st_size == total:
        return f"ya estaba  {destino.name}"
    tmp = destino.parent / f".bajando_{i}"
    tmp.mkdir(exist_ok=True)
    for _ in range(3):
        subprocess.run(["rclone", "backend", "copyid", REMOTO, i, str(tmp) + os.sep, "--drive-acknowledge-abuse"],
                       capture_output=True)
        archivos = [p for p in tmp.iterdir() if p.is_file()]
        if archivos and archivos[0].stat().st_size == total:
            archivos[0].replace(destino)
            tmp.rmdir()
            return f"OK  {destino.name}  ({total / 1e6:.0f} MB)"
        for p in archivos:
            p.unlink()
    tmp.rmdir()
    return f"✖ FALLÓ {destino.name}"


def main() -> None:
    brief = pathlib.Path(sys.argv[1])
    solo_carpetas = "--solo-carpetas" in sys.argv
    videos = leer_brief(brief)
    if "--videos" in sys.argv:
        elegidos = {int(x) for x in sys.argv[sys.argv.index("--videos") + 1].split(",")}
        videos = [v for v in videos if v["video"] in elegidos]
    BRUTO.mkdir(exist_ok=True)
    (BRUTO / "brief.json").write_text(json.dumps(videos, ensure_ascii=False, indent=1), encoding="utf-8")

    ids = sorted({l["id"] for v in videos for b in v["bloques"] for l in b["links_insert"] + b["links_clip"]}
                 | {l["id"] for v in videos for e in v["extras"] for l in e["links"]})
    meta_path = BRUTO / "meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    faltan = [i for i in ids if i not in meta]
    with cf.ThreadPoolExecutor(12) as ex:
        for i, m in zip(faltan, ex.map(info_drive, faltan)):
            meta[i] = m
    # nombre local único (dos archivos de Drive pueden llamarse igual)
    usados = {}
    for i in ids:
        n = meta[i]["nombre"] or f"{i}.bin"
        base, ext = os.path.splitext(n)
        k = usados.get(n.lower(), 0)
        usados[n.lower()] = k + 1
        meta[i]["local"] = n if k == 0 else f"{base}_{k + 1}{ext}"
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(ids)} archivos · {sum(m['bytes'] or 0 for m in meta.values()) / 1e9:.1f} GB", flush=True)

    if not solo_carpetas:
        with cf.ThreadPoolExecutor(4) as ex:
            futuros = [ex.submit(bajar, i, BRUTO / meta[i]["local"], meta[i]["bytes"]) for i in ids]
            for n, f in enumerate(cf.as_completed(futuros), 1):
                print(f"[{n}/{len(ids)}] {f.result()}", flush=True)

    # carpetas por video
    copiados: set[pathlib.Path] = set()
    for v in videos:
        carpeta = RAIZ / nombre_carpeta(v["titulo"])
        ficha = [f"# {v['titulo']}", "", "| # | Inserts sugeridos | Texto (referencia) | Clip | Indicación | Archivos |",
                 "|---|---|---|---|---|---|"]

        def enlazar(link, sub, prefijo):
            m = meta[link["id"]]
            origen = BRUTO / m["local"]
            ext = os.path.splitext(m["local"])[1].lower()
            sub = {".mp3": "VOZ EN OFF", ".wav": "VOZ EN OFF", ".png": "FOTOS", ".jpg": "FOTOS"}.get(ext, sub)
            destino = carpeta / sub / f"{prefijo}_{re.sub(r'[^A-Za-z0-9]+', '', link['texto']) or 'Clip'}_{m['local']}"
            destino.parent.mkdir(parents=True, exist_ok=True)
            if origen.exists() and not destino.exists():
                try:
                    os.link(origen, destino)          # NTFS: enlace, no ocupa espacio extra
                except OSError:
                    shutil.copy2(origen, destino)     # exFAT (disco E): no admite enlaces, se copia
                    copiados.add(origen)
            return f"{sub}/{destino.name}"

        for b in v["bloques"]:
            pref = "B" + (b["bloque"].replace("Hook ", "H") if b["bloque"].startswith("Hook") else b["bloque"].zfill(2))
            archivos = [enlazar(l, "PRESENTADORA", pref) for l in b["links_clip"]]
            archivos += [enlazar(l, "B-ROLL", pref) for l in b["links_insert"]]
            celda = lambda s: s.replace("|", "/").replace("\n", " ")
            ficha.append(f"| {b['bloque']} | {celda(b['inserts_sug'])} | {celda(b['texto'])} | {celda(b['clip'])} | "
                         f"{celda(b['indicacion'])} | {'<br>'.join(archivos)} |")
        for e in v["extras"]:
            archivos = [enlazar(l, "B-ROLL", "EXTRA") for l in e["links"]]
            ficha += ["", f"**{e['texto']}** → " + ", ".join(archivos)]
        carpeta.mkdir(parents=True, exist_ok=True)
        (carpeta / "guion.md").write_text("\n".join(ficha) + "\n", encoding="utf-8")
        print(f"Carpeta lista: {carpeta.name}", flush=True)

    # sin enlaces (exFAT) el material quedó copiado en cada carpeta: se borra el de _MATERIAL_BRUTO
    for f in copiados:
        f.unlink(missing_ok=True)
    if copiados:
        print(f"{len(copiados)} archivos movidos de _MATERIAL_BRUTO a las carpetas de video", flush=True)


if __name__ == "__main__":
    main()
