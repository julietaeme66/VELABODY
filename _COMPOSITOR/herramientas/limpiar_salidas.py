"""Libera espacio en _COMPOSITOR_SALIDAS: deja, por pieza, solo la última versión en alta (render, _norm, informe,
verificación, hoja y portada) y manda todo lo demás a la Papelera de Windows (versiones anteriores, _baja,
_media, previews/). Lo que ya está en _ENTREGAS no se toca. Si el disco no tiene Papelera, no borra nada.

    python limpiar_salidas.py --simular     # lista lo que se iría, con el tamaño
    python limpiar_salidas.py               # lo manda a la Papelera
"""
import argparse
import ctypes
import pathlib
import re
import sys
from ctypes import wintypes

AQUI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parents[1] / "_HERRAMIENTAS"))
import velabody  # noqa: E402

SALIDAS = velabody.RAIZ / "_COMPOSITOR_SALIDAS"
VERSION = re.compile(r"(?P<pieza>.+?)(?P<calidad>_baja|_media)?_v(?P<v>\d{3})(?:_norm)?\.")


def que_queda(archivos: list[pathlib.Path]) -> set[pathlib.Path]:
    ultima: dict[str, int] = {}
    for f in archivos:
        m = VERSION.match(f.name)
        if m and not m.group("calidad"):
            ultima[m.group("pieza")] = max(ultima.get(m.group("pieza"), 0), int(m.group("v")))
    queda = set()
    for f in archivos:
        m = VERSION.match(f.name)
        if m is None:                       # resúmenes y otros archivos sin versión
            queda.add(f)
        elif "_piloto" in m.group("pieza"):   # pruebas del piloto (ADS14_H2_piloto): no son piezas
            continue
        elif not m.group("calidad") and int(m.group("v")) == ultima.get(m.group("pieza")):
            queda.add(f)
    return queda


class SHFILEOPSTRUCTW(ctypes.Structure):
    _fields_ = [("hwnd", wintypes.HWND), ("wFunc", wintypes.UINT), ("pFrom", wintypes.LPCWSTR),
                ("pTo", wintypes.LPCWSTR), ("fFlags", ctypes.c_ushort), ("fAnyOperationsAborted", wintypes.BOOL),
                ("hNameMappings", ctypes.c_void_p), ("lpszProgressTitle", wintypes.LPCWSTR)]


def a_la_papelera(rutas: list[pathlib.Path]) -> None:
    """SHFileOperation con FOF_ALLOWUNDO: va a la Papelera (se puede recuperar)."""
    FO_DELETE, FOF_ALLOWUNDO, FOF_NOCONFIRMATION, FOF_SILENT, FOF_NOERRORUI = 3, 0x40, 0x10, 0x4, 0x400
    op = SHFILEOPSTRUCTW(wFunc=FO_DELETE, pFrom="\0".join(str(r) for r in rutas) + "\0\0",
                         fFlags=FOF_ALLOWUNDO | FOF_NOCONFIRMATION | FOF_SILENT | FOF_NOERRORUI)
    r = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(op))
    if r or op.fAnyOperationsAborted:
        raise OSError(f"SHFileOperationW devolvió {r}")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--simular", action="store_true")
    a = ap.parse_args()
    archivos = [f for f in SALIDAS.iterdir() if f.is_file()]
    queda = que_queda(archivos)
    se_va = sorted(f for f in archivos if f not in queda)
    carpetas = [d for d in SALIDAS.iterdir() if d.is_dir()]
    total = sum(f.stat().st_size for f in se_va) + sum(f.stat().st_size for d in carpetas for f in d.rglob("*") if f.is_file())
    for f in se_va:
        print(f"  se va  {f.name}  ({f.stat().st_size / 1e6:.1f} MB)")
    for d in carpetas:
        print(f"  se va  {d.name}/")
    for f in sorted(queda):
        print(f"  queda  {f.name}")
    print(f"\n{len(se_va)} archivos y {len(carpetas)} carpetas · {total / 1e9:.2f} GB")
    if a.simular or not (se_va or carpetas):
        return
    papelera = pathlib.Path(SALIDAS.anchor) / "$RECYCLE.BIN"
    if not papelera.exists():
        sys.exit(f"{SALIDAS.anchor} no tiene Papelera: no borro nada (borralo a mano si estás seguro).")
    a_la_papelera(se_va + carpetas)
    print("Enviado a la Papelera.")


if __name__ == "__main__":
    main()
