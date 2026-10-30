import { Sequence } from "remotion";
import { COMP, FAMILIAS, VIOLETA } from "../estilo";
import type { Subtitulo as SubT } from "../tipos";

// Subtítulos quemados (en Premiere eran pistas nativas con estilos de pista). Una línea, a altura fija,
// como se habla. Sobre B-roll: caja #6F04BA (Montserrat Medium 58). A cámara: blanco con brillo violeta
// leve (Gotham Book 49). Medidas tomadas del aprobado: config › compositor.subtitulos.
const Subtitulo: React.FC<{ s: SubT }> = ({ s }) => {
  const cs = COMP.subtitulos;
  if (s.estilo === "fondo") {
    const e = cs.fondo;
    const w = s.w ?? 0;
    return (
      <svg width={1080} height={1920} style={{ position: "absolute", inset: 0 }}>
        <rect x={540 - w / 2} y={cs.centro_y - e.alto_caja / 2} width={w} height={e.alto_caja} rx={e.radio} fill={VIOLETA} />
        <text
          x={540}
          y={cs.centro_y + e.base_dy}
          textAnchor="middle"
          fill="#FFFFFF"
          style={{ fontFamily: FAMILIAS.subsFondo, fontSize: e.px, letterSpacing: `${e.tracking_em}em` }}
        >
          {s.texto}
        </text>
      </svg>
    );
  }
  const e = cs.camara;
  return (
    <svg width={1080} height={1920} style={{ position: "absolute", inset: 0 }}>
      <defs>
        {/* halo amplio y suave más uno cercano, como el sombreado de Premiere del aprobado */}
        <filter id="brillo-camara" x="-30%" y="-150%" width="160%" height="400%">
          {e.brillo.map((b, i) => (
            <feDropShadow key={i} dx={0} dy={0} stdDeviation={b.desvio_px} floodColor={VIOLETA} floodOpacity={b.opacidad} result={`s${i}`} />
          ))}
        </filter>
      </defs>
      <text
        x={540}
        y={cs.centro_y + e.base_dy}
        textAnchor="middle"
        fill="#FFFFFF"
        filter="url(#brillo-camara)"
        style={{ fontFamily: FAMILIAS.subsCamara, fontSize: e.px, letterSpacing: `${e.tracking_em}em` }}
      >
        {s.texto}
      </text>
    </svg>
  );
};

export const Subtitulos: React.FC<{ subs: SubT[] }> = ({ subs }) => (
  <>
    {subs.map((s, i) => (
      <Sequence key={i} from={s.desde} durationInFrames={Math.max(1, s.hasta - s.desde)} layout="none">
        <Subtitulo s={s} />
      </Sequence>
    ))}
  </>
);
