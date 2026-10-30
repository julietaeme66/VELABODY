import { useCurrentFrame } from "remotion";
import { COMP } from "../estilo";
import type { Transicion } from "../tipos";

// Equivalente del Pan Left de Mister Horse, medido cuadro a cuadro en los dos cortes del Video 1 FINAL
// (config › compositor.pan_left): la toma que sale apenas se corre a la izquierda en los 3 cuadros previos
// al corte; la que entra aparece ~500 px a la derecha y frena en 9 cuadros. El desenfoque es solo
// horizontal y sigue la velocidad. El hueco que deja el desplazamiento se rellena en espejo. Afecta video
// y gráficos, no los subtítulos (que en Premiere van en su propia pista, arriba).
const DESPLAZAMIENTO: Record<string, number> = COMP.pan_left.desplazamiento_px;
const DESENFOQUE: Record<string, number> = COMP.pan_left.desenfoque_px;

export const estadoPanLeft = (frame: number, trs: Transicion[]) => {
  for (const tr of trs) {
    const k = String(frame - tr.cuadro);
    if (k in DESPLAZAMIENTO) return { desplazamiento: DESPLAZAMIENTO[k], blur: DESENFOQUE[k] ?? 0 };
  }
  return null;
};

export const ConPanLeft: React.FC<{ trs: Transicion[]; children: React.ReactNode }> = ({ trs, children }) => {
  const frame = useCurrentFrame();
  const e = estadoPanLeft(frame, trs);
  if (!e) return <div style={{ position: "absolute", inset: 0 }}>{children}</div>;
  const copia = (dx: number, espejo: boolean) => (
    <div style={{ position: "absolute", inset: 0, transform: `translateX(${dx}px)${espejo ? " scaleX(-1)" : ""}` }}>{children}</div>
  );
  return (
    <div style={{ position: "absolute", inset: 0, overflow: "hidden" }}>
      <svg width={0} height={0} style={{ position: "absolute" }}>
        <filter id="pan-left-blur" x="-10%" y="0" width="120%" height="100%">
          <feGaussianBlur stdDeviation={`${e.blur} 0`} edgeMode="duplicate" />
        </filter>
      </svg>
      <div style={{ position: "absolute", inset: 0, filter: e.blur > 0 ? "url(#pan-left-blur)" : undefined }}>
        {/* espejo solo del lado que queda vacío */}
        {e.desplazamiento > 0 ? copia(e.desplazamiento - 1080, true) : null}
        {copia(e.desplazamiento, false)}
        {e.desplazamiento < 0 ? copia(e.desplazamiento + 1080, true) : null}
      </div>
    </div>
  );
};
