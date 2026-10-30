import { useCurrentFrame } from "remotion";
import { COMP } from "../estilo";
import type { Transicion } from "../tipos";

// Equivalente del Pan Left de Mister Horse, medido en el aprobado: ~5 cuadros antes y 5 después del
// corte, la imagen se desliza a la izquierda con desenfoque horizontal (máximo en el corte) y bordes en
// espejo. Afecta video y gráficos, no los subtítulos (que en Premiere van en su propia pista, arriba).
const easeInOutCubic = (x: number) => (x < 0.5 ? 4 * x ** 3 : 1 - (-2 * x + 2) ** 3 / 2);

export const estadoPanLeft = (frame: number, trs: Transicion[]) => {
  const { cuadros_antes: antes, cuadros_despues: despues, desenfoque_max_px: blurMax } = COMP.pan_left;
  for (const tr of trs) {
    if (frame < tr.cuadro - antes || frame >= tr.cuadro + despues) continue;
    const total = antes + despues;
    const x = (frame - (tr.cuadro - antes) + 0.5) / total;
    const p = easeInOutCubic(x);
    const velocidad = 1 - Math.abs(2 * x - 1);              // 0 en los bordes, 1 en el corte
    const desplazamiento = frame < tr.cuadro ? -p * 1080 : (1 - p) * 1080;
    return { desplazamiento, blur: blurMax * velocidad ** 1.5 };
  }
  return null;
};

// Envuelve la capa de imagen: fuera de la transición la deja igual; durante, la desplaza con copias
// en espejo a los costados y le aplica desenfoque solo horizontal (filtro SVG con desvío en x).
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
      <div style={{ position: "absolute", inset: 0, filter: "url(#pan-left-blur)" }}>
        {copia(e.desplazamiento - 1080, true)}
        {copia(e.desplazamiento, false)}
        {copia(e.desplazamiento + 1080, true)}
      </div>
    </div>
  );
};
