import { Video } from "@remotion/media";
import { OffthreadVideo, Sequence, interpolate, staticFile, useCurrentFrame } from "remotion";
import type { Caja, CajaKf } from "../tipos";

// Caja del clip en este cuadro: fija, o interpolada lineal entre dos keyframes (como el zoom lento
// del builder: dos claves lineales en Escala y Posición).
const cajaEn = (cuadro: number, caja?: Caja, kf?: CajaKf[]): Caja => {
  if (!kf || kf.length < 2) return caja!;
  const t = [kf[0].cuadro, kf[kf.length - 1].cuadro];
  const k = (campo: keyof Caja) => interpolate(cuadro, t, [kf[0][campo], kf[kf.length - 1][campo]], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return { x: k("x"), y: k("y"), w: k("w"), h: k("h") };
};

const Encuadre: React.FC<{
  src: string;
  trim: number;
  desde: number;
  caja?: Caja;
  kf?: CajaKf[];
  muted: boolean;
  alfa?: boolean;
}> = ({ src, trim, desde, caja, kf, muted, alfa }) => {
  const frame = useCurrentFrame();
  const c = cajaEn(desde + frame, caja, kf);
  const estilo: React.CSSProperties = { position: "absolute", left: c.x, top: c.y, width: c.w, height: c.h };
  return (
    <div style={estilo}>
      {alfa ? (
        // los tramos con máscara de persona traen transparencia: OffthreadVideo extrae PNG
        <OffthreadVideo src={staticFile(src)} trimBefore={trim} muted transparent style={{ width: "100%", height: "100%" }} />
      ) : (
        <Video src={staticFile(src)} trimBefore={trim} muted={muted} objectFit="fill" style={{ width: "100%", height: "100%" }} />
      )}
    </div>
  );
};

export const ClipEnLinea: React.FC<{
  src: string;
  desde: number;
  dur: number;
  trim: number;
  caja?: Caja;
  kf?: CajaKf[];
  muted: boolean;
  alfa?: boolean;
}> = (p) => (
  <Sequence from={p.desde} durationInFrames={p.dur} layout="none">
    <Encuadre src={p.src} trim={p.trim} desde={p.desde} caja={p.caja} kf={p.kf} muted={p.muted} alfa={p.alfa} />
  </Sequence>
);
