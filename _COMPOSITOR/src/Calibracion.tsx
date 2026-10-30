import { useEffect, useState } from "react";
import { AbsoluteFill, OffthreadVideo, continueRender, delayRender, staticFile } from "remotion";
import { GraficoEnLinea } from "./componentes/Graficos";
import { Subtitulos } from "./componentes/Subtitulos";
import { cargarFuentes } from "./estilo";
import type { Grafico, Subtitulo } from "./tipos";

// Calibración contra el Video 1 FINAL: los mismos gráficos del aprobado, hechos con nuestros componentes,
// en los mismos cuadros y con las medidas de Premiere (escala/posición) que reconstruimos. Con fondo gris
// se mide con herramientas/medir_referencia.py y se compara cuadro a cuadro con el aprobado; con
// fondo "aprobado" se superpone en modo diferencia para ver a ojo dónde no coincide.
// Los valores de cada gráfico salen de la medición del aprobado (ver LEEME, "Calibración").
export type CalibracionProps = { fondo: "gris" | "aprobado" };

const GRAFICOS: Grafico[] = [
  // DIAGNÓSTICO / FACIAL AVANZADO (0 s): línea 1 justificada a 852 px; la línea 2 del aprobado no estaba justificada
  { tipo: "titulo", texto: "DIAGNÓSTICO", desde: 0, hasta: 42, fontPx: 120, x: 540, base: 450 },
  { tipo: "titulo", texto: "FACIAL AVANZADO", desde: 12, hasta: 42, fontPx: 82.9, x: 540, base: 530 },
  // DERMA SCAN detrás de la cabeza (11,9 s) y reutilizada más chica (23,0 s)
  { tipo: "pastilla", texto: "DERMA SCAN", desde: 356, hasta: 386, escala: 92, cx: 545, cy: 434, fontPx: 114.26, w: 872.5, h: 166.06 },
  { tipo: "pastilla", texto: "DERMA SCAN", desde: 689, hasta: 750, escala: 67, cx: 545, cy: 434.5, fontPx: 83.21, w: 635.5, h: 120.94 },
];

const SUBS: Subtitulo[] = [
  { texto: "para crear", desde: 85, hasta: 96, estilo: "camara" },
  { texto: "a simple vista", desde: 280, hasta: 291, estilo: "fondo", w: 449.6 },
];

export const Calibracion: React.FC<CalibracionProps> = ({ fondo }) => {
  const [fuentes] = useState(() => delayRender("Cargando fuentes VELABODY"));
  useEffect(() => {
    cargarFuentes().then(() => continueRender(fuentes));
  }, [fuentes]);
  return (
    <AbsoluteFill style={{ backgroundColor: "#e4e1de" }}>
      {fondo === "aprobado" ? <OffthreadVideo src={staticFile("referencias/video1_org12_FINAL.mp4")} muted /> : null}
      <AbsoluteFill style={{ mixBlendMode: fondo === "aprobado" ? "difference" : "normal" }}>
        {GRAFICOS.map((g, i) => <GraficoEnLinea key={i} g={g} terminaEnCorte />)}
        <Subtitulos subs={SUBS} />
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
