"""Pruebas del adaptador armado.json → timeline.json.

    .venv/Scripts/python herramientas/test_adaptar_armado.py      (desde _COMPOSITOR)
"""
import copy
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import adaptar_armado as ad  # noqa: E402

MEDIOS = {
    "medios": {
        "A": {"src": "medios/A.mp4", "inicio": 4.0, "fin": 10.0, "ancho": 2160, "alto": 3840},
        "B": {"src": "medios/B.mp4", "inicio": 1.0, "fin": 6.0, "ancho": 2160, "alto": 3840},
    },
    "voces": {"A|+15.0": {"src": "medios/voz_A_+15.0dB.wav", "inicio": 4.0}},
    "audio": {"click": "audio/click.mp3", "click_silencio_inicial_s": 0.262, "musica": "audio/musica.wav"},
}

ARMADO = {
    "nombre": "prueba",
    "secuencia": {"ancho": 1080, "alto": 1920, "fps": 30},
    "duracion": 4.0,
    "estilo_v2": {"sfx_adelanto": 0.1, "sfx_transicion_db": -12, "musica_fade": 2.0},
    "audio": {"click_db": -8},
    "musica": {"ruta": "x.wav", "db": -30.0},
    "aroll": [
        {"clip": "A", "in": 5.0, "out": 6.4, "t": 0.0, "escala": 50.0, "pos": [540, 960], "ganancia_db": 15.0, "bloque": 1},
        {"clip": "A", "in": 6.4, "out": 9.0, "t": 1.4, "escala": 50.0, "pos": [540, 960], "ganancia_db": 15.0, "bloque": 1,
         "kf": [{"t": 1.4, "escala": 50.0, "pos": [540, 960]}, {"t": 4.0, "escala": 56.0, "pos": [500, 900]}]},
    ],
    "broll": [{"clip": "B", "in": 2.0, "out": 3.0, "t": 1.0, "foco_x": 0.5, "foco_y": 0.5, "zoom": 1.0, "bloque": 1}],
    "graficos": [
        {"tipo": "titulo", "t": 2.0, "fin": 3.0, "texto": "HOLA", "escala": 100.0, "pos": [540, 400.0], "bloque": 1},
    ],
    "transiciones": [{"t": 1.4, "tipo": "Pan Left"}],
    "subs": [{"i": 0.1, "f": 0.9, "texto": "hola", "tipo": "camara"}],
    "light_leaks": [],
    "titulos": [],
}


class TestAdaptador(unittest.TestCase):
    def adaptar(self, cambios=None):
        a = copy.deepcopy(ARMADO)
        for k, v in (cambios or {}).items():
            a[k] = v
        return ad.adaptar(a, MEDIOS)

    def test_escala_premiere_a_caja(self):
        # escala 50 sobre 2160x3840 centrada = el cuadro entero de la secuencia
        self.assertEqual(ad.caja_premiere(2160, 3840, 50, [540, 960]), {"x": 0.0, "y": 0.0, "w": 1080.0, "h": 1920.0})
        c = ad.caja_premiere(2160, 3840, 56, [500, 900])
        self.assertAlmostEqual(c["w"], 1209.6)
        self.assertAlmostEqual(c["x"] + c["w"] / 2, 500)

    def test_encuadrar_como_el_jsx(self):
        c = ad.caja_encuadrar({"ancho": 2160, "alto": 3840}, 1080, 1920, 0.5, 1.2, 0.5)
        self.assertAlmostEqual(c["w"], 1296)
        self.assertAlmostEqual(c["x"], -108)
        # un foco extremo no deja bordes: se limita al desplazamiento posible
        c = ad.caja_encuadrar({"ancho": 2160, "alto": 3840}, 1080, 1920, 0.0, 1.2, 0.5)
        self.assertAlmostEqual(c["x"], 0)

    def test_cuadros_contiguos_y_trim(self):
        tl = self.adaptar()
        a0, a1 = [v for v in tl["videos"] if v["capa"] == "aroll"]
        self.assertEqual(a0["desde"] + a0["dur"], a1["desde"])
        self.assertEqual(a0["trim"], 30)            # in 5,0 s − inicio del proxy 4,0 s
        self.assertEqual(a1["kf"][0]["cuadro"], 42)
        self.assertEqual(tl["duracion"], 120)

    def test_voz_en_pista_propia(self):
        tl = self.adaptar()
        self.assertEqual([v["src"] for v in tl["voces"]], ["medios/voz_A_+15.0dB.wav"] * 2)
        self.assertEqual([(v["desde"], v["dur"], v["trim"]) for v in tl["voces"]], [(0, 42, 30), (42, 78, 72)])
        with self.assertRaises(ad.ArmadoNoSoportado):    # una ganancia sin su WAV
            self.adaptar({"aroll": [{**ARMADO["aroll"][0], "ganancia_db": 12.0}]})

    def test_titulo_linea_de_base(self):
        g = self.adaptar()["graficos"][0]
        self.assertEqual(g["fontPx"], 100.0)
        self.assertAlmostEqual(g["base"], 400 + ad.CONFIG["titulos_v2"]["base_rel"] * 100)

    def test_audio_click_musica(self):
        tl = self.adaptar()
        click = next(x for x in tl["audio"] if x["src"].endswith("click.mp3"))
        self.assertEqual(click["desde"], 60)
        self.assertEqual(click["trim"], 8)           # 0,262 s de silencio del mp3
        self.assertAlmostEqual(click["volumen"], 10 ** (-8 / 20), places=4)
        musica = next(x for x in tl["audio"] if x["src"].endswith("musica.wav"))
        self.assertEqual(musica["fadeFinal"], 60)
        self.assertEqual(tl["transiciones"], [{"tipo": "panLeft", "cuadro": 42}])

    def test_broll_pisa_como_overwrite(self):
        # dos insertos que se cruzan: el segundo pisa la cola del primero (overwriteClip en una pista)
        tl = self.adaptar({"broll": [ARMADO["broll"][0], {**ARMADO["broll"][0], "t": 1.5, "in": 3.0, "out": 4.0}]})
        b0, b1 = [v for v in tl["videos"] if v["capa"] == "broll"]
        self.assertEqual((b0["desde"], b0["dur"]), (30, 15))
        self.assertEqual((b1["desde"], b1["dur"]), (45, 30))

    def test_rechaza_lo_que_no_sabe_hacer(self):
        with self.assertRaises(ad.ArmadoNoSoportado):
            self.adaptar({"light_leaks": [{"t": 1.0}]})
        with self.assertRaises(ad.ArmadoNoSoportado):
            self.adaptar({"titulos": [{"t": 1.0}]})
        with self.assertRaises(ad.ArmadoNoSoportado):
            self.adaptar({"broll": [{**ARMADO["broll"][0], "rotacion": 5}]})
        with self.assertRaises(ad.ArmadoNoSoportado):    # fuera del tramo del proxy
            self.adaptar({"broll": [{**ARMADO["broll"][0], "in": 5.5, "out": 6.5}]})
        with self.assertRaises(ad.ArmadoNoSoportado):    # A-roll superpuesto
            self.adaptar({"aroll": [ARMADO["aroll"][0], {**ARMADO["aroll"][1], "t": 1.0}]})
        with self.assertRaises(ad.ArmadoNoSoportado):
            self.adaptar({"graficos": [{**ARMADO["graficos"][0], "fondo_cargado": "neon"}]})

    def test_desenfoque_una_zona_por_titulo(self):
        # dos líneas del mismo título (mismo bloque y mismo final) comparten una sola zona desenfocada
        l1 = {**ARMADO["graficos"][0], "texto": "PROTECTOR", "fondo_cargado": "desenfoque"}
        l2 = {**l1, "texto": "SOLAR", "t": 2.3, "pos": [540, 520.0], "escala": 140.0}
        tl = self.adaptar({"graficos": [l1, l2]})
        self.assertEqual(len(tl["desenfoques"]), 1)
        z = tl["desenfoques"][0]
        self.assertEqual((z["desde"], z["hasta"]), (60, 90))
        bases = [g["base"] for g in tl["graficos"]]
        self.assertLess(z["y"], min(bases) - 100)          # abarca las dos líneas con margen
        self.assertGreater(z["y"] + z["h"], max(bases))

    def test_sin_carpeta_publica_no_mueve_graficos(self):
        # sin cuadros para mirar (pruebas), ni títulos ni pastillas se mueven por la cabeza
        g = self.adaptar({"graficos": [{"tipo": "pastilla", "t": 2.0, "fin": 3.0, "texto": "DERMA SCAN", "escala": 86,
                                        "pos": [545, 440], "bloque": 1}]})["graficos"][0]
        self.assertEqual(g["cy"], 440)
        self.assertNotIn("detras", g)

    def test_pastilla_medida_en_el_aprobado(self):
        # DERMA SCAN a escala 92 midió 873 x 166 px en el Video 1 FINAL
        g = self.adaptar({"graficos": [{"tipo": "pastilla", "t": 2.0, "fin": 3.0, "texto": "DERMA SCAN", "escala": 92,
                                        "pos": [545, 434], "bloque": 1}]})["graficos"][0]
        self.assertAlmostEqual(g["w"], 873, delta=3)
        self.assertAlmostEqual(g["h"], 166, delta=1)


if __name__ == "__main__":
    unittest.main()
