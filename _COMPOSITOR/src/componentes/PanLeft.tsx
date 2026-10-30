import { useCurrentFrame } from "remotion";
import { COMP } from "../estilo";
import type { Transicion } from "../tipos";

// Pan Left de Mister Horse, con los keyframes del proyecto validado (config › compositor.pan_left): dos capas
// de ajuste, 4 cuadros antes y 11 después del corte. V12 corre la imagen (la que sale acelera hacia la
// izquierda; la que entra aparece ~470 px a la derecha y frena) y rellena el hueco en espejo; V13 le aplica
// un desenfoque direccional horizontal (acá, gaussiano solo en x con σ ≈ 0,58 × el largo). Afecta video y
// gráficos, no los subtítulos (que en Premiere van en su propia pista, arriba).
const DESPLAZAMIENTO: Record<string, number> = COMP.pan_left.desplazamiento_px;
const DESENFOQUE: Record<string, number> = COMP.pan_left.desenfoque_px;
const SIGMA = COMP.pan_left.sigma_por_px_direccional;

export const estadoPanLeft = (frame: number, trs: Transicion[]) => {
  for (const tr of trs) {
    const k = String(frame - tr.cuadro);
    if (k in DESPLAZAMIENTO) return { desplazamiento: DESPLAZAMIENTO[k], blur: (DESENFOQUE[k] ?? 0) * SIGMA };
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
