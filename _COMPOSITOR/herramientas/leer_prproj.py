"""Lee un proyecto de Premiere (.prproj) y vuelca la línea de tiempo de una secuencia a JSON.

Para analizar ediciones validadas sin abrir Premiere: por cada pista, cada clip con su nombre, medio,
tiempos (en segundos y cuadros a 30 fps) y la cadena de efectos con sus parámetros y keyframes.
Los tiempos de Premiere están en "ticks" (254016000000 por segundo).

Uso:
    python leer_prproj.py <proyecto.prproj> <salida.json> [--secuencia "texto del nombre"]
"""
import argparse
import gzip
import json
import pathlib
import sys
import xml.etree.ElementTree as ET

TICKS = 254016000000


def cargar(ruta: pathlib.Path) -> ET.Element:
    datos = ruta.read_bytes()
    if datos[:2] == b"\x1f\x8b":
        datos = gzip.decompress(datos)
    return ET.fromstring(datos)


class Proyecto:
    def __init__(self, raiz: ET.Element):
        self.por_id = {e.get("ObjectID"): e for e in raiz if e.get("ObjectID")}
        self.por_uid = {e.get("ObjectUID"): e for e in raiz if e.get("ObjectUID")}
        self.raiz = raiz

    def ref(self, e: ET.Element | None) -> ET.Element | None:
        if e is None:
            return None
        if e.get("ObjectRef"):
            return self.por_id.get(e.get("ObjectRef"))
        if e.get("ObjectURef"):
            return self.por_uid.get(e.get("ObjectURef"))
        return e

    def hijo(self, e: ET.Element | None, ruta: str) -> ET.Element | None:
        """Sigue una ruta tipo "A/B/C" resolviendo referencias en cada paso."""
        for paso in ruta.split("/"):
            if e is None:
                return None
            e = self.ref(e.find(paso))
        return e

    def texto(self, e: ET.Element | None, ruta: str) -> str | None:
        x = e.find(ruta) if e is not None else None
        return x.text if x is not None else None


def keyframes(param: ET.Element) -> list | None:
    """'tiempo,valor,...;tiempo,valor,...' → [(segundos desde el inicio del clip, valor), ...]."""
    k = param.findtext("Keyframes")
    if not k:
        return None
    salida = []
    for bloque in k.strip(";").split(";"):
        partes = bloque.split(",")
        try:
            salida.append({"t_s": round(int(partes[0]) / TICKS, 4), "valor": partes[1]})
        except (ValueError, IndexError):
            salida.append({"crudo": bloque})
    return salida


def efectos(p: Proyecto, item: ET.Element) -> list[dict]:
    cadena = p.hijo(item, "ClipTrackItem/ComponentOwner/Components") or p.hijo(item, "ComponentOwner/Components")
    if cadena is None:
        return []
    comps = cadena.find("ComponentChain/Components")
    salida = []
    for c in (comps if comps is not None else []):
        comp = p.ref(c)
        if comp is None:
            continue
        info = {"efecto": comp.findtext("MatchName"), "nombre": comp.findtext("Component/DisplayName"),
                "instancia": comp.findtext("Component/InstanceName"),
                "desactivado": comp.findtext("Component/Bypass") == "true", "parametros": []}
        for prm in comp.findall("Component/Params/Param"):
            v = p.ref(prm)
            if v is None:
                continue
            nombre = v.findtext("Name")
            dato = {"nombre": nombre, "valor": v.findtext("StartKeyframe") or v.findtext("CurrentValue")}
            k = keyframes(v)
            if k and len(k) > 1:
                dato["keyframes"] = k
            if nombre or k:
                info["parametros"].append(dato)
        salida.append(info)
    return salida


def secuencia(p: Proyecto, filtro: str | None) -> dict:
    seqs = [e for e in p.raiz.iter("Sequence") if e.get("ObjectUID") and e.findtext("Name")]
    if filtro:
        seqs = [s for s in seqs if filtro.lower() in s.findtext("Name").lower()]
    if not seqs:
        raise SystemExit("No encontré la secuencia")
    seq = seqs[0]
    resultado = {"secuencia": seq.findtext("Name"), "pistas": []}
    for tg in seq.findall("TrackGroups/TrackGroup"):
        grupo = p.ref(tg.find("Second"))
        if grupo is None:
            continue
        tipo = "video" if grupo.tag.startswith("Video") else "audio"
        for k, tr in enumerate(grupo.findall("TrackGroup/Tracks/Track")):
            pista = p.ref(tr)
            items = pista.find("ClipTrack/ClipItems/TrackItems") if pista is not None else None
            clips = []
            for it in (items if items is not None else []):
                item = p.ref(it)
                if item is None:
                    continue
                ti = item.find("ClipTrackItem/TrackItem")
                ini, fin = int(ti.findtext("Start") or 0), int(ti.findtext("End") or 0)
                sub = p.hijo(item, "ClipTrackItem/SubClip")
                nombre = sub.findtext("Name") if sub is not None else None
                clip = p.hijo(sub, "Clip") if sub is not None else None
                entrada = clip.findtext("Clip/InPoint") if clip is not None else None
                medio = None
                fuente = p.hijo(clip, "Clip/Source") if clip is not None else None
                if fuente is not None:
                    m = p.hijo(fuente, "MediaSource/Media")
                    if m is not None:
                        medio = m.findtext("Title") or m.findtext("FilePath")
                clips.append({"nombre": nombre, "medio": medio, "desde_s": round(ini / TICKS, 4), "hasta_s": round(fin / TICKS, 4),
                              "desde_cuadro": round(ini / TICKS * 30), "hasta_cuadro": round(fin / TICKS * 30),
                              "in_s": round(int(entrada) / TICKS, 4) if entrada else None,
                              "efectos": efectos(p, item) if tipo == "video" else []})
            resultado["pistas"].append({"tipo": tipo, "n": k + 1, "clips": clips})
    return resultado


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("proyecto")
    ap.add_argument("salida")
    ap.add_argument("--secuencia")
    a = ap.parse_args()
    p = Proyecto(cargar(pathlib.Path(a.proyecto)))
    if not a.secuencia:
        for s in p.raiz.iter("Sequence"):
            if s.findtext("Name"):
                print("secuencia:", s.findtext("Name"))
    r = secuencia(p, a.secuencia)
    pathlib.Path(a.salida).write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
    for pista in r["pistas"]:
        print(f"{pista['tipo']} {pista['n']}: " + " | ".join(
            f"{c['nombre']} {c['desde_s']:.2f}-{c['hasta_s']:.2f}" for c in pista["clips"]))


if __name__ == "__main__":
    main()
