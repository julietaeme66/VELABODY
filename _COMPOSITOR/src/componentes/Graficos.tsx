import { Sequence, interpolate, useCurrentFrame } from "remotion";
import { COMP, FAMILIAS, VIOLETA, progresoEntrada } from "../estilo";
import type { Pastilla as PastillaT, Titulo as TituloT } from "../tipos";

// Salida: si el gráfico termina en un corte con Pan Left, lo corta la transición (así en el aprobado);
// si termina en mitad de un plano, se funde en pocos cuadros en vez de desaparecer de golpe.
const opacidadSalida = (frame: number, dur: number, fundido: number) =>
  fundido > 0 ? interpolate(frame, [dur - fundido, dur], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }) : 1;

// Fondo cargado (wiki › títulos): sombra paralela leve, que tiene que notarse en la lectura, no como sombra.
const estiloGrafico = (opacidad: number, sombra?: boolean): React.CSSProperties => {
  const s = COMP.sombra_fondo_cargado;
  const alfa = Math.round(s.opacidad * 255).toString(16).padStart(2, "0");
  return {
    position: "absolute",
    inset: 0,
    opacity: opacidad,
    filter: sombra ? `drop-shadow(0px ${s.dy}px ${s.desenfoque}px ${s.color}${alfa})` : undefined,
  };
};

// Título "paquetito" (equivalente del MOGRT Ease Position & Mask Y - Bottom): Montserrat Medium en
// mayúsculas, violeta, entra subiendo desde una máscara cuyo borde inferior es la línea de base. El borde
// baja con la entrada hasta dejar lugar a los descendentes (la cola de la Q en "QUE"), sin cortarlos al final.
const DESCENDENTE_EM = 0.25;

export const Titulo: React.FC<{ g: TituloT; fundido: number }> = ({ g, fundido }) => {
  const frame = useCurrentFrame();
  const c = COMP.titulo;
  const p = progresoEntrada(frame, c.entrada);
  const dy = (1 - p) * c.recorrido_em * g.fontPx;
  const id = `mascara-titulo-${g.desde}-${g.base}`;
  return (
    <svg width={1080} height={1920} style={estiloGrafico(opacidadSalida(frame, g.hasta - g.desde, fundido), g.sombra)}>
      <defs>
        <clipPath id={id}>
          <rect x={0} y={0} width={1080} height={g.base + DESCENDENTE_EM * g.fontPx * p} />
        </clipPath>
      </defs>
      <g clipPath={`url(#${id})`}>
        <text
          x={g.x}
          y={g.base + dy}
          textAnchor="middle"
          fill={VIOLETA}
          style={{ fontFamily: FAMILIAS.titulo, fontSize: g.fontPx, letterSpacing: `${c.tracking_em}em` }}
        >
          {g.texto}
        </text>
      </g>
    </svg>
  );
};

// Pastilla (equivalente del MOGRT 1-Line Fill Text Box - Up): caja violeta con puntas redondas que crece
// desde su borde inferior; el texto blanco sube con el borde superior y queda recortado por la caja.
export const Pastilla: React.FC<{ g: PastillaT; fundido: number }> = ({ g, fundido }) => {
  const frame = useCurrentFrame();
  const c = COMP.pastilla;
  const p = progresoEntrada(frame, c.entrada);
  const h = g.h * p;
  const abajo = g.cy + g.h / 2;
  const arriba = abajo - h;
  const x = g.cx - g.w / 2;
  const base = g.cy + c.texto_dy_px + (0.7 * g.fontPx) / 2 + (g.h - h);
  const id = `caja-pastilla-${g.desde}`;
  if (h <= 0.01) return null;
  return (
    <svg width={1080} height={1920} style={estiloGrafico(opacidadSalida(frame, g.hasta - g.desde, fundido), g.sombra)}>
      <defs>
        <clipPath id={id}>
          <rect x={x} y={arriba} width={g.w} height={h} rx={Math.min(h, g.h) / 2} />
        </clipPath>
      </defs>
      <rect x={x} y={arriba} width={g.w} height={h} rx={Math.min(h, g.h) / 2} fill={VIOLETA} />
      <g clipPath={`url(#${id})`}>
        <text
          x={g.cx}
          y={base}
          textAnchor="middle"
          fill="#FFFFFF"
          style={{ fontFamily: FAMILIAS.pastilla, fontSize: g.fontPx, fontWeight: c.peso, letterSpacing: `${c.tracking_em}em` }}
        >
          {g.texto}
        </text>
      </g>
    </svg>
  );
};

export const GraficoEnLinea: React.FC<{ g: TituloT | PastillaT; terminaEnCorte: boolean }> = ({ g, terminaEnCorte }) => {
  const fundido = terminaEnCorte ? 0 : COMP.pastilla.salida_fundido_cuadros;
  return (
    <Sequence from={g.desde} durationInFrames={g.hasta - g.desde} layout="none">
      {g.tipo === "titulo" ? <Titulo g={g} fundido={fundido} /> : <Pastilla g={g} fundido={fundido} />}
    </Sequence>
  );
};
