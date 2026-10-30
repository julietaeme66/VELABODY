import { Sequence, interpolate, useCurrentFrame } from "remotion";
import { COMP } from "../estilo";
import type { Desenfoque as DesenfoqueT } from "../tipos";

// Fondo cargado (wiki › títulos, opción 2): se desenfoca un poco el video solo en la zona del gráfico,
// con una máscara de borde muy suave (elipse) para que no se vea el recorte. Entra y sale con el gráfico.
const Zona: React.FC<{ z: DesenfoqueT }> = ({ z }) => {
  const frame = useCurrentFrame();
  const c = COMP.desenfoque_fondo;
  const dur = z.hasta - z.desde;
  const opacidad = interpolate(frame, [0, c.entrada_cuadros, dur - c.entrada_cuadros, dur], [0, 1, 1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const mascara = "radial-gradient(ellipse 50% 50% at 50% 50%, black 55%, transparent 100%)";
  return (
    <div
      style={{
        position: "absolute",
        left: z.x,
        top: z.y,
        width: z.w,
        height: z.h,
        opacity: opacidad,
        backdropFilter: `blur(${c.px}px)`,
        WebkitBackdropFilter: `blur(${c.px}px)`,
        maskImage: mascara,
        WebkitMaskImage: mascara,
      }}
    />
  );
};

export const Desenfoques: React.FC<{ zonas: DesenfoqueT[] }> = ({ zonas }) => (
  <>
    {zonas.map((z, i) => (
      <Sequence key={i} from={z.desde} durationInFrames={Math.max(1, z.hasta - z.desde)} layout="none">
        <Zona z={z} />
      </Sequence>
    ))}
  </>
);
