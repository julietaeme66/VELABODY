"""Transcribe clips con tiempos por palabra (faster-whisper).

Uso:
    python transcribir.py <carpeta_o_archivo> [--salida <carpeta>] [--modelo large-v3] [--desde SEG]

--desde: transcribe solo a partir de ese segundo (cuando hay varias tomas pegadas y Whisper las mezcla);
         genera <clip>.desde<SEG>.words.json con tiempos absolutos.

Genera un <clip>.words.json por archivo con segmentos y palabras (inicio/fin en segundos).
"""
import argparse
import json
import os
import pathlib
import subprocess

# DLLs de CUDA instaladas por pip (nvidia-cublas-cu12 / nvidia-cudnn-cu12)
try:
    import nvidia
    for base in nvidia.__path__:
        for bin_dir in pathlib.Path(base).glob("*/bin"):
            os.add_dll_directory(str(bin_dir))
            os.environ["PATH"] = str(bin_dir) + os.pathsep + os.environ["PATH"]
except ImportError:
    pass

import numpy as np
from faster_whisper import WhisperModel

EXT_VIDEO = {".mp4", ".mov", ".mxf", ".m4v", ".wav", ".mp3"}


def extraer_audio(src: pathlib.Path, desde: float = 0.0) -> np.ndarray:
    """Audio mono 16 kHz float32 (se decodifica con ffmpeg, no con PyAV)."""
    pcm = subprocess.run(
        ["ffmpeg", "-v", "error", "-ss", f"{desde:.3f}", "-i", str(src), "-vn", "-ac", "1", "-ar", "16000", "-f", "s16le", "-"],
        check=True, capture_output=True,
    ).stdout
    return np.frombuffer(pcm, np.int16).astype(np.float32) / 32768.0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("entrada")
    ap.add_argument("--salida")
    ap.add_argument("--modelo", default="large-v3")
    ap.add_argument("--desde", type=float, default=0.0)
    args = ap.parse_args()

    entrada = pathlib.Path(args.entrada)
    archivos = [entrada] if entrada.is_file() else sorted(
        p for p in entrada.iterdir() if p.suffix.lower() in EXT_VIDEO
    )
    salida = pathlib.Path(args.salida) if args.salida else (entrada.parent if entrada.is_file() else entrada) / "_EDICION" / "transcripciones"
    salida.mkdir(parents=True, exist_ok=True)

    try:
        modelo = WhisperModel(args.modelo, device="cuda", compute_type="float16")
    except Exception:
        modelo = WhisperModel(args.modelo, device="cpu", compute_type="int8")

    for src in archivos:
        sufijo = f".desde{args.desde:g}" if args.desde else ""
        destino = salida / f"{src.stem}{sufijo}.words.json"
        if destino.exists():
            print(f"[skip] {src.name}")
            continue
        segmentos, info = modelo.transcribe(
            extraer_audio(src, args.desde), language="es", word_timestamps=True, vad_filter=True
        )
        datos = {"archivo": str(src), "duracion": info.duration, "segmentos": []}
        for s in segmentos:
            datos["segmentos"].append({
                "inicio": round(s.start + args.desde, 3),
                "fin": round(s.end + args.desde, 3),
                "texto": s.text.strip(),
                "palabras": [
                    {"w": w.word.strip(), "i": round(w.start + args.desde, 3), "f": round(w.end + args.desde, 3), "p": round(w.probability, 3)}
                    for w in (s.words or [])
                ],
            })
        destino.write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")
        texto = " ".join(s["texto"] for s in datos["segmentos"])
        print(f"[ok] {src.name}: {texto[:160]}")


if __name__ == "__main__":
    main()
