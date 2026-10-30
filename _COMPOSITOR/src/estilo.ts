// Estilo VELABODY: todo sale de _HERRAMIENTAS/config_velabody.json (la misma fuente que usa velabody.py),
// sin duplicar reglas acá.
import config from "../../_HERRAMIENTAS/config_velabody.json";
import { loadFont } from "@remotion/fonts";
import { staticFile } from "remotion";

export const CONFIG = config;
export const COMP = config.compositor;
export const VIOLETA = config.violeta;

export const FAMILIAS = {
  titulo: "VB Titulo",
  pastilla: "VB Pastilla",
  subsFondo: "VB Subs Fondo",
  subsCamara: "VB Subs Camara",
} as const;

export const cargarFuentes = () =>
  Promise.all([
    loadFont({ family: FAMILIAS.titulo, url: staticFile(`fuentes/${COMP.titulo.fuente}`) }),
    loadFont({ family: FAMILIAS.pastilla, url: staticFile(`fuentes/${COMP.pastilla.fuente}`) }),
    loadFont({ family: FAMILIAS.subsFondo, url: staticFile(`fuentes/${COMP.subtitulos.fondo.fuente}`) }),
    loadFont({ family: FAMILIAS.subsCamara, url: staticFile(`fuentes/${COMP.subtitulos.camara.fuente}`) }),
  ]);

const CURVAS: Record<string, (x: number) => number> = {
  cubic: (x) => 1 - (1 - x) ** 3,
  quint: (x) => 1 - (1 - x) ** 5,
};

// progreso 0..1 de una entrada medida en el aprobado (curva, retraso y duración en cuadros)
export const progresoEntrada = (
  cuadroRel: number,
  entrada: { curva: string; retraso_cuadros: number; cuadros: number },
) => {
  const x = Math.min(1, Math.max(0, (cuadroRel - entrada.retraso_cuadros) / entrada.cuadros));
  return CURVAS[entrada.curva](x);
};
