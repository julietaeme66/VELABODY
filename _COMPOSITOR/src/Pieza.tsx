import { Audio } from "@remotion/media";
import { useEffect, useState } from "react";
import { AbsoluteFill, Sequence, continueRender, delayRender, interpolate, staticFile, useCurrentFrame } from "remotion";
import { ClipEnLinea } from "./componentes/ClipVideo";
import { GraficoEnLinea } from "./componentes/Graficos";
import { ConPanLeft } from "./componentes/PanLeft";
import { Subtitulos } from "./componentes/Subtitulos";
import { cargarFuentes } from "./estilo";
import type { PistaAudio, Timeline } from "./tipos";

export type PiezaProps = { timeline: Timeline | null; zonaSegura?: boolean };

const Pista: React.FC<{ a: PistaAudio }> = ({ a }) => {
  const frame = useCurrentFrame();
  const dur = a.dur ?? 0;
  const fade = a.fadeFinal ?? 0;
  const volumen = fade > 0 ? a.volumen * interpolate(frame, [dur - fade, dur], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }) : a.volumen;
  return <Audio src={staticFile(a.src)} trimBefore={a.trim} volume={volumen} />;
};

// Orden de capas, como la secuencia v2 de Premiere: A-roll, B-roll, pastilla, (persona recortada para el
// sándwich), títulos; todo eso pasa por el Pan Left. Arriba, los subtítulos. La zona segura solo se ve en
// Studio (prop zonaSegura), nunca en el render.
export const Pieza: React.FC<PiezaProps> = ({ timeline, zonaSegura }) => {
  const [fuentes] = useState(() => delayRender("Cargando fuentes VELABODY"));
  useEffect(() => {
    cargarFuentes().then(() => continueRender(fuentes));
  }, [fuentes]);
  if (!timeline) return <AbsoluteFill style={{ backgroundColor: "black" }} />;
  const cortes = new Set(timeline.transiciones.map((t) => t.cuadro));
  const terminaEnCorte = (hasta: number) => cortes.has(hasta) || hasta >= timeline.duracion;
  const pastillas = timeline.graficos.filter((g) => g.tipo === "pastilla");
  const titulos = timeline.graficos.filter((g) => g.tipo === "titulo");
  return (
    <AbsoluteFill style={{ backgroundColor: "black" }}>
      <ConPanLeft trs={timeline.transiciones}>
        {timeline.videos.filter((v) => v.capa === "aroll").map((v, i) => <ClipEnLinea key={`a${i}`} {...v} muted={false} />)}
        {timeline.videos.filter((v) => v.capa === "broll").map((v, i) => <ClipEnLinea key={`b${i}`} {...v} muted />)}
        {pastillas.map((g, i) => <GraficoEnLinea key={`p${i}`} g={g} terminaEnCorte={terminaEnCorte(g.hasta)} />)}
        {timeline.sandwich.map((s, i) => <ClipEnLinea key={`s${i}`} {...s} muted alfa />)}
        {titulos.map((g, i) => <GraficoEnLinea key={`t${i}`} g={g} terminaEnCorte={terminaEnCorte(g.hasta)} />)}
      </ConPanLeft>
      <Subtitulos subs={timeline.subtitulos} />
      {zonaSegura ? <AbsoluteFill style={{ backgroundImage: `url(${staticFile("zona-segura.png")})`, opacity: 0.5 }} /> : null}
      {timeline.voces.map((v, i) => (
        <Sequence key={`v${i}`} from={v.desde} durationInFrames={v.dur}>
          <Audio src={staticFile(v.src)} trimBefore={v.trim} />
        </Sequence>
      ))}
      {timeline.audio.map((a, i) => (
        <Sequence key={`au${i}`} from={a.desde} durationInFrames={a.dur} layout="none">
          <Pista a={a} />
        </Sequence>
      ))}
    </AbsoluteFill>
  );
};
