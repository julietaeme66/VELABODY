// Forma de timeline.json (lo escribe herramientas/adaptar_armado.py). Cuadros a 30 fps, px de 1080x1920.

export type Caja = { x: number; y: number; w: number; h: number };
export type CajaKf = Caja & { cuadro: number };

export type ClipVideo = {
  capa: "aroll" | "broll";
  clip: string;
  src: string;
  desde: number;
  dur: number;
  trim: number;
  caja?: Caja;
  kf?: CajaKf[];
};

export type Titulo = { tipo: "titulo"; texto: string; desde: number; hasta: number; fontPx: number; x: number; base: number; sombra?: boolean; desenfoque?: boolean };
export type Pastilla = {
  tipo: "pastilla";
  texto: string;
  desde: number;
  hasta: number;
  escala: number;
  cx: number;
  cy: number;
  fontPx: number;
  w: number;
  h: number;
  sombra?: boolean;
  desenfoque?: boolean;
};
export type Grafico = Titulo | Pastilla;

export type Subtitulo = { texto: string; desde: number; hasta: number; estilo: "fondo" | "camara"; w?: number };
export type Transicion = { tipo: "panLeft"; cuadro: number };
export type PistaAudio = { src: string; desde: number; dur?: number; trim?: number; volumen: number; fadeFinal?: number };
// tramo de A-roll recortado con la máscara de persona, que va por encima de la pastilla
// zona del fondo que se desenfoca detrás de un gráfico (fondo cargado)
export type Desenfoque = { desde: number; hasta: number; x: number; y: number; w: number; h: number };
export type Sandwich = { src: string; desde: number; dur: number; trim: number; caja?: Caja; kf?: CajaKf[] };

export type Timeline = {
  version: 1;
  nombre: string;
  fps: number;
  ancho: number;
  alto: number;
  duracion: number;
  videos: ClipVideo[];
  voces: { src: string; desde: number; dur: number; trim: number }[];
  graficos: Grafico[];
  subtitulos: Subtitulo[];
  transiciones: Transicion[];
  audio: PistaAudio[];
  sandwich: Sandwich[];
  desenfoques?: Desenfoque[];
};
