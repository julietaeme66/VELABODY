import { Composition, staticFile } from "remotion";
import { Calibracion, type CalibracionProps } from "./Calibracion";
import { Pieza, type PiezaProps } from "./Pieza";
import type { Timeline } from "./tipos";

// El timeline se lee de la carpeta pública (lo escribe adaptar_armado.py); la duración sale de ahí.
const cargarTimeline = async ({ props }: { props: PiezaProps }) => {
  const timeline: Timeline = props.timeline ?? (await (await fetch(staticFile("timeline.json"))).json());
  return { durationInFrames: timeline.duracion, fps: timeline.fps, width: timeline.ancho, height: timeline.alto, props: { ...props, timeline } };
};

export const RemotionRoot: React.FC = () => (
  <>
    <Composition
      id="VelabodyPieza"
      component={Pieza}
      width={1080}
      height={1920}
      fps={30}
      durationInFrames={30}
      defaultProps={{ timeline: null, zonaSegura: false } as PiezaProps}
      calculateMetadata={cargarTimeline}
    />
    <Composition
      id="Calibracion"
      component={Calibracion}
      width={1080}
      height={1920}
      fps={30}
      durationInFrames={830}
      defaultProps={{ fondo: "gris" } as CalibracionProps}
    />
  </>
);
