// La carpeta pública (proxies, fuentes, audio y timeline.json) vive fuera de Git, en
// <raiz>/_COMPOSITOR_CACHE/publico. La raíz sale de VELABODY_RAIZ o de _HERRAMIENTAS/config_local.json.
// (Remotion empaqueta este archivo: __dirname no apunta acá, por eso se parte de process.cwd(), que es
// la carpeta _COMPOSITOR desde donde se corren los comandos.)
import { Config } from "@remotion/cli/config";
import fs from "node:fs";
import path from "node:path";

const local = path.resolve(process.cwd(), "..", "_HERRAMIENTAS", "config_local.json");
const raiz =
  process.env.VELABODY_RAIZ ??
  (fs.existsSync(local) ? JSON.parse(fs.readFileSync(local, "utf-8")).raiz : null) ??
  "E:/VELABODY";

Config.setPublicDir(path.join(raiz, "_COMPOSITOR_CACHE", "publico"));
Config.setVideoImageFormat("png");
Config.setCodec("h264");
Config.setPixelFormat("yuv420p");
Config.setColorSpace("bt709");
Config.setCrf(16);
Config.setAudioCodec("aac");
Config.setAudioBitrate("320k");
