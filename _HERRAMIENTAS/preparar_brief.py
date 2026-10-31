"""Lee el brief de edición (.pdf o .docx, con una tabla por video y links de Drive), baja el material
y arma una carpeta por video con lo que le corresponde.

Uso:
    python preparar_brief.py <brief.pdf|brief.docx> [--videos 6,7,8] [--solo-carpetas]

--videos: solo los videos indicados
--solo-carpetas: arma las carpetas y las fichas sin bajar nada

La raíz es la de velabody.py (config_local.json › raiz o VELABODY_RAIZ). Estructura que crea:
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

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))     # con python -I no está
import velabody  # noqa: E402  (raíz de esta compu: config_local.json)

RAIZ = velabody.RAIZ
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


def leer_brief_pdf(ruta: pathlib.Path) -> tuple[list[dict], str]:
    """El mismo brief en PDF (como el de los Videos 6 a 16). Devuelve (videos, lineamientos):
    - videos: igual que leer_brief(); el título es la línea "Video N — …" (y la siguiente si se partió);
      las tablas siguen al último título, aunque continúen en la página siguiente (con el encabezado
      repetido o con una fila partida); cada link de Drive va a la celda que lo contiene (por coordenadas);
      los links fuera de las tablas son extras ("Más inserts disponibles…").
    - lineamientos: el texto general del brief antes de las fichas (duración, B-roll, nombres de archivo…)."""
    import pdfplumber
    videos, actual, lineamientos = [], None, []
    drive_id = lambda uri: (re.search(r"/d/([^/]+)", uri or "") or [None, None])[1]
    with pdfplumber.open(str(ruta)) as pdf:
        for pg in pdf.pages:
            tablas = pg.find_tables()
            dentro = lambda y: any(t.bbox[1] - 2 <= y <= t.bbox[3] + 2 for t in tablas)
            links = [{"id": drive_id(h.get("uri")), "x": (h["x0"] + h["x1"]) / 2, "y": (h["top"] + h["bottom"]) / 2,
                      "texto": (pg.crop((h["x0"] - 1, h["top"] - 1, h["x1"] + 1, h["bottom"] + 1)).extract_text() or "").strip()}
                     for h in pg.hyperlinks if drive_id(h.get("uri"))]
            # títulos, extras y tablas, en el orden en que aparecen en la página
            eventos = [("tabla", t.bbox[1], t) for t in tablas]
            lineas = [l for l in pg.extract_text_lines() if not dentro(l["top"])]
            for k, l in enumerate(lineas):
                eventos.append(("linea", l["top"], (l, lineas[k + 1] if k + 1 < len(lineas) else None)))
            for tipo, _, x in sorted(eventos, key=lambda e: e[1]):
                if tipo == "linea":
                    l, siguiente = x
                    m = re.match(r"Video (\d+) — (.+)", l["text"])
                    if m:
                        titulo = l["text"]
                        # título partido en dos renglones: la línea siguiente, si está pegada y no es otra cosa
                        if siguiente and siguiente["top"] - l["bottom"] < 6 and not re.match(r"Video \d+ —", siguiente["text"]):
                            titulo += " " + siguiente["text"]
                        actual = {"video": int(m.group(1)), "titulo": titulo, "bloques": [], "extras": []}
                        videos.append(actual)
                    elif actual is None:
                        lineamientos.append(l["text"])
                    else:
                        propios = [{"texto": e["texto"], "id": e["id"]} for e in links if l["top"] - 2 <= e["y"] <= l["bottom"] + 2]
                        if propios:
                            actual["extras"].append({"texto": l["text"], "links": propios})
                    continue
                if actual is None:
                    continue
                for fila, celdas in zip(x.extract(), x.rows):
                    fila = [(c or "").replace("\n", " ").strip() for c in fila]
                    if fila[0] == "#" or len(fila) < 5:            # encabezado (se repite en cada página)
                        continue
                    def en(c):
                        bb = celdas.cells[c]
                        return [{"texto": e["texto"], "id": e["id"]} for e in links
                                if bb and bb[0] <= e["x"] <= bb[2] and bb[1] <= e["y"] <= bb[3]]
                    if not fila[0] and actual["bloques"]:          # fila partida entre dos páginas
                        b = actual["bloques"][-1]
                        for clave, c in (("inserts_sug", 1), ("texto", 2), ("clip", 3), ("indicacion", 4)):
                            b[clave] = (b[clave] + " " + fila[c]).strip()
                        b["links_insert"] += en(1)
                        b["links_clip"] += en(3)
                        continue
                    actual["bloques"].append({"bloque": fila[0], "inserts_sug": fila[1], "texto": fila[2],
                                              "clip": fila[3], "indicacion": fila[4],
                                              "links_insert": en(1), "links_clip": en(3)})
    return videos, "\n".join(lineamientos)


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
    enseguida con archivos 4K: 'Google Drive - Quota exceeded'). Sin rclone, con curl (anónima)."""
    if destino.exists() and destino.stat().st_size == total:
        return f"ya estaba  {destino.name}"
    if not shutil.which("rclone"):
        tmp = destino.parent / f".bajando_{i}"
        for _ in range(3):
            subprocess.run(["curl", "-sL", "-m", "3600", "-o", str(tmp), URL.format(i)], capture_output=True)
            if tmp.exists() and (total is None or tmp.stat().st_size == total):
                tmp.replace(destino)
                return f"OK  {destino.name}  ({destino.stat().st_size / 1e6:.0f} MB)"
        tmp.unlink(missing_ok=True)
        return f"✖ FALLÓ {destino.name} (sin rclone; Drive puede haber cortado la descarga anónima por cuota)"
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
    if brief.suffix.lower() == ".pdf":
        videos, lineamientos = leer_brief_pdf(brief)
    else:
        videos, lineamientos = leer_brief(brief), ""
    if "--videos" in sys.argv:
        elegidos = {int(x) for x in sys.argv[sys.argv.index("--videos") + 1].split(",")}
        videos = [v for v in videos if v["video"] in elegidos]
    BRUTO.mkdir(exist_ok=True)
    (BRUTO / "brief.json").write_text(json.dumps(videos, ensure_ascii=False, indent=1), encoding="utf-8")
    if lineamientos:      # lo general del brief (duración, B-roll, nombres de archivo, portada…), para revisar cada video
        (BRUTO / "brief_lineamientos.md").write_text(lineamientos + "\n", encoding="utf-8")

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
